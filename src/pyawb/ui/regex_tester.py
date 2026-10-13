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
# After AutoWikiBrowser WikiFunctions/Controls/RegexTester.cs (GPL-2.0-or-later).
"""AWB Regex Tester: try a .NET-syntax regex (and a replacement) on some text. Opened from
Tools and from the Test… buttons of the advanced find and replace, which take back what was
edited when the tester is closed with OK."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyawb.rules import regextest
from pyawb.ui.editor_dialogs import primary_button


class RegexTesterDialog(QDialog):
    def __init__(
        self,
        find: str = "",
        replace: str | None = "",
        *,
        ignore_case: bool = False,
        multiline: bool = False,
        singleline: bool = False,
        text: str = "",
        returns: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        """replace None: the caller has no replacement (an If condition). returns: show OK and
        Cancel so the caller can take back the edited pattern and options."""
        super().__init__(parent)
        self.setWindowTitle(self.tr("AWB Regex Tester"))
        self.find_box = QPlainTextEdit(find, self)
        self.find_box.setTabChangesFocus(True)
        self.replace_box = QLineEdit(replace or "", self)
        self.replace_box.setEnabled(replace is not None)
        options = QGroupBox(self.tr("RegexOptions"), self)
        self.multiline = QCheckBox(self.tr("MultiLine"), options)
        self.multiline.setChecked(multiline)
        self.singleline = QCheckBox(self.tr("SingleLine"), options)
        self.singleline.setChecked(singleline)
        self.ignore_case = QCheckBox(self.tr("IgnoreCase"), options)
        self.ignore_case.setChecked(ignore_case)
        self.explicit_capture = QCheckBox(self.tr("ExplicitCapture"), options)
        og = QGridLayout(options)
        og.addWidget(self.multiline, 0, 0)
        og.addWidget(self.singleline, 0, 1)
        og.addWidget(self.ignore_case, 1, 0)
        og.addWidget(self.explicit_capture, 1, 1)
        self.find_button = QPushButton(self.tr("Find"), self)
        self.find_button.clicked.connect(self.run_find)
        self.replace_button = QPushButton(self.tr("Replace"), self)
        self.replace_button.clicked.connect(self.run_replace)
        self.replace_button.setEnabled(replace is not None)
        self.text = QPlainTextEdit(text, self)
        self.result_box = QPlainTextEdit(self)
        self.result_box.setReadOnly(True)
        self.status = QLabel(self)

        grid = QGridLayout()
        grid.addWidget(QLabel(self.tr("Find:"), self), 0, 0)
        grid.addWidget(self.find_box, 0, 1)
        grid.addWidget(options, 0, 2)
        grid.addWidget(QLabel(self.tr("Replace:"), self), 1, 0)
        grid.addWidget(self.replace_box, 1, 1)
        actions = QHBoxLayout()
        actions.addWidget(self.find_button)
        actions.addWidget(self.replace_button)
        grid.addLayout(actions, 1, 2)
        grid.addWidget(QLabel(self.tr("Text to search:"), self), 2, 0)
        grid.addWidget(self.text, 2, 1, 1, 2)
        grid.addWidget(QLabel(self.tr("Result:"), self), 3, 0)
        grid.addWidget(self.result_box, 3, 1, 1, 2)
        grid.setRowStretch(2, 1)
        grid.setRowStretch(3, 1)
        grid.setColumnStretch(1, 1)
        top = QVBoxLayout(self)
        top.addLayout(grid, 1)
        top.addWidget(self.status)
        if returns:
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
            )
            primary_button(buttons.button(QDialogButtonBox.StandardButton.Ok))
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            top.addWidget(buttons)
        self.find_box.textChanged.connect(self._update)
        self._update()
        self.resize(720, 540)

    def _update(self) -> None:
        has = bool(self.find_box.toPlainText())
        self.find_button.setEnabled(has)
        self.replace_button.setEnabled(has and self.replace_box.isEnabled())

    def _options(self) -> regextest.DotNetOptions:
        return regextest.options_from(
            ignore_case=self.ignore_case.isChecked(),
            multiline=self.multiline.isChecked(),
            singleline=self.singleline.isChecked(),
            explicit_capture=self.explicit_capture.isChecked(),
        )

    def run_find(self) -> None:
        test = regextest.find(self.find_box.toPlainText(), self._options(), self.text.toPlainText())
        self.result_box.setPlainText(regextest.describe(test))
        self.status.setText(test.error or self.tr("%n match(es)", "", len(test.matches)))

    def run_replace(self) -> None:
        test = regextest.replace(
            self.find_box.toPlainText(),
            self.replace_box.text(),
            self._options(),
            self.text.toPlainText(),
        )
        self.result_box.setPlainText(test.error or test.result)
        self.status.setText(test.error or self.tr("%n replacement(s)", "", len(test.matches)))
