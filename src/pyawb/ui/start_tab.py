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
"""AWB's Start tab: the edit summary, the loop's buttons, page statistics, alerts and Find.

Laid out as full-width horizontal bands (summary, actions, statistics, alerts, find), so the tab
works in the narrow control column.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyawb.api.models import WatchOptions
from pyawb.core.process import PageInfo

WATCH_CHOICES = (
    ("Don't change the watchlist", WatchOptions.NO_CHANGE),
    ("Add to watchlist", WatchOptions.WATCH),
    ("Remove from watchlist", WatchOptions.UNWATCH),
    ("Use preferences", WatchOptions.PREFERENCES),
)


class StartTab(QWidget):
    find_requested = Signal(str, bool, bool)  # text, regex, case sensitive

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("startTab")

        # -- summary band --
        self.summary = QComboBox(self)
        self.summary.setEditable(True)
        self.summary.setObjectName("summary")
        edit = self.summary.lineEdit()
        if edit is not None:
            edit.setPlaceholderText(self.tr("Default edit summary"))
        self.lock = QCheckBox(self.tr("Lock"), self)
        self.lock.setToolTip(self.tr("Keep the default summary from being changed"))
        self.lock.toggled.connect(lambda on: self.summary.setEnabled(not on))
        self.minor = QCheckBox(self.tr("Minor edit"), self)
        self.watch = QComboBox(self)
        for label, value in WATCH_CHOICES:
            self.watch.addItem(self.tr(label), value)
        summary_box = QGroupBox(self.tr("Default summary"), self)
        sb = QGridLayout(summary_box)
        sb.addWidget(self.summary, 0, 0, 1, 3)
        sb.addWidget(self.lock, 1, 0)
        sb.addWidget(self.minor, 1, 1)
        sb.setColumnStretch(2, 1)

        # -- actions band: Start, Stop | Preview, Diff | Skip, Save --
        self.start = QPushButton(self.tr("Start"), self)
        self.stop = QPushButton(self.tr("Stop"), self)
        self.preview = QPushButton(self.tr("Preview"), self)
        self.diff = QPushButton(self.tr("Diff"), self)
        self.skip = QPushButton(self.tr("Skip"), self)
        self.skip.setObjectName("skipButton")
        self.skip.setToolTip(self.tr("Skip this page and continue (Ctrl+I)"))
        self.save = QPushButton(self.tr("Save"), self)
        self.save.setObjectName("saveButton")
        self.save.setProperty("primary", True)
        self.save.setToolTip(self.tr("Save the changes and continue (Ctrl+S)"))
        actions = QGridLayout()
        for col, b in enumerate((self.start, self.stop, self.preview, self.diff)):
            actions.addWidget(b, 0, col)
        actions.addWidget(self.skip, 1, 0, 1, 2)
        actions.addWidget(self.save, 1, 2, 1, 2)
        for big in (self.skip, self.save):
            big.setMinimumHeight(36)

        # -- statistics band: three columns of two --
        stats = QGroupBox(self.tr("Page statistics"), self)
        self.stat_labels: dict[str, QLabel] = {}
        grid = QGridLayout(stats)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(2)
        for i, (key, label) in enumerate(
            (
                ("words", self.tr("Words:")),
                ("links", self.tr("Links:")),
                ("images", self.tr("Images:")),
                ("categories", self.tr("Categories:")),
                ("interwiki_links", self.tr("Interwiki links:")),
                ("dates", self.tr("Dates O/I/A:")),
            )
        ):
            value = QLabel(self)
            value.setObjectName("statValue")
            self.stat_labels[key] = value
            row, col = divmod(i, 3)
            grid.addWidget(QLabel(label, self), row, col * 2)
            grid.addWidget(value, row, col * 2 + 1)
        for col in (1, 3, 5):
            grid.setColumnStretch(col, 1)

        # -- alerts band: alerts | multiple wiki-links --
        alerts_box = QGroupBox(self.tr("Alerts"), self)
        self.alerts = QListWidget(alerts_box)
        self.alerts.setObjectName("alerts")
        al = QVBoxLayout(alerts_box)
        al.addWidget(self.alerts)
        self.links_box = QGroupBox(self.tr("Multiple wiki-links"), self)
        self.links_box.setObjectName("warningBox")
        self.links = QListWidget(self.links_box)
        ll = QVBoxLayout(self.links_box)
        ll.addWidget(self.links)
        self.links_label = self.links_box  # shown only when there are repeated links
        alerts = QHBoxLayout()
        alerts.addWidget(alerts_box, 3)
        alerts.addWidget(self.links_box, 2)
        rows = self.fontMetrics().lineSpacing()
        for lw in (self.alerts, self.links):
            lw.setWordWrap(True)  # long alerts wrap instead of scrolling sideways
            lw.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            lw.setMinimumHeight(rows * 6 + 8)  # and they grow with the tab

        # -- find band --
        find = QGroupBox(self.tr("Find"), self)
        self.find_text = QLineEdit(find)
        self.find_regex = QCheckBox(self.tr("Regex"), find)
        self.find_case = QCheckBox(self.tr("Case sensitive"), find)
        self.find_button = QPushButton(self.tr("Find"), find)
        self.find_button.clicked.connect(self._find)
        self.find_text.returnPressed.connect(self._find)
        # the text on its own full-width row; the options and the button below it
        fl = QGridLayout(find)
        fl.addWidget(self.find_text, 0, 0, 1, 4)
        fl.addWidget(self.find_regex, 1, 0)
        fl.addWidget(self.find_case, 1, 1)
        fl.addWidget(self.find_button, 1, 3)
        fl.setColumnStretch(2, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(summary_box)
        layout.addLayout(actions)
        layout.addWidget(stats)
        layout.addLayout(alerts, 1)  # the alerts take the spare height
        layout.addWidget(find)
        layout.addWidget(self.watch)  # the watchlist choice at the bottom, full width
        self.set_page_info(None)

    def set_page_info(self, info: PageInfo | None) -> None:
        """Show a page's statistics and alerts (None: clear, as AWB's ArticleInfo(reset))."""
        s = info.statistics if info is not None else None
        for key, label in self.stat_labels.items():
            label.setText("–" if s is None else str(getattr(s, key)))
        self.alerts.clear()
        self.links.clear()
        if info is not None:
            self.alerts.addItems(list(info.alerts))
            self.links.addItems(list(info.multiple_wikilinks))
        self.links_box.setVisible(bool(info and info.multiple_wikilinks))

    def remember_summary(self) -> None:
        text = self.summary.currentText().strip()
        if text and self.summary.findText(text) < 0:
            self.summary.insertItem(0, text)

    def _find(self) -> None:
        if self.find_text.text():
            self.find_requested.emit(
                self.find_text.text(), self.find_regex.isChecked(), self.find_case.isChecked()
            )
