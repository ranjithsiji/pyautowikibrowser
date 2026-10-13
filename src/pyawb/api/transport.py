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
"""How pyawb.api talks to a wiki: a Transport sends one API request and returns the JSON.

Everything above this layer (siteinfo, CheckPage, open/save, Wikidata) is written against the
Transport protocol, so tests use a fake transport and never touch the network. PywikibotTransport
is the real one: pywikibot does the HTTP, login cookies, throttling, maxlag waits and assert=user.

pywikibot is configured in code (no user-config.py); load_pywikibot must run before anything
imports pywikibot.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol

from pyawb import __version__
from pyawb.api.errors import ApiErrorException, api_error, check_errors

if TYPE_CHECKING:
    import pywikibot.site

type Param = str | int | bool | None
"""A request parameter: True/None mean a flag with no value; False leaves it out."""


class Transport(Protocol):
    """One wiki's API endpoint."""

    def request(
        self, params: Mapping[str, Param], *, post: bool = False, token: str | None = None
    ) -> Mapping[str, Any]:
        """Send an API request (formatversion=2 JSON) and return the decoded response.

        token: a token type ("csrf", "watch", "rollback", "login"); the transport adds the token
        parameter. Errors raise the matching pyawb.api.errors exception.
        """
        ...


def normalise_params(params: Mapping[str, Param]) -> dict[str, str]:
    """Flags (True/None) become "1"; False is dropped; format=json, formatversion=2 added."""
    out: dict[str, str] = {"format": "json", "formatversion": "2"}
    for k, v in params.items():
        if v is False:
            continue
        out[k] = "1" if v is True or v is None else str(v)
    return out


# pywikibot ------------------------------------------------------------------------------------

USER_AGENT_FORMAT = (
    "PyAutoWikiBrowser/"
    + __version__
    + " ({script_comments}) {pwb} ({revision}) {http_backend} {python}"
)
"""Descriptive User-Agent (Wikimedia User-Agent policy): program, version, then pywikibot's
comments: the contact given to load_pywikibot, the wiki and the logged-in account."""

_pywikibot: ModuleType | None = None


def default_data_dir() -> Path:
    """Where pywikibot keeps cookies, throttle files and caches for PyAutoWikiBrowser."""
    from pyawb.paths import data_dir

    return data_dir() / "pywikibot"


def load_pywikibot(data_dir: Path | None = None, contact: str = "") -> ModuleType:
    """Import pywikibot configured for PyAutoWikiBrowser: no user-config.py, our own data directory,
    descriptive User-Agent, maxlag on writes, no console prompts.

    contact: a URL or e-mail address for the User-Agent. Wikimedia rate-limits clients that
    give no way to contact them; once logged in, the account's user page is added as well.
    """
    global _pywikibot
    if _pywikibot is not None:
        return _pywikibot
    data_dir = data_dir or default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    # pywikibot only accepts PYWIKIBOT_DIR if it holds a user-config.py (otherwise it writes its
    # cache and throttle files to the working directory); with PYWIKIBOT_NO_USER_CONFIG=2 the
    # file is not read
    marker = data_dir / "user-config.py"
    if not marker.exists():
        marker.write_text(
            "# PyAutoWikiBrowser configures pywikibot in code (pyawb.api.transport)\n"
        )
    os.environ["PYWIKIBOT_NO_USER_CONFIG"] = "2"
    os.environ["PYWIKIBOT_DIR"] = str(data_dir)

    import pywikibot
    from pywikibot import config

    config.user_agent_format = USER_AGENT_FORMAT
    config.user_agent_description = contact or None
    config.write_maxlag = 5  # Wikimedia's recommended value for automated edits
    config.put_throttle = 1  # seconds between saves; the edit loop adds the user's own delay
    config.max_retries = 5
    config.noisysleep = 3600.0  # don't print every maxlag wait on the console
    config.log = []
    _pywikibot = pywikibot
    return pywikibot


def pywikibot_site(
    lang: str, project: str, custom_url: str | None = None
) -> pywikibot.site.APISite:
    """The pywikibot site for a Wikimedia project (lang, project) or a custom wiki's script URL
    (e.g. "https://wiki.example.org/w/")."""
    pwb = load_pywikibot()
    if custom_url:
        from pywikibot.family import AutoFamily

        fam = AutoFamily("awbl-custom", custom_url.rstrip("/") + "/api.php")
        return pwb.Site(fam.name, fam)  # type: ignore[no-any-return]
    family = {"commons": "commons", "meta": "meta", "species": "species"}.get(project, project)
    if family in ("commons", "meta", "species", "mediawiki", "incubator", "wikidata"):
        lang = family
    return pwb.Site(lang, family)  # type: ignore[no-any-return]


class PywikibotTransport:
    """Transport over a pywikibot APISite."""

    def __init__(self, site: pywikibot.site.APISite) -> None:
        self.site = site

    def request(
        self, params: Mapping[str, Param], *, post: bool = False, token: str | None = None
    ) -> Mapping[str, Any]:
        from pywikibot.exceptions import APIError

        p: dict[str, Any] = normalise_params(params)
        del p["format"]  # pywikibot adds format=json itself
        if token is not None:
            p["token"] = self.site.tokens[token]
        req = self.site.simple_request(**p)
        if post:
            req.use_get = False
        try:
            result: Mapping[str, Any] = req.submit()
        except APIError as e:
            raise api_error(e.code, e.info, e.other) from e
        return check_errors(result)

    def login(self, username: str, password: str) -> None:
        """Log in without console prompts. A bot password ("Name@BotName") uses action=login;
        a main password uses action=clientlogin (two-factor accounts need a bot password)."""
        from pywikibot import login as pwb_login
        from pywikibot.exceptions import APIError, NoUsernameError

        from pyawb.api.session import LoginException

        manager = pwb_login.ClientLoginManager(password=password, site=self.site, user=username)
        try:
            ok = manager.login(retry=False)
        except (APIError, NoUsernameError) as e:
            raise LoginException(str(e)) from e
        if not ok:
            raise LoginException(f"login as {username} failed")
        # tell the site who is logged in; it checks the session cookie against userinfo
        self.site.login(user=username.split("@", 1)[0], cookie_only=True)

    def logout(self) -> None:
        self.site.logout()


__all__ = [
    "ApiErrorException",
    "Param",
    "PywikibotTransport",
    "Transport",
    "load_pywikibot",
    "normalise_params",
    "pywikibot_site",
]
