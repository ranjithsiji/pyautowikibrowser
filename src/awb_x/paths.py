# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""Where AWB-X keeps its files on each OS.

| | Linux | macOS | Windows |
|---|---|---|---|
| config | $XDG_CONFIG_HOME/awb-x | ~/Library/Application Support/awb-x | %APPDATA%\\awb-x |
| data | $XDG_DATA_HOME/awb-x | ~/Library/Application Support/awb-x | %LOCALAPPDATA%\\awb-x |

AWB_X_HOME overrides both (portable installs, tests).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR = "awb-x"


def _home_override() -> Path | None:
    home = os.environ.get("AWB_X_HOME")
    return Path(home) if home else None


def config_dir() -> Path:
    """User settings (config.toml)."""
    if (home := _home_override()) is not None:
        return home
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_DIR
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / APP_DIR


def data_dir() -> Path:
    """Caches and pywikibot's files (cookies, throttle, API cache)."""
    if (home := _home_override()) is not None:
        return home
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_DIR
