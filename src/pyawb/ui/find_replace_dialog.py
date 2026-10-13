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
"""The find and replace rules table (AWB's FindandReplace form)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyawb.rules.findreplace import ReplacementRow, next_search_match, row_error
from pyawb.ui.editor_dialogs import primary_button

# (field, header) in AWB's column order; the bool fields are check boxes
COLUMNS: Sequence[tuple[str, str]] = (
    ("find", "Find"),
    ("replace", "Replace with"),
    ("case_sensitive", "Case sensitive"),
    ("is_regex", "Regex"),
    ("multiline", "Multiline"),
    ("singleline", "Singleline"),
    ("minor", "Minor"),
    ("after_fixes", "After fixes"),
    ("enabled", "Enabled"),
    ("comment", "Comment"),
)
_BOOL = {f.name for f in fields(ReplacementRow) if f.type in ("bool", bool)}


@dataclass(frozen=True)
class FindReplaceSettings:
    rows: tuple[ReplacementRow, ...] = ()
    ignore_links: bool = False
    ignore_more: bool = False
    add_to_summary: bool = True


class FindReplaceDialog(QDialog):
    def __init__(self, settings: FindReplaceSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Find and replace"))
        self.resize(1000, 520)

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setObjectName("findReplaceTable")
        self.table.setHorizontalHeaderLabels([self.tr(h) for _, h in COLUMNS])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for col in (0, 1):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(len(COLUMNS) - 1, QHeaderView.ResizeMode.Stretch)
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._header_menu)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(26)
        self.table.cellChanged.connect(self._cell_changed)

        add = QPushButton(self.tr("Insert row"), self)
        add.clicked.connect(lambda: self.insert_row(self._row_after_current()))
        delete = QPushButton(self.tr("Delete rows"), self)
        delete.clicked.connect(self.delete_rows)
        up = QPushButton(self.tr("Move up"), self)
        up.clicked.connect(lambda: self.move_row(-1))
        down = QPushButton(self.tr("Move down"), self)
        down.clicked.connect(lambda: self.move_row(1))
        clear = QPushButton(self.tr("Clear"), self)
        clear.clicked.connect(self.clear)
        row_buttons = QHBoxLayout()
        for b in (add, delete, up, down, clear):
            row_buttons.addWidget(b)
        row_buttons.addStretch(1)
        # AWB's Search + Go: the next row whose Find or Replace with contains the text
        self.search = QLineEdit(self)
        self.search.setPlaceholderText(self.tr("Search"))
        self.search.setClearButtonEnabled(True)
        self.search_go = QPushButton(self.tr("Go"), self)
        self.search_go.setEnabled(False)
        self.search.textChanged.connect(lambda t: self.search_go.setEnabled(bool(t)))
        self.search.returnPressed.connect(self.search_next)
        self.search_go.clicked.connect(self.search_next)
        row_buttons.addWidget(QLabel(self.tr("Search:"), self))
        row_buttons.addWidget(self.search)
        row_buttons.addWidget(self.search_go)

        self.ignore_links = QCheckBox(
            self.tr("Ignore external/interwiki links, images, nowiki, math and <!-- -->"), self
        )
        self.ignore_more = QCheckBox(
            self.tr("Ignore templates, refs, link targets, and headings"), self
        )
        self.add_to_summary = QCheckBox(self.tr("Add replacements to edit summary"), self)
        self.error = QLabel(self)
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.hide()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        primary_button(ok)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(row_buttons)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.ignore_links)
        layout.addWidget(self.ignore_more)
        layout.addWidget(self.add_to_summary)
        layout.addWidget(self.error)
        layout.addWidget(buttons)

        self.set_settings(settings)

    # -- rows ---------------------------------------------------------------------------------

    def search_next(self) -> bool:
        """Go: select the next cell (Find or Replace with) containing the search text."""
        cells: list[tuple[str, str]] = []
        for r in range(self.table.rowCount()):
            find, with_ = (self.table.item(r, c) for c in (0, 1))
            cells.append((find.text() if find else "", with_.text() if with_ else ""))
        hit = next_search_match(cells, self.search.text(), self.table.currentRow())
        if hit is None:
            return False
        row, col = hit
        self.table.setCurrentCell(row, col)
        self.table.scrollTo(self.table.model().index(row, col))
        return True

    def set_settings(self, settings: FindReplaceSettings) -> None:
        self.table.setRowCount(0)
        for row in settings.rows:
            self.insert_row(self.table.rowCount(), row)
        self._ensure_empty_row()
        self.ignore_links.setChecked(settings.ignore_links)
        self.ignore_more.setChecked(settings.ignore_more)
        self.add_to_summary.setChecked(settings.add_to_summary)

    def insert_row(self, index: int, row: ReplacementRow | None = None) -> None:
        row = row or ReplacementRow()
        self.table.blockSignals(True)
        self.table.insertRow(index)
        for col, (name, _) in enumerate(COLUMNS):
            value = getattr(row, name)
            item = QTableWidgetItem()
            if name in _BOOL:
                item.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                )
                item.setCheckState(Qt.CheckState.Checked if value else Qt.CheckState.Unchecked)
            else:
                item.setText(str(value))
            self.table.setItem(index, col, item)
        self.table.blockSignals(False)

    def row(self, index: int) -> ReplacementRow:
        values: dict[str, object] = {}
        for col, (name, _) in enumerate(COLUMNS):
            item = self.table.item(index, col)
            if name in _BOOL:
                values[name] = item is not None and item.checkState() == Qt.CheckState.Checked
            else:
                values[name] = item.text() if item is not None else ""
        return ReplacementRow(**values)  # type: ignore[arg-type]

    def rows(self) -> tuple[ReplacementRow, ...]:
        """The rows with a find pattern, in order (AWB's MakeList)."""
        return tuple(r for i in range(self.table.rowCount()) if (r := self.row(i)).find)

    def settings(self) -> FindReplaceSettings:
        return FindReplaceSettings(
            self.rows(),
            self.ignore_links.isChecked(),
            self.ignore_more.isChecked(),
            self.add_to_summary.isChecked(),
        )

    def _row_after_current(self) -> int:
        current = self.table.currentRow()
        return current + 1 if current >= 0 else self.table.rowCount()

    def _ensure_empty_row(self) -> None:
        """Like a DataGridView's new row: there is always an empty row to type in."""
        n = self.table.rowCount()
        if n == 0 or self.row(n - 1).find:
            self.insert_row(n)

    def _cell_changed(self, row: int, col: int) -> None:
        if COLUMNS[col][0] == "find":
            self._ensure_empty_row()

    def delete_rows(self) -> None:
        for index in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(index)
        self._ensure_empty_row()

    def move_row(self, step: int) -> None:
        index = self.table.currentRow()
        target = index + step
        if index < 0 or not 0 <= target < self.table.rowCount():
            return
        row = self.row(index)
        self.table.removeRow(index)
        self.insert_row(target, row)
        self.table.setCurrentCell(target, self.table.currentColumn())
        self._ensure_empty_row()

    def clear(self) -> None:
        self.table.setRowCount(0)
        self._ensure_empty_row()

    def set_column(self, col: int, checked: bool) -> None:
        """Check or uncheck a column in every row (AWB's "Check all ..." menu)."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.table.rowCount()):
            item = self.table.item(i, col)
            if item is not None:
                item.setCheckState(state)

    def _header_menu(self, pos: QPoint) -> None:
        col = self.table.horizontalHeader().logicalIndexAt(pos)
        if col < 0 or COLUMNS[col][0] not in _BOOL:
            return
        menu = QMenu(self)
        menu.addAction(self.tr("Check all"), lambda: self.set_column(col, True))
        menu.addAction(self.tr("Uncheck all"), lambda: self.set_column(col, False))
        menu.exec(self.table.horizontalHeader().mapToGlobal(pos))

    # -- validation ---------------------------------------------------------------------------

    def first_error(self) -> tuple[int, str] | None:
        for i in range(self.table.rowCount()):
            error = row_error(self.row(i))
            if error:
                return i, error
        return None

    def _accept(self) -> None:
        bad = self.first_error()
        if bad is not None:
            index, error = bad
            self.table.setCurrentCell(index, 0)
            self.error.setText(
                self.tr("Row %1: %2").replace("%1", str(index + 1)).replace("%2", error)
            )
            self.error.show()
            return
        self.accept()
