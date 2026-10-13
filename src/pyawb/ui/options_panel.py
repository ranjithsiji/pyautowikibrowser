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

import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
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
from pyawb.core.site import SiteConfig, current_site, use_site
from pyawb.editloop import LoopOptions
from pyawb.rules.findreplace import find_and_replace_from_rows
from pyawb.rules.replacespecial import IRule, ReplaceSpecial
from pyawb.rules.skip import create_comparer
from pyawb.rules.substtemplates import SubstTemplates
from pyawb.ui.find_replace_dialog import FindReplaceDialog, FindReplaceSettings
from pyawb.ui.replace_special_dialog import ReplaceSpecialDialog
from pyawb.ui.subst_templates_dialog import SubstSettings, SubstTemplatesDialog

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
        self.replace_special_rules: list[IRule] = []
        self.subst_settings = SubstSettings()
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
        # AWB's three buttons: the table, Replace Special and template substitution
        self.far_rules = QPushButton(self.tr("Normal settings"), far)
        self.far_rules.clicked.connect(self.edit_find_replace)
        self.far_advanced = QPushButton(self.tr("Advanced settings"), far)
        self.far_advanced.clicked.connect(self.edit_replace_special)
        self.far_subst = QPushButton(self.tr("Template substitution"), far)
        self.far_subst.clicked.connect(self.edit_subst_templates)
        self.far_count = QLabel(far)
        self.far_count.setWordWrap(True)
        self.skip_no_far = QCheckBox(self.tr("Skip if no replacement"), far)
        self.skip_minor_far = QCheckBox(self.tr("Skip if only minor replacements"), far)
        fl = QGridLayout(far)
        fl.addWidget(self.find_replace, 0, 0)
        fl.addWidget(self.far_rules, 0, 1)
        fl.addWidget(self.far_advanced, 1, 1)
        fl.addWidget(self.far_subst, 2, 1)
        fl.addWidget(self.far_count, 1, 0, 2, 1)
        fl.addWidget(self.skip_no_far, 3, 0, 1, 2)
        fl.addWidget(self.skip_minor_far, 4, 0, 1, 2)

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
        """AWB's Skip tab: text conditions, general skip options (with the kinds of "no
        change" under it) and whether the page must exist."""
        skip = QWidget(self)
        self.contains = _ContainsRow(self.tr("Contains"), skip)
        self.not_contains = _ContainsRow(self.tr("Doesn't contain"), skip)

        box = QGroupBox(self.tr("General skip options"), skip)
        self.skip_in_use = QCheckBox(self.tr("Page is in use"), box)
        self.skip_spam_filter = QCheckBox(self.tr("Edit blocked by spam filter"), box)
        self.skip_spam_filter.setToolTip(
            self.tr("Skip without asking when the spam blacklist stops a save")
        )
        self.skip_no_links = QCheckBox(self.tr("Page contains no links"), box)
        self.skip_no_changes = QCheckBox(self.tr("No changes are made"), box)
        self.skip_no_changes.setChecked(True)
        self.skip_whitespace = QCheckBox(self.tr("Only whitespace"), box)
        self.skip_casing = QCheckBox(self.tr("Only casing"), box)
        self.skip_genfixes = QCheckBox(self.tr("Only genfixes"), box)
        self.skip_minor_genfixes = QCheckBox(self.tr("Only minor genfixes"), box)
        self.skip_cosmetic = QCheckBox(self.tr("Only cosmetic changes"), box)
        self.skip_cosmetic.setToolTip(
            self.tr("The edited page would look the same to readers (asks the wiki to render both)")
        )
        self.skip_redirect = QCheckBox(self.tr("Page is redirect"), box)
        self.skip_no_alerts = QCheckBox(self.tr("No alerts"), box)
        g = QGridLayout(box)
        g.addWidget(self.skip_in_use, 0, 0)
        g.addWidget(self.skip_spam_filter, 0, 1)
        g.addWidget(self.skip_no_links, 1, 0, 1, 2)
        g.addWidget(self.skip_no_changes, 2, 0, 1, 2)
        sub = QGridLayout()
        sub.setContentsMargins(20, 0, 0, 0)  # under "No changes are made", as in AWB
        sub.addWidget(self.skip_whitespace, 0, 0)
        sub.addWidget(self.skip_casing, 0, 1)
        sub.addWidget(self.skip_genfixes, 1, 0)
        sub.addWidget(self.skip_minor_genfixes, 1, 1)
        sub.addWidget(self.skip_cosmetic, 2, 0, 1, 2)
        g.addLayout(sub, 3, 0, 1, 2)
        g.addWidget(self.skip_redirect, 4, 0)
        g.addWidget(self.skip_no_alerts, 4, 1)
        # "Only genfixes" covers the minor ones (AWB disables the second)
        self.skip_genfixes.toggled.connect(lambda on: self.skip_minor_genfixes.setEnabled(not on))

        page = QGroupBox(self.tr("Page"), skip)
        self.page_exists = QRadioButton(self.tr("Exists"), page)
        self.page_exists.setToolTip(self.tr("Skip pages that exist"))
        self.page_missing = QRadioButton(self.tr("Doesn't exist"), page)
        self.page_missing.setToolTip(self.tr("Skip pages that do not exist"))
        self.page_any = QRadioButton(self.tr("Don't care"), page)
        self.page_missing.setChecked(True)
        self.page_group = QButtonGroup(page)
        pl = QHBoxLayout(page)
        for b in (self.page_exists, self.page_missing, self.page_any):
            self.page_group.addButton(b)
            pl.addWidget(b)
        pl.addStretch(1)

        sl = QVBoxLayout(skip)
        sl.addWidget(self.contains)
        sl.addWidget(self.not_contains)
        sl.addWidget(box)
        sl.addWidget(page)
        sl.addStretch(1)
        self.addTab(_scrolled(skip), self.tr("Skip"))

    def set_site(self, site: SiteConfig) -> None:
        """The connected wiki (its namespaces for the category and file fields)."""
        self.site = site

    # -- find and replace, more ---------------------------------------------------------------

    def edit_find_replace(self) -> None:
        dialog = FindReplaceDialog(self.far_settings, self)
        if dialog.exec():
            self.set_find_replace(dialog.settings())

    def edit_replace_special(self) -> None:
        """Advanced settings: Replace Special's rule tree."""
        dialog = ReplaceSpecialDialog(self.replace_special_rules, self)
        if dialog.exec():
            self.set_replace_special(dialog.rules())

    def set_replace_special(self, rules: list[IRule]) -> None:
        self.replace_special_rules = rules
        if rules and not self.find_replace.isChecked():
            self.find_replace.setChecked(True)
        self._update_far_count()

    def edit_subst_templates(self) -> None:
        dialog = SubstTemplatesDialog(self.subst_settings, self)
        if dialog.exec():
            self.set_subst_templates(dialog.value())

    def set_subst_templates(self, settings: SubstSettings) -> None:
        self.subst_settings = settings
        if settings.templates and not self.find_replace.isChecked():
            self.find_replace.setChecked(True)
        self._update_far_count()

    def set_find_replace(self, settings: FindReplaceSettings) -> None:
        self.far_settings = settings
        if settings.rows and not self.find_replace.isChecked():
            self.find_replace.setChecked(True)
        self._update_far_count()

    def _update_far_count(self) -> None:
        enabled = sum(1 for r in self.far_settings.rows if r.enabled)
        parts = [
            self.tr("%1 rules, %2 enabled")
            .replace("%1", str(len(self.far_settings.rows)))
            .replace("%2", str(enabled))
        ]
        if self.replace_special_rules:
            parts.append(self.tr("%n advanced rule(s)", "", len(self.replace_special_rules)))
        if self.subst_settings.templates:
            parts.append(
                self.tr("%n template(s) to substitute", "", len(self.subst_settings.templates))
            )
        self.far_count.setText("\n".join(parts))

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
        replace_special: ReplaceSpecial | None = None
        subst: SubstTemplates | None = None
        if self.find_replace.isChecked():
            # AWB runs the advanced rules and template substitution as part of find and replace
            s = self.far_settings
            if self.replace_special_rules:
                replace_special = ReplaceSpecial(copy.deepcopy(self.replace_special_rules))
            if self.subst_settings.templates:
                st = self.subst_settings
                subst = SubstTemplates(
                    expand_recursively=st.expand_recursively,
                    ignore_unformatted=st.ignore_unformatted,
                    include_comments=st.include_comments,
                )
                with use_site(self.site):
                    subst.template_list = st.templates
            if s.rows or replace_special or subst:
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
            replace_special=replace_special,
            subst_templates=subst,
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
            skip_non_existent=self.page_missing.isChecked(),
            skip_existent=self.page_exists.isChecked(),
            skip_if_no_alerts=self.skip_no_alerts.isChecked(),
            skip_cosmetic=self.skip_cosmetic.isChecked(),
            skip_if_in_use=self.skip_in_use.isChecked(),
            section_summary=self.section_summary.isChecked(),
            summary=summary,
        )
