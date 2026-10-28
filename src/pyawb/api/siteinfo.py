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
# Ported from AutoWikiBrowser WikiFunctions/SiteInfo.cs and Variables.SetProject /
# SetLanguageSpecificValues. Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""A wiki's configuration from the API (meta=siteinfo) and the SiteConfig built from it.

Parsing is separate from fetching: parse_siteinfo and site_config take JSON and return data, so
tests run offline on recorded responses.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlsplit

from pyawb.api.errors import BrokenResponseException, check_errors
from pyawb.api.transport import Param, Transport
from pyawb.core import namespace as ns_util
from pyawb.core import rx
from pyawb.core.site import (
    CANONICAL_NAMESPACE_ALIASES,
    CANONICAL_NAMESPACES,
    EN_MONTH_NAMES,
    SiteConfig,
)

SITEINFO_PARAMS: Mapping[str, Param] = {
    "action": "query",
    "meta": "siteinfo",
    "siprop": "general|namespaces|namespacealiases|magicwords|extensiontags|functionhooks|variables"
    "|protocols|restrictions",
}

MONTH_MESSAGES: tuple[str, ...] = tuple(m.lower() + "-gen" for m in EN_MONTH_NAMES)
"""MediaWiki messages with the genitive month names (AWB's localised month names)."""

# Projects whose wiki is one site, not one per language (Variables.SetProject).
_SINGLE_SITE_URLS: Mapping[str, str] = {
    "commons": "https://commons.wikimedia.org",
    "meta": "https://meta.wikimedia.org",
    "mediawiki": "https://www.mediawiki.org",
    "incubator": "https://incubator.wikimedia.org",
    "species": "https://species.wikimedia.org",
    "wikidata": "https://www.wikidata.org",
}


@dataclass(frozen=True)
class SiteInfo:
    """meta=siteinfo, as AWB reads it (SiteInfo.cs)."""

    language: str = "en"
    is_right_to_left: bool = False
    capitalize_first_letter: bool = True
    mediawiki_version: str = ""
    category_collation: str = ""
    server: str = ""
    script_path: str = "/w"
    article_path: str = "/wiki/$1"
    # id -> "Name:" (no entry for 0)
    namespaces: Mapping[int, str] = field(default_factory=dict[int, str])
    canonical_namespaces: Mapping[int, str] = field(default_factory=dict[int, str])
    namespace_aliases: Mapping[int, tuple[str, ...]] = field(
        default_factory=dict[int, tuple[str, ...]]
    )
    magic_words: Mapping[str, tuple[str, ...]] = field(default_factory=dict[str, tuple[str, ...]])
    # the whole "query" object, for the editor's highlighter (editor.mwconfig.from_siteinfo)
    query: Mapping[str, Any] = field(default_factory=dict[str, Any])

    @property
    def article_url(self) -> str:
        return _absolute(self.server) + self.article_path

    @property
    def unicode_category_collation(self) -> bool:
        """Variables.UnicodeCategoryCollation: the wiki sorts categories by uca-* collation."""
        return bool(rx.DotNetRegex("[a-z-]*uca-").is_match(self.category_collation))


def _absolute(server: str) -> str:
    return "https:" + server if server.startswith("//") else server


def parse_siteinfo(result: Mapping[str, Any]) -> SiteInfo:
    """SiteInfo from a SITEINFO_PARAMS response (formatversion=2)."""
    check_errors(result)
    query: Mapping[str, Any] | None = result.get("query")
    if query is None or "general" not in query:
        raise BrokenResponseException("siteinfo response without general information")
    general: Mapping[str, Any] = query["general"]
    if "namespaces" not in query or "namespacealiases" not in query:
        raise BrokenResponseException("siteinfo response without namespaces")

    namespaces: dict[int, str] = {}
    canonical: dict[int, str] = {}
    raw_ns: Mapping[str, Mapping[str, Any]] = query["namespaces"]
    for info in raw_ns.values():
        ns_id = int(info["id"])
        if ns_id == 0:
            continue
        namespaces[ns_id] = str(info.get("name", info.get("*", ""))) + ":"
        if info.get("canonical"):
            canonical[ns_id] = str(info["canonical"]) + ":"
    if not ns_util.verify_namespaces(namespaces):
        raise BrokenResponseException("the wiki's namespaces are incomplete")

    aliases: dict[int, list[str]] = {n: [] for n in namespaces}
    for a in query["namespacealiases"]:
        ns_id = int(a["id"])
        if ns_id != 0 and ns_id in aliases:
            aliases[ns_id].append(str(a.get("alias", a.get("*", ""))) + ":")

    magic: dict[str, tuple[str, ...]] = {}
    for mw in query.get("magicwords", ()):
        magic[str(mw["name"])] = tuple(str(x) for x in mw.get("aliases", ()))

    rtl = general.get("rtl", False)
    return SiteInfo(
        language=str(general.get("lang", "en")),
        # formatversion=2 gives a boolean; formatversion=1 an empty string when set
        is_right_to_left=rtl is not False and rtl is not None,
        capitalize_first_letter=general.get("case") == "first-letter",
        mediawiki_version=str(general.get("generator", "")).replace("MediaWiki ", ""),
        category_collation=str(general.get("categorycollation", "")),
        server=str(general.get("server", "")),
        script_path=str(general.get("scriptpath", "/w")),
        article_path=str(general.get("articlepath", "/wiki/$1")),
        namespaces=namespaces,
        canonical_namespaces=canonical,
        namespace_aliases={n: tuple(v) for n, v in aliases.items()},
        magic_words=magic,
        query=query,
    )


