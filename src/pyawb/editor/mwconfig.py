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
# Configuration and token names ported from @bhsd/codemirror-mediawiki 4.7.1 (src/config.ts,
# src/static.ts; GPL-2.0-or-later, (C) MusikAnimal, Bhsd and others), @bhsd/cm-util (MIT) and
# wikiparser-node (config/default.json; GPL-3.0-or-later, (C) Bhsd).
"""What the wikitext tokenizer needs to know about a wiki (MwConfig) and the token class names."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import regex

TOKENS: Mapping[str, str] = {
    "apostrophes": "mw-apostrophes",
    "comment": "mw-comment",
    "convertBracket": "mw-convert-bracket",
    "convertDelimiter": "mw-convert-delimiter",
    "convertFlag": "mw-convert-flag",
    "convertLang": "mw-convert-lang",
    "doubleUnderscore": "mw-double-underscore",
    "em": "mw-em",
    "error": "mw-error",
    "extLink": "mw-extlink",
    "extLinkBracket": "mw-extlink-bracket",
    "extLinkProtocol": "mw-extlink-protocol",
    "extLinkText": "mw-extlink-text",
    "extTag": "mw-exttag",
    "extTagAttribute": "mw-exttag-attribute",
    "extTagAttributeValue": "mw-exttag-attribute-value",
    "extTagBracket": "mw-exttag-bracket",
    "extTagName": "mw-exttag-name",
    "fileDelimiter": "mw-file-delimiter",
    "fileText": "mw-file-text",
    "freeExtLink": "mw-free-extlink",
    "freeExtLinkProtocol": "mw-free-extlink-protocol",
    "hr": "mw-hr",
    "htmlEntity": "mw-entity",
    "htmlTagAttribute": "mw-htmltag-attribute",
    "htmlTagAttributeValue": "mw-htmltag-attribute-value",
    "htmlTagBracket": "mw-htmltag-bracket",
    "htmlTagName": "mw-htmltag-name",
    "ignored": "mw-ignored",
    "imageParameter": "mw-image-parameter",
    "linkBracket": "mw-link-bracket",
    "linkDelimiter": "mw-link-delimiter",
    "linkPageName": "mw-link-pagename",
    "linkText": "mw-link-text",
    "linkToSection": "mw-link-tosection",
    "list": "mw-list",
    "magicLink": "mw-magic-link",
    "pageName": "mw-pagename",
    "parserFunction": "mw-parserfunction",
    "parserFunctionArgumentName": "mw-parserfunction-argument-name",
    "parserFunctionBracket": "mw-parserfunction-bracket",
    "parserFunctionDelimiter": "mw-parserfunction-delimiter",
    "parserFunctionName": "mw-parserfunction-name",
    "redirect": "mw-redirect",
    "section": "mw-section",
    "sectionHeader": "mw-section-header",
    "signature": "mw-signature",
    "skipFormatting": "mw-skipformatting",
    "strong": "mw-strong",
    "tableBracket": "mw-table-bracket",
    "tableCaption": "mw-table-caption",
    "tableDefinition": "mw-table-definition",
    "tableDefinitionValue": "mw-table-definition-value",
    "tableDelimiter": "mw-table-delimiter",
    "tableDelimiter2": "mw-table-delimiter2",
    "tableTd": "mw-table-td",
    "tableTh": "mw-table-th",
    "template": "mw-template",
    "templateArgumentName": "mw-template-argument-name",
    "templateBracket": "mw-template-bracket",
    "templateDelimiter": "mw-template-delimiter",
    "templateName": "mw-template-name",
    "templateVariable": "mw-templatevariable",
    "templateVariableBracket": "mw-templatevariable-bracket",
    "templateVariableDelimiter": "mw-templatevariable-delimiter",
    "templateVariableName": "mw-templatevariable-name",
}
"""Token identifiers -> CSS-like class names (config.ts `tokens`)."""

# HTML tags MediaWiki allows (wikiparser-node config `html`): normal, can self-close, void.
HTML_TAGS_NORMAL: tuple[str, ...] = (
    "b", "bdi", "del", "i", "ins", "u", "font", "big", "small", "sub", "sup", "h1", "h2", "h3",
    "h4", "h5", "h6", "cite", "code", "em", "s", "strike", "strong", "tt", "var", "div", "center",
    "blockquote", "ol", "ul", "dl", "table", "caption", "pre", "ruby", "rb", "rp", "rt", "rtc",
    "p", "span", "abbr", "dfn", "kbd", "samp", "data", "time", "mark", "tr", "td", "th", "q",
    "bdo",
)  # fmt: skip
SELF_CLOSING_TAGS: tuple[str, ...] = ("li", "dt", "dd")
VOID_HTML_TAGS: tuple[str, ...] = ("br", "wbr", "hr", "meta", "link")
HTML_TAGS: tuple[str, ...] = HTML_TAGS_NORMAL + SELF_CLOSING_TAGS + VOID_HTML_TAGS

TAG_MODES: Mapping[str, str] = {
    "onlyinclude": "mediawiki",
    "includeonly": "mediawiki",
    "noinclude": "mediawiki",
    "translate": "mediawiki",
    "tvar": "mediawiki",
    "indicator": "mediawiki",
    "poem": "mediawiki",
    "ref": "mediawiki",
    "poll": "mediawiki",
    "tabs": "mediawiki",
    "tab": "mediawiki",
    "option": "mediawiki",
    "combooption": "mediawiki",
    "langconvert": "mediawiki",
    "phonos": "mediawiki",
    "pre": "text/pre",
    "nowiki": "text/nowiki",
    "references": "text/references",
    "gallery": "text/gallery",
    "choose": "text/choose",
    "combobox": "text/combobox",
    "inputbox": "text/inputbox",
    "templatedata": "json",
    "maplink": "jsonc",
    "mapframe": "jsonc",
    "math": "text/math",
    "chem": "text/math",
    "ce": "text/math",
    "score": "lilypond",
}
"""Extension tag -> how its content is highlighted (static.ts `tagModes`)."""


@dataclass(frozen=True)
class MwConfig:
    """MwConfig (token.ts): magic words, extension tags, protocols and namespaces of one wiki."""

    url_protocols: str
    tags: Mapping[str, bool]  # extension tags
    tag_modes: Mapping[str, str]
    # [case-insensitive (lower-case keys), case-sensitive]: alias -> canonical name
    function_synonyms: tuple[Mapping[str, str], Mapping[str, str]]
    # [case-insensitive, case-sensitive]: "__notoc__" -> name
    double_underscore: tuple[Mapping[str, str], Mapping[str, str]]
    nsid: Mapping[str, int]  # lower-case namespace name or alias -> id
    variable_ids: Sequence[str] | None = None
    function_hooks: Sequence[str] | None = None
    variants: Sequence[str] | None = None
    redirection: Sequence[str] = ("#REDIRECT",)
    image_keywords: Mapping[str, str] = field(default_factory=dict[str, str])
    permitted_html_tags: Sequence[str] = ()
    implicitly_closed_html_tags: Sequence[str] = ()


def _is_underscore(s: str) -> bool:
    """@bhsd/cm-util isUnderscore: a switch written with "__" (not full-width "＿＿")."""
    return not (s.startswith("＿＿") and s.endswith("＿＿") and len(s) > 4)


def _double_underscore(new_schema: Mapping[str, str]) -> dict[str, str]:
    return {(f"__{k}__" if _is_underscore(k) else k): v for k, v in new_schema.items()}


_VARIANT_MAP = {
    "sr-ec": "sr-Cyrl",
    "sr-el": "sr-Latn",
    "zh-cn": "zh-Hans-CN",
    "zh-sg": "zh-Hans-SG",
    "zh-my": "zh-Hans-MY",
    "zh-tw": "zh-Hant-TW",
    "zh-hk": "zh-Hant-HK",
    "zh-mo": "zh-Hant-MO",
}


def _bcp47(tag: str) -> str:
    """Canonical case of a BCP 47 tag (what Intl.Locale prints): zh-hans -> zh-Hans."""
    parts = tag.split("-")
    out = [parts[0].lower()]
    for p in parts[1:]:
        if len(p) == 4 and p.isalpha():
            out.append(p.title())
        elif len(p) == 2 and p.isalpha():
            out.append(p.upper())
        else:
            out.append(p.lower())
    return "-".join(out)


def bcp47_variants(variants: Sequence[str]) -> list[str]:
    """@bhsd/cm-util getBCP47Variants: the variants plus their BCP 47 forms."""
    if not variants or any(v.lower() != v for v in variants):
        return list(variants)
    out = dict.fromkeys(variants)
    for v in variants:
        out.setdefault(_VARIANT_MAP.get(v, _bcp47(v)))
    return list(out)


def config_from_parser_data(
    data: Mapping[str, Any], modes: Mapping[str, str] = TAG_MODES
) -> MwConfig:
    """static.ts getStaticMwConfig: MwConfig from a wikiparser-node configuration."""
    p0, p1, *p2 = data["parserFunction"]
    d = data["doubleUnderscore"]
    flat = [s for group in p2 for s in group]
    return MwConfig(
        url_protocols=data["protocol"] + "|//",
        tags={s: True for s in data["ext"]},
        tag_modes=dict(modes),
        function_synonyms=({**p0, **{s: s for s in flat}}, dict(p1)),
        double_underscore=(_double_underscore(d[2]), _double_underscore(d[3])),
        nsid=dict(data["nsid"]),
        variable_ids=list(data["variable"]),
        function_hooks=list(data["functionHook"]),
        variants=bcp47_variants(data.get("variants", [])),
        redirection=list(data["redirection"]),
        image_keywords=dict(data["img"]),
    )


_CASE_INSENSITIVE_SUBST = ("subst", "safesubst")


def from_siteinfo(query: Mapping[str, Any], modes: Mapping[str, str] = TAG_MODES) -> MwConfig:
    """MwConfig from a wiki's siteinfo "query" object (siprop general, namespaces,
    namespacealiases, magicwords, extensiontags, functionhooks, variables, protocols).

    Extension:CodeMirror reads this from the parser itself; siteinfo does not say which parser
    functions need a "#", so every function alias is accepted with and without one (slightly
    more permissive highlighting, never less). Aliases are lower-cased for case-insensitive
    magic words and lose a trailing ":", as in wikiparser-node's getParserConfig.
    """
    magic: Sequence[Mapping[str, Any]] = query.get("magicwords", ())
    hooks = [str(h).lower() for h in query.get("functionhooks", ())]
    variables = [str(v) for v in query.get("variables", ())]
    wanted = {*hooks, *variables, "msgnw", "msg", "raw", *_CASE_INSENSITIVE_SUBST}
    insensitive: dict[str, str] = {}
    sensitive: dict[str, str] = {}
    du_insensitive: dict[str, str] = {}
    du_sensitive: dict[str, str] = {}
    image_keywords: dict[str, str] = {}
    redirection: list[str] = ["#redirect"]
    for word in magic:
        name = str(word["name"])
        aliases = [str(a) for a in word.get("aliases", ())]
        case_sensitive = bool(word.get("case-sensitive", False))
        if name == "redirect":
            redirection = [a.lower() for a in aliases]
        if name.startswith("img_") and name != "img_lossy":
            key = name[4:].replace("_", "-")
            for a in aliases:
                if key != "alt" or "$1" in a:
                    image_keywords[a] = key
        if all(a.startswith("__") and a.endswith("__") and len(a) > 4 for a in aliases) and aliases:
            target = du_sensitive if case_sensitive else du_insensitive
            for a in aliases:
                target[a if case_sensitive else a.lower()] = name
            continue
        if name not in wanted:
            continue
        target = sensitive if case_sensitive else insensitive
        for a in aliases:
            key = a[:-1] if a.endswith(":") else a
            key = key if case_sensitive else key.lower()
            target.setdefault(key, name)
            if name in hooks and not key.startswith("#"):
                target.setdefault("#" + key, name)
    nsid: dict[str, int] = {}
    for ns in query.get("namespaces", {}).values():
        ns_id = int(ns["id"])
        for n in (ns.get("name", ""), ns.get("canonical", "")):
            if n or ns_id == 0:
                nsid[str(n).lower()] = ns_id
    for alias in query.get("namespacealiases", ()):
        nsid[str(alias["alias"]).lower()] = int(alias["id"])
    general: Mapping[str, Any] = query.get("general", {})
    variants = (
        [str(v["code"]) for v in general.get("variants", ())]
        if general.get("langconversion")
        else []
    )
    protocols = "|".join(regex.escape(str(p).lower()) for p in query.get("protocols", ()))
    return MwConfig(
        url_protocols=protocols or "//",
        tags={str(t).strip("<>"): True for t in query.get("extensiontags", ())},
        tag_modes=dict(modes),
        function_synonyms=(insensitive, sensitive),
        double_underscore=(du_insensitive, du_sensitive),
        nsid=nsid,
        variable_ids=[*dict.fromkeys([*variables, "="])],
        function_hooks=[*dict.fromkeys([*hooks, "msgnw"])],
        variants=bcp47_variants(variants),
        redirection=redirection,
        image_keywords=image_keywords,
    )


def default_config() -> MwConfig:
    """English Wikipedia's configuration, bundled (data/enwiki.json from wikiparser-node)."""
    import json
    from importlib.resources import files

    data = json.loads(files("pyawb.editor").joinpath("data/enwiki.json").read_text("utf-8"))
    return config_from_parser_data(data)
