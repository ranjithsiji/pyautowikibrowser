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
"""The information bar above the toolbar: which wiki, which user (or why not logged in), whether
the CheckPage allows saving, and the mode."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from pyawb.ui.icons import codex_icon

PROJECT_LOGOS = {
    "wikipedia": "logoWikipedia",
    "wiktionary": "logoWiktionary",
    "wikisource": "logoWikisource",
    "wikiquote": "logoWikiquote",
    "wikibooks": "logoWikibooks",
    "wikinews": "logoWikinews",
    "wikiversity": "logoWikiversity",
    "wikivoyage": "logoWikivoyage",
    "commons": "logoWikimediaCommons",
    "meta": "logoMetaWiki",
    "wikidata": "logoWikidata",
    "species": "logoWikispecies",
    "mediawiki": "logoMediaWiki",
}


@dataclass(frozen=True)
class Info:
    """What the bar shows (built by the main window from its session and mode)."""

    project: str = ""  # "wikipedia", "custom"…
    wiki: str = ""  # "Wikipedia (ml.wikipedia.org)"; "" when not connected
    user: str = ""  # logged-in user name; "" when not logged in
    user_groups: str = ""  # "bot, admin"
    approved: bool | None = None  # CheckPage: None when not checked (not logged in)
    approval_note: str = ""
    mode_icon: str = "eye"
    mode: str = ""


class _Chip(QWidget):
    """An icon and a text, coloured by state (good / warn / bad / neutral) in the stylesheet."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("infoChip")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)  # draw the QSS background
        self.icon = QLabel(self)
        self.text = QLabel(self)
        self.text.setObjectName("infoChipText")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 10, 2)
        layout.setSpacing(6)
        layout.addWidget(self.icon)
        layout.addWidget(self.text)

    def set(self, icon: str, text: str, state: str = "neutral", tip: str = "") -> None:
        self.icon.setPixmap(codex_icon(icon, rtl=self.isRightToLeft()).pixmap(16, 16))
        self.text.setText(text)
        self.setToolTip(tip)
        for w in (self, self.text):
            w.setProperty("state", state)
            w.style().unpolish(w)
            w.style().polish(w)


class InfoBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("infoBar")
        self.wiki = _Chip(self)
        self.user = _Chip(self)
        self.approval = _Chip(self)
        self.mode = _Chip(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(8)
        for chip in (self.wiki, self.user, self.approval, self.mode):
            layout.addWidget(chip)
        layout.addStretch(1)
        self.show_info(Info())

    def show_info(self, info: Info) -> None:
        tr = self.tr
        if info.wiki:
            self.wiki.set(PROJECT_LOGOS.get(info.project, "globe"), info.wiki, "neutral")
        else:
            self.wiki.set("globe", tr("No wiki"), "warn", tr("Log in to connect to a wiki"))
        if info.user:
            text = info.user + (f" ({info.user_groups})" if info.user_groups else "")
            self.user.set("userAvatar", text, "good", tr("Logged in"))
        else:
            self.user.set(
                "userAnonymous",
                tr("Not logged in"),
                "bad",
                tr("Log in (File → Log in, Ctrl+L) to connect to a wiki and work on pages"),
            )
        if info.approved is None:
            self.approval.hide()
        else:
            self.approval.show()
            if info.approved:
                self.approval.set("success", tr("Approved for editing"), "good", info.approval_note)
            else:
                self.approval.set(
                    "alert", tr("Not approved: read only and dry run"), "warn", info.approval_note
                )
        self.mode.set(info.mode_icon, tr("Mode: %1").replace("%1", info.mode), "mode")
