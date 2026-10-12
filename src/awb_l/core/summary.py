# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/Summary.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Edit summary helpers (port of Summary.cs). Lengths are UTF-8 bytes, as MediaWiki counts."""

from __future__ import annotations

from awb_l.core import rx
from awb_l.core import wikiregexes as W
from awb_l.core.site import current_site

MaxLength = 255

_SummaryTrim = rx.DotNetRegex(r"\s*\[\[[^\[\]\r\n]+?\]\]$")


def _utf8_len(s: str) -> int:
    return len(s.encode("utf-8", "surrogatepass"))


def modified_section(original_text: str, article_text: str) -> str:
    """The heading of the only section that changed ("top" for the zeroth), or "" if none or
    several changed, or the number of sections changed."""
    from awb_l.core import tools

    before = tools.split_to_sections(original_text)
    after = tools.split_to_sections(article_text)
    if len(after) != len(before):
        return ""
    changed = [i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b]
    if len(changed) != 1:
        return ""
    heading = W.Headings.match(after[changed[0]]).group(1).strip()
    return heading or "top"


def trim(summary: str, summary_tag: str | None = None) -> str:
    """Shorten an edit summary to fit with the tool's tag appended (summary_tag defaults to the
    current wiki's)."""
    tag = current_site().summary_tag if summary_tag is None else summary_tag
    max_available = MaxLength - 5 - (len(tag) + 1)
    # replace the last wikilink with dots rather than break it
    if _utf8_len(summary) >= max_available and summary.endswith("]]"):
        summary = _SummaryTrim.replace(summary, "...")
    return (
        _limit_byte_length(summary, max_available)
        if _utf8_len(summary) > max_available
        else summary
    )


def is_correct(s: str) -> bool:
    """Whether the summary fits in 255 bytes and its [[links]] are balanced and not nested."""
    if _utf8_len(s) > MaxLength:
        return False
    res = True
    pos = s.find("[[")
    while pos >= 0:
        s = s[pos:]
        if res:
            # another link opened before this one closed: invalid
            close = s.find("]]")
            if "[[" in s[2 : 2 + (close if close > 0 else 0)]:
                return False
            pos = s.find("]]")
        else:
            pos = s.find("[[")
        res = not res
    return res


def _limit_byte_length(text: str, max_length: int) -> str:
    for i in range(len(text) - 1, -1, -1):
        if _utf8_len(text[: i + 1]) <= max_length:
            return text[: i + 1]
    return ""
