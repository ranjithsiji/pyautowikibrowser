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
# Ported from AutoWikiBrowser WikiFunctions/Session.cs and API/ApiEdit.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""One wiki: its configuration, the logged-in user, the CheckPage decision, and open/save.

Calls block; the UI runs them in a worker thread. Saving is refused unless the CheckPage gate
said REGISTERED, the page was opened first (baserevid, basetimestamp, starttimestamp) and the
text has no leftover HideText placeholders.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Protocol

from pyawb import __version__
from pyawb.api import checkpage, siteinfo
from pyawb.api.errors import ApiException, CaptchaException, check_errors
from pyawb.api.models import (
    OPEN_PARAMS,
    USERINFO_PROPS,
    PageInfo,
    SaveInfo,
    UserInfo,
    WatchOptions,
)
from pyawb.api.transport import Cookie, Param, SecondFactor, Transport
from pyawb.core import tools
from pyawb.core.site import SiteConfig

TEMPLATE_REDIRECTS_TITLE = "Project:AutoWikiBrowser/Template redirects"
DATED_TEMPLATES_TITLE = "Project:AutoWikiBrowser/Dated templates"
RENAME_TEMPLATE_PARAMETERS_TITLE = "Project:AutoWikiBrowser/Rename template parameters"

_PLACEHOLDER_MARKS = ("⌊⌊⌊⌊", "⌋⌋⌋⌋")


class NotApprovedException(ApiException):
    """Saving was refused: the CheckPage gate has not approved this user (or was not run)."""

    def __init__(self, status: checkpage.StatusResult | None) -> None:
        reason = "the CheckPage has not been checked" if status is None else status.status.value
        if status is not None and status.reason:
            reason += f" ({status.reason})"
        super().__init__(f"Not allowed to save: {reason}")
        self.status = status


class LoginException(ApiException):
    """Login failed (wrong name or bot password, or the account is locked)."""


class Login(Protocol):
    """A transport that can log in (PywikibotTransport does)."""

    def login(
        self, username: str, password: str, second_factor: SecondFactor | None = None
    ) -> None: ...

    def logout(self) -> None: ...


@dataclass(frozen=True)
class ConfigPages:
    """Texts of the wiki's AWB configuration pages (Main.LoadTemplateRedirects etc.)."""

    template_redirects: str = ""
    dated_templates: str = ""
    rename_template_parameters: str = ""

    def apply(self, cfg: SiteConfig) -> SiteConfig:
        """SiteConfig with these pages; dated templates are kept unless the page has text."""
        from pyawb.core.parsers.templates import load_dated_templates

        dated = (
            tuple(load_dated_templates(self.dated_templates))
            if self.dated_templates
            else cfg.dated_templates
        )
        return replace(
            cfg,
            template_redirects_text=self.template_redirects,
            dated_templates=dated,
            renamed_template_parameters_text=self.rename_template_parameters
            or cfg.renamed_template_parameters_text,
        )


def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()


@dataclass(frozen=True)
class Rendering:
    html: str
    links: tuple[str, ...]  # categories and language links, sorted


