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

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyawb.core.article import CategorisationOptions, ImageReplaceOptions, TypoFixer
from pyawb.core.process import (
    ContainsCheck,
    ProcessOptions,
    clean_category_input,
    clean_file_input,
)
from pyawb.core.site import SiteConfig, current_site
from pyawb.editloop import LoopOptions
from pyawb.rules.findreplace import find_and_replace_from_rows
from pyawb.rules.skip import create_comparer
from pyawb.ui.find_replace_dialog import FindReplaceDialog, FindReplaceSettings

# AWB's combo box items, in its order (the enum values)
CATEGORY_ACTIONS = (
    ("Categories: no change", CategorisationOptions.NO_ACTION),
    ("Replace category", CategorisationOptions.RE_CAT),
    ("Add category", CategorisationOptions.ADD_CAT),
    ("Remove category", CategorisationOptions.REMOVE_CAT),
)
FILE_ACTIONS = (
    ("Files: no change", ImageReplaceOptions.NO_ACTION),
    ("Replace file", ImageReplaceOptions.REPLACE),
    ("Remove file", ImageReplaceOptions.REMOVE),
    ("Comment out file", ImageReplaceOptions.COMMENT),
)


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
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.enabled, 0, 0)
        grid.addWidget(self.text, 0, 1, 1, 3)
        grid.addWidget(self.regex, 1, 1)
        grid.addWidget(self.case, 1, 2)
        grid.addWidget(self.after, 1, 3)

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


def _scrolled(page: QWidget) -> QScrollArea:
    """A tab's page that scrolls when the panel is narrower or shorter than it."""
    area = QScrollArea()
    area.setWidget(page)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    return area


