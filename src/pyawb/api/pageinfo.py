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

from collections.abc import Iterable, Mapping
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
