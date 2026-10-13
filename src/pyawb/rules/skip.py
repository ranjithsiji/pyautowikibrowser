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
# Ported from AutoWikiBrowser WikiFunctions/Article/Comparers/*.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Article comparers: does a page's text contain some text or match a regex? Used by the "skip if
contains / doesn't contain" options. %%keywords%% (%%title%% etc.) are expanded per page.

A regex comparer that times out does not match, and sets timed_out so the caller can report it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from pyawb.core import tools
from pyawb.core.rx import DotNetOptions, DotNetRegex

DEFAULT_TIMEOUT = 10.0
"""Seconds a regex comparer may run against one page."""


class PageLike(Protocol):
    """What a comparer needs from a page (core.article.Article)."""

    @property
    def name(self) -> str: ...

    @property
    def article_text(self) -> str: ...


class ArticleComparer(Protocol):
    """AWB's IArticleComparer."""

    def matches(self, article: PageLike) -> bool: ...


def _text(article: PageLike) -> str:
    return tools.convert_from_local_line_endings(article.article_text)


def _contains_ignore_case(text: str, comparator: str) -> bool:
    # AWB: IndexOf(..., StringComparison.CurrentCultureIgnoreCase)
    return comparator.casefold() in text.casefold()


@dataclass(frozen=True)
class CaseSensitiveArticleComparer:
    comparator: str

    def matches(self, article: PageLike) -> bool:
        return self.comparator in _text(article)


@dataclass(frozen=True)
class CaseInsensitiveArticleComparer:
    comparator: str

    def matches(self, article: PageLike) -> bool:
        return _contains_ignore_case(_text(article), self.comparator)


@dataclass(frozen=True)
class CaseSensitiveArticleComparerWithKeywords:
    comparator: str

    def matches(self, article: PageLike) -> bool:
        return tools.apply_key_words(article.name, self.comparator) in _text(article)


@dataclass(frozen=True)
class CaseInsensitiveArticleComparerWithKeywords:
    comparator: str

    def matches(self, article: PageLike) -> bool:
        return _contains_ignore_case(
            _text(article), tools.apply_key_words(article.name, self.comparator)
        )


@dataclass
class RegexArticleComparer:
    comparator: DotNetRegex
    timeout: float = DEFAULT_TIMEOUT
    timed_out: bool = field(default=False, init=False)

    def matches(self, article: PageLike) -> bool:
        self.timed_out = False
        try:
            return self.comparator.is_match(_text(article), timeout=self.timeout)
        except TimeoutError:
            self.timed_out = True
            return False


@dataclass
class DynamicRegexArticleComparer:
    """A regex containing %%keywords%%, built per page."""

    comparator: str
    options: DotNetOptions
    timeout: float = DEFAULT_TIMEOUT
    timed_out: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.options &= ~DotNetOptions.COMPILED
        # build a regex to try it out: raises if the pattern is invalid
        DotNetRegex(tools.apply_key_words("a", self.comparator), self.options)

    def matches(self, article: PageLike) -> bool:
        self.timed_out = False
        r = DotNetRegex(tools.apply_key_words(article.name, self.comparator), self.options)
        try:
            return r.is_match(_text(article), timeout=self.timeout)
        except TimeoutError:
            self.timed_out = True
            return False


def create_comparer(
    comparator: str,
    is_case_sensitive: bool,
    is_regex: bool,
    is_single_line: bool,
    is_multi_line: bool,
) -> ArticleComparer:
    """The comparer for these options (ArticleComparerFactory.Create). An invalid regex raises
    (regex.error or UnsupportedPatternError); the UI reports it."""
    if is_regex:
        opts = DotNetOptions.NONE
        if not is_case_sensitive:
            opts |= DotNetOptions.IGNORE_CASE
        if is_single_line:
            opts |= DotNetOptions.SINGLELINE
        if is_multi_line:
            opts |= DotNetOptions.MULTILINE
        if "%%" in comparator:
            return DynamicRegexArticleComparer(comparator, opts)
        return RegexArticleComparer(DotNetRegex(comparator, opts | DotNetOptions.COMPILED))

    # allow \n to match newline
    comparator = comparator.replace("\\n", "\n")
    if "%%" in comparator:
        if is_case_sensitive:
            return CaseSensitiveArticleComparerWithKeywords(comparator)
        return CaseInsensitiveArticleComparerWithKeywords(comparator)
    if is_case_sensitive:
        return CaseSensitiveArticleComparer(comparator)
    return CaseInsensitiveArticleComparer(comparator)