class WikiSession:
    """A connection to one wiki (AWB's Session + ApiEdit)."""

    def __init__(
        self,
        transport: Transport,
        site: SiteConfig,
        *,
        global_transport: Transport | None = None,
        app_version: str = __version__,
        require_enabled_version: bool = False,
    ) -> None:
        """transport: the wiki. global_transport: English Wikipedia, for the global version page
        and the interwiki order (defaults to transport).

        require_enabled_version: also refuse when app_version is not an enabled version on the
        global version page. Off until PyAWB has its own entry there: AWB's page lists AWB's
        versions only. The CheckPage, banned names and global users still apply.
        """
        self.transport = transport
        self.global_transport = global_transport or transport
        self.site = site
        self.app_version = app_version
        self.require_enabled_version = require_enabled_version
        self.siteinfo: siteinfo.SiteInfo | None = None
        self.tag_edits = False
        self.user = UserInfo()
        self.status: checkpage.StatusResult | None = None
        self.page: PageInfo | None = None

    # configuration ----------------------------------------------------------------------------

    def raw_page(self, title: str, transport: Transport | None = None) -> str:
        """The current wikitext of a page, "" if it does not exist."""
        t = transport or self.transport
        return checkpage.raw_page_text(t.request(checkpage.raw_page_params(title)))

    def load_site(self) -> SiteConfig:
        """Load the wiki's configuration (Session.LoadProjectOptions and Main's loaders):
        siteinfo, month names, AWB change tag, AWB config pages, interwiki order."""
        cfg, info, tag = siteinfo.load_site_config(self.transport, self.site)
        self.siteinfo, self.tag_edits = info, tag
        pages = ConfigPages(
            self._raw_or_empty(TEMPLATE_REDIRECTS_TITLE),
            self._raw_or_empty(DATED_TEMPLATES_TITLE),
            self._raw_or_empty(RENAME_TEMPLATE_PARAMETERS_TITLE),
        )
        cfg = pages.apply(cfg)
        iw_text = self._raw_or_empty(siteinfo.INTERWIKI_ORDER_TITLE, self.global_transport)
        if iw_text:
            cfg = replace(cfg, **siteinfo.parse_interwiki_order(iw_text))
        try:
            matrix = siteinfo.parse_sitematrix(
                self.global_transport.request(siteinfo.SITEMATRIX_PARAMS)
            )
            if matrix.languages:
                cfg = replace(cfg, interwiki_languages=matrix.languages)
        except ApiException:
            pass
        self.site = cfg
        return cfg

    def _raw_or_empty(self, title: str, transport: Transport | None = None) -> str:
        # AWB treats any failure to load a config page as an empty page
        try:
            return self.raw_page(title, transport)
        except ApiException:
            return ""

    # user and CheckPage -----------------------------------------------------------------------

    def login(
        self, username: str, password: str, second_factor: SecondFactor | None = None
    ) -> UserInfo:
        """Log in with a bot password ("Name@BotName") or the main password (second_factor
        answers a two-factor prompt), then check the CheckPage again."""
        if not hasattr(self.transport, "login"):
            raise LoginException("this connection cannot log in")
        login: Login = self.transport  # type: ignore[assignment]
        if second_factor is None:
            login.login(username, password)
        else:
            login.login(username, password, second_factor)
        return self._logged_in(username)

    def login_with_cookies(self, cookies: Iterable[Cookie], username: str) -> UserInfo:
        """Log in with a session from the wiki's own login page (see Transport.adopt_cookies)."""
        adopt = getattr(self.transport, "adopt_cookies", None)
        if adopt is None:
            raise LoginException("this connection cannot use a browser session")
        adopt(cookies, username)
        return self._logged_in(username)

    def _logged_in(self, username: str) -> UserInfo:
        self.refresh_user()
        if not self.user.is_logged_in:
            raise LoginException(f"login as {username} failed")
        self.check_status()
        return self.user

    def logout(self) -> None:
        if hasattr(self.transport, "logout"):
            login: Login = self.transport  # type: ignore[assignment]
            login.logout()
        self.user = UserInfo()
        self.status = None

    def refresh_user(self) -> UserInfo:
        result = self.transport.request(
            {"action": "query", "meta": "userinfo", "uiprop": USERINFO_PROPS}
        )
        self.user = UserInfo.from_json(result)
        return self.user

    def check_status(self) -> checkpage.StatusResult:
        """Session.UpdateWikiStatus: load the version, Config and CheckPage pages and decide.
        The Config page's underscored titles are applied to the SiteConfig."""
        try:
            version_text = self.raw_page(checkpage.VERSION_PAGE_TITLE, self.global_transport)
            config_text = self.raw_page(checkpage.CONFIG_TITLE)
            check_text = self.raw_page(checkpage.CHECKPAGE_TITLE)
        except ApiException as e:
            self.status = checkpage.StatusResult(checkpage.WikiStatus.ERROR, reason=str(e))
            return self.status
        self.status = checkpage.evaluate_status(
            self.user,
            version_text,
            config_text,
            check_text,
            app_version=self.app_version,
            project=self.site.project,
            require_enabled_version=self.require_enabled_version,
        )
        if self.status.config.underscore_titles:
            self.site = replace(
                self.site, underscored_titles=frozenset(self.status.config.underscore_titles)
            )
        return self.status

    @property
    def can_save(self) -> bool:
        return self.status is not None and self.status.can_edit

    @property
    def is_bot(self) -> bool:
        """Bot mode allowed: listed in the CheckPage's enabledbots."""
        return self.status is not None and self.status.is_bot

    # pages ------------------------------------------------------------------------------------

    def open(self, title: str, resolve_redirects: bool = False) -> PageInfo:
        """ApiEdit.Open: the page's text, tokens, protection and timestamps."""
        if not title:
            raise ValueError("page name required")
        params: dict[str, Param] = {**OPEN_PARAMS, "titles": title}
        if resolve_redirects:
            params["redirects"] = True
        if self.user.is_logged_in:
            # ActionOptions.CheckNewMessages: the talk page flag and the notification count
            # come with every page, so the loop can stop for new messages
            params["meta"] = f"{params['meta']}|userinfo|notifications"
            params["uiprop"] = "hasmsg"
            params["notprop"] = "count"
        result = self.transport.request(params)
        self.page = PageInfo.from_json(result)
        self.user = self.user.updated(result)
        return self.page

    def page_exists(self, title: str) -> bool:
        result = self.transport.request({"action": "query", "prop": "info", "titles": title})
        pages = result.get("query", {}).get("pages", ())
        return bool(pages) and not pages[0].get("missing") and not pages[0].get("invalid")

    def prefix_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Link target suggestions: mw.widgets.TitleWidget's query (generator=prefixsearch with
        info, disambiguation pageprops, descriptions and redirects), as the `query` object for
        editor.dialogs.title_options."""
        if not query.strip():
            return {}
        params: dict[str, Param] = {
            "action": "query",
            "prop": "info|pageprops|description",
            "generator": "prefixsearch",
            "gpssearch": query,
            "gpslimit": limit,
            "ppprop": "disambiguation",
            "redirects": True,
        }
        return dict(self.transport.request(params).get("query", {}))

    def save(
        self,
        text: str,
        summary: str,
        *,
        minor: bool = False,
        watch: WatchOptions = WatchOptions.NO_CHANGE,
        bot: bool = False,
        page: PageInfo | None = None,
    ) -> SaveInfo:
        """ApiEdit.Save: save the opened page. Refused unless the CheckPage gate approved the
        user. bot: mark as a bot edit, only if the user is enabled as a bot and has the right."""
        if not self.can_save:
            raise NotApprovedException(self.status)
        page = page or self.page
        if page is None or (not page.edit_token):
            raise ApiException("the page was not opened for editing")
        if not text and not page.exists:
            raise ValueError("can't save empty pages")
        if any(mark in text and mark not in page.text for mark in _PLACEHOLDER_MARKS):
            raise ApiException("the text still contains hidden-text placeholders (⌊⌊⌊⌊n⌋⌋⌋⌋)")

        text = tools.convert_from_local_line_endings(text)
        params: dict[str, Param] = {
            "action": "edit",
            "title": page.title,
            "watchlist": watch.value,
            "minor": minor,
            "bot": bot and self.is_bot and self.user.is_bot,
            "md5": md5(text),
            "summary": summary,
            "text": text,
            "assert": "user",
        }
        if page.exists:
            params["basetimestamp"] = page.timestamp
            params["baserevid"] = page.revision_id
            params["nocreate"] = True  # deleted since opened: don't recreate
        else:
            params["createonly"] = True
        if page.token_timestamp:
            params["starttimestamp"] = page.token_timestamp
        if self.tag_edits:
            params["tags"] = "AWB"
        if page.content_model != "wikitext":
            params["contentmodel"] = page.content_model
        result = self.transport.request(params, post=True, token="csrf")
        info = SaveInfo.from_json(result)
        if not info.success:
            if info.captcha:
                raise CaptchaException("the wiki asks for a captcha")
            raise ApiException(f"save failed: {info.result} {dict(info.extra)}")
        if page is self.page:
            self.page = None
        return info

    def preview(self, title: str, text: str) -> str:
        """ApiEdit.Preview: the rendered HTML (parse warnings first), for the browser."""
        result = check_errors(
            self.transport.request(
                {
                    "action": "parse",
                    "prop": "text|parsewarnings",
                    "title": title,
                    "text": tools.convert_from_local_line_endings(text),
                    "pst": True,
                    "disablelimitreport": True,
                    "contentmodel": "wikitext",
                },
                post=True,
            )
        )
        parse: Mapping[str, Any] = result.get("parse", {})
        html = str(parse.get("text", ""))
        warnings = parse.get("parsewarnings", ())
        if warnings:
            notes = "<p>".join(str(w) for w in warnings)
            html = f'<div class="previewnote" style="color:#d33">{notes}<p></div>' + html
        return html

    def rendering(self, title: str, text: str | None = None) -> Rendering:
        """The parsed page (text None: the saved revision) as Article.OnlyCosmeticChanged reads
        it: the HTML, and the categories and language links."""
        params: dict[str, Param] = {
            "action": "parse",
            "prop": "text|langlinks|categories",
            "disablelimitreport": True,
        }
        if text is None:
            params["page"] = title
        else:
            params.update(
                title=title,
                text=tools.convert_from_local_line_endings(text),
                pst=True,
                contentmodel="wikitext",
            )
        parse: Mapping[str, Any] = check_errors(
            self.transport.request(params, post=text is not None)
        ).get("parse", {})
        cats = sorted("cat:" + str(c.get("category", "")) for c in parse.get("categories", ()))
        langs = sorted(
            "lang:" + str(link.get("lang", "")) + ":" + str(link.get("title", ""))
            for link in parse.get("langlinks", ())
        )
        return Rendering(str(parse.get("text", "")), tuple(cats + langs))

    def compare(self, title: str, text: str) -> str:
        """The wiki's own diff (action=compare) of the current revision against text, as HTML
        table rows."""
        result = check_errors(
            self.transport.request(
                {
                    "action": "compare",
                    "fromtitle": title,
                    "toslots": "main",
                    "totext-main": tools.convert_from_local_line_endings(text),
                    "topst": True,
                    "prop": "diff",
                },
                post=True,
            )
        )
        return str(result.get("compare", {}).get("body", ""))

    def expand_templates(self, text: str, title: str) -> str:
        """action=expandtemplates: the wikitext with templates expanded (Tools.ExpandTemplate)."""
        result = check_errors(
            self.transport.request(
                {
                    "action": "expandtemplates",
                    "prop": "wikitext",
                    "title": title,
                    "text": text,
                },
                post=True,
            )
        )
        return str(result.get("expandtemplates", {}).get("wikitext", ""))
