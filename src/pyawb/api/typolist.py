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
# Ported from AutoWikiBrowser WikiFunctions/Parse/RegExTypoFix.cs (TyposDownloader) and
# WikiFunctions/Session.cs (TypoLink)
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Where a wiki's typo list is, and fetching it (RegExTypo Fix, "RETF").

The list is Project:AutoWikiBrowser/Typos unless the wiki's AutoWikiBrowser/Config page names
another ("typolink": a page name, or a page URL on any Wikimedia wiki). AWB downloaded it over
plain HTTP; here it is read through the API like any page.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlsplit

import regex

from pyawb.api.session import WikiSession
from pyawb.api.transport import Transport
from pyawb.core.site import Namespace, SiteConfig

ENGLISH_TYPOS_TITLE = "Wikipedia:AutoWikiBrowser/Typos"
_WIKIMEDIA_HOST = regex.compile(
    r"([a-z][a-z0-9-]*)\.(wikipedia|wiktionary|wikisource|wikiquote|wikibooks|wikinews|"
    r"wikiversity|wikivoyage)\.org"
)


@dataclass(frozen=True)
class TypoLocation:
    """The typo list page. lang/project: another Wikimedia wiki, or None for this wiki."""

    title: str
    lang: str | None = None
    project: str | None = None

    @property
    def on_this_wiki(self) -> bool:
        return self.lang is None


def typo_location(typo_link: str, site: SiteConfig) -> TypoLocation:
    """Variables.RetfPath: the Config page's typolink, else Project:AutoWikiBrowser/Typos."""
    link = typo_link.strip()
    if not link:
        return TypoLocation(site.namespaces[Namespace.PROJECT] + "AutoWikiBrowser/Typos")
    if not link.startswith(("http://", "https://", "//")):
        return TypoLocation(link)
    parts = urlsplit(link if not link.startswith("//") else "https:" + link)
    title = ""
    query = parse_qs(parts.query)
    if "title" in query:
        title = query["title"][0]
    elif "/wiki/" in parts.path:
        title = parts.path.split("/wiki/", 1)[1]
    title = unquote(title).replace("_", " ")
    host = parts.hostname or ""
    if host == urlsplit(site.url).hostname:
        return TypoLocation(title)
    m = _WIKIMEDIA_HOST.fullmatch(host)
    if not m or not title:
        raise ValueError(f"the typo list is not on a Wikimedia wiki: {link}")
    return TypoLocation(title, m.group(1), m.group(2))


def fetch_typo_list(
    session: WikiSession,
    typo_link: str,
    other_wiki: Callable[[str, str], Transport] | None = None,
) -> tuple[TypoLocation, str]:
    """The typo list's wikitext ("" if the page does not exist). other_wiki(lang, project) gives
    a transport for a list kept on another wiki (connect.wiki_transport)."""
    location = typo_location(typo_link, session.site)
    transport: Transport | None = None
    if not location.on_this_wiki:
        assert location.lang is not None and location.project is not None
        if location.lang == "en" and location.project == "wikipedia":
            transport = session.global_transport
        elif other_wiki is not None:
            transport = other_wiki(location.lang, location.project)
        else:
            raise ValueError(f"cannot read {location.lang}.{location.project}")
    return location, session.raw_page(location.title, transport)


def fetch_english_typo_list(session: WikiSession) -> str:
    """English Wikipedia's list, which AWB offers when a wiki has none (English wikis only)."""
    return session.raw_page(ENGLISH_TYPOS_TITLE, session.global_transport)
