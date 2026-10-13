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
#
# Ported from AutoWikiBrowser WikiFunctions/Parse/FindandReplace.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Find and replace rules (the engine half of AWB's FindandReplace form).

Rules use .NET regex syntax and .NET replacement strings, as in AWB settings files. Each rule
runs with a timeout; a rule that times out leaves the text unchanged and is listed in
FindAndReplace.timed_out (AWB allowed 60 seconds and then failed the page).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from awb_x.core import rx, tools
from awb_x.core.dotnet_regex import translate_replacement
from awb_x.core.parsers.hidetext import HideText
from awb_x.core.rx import DotNetMatch, DotNetOptions, DotNetRegex
from awb_x.core.site import current_site

DEFAULT_TIMEOUT = 10.0
"""Seconds one find and replace rule may run against one page."""

_NewlineRegex = rx.DotNetRegex(r"(?<!\\)\\n", DotNetOptions.COMPILED)
_TabulationRegex = rx.DotNetRegex(r"(?<!\\)\\t", DotNetOptions.COMPILED)


def arrow() -> str:
    """FindandReplace.Arrow: " → ", or " ← " on right-to-left wikis."""
    return " ← " if current_site().rtl else " → "


def _comma() -> str:
    return "، " if current_site().lang_code in ("ar", "arz", "fa") else ", "


@dataclass
class Replacement:
    """One find and replace rule (AWB's Replacement). find is a .NET regex (already escaped for
    plain-text rules: see from_row); replace is a .NET replacement string."""

    find: str = ""
    replace: str = ""
    is_regex: bool = False
    enabled: bool = True
    minor: bool = False
    before_or_after: bool = False  # False: run before general fixes; True: after
    options: DotNetOptions = DotNetOptions.NONE
    comment: str = ""

    @classmethod
    def from_row(
        cls,
        find: str,
        replace: str = "",
        *,
        case_sensitive: bool = True,
        is_regex: bool = False,
        multiline: bool = False,
        singleline: bool = False,
        minor: bool = False,
        before_or_after: bool = False,
        enabled: bool = True,
        comment: str = "",
    ) -> Replacement:
        """A rule as typed in the find and replace table (AWB's RowToReplacement): "\\r\\n" stands
        for a line break; plain-text finds are escaped, keeping "\\n" as a newline."""
        f, r = _encode(find), _encode(replace)
        if not is_regex:
            newlines = "\\n" in f
            f = rx.escape(f)
            if newlines:
                f = f.replace("\\\\n", "\n")
        options = DotNetOptions.NONE
        if not case_sensitive:
            options |= DotNetOptions.IGNORE_CASE
        if multiline:
            options |= DotNetOptions.MULTILINE
        if singleline:
            options |= DotNetOptions.SINGLELINE
        return cls(f, r, is_regex, enabled, minor, before_or_after, options, comment)


def _encode(text: str) -> str:
    """Typed "\\r\\n" text to a real CRLF line break."""
    return text.replace("\\r\\n", "\r\n")


def _prepare_replace_part(replace: str) -> str:
    replace = _NewlineRegex.replace(replace, "\n")
    return _TabulationRegex.replace(replace, "\t")


# Localised summary prefixes: (replaced, removed)
_SUMMARY_WORDS: dict[str, tuple[str, str]] = {
    "ar": ("استبدل: ", "أزال: "),
    "arz": ("غير: ", "شال: "),
    "be": ("перанесена: ", "выдалена: "),
    "el": ("αντικατέστησε: ", "αφαίρεσε: "),
    "eo": ("anstataŭigis: ", "forigis: "),
    "fa": ("جایگزین شد: ", "حذف شده: "),
    "fr": ("remplacement: ", "retrait: "),
    "hy": ("փոխարինվեց: ", "ջնջվեց: "),
    "sq": ("zëvendësova: ", "hoqa: "),
    "tr": ("değiştirildi: ", "çıkartıldı:"),
}


