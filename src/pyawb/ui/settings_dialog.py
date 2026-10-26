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

import shutil
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pyawb import paths
from pyawb.settings import languages
from pyawb.settings.appconfig import AppConfig
from pyawb.settings.preferences import (
    ALERTS,
    AUTOSAVE_SECONDS,
    SAMPLES,
    FontChoice,
    Preferences,
    default_autosave_file,
    font_install_help,
    suggest_font,
)
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


def user_font_dir() -> Path:
    """Fonts added with "Add a font file…": loaded by PyAutoWikiBrowser at every start, so a
    script's font works without installing it in the system (or administrator rights)."""
    return paths.data_dir() / "fonts"


def load_user_fonts() -> list[str]:
    """Register the fonts in user_font_dir() with Qt; the families they add."""
    families: list[str] = []
    folder = user_font_dir()
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() in (".ttf", ".otf", ".ttc", ".otc"):
                font_id = QFontDatabase.addApplicationFont(str(path))
                if font_id >= 0:
                    families += QFontDatabase.applicationFontFamilies(font_id)
    return families


def add_font_file(source: Path) -> list[str]:
    """Copy a font file into user_font_dir() and load it; the families it has ([] if Qt cannot
    read it, in which case it is not kept)."""
    folder = user_font_dir()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / source.name
    shutil.copyfile(source, target)
    font_id = QFontDatabase.addApplicationFont(str(target))
    if font_id < 0:
        target.unlink(missing_ok=True)
        return []
    return QFontDatabase.applicationFontFamilies(font_id)


class FontsPage(QWidget):
    """The fonts for one script at a time, with a live sample in that script."""

    def __init__(
        self,
        prefs: Preferences,
        script: str,
        parent: QWidget | None = None,
        *,
        fixed_script: bool = False,
    ) -> None:
        """fixed_script: only this script's fonts (the start screen, for the chosen wiki)."""
        super().__init__(parent)
        self.prefs = prefs
        self.families: list[str] = []
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
        # why this matters, always shown
        self.notice = QLabel(
            self.tr(
                "Choosing the font is a critical step: the wiki's text is shown and edited in it. "
                "It must be a Unicode font that has the language's script, with its letters, vowel "
                "signs and conjuncts. If no such font is installed, install one first; otherwise "
                "the text shows as boxes or broken letters."
            ),
            self,
        )
        self.notice.setObjectName("infoNotice")
        self.notice.setWordWrap(True)
        # no font with the script: what to install, and how
        self.missing = QWidget(self)
        self.missing.setObjectName("warningNotice")
        self.missing.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.warning = QLabel(self.missing)
        self.warning.setWordWrap(True)
        self.warning.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.download = QPushButton(self.tr("Download the font"), self.missing)
        self.download.clicked.connect(self._open_download)
        self.add_file = QPushButton(self.tr("Add a font file…"), self.missing)
        self.add_file.clicked.connect(self._add_font_file)
        self.recheck = QPushButton(self.tr("Check again"), self.missing)
        self.recheck.clicked.connect(self._fill)
        missing_buttons = QHBoxLayout()
        for b in (self.download, self.add_file, self.recheck):
            missing_buttons.addWidget(b)
        missing_buttons.addStretch(1)
        ml = QVBoxLayout(self.missing)
        ml.addWidget(self.warning)
        ml.addLayout(missing_buttons)
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
        layout.addWidget(self.notice)
        layout.addWidget(self.missing)
        layout.addLayout(form)
        layout.addWidget(sample_box)
        layout.addStretch(1)

        self._current = script
        self.script.setCurrentIndex(max(self.script.findData(script), 0))
        self.script.setEnabled(not fixed_script)
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
        self.families = families_for_script(script)
        families = (
            sorted(QFontDatabase.families(), key=str.casefold)
            if self.show_all.isChecked()
            else self.families
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
        if self.has_fonts():
            self.missing.hide()
        else:
            help_ = font_install_help(script)
            self.warning.setText(
                self.tr(
                    "No installed font has the %1 script, so its text cannot be shown. Install a "
                    "Unicode font for it first, for example %2:\n"
                    "• Download it (button below), then add the file here or install it in the "
                    "system.\n"
                    "• Linux: %3\n"
                    "• Windows: %4\n"
                    "• macOS: %5\n"
                    "Then press Check again (a font installed in the system may need "
                    "PyAutoWikiBrowser to be restarted)."
                )
                .replace("%1", script)
                .replace("%2", help_.family)
                .replace("%3", help_.linux)
                .replace("%4", help_.windows)
                .replace("%5", help_.macos)
            )
            self.missing.show()
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

    def _open_download(self) -> None:
        QDesktopServices.openUrl(QUrl(font_install_help(self._current).download_url))

    def _add_font_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Add a font file"),
            "",
            self.tr("Fonts (*.ttf *.otf *.ttc *.otc);;All files (*)"),
        )
        if not name:
            return
        families = add_font_file(Path(name))
        if not families:
            QMessageBox.warning(
                self, self.tr("Font"), self.tr("This file is not a font Qt can read.")
            )
            return
        self._fill()
        if self.has_fonts() and families[0] in self.families:
            self.editor_font.setCurrentIndex(max(self.editor_font.findData(families[0]), 0))

    def set_script(self, script: str) -> None:
        self.script.setCurrentIndex(max(self.script.findData(script), 0))

    def has_fonts(self) -> bool:
        """Whether an installed font has the script (Latin always has one)."""
        return self._current == "Latin" or bool(self.families)

    def ensure_font(self) -> bool:
        """Choose a suitable editor font for the script when none is chosen yet (its Noto font,
        or another that has it); False when no installed font has the script."""
        if not self.has_fonts():
            return False
        if not self.editor_font.currentData():
            suggested = suggest_font(self._current, self.families)
            if suggested:
                self.editor_font.setCurrentIndex(max(self.editor_font.findData(suggested), 0))
        return True

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


