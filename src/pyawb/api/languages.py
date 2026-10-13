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
"""Fetch Meta-Wiki's language list and site matrix (settings.languages holds and parses them)."""

from __future__ import annotations

from datetime import UTC, datetime

from pyawb.api.transport import Transport
from pyawb.settings.languages import (
    LANGUAGEINFO_PARAMS,
    SITEMATRIX_PARAMS,
    LanguageData,
    parse_languageinfo,
    parse_open_wikis,
)


def fetch_language_data(meta: Transport) -> LanguageData:
    """meta: Meta-Wiki's API (read-only; no login needed)."""
    languages = parse_languageinfo(meta.request(LANGUAGEINFO_PARAMS))
    wikis = parse_open_wikis(meta.request(SITEMATRIX_PARAMS))
    return LanguageData(datetime.now(UTC).date().isoformat(), languages, wikis)
