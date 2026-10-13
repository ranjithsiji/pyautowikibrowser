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
"""WikiEditor's dialogs as Qt dialogs: insert link, insert file, insert table, search and replace.

The forms follow WikiEditor's templates; what the buttons do is pyawb.editor.dialogs. Link target
suggestions come from a `suggest(query) -> query result` callable (WikiSession.prefix_search),
run off the UI thread; without one the dialog works without suggestions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pyawb.editor import dialogs as dl
from pyawb.editor.messages import Messages
from pyawb.editor.textselection import TextAction
from pyawb.editor.toolbar import ToolbarSite
from pyawb.ui.editor_toolbar import apply_action, apply_edit, select, selection
from pyawb.ui.icons import ICON_SIZE, codex_icon

Suggest = Callable[[str], Mapping[str, Any]]

#: the dialog modules implemented here (WikiEditorToolbar enables their tools)
DIALOGS = frozenset({"insert-link", "insert-file", "insert-table", "search-and-replace"})


def _primary(button: QPushButton | None) -> None:
    """Codex's primary progressive button (the dialog's main action, also on Enter)."""
    if button is not None:
        button.setProperty("primary", True)
        button.setDefault(True)
        # the stylesheet has already been applied: apply it again for the new property
        button.style().unpolish(button)
        button.style().polish(button)


class _SuggestJob(QRunnable):
    """Runs suggest(query) in the thread pool; the result comes back through a queued signal."""

    class Signals(QObject):
        done = Signal(int, str, object)

    def __init__(self, serial: int, query: str, suggest: Suggest, signals: Signals) -> None:
        super().__init__()
        self.serial, self.query, self.suggest, self.signals = serial, query, suggest, signals

    def run(self) -> None:
        try:
            result: Mapping[str, Any] = self.suggest(self.query)
        except Exception:  # network or API error: no suggestions, never a crash
            result = {}
        self.signals.done.emit(self.serial, self.query, result)


class _Base(QDialog):
    def __init__(self, editor: QPlainTextEdit, msg: Messages, site: ToolbarSite, title: str):
        super().__init__(editor.window())
        self.editor, self.msg, self.site = editor, msg, site
        self.setWindowTitle(msg.text(title))
        self.setLayoutDirection(editor.window().layoutDirection())

    def t(self, key: str, *params: str) -> str:
        return self.msg.text(key, *params)

    def run_action(self, action: TextAction) -> None:
        apply_action(self.editor, action)


# --- insert link ------------------------------------------------------------------------------


class InsertLinkDialog(_Base):
    """insert-link: target with suggestions and status, link text, internal/external."""

    DEBOUNCE_MS = 250

    def __init__(
        self, editor: QPlainTextEdit, msg: Messages, site: ToolbarSite, suggest: Suggest | None
    ) -> None:
        super().__init__(editor, msg, site, "wikieditor-toolbar-tool-link-title")
        self.setObjectName("insertLinkDialog")
        self.setMinimumWidth(500)
        self.suggest = suggest
        self.options: list[dl.TitleOption] = []
        self.external_mode = False
        self.mode_manual = False
        self.text_touched = False
        self.whitespace: tuple[str, str] = ("", "")
        self._invalid = False
        self._serial = 0
        self._signals = _SuggestJob.Signals(self)
        self._signals.done.connect(self._on_suggestions)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.t("wikieditor-toolbar-tool-link-int-target")))
        self.target = QLineEdit(self)
        self.target.setObjectName("linkTarget")
        self.target.setPlaceholderText(self.t("wikieditor-toolbar-tool-link-int-target-tooltip"))
        layout.addWidget(self.target)
        self.model = QStandardItemModel(self)
        self.completer = QCompleter(self.model, self)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setCompletionRole(Qt.ItemDataRole.UserRole)
        self.target.setCompleter(self.completer)
        self.completer.activated[str].connect(self._on_chosen)  # type: ignore[index]

        status_row = QHBoxLayout()
        self.status_icon = QLabel(self)
        self.status = QLabel(self)
        self.status.setObjectName("linkStatus")
        self.status.setWordWrap(True)
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status, 1)
        layout.addLayout(status_row)

        layout.addWidget(QLabel(self.t("wikieditor-toolbar-tool-link-int-text")))
        self.text = QLineEdit(self)
        self.text.setObjectName("linkText")
        self.text.setPlaceholderText(self.t("wikieditor-toolbar-tool-link-int-text-tooltip"))
        self.text.textEdited.connect(self._on_text_edited)
        layout.addWidget(self.text)

        self.radio_int = QRadioButton(self.t("wikieditor-toolbar-tool-link-int"), self)
        self.radio_ext = QRadioButton(self.t("wikieditor-toolbar-tool-link-ext"), self)
        self.radio_int.clicked.connect(lambda: self._set_url_mode(external=False))
        self.radio_ext.clicked.connect(lambda: self._set_url_mode(external=True))
        layout.addWidget(self.radio_int)
        layout.addWidget(self.radio_ext)

        self.buttons = QDialogButtonBox(self)
        self.insert_button = self.buttons.addButton(
            self.t("wikieditor-toolbar-tool-link-insert"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        _primary(self.insert_button)
        self.buttons.addButton(
            self.t("wikieditor-toolbar-tool-link-cancel"), QDialogButtonBox.ButtonRole.RejectRole
        )
        self.buttons.accepted.connect(self.insert)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(self.DEBOUNCE_MS)
        self._timer.timeout.connect(self._fetch)
        self.target.textChanged.connect(self._on_target_changed)

    # open(): pre-fill from the selection
    def prepare(self) -> None:
        text, start, end = selection(self.editor)
        fields = dl.link_fields_from_selection(text[start:end])
        self.mode_manual = False
        self.external_mode = False
        self.text_touched = False
        self.options = []
        self.model.clear()
        self.radio_int.setAutoExclusive(False)
        self.radio_int.setChecked(False)
        self.radio_ext.setChecked(False)
        self.radio_int.setAutoExclusive(True)
        self.target.setText(fields.target)
        self.text.setText(fields.text)
        self.text_touched = fields.text_touched
        self.whitespace = fields.whitespace
        if fields.is_external is not None:
            self._set_url_mode(fields.is_external)
        self._on_target_changed(self.target.text())
        self.target.setFocus()

    def _on_text_edited(self, _: str) -> None:
        self.text_touched = True

    def _set_url_mode(self, external: bool) -> None:
        # TitleInputField.setUrlMode
        self.external_mode = external
        self.mode_manual = True
        (self.radio_ext if external else self.radio_int).setChecked(True)
        self._validate(self.target.text())
        self._show_status(dl.first_match(self.options, self.target.text()))

    def _on_target_changed(self, value: str) -> None:
        # TitleInputField.onChange
        if not self.mode_manual and dl.looks_like_external_link(value, self.site):
            self.external_mode = True
        self._validate(value)
        if self.suggest is not None and value.strip():
            self._timer.start()

    def _validate(self, value: str) -> None:
        if not self.external_mode and value != "" and not dl.is_valid_title(value):
            self._set_status(
                "error", self.t("wikieditor-toolbar-tool-link-int-target-status-invalid")
            )
            self.insert_button.setEnabled(False)
            self._invalid = True
            return
        self._invalid = False
        self._set_status(None, "")
        # the dialog's change handler
        (self.radio_ext if self.external_mode else self.radio_int).setChecked(True)
        if not self.text_touched:
            self.text.setText(value)
        self.insert_button.setEnabled(value != "")

    def _set_status(self, icon: str | None, message: str) -> None:
        self.status.setText(message)
        if icon:
            pixmap = codex_icon(icon, self.msg.lang).pixmap(ICON_SIZE, ICON_SIZE)
            self.status_icon.setPixmap(pixmap)
        else:
            self.status_icon.clear()

    def _show_status(self, option: dl.TitleOption | None) -> None:
        status = dl.link_status(option, self.external_mode, self.mode_manual)
        if status is not None and not self._invalid:
            self._set_status(status[0], self.t(status[1]))

    def _fetch(self) -> None:
        if self.suggest is None:
            return
        self._serial += 1
        job = _SuggestJob(self._serial, self.target.text(), self.suggest, self._signals)
        QThreadPool.globalInstance().start(job)

    def _on_suggestions(self, serial: int, query: str, result: Mapping[str, Any]) -> None:
        if serial != self._serial or query != self.target.text():
            return  # an older request, or the text changed meanwhile
        redirect_msg = self.t("mw-widgets-titleinput-description-redirect", "$1")
        self.set_options(dl.title_options(result, query, self.site, redirect_msg))

    def set_options(self, options: list[dl.TitleOption]) -> None:
        self.options = options
        self.model.clear()
        new_page = self.t("mw-widgets-titleinput-description-new-page")
        for option in options:
            description = option.description or (new_page if option.missing else "")
            item = QStandardItem(f"{option.title} — {description}" if description else option.title)
            item.setData(option.title, Qt.ItemDataRole.UserRole)
            self.model.appendRow(item)
        if options and self.target.hasFocus():
            self.completer.complete()
        self._show_status(dl.first_match(options, self.target.text()))

    def _on_chosen(self, title: str) -> None:
        option = next((o for o in self.options if o.title == title), None)
        self._set_status(None, "")
        self._show_status(option)

    def insert(self) -> None:
        if not self.insert_button.isEnabled():
            return
        result = dl.insert_link(
            self.target.text(),
            self.text.text(),
            not self.radio_ext.isChecked(),
            self.site,
            self.whitespace,
        )
        if isinstance(result, dl.LooksInternal):
            if not self._ask_internal(result.title):
                result = dl.insert_link(
                    self.target.text(),
                    self.text.text(),
                    False,
                    self.site,
                    self.whitespace,
                    ignore_looks_internal=True,
                )
            else:
                self.target.setText(result.title)
                self._set_url_mode(external=False)
                return
        assert isinstance(result, TextAction)
        self.accept()
        self.run_action(result)

    def _ask_internal(self, title: str) -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(self.windowTitle())
        box.setText(self.t("wikieditor-toolbar-tool-link-lookslikeinternal", title))
        internal = box.addButton(
            self.t("wikieditor-toolbar-tool-link-lookslikeinternal-int"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        box.addButton(
            self.t("wikieditor-toolbar-tool-link-lookslikeinternal-ext"),
            QMessageBox.ButtonRole.RejectRole,
        )
        box.exec()
        return box.clickedButton() is internal


# --- insert file ------------------------------------------------------------------------------


class InsertFileDialog(_Base):
    """insert-file: file name, caption, alt text, size, alignment, format."""

    def __init__(
        self,
        editor: QPlainTextEdit,
        msg: Messages,
        site: ToolbarSite,
        open_url: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(editor, msg, site, "wikieditor-toolbar-tool-file-title")
        self.setObjectName("insertFileDialog")
        self.setMinimumWidth(590)
        self.open_url = open_url
        self.whitespace: tuple[str, str] = ("", "")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.file_name = QLineEdit(self)
        self.caption = QLineEdit(self)
        self.alt = QLineEdit(self)
        form.addRow(self.t("wikieditor-toolbar-file-target"), self.file_name)
        form.addRow(self.t("wikieditor-toolbar-file-caption"), self.caption)
        alt_help = QLabel(self.t("wikieditor-toolbar-file-alt-help"), self)
        alt_help.setWordWrap(True)
        alt_help.setVisible(False)
        # an expandable help text, as in WikiEditor
        toggle = QLabel(f'<a href="#">{self.t("wikieditor-toolbar-file-alt-help-label")}</a>', self)
        toggle.linkActivated.connect(lambda _: alt_help.setVisible(not alt_help.isVisible()))
        alt_label = QWidget(self)
        alt_row = QHBoxLayout(alt_label)
        alt_row.setContentsMargins(0, 0, 0, 0)
        alt_row.addWidget(QLabel(self.t("wikieditor-toolbar-file-alt")))
        alt_row.addWidget(toggle)
        form.addRow(alt_label, self.alt)
        form.addRow("", alt_help)
        layout.addLayout(form)

        options = QGridLayout()
        self.size_edit = QLineEdit(self)
        self.size_edit.setPlaceholderText(self.t("wikieditor-toolbar-file-default"))
        self.align = QComboBox(self)
        self.align.addItem(self.t("wikieditor-toolbar-file-default"), "default")
        for name in ("img_none", "img_center", "img_left", "img_right"):
            word = site.magic_word(name)
            self.align.addItem(word, word)
        self.format_box = QComboBox(self)
        for name in ("img_thumbnail", "img_framed", "img_frameless"):
            word = site.magic_word(name)
            self.format_box.addItem(word, word)
        self.format_box.addItem(self.t("wikieditor-toolbar-file-format-none"), "default")
        for col, (key, widget) in enumerate(
            (
                ("wikieditor-toolbar-file-size", self.size_edit),
                ("wikieditor-toolbar-file-float", self.align),
                ("wikieditor-toolbar-file-format", self.format_box),
            )
        ):
            options.addWidget(QLabel(self.t(key)), 0, col)
            options.addWidget(widget, 1, col)
        layout.addLayout(options)

        buttons = QDialogButtonBox(self)
        insert = buttons.addButton(
            self.t("wikieditor-toolbar-tool-file-insert"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        _primary(insert)
        buttons.addButton(
            self.t("wikieditor-toolbar-tool-file-cancel"), QDialogButtonBox.ButtonRole.RejectRole
        )
        upload = buttons.addButton(
            self.t("wikieditor-toolbar-tool-file-upload"), QDialogButtonBox.ButtonRole.ActionRole
        )
        # WikiEditor opens an upload dialog; here the wiki's Special:Upload in the browser
        upload.setEnabled(open_url is not None and bool(site.server))
        upload.clicked.connect(self.upload)
        buttons.accepted.connect(self.insert)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def prepare(self) -> None:
        text, start, end = selection(self.editor)
        self.set_fields(dl.file_fields_from_selection(text[start:end], self.site))
        self.file_name.setFocus()

    def set_fields(self, f: dl.FileFields) -> None:
        self.whitespace = f.whitespace
        self.file_name.setText(f.file_name)
        self.caption.setText(f.caption)
        self.alt.setText(f.alt)
        self.size_edit.setText(f.size)
        self.align.setCurrentIndex(max(0, self.align.findData(f.float)))
        self.format_box.setCurrentIndex(max(0, self.format_box.findData(f.format or "default")))

    def fields(self) -> dl.FileFields:
        return dl.FileFields(
            self.file_name.text(),
            self.caption.text(),
            self.alt.text(),
            self.size_edit.text(),
            str(self.align.currentData()),
            str(self.format_box.currentData()),
            self.whitespace,
        )

    def insert(self) -> None:
        action = dl.insert_file(self.fields(), self.site)
        self.accept()
        self.run_action(action)

    def upload(self) -> None:
        if self.open_url is not None:
            server = self.site.server
            if server.startswith("//"):
                server = "https:" + server
            self.open_url(server + self.site.article_path.replace("$1", "Special:Upload"))
            self.reject()


# --- insert table -----------------------------------------------------------------------------


class InsertTableDialog(_Base):
    """insert-table: header row, borders, sortable, rows and columns, with a preview."""

    def __init__(self, editor: QPlainTextEdit, msg: Messages, site: ToolbarSite) -> None:
        super().__init__(editor, msg, site, "wikieditor-toolbar-tool-table-title")
        self.setObjectName("insertTableDialog")
        self.setMinimumWidth(590)
        layout = QHBoxLayout(self)
        form = QVBoxLayout()
        self.header = QCheckBox(self.t("wikieditor-toolbar-tool-table-dimensions-header"), self)
        self.wikitable = QCheckBox(self.t("wikieditor-toolbar-tool-table-wikitable"), self)
        self.sortable = QCheckBox(self.t("wikieditor-toolbar-tool-table-sortable"), self)
        for box in (self.header, self.wikitable, self.sortable):
            form.addWidget(box)
            box.toggled.connect(self._update_preview)
        dims = QGridLayout()
        self.rows = QSpinBox(self)
        self.columns = QSpinBox(self)
        for col, (key, spin) in enumerate(
            (
                ("wikieditor-toolbar-tool-table-dimensions-rows", self.rows),
                ("wikieditor-toolbar-tool-table-dimensions-columns", self.columns),
            )
        ):
            spin.setRange(0, dl.TABLE_MAX_CELLS)
            dims.addWidget(QLabel(self.t(key)), 0, col)
            dims.addWidget(spin, 1, col)
        form.addLayout(dims)
        form.addStretch(1)
        buttons = QDialogButtonBox(self)
        insert = buttons.addButton(
            self.t("wikieditor-toolbar-tool-table-insert"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        _primary(insert)
        buttons.addButton(
            self.t("wikieditor-toolbar-tool-table-cancel"), QDialogButtonBox.ButtonRole.RejectRole
        )
        buttons.accepted.connect(self.insert)
        buttons.rejected.connect(self.reject)
        form.addWidget(buttons)
        layout.addLayout(form, 1)

        preview = QVBoxLayout()
        preview.addWidget(QLabel(self.t("wikieditor-toolbar-tool-table-example")))
        self.preview = QTextBrowser(self)
        self.preview.setObjectName("tablePreview")
        preview.addWidget(self.preview)
        layout.addLayout(preview, 1)
        self.reset()

    def reset(self) -> None:
        """Restore form state (as after an insert)."""
        self.rows.setValue(3)
        self.columns.setValue(3)
        self.header.setChecked(True)
        self.wikitable.setChecked(True)
        self.sortable.setChecked(False)
        self._update_preview()

    def prepare(self) -> None:
        self.rows.setFocus()

    def _update_preview(self) -> None:
        border = ' border="1"' if self.wikitable.isChecked() else ""
        head = self.t("wikieditor-toolbar-tool-table-example-header")
        cell = self.t("wikieditor-toolbar-tool-table-example-cell-text")
        rows = [f"<tr>{f'<th>{head}</th>' * 3}</tr>"] if self.header.isChecked() else []
        rows += [f"<tr>{f'<td>{cell}</td>' * 3}</tr>"] * 3
        caption = self.t("wikieditor-toolbar-tool-table-example-caption")
        self.preview.setHtml(
            f'<table{border} cellspacing="0" cellpadding="3"><caption>{caption}</caption>'
            + "".join(rows)
            + "</table>"
        )

    def insert(self) -> None:
        result = dl.insert_table(
            str(self.rows.value()),
            str(self.columns.value()),
            self.header.isChecked(),
            self.wikitable.isChecked(),
            self.sortable.isChecked(),
            self.msg,
        )
        if isinstance(result, dl.TableError):
            QMessageBox.warning(self, self.windowTitle(), self.t(result.message, *result.params))
            return
        self.accept()
        self.run_action(result)
        self.reset()


# --- search and replace -----------------------------------------------------------------------


class SearchReplaceDialog(_Base):
    """search-and-replace: not modal; Find next, Replace, Replace all."""

    def __init__(self, editor: QPlainTextEdit, msg: Messages, site: ToolbarSite) -> None:
        super().__init__(editor, msg, site, "wikieditor-toolbar-tool-replace-title")
        self.setObjectName("searchReplaceDialog")
        self.setModal(False)
        self.setMinimumWidth(500)
        self.state = dl.SearchReplace()
        layout = QVBoxLayout(self)
        self.message = QLabel(self)
        self.message.setObjectName("replaceMessage")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        form = QFormLayout()
        self.search = QLineEdit(self)
        self.replace = QLineEdit(self)
        form.addRow(self.t("wikieditor-toolbar-tool-replace-search"), self.search)
        form.addRow(self.t("wikieditor-toolbar-tool-replace-replace"), self.replace)
        layout.addLayout(form)
        self.match_case = QCheckBox(self.t("wikieditor-toolbar-tool-replace-case"), self)
        self.match_word = QCheckBox(self.t("wikieditor-toolbar-tool-replace-word"), self)
        self.is_regex = QCheckBox(self.t("wikieditor-toolbar-tool-replace-regex"), self)
        for box in (self.match_case, self.match_word, self.is_regex):
            layout.addWidget(box)
        buttons = QDialogButtonBox(self)
        self.find_button = buttons.addButton(
            self.t("wikieditor-toolbar-tool-replace-button-findnext"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        _primary(self.find_button)
        replace = buttons.addButton(
            self.t("wikieditor-toolbar-tool-replace-button-replace"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        replace_all = buttons.addButton(
            self.t("wikieditor-toolbar-tool-replace-button-replaceall"),
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        close = buttons.addButton(
            self.t("wikieditor-toolbar-tool-replace-close"), QDialogButtonBox.ButtonRole.RejectRole
        )
        self.find_button.clicked.connect(lambda: self.run("find"))
        replace.clicked.connect(lambda: self.run("replace"))
        replace_all.clicked.connect(lambda: self.run("replaceAll"))
        close.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def prepare(self) -> None:
        self.state.reset()
        self.message.clear()
        self.search.setFocus()
        self.search.selectAll()

    def run(self, mode: str) -> None:
        self.message.clear()
        text = self.editor.toPlainText()
        result = self.state.run(
            mode,
            text,
            self.search.text(),
            self.replace.text(),
            self.match_case.isChecked(),
            self.is_regex.isChecked(),
            self.match_word.isChecked(),
        )
        if result.edit is not None and not self.editor.isReadOnly():
            text = apply_edit(self.editor, text, result.edit)
        if result.selection is not None:
            select(self.editor, *result.selection, text)
            self.editor.ensureCursorVisible()
        if result.message is not None:
            self.message.setText(self.t(result.message, *result.params))


AnyDialog = InsertLinkDialog | InsertFileDialog | InsertTableDialog | SearchReplaceDialog


# --- the toolbar's dialogs --------------------------------------------------------------------


class EditorDialogs(QObject):
    """Opens the dialogs for a WikiEditorToolbar's dialog tools (connect to dialog_requested)."""

    def __init__(
        self,
        editor: QPlainTextEdit,
        msg: Messages,
        site: ToolbarSite,
        suggest: Suggest | None = None,
        open_url: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(editor)
        self.editor, self.msg, self.site = editor, msg, site
        self.suggest, self.open_url = suggest, open_url
        self._dialogs: dict[str, AnyDialog] = {}

    def set_site(self, msg: Messages, site: ToolbarSite, suggest: Suggest | None = None) -> None:
        """Another wiki or language: the dialogs are rebuilt when next opened."""
        self.msg, self.site, self.suggest = msg, site, suggest
        for dialog in self._dialogs.values():
            dialog.deleteLater()
        self._dialogs.clear()

    def dialog(self, module: str) -> AnyDialog:
        if module not in self._dialogs:
            if module == "insert-link":
                d: Any = InsertLinkDialog(self.editor, self.msg, self.site, self.suggest)
            elif module == "insert-file":
                d = InsertFileDialog(self.editor, self.msg, self.site, self.open_url)
            elif module == "insert-table":
                d = InsertTableDialog(self.editor, self.msg, self.site)
            elif module == "search-and-replace":
                d = SearchReplaceDialog(self.editor, self.msg, self.site)
            else:
                raise KeyError(module)
            self._dialogs[module] = d
        return self._dialogs[module]

    def open(self, module: str) -> None:
        """Open a dialog; the modal ones return after Insert or Cancel."""
        if module not in DIALOGS:
            return
        d = self.dialog(module)
        d.prepare()
        if isinstance(d, SearchReplaceDialog):
            d.show()
            d.raise_()
            d.activateWindow()
        else:
            d.open()
