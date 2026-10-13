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
# After AutoWikiBrowser WikiFunctions/ReplaceSpecial/ReplaceSpecial.cs, RuleControl.cs,
# InTemplateRuleControl.cs and TemplateParamRuleControl.cs (GPL-2.0-or-later).
"""Advanced find and replace (AWB's Replace Special): a tree of rules, each edited on the right.
The rules themselves are rules.replacespecial's; this dialog only edits them."""

from __future__ import annotations

import copy
from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QBrush, QColor, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pyawb.core.rx import DotNetOptions
from pyawb.rules.replacespecial import (
    InTemplateRule,
    IRule,
    Rule,
    RuleHistory,
    RuleType,
    TemplateParamRule,
)
from pyawb.ui import theme
from pyawb.ui.editor_dialogs import primary_button
from pyawb.ui.icons import codex_icon
from pyawb.ui.regex_tester import RegexTesterDialog

RULE_ROLE = Qt.ItemDataRole.UserRole


def _options(case: QCheckBox, multi: QCheckBox, single: QCheckBox) -> DotNetOptions:
    opts = DotNetOptions.NONE
    if not case.isChecked():
        opts |= DotNetOptions.IGNORE_CASE
    if single.isChecked():
        opts |= DotNetOptions.SINGLELINE
    if multi.isChecked():
        opts |= DotNetOptions.MULTILINE
    return opts


def _show_options(
    opts: DotNetOptions, case: QCheckBox, multi: QCheckBox, single: QCheckBox
) -> None:
    case.setChecked(not opts & DotNetOptions.IGNORE_CASE)
    multi.setChecked(bool(opts & DotNetOptions.MULTILINE))
    single.setChecked(bool(opts & DotNetOptions.SINGLELINE))


def _children(item: QTreeWidgetItem) -> list[QTreeWidgetItem]:
    found = (item.child(i) for i in range(item.childCount()))
    return [c for c in found if c is not None]


