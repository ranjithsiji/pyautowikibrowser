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
"""Application bootstrap."""

from __future__ import annotations

import locale
import os
import sys
from collections.abc import MutableMapping

from PySide6.QtWidgets import QApplication

from pyawb import __version__
from pyawb.ui import theme
from pyawb.ui.main_window import MainWindow


def _locale_available(name: str) -> bool:
    saved = locale.setlocale(locale.LC_CTYPE)
    try:
        locale.setlocale(locale.LC_CTYPE, name)
    except locale.Error:
        return False
    finally:
        locale.setlocale(locale.LC_CTYPE, saved)
    return True


def ensure_utf8_ctype(env: MutableMapping[str, str]) -> str | None:
    """Make the character-type locale UTF-8, keeping the language (en_IN -> en_IN.UTF-8).

    With a non-UTF-8 locale such as LANG=en_IN (ISO-8859-1), Qt cannot load its compose table, so
    dead keys and compose sequences stop working, and xkbcommon prints errors. Only LC_CTYPE (or a
    non-UTF-8 LC_ALL) is changed. Returns the locale set, or None if nothing changed.
    """
    current = env.get("LC_ALL") or env.get("LC_CTYPE") or env.get("LANG") or ""
    if "utf-8" in current.lower() or "utf8" in current.lower():
        return None
    base = current.split(".")[0].split("@")[0]
    candidates = [f"{base}.UTF-8"] if base and base not in ("C", "POSIX") else []
    chosen = next((c for c in [*candidates, "C.UTF-8"] if _locale_available(c)), None)
    if chosen is None:
        return None
    env["LC_CTYPE"] = chosen
    if env.get("LC_ALL"):
        env["LC_ALL"] = chosen
    return chosen


def run(argv: list[str]) -> int:
    if sys.platform != "win32":
        ensure_utf8_ctype(os.environ)
    app = QApplication(argv)
    app.setApplicationName("PyAutoWikiBrowser")
    app.setApplicationVersion(__version__)
    theme.apply(app)
    window = MainWindow()
    window.show()
    return app.exec()
