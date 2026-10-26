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
"""Run blocking work (API calls, page processing) off the UI thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal

_running: set[_Signals] = set()  # keep the signal objects alive until delivered
_low_priority = False


def set_low_priority(on: bool) -> None:
    """Preferences ▸ Low priority: background work runs in low-priority threads (AWB lowered its
    main thread's priority)."""
    global _low_priority
    _low_priority = on


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any], signals: _Signals) -> None:
        super().__init__()
        self.fn, self.signals = fn, signals

    def run(self) -> None:
        thread = QThread.currentThread()
        if thread is not None:
            thread.setPriority(
                QThread.Priority.LowPriority if _low_priority else QThread.Priority.NormalPriority
            )
        try:
            result = self.fn()
        except Exception as e:  # reported to the UI, never lost in the worker
            self.signals.failed.emit(e)
        else:
            self.signals.done.emit(result)


def run_task(
    fn: Callable[[], Any],
    on_done: Callable[[Any], None],
    on_error: Callable[[Exception], None],
    pool: QThreadPool | None = None,
) -> None:
    """Run fn() in the thread pool; on_done(result) or on_error(exception) then runs on the UI
    thread (the signals object lives there, so the connections are queued)."""
    signals = _Signals()
    _running.add(signals)

    def finish(callback: Callable[[Any], None], value: Any) -> None:
        _running.discard(signals)
        callback(value)

    signals.done.connect(lambda r: finish(on_done, r))
    signals.failed.connect(lambda e: finish(on_error, e))
    (pool or QThreadPool.globalInstance()).start(_Task(fn, signals))
