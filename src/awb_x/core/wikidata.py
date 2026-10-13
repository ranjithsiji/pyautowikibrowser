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
"""Wikidata as plain data, and fixes that use it. Not in AWB.

awb_x.api.wikidata fetches items and builds WikidataItem; the functions here only take them as
inputs, so they run offline:

- local interwiki links Wikidata already has (sitelinks) can be removed; links that disagree with
  Wikidata are reported, never changed;
- birth and death dates (P569, P570), "instance of human" (P31 = Q5), short description,
  coordinates (P625) and authority control identifiers are exposed for the category, person and
  DEFAULTSORT fixes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from awb_x.core import tools
from awb_x.core import wikiregexes as W
from awb_x.core.parsers import templates as _templates
from awb_x.core.rx import DotNetMatch
from awb_x.core.site import SiteConfig, current_site
from awb_x.core.textutil import turn_first_to_upper

HUMAN = "Q5"
GREGORIAN = "http://www.wikidata.org/entity/Q1985727"
JULIAN = "http://www.wikidata.org/entity/Q1985786"

AUTHORITY_CONTROL: Mapping[str, str] = {
    "P213": "ISNI",
    "P214": "VIAF",
    "P227": "GND",
    "P244": "LCCN",
    "P268": "BnF",
    "P269": "IdRef",
    "P349": "NDL",
    "P496": "ORCID",
    "P646": "Freebase",
    "P906": "SELIBR",
    "P950": "BNE",
    "P1006": "NTA",
    "P1015": "NORAF",
    "P7859": "WorldCat Identities",
}
"""Common authority control properties (as in {{Authority control}})."""


@dataclass(frozen=True)
class WikidataTime:
    """A time value: precision 9 = year, 10 = month, 11 = day (Wikidata's precision codes)."""

    year: int
    month: int = 0
    day: int = 0
    precision: int = 11
    calendar: str = GREGORIAN

    @classmethod
    def parse(cls, time: str, precision: int = 11, calendar: str = GREGORIAN) -> WikidataTime:
        """From "+1952-03-11T00:00:00Z" (signed year; month and day 00 when unknown)."""
        sign = -1 if time.startswith("-") else 1
        date = time.lstrip("+-").split("T", 1)[0]
        y, m, d = [*date.split("-"), "0", "0"][:3]
        month = int(m) if precision >= 10 else 0
        day = int(d) if precision >= 11 else 0
        return cls(sign * int(y), month, day, precision, calendar)

    @property
    def is_julian(self) -> bool:
        return self.calendar == JULIAN


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float
    precision: float | None = None
    globe: str = "http://www.wikidata.org/entity/Q2"  # Earth


@dataclass(frozen=True)
class WikidataItem:
    """What AWB-X uses from one Wikidata item. Statement values are the best-ranked ones
    (preferred, else normal; never deprecated)."""

    id: str
    sitelinks: Mapping[str, str] = field(default_factory=dict[str, str])  # dbname -> title
    labels: Mapping[str, str] = field(default_factory=dict[str, str])
    descriptions: Mapping[str, str] = field(default_factory=dict[str, str])
    instance_of: tuple[str, ...] = ()
    birth_dates: tuple[WikidataTime, ...] = ()
    death_dates: tuple[WikidataTime, ...] = ()
    coordinates: tuple[Coordinates, ...] = ()
    authority_control: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict[str, tuple[str, ...]]
    )

    @property
    def is_human(self) -> bool:
        return HUMAN in self.instance_of

    @property
    def is_living(self) -> bool | None:
        """True for a human with a birth date and no death date; None when unknown."""
        if not self.is_human or not self.birth_dates:
            return None
        return not self.death_dates

    def birth_year(self) -> int | None:
        """The birth year if Wikidata's best values agree on one."""
        return _single_year(self.birth_dates)

    def death_year(self) -> int | None:
        return _single_year(self.death_dates)


def _single_year(dates: tuple[WikidataTime, ...]) -> int | None:
    years = {d.year for d in dates if d.precision >= 9}
    return years.pop() if len(years) == 1 else None


