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
"""Settings: theme, interface language, fonts per script, user profiles and general preferences,
saved in config.toml. The fonts page is also the start screen's font step."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyawb.settings import languages
from pyawb.settings.appconfig import AppConfig
from pyawb.settings.preferences import SAMPLES, FontChoice, Preferences
from pyawb.ui.editor_dialogs import primary_button

DEFAULT_FONT = ""  # combo data for "the system's default"


def families_for_script(script: str) -> list[str]:
    """Installed font families that can show the script: Qt's writing-system list where Qt knows
    the script, else the families with a glyph for every letter of the script's sample."""
    system = getattr(QFontDatabase.WritingSystem, script, None)
    if isinstance(system, QFontDatabase.WritingSystem):
        return sorted(QFontDatabase.families(system), key=str.casefold)
    sample = [ord(c) for c in SAMPLES.get(script, "") if not c.isspace() and not c.isascii()]
    out = []
    for family in QFontDatabase.families():
        metrics = QFontMetrics(QFont(family))
        if all(metrics.inFontUcs4(c) for c in sample):
            out.append(family)
    return sorted(out, key=str.casefold)


class FontsPage(QWidget):
    """The fonts for one script at a time, with a live sample in that script."""

    def __init__(self, prefs: Preferences, script: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.prefs = prefs
        self.script = QComboBox(self)
        for name in sorted(SAMPLES):
            self.script.addItem(name, name)
        self.show_all = QCheckBox(self.tr("Show all fonts (also those without this script)"), self)
        self.editor_font = QComboBox(self)
        self.editor_size = QSpinBox(self)
        self.editor_size.setRange(0, 72)
        self.editor_size.setSpecialValueText(self.tr("Default size"))
        self.interface_font = QComboBox(self)
        self.diff_font = QComboBox(self)
        self.warning = QLabel(self)
        self.warning.setObjectName("error")
        self.warning.setWordWrap(True)
        self.sample = QLabel(self)
        self.sample.setObjectName("fontSample")
        self.sample.setWordWrap(True)
        self.sample.setMinimumHeight(64)
        self.sample.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        form = QFormLayout()
        form.addRow(self.tr("Script"), self.script)
        form.addRow("", self.show_all)
        editor_row = QHBoxLayout()
        editor_row.addWidget(self.editor_font, 1)
        editor_row.addWidget(self.editor_size)
        form.addRow(self.tr("Editor font"), editor_row)
        form.addRow(self.tr("Interface font"), self.interface_font)
        form.addRow(self.tr("Diff font"), self.diff_font)
        sample_box = QGroupBox(self.tr("Sample"), self)
        sl = QVBoxLayout(sample_box)
        sl.addWidget(self.sample)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                self.tr(
                    "Choose fonts that have the wiki's script: they shape every word in the "
                    "editor, the diff and the lists."
                ),
                self,
            )
        )
        layout.addLayout(form)
        layout.addWidget(self.warning)
        layout.addWidget(sample_box)
        layout.addStretch(1)

        self._current = script
        self.script.setCurrentIndex(max(self.script.findData(script), 0))
        self.script.currentIndexChanged.connect(self._script_changed)
        self.show_all.toggled.connect(lambda _: self._fill())
        for w in (self.editor_font, self.interface_font, self.diff_font):
            w.currentIndexChanged.connect(self._update_sample)
        self.editor_size.valueChanged.connect(self._update_sample)
        self._fill()

    def _script_changed(self) -> None:
        self._store()  # keep what was chosen for the previous script
        self._current = str(self.script.currentData())
        self._fill()

    def _fill(self) -> None:
        script = self._current
        families = (
            sorted(QFontDatabase.families(), key=str.casefold)
            if self.show_all.isChecked()
            else families_for_script(script)
        )
        chosen = self.prefs.font_for(script)
        for combo, value in (
            (self.editor_font, chosen.editor),
            (self.interface_font, chosen.interface),
            (self.diff_font, chosen.diff),
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(self.tr("System default"), DEFAULT_FONT)
            for family in families:
                combo.addItem(family, family)
                combo.setItemData(combo.count() - 1, QFont(family), Qt.ItemDataRole.FontRole)
            if value and combo.findData(value) < 0:
                combo.addItem(value, value)  # chosen before; keep it even if not listed now
            combo.setCurrentIndex(max(combo.findData(value), 0))
            combo.blockSignals(False)
        self.editor_size.setValue(chosen.editor_size)
        self.warning.setText(
            ""
            if families
            else self.tr(
                "No installed font has the %1 script. Install one (for example a Noto font for "
                "it), or the text will show as boxes."
            ).replace("%1", script)
        )
        self.warning.setVisible(not families)
        self._update_sample()

    def _update_sample(self) -> None:
        text = SAMPLES.get(self._current, "")
        family = str(self.editor_font.currentData() or "")
        font = QFont(family) if family else QFont()
        if self.editor_size.value():
            font.setPointSize(self.editor_size.value())
        font.setPointSizeF(max(font.pointSizeF(), 12))
        self.sample.setFont(font)
        self.sample.setText(text)

    def _store(self) -> None:
        self.prefs = self.prefs.with_font(
            self._current,
            FontChoice(
                editor=str(self.editor_font.currentData() or ""),
                editor_size=self.editor_size.value(),
                interface=str(self.interface_font.currentData() or ""),
                diff=str(self.diff_font.currentData() or ""),
            ),
        )

    def preferences(self) -> Preferences:
        self._store()
        return self.prefs


class SettingsDialog(QDialog):
    """Settings → Theme / Language / Fonts / User profiles / Preferences (one dialog, one tab
    each). The result is the updated configuration (updated_config)."""

    PAGES = ("theme", "language", "fonts", "profiles", "general")

    def __init__(
        self,
        config: AppConfig,
        wiki_script: str = "Latin",
        page: str = "general",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Settings"))
        self.resize(720, 560)
        self.config = config
        prefs = config.preferences
        self.tabs = QTabWidget(self)

        # theme
        theme = QWidget(self)
        self.theme_group = QButtonGroup(self)
        tl = QVBoxLayout(theme)
        for value, label in (
            ("system", self.tr("Follow the system (light or dark)")),
            ("light", self.tr("Light")),
            ("dark", self.tr("Dark")),
        ):
            radio = QRadioButton(label, theme)
            radio.setProperty("value", value)
            radio.setChecked(prefs.theme == value)
            self.theme_group.addButton(radio)
            tl.addWidget(radio)
        tl.addWidget(
            QLabel(
                self.tr(
                    "Wikitext highlighting follows the theme: CodeMirror's MediaWiki colours, "
                    "Nord in dark mode."
                ),
                theme,
            )
        )
        tl.addStretch(1)
        self.tabs.addTab(theme, self.tr("Theme"))

        # language
        language = QWidget(self)
        self.language_filter = QLineEdit(language)
        self.language_filter.setPlaceholderText(self.tr("Search languages"))
        self.language_filter.textChanged.connect(self._filter_languages)
        self.languages = QListWidget(language)
        system = QListWidgetItem(self.tr("The system's language"))
        system.setData(Qt.ItemDataRole.UserRole, "")
        self.languages.addItem(system)
        data = languages.load()
        for lang in sorted(data.languages.values(), key=lambda x: (x.name.casefold(), x.code)):
            item = QListWidgetItem(lang.label)
            item.setData(Qt.ItemDataRole.UserRole, lang.code)
            self.languages.addItem(item)
            if lang.code == prefs.language:
                self.languages.setCurrentItem(item)
        if not prefs.language:
            self.languages.setCurrentRow(0)
        ll = QVBoxLayout(language)
        ll.addWidget(
            QLabel(
                self.tr(
                    "The interface language (from Meta-Wiki's list). Right-to-left languages "
                    "mirror the window."
                ),
                language,
            )
        )
        ll.addWidget(self.language_filter)
        ll.addWidget(self.languages, 1)
        self.tabs.addTab(language, self.tr("Language"))

        # fonts
        self.fonts = FontsPage(prefs, wiki_script, self)
        self.tabs.addTab(self.fonts, self.tr("Fonts"))

        # user profiles
        profiles = QWidget(self)
        self.profile_table = QTableWidget(0, 4, profiles)
        self.profile_table.setHorizontalHeaderLabels(
            [self.tr("Profile"), self.tr("Wiki"), self.tr("User name"), self.tr("Default")]
        )
        self.profile_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.profile_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.profile_table.verticalHeader().hide()
        header = self.profile_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        add = QPushButton(self.tr("Add…"), profiles)
        add.clicked.connect(lambda: self._edit_profile(""))
        edit = QPushButton(self.tr("Edit…"), profiles)
        edit.clicked.connect(lambda: self._edit_profile(self._selected_profile()))
        delete = QPushButton(self.tr("Delete"), profiles)
        delete.clicked.connect(self._delete_profile)
        default = QPushButton(self.tr("Make default"), profiles)
        default.clicked.connect(self._make_default)
        self.profile_table.doubleClicked.connect(
            lambda _: self._edit_profile(self._selected_profile())
        )
        buttons = QHBoxLayout()
        for b in (add, edit, delete, default):
            buttons.addWidget(b)
        buttons.addStretch(1)
        pl = QVBoxLayout(profiles)
        pl.addWidget(
            QLabel(
                self.tr(
                    "A profile is a wiki and an account. Passwords are kept in the system "
                    "keychain, never in the settings file."
                ),
                profiles,
            )
        )
        pl.addWidget(self.profile_table, 1)
        pl.addLayout(buttons)
        self.tabs.addTab(profiles, self.tr("User profiles"))
        self._fill_profiles()

        # general
        general = QWidget(self)
        self.on_load = QComboBox(general)
        self.on_load.addItem(self.tr("Show the diff"), "diff")
        self.on_load.addItem(self.tr("Show the edit box"), "edit")
        self.on_load.setCurrentIndex(max(self.on_load.findData(prefs.on_load), 0))
        self.warn_on_exit = QCheckBox(self.tr("Ask before closing"), general)
        self.warn_on_exit.setChecked(prefs.warn_on_exit)
        self.word_wrap = QCheckBox(self.tr("Wrap long lines in the editor"), general)
        self.word_wrap.setChecked(prefs.word_wrap)
        gl = QFormLayout(general)
        gl.addRow(self.tr("When a page is loaded"), self.on_load)
        gl.addRow("", self.warn_on_exit)
        gl.addRow("", self.word_wrap)
        self.tabs.addTab(general, self.tr("Preferences"))

        ok_cancel = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        primary_button(ok_cancel.button(QDialogButtonBox.StandardButton.Ok))
        ok_cancel.accepted.connect(self.accept)
        ok_cancel.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(ok_cancel)
        self.show_page(page)

    def show_page(self, page: str) -> None:
        if page in self.PAGES:
            self.tabs.setCurrentIndex(self.PAGES.index(page))

    # -- language -----------------------------------------------------------------------------

    def _filter_languages(self, text: str) -> None:
        needle = text.casefold().strip()
        for i in range(self.languages.count()):
            item = self.languages.item(i)
            item.setHidden(bool(needle) and needle not in item.text().casefold())

    # -- profiles -----------------------------------------------------------------------------

    def _fill_profiles(self) -> None:
        keep = self._selected_profile() if self.profile_table.rowCount() else None
        self.profile_table.setRowCount(0)
        for p in self.config.profiles:
            row = self.profile_table.rowCount()
            self.profile_table.insertRow(row)
            wiki = p.custom_url or f"{p.lang}.{p.project}"
            is_default = p.name == self.config.default_profile
            for col, value in enumerate(
                (p.name, wiki, p.username, self.tr("Yes") if is_default else "")
            ):
                self.profile_table.setItem(row, col, QTableWidgetItem(value))
            if p.name == keep:
                self.profile_table.selectRow(row)

    def _selected_profile(self) -> str | None:
        row = self.profile_table.currentRow()
        item = self.profile_table.item(row, 0) if row >= 0 else None
        return item.text() if item is not None else None

    def _edit_profile(self, name: str | None) -> None:
        if name is None:
            return
        from pyawb.ui.login_dialog import LoginDialog

        dialog = LoginDialog(self.config, parent=self, edit_only=True, profile_name=name)
        if dialog.exec():
            self.config = dialog.updated_config()
            self._fill_profiles()

    def _delete_profile(self) -> None:
        name = self._selected_profile()
        if name is not None:
            self.config = self.config.without_profile(name)
            self._fill_profiles()

    def _make_default(self) -> None:
        name = self._selected_profile()
        if name is not None:
            self.config = replace(self.config, default_profile=name)
            self._fill_profiles()

    # -- result -------------------------------------------------------------------------------

    def preferences(self) -> Preferences:
        prefs = self.fonts.preferences()
        checked = self.theme_group.checkedButton()
        item = self.languages.currentItem()
        return replace(
            prefs,
            theme=str(checked.property("value")) if checked is not None else prefs.theme,
            language=str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else "",
            on_load=str(self.on_load.currentData()),
            warn_on_exit=self.warn_on_exit.isChecked(),
            word_wrap=self.word_wrap.isChecked(),
        )

    def updated_config(self) -> AppConfig:
        return replace(self.config, preferences=self.preferences())
