"""Settings: theme, language, fonts per script, profiles, preferences."""

from pytestqt.qtbot import QtBot

from pyawb.settings.appconfig import AppConfig, Profile
from pyawb.settings.preferences import FontChoice, Preferences
from pyawb.ui.settings_dialog import SettingsDialog, families_for_script

ML = Profile(name="ml", lang="ml", username="Alice@PyAWB")


def dialog(qtbot: QtBot, config: AppConfig | None = None, page: str = "general") -> SettingsDialog:
    d = SettingsDialog(config or AppConfig(profiles=(ML,)), "Malayalam", page)
    qtbot.addWidget(d)
    return d


def test_pages_open_from_the_menu_names(qtbot: QtBot) -> None:
    for i, page in enumerate(SettingsDialog.PAGES):
        assert dialog(qtbot, page=page).tabs.currentIndex() == i


def test_theme_language_and_general(qtbot: QtBot) -> None:
    d = dialog(qtbot)
    for b in d.theme_group.buttons():
        if b.property("value") == "dark":
            b.setChecked(True)
    d.language_filter.setText("malay")
    visible = [d.languages.item(i) for i in range(d.languages.count())]
    shown = [i.text() for i in visible if not i.isHidden()]
    assert any("മലയാളം" in t for t in shown) and not any("العربية" in t for t in shown)
    match = next(i for i in visible if not i.isHidden() and "(ml)" in i.text())
    d.languages.setCurrentItem(match)
    d.word_wrap.setChecked(False)
    prefs = d.preferences()
    assert prefs.theme == "dark" and prefs.language == "ml" and not prefs.word_wrap


def test_fonts_are_kept_per_script(qtbot: QtBot) -> None:
    prefs = Preferences().with_font("Arabic", FontChoice(editor="Some Arabic Font"))
    d = dialog(qtbot, AppConfig(preferences=prefs), "fonts")
    page = d.fonts
    assert page.script.currentData() == "Malayalam"
    page.editor_size.setValue(15)
    page.script.setCurrentIndex(page.script.findData("Arabic"))
    assert page.editor_font.currentData() == "Some Arabic Font"  # kept though not installed
    result = d.preferences()
    assert result.font_for("Malayalam").editor_size == 15
    assert result.font_for("Arabic").editor == "Some Arabic Font"


def test_families_for_script_are_installed_fonts(qtbot: QtBot) -> None:
    from PySide6.QtGui import QFontDatabase

    latin = families_for_script("Latin")
    assert latin and set(latin) <= set(QFontDatabase.families())


def test_profiles(qtbot: QtBot, monkeypatch: object) -> None:
    from pyawb.ui import login_dialog

    d = dialog(qtbot, page="profiles")
    assert d.profile_table.rowCount() == 1

    class FakeLogin:
        def __init__(self, config: AppConfig, **kwargs: object) -> None:
            self.config = config

        def exec(self) -> bool:
            return True

        def updated_config(self) -> AppConfig:
            return self.config.with_profile(Profile(name="ar", lang="ar", username="Bob@B"))

    import pytest

    mp = pytest.MonkeyPatch()
    mp.setattr(login_dialog, "LoginDialog", FakeLogin)
    try:
        d._edit_profile("")  # pyright: ignore[reportPrivateUsage]
    finally:
        mp.undo()
    assert d.profile_table.rowCount() == 2
    d.profile_table.selectRow(1)
    d._make_default()  # pyright: ignore[reportPrivateUsage]
    assert d.updated_config().default_profile == "ar"
    d._delete_profile()  # pyright: ignore[reportPrivateUsage]
    assert [p.name for p in d.updated_config().profiles] == ["ml"]


def test_menu_applies_and_saves(qtbot: QtBot, monkeypatch: object) -> None:
    import pytest

    from pyawb.settings import appconfig
    from pyawb.ui import main_window
    from pyawb.ui.main_window import MainWindow

    w = MainWindow(language="en")
    qtbot.addWidget(w)
    chosen = Preferences(word_wrap=False).with_font("Latin", FontChoice(editor_size=17))

    class FakeSettings:
        def __init__(self, config: AppConfig, *args: object) -> None:
            self.config = config

        def exec(self) -> bool:
            return True

        def updated_config(self) -> AppConfig:
            from dataclasses import replace

            return replace(self.config, preferences=chosen)

    mp = pytest.MonkeyPatch()
    mp.setattr(main_window, "SettingsDialog", FakeSettings)
    try:
        w.open_settings("fonts")
    finally:
        mp.undo()
    assert w.editor.font().pointSize() == 17
    assert w.editor.lineWrapMode() == w.editor.LineWrapMode.NoWrap
    assert appconfig.load().preferences == chosen


def test_add_a_font_file(qtbot: QtBot, tmp_path: object) -> None:
    import subprocess
    from pathlib import Path

    import pytest

    from pyawb.ui.settings_dialog import add_font_file, load_user_fonts, user_font_dir

    found = subprocess.run(["fc-list", ":", "file"], capture_output=True, text=True).stdout
    fonts = [
        line.rstrip(": ").strip() for line in found.splitlines() if line.strip().endswith(".ttf:")
    ]
    if not fonts:
        pytest.skip("no TrueType font on this system to test with")
    families = add_font_file(Path(fonts[0]))
    assert families and (user_font_dir() / Path(fonts[0]).name).exists()
    assert set(families) <= set(load_user_fonts())

    not_a_font = Path(str(tmp_path)) / "notes.ttf"
    not_a_font.write_text("not a font")
    assert add_font_file(not_a_font) == [] and not (user_font_dir() / "notes.ttf").exists()


def test_missing_font_says_how_to_install(qtbot: QtBot, monkeypatch: object) -> None:
    import pytest

    from pyawb.ui import settings_dialog

    mp = pytest.MonkeyPatch()
    mp.setattr(settings_dialog, "families_for_script", lambda script: [])
    try:
        d = dialog(qtbot, page="fonts")
        page = d.fonts
        assert page.notice.text().startswith("Choosing the font is a critical step")
        assert page.missing.isVisibleTo(page)
        text = page.warning.text()
        assert "Noto Sans Malayalam" in text and "apt install" in text and "Font Book" in text
    finally:
        mp.undo()
    page._fill()  # pyright: ignore[reportPrivateUsage]  # fonts found again
    assert not page.missing.isVisibleTo(page) or not page.has_fonts()
