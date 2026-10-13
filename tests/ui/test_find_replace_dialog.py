"""The find and replace table."""

from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from pyawb.rules.findreplace import ReplacementRow
from pyawb.ui.find_replace_dialog import COLUMNS, FindReplaceDialog, FindReplaceSettings

ROWS = (
    ReplacementRow("قط", "هر", minor=True),
    ReplacementRow(r"\bfoo\b", "bar", is_regex=True, case_sensitive=True, comment="c"),
)


def dialog(qtbot: QtBot, settings: FindReplaceSettings | None = None) -> FindReplaceDialog:
    d = FindReplaceDialog(settings or FindReplaceSettings(ROWS, ignore_links=True))
    qtbot.addWidget(d)
    return d


def test_round_trip_with_an_empty_row_to_type_in(qtbot: QtBot) -> None:
    d = dialog(qtbot)
    assert d.table.rowCount() == 3 and d.row(2) == ReplacementRow()
    s = d.settings()
    assert s.rows == ROWS and s.ignore_links and not s.ignore_more and s.add_to_summary


def test_typing_in_the_last_row_adds_another(qtbot: QtBot) -> None:
    d = dialog(qtbot, FindReplaceSettings())
    assert d.table.rowCount() == 1
    item = d.table.item(0, 0)
    assert item is not None
    item.setText("x")
    assert d.table.rowCount() == 2
    assert d.rows() == (ReplacementRow("x"),)  # new rows are enabled, as in AWB


def test_move_delete_and_check_all(qtbot: QtBot) -> None:
    d = dialog(qtbot)
    d.table.setCurrentCell(1, 0)
    d.move_row(-1)
    assert [r.find for r in d.rows()] == [r"\bfoo\b", "قط"]
    minor = [name for name, _ in COLUMNS].index("minor")
    d.set_column(minor, True)
    assert all(r.minor for r in d.rows())
    d.table.selectRow(0)
    d.delete_rows()
    assert [r.find for r in d.rows()] == ["قط"]
    d.clear()
    assert d.rows() == () and d.table.rowCount() == 1


def test_invalid_regex_keeps_the_dialog_open(qtbot: QtBot) -> None:
    d = dialog(qtbot, FindReplaceSettings((ReplacementRow("(a", is_regex=True),)))
    d._accept()  # pyright: ignore[reportPrivateUsage]
    assert d.result() == 0 and d.error.isVisibleTo(d) and "Row 1" in d.error.text()
    item = d.table.item(0, [n for n, _ in COLUMNS].index("is_regex"))
    assert item is not None
    item.setCheckState(Qt.CheckState.Unchecked)
    d._accept()  # pyright: ignore[reportPrivateUsage]
    assert d.result() == 1
