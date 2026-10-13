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
# Colours and rules ported from src/mediawiki.ts (wikiTheme), src/theme.ts and css/unused.css of
# @bhsd/codemirror-mediawiki 4.7.1 (GPL-2.0-or-later; pastakhov, Bhsd, 鬼影233 and others).
"""How each token class looks: the CSS of CodeMirror's MediaWiki theme as data.

style_for(classes) applies the theme's rules in their CSS order (all are single-class rules of the
same specificity, so a later rule wins for each property) and returns a TextStyle that the Qt
highlighter turns into a QTextCharFormat. Link underlines (shown on hover only) are left out.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache

type Rgba = tuple[int, int, int, int]

LIGHT: Mapping[str, str] = {
    "arg": "#b0c",
    "attr": "#179b1c",
    "comment": "#7b8c8f",
    "convert": "#b68",
    "entity": "#00a1a1",
    "error": "#d73333",
    "func": "#a11",
    "hr": "#0076dd",
    "hr-bg": "rgb(0,0,0,.07)",
    "link": "#000aaa",
    "sect": "#006fe6",
    "sp": "rgb(134,206,255,.3)",
    "table": "#d08",
    "table-attr": "#f500d4",
    "tag": "#14866d",
    "tpl": "#80c",
    "var-name": "#ac6600",
    "ref": "rgb(223,242,235,.5)",
}

DARK: Mapping[str, str] = {
    "arg": "#9f78a5",
    "attr": "#97b757",
    "comment": "#4c566a",
    "convert": "#b68",
    "entity": "#00a1a1",
    "error": "#bf616a",
    "func": "#bf616a",
    "hr": "#5e81ac",
    "hr-bg": "rgb(59,66,82,.5)",
    "link": "#5e81ac",
    "sect": "#81a1c1",
    "sp": "rgb(136,192,208,.5)",
    "table": "#b48ead",
    "table-attr": "#9f78a5",
    "tag": "#a3be8c",
    "tpl": "#9f78a5",
    "var-name": "#d08770",
    "ref": "rgb(60,90,80,.5)",
}


def parse_color(value: str) -> Rgba:
    """#rgb, #rrggbb or rgb(r,g,b,a) as (r, g, b, alpha 0-255)."""
    v = value.strip()
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255
    parts = [p.strip() for p in v[v.index("(") + 1 : v.rindex(")")].split(",")]
    alpha = round(float(parts[3]) * 255) if len(parts) > 3 else 255
    return int(parts[0]), int(parts[1]), int(parts[2]), alpha


@dataclass(frozen=True)
class TextStyle:
    color: Rgba | None = None  # None: the editor's text colour
    background: Rgba | None = None
    bold: bool = False
    italic: bool = False
    size: float = 1.0  # relative font size (level 1 and 2 headings)


