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
"""The list maker (AWB's ListMaker control): a source, its input, and the page list."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyawb.core.article import Article
from pyawb.core.site import SiteConfig, current_site, use_site
from pyawb.lists import sources
from pyawb.lists.listmaker import ArticleList
from pyawb.lists.sources import Input, Source, WikiContext
from pyawb.lists.wikidataquery import EXAMPLE_QUERY, WikidataQueryListProvider
from pyawb.ui.tasks import run_task


class ListMaker(QWidget):
    """Make, show and edit the list of pages to work on."""

    status = Signal(str)  # messages for the status bar
    changed = Signal()  # the list changed

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.articles = ArticleList()
        self.wiki: WikiContext | None = None
        self.site: SiteConfig = current_site()
        self.busy = False

        self.source = QComboBox(self)
        for s in sources.SOURCES:
            self.source.addItem(s.name, s.name)
        self.source.setMaxVisibleItems(20)
        self.label = QLabel(self)

        self.line = QLineEdit(self)
        self.text = QPlainTextEdit(self)
        self.text.setObjectName("listInput")
        self.text.setTabChangesFocus(True)
        file_row = QWidget(self)
        self.file = QLineEdit(file_row)
        browse = QPushButton(self.tr("Browse…"), file_row)
        browse.clicked.connect(self._browse)
        fl = QHBoxLayout(file_row)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(self.file, 1)
        fl.addWidget(browse)
        self.inputs = QStackedWidget(self)
        self.inputs.addWidget(QWidget(self))  # Input.NONE
        self.inputs.addWidget(self.line)
        self.inputs.addWidget(self.text)
        self.inputs.addWidget(file_row)
        self._input_index = {Input.NONE: 0, Input.LINE: 1, Input.TEXT: 2, Input.FILE: 3}

        self.namespace = QComboBox(self)
        self.make = QPushButton(self.tr("Make list"), self)
        self.make.setProperty("primary", True)
        self.make.clicked.connect(self.make_list)
        self.line.returnPressed.connect(self.make_list)

        self.list = QListWidget(self)
        self.list.setObjectName("pageList")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.itemSelectionChanged.connect(self._sync_selection)
        self.count = QLabel(self)
        self.remove = QPushButton(self.tr("Remove"), self)
        self.remove.clicked.connect(self.remove_selected)
        self.clear = QPushButton(self.tr("Clear"), self)
        self.clear.clicked.connect(self.clear_list)
        self.dedupe = QPushButton(self.tr("Remove duplicates"), self)
        self.dedupe.clicked.connect(self.remove_duplicates)
        QShortcut(QKeySequence.StandardKey.Delete, self.list, self.remove_selected)

        top = QVBoxLayout(self)
        top.setContentsMargins(8, 8, 8, 8)
        top.addWidget(QLabel(self.tr("Source"), self))
        top.addWidget(self.source)
        top.addWidget(self.label)
        top.addWidget(self.inputs)
        ns_row = QHBoxLayout()
        ns_row.addWidget(self.namespace, 1)
        ns_row.addWidget(self.make)
        top.addLayout(ns_row)
        top.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.count, 1)
        buttons.addWidget(self.dedupe)
        buttons.addWidget(self.remove)
        buttons.addWidget(self.clear)
        top.addLayout(buttons)

        self.source.currentIndexChanged.connect(self._source_changed)
        self._fill_namespaces()
        self._source_changed()
        self.refresh()

    # -- configuration ------------------------------------------------------------------------

    @property
    def current_source(self) -> Source:
        return sources.source(str(self.source.currentData()))

    def set_wiki(self, wiki: WikiContext | None, site: SiteConfig) -> None:
        """The connected wiki (None: offline; only manual and file lists)."""
        self.wiki, self.site = wiki, site
        rtl = Qt.LayoutDirection.RightToLeft if site.rtl else Qt.LayoutDirection.LeftToRight
        for w in (self.list, self.line, self.text):
            w.setLayoutDirection(rtl)
        self._fill_namespaces()
        self._source_changed()

    def _fill_namespaces(self) -> None:
        current = self.namespace.currentData()
        self.namespace.clear()
        self.namespace.addItem(self.tr("(Main)"), 0)
        for ns, name in sorted(self.site.namespaces.items()):
            if ns > 0:
                self.namespace.addItem(name.rstrip(":"), ns)
        index = self.namespace.findData(current if current is not None else 0)
        self.namespace.setCurrentIndex(max(index, 0))

    def _source_changed(self) -> None:
        src = self.current_source
        self.label.setText(self.tr(src.label) if src.label else "")
        self.label.setVisible(bool(src.label))
        self.inputs.setCurrentIndex(self._input_index[src.input])
        self.inputs.setVisible(src.input is not Input.NONE)
        self.text.setPlaceholderText(
            EXAMPLE_QUERY if src.provider is WikidataQueryListProvider else "Page one\nPage two"
        )
        self.text.setLayoutDirection(
            Qt.LayoutDirection.LeftToRight
            if src.provider is WikidataQueryListProvider
            else (
                Qt.LayoutDirection.RightToLeft if self.site.rtl else Qt.LayoutDirection.LeftToRight
            )
        )
        self.namespace.setVisible(src.takes_namespace)
        self.make.setText(
            self.tr("Add to list")
            if src.input is Input.TEXT and not src.needs_wiki
            else self.tr("Make list")
        )
        self._update_buttons()

    def _browse(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, self.tr("Page list"), "", self.tr("Text files (*.txt);;All files (*)")
        )
        if name:
            self.file.setText(name)

    def input_text(self) -> str:
        src = self.current_source
        return {
            Input.NONE: "",
            Input.LINE: self.line.text(),
            Input.TEXT: self.text.toPlainText(),
            Input.FILE: self.file.text(),
        }[src.input]

    # -- making lists -------------------------------------------------------------------------

    def make_list(self) -> None:
        if self.busy:
            return
        src = self.current_source
        crit = sources.criteria(src, self.input_text())
        if not crit and src.input is not Input.NONE:
            self.status.emit(self.tr("Nothing to make a list from"))
            return
        ns = self.namespace.currentData() if src.takes_namespace else None
        try:
            provider = sources.build(src, self.wiki, ns)
        except sources.SourceUnavailable as e:
            self.status.emit(str(e))
            return
        site = self.site

        def work() -> list[Article]:
            with use_site(site):
                return provider.make_list(*crit)

        self._set_busy(True)
        self.status.emit(self.tr("Making list…"))
        run_task(work, self._list_made, self._list_failed)

    def _list_made(self, result: object) -> None:
        self._set_busy(False)
        new: list[Article] = result  # type: ignore[assignment]
        before = len(self.articles)
        with use_site(self.site):
            self.articles.add(new)
        if self.current_source.input is Input.TEXT and not self.current_source.needs_wiki:
            self.text.clear()  # the manual box has been added: ready for more
        self.refresh()
        self.status.emit(self.tr("%n page(s) added", "", len(self.articles) - before))

    def _list_failed(self, error: object) -> None:
        self._set_busy(False)
        self.status.emit(self.tr("Could not make the list: %1").replace("%1", str(error)))

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.make.setEnabled(not busy)
        self.source.setEnabled(not busy)

    # -- the list -----------------------------------------------------------------------------

    def refresh(self) -> None:
        """Show the model (after it changed)."""
        self.list.blockSignals(True)
        self.list.clear()
        self.list.addItems([a.name for a in self.articles])
        selected = self.articles.get_selected_article_list()
        if selected:
            i = self.articles.selected_index
            self.list.setCurrentRow(i)
            self.list.scrollToItem(self.list.item(i))
        self.list.blockSignals(False)
        self.count.setText(self.tr("%n page(s)", "", len(self.articles)))
        self._update_buttons()
        self.changed.emit()

    def _update_buttons(self) -> None:
        has = len(self.articles) > 0
        for b in (self.remove, self.clear, self.dedupe):
            b.setEnabled(has)

    def _sync_selection(self) -> None:
        rows = {i.row() for i in self.list.selectedIndexes()}
        for i in range(len(self.articles)):
            self.articles.set_selected(i, i in rows)

    def remove_selected(self) -> None:
        self._sync_selection()
        self.articles.remove_selected()
        self.refresh()

    def clear_list(self) -> None:
        self.articles.clear()
        self.refresh()

    def remove_duplicates(self) -> None:
        self.articles.remove_list_duplicates()
        self.refresh()

    # -- for the edit loop --------------------------------------------------------------------

    def selected_article(self) -> Article | None:
        article = self.articles.selected_article()
        self.refresh()
        return article

    def remove_article(self, article: Article | str) -> bool:
        removed = self.articles.remove(article)
        self.refresh()
        return removed

    def replace_article(self, old: Article | str, new: Article) -> None:
        if old in self.articles:
            self.articles.replace_article(old, new)
            self.refresh()

    def set_editable(self, editable: bool) -> None:
        """Lock the list while pages are being processed (the loop owns the selection)."""
        for w in (self.make, self.remove, self.clear, self.dedupe, self.source):
            w.setEnabled(editable)
        self.list.setEnabled(editable)
        if editable:
            self._update_buttons()
