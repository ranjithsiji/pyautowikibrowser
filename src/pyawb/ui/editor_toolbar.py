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
"""The WikiEditor toolbar above the wikitext editor.

Layout as in WikiEditor: the main tools, the tabs (Advanced, Special characters, Help), and the
secondary tools at the far end; a tab opens its section below the row. The toolbar's content is
pyawb.editor.toolbar data and its actions are pyawb.editor.textselection functions; this widget
only passes the selection in and applies the returned edit as one undo step.
"""

from __future__ import annotations

import bisect
import sys
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QSizePolicy,
    QStackedWidget,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pyawb.editor import textselection as ts
from pyawb.editor.messages import Messages
from pyawb.editor.toolbar import (
    Action,
    BookletSection,
    Character,
    CharacterPage,
    DialogAction,
    HelpPage,
    Tool,
    Toolbar,
    ToolbarSection,
    remember_character,
    shortcut_label,
)
from pyawb.ui.highlighter import utf16_offsets
from pyawb.ui.icons import ICON_SIZE, codex_icon


def to_index(text: str, utf16_pos: int) -> int:
    """str index of a Qt (UTF-16) position in text."""
    if text.isascii() or all(ord(c) <= 0xFFFF for c in text):
        return min(utf16_pos, len(text))
    offsets = utf16_offsets(text)
    return bisect.bisect_left(offsets, utf16_pos)


def to_utf16(text: str, index: int) -> int:
    """Qt (UTF-16) position of a str index in text."""
    return index + sum(1 for c in text[:index] if ord(c) > 0xFFFF)


def apply_action(editor: QPlainTextEdit, action: ts.TextAction) -> None:
    """Run an encapsulate/replace action on the editor's selection, as one undo step."""
    if editor.isReadOnly():
        return
    cursor = editor.textCursor()
    text = editor.toPlainText()
    start = to_index(text, cursor.selectionStart())
    end = to_index(text, cursor.selectionEnd())
    edit = ts.do_action(text, start, end, action)
    new_text = edit.apply(text)
    cursor.beginEditBlock()
    cursor.setPosition(to_utf16(text, edit.start))
    cursor.setPosition(to_utf16(text, edit.end), QTextCursor.MoveMode.KeepAnchor)
    cursor.insertText(edit.insert)
    cursor.endEditBlock()
    cursor.setPosition(to_utf16(new_text, edit.sel_start))
    cursor.setPosition(to_utf16(new_text, edit.sel_end), QTextCursor.MoveMode.KeepAnchor)
    editor.setTextCursor(cursor)
    editor.setFocus()


