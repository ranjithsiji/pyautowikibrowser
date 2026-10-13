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
"""The single entry point for regular expressions in PyAutoWikiBrowser.

Everything goes through the `regex` module with VERSION0 semantics. Every rule runs with a
timeout; a rule that times out is reported and skipped, never allowed to hang the caller.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass

import regex

from pyawb.core.dotnet_regex import (
    DotNetOptions,
    Replacement,
    TranslatedPattern,
    UnsupportedPatternError,
    escape,
    translate,
    translate_replacement,
)

__all__ = [
    "DEFAULT_TIMEOUT",
    "DotNetMatch",
    "DotNetOptions",
    "DotNetRegex",
    "Rule",
    "RuleResult",
    "UnsupportedPatternError",
    "compile",
    "compile_dotnet",
    "escape",
    "rule",
]

DEFAULT_TIMEOUT = 2.0
"""Seconds a single rule may run against one page before it is abandoned."""

Pattern = regex.Pattern[str]
Match = regex.Match[str]


@functools.lru_cache(maxsize=8192)
def compile(pattern: str, flags: int = 0) -> Pattern:
    """Compile a native `regex` pattern with VERSION0 semantics, cached."""
    return regex.compile(pattern, flags | regex.VERSION0)


@functools.lru_cache(maxsize=8192)
def _translate_cached(pattern: str, options: DotNetOptions) -> TranslatedPattern:
    return translate(pattern, options)


def compile_dotnet(pattern: str, options: DotNetOptions = DotNetOptions.NONE) -> Pattern:
    """Translate and compile a .NET pattern, cached."""
    tp = _translate_cached(pattern, options)
    return compile(tp.pattern, tp.flags)


@dataclass(frozen=True)
class RuleResult:
    text: str
    count: int
    timed_out: bool = False


@dataclass(frozen=True)
class Rule:
    """A find-and-replace rule written in .NET syntax (AWB rules, typo lists)."""

    translated: TranslatedPattern
    compiled: Pattern
    replacement: Replacement

    @property
    def source(self) -> str:
        return self.translated.source

    def search(self, text: str, timeout: float | None = DEFAULT_TIMEOUT) -> Match | None:
        return self.compiled.search(text, timeout=timeout)

    def apply(
        self, text: str, *, count: int = 0, timeout: float | None = DEFAULT_TIMEOUT
    ) -> RuleResult:
        """Replace matches in text. On timeout the text is returned unchanged."""
        repl = self.replacement
        try:
            if repl.is_literal:
                literal = "".join(p for p in repl.parts if isinstance(p, str))
                new, n = self.compiled.subn(lambda _m: literal, text, count=count, timeout=timeout)
            else:
                new, n = self.compiled.subn(repl, text, count=count, timeout=timeout)
        except TimeoutError:
            return RuleResult(text, 0, timed_out=True)
        return RuleResult(new, n)


def rule(find: str, replace: str, options: DotNetOptions = DotNetOptions.NONE) -> Rule:
    """Build a Rule from a .NET pattern and .NET replacement string."""
    tp = _translate_cached(find, options)
    return Rule(tp, compile(tp.pattern, tp.flags), translate_replacement(replace, tp))


# -- .NET-style API, for code ported from AWB -----------------------------------------------------

type GroupKey = int | str


class DotNetMatch:
    """A match whose group numbers follow .NET's numbering (System.Text.RegularExpressions.Match).

    Like .NET, a failed match is still a DotNetMatch: success is False, value is "" and every group
    is empty, so ported code such as ``r.match(s).group(1)`` works unchanged. It is falsy.
    Groups that did not participate give "" (as .NET's Group.Value does), never None.
    """

    __slots__ = ("_map", "m")

    def __init__(self, m: Match | None, group_map: dict[int, int]) -> None:
        self.m = m
        self._map = group_map

    def _key(self, key: GroupKey) -> GroupKey | None:
        """Python group for a .NET group number or name; None if the group does not exist."""
        if isinstance(key, int):
            return self._map.get(key)
        return key if self.m is not None and key in self.m.re.groupindex else None

    @property
    def success(self) -> bool:
        return self.m is not None

    def __bool__(self) -> bool:
        return self.m is not None

    @property
    def value(self) -> str:
        return "" if self.m is None else self.m.group(0)

    @property
    def index(self) -> int:
        return 0 if self.m is None else self.m.start()

    @property
    def length(self) -> int:
        return 0 if self.m is None else self.m.end() - self.m.start()

    def group(self, key: GroupKey = 0) -> str:
        """Groups[key].Value: "" for a failed match, a non-participating or unknown group."""
        k = self._key(key)
        if self.m is None or k is None:
            return ""
        return self.m.group(k) or ""

    def group_success(self, key: GroupKey) -> bool:
        """Groups[key].Success."""
        k = self._key(key)
        return self.m is not None and k is not None and self.m.start(k) >= 0

    def start(self, key: GroupKey = 0) -> int:
        """Groups[key].Index (0 when the group did not participate, as in .NET)."""
        k = self._key(key)
        return 0 if self.m is None or k is None else max(self.m.start(k), 0)

    def end(self, key: GroupKey = 0) -> int:
        k = self._key(key)
        return 0 if self.m is None or k is None else max(self.m.end(k), 0)

    def captures(self, key: GroupKey) -> list[str]:
        """Groups[key].Captures: every value the group captured, in order."""
        k = self._key(key)
        return [] if self.m is None or k is None else list(self.m.captures(k))

    def __repr__(self) -> str:
        if self.m is None:
            return "<DotNetMatch failed>"
        return f"<DotNetMatch {self.value!r} at {self.index}>"


class DotNetRegex:
    """A .NET pattern with a .NET-like API: is_match, match, matches, replace, split.

    Internal (non-user) regexes run without a timeout by default; the article pipeline that calls
    them runs in a worker with its own time limit. Pass timeout= to bound a single call.
    """

    __slots__ = ("compiled", "options", "translated")

    def __init__(self, pattern: str, options: DotNetOptions = DotNetOptions.NONE) -> None:
        self.translated = _translate_cached(pattern, options)
        self.options = options
        self.compiled = compile(self.translated.pattern, self.translated.flags)

    @property
    def pattern(self) -> str:
        """The original .NET pattern (Regex.ToString())."""
        return self.translated.source

    def __str__(self) -> str:
        return self.translated.source

    def __repr__(self) -> str:
        return f"DotNetRegex({self.translated.source!r}, {self.options!r})"

    def __add__(self, other: str) -> str:
        """C# allows ``regex + "text"`` (implicit ToString); AWB code builds patterns this way."""
        return self.translated.source + other

    def __radd__(self, other: str) -> str:
        return other + self.translated.source

    def is_match(self, text: str, start: int = 0, *, timeout: float | None = None) -> bool:
        return self.compiled.search(text, start, timeout=timeout) is not None

    def match(self, text: str, start: int = 0, *, timeout: float | None = None) -> DotNetMatch:
        """Regex.Match: the first match at or after start (a search, not an anchored match).

        Always returns a DotNetMatch; check .success (or truthiness), as in .NET.
        """
        m = self.compiled.search(text, start, timeout=timeout)
        return DotNetMatch(m, self.translated.group_map)

    def matches(
        self, text: str, start: int = 0, *, timeout: float | None = None
    ) -> list[DotNetMatch]:
        group_map = self.translated.group_map
        return [
            DotNetMatch(m, group_map) for m in self.compiled.finditer(text, start, timeout=timeout)
        ]

    def replace(
        self,
        text: str,
        replacement: str | Callable[[DotNetMatch], str],
        count: int = -1,
        *,
        timeout: float | None = None,
    ) -> str:
        """Regex.Replace. replacement is a .NET replacement string or a MatchEvaluator."""
        n = 0 if count < 0 else count
        if count == 0:
            return text
        if isinstance(replacement, str):
            return self.compiled.sub(
                translate_replacement(replacement, self.translated), text, count=n, timeout=timeout
            )
        group_map = self.translated.group_map
        evaluator = replacement

        def repl(m: Match) -> str:
            return evaluator(DotNetMatch(m, group_map))

        return self.compiled.sub(repl, text, count=n, timeout=timeout)

    def result(self, m: DotNetMatch, replacement: str) -> str:
        """Match.Result: the .NET replacement string expanded for a match of this regex."""
        if m.m is None:
            return ""
        return translate_replacement(replacement, self.translated)(m.m)

    def split(self, text: str, *, timeout: float | None = None) -> list[str]:
        """Regex.Split: the text between matches, plus what each .NET group captured.

        Groups that exist only because of the translation (balancing-group recursion) are left
        out, as .NET has no such captures. Groups that did not participate are skipped.
        """
        names = {v: k for k, v in self.compiled.groupindex.items()}
        groups = sorted(
            {
                py
                for py in self.translated.group_map.values()
                if py and not names.get(py, "").startswith("_bal")
            }
        )
        out: list[str] = []
        pos = 0
        for m in self.compiled.finditer(text, timeout=timeout):
            out.append(text[pos : m.start()])
            out.extend(m.group(g) for g in groups if m.start(g) >= 0)
            pos = m.end()
        out.append(text[pos:])
        return out
