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
# Ported from AutoWikiBrowser WikiFunctions/Controls/Lists/ListMaker.cs, ListBox2.cs and
# ListComparer.cs. Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The page list (the model behind AWB's list maker): adding titles, de-duplicating, filtering,
selection, and comparing two lists. The Qt list view in ui/ shows one of these."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence

from awb_l.core import tools
from awb_l.core.article import Article
from awb_l.core.site import Namespace, current_site
from awb_l.core.textutil import turn_first_to_upper


def _distinct(items: Iterable[Article]) -> list[Article]:
    """In order, without repeats (LINQ Distinct)."""
    return list(dict.fromkeys(items))


class ArticleList:
    """An ordered list of pages, with a selection."""

    def __init__(self) -> None:
        self.items: list[Article] = []
        self._selected: set[int] = set()
        self.filter_duplicates = False  # don't add pages already in the list
        self.filter_non_main_auto = False  # only add mainspace pages

    # -- adding --------------------------------------------------------------------------------

    def add(self, item: Article | str | Iterable[Article]) -> None:
        """Add a page, a title (cleaned of link syntax, first letter upper on most wikis) or a list
        of pages (de-duplicated against the list if filter_duplicates)."""
        if isinstance(item, Article):
            self.items.append(item)
            return
        if isinstance(item, str):
            s = tools.remove_syntax(item)
            if current_site().capitalize_first_letter:
                s = turn_first_to_upper(s)
            item = [Article(s)]
        new = list(item)
        if not new:
            return
        if self.filter_non_main_auto:
            new = [a for a in new if a.namespace_key == Namespace.ARTICLE]
        if self.filter_duplicates:
            # LINQ Except: distinct items not already in the list
            existing = set(self.items)
            new = [a for a in _distinct(new) if a not in existing]
        self.items.extend(new)

    @staticmethod
    def normalize_title(s: str) -> str:
        """A page title from a URL or pasted text."""
        return tools.normalize_title_core(s)

    # -- list operations -----------------------------------------------------------------------

    @property
    def count(self) -> int:
        return len(self.items)

    @property
    def number_of_articles(self) -> int:
        return len(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[Article]:
        return iter(self.items)

    def __contains__(self, item: object) -> bool:
        return item in self.items

    def contains(self, item: Article | str) -> bool:
        return item in self.items

    def clear(self) -> None:
        self.items.clear()
        self._selected.clear()

    def remove_list_duplicates(self) -> None:
        """Remove repeats, keeping the first of each."""
        self.items = _distinct(self.items)
        self._selected.clear()

    def filter_non_main_articles(self) -> None:
        """Remove pages outside the main namespace."""
        self.items = [a for a in self.items if a.namespace_key == Namespace.ARTICLE]
        self._selected.clear()

    def get_article_list(self) -> list[Article]:
        return list(self.items)

    # -- selection -----------------------------------------------------------------------------

    def set_selected(self, index: int, selected: bool) -> None:
        if not 0 <= index < len(self.items):
            raise IndexError(index)
        if selected:
            self._selected.add(index)
        else:
            self._selected.discard(index)

    def get_selected_article_list(self) -> list[Article]:
        return [self.items[i] for i in sorted(self._selected)]

    @property
    def selected_index(self) -> int:
        """The first selected index, or -1."""
        return min(self._selected) if self._selected else -1

    def remove_selected(self, filter_duplicates: bool = False) -> None:
        """Remove the selected pages and select the page after them (AWB's ListBox2.RemoveSelected;
        filter_duplicates only chose a faster algorithm there)."""
        i = self.selected_index
        if i < 0:
            return
        selected = self._selected
        self.items = [a for n, a in enumerate(self.items) if n not in selected]
        self._selected = set()
        # if the last deleted page was at the end of the list, select the new end
        new_index = i if len(self.items) > i else min(i, len(self.items)) - 1
        if new_index >= 0:
            self._selected.add(new_index)


def compare_lists(
    list1: Sequence[Article], list2: Sequence[Article]
) -> tuple[list[Article], list[Article], list[Article]]:
    """(only in list1, only in list2, in both), each without repeats (ListComparer.CompareLists)."""
    set1, set2 = set(list1), set(list2)
    only1 = [a for a in _distinct(list1) if a not in set2]
    only2 = [a for a in _distinct(list2) if a not in set1]
    both = [a for a in _distinct(list1) if a in set2]
    return only1, only2, both
