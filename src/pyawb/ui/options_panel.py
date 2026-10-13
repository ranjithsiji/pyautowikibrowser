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
"""The processing options (AWB's Options and Skip tabs) as a LoopOptions value."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyawb.core.process import ContainsCheck, ProcessOptions
from pyawb.editloop import LoopOptions
from pyawb.rules.skip import create_comparer


class OptionsError(ValueError):
    """An option the user gave cannot be used (an invalid regex)."""


class _ContainsRow(QWidget):
    def __init__(self, title: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.enabled = QCheckBox(title, self)
        self.text = QLineEdit(self)
        self.regex = QCheckBox(self.tr("Regex"), self)
        self.case = QCheckBox(self.tr("Case sensitive"), self)
        self.after = QCheckBox(self.tr("After processing"), self)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.enabled)
        row.addWidget(self.text, 1)
        row.addWidget(self.regex)
        row.addWidget(self.case)
        row.addWidget(self.after)

    def check(self, negate: bool) -> ContainsCheck | None:
        text = self.text.text()
        if not self.enabled.isChecked() or not text:
            return None
        try:
            comparer = create_comparer(
                text, self.case.isChecked(), self.regex.isChecked(), False, False
            )
        except Exception as e:  # regex.error, UnsupportedPatternError
            raise OptionsError(f"{text}: {e}") from e
        return ContainsCheck(text, comparer, negate=negate, after=self.after.isChecked())


class OptionsPanel(QTabWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("optionsPanel")

        # Options tab
        options = QWidget(self)
        self.general_fixes = QCheckBox(self.tr("Apply general fixes"), options)
        self.general_fixes.setChecked(True)
        self.auto_tag = QCheckBox(self.tr("Auto tag"), options)
        self.unicodify = QCheckBox(self.tr("Unicodify whole page"), options)
        self.unicodify.setChecked(True)
        self.follow_redirects = QCheckBox(self.tr("Follow redirects"), options)
        self.follow_redirects.setChecked(True)
        self.section_summary = QCheckBox(self.tr("Section edit summaries"), options)
        self.section_summary.setChecked(True)
        self.ignore_nobots = QCheckBox(self.tr("Ignore {{bots}} and {{nobots}}"), options)
        grid = QGridLayout(options)
        for i, w in enumerate(
            (
                self.general_fixes,
                self.auto_tag,
                self.unicodify,
                self.follow_redirects,
                self.section_summary,
                self.ignore_nobots,
            )
        ):
            grid.addWidget(w, i % 3, i // 3)
        grid.setRowStretch(3, 1)
        self.addTab(options, self.tr("Options"))

        # Skip tab
        skip = QWidget(self)
        box = QGroupBox(self.tr("Skip the page if"), skip)
        self.skip_no_changes = QCheckBox(self.tr("No changes are made"), box)
        self.skip_no_changes.setChecked(True)
        self.skip_whitespace = QCheckBox(self.tr("Only whitespace is changed"), box)
        self.skip_casing = QCheckBox(self.tr("Only casing is changed"), box)
        self.skip_minor_genfixes = QCheckBox(self.tr("Only minor general fixes"), box)
        self.skip_genfixes = QCheckBox(self.tr("Only general fixes"), box)
        self.skip_no_links = QCheckBox(self.tr("The page has no links"), box)
        self.skip_redirect = QCheckBox(self.tr("The page is a redirect"), box)
        self.skip_in_use = QCheckBox(self.tr("The page is in use ({{inuse}})"), box)
        self.skip_non_existent = QCheckBox(self.tr("The page does not exist"), box)
        self.skip_non_existent.setChecked(True)
        self.skip_existent = QCheckBox(self.tr("The page exists"), box)
        g = QGridLayout(box)
        for i, w in enumerate(
            (
                self.skip_no_changes,
                self.skip_whitespace,
                self.skip_casing,
                self.skip_minor_genfixes,
                self.skip_genfixes,
                self.skip_no_links,
                self.skip_redirect,
                self.skip_in_use,
                self.skip_non_existent,
                self.skip_existent,
            )
        ):
            g.addWidget(w, i % 5, i // 5)
        self.contains = _ContainsRow(self.tr("Contains"), skip)
        self.not_contains = _ContainsRow(self.tr("Doesn't contain"), skip)
        sl = QVBoxLayout(skip)
        sl.addWidget(box)
        sl.addWidget(self.contains)
        sl.addWidget(self.not_contains)
        sl.addStretch(1)
        self.addTab(skip, self.tr("Skip"))

        self.skip_non_existent.toggled.connect(
            lambda on: on and self.skip_existent.setChecked(False)
        )
        self.skip_existent.toggled.connect(
            lambda on: on and self.skip_non_existent.setChecked(False)
        )

    def loop_options(
        self,
        summary: str,
        user_name: str,
        no_parse: frozenset[str] = frozenset(),
        no_retf: frozenset[str] = frozenset(),
    ) -> LoopOptions:
        """The options as set (raises OptionsError for an unusable skip pattern)."""
        p = ProcessOptions(
            user_name=user_name,
            ignore_no_bots=self.ignore_nobots.isChecked(),
            no_parse=no_parse,
            no_retf=no_retf,
            unicodify_whole=self.unicodify.isChecked(),
            general_fixes=self.general_fixes.isChecked(),
            auto_tag=self.auto_tag.isChecked(),
            skip_no_changes=self.skip_no_changes.isChecked(),
            skip_whitespace_only=self.skip_whitespace.isChecked(),
            skip_casing_only=self.skip_casing.isChecked(),
            skip_minor_general_fixes_only=self.skip_minor_genfixes.isChecked(),
            skip_general_fixes_only=self.skip_genfixes.isChecked(),
            skip_no_page_links=self.skip_no_links.isChecked(),
            skip_if_contains=self.contains.check(negate=False),
            skip_if_not_contains=self.not_contains.check(negate=True),
        )
        return LoopOptions(
            process=p,
            follow_redirects=self.follow_redirects.isChecked(),
            skip_if_redirect=self.skip_redirect.isChecked(),
            skip_non_existent=self.skip_non_existent.isChecked(),
            skip_existent=self.skip_existent.isChecked(),
            skip_if_in_use=self.skip_in_use.isChecked(),
            section_summary=self.section_summary.isChecked(),
            summary=summary,
        )
