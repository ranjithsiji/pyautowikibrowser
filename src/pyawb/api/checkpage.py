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
#
# Ported from AutoWikiBrowser WikiFunctions/Session.cs (UpdateWikiStatus), Updater.cs and
# UsernameComparer.cs. Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The CheckPage gate: may this user edit with PyAutoWikiBrowser on this wiki?

Three JSON pages decide it, as in AWB:

- the global version page on English Wikipedia (Wikipedia:AutoWikiBrowser/CheckPage/VersionJSON):
  enabled versions, globally banned user names (badnames), global users, global messages;
- the wiki's Project:AutoWikiBrowser/Config: messages, typo list location, pages without general
  fixes or typo fixing, and the allusersenabled / allusersenabledusermode switches;
- the wiki's Project:AutoWikiBrowser/CheckPageJSON: enabledusers and enabledbots.

evaluate_status is pure: it takes the page texts and the user and returns the decision.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pyawb.api.models import UserInfo
from pyawb.core.rx import DotNetOptions, DotNetRegex
from pyawb.core.textutil import turn_first_to_upper_no_project_check

VERSION_PAGE_URL = (
    "https://en.wikipedia.org/w/index.php?"
    "title=Wikipedia:AutoWikiBrowser/CheckPage/VersionJSON&action=raw"
)
VERSION_PAGE_TITLE = "Wikipedia:AutoWikiBrowser/CheckPage/VersionJSON"
CHECKPAGE_TITLE = "Project:AutoWikiBrowser/CheckPageJSON"
CONFIG_TITLE = "Project:AutoWikiBrowser/Config"

DEFAULT_WIKI_CONFIG: Mapping[str, Any] = {
    "typolink": "",
    "allusersenabled": True,
    "allusersenabledusermode": True,
    "messages": [],
    "underscoretitles": [],
    "nogenfixes": [],
    "noregextypofix": [],
}
"""Session.DefaultWikiConfig: used when the wiki has no Config page."""


class WikiStatus(enum.Enum):
    """Variables.WikiStatusResult."""

    ERROR = "error"
    NOT_LOGGED_IN = "not logged in"
    NOT_REGISTERED = "not registered"  # not on the CheckPage, or a banned user name
    OLD_VERSION = "old version"  # this version is disabled
    NO_RIGHTS = "no rights"
    REGISTERED = "registered"


def usernames_equal(x: str, y: str) -> bool:
    """UsernameComparer: user names compare with the first letter case-insensitive."""
    return turn_first_to_upper_no_project_check(x) == turn_first_to_upper_no_project_check(y)


def _contains_user(names: Iterable[str], user: str) -> bool:
    return any(usernames_equal(n, user) for n in names)


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value]  # pyright: ignore[reportUnknownVariableType]


