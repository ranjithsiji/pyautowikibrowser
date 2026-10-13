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
"""Main window: log in, make a list, and work through it (AWB's MainForm).

The page-by-page work runs in pyawb.editloop, off the UI thread; this window holds the state
between steps (the page shown, waiting for Save or Skip) and moves on through the list.
"""

from __future__ import annotations

import html
import json
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QLocale, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pyawb import __version__, paths
from pyawb.api import connect, credentials
from pyawb.api.models import WatchOptions
from pyawb.api.session import WikiSession
from pyawb.api.sparql import PywikibotSparql
from pyawb.core import tools
from pyawb.core.article import Article
from pyawb.core.site import SiteConfig, current_site
from pyawb.editloop import EditLoop, LoadResult
from pyawb.editor import mwconfig
from pyawb.editor.diffhtml import DiffColors, qt_diff_html
from pyawb.editor.messages import Messages
from pyawb.editor.mwconfig import MwConfig, default_config
from pyawb.editor.toolbar import ToolbarSite, build_toolbar
from pyawb.lists.sources import WikiContext
from pyawb.settings import appconfig
from pyawb.ui import theme
from pyawb.ui.editor_dialogs import DIALOGS, EditorDialogs, Suggest
from pyawb.ui.editor_toolbar import WikiEditorToolbar
from pyawb.ui.highlighter import WikitextHighlighter
from pyawb.ui.list_maker import ListMaker
from pyawb.ui.login_dialog import LoginDialog
from pyawb.ui.options_panel import OptionsError, OptionsPanel
from pyawb.ui.tasks import run_task

RECENT_FILE = "recent_characters.json"
_WATCH = (
    ("Don't change the watchlist", WatchOptions.NO_CHANGE),
    ("Add to watchlist", WatchOptions.WATCH),
    ("Remove from watchlist", WatchOptions.UNWATCH),
    ("Use preferences", WatchOptions.PREFERENCES),
)


def ui_language() -> str:
    """The interface language as a MediaWiki language code, from the system locale."""
    locale = QLocale.system()
    code = locale.bcp47Name().lower()
    if code.startswith("zh"):
        script = locale.script()
        return "zh-hant" if script == QLocale.Script.TraditionalHanScript else "zh-hans"
    return code or "en"


