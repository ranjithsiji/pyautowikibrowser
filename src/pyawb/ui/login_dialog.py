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
"""Choose or create a profile (wiki and account) and log in (AWB's Profiles and Login forms)."""

from __future__ import annotations

from dataclasses import replace

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

from pyawb.settings.appconfig import AppConfig, Profile

PROJECTS = (
    "wikipedia",
    "wiktionary",
    "wikisource",
    "wikiquote",
    "wikibooks",
    "wikinews",
    "wikiversity",
    "wikivoyage",
    "commons",
    "meta",
    "wikidata",
    "species",
    "mediawiki",
    "incubator",
    "custom",
)
_PER_LANGUAGE = {"wikipedia", "wiktionary", "wikisource", "wikiquote", "wikibooks", "wikinews",
                 "wikiversity", "wikivoyage"}  # fmt: skip
NEW_PROFILE = "⁣new"  # item data of the "New profile" entry (never a valid profile name)


class LoginDialog(QDialog):
    """Pick a profile, edit it, and give the password (empty: the one in the keychain)."""

    def __init__(
        self,
        config: AppConfig,
        has_password: dict[str, bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Log in"))
        self.config = config
        self.has_password = has_password or {}

        self.profiles = QComboBox(self)
        for p in config.profiles:
            self.profiles.addItem(p.name, p.name)
        self.profiles.addItem(self.tr("New profile…"), NEW_PROFILE)
        self.name = QLineEdit(self)
        self.lang = QLineEdit(self)
        self.lang.setPlaceholderText("en, ml, ar, zh-yue …")
        self.project = QComboBox(self)
        self.project.addItems(PROJECTS)
        self.custom_url = QLineEdit(self)
        self.custom_url.setPlaceholderText("https://wiki.example.org/w/")
        self.username = QLineEdit(self)
        self.username.setPlaceholderText(self.tr("Name@BotName (Special:BotPasswords)"))
        self.password = QLineEdit(self)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember = QCheckBox(self.tr("Remember the password in the system keychain"), self)
        self.make_default = QCheckBox(self.tr("Use this profile at start-up"), self)
        self.error = QLabel(self)
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.hide()

        form = QFormLayout()
        form.addRow(self.tr("Profile"), self.profiles)
        form.addRow(self.tr("Profile name"), self.name)
        form.addRow(self.tr("Project"), self.project)
        form.addRow(self.tr("Language"), self.lang)
        form.addRow(self.tr("Script path"), self.custom_url)
        form.addRow(self.tr("User name"), self.username)
        form.addRow(self.tr("Password"), self.password)
        form.addRow("", self.remember)
        form.addRow("", self.make_default)
        self.form = form

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText(self.tr("Log in"))
        ok.setProperty("primary", True)
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(self.buttons)

        self.profiles.currentIndexChanged.connect(self._load_profile)
        self.project.currentTextChanged.connect(self._update_fields)
        default = config.profile()
        if default is not None:
            self.profiles.setCurrentIndex(self.profiles.findData(default.name))
        self._load_profile()

    def _load_profile(self) -> None:
        key = self.profiles.currentData()
        p = self.config.profile(key) if key != NEW_PROFILE else None
        p = p or Profile(name="")
        self.name.setText(p.name)
        self.name.setEnabled(key == NEW_PROFILE)
        self.lang.setText(p.lang)
        self.project.setCurrentText(p.project if p.project in PROJECTS else "custom")
        self.custom_url.setText(p.custom_url)
        self.username.setText(p.username)
        self.remember.setChecked(p.remember_password)
        self.make_default.setChecked(bool(p.name) and p.name == self.config.default_profile)
        self.password.clear()
        remembered = self.has_password.get(p.name, False)
        self.password.setPlaceholderText(
            self.tr("(remembered in the keychain)") if remembered else ""
        )
        self._update_fields()

    def _update_fields(self) -> None:
        project = self.project.currentText()
        self.lang.setEnabled(project in _PER_LANGUAGE)
        self.custom_url.setEnabled(project == "custom")

    def profile(self) -> Profile:
        """The profile as edited."""
        project = self.project.currentText()
        return Profile(
            name=self.name.text().strip(),
            lang=self.lang.text().strip().lower() or "en",
            project=project,
            custom_url=self.custom_url.text().strip() if project == "custom" else "",
            username=self.username.text().strip(),
            remember_password=self.remember.isChecked(),
        )

    def validation_error(self) -> str | None:
        p = self.profile()
        if not p.name:
            return self.tr("Give the profile a name.")
        if self.profiles.currentData() == NEW_PROFILE and self.config.profile(p.name):
            return self.tr("A profile with this name already exists.")
        if p.project == "custom" and not p.custom_url:
            return self.tr("Give the custom wiki's script path.")
        if not p.username:
            return self.tr("Give a user name.")
        if not self.password.text() and not self.has_password.get(p.name, False):
            return self.tr("Give the password.")
        return None

    def updated_config(self) -> AppConfig:
        """The configuration with this profile added or updated (notes kept)."""
        p = self.profile()
        old = self.config.profile(p.name)
        if old is not None:
            p = replace(p, notes=old.notes)
        make_default = self.make_default.isChecked() or not self.config.profiles
        config = self.config.with_profile(p, make_default=make_default)
        if not make_default and self.config.default_profile == p.name:
            config = replace(config, default_profile="")
        return config

    def _accept(self) -> None:
        error = self.validation_error()
        if error:
            self.error.setText(error)
            self.error.show()
            return
        self.accept()