class _Header(QWidget):
    """Name and Enabled, at the top of every rule editor."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.name = QLineEdit(self)
        self.enabled = QCheckBox(self.tr("Enabled"), self)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(self.tr("Name"), self))
        row.addWidget(self.name, 1)
        row.addWidget(self.enabled)


class RuleEditor(QGroupBox):
    """RuleControl: find and replace, its type, and the If conditions."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(self.tr("Find and replace"), parent)
        self.header = _Header(self)
        self.type = QComboBox(self)
        self.type.addItem(self.tr("Entire text"), RuleType.ON_WHOLE_PAGE)
        self.type.addItem(self.tr("Inside templates {{..}}"), RuleType.INSIDE_TEMPLATE)
        tabs = QTabWidget(self)

        find = QWidget(tabs)
        self.find_text = QPlainTextEdit(find)
        self.replace_with = QPlainTextEdit(find)
        self.is_regex = QCheckBox(self.tr("Regular expression"), find)
        self.case = QCheckBox(self.tr("Case sensitive"), find)
        self.multiline = QCheckBox(self.tr("Multiline"), find)
        self.singleline = QCheckBox(self.tr("Singleline"), find)
        self.times = QSpinBox(find)
        self.times.setRange(1, 100)
        self.test_find = QPushButton(self.tr("Test…"), find)
        self.test_find.clicked.connect(self._test_find)
        fg = QGridLayout(find)
        fg.addWidget(self.find_text, 0, 0, 1, 4)
        fg.addWidget(QLabel(self.tr("Replace with:"), find), 1, 0, 1, 4)
        fg.addWidget(self.replace_with, 2, 0, 1, 4)
        fg.addWidget(self.is_regex, 3, 0)
        fg.addWidget(self.multiline, 3, 1)
        fg.addWidget(QLabel(self.tr("Apply No. of times"), find), 3, 2)
        fg.addWidget(self.times, 3, 3)
        fg.addWidget(self.case, 4, 0)
        fg.addWidget(self.singleline, 4, 1)
        fg.addWidget(self.test_find, 4, 3)
        tabs.addTab(find, self.tr("Find"))

        cond = QWidget(tabs)
        self.if_contains = QPlainTextEdit(cond)
        self.if_not_contains = QPlainTextEdit(cond)
        self.if_regex = QCheckBox(self.tr("Regular expression"), cond)
        self.if_case = QCheckBox(self.tr("Case sensitive"), cond)
        self.if_multiline = QCheckBox(self.tr("Multiline"), cond)
        self.if_singleline = QCheckBox(self.tr("Singleline"), cond)
        self.test_if = QPushButton(self.tr("Test…"), cond)
        test_menu = QMenu(self.test_if)
        test_menu.addAction(self.tr("Test if contains…"), lambda: self._test_if(self.if_contains))
        test_menu.addAction(
            self.tr("Test if not contains…"), lambda: self._test_if(self.if_not_contains)
        )
        self.test_if.setMenu(test_menu)
        ig = QGridLayout(cond)
        ig.addWidget(QLabel(self.tr("Contains"), cond), 0, 0, 1, 3)
        ig.addWidget(self.if_contains, 1, 0, 1, 3)
        ig.addWidget(QLabel(self.tr("Not contains"), cond), 2, 0, 1, 3)
        ig.addWidget(self.if_not_contains, 3, 0, 1, 3)
        ig.addWidget(self.if_regex, 4, 0)
        ig.addWidget(self.if_multiline, 4, 1)
        ig.addWidget(self.if_case, 5, 0)
        ig.addWidget(self.if_singleline, 5, 1)
        ig.addWidget(self.test_if, 5, 2)
        tabs.addTab(cond, self.tr("If"))

        form = QFormLayout()
        form.addRow(self.tr("Type"), self.type)
        top = QVBoxLayout(self)
        top.addWidget(self.header)
        top.addLayout(form)
        top.addWidget(tabs, 1)
        self.is_regex.toggled.connect(self._update)
        self.if_regex.toggled.connect(self._update)
        self._update()

    def _update(self) -> None:
        """RuleControl.UpdateRegexOptionCheckboxes."""
        on = self.is_regex.isChecked()
        for w in (self.multiline, self.singleline, self.test_find):
            w.setEnabled(on)
        on = self.if_regex.isChecked()
        for w in (self.if_multiline, self.if_singleline, self.test_if):
            w.setEnabled(on)

    def load(self, rule: Rule) -> None:
        self.header.name.setText(rule.name)
        self.header.enabled.setChecked(rule.enabled)
        self.type.setCurrentIndex(self.type.findData(rule.rule_type))
        self.find_text.setPlainText(rule.replace)
        self.replace_with.setPlainText(rule.with_)
        self.is_regex.setChecked(rule.regex)
        _show_options(rule.regex_options, self.case, self.multiline, self.singleline)
        self.times.setValue(rule.num_of_times)
        self.if_contains.setPlainText(rule.if_contains)
        self.if_not_contains.setPlainText(rule.if_not_contains)
        self.if_regex.setChecked(rule.if_is_regex)
        _show_options(rule.if_regex_options, self.if_case, self.if_multiline, self.if_singleline)
        self._update()

    def save(self, rule: Rule) -> None:
        rule.name = self.header.name.text().strip() or rule.name
        rule.enabled = self.header.enabled.isChecked()
        rule.rule_type = RuleType(self.type.currentData())
        rule.replace = self.find_text.toPlainText()
        rule.with_ = self.replace_with.toPlainText()
        rule.regex = self.is_regex.isChecked()
        rule.regex_options = _options(self.case, self.multiline, self.singleline)
        rule.num_of_times = self.times.value()
        rule.if_contains = self.if_contains.toPlainText()
        rule.if_not_contains = self.if_not_contains.toPlainText()
        rule.if_is_regex = self.if_regex.isChecked()
        rule.if_regex_options = _options(self.if_case, self.if_multiline, self.if_singleline)

    def _test_find(self) -> None:
        t = RegexTesterDialog(
            self.find_text.toPlainText(),
            self.replace_with.toPlainText(),
            ignore_case=not self.case.isChecked(),
            multiline=self.multiline.isChecked(),
            singleline=self.singleline.isChecked(),
            returns=True,
            parent=self,
        )
        if t.exec() == QDialog.DialogCode.Accepted:
            self.find_text.setPlainText(t.find_box.toPlainText())
            self.replace_with.setPlainText(t.replace_box.text())
            self.case.setChecked(not t.ignore_case.isChecked())
            self.multiline.setChecked(t.multiline.isChecked())
            self.singleline.setChecked(t.singleline.isChecked())

    def _test_if(self, box: QPlainTextEdit) -> None:
        t = RegexTesterDialog(
            box.toPlainText(),
            None,
            ignore_case=not self.if_case.isChecked(),
            multiline=self.if_multiline.isChecked(),
            singleline=self.if_singleline.isChecked(),
            returns=True,
            parent=self,
        )
        if t.exec() == QDialog.DialogCode.Accepted:
            box.setPlainText(t.find_box.toPlainText())
            self.if_case.setChecked(not t.ignore_case.isChecked())
            self.if_multiline.setChecked(t.multiline.isChecked())
            self.if_singleline.setChecked(t.singleline.isChecked())


