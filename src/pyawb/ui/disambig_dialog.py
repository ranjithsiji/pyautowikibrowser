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
# After AutoWikiBrowser WikiFunctions/Disambiguation/DabForm.cs and DabControl.cs
# (GPL-2.0-or-later).
"""The disambiguation dialog: one row per link to the disambiguation page, with its paragraph,
the choice (no change, unlink, {{Disambiguation needed}}, a variant) and the editable result.
The work is rules.disambiguation's."""

from __future__ import annotations

import html
from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pyawb.rules import disambiguation as dab
from pyawb.ui import theme
from pyawb.ui.editor_dialogs import primary_button

ABORTED = 2  # dialog result: stop the whole run (AWB's Abort)


class DabRow(QFrame):
    """DabControl: one link."""

    changed = Signal()

    def __init__(self, link: dab.DabLink, variants: Sequence[str], parent: QWidget) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.link = link
        self.variants = list(variants)
        self.current = link.value
        self.viewer = QTextBrowser(self)
        self.viewer.setOpenLinks(False)
        self.viewer.setMaximumHeight(self.fontMetrics().lineSpacing() * 5 + 12)
        self.viewer.setHtml(self._paragraph_html())
        self.choice = QComboBox(self)
        self.choice.addItems(
            [self.tr("[no change]"), self.tr("[unlink]"), "{{Disambiguation needed}}", *variants]
        )
        self.correction = QLineEdit(link.value, self)
        self.reset_button = QPushButton(self.tr("Reset"), self)
        self.undo_button = QPushButton(self.tr("Undo"), self)
        self.unpipe_button = QPushButton(self.tr("Unpipe"), self)
        self.flip_button = QPushButton(self.tr("Flip"), self)
        self.choice.currentIndexChanged.connect(self._choose)
        self.correction.textChanged.connect(lambda _t: self.changed.emit())
        self.reset_button.clicked.connect(self.reset)
        self.undo_button.clicked.connect(self.undo)
        self.unpipe_button.clicked.connect(lambda: self._rewrite(dab.unpipe))
        self.flip_button.clicked.connect(lambda: self._rewrite(dab.flip))
        grid = QGridLayout(self)
        grid.addWidget(self.viewer, 0, 0, 1, 6)
        grid.addWidget(self.choice, 1, 0, 1, 2)
        grid.addWidget(self.correction, 2, 0, 1, 2)
        grid.addWidget(self.reset_button, 1, 2)
        grid.addWidget(self.undo_button, 1, 3)
        grid.addWidget(self.unpipe_button, 2, 2)
        grid.addWidget(self.flip_button, 2, 3)
        grid.setColumnStretch(1, 1)
        self._choose(0)

    def _paragraph_html(self) -> str:
        """The paragraph, the link in bold on a yellow background (AWB's FFD754)."""
        lk = self.link
        start = lk.index - lk.paragraph_start
        end = start + len(lk.value)
        p = lk.paragraph
        mark = theme.tokens(theme.Mode.SYSTEM)["background_color_warning_subtle"]
        return (
            html.escape(p[:start])
            + f'<b style="background-color:{mark}">'
            + html.escape(p[start:end])
            + "</b>"
            + html.escape(p[end:])
        )

    def _choose(self, n: int) -> None:
        self.current = self.link.choice(n, self.variants)
        self.correction.setText(self.current)
        has_pipe = "|" in self.current
        self.unpipe_button.setEnabled(has_pipe)
        self.flip_button.setEnabled(has_pipe)
        self.changed.emit()

    def _rewrite(self, how: Callable[[str], str]) -> None:
        new = how(self.current)
        self.correction.setText(self.correction.text().replace(self.current, new))
        self.current = new

    def reset(self) -> None:
        """Back to "no change"."""
        if self.choice.currentIndex() != 0:
            self.choice.setCurrentIndex(0)
        else:
            self._choose(0)

    def undo(self) -> None:
        """Undo hand edits: the result of the current choice again."""
        self._choose(self.choice.currentIndex())

    @property
    def can_save(self) -> bool:
        return bool(self.correction.text().strip())

    @property
    def no_change(self) -> bool:
        return self.choice.currentIndex() == 0 and self.correction.text() == self.link.value

    def result(self) -> str | None:
        return None if self.no_change else self.correction.text()


class DisambigDialog(QDialog):
    """DabForm: all the links on the page; Done applies the choices, Cancel leaves the page as
    it is, Abort stops the run."""

    def __init__(
        self,
        title: str,
        links: Sequence[dab.DabLink],
        variants: Sequence[str],
        *,
        open_page: Callable[[], object],
        edit_page: Callable[[], object],
        watch: Callable[[bool], object] | None = None,
        rtl: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Disambiguation") + " — " + title)
        self.rows: list[DabRow] = []
        holder = QWidget(self)
        rows = QVBoxLayout(holder)
        for link in links:
            row = DabRow(link, variants, holder)
            direction = Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
            for w in (row.viewer, row.correction, row.choice):
                w.setLayoutDirection(direction)
            row.changed.connect(self._update)
            self.rows.append(row)
            rows.addWidget(row)
        rows.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        self.done_button = QPushButton(self.tr("Done"), self)
        primary_button(self.done_button)
        self.done_button.clicked.connect(self.accept)
        cancel = QPushButton(self.tr("Cancel"), self)
        cancel.clicked.connect(self.reject)
        reset_all = QPushButton(self.tr("Reset all"), self)
        reset_all.clicked.connect(lambda: [r.reset() for r in self.rows])
        undo_all = QPushButton(self.tr("Undo all"), self)
        undo_all.clicked.connect(lambda: [r.undo() for r in self.rows])
        abort = QPushButton(self.tr("Abort"), self)
        abort.setToolTip(self.tr("Leave this page and stop the run"))
        abort.clicked.connect(lambda: self.done(ABORTED))
        page = QPushButton(self.tr("Page…"), self)
        menu = QMenu(page)
        menu.addAction(self.tr("Open in browser"), open_page)
        menu.addAction(self.tr("Edit in browser"), edit_page)
        if watch is not None:
            menu.addAction(self.tr("Watch with this account"), lambda: watch(False))
            menu.addAction(self.tr("Unwatch with this account"), lambda: watch(True))
        page.setMenu(menu)
        buttons = QHBoxLayout()
        for b in (page, reset_all, undo_all, abort):
            buttons.addWidget(b)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(self.done_button)
        top = QVBoxLayout(self)
        top.addWidget(scroll, 1)
        top.addLayout(buttons)
        self.resize(760, 560)
        if self.rows:
            self.rows[0].choice.setFocus(Qt.FocusReason.OtherFocusReason)
        self._update()

    def _update(self) -> None:
        self.done_button.setEnabled(all(r.can_save for r in self.rows))

    def results(self) -> list[str | None]:
        return [r.result() for r in self.rows]
