import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from awb_l.ui import theme


def test_light_and_dark_define_the_same_tokens() -> None:
    assert theme.LIGHT.keys() == theme.DARK.keys()


@pytest.mark.parametrize("mode", [theme.Mode.LIGHT, theme.Mode.DARK])
def test_stylesheet_fills_every_placeholder(mode: theme.Mode) -> None:
    # Template.substitute raises KeyError on an unknown token.
    qss = theme.stylesheet(mode)
    assert "$" not in qss
    assert theme.tokens(mode)["accent"] in qss


def test_apply_forces_fusion(qtbot: QtBot) -> None:
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    theme.apply(app, theme.Mode.DARK)
    try:
        assert app.palette().window().color().name() == theme.DARK["bg"]
    finally:
        app.setStyleSheet("")
    # With a stylesheet set, style() is Qt's stylesheet proxy; check the real style without it.
    assert app.style().name().lower() == "fusion"
