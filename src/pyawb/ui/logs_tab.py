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
"""AWB's Logs tab: pages saved and pages skipped (by whom and why)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _LogTable(QWidget):
    add_to_list = Signal(list)

    def __init__(self, caption: str, headers: list[str], parent: QWidget) -> None:
        super().__init__(parent)
        self.caption = caption
        self.label = QLabel(self)
        self.table = QTableWidget(0, len(headers), self)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        save = QPushButton(self.tr("Save log"), self)
        save.clicked.connect(self.save)
        add = QPushButton(self.tr("Add all to list"), self)
        add.clicked.connect(lambda: self.add_to_list.emit(self.pages()))
        clear = QPushButton(self.tr("Clear"), self)
        clear.clicked.connect(self.clear)
        buttons = QHBoxLayout()
        buttons.addWidget(save)
        buttons.addWidget(add)
        buttons.addStretch(1)
        buttons.addWidget(clear)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        self._update_label()

    def add(self, *values: str) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, value in enumerate(values):
            self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.scrollToBottom()
        self._update_label()

    def rows(self) -> list[list[str]]:
        out: list[list[str]] = []
        for r in range(self.table.rowCount()):
            cells = [self.table.item(r, c) for c in range(self.table.columnCount())]
            out.append([c.text() if c is not None else "" for c in cells])
        return out

    def pages(self) -> list[str]:
        return [row[0] for row in self.rows()]

    def clear(self) -> None:
        self.table.setRowCount(0)
        self._update_label()

    def save(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save log"), "", self.tr("Text files (*.txt);;All files (*)")
        )
        if name:
            lines = ["\t".join(row) for row in self.rows()]
            with open(name, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

    def _update_label(self) -> None:
        self.label.setText(f"{self.caption} {self.table.rowCount()}")


class LogsTab(QWidget):
    add_to_list = Signal(list)  # page titles

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.saved = _LogTable(
            self.tr("Successfully saved:"), [self.tr("Page"), self.tr("Time")], self
        )
        self.skipped = _LogTable(
            self.tr("Skipped:"),
            [self.tr("Page"), self.tr("Time"), self.tr("Skipped by"), self.tr("Skip reason")],
            self,
        )
        for t in (self.saved, self.skipped):
            t.add_to_list.connect(self.add_to_list)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.saved, 1)
        layout.addWidget(self.skipped, 1)

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_saved(self, page: str) -> None:
        self.saved.add(page, self._now())

    def log_skipped(self, page: str, by: str, reason: str) -> None:
        self.skipped.add(page, self._now(), by, reason)
