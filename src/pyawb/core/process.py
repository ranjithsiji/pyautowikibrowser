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
# Ported from AutoWikiBrowser AWB/Main.cs (ProcessPage, RunSkipChecks, SkipChecks,
# MakeDefaultEditSummary, AppendUsingAWBSummary)
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Processing one page with the user's options, without the UI (AWB's MainForm.ProcessPage).

AWB reads its options from the main form's check boxes; here they are a ProcessOptions value, so
the edit loop can run off the UI thread. Left out: custom modules, external programs, plugins
(roadmap step 6) and disambiguation (needs the wiki and a dialog).
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Protocol

from pyawb.core import namespace, rx, tools
from pyawb.core import summary as _summary
from pyawb.core import wikiregexes as W
from pyawb.core.article import (
    Article,
    CategorisationOptions,
    FindAndReplacer,
    ImageReplaceOptions,
    SkipOptions,
    TextRules,
    TypoFixer,
)
from pyawb.core.parsers import parsers as _parsers
from pyawb.core.parsers.categorydefaultsort import fix_categories
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.parsers import Parsers
from pyawb.core.rx import DotNetOptions, DotNetRegex
from pyawb.core.site import Namespace, SiteConfig, current_site
from pyawb.core.textutil import turn_first_to_upper

UNICODE_PUA = DotNetRegex(r"\p{IsPrivateUse}")


class Comparer(Protocol):
    """rules.skip.ArticleComparer."""

    def matches(self, article: Article) -> bool: ...


@dataclass(frozen=True)
class ContainsCheck:
    """Skip if the page contains (or, negate, does not contain) text (AWB's PageContainsControl
    and PageNotContainsControl). comparer: from rules.skip.create_comparer. after: check the
    processed text instead of the text as loaded."""

    text: str
    comparer: Comparer
    negate: bool = False
    after: bool = False

    def matches(self, article: Article) -> bool:
        return self.comparer.matches(article) != self.negate

    @property
    def skip_reason(self) -> str:
        return ("Page doesn't contain: " if self.negate else "Page contains: ") + self.text


@dataclass
class ProcessOptions:
    """The main form's processing options (the check boxes ProcessPage reads)."""

    user_name: str = ""
    bot_mode: bool = False
    ignore_no_bots: bool = False
    no_parse: Collection[str] = ()  # CheckPage Config "nogenfixes"
    no_retf: Collection[str] = ()  # CheckPage Config "noregextypofix"

    unicodify_whole: bool = True
    skip: SkipOptions = field(default_factory=SkipOptions)

    find_and_replace: FindAndReplacer | None = None
    subst_templates: TextRules | None = None
    replace_special: TextRules | None = None
    skip_when_no_far: bool = False
    skip_only_minor_far: bool = False

    categorise: CategorisationOptions = CategorisationOptions.NO_ACTION
    category: str = ""
    category2: str = ""
    remove_sort_key: bool = False
    skip_no_cat_change: bool = False

    general_fixes: bool = False
    replace_reference_tags: bool = True
    restrict_defaultsort_changes: bool = True
    no_mos_compliance_fixes: bool = False
    auto_tag: bool = False
    restrict_orphan_tagging: bool = True
    user_talk_templates: DotNetRegex | None = None

    typos: TypoFixer | None = None
    skip_if_no_typo: bool = False

    append_text: str = ""  # "" = off
    prepend: bool = False
    append_newlines: int = 2
    append_sort_metadata: bool = False

    images: ImageReplaceOptions = ImageReplaceOptions.NO_ACTION
    image_replace: str = ""
    image_with: str = ""
    skip_no_image_change: bool = False

    # RunSkipChecks
    skip_no_changes: bool = True
    skip_whitespace_only: bool = False
    skip_casing_only: bool = False
    skip_minor_general_fixes_only: bool = False
    skip_general_fixes_only: bool = False
    skip_no_page_links: bool = False

    skip_if_contains: ContainsCheck | None = None
    skip_if_not_contains: ContainsCheck | None = None


