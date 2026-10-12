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
"""Application bootstrap."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from awb_l import __version__
from awb_l.ui import theme
from awb_l.ui.main_window import MainWindow


def run(argv: list[str]) -> int:
    app = QApplication(argv)
    app.setApplicationName("AWB-L")
    app.setApplicationVersion(__version__)
    theme.apply(app)
    window = MainWindow()
    window.show()
    return app.exec()
