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
# After AutoWikiBrowser WikiFunctions/Controls/ArticleActionDialog.cs (GPL-2.0-or-later).
"""Move, Delete or Protect a page: the details AWB's ArticleActionDialog asks for."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from pyawb.api.pageactions import EXPIRY_INFINITE, MoveRequest, PageAction, ProtectRequest
from pyawb.ui.editor_dialogs import primary_button


class PageActionDialog(QDialog):
    def __init__(
        self,
        action: PageAction,
        title: str,
        reasons: Sequence[str],
        *,
        last_reason: str = "",
        levels: Sequence[str] = (),
        edit_level: str = "",
        move_level: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.setWindowTitle(self.tr(action.value) + " — " + title)
        form = QFormLayout()
        self.new_title = QLineEdit(title, self)
        self.reason = QComboBox(self)
        self.reason.setEditable(True)
        self.reason.addItems(list(reasons))
        self.reason.setEditText(last_reason)
        self.no_redirect = QCheckBox(self.tr("No redirect"), self)
        self.watch = QCheckBox(self.tr("Watch"), self)
        self.move_talk = QCheckBox(self.tr("Move associated talk page"), self)
        self.move_talk.setChecked(True)
        self.edit_level = QComboBox(self)
        self.move_level = QComboBox(self)
        for box, current in ((self.edit_level, edit_level), (self.move_level, move_level)):
            for level in levels or ("",):
                box.addItem(level or self.tr("Allow all users"), level)
            box.setCurrentIndex(max(box.findData(current), 0))
        self.expiry = QLineEdit(EXPIRY_INFINITE, self)
        self.expiry.setToolTip(self.tr("For example: infinite, 1 week, 2027-01-01"))
        self.cascade = QCheckBox(self.tr("Cascading protection"), self)
        self.cascade.setToolTip(self.tr("Automatically protect any pages transcluded in this page"))
        self.edit_level.currentIndexChanged.connect(self._update_cascade)
        self.error = QLabel(self)
        self.error.setObjectName("error")
        self.error.hide()

        if action is PageAction.MOVE:
            form.addRow(self.tr("New title:"), self.new_title)
        form.addRow(self.tr("Summary"), self.reason)
        if action is PageAction.PROTECT:
            form.addRow(self.tr("Edit:"), self.edit_level)
            form.addRow(self.tr("Move:"), self.move_level)
            form.addRow(self.tr("Expiry:"), self.expiry)
            form.addRow("", self.cascade)
        if action is PageAction.MOVE:
            form.addRow("", self.move_talk)
            form.addRow("", self.no_redirect)
        form.addRow("", self.watch)
        # the other modes' fields are not in this form: keep them out of sight
        used = {
            PageAction.MOVE: (self.new_title, self.move_talk, self.no_redirect),
            PageAction.PROTECT: (self.edit_level, self.move_level, self.expiry, self.cascade),
            PageAction.DELETE: (),
        }[action]
        for w in (self.new_title, self.move_talk, self.no_redirect, self.edit_level,
                  self.move_level, self.expiry, self.cascade):  # fmt: skip
            if w not in used:
                w.hide()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        ok = buttons.addButton(self.tr(action.value), QDialogButtonBox.ButtonRole.AcceptRole)
        primary_button(ok)
        buttons.accepted.connect(self._ok)
        buttons.rejected.connect(self.reject)
        top = QVBoxLayout(self)
        top.addLayout(form)
        top.addWidget(self.error)
        top.addWidget(buttons)
        self._update_cascade()
        self.resize(560, self.sizeHint().height())

    def _update_cascade(self) -> None:
        """Cascading protection needs the highest level (AWB's CascadingEnabled)."""
        levels = [self.edit_level.itemData(i) for i in range(self.edit_level.count())]
        top_level = levels[-1] if levels else ""
        on = bool(top_level) and self.edit_level.currentData() == top_level
        self.cascade.setEnabled(on)
        if not on:
            self.cascade.setChecked(False)

    def problems(self) -> list[str]:
        """ArticleActionDialog_FormClosing's checks."""
        out: list[str] = []
        if not self.reason.currentText().strip():
            out.append(
                {
                    PageAction.MOVE: self.tr("Please enter/select a move reason."),
                    PageAction.DELETE: self.tr("Please enter/select a deletion reason."),
                    PageAction.PROTECT: self.tr("Please enter/select a protection reason."),
                }[self.action]
            )
        if self.action is PageAction.MOVE and not self.new_title.text().strip():
            out.append(self.tr("Please enter a new/target title."))
        if (
            self.action is PageAction.PROTECT
            and (self.edit_level.currentData() or self.move_level.currentData())
            and not self.expiry.text().strip()
        ):
            out.append(self.tr("Please enter an expiry time."))
        return out

    def _ok(self) -> None:
        problems = self.problems()
        if problems:
            self.error.setText("\n".join(problems))
            self.error.show()
            return
        self.accept()

    def reason_text(self) -> str:
        return self.reason.currentText().strip()

    def move_request(self) -> MoveRequest:
        return MoveRequest(
            to=self.new_title.text().strip(),
            reason=self.reason_text(),
            move_talk=self.move_talk.isChecked(),
            no_redirect=self.no_redirect.isChecked(),
            watch=self.watch.isChecked(),
        )

    def protect_request(self) -> ProtectRequest:
        return ProtectRequest(
            reason=self.reason_text(),
            edit=str(self.edit_level.currentData() or ""),
            move=str(self.move_level.currentData() or ""),
            expiry=self.expiry.text().strip(),
            cascade=self.cascade.isChecked(),
            watch=self.watch.isChecked(),
        )
