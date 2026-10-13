# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
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

from awb_x.api import credentials
from awb_x.api.credentials import KeyringBackend
from awb_x.api.models import UserInfo
from awb_x.api.session import LoginException, WikiSession
from awb_x.api.siteinfo import base_site_config
from awb_x.api.transport import PywikibotTransport, load_pywikibot, pywikibot_site
from awb_x.settings.appconfig import AppConfig, Profile


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


def log_in(
    session: WikiSession,
    profile: Profile,
    password: str | None = None,
    *,
    keyring: KeyringBackend | None = None,
) -> UserInfo:
    """Log in as the profile's account. Without password, the one remembered in the keychain is
    used. A password that works is remembered if the profile says so, and forgotten if not."""
    if not profile.username:
        raise LoginException(f"profile {profile.name!r} has no user name")
    remembered = credentials.load_password(profile.wiki_url, profile.username, keyring)
    password = password or remembered
    if not password:
        raise LoginException(f"no password for {profile.username}")
    user = session.login(profile.username, password)
    if profile.remember_password:
        if password != remembered:
            credentials.save_password(profile.wiki_url, profile.username, password, keyring)
    elif remembered is not None:
        credentials.forget_password(profile.wiki_url, profile.username, keyring)
    return user
