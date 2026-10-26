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
# After AutoWikiBrowser AWB/Main.cs (lblTimer, lblUserNotifications, EditBoxSaveTimer, ntfyTray)
# (GPL-2.0-or-later).
"""Main window extras that follow the preferences: the save timer and notification count in
the status bar, the edit box's auto-save, and the notification-area icon."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMenu, QSystemTrayIcon, QWidget

from pyawb.ui.icons import codex_icon


class SaveTimer(QLabel):
    """AWB's "Timer: n": seconds since the last save started (Preferences ▸ show timer)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("saveTimer")
        self.seconds = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._show()
        self.hide()

    def _tick(self) -> None:
        self.seconds += 1
        self._show()

    def _show(self) -> None:
        self.setText(self.tr("Timer: %1").replace("%1", str(self.seconds)))

    def restart(self) -> None:
        """A save started: count from 0 (SaveArticle's StopSaveInterval + Ticker)."""
        self.seconds = 0
        self._show()
        if self.isVisible():
            self._timer.start()

    def set_enabled(self, on: bool) -> None:
        self.setVisible(on)
        if not on:
            self._timer.stop()
            self.seconds = 0
            self._show()


class NotificationsLabel(QLabel):
    """AWB's lblUserNotifications: the user's unread notifications, red when there are some."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("notifications")
        self.show_count(0)

    def show_count(self, count: int) -> None:
        self.setText(str(count))
        self.setToolTip(self.tr("%n unread notification(s)", "", count))
        self.setProperty("unread", count > 0)
        self.style().unpolish(self)
        self.style().polish(self)


class EditBoxAutosave(QObject):
    """Preferences ▸ save the edit box to a file every n seconds (EditBoxSaveTimer)."""

    def __init__(self, text: Callable[[], str], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self.path: Path | None = None
        self.error = ""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.save_now)

    def configure(self, on: bool, seconds: int, path: Path) -> None:
        self.path = path if on else None
        if on:
            self._timer.start(seconds * 1000)
        else:
            self._timer.stop()

    @property
    def active(self) -> bool:
        return self._timer.isActive()

    def save_now(self) -> None:
        text = self._text()
        if self.path is None or not text:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(text, encoding="utf-8")
            self.error = ""
        except OSError as e:  # reported once in the status bar, never a dialog every n seconds
            self.error = str(e)


class TrayIcon(QSystemTrayIcon):
    """Minimize to the notification area: Show / Hide / Exit (AWB's mnuNotify)."""

    def __init__(self, window: QWidget, quit_app: Callable[[], object]) -> None:
        super().__init__(codex_icon("logoWikipedia"), window)
        self.window = window
        self.setToolTip("PyAutoWikiBrowser")
        menu = QMenu(window)
        self.show_action = QAction(self.tr("Show"), menu)
        self.show_action.triggered.connect(self.restore)
        self.hide_action = QAction(self.tr("Hide"), menu)
        self.hide_action.triggered.connect(window.hide)
        exit_action = QAction(self.tr("Exit"), menu)
        exit_action.triggered.connect(lambda _=False: quit_app())
        menu.addActions([self.show_action, self.hide_action])
        menu.addSeparator()
        menu.addAction(exit_action)
        self.setContextMenu(menu)
        self.activated.connect(self._activated)

    def _activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.restore()

    def restore(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()
