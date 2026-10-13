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
"""RegExTypoFix: typo lists and typo fixing (port of WikiFunctions/Parse/RegExTypoFix.cs).

The list format is one `<Typo word="..." find="..." replace="..." />` per rule, with
.NET-syntax find/replace strings. Fetching the list page is the job of awb_x.api.

Each typo rule runs with a timeout; one that times out is skipped for that page and listed in
RegExTypoFix.timed_out.
"""

# Ported from AutoWikiBrowser WikiFunctions/Parse/RegExTypoFix.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import cast

from awb_x.core import rx
from awb_x.core.dotnet_regex import Replacement, translate_replacement
from awb_x.core.parsers.hidetext import HideText
from awb_x.core.rx import DotNetRegex
from awb_x.core.site import current_site
from awb_x.rules.findreplace import arrow

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


def create_rule(find: str, replace: str, name: str = "<enter a name>") -> str:
    """A rule in the list format (RegExTypoFix.CreateRule)."""
    return '<Typo word="' + name + '" find="' + find + '" replace="' + replace + '" />'


DEFAULT_TIMEOUT = rx.DEFAULT_TIMEOUT
"""Seconds one typo rule may run against one page."""

LINK_CHECK_TIMEOUT = 10.0
"""Seconds for the check that a typo is not inside a wikilink target (AWB allowed 60)."""


@dataclass
class TypoStat:
    """Statistics for one typo rule on the last page."""

    find: str
    replace: str
    total: int = 0
    self_matches: int = 0
    false_positives: int = 0

    def __str__(self) -> str:
        return self.find + " → " + self.replace


class TypoRuleError(ValueError):
    """A typo rule does not compile (AWB's TypoException); no typos are loaded."""


@dataclass(frozen=True)
class _Typo:
    regex: DotNetRegex
    replace: str
    expand: Replacement


