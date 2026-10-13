"""The edit box's context menu (AWB mnuTextBox) and the diff's double click."""

from typing import Any

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QInputDialog, QMessageBox
from pytestqt.qtbot import QtBot

from pyawb.settings import appconfig
from pyawb.ui.edit_box_menu import PasteMoreDialog
from pyawb.ui.main_window import MainWindow
from tests.ui.test_main_loop import window


def started(qtbot: QtBot, text: str = "حيوان [[أليف|أليف]] صغير.") -> tuple[MainWindow, Any]:
    w, t = window(qtbot, {"قط": text})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    return w, t


def titles(w: MainWindow) -> list[str]:
    return [a.text() for a in w.edit_box_menu.menu().actions() if not a.isSeparator()]


def select_range(w: MainWindow, start: int, end: int) -> None:
    cursor = w.editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    w.editor.setTextCursor(cursor)


def test_menu_items(qtbot: QtBot) -> None:
    w, _ = started(qtbot)
    assert titles(w) == [
        "Word wrap",
        "Undo",
        "Cut",
        "Copy",
        "Paste",
        "Paste more",
        "Select all",
        "Save text to file…",
        "Go to line",
        "Insert…",
        "Insert tag",
        "Convert list to",
        "Unicodify selected",
        "Bypass all redirects",
        "Fix all excess whitespace",
        "Re-parse",
        "Comment selected",
        "Open page in browser",
        "Open talk page in browser",
        "Open page history in browser",
        "Open text selection in browser",
        "Replace text with last edit",
        "Undo all changes",
    ]
    m = w.edit_box_menu
    m.menu()
    assert m.reparse.isEnabled() and m.open_page.isEnabled()
    assert not m.bypass.isEnabled()  # administrators only
    assert not m.unicodify.isEnabled()  # nothing selected
    assert not m.last_edit.isEnabled()
    assert m.comment.shortcut().toString() == "Ctrl+Shift+K"
    assert m.reparse.shortcut().toString() == "F5"


def test_comment_and_tags(qtbot: QtBot) -> None:
    w, _ = started(qtbot, "ab [[cd|cd]]")
    assert w.editor.toPlainText() == "ab [[cd]]"
    select_range(w, 3, 9)
    w.edit_box_menu.comment.trigger()
    assert w.editor.toPlainText() == "ab <!-- [[cd]] -->"
    w.editor.undo()
    assert w.editor.toPlainText() == "ab [[cd]]"  # one undo step
    w.edit_box_menu.disambig.trigger()
    assert "{{Disambiguation}}" in w.editor.toPlainText()
    w.edit_box_menu.wikify.trigger()
    assert w.editor.toPlainText().startswith("{{Wikify|date=")


def test_paste_more(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, _ = started(qtbot, "[[x|x]]")

    def configure(dialog: PasteMoreDialog) -> int:
        dialog.fields[0].setText("{{one}}")
        dialog.fields[9].setText("{{ten}}")
        return PasteMoreDialog.DialogCode.Accepted

    monkeypatch.setattr(PasteMoreDialog, "exec", configure)
    w.edit_box_menu.configure_paste.trigger()
    assert appconfig.load().preferences.paste_more[9] == "{{ten}}"
    w.edit_box_menu.menu()
    assert w.edit_box_menu.paste_more[0].text() == "{{one}}"
    assert w.edit_box_menu.paste_more[9].shortcut().toString() == "Ctrl+0"
    w.editor.moveCursor(QTextCursor.MoveOperation.End)
    w.edit_box_menu.paste_more[9].trigger()
    assert w.editor.toPlainText() == "[[x]]{{ten}}"


def test_undo_all_and_diff_double_click(qtbot: QtBot) -> None:
    w, _ = started(qtbot, "one\ntwo [[أليف|أليف]]\nthree")
    assert w.editor.toPlainText() == "one\ntwo [[أليف]]\nthree"  # processed
    w.editor.setPlainText("ONE\ntwo [[أليف]]\nthree")
    w.undo_line(1)
    qtbot.waitUntil(lambda: not w.busy, timeout=5000)
    assert w.editor.toPlainText() == "one\ntwo [[أليف]]\nthree"
    w.edit_box_menu.undo_all.trigger()
    assert w.editor.toPlainText() == "one\ntwo [[أليف|أليف]]\nthree"


def test_reparse_processes_the_edited_text(qtbot: QtBot) -> None:
    w, _ = started(qtbot)
    w.editor.setPlainText("حيوان [[كلب|كلب]]")
    w.reparse()
    qtbot.waitUntil(lambda: not w.busy, timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[كلب]]"


def test_last_edit_is_kept_after_a_failed_save(
    qtbot: QtBot, message_boxes: list[tuple[str, str]]
) -> None:
    w, t = started(qtbot)
    t.responses[("action", "edit")] = {"error": {"code": "readonly", "info": "Read only"}}
    w.editor.setPlainText("my edit")
    w.save()
    qtbot.waitUntil(lambda: not w.busy, timeout=5000)
    assert w.last_text == "my edit" and message_boxes
    w.editor.setPlainText("lost")
    w.edit_box_menu.last_edit.trigger()
    qtbot.waitUntil(lambda: not w.busy, timeout=5000)
    assert w.editor.toPlainText() == "my edit"


def test_insert_category_warns_when_missing(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, message_boxes: list[tuple[str, str]]
) -> None:
    w, t = started(qtbot, "نص [[ب|ب]]")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("قطط", True))
    t.responses[("titles", "تصنيف:قطط")] = {
        "query": {"pages": [{"title": "تصنيف:قطط", "ns": 14, "missing": True}]}
    }
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.insert_category()
    qtbot.waitUntil(lambda: "[[تصنيف:قطط]]" in w.editor.toPlainText(), timeout=5000)
