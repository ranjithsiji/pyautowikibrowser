"""The main window's edit loop against a fake Arabic Wikipedia: modes, pause, save, skip."""

from typing import Any

from pytestqt.qtbot import QtBot

from pyawb.core.article import Article
from pyawb.lists.listmaker import ArticleList
from pyawb.ui.main_window import MainWindow
from tests.api.test_editloop import open_response
from tests.api.test_session import SAVE_OK, approved_session

DIFF_ROWS = (
    '<tr><td class="diff-marker" data-marker="−"></td>'
    '<td class="diff-deletedline"><div>حيوان <del class="diffchange">[[أليف|أليف]]</del></div></td>'
    '<td class="diff-marker" data-marker="+"></td>'
    '<td class="diff-addedline"><div>حيوان <ins class="diffchange">[[أليف]]</ins></div></td></tr>'
)


def window(qtbot: QtBot, pages: dict[str, str | None]) -> tuple[MainWindow, Any]:
    session, t = approved_session()
    for title, text in pages.items():
        t.responses[("titles", title)] = open_response(title, text)
    t.responses[("action", "compare")] = {"compare": {"body": DIFF_ROWS}}
    t.responses[("action", "edit")] = SAVE_OK
    w = MainWindow(language="ar")
    qtbot.addWidget(w)
    w.use_session(session)
    w.list_maker.articles.add([Article(t) for t in pages])
    w.list_maker.refresh()
    w.summary.setEditText("تنظيف")
    return w, t


def idle(w: MainWindow) -> bool:
    return not w.busy


def loaded(w: MainWindow, index: int) -> bool:
    return w.current_index == index and w.current is not None and idle(w)


def statuses(w: MainWindow) -> list[str]:
    return [a.list_status for a in w.list_maker.articles]


def test_start_shows_processed_text_and_diff_then_saves(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير.", "كلب": "نص &eacute;"})
    w.show()
    assert w.start_action.isEnabled() and not w.diff.isVisible()
    assert w.position_label.text() == "0 / 2"  # nothing selected yet
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]] صغير."
    assert w.review_summary.currentText() == "/* top */ تنظيف"
    assert w.diff.isVisible() and "[[أليف]]" in w.diff.toPlainText()
    assert w.save_button.isEnabled() and not w.start_action.isEnabled()
    assert w.start_tab.stat_labels["links"].text() == "1"

    w.editor.setPlainText("حيوان [[أليف]] صغير جدا.")
    w.save()
    # saved; the next page loads by itself
    qtbot.waitUntil(lambda: w.edits == 1 and w.current is not None and idle(w), timeout=5000)
    edit = t.last("edit")
    assert edit["text"] == "حيوان [[أليف]] صغير جدا." and edit["title"] == "قط"
    assert edit["summary"].startswith("/* top */ تنظيف")
    assert statuses(w) == [ArticleList.SAVED, ""]
    assert w.position_label.text() == "2 / 2" and w.progress.value() == 1
    assert w.editor.toPlainText() == "نص é"
    assert w.logs.saved.pages() == ["قط"]

    w.skip_page("user")
    qtbot.waitUntil(lambda: not w.running and idle(w), timeout=5000)
    assert w.skips == 1 and statuses(w) == [ArticleList.SAVED, ArticleList.SKIPPED]
    assert w.current is None and w.editor.toPlainText() == "" and not w.diff.isVisible()
    assert w.logs.skipped.rows()[0][2:] == ["User", "Clicked ignore"]
    assert w.status_label.text() == "List complete!"


def test_skipped_pages_are_marked_and_the_loop_goes_on(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"نص": "نص", "مفقود": None, "قط": "حيوان [[أليف|أليف]]."})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.skips == 2  # no change, non-existent
    assert statuses(w) == [ArticleList.SKIPPED, ArticleList.SKIPPED, ""]
    assert [r[3] for r in w.logs.skipped.rows()] == ["No change", "Non-existent page"]
    w.list_maker.remove_done()
    assert [a.name for a in w.list_maker.articles] == ["قط"]