class OptionsPanel(QTabWidget):
    typos_toggled = Signal(bool)  # "Fix typos" switched: the list is loaded on first use

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("optionsPanel")
        self.far_settings = FindReplaceSettings()
        self.site: SiteConfig = current_site()
        self._make_options_tab()
        self._make_more_tab()
        self._make_skip_tab()

    # -- tabs ---------------------------------------------------------------------------------

    def _make_options_tab(self) -> None:
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
        general = QVBoxLayout()
        for w in (
            self.general_fixes,
            self.auto_tag,
            self.unicodify,
            self.follow_redirects,
            self.section_summary,
            self.ignore_nobots,
        ):
            general.addWidget(w)

        far = QGroupBox(self.tr("Find and replace"), options)
        self.find_replace = QCheckBox(self.tr("Find and replace"), far)
        self.far_rules = QPushButton(self.tr("Rules…"), far)
        self.far_rules.clicked.connect(self.edit_find_replace)
        self.far_count = QLabel(far)
        self.skip_no_far = QCheckBox(self.tr("Skip if no replacement"), far)
        self.skip_minor_far = QCheckBox(self.tr("Skip if only minor replacements"), far)
        fl = QGridLayout(far)
        fl.addWidget(self.find_replace, 0, 0)
        fl.addWidget(self.far_rules, 0, 1)
        fl.addWidget(self.far_count, 1, 0, 1, 2)
        fl.addWidget(self.skip_no_far, 2, 0, 1, 2)
        fl.addWidget(self.skip_minor_far, 3, 0, 1, 2)

        typos = QGroupBox(self.tr("Typo fixing"), options)
        self.fix_typos = QCheckBox(self.tr("Fix typos (RegExTypoFix)"), typos)
        self.fix_typos.toggled.connect(self.typos_toggled)
        self.typo_status = QLabel(self.tr("Not loaded"), typos)
        self.typo_status.setWordWrap(True)
        self.skip_no_typo = QCheckBox(self.tr("Skip if no typo fixed"), typos)
        tl = QVBoxLayout(typos)
        for w in (self.fix_typos, self.typo_status, self.skip_no_typo):
            tl.addWidget(w)
        tl.addStretch(1)

        # one narrow column, as AWB's control panel
        column = QVBoxLayout(options)
        column.addLayout(general)
        column.addWidget(far)
        column.addWidget(typos)
        column.addStretch(1)
        self.addTab(_scrolled(options), self.tr("Options"))
        self._update_far_count()

    def _make_more_tab(self) -> None:
        more = QWidget(self)
        append = QGroupBox(self.tr("Append or prepend text"), more)
        self.append = QCheckBox(self.tr("Enabled"), append)
        self.append_where = QComboBox(append)
        self.append_where.addItem(self.tr("Append"), False)
        self.append_where.addItem(self.tr("Prepend"), True)
        self.append_text = QPlainTextEdit(append)
        self.append_text.setPlaceholderText(self.tr("Text (%%title%% and other keywords work)"))
        self.append_newlines = QSpinBox(append)
        self.append_newlines.setRange(0, 10)
        self.append_newlines.setValue(2)
        self.append_newlines.setPrefix(self.tr("Newlines: "))
        self.append_sort = QCheckBox(self.tr("Sort metadata after"), append)
        al = QGridLayout(append)
        al.addWidget(self.append, 0, 0)
        al.addWidget(self.append_where, 0, 1)
        al.addWidget(self.append_newlines, 1, 0)
        al.addWidget(self.append_sort, 1, 1)
        al.addWidget(self.append_text, 2, 0, 1, 2)

        cats = QGroupBox(self.tr("Categories"), more)
        self.category_action = QComboBox(cats)
        for label, value in CATEGORY_ACTIONS:
            self.category_action.addItem(self.tr(label), value)
        self.category = QLineEdit(cats)
        self.category.setPlaceholderText(self.tr("Category (without the namespace)"))
        self.category2 = QLineEdit(cats)
        self.category2.setPlaceholderText(self.tr("New category (replace)"))
        self.remove_sort_key = QCheckBox(self.tr("Remove sort key"), cats)
        self.skip_no_cat_change = QCheckBox(self.tr("Skip if no change"), cats)
        cl = QFormLayout(cats)
        cl.addRow(self.category_action)
        cl.addRow(self.category)
        cl.addRow(self.category2)
        cl.addRow(self.remove_sort_key)
        cl.addRow(self.skip_no_cat_change)

        files = QGroupBox(self.tr("Files"), more)
        self.file_action = QComboBox(files)
        for label, value in FILE_ACTIONS:
            self.file_action.addItem(self.tr(label), value)
        self.file_replace = QLineEdit(files)
        self.file_replace.setPlaceholderText(self.tr("File (without the namespace)"))
        self.file_with = QLineEdit(files)
        self.file_with.setPlaceholderText(self.tr("With (replace) or comment"))
        self.skip_no_file_change = QCheckBox(self.tr("Skip if no change"), files)
        il = QFormLayout(files)
        il.addRow(self.file_action)
        il.addRow(self.file_replace)
        il.addRow(self.file_with)
        il.addRow(self.skip_no_file_change)

        column = QVBoxLayout(more)
        column.addWidget(append)
        column.addWidget(cats)
        column.addWidget(files)
        column.addStretch(1)
        self.addTab(_scrolled(more), self.tr("More"))

        for edit in (self.category, self.category2):
            edit.editingFinished.connect(
                lambda e=edit: e.setText(clean_category_input(e.text(), self.site))
            )
        for edit in (self.file_replace, self.file_with):
            edit.editingFinished.connect(
                lambda e=edit: e.setText(clean_file_input(e.text(), self.site))
            )
        self.category_action.currentIndexChanged.connect(self._update_more)
        self.file_action.currentIndexChanged.connect(self._update_more)
        self.append.toggled.connect(self._update_more)
        self._update_more()

    def _make_skip_tab(self) -> None:
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
        self.addTab(_scrolled(skip), self.tr("Skip"))

        self.skip_non_existent.toggled.connect(
            lambda on: on and self.skip_existent.setChecked(False)
        )
        self.skip_existent.toggled.connect(
            lambda on: on and self.skip_non_existent.setChecked(False)
        )

    def set_site(self, site: SiteConfig) -> None:
        """The connected wiki (its namespaces for the category and file fields)."""
        self.site = site

    # -- find and replace, more ---------------------------------------------------------------

    def edit_find_replace(self) -> None:
        dialog = FindReplaceDialog(self.far_settings, self)
        if dialog.exec():
            self.set_find_replace(dialog.settings())

    def set_find_replace(self, settings: FindReplaceSettings) -> None:
        self.far_settings = settings
        if settings.rows and not self.find_replace.isChecked():
            self.find_replace.setChecked(True)
        self._update_far_count()

    def _update_far_count(self) -> None:
        enabled = sum(1 for r in self.far_settings.rows if r.enabled)
        self.far_count.setText(
            self.tr("%1 rules, %2 enabled")
            .replace("%1", str(len(self.far_settings.rows)))
            .replace("%2", str(enabled))
        )

    def _update_more(self) -> None:
        cat = self.category_action.currentData()
        for w in (self.category, self.remove_sort_key, self.skip_no_cat_change):
            w.setEnabled(cat != CategorisationOptions.NO_ACTION)
        self.category2.setEnabled(cat == CategorisationOptions.RE_CAT)
        file = self.file_action.currentData()
        for w in (self.file_replace, self.skip_no_file_change):
            w.setEnabled(file != ImageReplaceOptions.NO_ACTION)
        self.file_with.setEnabled(
            file in (ImageReplaceOptions.REPLACE, ImageReplaceOptions.COMMENT)
        )
        on = self.append.isChecked()
        for w in (self.append_where, self.append_text, self.append_newlines, self.append_sort):
            w.setEnabled(on)

    # -- the options --------------------------------------------------------------------------

    def loop_options(
        self,
        summary: str,
        user_name: str,
        no_parse: frozenset[str] = frozenset(),
        no_retf: frozenset[str] = frozenset(),
        typos: TypoFixer | None = None,
    ) -> LoopOptions:
        """The options as set (raises OptionsError for an unusable skip pattern). typos: the
        loaded typo list, used when "Fix typos" is on."""
        far = None
        if self.find_replace.isChecked() and self.far_settings.rows:
            s = self.far_settings
            far = find_and_replace_from_rows(
                s.rows,
                ignore_links=s.ignore_links,
                ignore_more=s.ignore_more,
                add_to_summary=s.add_to_summary,
            )
        p = ProcessOptions(
            user_name=user_name,
            ignore_no_bots=self.ignore_nobots.isChecked(),
            no_parse=no_parse,
            no_retf=no_retf,
            unicodify_whole=self.unicodify.isChecked(),
            find_and_replace=far,
            skip_when_no_far=self.skip_no_far.isChecked(),
            skip_only_minor_far=self.skip_minor_far.isChecked(),
            categorise=self.category_action.currentData(),
            category=self.category.text(),
            category2=self.category2.text(),
            remove_sort_key=self.remove_sort_key.isChecked(),
            skip_no_cat_change=self.skip_no_cat_change.isChecked(),
            general_fixes=self.general_fixes.isChecked(),
            auto_tag=self.auto_tag.isChecked(),
            typos=typos if self.fix_typos.isChecked() else None,
            skip_if_no_typo=self.skip_no_typo.isChecked(),
            append_text=self.append_text.toPlainText() if self.append.isChecked() else "",
            prepend=bool(self.append_where.currentData()),
            append_newlines=self.append_newlines.value(),
            append_sort_metadata=self.append_sort.isChecked(),
            images=self.file_action.currentData(),
            image_replace=self.file_replace.text(),
            image_with=self.file_with.text(),
            skip_no_image_change=self.skip_no_file_change.isChecked(),
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
