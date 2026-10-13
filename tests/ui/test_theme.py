import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from pyawb.ui import theme


def test_light_and_dark_define_the_same_codex_tokens() -> None:
    tokens = theme.codex_tokens()
    assert tokens["light"].keys() == tokens["dark"].keys()
    assert tokens["light"]["color-progressive"] == "#36c"
    assert tokens["dark"]["background-color-base"] == "#101418"


def test_css_rgba_becomes_qss_argb() -> None:
    assert theme.tokens(theme.Mode.LIGHT)["background_color_button_quiet__hover"] == "#07001849"


@pytest.mark.parametrize("mode", [theme.Mode.LIGHT, theme.Mode.DARK])
def test_stylesheet_fills_every_placeholder(mode: theme.Mode) -> None:
    # Template.substitute raises KeyError on an unknown token.
    qss = theme.stylesheet(mode)
    assert "$" not in qss
    assert theme.tokens(mode)["background_color_progressive"] in qss


def test_apply_forces_fusion(qtbot: QtBot) -> None:
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    theme.apply(app, theme.Mode.DARK)
    try:
        expected = theme.codex_tokens()["dark"]["background-color-neutral-subtle"]
        assert app.palette().window().color().name() == expected
    finally:
        app.setStyleSheet("")
    # With a stylesheet set, style() is Qt's stylesheet proxy; check the real style without it.
    assert app.style().name().lower() == "fusion"


def _parse_messages(qss: str) -> list[str]:
    from PySide6.QtCore import qInstallMessageHandler

    app = QApplication.instance()
    assert isinstance(app, QApplication)
    messages: list[str] = []
    previous = qInstallMessageHandler(lambda _type, _ctx, msg: messages.append(msg))
    try:
        app.setStyleSheet(qss)
    finally:
        app.setStyleSheet("")
        qInstallMessageHandler(previous)
    return [m for m in messages if "parse" in m.lower()]


@pytest.mark.parametrize("mode", [theme.Mode.LIGHT, theme.Mode.DARK])
def test_qt_parses_the_stylesheet(qtbot: QtBot, mode: theme.Mode) -> None:
    # Qt drops the whole stylesheet on one syntax error (e.g. "*/" inside a comment)
    assert _parse_messages("/* a */ b */ QWidget {}")  # the check itself works
    assert not _parse_messages(theme.stylesheet(mode))
