"""The Disambig tab and the disambiguation dialog in the edit loop (AWB DabForm/DabControl)."""

from collections.abc import Mapping
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from pyawb.rules import disambiguation as dab
from pyawb.ui.disambig_dialog import ABORTED, DisambigDialog
from tests.ui.test_main_loop import window

TEXT = "حيوان [[أليف|أليف]] و[[قط]] صغير."


def dialog(qtbot: QtBot) -> DisambigDialog:
    links = dab.find_links("The [[Mercury]] rises.", "Mercury", 10)
    d = DisambigDialog(
        "X", links, ["Mercury (planet)"], open_page=lambda: None, edit_page=lambda: None
    )
    qtbot.addWidget(d)
    return d


def test_rows_choices_and_buttons(qtbot: QtBot) -> None:
    d = dialog(qtbot)
    row = d.rows[0]
    assert row.no_change and d.results() == [None]
    row.choice.setCurrentIndex(3)
    assert row.correction.text() == "[[Mercury (planet)|Mercury]]"
    assert row.flip_button.isEnabled()
    row.unpipe_button.click()
    assert d.results() == ["[[Mercury (planet)]]"]
    row.correction.setText("")
    assert not d.done_button.isEnabled()  # an empty result cannot be saved
    row.undo()
    assert row.correction.text() == "[[Mercury (planet)|Mercury]]"
    row.reset()
    assert row.no_change


def setup(qtbot: QtBot, skip: bool = False) -> Any:
    w, t = window(qtbot, {"كلب": TEXT})  # not the page قط: a self-link becomes bold
    o = w.options
    o.dab_enabled.setChecked(True)
    o.dab_link.setText("قط")
    o.set_dab_variants(["قط (حيوان)", "قط (توضيح)"])
    o.dab_skip.setChecked(skip)
    return w, t


def test_done_applies_the_choice(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, _ = setup(qtbot)

    def choose(d: DisambigDialog) -> int:
        d.rows[0].choice.setCurrentIndex(3)
        return DisambigDialog.DialogCode.Accepted

    monkeypatch.setattr(DisambigDialog, "exec", choose)
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]] و[[قط (حيوان)|قط]] صغير."
    assert w.current is not None and w.current.article is not None


def test_cancel_with_skip(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, _ = setup(qtbot, skip=True)
    monkeypatch.setattr(DisambigDialog, "exec", lambda d: DisambigDialog.DialogCode.Rejected)
    w.start()
    qtbot.waitUntil(lambda: w.skips == 1, timeout=5000)
    assert w.logs.skipped.rows()[0][3] == "No disambiguation"


def test_abort_stops_the_run(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w, _ = setup(qtbot)
    monkeypatch.setattr(DisambigDialog, "exec", lambda d: ABORTED)
    w.start()
    qtbot.waitUntil(lambda: not w.running and not w.busy, timeout=5000)
    assert w.skips == 0 and w.edits == 0


def test_load_links(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "x"})

    def handler(p: Mapping[str, str]) -> Mapping[str, Any]:
        links = [{"ns": 0, "title": "قط (حيوان)"}, {"ns": 0, "title": "1999"}]
        return {"query": {"pages": [{"title": "قط (توضيح)", "links": links}]}}

    t.handler = handler
    w.load_dab_links("قط (توضيح)")
    qtbot.waitUntil(lambda: bool(w.options.dab_variants.toPlainText()), timeout=5000)
    assert w.options.dab_variants.toPlainText() == "قط (حيوان)"  # the year is left out
