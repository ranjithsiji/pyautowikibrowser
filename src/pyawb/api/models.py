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
# Ported from AutoWikiBrowser WikiFunctions/API/UserInfo.cs, PageInfo.cs, SaveInfo.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""What the API returns about the user, an opened page and a save, parsed from JSON
(formatversion=2). Pure data: no network."""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from pyawb.api.errors import BrokenResponseException
from pyawb.core.site import Namespace

USERINFO_PROPS = "blockinfo|hasmsg|groups|rights"


@dataclass(frozen=True)
class UserInfo:
    """The logged-in user (meta=userinfo)."""

    name: str = ""
    id: int = 0
    groups: frozenset[str] = frozenset()
    rights: frozenset[str] = frozenset()
    is_blocked: bool = False
    has_messages: bool = False
    notifications: int = 0  # unread notifications (Echo), as of the last page opened

    @classmethod
    def from_json(cls, result: Mapping[str, Any]) -> UserInfo:
        query: Mapping[str, Any] = result.get("query", {})
        u: Mapping[str, Any] | None = query.get("userinfo")
        if u is None:
            raise BrokenResponseException("response with userinfo expected")
        return cls(
            name=str(u.get("name", "")),
            id=int(u.get("id", 0)),
            groups=frozenset(u.get("groups", ())),
            rights=frozenset(u.get("rights", ())),
            is_blocked="blockedby" in u or "blockid" in u,
            has_messages=bool(u.get("messages", False)),
        )

    def updated(self, result: Mapping[str, Any]) -> UserInfo:
        """UserInfo.Update: the new-message flag and notification count from a query that
        asked for them (userinfo with hasmsg, notifications with count)."""
        query: Mapping[str, Any] = result.get("query", {})
        u: Mapping[str, Any] | None = query.get("userinfo")
        if u is None:
            return self
        notes: Mapping[str, Any] = query.get("notifications", {})
        raw = notes.get("rawcount", 0)
        return replace(
            self,
            has_messages=bool(u.get("messages", False)),
            notifications=raw if isinstance(raw, int) else 0,
        )

    @property
    def is_logged_in(self) -> bool:
        return self.id != 0

    @property
    def is_sysop(self) -> bool:
        return self.is_in_group("sysop")

    @property
    def is_bot(self) -> bool:
        return self.is_in_group("bot") or self.has_right("bot")

    @property
    def has_api_high_limit(self) -> bool:
        return self.has_right("apihighlimits")

    def is_in_group(self, group: str) -> bool:
        return not group or group in self.groups

    def has_right(self, right: str) -> bool:
        return not right or right in self.rights

    def can_edit_page(self, page: PageInfo) -> bool:
        return (
            self.is_in_group(page.edit_protection) or self.has_right(page.edit_protection)
        ) and not (page.namespace_id == Namespace.MEDIAWIKI and not self.has_right("editinterface"))

    def can_create_page(self, page: PageInfo) -> bool:
        return self.is_in_group(page.create_protection) or self.has_right(page.create_protection)

    def can_move_page(self, page: PageInfo) -> bool:
        return page.namespace_id != Namespace.MEDIAWIKI and (
            self.is_in_group(page.move_protection) or self.has_right(page.move_protection)
        )

    def can_delete_page(self) -> bool:
        return self.has_right("delete")

    def can_protect_page(self) -> bool:
        return self.has_right("protect")


class PageTitleStatus(enum.Flag):
    NO_CHANGE = 0
    REDIRECT_LOOP = 1
    MULTIPLE_REDIRECTS = 2
    REDIRECTED = 4
    NORMALISED = 8


OPEN_PARAMS: Mapping[str, str | None] = {
    "action": "query",
    "converttitles": None,
    "prop": "info|revisions",
    "meta": "tokens",
    "type": "csrf|watch|rollback",
    "inprop": "protection|watched|displaytitle",
    "rvprop": "content|timestamp|ids",
    "rvslots": "main",
    "curtimestamp": None,
}
"""ApiEdit.Open's query (plus titles=, and redirects= when following redirects)."""


