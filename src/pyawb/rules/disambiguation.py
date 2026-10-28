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
# Ported from AutoWikiBrowser WikiFunctions/Disambiguation/DabForm.cs and DabControl.cs.
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Disambiguation (the Disambig tab): find the links to a disambiguation page, and for each one
build the replacement the user picks (no change, unlink, {{Disambiguation needed}}, or one of
the variants). The dialog in ui/ only shows these and collects the choices."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pyawb.core import rx
from pyawb.core.parsers.wikilinks import simplify_links, sticky_links
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.textutil import first_letter_case_insensitive, turn_first_to_upper

NO_CHANGE, UNLINK, DAB_NEEDED = 0, 1, 2  # the choice box's first three entries
FIRST_VARIANT = 3
DAB_NEEDED_TAG = "{{Disambiguation needed|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"

# end of a link, then {{Disambiguation needed}}, then punctuation (DnPunctuationR). AWB's pattern
# wanted the bare template, but the tag it inserts has |date={{subst:...}}, so it never moved the
# tag after the punctuation; this one allows the dated tag.
_DnPunctuation = DotNetRegex(
    r"(\]\])({{Disambiguation needed(?:\|(?:[^{}]|{{[^{}]*}})*)?}})([.,'\":;]+)"
)
_Unpipe = DotNetRegex(r"\[\[\s*([^\|\]]*)\s*\|\s*[^\]]*\s*\]\](.*)")
_Flip = DotNetRegex(r"\[\[(.*)\|(.*)\]\]")


def clean_variants(lines: Iterable[str]) -> list[str]:
    """The variants box: one target per line, blank lines dropped."""
    return [s.strip() for s in lines if s.strip()]


def variants_from_links(titles: Iterable[str]) -> list[str]:
    """Load links: the disambiguation page's links, without years (numbers below 2100)."""
    return [t for t in titles if not (t.isdecimal() and t.isascii() and int(t) < 2100)]


def link_regex(dab_link: str) -> DotNetRegex:
    """DabForm.Search: links to dab_link ("A|B" for several), first letter in either case,
    with an optional #section, a pipe and a link trail."""
    if "|" in dab_link:
        parts = [first_letter_case_insensitive(rx.escape(s.strip())) for s in dab_link.split("|")]
        parts = [p for p in parts if p]
        target = "(?:" + "|".join(parts) + ")" if len(parts) > 1 else "".join(parts)
    else:
        target = first_letter_case_insensitive(rx.escape(dab_link.strip()))
    return DotNetRegex(
        r"\[\[\s*("
        + target
        + r")\s*(?:|#[^\|\]]*)(|\|[^\]]*)\]\]([\p{Ll}\p{Lu}\p{Lt}\p{Pc}\p{Lm}]*)"
    )


def _is_separator(ch: str) -> bool:
    """char.IsSeparator: Unicode space, line or paragraph separators."""
    return unicodedata.category(ch) in ("Zs", "Zl", "Zp")


@dataclass(frozen=True)
class DabLink:
    """One link to disambiguate (DabControl_Load): where it is, its paragraph and context."""

    value: str  # the whole link, with its trail
    index: int
    real_link: str  # the target
    visible_link: str  # the text shown
    link_trail: str
    paragraph: str
    paragraph_start: int
    surroundings: str  # about context_chars either side, cut at spaces
    surroundings_start: int
    start_of_sentence: bool

    @classmethod
    def from_match(cls, text: str, m: DotNetMatch, context_chars: int) -> DabLink:
        pos_start = m.index
        while pos_start > 0:
            if text[pos_start] in "\n\r":
                pos_start += 1
                break
            pos_start -= 1
        pos_end = m.index + m.length
        if not m.group(2):
            visible = real = m.group(1).strip()
        else:
            visible = m.group(2).strip()
            real = m.group(1).strip()
        visible = visible.lstrip("|")
        # AWB stopped one character short, losing the last one at the end of the text
        while pos_end < len(text) and text[pos_end] not in "\n\r":
            pos_end += 1
        n = max(m.index - context_chars, pos_start)
        while n > pos_start:
            if _is_separator(text[n]):
                n += 1
                break
            n -= 1
        surroundings_start = n
        n = min(m.index + m.length + context_chars, pos_end)
        while n < pos_end and not _is_separator(text[n]):
            n += 1
        start_of_sentence = False
        n = m.index - 1
        while n > pos_start:
            if text[n] == ".":
                start_of_sentence = True
                break
            if not text[n].isspace():
                break
            n -= 1
        if n == pos_start:
            start_of_sentence = True
        return cls(
            value=m.value,
            index=m.index,
            real_link=real,
            visible_link=visible,
            link_trail=m.group(3),
            paragraph=text[pos_start:pos_end],
            paragraph_start=pos_start,
            surroundings=text[surroundings_start:n],
            surroundings_start=surroundings_start,
            start_of_sentence=start_of_sentence,
        )

    def choice(self, n: int, variants: Sequence[str]) -> str:
        """ComboBoxChanged: the replacement for choice n (0 no change, 1 unlink,
        2 {{Disambiguation needed}}, 3… the variants)."""
        if n == NO_CHANGE:
            return self.value
        if n == UNLINK:
            return self.visible_link + self.link_trail
        if n == DAB_NEEDED:
            return self.value + DAB_NEEDED_TAG
        variant = variants[n - FIRST_VARIANT]
        upper = self.start_of_sentence or (self.real_link[:1].isupper())
        link = "[[" + (turn_first_to_upper(variant) if upper else variant) + "|" + self.visible_link
        if self.real_link == self.visible_link:
            link += self.link_trail + "]]"
        else:
            link += "]]" + self.link_trail
        return simplify_links(link)


def find_links(text: str, dab_link: str, context_chars: int) -> list[DabLink]:
    regex = link_regex(dab_link)
    return [DabLink.from_match(text, m, context_chars) for m in regex.matches(text)]


def unpipe(link: str) -> str:
    """Unpipe: [[Target|text]]trail -> [[Target]]trail."""
    return _Unpipe.replace(link, "[[$1]]$2")


def flip(link: str) -> str:
    """Flip: [[A|B]] -> [[B|A]]."""
    return _Flip.replace(link, "[[$2|$1]]")


def apply(text: str, dab_link: str, results: Sequence[str | None]) -> tuple[str, bool]:
    """DabForm.Disambiguate after OK: each link replaced by its result (None: unchanged), by
    position, so a link found twice on a line gets its own choice; {{Disambiguation needed}}
    moved after punctuation; sticky links. Returns (text, changed)."""
    regex = link_regex(dab_link)
    count = 0
    dn = False

    def replace(m: DotNetMatch) -> str:
        nonlocal count, dn
        res = results[count] if count < len(results) else None
        count += 1
        if res is None:
            return m.value
        if "{{Disambiguation needed" in res:
            dn = True
        return res

    new = regex.replace(text, replace)
    if new == text:
        return text, False
    if dn:
        new = _DnPunctuation.replace(new, "$1$3$2")
    return sticky_links(new), True
