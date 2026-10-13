"""The menu bar: View, Options, Tools, Help (AWB Main.Designer.cs) and what they do."""

from pathlib import Path

import pytest
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMenu
from pytestqt.qtbot import QtBot

from pyawb.core.article import Article
from pyawb.editloop import Mode
from pyawb.ui import main_window
from pyawb.ui.main_window import MainWindow
from tests.ui.test_main_loop import window


def menu(w: MainWindow, title: str) -> list[str]:
    for a in w.menuBar().actions():
        if a.text().replace("&", "") == title:
            m = a.menu()
            assert isinstance(m, QMenu)
            return [x.text() for x in m.actions() if not x.isSeparator()]
    raise AssertionError(title)


def test_menu_bar(qtbot: QtBot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    titles = [a.text().replace("&", "") for a in w.menuBar().actions()]
    assert titles == ["File", "View", "List", "Options", "Tools", "Settings", "Help"]
    assert menu(w, "Options") == [
        "Preferences…",
        "Use pre-parse mode",
        "Follow redirects",
        "Apply changes automatically",
        "Auto focus end of the edit box",
        "Do not use section edit summaries",
        "Restrict {{DEFAULTSORT}} change/addition",
        "Restrict orphan tag addition to linkless pages",
        "Do not apply WP:MOS fixes",
        "Highlight syntax in edit box",
        "Highlight Find matches",
        "Highlight errors",
        "Mark all as minor",
        "Watchlist",
        "Sort interwiki links",
        "Replace reference tags",
    ]
    assert menu(w, "View")[:4] == [
        "Show toolbar",
        "Show control panel",
        "Enlarge edit box",
        "Show edit box toolbar",
    ]
    assert menu(w, "Tools") == ["Regex tester", "Reset saved/skipped counts", "Invalidate cache"]
    assert menu(w, "Help") == ["Help", "About PyAutoWikiBrowser"]


def test_menu_items_mirror_the_tabs(qtbot: QtBot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.no_section_summary_action.setChecked(True)
    assert not w.options.section_summary.isChecked()
    w.options.follow_redirects.setChecked(False)
    assert not w.follow_redirects_action.isChecked()
    w.minor_action.setChecked(True)
    assert w.minor.isChecked()
    w.watch.setCurrentIndex(1)
    watch = [a for a in w.findChildren(type(w.minor_action)) if a.text() == w.watch.itemText(1)]
    assert any(a.isChecked() for a in watch)


def test_view_toggles(qtbot: QtBot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    w.show_panel_action.setChecked(False)
    assert not w.options.isVisible()
    w.show_panel_action.setChecked(True)
    w.enlarge_action.setChecked(True)
    assert not w.options.isVisible()
    w.enlarge_action.setChecked(False)
    assert w.options.isVisible()
    w.false_positives_action.setChecked(True)
    assert w.start_tab.false_button.isVisible()


def test_options_go_to_the_loop(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير."})
    w.restrict_defaultsort_action.setChecked(True)
    w.no_mos_action.setChecked(True)
    w.sort_interwikis_action.setChecked(False)
    w.apply_changes_action.setChecked(False)
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    assert w.opts is not None
    assert w.opts.process.restrict_defaultsort_changes and w.opts.process.no_mos_compliance_fixes
    assert not w.opts.sort_interwikis
    assert w.editor.toPlainText() == "حيوان [[أليف|أليف]] صغير."  # not applied
    w.reparse()
    qtbot.waitUntil(lambda: not w.busy, timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]] صغير."


def test_pre_parse_marks_pages_and_goes_on(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]].", "كلب": "نص", "فأر": "[[ب|ب]]"})
    w.set_mode(Mode.READ_ONLY)
    w.pre_parse_action.setChecked(True)
    w.start()
    qtbot.waitUntil(lambda: not w.running and not w.busy, timeout=8000)
    assert [a.pre_processed for a in w.list_maker.articles] == [True, False, True]
    assert [a.list_status for a in w.list_maker.articles] == ["", "skipped", ""]
    assert w.status_label.text() == "Pre-parsing finished"
    assert not any(p.get("action") == "compare" for p, _, _ in t.requests)  # no diffs


def test_highlight_find_and_errors(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]] و [[ب حيوان."})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    w.start_tab.find_text.setText("حيوان")
    w.highlight_find_action.setChecked(True)
    assert len(w.editor.extraSelections()) == 2
    w.highlight_errors_action.setChecked(True)
    assert w.errors and len(w.editor.extraSelections()) == 2 + len(w.errors)
    w.next_error()
    assert w.editor.textCursor().selectedText().startswith("[[")


def test_delink_and_false_positive(qtbot: QtBot, private_home: Path) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]] [[كلب|الكلب]]."})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    text = w.editor.toPlainText()
    start = text.index("[[كلب")
    cursor = w.editor.textCursor()
    cursor.setPosition(start)
    cursor.setPosition(text.index("]].") + 2, QTextCursor.MoveMode.KeepAnchor)
    w.editor.setTextCursor(cursor)
    w.delink_selection()
    assert w.editor.toPlainText() == "حيوان [[أليف]] الكلب."
    w.record_false_positive()
    found = list(private_home.rglob("False positives.txt"))
    assert found and found[0].read_text(encoding="utf-8") == "#[[قط]]\n"


def test_reset_counts_and_help(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    w.edits, w.skips = 3, 2
    w.reset_counts()
    assert (w.edits, w.skips) == (0, 0)
    opened: list[str] = []
    monkeypatch.setattr(MainWindow, "open_url", staticmethod(opened.append))
    w.open_help()
    assert opened == [main_window.HELP_URL]
    w.list_maker.articles.add([Article("A")])
    w.invalidate_cache()
    assert w.status_label.text() == "Cache cleared"
