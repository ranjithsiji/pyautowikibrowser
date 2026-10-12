"""Port of AWB UnitTests/RegexAssert.cs and RegexTestsBase helpers.

RegexAssert.cs: Copyright (C) 2008 Max Semenik, zlib licence (compatible with GPL).
"""

from __future__ import annotations

from typing import Any

from awb_l.core.dotnet_regex import DotNetOptions
from awb_l.core.rx import DotNetRegex


def _regex(pattern: DotNetRegex | str, options: DotNetOptions = DotNetOptions.NONE) -> DotNetRegex:
    return pattern if isinstance(pattern, DotNetRegex) else DotNetRegex(pattern, options)


def _split(args: tuple[Any, ...]) -> tuple[DotNetRegex, str, str]:
    """(regex|pattern, [options,] input, [message])"""
    r, *rest = args
    if rest and isinstance(rest[0], DotNetOptions):
        opts, *rest = rest
        r = _regex(r, opts)
    return _regex(r), rest[0], rest[1] if len(rest) > 1 else ""


def is_match(*args: Any) -> None:
    r, text, msg = _split(args)
    assert r.is_match(text), f"<{text}> does not match <{r}> {msg}"


def no_match(*args: Any) -> None:
    r, text, msg = _split(args)
    assert not r.is_match(text), f"<{text}> matches <{r}> {msg}"


def matches(*args: Any) -> None:
    """Single result: (expected, regex|pattern, [options,] input, [message]).
    Multiple results: ([message,] regex, input, *expected)."""
    if isinstance(args[0], DotNetRegex):
        r, text, *expected = args
        assert [m.value for m in r.matches(text)] == expected
        return
    if isinstance(args[1], DotNetRegex) and len(args) > 4:
        msg, r, text, *expected = args
        assert [m.value for m in r.matches(text)] == expected, msg
        return
    items: list[Any] = list(args)
    r, text, msg = _split(tuple(items[1:]))
    expected = items[0]
    actual = r.match(text).value
    assert actual == expected, f"expected match <{expected}>, actual <{actual}> {msg}"


def not_matches(*args: Any) -> None:
    expected, rest = args[0], args[1:]
    r, text, msg = _split(rest)
    assert r.match(text).value != expected, f"unexpectedly matched <{expected}> {msg}"


def check_match(r: DotNetRegex, text: str, *args: Any) -> None:
    """RegexTestsBase.TestMatch: (r, text), (r, text, is_match) or (r, text, *groups)."""
    if not args:
        assert r.is_match(text), f"<{text}> does not match <{r}>"
        return
    if len(args) == 1 and isinstance(args[0], bool):
        assert r.is_match(text) == args[0]
        return
    m = r.match(text)
    assert len(r.translated.group_map) >= len(args), "Too few groups matched"
    for i, expected in enumerate(args):
        if expected is not None:
            assert m.group(i) == expected, f"group {i}: {m.group(i)!r} != {expected!r}"


def check_matches(r: DotNetRegex, text: str, expected_matches: int) -> None:
    """RegexTestsBase.TestMatches."""
    assert len(r.matches(text)) == expected_matches
