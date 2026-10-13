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
"""The diff pane at the top of the window (AWB's web control window)."""

from __future__ import annotations

import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTextBrowser, QWidget

from pyawb.editor.diffhtml import DiffColors, qt_diff_html, row_lines


class DiffView(QTextBrowser):
    """Shows the wiki's diff; a click on a line moves the editor there (line_clicked, 1-based),
    a double click undoes the changes on that line (line_double_clicked)."""

    line_clicked = Signal(int)
    line_double_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("diffView")
        self.setOpenLinks(False)
        self._lines: list[int | None] = []

    def show_diff(self, rows: str, colors: DiffColors, *, rtl: bool, hint: str, line_label: str,
                  no_difference: str) -> None:  # fmt: skip
        """The diff rows from action=compare, or the "No changes" page when they are empty."""
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        )
        if not rows.strip():
            self._lines = []
            self.setHtml(
                f'<html><body style="color:{colors.text}"><h2>{html.escape(no_difference)}</h2>'
                f"<hr><p>{html.escape(hint)}</p></body></html>"
            )
            return
        self._lines = row_lines(rows)
        page = qt_diff_html(rows, colors, rtl=rtl, line_label=line_label, no_difference="")
        self.setHtml(page)

    def show_message(self, title: str, text: str = "") -> None:
        self._lines = []
        body = f"<h2>{html.escape(title)}</h2>" + (f"<p>{html.escape(text)}</p>" if text else "")
        self.setHtml(f"<html><body>{body}</body></html>")

    def _line_at(self, e: QMouseEvent) -> int | None:
        if e.button() != Qt.MouseButton.LeftButton or not self._lines:
            return None
        cursor = self.cursorForPosition(e.position().toPoint())
        table = cursor.currentTable()
        if table is None:
            return None
        row = table.cellAt(cursor).row()
        return self._lines[row] if 0 <= row < len(self._lines) else None

    def mousePressEvent(self, e: QMouseEvent) -> None:
        super().mousePressEvent(e)
        line = self._line_at(e)
        if line is not None:
            self.line_clicked.emit(line)

    def mouseDoubleClickEvent(self, e: QMouseEvent) -> None:
        super().mouseDoubleClickEvent(e)
        line = self._line_at(e)
        if line is not None:
            self.line_double_clicked.emit(line)
