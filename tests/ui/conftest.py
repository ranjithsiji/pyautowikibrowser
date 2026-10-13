"""UI tests: a private settings directory, and message boxes recorded instead of shown."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QMessageBox


@pytest.fixture(autouse=True)
def private_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PYAWB_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def message_boxes(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, str]]]:
    """Modal boxes would block a headless test: record (kind, text) and answer No."""
    shown: list[tuple[str, str]] = []

    def record(kind: str, answer: Any = QMessageBox.StandardButton.Ok) -> Any:
        def box(_parent: Any, _title: str, text: str, *args: Any, **kwargs: Any) -> Any:
            shown.append((kind, text))
            return answer

        return box

    monkeypatch.setattr(QMessageBox, "warning", record("warning"))
    monkeypatch.setattr(QMessageBox, "information", record("information"))
    monkeypatch.setattr(QMessageBox, "question", record("question", QMessageBox.StandardButton.No))
    yield shown