class _TypoGroup:
    """Similar typos, tried together with one combined regex before the individual rules."""

    def __init__(
        self, group_size: int, match: str | None, dont_match: str | None, prefix: str, postfix: str
    ) -> None:
        self.group_size = group_size
        self._allow = DotNetRegex(match) if match else None
        self._disallow = DotNetRegex(dont_match) if dont_match else None
        self._prefix, self._postfix = prefix, postfix
        self._groups: list[DotNetRegex] | None = None
        self.typos: list[_Typo] = []
        self.statistics: list[TypoStat] = []
        self.timed_out: list[str] = []

    def is_suitable_typo(self, typo: str) -> bool:
        """Whether the typo pattern belongs here: matches allow (if set) and not disallow."""
        if self._allow is not None and not self._allow.is_match(typo):
            return False
        return not (self._disallow is not None and self._disallow.is_match(typo))

    def add(self, typo: str, replacement: str) -> None:
        if not self.is_suitable_typo(typo):
            raise ValueError(f'Typo "{typo}" is not suitable for this group.')
        try:
            r = DotNetRegex(typo)
            expand = translate_replacement(replacement, r.translated)
        except Exception as ex:  # regex.error or UnsupportedPatternError
            raise TypoRuleError(f"Error in typo '{typo}': {ex}") from ex
        self.typos.append(_Typo(r, replacement, expand))

    def make_groups(self) -> None:
        """Combined regexes for each batch of group_size typos."""
        if self.group_size <= 1:
            return
        self._groups = []
        n_typos = len(self.typos)
        for n in range((n_typos - 1) // self.group_size + 1):
            parts: list[str] = []
            for i in range(min(self.group_size, n_typos - n * self.group_size)):
                typo = self.typos[n * self.group_size + i].regex.pattern
                if self._allow is not None:
                    typo = self._allow.match(typo).group(1)
                parts.append(typo)
            if parts:
                self._groups.append(
                    DotNetRegex(self._prefix + "(" + "|".join(parts) + ")" + self._postfix)
                )

    def _fix_typo(
        self, article_text: str, summary: str, typo: _Typo, article_title: str
    ) -> tuple[str, str]:
        """Apply one typo rule unless it matches the title. The summary gets the first match that
        changes and the number of changes."""
        try:
            # don't apply the typo if it matches on the article's title
            if typo.regex.is_match(article_title, timeout=DEFAULT_TIMEOUT):
                return article_text, summary
            matches = typo.regex.matches(article_text, timeout=DEFAULT_TIMEOUT)
            if not matches:
                return article_text, summary
            new_text = typo.regex.replace(article_text, typo.replace, timeout=DEFAULT_TIMEOUT)
        except TimeoutError:
            self.timed_out.append(typo.regex.pattern)
            return article_text, summary

        comma = "، " if current_site().lang_code in ("ar", "arz", "fa") else ", "
        stats = TypoStat(typo.regex.pattern, typo.replace, total=len(matches))
        count = 0
        for m in matches:
            assert m.m is not None
            res = typo.expand(m.m)
            if res != m.value:
                count += 1
                if count == 1:
                    summary += (comma if summary else "") + m.value + arrow() + res
        if count > 1:
            summary += f" ({count})"
        stats.self_matches = stats.total - count
        self.statistics.append(stats)
        return new_text, summary

    def fix_typos(
        self, article_text: str, summary: str, article_title: str, original_article_text: str
    ) -> tuple[str, str]:
        """Apply the group's typos; returns (text, summary)."""
        self.statistics.clear()
        if self._groups is None:
            for typo in self.typos:
                article_text, summary = self._fix_typo(article_text, summary, typo, article_title)
            return article_text, summary

        for i, group in enumerate(self._groups):
            try:
                hit = group.is_match(article_text, timeout=DEFAULT_TIMEOUT)
            except TimeoutError:
                hit = True  # can't tell: try the rules one by one
            if not hit:
                continue
            for j in range(min(self.group_size, len(self.typos) - i * self.group_size)):
                typo = self.typos[i * self.group_size + j]
                # don't apply the typo if it matches on a link target in a wikilink (but not
                # image/interwiki/category link)
                in_link = DotNetRegex(
                    r"\[\[[^[\]\n\|]*?"
                    + typo.regex.pattern
                    + r"[^\[\]\r\n\|]*?(?<!\[\[[A-Z]?[a-z-]{2,}:[^[\]\n]+)(?:\]\]|\|)"
                )
                try:
                    if in_link.is_match(original_article_text, timeout=LINK_CHECK_TIMEOUT):
                        continue
                except TimeoutError:
                    self.timed_out.append(typo.regex.pattern)
                    continue
                article_text, summary = self._fix_typo(article_text, summary, typo, article_title)
        return article_text, summary


_IgnoreRegex = DotNetRegex(
    r"\(sic\)|\[sic\]|\[''sic''\]|\{\{sic\}\}|spellfixno", rx.DotNetOptions.COMPILED
)
_RemoveTail = DotNetRegex(r"(\s|\n|\r|\*|#|:|⌊⌊⌊⌊M?\d*⌋⌋⌋⌋)+$", rx.DotNetOptions.COMPILED)


class RegExTypoFix:
    """Typo fixing with a list of rules (find -> replace, in list order).

    A rule that does not compile makes the whole list unusable, as in AWB (which refuses
    malformed lists so that they get fixed): typos_loaded is then False and error says why.
    """

    def __init__(self, typos: Mapping[str, str] | Iterable[TypoEntry]) -> None:
        rules: list[tuple[str, str]]
        if isinstance(typos, Mapping):
            rules = list(cast("Mapping[str, str]", typos).items())
        else:
            rules = [(e.find, e.replace) for e in typos]
        self.error: str | None = None
        self._groups = self._make_groups()
        self.typo_count = 0
        try:
            for find, replace in rules:
                for grp in self._groups:
                    if grp.is_suitable_typo(find):
                        grp.add(find, replace)
                        self.typo_count += 1
                        break
            for grp in self._groups:
                grp.make_groups()
        except TypoRuleError as ex:
            self.error = str(ex)
            self._groups = []
            self.typo_count = 0
        self.typos_loaded = self.typo_count > 0

    @staticmethod
    def _make_groups() -> list[_TypoGroup]:
        return [
            _TypoGroup(20, r"^\\b(\(\[[A-M].*)\\b$", r"[^\\]\\\d", r"\b", r"\b"),
            _TypoGroup(19, r"^\\b(\(\[[N-Z].*)\\b$", r"[^\\]\\\d", r"\b", r"\b"),
            _TypoGroup(18, r"^\\b((\(|\[)?[A-Za-z].*)", r"[^\\]\\\d", r"\b", ""),
            _TypoGroup(5, None, r"[^\\]\\\d", "", ""),
            _TypoGroup(1, None, None, "", ""),
        ]

    @property
    def timed_out(self) -> list[str]:
        """Typo patterns that timed out on the last page."""
        return [t for g in self._groups for t in g.timed_out]

    def _prepare(self, article_text: str) -> tuple[HideText, str, str]:
        remove_text = HideText(True, False, True)
        article_text = remove_text.hide_more(article_text, True)
        # remove newlines, whitespace and hide tokens from the bottom to avoid running 2K regexes
        # on them
        m = _RemoveTail.match(article_text)
        tail = m.value
        if tail:
            article_text = article_text[: m.index]
        return remove_text, article_text, tail

    def perform_typo_fixes(self, article_text: str, article_title: str) -> tuple[str, bool, str]:
        """Fix typos, not if no typos are loaded or the page has a {{sic}}-style marker. AWB's out
        noChange and out summary: returns (text, no_change, summary)."""
        original_article_text = article_text
        if self.typo_count == 0 or _IgnoreRegex.is_match(article_text):
            return article_text, True, ""
        for g in self._groups:
            g.timed_out.clear()

        remove_text, article_text, tail = self._prepare(article_text)
        original_text = article_text
        str_summary = ""

        # AWB runs each group on its own thread against the same text, then merges: the first
        # group with changes is taken as is, later ones are re-run on the updated text.
        results = [
            g.fix_typos(article_text, str_summary, article_title, original_article_text)
            for g in self._groups
        ]
        for g, (group_text, group_summary) in zip(self._groups, results, strict=True):
            if group_summary:
                if str_summary:
                    # earlier group had changes, so need to re-run this one
                    article_text, str_summary = g.fix_typos(
                        article_text, str_summary, article_title, original_article_text
                    )
                else:
                    str_summary = group_summary
                    article_text = group_text

        no_change = original_text == article_text
        summary = current_site().typo_summary_tag + str_summary.strip()
        return remove_text.add_back_more(article_text + tail), no_change, summary

    def detect_typo(self, article_text: str, article_title: str) -> bool:
        """Whether the page has any known typo."""
        original_article_text = article_text
        if self.typo_count == 0 or _IgnoreRegex.is_match(article_text):
            return False
        _, article_text, _ = self._prepare(article_text)
        str_summary = ""
        for grp in self._groups:
            article_text, str_summary = grp.fix_typos(
                article_text, str_summary, article_title, original_article_text
            )
            if str_summary:
                return True
        return False

    def get_statistics(self) -> list[TypoStat]:
        """Statistics of typos fixed on the last page."""
        return [s for g in self._groups for s in g.statistics]

    def get_typos(self) -> list[tuple[str, str]]:
        """(find, replace) of every loaded rule, grouped as they are applied."""
        return [(t.regex.pattern, t.replace) for g in self._groups for t in g.typos]
