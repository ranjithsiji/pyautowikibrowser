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
# After AutoWikiBrowser WikiFunctions/SubstTemplates.cs (GPL-2.0-or-later).
"""Substitute templates: the list of templates and the options; rules.substtemplates does the
work."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyawb.ui.editor_dialogs import primary_button


@dataclass(frozen=True)
class SubstSettings:
    templates: tuple[str, ...] = ()
    ignore_unformatted: bool = False
    expand_recursively: bool = True  # AWB's default
    include_comments: bool = False


class SubstTemplatesDialog(QDialog):
    def __init__(self, settings: SubstSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Substitute templates"))
        self.initial = settings
        self.templates = QPlainTextEdit("\n".join(settings.templates), self)
        self.templates.setPlaceholderText(self.tr("One template per line, e.g. Unsigned"))
        self.ignore = QCheckBox(
            self.tr("Ignore external/interwiki links, images, nowiki, math and <!-- -->"), self
        )
        self.ignore.setChecked(settings.ignore_unformatted)
        self.expand = QCheckBox(self.tr("Expand recursively"), self)
        self.expand.setToolTip(
            self.tr("Expand the templates through the wiki instead of adding subst:")
        )
        self.expand.setChecked(settings.expand_recursively)
        self.comment = QCheckBox(self.tr("Include comment with template name"), self)
        self.comment.setChecked(settings.include_comments)
        self.expand.toggled.connect(self.comment.setEnabled)
        self.comment.setEnabled(settings.expand_recursively)
        clear = QPushButton(self.tr("Clear"), self)
        clear.clicked.connect(self.templates.clear)
        reset = QPushButton(self.tr("Reset"), self)
        reset.setToolTip(self.tr("Back to the list as it was when this window opened"))
        reset.clicked.connect(
            lambda: self.templates.setPlainText("\n".join(self.initial.templates))
        )
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        primary_button(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        grid = QGridLayout()
        grid.addWidget(self.ignore, 0, 0, 1, 2)
        grid.addWidget(self.expand, 1, 0)
        grid.addWidget(self.comment, 1, 1)
        bottom = QGridLayout()
        bottom.addWidget(clear, 0, 0)
        bottom.addWidget(reset, 0, 1)
        bottom.setColumnStretch(2, 1)
        bottom.addWidget(buttons, 0, 3)
        top = QVBoxLayout(self)
        top.addWidget(QLabel(self.tr("Templates to substitute:"), self))
        top.addWidget(self.templates, 1)
        top.addLayout(grid)
        top.addLayout(bottom)
        self.resize(420, 320)

    def value(self) -> SubstSettings:
        lines = [line.strip() for line in self.templates.toPlainText().splitlines()]
        return SubstSettings(
            templates=tuple(line for line in lines if line),
            ignore_unformatted=self.ignore.isChecked(),
            expand_recursively=self.expand.isChecked(),
            include_comments=self.comment.isChecked(),
        )
