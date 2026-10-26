"""History, What links here, Page logs and Typos tabs in the main window."""

from typing import Any

import pytest
from PySide6.QtCore import QItemSelectionModel
from pytestqt.qtbot import QtBot

from pyawb.rules.typos import TypoStat
from pyawb.ui.page_tabs import PageLogsTab, TyposTab
from tests.ui.test_main_loop import window


def tab_titles(w: Any) -> list[str]:
    return [w.edit_tabs.tabText(i) for i in range(w.edit_tabs.count())]


def test_tabs_load_when_shown(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير."})
    assert tab_titles(w) == ["Edit box", "History", "What links here", "Logs", "Page logs"]
    revisions = [
        {"revid": 9, "parentid": 8, "timestamp": "2026-10-01T10:00:00Z", "user": "Alice",
         "comment": "تنظيف", "size": 50},
    ]  # fmt: skip
    history = {"query": {"pages": [{"title": "قط", "revisions": revisions}]}}
    # first, so it wins over the page-open response that also matches titles=قط
    t.responses = {("rvprop", "ids|timestamp|user|comment|size|flags"): history, **t.responses}
    t.responses[("bltitle", "قط")] = {"query": {"backlinks": [{"title": "كلب", "ns": 0}]}}
    t.responses[("eititle", "قط")] = {"query": {"embeddedin": []}}
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    w.edit_tabs.setCurrentWidget(w.history_tab)
    qtbot.waitUntil(lambda: w.history_tab.table.rowCount() == 1, timeout=5000)
    item = w.history_tab.table.item(0, 1)
    assert item is not None and item.text() == "Alice"
    asked = len(t.requests)
    w.edit_tabs.setCurrentIndex(0)
    w.edit_tabs.setCurrentWidget(w.history_tab)  # same page: not loaded again
    assert len(t.requests) == asked
    w.edit_tabs.setCurrentWidget(w.links_tab)
    qtbot.waitUntil(lambda: w.links_tab.table.rowCount() == 1, timeout=5000)
    added: list[list[str]] = []
    w.links_tab.add_to_list.connect(added.append)
    w.links_tab.table.selectionModel().select(
        w.links_tab.table.model().index(0, 0),
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )
    w.links_tab.add_to_list.emit(w.links_tab.selected_titles())
    assert added == [["كلب"]]


def test_history_diff_link(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    from pyawb.api.pageinfo import Revision
    from pyawb.ui import page_tabs

    w, _ = window(qtbot, {"قط": "x"})
    tab = w.history_tab
    tab.show_history("قط", [Revision(42, 41, "2026-10-01T10:00:00Z", "A", "", 10, False, -5)])
    change = tab.table.item(0, 3)
    assert change is not None and change.text() == "-5"
    opened: list[str] = []
    monkeypatch.setattr(page_tabs, "_open", opened.append)
    tab.table.selectionModel().select(
        tab.table.model().index(0, 0),
        QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows,
    )
    tab.open_diff()
    assert opened == ["https://en.wikipedia.org/w/index.php?diff=42"]


def test_page_logs(qtbot: QtBot) -> None:
    tab = PageLogsTab()
    qtbot.addWidget(tab)
    tab.log_action("قط", True, "Move", "to كلب")
    tab.log_action("فأر", False, "Delete", "permissiondenied")
    assert tab.pages(tab.successful) == ["قط"] and tab.pages(tab.failed) == ["فأر"]


def test_typos_tab(qtbot: QtBot) -> None:
    tab = TyposTab()
    qtbot.addWidget(tab)
    stats = [TypoStat("teh", "the", total=2, self_matches=2), TypoStat("adn", "and", total=1)]
    tab.page_stats(stats)
    assert tab.current.rowCount() == 2
    tab.add_overall(stats, skipped=False)
    assert tab.total.text() == "3" and tab.no_change.text() == "2" and tab.ratio.text() == "1.00"
    first = tab.overall.item(0, 0)
    assert first is not None and first.background().color().isValid()  # all no-change: yellow
    tab.clear()
    assert tab.overall.rowCount() == 0 and tab.total.text() == "0"


def test_typos_tab_follows_the_typo_list(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, _ = window(qtbot, {"قط": "x"})
    w._show_typos_tab(True)  # pyright: ignore[reportPrivateUsage]
    assert "Typos" in tab_titles(w)
    w._typos_unavailable("none")  # pyright: ignore[reportPrivateUsage]
    assert "Typos" not in tab_titles(w)