@dataclass(frozen=True)
class PageInfo:
    """A page opened for editing (PageInfo.cs). Text uses \\r\\n line endings, as in AWB."""

    title: str = ""
    original_title: str = ""
    display_title: str | None = None
    title_changed_status: PageTitleStatus = PageTitleStatus.NO_CHANGE
    text: str = ""
    exists: bool = False
    revision_id: int = -1
    namespace_id: int = 0
    timestamp: str = ""  # of the current revision (basetimestamp)
    token_timestamp: str = ""  # when the page was opened (starttimestamp)
    edit_token: str = ""
    watch_token: str = ""
    rollback_token: str = ""
    edit_protection: str = ""
    move_protection: str = ""
    create_protection: str = ""
    is_watched: bool = False
    content_model: str = "wikitext"

    @property
    def was_redirected(self) -> bool:
        return bool(
            self.title_changed_status
            & (
                PageTitleStatus.REDIRECTED
                | PageTitleStatus.REDIRECT_LOOP
                | PageTitleStatus.MULTIPLE_REDIRECTS
            )
        )

    @classmethod
    def from_json(cls, result: Mapping[str, Any]) -> PageInfo:
        query: Mapping[str, Any] = result.get("query", {})
        redirects: Sequence[Mapping[str, Any]] = query.get("redirects", ())
        status = PageTitleStatus.NO_CHANGE
        redirect_from = ""
        if redirects:
            first, last = redirects[0], redirects[-1]
            if first["from"] == last["to"] or last["from"] == last["to"]:
                return cls(
                    title=first["from"],
                    original_title=first["from"],
                    title_changed_status=PageTitleStatus.REDIRECT_LOOP,
                    exists=True,
                )
            redirect_from = str(first.get("from", ""))
            status = (
                PageTitleStatus.REDIRECTED
                if len(redirects) == 1
                else PageTitleStatus.MULTIPLE_REDIRECTS
            )

        pages: Sequence[Mapping[str, Any]] = query.get("pages", ())
        if not pages:
            if redirects:
                # a redirect to an interwiki or a special page: no page to edit
                return cls(title_changed_status=status, original_title=redirect_from)
            raise BrokenResponseException("cannot find the page in the response")
        page = pages[0]
        if page.get("invalid"):
            from pyawb.api.errors import InvalidTitleException

            raise InvalidTitleException(str(page.get("invalidreason", page.get("title", ""))))

        original = ""
        normalized: Sequence[Mapping[str, Any]] = query.get("normalized", ())
        if normalized:
            original = str(normalized[0].get("from", ""))
            status = (
                PageTitleStatus.NORMALISED
                if status == PageTitleStatus.NO_CHANGE
                else status | PageTitleStatus.NORMALISED
            )
        converted: Sequence[Mapping[str, Any]] = query.get("converted", ())
        if not original and converted:
            original = str(converted[0].get("from", ""))
        original = original or redirect_from

        tokens: Mapping[str, Any] = query.get("tokens", {})
        protection: dict[str, str] = {}
        for pr in page.get("protection", ()):
            protection.setdefault(str(pr.get("type")), str(pr.get("level", "")))

        text = ""
        timestamp = ""
        revisions: Sequence[Mapping[str, Any]] = page.get("revisions", ())
        content_model = str(page.get("contentmodel", "wikitext"))
        if revisions:
            rev = revisions[0]
            timestamp = str(rev.get("timestamp", ""))
            slot: Mapping[str, Any] = rev.get("slots", {}).get("main", rev)
            text = str(slot.get("content", ""))
            content_model = str(slot.get("contentmodel", content_model))

        title = str(page.get("title", ""))
        return cls(
            title=title,
            original_title=original or title,
            display_title=page.get("displaytitle"),
            title_changed_status=status,
            # API returns \n line endings; AWB works with \r\n
            text=text.replace("\n", "\r\n"),
            exists=not page.get("missing", False),
            revision_id=int(page.get("lastrevid", -1)),
            namespace_id=int(page.get("ns", 0)),
            timestamp=timestamp,
            token_timestamp=str(page.get("starttimestamp") or result.get("curtimestamp", "")),
            edit_token=str(tokens.get("csrftoken", "")),
            watch_token=str(tokens.get("watchtoken", "")),
            rollback_token=str(tokens.get("rollbacktoken", "")),
            edit_protection=protection.get("edit", ""),
            move_protection=protection.get("move", ""),
            create_protection=protection.get("create", ""),
            is_watched=bool(page.get("watched", False)),
            content_model=content_model,
        )


@dataclass(frozen=True)
class SaveInfo:
    """The result of action=edit (SaveInfo.cs)."""

    result: str = ""
    title: str = ""
    page_id: int = 0
    old_revision_id: int = 0
    new_revision_id: int = 0
    no_change: bool = False
    new_page: bool = False
    timestamp: str = ""
    extra: Mapping[str, Any] = field(default_factory=dict[str, Any])

    @property
    def success(self) -> bool:
        return self.result == "Success"

    @property
    def captcha(self) -> bool:
        return "captcha" in self.extra

    @classmethod
    def from_json(cls, result: Mapping[str, Any]) -> SaveInfo:
        e: Mapping[str, Any] | None = result.get("edit")
        if e is None:
            raise BrokenResponseException("response with edit result expected")
        known = {
            "result",
            "title",
            "pageid",
            "oldrevid",
            "newrevid",
            "nochange",
            "new",
            "newtimestamp",
        }
        return cls(
            result=str(e.get("result", "")),
            title=str(e.get("title", "")),
            page_id=int(e.get("pageid", 0)),
            old_revision_id=int(e.get("oldrevid", 0)),
            new_revision_id=int(e.get("newrevid", 0)),
            no_change=bool(e.get("nochange", False)),
            new_page=bool(e.get("new", False)),
            timestamp=str(e.get("newtimestamp", "")),
            extra={k: v for k, v in e.items() if k not in known},
        )


class WatchOptions(enum.Enum):
    NO_CHANGE = "nochange"
    WATCH = "watch"
    UNWATCH = "unwatch"
    PREFERENCES = "preferences"