def process_page(
    article: Article,
    opts: ProcessOptions,
    parsers: Parsers,
    remove_text: HideText,
    main_process: bool = True,
) -> None:
    """MainForm.ProcessPage: apply every enabled change to the page. A step may mark the page
    skipped (article.skip_article, with the reason in article.log). Exceptions propagate: AWB
    logs them and stops, which is the caller's job."""
    process = True
    article.awb_change_article_text(
        "Fixes for Unicode compatibility", parsers.fix_unicode(article.article_text), True
    )
    if article.name in opts.no_parse:
        process = False

    if not opts.ignore_no_bots and not _parsers.check_no_bots(article.article_text, opts.user_name):
        article.awb_skip("Restricted by {{bots}}/{{nobots}}")
        return

    if process and opts.unicodify_whole:
        article.unicodify(opts.skip.skip_no_unicode, parsers, remove_text)

    far = opts.find_and_replace
    if far is not None:
        article.perform_find_and_replace(
            far,
            opts.subst_templates,
            opts.replace_special,
            main_process and opts.skip_when_no_far,
            main_process and opts.skip_only_minor_far,
            False,
        )
        article.do_far_skips(far)
        if article.skip_article:
            return

    if opts.categorise != CategorisationOptions.NO_ACTION:
        article.categorisation(
            opts.categorise,
            parsers,
            opts.skip_no_cat_change,
            opts.category.strip(),
            opts.category2.strip(),
            opts.remove_sort_key,
        )
        if article.skip_article:
            return
        if not opts.general_fixes:
            article.awb_change_article_text(
                "Fix categories", fix_categories(article.article_text), True
            )

    if process:
        if opts.general_fixes:
            article.perform_universal_general_fixes()
        if article.can_do_general_fixes:
            if opts.general_fixes:
                article.perform_general_fixes(
                    parsers,
                    remove_text,
                    opts.skip,
                    opts.replace_reference_tags,
                    opts.restrict_defaultsort_changes,
                    opts.no_mos_compliance_fixes,
                )
            if opts.auto_tag:
                article.auto_tag(parsers, opts.skip.skip_no_tag, opts.restrict_orphan_tagging)
                if main_process and article.skip_article:
                    return
        elif opts.general_fixes:
            if article.namespace_key == namespace.Namespace.USER_TALK:
                article.perform_user_talk_general_fixes(
                    remove_text,
                    opts.user_talk_templates,
                    opts.skip.skip_no_user_talk_templates_substd,
                )
            elif article.can_do_talk_general_fixes:
                article.perform_talk_general_fixes(remove_text)

    typos = opts.typos
    if typos is not None and not opts.bot_mode and not namespace.is_talk(article.namespace_key):
        if article.name not in opts.no_retf:
            article.perform_typo_fixes(typos, opts.skip_if_no_typo)
        elif opts.skip_if_no_typo:
            article.log.awb_skipped(
                "No typo fixes (Title blacklisted from RegExTypoFix Typo Fixing)"
            )
        if article.skip_article:
            return

    if far is not None:
        article.perform_find_and_replace(
            far,
            opts.subst_templates,
            opts.replace_special,
            main_process and opts.skip_when_no_far,
            main_process and opts.skip_only_minor_far,
            True,
        )
        article.do_far_skips(far)
        if article.skip_article:
            return

    if opts.append_text:
        newlines = "\n" * opts.append_newlines
        message = tools.apply_key_words(article.name, opts.append_text)
        if opts.prepend:
            article.awb_change_article_text(
                "Prepended your message", message + newlines + article.article_text, False
            )
        else:
            article.awb_change_article_text(
                "Appended your message", article.article_text + newlines + message, False
            )
        if opts.append_sort_metadata:
            article.perform_meta_data_sort(parsers)

    if opts.images != ImageReplaceOptions.NO_ACTION:
        article.update_images(
            opts.images, opts.image_replace, opts.image_with, opts.skip_no_image_change
        )


def contains_skip_reason(article: Article, opts: ProcessOptions, after: bool) -> str | None:
    """The contains / not contains half of MainForm.SkipChecks, for the checks that run before
    (after=False) or after (after=True) processing. None if the page is not skipped."""
    for check in (opts.skip_if_contains, opts.skip_if_not_contains):
        if check is not None and check.after == after and check.matches(article):
            return check.skip_reason
    return None