_PROJECT_SUFFIX: Mapping[str, str] = {
    "wikipedia": "wiki",
    "wiktionary": "wiktionary",
    "wikisource": "wikisource",
    "wikiquote": "wikiquote",
    "wikiversity": "wikiversity",
    "wikivoyage": "wikivoyage",
    "wikibooks": "wikibooks",
    "wikinews": "wikinews",
}

# interwiki prefixes whose database name differs from prefix.replace("-", "_")
_DBNAME_EXCEPTIONS: Mapping[str, str] = {"be-tarask": "be_x_old", "nb": "no"}


def dbname(lang: str, project: str = "wikipedia") -> str:
    """Wikidata's site id for an interwiki prefix, e.g. ("de", "wikipedia") -> "dewiki",
    ("zh-yue", "wikipedia") -> "zh_yuewiki", ("be-tarask", ...) -> "be_x_oldwiki"."""
    lang = lang.lower()
    return _DBNAME_EXCEPTIONS.get(lang, lang.replace("-", "_")) + _PROJECT_SUFFIX.get(
        project, project
    )


def _same_title(a: str, b: str, case_sensitive_first: bool) -> bool:
    a, b = a.replace("_", " ").strip(), b.replace("_", " ").strip()
    if case_sensitive_first:
        return a == b
    return turn_first_to_upper(a) == turn_first_to_upper(b)


@dataclass(frozen=True)
class InterwikiCheck:
    """Local interwiki links compared with the item's sitelinks."""

    redundant: tuple[str, ...] = ()  # links Wikidata already has, e.g. "[[de:Berlin]]"
    conflicts: tuple[tuple[str, str, str], ...] = ()  # (link, local target, Wikidata target)
    not_on_wikidata: tuple[str, ...] = ()  # links to a wiki the item has no sitelink for


def _interwiki_links(article_text: str, site: SiteConfig) -> list[DotNetMatch]:
    """Interwiki links outside comments, nowiki and template calls."""
    unformatted = "".join(u.value for u in W.UnformattedText.matches(article_text))
    templates = _templates.get_all_template_detail(article_text)
    out: list[DotNetMatch] = []
    for m in W.PossibleInterwikis.matches(article_text):
        lang = m.group(1).strip().lower()
        if lang not in site.interwiki_languages or lang == site.lang_code:
            continue
        if any(m.value in t for t in templates):
            continue
        if m.value in unformatted:
            unformatted = tools.replace_once(unformatted, m.value, "")[0]
            continue
        out.append(m)
    return out


def check_interwikis(
    article_text: str, item: WikidataItem, site: SiteConfig | None = None
) -> InterwikiCheck:
    """Compare the page's interwiki links with item's sitelinks for the same project."""
    site = site or current_site()
    redundant: list[str] = []
    conflicts: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for m in _interwiki_links(article_text, site):
        lang = m.group(1).strip().lower()
        target = m.group(2).strip()
        on_wikidata = item.sitelinks.get(dbname(lang, site.project))
        link = m.value.strip()
        if on_wikidata is None:
            missing.append(link)
        elif _same_title(target, on_wikidata, lang == "jbo" or site.project == "wiktionary"):
            redundant.append(link)
        else:
            conflicts.append((link, target, on_wikidata))
    return InterwikiCheck(tuple(redundant), tuple(conflicts), tuple(missing))


def remove_interwikis_on_wikidata(
    article_text: str, item: WikidataItem, site: SiteConfig | None = None
) -> tuple[str, InterwikiCheck]:
    """Remove the interwiki links Wikidata already has (with a trailing comment on the same
    line). Conflicting links and links Wikidata lacks are kept and reported."""
    site = site or current_site()
    check = check_interwikis(article_text, item, site)
    if not check.redundant:
        return article_text, check
    remove = set(check.redundant)
    matches = [m for m in _interwiki_links(article_text, site) if m.value.strip() in remove]
    # remove each link; a line left empty goes too
    text = article_text
    for m in reversed(matches):
        start, end = m.index, m.index + m.length
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", end)
        line_end = len(text) if line_end < 0 else line_end
        if not (text[line_start:start] + text[end:line_end]).strip():
            start, end = line_start, min(line_end + 1, len(text))
        text = text[:start] + text[end:]
    return text, check
