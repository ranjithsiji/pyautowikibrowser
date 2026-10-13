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

Layout after AWB's (docs/design/awb-ui-reference.md): the page list full height on the left; the
diff above (shown once a page is loaded) and, below it, the control tabs (Options, More, Skip,
Start) and the edit tabs (Edit box, Logs). A toolbar that is always visible moves through the list
(Start/Stop, Previous/Next, Save/Skip, Preview/Diff) and shows the progress.

The page-by-page work runs in pyawb.editloop, off the UI thread; this window holds the state
between steps. Unlike AWB, pages the loop is done with stay in the list, marked saved or skipped,
so the loop can go back to them.
"""

from __future__ import annotations

import html
import json
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import Any

from PySide6.QtCore import QLocale, Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDesktopServices,
    QFont,
    QKeySequence,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from pyawb import __version__, paths
from pyawb.api import connect, credentials
from pyawb.api.session import WikiSession
from pyawb.api.typolist import fetch_english_typo_list, fetch_typo_list
from pyawb.core import process, tools
from pyawb.core.article import Article
from pyawb.core.site import SiteConfig, current_site, use_site
from pyawb.editloop import EditLoop, LoadResult, LoopOptions, Mode, available_modes
from pyawb.editor import mwconfig
from pyawb.editor.dialogs import SearchReplace
from pyawb.editor.diffhtml import DiffColors
from pyawb.editor.messages import Messages
from pyawb.editor.mwconfig import MwConfig, default_config
from pyawb.editor.toolbar import ToolbarSite, build_toolbar
from pyawb.lists.listmaker import ArticleList
from pyawb.lists.sources import WikiContext, wiki_context
from pyawb.rules import typos
from pyawb.rules.typos import RegExTypoFix
from pyawb.settings import appconfig
from pyawb.settings.preferences import Preferences, is_rtl_language, script_for_language
from pyawb.ui import theme
from pyawb.ui.diff_view import DiffView
from pyawb.ui.editor_dialogs import DIALOGS, EditorDialogs, Suggest
from pyawb.ui.editor_toolbar import WikiEditorToolbar, select
from pyawb.ui.highlighter import WikitextHighlighter
from pyawb.ui.icons import codex_icon
from pyawb.ui.info_bar import Info, InfoBar
from pyawb.ui.list_maker import ListMaker
from pyawb.ui.login_dialog import LoginDialog
from pyawb.ui.logs_tab import LogsTab
from pyawb.ui.options_panel import OptionsError, OptionsPanel
from pyawb.ui.settings_dialog import SettingsDialog
from pyawb.ui.start_screen import StartResult
from pyawb.ui.start_tab import StartTab
from pyawb.ui.tasks import run_task

RECENT_FILE = "recent_characters.json"


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


class _Rate:
    """Events in the last minute (AWB's Pages/min, Edits/min)."""

    def __init__(self) -> None:
        self.times: deque[float] = deque()

    def add(self) -> None:
        self.times.append(time.monotonic())

    def per_minute(self) -> int:
        now = time.monotonic()
        while self.times and now - self.times[0] > 60:
            self.times.popleft()
        return len(self.times)


class MainWindow(QMainWindow):
    def __init__(self, language: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"PyAutoWikiBrowser {__version__}")
        self.resize(1280, 820)

        self.config = self._load_config()
        self.session: WikiSession | None = None
        self.loop: EditLoop | None = None
        self.current: LoadResult | None = None
        self.current_index = -1  # the list entry being worked on
        self.running = False  # Play pressed and not stopped
        self.busy = False  # a background step is running
        self.edits = self.skips = self.new_pages = 0
        self.edit_rate, self.page_rate = _Rate(), _Rate()
        self.typos: RegExTypoFix | None = None  # the wiki's typo list, loaded on first use
        self.typos_loading = False
        self.opts: LoopOptions | None = None  # the options the current page was processed with
        self.find_state = SearchReplace()
        self.lang = language or ui_language()
        self.mode = Mode.READ_ONLY
        self.paused = False  # one page at a time: no automatic step after Save
        self.next_index = -1  # paused after a save: the page Next goes to

        # -- edit box (editor toolbar, this page's summary, the editor) --
        edit_box = QWidget(self)
        eb = QVBoxLayout(edit_box)
        eb.setContentsMargins(0, 0, 0, 0)
        eb.setSpacing(0)
        self.editor = QPlainTextEdit(edit_box)
        self.editor.setObjectName("editor")
        self.highlighter = WikitextHighlighter(self.editor.document(), default_config())
        self.messages = Messages(self.lang)
        self.site = ToolbarSite()
        self.toolbar = WikiEditorToolbar(
            self.editor,
            build_toolbar(self.messages, self.site, recent_characters=_load_recent()),
            self.messages,
            dialogs=DIALOGS,
            parent=edit_box,
        )
        self.toolbar.recent_changed.connect(_save_recent)
        self.dialogs = EditorDialogs(self.editor, self.messages, self.site, open_url=self.open_url)
        self.toolbar.dialog_requested.connect(self.dialogs.open)
        self.review_summary = QComboBox(edit_box)
        self.review_summary.setEditable(True)
        self.review_summary.setObjectName("reviewSummary")
        edit = self.review_summary.lineEdit()
        if edit is not None:
            edit.setPlaceholderText(self.tr("Edit summary for this page"))
        eb.addWidget(self.toolbar)
        eb.addWidget(self.review_summary)
        eb.addWidget(self.editor, 1)

        self.logs = LogsTab(self)
        self.edit_tabs = QTabWidget(self)
        self.edit_tabs.setObjectName("editTabs")
        self.edit_tabs.addTab(edit_box, self.tr("Edit box"))
        self.edit_tabs.addTab(self.logs, self.tr("Logs"))

        # -- control tabs (Options, More, Skip from the panel; Start) --
        self.options = OptionsPanel(self)
        self.options.typos_toggled.connect(self._typos_toggled)
        self.start_tab = StartTab(self)
        self.options.addTab(self.start_tab, self.tr("Start"))
        self.options.setCurrentWidget(self.start_tab)
        self.summary = self.start_tab.summary
        self.minor = self.start_tab.minor
        self.watch = self.start_tab.watch
        self.start_tab.find_requested.connect(self.find_in_editor)
        self.save_button = self.start_tab.save
        self.skip_button = self.start_tab.skip
        self.diff_button = self.start_tab.diff
        self.preview_button = self.start_tab.preview
        self.start_tab.start.clicked.connect(self.start)
        self.start_tab.stop.clicked.connect(self.stop)
        self.save_button.clicked.connect(self.save)
        self.skip_button.clicked.connect(lambda: self.skip_page("user"))
        self.diff_button.clicked.connect(self.show_diff)
        self.preview_button.clicked.connect(self.preview)

        # -- the diff, above the control and edit tabs; hidden until a page is loaded --
        self.diff = DiffView(self)
        self.diff.line_clicked.connect(self.go_to_line)
        self.diff.hide()
        bottom = QSplitter(Qt.Orientation.Horizontal, self)
        bottom.addWidget(self.options)
        bottom.addWidget(self.edit_tabs)
        bottom.setStretchFactor(0, 0)
        bottom.setStretchFactor(1, 1)
        self.bottom_splitter = bottom
        self._sized = False
        self.splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.splitter.addWidget(self.diff)
        self.splitter.addWidget(bottom)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        # -- the list, full height on the left --
        self.list_maker = ListMaker(self)
        self.list_maker.status.connect(self.set_status)
        self.list_maker.changed.connect(self._update_buttons)
        self.logs.add_to_list.connect(self._add_titles)
        dock = QDockWidget(self.tr("Make list"), self)
        dock.setObjectName("listDock")
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        dock.setWidget(self.list_maker)
        self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self.info_bar = InfoBar(self)
        info = QToolBar(self.tr("Information"), self)
        info.setObjectName("infoToolbar")
        info.setMovable(False)
        info.addWidget(self.info_bar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, info)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self._make_toolbar()
        self._make_statusbar()
        self._make_menus()
        self.apply_preferences(self.config.preferences)
        self._update_modes()
        self._update_counts()
        self._update_buttons()

    # -- toolbar, status bar, menus -----------------------------------------------------------

    def _make_toolbar(self) -> None:
        """Always visible: Start/Stop | Previous, Next | Save, Skip | Preview, Diff, and the
        progress through the list."""
        bar = QToolBar(self.tr("Pages"), self)
        bar.setObjectName("loopToolbar")
        bar.setMovable(False)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft

        def action(icon: str, text: str, slot: Any, key: str = "") -> QAction:
            a = QAction(codex_icon(icon, self.lang, rtl), text, self)
            a.triggered.connect(slot)
            if key:
                a.setShortcut(QKeySequence(key))
                a.setToolTip(
                    f"{text} ({QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText)})"
                )
            bar.addAction(a)
            return a

        # the mode first, the active one highlighted; only those the user may use are shown
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_actions: dict[Mode, QAction] = {}
        for mode, icon, text, tip in (
            (Mode.READ_ONLY, "eye", self.tr("Read only"),
             self.tr("Open and show pages as they are; nothing is changed or saved")),
            (Mode.DRY_RUN, "labFlask", self.tr("Dry run"),
             self.tr("Make the changes and show the diff, but never save")),
            (Mode.EDIT, "edit", self.tr("Make changes"),
             self.tr("Make the changes, show the diff and save")),
        ):  # fmt: skip
            a = QAction(codex_icon(icon, self.lang, rtl), text, self)
            a.setCheckable(True)
            a.setToolTip(tip)
            a.triggered.connect(lambda _=False, m=mode: self.set_mode(m))
            self.mode_group.addAction(a)
            bar.addAction(a)
            button = bar.widgetForAction(a)
            if button is not None:
                button.setObjectName("modeButton")
            self.mode_actions[mode] = a
        bar.addSeparator()
        self.start_action = action("play", self.tr("Start"), self.start)
        self.stop_action = action("stop", self.tr("Stop"), self.stop)
        bar.addSeparator()
        self.previous_action = action("previous", self.tr("Previous"), self.previous_page)
        self.pause_action = action("pause", self.tr("Pause"), self.set_paused)
        self.pause_action.setCheckable(True)
        self.pause_action.setToolTip(
            self.tr("Go one page at a time with Previous and Next (Skip still moves on)")
        )
        pause_button = bar.widgetForAction(self.pause_action)
        if pause_button is not None:
            pause_button.setObjectName("modeButton")
        self.next_action = action("next", self.tr("Next"), self.next_page)
        bar.addSeparator()
        self.save_action = action("check", self.tr("Save"), self.save, "Ctrl+S")
        self.skip_action = action(
            "arrowNext", self.tr("Skip"), lambda: self.skip_page("user"), "Ctrl+I"
        )
        bar.addSeparator()
        self.preview_action = action("eye", self.tr("Preview"), self.preview, "Ctrl+E")
        self.diff_action = action("diffs", self.tr("Diff"), self.show_diff, "Ctrl+D")
        bar.addSeparator()
        self.position_label = QLabel(self)
        self.position_label.setObjectName("positionLabel")
        self.progress = QProgressBar(self)
        self.progress.setObjectName("listProgress")
        self.progress.setTextVisible(False)
        self.progress.setMaximumWidth(220)
        bar.addWidget(self.position_label)
        bar.addWidget(self.progress)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, bar)
        self.loop_toolbar = bar

    def _make_statusbar(self) -> None:
        self.status_label = QLabel(self.tr("Not logged in"), self)
        self.counts_label = QLabel(self)
        self.wiki_label = QLabel(self)
        self.user_label = QLabel(self)
        self.user_label.setObjectName("userLabel")
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.counts_label)
        self.statusBar().addPermanentWidget(self.wiki_label)
        self.statusBar().addPermanentWidget(self.user_label)
        self._update_user()

    def _make_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&File"))
        self.login_action = QAction(self.tr("Log in/Profiles…"), self)
        self.login_action.setShortcut(QKeySequence("Ctrl+L"))
        self.login_action.triggered.connect(self.log_in)
        self.logout_action = QAction(self.tr("Log out"), self)
        self.logout_action.triggered.connect(self.log_out)
        refresh = QAction(self.tr("Refresh status/typos"), self)
        refresh.setShortcut(QKeySequence("Ctrl+R"))
        refresh.triggered.connect(self.refresh_typos)
        quit_action = QAction(self.tr("Exit"), self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addActions([self.login_action, self.logout_action, refresh])
        file_menu.addSeparator()
        file_menu.addAction(quit_action)

        list_menu = self.menuBar().addMenu(self.tr("&List"))
        lm = self.list_maker
        for text, slot in (
            (self.tr("Remove duplicates"), lm.remove_duplicates),
            (self.tr("Remove done pages"), lm.remove_done),
            (self.tr("Clear current list"), lm.clear_list),
        ):
            a = QAction(text, self)
            a.triggered.connect(slot)
            list_menu.addAction(a)

        settings_menu = self.menuBar().addMenu(self.tr("&Settings"))
        for text, page, key in (
            (self.tr("Theme…"), "theme", ""),
            (self.tr("Language…"), "language", ""),
            (self.tr("Fonts…"), "fonts", ""),
            (self.tr("User profiles…"), "profiles", ""),
            (None, "", ""),
            (self.tr("Preferences…"), "general", "Ctrl+P"),
        ):
            if text is None:
                settings_menu.addSeparator()
                continue
            a = QAction(text, self)
            if key:
                a.setShortcut(QKeySequence(key))
            a.triggered.connect(lambda _=False, p=page: self.open_settings(p))
            settings_menu.addAction(a)

        view_menu = self.menuBar().addMenu(self.tr("&View"))
        self.show_diff_action = QAction(self.tr("Show the diff pane"), self)
        self.show_diff_action.setCheckable(True)
        self.show_diff_action.toggled.connect(self.diff.setVisible)
        view_menu.addAction(self.show_diff_action)

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
            self.tr("Pages/min: %1  Edits/min: %2  Edits: %3  Skipped: %4  New: %5")
            .replace("%1", str(self.page_rate.per_minute()))
            .replace("%2", str(self.edit_rate.per_minute()))
            .replace("%3", str(self.edits))
            .replace("%4", str(self.skips))
            .replace("%5", str(self.new_pages))
        )
        self._update_progress()

    def _update_progress(self) -> None:
        articles = self.list_maker.articles
        total = len(articles)
        index = self.current_index if self.current_index >= 0 else articles.selected_index
        self.position_label.setText(f"{index + 1 if index >= 0 else 0} / {total}")
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(articles.done_count)

    def _update_user(self) -> None:
        if hasattr(self, "info_bar"):
            self._update_info()
        """AWB's user box: the name on green when logged in, red "User:" when not."""
        s = self.session
        logged_in = s is not None and s.user.is_logged_in
        self.user_label.setText(s.user.name if s is not None and logged_in else self.tr("User:"))
        self.user_label.setProperty("loggedIn", logged_in)
        self.user_label.style().unpolish(self.user_label)
        self.user_label.style().polish(self.user_label)

    def _update_buttons(self) -> None:
        page = self.current is not None and not self.busy
        articles = self.list_maker.articles
        has_pages = len(articles) > 0
        ready = self._can_run() and has_pages
        self.start_action.setEnabled(ready and not self.running)
        self.start_tab.start.setEnabled(ready and not self.running)
        index = self.current_index if self.current_index >= 0 else articles.selected_index
        # Previous and Next step by hand: while paused (a running batch moves by itself)
        target = self.next_index if self.current is None and self.next_index >= 0 else index + 1
        self.previous_action.setEnabled(self.paused and ready and index > 0)
        self.next_action.setEnabled(self.paused and ready and 0 <= target < len(articles))
        stop = self.running or self.busy or self.current is not None
        self.stop_action.setEnabled(stop)
        self.start_tab.stop.setEnabled(stop)
        editing = self.mode is not Mode.READ_ONLY
        saving = self.mode is Mode.EDIT
        for widget, on in (
            (self.save_button, page and saving),
            (self.save_action, page and saving),
            (self.skip_button, page and editing),
            (self.skip_action, page and editing),
            (self.diff_button, page and editing),
            (self.diff_action, page and editing),
            (self.preview_button, page),
            (self.preview_action, page),
        ):
            widget.setEnabled(on)
        self.logout_action.setEnabled(self.session is not None and not self.busy)
        self.login_action.setEnabled(not self.busy)
        self.list_maker.set_editable(not self.running and self.current is None)
        self._update_progress()

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
            return session, wiki_context(cfg, session)

        run_task(work, self._connected, self._connect_failed)

    def _connected(self, result: object) -> None:
        session, wiki = result  # type: ignore[misc]
        assert isinstance(session, WikiSession) and isinstance(wiki, WikiContext)
        self.use_session(session, wiki)

    def use_session(self, session: WikiSession, wiki: WikiContext | None = None) -> None:
        """Work on this (connected) wiki."""
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
        self.options.set_site(site)
        self.typos = None
        self.wiki_label.setText(site.url.replace("https://", "").replace(".org", ""))
        self._update_user()
        status = session.status
        if session.can_save:
            self.set_status(
                self.tr("Logged in, user and software enabled. Bot = %1, Admin = %2")
                .replace("%1", str(session.is_bot))
                .replace("%2", str(session.user.is_sysop))
            )
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
        if session.can_save:
            self.mode = Mode.EDIT
        self._update_modes()
        if self.options.fix_typos.isChecked() and self.mode is not Mode.READ_ONLY:
            self.load_typos()
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
        self.typos = None
        self.options.typo_status.setText(self.tr("Not loaded"))
        self.wiki_label.clear()
        self.list_maker.set_wiki(None, current_site())
        self.set_status(self.tr("Not logged in"))
        self._update_user()
        self._update_modes()
        self._update_buttons()

    def adopt_start(self, result: StartResult) -> None:
        """Begin with what the start screen set up: the session, its wiki and the first list."""
        self.config = result.config
        self.apply_preferences(result.config.preferences)
        if result.session is not None:
            self.use_session(result.session, result.wiki)
        if result.pages:
            self.list_maker.articles.add(list(result.pages))
            self.list_maker.refresh()

    def _add_titles(self, titles: list[str]) -> None:
        self.list_maker.articles.add([Article(t) for t in titles])
        self.list_maker.refresh()

    # -- moving through the list --------------------------------------------------------------

    def _logged_in(self) -> bool:
        return self.session is not None and self.session.user.is_logged_in

    def _update_modes(self) -> None:
        """Show the modes this user may use; fall back to the safest one available."""
        can_save = self.session is not None and self.session.can_save
        modes = available_modes(self._logged_in(), can_save)
        for mode, action in self.mode_actions.items():
            action.setVisible(mode in modes)
        if self.mode not in modes:
            self.mode = Mode.DRY_RUN if Mode.DRY_RUN in modes else Mode.READ_ONLY
        self.mode_actions[self.mode].setChecked(True)
        self._update_info()

    def _update_info(self) -> None:
        """The information bar: wiki, user, CheckPage approval, mode."""
        s = self.session
        names = {
            Mode.READ_ONLY: (self.tr("Read only"), "eye"),
            Mode.DRY_RUN: (self.tr("Dry run"), "labFlask"),
            Mode.EDIT: (self.tr("Make changes"), "edit"),
        }
        mode, icon = names[self.mode]
        if s is None:
            self.info_bar.show_info(Info(mode=mode, mode_icon=icon))
            return
        general = s.siteinfo.query.get("general", {}) if s.siteinfo else {}
        host = s.site.url.replace("https://", "").replace("http://", "")
        sitename = str(general.get("sitename", "")) or s.site.project
        groups = [g for g, on in (("bot", s.user.is_bot), ("admin", s.user.is_sysop)) if on]
        logged_in = self._logged_in()
        status = s.status
        note = ""
        if status is not None:
            note = status.status.value + (f": {status.reason}" if status.reason else "")
        self.info_bar.show_info(
            Info(
                project=s.site.project,
                # isolated, so a right-to-left site name does not reorder the host after it
                wiki=f"\u2068{sitename}\u2069 ({host})",
                user=s.user.name if logged_in else "",
                user_groups=", ".join(groups),
                approved=s.can_save if logged_in else None,
                approval_note=note,
                mode=mode,
                mode_icon=icon,
            )
        )

    def set_mode(self, mode: Mode) -> None:
        """Change the mode; the page shown (if any) is put aside, since it was loaded for the
        other mode."""
        if mode is self.mode:
            return
        self.stop()
        self.mode = mode
        self._update_modes()
        self.set_status(
            {
                Mode.READ_ONLY: self.tr("Read only: pages are shown, nothing is changed"),
                Mode.DRY_RUN: self.tr("Dry run: changes are shown, nothing is saved"),
                Mode.EDIT: self.tr("Make changes"),
            }[self.mode]
        )
        self._update_buttons()

    def _can_run(self) -> bool:
        if self.busy or self.loop is None or self.session is None:
            return False
        return self.mode in available_modes(self._logged_in(), self.session.can_save)

    def start(self) -> None:
        """Start (or go on with) the editing: from the selected page, or the next one not done."""
        if not self._can_run():
            return
        articles = self.list_maker.articles
        index = articles.selected_index
        if index < 0 or articles.items[index].list_status:
            index = articles.next_pending(max(index, 0))
            if index < 0:
                index = articles.next_pending(0)
        if index < 0:
            self.set_status(
                self.tr("No pages left in the list: make a list first")
                if not len(articles)
                else self.tr("The list is done")
            )
            return
        self.load_index(index)

    def _position(self) -> int:
        articles = self.list_maker.articles
        return self.current_index if self.current_index >= 0 else articles.selected_index

    def previous_page(self) -> None:
        """Load the page before this one in the list (saved and skipped pages too)."""
        index = self._position()
        if self._can_run() and index > 0:
            self.load_index(index - 1)

    def next_page(self) -> None:
        """Load the page after this one, leaving this one as it is (not marked skipped); after a
        save while paused, the page selected next."""
        if not self._can_run():
            return
        if self.current is None and self.next_index >= 0:
            self.load_index(self.next_index)
            return
        index = self._position()
        if index + 1 < len(self.list_maker.articles):
            self.load_index(index + 1)

    def set_paused(self, paused: bool) -> None:
        """Pause: stay on each page after saving and move with Previous / Next. Unpausing goes
        on to the next page if one is waiting."""
        self.paused = paused
        self.pause_action.setChecked(paused)
        if not paused and self.running and self.current is None and self.next_index >= 0:
            self.load_index(self.next_index)
            return
        self.set_status(
            self.tr("Paused: move with Previous and Next") if paused else self.tr("Resumed")
        )
        self._update_buttons()

    def load_index(self, index: int) -> None:
        """StartArticleProcessing for the list entry at index (done pages are processed again)."""
        if not self._can_run():
            return
        assert self.session is not None and self.loop is not None
        if (
            self.mode is Mode.EDIT
            and self.session.site.project != "custom"
            and not self.summary.currentText().strip()
        ):
            QMessageBox.warning(
                self, self.tr("Edit summary"), self.tr("Please enter an edit summary.")
            )
            self.stop()
            return
        if (
            self.mode is not Mode.READ_ONLY
            and self.options.fix_typos.isChecked()
            and self.typos is None
        ):
            # AWB loads the list before the first page; go on once it is there
            if not self.typos_loading:
                self.load_typos(then_index=index)
            return
        try:
            status = self.session.status
            config = status.config if status else None
            opts = self.options.loop_options(
                self.summary.currentText(),
                self.session.user.name,
                frozenset(config.no_genfixes) if config else frozenset(),
                frozenset(config.no_regex_typo_fix) if config else frozenset(),
                self.typos,
            )
        except OptionsError as e:
            QMessageBox.warning(self, self.tr("Skip options"), str(e))
            self.stop()
            return
        opts.mode = self.mode
        self.start_tab.remember_summary()
        articles = self.list_maker.articles
        if not 0 <= index < len(articles):
            self.stop()
            return
        self.running = True
        self._clear_page()
        self.next_index = -1
        self.current_index = index
        self.list_maker.select_index(index)
        loop, title = self.loop, articles.items[index].name
        self.opts = opts
        self._set_busy(True, self.tr("Loading %1…").replace("%1", title))
        run_task(lambda: loop.load(title, opts), self._loaded, self._step_failed)

    def _report_timeouts(self) -> None:
        """Rules that ran out of time on this page were skipped (rule 2): say which."""
        p = self.opts.process if self.opts else None
        slow: list[str] = []
        if p is not None and p.find_and_replace is not None:
            slow += [r.find for r in getattr(p.find_and_replace, "timed_out", ())]
        if p is not None and isinstance(p.typos, RegExTypoFix):
            slow += p.typos.timed_out
        if slow:
            self.set_status(
                self.tr("Rules skipped (too slow): %1").replace("%1", ", ".join(slow[:5]))
            )

    # -- typo fixing --------------------------------------------------------------------------

    def _typos_toggled(self, on: bool) -> None:
        if on and self.typos is None and not self.typos_loading and self.session is not None:
            self.load_typos()

    def refresh_typos(self) -> None:
        """File → Refresh status/typos: load the typo list again."""
        if self.session is not None and not self.typos_loading:
            self.typos = None
            if self.options.fix_typos.isChecked():
                self.load_typos()

    def load_typos(self, english: bool = False, then_index: int = -1) -> None:
        """Load the wiki's typo list (or English Wikipedia's) in the background; then_index: a
        page to load once it is there."""
        session = self.session
        if session is None:
            return
        cfg = self.config
        link = session.status.config.typo_link if session.status else ""

        def work() -> tuple[str, RegExTypoFix | None]:
            with use_site(session.site):
                if english:
                    where = "en: Wikipedia:AutoWikiBrowser/Typos"
                    text = fetch_english_typo_list(session)
                else:
                    loc, text = fetch_typo_list(
                        session,
                        link,
                        lambda lang, project: connect.wiki_transport(cfg, lang, project),
                    )
                    where = loc.title
                if not text.strip():
                    return where, None
                return where, RegExTypoFix(typos.parse(text))

        def done(result: object) -> None:
            self.typos_loading = False
            if session is not self.session:
                return  # logged in elsewhere meanwhile
            where, fixer = result  # type: ignore[misc]
            assert isinstance(where, str)
            if fixer is None:
                answer = QMessageBox.question(
                    self,
                    self.tr("Typo list"),
                    self.tr(
                        "No list of typos was found at %1. Would you like to use the list of "
                        "typos from the English Wikipedia? Only choose Yes if this is an English "
                        "wiki."
                    ).replace("%1", where),
                )
                if answer == QMessageBox.StandardButton.Yes and not english:
                    self.load_typos(english=True, then_index=then_index)
                else:
                    self._typos_unavailable(self.tr("No typo list"))
                return
            assert isinstance(fixer, RegExTypoFix)
            if not fixer.typos_loaded:
                self._typos_unavailable(fixer.error or self.tr("The typo list has no rules"))
                return
            self.typos = fixer
            loaded = self.tr("%1 typos loaded").replace("%1", str(fixer.typo_count))
            self.options.typo_status.setText(loaded + " (" + where + ")")
            self.set_status(loaded)
            if then_index >= 0:
                self.load_index(then_index)

        def failed(error: Exception) -> None:
            self.typos_loading = False
            if session is self.session:
                self._typos_unavailable(str(error) or type(error).__name__)

        self.typos_loading = True
        self.options.typo_status.setText(self.tr("Loading the typo list…"))
        run_task(work, done, failed)

    def _typos_unavailable(self, why: str) -> None:
        self.options.typo_status.setText(self.tr("Not loaded: %1").replace("%1", why))
        self.options.fix_typos.setChecked(False)

    # -- one page -----------------------------------------------------------------------------

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
        self._report_timeouts()
        if result.skipped:
            self.current = result
            self.skip_page(result.skip_reason or "")
            return

        self.current = result
        self.editor.setPlainText(tools.convert_from_local_line_endings(result.text))
        self.editor.moveCursor(self.editor.textCursor().MoveOperation.Start)
        self.review_summary.setEditText(result.summary)
        title = result.page.title if result.page else result.title
        self.setWindowTitle(f"PyAutoWikiBrowser – {title}")
        if result.article is not None:
            with use_site(self.session.site if self.session else current_site()):
                self.start_tab.set_page_info(process.page_info(result.text, result.article))
        if result.in_use:
            self.set_status(self.tr("This page has {{inuse}}: consider skipping it"))
        self.edit_tabs.setCurrentIndex(0)
        self.editor.setReadOnly(self.mode is Mode.READ_ONLY)
        self._update_buttons()
        if self.mode is Mode.READ_ONLY:
            self.set_status(self.tr("Read only: %1").replace("%1", title))
            return
        if self.config.preferences.on_load == "edit":
            self._set_busy(False, self.tr("Ready: Diff shows the changes"))
            self.editor.setFocus()
            return
        self.diff.show()
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
            self._set_busy(
                False,
                self.tr("Ready to save")
                if self.mode is Mode.EDIT
                else self.tr("Dry run: Skip or Next to go on (nothing is saved)"),
            )
            self.diff.show()
            self.diff.show_diff(
                str(rows),
                diff_colors(),
                rtl=rtl,
                hint=self.tr('Press the "Skip" button to skip to the next page.'),
                line_label=self.tr("Line $1:"),
                no_difference=self.tr("No changes"),
            )
            self.save_button.setFocus()

        run_task(lambda: loop.diff(result, text), done, self._step_failed)

    def go_to_line(self, line: int) -> None:
        """A click on the diff: put the editor's cursor at the start of that line."""
        block = self.editor.document().findBlockByNumber(max(line - 1, 0))
        if block.isValid():
            cursor = self.editor.textCursor()
            cursor.setPosition(block.position())
            self.editor.setTextCursor(cursor)
            self.edit_tabs.setCurrentIndex(0)
            self.editor.setFocus()
            self.editor.centerCursor()

    def find_in_editor(self, text: str, is_regex: bool, case_sensitive: bool) -> None:
        """The Start tab's Find: the next match in the editor (.NET regex syntax via core.rx)."""
        content = self.editor.toPlainText()
        cursor = self.editor.textCursor()
        self.find_state.offset = cursor.selectionEnd()
        result = self.find_state.run("find", content, text, "", case_sensitive, is_regex)
        if result.selection is not None:
            select(self.editor, *result.selection, content)
            self.editor.ensureCursorVisible()
            self.edit_tabs.setCurrentIndex(0)
        else:
            self.set_status(self.tr("Not found: %1").replace("%1", text))

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
        if self.current is None or self.loop is None or self.busy or self.mode is not Mode.EDIT:
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
        result = self.current
        self.edits += 1
        self.edit_rate.add()
        self.page_rate.add()
        if result is not None and result.page is not None and not result.page.exists:
            self.new_pages += 1
        if result is not None:
            self.logs.log_saved(result.page.title if result.page else result.title)
        self._update_counts()
        self._done_with_page(ArticleList.SAVED)

    def _save_failed(self, error: Exception) -> None:
        # the page stays loaded: the user may retry, edit or skip
        self._set_busy(False, self.tr("Save failed: %1").replace("%1", str(error)))
        QMessageBox.warning(self, self.tr("Save"), str(error) or type(error).__name__)

    def skip_page(self, reason: str) -> None:
        if self.current is None or self.busy:
            return
        self.skips += 1
        self.page_rate.add()
        title = self.current.page.title if self.current.page else self.current.title
        if reason == "user":
            self.logs.log_skipped(title, self.tr("User"), self.tr("Clicked ignore"))
            why = self.tr("skipped by you")
        else:
            self.logs.log_skipped(title, "AWB", reason)
            why = reason
        self.set_status(self.tr("Skipped %1: %2").replace("%1", title).replace("%2", why))
        self._update_counts()
        self._done_with_page(ArticleList.SKIPPED)

    def _done_with_page(self, status: str) -> None:
        """Mark the page done and go on with the next one not done (PageSaved / SkipPage)."""
        index = self.current_index
        self._clear_page()
        self.list_maker.mark(index, status)
        articles = self.list_maker.articles
        following = articles.next_pending(index + 1)
        if following >= 0:
            self.list_maker.select_index(following)
        # Skip always moves on; after a save, a paused loop waits for Next
        advance = status == ArticleList.SKIPPED or not self.paused
        if self.running and following >= 0 and advance:
            self.load_index(following)
            return
        self.current_index = -1
        if self.running and following >= 0:
            self.next_index = following
            self.set_status(self.tr("Saved. Paused: press Next for the next page"))
            self._update_buttons()
            return
        self.running = False
        if following < 0:
            self.set_status(self.tr("List complete!"))
        self._update_buttons()

    def _step_failed(self, error: Exception) -> None:
        """Loading or processing failed: stop, as AWB does, and keep the page in the list."""
        self._set_busy(False)
        self.stop()
        self.set_status(self.tr("Error: %1").replace("%1", str(error) or type(error).__name__))
        QMessageBox.warning(self, "PyAutoWikiBrowser", str(error) or type(error).__name__)

    def stop(self) -> None:
        self.running = False
        self.next_index = -1
        if not self.busy:
            self._clear_page()
            self.current_index = -1
            self.set_status(self.tr("Stopped"))
        self._update_buttons()

    def _clear_page(self) -> None:
        self.current = None
        self.editor.clear()
        self.diff.clear()
        if not self.show_diff_action.isChecked():
            self.diff.hide()
        self.review_summary.setEditText("")
        self.start_tab.set_page_info(None)
        self.setWindowTitle(f"PyAutoWikiBrowser {__version__}")
        self._update_buttons()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._sized:  # first show: the editor gets the room, the controls ~40%
            self._sized = True
            width = self.bottom_splitter.width()
            self.bottom_splitter.setSizes([width * 2 // 5, width - width * 2 // 5])

    def closeEvent(self, event: QCloseEvent) -> None:
        busy = self.running or self.current is not None
        if busy and self.config.preferences.warn_on_exit:
            answer = QMessageBox.question(
                self,
                self.tr("Close"),
                self.tr("A page is open or a run is going on. Close PyAutoWikiBrowser?"),
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self.running = False
        super().closeEvent(event)

    # -- settings -----------------------------------------------------------------------------

    def _wiki_script(self) -> str:
        """The script of the wiki being worked on (or the default profile's), for its fonts."""
        if self.session is not None:
            lang = self.session.site.lang_code
        else:
            profile = self.config.profile()
            lang = profile.lang if profile is not None else "en"
        return script_for_language(lang)

    def open_settings(self, page: str = "general") -> None:
        """Settings → Theme / Language / Fonts / User profiles / Preferences."""
        dialog = SettingsDialog(self.config, self._wiki_script(), page, self)
        if not dialog.exec():
            return
        config = dialog.updated_config()
        if config != self.config:
            try:
                appconfig.save(config)
            except OSError as e:
                QMessageBox.warning(self, self.tr("Settings"), str(e))
            self.config = config
        self.apply_preferences(config.preferences)

    def apply_preferences(self, prefs: Preferences) -> None:
        """Theme, interface language, fonts (for the wiki's script), word wrap."""
        app = QApplication.instance()
        if isinstance(app, QApplication):
            mode = theme.Mode(prefs.theme)
            theme.apply(app, mode)
            self.highlighter.set_dark(theme.resolve(mode) is theme.Mode.DARK)
            app.setLayoutDirection(
                Qt.LayoutDirection.RightToLeft
                if is_rtl_language(prefs.language or self.lang)
                else Qt.LayoutDirection.LeftToRight
            )
        language = prefs.language or ui_language()
        if language != self.lang:
            self.lang = language
            self.messages = Messages(language, self.site.sitename)
            self.set_site(self.site, self.session.site.rtl if self.session else False)
        fonts = prefs.font_for(self._wiki_script())
        editor_font = QFont(fonts.editor) if fonts.editor else QFont()
        if fonts.editor_size:
            editor_font.setPointSize(fonts.editor_size)
        self.editor.setFont(editor_font)
        self.list_maker.list.setFont(editor_font)  # the titles are in the wiki's script
        self.highlighter.rehighlight()
        self.diff.setFont(QFont(fonts.diff) if fonts.diff else editor_font)
        if isinstance(app, QApplication) and fonts.interface:
            app.setFont(QFont(fonts.interface))
        self.editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if prefs.word_wrap
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

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
