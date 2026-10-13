from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from awb_x.ui.main_window import MainWindow


def test_window_opens_and_switches_to_rtl(qtbot: QtBot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    w.set_text_direction(rtl=True)
    assert w.editor.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert w.editor.document().defaultTextOption().textDirection() == Qt.LayoutDirection.RightToLeft


def test_ensure_utf8_ctype_keeps_language() -> None:
    from awb_x.ui.app import ensure_utf8_ctype

    env = {"LANG": "en_IN"}
    chosen = ensure_utf8_ctype(env)
    assert chosen in ("en_IN.UTF-8", "C.UTF-8")
    assert env["LC_CTYPE"] == chosen and env["LANG"] == "en_IN"

    utf8 = {"LANG": "ml_IN.UTF-8"}
    assert ensure_utf8_ctype(utf8) is None and "LC_CTYPE" not in utf8
