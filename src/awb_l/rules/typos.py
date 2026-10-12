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
"""RegExTypoFix list loading (port of the parsing half of WikiFunctions/Parse/RegExTypoFix.cs).

The list format is one `<Typo word="..." find="..." replace="..." />` per rule, with
.NET-syntax find/replace strings. Fetching the list page is the job of awb_l.api.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from awb_l.core import rx

ENWIKI_TYPOS_URL = (
    "https://en.wikipedia.org/w/index.php?title=Wikipedia:AutoWikiBrowser/Typos&action=raw"
)

# Same pattern as AWB's TypoRegex.
_TYPO = rx.compile(r'<(?:Typo)?\s+(?:word="(.*?)"\s+)?find="(.*?)"\s+replace="(.*?)"\s*/?>')


class TypoListError(ValueError):
    """The list is malformed; AWB refuses such lists to encourage fixing them."""


@dataclass(frozen=True)
class TypoEntry:
    word: str
    find: str
    replace: str


@dataclass
class TypoList:
    rules: list[tuple[TypoEntry, rx.Rule]] = field(default_factory=list[tuple[TypoEntry, rx.Rule]])
    errors: list[tuple[TypoEntry, str]] = field(default_factory=list[tuple[TypoEntry, str]])


def parse(text: str) -> list[TypoEntry]:
    """Extract entries. Raises TypoListError on duplicate find patterns, as AWB does."""
    entries: list[TypoEntry] = []
    seen: set[str] = set()
    for m in _TYPO.finditer(text):
        word, find, replace = m.group(1) or "", m.group(2), m.group(3)
        if find in seen:
            raise TypoListError(f"Duplicate typo rule {find!r} found.")
        seen.add(find)
        entries.append(TypoEntry(word, find, replace))
    return entries


def load(text: str) -> TypoList:
    """Parse and compile every rule; rules that fail are collected in `errors`."""
    result = TypoList()
    for entry in parse(text):
        try:
            result.rules.append((entry, rx.rule(entry.find, entry.replace)))
        except Exception as e:  # regex.error or UnsupportedPatternError
            result.errors.append((entry, str(e)))
    return result
