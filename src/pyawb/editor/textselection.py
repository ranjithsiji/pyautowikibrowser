# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# Ported from MediaWiki core's resources/src/jquery/jquery.textSelection.js (encapsulateSelection)
# and WikiEditor's modules/jquery.wikiEditor.toolbar.js (doAction), both GPL-2.0-or-later,
# (C) MediaWiki contributors.
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""Editor actions as functions over (text, selection): the toolbar's `encapsulate` and `replace`.

Positions are str indices (code points). The Qt editor converts its UTF-16 positions in and out.
Each function returns an Edit (replace text[start:end] with insert, then select sel_start..sel_end)
instead of a new text, so the editor can apply it as one undo step.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import regex


@dataclass(frozen=True, slots=True)
class EncapsulateOptions:
    """jquery.textSelection's encapsulateSelection options (same names, snake_case)."""

    pre: str = ""
    peri: str = ""
    post: str = ""
    ownline: bool = False
    replace: bool = False
    select_peri: bool = True
    splitlines: bool = False
    selection_start: int | None = None
    selection_end: int | None = None


@dataclass(frozen=True, slots=True)
class RegexReplace:
    """WikiEditor's `regex` + `regexReplace` options, hand-translated from JavaScript.

    `pattern` is a `regex` pattern with the JavaScript flags as inline flags; JavaScript's `$`
    without the m flag is written `\\Z`. `replacement` uses Python's syntax (`\\1`, not `$1`).
    `count=0` is JavaScript's g flag (replace all), 1 replaces the first match only.
    """

    pattern: str
    replacement: str
    count: int = 1

    def test(self, text: str) -> bool:
        return regex.search(self.pattern, text) is not None

    def apply(self, text: str) -> str:
        return regex.sub(self.pattern, self.replacement, text, count=self.count)


@dataclass(frozen=True, slots=True)
class TextAction:
    """A toolbar action that edits text: WikiEditor's 'encapsulate' or 'replace' type."""

    type: str  # "encapsulate" | "replace"
    options: EncapsulateOptions
    regex: RegexReplace | None = None


@dataclass(frozen=True, slots=True)
class Edit:
    """Replace text[start:end] with insert, then select sel_start..sel_end (in the new text)."""

    start: int
    end: int
    insert: str
    sel_start: int
    sel_end: int

    def apply(self, text: str) -> str:
        return text[: self.start] + self.insert + text[self.end :]


def encapsulate_selection(text: str, start: int, end: int, options: EncapsulateOptions) -> Edit:
    """Port of jquery.textSelection's encapsulateSelection for one selection start..end of text."""
    if options.selection_start is not None:
        start = options.selection_start
        end = options.selection_end if options.selection_end is not None else start
    start, end = min(start, end), max(start, end)
    pre, post = options.pre, options.post
    sel_text = text[start:end]
    is_sample = False

    # checkSelectedText
    if not sel_text:
        sel_text = options.peri
        is_sample = True
    elif options.replace:
        sel_text = options.peri
    else:
        while sel_text.endswith(" "):
            # Exclude ending space char
            sel_text = sel_text[:-1]
            post += " "
        while sel_text.startswith(" "):
            # Exclude prepending space char
            sel_text = sel_text[1:]
            pre = " " + pre

    if options.splitlines:
        insert_text = "\n".join(pre + line + post for line in sel_text.split("\n"))
    else:
        insert_text = pre + sel_text + post
    if options.ownline:
        if start != 0 and text[start - 1] not in "\n\r":
            insert_text = "\n" + insert_text
            pre += "\n"
        if end >= len(text) or text[end] not in "\n\r":
            insert_text += "\n"
            post += "\n"

    if is_sample and options.select_peri and (not options.splitlines or "\n" not in sel_text):
        sel_start = start + len(pre)
        sel_end = sel_start + len(sel_text)
    else:
        sel_start = sel_end = start + len(insert_text)
    return Edit(start, end, insert_text, sel_start, sel_end)


def do_action(text: str, start: int, end: int, action: TextAction) -> Edit:
    """Port of WikiEditor's toolbar doAction for 'encapsulate' and 'replace' actions."""
    options = action.options
    replace_ = action.type == "replace"
    rr = action.regex
    if rr is not None:
        selection = text[min(start, end) : max(start, end)]
        if selection != "" and rr.test(selection):
            options = replace(options, peri=rr.apply(selection), pre="", post="")
            replace_ = True
    return encapsulate_selection(text, start, end, replace(options, replace=replace_))
