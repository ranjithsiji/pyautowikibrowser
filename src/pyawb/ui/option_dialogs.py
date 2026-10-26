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
# After AutoWikiBrowser AWB/SkipOptions.cs and AWB/SummaryEditor.cs (GPL-2.0-or-later).
"""Small option dialogs: "Skip if no…" (the general fixes' auto changes) and the default edit
summaries."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyawb.core.process import SKIP_IF_NO
from pyawb.ui.editor_dialogs import primary_button


class SkipIfNoDialog(QDialog):
    """Skip if no…: skip a page when general fixes made none of the chosen changes."""

    def __init__(self, chosen: Collection[int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Skip if no…"))
        self.check_all = QCheckBox(self.tr("all"), self)
        self.check_none = QCheckBox(self.tr("none"), self)
        self.list = QListWidget(self)
        self.list.setObjectName("checkList")
        for alert_id, label, _field in SKIP_IF_NO:
            item = QListWidgetItem(self.tr(label), self.list)
            item.setData(Qt.ItemDataRole.UserRole, alert_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if alert_id in chosen else Qt.CheckState.Unchecked
            )
        self.check_all.toggled.connect(lambda on: on and self._set_all(True))
        self.check_none.toggled.connect(lambda on: on and self._set_all(False))
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Check"), self))
        row.addWidget(self.check_all)
        row.addWidget(self.check_none)
        row.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.accept)  # AWB's form only has Close; the choice stays
        top = QVBoxLayout(self)
        top.addLayout(row)
        top.addWidget(self.list, 1)
        top.addWidget(buttons)
        self.resize(300, 420)

    def _set_all(self, on: bool) -> None:
        """CheckAll / CheckNone: the two exclude each other."""
        (self.check_none if on else self.check_all).setChecked(False)
        state = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item is not None:
                item.setCheckState(state)

    def value(self) -> frozenset[int]:
        chosen: set[int] = set()
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                chosen.add(int(item.data(Qt.ItemDataRole.UserRole)))
        return frozenset(chosen)


class SummaryEditorDialog(QDialog):
    """Options ▸ Default edit summaries: one summary per line, with Sort."""

    def __init__(self, summaries: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Default edit summaries"))
        self.text = QPlainTextEdit("\n".join(summaries), self)
        self.text.setPlaceholderText(self.tr("One edit summary per line"))
        sort = QPushButton(self.tr("Sort"), self)
        sort.clicked.connect(self.sort)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        primary_button(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(sort)
        row.addStretch(1)
        row.addWidget(buttons)
        top = QVBoxLayout(self)
        top.addWidget(self.text, 1)
        top.addLayout(row)
        self.resize(520, 360)

    def sort(self) -> None:
        """btnSort: the lines in ordinal order, empty ones dropped."""
        lines = sorted(line for line in self.text.toPlainText().splitlines() if line)
        self.text.setPlainText("\n".join(lines))

    def value(self) -> tuple[str, ...]:
        lines = (line.strip() for line in self.text.toPlainText().splitlines())
        return tuple(line for line in lines if line)
