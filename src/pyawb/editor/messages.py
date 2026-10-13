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
"""Interface messages for the editor toolbar, from WikiEditor's and MediaWiki core's i18n.

The messages are copied by tools/porting/wikieditor_data.py into data/wikieditor/messages/. A
message is looked up in the language, then its MediaWiki fallback chain, then English.

Message syntax supported (what the toolbar's messages use): $1..$9, {{PLURAL:}}, {{GENDER:}},
{{GRAMMAR:}}, {{SITENAME}}, and HTML entities. PLURAL picks explicit `n=` forms, else the first form
for 1 and the last otherwise: MediaWiki's per-language (CLDR) plural rules are not ported.
"""

from __future__ import annotations

import html
import json
from collections.abc import Mapping
from functools import cache
from importlib.resources import files

import regex

_DATA = files("pyawb.editor") / "data" / "wikieditor"

_PARAM = regex.compile(r"\$(\d)")
_MAGIC = regex.compile(
    r"\{\{\s*(PLURAL|GENDER|GRAMMAR|SITENAME)\s*(?::((?:[^{}]|\{\{(?2)\}\})*))?\}\}"
)


@cache
def _fallbacks() -> dict[str, list[str]]:
    return json.loads((_DATA / "fallbacks.json").read_text(encoding="utf-8"))


@cache
def _load(lang: str) -> dict[str, str]:
    f = _DATA / "messages" / f"{lang}.json"
    if not f.is_file():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def available_languages() -> list[str]:
    return sorted(p.name.removesuffix(".json") for p in (_DATA / "messages").iterdir())


def language_chain(lang: str) -> list[str]:
    """lang, its fallbacks (MediaWiki's $fallback), its base language, then English."""
    lang = lang.lower().replace("_", "-")
    chain = [lang, *_fallbacks().get(lang, [])]
    if "-" in lang:
        chain.append(lang.split("-")[0])
    chain.append("en")
    return list(dict.fromkeys(chain))


def _plural(n: str, forms: list[str]) -> str:
    try:
        number = float(n.replace(",", ""))
    except ValueError:
        number = 0
    plain = []
    for form in forms:
        m = regex.match(r"^\s*(\d+)\s*=(.*)$", form, flags=regex.S)
        if m:
            if float(m.group(1)) == number:
                return m.group(2)
        else:
            plain.append(form)
    if not plain:
        return ""
    return plain[0] if number == 1 else plain[-1]


class Messages:
    """Messages in one language with its fallback chain."""

    def __init__(self, lang: str, sitename: str = "", overrides: Mapping[str, str] | None = None):
        self.lang = lang
        self.sitename = sitename
        self._chain = [_load(code) for code in language_chain(lang)]
        self._overrides = dict(overrides or {})

    def raw(self, key: str) -> str:
        """The message text before parameters are filled, or `⧼key⧽` (as MediaWiki) when missing."""
        if key in self._overrides:
            return self._overrides[key]
        for messages in self._chain:
            text = messages.get(key)
            if text is not None:
                return text
        return f"⧼{key}⧽"

    def has(self, key: str) -> bool:
        return key in self._overrides or any(key in m for m in self._chain)

    def text(self, key: str, *params: str) -> str:
        """The message with $n replaced and the supported {{...}} expanded (MediaWiki's text())."""
        text = _PARAM.sub(
            lambda m: params[int(m.group(1)) - 1] if 0 < int(m.group(1)) <= len(params) else m[0],
            self.raw(key),
        )
        return html.unescape(self._expand(text))

    def _expand(self, text: str) -> str:
        def one(m: regex.Match[str]) -> str:
            name, arg = m.group(1), m.group(2)
            if name == "SITENAME":
                return self.sitename or "{{SITENAME}}"
            parts = self._expand(arg or "").split("|")
            if name == "PLURAL":
                return _plural(parts[0], parts[1:])
            if name == "GENDER":
                # GENDER:user|male|female|neutral; no gender known: neutral, else the first form
                forms = parts[1:]
                return forms[2] if len(forms) > 2 else (forms[0] if forms else "")
            return parts[-1]  # GRAMMAR:case|word -> word

        return _MAGIC.sub(one, text)
