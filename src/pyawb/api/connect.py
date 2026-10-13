# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""Connect to the wiki a profile names, and log in with its account."""

from __future__ import annotations

from collections.abc import Iterable

from pyawb.api import credentials
from pyawb.api.credentials import KeyringBackend
from pyawb.api.models import UserInfo
from pyawb.api.session import LoginException, WikiSession
from pyawb.api.siteinfo import base_site_config
from pyawb.api.transport import (
    Cookie,
    PywikibotTransport,
    SecondFactor,
    load_pywikibot,
    pywikibot_site,
)
from pyawb.settings.appconfig import AppConfig, Profile


def open_session(config: AppConfig, profile: Profile) -> WikiSession:
    """A session on the profile's wiki (not yet loaded or logged in). pywikibot is set up with the
    configured User-Agent contact on first use."""
    load_pywikibot(contact=config.user_agent_contact)
    transport = PywikibotTransport(
        pywikibot_site(profile.lang, profile.project, profile.custom_url)
    )
    global_transport = PywikibotTransport(pywikibot_site("en", "wikipedia"))
    site = base_site_config(profile.lang, profile.project, profile.custom_url)
    return WikiSession(transport, site, global_transport=global_transport)


def wikidata_transport(config: AppConfig) -> PywikibotTransport:
    """Wikidata's API (sitelinks for Wikidata query lists), read-only and not logged in."""
    load_pywikibot(contact=config.user_agent_contact)
    return PywikibotTransport(pywikibot_site("wikidata", "wikidata"))


def log_in(
    session: WikiSession,
    profile: Profile,
    password: str | None = None,
    *,
    keyring: KeyringBackend | None = None,
    second_factor: SecondFactor | None = None,
) -> UserInfo:
    """Log in as the profile's account. Without password, the one remembered in the keychain is
    used. A password that works is remembered if the profile says so, and forgotten if not.
    second_factor answers the wiki's two-factor prompt (main-password logins)."""
    if not profile.username:
        raise LoginException(f"profile {profile.name!r} has no user name")
    remembered = credentials.load_password(profile.wiki_url, profile.username, keyring)
    password = password or remembered
    if not password:
        raise LoginException(f"no password for {profile.username}")
    user = session.login(profile.username, password, second_factor)
    if profile.remember_password:
        if password != remembered:
            credentials.save_password(profile.wiki_url, profile.username, password, keyring)
    elif remembered is not None:
        credentials.forget_password(profile.wiki_url, profile.username, keyring)
    return user


def connect(
    config: AppConfig,
    profile: Profile,
    password: str | None = None,
    *,
    keyring: KeyringBackend | None = None,
    second_factor: SecondFactor | None = None,
) -> WikiSession:
    """Open the profile's wiki, load its configuration and log in (the CheckPage is checked as
    part of logging in). Blocking: run it off the UI thread."""
    session = open_session(config, profile)
    session.load_site()
    log_in(session, profile, password, keyring=keyring, second_factor=second_factor)
    return session


def connect_with_cookies(
    config: AppConfig, profile: Profile, cookies: Iterable[Cookie], username: str
) -> WikiSession:
    """Open the profile's wiki and use a session from its own login page in a browser."""
    session = open_session(config, profile)
    session.load_site()
    session.login_with_cookies(cookies, username)
    return session


def wiki_transport(config: AppConfig, lang: str, project: str) -> PywikibotTransport:
    """Another Wikimedia wiki, read-only (a typo list kept elsewhere)."""
    load_pywikibot(contact=config.user_agent_contact)
    return PywikibotTransport(pywikibot_site(lang, project))
