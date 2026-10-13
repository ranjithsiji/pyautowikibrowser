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
# After AutoWikiBrowser WikiFunctions/Controls/RegexTester.cs (GPL-2.0-or-later).
"""The regex tester's work (AWB's RegexTester form; also behind the Test… buttons of the
advanced find and replace): .NET syntax through core.rx, with a timeout."""

from __future__ import annotations

from dataclasses import dataclass

import regex

from pyawb.core.rx import DotNetMatch, DotNetOptions, DotNetRegex

__all__ = ["DotNetOptions", "RegexTest", "describe", "find", "options_from", "replace"]

TIMEOUT = 10.0  # seconds; a pattern that runs longer is reported, not waited for


@dataclass(frozen=True)
class RegexTest:
    matches: tuple[DotNetMatch, ...] = ()
    result: str = ""  # the text after the replacement (Replace only)
    error: str = ""
    groups: int = 0  # the highest numbered .NET group


def options_from(
    *, ignore_case: bool = False, multiline: bool = False, singleline: bool = False,
    explicit_capture: bool = False,
) -> DotNetOptions:  # fmt: skip
    opts = DotNetOptions.NONE
    if ignore_case:
        opts |= DotNetOptions.IGNORE_CASE
    if multiline:
        opts |= DotNetOptions.MULTILINE
    if singleline:
        opts |= DotNetOptions.SINGLELINE
    if explicit_capture:
        opts |= DotNetOptions.EXPLICIT_CAPTURE
    return opts


def find(pattern: str, options: DotNetOptions, text: str) -> RegexTest:
    """Every match of pattern in text (Find)."""
    try:
        rx = DotNetRegex(pattern, options)
        return RegexTest(tuple(rx.matches(text, timeout=TIMEOUT)), groups=_groups(rx))
    except TimeoutError:
        return RegexTest(error=f"The regex took more than {TIMEOUT:g} s")
    except (ValueError, regex.error) as e:
        return RegexTest(error=str(e))


def replace(pattern: str, replacement: str, options: DotNetOptions, text: str) -> RegexTest:
    """Text with every match replaced (.NET replacement syntax: $1, ${name}, $$)."""
    try:
        rx = DotNetRegex(pattern, options)
        matches = tuple(rx.matches(text, timeout=TIMEOUT))
        return RegexTest(
            matches, rx.replace(text, replacement, timeout=TIMEOUT), groups=_groups(rx)
        )
    except TimeoutError:
        return RegexTest(error=f"The regex took more than {TIMEOUT:g} s")
    except (ValueError, regex.error) as e:
        return RegexTest(error=str(e))


def _groups(rx: DotNetRegex) -> int:
    return max((k for k in rx.translated.group_map if isinstance(k, int)), default=0)


def describe(test: RegexTest) -> str:
    """The Result box for Find: each match with its position and groups."""
    if test.error:
        return test.error
    if not test.matches:
        return "No matches"
    lines = [f"{len(test.matches)} match(es)"]
    for n, m in enumerate(test.matches, 1):
        lines.append(f"{n}. [{m.index}] {m.value!r}")
        for g in range(1, test.groups + 1):
            lines.append(f"     ${g} = {m.group(g)!r}")
    return "\n".join(lines)