def _load_recent() -> list[Any]:
    try:
        data = json.loads((paths.data_dir() / RECENT_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def _save_recent(recent: list[Any]) -> None:
    try:
        paths.data_dir().mkdir(parents=True, exist_ok=True)
        (paths.data_dir() / RECENT_FILE).write_text(
            json.dumps(recent, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def _placeholder(combo: QComboBox, text: str) -> None:
    edit = combo.lineEdit()
    if edit is not None:
        edit.setPlaceholderText(text)


def diff_colors() -> DiffColors:
    t = theme.tokens(theme.Mode.SYSTEM)
    return DiffColors(
        added=t["background_color_content_added"],
        removed=t["background_color_content_removed"],
        added_border=t["border_color_content_added"],
        removed_border=t["border_color_content_removed"],
        context=t["background_color_neutral_subtle"],
        text=t["color_base"],
        subtle=t["color_subtle"],
    )


class MainWindow(QMainWindow):
    def __init__(self, language: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"PyAutoWikiBrowser {__version__}")
        self.resize(1200, 800)

        self.config = self._load_config()
        self.session: WikiSession | None = None
        self.loop: EditLoop | None = None
        self.current: LoadResult | None = None
        self.running = False  # Start pressed and not stopped
        self.busy = False  # a background step is running
        self.edits = self.skips = 0

        # editor (Edit tab)
        edit_tab = QWidget(self)
        edit_layout = QVBoxLayout(edit_tab)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(0)
        self.editor = QPlainTextEdit(edit_tab)
        self.editor.setObjectName("editor")
        self.highlighter = WikitextHighlighter(self.editor.document(), default_config())
        self.messages = Messages(language or ui_language())
        self.site = ToolbarSite()
        self.toolbar = WikiEditorToolbar(
            self.editor,
            build_toolbar(self.messages, self.site, recent_characters=_load_recent()),
            self.messages,
            dialogs=DIALOGS,
            parent=edit_tab,
        )
        self.toolbar.recent_changed.connect(_save_recent)
        self.dialogs = EditorDialogs(self.editor, self.messages, self.site, open_url=self.open_url)
        self.toolbar.dialog_requested.connect(self.dialogs.open)
        edit_layout.addWidget(self.toolbar)
        edit_layout.addWidget(self.editor, 1)

        # diff (Diff tab)
        self.diff = QTextBrowser(self)
        self.diff.setObjectName("diffView")
        self.diff.setOpenLinks(False)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(edit_tab, self.tr("Edit"))
        self.tabs.addTab(self.diff, self.tr("Diff"))

        # options, summary, buttons
        self.options = OptionsPanel(self)
        self.summary = QComboBox(self)
        self.summary.setEditable(True)
        self.summary.setObjectName("summary")
        _placeholder(self.summary, self.tr("Default edit summary"))
        self.review_summary = QComboBox(self)
        self.review_summary.setEditable(True)
        _placeholder(self.review_summary, self.tr("Edit summary for this page"))
        self.minor = QCheckBox(self.tr("Minor edit"), self)
        self.watch = QComboBox(self)
        for label, value in _WATCH:
            self.watch.addItem(self.tr(label), value)

        self.start_button = QPushButton(self.tr("Start"), self)
        self.start_button.setProperty("primary", True)
        self.save_button = QPushButton(self.tr("Save"), self)
        self.save_button.setProperty("primary", True)
        self.skip_button = QPushButton(self.tr("Skip"), self)
        self.stop_button = QPushButton(self.tr("Stop"), self)
        self.diff_button = QPushButton(self.tr("Show changes"), self)
        self.preview_button = QPushButton(self.tr("Preview"), self)
        self.start_button.clicked.connect(self.start)
        self.save_button.clicked.connect(self.save)
        self.skip_button.clicked.connect(lambda: self.skip_page("user"))
        self.stop_button.clicked.connect(self.stop)
        self.diff_button.clicked.connect(self.show_diff)
        self.preview_button.clicked.connect(self.preview)

        controls = QWidget(self)
        cl = QVBoxLayout(controls)
        cl.setContentsMargins(8, 4, 8, 8)
        summary_row = QHBoxLayout()
        summary_row.addWidget(QLabel(self.tr("Summary"), controls))
        summary_row.addWidget(self.summary, 2)
        summary_row.addWidget(self.review_summary, 3)
        cl.addLayout(summary_row)
        button_row = QHBoxLayout()
        button_row.addWidget(self.minor)
        button_row.addWidget(self.watch)
        button_row.addStretch(1)
        for b in (
            self.start_button,
            self.stop_button,
            self.diff_button,
            self.preview_button,
            self.skip_button,
            self.save_button,
        ):
            button_row.addWidget(b)
        cl.addLayout(button_row)

        bottom = QWidget(self)
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(self.options, 1)
        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.addWidget(self.tabs)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(splitter, 1)
        layout.addWidget(controls)
        self.setCentralWidget(central)

        # list maker
        self.list_maker = ListMaker(self)
        self.list_maker.status.connect(self.set_status)
        self.list_maker.changed.connect(self._update_buttons)
        dock = QDockWidget(self.tr("Pages"), self)
        dock.setObjectName("listDock")
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        dock.setWidget(self.list_maker)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        # status bar
        self.status_label = QLabel(self.tr("Not logged in"), self)
        self.counts_label = QLabel(self)
        self.wiki_label = QLabel(self)
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.counts_label)
        self.statusBar().addPermanentWidget(self.wiki_label)

        self._make_menus()
        self._update_counts()
        self._update_buttons()

    # -- menus --------------------------------------------------------------------------------

    def _make_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.login_action = QAction(self.tr("Log in…"), self)
        self.login_action.setShortcut(QKeySequence("Ctrl+L"))
        self.login_action.triggered.connect(self.log_in)
        self.logout_action = QAction(self.tr("Log out"), self)
        self.logout_action.triggered.connect(self.log_out)
        quit_action = QAction(self.tr("Quit"), self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addActions([self.login_action, self.logout_action])
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        # AWB's keyboard shortcuts for the loop
        for key, slot in (
            ("Ctrl+S", self.save),
            ("Ctrl+I", lambda: self.skip_page("user")),
            ("Ctrl+D", self.show_diff),
            ("Ctrl+E", self.preview),
        ):
            action = QAction(self)
            action.setShortcut(QKeySequence(key))
            action.triggered.connect(slot)
            self.addAction(action)

        help_menu = self.menuBar().addMenu(self.tr("&Help"))
        about = QAction(self.tr("About PyAutoWikiBrowser"), self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

    def _about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("About PyAutoWikiBrowser"),
            f"PyAutoWikiBrowser {__version__}<br>"
            '<a href="https://en.wikipedia.org/wiki/Wikipedia:PyAutoWikiBrowser">'
            "Wikipedia:PyAutoWikiBrowser</a><br>GPL-3.0-or-later",
        )

    # -- status -------------------------------------------------------------------------------

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _update_counts(self) -> None:
        self.counts_label.setText(
            self.tr("Edits: %1  Skipped: %2")
            .replace("%1", str(self.edits))
            .replace("%2", str(self.skips))
        )

    def _update_buttons(self) -> None:
        can_save = self.session is not None and self.session.can_save
        page = self.current is not None and not self.busy
        has_pages = len(self.list_maker.articles) > 0
        self.start_button.setEnabled(can_save and not self.busy and not page and has_pages)
        self.stop_button.setEnabled(self.running or self.busy)
        for b in (self.save_button, self.skip_button, self.diff_button, self.preview_button):
            b.setEnabled(page)
        self.logout_action.setEnabled(self.session is not None and not self.busy)
        self.login_action.setEnabled(not self.busy)
        self.list_maker.set_editable(not self.running)

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self.busy = busy
        if status:
            self.set_status(status)
        self._update_buttons()

    # -- configuration and login --------------------------------------------------------------

    def _load_config(self) -> appconfig.AppConfig:
        try:
            return appconfig.load()
        except (appconfig.ConfigError, OSError) as e:
            QMessageBox.warning(None, "PyAutoWikiBrowser", f"config.toml: {e}")
            return appconfig.AppConfig()

    def log_in(self) -> None:
        remembered: dict[str, bool] = {}
        for p in self.config.profiles:
            if p.remember_password and p.username:
                try:
                    remembered[p.name] = (
                        credentials.load_password(p.wiki_url, p.username) is not None
                    )
                except Exception:  # no usable keychain
                    remembered[p.name] = False
        dialog = LoginDialog(self.config, remembered, self)
        if not dialog.exec():
            return
        config = dialog.updated_config()
        profile = dialog.profile()
        password = dialog.password.text() or None
        if config != self.config:
            try:
                appconfig.save(config)
            except OSError as e:
                QMessageBox.warning(self, self.tr("Settings"), str(e))
            self.config = config

        self.stop()
        self._set_busy(True, self.tr("Connecting to %1…").replace("%1", profile.wiki_url))
        cfg = self.config

        def work() -> tuple[WikiSession, WikiContext]:
            session = connect.connect(cfg, profile, password)
            return session, self._wiki_context(cfg, session)

        run_task(work, self._connected, self._connect_failed)

    @staticmethod
    def _wiki_context(cfg: appconfig.AppConfig, session: WikiSession) -> WikiContext:
        general: dict[str, Any] = (
            dict(session.siteinfo.query.get("general", {})) if session.siteinfo else {}
        )
        try:
            wikidata = connect.wikidata_transport(cfg)
        except Exception:  # Wikidata unreachable: everything else still works
            wikidata = None
        return WikiContext(
            transport=session.transport,
            wikidata=wikidata,
            sparql=PywikibotSparql(),
            site_id=str(general.get("wikiid", "")),
            article_url=session.siteinfo.article_url if session.siteinfo else "",
            pywikibot_site=getattr(session.transport, "site", None),
        )

    def _connected(self, result: object) -> None:
        session, wiki = result  # type: ignore[misc]
        assert isinstance(session, WikiSession) and isinstance(wiki, WikiContext)
        self.session = session
        self.loop = EditLoop(session)
        self._set_busy(False)
        site = session.site
        query = session.siteinfo.query if session.siteinfo else {}
        if query:
            self.set_site(ToolbarSite.from_siteinfo(query), site.rtl, session.prefix_search)
            self.set_wiki_config(mwconfig.from_siteinfo(query))
        else:
            self.set_text_direction(site.rtl)
        self.list_maker.set_wiki(wiki, site)
        self.wiki_label.setText(f"{session.user.name} @ {site.url}")
        status = session.status
        if session.can_save:
            self.set_status(self.tr("Logged in"))
        else:
            reason = status.status.value if status else "unknown"
            detail = status.reason if status and status.reason else ""
            self.set_status(self.tr("Logged in, but not allowed to save: %1").replace("%1", reason))
            QMessageBox.warning(
                self,
                self.tr("CheckPage"),
                self.tr(
                    "You are not approved to use AutoWikiBrowser on this wiki (%1). Ask for "
                    "approval at the wiki's AutoWikiBrowser/CheckPage. You can still make lists."
                ).replace("%1", detail or reason),
            )
        if status and status.messages:
            QMessageBox.information(self, self.tr("Messages"), "\n\n".join(status.messages))
        self._update_buttons()

    def _connect_failed(self, error: Exception) -> None:
        self._set_busy(False, self.tr("Could not log in"))
        QMessageBox.warning(self, self.tr("Log in"), str(error) or type(error).__name__)

    def log_out(self) -> None:
        self.stop()
        if self.session is not None:
            session = self.session
            run_task(session.logout, lambda _: None, lambda _: None)
        self.session = self.loop = None
        self.wiki_label.clear()
        self.list_maker.set_wiki(None, current_site())
        self.set_status(self.tr("Not logged in"))
        self._update_buttons()

    # -- the loop -----------------------------------------------------------------------------

    def start(self) -> None:
        """StartArticleProcessing: load and process the selected page."""
        if self.busy or self.loop is None or self.session is None or not self.session.can_save:
            return
        if self.session.site.project != "custom" and not self.summary.currentText().strip():
            QMessageBox.warning(
                self, self.tr("Edit summary"), self.tr("Please enter an edit summary.")
            )
            self.stop()
            return
        try:
            status = self.session.status
            config = status.config if status else None
            opts = self.options.loop_options(
                self.summary.currentText(),
                self.session.user.name,
                frozenset(config.no_genfixes) if config else frozenset(),
                frozenset(config.no_regex_typo_fix) if config else frozenset(),
            )
        except OptionsError as e:
            QMessageBox.warning(self, self.tr("Skip options"), str(e))
            self.stop()
            return
        self._remember_summary()
        article = self.list_maker.selected_article()
        if article is None:
            self.stop()
            self.set_status(self.tr("No pages in the list: make a list first"))
            return
        self.running = True
        self._clear_page()
        loop, title = self.loop, article.name
        self._set_busy(True, self.tr("Loading %1…").replace("%1", title))
        run_task(lambda: loop.load(title, opts), self._loaded, self._step_failed)

    def _remember_summary(self) -> None:
        text = self.summary.currentText().strip()
        if text and self.summary.findText(text) < 0:
            self.summary.insertItem(0, text)

    def _loaded(self, result: object) -> None:
        assert isinstance(result, LoadResult)
        self._set_busy(False)
        if not self.running:
            return
        if result.new_messages:
            self.stop()
            QMessageBox.information(
                self, self.tr("New messages"), self.tr("You have new messages on your talk page.")
            )
            return
        if result.renamed and result.page is not None:
            self.list_maker.replace_article(result.title, Article(result.page.title))
            if result.page.was_redirected:
                self.set_status(
                    self.tr("Followed redirect %1 → %2")
                    .replace("%1", result.title)
                    .replace("%2", result.page.title)
                )
        if result.skipped:
            self.current = result
            self.skip_page(result.skip_reason or "")
            return

        self.current = result
        self.editor.setPlainText(tools.convert_from_local_line_endings(result.text))
        self.editor.moveCursor(self.editor.textCursor().MoveOperation.Start)
        self.review_summary.setEditText(result.summary)
        title = result.page.title if result.page else result.title
        self.setWindowTitle(f"{title} – PyAutoWikiBrowser")
        if result.in_use:
            self.set_status(self.tr("This page has {{inuse}}: consider skipping it"))
        self._update_buttons()
        self.show_diff()

    def _edited_text(self) -> str:
        return tools.convert_to_local_line_endings(self.editor.toPlainText())

    def show_diff(self) -> None:
        if self.current is None or self.loop is None or self.busy:
            return
        loop, result, text = self.loop, self.current, self._edited_text()
        rtl = self.session.site.rtl if self.session else False
        self._set_busy(True, self.tr("Getting the diff…"))

        def done(rows: object) -> None:
            self._set_busy(False, self.tr("Ready to save"))
            self.diff.setHtml(
                qt_diff_html(
                    str(rows),
                    diff_colors(),
                    rtl=rtl,
                    line_label=self.tr("Line $1:"),
                    no_difference=self.tr("No difference"),
                )
            )
            self.tabs.setCurrentWidget(self.diff)
            self.save_button.setFocus()

        run_task(lambda: loop.diff(result, text), done, self._step_failed)

    def preview(self) -> None:
        """Parse the edited text on the wiki and open it in the default browser."""
        if self.current is None or self.loop is None or self.busy or self.session is None:
            return
        loop, result, text = self.loop, self.current, self._edited_text()
        site = self.session.site
        self._set_busy(True, self.tr("Getting the preview…"))

        def done(body: object) -> None:
            self._set_busy(False, self.tr("Preview opened in the browser"))
            path = write_preview(str(body), result, site)
            self.open_url(QUrl.fromLocalFile(str(path)).toString())

        run_task(lambda: loop.preview(result, text), done, self._step_failed)

    def save(self) -> None:
        if self.current is None or self.loop is None or self.busy:
            return
        text = self._edited_text()
        page = self.current.page
        if not text.strip() and page is not None and page.exists:
            answer = QMessageBox.question(
                self, self.tr("Save?"), self.tr("Do you really want to save a blank page?")
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.skip_page("Nothing to save - blank page")
                return
        loop, result = self.loop, self.current
        summary = self.review_summary.currentText()
        minor, watch = self.minor.isChecked(), self.watch.currentData()
        self._set_busy(True, self.tr("Saving…"))
        run_task(
            lambda: loop.save(result, text, summary, minor=minor, watch=watch),
            self._saved,
            self._save_failed,
        )

    def _saved(self, _info: object) -> None:
        self._set_busy(False, self.tr("Saved"))
        self.edits += 1
        self._update_counts()
        self._done_with_page()

    def _save_failed(self, error: Exception) -> None:
        # the page stays loaded: the user may retry, edit or skip
        self._set_busy(False, self.tr("Save failed: %1").replace("%1", str(error)))
        QMessageBox.warning(self, self.tr("Save"), str(error) or type(error).__name__)

    def skip_page(self, reason: str) -> None:
        if self.current is None or self.busy:
            return
        self.skips += 1
        self._update_counts()
        title = self.current.page.title if self.current.page else self.current.title
        why = self.tr("skipped by you") if reason == "user" else reason
        self.set_status(self.tr("Skipped %1: %2").replace("%1", title).replace("%2", why))
        self._done_with_page()

    def _done_with_page(self) -> None:
        """Remove the page from the list and go on with the next (PageSaved / SkipPage)."""
        result = self.current
        self._clear_page()
        if result is not None:
            title = result.page.title if result.page and result.renamed else result.title
            if not self.list_maker.remove_article(title):
                self.stop()
                QMessageBox.warning(
                    self,
                    self.tr("List"),
                    self.tr("The page could not be removed from the list. Please remove it."),
                )
                return
        if self.running and len(self.list_maker.articles) > 0:
            self.start()
        else:
            self.running = False
            if not len(self.list_maker.articles):
                self.set_status(self.tr("The list is done"))
            self._update_buttons()

    def _step_failed(self, error: Exception) -> None:
        """Loading or processing failed: stop, as AWB does, and keep the page in the list."""
        self._set_busy(False)
        self.stop()
        self.set_status(self.tr("Error: %1").replace("%1", str(error) or type(error).__name__))
        QMessageBox.warning(self, "PyAutoWikiBrowser", str(error) or type(error).__name__)

    def stop(self) -> None:
        self.running = False
        if not self.busy:
            self._clear_page()
            self.set_status(self.tr("Stopped"))
        self._update_buttons()

    def _clear_page(self) -> None:
        self.current = None
        self.editor.clear()
        self.diff.clear()
        self.review_summary.setEditText("")
        self.setWindowTitle(f"PyAutoWikiBrowser {__version__}")
        self.tabs.setCurrentIndex(0)
        self._update_buttons()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.running = False
        super().closeEvent(event)

    # -- wiki-specific editor setup -----------------------------------------------------------

    def set_site(
        self, site: ToolbarSite, rtl: bool = False, suggest: Suggest | None = None
    ) -> None:
        """Rebuild the toolbar and dialogs for a loaded wiki (namespaces, magic words, content
        language). suggest: link target suggestions, WikiSession.prefix_search."""
        self.site = site
        self.messages = Messages(self.messages.lang, site.sitename)
        content = Messages(site.content_language, site.sitename)
        toolbar = build_toolbar(
            self.messages, site, content, recent_characters=self.toolbar.recent_characters
        )
        self.toolbar.set_toolbar(toolbar, self.messages)
        self.dialogs.set_site(self.messages, site, suggest)
        self.set_text_direction(rtl)

    @staticmethod
    def open_url(url: str) -> None:
        """Open a page in the default browser (Firefox where installed is the user's choice)."""
        QDesktopServices.openUrl(QUrl(url))

    def set_wiki_config(self, config: MwConfig) -> None:
        """Highlight with the loaded wiki's magic words, tags and namespaces."""
        self.highlighter.set_config(config)

    def set_text_direction(self, rtl: bool) -> None:
        """Set editor, summary and diff direction from the wiki's siteinfo `rtl` flag."""
        direction = Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        self.editor.setLayoutDirection(direction)
        option = self.editor.document().defaultTextOption()
        option.setTextDirection(direction)
        # Qt does not take the alignment from the direction: start lines at the leading edge
        option.setAlignment(Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft)
        self.editor.document().setDefaultTextOption(option)
        for w in (self.summary, self.review_summary, self.diff):
            w.setLayoutDirection(direction)


def write_preview(body: str, result: LoadResult, site: SiteConfig) -> Path:
    """A page for the browser: the parsed HTML with the wiki's styles, in the wiki's direction."""
    title = result.page.title if result.page else result.title
    lang = html.escape(site.lang_code)
    direction = "rtl" if site.rtl else "ltr"
    base = html.escape(site.url + "/")
    styles = html.escape(
        site.url
        + "/w/load.php?modules=site.styles|skins.vector.styles.legacy|mediawiki.skinning.content"
        "&only=styles&skin=vector"
    )
    page = (
        f'<!DOCTYPE html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8">'
        f'<base href="{base}"><link rel="stylesheet" href="{styles}">'
        f"<title>{html.escape(title)} (preview)</title></head>"
        f'<body class="mw-body" style="max-width:60em;margin:1em auto;padding:0 1em">'
        f'<h1 class="firstHeading">{html.escape(title)}</h1>'
        f'<div class="mw-body-content mw-content-{direction}" lang="{lang}" dir="{direction}">'
        f"{body}</div></body></html>"
    )
    folder = Path(tempfile.gettempdir()) / "pyawb-preview"
    folder.mkdir(exist_ok=True)
    path = folder / "preview.html"
    path.write_text(page, encoding="utf-8")
    return path
