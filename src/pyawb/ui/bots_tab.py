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
# After AutoWikiBrowser AWB/Main.cs (tpBots, DelayedAutoSave, NudgeTimer_Tick, Shutdown),
# AWB/NudgeTimer.cs and AWB/ShutdownNotification.cs (GPL-2.0-or-later).
"""The Bots tab (auto save with a delay, max edits, the nudge timer, auto shutdown), the timers
behind it and the shutdown countdown. The rules are pyawb.botmode's."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyawb import botmode
from pyawb.botmode import BotSettings, Countdown, Nudger, PowerAction


class BotsTab(QWidget):
    """AWB's tpBots. auto_save_toggled: bot mode turned on or off."""

    auto_save_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("botsTab")
        self.auto_save = QCheckBox(self.tr("&Auto save"), self)
        self.auto_save.setToolTip(self.tr("Automatically save all edits"))
        self.delay = QSpinBox(self)
        self.delay.setRange(0, botmode.MAX_DELAY)
        self.delay.setValue(botmode.DEFAULT_DELAY)
        self.delay.setSuffix(self.tr(" s"))
        self.delay.setToolTip(self.tr("Time in seconds between saves (maximum 99)"))
        self.max_edits = QSpinBox(self)
        self.max_edits.setRange(0, botmode.MAX_EDITS)
        self.max_edits.setSpecialValueText(self.tr("No limit"))
        self.max_edits.setToolTip(self.tr("Stop when the edit count reaches this number"))
        self.suppress_tag = QCheckBox(self.tr('Suppress "using AWB" in edit summary'), self)
        self.suppress_tag.setToolTip(
            self.tr("Removes the automatic addition of the AWB suffix to edit summaries")
        )
        self.delay_label = QLabel(self.tr("&Delay"), self)
        self.delay_label.setBuddy(self.delay)
        self.max_edits_label = QLabel(self.tr("Max edits"), self)
        self.max_edits_label.setBuddy(self.max_edits)

        nudge_box = QGroupBox(self.tr("Nudge timer"), self)
        self.nudge = QCheckBox(self.tr('Resave ("nudge") if stuck'), nudge_box)
        self.nudge.setToolTip(
            self.tr(
                "If checked, the page is started again when it is stuck: first after 2 minutes, "
                "then in longer intervals"
            )
        )
        self.nudge_skip = QCheckBox(self.tr("Skip page if first nudge doesn't help"), nudge_box)
        self.nudge_skip.setToolTip(self.tr("Limits the nudges to one per page"))
        self.nudges_label = QLabel(nudge_box)
        self.reset_nudges = QPushButton(self.tr("Reset counter"), nudge_box)
        self.reset_nudges.setToolTip(self.tr("Reset the nudge counter to zero"))
        nl = QGridLayout(nudge_box)
        nl.addWidget(self.nudge, 0, 0, 1, 2)
        nl.addWidget(self.nudge_skip, 1, 0, 1, 2)
        nl.addWidget(self.nudges_label, 2, 0)
        nl.addWidget(self.reset_nudges, 2, 1)
        nl.setColumnStretch(0, 1)

        shutdown_box = QGroupBox(self.tr("Shutdown"), self)
        self.shutdown = QCheckBox(self.tr("Auto shutdown"), shutdown_box)
        self.shutdown.setToolTip(
            self.tr("Automatically shut down the computer when the list is done")
        )
        self.power_group = QButtonGroup(shutdown_box)
        self.power_buttons: dict[PowerAction, QRadioButton] = {}
        sl = QGridLayout(shutdown_box)
        sl.addWidget(self.shutdown, 0, 0, 1, 2)
        names = {
            PowerAction.SHUTDOWN: self.tr("Shutdown"),
            PowerAction.STANDBY: self.tr("Standby"),
            PowerAction.RESTART: self.tr("Restart"),
            PowerAction.HIBERNATE: self.tr("Hibernate"),
        }
        for i, action in enumerate(PowerAction):
            b = QRadioButton(names[action], shutdown_box)
            self.power_group.addButton(b)
            self.power_buttons[action] = b
            sl.addWidget(b, 1 + i // 2, i % 2)
        self.power_buttons[PowerAction.SHUTDOWN].setChecked(True)

        top = QGridLayout()
        top.addWidget(self.auto_save, 0, 0, 1, 2)
        top.addWidget(self.delay_label, 1, 0)
        top.addWidget(self.delay, 1, 1)
        top.addWidget(self.max_edits_label, 2, 0)
        top.addWidget(self.max_edits, 2, 1)
        top.addWidget(self.suppress_tag, 3, 0, 1, 3)
        top.setColumnStretch(2, 1)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        row = QHBoxLayout()
        row.addWidget(nudge_box, 1)
        row.addWidget(shutdown_box, 1)
        lay.addLayout(row)
        lay.addStretch(1)

        self.auto_save.toggled.connect(self._auto_save_toggled)
        self.shutdown.toggled.connect(self._enable_shutdown)
        self.show_nudges(0)
        self._enable(False)

    def _auto_save_toggled(self, on: bool) -> None:
        """chkAutoMode_CheckedChanged: the bot controls follow; nudging on, skipping off."""
        self._enable(on)
        if on:
            self.nudge.setChecked(True)
            self.nudge_skip.setChecked(False)
        self.auto_save_toggled.emit(on)

    def _enable(self, on: bool) -> None:
        """SetBotModeEnabled (AWB also unticks "nudge" when bot mode goes off)."""
        for w in (self.delay, self.delay_label, self.max_edits, self.max_edits_label,
                  self.nudge, self.nudge_skip, self.nudges_label, self.reset_nudges,
                  self.shutdown):  # fmt: skip
            w.setEnabled(on)
        if not on:
            self.shutdown.setChecked(False)
        self._enable_shutdown(on and self.shutdown.isChecked())

    def _enable_shutdown(self, on: bool) -> None:
        for b in self.power_buttons.values():
            b.setEnabled(on)

    def show_nudges(self, total: int) -> None:
        self.nudges_label.setText(self.tr("Total nudges: %1").replace("%1", str(total)))

    def settings(self) -> BotSettings:
        action = next(a for a, b in self.power_buttons.items() if b.isChecked())
        return BotSettings(
            auto_save=self.auto_save.isChecked(),
            delay=self.delay.value(),
            max_edits=self.max_edits.value(),
            suppress_tag=self.suppress_tag.isChecked(),
            nudge=self.nudge.isChecked(),
            nudge_skip=self.nudge_skip.isChecked(),
            shutdown=self.shutdown.isChecked(),
            shutdown_action=action,
        )


class BotTimers(QObject):
    """The two clocks of bot mode: the auto-save countdown (one tick a second, AWB's Ticker)
    and the nudge timer. tick: seconds counted so far; save_due: time to save; nudge_due: the
    page has been stuck for the nudge interval."""

    tick = Signal(int)
    save_due = Signal()
    nudge_due = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.nudger = Nudger()
        self.countdown: Countdown | None = None
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick)
        self._nudge = QTimer(self)
        self._nudge.setSingleShot(True)
        self._nudge.timeout.connect(self.nudge_due.emit)

    @property
    def counting(self) -> bool:
        return self.countdown is not None

    def start_countdown(self, delay: int) -> None:
        """StartDelayedAutoSaveTimer."""
        self.countdown = Countdown(delay)
        self.tick.emit(0)
        self._clock.start()

    def stop_countdown(self) -> None:
        """StopDelayedAutoSaveTimer."""
        self._clock.stop()
        self.countdown = None
        self.tick.emit(0)

    def _tick(self) -> None:
        countdown = self.countdown
        if countdown is None:
            return
        if countdown.tick():
            self.stop_countdown()
            self.save_due.emit()
            return
        self.tick.emit(countdown.elapsed)

    @property
    def nudging(self) -> bool:
        return self._nudge.isActive()

    def start_nudge(self) -> None:
        """NudgeTimer.StartMe: when a page is started."""
        self._nudge.start(self.nudger.interval * 1000)

    def page_loaded(self) -> None:
        """NudgeTimer.Reset after a good load: the next nudge is 2 minutes away again."""
        self.nudger.reset_interval()
        if self._nudge.isActive():
            self._nudge.start(self.nudger.interval * 1000)

    def stop_nudge(self) -> None:
        self._nudge.stop()

    def stop(self) -> None:
        self.stop_countdown()
        self.stop_nudge()


