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
#
# Port of src/math.ts and src/json.ts of @bhsd/codemirror-mediawiki 4.7.1
# (GPL-2.0-or-later, (C) Bhsd and others).
"""Highlighting inside <math>/<chem>/<ce> (TeX) and <templatedata>/<maplink>/<mapframe> (JSON).
These are TeX and JSON tokens, so digits, word characters and word boundaries are ASCII, as in
the original."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import regex

from pyawb.editor.stream import StringStream

_A = regex.VERSION0 | regex.ASCII
_LETTERS = regex.compile(r"[a-z]", _A | regex.IGNORECASE)
_DIGIT = regex.compile(r"[0-9]")
_TEX_ESCAPED = regex.compile(r"[,;!\\]")
_TEX_ATOM = regex.compile(r"[$&%#{}_]")
_TEX_NUMBER = regex.compile(r"[0-9]*(?:\.[0-9]*)?")
_TEX_OTHER = regex.compile(r"[^\\^&{}[\]().\w]", _A)


class MathParser:
    """math.ts (without the optional list of known TeX commands)."""

    def start_state(self) -> dict[str, Any]:
        return {}

    def token(self, stream: StringStream, state: Any) -> str:
        if stream.eat_space():
            return ""
        ch = stream.next() or ""
        if ch == "\\":
            if stream.eat_while(_LETTERS) or stream.eat(_TEX_ESCAPED):
                return "keyword"
            return "atom" if stream.eat(_TEX_ATOM) else "invalid"
        if ch in ("^", "_", "&"):
            return "operator"
        if ch in ("{", "}"):
            return "brace"
        if ch in ("[", "]"):
            return "squareBracket"
        if ch in ("(", ")"):
            return "paren"
        if ch == ".":
            return "number" if stream.eat_while(_DIGIT) else ""
        if _DIGIT.match(ch):
            stream.match(_TEX_NUMBER)
            return "number"
        if _LETTERS.match(ch):
            stream.eat_while(_LETTERS)
            return "variableName.special"
        stream.eat_while(_TEX_OTHER)
        return ""


_NUMBER = regex.compile(r"^[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?", _A | regex.IGNORECASE)
_PROPERTY = regex.compile(r"^\s*:")
_NULL = regex.compile(r"^ull\b", _A)
_TRUE = regex.compile(r"^rue\b", _A)
_FALSE = regex.compile(r"^alse\b", _A)
_WORD = regex.compile(r"[\w$]", _A)

type _JsonTok = Callable[[StringStream, dict[str, Any]], str]


def _eat_number(stream: StringStream, state: dict[str, Any]) -> str:
    if stream.match(_NUMBER):
        state["wb"] = False
        return "number"
    state["wb"] = True
    return ""


class JsonParser:
    """json.ts mkJson(jsoncMode)."""

    def __init__(self, jsonc: bool = False) -> None:
        self.jsonc = jsonc

    def _in_comment(self, stream: StringStream, state: dict[str, Any]) -> str:
        if stream.skip_to("*/"):
            stream.next()
            stream.next()
            state["tokenize"] = self._in_base
        else:
            stream.skip_to_end()
        return "comment"

    def _in_base(self, stream: StringStream, state: dict[str, Any]) -> str:
        if stream.eat_space():
            state["wb"] = True
            return ""
        ch = stream.next() or ""
        if ch in ("{", "}"):
            state["wb"] = True
            return "brace"
        if ch in ("[", "]"):
            state["wb"] = True
            return "squareBracket"
        if ch in (":", ","):
            state["wb"] = True
            return "separator"
        if ch == "/":
            state["wb"] = True
            if self.jsonc:
                if stream.eat("/"):
                    stream.skip_to_end()
                    return "comment"
                if stream.eat("*"):
                    state["tokenize"] = self._in_comment
                    return "comment"
            return ""
        if ch == '"':
            state["wb"] = True
            escaped = False
            nxt = stream.next()
            while nxt:
                if not escaped and nxt == '"':
                    break
                escaped = not escaped and nxt == "\\"
                nxt = stream.next()
            return "propertyName.definition" if stream.match(_PROPERTY, False) else "string"
        if ch == "-":
            if state["wb"]:
                return _eat_number(stream, state)
            state["wb"] = True
            return ""
        if state["wb"]:
            if _DIGIT.match(ch):
                stream.back_up(1)
                return _eat_number(stream, state)
            if ch == "n" and stream.match(_NULL):
                state["wb"] = False
                return "null"
            if (ch == "t" and stream.match(_TRUE)) or (ch == "f" and stream.match(_FALSE)):
                state["wb"] = False
                return "bool"
        state["wb"] = not _WORD.match(ch)
        return ""

    def start_state(self) -> dict[str, Any]:
        return {"tokenize": self._in_base, "wb": True}

    def token(self, stream: StringStream, state: dict[str, Any]) -> str:
        if stream.sol():
            state["wb"] = True
        tokenize: _JsonTok = state["tokenize"]
        return tokenize(stream, state)
