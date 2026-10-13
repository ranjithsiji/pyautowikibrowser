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
# Port of CodeMirror 6's StringStream (@codemirror/language, MIT, (C) Marijn Haverbeke and others).
"""CodeMirror's StringStream: a cursor over one line, as the stream tokenizers expect it.

Positions are Python string indices (code points); CodeMirror counts UTF-16 code units. The Qt
highlighter converts. Regex patterns are `regex` patterns compiled with js_regex(), matched as
JavaScript's String.prototype.match does on the rest of the line: a match must start at the
current position, and lookbehind cannot see before it.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

import regex

_FLAGS = regex.VERSION0


@lru_cache(maxsize=4096)
def js_regex(source: str, ignore_case: bool = False) -> regex.Pattern[str]:
    """Compile a JavaScript regex source written with the `u` flag (and `i` if ignore_case)."""
    return regex.compile(source, _FLAGS | (regex.IGNORECASE if ignore_case else 0))


_SPACE = js_regex(r"[\s ]")

type Matcher = str | regex.Pattern[str] | Callable[[str], bool]


class StringStream:
    __slots__ = ("indent_unit", "pos", "start", "string")

    def __init__(self, string: str, indent_unit: int = 2) -> None:
        self.string = string
        self.pos = 0
        self.start = 0
        self.indent_unit = indent_unit

    def eol(self) -> bool:
        return self.pos >= len(self.string)

    def sol(self) -> bool:
        return self.pos == 0

    def peek(self) -> str | None:
        """The next character, None at the end of the line."""
        return self.string[self.pos] if self.pos < len(self.string) else None

    def next(self) -> str | None:
        if self.pos < len(self.string):
            self.pos += 1
            return self.string[self.pos - 1]
        return None

    def eat(self, match: Matcher) -> str | None:
        ch = self.string[self.pos] if self.pos < len(self.string) else ""
        if isinstance(match, str):
            ok = ch == match
        elif isinstance(match, regex.Pattern):
            ok = bool(ch) and match.search(ch) is not None
        else:
            ok = bool(ch) and match(ch)
        if ok:
            self.pos += 1
            return ch
        return None

    def eat_while(self, match: Matcher) -> bool:
        start = self.pos
        while self.eat(match):
            pass
        return self.pos > start

    def eat_space(self) -> bool:
        start = self.pos
        while self.pos < len(self.string) and _SPACE.match(self.string[self.pos]):
            self.pos += 1
        return self.pos > start

    def skip_to_end(self) -> None:
        self.pos = len(self.string)

    def skip_to(self, ch: str) -> bool:
        found = self.string.find(ch, self.pos)
        if found > -1:
            self.pos = found
            return True
        return False

    def back_up(self, n: int) -> None:
        self.pos -= n

    def match_str(self, pattern: str, consume: bool = True, case_insensitive: bool = False) -> bool:
        substr = self.string[self.pos : self.pos + len(pattern)]
        if (substr.lower() == pattern.lower()) if case_insensitive else (substr == pattern):
            if consume:
                self.pos += len(pattern)
            return True
        return False

    def match(self, pattern: regex.Pattern[str], consume: bool = True) -> regex.Match[str] | None:
        m = pattern.search(self.string[self.pos :])
        if m is None or m.start() > 0:
            return None
        if consume:
            self.pos += len(m[0])
        return m

    def current(self) -> str:
        return self.string[self.start : self.pos]
