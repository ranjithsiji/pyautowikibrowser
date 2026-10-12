# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
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

from awb_l import __version__


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"AWB-L {__version__}")
        self.resize(1000, 700)
        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("editor")
        self.setCentralWidget(self.editor)

    def set_text_direction(self, rtl: bool) -> None:
        """Set editor direction from the wiki's siteinfo `rtl` flag."""
        direction = Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        self.editor.setLayoutDirection(direction)
        option = self.editor.document().defaultTextOption()
        option.setTextDirection(direction)
        self.editor.document().setDefaultTextOption(option)
