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
"""Wikitext highlighting for the editor: pyawb.editor.tokenizer per text block (line).

Each block keeps a copy of the tokenizer state at its end (QTextBlockUserData). Qt highlights the
next block again only when a block's state number changes, so the number is a fingerprint of the
tokenizer state: an edit re-highlights from the changed line until the state is the same as
before.
"""

from __future__ import annotations

import zlib
from typing import Any

from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextBlockUserData,
    QTextCharFormat,
    QTextDocument,
)

from pyawb.editor import tokenizer as tk
from pyawb.editor.highlight_style import TextStyle, style_for
from pyawb.editor.mwconfig import MwConfig


class _StateData(QTextBlockUserData):
    def __init__(self, state: Any) -> None:
        super().__init__()
        self.state = state


def _args_key(args: tuple[Any, ...]) -> str:
    return repr(
        tuple(
            a if isinstance(a, str | int | float | bool | None) else type(a).__name__ for a in args
        )
    )


def _tok_key(t: tk.Tok) -> str:
    return t.name + _args_key(t.args)


def fingerprint(state: Any) -> int:
    """A number that changes when the tokenizer state at the end of a line changes."""
    if isinstance(state, dict):
        return zlib.crc32(repr(sorted((str(k), repr(v)) for k, v in state.items())).encode())  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    if not isinstance(state, tk.State):
        return 0
    dt = state.dt
    parts = (
        _tok_key(state.tokenize),
        tuple(_tok_key(t) for t in state.stack),
        tuple(state.in_html_tag),
        state.ext_name,
        type(state.ext_mode).__name__,
        state.n_template,
        state.n_ext,
        state.n_var,
        state.n_link,
        state.n_ext_link,
        state.lbrack,
        state.bold,
        state.italic,
        state.sof,
        repr(state.redirect),
        state.img_link,
        state.section,
        (dt.n, dt.html, dt.n_template, dt.n_ext, dt.n_var, dt.n_link, dt.n_ext_link, dt.ext_name),
        fingerprint(state.ext_state),
    )
    return zlib.crc32(repr(parts).encode()) & 0x3FFFFFFF


def utf16_offsets(text: str) -> list[int]:
    """Qt positions (UTF-16 code units) of each str index of text, and of its end."""
    out = [0] * (len(text) + 1)
    pos = 0
    for i, ch in enumerate(text):
        out[i] = pos
        pos += 2 if ord(ch) > 0xFFFF else 1
    out[len(text)] = pos
    return out


def char_format(style: TextStyle, base_point_size: float) -> QTextCharFormat:
    fmt = QTextCharFormat()
    if style.color is not None:
        fmt.setForeground(QColor(*style.color))
    if style.background is not None:
        fmt.setBackground(QColor(*style.background))
    if style.bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if style.italic:
        fmt.setFontItalic(True)
    if style.size != 1.0 and base_point_size > 0:
        fmt.setFontPointSize(base_point_size * style.size)
    return fmt


class WikitextHighlighter(QSyntaxHighlighter):
    """Highlights a QTextDocument as wikitext of the wiki described by config."""

    def __init__(self, document: QTextDocument, config: MwConfig, dark: bool = False) -> None:
        super().__init__(document)
        self._dark = dark
        self._formats: dict[str, QTextCharFormat] = {}
        self.set_config(config)

    def set_config(self, config: MwConfig) -> None:
        """Use another wiki's configuration (after switching wiki) and highlight again."""
        self._mw = tk.MediaWiki(config)
        self._parser = self._mw.mediawiki()
        self.rehighlight()

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        self._formats.clear()
        self.rehighlight()

    def _format(self, classes: str) -> QTextCharFormat:
        fmt = self._formats.get(classes)
        if fmt is None:
            size = self.document().defaultFont().pointSizeF()
            fmt = self._formats[classes] = char_format(style_for(classes, self._dark), size)
        return fmt

    def highlightBlock(self, text: str) -> None:
        previous = self.currentBlock().previous()
        data = previous.userData() if previous.isValid() else None
        if isinstance(data, _StateData):
            state = tk.copy_state(data.state)
        else:
            state = self._parser.start_state()
        # forget the previous line's look-ahead tokens (data is shared between line states)
        state.data.old_token = None
        try:
            tokens = tk.tokenize_line(self._parser, text, state)
        except RuntimeError:
            # a tokenizer bug must never break editing: leave the line plain
            tokens = []
            state = self._parser.start_state()
        offsets = utf16_offsets(text) if any(ord(c) > 0xFFFF for c in text) else None
        for start, end, classes in tokens:
            if not classes.strip():
                continue
            if offsets is not None:
                start, end = offsets[start], offsets[end]
            self.setFormat(start, end - start, self._format(classes))
        self.setCurrentBlockUserData(_StateData(tk.copy_state(state)))
        self.setCurrentBlockState(fingerprint(state))