class ShutdownDialog(QDialog):
    """ShutdownNotification: two minutes to cancel; at zero the dialog accepts by itself."""

    def __init__(
        self,
        action: PowerAction,
        seconds: int = botmode.SHUTDOWN_COUNTDOWN,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.remaining = seconds
        names = {
            PowerAction.SHUTDOWN: self.tr("Shutdown"),
            PowerAction.STANDBY: self.tr("Standby"),
            PowerAction.RESTART: self.tr("Restart"),
            PowerAction.HIBERNATE: self.tr("Hibernate"),
        }
        self.action_name = names[action]
        self.setWindowTitle(self.action_name)
        prompt = QLabel(
            self.tr("The list is done. The computer will now %1. Press Cancel to stop it.").replace(
                "%1", self.action_name.lower()
            ),
            self,
        )
        prompt.setWordWrap(True)
        self.timer_label = QLabel(self)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(prompt)
        lay.addWidget(self.timer_label)
        lay.addWidget(buttons)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._show()

    def _show(self) -> None:
        self.timer_label.setText(
            self.tr("Time until %1: %2")
            .replace("%1", self.action_name)
            .replace("%2", str(self.remaining))
        )

    def _tick(self) -> None:
        self.remaining -= 1
        if self.remaining <= 0:
            self._timer.stop()
            self.accept()
            return
        self._show()