@dataclass
class FindAndReplace:
    """A list of find and replace rules with AWB's options."""

    replacements: list[Replacement] = field(default_factory=list[Replacement])
    ignore_links: bool = False  # hide links, images, templates etc. (HideText.hide)
    ignore_more: bool = False  # also hide headings, link targets, templates, refs (hide_more)
    add_to_summary: bool = True
    timeout: float = DEFAULT_TIMEOUT
    replaced_summary: str = ""
    removed_summary: str = ""
    timed_out: list[Replacement] = field(default_factory=list[Replacement])

    def add_new(self, r: Replacement | Iterable[Replacement]) -> None:
        """Add one rule or several (AWB's AddNew overloads)."""
        if isinstance(r, Replacement):
            self.replacements.append(r)
        else:
            self.replacements.extend(r)

    def get_list(self) -> list[Replacement]:
        return self.replacements

    def clear(self) -> None:
        self.replacements.clear()

    @property
    def has_replacements(self) -> bool:
        return bool(self.replacements)

    def has_processing_replacements(self, after: bool) -> bool:
        """Whether any enabled rule runs at this point (before or after general fixes)."""
        return any(r.enabled and r.before_or_after == after for r in self.replacements)

    @property
    def has_after_processing_replacements(self) -> bool:
        return self.has_processing_replacements(True)

    def multiple_find_and_replace(
        self, article_text: str, title: str, before_or_after: bool, edit_summary: str = ""
    ) -> tuple[str, str, bool]:
        """Apply the enabled rules for this point. AWB's ref editSummary and out
        majorChangesMade: returns (text, edit summary, whether a non-minor rule changed it)."""
        major_changes_made = False
        if not self.has_replacements:
            return article_text, edit_summary, major_changes_made

        self.replaced_summary = ""
        self.removed_summary = ""
        self.timed_out = []
        remove = HideText(True, False, True)

        if self.ignore_more:
            article_text = remove.hide_more(article_text)
        elif self.ignore_links:
            article_text = remove.hide(article_text)

        for rep in self.replacements:
            if not rep.enabled or rep.before_or_after != before_or_after:
                continue
            article_text, change_made = self.perform_find_and_replace(rep, article_text, title)
            if change_made and not rep.minor:
                major_changes_made = True

        if self.ignore_more:
            # AWB FIXME: a rule replacing digits or "M" inside ⌊⌊⌊⌊M2⌋⌋⌋⌋ markers corrupts them
            article_text = remove.add_back_more(article_text)
        elif self.ignore_links:
            article_text = remove.add_back(article_text)

        if self.add_to_summary:
            lang = current_site().lang_code
            replaced_word, removed_word = _SUMMARY_WORDS.get(lang, ("replaced: ", "removed: "))
            if self.replaced_summary:
                if lang in _SUMMARY_WORDS:
                    edit_summary = replaced_word + self.replaced_summary.strip()
                else:  # AWB appends here but replaces for the localised wikis
                    edit_summary += replaced_word + self.replaced_summary.strip()

            if self.removed_summary:
                if edit_summary:
                    edit_summary += _comma()
                edit_summary += removed_word + self.removed_summary.strip()

        return article_text, edit_summary, major_changes_made

    def perform_find_and_replace(
        self, rep: Replacement, article_text: str, article_title: str
    ) -> tuple[str, bool]:
        """Run one rule (after expanding %%keywords%%). The summary records the first match whose
        replacement changes the text, and the count of such changes. AWB's out changeMade:
        returns (text, change made)."""
        find_this = tools.apply_key_words(article_title, rep.find, True)
        replace_with = tools.apply_key_words(article_title, _prepare_replace_part(rep.replace))
        comma = _comma()

        find_regex = DotNetRegex(find_this, rep.options)
        expand = translate_replacement(replace_with, find_regex.translated)
        rep_count = rem_count = 0
        replaced: list[str] = []
        removed: list[str] = []

        def evaluator(m: DotNetMatch) -> str:
            nonlocal rep_count, rem_count
            assert m.m is not None
            mres = expand(m.m)
            if m.value != mres:
                if mres:
                    if rep_count == 0:
                        replaced.append(m.value + arrow() + mres)
                    rep_count += 1
                else:
                    if rem_count == 0:
                        removed.append(m.value)
                    rem_count += 1
            return mres

        try:
            res = find_regex.replace(article_text, evaluator, timeout=self.timeout)
        except TimeoutError:
            self.timed_out.append(rep)
            return article_text, False

        if replaced:
            if self.replaced_summary:  # add comma before next replaced
                self.replaced_summary += comma
            self.replaced_summary += replaced[0]
        if removed:
            if self.removed_summary:  # add comma before next removed
                self.removed_summary += comma
            self.removed_summary += removed[0]

        # update summaries with count of changes
        if rep_count > 1:
            self.replaced_summary += f" ({rep_count})"
        if rem_count > 1:
            self.removed_summary += f" ({rem_count})"

        return res, rep_count + rem_count > 0
