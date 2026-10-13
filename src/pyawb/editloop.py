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
# Ported from AutoWikiBrowser AWB/Main.cs (StartArticleProcessing, PageLoaded, LoadSuccessApi,
# SkipChecks, RunSkipChecks, SaveArticle)
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The edit loop without the UI: load a page, check it, process it, save it.

AWB runs these steps as event handlers on the main form. Here load() and save() are plain
blocking calls that the UI runs in a worker thread; what the form did between them (show the
diff, wait for Save or Skip, remove the page from the list, start the next) stays in ui/.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pyawb.api.models import PageInfo, PageTitleStatus, SaveInfo, WatchOptions
from pyawb.api.session import WikiSession
from pyawb.api.tagger import WikiTaggerLookups
from pyawb.core import namespace, process, tools
from pyawb.core.article import Article
from pyawb.core.parsers import parsers as _parsers
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.parsers import Parsers
from pyawb.core.site import use_site


@dataclass
class LoopOptions:
    """Options for loading and checking pages, around ProcessOptions."""

    process: process.ProcessOptions = field(default_factory=process.ProcessOptions)
    follow_redirects: bool = True
    skip_if_redirect: bool = False
    skip_non_existent: bool = True
    skip_existent: bool = False
    skip_if_in_use: bool = False
    filter_non_main_space: bool = False  # skip redirects to other namespaces
    section_summary: bool = True
    summary: str = ""  # the user's edit summary


@dataclass
class LoadResult:
    """One page after loading and processing (or skipping).

    title: the page as listed (after canonicalisation); page.title may differ when a redirect was
    followed or the title was normalised, and the list should then show page.title instead.
    """

    title: str
    page: PageInfo | None = None
    article: Article | None = None
    skip_reason: str | None = None
    summary: str = ""
    in_use: bool = False  # {{inuse}} without "skip if in use": AWB warns
    new_messages: bool = False  # the user has new talk page messages: AWB stops

    @property
    def skipped(self) -> bool:
        return self.skip_reason is not None

    @property
    def renamed(self) -> bool:
        """The list entry should be replaced by page.title."""
        return self.page is not None and bool(self.page.title) and self.page.title != self.title

    @property
    def text(self) -> str:
        return self.article.article_text if self.article is not None else ""


class EditLoop:
    """The page-by-page work of AWB's main form, against a WikiSession."""

    def __init__(self, session: WikiSession) -> None:
        self.session = session
        self.parsers = Parsers()
        self.parsers.tagger_lookups = WikiTaggerLookups(session.transport)
        self.remove_text = HideText(False, True, True)  # AWB MainForm.RemoveText

    def load(self, title: str, opts: LoopOptions) -> LoadResult:
        """StartArticleProcessing + PageLoaded + ProcessPage + RunSkipChecks for one title."""
        with use_site(self.session.site):
            return self._load(title, opts)

    def _load(self, title: str, opts: LoopOptions) -> LoadResult:
        if not tools.is_valid_title(title):
            return LoadResult(title, skip_reason="Invalid page title")
        title = _parsers.canonicalize_title_aggressively(title)

        # with "skip if redirect" on, redirects are not followed even if "follow" is on too
        page = self.session.open(title, opts.follow_redirects and not opts.skip_if_redirect)
        result = LoadResult(title, page)

        # LoadSuccessApi
        if not page.exists and opts.skip_non_existent:
            return self._skip(result, "Non-existent page")
        if page.exists and opts.skip_existent:
            return self._skip(result, "Existing page")
        if self.session.user.has_messages:
            result.new_messages = True
            return result

        # PageLoaded
        if namespace.is_special(namespace.determine(page.title)):
            return self._skip(result, "Page is a special page")
        article = Article(page.title, page.text, page.namespace_id)
        article.display_title = page.display_title
        result.article = article
        if opts.skip_if_redirect and tools.is_redirect(page.text):
            return self._skip(result, "Page is a redirect")
        if opts.follow_redirects and page.was_redirected:
            if page.title_changed_status & PageTitleStatus.REDIRECT_LOOP:
                return self._skip(result, "Recursive redirect")
            if (
                opts.filter_non_main_space
                and namespace.determine(page.title) != namespace.Namespace.ARTICLE
            ):
                return self._skip(result, "Page redirects to non-mainspace")

        reason = self._protection_skip_reason(page)
        if reason is None:
            reason = process.contains_skip_reason(article, opts.process, after=False)
        if reason is not None:
            return self._skip(result, reason)

        if article.is_in_use:
            if opts.skip_if_in_use:
                return self._skip(result, "Page contains {{inuse}}")
            result.in_use = True

        if process.has_private_use_characters(page.text):
            return self._skip(result, "Page has character in Unicode Private Use Area")

        process.process_page(article, opts.process, self.parsers, self.remove_text)

        # RunSkipChecks
        if article.skip_article:
            return self._skip(result, article.log.skip_reason)
        reason = process.no_change_skip_reason(article, opts.process)
        if reason is None:
            reason = process.contains_skip_reason(article, opts.process, after=True)
        if reason is not None:
            return self._skip(result, reason)

        result.summary = process.make_default_edit_summary(
            article, opts.summary, article.article_text, opts.section_summary
        )
        return result

    def _protection_skip_reason(self, page: PageInfo) -> str | None:
        user = self.session.user
        if not user.can_edit_page(page):
            return "Page is protected"
        if not user.can_create_page(page):
            return "Page is protected from creation"
        return None

    @staticmethod
    def _skip(result: LoadResult, reason: str) -> LoadResult:
        result.skip_reason = reason
        if result.article is not None and not result.article.skip_article:
            result.article.awb_skip(reason)
        return result

    def save(
        self,
        result: LoadResult,
        text: str,
        summary: str,
        *,
        minor: bool = False,
        watch: WatchOptions = WatchOptions.NO_CHANGE,
        suppress_tag: bool = False,
    ) -> SaveInfo:
        """SaveArticle: save the edited text of a loaded page. A /* section */ summary that no
        longer matches the edit loses its section; the tool's summary tag is appended."""
        page = result.page
        if page is None or result.article is None:
            raise ValueError("the page was not loaded")
        with use_site(self.session.site):
            summary = process.check_section_summary(
                summary, result.article.original_article_text, text
            )
            summary = process.append_summary_tag(
                summary, self.session.site, is_bot=self.session.user.is_bot, suppress=suppress_tag
            )
        return self.session.save(text, summary, minor=minor, watch=watch, page=page)

    def diff(self, result: LoadResult, text: str) -> str:
        """The wiki's diff of the current revision against text (HTML table rows)."""
        title = result.page.title if result.page is not None else result.title
        return self.session.compare(title, text)

    def preview(self, result: LoadResult, text: str) -> str:
        title = result.page.title if result.page is not None else result.title
        return self.session.preview(title, text)
