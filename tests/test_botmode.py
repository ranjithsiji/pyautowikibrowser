"""Bot mode's rules (AWB Main.cs DelayedAutoSave, NudgeTimer.cs, NudgeTimer_Tick, Shutdown)."""

from pyawb import botmode
from pyawb.botmode import BotSettings, Countdown, NudgeAction, Nudger, PowerAction


def test_countdown_counts_up_to_the_delay_then_saves() -> None:
    c = Countdown(2)
    assert [c.tick(), c.tick(), c.tick()] == [False, False, True]
    assert c.elapsed == 2
    assert Countdown(0).tick()  # no delay: the first tick saves
    assert Countdown(500).delay == botmode.MAX_DELAY


def test_max_edits() -> None:
    assert not BotSettings().edits_reached(10_000)  # 0: no limit
    assert not BotSettings(max_edits=3).edits_reached(2)
    assert BotSettings(max_edits=3).edits_reached(3)


def test_nudge_intervals_grow_and_reset() -> None:
    n = Nudger()
    seen = [n.interval]
    for _ in range(4):
        n.nudge(skip_if_nudged=False)
        seen.append(n.interval)
    assert seen == [120, 240, 360, 600, 600]
    n.reset_interval()
    assert n.interval == 120 and n.total == 4


def test_second_nudge_on_a_page_skips_it() -> None:
    n = Nudger()
    assert n.nudge(skip_if_nudged=True) is NudgeAction.RETRY
    assert n.nudge(skip_if_nudged=True) is NudgeAction.SKIP
    assert n.nudge(skip_if_nudged=True) is NudgeAction.RETRY  # the next page
    n.page_done()
    assert n.nudge(skip_if_nudged=True) is NudgeAction.RETRY
    # without the option every nudge retries
    m = Nudger()
    assert {m.nudge(False), m.nudge(False)} == {NudgeAction.RETRY}
    m.reset_counter()
    assert m.total == m.same_page == 0


def test_power_commands() -> None:
    assert botmode.power_command(PowerAction.SHUTDOWN, "linux") == ["systemctl", "poweroff"]
    assert botmode.power_command(PowerAction.HIBERNATE, "linux") == ["systemctl", "hibernate"]
    assert botmode.power_command(PowerAction.RESTART, "win32") == ["shutdown", "/r", "/t", "0"]
    assert botmode.power_command(PowerAction.STANDBY, "win32")[0] == "rundll32.exe"
    assert botmode.power_command(PowerAction.STANDBY, "darwin") == ["pmset", "sleepnow"]
    assert "shut down" in botmode.power_command(PowerAction.SHUTDOWN, "darwin")[-1]