def _distinct(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _load_json(text: str) -> Mapping[str, Any]:
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON object expected")
    return data  # pyright: ignore[reportUnknownVariableType]


@dataclass(frozen=True)
class Message:
    """A message for users of some versions ("*" for all) from a Config or version page."""

    text: str
    versions: tuple[str, ...]
    enabled: bool = True

    def applies_to(self, app_version: str) -> bool:
        # AWB: TODO proper semver checking; exact match or "*"
        return self.enabled and any(v in ("*", app_version) for v in self.versions)


def parse_messages(value: Any) -> tuple[Message, ...]:
    """Session.JSONMessages: the "messages" array; a message's "version" is a string or array."""
    out: list[Message] = []
    if not isinstance(value, list):
        return ()
    for m in value:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(m, dict) or m.get("text") is None:  # pyright: ignore[reportUnknownMemberType]
            continue
        msg: dict[str, Any] = m  # pyright: ignore[reportUnknownVariableType]
        version = msg.get("version", "")
        versions = tuple(_strings(version)) if isinstance(version, list) else (str(version),)
        enabled = msg.get("enabled")
        out.append(Message(str(msg["text"]).strip(), versions, enabled is None or bool(enabled)))
    return tuple(out)


@dataclass(frozen=True)
class EnabledVersion:
    version: str
    dev: bool = False


@dataclass(frozen=True)
class VersionPage:
    """The global version page (Updater.UpdateFunc)."""

    enabled_versions: tuple[EnabledVersion, ...] = ()
    updater_version: str = ""
    badnames: tuple[str, ...] = ()
    globalusers: tuple[str, ...] = ()
    messages: tuple[Message, ...] = ()

    @classmethod
    def parse(cls, text: str) -> VersionPage:
        data = _load_json(text)
        versions: list[EnabledVersion] = []
        for v in data.get("enabledversions", []):
            if isinstance(v, dict):
                ver: dict[str, Any] = v  # pyright: ignore[reportUnknownVariableType]
                versions.append(EnabledVersion(str(ver.get("version", "")), bool(ver.get("dev"))))
        return cls(
            enabled_versions=tuple(versions),
            updater_version=str(data.get("updaterversion", "")),
            badnames=tuple(_strings(data.get("badnames"))),
            globalusers=tuple(_strings(data.get("globalusers"))),
            messages=parse_messages(data.get("messages")),
        )

    def is_enabled(self, app_version: str) -> bool:
        return any(v.version == app_version for v in self.enabled_versions)

    def newer_versions(self, app_version: str) -> list[str]:
        """Released (not dev) versions newer than app_version: optional updates."""
        current = _version_key(app_version)
        return [
            v.version
            for v in self.enabled_versions
            if not v.dev and _version_key(v.version) > current
        ]

    def is_bad_name(self, user_name: str) -> bool:
        """The user name matches a globally banned pattern (IgnoreCase | Multiline)."""
        if not user_name:
            return False
        opts = DotNetOptions.IGNORE_CASE | DotNetOptions.MULTILINE
        return any(DotNetRegex(p, opts).is_match(user_name) for p in self.badnames)


def _version_key(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for p in version.split("."):
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


@dataclass(frozen=True)
class WikiConfigPage:
    """Project:AutoWikiBrowser/Config."""

    typo_link: str = ""
    all_users_enabled: bool = True
    all_users_enabled_user_mode: bool = True
    messages: tuple[Message, ...] = ()
    underscore_titles: tuple[str, ...] = ()
    no_genfixes: tuple[str, ...] = ()
    no_regex_typo_fix: tuple[str, ...] = ()
    is_default: bool = False

    @classmethod
    def parse(cls, text: str) -> WikiConfigPage:
        """The page's JSON, or AWB's default configuration when the page is empty."""
        is_default = not text.strip()
        data = DEFAULT_WIKI_CONFIG if is_default else _load_json(text)
        return cls(
            typo_link=str(data.get("typolink") or ""),
            all_users_enabled=bool(data.get("allusersenabled", False)),
            all_users_enabled_user_mode=bool(data.get("allusersenabledusermode", False)),
            messages=parse_messages(data.get("messages")),
            underscore_titles=tuple(
                t for t in (s.strip() for s in _strings(data.get("underscoretitles"))) if t
            ),
            no_genfixes=_distinct(_strings(data.get("nogenfixes"))),
            no_regex_typo_fix=_distinct(_strings(data.get("noregextypofix"))),
            is_default=is_default,
        )


@dataclass(frozen=True)
class CheckPage:
    """Project:AutoWikiBrowser/CheckPageJSON."""

    enabled_users: tuple[str, ...] = ()
    enabled_bots: tuple[str, ...] = ()

    @classmethod
    def parse(cls, text: str) -> CheckPage:
        data = _load_json(text)
        return cls(
            tuple(_strings(data.get("enabledusers"))), tuple(_strings(data.get("enabledbots")))
        )


@dataclass(frozen=True)
class StatusResult:
    """The decision, with what the Config page sets for the session."""

    status: WikiStatus
    is_bot: bool = False  # bot mode allowed (listed in enabledbots)
    messages: tuple[str, ...] = ()  # to show to the user
    config: WikiConfigPage = field(default_factory=WikiConfigPage)
    reason: str = ""  # why it failed, for the log

    @property
    def can_edit(self) -> bool:
        return self.status == WikiStatus.REGISTERED


def evaluate_status(
    user: UserInfo,
    version_page_text: str,
    config_page_text: str,
    checkpage_text: str,
    *,
    app_version: str,
    project: str = "wikipedia",
    require_enabled_version: bool = True,
) -> StatusResult:
    """Session.UpdateWikiStatus: decide whether the user may edit.

    require_enabled_version: refuse when app_version is not in the version page's enabled
    versions. Any malformed page gives WikiStatus.ERROR, as in AWB.
    """
    try:
        version_page = VersionPage.parse(version_page_text)
    except ValueError as e:
        return StatusResult(WikiStatus.ERROR, reason=f"version page: {e}")
    if require_enabled_version and not version_page.is_enabled(app_version):
        return StatusResult(WikiStatus.OLD_VERSION, reason=f"version {app_version} is not enabled")
    if not user.is_logged_in:
        return StatusResult(WikiStatus.NOT_LOGGED_IN)

    try:
        if version_page.is_bad_name(user.name):
            return StatusResult(WikiStatus.NOT_REGISTERED, reason="user name is not allowed")
        config = WikiConfigPage.parse(config_page_text)
    except Exception as e:  # malformed JSON or badname pattern
        return StatusResult(WikiStatus.ERROR, reason=str(e))

    messages = tuple(
        m.text for m in (*version_page.messages, *config.messages) if m.applies_to(app_version)
    )

    def result(status: WikiStatus, is_bot: bool = False, reason: str = "") -> StatusResult:
        return StatusResult(status, is_bot, messages, config, reason)

    # no approval needed if the wiki has no CheckPage, or the Config page enables everyone
    if not checkpage_text or config.all_users_enabled:
        return result(WikiStatus.REGISTERED, is_bot=True)

    try:
        checkpage = CheckPage.parse(checkpage_text)
    except ValueError as e:
        return result(WikiStatus.ERROR, reason=f"CheckPage: {e}")

    is_bot_enabled = _contains_user(checkpage.enabled_bots, user.name)
    if (
        config.all_users_enabled_user_mode
        or (user.is_sysop and project != "wikia")
        or is_bot_enabled
        or _contains_user(checkpage.enabled_users, user.name)
    ):
        return result(WikiStatus.REGISTERED, is_bot=is_bot_enabled)

    if project != "custom" and user.name in version_page.globalusers:
        return result(WikiStatus.REGISTERED)
    return result(WikiStatus.NOT_REGISTERED, reason="not listed on the CheckPage")


def raw_page_params(title: str) -> dict[str, str]:
    """Query for a page's current wikitext (AWB fetches index.php?action=raw)."""
    return {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": title,
    }


def raw_page_text(result: Mapping[str, Any]) -> str:
    """The text from a raw_page_params response; "" for a missing page."""
    pages: Sequence[Mapping[str, Any]] = result.get("query", {}).get("pages", ())
    if not pages or pages[0].get("missing") or pages[0].get("invalid"):
        return ""
    revisions: Sequence[Mapping[str, Any]] = pages[0].get("revisions", ())
    if not revisions:
        return ""
    rev = revisions[0]
    slot: Mapping[str, Any] = rev.get("slots", {}).get("main", rev)
    return str(slot.get("content", ""))
