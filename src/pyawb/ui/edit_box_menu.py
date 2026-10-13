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
# After AutoWikiBrowser AWB/Main.cs (mnuTextBox) and ConfigurePasteMoreItems.cs (GPL-2.0-or-later).
"""The edit box's context menu (AWB's mnuTextBox). The text work is in editor.editcommands; the
main window supplies the page, the wiki and Re-parse."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QAction, QIntValidator, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from pyawb.core import tools
from pyawb.core.parsers.parsers import Parsers
from pyawb.core.site import use_site
from pyawb.editor import editcommands as ec
from pyawb.editor.textselection import Edit
from pyawb.settings.preferences import PASTE_MORE_SLOTS

if TYPE_CHECKING:
    from pyawb.ui.main_window import MainWindow

PASTE_MORE_KEYS = [f"Ctrl+{n % 10}" for n in range(1, PASTE_MORE_SLOTS + 1)]  # Ctrl+1 … Ctrl+0


def apply_edit(editor: QPlainTextEdit, edit: Edit) -> None:
    """Apply an Edit as one undoable step and set the selection."""
    cursor = editor.textCursor()
    cursor.beginEditBlock()
    cursor.setPosition(edit.start)
    cursor.setPosition(edit.end, cursor.MoveMode.KeepAnchor)
    cursor.insertText(edit.insert)
    cursor.endEditBlock()
    cursor.setPosition(edit.sel_start)
    cursor.setPosition(edit.sel_end, cursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)


def selection(editor: QPlainTextEdit) -> tuple[str, int, int]:
    """(text, selection start, selection end) in the editor's own "\\n" text."""
    cursor = editor.textCursor()
    return editor.toPlainText(), cursor.selectionStart(), cursor.selectionEnd()