def parse_messages(result: Mapping[str, Any]) -> dict[str, str]:
    """meta=allmessages as {name: text}; missing messages are left out."""
    check_errors(result)
    out: dict[str, str] = {}
    for m in result.get("query", {}).get("allmessages", ()):
        if m.get("missing"):
            continue
        out[str(m["name"])] = str(m.get("content", m.get("*", "")))
    return out


def month_names(messages: Mapping[str, str]) -> tuple[str, ...] | None:
    """The 12 localised month names, or None unless all 12 messages exist."""
    if not all(m in messages for m in MONTH_MESSAGES):
        return None
    return tuple(messages[m] for m in MONTH_MESSAGES)


def parse_awb_tag_defined(result: Mapping[str, Any]) -> bool:
    """list=tags&tgprop=active: whether an active "AWB" change tag exists (SiteInfo.LoadAWBTag).
    An error response (e.g. a private wiki) counts as not defined."""
    if "error" in result:
        return False
    tags: Sequence[Mapping[str, Any]] = result.get("query", {}).get("tags", ())
    return any(t.get("name") == "AWB" and t.get("active") not in (None, False) for t in tags)


# Variables.SetLanguageSpecificValues: (mSummaryTag, WPAWB) where they differ from
# ("using", "[[Project:AWB|AWB]]"). "en" Wikipedia uses "[[WP:AWB|AWB]]".
_SUMMARY_TAGS: Mapping[str, tuple[str | None, str | None]] = {
    "ar": ("", "باستخدام [[Project:أوب|أوب]]"),
    "arz": ("", "عن طريق [[Project:AWB|اوب]]"),
    "be": ("з дапамогай", None),
    "bg": ("редактирано с", "AWB"),
    "bn": ("", "[[Project:অউব্রা|অউব্রা]] ব্যবহার করে"),
    "ca": ("", "[[Viquipèdia:AutoWikiBrowser|AWB]]"),
    "cs": ("za použití", "[[Wikipedie:AutoWikiBrowser|AWB]]"),
    "da": ("ved brug af", "[[en:WP:AWB|AWB]]"),
    "de": ("mit", None),
    "el": ("με τη χρήση", None),
    "eo": ("per", "[[Vikipedio:AutoWikiBrowser|AWB]]"),
    "es": ("(Usando", "[[:w:WP:AWB|AWB]])"),
    "fa": ("", "با استفاده از [[Project:AutoWikiBrowser|AWB]]"),
    "fr": ("avec", "[[Wikipédia:AutoWikiBrowser|AWB]]"),
    "he": ("באמצעות", "[[ויקיפדיה:AutoWikiBrowser|AWB]]"),
    "hi": ("", "[[विकिपीडिया:ऑटोविकिब्राउज़र|AWB]] के साथ"),
    "hu": ("", "[[Wikipédia:AutoWikiBrowser|AWB]]"),
    "hy": ("oգտվելով", "[[Վիքիպեդիա:ԱվտոՎիքիԲրաուզեր|ԱՎԲ]]"),
    "it": ("", None),
    "ku": ("", "[[Wîkîpediya:AutoWikiBrowser|AWB]]"),
    "ms": ("menggunakan", None),
    "ne": ("", "स्वतःविकी ब्राउजर प्रयोग गर्दै"),
    "nl": ("met", None),
    "pa": ("ਦੀ ਵਰਤੋਂ ਨਾਲ", None),
    "pl": ("przy użyciu", None),
    "pt": ("utilizando", None),
    "ru": ("с помощью", None),
    "sk": ("", None),
    "sl": ("", None),
    "sq": ("duke përdorur", None),
    "sr": ("користећи", "[[Project:AWB|AWB]]"),
    "sv": ("med", None),
    "tr": ("", "[[Vikipedi:AWB|AWB]] ile "),
    "uk": ("за допомогою", None),
    "zh": ("由", "[[维基百科:自动维基浏览器|自动维基浏览器]]协助"),
    "zh-classical": ("藉", "[[維基大典:自動維基瀏覽器|自動維基瀏覽器]]之助"),
    "zh-yue": ("用", "[[Wikipedia:AutoWikiBrowser|AWB]]幫手"),
}

