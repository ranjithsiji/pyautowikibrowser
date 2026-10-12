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
"""One look on every OS: Fusion style + a palette + a QSS stylesheet with colour tokens.

Native styles (Windows 11, macOS Aqua, GTK) each interpret stylesheets differently, so we always
use Fusion, which draws every widget itself. QSS has no variables; `app.qss` uses `$token`
placeholders filled from the token tables below.

Only direction-neutral properties (symmetric padding/margins) belong in the stylesheet, so the
same rules work for RTL wikis.
"""

from __future__ import annotations

import enum
from importlib.resources import files
from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication


class Mode(enum.StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


LIGHT: dict[str, str] = {
    "bg": "#f6f7f9",
    "surface": "#ffffff",
    "surface_alt": "#eef0f3",
    "border": "#d0d4da",
    "border_strong": "#a9b0ba",
    "text": "#1d2127",
    "text_muted": "#5d6570",
    "accent": "#3366cc",  # MediaWiki progressive blue
    "accent_hover": "#2a4b8d",
    "accent_text": "#ffffff",
    "selection": "#c9d8f5",
    "danger": "#d73333",
    "diff_add": "#d8f0dd",
    "diff_del": "#fbe1e1",
}

DARK: dict[str, str] = {
    "bg": "#1b1d21",
    "surface": "#23262b",
    "surface_alt": "#2c3036",
    "border": "#3a3f47",
    "border_strong": "#565d68",
    "text": "#e6e8eb",
    "text_muted": "#9aa2ad",
    "accent": "#6d8af0",
    "accent_hover": "#8ea5f5",
    "accent_text": "#0f1115",
    "selection": "#33467a",
    "danger": "#f07272",
    "diff_add": "#1f3a27",
    "diff_del": "#45242a",
}


def resolve(mode: Mode) -> Mode:
    if mode is not Mode.SYSTEM:
        return mode
    scheme = QGuiApplication.styleHints().colorScheme()
    return Mode.DARK if scheme == Qt.ColorScheme.Dark else Mode.LIGHT


def tokens(mode: Mode) -> dict[str, str]:
    return DARK if resolve(mode) is Mode.DARK else LIGHT


def stylesheet(mode: Mode) -> str:
    template = files("awb_l.ui.styles").joinpath("app.qss").read_text(encoding="utf-8")
    return Template(template).substitute(tokens(mode))


def palette(mode: Mode) -> QPalette:
    """Palette matching the tokens, for anything the stylesheet does not cover."""
    t = {k: QColor(v) for k, v in tokens(mode).items()}
    p = QPalette()
    R = QPalette.ColorRole
    p.setColor(R.Window, t["bg"])
    p.setColor(R.WindowText, t["text"])
    p.setColor(R.Base, t["surface"])
    p.setColor(R.AlternateBase, t["surface_alt"])
    p.setColor(R.Text, t["text"])
    p.setColor(R.PlaceholderText, t["text_muted"])
    p.setColor(R.Button, t["surface_alt"])
    p.setColor(R.ButtonText, t["text"])
    p.setColor(R.Highlight, t["selection"])
    p.setColor(R.HighlightedText, t["text"])
    p.setColor(R.ToolTipBase, t["surface"])
    p.setColor(R.ToolTipText, t["text"])
    p.setColor(R.Link, t["accent"])
    p.setColor(R.BrightText, t["danger"])
    for role in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, t["text_muted"])
    return p


def apply(app: QApplication, mode: Mode = Mode.SYSTEM) -> None:
    app.setStyle("Fusion")
    app.setPalette(palette(mode))
    app.setStyleSheet(stylesheet(mode))