class LanguagePicker(QWidget):
    """A searchable list of languages (autonym — English name (code)); first_item: an entry with
    code "" at the top (e.g. "The system's language")."""

    def __init__(
        self,
        langs: list[languages.Language],
        current: str = "",
        first_item: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText(self.tr("Search languages"))
        self.filter.textChanged.connect(self._filter)
        self.list = QListWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.filter)
        layout.addWidget(self.list, 1)
        self.set_languages(langs, current, first_item)

    def set_languages(
        self, langs: list[languages.Language], current: str = "", first_item: str = ""
    ) -> None:
        self.list.clear()
        if first_item:
            item = QListWidgetItem(first_item)
            item.setData(Qt.ItemDataRole.UserRole, "")
            self.list.addItem(item)
        for lang in langs:
            item = QListWidgetItem(lang.label)
            item.setData(Qt.ItemDataRole.UserRole, lang.code)
            self.list.addItem(item)
            if lang.code == current:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        self._filter(self.filter.text())

    def _filter(self, text: str) -> None:
        needle = text.casefold().strip()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(needle) and needle not in item.text().casefold())

    def code(self) -> str:
        item = self.list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else ""


def all_languages() -> list[languages.Language]:
    """Meta-Wiki's languages, by English name."""
    data = languages.load()
    return sorted(data.languages.values(), key=lambda x: (x.name.casefold(), x.code))