def test_pause_previous_next_and_skip(qtbot: QtBot) -> None:
    w, _ = window(
        qtbot, {"قط": "حيوان [[أليف|أليف]].", "كلب": "نص &eacute;", "حصان": "نص &eacute; ب"}
    )
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    # a running batch moves by itself: Previous / Next only while paused
    assert not w.previous_action.isEnabled() and not w.next_action.isEnabled()
    w.set_paused(True)
    assert not w.previous_action.isEnabled() and w.next_action.isEnabled()
    w.next_page()
    qtbot.waitUntil(lambda: loaded(w, 1), timeout=5000)
    assert statuses(w) == ["", "", ""]  # Next leaves the page unmarked
    w.previous_page()
    qtbot.waitUntil(lambda: loaded(w, 0), timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]]."
    # Skip moves on even when paused
    w.skip_page("user")
    qtbot.waitUntil(lambda: loaded(w, 1), timeout=5000)
    # Save waits for Next when paused
    w.save()
    qtbot.waitUntil(lambda: w.edits == 1 and idle(w), timeout=5000)
    assert w.current is None and w.next_index == 2 and w.next_action.isEnabled()
    assert statuses(w) == [ArticleList.SKIPPED, ArticleList.SAVED, ""]
    w.next_page()
    qtbot.waitUntil(lambda: loaded(w, 2), timeout=5000)


def test_unpausing_goes_on(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]].", "كلب": "نص &eacute;"})
    w.set_paused(True)
    w.start()
    qtbot.waitUntil(lambda: loaded(w, 0), timeout=5000)
    w.save()
    qtbot.waitUntil(lambda: w.edits == 1 and idle(w), timeout=5000)
    assert w.current is None
    w.set_paused(False)
    qtbot.waitUntil(lambda: loaded(w, 1), timeout=5000)


def test_modes(qtbot: QtBot) -> None:
    from pyawb.editloop import Mode

    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]]."})
    w.show()
    assert w.mode is Mode.EDIT and all(a.isVisible() for a in w.mode_actions.values())
    w.set_mode(Mode.READ_ONLY)
    w.start()
    qtbot.waitUntil(lambda: loaded(w, 0), timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف|أليف]]." and w.editor.isReadOnly()
    assert not w.diff.isVisible() and not w.save_action.isEnabled()
    w.set_mode(Mode.DRY_RUN)
    w.start()
    qtbot.waitUntil(lambda: loaded(w, 0), timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]]." and not w.editor.isReadOnly()
    assert w.skip_action.isEnabled() and not w.save_action.isEnabled()
    w.save()
    assert not any(p.get("action") == "edit" for p, _, _ in t.requests)
    w.log_out()
    assert [m for m, a in w.mode_actions.items() if a.isVisible()] == [Mode.READ_ONLY]
    assert w.mode is Mode.READ_ONLY


def test_diff_click_moves_the_editor(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "سطر\nحيوان [[أليف|أليف]]."})
    w.go_to_line(2)
    assert w.editor.textCursor().blockNumber() == 0  # nothing loaded: one empty block
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    w.go_to_line(2)
    assert w.editor.textCursor().blockNumber() == 1


def test_find_in_editor(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير."})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    w.find_in_editor("صغ.ر", True, False)
    assert w.editor.textCursor().selectedText() == "صغير"


def test_start_needs_an_edit_summary(qtbot: QtBot, message_boxes: list[tuple[str, str]]) -> None:
    w, t = window(qtbot, {"قط": "x &amp;"})
    w.summary.setEditText("")
    w.start()
    assert message_boxes and message_boxes[0][0] == "warning"
    assert not w.running and not any(p.get("titles") == "قط" for p, _, _ in t.requests)


def test_stop_keeps_the_page_in_the_list(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]]."})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    w.stop()
    assert w.current is None and not w.running
    assert statuses(w) == [""]
    assert w.start_action.isEnabled()


