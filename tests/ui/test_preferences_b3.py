"""Skip if no…, default summaries, the Alerts page and the remaining preferences in the window
(AWB SkipOptions.cs, SummaryEditor.cs, Preferences.cs)."""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from pyawb.settings.appconfig import AppConfig
from pyawb.settings.preferences import DEFAULT_SUMMARIES
from pyawb.ui.main_window import MainWindow
from pyawb.ui.option_dialogs import SkipIfNoDialog, SummaryEditorDialog
from pyawb.ui.options_panel import OptionsPanel
from pyawb.ui.settings_dialog import SettingsDialog
from tests.ui.test_main_loop import window


def test_skip_if_no_dialog(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    d = SkipIfNoDialog({1})
    qtbot.addWidget(d)
    assert d.value() == {1}
    d.check_all.setChecked(True)
    assert len(d.value()) == 10
    d.check_none.setChecked(True)
    assert d.value() == frozenset() and not d.check_all.isChecked()

    p = OptionsPanel()
    qtbot.addWidget(p)

    def choose(dialog: SkipIfNoDialog) -> int:
        dialog.list.item(6).setCheckState(Qt.CheckState.Checked)  # {{defaultsort}} added
        return 1

    monkeypatch.setattr(SkipIfNoDialog, "exec", choose)
    p.edit_skip_if_no()
    assert p.loop_options("x", "A").process.skip.skip_no_default_sort_added
    p.general_fixes.setChecked(False)
    assert not p.skip_if_no_button.isEnabled()


def test_summary_editor(qtbot: QtBot) -> None:
    d = SummaryEditorDialog(["zeta", "alpha"])
    qtbot.addWidget(d)
    d.sort()
    assert d.text.toPlainText() == "alpha\nzeta"
    d.text.setPlainText("one\n\n  two  \n")
    assert d.value() == ("one", "two")


def test_summaries_follow_the_wiki_language(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    items = [w.summary.itemText(i) for i in range(w.summary.count())]
    assert tuple(items) == DEFAULT_SUMMARIES  # no wiki yet: English
    aw, _ = window(qtbot, {"قط": "x"})  # Arabic Wikipedia: AWB's English list is not offered
    assert aw.summary.count() == 0

    def edit(dialog: SummaryEditorDialog) -> int:
        dialog.text.setPlainText("تنظيف\nتصنيف")
        return SummaryEditorDialog.DialogCode.Accepted

    monkeypatch.setattr(SummaryEditorDialog, "exec", edit)
    aw.edit_summaries()
    assert [aw.summary.itemText(i) for i in range(aw.summary.count())] == ["تنظيف", "تصنيف"]
    assert aw.config.preferences.custom_summaries


def test_settings_dialog_preferences_and_alerts(qtbot: QtBot) -> None:
    d = SettingsDialog(AppConfig(), page="alerts")
    qtbot.addWidget(d)
    assert d.chosen_alerts() == ()  # all on
    item = d.alerts.item(0)
    assert item is not None
    item.setCheckState(Qt.CheckState.Unchecked)
    d.autosave.setChecked(True)
    d.autosave_seconds.setValue(45)
    d.on_load.setCurrentIndex(d.on_load.findData("preview"))
    p = d.preferences()
    assert 1 not in p.alerts and len(p.alerts) == 21
    assert p.autosave_edit_box and p.autosave_seconds == 45
    assert p.on_load == "preview"


def test_alert_preferences_in_the_loop(qtbot: QtBot) -> None:
    w, t = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير."})
    w._save_preferences(  # pyright: ignore[reportPrivateUsage]
        replace(w.config.preferences, alerts=(17,))
    )
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    alerts = [w.start_tab.alerts.item(i).text() for i in range(w.start_tab.alerts.count())]
    assert not any("No category" in a for a in alerts)  # only unbalanced brackets chosen
    w.save()
    qtbot.waitUntil(lambda: w.edits == 1, timeout=5000)
    assert w.session is not None  # the tool tag stays on Wikimedia wikis, as in AWB
    assert t.last("edit")["summary"].endswith(w.session.site.summary_tag)


def test_timer_autosave_and_clear_list(qtbot: QtBot, private_home: Path) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير."})
    target = private_home / "box.txt"
    w._save_preferences(  # pyright: ignore[reportPrivateUsage]
        replace(
            w.config.preferences,
            show_timer=True,
            autosave_edit_box=True,
            autosave_seconds=5,
            autosave_file=str(target),
            clear_list_on_wiki_change=True,
        )
    )
    w.show()
    assert w.save_timer.isVisible() and w.autosave.active
    w.editor.setPlainText("نص محفوظ")
    w.autosave.save_now()
    assert target.read_text(encoding="utf-8") == "نص محفوظ"
    # another wiki: the list empties
    from tests.api.test_session import approved_session

    other, _ = approved_session()
    other.site = replace(other.site, url="https://he.wikipedia.org")
    assert len(w.list_maker.articles) == 1
    w.use_session(other)
    assert len(w.list_maker.articles) == 0