class SettingsDialog(QDialog):
    """Settings → Theme / Language / Fonts / User profiles / Preferences (one dialog, one tab
    each). The result is the updated configuration (updated_config)."""

    PAGES = ("theme", "language", "fonts", "profiles", "general", "alerts")

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
        self.language_picker = LanguagePicker(
            all_languages(), prefs.language, self.tr("The system's language"), language
        )
        self.language_filter = self.language_picker.filter
        self.languages = self.language_picker.list
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
        ll.addWidget(self.language_picker, 1)
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

        # general (AWB Preferences: General, Site, Editing and saving)
        general = QWidget(self)
        self.on_load = QComboBox(general)
        self.on_load.addItem(self.tr("Show the diff"), "diff")
        self.on_load.addItem(self.tr("Show the preview"), "preview")
        self.on_load.addItem(self.tr("Show the edit box"), "edit")
        self.on_load.setCurrentIndex(max(self.on_load.findData(prefs.on_load), 0))
        self.warn_on_exit = QCheckBox(self.tr("Ask before closing"), general)
        self.warn_on_exit.setChecked(prefs.warn_on_exit)
        self.word_wrap = QCheckBox(self.tr("Wrap long lines in the editor"), general)
        self.word_wrap.setChecked(prefs.word_wrap)
        self.minimize_to_tray = QCheckBox(self.tr("Minimize to the notification area"), general)
        self.minimize_to_tray.setChecked(prefs.minimize_to_tray)
        self.low_priority = QCheckBox(
            self.tr("Low priority (works better in the background)"), general
        )
        self.low_priority.setChecked(prefs.low_priority)
        self.clear_list = QCheckBox(self.tr("Empty the page list when the wiki changes"), general)
        self.clear_list.setChecked(prefs.clear_list_on_wiki_change)
        self.autosave = QCheckBox(self.tr("Save the edit box to a file every"), general)
        self.autosave.setChecked(prefs.autosave_edit_box)
        self.autosave_seconds = QSpinBox(general)
        self.autosave_seconds.setRange(*AUTOSAVE_SECONDS)
        self.autosave_seconds.setSuffix(self.tr(" s"))
        self.autosave_seconds.setValue(prefs.autosave_seconds)
        self.autosave_file = QLineEdit(prefs.autosave_file, general)
        self.autosave_file.setPlaceholderText(str(default_autosave_file()))
        browse = QPushButton(self.tr("Browse…"), general)
        browse.clicked.connect(self._browse_autosave)
        for w in (self.autosave_seconds, self.autosave_file, browse):
            w.setEnabled(prefs.autosave_edit_box)
            self.autosave.toggled.connect(w.setEnabled)
        autosave_row = QHBoxLayout()
        autosave_row.addWidget(self.autosave)
        autosave_row.addWidget(self.autosave_seconds)
        autosave_row.addStretch(1)
        file_row = QHBoxLayout()
        file_row.addWidget(self.autosave_file, 1)
        file_row.addWidget(browse)
        self.show_timer = QCheckBox(self.tr("Show the time since the last save"), general)
        self.show_timer.setChecked(prefs.show_timer)
        self.flash = QCheckBox(self.tr("Flash"), general)
        self.flash.setChecked(prefs.flash)
        self.beep = QCheckBox(self.tr("Beep"), general)
        self.beep.setChecked(prefs.beep)
        ready_row = QHBoxLayout()
        ready_row.addWidget(self.flash)
        ready_row.addWidget(self.beep)
        ready_row.addStretch(1)
        gl = QFormLayout(general)
        gl.addRow(self.tr("When a page is loaded"), self.on_load)
        for w in (self.warn_on_exit, self.word_wrap, self.minimize_to_tray, self.low_priority):
            gl.addRow("", w)
        gl.addRow(self.tr("Site"), self.clear_list)
        gl.addRow(self.tr("Editing and saving"), autosave_row)
        gl.addRow("", file_row)
        gl.addRow("", self.show_timer)
        gl.addRow(self.tr("When ready to save"), ready_row)
        self.tabs.addTab(general, self.tr("Preferences"))

        # alerts (AWB Preferences: Alerts); none checked shows them all, as in AWB
        alerts = QWidget(self)
        self.alerts = QListWidget(alerts)
        self.alerts.setObjectName("checkList")
        for alert_id, label in ALERTS:
            item = QListWidgetItem(self.tr(label), self.alerts)
            item.setData(Qt.ItemDataRole.UserRole, alert_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            on = not prefs.alerts or alert_id in prefs.alerts
            item.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
        al = QVBoxLayout(alerts)
        al.addWidget(QLabel(self.tr("Alerts shown on the Start tab for each page:"), alerts))
        al.addWidget(self.alerts, 1)
        self.tabs.addTab(alerts, self.tr("Alerts"))

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
        return replace(
            prefs,
            theme=str(checked.property("value")) if checked is not None else prefs.theme,
            language=self.language_picker.code(),
            on_load=str(self.on_load.currentData()),
            warn_on_exit=self.warn_on_exit.isChecked(),
            word_wrap=self.word_wrap.isChecked(),
            minimize_to_tray=self.minimize_to_tray.isChecked(),
            low_priority=self.low_priority.isChecked(),
            clear_list_on_wiki_change=self.clear_list.isChecked(),
            autosave_edit_box=self.autosave.isChecked(),
            autosave_seconds=self.autosave_seconds.value(),
            autosave_file=self.autosave_file.text().strip(),
            show_timer=self.show_timer.isChecked(),
            flash=self.flash.isChecked(),
            beep=self.beep.isChecked(),
            alerts=self.chosen_alerts(),
        )

    def chosen_alerts(self) -> tuple[int, ...]:
        """The checked alerts; all of them checked is stored as () (show all)."""
        chosen: list[int] = []
        for i in range(self.alerts.count()):
            item = self.alerts.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                chosen.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return () if len(chosen) == len(ALERTS) else tuple(chosen)

    def _browse_autosave(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Edit box file"),
            self.autosave_file.text() or str(default_autosave_file()),
        )
        if name:
            self.autosave_file.setText(name)

    def updated_config(self) -> AppConfig:
        return replace(self.config, preferences=self.preferences())
