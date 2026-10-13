from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtWidgets import QPlainTextEdit
from pytestqt.qtbot import QtBot

from pyawb.editor.messages import Messages
from pyawb.editor.toolbar import ToolbarSite, build_toolbar
from pyawb.ui.editor_dialogs import (
    DIALOGS,
    EditorDialogs,
    InsertFileDialog,
    InsertLinkDialog,
    InsertTableDialog,
    SearchReplaceDialog,
)
from pyawb.ui.editor_toolbar import WikiEditorToolbar, select

SITE = ToolbarSite(sitename="Wikipedia")


def make(
    qtbot: QtBot, text: str = "", suggest: Any = None
) -> tuple[QPlainTextEdit, WikiEditorToolbar, EditorDialogs]:
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    editor.setPlainText(text)
    msg = Messages("en", "Wikipedia")
    bar = WikiEditorToolbar(editor, build_toolbar(msg, SITE), msg, dialogs=DIALOGS)
    qtbot.addWidget(bar)
    dialogs = EditorDialogs(editor, msg, SITE, suggest=suggest)
    bar.dialog_requested.connect(dialogs.open)
    return editor, bar, dialogs


def test_toolbar_opens_the_link_dialog_prefilled(qtbot: QtBot) -> None:
    editor, bar, dialogs = make(qtbot, "see [[Foo|bar]] here")
    select(editor, 4, 15)
    assert bar.button("link").isEnabled()
    bar.button("link").click()
    d = dialogs.dialog("insert-link")
    assert isinstance(d, InsertLinkDialog) and d.isVisible()
    assert (d.target.text(), d.text.text(), d.radio_int.isChecked()) == ("Foo", "bar", True)
    d.target.setText("Baz")
    assert d.text.text() == "bar"  # the text came from the selection: not overwritten
    d.insert()
    assert editor.toPlainText() == "see [[Baz|bar]] here"
    assert not d.isVisible()


def test_link_dialog_copies_target_and_detects_urls(qtbot: QtBot) -> None:
    editor, _, dialogs = make(qtbot)
    dialogs.open("insert-link")
    d = dialogs.dialog("insert-link")
    assert isinstance(d, InsertLinkDialog)
    assert not d.insert_button.isEnabled()
    d.target.setText("www.example.org")
    assert d.radio_ext.isChecked() and d.text.text() == "www.example.org"
    d.text.setText("Example")
    d.text.textEdited.emit("Example")
    d.insert()
    assert editor.toPlainText() == "[http://www.example.org Example]"


def test_link_dialog_rejects_invalid_titles(qtbot: QtBot) -> None:
    _, _, dialogs = make(qtbot)
    dialogs.open("insert-link")
    d = dialogs.dialog("insert-link")
    assert isinstance(d, InsertLinkDialog)
    d.target.setText("a[b")
    assert not d.insert_button.isEnabled()
    assert d.status.text() == "The title you specified is invalid"


def test_link_suggestions_come_from_a_worker_thread(qtbot: QtBot) -> None:
    calls: list[str] = []

    def suggest(query: str) -> Mapping[str, Any]:
        calls.append(query)
        return {"pages": [{"title": "Mercury", "index": 1, "description": "Planet"}]}

    _, _, dialogs = make(qtbot, suggest=suggest)
    dialogs.open("insert-link")
    d = dialogs.dialog("insert-link")
    assert isinstance(d, InsertLinkDialog)
    d.target.setText("Mercury")
    qtbot.waitUntil(lambda: bool(d.options), timeout=3000)
    assert calls == ["Mercury"]
    assert d.model.item(0).text() == "Mercury — Planet"
    assert d.status.text() == "This page exists on Wikipedia"


def test_file_dialog_round_trips_a_selected_file(qtbot: QtBot) -> None:
    text = "[[Image:a.jpg|thumb|left|Caption]]"
    editor, _, dialogs = make(qtbot, text)
    select(editor, 0, len(text))
    dialogs.open("insert-file")
    d = dialogs.dialog("insert-file")
    assert isinstance(d, InsertFileDialog)
    assert (d.file_name.text(), d.caption.text()) == ("A.jpg", "Caption")
    assert (d.align.currentData(), d.format_box.currentData()) == ("left", "thumb")
    d.size_edit.setText("100")
    d.insert()
    assert editor.toPlainText() == "[[File:A.jpg|100px|thumb|left|Caption]]\n"


def test_table_dialog_inserts_and_reports_errors(qtbot: QtBot, monkeypatch: Any) -> None:
    editor, _, dialogs = make(qtbot)
    dialogs.open("insert-table")
    d = dialogs.dialog("insert-table")
    assert isinstance(d, InsertTableDialog)
    warnings: list[str] = []
    monkeypatch.setattr(
        "pyawb.ui.editor_dialogs.QMessageBox.warning",
        lambda _parent, _title, text: warnings.append(text),
    )
    d.columns.setValue(0)
    d.insert()
    assert warnings == ["You cannot insert a table with zero rows or columns."]
    assert editor.toPlainText() == ""
    d.columns.setValue(1)
    d.rows.setValue(1)
    d.insert()
    assert editor.toPlainText().startswith('{| class="wikitable"\n|+ Caption text\n')
    assert d.rows.value() == 3  # form restored


def test_search_and_replace_dialog(qtbot: QtBot) -> None:
    editor, bar, dialogs = make(qtbot, "a cat, a cat")
    bar.button("replace").click()
    d = dialogs.dialog("search-and-replace")
    assert isinstance(d, SearchReplaceDialog) and d.isVisible() and not d.isModal()
    d.search.setText("cat")
    d.replace.setText("dog")
    d.run("find")
    assert editor.textCursor().selectedText() == "cat"
    d.run("replaceAll")
    assert editor.toPlainText() == "a dog, a dog"
    assert d.message.text() == "2 replacements made."
    editor.undo()
    assert editor.toPlainText() == "a cat, a cat"
    d.search.setText("")
    d.run("find")
    assert d.message.text() == "You did not enter anything to search for."
