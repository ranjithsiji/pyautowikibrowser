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
# Ported from AutoWikiBrowser WikiFunctions/Variables.cs and Namespace.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Per-wiki settings that regexes and parsers depend on (the regex-relevant half of Variables).

A SiteConfig is immutable; build one per wiki (from siteinfo, in awb_x.api). Code that AWB wrote
against the global Variables reads current_site() instead; use_site() sets it for a block. The
current site is a ContextVar, so worker threads and tasks each see their own.
"""

from __future__ import annotations

import contextlib
from collections.abc import Generator, Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass, field, replace
from types import MappingProxyType


class Namespace:
    """Namespace numbers (WikiFunctions/Namespace.cs)."""

    MEDIA = -2
    SPECIAL = -1
    ARTICLE = 0
    TALK = 1
    USER = 2
    USER_TALK = 3
    PROJECT = 4
    PROJECT_TALK = 5
    FILE = 6
    FILE_TALK = 7
    MEDIAWIKI = 8
    MEDIAWIKI_TALK = 9
    TEMPLATE = 10
    TEMPLATE_TALK = 11
    HELP = 12
    HELP_TALK = 13
    CATEGORY = 14
    CATEGORY_TALK = 15
    PORTAL = 100
    PORTAL_TALK = 101
    DRAFT = 118
    DRAFT_TALK = 119
    MOS = 126
    MOS_TALK = 127
    TIMEDTEXT = 710
    TIMEDTEXT_TALK = 711
    MODULE = 828
    MODULE_TALK = 829
    EVENT = 1728
    EVENT_TALK = 1729


CANONICAL_NAMESPACES: Mapping[int, str] = MappingProxyType(
    {
        -2: "Media:",
        -1: "Special:",
        1: "Talk:",
        2: "User:",
        3: "User talk:",
        4: "Project:",
        5: "Project talk:",
        6: "File:",
        7: "File talk:",
        8: "MediaWiki:",
        9: "MediaWiki talk:",
        10: "Template:",
        11: "Template talk:",
        12: "Help:",
        13: "Help talk:",
        14: "Category:",
        15: "Category talk:",
        118: "Draft:",
        119: "Draft talk:",
        126: "MOS:",
        127: "MOS talk:",
        710: "TimedText:",
        711: "TimedText talk:",
        828: "Module:",
        829: "Module talk:",
        1728: "Event:",
        1729: "Event talk:",
    }
)

CANONICAL_NAMESPACE_ALIASES: Mapping[int, tuple[str, ...]] = MappingProxyType(
    {n: ("Image:",) if n == 6 else ("Image talk:",) if n == 7 else () for n in CANONICAL_NAMESPACES}
)

EN_MONTH_NAMES: tuple[str, ...] = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


# AWB's ProjectEnum, in its order: Variables compares positions (e.g. "<= commons").
PROJECTS: tuple[str, ...] = (
    "wikipedia",
    "wiktionary",
    "wikidata",
    "wikisource",
    "wikiquote",
    "wikiversity",
    "wikivoyage",
    "wikibooks",
    "wikinews",
    "species",
    "commons",
    "meta",
    "mediawiki",
    "incubator",
    "wikia",
    "fandom",
    "custom",
)


def _frozen[K, V](d: Mapping[K, V]) -> Mapping[K, V]:
    return MappingProxyType(dict(d))


@dataclass(frozen=True)
class SiteConfig:
    """What WikiRegexes and the parsers need to know about one wiki.

    Namespace names end with ":" (as in AWB). Namespace 0 has no entry.
    """

    lang_code: str = "en"
    project: str = "wikipedia"
    url: str = "https://en.wikipedia.org"
    url_end: str = "/w/"
    rtl: bool = False
    capitalize_first_letter: bool = True
    namespaces: Mapping[int, str] = field(default_factory=lambda: _frozen(_EN_NAMESPACES))
    canonical_namespaces: Mapping[int, str] = CANONICAL_NAMESPACES
    namespace_aliases: Mapping[int, tuple[str, ...]] = CANONICAL_NAMESPACE_ALIASES
    # MediaWiki magic word id -> aliases, e.g. "redirect" -> ("#REDIRECT",)
    magic_words: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: _frozen({}))
    month_names: tuple[str, ...] = EN_MONTH_NAMES
    stub: str = "[^{}|]*?[Ss]tub"  # Variables.Stub: stub template name pattern
    sect_stub: str = r"\{\{[Ss]ect"  # Variables.SectStub: section stub template start
    typo_summary_tag: str = "typos fixed: "  # Variables.TypoSummaryTag
    untitled_heading: str = "Untitled"  # Variables.UntitledHeading (talk page fixes)
    # Templates that take a date= parameter (WikiRegexes.DatedTemplates, from
    # [[WP:AWB/Dated templates]]), first letter upper case; awb_x.api loads them with
    # parsers.templates.load_dated_templates.
    dated_templates: tuple[str, ...] = ()
    # Text of [[WP:AWB/Template redirects]] and the {{AWB rename template parameter}} rules
    # (WikiRegexes.TemplateRedirects / RenamedTemplateParameters); parsed and cached by
    # parsers.templates.site_template_redirects / site_renamed_template_parameters.
    template_redirects_text: str = ""
    renamed_template_parameters_text: str = ""
    script_path: str = "/w"
    # Wikis sorting categories by Unicode collation (uca-*): sort keys keep their diacritics.
    unicode_category_collation: bool = False
    # Interwiki language codes (SiteMatrix.Languages). awb_x.api fills this from the site matrix;
    # the default is the set AWB's unit tests use.
    interwiki_languages: frozenset[str] = frozenset({"ar", "en", "ru", "sq"})
    # Titles that really contain underscores (Variables.UnderscoredTitles), loaded by awb_x.api.
    underscored_titles: frozenset[str] = frozenset()
    # Appended to edit summaries (Variables.SummaryTag), localised per wiki.
    summary_tag: str = " using [[Project:AWB|AWB]]"
    # Interwiki ordering lists ([[WP:AWB/IW]]); defaults are AWB's unit-test values.
    interwiki_local_alpha: tuple[str, ...] = ("ar", "de", "en", "ru", "sq")
    interwiki_local_first: tuple[str, ...] = ("ar", "de", "en", "ru", "sq")
    interwiki_alpha: tuple[str, ...] = ("ar", "de", "en", "ru", "sq")
    interwiki_alpha_en_first: tuple[str, ...] = ("en", "ar", "de", "ru", "sq")

    def __post_init__(self) -> None:
        for ns, name in self.namespaces.items():
            if not name.endswith(":"):
                raise ValueError(f"namespace {ns} name {name!r} must end with ':'")
        if 0 in self.namespaces:
            raise ValueError("namespace 0 must not have an entry")

    def __hash__(self) -> int:
        # The mapping fields are read-only views, which are not hashable themselves.
        return hash(
            (
                self.lang_code,
                self.project,
                self.url,
                self.url_end,
                self.rtl,
                self.capitalize_first_letter,
                tuple(self.namespaces.items()),
                tuple(self.canonical_namespaces.items()),
                tuple(self.namespace_aliases.items()),
                tuple(self.magic_words.items()),
                self.month_names,
                self.stub,
                self.sect_stub,
                self.typo_summary_tag,
                self.untitled_heading,
                self.dated_templates,
                self.template_redirects_text,
                self.renamed_template_parameters_text,
                self.script_path,
                self.unicode_category_collation,
                self.interwiki_languages,
                self.underscored_titles,
                self.summary_tag,
                self.interwiki_local_alpha,
                self.interwiki_local_first,
                self.interwiki_alpha,
                self.interwiki_alpha_en_first,
            )
        )

    @property
    def _project_index(self) -> int:
        return (
            PROJECTS.index(self.project) if self.project in PROJECTS else PROJECTS.index("custom")
        )

    @property
    def is_wikimedia_project(self) -> bool:
        """Variables.IsWikimediaProject: a project up to Commons in AWB's ordering."""
        return self._project_index <= PROJECTS.index("commons")

    @property
    def is_wikimedia_monolingual_project(self) -> bool:
        """Variables.IsWikimediaMonolingualProject: species, commons, meta, mediawiki, incubator."""
        return PROJECTS.index("species") <= self._project_index < PROJECTS.index("wikia")

    @property
    def is_wikipedia_en(self) -> bool:
        return self.project == "wikipedia" and self.lang_code == "en"

    @property
    def url_long(self) -> str:
        return self.url + self.url_end

    @classmethod
    def english(cls) -> SiteConfig:
        """English Wikipedia defaults (Variables.SetToEnglish, AWB's unit-test configuration)."""
        return cls()

    def with_lang_code(self, lang_code: str) -> SiteConfig:
        """Variables.SetProjectLangCode: change the language and AWB's language-specific values
        (stub patterns, typo summary, untitled heading); namespaces stay as they are.

        As in AWB, a value a language does not set keeps its previous value, except that "en"
        resets them all to the English defaults. The summary tag is not changed here: it also
        needs the wiki's AWB project link, which awb_x.api sets from the wiki's configuration.
        """
        defaults = SiteConfig()
        if lang_code == "en":
            values: dict[str, str] = {
                "stub": defaults.stub,
                "sect_stub": defaults.sect_stub,
                "typo_summary_tag": "[[WP:AWB/T|typo(s) fixed]]: ",
                "untitled_heading": defaults.untitled_heading,
            }
        else:
            values = {"untitled_heading": defaults.untitled_heading}
            values.update(_LANGUAGE_VALUES.get(lang_code, {}))
        return replace(self, lang_code=lang_code, rtl=lang_code == "ar", **values)

    def generate_namespace_regex(self, *namespaces: int) -> str:
        """All names of the given namespaces as a regex alternation, e.g. "File|Image".

        Port of WikiRegexes.GenerateNamespaceRegex.
        """
        parts: list[str] = []
        for ns in namespaces:
            if ns == Namespace.ARTICLE:
                continue
            name = self.namespaces[ns]
            parts.append(name.rstrip(":"))
            canonical = self.canonical_namespaces.get(ns)
            if canonical is not None and canonical != name:
                parts.append(canonical.rstrip(":"))
            parts.extend(alias.rstrip(":") for alias in self.namespace_aliases.get(ns, ()))
        return "|".join(parts).replace(" ", "[ _]")

    @property
    def namespaces_case_insensitive(self) -> Mapping[int, str]:
        """Variables.NamespacesCaseInsensitive: regex text matching each namespace prefix."""
        return {ns: "(?i:" + self.generate_namespace_regex(ns) + r")\s*:" for ns in self.namespaces}