class WikiEditorToolbar(QWidget):
    """WikiEditor's toolbar for a QPlainTextEdit."""

    #: a tool with a DialogAction was used; the module name ("insert-link", ...)
    dialog_requested = Signal(str)
    #: the recently used special characters changed (to be saved by the owner)
    recent_changed = Signal(list)

    def __init__(
        self,
        editor: QPlainTextEdit,
        toolbar: Toolbar,
        msg: Messages,
        rtl: bool = False,
        dialogs: frozenset[str] = frozenset(),
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("wikiEditorToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.editor = editor
        self._msg = msg
        self._rtl = rtl
        self._dialogs = dialogs
        self._recent: list[Any] = [c.config for c in self._character_pages(toolbar)[0].characters]
        self._buttons: dict[str, QToolButton] = {}
        self._shortcuts: list[QShortcut] = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.set_toolbar(toolbar)

    # --- building --------------------------------------------------------------------------

    @staticmethod
    def _character_pages(toolbar: Toolbar) -> tuple[CharacterPage, ...]:
        return tuple(p for p in toolbar.characters.pages if isinstance(p, CharacterPage))

    def set_toolbar(self, toolbar: Toolbar, msg: Messages | None = None) -> None:
        """Rebuild for another language or wiki."""
        if msg is not None:
            self._msg = msg
        self.toolbar = toolbar
        while (item := self._layout.takeAt(0)) is not None:
            if (w := item.widget()) is not None:
                w.deleteLater()
        for s in self._shortcuts:
            s.setEnabled(False)
            s.deleteLater()
        self._shortcuts.clear()
        self._buttons.clear()

        row = QWidget(self)
        row.setObjectName("wikiEditorToolbarRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(2, 2, 2, 2)
        row_layout.setSpacing(2)
        self._add_groups(row_layout, toolbar.main)

        self._stack = QStackedWidget(self)
        self._stack.setVisible(False)
        self._tabs: dict[str, QToolButton] = {}
        for section in toolbar.tabs:
            tab = QToolButton(row)
            tab.setText(section.label or section.id)
            tab.setCheckable(True)
            tab.setAutoRaise(True)
            tab.setObjectName(f"tab-{section.id}")
            index = self._stack.addWidget(self._build_section(section))
            tab.toggled.connect(lambda on, sid=section.id, i=index: self._show_tab(sid, i, on))
            self._tabs[section.id] = tab
            row_layout.addWidget(tab)
        row_layout.addStretch(1)
        self._add_groups(row_layout, toolbar.secondary)

        self._layout.addWidget(row)
        self._layout.addWidget(self._stack)

    def _icon(self, name: str) -> QIcon:
        return codex_icon(name, self._msg.lang, self._rtl, self.palette())

    def _add_groups(self, layout: QHBoxLayout, section: ToolbarSection) -> None:
        for i, group in enumerate(section.groups):
            if i > 0:
                sep = QFrame(self)
                sep.setFrameShape(QFrame.Shape.VLine)
                sep.setFrameShadow(QFrame.Shadow.Plain)
                layout.addWidget(sep)
            if group.label:
                label = QLabel(group.label, self)
                label.setObjectName("wikiEditorGroupLabel")
                layout.addWidget(label)
            for tool in group.tools:
                layout.addWidget(self._build_tool(tool))

    def _build_tool(self, tool: Tool) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(f"tool-{tool.id}")
        button.setAutoRaise(True)
        mac = sys.platform == "darwin"
        button.setToolTip(shortcut_label(self._msg, tool.label, tool.hotkey, mac))
        button.setAccessibleName(tool.label)
        if tool.type == "select":
            button.setText(tool.label)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            menu = QMenu(button)
            for option in tool.options:
                act = menu.addAction(option.label)
                act.setObjectName(f"option-{option.id}")
                act.triggered.connect(lambda _=False, a=option.action: self.run_action(a))
            button.setMenu(menu)
        else:
            if tool.icon:
                button.setIcon(self._icon(tool.icon))
                button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
            else:
                button.setText(tool.label)
            if tool.action is not None:
                action = tool.action
                if isinstance(action, DialogAction) and action.module not in self._dialogs:
                    button.setEnabled(False)
                button.clicked.connect(lambda _=False, a=action: self.run_action(a))
                if tool.hotkey:
                    shortcut = QShortcut(QKeySequence(f"Ctrl+{tool.hotkey}"), self.editor)
                    shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
                    shortcut.activated.connect(lambda a=action: self.run_action(a))
                    self._shortcuts.append(shortcut)
        self._buttons[tool.id] = button
        return button

    def _build_section(self, section: ToolbarSection | BookletSection) -> QWidget:
        if isinstance(section, ToolbarSection):
            page = QWidget(self)
            layout = QHBoxLayout(page)
            layout.setContentsMargins(2, 2, 2, 2)
            layout.setSpacing(2)
            self._add_groups(layout, section)
            layout.addStretch(1)
            return page
        pages = section.pages
        if pages and isinstance(pages[0], CharacterPage):
            return self._build_characters(self._character_pages(self.toolbar))
        return self._build_help(tuple(p for p in pages if isinstance(p, HelpPage)))

    def _booklet(self, labels: list[str]) -> tuple[QWidget, QListWidget, QHBoxLayout]:
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        index = QListWidget(widget)
        index.setObjectName("bookletIndex")
        index.addItems(labels)
        index.setFixedWidth(max(140, index.sizeHintForColumn(0) + 24))
        layout.addWidget(index)
        widget.setFixedHeight(150)
        return widget, index, layout

    def _build_characters(self, pages: tuple[CharacterPage, ...]) -> QWidget:
        widget, index, layout = self._booklet([p.label for p in pages])
        chars = QListWidget(widget)
        chars.setObjectName("specialCharacters")
        chars.setViewMode(QListWidget.ViewMode.IconMode)
        chars.setFlow(QListWidget.Flow.LeftToRight)
        chars.setWrapping(True)
        chars.setResizeMode(QListWidget.ResizeMode.Adjust)
        chars.setMovement(QListWidget.Movement.Static)
        chars.setUniformItemSizes(False)
        chars.setSpacing(1)
        font = chars.font()
        font.setPointSizeF(font.pointSizeF() * 1.25)
        chars.setFont(font)
        chars.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(chars, 1)
        self._chars = chars
        self._char_index = index
        self._char_pages = list(pages)

        def show(row: int) -> None:
            if row < 0:
                return
            if self._char_pages[row].id == "recent":
                self._refresh_recent()
            self._fill_characters(self._char_pages[row])

        index.currentRowChanged.connect(show)
        chars.itemClicked.connect(self._character_clicked)
        # WikiEditor opens the first page (recently used); while that is empty, open the next
        index.setCurrentRow(0 if self._recent else 1)
        return widget

    def _refresh_recent(self) -> None:
        from pyawb.editor.toolbar import character

        recent = tuple(c for c in (character(x, self._msg) for x in self._recent) if c is not None)
        old = self._char_pages[0]
        self._char_pages[0] = CharacterPage(old.id, old.label, recent, old.language, old.direction)

    def _fill_characters(self, page: CharacterPage) -> None:
        chars = self._chars
        chars.clear()
        rtl = page.direction == "rtl"
        chars.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        )
        for char in page.characters:
            item = QListWidgetItem(char.label)
            item.setData(Qt.ItemDataRole.UserRole, char)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if char.title:
                item.setToolTip(char.title)
            chars.addItem(item)

    def _character_clicked(self, item: QListWidgetItem) -> None:
        char: Character = item.data(Qt.ItemDataRole.UserRole)
        self.run_action(char.action)
        self._recent = remember_character(self._recent, char)
        self.recent_changed.emit(list(self._recent))

    def _build_help(self, pages: tuple[HelpPage, ...]) -> QWidget:
        widget, index, layout = self._booklet([p.label for p in pages])
        browser = QTextBrowser(widget)
        browser.setObjectName("helpBrowser")
        browser.setOpenLinks(False)
        layout.addWidget(browser, 1)

        def show(row: int) -> None:
            if 0 <= row < len(pages):
                browser.setHtml(help_html(pages[row]))

        index.currentRowChanged.connect(show)
        index.setCurrentRow(0)
        self._help_browser = browser
        return widget

    def _show_tab(self, section_id: str, index: int, on: bool) -> None:
        if on:
            for sid, tab in self._tabs.items():
                if sid != section_id and tab.isChecked():
                    tab.blockSignals(True)
                    tab.setChecked(False)
                    tab.blockSignals(False)
            self._stack.setCurrentIndex(index)
            # a stack is as tall as its tallest page; size it to the shown one
            page = self._stack.widget(index)
            assert page is not None
            fixed = page.minimumHeight() == page.maximumHeight()
            self._stack.setFixedHeight(page.maximumHeight() if fixed else page.sizeHint().height())
        self._stack.setVisible(any(t.isChecked() for t in self._tabs.values()))

    # --- state and actions ---------------------------------------------------------------

    def button(self, tool_id: str) -> QToolButton:
        return self._buttons[tool_id]

    def tab(self, section_id: str) -> QToolButton:
        return self._tabs[section_id]

    @property
    def recent_characters(self) -> list[Any]:
        return list(self._recent)

    def set_recent_characters(self, recent: list[Any]) -> None:
        self._recent = list(recent)
        if self._char_index.currentRow() == 0:
            self._refresh_recent()
            self._fill_characters(self._char_pages[0])

    def set_namespace(self, namespace: int, wants_signature: bool) -> None:
        """Show the signature tool only where signatures belong (talk pages and so on)."""
        del namespace
        if "signature" in self._buttons:
            self._buttons["signature"].setVisible(wants_signature)

    def run_action(self, action: Action) -> None:
        if isinstance(action, DialogAction):
            self.dialog_requested.emit(action.module)
            return
        apply_action(self.editor, action)


def help_html(page: HelpPage) -> str:
    head = "".join(f"<th align='start'>{h}</th>" for h in page.headings)
    rows = "".join(
        f"<tr><td>{r.description}</td><td><code>{r.syntax}</code></td><td>{r.result}</td></tr>"
        for r in page.rows
    )
    return f"<table cellspacing='0' cellpadding='4' width='100%'><tr>{head}</tr>{rows}</table>"
