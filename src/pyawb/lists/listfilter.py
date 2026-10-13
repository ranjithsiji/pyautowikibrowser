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
# Ported from AutoWikiBrowser WikiFunctions/Lists/ListFilterForm.cs (btnApply_Click).
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The List filter (List ▸ Filter…): namespaces to keep, titles to remove or keep, a set
operation with another list, duplicates and sorting. Unlike AWB's HashSet, the set operations
keep the list's order."""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass, field

from pyawb.core.article import Article
from pyawb.core.rx import DotNetRegex, escape


class SetOperation(enum.IntEnum):
    """cbOpType: AWB labelled the first "Symmetric difference", but it removes the other list's
    pages (a set difference)."""

    DIFFERENCE = 0
    INTERSECTION = 1


@dataclass(frozen=True)
class ListFilter:
    namespaces: frozenset[int] = frozenset()  # keep only these (none chosen: all)
    remove_containing: str = ""  # "Remove titles containing" (when not empty)
    keep_containing: str = ""  # "Keep titles containing"
    is_regex: bool = False
    remove_duplicates: bool = True
    sort: bool = True
    operation: SetOperation = SetOperation.DIFFERENCE
    other: tuple[str, ...] = field(default=())  # the set operation's list (titles)

    def apply(self, articles: Sequence[Article]) -> list[Article]:
        """The filtered list. A bad pattern raises ValueError or regex.error (the dialog reports
        it)."""
        out = list(dict.fromkeys(articles)) if self.remove_duplicates else list(articles)
        if self.other:
            others = set(self.other)
            if self.operation is SetOperation.DIFFERENCE:
                out = [a for a in dict.fromkeys(out) if a.name not in others]
            else:
                out = [a for a in dict.fromkeys(out) if a.name in others]
        if self.remove_containing or self.keep_containing:
            remove = self._regex(self.remove_containing)
            keep = self._regex(self.keep_containing)
            out = [
                a
                for a in out
                if not (remove and remove.is_match(a.name))
                and not (keep and not keep.is_match(a.name))
            ]
        if self.namespaces:
            out = [a for a in out if a.namespace_key in self.namespaces]
        if self.sort:
            out.sort()
        return out

    def _regex(self, text: str) -> DotNetRegex | None:
        if not text:
            return None
        return DotNetRegex(text if self.is_regex else escape(text))
