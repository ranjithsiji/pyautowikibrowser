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
"""Main window. Placeholder until the UI MVP (roadmap step 5)."""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QLocale, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget

from pyawb import __version__, paths
from pyawb.editor.messages import Messages
from pyawb.editor.mwconfig import MwConfig, default_config
from pyawb.editor.toolbar import ToolbarSite, build_toolbar
from pyawb.ui.editor_dialogs import DIALOGS, EditorDialogs, Suggest
from pyawb.ui.editor_toolbar import WikiEditorToolbar
from pyawb.ui.highlighter import WikitextHighlighter

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


class MainWindow(QMainWindow):
    def __init__(self, language: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"PyAutoWikiBrowser {__version__}")
        self.resize(1000, 700)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.editor = QPlainTextEdit(central)
        self.editor.setObjectName("editor")
        self.highlighter = WikitextHighlighter(self.editor.document(), default_config())
        self.messages = Messages(language or ui_language())
        self.site = ToolbarSite()
        self.toolbar = WikiEditorToolbar(
            self.editor,
            build_toolbar(self.messages, self.site, recent_characters=_load_recent()),
            self.messages,
            dialogs=DIALOGS,
            parent=central,
        )
        self.toolbar.recent_changed.connect(_save_recent)
        self.dialogs = EditorDialogs(self.editor, self.messages, self.site, open_url=self.open_url)
        self.toolbar.dialog_requested.connect(self.dialogs.open)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.editor, 1)
        self.setCentralWidget(central)

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
        """Set editor direction from the wiki's siteinfo `rtl` flag."""
        direction = Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        self.editor.setLayoutDirection(direction)
        option = self.editor.document().defaultTextOption()
        option.setTextDirection(direction)
        self.editor.document().setDefaultTextOption(option)
