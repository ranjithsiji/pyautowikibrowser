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
# After AutoWikiBrowser AWB/Main.cs (tpHistory, tpLinks), WikiFunctions/Logging/
# ArticleActionLogControl.cs and WikiFunctions/Controls/TypoStatsControl.cs (GPL-2.0-or-later).
"""The edit tabs about the page: History, What links here, Page logs and Typos. AWB showed
history and links as web pages; here they are tables filled from the API."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from datetime import datetime

from PySide6.QtCore import QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyawb.api.pageinfo import Backlink, Revision
from pyawb.core import tools
from pyawb.core.site import SiteConfig, current_site, use_site
from pyawb.rules.typos import OverallTypoStats, TypoStat
from pyawb.ui import theme


def _table(parent: QWidget, headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers), parent)
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.verticalHeader().hide()
    header = t.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(True)
    t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    return t


def _fill(table: QTableWidget, rows: Iterable[Sequence[str]]) -> None:
    table.setRowCount(0)
    for values in rows:
        r = table.rowCount()
        table.insertRow(r)
        for c, v in enumerate(values):
            table.setItem(r, c, QTableWidgetItem(v))


def _selected_rows(table: QTableWidget) -> list[int]:
    return sorted({i.row() for i in table.selectedIndexes()})


def _open(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


def local_time(timestamp: str) -> str:
    """An API timestamp (UTC) in the computer's time zone, as the wiki shows it to readers."""
    try:
        when = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return timestamp
    return when.astimezone().strftime("%Y-%m-%d %H:%M")


class _PageTab(QWidget):
    """A tab about the page being edited, loaded on demand (when shown) for one title."""

    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.site: SiteConfig = current_site()
        self.title = ""  # the page shown
        self.label = QLabel(self)
        self.label.setObjectName("pageTabTitle")

    def needs(self, title: str) -> bool:
        """Whether title has to be loaded (another page, or nothing loaded yet)."""
        return bool(title) and title != self.title

    def show_message(self, text: str) -> None:
        self.label.setText(text)


