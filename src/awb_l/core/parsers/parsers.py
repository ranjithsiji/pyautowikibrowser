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
# Ported from AutoWikiBrowser WikiFunctions/Parse/Parsers.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Port of Parse/Parsers.cs (in progress: only what other modules need so far)."""

from __future__ import annotations

import enum

from awb_l.core import wikiregexes
from awb_l.core.site import current_site
from awb_l.core.textutil import remove_hash_from_page_title, turn_first_to_upper, wiki_decode


class DateLocale(enum.Enum):
    INTERNATIONAL = "International"
    AMERICAN = "American"
    ISO = "ISO"
    UNDETERMINED = "Undetermined"


def canonicalize_title_aggressively(title: str) -> str:
    """Title as MediaWiki stores it: decoded, first letter upper, canonical namespace prefix."""
    site = current_site()
    title = remove_hash_from_page_title(title)
    title = wiki_decode(title).strip()
    title = turn_first_to_upper(title, site)

    if title.startswith(":"):
        title = title[1:].strip()

    pos = title.find(":")
    if pos <= 0:
        return title

    title_part = title[: pos + 1]
    for key, regex in wikiregexes.for_site(site).NamespacesCaseInsensitive.items():
        m = regex.match(title_part)
        if not m.success or m.index != 0:
            continue
        return site.namespaces[key] + turn_first_to_upper(title[pos + 1 :].strip(), site)
    return title