class InTemplateEditor(QGroupBox):
    """InTemplateRuleControl: the templates whose calls the subrules work inside, and an
    optional new name for them."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(self.tr("In template call"), parent)
        self.header = _Header(self)
        self.templates = QListWidget(self)
        self.new_template = QLineEdit(self)
        self.new_template.setPlaceholderText(self.tr("Template name"))
        add = QPushButton(self.tr("Add"), self)
        add.clicked.connect(self._add)
        self.new_template.returnPressed.connect(self._add)
        remove = QPushButton(self.tr("Remove"), self)
        remove.clicked.connect(self._remove)
        self.do_replace = QCheckBox(self.tr("Replace with:"), self)
        self.replace_with = QLineEdit(self)
        self.do_replace.toggled.connect(self.replace_with.setEnabled)
        row = QHBoxLayout()
        row.addWidget(self.new_template, 1)
        row.addWidget(add)
        row.addWidget(remove)
        rep = QHBoxLayout()
        rep.addWidget(self.do_replace)
        rep.addWidget(self.replace_with, 1)
        top = QVBoxLayout(self)
        top.addWidget(self.header)
        top.addWidget(QLabel(self.tr("Templates:"), self))
        top.addWidget(self.templates, 1)
        top.addLayout(row)
        top.addLayout(rep)

    def _add(self) -> None:
        name = self.new_template.text().strip()
        if name:
            self.templates.addItem(name)
            self.new_template.clear()

    def _remove(self) -> None:
        for item in self.templates.selectedItems():
            self.templates.takeItem(self.templates.row(item))

    def load(self, rule: InTemplateRule) -> None:
        self.header.name.setText(rule.name)
        self.header.enabled.setChecked(rule.enabled)
        self.templates.clear()
        self.templates.addItems(rule.template_names)
        self.do_replace.setChecked(rule.do_replace)
        self.replace_with.setText(rule.replace_with)
        self.replace_with.setEnabled(rule.do_replace)

    def save(self, rule: InTemplateRule) -> None:
        rule.name = self.header.name.text().strip() or rule.name
        rule.enabled = self.header.enabled.isChecked()
        rule.template_names = [self.templates.item(i).text() for i in range(self.templates.count())]
        rule.do_replace = self.do_replace.isChecked()
        rule.replace_with = self.replace_with.text().strip()


class TemplateParamEditor(QGroupBox):
    """TemplateParamRuleControl: rename a template parameter."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(self.tr("Template parameter"), parent)
        self.header = _Header(self)
        self.param = QLineEdit(self)
        self.new_name = QLineEdit(self)
        form = QFormLayout()
        form.addRow(self.tr("Name of parameter:"), self.param)
        form.addRow(self.tr("Change name to:"), self.new_name)
        top = QVBoxLayout(self)
        top.addWidget(self.header)
        top.addLayout(form)
        top.addStretch(1)

    def load(self, rule: TemplateParamRule) -> None:
        self.header.name.setText(rule.name)
        self.header.enabled.setChecked(rule.enabled)
        self.param.setText(rule.param_name)
        self.new_name.setText(rule.new_param_name)

    def save(self, rule: TemplateParamRule) -> None:
        rule.name = self.header.name.text().strip() or rule.name
        rule.enabled = self.header.enabled.isChecked()
        rule.param_name = self.param.text().strip()
        rule.new_param_name = self.new_name.text().strip()


