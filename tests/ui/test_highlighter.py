"""The Qt highlighter: formats land on the right UTF-16 ranges and follow multi-line state."""

import json
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QTextDocument
from PySide6.QtWidgets import QPlainTextEdit
from pytestqt.qtbot import QtBot

from pyawb.editor.mwconfig import default_config, from_siteinfo
from pyawb.ui.highlighter import WikitextHighlighter, utf16_offsets

DATA = Path(__file__).parents[1] / "editor" / "data"


def at(doc: QTextDocument, line: int, index: int) -> tuple[QColor, bool] | None:
    """(foreground, bold) of the format covering a UTF-16 position of a line, None if plain."""
    block = doc.findBlockByNumber(line)
    for r in block.layout().formats():
        if r.start <= index < r.start + r.length:
            return r.format.foreground().color(), r.format.fontWeight() == QFont.Weight.Bold
    return None


def find(doc: QTextDocument, line: int, piece: str) -> tuple[QColor, bool] | None:
    """The format of every UTF-16 position of piece, which must be the same throughout."""
    text = doc.findBlockByNumber(line).text()
    offsets = utf16_offsets(text)  # block.text() is a str; format ranges are UTF-16
    start, end = offsets[text.index(piece)], offsets[text.index(piece) + len(piece)]
    looks = {
        (None if f is None else (f[0].name(), f[1]))
        for f in (at(doc, line, i) for i in range(start, end))
    }
    assert len(looks) == 1, f"{piece!r} is not formatted uniformly: {looks}"
    return at(doc, line, start)


def new_editor(qtbot: QtBot) -> QPlainTextEdit:
    """An editor, as in the app: highlight its document (a bare QTextDocument has no layout,
    and Qt then does not report edits to the highlighter)."""
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    return editor


TEMPLATE = QColor("#8800cc")
LINK = QColor("#000aaa")


def test_template_and_link_colours(qtbot: QtBot) -> None:
    editor = new_editor(qtbot)
    doc = editor.document()
    h = WikitextHighlighter(doc, default_config())  # noqa: F841 (keep the Python object alive)
    doc.setPlainText("{{Infobox|name=x}} [[Kerala]]")
    assert find(doc, 0, "Infobox") == (TEMPLATE, True)
    found = find(doc, 0, "Kerala")
    assert found is not None and found[0] == LINK


def test_multi_line_state_follows_edits(qtbot: QtBot) -> None:
    editor = new_editor(qtbot)
    doc = editor.document()
    h = WikitextHighlighter(doc, default_config())  # noqa: F841 (keep the Python object alive)
    doc.setPlainText("text\n| name = value\n}}")
    assert find(doc, 1, " name =") is None
    # opening a template on line 1 re-highlights the following lines
    cursor = doc.find("text")
    cursor.insertText("{{Infobox")
    assert find(doc, 1, " name =") == (QColor("#bb00cc"), False)  # template argument name
    assert find(doc, 2, "}}") == (TEMPLATE, True)
    # and closing it earlier undoes that
    cursor = doc.find("{{Infobox")
    cursor.insertText("{{Infobox}}")
    assert find(doc, 1, " name =") is None


def test_astral_characters_use_utf16_positions(qtbot: QtBot) -> None:
    assert utf16_offsets("a𠀋b") == [0, 1, 3, 4]
    editor = new_editor(qtbot)
    doc = editor.document()
    h = WikitextHighlighter(doc, default_config())  # noqa: F841 (keep the Python object alive)
    doc.setPlainText("𠀋 [[𠀋𠀋]] x")
    found = find(doc, 0, "𠀋𠀋")
    assert found is not None and found[0] == LINK
    assert at(doc, 0, 0) is None


def test_malayalam_wiki_config(qtbot: QtBot) -> None:
    query = json.loads((DATA / "mlwiki_siteinfo.json").read_text(encoding="utf-8"))["query"]
    editor = new_editor(qtbot)
    doc = editor.document()
    h = WikitextHighlighter(doc, default_config())
    doc.setPlainText("{{എങ്കിൽ:a|b}}")
    assert find(doc, 0, "എങ്കിൽ") == (TEMPLATE, True)  # a template name on English Wikipedia
    h.set_config(from_siteinfo(query))
    assert find(doc, 0, "എങ്കിൽ") == (QColor("#aa1111"), True)  # Malayalam {{if:}}
