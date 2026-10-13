"""The login dialog: profile choice, validation, and the profile saved to config.toml."""

from pytestqt.qtbot import QtBot

from pyawb.settings.appconfig import AppConfig, Profile
from pyawb.ui.login_dialog import NEW_PROFILE, LoginDialog

ML = Profile(name="ml", lang="ml", username="Alice@PyAWB", remember_password=True, notes="n")


def test_new_profile_on_empty_config(qtbot: QtBot) -> None:
    d = LoginDialog(AppConfig())
    qtbot.addWidget(d)
    assert d.profiles.currentData() == NEW_PROFILE and d.name.isEnabled()
    assert d.validation_error() == "Give the profile a name."
    d.name.setText("ar")
    d.lang.setText("AR")
    d.username.setText("Bob@Bot")
    assert d.validation_error() == "Give the password."
    d.password.setText("secret")
    assert d.validation_error() is None
    config = d.updated_config()
    assert config.default_profile == "ar"  # the first profile becomes the default
    p = config.profile("ar")
    assert p is not None and p.lang == "ar" and p.username == "Bob@Bot"


def test_existing_profile_with_remembered_password(qtbot: QtBot) -> None:
    d = LoginDialog(AppConfig(profiles=(ML,), default_profile="ml"), {"ml": True})
    qtbot.addWidget(d)
    assert d.profiles.currentData() == "ml" and not d.name.isEnabled()
    assert d.lang.text() == "ml" and d.remember.isChecked() and d.make_default.isChecked()
    assert d.validation_error() is None  # the keychain has the password
    d.project.setCurrentText("custom")
    assert not d.lang.isEnabled() and d.custom_url.isEnabled()
    assert d.validation_error() == "Give the custom wiki's script path."
    d.custom_url.setText("https://wiki.example.org/w/")
    d.make_default.setChecked(False)
    config = d.updated_config()
    p = config.profile("ml")
    assert p is not None and p.custom_url == "https://wiki.example.org/w/" and p.notes == "n"
    assert config.default_profile == ""


def test_duplicate_new_profile_name(qtbot: QtBot) -> None:
    d = LoginDialog(AppConfig(profiles=(ML,)))
    qtbot.addWidget(d)
    d.profiles.setCurrentIndex(d.profiles.findData(NEW_PROFILE))
    d.name.setText("ml")
    assert d.validation_error() == "A profile with this name already exists."
