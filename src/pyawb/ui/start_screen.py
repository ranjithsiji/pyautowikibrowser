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
"""The start screen: what is needed before the main window opens.

1. Wiki: project and language (Meta-Wiki's list of open wikis), or a wiki's script path. The
   language of the wiki decides the script.
2. Fonts for that script: required, since they shape every display of the wiki's text; a suitable
   installed font is chosen to start with, and the screen cannot go on without one
3. Log in: a bot password; the account's password, with a two-factor code if the wiki asks; or the
   wiki's own login page (security keys, passkeys). Or Skip: work offline, with a warning
4. Pages: the list maker, to start with a list

The interface language is not asked: it follows the system (Settings → Language changes it).

The first run starts at step 1; once a profile exists, at the login step (Back goes to the others).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from pyawb.api import connect, credentials
from pyawb.api.session import WikiSession
from pyawb.api.siteinfo import wiki_url
from pyawb.api.transport import Cookie
from pyawb.core.article import Article
from pyawb.lists.sources import WikiContext, wiki_context
from pyawb.settings import appconfig, languages
from pyawb.settings.appconfig import AppConfig, Profile
from pyawb.settings.preferences import script_for_language
from pyawb.ui import browser_login
from pyawb.ui.editor_dialogs import primary_button
from pyawb.ui.list_maker import ListMaker
from pyawb.ui.login_dialog import PROJECTS
from pyawb.ui.settings_dialog import FontsPage, LanguagePicker
from pyawb.ui.tasks import run_task

STEPS = ("wiki", "fonts", "login", "pages")

BOT_PASSWORD, ACCOUNT_PASSWORD, WIKI_PAGE = "bot", "account", "browser"


@dataclass
class StartResult:
    config: AppConfig
    session: WikiSession | None = None
    wiki: WikiContext | None = None
    pages: tuple[Article, ...] = ()


type Connector = Callable[..., WikiSession]


class _SecondFactor(QObject):
    """Lets the login (in a worker thread) ask the screen for a two-factor code and wait."""

    asked = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._event = threading.Event()
        self._answer: str | None = None

    def ask(self, label: str) -> str | None:  # in the worker
        self._event.clear()
        self.asked.emit(label)  # queued to the screen
        if not self._event.wait(timeout=600):
            return None
        return self._answer

    def answer(self, code: str | None) -> None:  # in the UI thread
        self._answer = code
        self._event.set()


class StartScreen(QDialog):
    def __init__(
        self,
        config: AppConfig,
        parent: QWidget | None = None,
        *,
        connector: Connector = connect.connect,
        cookie_connector: Connector = connect.connect_with_cookies,
        context: Callable[[AppConfig, WikiSession], WikiContext | None] = wiki_context,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("PyAutoWikiBrowser — start"))
        self.resize(820, 640)
        self.config = config
        self.connector, self.cookie_connector, self.context = (
            connector,
            cookie_connector,
            context,
        )
        self.session: WikiSession | None = None
        self.wiki: WikiContext | None = None
        self.busy = False
        self.second_factor = _SecondFactor()
        self.second_factor.asked.connect(self._ask_code)
        profile = config.profile()
        self.profile = profile or Profile(name="", lang="en")
        prefs = config.preferences

        self.steps_label = QLabel(self)
        self.steps_label.setObjectName("startSteps")
        self.stack = QStackedWidget(self)

        # 2. wiki
        wiki = QWidget(self)
        self.project = QComboBox(wiki)
        for p in PROJECTS:
            self.project.addItem(p, p)
        self.project.setCurrentIndex(max(self.project.findData(self.profile.project), 0))
        self.wiki_language = LanguagePicker([], self.profile.lang, parent=wiki)
        self.custom_url = QLineEdit(wiki)
        self.custom_url.setPlaceholderText("https://wiki.example.org/w/")
        self.custom_url.setText(self.profile.custom_url)
        wl = QFormLayout(wiki)
        wl.addRow(self.tr("Project"), self.project)
        wl.addRow(self.tr("Language"), self.wiki_language)
        wl.addRow(self.tr("Or a wiki's script path"), self.custom_url)
        self.project.currentIndexChanged.connect(self._project_changed)
        self._project_changed()
        self.stack.addWidget(
            self._page(
                self.tr("Wiki"),
                self.tr(
                    "Which wiki you will work on. The list has every open wiki of the project."
                ),
                wiki,
            )
        )

        # 3. fonts
        self.fonts = FontsPage(
            prefs, script_for_language(self.profile.lang), self, fixed_script=True
        )
        self.stack.addWidget(
            self._page(
                self.tr("Fonts"),
                self.tr(
                    "A font with the wiki's script is needed to show its text correctly. "
                    "A suitable installed font is chosen; change it if you prefer another."
                ),
                self.fonts,
            )
        )

        # 4. login
        login = QWidget(self)
        self.method_group = QButtonGroup(self)
        methods = QVBoxLayout()
        for key, text, tip in (
            (BOT_PASSWORD, self.tr("Bot password (Name@Tool from Special:BotPasswords)"),
             self.tr("Recommended. Can be remembered in the system keychain.")),
            (ACCOUNT_PASSWORD, self.tr("Account password (a two-factor code is asked if needed)"),
             self.tr("For accounts with two-factor authentication (TOTP). Never stored.")),
            (WIKI_PAGE, self.tr("The wiki's own login page (security keys, passkeys)"),
             self.tr("Opens the wiki's login page here; any method the wiki offers works.")),
        ):  # fmt: skip
            radio = QRadioButton(text, login)
            radio.setToolTip(tip)
            radio.setProperty("method", key)
            if key == WIKI_PAGE and not browser_login.available():
                radio.setEnabled(False)
                radio.setToolTip(self.tr("Needs Qt WebEngine, which is not installed."))
            self.method_group.addButton(radio)
            methods.addWidget(radio)
        self.method_group.buttons()[0].setChecked(True)
        self.username = QLineEdit(self.profile.username, login)
        self.password = QLineEdit(login)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.remember = QCheckBox(
            self.tr("Remember the bot password in the system keychain"), login
        )
        self.remember.setChecked(self.profile.remember_password)
        self.code_label = QLabel(login)
        self.code = QLineEdit(login)
        self.code.setPlaceholderText("123456")
        self.code.returnPressed.connect(self._send_code)
        self.code_button = QPushButton(self.tr("Continue"), login)
        self.code_button.clicked.connect(self._send_code)
        code_row = QHBoxLayout()
        code_row.addWidget(self.code, 1)
        code_row.addWidget(self.code_button)
        self.login_button = QPushButton(self.tr("Log in"), login)
        primary_button(self.login_button)
        self.login_button.clicked.connect(self.log_in)
        self.skip_button = QPushButton(self.tr("Skip (work offline)"), login)
        self.skip_button.clicked.connect(self.skip_login)
        self.login_status = QLabel(login)
        self.login_status.setWordWrap(True)
        form = QFormLayout()
        form.addRow(self.tr("User name"), self.username)
        form.addRow(self.tr("Password"), self.password)
        form.addRow("", self.remember)
        form.addRow(self.code_label, code_row)
        ll = QVBoxLayout(login)
        ll.addLayout(methods)
        ll.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addWidget(self.login_button)
        buttons.addWidget(self.skip_button)
        buttons.addStretch(1)
        ll.addLayout(buttons)
        ll.addWidget(self.login_status)
        ll.addStretch(1)
        self.method_group.buttonToggled.connect(lambda *_: self._method_changed())
        self._method_changed()
        self._show_code(False)
        self.stack.addWidget(
            self._page(
                self.tr("Log in"),
                self.tr(
                    "Connecting to a wiki needs a login. Without one (Skip) you can only make "
                    "lists from text you paste or from files, and you cannot edit."
                ),
                login,
            )
        )

        # 5. pages
        self.list_maker = ListMaker(self)
        self.stack.addWidget(
            self._page(
                self.tr("Pages"),
                self.tr("Make the list of pages to work on (you can also do it later)."),
                self.list_maker,
            )
        )

        self.back = QPushButton(self.tr("Back"), self)
        self.back.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        self.next = QPushButton(self.tr("Next"), self)
        primary_button(self.next)
        self.next.clicked.connect(self._next)
        nav = QHBoxLayout()
        nav.addWidget(self.back)
        nav.addStretch(1)
        nav.addWidget(self.next)
        layout = QVBoxLayout(self)
        layout.addWidget(self.steps_label)
        layout.addWidget(self.stack, 1)
        layout.addLayout(nav)
        self.go(STEPS.index("login") if profile is not None else 0)

    # -- pages --------------------------------------------------------------------------------

    def _page(self, title: str, text: str, body: QWidget) -> QWidget:
        page = QWidget(self)
        heading = QLabel(title, page)
        heading.setObjectName("startHeading")
        layout = QVBoxLayout(page)
        layout.addWidget(heading)
        if text:
            intro = QLabel(text, page)
            intro.setWordWrap(True)
            layout.addWidget(intro)
        layout.addWidget(body, 1)
        return page

    def step(self) -> str:
        return STEPS[self.stack.currentIndex()]

    def go(self, index: int) -> None:
        if not 0 <= index < len(STEPS) or self.busy:
            return
        if STEPS[index] == "fonts":
            # the wiki chosen decides the script whose fonts are asked for
            self.fonts.set_script(script_for_language(self.wiki_lang()))
            self.fonts.ensure_font()
        self.stack.setCurrentIndex(index)
        names = [
            self.tr("Wiki"),
            self.tr("Fonts"),
            self.tr("Log in"),
            self.tr("Pages"),
        ]
        self.steps_label.setText(
            "  ›  ".join(
                f"<b>{i + 1}. {n}</b>" if i == index else f"{i + 1}. {n}"
                for i, n in enumerate(names)
            )
        )
        self.back.setEnabled(index > 0)
        last = index == len(STEPS) - 1
        self.next.setText(self.tr("Open PyAutoWikiBrowser") if last else self.tr("Next"))
        # no font with the wiki's script: the text could not be shown, so no going on
        self.next.setEnabled(STEPS[index] != "fonts" or self.fonts.has_fonts())

    def _next(self) -> None:
        if self.step() == "fonts" and not self.fonts.ensure_font():
            return  # the page says which font to install
        if self.step() == "login" and self.session is None and not self._offline:
            self.login_status.setText(
                self.tr("Log in, or Skip to work offline (lists only, no editing).")
            )
            return
        if self.stack.currentIndex() == len(STEPS) - 1:
            self._finish()
        else:
            self.go(self.stack.currentIndex() + 1)

    _offline = False

    # -- wiki ---------------------------------------------------------------------------------

    def _project_changed(self) -> None:
        data = languages.load()
        project = str(self.project.currentData())
        langs = data.wiki_languages(project)
        self.wiki_language.setEnabled(bool(langs))
        self.custom_url.setEnabled(project == "custom")
        self.wiki_language.set_languages(langs, self.profile.lang)

    def wiki_lang(self) -> str:
        return self.wiki_language.code() or "en"

    def chosen_profile(self) -> Profile:
        """The profile as chosen on the wiki and login steps (named after the wiki)."""
        project = str(self.project.currentData())
        lang = self.wiki_lang()
        custom = self.custom_url.text().strip() if project == "custom" else ""
        name = self.profile.name if self._same_wiki(project, lang, custom) else ""
        if not name:
            name = custom or f"{lang}.{project}"
        return replace(
            self.profile,
            name=name,
            lang=lang,
            project=project,
            custom_url=custom,
            username=self.username.text().strip(),
            remember_password=self.remember.isChecked() and self.method() == BOT_PASSWORD,
        )

    def _same_wiki(self, project: str, lang: str, custom: str) -> bool:
        p = self.profile
        return bool(p.name) and (p.project, p.lang, p.custom_url) == (project, lang, custom)

    # -- login --------------------------------------------------------------------------------

    def method(self) -> str:
        checked = self.method_group.checkedButton()
        return str(checked.property("method")) if checked is not None else BOT_PASSWORD

    def _method_changed(self) -> None:
        browser = self.method() == WIKI_PAGE
        for w in (self.username, self.password):
            w.setEnabled(not browser)
        self.remember.setVisible(self.method() == BOT_PASSWORD)

    def _show_code(self, visible: bool, label: str = "") -> None:
        self.code_label.setText(label or self.tr("Two-factor code"))
        for w in (self.code_label, self.code, self.code_button):
            w.setVisible(visible)

    def _ask_code(self, label: str) -> None:
        """The wiki asked for a second factor: show the code field."""
        self._show_code(True, label)
        self.login_status.setText(self.tr("Enter the code from your authenticator app."))
        self.code.clear()
        self.code.setFocus()

    def _send_code(self) -> None:
        if self.code.text().strip():
            self._show_code(False)
            self.login_status.setText(self.tr("Checking the code…"))
            self.second_factor.answer(self.code.text().strip())

    def _profile_config(self) -> AppConfig:
        profile = self.chosen_profile()
        config = self.config.with_profile(profile, make_default=True)  # other profiles stay
        return replace(config, preferences=self.fonts.preferences())

    def log_in(self) -> None:
        if self.busy:
            return
        config = self._profile_config()
        profile = config.profile(config.default_profile)
        assert profile is not None
        method = self.method()
        if method != WIKI_PAGE and not profile.username:
            self.login_status.setText(self.tr("Give the user name."))
            return
        password = self.password.text() or None
        if method != WIKI_PAGE and password is None and not self._remembered(profile):
            self.login_status.setText(self.tr("Give the password."))
            return

        if method == WIKI_PAGE:
            script_url = "".join(wiki_url(profile.lang, profile.project, profile.custom_url)[:2])
            dialog = browser_login.BrowserLoginDialog(script_url, self)
            if not dialog.exec() or not dialog.username:
                return
            cookies: list[Cookie] = list(dialog.cookies.values())
            name = dialog.username

            def work() -> tuple[WikiSession, WikiContext | None]:
                session = self.cookie_connector(config, profile, cookies, name)
                return session, self.context(config, session)

        else:
            second = self.second_factor.ask if method == ACCOUNT_PASSWORD else None

            def work() -> tuple[WikiSession, WikiContext | None]:
                session = self.connector(config, profile, password, second_factor=second)
                return session, self.context(config, session)

        self._set_busy(True)
        self.login_status.setText(self.tr("Logging in to %1…").replace("%1", profile.wiki_url))
        run_task(work, lambda r: self._logged_in(config, r), self._login_failed)

    def _remembered(self, profile: Profile) -> bool:
        try:
            return credentials.load_password(profile.wiki_url, profile.username) is not None
        except Exception:  # no usable keychain
            return False

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        for w in (self.login_button, self.skip_button, self.back, self.next):
            w.setEnabled(not busy)

    def _logged_in(self, config: AppConfig, result: Any) -> None:
        self._set_busy(False)
        session, wiki = result
        assert isinstance(session, WikiSession)
        self.session, self.wiki, self.config = session, wiki, config
        self._offline = False
        self.password.clear()
        status = session.status
        if session.can_save:
            note = self.tr("Logged in as %1. Approved for editing.")
        else:
            reason = status.status.value if status else ""
            note = self.tr("Logged in as %1. Not approved on the CheckPage (%2): read only and "
                           "dry run.").replace("%2", reason)  # fmt: skip
        self.login_status.setText(note.replace("%1", session.user.name))
        self.list_maker.set_wiki(wiki, session.site)
        self.go(STEPS.index("pages"))

    def _login_failed(self, error: Exception) -> None:
        self._set_busy(False)
        self._show_code(False)
        self.login_status.setText(
            self.tr("Could not log in: %1").replace("%1", str(error) or type(error).__name__)
        )

    def skip_login(self) -> None:
        answer = QMessageBox.question(
            self,
            self.tr("Work offline"),
            self.tr(
                "Without logging in (and without approval on the wiki's CheckPage) you cannot "
                "edit, and you cannot load pages or make lists from the wiki. Lists from pasted "
                "text and files still work. Continue without logging in?"
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._offline = True
        self.session = self.wiki = None
        self.config = self._profile_config()
        self.login_status.setText(self.tr("Working offline."))
        self.go(STEPS.index("pages"))

    # -- result -------------------------------------------------------------------------------

    def _finish(self) -> None:
        if self.session is None:
            self.config = self._profile_config()
        else:
            self.config = replace(self.config, preferences=self.fonts.preferences())
        try:
            appconfig.save(self.config)
        except OSError as e:
            QMessageBox.warning(self, self.tr("Settings"), str(e))
        self.accept()

    def result_value(self) -> StartResult:
        return StartResult(
            self.config, self.session, self.wiki, tuple(self.list_maker.articles.items)
        )

    def keyPressEvent(self, event: Any) -> None:
        # Enter in a field must not close the screen (it is a dialog)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return
        super().keyPressEvent(event)