_LANGUAGE_PROJECTS = frozenset(
    {"wikipedia", "wikinews", "wikisource", "wikibooks", "wikiquote", "wiktionary", "wikiversity"}
)


def summary_tag(lang_code: str, project: str) -> str:
    """Variables.SummaryTag: the text appended to edit summaries, e.g. " using [[WP:AWB|AWB]]".
    Language-specific wording applies to the per-language projects only, as in AWB. Empty parts
    are skipped (AWB would leave a double space)."""
    using, link = "using", "[[Project:AWB|AWB]]"
    if project in _LANGUAGE_PROJECTS:
        if lang_code == "en" and project == "wikipedia":
            link = "[[WP:AWB|AWB]]"
        local_using, local_link = _SUMMARY_TAGS.get(lang_code, (None, None))
        using = using if local_using is None else local_using
        link = link if local_link is None else local_link
    return " " + " ".join(p for p in (using, link) if p)


def wiki_url(lang_code: str, project: str, custom_url: str = "") -> tuple[str, str, str]:
    """(url, url_end, lang_code) for a project (Variables.SetProject): "https://en.wikipedia.org",
    "/w/". custom_url is a custom wiki's script path, e.g. "https://wiki.example.org/w/"; its
    language comes from siteinfo later."""
    if project == "custom" or custom_url:
        parts = urlsplit(custom_url if "://" in custom_url else "https://" + custom_url)
        url_end = parts.path or "/"
        if not url_end.endswith("/"):
            url_end += "/"
        return f"{parts.scheme}://{parts.netloc}", url_end, "en"
    if project in _SINGLE_SITE_URLS:
        return _SINGLE_SITE_URLS[project], "/w/", "en"
    return f"https://{lang_code}.{project}.org", "/w/", lang_code


def base_site_config(lang_code: str, project: str, custom_url: str = "") -> SiteConfig:
    """The SiteConfig for a wiki before anything is loaded from it: URL and AWB's
    language-specific values (stub patterns, typo summary, summary tag)."""
    url, url_end, lang = wiki_url(lang_code, project, custom_url)
    cfg = SiteConfig(project=project if not custom_url else "custom", url=url, url_end=url_end)
    if project in _LANGUAGE_PROJECTS:
        cfg = cfg.with_lang_code(lang)
    else:
        cfg = replace(cfg, lang_code=lang)
    return replace(cfg, summary_tag=summary_tag(lang, cfg.project))


def site_config(
    base: SiteConfig,
    info: SiteInfo,
    months: Sequence[str] | None = None,
    *,
    tag_edits: bool = False,
) -> SiteConfig:
    """Apply siteinfo to a SiteConfig (Session.LoadProjectOptions and UpdateWikiStatus).

    Namespaces, aliases and magic words come from the wiki; canonical names are MediaWiki's, plus
    the wiki's canonical names for extension namespaces. Custom wikis take their language from
    siteinfo. Wiktionary never capitalises the first letter. With tag_edits (an active "AWB"
    change tag) edits are tagged instead of getting the summary tag.
    """
    canonical = dict(CANONICAL_NAMESPACES)
    for ns_id, name in info.canonical_namespaces.items():
        canonical.setdefault(ns_id, name)
    aliases: dict[int, tuple[str, ...]] = {}
    for ns_id in info.namespaces:
        # canonical aliases ("Image:") are kept, as the wiki lists them only on some versions
        extra = [a for a in CANONICAL_NAMESPACE_ALIASES.get(ns_id, ()) if a]
        local = list(info.namespace_aliases.get(ns_id, ()))
        aliases[ns_id] = tuple(dict.fromkeys(local + extra))

    cfg = base
    if base.project in ("custom", "wikia", "fandom") and info.language != base.lang_code:
        cfg = cfg.with_lang_code(info.language)
    if months is None or base.is_wikipedia_en:
        months = EN_MONTH_NAMES
    return replace(
        cfg,
        rtl=info.is_right_to_left,
        capitalize_first_letter=info.capitalize_first_letter and base.project != "wiktionary",
        unicode_category_collation=base.project != "custom" and info.unicode_category_collation,
        namespaces=dict(info.namespaces),
        canonical_namespaces=canonical,
        namespace_aliases=aliases,
        magic_words=dict(info.magic_words),
        month_names=tuple(months),
        script_path=info.script_path,
        summary_tag="" if tag_edits else cfg.summary_tag,
    )


