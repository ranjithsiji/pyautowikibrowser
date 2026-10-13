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
# Ported from AutoWikiBrowser WikiFunctions/Controls/Lists/ListMaker.cs, ListBox2.cs and
# ListComparer.cs. Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The page list (the model behind AWB's list maker): adding titles, de-duplicating, filtering,
selection, and comparing two lists. The Qt list view in ui/ shows one of these."""

from __future__ import annotations

import enum
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from pyawb.core import tools
from pyawb.core.article import Article
from pyawb.core.site import Namespace, current_site
from pyawb.core.textutil import turn_first_to_upper


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
        self.auto_alpha = False  # keep alphabetized (List ▸ Keep alphabetized)

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
        if self.auto_alpha:  # ListMaker.UpdateNumberOfArticles(true)
            self.sort()

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

    def sort(self, reverse: bool = False) -> None:
        """ListBox2.Sort / ReverseSort: MediaWiki's order (Article.compare_to). The selection
        follows the pages it was on."""
        chosen = {id(self.items[i]) for i in self._selected}
        self.items.sort(reverse=reverse)  # stable, as only equal names tie
        self._selected = {i for i, a in enumerate(self.items) if id(a) in chosen}

    def convert_to_talk_pages(self) -> None:
        """ListMaker.ConvertToTalkPages: each page's talk page, added back through add()."""
        titles = tools.convert_to_talk_list(a.name for a in self.items)
        self.clear()
        self.add([Article(t) for t in titles])

    def convert_from_talk_pages(self) -> None:
        """ListMaker.ConvertFromTalkPages."""
        titles = tools.convert_from_talk_list(a.name for a in self.items)
        self.clear()
        self.add([Article(t) for t in titles])

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
    def selected_indices(self) -> list[int]:
        return sorted(self._selected)

    def select_all(self) -> None:
        self._selected = set(range(len(self.items)))

    def select_none(self) -> None:
        self._selected = set()

    def invert_selection(self) -> None:
        self._selected = set(range(len(self.items))) - self._selected

    def copy_text(self) -> str:
        """Tools.Copy(ListBox): the selected titles, one per line."""
        return "\n".join(a.name for a in self.get_selected_article_list()).strip()

    def move_selected(self, to_top: bool) -> None:
        """ListMaker.MoveSelectedItems: the selected pages, in their order, to the top or the
        bottom (the instances selected, not earlier duplicates). They stay selected."""
        moving = self.get_selected_article_list()
        if not moving:
            return
        rest = [a for n, a in enumerate(self.items) if n not in self._selected]
        self.items = moving + rest if to_top else rest + moving
        start = 0 if to_top else len(rest)
        self._selected = set(range(start, start + len(moving)))

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

    # -- progress (PyAWB keeps pages it is done with, marked, so the loop can go back) ---------

    SAVED = "saved"
    SKIPPED = "skipped"

    @property
    def done_count(self) -> int:
        return sum(1 for a in self.items if a.list_status)

    def next_pending(self, start: int = 0) -> int:
        """The first page at or after start that the loop has not done, or -1."""
        for i in range(max(start, 0), len(self.items)):
            if not self.items[i].list_status:
                return i
        return -1

    def select(self, index: int) -> None:
        """Make index the only selected page (the page the loop is on)."""
        self._selected = {index} if 0 <= index < len(self.items) else set()

    def remove_done(self) -> None:
        """Remove the pages the loop has saved or skipped (AWB removes them as it goes)."""
        current = self.selected_article()
        self.items = [a for a in self.items if not a.list_status]
        self._selected = set()
        if current is not None and current in self.items:
            self._selected.add(self.items.index(current))

    # -- the edit loop (ListMaker.SelectedArticle, Remove, ReplaceArticle) ----------------------

    def selected_article(self) -> Article | None:
        """The first selected page; selects the first page if none is (None if the list is
        empty)."""
        if not self.items:
            return None
        if not self._selected:
            self._selected.add(0)
        return self.items[self.selected_index]

    def remove(self, item: Article | str) -> bool:
        """Remove the first instance of a page (after saving or skipping it) and select the page
        that takes its place. False if it is not in the list."""
        if item not in self.items:
            return False
        if len(self._selected) == 1 and self.items[self.selected_index] == item:
            self.remove_selected()
            return True
        position = self.items.index(item)  # type: ignore[arg-type]
        self._selected.clear()
        del self.items[position]
        if len(self.items) == position:
            position -= 1
        if self.items:
            self._selected.add(position)
        return True

    def replace_article(self, old: Article | str, new: Article) -> None:
        """Put new where old is (a followed redirect, a normalised title) and select it. Where
        old is selected, that instance is replaced, not an earlier duplicate."""
        if len(self._selected) == 1 and self.items[self.selected_index] == old:
            position = self.selected_index
        else:
            position = self.items.index(old)  # type: ignore[arg-type]
        new.list_status = self.items[position].list_status
        del self.items[position]
        self._selected.clear()
        self.items.insert(position, new)
        self._selected.add(position)


class OutputFormat(enum.IntEnum):
    """ListBox2.OutputFormat: the Save list formats, in the dialog's filter order."""

    WIKI_TEXT = 1  # "# [[:Title]]" lines
    PLAIN_TEXT = 2
    CSV = 3  # "a, b"
    CSV_WIKI_TEXT = 4  # "[[:a]], [[:b]]"


SAVE_FILTERS: dict[OutputFormat, str] = {
    OutputFormat.WIKI_TEXT: "Text file with wiki markup (*.txt)",
    OutputFormat.PLAIN_TEXT: "Plaintext list (*.txt)",
    OutputFormat.CSV: "CSV (Comma Separated Values) (*.txt)",
    OutputFormat.CSV_WIKI_TEXT: "CSV with Wikitext (*.txt)",
}


def format_list(articles: Iterable[Article], fmt: OutputFormat) -> str:
    """ListBox2.SaveList's text (AppendLine ends lines with a newline; the CSV forms have none)."""
    names = [a.name for a in articles]
    if fmt is OutputFormat.WIKI_TEXT:
        return "".join(f"# [[:{n}]]\n" for n in names)
    if fmt is OutputFormat.PLAIN_TEXT:
        return "".join(f"{n}\n" for n in names)
    if fmt is OutputFormat.CSV:
        return ", ".join(names)
    return ", ".join(f"[[:{n}]]" for n in names)


def save_list(articles: Iterable[Article], path: Path, fmt: OutputFormat) -> None:
    """Write the list as UTF-8 (Tools.WriteTextFileAbsolutePath)."""
    path.write_text(format_list(articles, fmt), encoding="utf-8", newline="\n")


def compare_lists(
    list1: Sequence[Article], list2: Sequence[Article]
) -> tuple[list[Article], list[Article], list[Article]]:
    """(only in list1, only in list2, in both), each without repeats (ListComparer.CompareLists)."""
    set1, set2 = set(list1), set(list2)
    only1 = [a for a in _distinct(list1) if a not in set2]
    only2 = [a for a in _distinct(list2) if a not in set1]
    both = [a for a in _distinct(list1) if a in set2]
    return only1, only2, both