class HistoryTab(_PageTab):
    """History: the page's latest revisions. Double click: that edit's diff in the browser."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = _table(
            self,
            [
                self.tr("Date"),
                self.tr("User"),
                self.tr("Size"),
                self.tr("Change"),
                "",
                self.tr("Summary"),
            ],
        )
        self.table.itemDoubleClicked.connect(lambda _i: self.open_diff())
        self.table.customContextMenuRequested.connect(self._menu)
        self.revisions: list[Revision] = []
        top = QVBoxLayout(self)
        top.setContentsMargins(6, 6, 6, 6)
        top.addWidget(self.label)
        top.addWidget(self.table, 1)

    def show_history(self, title: str, revisions: list[Revision]) -> None:
        self.title = title
        self.revisions = revisions
        self.label.setText(self.tr("History of %1").replace("%1", title))
        _fill(
            self.table,
            (
                (
                    local_time(r.timestamp),
                    r.user,
                    str(r.size),
                    "" if r.size_change is None else f"{r.size_change:+d}",
                    self.tr("m") if r.minor else "",
                    r.comment,
                )
                for r in revisions
            ),
        )
        for row, r in enumerate(revisions):
            change = self.table.item(row, 3)
            if change is not None and r.size_change:
                t = theme.tokens(theme.Mode.SYSTEM)
                change.setForeground(
                    QColor(t["color_success"] if r.size_change > 0 else t["color_error"])
                )

    def _menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction(self.tr("Open history in browser"), self.open_history)
        diff = menu.addAction(self.tr("Open diff in browser"), self.open_diff)
        diff.setEnabled(bool(_selected_rows(self.table)))
        menu.addAction(self.tr("Refresh history"), self.refresh_requested.emit)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def open_history(self) -> None:
        if self.title:
            with use_site(self.site):
                _open(tools.get_article_history_url(self.title))

    def open_diff(self) -> None:
        for row in _selected_rows(self.table):
            with use_site(self.site):
                _open(tools.get_diff_url(self.revisions[row].revid))


class LinksTab(_PageTab):
    """What links here: links, redirects and transclusions of the page."""

    add_to_list = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = _table(self, [self.tr("Page"), self.tr("Type")])
        self.table.itemDoubleClicked.connect(lambda _i: self.open_pages())
        self.table.customContextMenuRequested.connect(self._menu)
        self.links: list[Backlink] = []
        top = QVBoxLayout(self)
        top.setContentsMargins(6, 6, 6, 6)
        top.addWidget(self.label)
        top.addWidget(self.table, 1)

    def show_links(self, title: str, links: list[Backlink]) -> None:
        self.title = title
        self.links = links
        kinds = {
            "link": self.tr("link"),
            "redirect": self.tr("redirect"),
            "transclusion": self.tr("transclusion"),
        }
        self.label.setText(self.tr("%n page(s) link to %1", "", len(links)).replace("%1", title))
        _fill(self.table, ((b.title, kinds.get(b.kind, b.kind)) for b in links))

    def selected_titles(self) -> list[str]:
        return [self.links[r].title for r in _selected_rows(self.table)]

    def _menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        chosen = bool(_selected_rows(self.table))
        add = menu.addAction(
            self.tr("Add selected to page list"),
            lambda: self.add_to_list.emit(self.selected_titles()),
        )
        add.setEnabled(chosen)
        menu.addAction(
            self.tr("Add all to page list"),
            lambda: self.add_to_list.emit([b.title for b in self.links]),
        ).setEnabled(bool(self.links))
        menu.addSeparator()
        menu.addAction(self.tr("Open in browser"), self.open_pages).setEnabled(chosen)
        menu.addAction(self.tr("Refresh"), self.refresh_requested.emit)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def open_pages(self) -> None:
        with use_site(self.site):
            for title in self.selected_titles():
                _open(tools.non_prettified_url(title))


class PageLogsTab(QWidget):
    """Page logs: what PyAWB did to pages besides editing (move, protect, delete), successful
    and failed (ArticleActionLogControl)."""

    add_to_list = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        headers = [self.tr("Page"), self.tr("Action"), self.tr("Time"), self.tr("Message")]
        self.successful = _table(self, headers)
        self.failed = _table(self, headers)
        for t in (self.successful, self.failed):
            t.customContextMenuRequested.connect(lambda pos, table=t: self._menu(table, pos))
        top = QVBoxLayout(self)
        top.setContentsMargins(6, 6, 6, 6)
        top.addWidget(QLabel(self.tr("Successful:"), self))
        top.addWidget(self.successful, 1)
        top.addWidget(QLabel(self.tr("Failed:"), self))
        top.addWidget(self.failed, 1)

    def log_action(self, page: str, succeeded: bool, action: str, message: str = "") -> None:
        """LogArticleAction."""
        table = self.successful if succeeded else self.failed
        row = table.rowCount()
        table.insertRow(row)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for c, v in enumerate((page, action, now, message)):
            table.setItem(row, c, QTableWidgetItem(v))

    @staticmethod
    def pages(table: QTableWidget, rows: Iterable[int] | None = None) -> list[str]:
        chosen = range(table.rowCount()) if rows is None else rows
        out: list[str] = []
        for r in chosen:
            item = table.item(r, 0)
            if item is not None:
                out.append(item.text())
        return out

    def _menu(self, table: QTableWidget, pos: QPoint) -> None:
        menu = QMenu(self)
        rows = _selected_rows(table)
        menu.addAction(
            self.tr("Add selected to page list"),
            lambda: self.add_to_list.emit(self.pages(table, rows)),
        ).setEnabled(bool(rows))
        menu.addAction(
            self.tr("Copy"),
            lambda: QApplication.clipboard().setText("\n".join(self.pages(table, rows))),
        ).setEnabled(bool(rows))
        menu.addSeparator()
        menu.addAction(self.tr("Clear"), lambda: table.setRowCount(0))
        menu.exec(table.viewport().mapToGlobal(pos))


class _TypoTable(QTableWidget):
    def __init__(self, parent: QWidget, overall: bool) -> None:
        super().__init__(0, 4, parent)
        self.overall = overall
        self.setHorizontalHeaderLabels(
            [self.tr("Find"), self.tr("Replace"), self.tr("Total"), self.tr("No changes")]
        )
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().hide()
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stats: list[TypoStat] = []

    def show_stats(self, stats: Iterable[TypoStat]) -> None:
        """A rule whose every match changed nothing is yellow (TypoStatsListViewItem)."""
        self.stats = list(stats)
        _fill(
            self,
            ((s.find, s.replace, str(s.total), str(s.self_matches)) for s in self.stats),
        )
        yellow = QColor(theme.tokens(theme.Mode.SYSTEM)["background_color_warning_subtle"])
        for row, s in enumerate(self.stats):
            if s.total and s.total == s.self_matches:
                for c in range(4):
                    item = self.item(row, c)
                    if item is not None:
                        item.setBackground(yellow)

    def selected(self) -> TypoStat | None:
        rows = _selected_rows(self)
        return self.stats[rows[0]] if rows else None


class TyposTab(QWidget):
    """Typos: the rules that matched on this page, and overall (with totals per save)."""

    test_regex = Signal(str, str)  # find, replace

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.overall_stats = OverallTypoStats()
        self.current = _TypoTable(self, overall=False)
        self.overall = _TypoTable(self, overall=True)
        for t in (self.current, self.overall):
            t.customContextMenuRequested.connect(lambda pos, table=t: self._menu(table, pos))
        self.total = QLabel("0", self)
        self.no_change = QLabel("0", self)
        self.ratio = QLabel("0", self)
        counts = QGridLayout()
        for col, (label, value) in enumerate(
            (
                (self.tr("Total:"), self.total),
                (self.tr("No change:"), self.no_change),
                (self.tr("Typos/save:"), self.ratio),
            )
        ):
            counts.addWidget(QLabel(label, self), 0, col * 2)
            counts.addWidget(value, 0, col * 2 + 1)
        counts.setColumnStretch(6, 1)
        top = QVBoxLayout(self)
        top.setContentsMargins(6, 6, 6, 6)
        top.addWidget(QLabel(self.tr("On this page:"), self))
        top.addWidget(self.current, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Overall:"), self))
        row.addStretch(1)
        top.addLayout(row)
        top.addWidget(self.overall, 2)
        top.addLayout(counts)

    def page_stats(self, stats: list[TypoStat] | None) -> None:
        """UpdateCurrentTypoStats."""
        self.current.show_stats(stats or [])

    def add_overall(self, stats: list[TypoStat] | None, skipped: bool) -> None:
        """UpdateOverallTypoStats after a save, or after an automatic skip."""
        if stats is None:
            return
        self.overall_stats.update(stats, skipped)
        self._show_overall()

    def clear(self) -> None:
        """ResetTypoStats."""
        self.overall_stats.clear()
        self.current.show_stats([])
        self._show_overall()

    def _show_overall(self) -> None:
        o = self.overall_stats
        self.overall.show_stats(o.data.values())
        self.total.setText(str(o.total_typos))
        self.no_change.setText(str(o.self_matches))
        self.ratio.setText(o.typos_per_save)

    def _menu(self, table: _TypoTable, pos: QPoint) -> None:
        typo = table.selected()
        menu = QMenu(self)

        def act(text: str, slot: Callable[[], object], enabled: bool = True) -> None:
            menu.addAction(text, slot).setEnabled(enabled)

        act(
            self.tr("Copy Find part"),
            lambda: QApplication.clipboard().setText(typo.find if typo else ""),
            typo is not None,
        )
        act(
            self.tr("Copy Replace part"),
            lambda: QApplication.clipboard().setText(typo.replace if typo else ""),
            typo is not None,
        )
        act(
            self.tr("Test regex…"),
            lambda: self.test_regex.emit(typo.find, typo.replace) if typo else None,
            typo is not None,
        )
        if table.overall:
            menu.addSeparator()
            act(self.tr("Clear statistics"), self.clear)
            act(self.tr("Save log"), self.save_log, self.overall_stats.saves > 0)
        menu.exec(table.viewport().mapToGlobal(pos))

    def save_log(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save log"), "", self.tr("Text files (*.txt);;All files (*)")
        )
        if name:
            with open(name, "w", encoding="utf-8") as f:
                f.write(self.overall_stats.log_text())
