from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit
from pytestqt.qtbot import QtBot

from pyawb.editor.messages import Messages
from pyawb.editor.toolbar import build_toolbar
from pyawb.ui.editor_toolbar import WikiEditorToolbar, to_index, to_utf16


def make(
    qtbot: QtBot, text: str = "", lang: str = "en"
) -> tuple[QPlainTextEdit, WikiEditorToolbar]:
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText(text)
    msg = Messages(lang)
    bar = WikiEditorToolbar(editor, build_toolbar(msg), msg)
    qtbot.addWidget(bar)
    return editor, bar


def select(editor: QPlainTextEdit, start: int, end: int) -> None:
    cursor = editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def test_bold_button_wraps_selection_in_one_undo_step(qtbot: QtBot) -> None:
    editor, bar = make(qtbot, "a word b")
    select(editor, 2, 6)
    bar.button("bold").click()
    assert editor.toPlainText() == "a '''word''' b"
    editor.undo()
    assert editor.toPlainText() == "a word b"


def test_example_text_is_selected_after_insert(qtbot: QtBot) -> None:
    editor, bar = make(qtbot, "")
    bar.button("italic").click()
    assert editor.toPlainText() == "''Italic text''"
    assert editor.textCursor().selectedText() == "Italic text"


def test_positions_after_astral_characters(qtbot: QtBot) -> None:
    text = "𠀀𠀁 മലയാളം"
    assert to_index(text, to_utf16(text, 3)) == 3
    editor, bar = make(qtbot, text)
    select(editor, to_utf16(text, 3), to_utf16(text, len(text)))
    bar.button("bold").click()
    assert editor.toPlainText() == "𠀀𠀁 '''മലയാളം'''"


def test_heading_menu_and_tabs(qtbot: QtBot) -> None:
    editor, bar = make(qtbot, "== History ==")
    select(editor, 0, len("== History =="))
    bar.tab("advanced").setChecked(True)
    menu = bar.button("heading").menu()
    assert menu is not None
    next(a for a in menu.actions() if a.objectName() == "option-heading-3").trigger()
    # ownline: at the end of the text core adds a newline after the line
    assert editor.toPlainText() == "=== History ===\n"
    bar.tab("characters").setChecked(True)
    assert not bar.tab("advanced").isChecked()


def test_special_character_inserts_and_is_remembered(qtbot: QtBot) -> None:
    editor, bar = make(qtbot, "ab")
    select(editor, 1, 1)
    assert bar._char_index.currentRow() == 1  # Latin, as nothing was used yet
    item = bar._chars.item(0)
    with qtbot.waitSignal(bar.recent_changed) as blocker:
        bar._chars.itemClicked.emit(item)
    assert editor.toPlainText() == "aÁb"
    assert blocker.args == [["Á"]]


def test_dialog_tools_disabled_until_implemented(qtbot: QtBot) -> None:
    _, bar = make(qtbot)
    assert not bar.button("link").isEnabled()


def test_signature_only_in_talk_namespaces(qtbot: QtBot) -> None:
    _, bar = make(qtbot)
    bar.show()
    bar.set_namespace(0, wants_signature=False)
    assert not bar.button("signature").isVisible()
    bar.set_namespace(1, wants_signature=True)
    assert bar.button("signature").isVisible()


def test_read_only_editor_is_not_changed(qtbot: QtBot) -> None:
    editor, bar = make(qtbot, "x")
    editor.setReadOnly(True)
    bar.button("bold").click()
    assert editor.toPlainText() == "x"
