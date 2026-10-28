# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser AWB/Main.cs (bot mode: DelayedAutoSave, NudgeTimer_Tick, Shutdown),
# AWB/NudgeTimer.cs (Stephen Kennedy) and AWB/ShutdownNotification.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Bot mode without the UI: the Bots tab's settings, the auto-save countdown, the "nudge"
schedule that restarts a stuck page, and the command that shuts the computer down at the end.

Only accounts the CheckPage lists as bots (WikiSession.is_bot) may use it; ui/ shows the Bots
tab only for them.
"""

from __future__ import annotations

import enum
import sys
from dataclasses import dataclass

MAX_DELAY = 99  # nudBotSpeed.Maximum: seconds between saves
DEFAULT_DELAY = 10
MAX_EDITS = 5000  # botEditsStop.Maximum; 0 = no limit
SHUTDOWN_COUNTDOWN = 120  # ShutdownNotification: two minutes to cancel

# NudgeTimer: the first nudge after 2 minutes, then 4, 6 and from then on every 10
NUDGE_INTERVALS = (120, 240, 360, 600)


class PowerAction(enum.Enum):
    """The Bots tab's Shutdown choices."""

    SHUTDOWN = "Shutdown"
    STANDBY = "Standby"
    RESTART = "Restart"
    HIBERNATE = "Hibernate"


@dataclass(frozen=True)
class BotSettings:
    """The Bots tab. auto_save: AWB's "Auto save" (chkAutoMode, i.e. bot mode itself)."""

    auto_save: bool = False
    delay: int = DEFAULT_DELAY  # seconds between a page being ready and its save
    max_edits: int = 0  # stop after this many edits (0: no limit)
    suppress_tag: bool = False  # leave "using AWB" out of edit summaries
    nudge: bool = True  # resave ("nudge") if stuck
    nudge_skip: bool = False  # skip the page if the first nudge doesn't help
    shutdown: bool = False
    shutdown_action: PowerAction = PowerAction.SHUTDOWN

    def edits_reached(self, edits: int) -> bool:
        """DelayedAutoSave's stop: the session's edit count reached "Max edits"."""
        return self.max_edits > 0 and edits >= self.max_edits


class Countdown:
    """DelayedAutoSave: one tick a second, counting up to the delay; the tick after that saves.
    tick() returns True when it is time to save."""

    def __init__(self, delay: int) -> None:
        self.delay = max(0, min(delay, MAX_DELAY))
        self.elapsed = 0  # AWB's _intTimer, shown as "Bot timer: n"

    def tick(self) -> bool:
        if self.elapsed < self.delay:
            self.elapsed += 1
            return False
        return True


class NudgeAction(enum.Enum):
    RETRY = "retry"  # stop and start the same page again
    SKIP = "skip"  # skip the page: a nudge already failed on it


class Nudger:
    """NudgeTimer and NudgeTimer_Tick: when a page has been loading or saving for too long, start
    it again; with nudge_skip, a second nudge on the same page skips it instead."""

    def __init__(self) -> None:
        self.total = 0  # "Total nudges"
        self.same_page = 0  # SameArticleNudges
        self._step = 0  # index into NUDGE_INTERVALS

    @property
    def interval(self) -> int:
        """Seconds until the next nudge."""
        return NUDGE_INTERVALS[self._step]

    def reset_interval(self) -> None:
        """NudgeTimer.Reset: a page loaded fine, so the next nudge is 2 minutes away again."""
        self._step = 0

    def page_done(self) -> None:
        """Saved or skipped: the page's nudges no longer count (SameArticleNudges = 0)."""
        self.same_page = 0
        self._step = 0

    def reset_counter(self) -> None:
        """btnResetNudges."""
        self.total = self.same_page = 0

    def nudge(self, skip_if_nudged: bool) -> NudgeAction:
        """The timer ran out: count it, lengthen the next interval, say what to do."""
        self.total += 1
        self._step = min(self._step + 1, len(NUDGE_INTERVALS) - 1)
        if skip_if_nudged and self.same_page > 0:
            self.same_page = 0
            return NudgeAction.SKIP
        self.same_page += 1
        return NudgeAction.RETRY


NUDGE_SKIP_REASON = "There was an error saving the page twice"


def power_command(action: PowerAction, platform: str = sys.platform) -> list[str]:
    """ShutdownComputer, for each OS: the command that shuts down, restarts, suspends or
    hibernates without asking (the user had two minutes to cancel). macOS has no separate
    hibernate command: it sleeps, and hibernates by its own power settings."""
    if platform.startswith("win"):
        return {
            PowerAction.SHUTDOWN: ["shutdown", "/s", "/t", "0"],
            PowerAction.RESTART: ["shutdown", "/r", "/t", "0"],
            PowerAction.HIBERNATE: ["shutdown", "/h"],
            PowerAction.STANDBY: ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        }[action]
    if platform == "darwin":
        if action in (PowerAction.STANDBY, PowerAction.HIBERNATE):
            return ["pmset", "sleepnow"]
        verb = "shut down" if action is PowerAction.SHUTDOWN else "restart"
        return ["osascript", "-e", f'tell application "System Events" to {verb}']
    # Linux and other systemd systems
    return [
        "systemctl",
        {
            PowerAction.SHUTDOWN: "poweroff",
            PowerAction.RESTART: "reboot",
            PowerAction.STANDBY: "suspend",
            PowerAction.HIBERNATE: "hibernate",
        }[action],
    ]
