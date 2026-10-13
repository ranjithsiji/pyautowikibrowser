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
"""Languages and wikis, as Meta-Wiki lists them.

- meta=languageinfo: every language MediaWiki knows, with its autonym, English name and
  direction (the interface language list, and which interface languages are right to left);
- action=sitematrix: which projects exist in which language (the wiki list; closed wikis left out).

A snapshot ships in settings/data/meta-languages.json (written by tools/porting/meta_languages.py),
so the start screen works before logging in; api.languages fetches a fresh copy into the user's
data directory, which is used when it is newer.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from pyawb import paths

SNAPSHOT = "meta-languages.json"

LANGUAGEINFO_PARAMS: Mapping[str, str] = {
    "action": "query",
    "meta": "languageinfo",
    "liprop": "code|autonym|name|dir",
    "uselang": "en",
}
SITEMATRIX_PARAMS: Mapping[str, str] = {"action": "sitematrix", "smtype": "language"}

# sitematrix site codes -> project names as profiles use them
SITEMATRIX_PROJECTS: Mapping[str, str] = {
    "wiki": "wikipedia",
    "wiktionary": "wiktionary",
    "wikibooks": "wikibooks",
    "wikinews": "wikinews",
    "wikiquote": "wikiquote",
    "wikisource": "wikisource",
    "wikiversity": "wikiversity",
    "wikivoyage": "wikivoyage",
}


@dataclass(frozen=True)
class Language:
    code: str
    autonym: str  # the language's name in itself ("മലയാളം")
    name: str  # in English ("Malayalam")
    rtl: bool

    @property
    def label(self) -> str:
        """ "മലയാളം — Malayalam (ml)"."""
        if self.autonym and self.autonym != self.name:
            return f"{self.autonym} — {self.name} ({self.code})"
        return f"{self.name or self.code} ({self.code})"


@dataclass(frozen=True)
class LanguageData:
    fetched: str  # ISO date of the snapshot
    languages: Mapping[str, Language]
    wikis: Mapping[str, tuple[str, ...]]  # project -> open wikis' language codes

    def language(self, code: str) -> Language:
        return self.languages.get(code) or Language(code, code, code, False)

    def wiki_languages(self, project: str) -> list[Language]:
        """The languages a project has an open wiki in, by English name."""
        return sorted(
            (self.language(c) for c in self.wikis.get(project, ())),
            key=lambda lang: (lang.name.casefold(), lang.code),
        )


def parse_languageinfo(result: Mapping[str, Any]) -> dict[str, Language]:
    """meta=languageinfo (formatversion=2) -> code -> Language; codes without an autonym (aliases,
    deprecated codes) are left out."""
    info: Mapping[str, Mapping[str, Any]] = result.get("query", {}).get("languageinfo", {})
    out: dict[str, Language] = {}
    for code, item in info.items():
        autonym = str(item.get("autonym") or "")
        if not autonym:
            continue
        out[code] = Language(code, autonym, str(item.get("name") or code), item.get("dir") == "rtl")
    return out


def parse_open_wikis(result: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """action=sitematrix -> project -> the language codes of its open (not closed) wikis."""
    matrix: Mapping[str, Any] = result.get("sitematrix", {})
    per_project: dict[str, set[str]] = {p: set() for p in SITEMATRIX_PROJECTS.values()}
    for key, entry in matrix.items():
        if key in ("count", "specials") or not isinstance(entry, Mapping):
            continue
        lang: Mapping[str, Any] = entry  # pyright: ignore[reportUnknownVariableType]
        code = str(lang.get("code", ""))
        for site in lang.get("site", ()):
            project = SITEMATRIX_PROJECTS.get(str(site.get("code", "")))
            if project is not None and "closed" not in site and "private" not in site:
                per_project[project].add(code)
    return {p: tuple(sorted(codes)) for p, codes in per_project.items()}


def to_json(data: LanguageData) -> str:
    return json.dumps(
        {
            "fetched": data.fetched,
            "languages": {
                c: [lang.autonym, lang.name, "rtl" if lang.rtl else "ltr"]
                for c, lang in sorted(data.languages.items())
            },
            "wikis": {p: list(codes) for p, codes in sorted(data.wikis.items())},
        },
        ensure_ascii=False,
        indent=0,
    )


def from_json(text: str) -> LanguageData:
    raw = json.loads(text)
    languages = {
        c: Language(c, autonym, name, direction == "rtl")
        for c, (autonym, name, direction) in raw["languages"].items()
    }
    wikis = {p: tuple(codes) for p, codes in raw["wikis"].items()}
    return LanguageData(str(raw.get("fetched", "")), languages, wikis)


def cache_path() -> Path:
    return paths.data_dir() / SNAPSHOT


@cache
def load() -> LanguageData:
    """The newest of the bundled snapshot and the user's fetched copy (read once; save_cache
    clears it)."""
    bundled = from_json(files("pyawb.settings").joinpath("data", SNAPSHOT).read_text("utf-8"))
    try:
        cached = from_json(cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError):
        return bundled
    return cached if cached.fetched > bundled.fetched else bundled


def save_cache(data: LanguageData) -> None:
    try:
        cache_path().parent.mkdir(parents=True, exist_ok=True)
        cache_path().write_text(to_json(data), encoding="utf-8")
    except OSError:
        pass
    load.cache_clear()
