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
# After AutoWikiBrowser WikiFunctions/Controls/Lists/ListMaker.cs (lbArticles_DrawItem).
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The list's "Format page titles per displaytitle": a page's displaytitle as the small piece of
rich text the list can show. AWB drew italics only and dropped sub/sup; this keeps italics, bold,
sub and sup, and drops every other tag."""

from __future__ import annotations

import html

from pyawb.core.rx import DotNetMatch, DotNetOptions, DotNetRegex

# a span positioned off screen hides text (AWB's SpanHide)
_SpanHide = DotNetRegex(
    r'< *span +style *= *" *position *: *absolute *; *top *: *-9999px;? *" *>.*?< */ *span *>'
)
_Tag = DotNetRegex(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
_KEEP = {"i": "i", "em": "i", "b": "b", "strong": "b", "sub": "sub", "sup": "sup"}
_Whitespace = DotNetRegex(r"\s+", DotNetOptions.NONE)


def display_title_html(display_title: str | None, name: str) -> str | None:
    """Qt rich text for the displaytitle, or None to show the plain page name (no displaytitle,
    or one that shows just the name)."""
    if not display_title:
        return None
    text = _Tag.replace(_SpanHide.replace(display_title, ""), _keep_tag)
    text = _Whitespace.replace(text, " ").strip()
    plain = html.unescape(_Tag.replace(text, ""))
    if not plain.strip() or (plain == name and "<" not in text):
        return None
    return text


def _keep_tag(m: DotNetMatch) -> str:
    kept = _KEEP.get(m.group(2).lower())
    return f"<{m.group(1)}{kept}>" if kept else ""
