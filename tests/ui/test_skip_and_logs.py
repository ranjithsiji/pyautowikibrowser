"""The Skip tab's general options and page radio, the spam filter, and the Logs context menu
(AWB Main.cs skip checks, LogControl.cs)."""

from typing import Any

import pytest
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from pyawb.ui.logs_tab import LogsTab
from pyawb.ui.main_window import MainWindow
from pyawb.ui.options_panel import OptionsPanel
from tests.ui.test_main_loop import window


def test_skip_tab_options_reach_the_loop(qtbot: QtBot) -> None:
    p = OptionsPanel()
    qtbot.addWidget(p)
    o = p.loop_options("x", "Alice")
    assert o.skip_non_existent and not o.skip_existent  # AWB's default: "Doesn't exist"
    p.page_exists.setChecked(True)
    p.skip_no_alerts.setChecked(True)
    p.skip_cosmetic.setChecked(True)
    o = p.loop_options("x", "Alice")
    assert o.skip_existent and not o.skip_non_existent
    assert o.skip_if_no_alerts and o.skip_cosmetic
    p.page_any.setChecked(True)
    o = p.loop_options("x", "Alice")
    assert not o.skip_existent and not o.skip_non_existent
    p.skip_genfixes.setChecked(True)
    assert not p.skip_minor_genfixes.isEnabled()


def started(qtbot: QtBot) -> tuple[MainWindow, Any]:
    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير.", "كلب": "[[ب|ب]]"})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    t.responses[("action", "edit")] = {
        "error": {"code": "spamblacklist", "info": "http://spam.example is blacklisted"}
    }
    return w, t


def test_spam_filter_skips_when_checked(qtbot: QtBot) -> None:
    w, _ = started(qtbot)
    w.options.skip_spam_filter.setChecked(True)
    w.save()
    qtbot.waitUntil(lambda: w.skips == 1, timeout=5000)
    assert "blacklisted" in w.logs.skipped.rows()[0][3]


def test_spam_filter_asks_to_try_again(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, _ = started(qtbot)
    asked: list[str] = []

    def answer(*args: Any, **kwargs: Any) -> QMessageBox.StandardButton:
        asked.append(args[2])
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", answer)
    w.save()
    qtbot.waitUntil(lambda: bool(asked) and w.current is not None and not w.busy, timeout=5000)
    assert "Try and edit again?" in asked[0] and w.skips == 0 and w.current_index == 0


def logs(qtbot: QtBot) -> LogsTab:
    tab = LogsTab()
    qtbot.addWidget(tab)
    tab.log_skipped("A", "AWB", "No change")
    tab.log_skipped("B", "AWB", "Non-existent page")
    tab.log_skipped("C", "AWB", "no change")
    tab.log_saved("D", 1234)
    return tab


def pick(log: Any, row: int) -> None:
    """Select one row through the selection model (QAbstractItemView.selectRow follows the
    application's keyboard state, which other window tests can leave toggling)."""
    t = log.table
    t.selectionModel().select(
        t.model().index(row, 0),
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )


def test_logs_newest_first_and_menu(qtbot: QtBot) -> None:
    tab = logs(qtbot)
    assert tab.skipped.pages() == ["C", "B", "A"]
    menu = [a.text() for a in tab.skipped.context_menu().actions() if not a.isSeparator()]
    assert menu == [
        "Add selected to page list",
        "Cut",
        "Copy",
        "Remove",
        "Select all",
        "Select none",
        "Open in browser",
        "Open history in browser",
        "Open diff in browser",
        "Clear",
        "Reset",
    ]
    pick(tab.skipped, 2)
    menu = [a.text() for a in tab.skipped.context_menu().actions() if not a.isSeparator()]
    assert "Filter by skip reason: No change" in menu
    assert not tab.skipped.diff_action.isEnabled()  # diffs: saved pages only


def test_logs_filter_and_reset(qtbot: QtBot) -> None:
    tab = logs(qtbot)
    pick(tab.skipped, 2)  # A, "No change"
    tab.skipped.filter_reason(keep=True)
    assert tab.skipped.pages() == ["C", "A"]  # case-insensitive, as AWB
    tab.skipped.reset()
    assert sorted(tab.skipped.pages()) == ["A", "B", "C"]
    pick(tab.skipped, 0)
    tab.skipped.filter_reason(keep=False)
    assert tab.skipped.pages() == ["B"]


def test_logs_copy_cut_and_add(qtbot: QtBot) -> None:
    tab = logs(qtbot)
    added: list[list[str]] = []
    tab.add_to_list.connect(added.append)
    pick(tab.skipped, 1)
    tab.skipped.add_selected_action.trigger()
    assert added == [["B"]]
    tab.skipped.cut()
    assert QApplication.clipboard().text() == "B" and tab.skipped.pages() == ["C", "A"]


def test_logs_diff_link(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    tab = logs(qtbot)
    opened: list[str] = []
    monkeypatch.setattr(tab.saved, "_open", lambda urls: opened.extend(urls))
    pick(tab.saved, 0)
    tab.saved.open_diffs()
    assert opened == ["https://en.wikipedia.org/w/index.php?diff=1234"]