# Variables.SetLanguageSpecificValues: per-language values other than the summary tag.
_LANGUAGE_VALUES: dict[str, dict[str, str]] = {
    "ar": {"stub": "[^{}|]*?(?:[Ss]tub|بذرة|بذور)[^{}]*?", "typo_summary_tag": "الأخطاء المصححة: "},
    "arz": {
        "stub": "[^{}|]*?(?:[Ss]tub|تقاوى|بذرة)[^{}]*?",
        "typo_summary_tag": "الأخطاء المصححة: ",
    },
    "bn": {"typo_summary_tag": "বানান সংশোধন: "},
    "cs": {"stub": "[^{}|]*?([Pp]ahýl)"},
    "cy": {"stub": "[^{}|]*?([Ss]tub|[Εe]ginyn[^{}]*?)"},
    "de": {"typo_summary_tag": "Schreibweise: "},
    "el": {"stub": "[^{}|]*?([Ss]tub|[Εε]πέκταση)", "sect_stub": r"\{\{θέματος"},
    "eo": {"typo_summary_tag": "Skribmaniero: "},
    "hy": {"stub": "[^{}|]*?([Ss]tub|Անավարտ|Զարգացնել[^{}]*?)"},
    "it": {"stub": "(DUMMYTEMPLATE)"},
    "pl": {"sect_stub": r"\{\{[Ss]ek"},
    "ru": {"stub": "[^{}]*?(?:[Ss]tub|[Зз]аготовка)"},
    "sco": {"stub": "(Stub/[^{}|]+|[^{}|]*?[Ss]tub)"},
    "sl": {"stub": "(?:[^{}]*?[Ss]tub|[Šš]krbina[^{}]*?)"},
    "sq": {
        "typo_summary_tag": "[[WP:AWB/T|përmirësime tipografike]]: ",
        "stub": "(?:[^{}]*?[Cc]ung[^{}]*?)",
    },
    "sr": {"untitled_heading": "Први поднаслов"},
    "sv": {
        "typo_summary_tag": "rättar stavfel: ",
        "stub": r"(?:[^{}]*?[Ss]tub|[^{}]+?stub(?:[ \-][^{}]+)?)"
        r"(?<![Ss]tubbmall|[Ss]ubstub|[Ss]tubavsnitt|[Uu]ncategorized stub)",
    },
    "tr": {"typo_summary_tag": "yazış şekli: "},
    "uk": {
        "stub": "[^{}|]*?(?:[Ss]tub|[Дд]оробити)",
        "sect_stub": r"\{\{([Рp]озділ\-доробити|[Ss]ection[ \-]stub)",
    },
    "ur": {"typo_summary_tag": "درستی املا"},
    "zh": {"stub": ".*?(?:小作品|[Ss]tub)", "untitled_heading": "無標題"},
}


_EN_NAMESPACES: dict[int, str] = {
    **CANONICAL_NAMESPACES,
    4: "Wikipedia:",
    5: "Wikipedia talk:",
    100: "Portal:",
    101: "Portal talk:",
}


_ENGLISH = SiteConfig()
_current: ContextVar[SiteConfig] = ContextVar("awb_x_site", default=_ENGLISH)


def current_site() -> SiteConfig:
    """The wiki being worked on (AWB's Variables). English Wikipedia unless set with use_site."""
    return _current.get()


def set_current_site(site: SiteConfig) -> Token[SiteConfig]:
    """Make site the current wiki until reset_current_site(token) (or for good, in a worker)."""
    return _current.set(site)


def reset_current_site(token: Token[SiteConfig]) -> None:
    _current.reset(token)


@contextlib.contextmanager
def use_site(site: SiteConfig) -> Generator[SiteConfig]:
    """Make site the current wiki for the duration of the block."""
    token = _current.set(site)
    try:
        yield site
    finally:
        _current.reset(token)