class PasteMoreDialog(QDialog):
    """ConfigurePasteMoreItems: the ten texts of Paste more."""

    def __init__(self, texts: tuple[str, ...], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Configure Paste more"))
        form = QFormLayout()
        self.fields: list[QLineEdit] = []
        for i, key in enumerate(PASTE_MORE_KEYS):
            field = QLineEdit(texts[i] if i < len(texts) else "", self)
            self.fields.append(field)
            form.addRow(QKeySequence(key).toString(QKeySequence.SequenceFormat.NativeText), field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        top = QVBoxLayout(self)
        top.addLayout(form)
        top.addWidget(buttons)
        self.resize(480, self.sizeHint().height())

    def value(self) -> tuple[str, ...]:
        return tuple(f.text() for f in self.fields)


class EditBoxMenu(QObject):
    """Builds the menu on each right click; the actions with shortcuts live on the editor."""

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.editor = window.editor
        self.parsers = Parsers()
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self._show)

        def action(text: str, slot: Callable[[], object], key: str = "") -> QAction:
            a = QAction(text, self.editor)
            a.triggered.connect(lambda _=False: slot())
            if key:
                a.setShortcut(QKeySequence(key))
                a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.editor.addAction(a)
            return a

        self.word_wrap = QAction(self.tr("Word wrap"), self.editor)
        self.word_wrap.setCheckable(True)
        self.word_wrap.toggled.connect(self.w.set_word_wrap)
        self.paste_more = [
            action("", lambda i=i: self._paste_more(i), key)
            for i, key in enumerate(PASTE_MORE_KEYS)
        ]
        self.configure_paste = action(self.tr("Configure…"), self._configure_paste_more)
        self.save_text = action(self.tr("Save text to file…"), self._save_text)
        self.birth_death = action(self.tr("Guess birth/death cats"), self._birth_death)
        self.category = action(self.tr("Category…"), self._category, "Ctrl+T")
        self.defaultsort = action(self.tr("Human name DEFAULTSORT"), self._defaultsort)
        self.hndis = action(self.tr("Human name disambig tag"), self._hndis)
        self.wikify = action(self.tr("Wikify"), lambda: self._prepend(ec.WIKIFY))
        self.cleanup = action(self.tr("Cleanup"), lambda: self._prepend(ec.CLEANUP))
        self.speedy = action(self.tr("Speedy delete…"), self._speedy)
        self.clear_tag = action("{{clear}}", lambda: self._insert(ec.CLEAR))
        self.disambig = action(self.tr("Disambiguation"), lambda: self._insert(ec.DISAMBIGUATION))
        self.uncat = action(self.tr("Uncategorised"), lambda: self._insert(ec.UNCATEGORISED))
        self.stub_text = QLineEdit("{{-stub}}")
        self.stub = action(self.tr("Stub"), lambda: self._insert(self.stub_text.text()))
        self.bullet_list = action(self.tr("* List"), lambda: self._convert_list("*"))
        self.number_list = action(self.tr("# List"), lambda: self._convert_list("#"))
        self.unicodify = action(self.tr("Unicodify selected"), self._unicodify)
        self.bypass = action(self.tr("Bypass all redirects"), self._bypass_redirects)
        self.whitespace = action(self.tr("Fix all excess whitespace"), self._whitespace)
        self.reparse = action(self.tr("Re-parse"), self.w.reparse, "F5")
        # AWB used Ctrl+K, which is the link dialog of the WikiEditor toolbar here
        self.comment = action(self.tr("Comment selected"), self._comment, "Ctrl+Shift+K")
        self.open_page = action(
            self.tr("Open page in browser"),
            lambda: self._open(tools.non_prettified_url),
            "Ctrl+Alt+P",
        )
        self.open_talk = action(self.tr("Open talk page in browser"), self._open_talk)
        self.open_history = action(
            self.tr("Open page history in browser"),
            lambda: self._open(tools.get_article_history_url),
            "Ctrl+Alt+H",
        )
        self.open_selection = action(
            self.tr("Open text selection in browser"), self._open_selection
        )
        self.last_edit = action(self.tr("Replace text with last edit"), self._replace_last_edit)
        self.undo_all = action(self.tr("Undo all changes"), self._undo_all)

    # -- the menu -----------------------------------------------------------------------------

    def _show(self, pos: QPoint) -> None:
        self.menu().exec(self.editor.viewport().mapToGlobal(pos))

    def menu(self) -> QMenu:
        """mnuTextBox, enabled as in mnuTextBox_Opening."""
        ed = self.editor
        menu = QMenu(ed)
        has_sel = ed.textCursor().hasSelection()
        page = self.w.current is not None and self.w.current.article is not None
        editable = not ed.isReadOnly()
        self.word_wrap.setChecked(ed.lineWrapMode() is not QPlainTextEdit.LineWrapMode.NoWrap)
        menu.addAction(self.word_wrap)
        menu.addSeparator()
        undo = menu.addAction(self.tr("Undo"), ed.undo)
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.setEnabled(ed.document().isUndoAvailable() and editable)
        cut = menu.addAction(self.tr("Cut"), ed.cut)
        cut.setShortcut(QKeySequence.StandardKey.Cut)
        cut.setEnabled(has_sel and editable)
        copy = menu.addAction(self.tr("Copy"), ed.copy)
        copy.setShortcut(QKeySequence.StandardKey.Copy)
        copy.setEnabled(has_sel)
        paste = menu.addAction(self.tr("Paste"), ed.paste)
        paste.setShortcut(QKeySequence.StandardKey.Paste)
        paste.setEnabled(ed.canPaste() and editable)
        more = menu.addMenu(self.tr("Paste more"))
        texts = self.w.config.preferences.paste_more
        for i, a in enumerate(self.paste_more):
            text = texts[i] if i < len(texts) else ""
            label = text if len(text) <= 40 else text[:39] + "…"
            a.setText(label.replace("&", "&&") or self.tr("(empty)"))
            a.setEnabled(bool(text) and editable)
            more.addAction(a)
        more.addSeparator()
        more.addAction(self.configure_paste)
        select_all = menu.addAction(self.tr("Select all"), ed.selectAll)
        select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        menu.addSeparator()
        menu.addAction(self.save_text)
        menu.addSeparator()
        goto = menu.addMenu(self.tr("Go to line"))
        line = QLineEdit()
        line.setPlaceholderText(self.tr("Enter line number"))
        line.setValidator(QIntValidator(1, 10_000_000, line))
        line.returnPressed.connect(lambda: (self.go_to_line(line.text()), menu.close()))
        holder = QWidgetAction(goto)
        holder.setDefaultWidget(line)
        goto.addAction(holder)
        menu.addSeparator()
        insert = menu.addMenu(self.tr("Insert…"))
        insert.addAction(self.birth_death)
        insert.addSeparator()
        insert.addAction(self.category)
        tags = menu.addMenu(self.tr("Insert tag"))
        tags.addActions(
            [
                self.defaultsort,
                self.hndis,
                self.wikify,
                self.cleanup,
                self.speedy,
                self.clear_tag,
                self.disambig,
                self.uncat,
                self.stub,
            ]
        )
        stub_holder = QWidgetAction(tags)
        stub_holder.setDefaultWidget(self.stub_text)
        tags.addAction(stub_holder)
        convert = menu.addMenu(self.tr("Convert list to"))
        convert.addActions([self.bullet_list, self.number_list])
        menu.addActions([self.unicodify, self.bypass, self.whitespace, self.reparse, self.comment])
        menu.addSeparator()
        menu.addActions([self.open_page, self.open_talk, self.open_history])
        menu.addSeparator()
        menu.addAction(self.open_selection)
        menu.addSeparator()
        menu.addActions([self.last_edit, self.undo_all])

        for a in (self.birth_death, self.defaultsort, self.hndis, self.reparse, self.undo_all):
            a.setEnabled(page and editable)
        for a in (self.wikify, self.cleanup, self.speedy, self.clear_tag, self.disambig):
            a.setEnabled(editable)
        for a in (self.uncat, self.stub, self.whitespace, self.comment):
            a.setEnabled(editable)
        self.category.setEnabled(page and editable and self.w.session is not None)
        for a in (self.bullet_list, self.number_list, self.unicodify):
            a.setEnabled(has_sel and editable)
        # AWB: administrators only (bypassing redirects is discouraged)
        self.bypass.setEnabled(page and editable and self.w.is_sysop())
        for a in (self.open_page, self.open_talk, self.open_history):
            a.setEnabled(bool(self.w.current_title()))
        self.open_selection.setEnabled(has_sel)
        self.last_edit.setEnabled(bool(self.w.last_text) and editable)
        tags.setEnabled(editable)
        insert.setEnabled(editable)
        return menu

    # -- commands -----------------------------------------------------------------------------

    def _apply(self, edit: Edit) -> None:
        apply_edit(self.editor, edit)

    def _insert(self, text: str) -> None:
        self._apply(ec.replace_selection(*selection(self.editor), text))

    def _prepend(self, tag: str) -> None:
        self._apply(ec.prepend_tag(self.editor.toPlainText(), tag))

    def _paste_more(self, i: int) -> None:
        texts = self.w.config.preferences.paste_more
        if i < len(texts) and texts[i] and not self.editor.isReadOnly():
            self._insert(texts[i])

    def _configure_paste_more(self) -> None:
        dialog = PasteMoreDialog(self.w.config.preferences.paste_more, self.w)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.w.set_paste_more(dialog.value())

    def _save_text(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self.w, self.tr("Save text to file"), "", self.tr("Text files (*.txt);;All files (*)")
        )
        if name:
            try:
                Path(name).write_text(self.editor.toPlainText(), encoding="utf-8")
            except OSError as e:
                QMessageBox.warning(self.w, self.tr("Save text to file"), str(e))

    def go_to_line(self, number: str) -> None:
        if number.isdigit():
            self.w.go_to_line(int(number))

    def _title(self) -> str:
        return self.w.current_title() or ""

    def _birth_death(self) -> None:
        text, start, end = selection(self.editor)
        with use_site(self.w.wiki_site()):
            edit = ec.insert_birth_death_categories(
                text, start, end, self._title(), self.parsers, self.w.restrict_defaultsort()
            )
        if edit is None:
            self.w.set_status(self.tr("No years found in the text"))
        else:
            self._apply(edit)

    def _defaultsort(self) -> None:
        with use_site(self.w.wiki_site()):
            self._apply(ec.human_name_defaultsort(*selection(self.editor), self._title()))

    def _hndis(self) -> None:
        with use_site(self.w.wiki_site()):
            self._apply(ec.human_name_disambig(*selection(self.editor), self._title()))

    def _speedy(self) -> None:
        reason, ok = QInputDialog.getText(
            self.w,
            self.tr("Speedy deletion"),
            self.tr("Enter a reason. Leave blank if you will write it in the edit box."),
        )
        if ok:
            self._prepend(ec.speedy_delete_tag(reason))

    def _convert_list(self, bullet: str) -> None:
        self._apply(ec.convert_list(*selection(self.editor), bullet))

    def _unicodify(self) -> None:
        with use_site(self.w.wiki_site()):
            self._apply(ec.unicodify_selected(*selection(self.editor), self.parsers))

    def _whitespace(self) -> None:
        with use_site(self.w.wiki_site()):
            self._apply(ec.fix_all_excess_whitespace(self.editor.toPlainText()))

    def _comment(self) -> None:
        if not self.editor.isReadOnly():
            self._apply(ec.comment_selected(*selection(self.editor)))

    def _category(self) -> None:
        self.w.insert_category()

    def _bypass_redirects(self) -> None:
        answer = QMessageBox.question(
            self.w,
            self.tr("Bypass redirects"),
            self.tr(
                "Replacing links to redirects with direct links is strongly discouraged, though "
                "it can be useful in some cases. Are you sure you want to continue?"
            ),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.w.bypass_redirects()

    def _open(self, url_for: Callable[[str], str]) -> None:
        title = self._title()
        if title:
            with use_site(self.w.wiki_site()):
                self.w.open_url(url_for(title))

    def _open_talk(self) -> None:
        title = self._title()
        if title:
            with use_site(self.w.wiki_site()):
                self.w.open_url(tools.non_prettified_url(tools.convert_to_talk(title)))

    def _open_selection(self) -> None:
        chosen = self.editor.textCursor().selectedText().replace(" ", "\n").strip()
        if not chosen:
            return
        if ec.is_url(chosen):
            self.w.open_url(QUrl.fromUserInput(chosen).toString())
        else:
            with use_site(self.w.wiki_site()):
                self.w.open_url(tools.non_prettified_url(chosen))

    def _replace_last_edit(self) -> None:
        if self.w.last_text:
            self._apply(ec.whole_text(self.editor.toPlainText(), self.w.last_text))
            self.w.show_diff_on_load()

    def _undo_all(self) -> None:
        current = self.w.current
        if current is not None and current.article is not None:
            original = tools.convert_from_local_line_endings(current.article.original_article_text)
            self._apply(ec.whole_text(self.editor.toPlainText(), original))
