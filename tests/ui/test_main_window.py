from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from awb_l.ui.main_window import MainWindow


def test_window_opens_and_switches_to_rtl(qtbot: QtBot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    w.set_text_direction(rtl=True)
    assert w.editor.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert w.editor.document().defaultTextOption().textDirection() == Qt.LayoutDirection.RightToLeft
