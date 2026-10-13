"""The main window's edit loop against a fake Arabic Wikipedia: start, diff, save, skip."""

from typing import Any

from pytestqt.qtbot import QtBot

from pyawb.core.article import Article
from pyawb.editloop import EditLoop
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
    w.session, w.loop = session, EditLoop(session)
    w.set_text_direction(session.site.rtl)
    w.list_maker.articles.add([Article(t) for t in pages])
    w.list_maker.refresh()
    w.summary.setEditText("تنظيف")
    return w, t


def idle(w: MainWindow) -> bool:
    return not w.busy


def test_start_shows_processed_text_and_diff_then_saves(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير.", "كلب": "نص &eacute;"})
    assert w.start_button.isEnabled()
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]] صغير."
    assert w.review_summary.currentText() == "/* top */ تنظيف"
    assert w.tabs.currentWidget() is w.diff
    assert "[[أليف]]" in w.diff.toPlainText()
    assert w.save_button.isEnabled() and not w.start_button.isEnabled()

    w.editor.setPlainText("حيوان [[أليف]] صغير جدا.")
    w.save()
    # saved; the next page loads by itself
    qtbot.waitUntil(lambda: w.edits == 1 and w.current is not None and idle(w), timeout=5000)
    edit = t.last("edit")
    assert edit["text"] == "حيوان [[أليف]] صغير جدا." and edit["title"] == "قط"
    assert edit["summary"].startswith("/* top */ تنظيف")
    assert [a.name for a in w.list_maker.articles] == ["كلب"]
    assert w.editor.toPlainText() == "نص é"

    w.skip_page("user")
    qtbot.waitUntil(lambda: not w.running and idle(w), timeout=5000)
    assert w.skips == 1 and len(w.list_maker.articles) == 0
    assert w.current is None and w.editor.toPlainText() == ""


def test_skipped_pages_are_removed_and_the_loop_goes_on(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"نص": "نص", "مفقود": None, "قط": "حيوان [[أليف|أليف]]."})
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and idle(w), timeout=5000)
    assert w.skips == 2  # no change, non-existent
    assert [a.name for a in w.list_maker.articles] == ["قط"]


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
    assert [a.name for a in w.list_maker.articles] == ["قط"]
    assert w.start_button.isEnabled()


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