def test_manual_list(qtbot: QtBot) -> None:
    w = MainWindow(language="en")
    qtbot.addWidget(w)
    lm = w.list_maker
    assert lm.current_source.name == "Manual list"
    lm.text.setPlainText("foo\nhttps://en.wikipedia.org/wiki/Bar_baz|മലയാളം")
    lm.make_list()
    qtbot.waitUntil(lambda: not lm.busy and len(lm.articles) == 3, timeout=5000)
    assert [lm.list.item(i).text() for i in range(3)] == ["Foo", "Bar baz", "മലയാളം"]
    assert lm.text.toPlainText() == ""
    # without a wiki, other sources say so
    lm.source.setCurrentIndex(lm.source.findData("Category"))
    lm.line.setText("Cats")
    lm.make_list()
    assert len(lm.articles) == 3 and "connect" in w.status_label.text()


def test_find_and_replace_and_append(qtbot: QtBot) -> None:
    from pyawb.rules.findreplace import ReplacementRow
    from pyawb.ui.find_replace_dialog import FindReplaceSettings

    w, _ = window(qtbot, {"قط": "حيوان [[أليف]] صغير."})
    w.options.set_find_replace(FindReplaceSettings((ReplacementRow("صغير", "كبير"),)))
    assert w.options.find_replace.isChecked()
    w.options.append.setChecked(True)
    w.options.append_text.setPlainText("{{بذرة}}")
    w.options.append_newlines.setValue(1)
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]] كبير.\n{{بذرة}}"
    assert "استبدل: صغير ← كبير" in w.review_summary.currentText()


def test_typo_list_is_loaded_and_used(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "هذا قطه صغير."})
    t.pages["ويكيبيديا:AutoWikiBrowser/Typos"] = (
        '<Typo word="قطة" find="\\bقطه\\b" replace="قطة" />'
    )
    w.options.fix_typos.setChecked(True)
    qtbot.waitUntil(lambda: w.typos is not None, timeout=5000)
    assert "1 typos loaded" in w.options.typo_status.text()
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.editor.toPlainText() == "هذا قطة صغير."
    assert "قطه" in w.review_summary.currentText()


def test_start_waits_for_the_typo_list(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "هذا قطه صغير."})
    t.pages["ويكيبيديا:AutoWikiBrowser/Typos"] = '<Typo find="\\bقطه\\b" replace="قطة" />'
    w.options.fix_typos.blockSignals(True)
    w.options.fix_typos.setChecked(True)
    w.options.fix_typos.blockSignals(False)
    w.start()  # loads the list, then starts
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.editor.toPlainText() == "هذا قطة صغير."


def test_missing_typo_list(qtbot: QtBot, message_boxes: list[tuple[str, str]]) -> None:
    w, _ = window(qtbot, {"قط": "x"})
    w.options.fix_typos.setChecked(True)
    qtbot.waitUntil(lambda: not w.typos_loading, timeout=5000)
    assert message_boxes and message_boxes[-1][0] == "question"  # English list? -> No
    assert not w.options.fix_typos.isChecked() and w.typos is None


def test_list_maker_input_fits_the_source(qtbot: QtBot) -> None:
    w = MainWindow(language="en")
    qtbot.addWidget(w)
    w.show()
    lm = w.list_maker
    assert lm.text.isVisible() and not lm.line.isVisible()  # Manual list: several lines
    lm.source.setCurrentIndex(lm.source.findData("What links here (all NS) (and to redirects)"))
    assert lm.line.isVisible() and not lm.text.isVisible()  # one value: one line
    assert lm.line.height() < lm.text.height()
    lm.source.setCurrentIndex(lm.source.findData("My watchlist"))
    assert not lm.line.isVisible() and not lm.text.isVisible()  # no input


def test_info_bar(qtbot: QtBot) -> None:
    w = MainWindow(language="en")
    qtbot.addWidget(w)
    bar = w.info_bar
    assert bar.wiki.text.text() == "No wiki" and bar.user.text.text() == "Not logged in"
    assert bar.approval.isHidden() and bar.mode.text.text() == "Mode: Read only"

    w2, _ = window(qtbot, {"قط": "x"})
    bar = w2.info_bar
    assert bar.wiki.text.text().endswith("(ar.wikipedia.org)")
    assert bar.user.text.text() == "Alice"
    assert bar.approval.text.text() == "Approved for editing"
    assert bar.mode.text.text() == "Mode: Make changes"
    from pyawb.editloop import Mode

    w2.set_mode(Mode.DRY_RUN)
    assert bar.mode.text.text() == "Mode: Dry run"
