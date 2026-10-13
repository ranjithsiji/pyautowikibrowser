"""The start screen: language, wiki, fonts, login (bot password, two-factor, skip), pages."""

from typing import Any

import pytest
from PySide6.QtWidgets import QMessageBox
from pytestqt.qtbot import QtBot

from pyawb.api.session import WikiSession
from pyawb.settings import appconfig
from pyawb.settings.appconfig import AppConfig, Profile
from pyawb.ui.start_screen import ACCOUNT_PASSWORD, STEPS, StartScreen
from tests.api.test_session import approved_session


def screen(qtbot: QtBot, config: AppConfig | None = None, **kwargs: Any) -> StartScreen:
    calls: list[tuple[Any, ...]] = kwargs.pop("calls", [])

    def connector(
        config: AppConfig, profile: Profile, password: str | None, **kw: Any
    ) -> WikiSession:
        calls.append((profile, password, kw))
        second = kw.get("second_factor")
        if second is not None:
            calls.append(("code", second("Two-factor authentication code")))
        return approved_session()[0]

    s = StartScreen(
        config or AppConfig(),
        connector=kwargs.pop("connector", connector),
        context=lambda config, session: None,
    )
    qtbot.addWidget(s)
    return s


def select(picker: Any, code: str) -> None:
    for i in range(picker.list.count()):
        item = picker.list.item(i)
        if item.data(0x0100) == code:  # Qt.UserRole
            picker.list.setCurrentItem(item)
            return
    raise AssertionError(code)


def test_first_run_goes_through_every_step(qtbot: QtBot) -> None:
    calls: list[tuple[Any, ...]] = []
    s = screen(qtbot, calls=calls)
    assert s.step() == "wiki" and not s.back.isEnabled()  # no interface language step
    assert s.project.currentData() == "wikipedia"
    select(s.wiki_language, "ml")
    s._next()  # pyright: ignore[reportPrivateUsage]
    assert s.step() == "fonts"
    # the wiki's script, fixed; a font that has it is chosen to start with
    assert s.fonts.script.currentData() == "Malayalam" and not s.fonts.script.isEnabled()
    if s.fonts.has_fonts():
        assert s.fonts.editor_font.currentData() in s.fonts.families
    s.fonts.editor_size.setValue(16)
    s._next()  # pyright: ignore[reportPrivateUsage]
    assert s.step() == "login"
    s._next()  # pyright: ignore[reportPrivateUsage]
    assert s.step() == "login"  # a login (or Skip) is needed to go on
    s.username.setText("Alice@PyAWB")
    s.password.setText("secret")
    s.log_in()
    qtbot.waitUntil(lambda: s.step() == "pages", timeout=5000)
    profile, password, _ = calls[0]
    assert (profile.name, profile.lang, profile.username, password) == (
        "ml.wikipedia",
        "ml",
        "Alice@PyAWB",
        "secret",
    )
    assert "Approved for editing" in s.login_status.text()
    s._next()  # pyright: ignore[reportPrivateUsage]  # Open PyAutoWikiBrowser
    assert s.result() == 1
    result = s.result_value()
    assert result.session is not None
    saved = appconfig.load()
    assert saved.default_profile == "ml.wikipedia"
    assert saved.preferences.language == ""  # the interface language follows the system
    assert saved.preferences.font_for("Malayalam").editor_size == 16


def test_fonts_are_required(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyawb.ui import settings_dialog

    monkeypatch.setattr(settings_dialog, "families_for_script", lambda script: [])
    s = screen(qtbot)
    select(s.wiki_language, "ml")
    s._next()  # pyright: ignore[reportPrivateUsage]
    assert s.step() == "fonts" and not s.next.isEnabled()
    assert "No installed font has the Malayalam script" in s.fonts.warning.text()
    s._next()  # pyright: ignore[reportPrivateUsage]
    assert s.step() == "fonts"
    s.back.click()
    select(s.wiki_language, "en")  # Latin: the system's font has it
    s._next()  # pyright: ignore[reportPrivateUsage]
    assert s.step() == "fonts" and s.next.isEnabled()


def test_two_factor_code(qtbot: QtBot) -> None:
    calls: list[tuple[Any, ...]] = []
    s = screen(qtbot, calls=calls)
    s.go(STEPS.index("login"))
    for b in s.method_group.buttons():
        if b.property("method") == ACCOUNT_PASSWORD:
            b.setChecked(True)
    s.username.setText("Alice")
    s.password.setText("main password")
    s.log_in()
    qtbot.waitUntil(lambda: s.code.isVisibleTo(s), timeout=5000)
    assert "Two-factor" in s.code_label.text()
    s.code.setText("123456")
    s._send_code()  # pyright: ignore[reportPrivateUsage]
    qtbot.waitUntil(lambda: s.step() == "pages", timeout=5000)
    assert ("code", "123456") in calls
    assert not s.chosen_profile().remember_password  # account passwords are never kept


def test_skip_warns_then_works_offline(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    s = screen(qtbot)
    s.go(STEPS.index("login"))
    s.skip_login()  # the test's message boxes answer No
    assert s.step() == "login"
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    s.skip_login()
    assert s.step() == "pages" and s.session is None
    assert s.list_maker.current_source.name == "Manual list"  # offline lists still work


def test_later_runs_start_at_login(qtbot: QtBot) -> None:
    config = AppConfig(
        profiles=(Profile(name="ar", lang="ar", username="Bob@B"),), default_profile="ar"
    )
    s = screen(qtbot, config)
    assert s.step() == "login" and s.username.text() == "Bob@B"
    assert s.steps_label.text().count("›") == 3  # Wiki, Fonts, Log in, Pages
    s.go(STEPS.index("wiki"))
    assert s.wiki_lang() == "ar"
    assert s.chosen_profile().name == "ar"  # the same wiki keeps its profile


def test_failed_login_says_why(qtbot: QtBot) -> None:
    from pyawb.api.session import LoginException

    def failing(*args: Any, **kwargs: Any) -> WikiSession:
        raise LoginException("Incorrect username or password")

    s = screen(qtbot, connector=failing)
    s.go(STEPS.index("login"))
    s.username.setText("Alice@PyAWB")
    s.password.setText("wrong")
    s.log_in()
    qtbot.waitUntil(lambda: "Could not log in" in s.login_status.text(), timeout=5000)
    assert s.step() == "login" and s.session is None
