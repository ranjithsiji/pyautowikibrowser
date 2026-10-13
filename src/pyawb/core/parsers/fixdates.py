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
# Ported from AutoWikiBrowser WikiFunctions/Parse/FixDates.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Date fixes (port of Parse/FixDates.cs): ordinals and "of" in dates, leading zeros, commas,
date and year ranges with en dashes. English Wikipedia only, as in AWB; the regexes use English
month names (AWB builds them from WikiRegexes.Months at static initialisation)."""

# ruff: noqa: E501

from __future__ import annotations

from pyawb.core import rx
from pyawb.core import wikiregexes as W
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import SiteConfig, current_site

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

_EN = W.for_site(SiteConfig.english())
_Months = _EN.Months
_MonthsNoGroup = _EN.MonthsNoGroup

# don't match 'in the June of 2007', 'on the 11th May 2008' etc.: they won't read well if changed
_OfBetweenMonthAndYear = _R(
    r"\b"
    + _Months
    + r" +of +(20\d\d|1[89]\d\d)\b(?<!\b[Tt]he {1,5}\w{3,15} {1,5}of {1,5}(20\d\d|1[89]\d\d))"
)
OrdinalsInDatesAm = _R(
    r"(?<!\b[1-3]\d +)\b"
    + _Months
    + r" +([0-3]?\d)(?:st|nd|rd|th)\b(?<!\b[Tt]he +\w{3,10} +(?:[0-3]?\d)(?:st|nd|rd|th)\b)(?:( *(?:to|and|.|&.dash;) *[0-3]?\d)(?:st|nd|rd|th)\b)?"
)
_OrdinalsInDatesAmRange = _R(
    r"(?<!\b[1-3]\d +)\b"
    + _Months
    + r" +([0-3]?\d)(?:st|nd|rd|th)\b(?<!\b[Tt]he +\w{3,10} +(?:[0-3]?\d)(?:st|nd|rd|th)\b)(?:( *(?:to|and|.|&.dash;) *[0-3]?\d)(?:st|nd|rd|th)\b)*"
)
OrdinalsInDatesInt = _R(
    r"(?:\b([0-3]?\d)(?:st|nd|rd|th)( *(?:to|and|.|&.dash;) *))?\b([0-3]?\d)(?:st|nd|rd|th) +"
    + _Months
    + r"\b(?<!\b[Tt]he +(?:[0-3]?\d)(?:st|nd|rd|th) +\w{3,10})"
)
_DateLeadingZerosAm = _R(r"(?<!\b[0-3]?\d *)\b" + _Months + r" +0([1-9])" + r"\b")
_DateLeadingZerosInt = _R(r"\b" + r"0([1-9]) +" + _Months + r"\b")
_MonthsRegex = _R(r"\b" + _MonthsNoGroup + r"\b.{0,30}")
_MonthsRegexNoSecondBreak = _R(r"\b" + _MonthsNoGroup + r".{0,30}")
_DayOfMonth = _R(r"(?<![Tt]he +)\b([1-9]|[12][0-9]|3[01])(?:st|nd|rd|th) +of +" + _Months)
Ordinal = _R(r"[0-9](?:st|nd|rd|th)")
_MonthsAct = _R(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) Act\b"
)
# ordinal number inside <sup> tags
SupOrdinal = _R(r"([0-9])<sup> ?(st|nd|rd|th) ?</sup>", O.IGNORE_CASE)
_FixDateOrdinalsAndOfQuick = _R(
    r"[0-9](?:<sup> *)?(st|nd|rd|th)|\b0[1-9]\b| of +([0-9]|[A-Z])", O.IGNORE_CASE
)
_OrdinalQuick = _R(r"[0-9](?:<sup> *)?(st|nd|rd|th)", O.IGNORE_CASE)
_OrdinalSuffix = _R(r"\b([1-3]?[0-9])(?:st|nd|rd|th)\b")

# extra comma or space in American format dates
IncorrectCommaAmericanDates = _R(_Months + r"[ ,]*([1-3]?\d(?:–[1-3]?\d)?)[ ,]+([12]\d{3})\b")
# comma between month and year in international format dates
IncorrectCommaInternationalDates = _R(
    r"\b((?:[1-3]?\d) +" + _MonthsNoGroup + r") *, *(1\d{3}|20\d{2})\b"
)

# date ranges use an en dash per [[WP:MOSDATE]]
_SameMonthInternationalDateRange = _R(r"( [1-3]?\d) *- *([1-3]?\d +" + _MonthsNoGroup + r")\b")
_SameMonthAmericanDateRange = _R(r"(" + _MonthsNoGroup + r" *)([0-3]?\d) *- *([0-3]?\d)\b(?!\-)")
# 13 July -28 July 2009 -> 13–28 July 2009; July 13 - July 28 2009 -> July 13–28, 2009
_LongFormatInternationalDateRange = _R(
    r"\b([1-3]?\d) +" + _Months + r" *(?:-|–|&nbsp;) *([1-3]?\d) +\2,? *([12]\d{3})\b"
)
_LongFormatAmericanDateRange = _R(
    _Months + r" +([1-3]?\d) +" + r" *(?:-|–|&nbsp;) *\1 +([1-3]?\d) *,? *([12]\d{3})\b"
)
_EnMonthRange = _R(r"\b" + _Months + r"-" + _Months + r"\b")

_FullYearRange = _R(
    r"((?:[\(,=;\|]|\b(?:from|between|and|reigned|f?or|ca?\.?\]*|circa)) *)([12]\d{3}) *- *([12]\d{3})(?= *(?:\)|[,;\|]|and\b|\s*$))",
    O.MULTILINE,
)
_SpacedFullYearRange = _R(r"(?<!\b(?:ca?\.?\]*|circa) *)([12]\d{3})(?: +– *| *– +)([12]\d{3})")
_YearRangeShortenedCentury = _R(
    r"((?:[\(,=;]|\b(?:from|between|and|reigned|the)) *)([12]\d{3}) *- *(\d{2})(?= *(?:\)|[,;]|and\b|\s*$))",
    O.MULTILINE,
)
_DateRangeToPresent = _R(
    r"\b(" + _MonthsNoGroup + r"| [0-3]?\d,?) +" + r"([12]\d{3}) *- *([Pp]resent\b)"
)
# 11 May 2010–2012 (unspaced en dash in a month–year range, should be spaced)
_DateRangeToYear = _R(
    r"\b("
    + _MonthsNoGroup
    + r"|\b"
    + _MonthsNoGroup
    + r"(?:&nbsp;|\s+)[0-3]?\d,?) +"
    + r"([12]\d{3})[-–]([12]\d{3})\b"
)
_YearRangeToPresent = _R(r"\b([12]\d{3}) *- *([Pp]resent\b)")

_YearDash = _R(r"[12]\d{3}[–-]")
_InternationalDateFullUnspacedRange = _R(_EN.InternationalDates + r"[–-]" + _EN.InternationalDates)
_AmericanDateFullUnspacedRange = _R(_EN.AmericanDates + r"[–-]" + _EN.AmericanDates)
_YearRange = _R(r"\b[12][0-9]{3}.{0,25}")
_SpacedHyphen = _R(r" *- *")


def _before(text: str, m: DotNetMatch) -> str:
    """The match plus up to 25 characters before it."""
    back = min(25, m.index)
    return text[m.index - back : m.index + m.length]


class FixDatesMixin:
    """Instance methods of Parsers from FixDates.cs."""

    def hide_text_images(self, article_text: str) -> str:  # provided by Parsers
        raise NotImplementedError

    def add_back_text_images(self, article_text: str) -> str:  # provided by Parsers
        raise NotImplementedError

    def fix_date_ordinals_and_of(self, article_text: str, article_title: str) -> str:
        """Remove ordinals and "of" from dates (June 11th -> June 11, 5 of May -> 5 May),
        leading zeros, and stray commas (en only)."""
        if current_site().lang_code != "en":
            return article_text
        months_in_title = _MonthsRegex.is_match(article_title)
        while True:
            reparse = False
            # performance: apply the regexes to each date found, filtered to those that could
            # change, rather than to the whole text
            candidates = [
                m
                for m in _MonthsRegex.matches(article_text)
                if _FixDateOrdinalsAndOfQuick.is_match(_before(article_text, m))
            ]
            for m in candidates:
                before = _before(article_text, m)
                if _MonthsAct.is_match(before):
                    continue
                after = self._fix_date_ordinals_and_of_local(before, months_in_title)
                # the start must not change: taking exactly 25 characters may have split a year
                if after != before and after[:1] == before[:1]:
                    reparse = True
                    article_text = article_text.replace(before, after)
                    # catch after other fixes
                    article_text = IncorrectCommaAmericanDates.replace(article_text, "$1 $2, $3")
                    article_text = IncorrectCommaInternationalDates.replace(article_text, "$1 $2")
                    break
            if not reparse:
                return article_text

    def _fix_date_ordinals_and_of_local(self, text: str, months_in_title: bool) -> str:
        text = _OfBetweenMonthAndYear.replace(text, "$1 $2")
        # not if the title has a month in it (e.g. [[6th of October City]]); ordinals check for
        # performance
        if not months_in_title and _OrdinalQuick.is_match(text):
            # no sup tags on ordinals [[WP:ORDINAL]] - CHECKWIKI error 101
            text = SupOrdinal.replace(text, "$1$2")
            text = _OrdinalsInDatesAmRange.replace(
                text, lambda m: _OrdinalSuffix.replace(m.value, "$1")
            )
            text = OrdinalsInDatesInt.replace(text, "$1$2$3 $4")
            text = _DayOfMonth.replace(text, "$1 $2")
        text = _DateLeadingZerosAm.replace(text, "$1 $2")
        return _DateLeadingZerosInt.replace(text, "$1 $2")

    def fix_dates_a(self, article_text: str) -> str:
        """Date range and comma fixes (en only), not inside images or external links."""
        if current_site().lang_code != "en":
            return article_text
        # performance: most articles need no change and hiding is slow on long ones, so first
        # check each date found in the raw text
        if not any(
            self.fix_dates_a_internal(_before(article_text, m)) != _before(article_text, m)
            for m in _MonthsRegexNoSecondBreak.matches(article_text)
        ):
            return article_text
        article_text = self.hide_text_images(article_text)
        article_text = self.fix_dates_a_internal(article_text)
        return self.add_back_text_images(article_text)

    def fix_dates_a_internal(self, text: str) -> str:
        original = text
        has_dash = "-" in text or "–" in text
        if "," in text:
            text = IncorrectCommaInternationalDates.replace(text, "$1 $2")
        if has_dash:
            text = _SameMonthInternationalDateRange.replace(text, "$1–$2")
            text = _SameMonthAmericanDateRange.replace(text, _same_month_american_date_range_me)
            text = _LongFormatInternationalDateRange.replace(text, "$1–$3 $2 $4")
            text = _LongFormatAmericanDateRange.replace(text, "$1 $2–$3, $4")
        # after the date range fixes
        text = IncorrectCommaAmericanDates.replace(text, "$1 $2, $3")
        # month range
        if has_dash:
            text = _EnMonthRange.replace(text, "$1–$2")
        # no changes to link targets, e.g. [[July 29 1966, P.N.E. Garden Aud., Vancouver Canada]]
        if original != text and "[[" in original:
            targets_before = [m.group(1) for m in W.WikiLinksOnlyPossiblePipe.matches(text)]
            targets_after = [m.group(1) for m in W.WikiLinksOnlyPossiblePipe.matches(original)]
            if targets_before != targets_after:
                return original
        return text

    def fix_dates_b(self, article_text: str, circa_link: bool, floruit: bool) -> str:
        """Year and date range fixes (en only); optionally link the first unlinked floruit."""
        if current_site().lang_code != "en":
            return article_text
        while True:
            # performance: apply the regexes to each year found, not the whole text
            reparse = False
            for m in _YearRange.matches(article_text):
                before = _before(article_text, m)
                after = self._fix_dates_b_internal(before, circa_link)
                if after != before:
                    reparse = True
                    article_text = article_text.replace(before, after)
                    break
            if not reparse:
                break
        # link the first unlinked floruit, zeroth section only
        if floruit:
            article_text = W.UnlinkedFloruit.replace(article_text, "([[floruit|fl.]] $1", 1)
        return article_text

    def _fix_dates_b_internal(self, text: str, circa_link: bool) -> str:
        text = _DateRangeToPresent.replace(text, "$1 $2 – $3")
        text = _YearRangeToPresent.replace(text, "$1–$2")
        # 1965–1968: only if the two years are in order
        if not circa_link:
            text = _FullYearRange.replace(text, _full_year_range_me)
            text = _SpacedFullYearRange.replace(text, _spaced_full_year_range_me)
        # 1965–68
        text = _YearRangeShortenedCentury.replace(text, _year_range_shortened_century_me)
        # date–year -> date – year
        text = _DateRangeToYear.replace(text, "$1 $2 – $3")
        # date–date -> date – date
        if _YearDash.is_match(text):
            text = _InternationalDateFullUnspacedRange.replace(
                text, lambda m: m.value.replace("-", "–").replace("–", " – ")
            )
            text = _AmericanDateFullUnspacedRange.replace(
                text, lambda m: m.value.replace("-", "–").replace("–", " – ")
            )
        return text


def _full_year_range_me(m: DotNetMatch) -> str:
    year1, year2 = int(m.group(2)), int(m.group(3))
    if year2 > year1 and year2 - year1 <= 300:
        return m.group(1) + m.group(2) + (" – " if "c" in m.group(1).lower() else "–") + m.group(3)
    return m.value


def _spaced_full_year_range_me(m: DotNetMatch) -> str:
    year1, year2 = int(m.group(1)), int(m.group(2))
    if year2 > year1 and year2 - year1 <= 300:
        return m.group(1) + "–" + m.group(2)
    return m.value


def _year_range_shortened_century_me(m: DotNetMatch) -> str:
    year1 = int(m.group(2))  # 1965
    year2 = int(m.group(2)[:2] + m.group(3))  # 68 -> 1968
    if year2 > year1 and year2 - year1 <= 99:
        return m.group(1) + m.group(2) + "–" + m.group(3)
    return m.value


def _same_month_american_date_range_me(m: DotNetMatch) -> str:
    if int(m.group(3)) > int(m.group(2)):
        return _SpacedHyphen.replace(m.value, "–")
    return m.value