def load_site_config(transport: Transport, base: SiteConfig) -> tuple[SiteConfig, SiteInfo, bool]:
    """Fetch siteinfo, localised month names and the AWB change tag, and build the SiteConfig.
    Returns (config, siteinfo, awb_tag_defined)."""
    info = parse_siteinfo(transport.request(SITEINFO_PARAMS))
    months = None
    if not base.is_wikipedia_en:
        months = month_names(
            parse_messages(
                transport.request(
                    {
                        "action": "query",
                        "meta": "allmessages",
                        "ammessages": "|".join(MONTH_MESSAGES),
                    }
                )
            )
        )
    try:
        tags = transport.request(
            {"action": "query", "list": "tags", "tgprop": "active", "tglimit": "max"}
        )
        tag_defined = parse_awb_tag_defined(tags)
    except Exception:  # a private wiki or an old MediaWiki: not tagged
        tag_defined = False
    return site_config(base, info, months, tag_edits=tag_defined), info, tag_defined


INTERWIKI_ORDER_TITLE = "Wikipedia:AutoWikiBrowser/IW"
"""On English Wikipedia: the interwiki orders MetaDataSorter uses on every wiki."""


def _interwiki_sort_key(code: str) -> tuple[str, str]:
    # AWB sorts with the en-US culture, ignoring case; hyphens weigh less than letters there
    return code.replace("-", "").lower(), code


def parse_interwiki_order(text: str) -> dict[str, tuple[str, ...]]:
    """MetaDataSorter.LoadInterWikiFromNetwork: the SiteConfig interwiki_* fields from the text of
    [[Wikipedia:AutoWikiBrowser/IW]]."""
    from pyawb.core.tools import string_between

    def codes(start: str, end: str) -> list[str]:
        raw = string_between(text, start, end)
        raw = raw.replace("\r\n", "").replace(">", "").replace("\n", "")
        return [s.strip().lower() for s in raw.split(",") if s.strip()]

    local_alpha = codes("<!--InterwikiLocalAlphaBegins-->", "<!--InterwikiLocalAlphaEnds-->")
    local_first = codes("<!--InterwikiLocalFirstBegins-->", "<!--InterwikiLocalFirstEnds-->")
    alpha = sorted(local_first, key=_interwiki_sort_key)
    alpha_en_first = ["en", *(c for c in alpha if c != "en")] if "en" in alpha else alpha
    return {
        "interwiki_local_alpha": tuple(local_alpha),
        "interwiki_local_first": tuple(local_first),
        "interwiki_alpha": tuple(alpha),
        "interwiki_alpha_en_first": tuple(alpha_en_first),
    }


SITEMATRIX_PARAMS: Mapping[str, Param] = {"action": "sitematrix", "smtype": "language"}

_SITEMATRIX_PROJECTS: Mapping[str, str] = {
    "wiki": "wikipedia",
    "wiktionary": "wiktionary",
    "wikibooks": "wikibooks",
    "wikinews": "wikinews",
    "wikisource": "wikisource",
    "wikiquote": "wikiquote",
    "wikiversity": "wikiversity",
    "wikivoyage": "wikivoyage",
}


@dataclass(frozen=True)
class SiteMatrix:
    """Wikimedia language codes (SiteMatrix.cs): all of them, and per project."""

    languages: frozenset[str] = frozenset()
    language_names: Mapping[str, str] = field(default_factory=dict[str, str])
    project_languages: Mapping[str, frozenset[str]] = field(
        default_factory=dict[str, frozenset[str]]
    )


def parse_sitematrix(result: Mapping[str, Any]) -> SiteMatrix:
    """SiteMatrix from action=sitematrix (formatversion=2). Closed wikis still count as
    languages, as interwiki links to them stay valid."""
    check_errors(result)
    matrix: Mapping[str, Any] = result.get("sitematrix", {})
    languages: set[str] = set()
    names: dict[str, str] = {}
    per_project: dict[str, set[str]] = {p: set() for p in _SITEMATRIX_PROJECTS.values()}
    for key, lang in matrix.items():
        if key in ("count", "specials") or not isinstance(lang, Mapping):
            continue
        entry: Mapping[str, Any] = lang  # pyright: ignore[reportUnknownVariableType]
        code = str(entry.get("code", ""))
        if code == "be-x-old":  # site name differs from the language code
            code = "be-tarask"
        languages.add(code)
        names[code] = str(entry.get("name") or code)
        for site in entry.get("site", ()):
            project = _SITEMATRIX_PROJECTS.get(str(site.get("code", "")))
            if project is not None:
                per_project[project].add(code)
    return SiteMatrix(
        frozenset(languages), names, {p: frozenset(v) for p, v in per_project.items()}
    )
