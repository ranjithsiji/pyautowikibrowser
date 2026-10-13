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
"""One look on every OS: Fusion style + a palette + a QSS stylesheet with Codex's design tokens.

Native styles (Windows 11, macOS Aqua, GTK) each interpret stylesheets differently, so we always
use Fusion, which draws every widget itself. The colours, radii and spacing are Wikimedia Codex
design tokens (https://doc.wikimedia.org/codex/latest/design-tokens/overview.html), light and
dark mode, converted by tools/porting/codex_data.py into styles/codex-tokens.json (Codex 2.7.0,
GPL-2.0-or-later, styles/codex-tokens.LICENSE). With the Codex icons (pyawb.icons) this gives
MediaWiki's own look.

QSS has no variables; `app.qss` uses `$token` placeholders: Codex's token names with `-` written
`_` (`$background_color_progressive` for `background-color-progressive`).

Only direction-neutral properties (symmetric padding/margins) belong in the stylesheet, so the
same rules work for RTL wikis.
"""

from __future__ import annotations

import enum
import json
import tempfile
from functools import cache
from importlib.resources import files
from pathlib import Path
from string import Template

import regex
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from pyawb.icons import icon_svg


class Mode(enum.StrEnum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


_RGBA = regex.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)")


def _qss_value(value: str) -> str:
    # QSS reads rgba() alpha as 0-255, CSS as 0-1: write #AARRGGBB instead
    m = _RGBA.fullmatch(value.strip())
    if m:
        r, g, b = (int(m.group(i)) for i in (1, 2, 3))
        a = round(float(m.group(4)) * 255)
        return f"#{a:02x}{r:02x}{g:02x}{b:02x}"
    return value


@cache
def codex_tokens() -> dict[str, dict[str, str]]:
    """Codex's tokens by mode ("light", "dark"), with Codex's names and CSS values."""
    text = files("pyawb.ui.styles").joinpath("codex-tokens.json").read_text(encoding="utf-8")
    data = json.loads(text)
    return {"light": data["light"], "dark": data["dark"]}


def resolve(mode: Mode) -> Mode:
    if mode is not Mode.SYSTEM:
        return mode
    scheme = QGuiApplication.styleHints().colorScheme()
    return Mode.DARK if scheme == Qt.ColorScheme.Dark else Mode.LIGHT


def tokens(mode: Mode) -> dict[str, str]:
    """The tokens for a mode as QSS placeholders: `-` -> `_`, values usable in QSS."""
    raw = codex_tokens()["dark" if resolve(mode) is Mode.DARK else "light"]
    return {name.replace("-", "_"): _qss_value(value) for name, value in raw.items()}


@cache
def _icon_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="pyawb-theme-"))


def _icon_url(name: str, color: str) -> str:
    """A file with a Codex icon in color, for QSS `image: url(...)` (QSS cannot take data)."""
    path = _icon_dir() / f"{name}-{color.lstrip('#')}.svg"
    if not path.exists():
        path.write_bytes(icon_svg(name, color=color) or b"")
    return path.as_posix()


def stylesheet(mode: Mode) -> str:
    template = files("pyawb.ui.styles").joinpath("app.qss").read_text(encoding="utf-8")
    t = tokens(mode)
    # Codex's checkbox mark: the check icon in the inverted colour
    t["icon_check"] = _icon_url("check", t["color_inverted_fixed"])
    # spin box arrows: Codex's chevrons
    t["icon_up"] = _icon_url("collapse", t["color_base"])
    t["icon_down"] = _icon_url("expand", t["color_base"])
    return Template(template).substitute(t)


def palette(mode: Mode) -> QPalette:
    """Palette matching the tokens, for anything the stylesheet does not cover."""
    t = {k: QColor(v) for k, v in tokens(mode).items() if QColor.isValidColorName(v)}
    p = QPalette()
    R = QPalette.ColorRole
    p.setColor(R.Window, t["background_color_neutral_subtle"])
    p.setColor(R.WindowText, t["color_base"])
    p.setColor(R.Base, t["background_color_base"])
    p.setColor(R.AlternateBase, t["background_color_interactive_subtle"])
    p.setColor(R.Text, t["color_base"])
    p.setColor(R.PlaceholderText, t["color_placeholder"])
    p.setColor(R.Button, t["background_color_interactive_subtle"])
    p.setColor(R.ButtonText, t["color_base"])
    p.setColor(R.Highlight, t["background_color_progressive_subtle"])
    p.setColor(R.HighlightedText, t["color_base"])
    p.setColor(R.ToolTipBase, t["background_color_base"])
    p.setColor(R.ToolTipText, t["color_base"])
    p.setColor(R.Link, t["color_progressive"])
    p.setColor(R.LinkVisited, t["color_visited"])
    p.setColor(R.BrightText, t["color_destructive"])
    for role in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, t["color_disabled"])
    return p


def apply(app: QApplication, mode: Mode = Mode.SYSTEM, *, force: bool = False) -> None:
    """Fusion, the palette and the stylesheet for mode (skipped if mode is already applied)."""
    if not force and app.property("pyawbTheme") == mode.value:
        return
    app.setProperty("pyawbTheme", mode.value)
    app.setStyle("Fusion")
    app.setPalette(palette(mode))
    app.setStyleSheet(stylesheet(mode))