# (classes without "mw-", properties). Values naming a palette entry are looked up per theme.
type _Props = Mapping[str, object]
_INHERIT = "inherit"
_RULES: Sequence[tuple[tuple[str, ...], _Props]] = (
    (("section--1",), {"size": 1.8}),
    (("section--2",), {"size": 1.5}),
    (("section--3", "section--4", "section--5", "section--6"), {"bold": True}),
    (
        (
            "section-header", "file-delimiter", "magic-link", "templatevariable",
            "link-pagename", "link-bracket", "link-delimiter", "extlink", "free-extlink",
            "exttag-bracket", "exttag-attribute", "htmltag-bracket", "htmltag-attribute",
            "table-delimiter2", "table-definition",
        ),
        {"bold": False},
    ),
    (
        (
            "redirect", "list", "free-extlink-protocol", "strong", "extlink-protocol",
            "extlink-bracket", "exttag-name", "htmltag-name", "table-bracket", "table-delimiter",
            "table-th", "table-caption", "convert-bracket", "convert-delimiter",
        ),
        {"bold": True},
    ),
    (("em",), {"italic": True}),
    # template and parser function arguments: neither bold nor italic
    (("template", "parserfunction"), {"bold": False, "italic": False, "color": _INHERIT}),
    (("section-header", "redirect", "list", "apostrophes"), {"color": "hr"}),
    (("error",), {"color": "error"}),
    (("skipformatting",), {"background": "sp"}),
    (
        ("double-underscore", "signature", "hr"),
        {"color": "hr", "bold": True, "background": "hr-bg"},
    ),
    (("comment", "ignored"), {"color": "comment", "bold": False}),
    (("template-name", "template-delimiter", "template-bracket"), {"color": "tpl", "bold": True}),
    (("template-argument-name", "parserfunction-argument-name"), {"color": "arg", "bold": False}),
    (
        ("templatevariable-name", "templatevariable-bracket", "templatevariable-delimiter"),
        {"color": "var-name", "bold": True},
    ),
    (
        ("parserfunction-name", "parserfunction-bracket", "parserfunction-delimiter"),
        {"color": "func", "bold": True},
    ),
    (
        (
            "link-pagename", "link-bracket", "link-delimiter", "file-delimiter", "magic-link",
            "extlink", "extlink-protocol", "extlink-bracket", "free-extlink",
            "free-extlink-protocol",
        ),
        {"color": "link"},
    ),
    (("image-parameter", "link-tosection"), {"color": "sect", "bold": False}),
    (
        (
            "exttag-name", "exttag-bracket", "exttag-attribute", "htmltag-name",
            "htmltag-bracket", "htmltag-attribute",
        ),
        {"color": "tag"},
    ),
    (("exttag-attribute-value", "htmltag-attribute-value"), {"color": "attr", "bold": False}),
    (
        ("table-bracket", "table-delimiter", "table-delimiter2", "table-definition"),
        {"color": "table"},
    ),
    (("table-definition-value",), {"color": "table-attr", "bold": False}),
    (
        ("convert-bracket", "convert-delimiter", "convert-flag", "convert-lang"),
        {"color": "convert"},
    ),
    (("entity",), {"color": "entity"}),
    (("exttag", "tag-score-scheme"), {"background": "rgb(119,0,170,.04)"}),
    # nesting backgrounds: (template, extension/parser function, link) depth
    (("template-ground",), {"background": "rgb(170,17,17,.04)"}),
    (("template2-ground",), {"background": "rgb(170,17,17,.08)"}),
    (("template3-ground",), {"background": "rgb(170,17,17,.12)"}),
    (("template-ext-ground", "ext-ground"), {"background": "rgb(119,0,170,.04)"}),
    (("template-ext2-ground", "ext2-ground"), {"background": "rgb(119,0,170,.08)"}),
    (("template-ext3-ground", "ext3-ground"), {"background": "rgb(119,0,170,.12)"}),
    (
        ("template-link-ground", "ext-link-ground", "link-ground"),
        {"background": "rgb(34,17,153,.04)"},
    ),
    (("template-ext-link-ground", "ext2-link-ground"), {"background": "rgb(77,9,162,.08)"}),
    (("template-ext2-link-ground", "ext3-link-ground"), {"background": "rgb(91,6,164,.12)"}),
    (("template-ext3-link-ground",), {"background": "rgb(98,4,166,.16)"}),
    (("template2-ext-ground",), {"background": "rgb(145,9,94,.08)"}),
    (("template2-ext2-ground",), {"background": "rgb(136,6,119,.12)"}),
    (("template2-ext3-ground",), {"background": "rgb(132,4,132,.16)"}),
    (("template2-link-ground",), {"background": "rgb(102,17,85,.08)"}),
    (("template2-ext-link-ground",), {"background": "rgb(108,11,113,.12)"}),
    (("template2-ext2-link-ground",), {"background": "rgb(111,9,128,.16)"}),
    (("template2-ext3-link-ground",), {"background": "rgb(112,7,136,.2)"}),
    (("template3-ext-ground",), {"background": "rgb(153,11,68,.12)"}),
    (("template3-ext2-ground",), {"background": "rgb(145,9,94,.16)"}),
    (("template3-ext3-ground",), {"background": "rgb(139,7,109,.2)"}),
    (("template3-link-ground",), {"background": "rgb(125,17,62,.12)"}),
    (("template3-ext-link-ground",), {"background": "rgb(123,13,89,.16)"}),
    (("template3-ext2-link-ground",), {"background": "rgb(122,10,105,.2)"}),
    (("template3-ext3-link-ground",), {"background": "rgb(122,9,116,.24)"}),
    (("tag-pre", "tag-nowiki"), {"background": "rgb(0,0,0,.04)"}),
    (("tag-ref",), {"background": "ref"}),
)  # fmt: skip

# Classes of the TeX and JSON modes (CodeMirror's default highlight style), light and dark.
_PLAIN_CLASSES: Mapping[str, tuple[str, str]] = {
    "keyword": ("#708", "#b48ead"),
    "atom": ("#219", "#81a1c1"),
    "number": ("#164", "#b48ead"),
    "string": ("#a11", "#a3be8c"),
    "variableName.special": ("#256", "#d08770"),
    "comment": ("#940", "#616e88"),
    "propertyName.definition": ("#00c", "#8fbcbb"),
    "invalid": ("#f00", "#bf616a"),
    "bool": ("#219", "#81a1c1"),
    "null": ("#708", "#81a1c1"),
    "operator": ("#708", "#81a1c1"),
}


def _value(value: object, palette: Mapping[str, str]) -> Rgba | None:
    if not isinstance(value, str):
        return None
    return parse_color(palette.get(value, value))


@lru_cache(maxsize=4096)
def style_for(classes: str, dark: bool = False) -> TextStyle:
    """The look of a token with these classes ("mw-template-ground mw-template-name ...")."""
    palette = DARK if dark else LIGHT
    names = {c.removeprefix("mw-") for c in classes.split()}
    color: Rgba | None = None
    background: Rgba | None = None
    bold = italic = False
    size = 1.0
    for selectors, props in _RULES:
        if names.isdisjoint(selectors):
            continue
        if "color" in props:
            color = None if props["color"] == _INHERIT else _value(props["color"], palette)
        if "background" in props:
            background = _value(props["background"], palette)
        if "bold" in props:
            bold = bool(props["bold"])
        if "italic" in props:
            italic = bool(props["italic"])
        if "size" in props:
            size = float(props["size"])  # pyright: ignore[reportArgumentType]
    for c in classes.split():
        plain = _PLAIN_CLASSES.get(c)
        if plain is not None:
            color = parse_color(plain[1 if dark else 0])
    return TextStyle(color, background, bold, italic, size)
