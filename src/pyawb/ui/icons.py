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
"""QIcons from the Codex icon set (pyawb.icons), in the palette's text colour.

Use these for every icon in the app instead of the OS icon theme, so it looks the same on Linux,
macOS and Windows.
"""

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer

from pyawb.icons import SIZE as ICON_SIZE
from pyawb.icons import icon_svg


def svg_icon(svg: bytes, size: int = ICON_SIZE) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg))
    icon = QIcon()
    for scale in (1, 2):
        pixmap = QPixmap(size * scale, size * scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        icon.addPixmap(pixmap)
    return icon


@cache
def _cached(name: str, lang: str, rtl: bool, color: str) -> QIcon:
    svg = icon_svg(name, lang, rtl, color)
    return svg_icon(svg) if svg is not None else QIcon()


def codex_icon(
    name: str, lang: str = "en", rtl: bool = False, palette: QPalette | None = None
) -> QIcon:
    """The Codex icon `name` for the interface language and direction (empty if unknown)."""
    palette = palette or QGuiApplication.palette()
    color = palette.color(QPalette.ColorRole.ButtonText).name()
    return _cached(name, lang.lower(), rtl, color)
