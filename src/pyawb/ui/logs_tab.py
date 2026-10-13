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
# After AutoWikiBrowser WikiFunctions/Logging/LogControl.cs (GPL-2.0-or-later).
"""AWB's Logs tab: pages saved and pages skipped (by whom and why), newest first, with the
context menu of AWB's LogControl."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyawb.core import tools
from pyawb.core.site import SiteConfig, current_site, use_site

REVISION_ROLE = Qt.ItemDataRole.UserRole  # on the page cell of saved rows: the new revision id


class _LogTable(QWidget):
    add_to_list = Signal(list)

    def __init__(
        self, caption: str, headers: list[str], parent: QWidget, *, skipped: bool = False
    ) -> None:
        super().__init__(parent)
        self.caption = caption
        self.is_skipped = skipped
        self.site: SiteConfig = current_site()
        self.filtered: list[list[str]] = []  # rows hidden by Filter (Reset brings them back)
        self.label = QLabel(self)
        self.table = QTableWidget(0, len(headers), self)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.itemDoubleClicked.connect(lambda _item: self.open_pages())
        self.save_button = QPushButton(self.tr("Save log"), self)
        self.save_button.clicked.connect(self.save)
        self.add_button = QPushButton(self.tr("Add all to list"), self)
        self.add_button.clicked.connect(lambda: self.add_to_list.emit(self.pages()))
        self.clear_button = QPushButton(self.tr("Clear"), self)
        self.clear_button.clicked.connect(self.clear)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.add_button)
        buttons.addStretch(1)
        buttons.addWidget(self.clear_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        self._make_actions()
        self._update_label()

    # -- rows ---------------------------------------------------------------------------------

    def add(self, *values: str, revision: int = 0) -> None:
        """A new entry, at the top (AWB sorts the logs newest first)."""
        self.table.insertRow(0)
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col == 0:
                item.setToolTip(value)
                if revision:
                    item.setData(REVISION_ROLE, revision)
            self.table.setItem(0, col, item)
        self.table.scrollToTop()
        self._update_label()

    def rows(self) -> list[list[str]]:
        out: list[list[str]] = []
        for r in range(self.table.rowCount()):
            cells = [self.table.item(r, c) for c in range(self.table.columnCount())]
            out.append([c.text() if c is not None else "" for c in cells])
        return out

    def pages(self) -> list[str]:
        return [row[0] for row in self.rows()]

    def selected_rows(self) -> list[int]:
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def selected_pages(self) -> list[str]:
        rows = self.rows()
        return [rows[r][0] for r in self.selected_rows()]

    def clear(self) -> None:
        self.table.setRowCount(0)
        self.filtered.clear()
        self._update_label()

    def save(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save log"), "", self.tr("Text files (*.txt);;All files (*)")
        )
        if name:
            lines = ["\t".join(row) for row in self.rows()]
            with open(name, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

    def _update_label(self) -> None:
        self.label.setText(f"{self.caption} {self.table.rowCount()}")
        has = self.table.rowCount() > 0
        for b in (self.save_button, self.add_button, self.clear_button):
            b.setEnabled(has)

    # -- context menu (LogControl.mnuListView) ------------------------------------------------

    def _make_actions(self) -> None:
        def action(text: str, slot: Callable[[], object], key: str = "") -> QAction:
            a = QAction(text, self.table)
            a.triggered.connect(lambda _=False: slot())
            if key:
                a.setShortcut(QKeySequence(key))
                a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.table.addAction(a)
            return a

        self.add_selected_action = action(
            self.tr("Add selected to page list"),
            lambda: self.add_to_list.emit(self.selected_pages()),
        )
        self.cut_action = action(self.tr("Cut"), self.cut, "Ctrl+X")
        self.copy_action = action(self.tr("Copy"), self.copy, "Ctrl+C")
        self.remove_action = action(self.tr("Remove"), self.remove_selected)
        self.select_all_action = action(self.tr("Select all"), self.table.selectAll, "Ctrl+A")
        self.select_none_action = action(self.tr("Select none"), self.table.clearSelection)
        self.open_action = action(self.tr("Open in browser"), self.open_pages, "Ctrl+Shift+P")
        self.history_action = action(
            self.tr("Open history in browser"), self.open_histories, "Ctrl+Shift+H"
        )
        self.diff_action = action(self.tr("Open diff in browser"), self.open_diffs, "Ctrl+Shift+D")
        self.filter_only_action = action("", lambda: self.filter_reason(keep=True))
        self.filter_exclude_action = action("", lambda: self.filter_reason(keep=False))
        self.clear_action = action(self.tr("Clear"), self.clear)
        self.reset_action = action(self.tr("Reset"), self.reset)

    def _context_menu(self, pos: QPoint) -> None:
        self.context_menu().exec(self.table.viewport().mapToGlobal(pos))

    def context_menu(self) -> QMenu:
        """Enabled as in AWB's mnuListView_Opening."""
        menu = QMenu(self)
        chosen = self.selected_rows()
        has_rows = self.table.rowCount() > 0
        menu.addAction(self.add_selected_action)
        menu.addSeparator()
        menu.addActions([self.cut_action, self.copy_action])
        menu.addSeparator()
        menu.addAction(self.remove_action)
        menu.addSeparator()
        menu.addActions([self.select_all_action, self.select_none_action])
        menu.addSeparator()
        menu.addActions([self.open_action, self.history_action, self.diff_action])
        reason = self.rows()[chosen[0]][3] if self.is_skipped and len(chosen) == 1 else None
        if reason is not None:
            menu.addSeparator()
            self.filter_only_action.setText(
                self.tr("Filter by skip reason: %1").replace("%1", reason)
            )
            self.filter_exclude_action.setText(
                self.tr("Filter exclude skip reason: %1").replace("%1", reason)
            )
            menu.addActions([self.filter_only_action, self.filter_exclude_action])
        menu.addSeparator()
        menu.addActions([self.clear_action, self.reset_action])
        for a in (
            self.add_selected_action,
            self.cut_action,
            self.copy_action,
            self.remove_action,
            self.open_action,
            self.history_action,
        ):
            a.setEnabled(bool(chosen))
        self.diff_action.setEnabled(bool(chosen) and not self.is_skipped)
        for a in (self.select_all_action, self.select_none_action, self.clear_action):
            a.setEnabled(has_rows)
        self.reset_action.setEnabled(bool(self.filtered))
        return menu

    def copy(self) -> None:
        text = "\n".join(self.selected_pages()).strip()
        if text:
            QApplication.clipboard().setText(text)

    def cut(self) -> None:
        self.copy()
        self.remove_selected()

    def remove_selected(self) -> None:
        for r in reversed(self.selected_rows()):
            self.table.removeRow(r)
        self._update_label()

    def _open(self, urls: list[str]) -> None:
        for url in urls:
            QDesktopServices.openUrl(QUrl(url))

    def open_pages(self) -> None:
        with use_site(self.site):
            self._open([tools.non_prettified_url(p) for p in self.selected_pages()])

    def open_histories(self) -> None:
        with use_site(self.site):
            self._open([tools.get_article_history_url(p) for p in self.selected_pages()])

    def open_diffs(self) -> None:
        """Saved edits only: the diff each save made (index.php?diff=newid)."""
        revisions = []
        for r in self.selected_rows():
            item = self.table.item(r, 0)
            revision = item.data(REVISION_ROLE) if item is not None else None
            if revision:
                revisions.append(int(revision))
        with use_site(self.site):
            self._open([tools.get_diff_url(rev) for rev in revisions])

    def filter_reason(self, keep: bool) -> None:
        """Skipped log: show only that skip reason, or hide it (case-insensitive, as AWB)."""
        chosen = self.selected_rows()
        if not self.is_skipped or len(chosen) != 1:
            return
        rows = self.rows()
        reason = rows[chosen[0]][3].lower()
        for r in reversed(range(len(rows))):
            matches = rows[r][3].lower() == reason
            if matches != keep:
                self.filtered.append(rows[r])
                self.table.removeRow(r)
        self._update_label()

    def reset(self) -> None:
        """Bring back the rows a filter hid."""
        for row in reversed(self.filtered):
            r = self.table.rowCount()
            self.table.insertRow(r)
            for col, value in enumerate(row):
                self.table.setItem(r, col, QTableWidgetItem(value))
        self.filtered.clear()
        self._update_label()


class LogsTab(QWidget):
    add_to_list = Signal(list)  # page titles

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.saved = _LogTable(
            self.tr("Successfully saved:"), [self.tr("Page"), self.tr("Time")], self
        )
        self.skipped = _LogTable(
            self.tr("Skipped:"),
            [self.tr("Page"), self.tr("Time"), self.tr("Skipped by"), self.tr("Skip reason")],
            self,
            skipped=True,
        )
        for t in (self.saved, self.skipped):
            t.add_to_list.connect(self.add_to_list)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.saved, 1)
        layout.addWidget(self.skipped, 1)

    def set_site(self, site: SiteConfig) -> None:
        """The wiki the pages are on (for the browser links)."""
        self.saved.site = self.skipped.site = site

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_saved(self, page: str, revision: int = 0) -> None:
        self.saved.add(page, self._now(), revision=revision)

    def log_skipped(self, page: str, by: str, reason: str) -> None:
        self.skipped.add(page, self._now(), by, reason)
