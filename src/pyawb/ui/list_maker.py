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
"""The list maker (AWB's ListMaker control): a source, its input, the page list and its
context menu. The List menu of the main window uses the same actions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QPersistentModelIndex,
    QPoint,
    QRectF,
    QSize,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAbstractTextDocumentLayout,
    QAction,
    QColor,
    QDesktopServices,
    QIcon,
    QKeySequence,
    QPainter,
    QPalette,
    QShortcut,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyawb.api.pageinfo import display_titles
from pyawb.core import tools
from pyawb.core.article import Article
from pyawb.core.site import SiteConfig, current_site, use_site
from pyawb.lists import providers, sources
from pyawb.lists.displaytitle import display_title_html
from pyawb.lists.listfilter import ListFilter
from pyawb.lists.listmaker import SAVE_FILTERS, ArticleList, OutputFormat, save_list
from pyawb.lists.sources import Input, Source, WikiContext
from pyawb.lists.wikidataquery import EXAMPLE_QUERY, WikidataQueryListProvider
from pyawb.ui import theme
from pyawb.ui.icons import codex_icon
from pyawb.ui.list_dialogs import AdvancedScraperDialog, ListFilterDialog
from pyawb.ui.tasks import run_task

RICH_ROLE = Qt.ItemDataRole.UserRole + 1  # displaytitle rich text for the delegate
BROWSER_WARNING = 10  # AWB asks before opening this many pages at once
CLEAR_WARNING = 100  # AWB asks before clearing a list this long


class RichTextDelegate(QStyledItemDelegate):
    """Draws an item's RICH_ROLE text as rich text (displaytitle italics, bold, sub, sup)."""

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> None:
        rich = index.data(RICH_ROLE)
        if not rich:
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        doc = self._document(str(rich), opt)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        text_rect = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
        painter.save()
        painter.translate(text_rect.topLeft())
        painter.setClipRect(text_rect.translated(-text_rect.topLeft()))
        ctx = QAbstractTextDocumentLayout.PaintContext()
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        ctx.palette.setColor(
            QPalette.ColorRole.Text,
            opt.palette.color(
                QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
            ),
        )
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(
        self, option: QStyleOptionViewItem, index: QModelIndex | QPersistentModelIndex
    ) -> QSize:
        size = super().sizeHint(option, index)
        rich = index.data(RICH_ROLE)
        if rich:
            doc = self._document(str(rich), option)
            size.setWidth(max(size.width(), int(doc.idealWidth()) + 8))
        return size

    @staticmethod
    def _document(rich: str, option: QStyleOptionViewItem) -> QTextDocument:
        doc = QTextDocument()
        doc.setDocumentMargin(0)
        doc.setDefaultFont(option.font)
        doc.setHtml(rich)
        doc.setTextWidth(QRectF(option.rect).width() or -1)
        return doc


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
        # one input shown at a time, each at its own height (a QStackedWidget would give the
        # single-line field the height of the multi-line box)
        self._inputs: dict[Input, QWidget] = {
            Input.LINE: self.line,
            Input.TEXT: self.text,
            Input.FILE: file_row,
        }
        # several values: a scrolling box of about eight lines, so the list keeps its room
        line_height = self.text.fontMetrics().lineSpacing()
        self.text.setFixedHeight(line_height * 8 + 12)

        self.namespace = QComboBox(self)
        # a number some sources need (recursion levels, number of contributions)
        self.option_label = QLabel(self)
        self.option = QSpinBox(self)
        self.make = QPushButton(self.tr("Make list"), self)
        self.make.setProperty("primary", True)
        self.make.clicked.connect(self.make_list)
        self.line.returnPressed.connect(self.make_list)
        self.stop_button = QPushButton(codex_icon("stop"), self.tr("Stop"), self)
        self.stop_button.setToolTip(self.tr("Stop making the list"))
        self.stop_button.clicked.connect(self.stop)
        self.stop_button.hide()
        self._generation = 0  # making a list again or stopping makes older results stale
        self.scraper_settings: dict[str, object] = {}
        self.list_filter = ListFilter()
        self._last_save: tuple[str, OutputFormat] = ("", OutputFormat.WIKI_TEXT)

        # AWB's text box with "+": add one page
        self.add_line = QLineEdit(self)
        self.add_line.setPlaceholderText(self.tr("Add a page"))
        self.add_button = QToolButton(self)
        self.add_button.setIcon(codex_icon("add"))
        self.add_button.setToolTip(self.tr("Add this page to the list"))
        self.add_button.clicked.connect(self.add_typed_page)
        self.add_line.returnPressed.connect(self.add_typed_page)
        self.add_line.textChanged.connect(lambda t: self.add_button.setEnabled(bool(t.strip())))
        self.add_button.setEnabled(False)

        self.list = QListWidget(self)
        self.list.setObjectName("pageList")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setItemDelegate(RichTextDelegate(self.list))
        self.list.itemSelectionChanged.connect(self._sync_selection)
        self.list.itemDoubleClicked.connect(lambda _item: self.open_in_browser())
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.count = QLabel(self)
        self.remove = QPushButton(self.tr("Remove"), self)
        self.remove.clicked.connect(self.remove_selected)
        self.filter_button = QPushButton(self.tr("Filter"), self)
        self.filter_button.clicked.connect(self.filter)
        QShortcut(QKeySequence.StandardKey.Delete, self.list, self.remove_selected)
        self._make_actions()

        top = QVBoxLayout(self)
        top.setContentsMargins(8, 8, 8, 8)
        top.addWidget(QLabel(self.tr("Source"), self))
        top.addWidget(self.source)
        top.addWidget(self.label)
        for widget in self._inputs.values():
            top.addWidget(widget)
        ns_row = QHBoxLayout()
        ns_row.addWidget(self.namespace, 1)
        ns_row.addWidget(self.option_label)
        ns_row.addWidget(self.option)
        ns_row.addWidget(self.make)
        ns_row.addWidget(self.stop_button)
        top.addLayout(ns_row)
        add_row = QHBoxLayout()
        add_row.addWidget(self.add_line, 1)
        add_row.addWidget(self.add_button)
        top.addLayout(add_row)
        top.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.count, 1)
        buttons.addWidget(self.remove)
        buttons.addWidget(self.filter_button)
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
        for kind, widget in self._inputs.items():
            widget.setVisible(kind is src.input)
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
        opt = src.option
        self.option_label.setVisible(opt is not None)
        self.option.setVisible(opt is not None)
        if opt is not None:
            self.option_label.setText(self.tr(opt.label))
            self.option.setRange(opt.minimum, opt.maximum)
            self.option.setValue(opt.default)
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
        settings: dict[str, object] = {}
        if src.provider is providers.AdvancedRegexHtmlScraper:
            dialog = AdvancedScraperDialog(self.scraper_settings, self)
            if dialog.exec() != AdvancedScraperDialog.DialogCode.Accepted:
                return
            self.scraper_settings = settings = dialog.value()
        ns = self.namespace.currentData() if src.takes_namespace else None
        option = self.option.value() if src.option is not None else None
        self._run_provider(src, crit, ns, option, settings)

    def add_selected_from(self, src: Source) -> None:
        """Context menu "Add selected to list from ▸": make a list from the selected pages."""
        chosen = [a.name for a in self.selected_articles()]
        if chosen and not self.busy:
            self._run_provider(src, chosen, None, None, {})

    def _run_provider(
        self,
        src: Source,
        crit: Sequence[str],
        ns: int | None,
        option: int | None,
        settings: dict[str, object],
    ) -> None:
        try:
            provider = sources.build(src, self.wiki, ns, option, settings)
        except sources.SourceUnavailable as e:
            self.status.emit(str(e))
            return
        site = self.site

        def work() -> list[Article]:
            with use_site(site):
                return provider.make_list(*crit)

        self._generation += 1
        generation = self._generation
        self._set_busy(True)
        self.status.emit(self.tr("Making list…"))
        run_task(
            work,
            lambda r: self._list_made(r, generation),
            lambda e: self._list_failed(e, generation),
        )

    def stop(self) -> None:
        """Stop making the list (AWB aborted the thread; here the result is thrown away when it
        comes)."""
        if self.busy:
            self._generation += 1
            self._set_busy(False)
            self.status.emit(self.tr("Stopped"))

    def _list_made(self, result: object, generation: int = 0) -> None:
        if generation != self._generation:
            return
        self._set_busy(False)
        new: list[Article] = result  # type: ignore[assignment]
        before = len(self.articles)
        with use_site(self.site):
            self.articles.add(new)
        if self.current_source.input is Input.TEXT and not self.current_source.needs_wiki:
            self.text.clear()  # the manual box has been added: ready for more
        self.refresh()
        self.status.emit(self.tr("%n page(s) added", "", len(self.articles) - before))
        if self.format_display_title.isChecked():
            self._fetch_display_titles()

    def _list_failed(self, error: object, generation: int = 0) -> None:
        if generation != self._generation:
            return
        self._set_busy(False)
        self.status.emit(self.tr("Could not make the list: %1").replace("%1", str(error)))

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.make.setEnabled(not busy)
        self.source.setEnabled(not busy)
        self.stop_button.setVisible(busy)

    def add_typed_page(self) -> None:
        """The "+" button: add the typed title (or URL, or [[link]]) to the list."""
        with use_site(self.site):
            new = providers.titles_from_paste(self.add_line.text())
            self.articles.add(new)
        self.add_line.clear()
        self.refresh()

    # -- actions shared with the List menu ----------------------------------------------------

    def _make_actions(self) -> None:
        def action(
            text: str, slot: Callable[[], object], key: str = "", list_only: bool = False
        ) -> QAction:
            a = QAction(text, self)
            a.triggered.connect(lambda _=False: slot())
            if key:
                a.setShortcut(QKeySequence(key))
                if list_only:  # only while the list has the focus (Ctrl+C etc. elsewhere)
                    a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                    self.list.addAction(a)
            return a

        def toggle(text: str, slot: Callable[[bool], None], key: str) -> QAction:
            a = QAction(text, self)
            a.setCheckable(True)
            a.setShortcut(QKeySequence(key))
            a.toggled.connect(slot)
            return a

        # List menu toggles (AWB: AutoAlpha, FilterDuplicates, FilterNonMainAuto)
        self.keep_alphabetized = toggle(
            self.tr("Keep alphabetized"), self._set_auto_alpha, "Ctrl+Shift+A"
        )
        self.filter_duplicates = toggle(
            self.tr("Remove duplicates"), self._set_filter_duplicates, "Ctrl+Shift+U"
        )
        self.filter_non_main = toggle(
            self.tr("Remove non-main space"), self._set_filter_non_main, "Ctrl+Shift+M"
        )
        self.convert_to_talk = action(self.tr("Convert to talk pages"), self.convert_to_talk_pages)
        self.convert_from_talk = action(
            self.tr("Convert from talk pages"), self.convert_from_talk_pages
        )
        self.filter_action = action(self.tr("Filter…"), self.filter, "Ctrl+Shift+F")
        self.save_action = action(self.tr("Save list…"), self.save_list)
        self.clear_action = action(self.tr("Clear current list"), self.ask_clear)
        self.remove_done_action = action(self.tr("Remove done pages"), self.remove_done)

        # context menu
        self.open_action = action(
            self.tr("Open in browser"), self.open_in_browser, "Ctrl+Shift+P", True
        )
        self.history_action = action(
            self.tr("Open history in browser"), self.open_history_in_browser, "Ctrl+Shift+H", True
        )
        self.cut_action = action(self.tr("Cut"), self.cut, "Ctrl+X", True)
        self.copy_action = action(self.tr("Copy"), self.copy, "Ctrl+C", True)
        self.paste_action = action(self.tr("Paste"), self.paste, "Ctrl+V", True)
        self.select_all_action = action(self.tr("All"), self.select_all, "Ctrl+A", True)
        # AWB's Ctrl+D is the Diff button here
        self.select_none_action = action(self.tr("None"), self.select_none)
        self.invert_action = action(self.tr("Inverse"), self.invert_selection, "Ctrl+Shift+I", True)
        self.remove_selected_action = action(self.tr("Selected"), self.remove_selected)
        self.remove_all_action = action(self.tr("All"), self.ask_clear)
        self.remove_duplicates_action = action(self.tr("Duplicates"), self.remove_duplicates)
        self.remove_non_main_action = action(self.tr("Non-main space"), self.remove_non_main)
        self.move_top_action = action(self.tr("Move to top"), lambda: self.move_selected(True))
        self.move_bottom_action = action(
            self.tr("Move to bottom"), lambda: self.move_selected(False)
        )
        self.format_display_title = QAction(self.tr("Format page titles per displaytitle"), self)
        self.format_display_title.setCheckable(True)
        self.format_display_title.toggled.connect(self._set_format_display_title)
        self.sort_action = action(self.tr("Sort alphabetically"), lambda: self.sort(False))
        self.reverse_sort_action = action(
            self.tr("Sort reverse alphabetically"), lambda: self.sort(True)
        )

    def list_menu_actions(self) -> list[QAction | None]:
        """The main window's List menu (None: a separator)."""
        return [
            self.keep_alphabetized,
            self.filter_duplicates,
            self.filter_non_main,
            None,
            self.convert_to_talk,
            self.convert_from_talk,
            None,
            self.filter_action,
            self.save_action,
            self.remove_done_action,
            self.clear_action,
        ]

    def _context_menu(self, pos: QPoint) -> None:
        self.context_menu().exec(self.list.viewport().mapToGlobal(pos))

    def context_menu(self) -> QMenu:
        """mnuListBox, enabled as in AWB's mnuListBox_Opening."""
        self._sync_selection()
        menu = QMenu(self)
        selected = bool(self.articles.selected_indices)
        count = len(self.articles)
        editable = self.list.isEnabled()
        menu.addActions([self.open_action, self.history_action])
        menu.addSeparator()
        menu.addActions([self.cut_action, self.copy_action, self.paste_action])
        menu.addSeparator()
        select = menu.addMenu(self.tr("Select"))
        select.addActions([self.select_all_action, self.select_none_action, self.invert_action])
        remove = menu.addMenu(self.tr("Remove"))
        remove.addActions(
            [
                self.remove_selected_action,
                self.remove_all_action,
                self.remove_duplicates_action,
                self.remove_non_main_action,
            ]
        )
        menu.addSeparator()
        add_from = menu.addMenu(self.tr("Add selected to list from"))
        for src in sources.ADD_FROM_SELECTED:
            a = add_from.addAction(self.tr(src.name))
            a.triggered.connect(lambda _=False, s=src: self.add_selected_from(s))
        add_from.setEnabled(selected and editable and self.wiki is not None and not self.busy)
        menu.addSeparator()
        menu.addActions([self.move_top_action, self.move_bottom_action])
        menu.addSeparator()
        menu.addActions([self.convert_to_talk, self.convert_from_talk])
        menu.addSeparator()
        menu.addActions(
            [
                self.format_display_title,
                self.filter_action,
                self.save_action,
                self.sort_action,
                self.reverse_sort_action,
            ]
        )
        for a in (self.open_action, self.history_action, self.copy_action):
            a.setEnabled(selected)
        for a in (
            self.cut_action,
            self.remove_selected_action,
            self.move_top_action,
            self.move_bottom_action,
        ):
            a.setEnabled(selected and editable)
        for a in (self.sort_action, self.reverse_sort_action, self.filter_action):
            a.setEnabled(count > 1 and editable)
        select.setEnabled(count > 0)
        remove.setEnabled(count > 0 and editable)
        for a in (self.convert_to_talk, self.convert_from_talk):
            a.setEnabled(count > 0 and editable)
        self.save_action.setEnabled(count > 0)
        self.paste_action.setEnabled(editable)
        return menu

    def _update_actions(self) -> None:
        """Enable the List menu as AWB's UpdateButtons does."""
        count = len(self.articles)
        editable = self.list.isEnabled()
        for a in (self.convert_to_talk, self.convert_from_talk, self.clear_action):
            a.setEnabled(count > 0 and editable)
        self.filter_action.setEnabled(count > 0 and editable)
        self.save_action.setEnabled(count > 0)
        self.remove_done_action.setEnabled(self.articles.done_count > 0 and editable)

    # -- the list -----------------------------------------------------------------------------

    def refresh(self) -> None:
        """Show the model (after it changed)."""
        self.list.blockSignals(True)
        self.list.clear()
        icons = {
            ArticleList.SAVED: codex_icon("check"),
            ArticleList.SKIPPED: codex_icon("arrowNext"),
        }
        done_color = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
        pre_parsed = QColor(theme.tokens(theme.Mode.SYSTEM)["background_color_success_subtle"])
        current = self.articles.selected_index
        chosen = set(self.articles.selected_indices)
        formatted = self.format_display_title.isChecked()
        for i, a in enumerate(self.articles):
            item = QListWidgetItem(a.name)
            item.setToolTip(a.name)
            if formatted:
                rich = display_title_html(a.display_title, a.name)
                if rich:
                    item.setData(RICH_ROLE, rich)
            if a.pre_processed and not a.list_status:  # pre-parse mode found changes (AWB: green)
                item.setBackground(pre_parsed)
                item.setToolTip(f"{a.name} ({self.tr('pre-parsed: has changes')})")
            if a.list_status:
                item.setIcon(icons.get(a.list_status, QIcon()))
                item.setForeground(done_color)
                item.setToolTip(f"{a.name} ({self.tr(a.list_status)})")
            if i == current:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.list.addItem(item)
            item.setSelected(i in chosen or i == current)
        if current >= 0:
            self.list.setCurrentRow(current, QItemSelectionModel.SelectionFlag.NoUpdate)
            self.list.scrollToItem(self.list.item(current))
        self.list.blockSignals(False)
        self.count.setText(self.tr("%n page(s)", "", len(self.articles)))
        self._update_buttons()
        self.changed.emit()

    def _update_buttons(self) -> None:
        has = len(self.articles) > 0
        editable = self.list.isEnabled()
        self.remove.setEnabled(has and editable)
        self.filter_button.setEnabled(has and editable)
        if hasattr(self, "save_action"):
            self._update_actions()

    def _sync_selection(self) -> None:
        rows = {i.row() for i in self.list.selectedIndexes()}
        for i in range(len(self.articles)):
            self.articles.set_selected(i, i in rows)

    def selected_articles(self) -> list[Article]:
        self._sync_selection()
        return self.articles.get_selected_article_list()

    def remove_selected(self) -> None:
        self._sync_selection()
        self.articles.remove_selected()
        self.refresh()

    def clear_list(self) -> None:
        self.articles.clear()
        self.refresh()

    def ask_clear(self) -> None:
        """Clear current list, asking first for a long list (AWB asks above 100 pages)."""
        if not self.articles:
            return
        if len(self.articles) > CLEAR_WARNING and (
            QMessageBox.question(
                self,
                self.tr("Clear current list"),
                self.tr("Do you want to clear the list of %n page(s)?", "", len(self.articles)),
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.clear_list()

    def remove_duplicates(self) -> None:
        self.articles.remove_list_duplicates()
        self.refresh()

    def remove_non_main(self) -> None:
        self.articles.filter_non_main_articles()
        self.refresh()

    def _set_auto_alpha(self, on: bool) -> None:
        self.articles.auto_alpha = on
        if on:
            self.sort(False)

    def _set_filter_duplicates(self, on: bool) -> None:
        self.articles.filter_duplicates = on
        if on:
            self.remove_duplicates()

    def _set_filter_non_main(self, on: bool) -> None:
        self.articles.filter_non_main_auto = on
        if on:
            self.remove_non_main()

    def sort(self, reverse: bool) -> None:
        self._sync_selection()
        self.articles.sort(reverse)
        self.refresh()

    def convert_to_talk_pages(self) -> None:
        with use_site(self.site):
            self.articles.convert_to_talk_pages()
        self.refresh()

    def convert_from_talk_pages(self) -> None:
        with use_site(self.site):
            self.articles.convert_from_talk_pages()
        self.refresh()

    def select_all(self) -> None:
        self.list.selectAll()

    def select_none(self) -> None:
        self.list.clearSelection()

    def invert_selection(self) -> None:
        self._sync_selection()
        self.articles.invert_selection()
        self.refresh()

    def move_selected(self, to_top: bool) -> None:
        self._sync_selection()
        self.articles.move_selected(to_top)
        self.refresh()

    def copy(self) -> None:
        self._sync_selection()
        text = self.articles.copy_text()
        if text:
            QApplication.clipboard().setText(text)

    def cut(self) -> None:
        self.copy()
        self.remove_selected()

    def paste(self) -> None:
        """Titles from the clipboard, one per line or separated by "|" (AWB's Paste)."""
        with use_site(self.site):
            self.articles.add(providers.titles_from_paste(QApplication.clipboard().text()))
        self.refresh()

    def _confirm_many(self, count: int) -> bool:
        return count < BROWSER_WARNING or (
            QMessageBox.question(
                self,
                self.tr("Continue?"),
                self.tr(
                    "Opening %n page(s) in your browser at once could make your system slow. "
                    "Continue?",
                    "",
                    count,
                ),
            )
            == QMessageBox.StandardButton.Yes
        )

    def open_in_browser(self) -> None:
        chosen = self.selected_articles()
        if chosen and self._confirm_many(len(chosen)):
            with use_site(self.site):
                urls = [tools.non_prettified_url(a.name) for a in chosen]
            for url in urls:
                QDesktopServices.openUrl(QUrl(url))

    def open_history_in_browser(self) -> None:
        chosen = self.selected_articles()
        if chosen and self._confirm_many(len(chosen)):
            with use_site(self.site):
                urls = [tools.get_article_history_url(a.name) for a in chosen]
            for url in urls:
                QDesktopServices.openUrl(QUrl(url))

    def filter(self) -> None:
        """List ▸ Filter…"""
        if not self.articles:
            return
        dialog = ListFilterDialog(self.site, self.list_filter, self)
        if dialog.exec() != ListFilterDialog.DialogCode.Accepted:
            return
        self.list_filter = dialog.value()
        self.apply_filter(self.list_filter)

    def apply_filter(self, f: ListFilter) -> None:
        current = self.articles.selected_article()
        kept = f.apply(self.articles.items)
        self.articles.items = kept
        self.articles.select(kept.index(current) if current is not None and current in kept else -1)
        self.refresh()
        self.status.emit(self.tr("%n page(s) in the list", "", len(kept)))

    def save_list(self) -> None:
        """Save list… in AWB's four formats, chosen by the file type."""
        if not self.articles:
            return
        filters = [self.tr(SAVE_FILTERS[f]) for f in OutputFormat]
        last_name, last_format = self._last_save
        name, chosen = QFileDialog.getSaveFileName(
            self, self.tr("Save page list"), last_name, ";;".join(filters), filters[last_format - 1]
        )
        if not name:
            return
        fmt = OutputFormat(filters.index(chosen) + 1) if chosen in filters else last_format
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix(".txt")
        try:
            save_list(self.articles, path, fmt)
        except OSError as e:
            QMessageBox.warning(self, self.tr("Save page list"), str(e))
            return
        self._last_save = (str(path), fmt)
        self.status.emit(self.tr("List saved to %1").replace("%1", str(path)))

    def _set_format_display_title(self, on: bool) -> None:
        if on:
            self._fetch_display_titles()
        self.refresh()

    def _fetch_display_titles(self) -> None:
        """Look up the displaytitles the list does not have yet."""
        if self.wiki is None:
            self.status.emit(self.tr("Connect to a wiki to read display titles"))
            return
        missing = [a.name for a in self.articles if a.display_title is None]
        if not missing:
            return
        transport = self.wiki.transport

        def done(result: object) -> None:
            found: dict[str, str] = result  # type: ignore[assignment]
            for a in self.articles:
                if a.name in missing:
                    a.display_title = found.get(a.name, "")
            self.refresh()

        run_task(
            lambda: display_titles(transport, missing),
            done,
            lambda e: self.status.emit(str(e)),
        )

    # -- for the edit loop --------------------------------------------------------------------

    def selected_article(self) -> Article | None:
        article = self.articles.selected_article()
        self.refresh()
        return article

    def mark(self, index: int, status: str) -> None:
        """The loop is done with the page at index (ArticleList.SAVED / SKIPPED)."""
        if 0 <= index < len(self.articles):
            self.articles.items[index].list_status = status
            self.refresh()

    def select_index(self, index: int) -> None:
        self.articles.select(index)
        self.refresh()

    def remove_done(self) -> None:
        self.articles.remove_done()
        self.refresh()

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
        for w in (self.make, self.remove, self.filter_button, self.source, self.add_line):
            w.setEnabled(editable)
        self.list.setEnabled(editable)
        for a in (self.keep_alphabetized, self.filter_duplicates, self.filter_non_main):
            a.setEnabled(editable)
        self._update_buttons()
