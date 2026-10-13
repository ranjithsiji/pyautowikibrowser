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
"""The wiki's diff (action=compare, wikidiff2 table rows) as HTML that Qt's rich text can show.

Qt's text engine knows no <del>/<ins>, data-marker or most CSS selectors, so the rows are rebuilt
with inline styles: MediaWiki's diff colours (Codex's content-added/removed tokens) and markers.
The text inside the cells is kept as the wiki sent it (already HTML-escaped).
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from html.parser import HTMLParser

import regex


@dataclass(frozen=True)
class DiffColors:
    """Codex tokens: background_color_content_added/removed, background_color_neutral_subtle,
    border_color_content_added/removed, color_base, color_subtle."""

    added: str = "#a3d3ff"
    removed: str = "#ffe49c"
    added_border: str = "#a3d3ff"
    removed_border: str = "#ffe49c"
    context: str = "#f8f9fa"
    text: str = "#202122"
    subtle: str = "#54595d"


_LINE_COMMENT = regex.compile(r"<!--\s*LINE\s+(\d+)\s*-->")
_MARKERS = {"diff-addedline": "+", "diff-deletedline": "−"}
_VOID = {"br", "img", "hr", "wbr"}


class _Rewriter(HTMLParser):
    def __init__(self, colors: DiffColors, line_label: str, rtl: bool) -> None:
        super().__init__(convert_charrefs=False)
        self.c, self.line_label, self.rtl = colors, line_label, rtl
        self.side = "right" if rtl else "left"  # the change bar, next to the marker
        self.out: list[str] = []
        self.stack: list[str] = []  # the tag written for each open element
        self.row_class = ""  # the class of the current changed cell, for inline changes
        self.row_start = 0  # index in out after <tr>
        self.cells: list[tuple[int, int]] = []  # (start, end) in out of each cell of the row
        self.cell_start = 0

    def _style_td(self, classes: set[str], attrs: dict[str, str | None]) -> str:
        c = self.c
        colspan = f' colspan="{attrs["colspan"]}"' if attrs.get("colspan") else ""
        if "diff-lineno" in classes:
            return f'<td{colspan} style="color:{c.subtle}; font-weight:bold; padding-top:8px">'
        if "diff-marker" in classes:
            marker = html.escape(attrs.get("data-marker") or "")
            self.out.append(f'<td width="1%" align="{self.side}" style="color:{c.subtle}">{marker}')
            return ""
        if "diff-addedline" in classes:
            self.row_class = "diff-addedline"
            return (
                f'<td width="49%"{colspan} style="background-color:{c.context};'
                f' border-{self.side}:4px solid {c.added_border}; color:{c.text}">'
            )
        if "diff-deletedline" in classes:
            self.row_class = "diff-deletedline"
            return (
                f'<td width="49%"{colspan} style="background-color:{c.context};'
                f' border-{self.side}:4px solid {c.removed_border}; color:{c.text}">'
            )
        if "diff-context" in classes:
            return (
                f'<td width="49%"{colspan} style="background-color:{c.context}; color:{c.subtle}">'
            )
        if "diff-empty" in classes or attrs.get("colspan"):
            return f"<td{colspan}>"
        return f'<td width="1%" align="{self.side}">'

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        written = tag
        if tag == "td":
            self.cell_start = len(self.out)
            start = self._style_td(classes, a)
            if start:
                self.out.append(start)
        elif tag in ("del", "ins") or "diffchange" in classes:
            color = (
                self.c.added
                if tag == "ins" or self.row_class == "diff-addedline"
                else (self.c.removed)
            )
            self.out.append(f'<span style="background-color:{color}; font-weight:bold">')
            written = "span"
        elif tag == "tr":
            self.row_class = ""
            self.out.append("<tr>")
            self.row_start, self.cells = len(self.out), []
        elif tag in ("div", "span", "a", "strong", "b", "i", "em", "br", "sup", "sub"):
            if tag == "a":
                written = "span"  # moved-paragraph anchors: no links in the diff
            self.out.append(f"<{written}>")
        else:
            written = ""
        if tag not in _VOID:
            self.stack.append(written)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID or not self.stack:
            return
        written = self.stack.pop()
        if written == "tr" and self.rtl:
            # Qt's tables ignore dir="rtl": mirror the row by writing its cells in reverse
            cells = [self.out[a:b] for a, b in self.cells]
            self.out[self.row_start :] = [part for cell in reversed(cells) for part in cell]
        if written:
            self.out.append(f"</{written}>")
        if written == "td":
            self.cells.append((self.cell_start, len(self.out)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.out.append("<br>")

    def handle_data(self, data: str) -> None:
        self.out.append(data)

    def handle_entityref(self, name: str) -> None:
        self.out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.out.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        m = _LINE_COMMENT.fullmatch(f"<!--{data}-->")
        if m:
            self.out.append(html.escape(self.line_label.replace("$1", m.group(1))))


def qt_diff_html(
    rows: str,
    colors: DiffColors | None = None,
    *,
    rtl: bool = False,
    line_label: str = "Line $1:",
    no_difference: str = "No difference",
) -> str:
    """A whole HTML document for QTextBrowser from action=compare's diff rows. rtl: the wiki's
    direction (the diff of an RTL wiki reads right to left, as on the wiki)."""
    c = colors or DiffColors()
    direction = "rtl" if rtl else "ltr"
    if not rows.strip():
        body = f'<p style="color:{c.subtle}">{html.escape(no_difference)}</p>'
    else:
        parser = _Rewriter(c, line_label, rtl)
        parser.feed(rows)
        parser.close()
        body = (
            '<table width="100%" cellspacing="2" cellpadding="4">'
            + "".join(parser.out)
            + "</table>"
        )
    return f'<html><body dir="{direction}" style="color:{c.text}">{body}</body></html>'


class _RowScanner(HTMLParser):
    """Per <tr>: the classes of its cells, the right-hand "Line N:" number, if any."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[list[set[str]], int | None]] = []
        self._cells: list[set[str]] = []
        self._line: int | None = None
        self._in_lineno = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._cells, self._line = [], None
        elif tag == "td":
            classes = set((dict(attrs).get("class") or "").split())
            self._cells.append(classes)
            self._in_lineno = "diff-lineno" in classes

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr":
            self.rows.append((self._cells, self._line))
        elif tag == "td":
            self._in_lineno = False

    def _number(self, text: str) -> None:
        m = regex.search(r"\d+", text)
        if m:
            self._line = int(m.group())  # the last one in the row is the new text's

    def handle_data(self, data: str) -> None:
        if self._in_lineno:
            self._number(data)

    def handle_comment(self, data: str) -> None:
        m = _LINE_COMMENT.fullmatch(f"<!--{data}-->")
        if m:
            self._number(m.group(1))


def row_lines(rows: str) -> list[int | None]:
    """For each table row of action=compare's diff, the 1-based line of the new text it shows (a
    deleted line: where it was), or None for "Line N:" headers. Lets a click on the diff move the
    editor to that line, as AWB and JWB do."""
    scanner = _RowScanner()
    scanner.feed(rows)
    scanner.close()
    out: list[int | None] = []
    next_line = 1
    for cells, line in scanner.rows:
        if line is not None:
            next_line = line
            out.append(None)
            continue
        right = cells[-1] if cells else set()
        out.append(next_line)
        if right & {"diff-addedline", "diff-context"}:
            next_line += 1
    return out
