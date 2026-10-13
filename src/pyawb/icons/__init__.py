# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# The logic of icon_svg follows resolveIcon/shouldIconFlip of @wikimedia/codex-icons (MIT).
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""PyAutoWikiBrowser's icon set: Wikimedia's Codex icons, as in MediaWiki's own interface.

codex-icons.json is converted from the @wikimedia/codex-icons 2.7.0 source by
tools/porting/codex_data.py. Package licence MIT (LICENSE);
the icon designs are CC BY 4.0, (C) Wikimedia Foundation Design System team and OOUI
contributors (README.md). See https://doc.wikimedia.org/codex/latest/icons/overview.html.
The same SVGs on every OS keep the look consistent; icon_svg draws them in the theme's colour.

Names are Codex's without the prefix: cdxIconBold is "bold", cdxIconListBullet "listBullet"
(the same names as OOUI's icons). An icon is one of:
- a string: the same drawing everywhere;
- {langCodeMap, default}: per-language drawings (bold is "B" in English, "F" in German, "ض" in
  Arabic...);
- {ltr, rtl}: separate drawings per direction;
- {ltr, shouldFlip[, shouldFlipExceptions]}: mirrored for rtl, except in the listed languages.
"""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from typing import Any

_DATA = files("pyawb.icons")
SIZE = 20  # Codex's design size (viewBox 0 0 20 20)


@cache
def _icons() -> dict[str, Any]:
    data = json.loads((_DATA / "codex-icons.json").read_text(encoding="utf-8"))
    return {k[len("cdxIcon")].lower() + k[len("cdxIcon") + 1 :]: v for k, v in data.items()}


def names() -> list[str]:
    return sorted(_icons())


def _base(lang: str) -> str:
    return lang.split("-")[0]


def resolve(name: str, lang: str = "en", rtl: bool = False) -> tuple[str, bool] | None:
    """(SVG contents, mirror it) for the interface language and direction; None if unknown."""
    icon = _icons().get(name)
    if icon is None:
        return None
    if isinstance(icon, str):
        return icon, False
    lang = lang.lower()
    if "langCodeMap" in icon:
        lang_map: dict[str, str] = icon["langCodeMap"]
        # Codex matches the exact code; falling back to the base language (de-at -> de) is ours
        return lang_map.get(lang) or lang_map.get(_base(lang)) or icon["default"], False
    if "shouldFlip" in icon:
        exceptions: list[str] = icon.get("shouldFlipExceptions", [])
        flip = rtl and lang not in exceptions and _base(lang) not in exceptions
        return icon["ltr"], flip
    return icon["rtl" if rtl else "ltr"], False


def icon_svg(
    name: str, lang: str = "en", rtl: bool = False, color: str = "#202122"
) -> bytes | None:
    """A standalone SVG document for the icon, drawn in color."""
    resolved = resolve(name, lang, rtl)
    if resolved is None:
        return None
    body, flip = resolved
    if flip:
        body = f'<g transform="translate({SIZE},0) scale(-1,1)">{body}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" '
        f'viewBox="0 0 {SIZE} {SIZE}" fill="{color}">{body}</svg>'
    ).encode()
