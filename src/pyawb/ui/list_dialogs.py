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
# After AutoWikiBrowser WikiFunctions/Lists/ListFilterForm.cs and
# Lists/Providers/AdvancedRegexHtmlScraper.cs (GPL-2.0-or-later).
"""Dialogs of the list maker: the List filter and the advanced regex HTML scraper."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import regex
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyawb.core import namespace
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import SiteConfig, use_site
from pyawb.lists.listfilter import ListFilter, SetOperation
from pyawb.lists.providers import TextFileListProvider, titles_from_paste
from pyawb.ui.editor_dialogs import primary_button


class ListFilterDialog(QDialog):
    """List ▸ Filter…: namespaces to keep (content and talk columns), titles to remove or keep,
    sorting, duplicates, and a set operation with a second list."""

    def __init__(self, site: SiteConfig, current: ListFilter, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("List filter"))
        self.site = site

        ns_box = QGroupBox(self.tr("Namespaces to keep"), self)
        self.content_all = QCheckBox(self.tr("Content"), ns_box)
        self.talk_all = QCheckBox(self.tr("Talk"), ns_box)
        self.content = QListWidget(ns_box)
        self.talk = QListWidget(ns_box)
        for lst in (self.content, self.talk):
            lst.setObjectName("checkList")
        content_names = {0: self.tr("Content")} | {
            k: v for k, v in site.namespaces.items() if k > 0 and not namespace.is_talk(k)
        }
        for lst, items in (
            (self.content, content_names),
            (self.talk, {k: v for k, v in site.namespaces.items() if namespace.is_talk(k)}),
        ):
            for ns, name in sorted(items.items()):
                item = QListWidgetItem(name, lst)
                item.setData(Qt.ItemDataRole.UserRole, ns)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                checked = ns in current.namespaces
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.content_all.toggled.connect(lambda on: self._check_all(self.content, on))
        self.talk_all.toggled.connect(lambda on: self._check_all(self.talk, on))
        grid = QGridLayout(ns_box)
        grid.addWidget(self.content_all, 0, 0)
        grid.addWidget(self.talk_all, 0, 1)
        grid.addWidget(self.content, 1, 0)
        grid.addWidget(self.talk, 1, 1)

        title_box = QGroupBox(self.tr("Title"), self)
        self.remove_check = QCheckBox(self.tr("Remove titles containing:"), title_box)
        self.remove_text = QLineEdit(current.remove_containing, title_box)
        self.keep_check = QCheckBox(self.tr("Keep titles containing:"), title_box)
        self.keep_text = QLineEdit(current.keep_containing, title_box)
        self.is_regex = QCheckBox(self.tr("Regular expressions"), title_box)
        self.remove_check.setChecked(bool(current.remove_containing))
        self.keep_check.setChecked(bool(current.keep_containing))
        self.is_regex.setChecked(current.is_regex)
        for check, text in (
            (self.remove_check, self.remove_text),
            (self.keep_check, self.keep_text),
        ):
            text.setEnabled(check.isChecked())
            check.toggled.connect(text.setEnabled)
            check.toggled.connect(self._update_regex)
        self._update_regex()
        tl = QVBoxLayout(title_box)
        for w in (
            self.remove_check,
            self.remove_text,
            self.keep_check,
            self.keep_text,
            self.is_regex,
        ):
            tl.addWidget(w)

        other_box = QGroupBox(self.tr("Other"), self)
        self.sort = QCheckBox(self.tr("Sort alphabetically"), other_box)
        self.sort.setChecked(current.sort)
        self.dedupe = QCheckBox(self.tr("Remove duplicates"), other_box)
        self.dedupe.setChecked(current.remove_duplicates)
        ol = QVBoxLayout(other_box)
        ol.addWidget(self.sort)
        ol.addWidget(self.dedupe)

        set_box = QGroupBox(self.tr("Set operations"), self)
        self.operation = QComboBox(set_box)
        self.operation.addItem(self.tr("Remove these pages (difference)"), SetOperation.DIFFERENCE)
        self.operation.addItem(
            self.tr("Keep only these pages (intersection)"), SetOperation.INTERSECTION
        )
        self.operation.setCurrentIndex(int(current.operation))
        self.other = QListWidget(set_box)
        self.other.addItems(list(current.other))
        open_file = QPushButton(self.tr("Open file…"), set_box)
        open_file.clicked.connect(self._open_file)
        paste = QPushButton(self.tr("Paste"), set_box)
        paste.clicked.connect(self._paste)
        clear = QPushButton(self.tr("Clear"), set_box)
        clear.clicked.connect(self.other.clear)
        sl = QVBoxLayout(set_box)
        sl.addWidget(self.operation)
        sl.addWidget(self.other, 1)
        buttons_row = QHBoxLayout()
        for b in (open_file, paste, clear):
            buttons_row.addWidget(b)
        sl.addLayout(buttons_row)

        middle = QVBoxLayout()
        middle.addWidget(title_box)
        middle.addWidget(other_box)
        middle.addStretch(1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close, self
        )
        apply = buttons.button(QDialogButtonBox.StandardButton.Apply)
        primary_button(apply)
        apply.clicked.connect(self._apply)
        buttons.rejected.connect(self.reject)

        row = QHBoxLayout()
        row.addWidget(ns_box, 3)
        row.addLayout(middle, 2)
        row.addWidget(set_box, 2)
        top = QVBoxLayout(self)
        top.addLayout(row, 1)
        top.addWidget(buttons)
        self.resize(960, 480)

    @staticmethod
    def _check_all(lst: QListWidget, on: bool) -> None:
        state = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for i in range(lst.count()):
            lst.item(i).setCheckState(state)

    def _update_regex(self) -> None:
        self.is_regex.setEnabled(self.remove_check.isChecked() or self.keep_check.isChecked())

    def _open_file(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Page list"), "", self.tr("Text files (*.txt);;All files (*)")
        )
        with use_site(self.site):
            for name in names:
                for a in TextFileListProvider().make_list(str(Path(name))):
                    self.other.addItem(a.name)

    def _paste(self) -> None:
        from PySide6.QtWidgets import QApplication

        with use_site(self.site):
            for a in titles_from_paste(QApplication.clipboard().text()):
                self.other.addItem(a.name)

    def value(self) -> ListFilter:
        chosen = {
            int(lst.item(i).data(Qt.ItemDataRole.UserRole))
            for lst in (self.content, self.talk)
            for i in range(lst.count())
            if lst.item(i).checkState() == Qt.CheckState.Checked
        }
        return ListFilter(
            namespaces=frozenset(chosen),
            remove_containing=self.remove_text.text() if self.remove_check.isChecked() else "",
            keep_containing=self.keep_text.text() if self.keep_check.isChecked() else "",
            is_regex=self.is_regex.isChecked(),
            remove_duplicates=self.dedupe.isChecked(),
            sort=self.sort.isChecked(),
            operation=SetOperation(self.operation.currentData()),
            other=tuple(self.other.item(i).text() for i in range(self.other.count())),
        )

    def _apply(self) -> None:
        f = self.value()
        for text in (f.remove_containing, f.keep_containing):
            if f.is_regex and text:
                try:
                    DotNetRegex(text)
                except (ValueError, regex.error) as e:
                    QMessageBox.warning(self, self.tr("Bad regex"), str(e))
                    return
        self.accept()


class AdvancedScraperDialog(QDialog):
    """The regex, options and group for HTML Scraper (advanced regex)."""

    def __init__(self, settings: Mapping[str, object], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Advanced Regex Html Scraper"))
        self.pattern = QLineEdit(str(settings.get("pattern", "")), self)
        self.pattern.setPlaceholderText('title="([^"]+)"')
        self.case_sensitive = QCheckBox(self.tr("Case sensitive"), self)
        self.case_sensitive.setChecked(bool(settings.get("case_sensitive", False)))
        self.singleline = QCheckBox(self.tr("SingleLine"), self)
        self.singleline.setChecked(bool(settings.get("singleline", False)))
        self.multiline = QCheckBox(self.tr("MultiLine"), self)
        self.multiline.setChecked(bool(settings.get("multiline", False)))
        self.group = QSpinBox(self)
        self.group.setRange(0, 99)
        group_value = settings.get("group", 1)
        self.group.setValue(group_value if isinstance(group_value, int) else 1)
        options = QHBoxLayout()
        for w in (self.case_sensitive, self.singleline, self.multiline):
            options.addWidget(w)
        form = QFormLayout()
        form.addRow(self.tr("Regex:"), self.pattern)
        form.addRow(options)
        form.addRow(self.tr("Group:"), self.group)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        primary_button(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        top = QVBoxLayout(self)
        top.addLayout(form)
        top.addWidget(buttons)

    def value(self) -> dict[str, object]:
        return {
            "pattern": self.pattern.text(),
            "case_sensitive": self.case_sensitive.isChecked(),
            "singleline": self.singleline.isChecked(),
            "multiline": self.multiline.isChecked(),
            "group": self.group.value(),
        }

    def _ok(self) -> None:
        try:
            DotNetRegex(self.pattern.text())
        except (ValueError, regex.error) as e:  # AWB: "Bad Regex"
            QMessageBox.warning(self, self.tr("Bad regex"), str(e))
            return
        if not self.pattern.text():
            QMessageBox.warning(self, self.tr("Bad regex"), self.tr("Enter a regex"))
            return
        self.accept()
