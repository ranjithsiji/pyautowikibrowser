# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/Parse/WikiLinks.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Port of Parse/WikiLinks.cs (in progress)."""

from __future__ import annotations

import functools

from awb_l.core import wikiregexes as W


@functools.lru_cache(maxsize=10)
def _all_wiki_links(article_text: str) -> tuple[str, ...]:
    text = article_text
    links: list[str] = []
    while True:
        matches = W.SimpleWikiLink.matches(text)
        if not matches:
            break
        links.extend(m.value for m in matches)
        # process the link contents again for any (further) nested links
        text = ",".join(m.group(1) for m in matches)
    return tuple(links)


def get_all_wiki_links(article_text: str) -> list[str]:
    """All wikilinks, including those nested in other links (e.g. in image captions).

    Returns a new list each time (AWB returned its cached list, which callers then modified).
    """
    return list(_all_wiki_links(article_text))
