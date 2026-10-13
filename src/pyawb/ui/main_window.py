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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QPlainTextEdit

from pyawb import __version__
from pyawb.editor.mwconfig import MwConfig, default_config
from pyawb.ui.highlighter import WikitextHighlighter


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"PyAutoWikiBrowser {__version__}")
        self.resize(1000, 700)
        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("editor")
        self.highlighter = WikitextHighlighter(self.editor.document(), default_config())
        self.setCentralWidget(self.editor)

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