class ReplaceSpecialDialog(QDialog):
    """Replace Special: the rule tree on the left, the selected rule on the right."""

    def __init__(self, rules: list[IRule], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Replace Special"))
        self.history = RuleHistory()
        self.clipboard: IRule | None = None
        self.current: QTreeWidgetItem | None = None
        self._loading = False  # an editor is being filled: its signals must not save

        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.tree.currentItemChanged.connect(self._selected)

        self.rule_editor = RuleEditor(self)
        self.template_editor = InTemplateEditor(self)
        self.param_editor = TemplateParamEditor(self)
        self.none_label = QLabel(self.tr("No rule selected"), self)
        self.none_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack = QStackedWidget(self)
        for w in (self.none_label, self.rule_editor, self.template_editor, self.param_editor):
            self.stack.addWidget(w)
        for editor in (self.rule_editor, self.template_editor, self.param_editor):
            editor.header.name.textEdited.connect(self._rename)
            editor.header.enabled.toggled.connect(lambda _on: self._save_current())

        self.up = QToolButton(self)
        self.up.setIcon(codex_icon("arrowUp"))
        self.up.setToolTip(self.tr("Move up"))
        self.up.clicked.connect(lambda: self.move_rule(-1))
        self.down = QToolButton(self)
        self.down.setIcon(codex_icon("arrowDown"))
        self.down.setToolTip(self.tr("Move down"))
        self.down.clicked.connect(lambda: self.move_rule(1))
        arrows = QVBoxLayout()
        arrows.addWidget(self.up)
        arrows.addWidget(self.down)
        arrows.addStretch(1)

        new_rule = QPushButton(self.tr("New Rule"), self)
        new_rule.clicked.connect(lambda: self.new_rule(Rule()))
        new_sub = QPushButton(self.tr("New Subrule"), self)
        new_sub.clicked.connect(lambda: self.new_rule(Rule(), sub=True))
        self.delete_button = QPushButton(self.tr("Delete"), self)
        self.delete_button.clicked.connect(self.delete)
        tree_box = QWidget(self)
        tl = QVBoxLayout(tree_box)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(self.tree, 1)
        tb = QHBoxLayout()
        for b in (new_rule, new_sub, self.delete_button):
            tb.addWidget(b)
        tl.addLayout(tb)
        left = QWidget(self)
        ll = QHBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(tree_box, 1)
        ll.addLayout(arrows)
        split = QSplitter(self)
        split.addWidget(left)
        split.addWidget(self.stack)
        split.setStretchFactor(1, 2)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        primary_button(buttons.button(QDialogButtonBox.StandardButton.Ok))
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)

        top = QVBoxLayout(self)
        top.setMenuBar(self._menus())
        top.addWidget(split, 1)
        top.addWidget(buttons)
        self.resize(900, 560)
        self.set_rules(copy.deepcopy(rules))

    # -- menus --------------------------------------------------------------------------------

    def _menus(self) -> QMenuBar:
        bar = QMenuBar(self)

        def act(menu: QMenu, text: str, slot: Callable[[], object], key: str = "") -> QAction:
            a = menu.addAction(text)
            a.triggered.connect(lambda _=False: slot())
            if key:
                a.setShortcut(QKeySequence(key))
            return a

        new = bar.addMenu(self.tr("New"))
        for title, sub in ((self.tr("Rule"), False), (self.tr("Subrule"), True)):
            m = new.addMenu(title)
            act(m, self.tr("Find and replace"), lambda s=sub: self.new_rule(Rule(), s),
                "" if sub else "Ctrl+N")  # fmt: skip
            act(m, self.tr("In template call"), lambda s=sub: self.new_rule(InTemplateRule(), s))
            act(
                m,
                self.tr("Template parameter"),
                lambda s=sub: self.new_rule(TemplateParamRule(), s),
            )
        edit = bar.addMenu(self.tr("Rule"))
        self.undo_action = act(edit, self.tr("Undo"), self.undo, "Ctrl+Z")
        self.redo_action = act(edit, self.tr("Redo"), self.redo, "Ctrl+Y")
        edit.addSeparator()
        act(edit, self.tr("Cut"), self.cut)
        act(edit, self.tr("Copy"), self.copy)
        act(edit, self.tr("Paste"), self.paste)
        edit.addSeparator()
        act(edit, self.tr("Delete"), self.delete)
        edit.addSeparator()
        act(edit, self.tr("Refresh colours"), self._colour_all)
        edit.aboutToShow.connect(self._update_actions)
        return bar

    def _tree_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        menu.addAction(self.tr("New Rule"), lambda: self.new_rule(Rule()))
        menu.addAction(self.tr("New Subrule"), lambda: self.new_rule(Rule(), sub=True))
        menu.addSeparator()
        menu.addAction(self.tr("Cut"), self.cut)
        menu.addAction(self.tr("Copy"), self.copy)
        paste = menu.addAction(self.tr("Paste"), self.paste)
        paste.setEnabled(self.clipboard is not None)
        menu.addAction(self.tr("Delete"), self.delete)
        menu.addSeparator()
        menu.addAction(self.tr("Expand all"), self.tree.expandAll)
        menu.addAction(self.tr("Collapse all"), self.tree.collapseAll)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _update_actions(self) -> None:
        self.undo_action.setEnabled(self.history.can_undo)
        self.redo_action.setEnabled(self.history.can_redo)

    # -- the tree -----------------------------------------------------------------------------

    @staticmethod
    def _rule(item: QTreeWidgetItem) -> IRule:
        rule = item.data(0, RULE_ROLE)
        assert isinstance(rule, IRule)
        return rule

    def _make_item(self, rule: IRule) -> QTreeWidgetItem:
        item = QTreeWidgetItem([rule.name])
        item.setData(0, RULE_ROLE, rule)
        for child in rule.children:
            item.addChild(self._make_item(child))
        self._colour(item)
        return item

    def set_rules(self, rules: list[IRule]) -> None:
        self.current = None
        self.tree.clear()
        for r in rules:
            self.tree.addTopLevelItem(self._make_item(r))
        self.tree.expandAll()
        self._selected(None, None)

    def rules(self) -> list[IRule]:
        """GetRules: the top-level rules, each with its children as the tree has them."""
        self._save_current()

        def collect(item: QTreeWidgetItem) -> IRule:
            rule = self._rule(item)
            rule.children = [collect(c) for c in _children(item)]
            return rule

        return [collect(item) for item in self._top_items()]

    def _colour(self, item: QTreeWidgetItem) -> None:
        """Disabled rules in red (SetNodeColour)."""
        t = theme.tokens(theme.Mode.SYSTEM)
        if self._rule(item).enabled:
            item.setBackground(0, QBrush())
            item.setForeground(0, QBrush())
        else:
            item.setBackground(0, QColor(t["background_color_error_subtle"]))
            item.setForeground(0, QColor(t["color_error"]))

    def _colour_all(self) -> None:
        def walk(item: QTreeWidgetItem) -> None:
            self._colour(item)
            for child in _children(item):
                walk(child)

        for item in self._top_items():
            walk(item)

    def _top_items(self) -> list[QTreeWidgetItem]:
        items = (self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount()))
        return [i for i in items if i is not None]

    def _editor_for(self, rule: IRule) -> RuleEditor | InTemplateEditor | TemplateParamEditor:
        if isinstance(rule, Rule):
            return self.rule_editor
        if isinstance(rule, InTemplateRule):
            return self.template_editor
        return self.param_editor

    def _save_current(self) -> None:
        if self.current is None or self._loading:
            return
        rule = self._rule(self.current)
        editor = self._editor_for(rule)
        editor.save(rule)  # type: ignore[arg-type]
        self.current.setText(0, rule.name)
        self._colour(self.current)

    def _selected(self, item: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        self._save_current()
        self.current = item
        if item is None:
            self.stack.setCurrentWidget(self.none_label)
        else:
            rule = self._rule(item)
            editor = self._editor_for(rule)
            self._loading = True
            try:
                editor.load(rule)  # type: ignore[arg-type]
            finally:
                self._loading = False
            self.stack.setCurrentWidget(editor)
        for w in (self.delete_button, self.up, self.down):
            w.setEnabled(item is not None)

    def _rename(self, name: str) -> None:
        if self.current is not None and name.strip():
            self.current.setText(0, name.strip())

    def _siblings(self, item: QTreeWidgetItem) -> tuple[QTreeWidgetItem | None, int]:
        parent = item.parent()
        index = parent.indexOfChild(item) if parent else self.tree.indexOfTopLevelItem(item)
        return parent, index

    def _insert(self, parent: QTreeWidgetItem | None, index: int, item: QTreeWidgetItem) -> None:
        if parent is None:
            self.tree.insertTopLevelItem(index, item)
        else:
            parent.insertChild(index, item)

    def _take(self, item: QTreeWidgetItem) -> None:
        parent, index = self._siblings(item)
        if parent is None:
            self.tree.takeTopLevelItem(index)
        else:
            parent.takeChild(index)

    def _remember(self) -> None:
        self.history.save(self.rules())

    def new_rule(self, rule: IRule, sub: bool = False) -> None:
        """AddNewRule: after the selected rule, or (sub) as its last child."""
        self._remember()
        item = self._make_item(rule)
        selected = self.tree.currentItem()
        if sub and selected is not None:
            selected.addChild(item)
            selected.setExpanded(True)
        elif selected is not None:
            parent, index = self._siblings(selected)
            self._insert(parent, index + 1, item)
        else:
            self.tree.addTopLevelItem(item)
        self.tree.setCurrentItem(item)
        editor = self._editor_for(rule)
        editor.header.name.setFocus()
        editor.header.name.selectAll()

    def delete(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        self._remember()
        self.current = None
        self._take(item)
        self._selected(self.tree.currentItem(), None)

    def move_rule(self, step: int) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        parent, index = self._siblings(item)
        count = parent.childCount() if parent else self.tree.topLevelItemCount()
        target = index + step
        if not 0 <= target < count:
            return
        self._remember()
        self._save_current()
        expanded = item.isExpanded()
        self.current = None
        self._take(item)
        self._insert(parent, target, item)
        item.setExpanded(expanded)
        self.tree.setCurrentItem(item)

    def copy(self) -> None:
        item = self.tree.currentItem()
        if item is not None:
            self.rules()  # brings each rule's children up to date with the tree
            self.clipboard = copy.deepcopy(self._rule(item))

    def cut(self) -> None:
        self.copy()
        self.delete()

    def paste(self) -> None:
        if self.clipboard is not None:
            self.new_rule(copy.deepcopy(self.clipboard))

    def undo(self) -> None:
        self.set_rules(self.history.undo(self.rules()))

    def redo(self) -> None:
        self.set_rules(self.history.redo(self.rules()))

    def _ok(self) -> None:
        self._save_current()
        self.accept()
