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
"""Page information for many pages at once (AWB API/PageInfo.cs reads displaytitle per page;
the list's "Format page titles per displaytitle" needs it for the whole list)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pyawb.api.transport import Transport

BATCH = 50  # titles per query for normal accounts


def display_titles(transport: Transport, titles: Iterable[str]) -> dict[str, str]:
    """title -> its displaytitle HTML, for the titles that exist and have one different from
    the title. Titles the wiki normalises are reported under the title asked for."""
    wanted = list(dict.fromkeys(titles))
    out: dict[str, str] = {}
    for start in range(0, len(wanted), BATCH):
        batch = wanted[start : start + BATCH]
        result: Mapping[str, Any] = transport.request(
            {
                "action": "query",
                "prop": "info",
                "inprop": "displaytitle",
                "titles": "|".join(batch),
            }
        ).get("query", {})
        back = {str(n["to"]): str(n["from"]) for n in result.get("normalized", ())}
        for page in result.get("pages", ()):
            title = str(page.get("title", ""))
            shown = page.get("displaytitle")
            if shown and shown != title and not page.get("missing"):
                out[back.get(title, title)] = str(shown)
    return out


def redirect_targets(transport: Transport, titles: Iterable[str]) -> dict[str, str]:
    """title -> target (with "#section" where the redirect has one), for the titles that are
    redirects. AWB opened each linked page in turn; here 50 titles go in each query."""
    wanted = list(dict.fromkeys(titles))
    out: dict[str, str] = {}
    for start in range(0, len(wanted), BATCH):
        batch = wanted[start : start + BATCH]
        result: Mapping[str, Any] = transport.request(
            {"action": "query", "titles": "|".join(batch), "redirects": True}
        ).get("query", {})
        back = {str(n["to"]): str(n["from"]) for n in result.get("normalized", ())}
        for r in result.get("redirects", ()):
            source = str(r["from"])
            target = str(r["to"])
            if r.get("tofragment"):
                target += "#" + str(r["tofragment"])
            out[back.get(source, source)] = target
    return out


@dataclass(frozen=True)
class Revision:
    """One line of the History tab."""

    revid: int
    parentid: int
    timestamp: str  # ISO 8601, UTC
    user: str
    comment: str
    size: int
    minor: bool
    size_change: int | None = None  # None for the oldest revision shown


def page_history(transport: Transport, title: str, limit: int = 50) -> list[Revision]:
    """The latest revisions of a page, newest first, with each one's change in size (AWB's
    History tab showed action=history; here the API's revisions)."""
    result: Mapping[str, Any] = transport.request(
        {
            "action": "query",
            "prop": "revisions",
            "titles": title,
            "rvprop": "ids|timestamp|user|comment|size|flags",
            "rvlimit": str(limit + 1),  # one more, for the size change of the last one shown
        }
    ).get("query", {})
    pages: Sequence[Mapping[str, Any]] = result.get("pages", ())
    if not pages:
        return []
    revs: Sequence[Mapping[str, Any]] = pages[0].get("revisions", ())
    out: list[Revision] = []
    for i, r in enumerate(revs[:limit]):
        older = revs[i + 1] if i + 1 < len(revs) else None
        size = int(r.get("size", 0))
        out.append(
            Revision(
                revid=int(r.get("revid", 0)),
                parentid=int(r.get("parentid", 0)),
                timestamp=str(r.get("timestamp", "")),
                user=str(r.get("user", "")),
                comment=str(r.get("comment", "")),
                size=size,
                minor=bool(r.get("minor", False)),
                size_change=size - int(older.get("size", 0)) if older is not None else None,
            )
        )
    return out


@dataclass(frozen=True)
class Backlink:
    """One line of the What links here tab."""

    title: str
    kind: str  # "link", "redirect" or "transclusion"
    ns: int = 0


def what_links_here(transport: Transport, title: str, limit: int = 500) -> list[Backlink]:
    """Pages that link to, redirect to or transclude title (Special:WhatLinksHere), up to limit
    of each kind; links first, then redirects, then transclusions."""
    links: Mapping[str, Any] = transport.request(
        {"action": "query", "list": "backlinks", "bltitle": title, "bllimit": str(limit)}
    ).get("query", {})
    redirects: Mapping[str, Any] = transport.request(
        {
            "action": "query",
            "list": "backlinks",
            "bltitle": title,
            "blfilterredir": "redirects",
            "bllimit": str(limit),
        }
    ).get("query", {})
    embeds: Mapping[str, Any] = transport.request(
        {"action": "query", "list": "embeddedin", "eititle": title, "eilimit": str(limit)}
    ).get("query", {})
    redirect_titles = {str(b.get("title", "")) for b in redirects.get("backlinks", ())}
    out = [
        Backlink(str(b.get("title", "")), "link", int(b.get("ns", 0)))
        for b in links.get("backlinks", ())
        if str(b.get("title", "")) not in redirect_titles
    ]
    out += [
        Backlink(str(b.get("title", "")), "redirect", int(b.get("ns", 0)))
        for b in redirects.get("backlinks", ())
    ]
    out += [
        Backlink(str(e.get("title", "")), "transclusion", int(e.get("ns", 0)))
        for e in embeds.get("embeddedin", ())
    ]
    return out
