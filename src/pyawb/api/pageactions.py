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
# After AutoWikiBrowser WikiFunctions/API/ApiEdit.cs (Move, Delete, Protect), Article.cs and
# Controls/ArticleActionDialog.cs (GPL-2.0-or-later).
"""Move, delete and protect a page (the Start tab's admin buttons), and the reasons and
protection levels the dialog offers."""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pyawb.api.errors import check_errors
from pyawb.api.transport import Param, Transport


class PageAction(enum.Enum):
    """ArticleAction."""

    MOVE = "Move"
    DELETE = "Delete"
    PROTECT = "Protect"


# AWB's ArticleActionDialog reasons (English Wikipedia's); used where the wiki's own dropdown
# message is empty
AWB_REASONS: Mapping[PageAction, tuple[str, ...]] = {
    PageAction.MOVE: (
        "Typo in page title",
        "Wikipedia naming convention",
        "Reverting vandalism page move",
        "Facilitating concordance with a category's name",
    ),
    PageAction.PROTECT: (
        "Excessive vandalism",
        "High traffic page",
        "Excessive spamming",
        "Edit warring",
    ),
    PageAction.DELETE: (
        "tagged for [[WP:PROD|proposed deletion]] for 7 days",
        "[[WP:CSD#G1|G1]]: [[WP:PN|Patent nonsense]], meaningless, or incomprehensible",
        "[[WP:CSD#G2|G2]]: Test page",
        "[[WP:CSD#G3|G3]]: [[WP:Vandalism|Vandalism]]",
        "[[WP:CSD#G6|G6]]: Housekeeping and routine (non-controversial) cleanup",
        "[[WP:CSD#G7|G7]]: One author who has requested deletion or blanked the page",
        "[[WP:CSD#G8|G8]]: Page dependent on a deleted or nonexistent page",
        "[[WP:CSD#R2|Cross namespace redirect from mainspace]]",
        "[[WP:CSD#C1|C1]]: Empty category",
        "[[WP:CSD#U1|U1]]: User request to delete page in own userspace",
    ),
}

# MediaWiki's own reason lists, in the wiki's language
DROPDOWN_MESSAGES: Mapping[PageAction, str] = {
    PageAction.MOVE: "movepage-reason-dropdown",
    PageAction.DELETE: "deletereason-dropdown",
    PageAction.PROTECT: "protect-dropdown",
}

DEFAULT_LEVELS = ("", "autoconfirmed", "sysop")
EXPIRY_INFINITE = "infinite"


def parse_dropdown(text: str) -> list[str]:
    """A MediaWiki reason dropdown ("* Group" lines, "** reason" lines): the reasons."""
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("**"):
            reason = line.lstrip("*").strip()
            if reason:
                out.append(reason)
    return out


def reasons(transport: Transport, action: PageAction) -> list[str]:
    """The wiki's reasons for action (content language), or AWB's when it has none."""
    result: Mapping[str, Any] = transport.request(
        {
            "action": "query",
            "meta": "allmessages",
            "ammessages": DROPDOWN_MESSAGES[action],
            "amenableparser": True,
            "amincludelocal": True,
            "amlang": "content",
        }
    ).get("query", {})
    for m in result.get("allmessages", ()):
        if m.get("missing"):
            continue
        found = parse_dropdown(str(m.get("content", "")))
        if found:
            return found
    return list(AWB_REASONS[action])


def protection_levels(siteinfo: Mapping[str, Any]) -> list[str]:
    """The wiki's protection levels ("" = no protection), from siteinfo restrictions."""
    levels: Sequence[Any] = siteinfo.get("restrictions", {}).get("levels", ())
    return [str(x) for x in levels] or list(DEFAULT_LEVELS)


def with_tag(reason: str, tag: str, add: bool) -> str:
    """Article.ArticleActionSummary: "reason (tag)" with Preferences ▸ add "using AWB" on page
    actions."""
    return f"{reason} ({tag.strip()})" if add and tag.strip() else reason


@dataclass(frozen=True)
class MoveRequest:
    to: str
    reason: str
    move_talk: bool = True
    no_redirect: bool = False
    watch: bool = False


@dataclass(frozen=True)
class ProtectRequest:
    reason: str
    edit: str = ""  # level; "" = all users
    move: str = ""
    expiry: str = EXPIRY_INFINITE
    cascade: bool = False
    watch: bool = False


def _watch(params: dict[str, Param], watch: bool) -> None:
    if watch:
        params["watchlist"] = "watch"


def move(transport: Transport, title: str, req: MoveRequest) -> Mapping[str, Any]:
    """ApiEdit.Move."""
    params: dict[str, Param] = {
        "action": "move",
        "from": title,
        "to": req.to,
        "reason": req.reason,
        "movetalk": req.move_talk,
        "noredirect": req.no_redirect,
    }
    _watch(params, req.watch)
    return check_errors(transport.request(params, post=True, token="csrf"))


def delete(transport: Transport, title: str, reason: str, watch: bool = False) -> Mapping[str, Any]:
    """ApiEdit.Delete."""
    params: dict[str, Param] = {"action": "delete", "title": title, "reason": reason}
    _watch(params, watch)
    return check_errors(transport.request(params, post=True, token="csrf"))


def protect(transport: Transport, title: str, req: ProtectRequest) -> Mapping[str, Any]:
    """ApiEdit.Protect: edit and move levels ("" lifts that protection)."""
    protections = f"edit={req.edit or 'all'}|move={req.move or 'all'}"
    expiry = req.expiry.strip() or EXPIRY_INFINITE
    params: dict[str, Param] = {
        "action": "protect",
        "title": title,
        "reason": req.reason,
        "protections": protections,
        "expiry": f"{expiry}|{expiry}",
        "cascade": req.cascade,
    }
    _watch(params, req.watch)
    return check_errors(transport.request(params, post=True, token="csrf"))