def no_change_skip_reason(article: Article, opts: ProcessOptions) -> str | None:
    """RunSkipChecks for a page that ProcessPage did not skip: the "skip if only ... changed"
    options. ("Only cosmetic changes" needs the wiki and is not checked here.)"""
    if (opts.skip_no_changes or opts.bot_mode) and article.no_article_text_changed:
        return "No change"
    if (
        opts.skip_whitespace_only
        and opts.skip_casing_only
        and (article.only_white_space_and_casing_changed)
    ):
        return "Only whitespace/casing changed"
    if opts.skip_whitespace_only and article.only_white_space_changed:
        return "Only whitespace changed"
    if opts.skip_casing_only and article.only_casing_changed:
        return "Only casing changed"
    if (
        opts.skip_minor_general_fixes_only
        and opts.general_fixes
        and article.only_minor_general_fixes_changed
    ):
        return "Only minor general fix changes"
    if opts.skip_general_fixes_only and opts.general_fixes and article.only_general_fixes_changed:
        return "Only general fix changes"
    if opts.skip_no_page_links and not W.WikiLinksOnly.matches(article.article_text):
        return "Page contains no links"
    return None


def has_private_use_characters(text: str) -> bool:
    """AWB skips pages with Private Use Area characters (its edit box broke them). Qt's editor
    keeps them, but the check stays for parity: such characters are almost always errors."""
    return bool(UNICODE_PUA.is_match(text))


def make_default_edit_summary(
    article: Article, user_summary: str, edited_text: str, section_summary: bool = True
) -> str:
    """MainForm.MakeDefaultEditSummary: the user's summary, then what processing did, prefixed
    with /* Section */ when only one level-2 section changed."""
    result = user_summary.strip()
    if article.edit_summary:
        comma = "، " if current_site().lang_code in ("ar", "arz", "fa") else ", "
        result += (comma if result else "") + article.edit_summary
    if section_summary:
        section = _summary.modified_section(article.original_article_text, edited_text)
        if section:
            result = "/* " + section + " */ " + result.lstrip()
    return result


def check_section_summary(summary: str, original_text: str, edited_text: str) -> str:
    """SaveArticle: drop a /* Section */ prefix when the edit no longer touches only that
    section."""
    if not summary.startswith("/*"):
        return summary
    section = _summary.modified_section(original_text, edited_text)
    if not section or ("/* " + section + " */") not in summary:
        end = summary.find("*/")
        return summary[end + 2 :] if end >= 0 else summary
    return summary


def append_summary_tag(
    summary: str, site: SiteConfig | None = None, *, is_bot: bool = False, suppress: bool = False
) -> str:
    """MainForm.AppendUsingAWBSummary: add the "using AWB" tag on Wikimedia wikis (bots may
    suppress it). An empty summary_tag (the wiki defines the AWB change tag) adds nothing."""
    site = site or current_site()
    if not (is_bot and suppress) and site.is_wikimedia_project:
        return _summary.trim(summary, site.summary_tag) + site.summary_tag
    return summary


def clean_category_input(text: str, site: SiteConfig | None = None) -> str:
    """MainForm.CategoryLeave: a category typed as [[Category:Foo]] or Category:foo -> "Foo"
    (any spelling of the namespace, as the wiki's case-insensitive namespace pattern)."""
    site = site or current_site()
    text = text.strip("[]")
    pattern = site.namespaces_case_insensitive[Namespace.CATEGORY]
    text = DotNetRegex("^" + pattern).replace(text, "")
    return turn_first_to_upper(text.strip())


def clean_file_input(text: str, site: SiteConfig | None = None) -> str:
    """MainForm.txtImageReplace_Leave: drop a leading File: (the wiki's name, any case)."""
    site = site or current_site()
    return DotNetRegex(
        "^" + rx.escape(site.namespaces[Namespace.FILE]), DotNetOptions.IGNORE_CASE
    ).replace(text, "")
