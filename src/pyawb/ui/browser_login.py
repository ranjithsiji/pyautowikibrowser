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
# The approach (the wiki's own login page in an embedded browser, session cookies captured) follows
# vcut-gui's browser login (src/vcut/gui/browser_login.py, browser_window.py; GPL-3.0-or-later).
"""Log in with the wiki's own login page.

Security keys, passkeys (WebAuthn) and any login method a wiki adds later cannot be done from a
native form: WebAuthn is bound to the wiki's origin. So the wiki's Special:UserLogin is shown in an
embedded browser (Qt WebEngine) with its own cookie store; whatever the wiki asks for is answered by
its own pages. When the cookies of a logged-in session appear, they are handed to the login step,
which gives them to pywikibot and checks them against the API. Nothing typed here passes through
PyAutoWikiBrowser, and no password is stored.
"""

from __future__ import annotations

import importlib.util
from urllib.parse import quote, urlsplit

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pyawb import paths
from pyawb.api.transport import Cookie


def available() -> bool:
    """Whether Qt WebEngine is installed (it is an optional part of PySide6 on some systems)."""
    return importlib.util.find_spec("PySide6.QtWebEngineWidgets") is not None


def login_url(script_url: str) -> str:
    """Special:UserLogin of the wiki whose script path is script_url ("https://ml.wikipedia.org/w/"),
    returning to a blank page."""
    base = script_url.rstrip("/")
    return f"{base}/index.php?title=Special:UserLogin&returnto={quote('Special:BlankPage')}"


def session_complete(cookies: dict[str, Cookie]) -> str:
    """The user name when the cookies are those of a logged-in session ("" otherwise): MediaWiki
    sets <wikiid>UserName with <wikiid>Session (or CentralAuth's centralauth_User and _Session)."""
    for name, cookie in cookies.items():
        if name.endswith("UserName") and cookie.value:
            prefix = name[: -len("UserName")]
            if f"{prefix}Session" in cookies or "centralauth_Session" in cookies:
                return cookie.value.replace("_", " ").replace("+", " ")
    user = cookies.get("centralauth_User")
    if user is not None and user.value and "centralauth_Session" in cookies:
        return user.value.replace("_", " ").replace("+", " ")
    return ""


class BrowserLoginDialog(QDialog):
    """The wiki's own login page; accept() once a logged-in session's cookies are there."""

    def __init__(self, script_url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self.setWindowTitle(self.tr("Log in with the wiki's login page"))
        self.resize(900, 760)
        self.cookies: dict[str, Cookie] = {}
        self.username = ""
        host = urlsplit(script_url).hostname or ""
        # the wiki's own cookies and those of its parent domains (CentralAuth: .wikipedia.org)
        self._domains = {host, "." + host} | {
            "." + ".".join(host.split(".")[i:]) for i in range(1, max(len(host.split(".")) - 1, 1))
        }

        self.profile = QWebEngineProfile("pyawb-login", self)
        storage = paths.data_dir() / "browser-login"
        storage.mkdir(parents=True, exist_ok=True)
        self.profile.setPersistentStoragePath(str(storage))
        self.profile.setCachePath(str(storage / "cache"))
        self.profile.cookieStore().cookieAdded.connect(self._cookie_added)
        self.view = QWebEngineView(self)
        self.view.setPage(QWebEnginePage(self.profile, self.view))
        self.view.load(QUrl(login_url(script_url)))

        hint = QLabel(
            self.tr(
                "Log in as you normally do — password, two-factor code, security key or passkey. "
                "This window closes once you are logged in."
            ),
            self,
        )
        hint.setWordWrap(True)
        self.status = QLabel(self.tr("Waiting for you to log in…"), self)
        reload = QPushButton(self.tr("Reload"), self)
        reload.clicked.connect(lambda: self.view.load(QUrl(login_url(script_url))))
        cancel = QPushButton(self.tr("Cancel"), self)
        cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(reload)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.status)
        layout.addLayout(buttons)

    def _cookie_added(self, cookie: object) -> None:
        from PySide6.QtNetwork import QNetworkCookie

        assert isinstance(cookie, QNetworkCookie)
        domain = cookie.domain()
        if domain and domain not in self._domains:
            return  # another site's cookie (auth.wikimedia.org's are not needed by the API)
        name = bytes(cookie.name().data()).decode("utf-8", "replace")
        value = bytes(cookie.value().data()).decode("utf-8", "replace")
        self.cookies[name] = Cookie(name, value, domain or "", cookie.path() or "/")
        if not self.username:
            self.username = session_complete(self.cookies)
            if self.username:
                self.status.setText(self.tr("Logged in as %1.").replace("%1", self.username))
                self.accept()

    def done(self, result: int) -> None:
        # the page must go before its profile, or Qt warns (and can crash) on exit
        page = self.view.page()
        self.view.setPage(None)  # type: ignore[arg-type]
        if page is not None:
            page.deleteLater()
        super().done(result)
