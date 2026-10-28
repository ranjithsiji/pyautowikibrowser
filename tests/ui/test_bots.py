"""The Bots tab: auto save with a delay, max edits, suppress the tag, the nudge timer and auto
shutdown, for accounts the CheckPage lists as bots (AWB Main.cs bot mode)."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from pyawb import botmode
from pyawb.lists.listmaker import ArticleList
from pyawb.ui import main_window
from pyawb.ui.bots_tab import ShutdownDialog
from pyawb.ui.main_window import MainWindow
from tests.api.fakes import userinfo
from tests.ui.test_main_loop import idle, statuses, window

TEXT = "حيوان [[أليف|أليف]] صغير."


def bot_window(
    qtbot: QtBot, pages: dict[str, str | None] | None = None, delay: int = 0
) -> tuple[MainWindow, Any]:
    w, t = window(qtbot, pages or {"قط": TEXT, "كلب": TEXT})
    s = w.session
    assert s is not None and s.status is not None
    t.responses[("meta", "userinfo")] = userinfo("Alice", groups=("user", "bot"))
    s.refresh_user()
    s.status = replace(s.status, is_bot=True)  # listed in the CheckPage's enabledbots
    w._update_bot_status()  # pyright: ignore[reportPrivateUsage]
    w.bots_tab.auto_save.setChecked(True)
    w.bots_tab.delay.setValue(delay)
    return w, t


def test_tab_only_for_checkpage_bots(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": TEXT})
    assert w.options.indexOf(w.bots_tab) < 0 and not w.bot_mode
    w, _ = bot_window(qtbot)
    assert w.options.indexOf(w.bots_tab) == w.options.indexOf(w.start_tab) - 1
    assert w.bot_mode and w.bots_tab.nudge.isChecked() and w.bots_tab.delay.isEnabled()
    w.bots_tab.auto_save.setChecked(False)
    assert not w.bots_tab.delay.isEnabled() and not w.bots_tab.shutdown.isEnabled()


def test_auto_save_runs_the_list(qtbot: QtBot) -> None:
    w, t = bot_window(qtbot)
    w.show()
    w.start()
    qtbot.waitUntil(lambda: not w.running and idle(w), timeout=10000)
    assert w.edits == 2 and statuses(w) == [ArticleList.SAVED, ArticleList.SAVED]
    assert t.last("edit")["summary"].startswith("/* top */ تنظيف")
    assert not w.diff.isVisible()  # no diff in bot mode unless asked for
    assert w.bot_timer_label.isVisible()
    assert w.status_label.text() == "List complete!"


def test_max_edits_and_suppressed_tag(qtbot: QtBot) -> None:
    w, t = bot_window(qtbot)
    w.bots_tab.max_edits.setValue(1)
    w.bots_tab.suppress_tag.setChecked(True)
    w.start()
    qtbot.waitUntil(lambda: w.edits == 1 and not w.running and idle(w), timeout=10000)
    assert statuses(w) == [ArticleList.SAVED, ""]
    assert w.status_label.text() == "Stopped: 1 edits reached"
    assert t.last("edit")["summary"] == "/* top */ تنظيف"  # no "using AWB"


def test_stop_during_the_countdown_keeps_the_page(qtbot: QtBot) -> None:
    w, _ = bot_window(qtbot, delay=99)
    w.start()
    qtbot.waitUntil(lambda: w.bot_timers.counting and idle(w), timeout=5000)
    w.user_stop()
    assert not w.bot_timers.counting and not w.running and w.current is not None
    assert w.save_button.isEnabled()  # to save or skip by hand


def test_nudge_restarts_then_skips(qtbot: QtBot) -> None:
    w, _ = bot_window(qtbot, delay=99)
    w.bots_tab.nudge_skip.setChecked(True)
    w.start()
    qtbot.waitUntil(lambda: w.bot_timers.counting and idle(w), timeout=5000)
    w._nudge()  # pyright: ignore[reportPrivateUsage]
    qtbot.waitUntil(lambda: w.bot_timers.counting and idle(w), timeout=5000)
    assert w.current_index == 0 and w.bots_tab.nudges_label.text() == "Total nudges: 1"
    w._nudge()  # pyright: ignore[reportPrivateUsage]
    qtbot.waitUntil(lambda: w.current_index == 1 and idle(w), timeout=5000)
    assert statuses(w)[0] == ArticleList.SKIPPED
    assert w.logs.skipped.rows()[0][3] == botmode.NUDGE_SKIP_REASON
    w.bots_tab.reset_nudges.click()
    assert w.bots_tab.nudges_label.text() == "Total nudges: 0"


def test_late_results_of_an_abandoned_step_are_dropped(qtbot: QtBot) -> None:
    w, _ = bot_window(qtbot)
    got: list[object] = []
    late = w._this_step(got.append)  # pyright: ignore[reportPrivateUsage]
    w._generation += 1  # pyright: ignore[reportPrivateUsage]
    late("result")
    assert got == []


def test_typo_fixing_is_not_for_bots(qtbot: QtBot, message_boxes: list[tuple[str, str]]) -> None:
    w, _ = bot_window(qtbot)
    w.bots_tab.auto_save.setChecked(False)
    w.options.fix_typos.blockSignals(True)
    w.options.fix_typos.setChecked(True)
    w.options.fix_typos.blockSignals(False)
    w.bots_tab.auto_save.setChecked(True)
    assert not w.options.fix_typos.isChecked() and message_boxes


@pytest.mark.parametrize("accept", [True, False])
def test_auto_shutdown(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    message_boxes: list[tuple[str, str]],
    accept: bool,
) -> None:
    ran: list[list[str]] = []
    monkeypatch.setattr(main_window, "subprocess", SimpleNamespace(Popen=ran.append))
    monkeypatch.setattr(
        ShutdownDialog,
        "exec",
        lambda _d: ShutdownDialog.DialogCode.Accepted if accept else 0,
    )
    w, _ = bot_window(qtbot, {"قط": TEXT})
    w.bots_tab.shutdown.setChecked(True)
    w.bots_tab.power_buttons[botmode.PowerAction.RESTART].setChecked(True)
    w.start()
    qtbot.waitUntil(lambda: w.edits == 1 and not w.running and idle(w), timeout=10000)
    if accept:
        qtbot.waitUntil(lambda: bool(ran), timeout=5000)
        assert ran == [botmode.power_command(botmode.PowerAction.RESTART)]
    else:
        qtbot.waitUntil(lambda: bool(message_boxes), timeout=5000)
        assert ran == [] and "aborted" in message_boxes[-1][1]


def test_shutdown_dialog_counts_down(qtbot: QtBot) -> None:
    d = ShutdownDialog(botmode.PowerAction.STANDBY, seconds=2)
    qtbot.addWidget(d)
    assert d.timer_label.text() == "Time until Standby: 2"
    d._tick()  # pyright: ignore[reportPrivateUsage]
    assert d.timer_label.text() == "Time until Standby: 1"
    d._tick()  # pyright: ignore[reportPrivateUsage]
    assert d.result() == ShutdownDialog.DialogCode.Accepted
