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
#
# Ported from AutoWikiBrowser WikiFunctions/Parse/Tagger.cs (its list providers) and
# Lists/Providers/ListProviders.cs. Copyright (C) the AutoWikiBrowser contributors
# (GPL-2.0-or-later).
"""Tagger's wiki lookups (core.parsers.tagger.TaggerLookups) through the API, and template
expansion for subst (core.parsers.tagger.ExpandTemplate)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from awb_x.api.errors import ApiException
from awb_x.api.transport import Transport
from awb_x.core import wikiregexes as W
from awb_x.core.parsers.tagger import regular_categories
from awb_x.core.rx import DotNetRegex
from awb_x.core.site import Namespace
from awb_x.core.textutil import html_decode
from awb_x.core.tools import replace_with_spaces

MIN_INCOMING_LINKS_TO_BE_CONSIDERED_AN_ORPHAN = 3


def count_incoming_links(result: Mapping[str, Any]) -> int:
    """Mainspace pages linking to the page directly or through a redirect, not counting the
    redirects themselves (WhatLinksHereAndPageRedirectsExcludingTheRedirectsListProvider)."""
    count = 0
    backlinks: Sequence[Mapping[str, Any]] = result.get("query", {}).get("backlinks", ())
    for bl in backlinks:
        if not bl.get("redirect"):
            count += 1
        count += sum(1 for r in bl.get("redirlinks", ()) if not r.get("redirect"))
    return count


@dataclass
class WikiTaggerLookups:
    """TaggerLookups backed by the wiki's API (the page as last saved on the wiki)."""

    transport: Transport

    def total_categories(self, article_title: str, categories_in_text: int) -> int:
        if categories_in_text:
            return categories_in_text
        # templates may add categories that are not [[Category:]] links
        result = self.transport.request(
            {
                "action": "query",
                "prop": "categories",
                "titles": article_title,
                "clshow": "!hidden",
                "cllimit": 10,
            }
        )
        pages: Sequence[Mapping[str, Any]] = result.get("query", {}).get("pages", ())
        titles = [str(c["title"]) for p in pages for c in p.get("categories", ())]
        return len(regular_categories(titles))

    def orphan_status(
        self, article_title: str, restrict_orphan_tagging: bool
    ) -> tuple[bool, bool, int]:
        try:
            result = self.transport.request(
                {
                    "action": "query",
                    "list": "backlinks",
                    "bltitle": article_title,
                    "blnamespace": Namespace.ARTICLE,
                    "blfilterredir": "nonredirects",
                    "blredirect": True,
                    "bllimit": 10,
                }
            )
        except ApiException:
            # don't mark as orphan when the lookup fails
            return False, False, 0
        incoming = count_incoming_links(result)
        orphaned = incoming < MIN_INCOMING_LINKS_TO_BE_CONSIDERED_AN_ORPHAN
        return orphaned, (incoming == 0) if restrict_orphan_tagging else orphaned, incoming

    def mainspace_links(self, article_title: str) -> int:
        result = self.transport.request(
            {
                "action": "query",
                "prop": "links",
                "titles": article_title,
                "plnamespace": Namespace.ARTICLE,
                "pllimit": "max",
            }
        )
        pages: Sequence[Mapping[str, Any]] = result.get("query", {}).get("pages", ())
        return sum(len(p.get("links", ())) for p in pages)


@dataclass
class WikiTemplateExpander:
    """core.parsers.tagger.ExpandTemplate through action=expandtemplates (Tools.ExpandTemplate):
    every call matched by a regex (outside comments) is replaced by its expansion, unicodified;
    with include_comment the original call is kept in a comment after it. A call that fails to
    expand is left as it is."""

    transport: Transport

    def expand(self, call: str, article_title: str) -> str:
        result = self.transport.request(
            {"action": "expandtemplates", "prop": "wikitext", "title": article_title, "text": call},
            post=True,
        )
        return html_decode(str(result["expandtemplates"]["wikitext"]))

    def __call__(
        self,
        article_text: str,
        article_title: str,
        regexes: dict[DotNetRegex, str],
        include_comment: bool,
    ) -> str:
        from awb_x.core.parsers.parsers import Parsers

        parsers = Parsers()
        for regex in regexes:
            failed: set[str] = set()
            while True:
                # avoid matching on previously commented out calls
                text = replace_with_spaces(article_text, W.Comments)
                m = next((m for m in regex.matches(text) if m.value not in failed), None)
                if m is None:
                    break
                call = m.value
                try:
                    result = self.expand(call, article_title)
                except (ApiException, KeyError):
                    failed.add(call)
                    continue
                result = parsers.unicodify(result)
                if include_comment:
                    result += "<!-- " + call + " -->"
                new_text = article_text.replace(call, result)
                if new_text == article_text:
                    break
                article_text = new_text
        return article_text
