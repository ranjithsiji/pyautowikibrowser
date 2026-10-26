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

from collections.abc import Callable, Collection, Sequence
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


# Options ▸ "Auto changes skip options" (AWB's "Skip if no…" form, SkipOptions.cs): id, label,
# SkipOptions field
SKIP_IF_NO: tuple[tuple[int, str, str], ...] = (
    (1, "Title boldened", "skip_no_bold_title"),
    (2, "External link bulleted", "skip_no_bulleted_link"),
    (3, "Bad links fixed", "skip_no_bad_link"),
    (4, "Unicodification", "skip_no_unicode"),
    (5, "Auto tag changes", "skip_no_tag"),
    (6, "Header error fixed", "skip_no_header_error"),
    (7, "{{defaultsort}} added", "skip_no_default_sort_added"),
    (8, "User talk templates subst'd", "skip_no_user_talk_templates_substd"),
    (9, "Citation templates dates fixed", "skip_no_cite_template_dates_fixed"),
    (10, "Human category changes", "skip_no_people_categories_fixed"),
)


def skip_options(ids: Collection[int]) -> SkipOptions:
    """SkipOptions with the chosen "Skip if no…" ids on."""
    return SkipOptions(**{name: i in ids for i, _, name in SKIP_IF_NO})


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
    restrict_defaultsort_changes: bool = False  # AWB's menu item is off by default
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


# -- MainForm.ArticleInfo: page statistics and alerts ------------------------------------------


@dataclass(frozen=True)
class PageStatistics:
    words: int = 0
    links: int = 0
    images: int = 0
    categories: int = 0
    interwiki_links: int = 0
    dates_iso: int = 0
    dates_international: int = 0
    dates_american: int = 0

    @property
    def dates(self) -> str:
        """AWB's "Dates O/I/A" (ISO / international / American)."""
        return f"{self.dates_iso}/{self.dates_international}/{self.dates_american}"


@dataclass(frozen=True)
class PageInfo:
    """What AWB's Start tab shows for the page being edited."""

    statistics: PageStatistics
    alerts: tuple[str, ...]
    multiple_wikilinks: tuple[str, ...]  # "Target (count)"


def page_info(
    text: str, article: Article, alerts: Collection[int] = (), typo_fixing: bool = False
) -> PageInfo:
    """MainForm.ArticleInfo for the edited text. alerts: the ids (settings.preferences.ALERTS)
    to show, none meaning all, as AWB's alert preferences; typo_fixing shows the 'sic' alert
    regardless. article supplies the name and namespace; its alert checks are run on text."""
    from pyawb.core.parsers.templates import get_all_template_detail

    s = W.for_site(current_site())
    info = Article(article.name, text, article.namespace_key)
    is_article = info.namespace_key == namespace.Namespace.ARTICLE
    templates = "".join(get_all_template_detail(text))
    word_count = tools.word_count(text)
    cat_count = len(s.Category.matches(text))
    shown: list[str] = []
    every = not alerts

    def on(alert_id: int) -> bool:
        return every or alert_id in alerts

    def counted(alert_id: int, label: str, found: Callable[[], Collection[object]]) -> None:
        if on(alert_id):
            items = found()
            if items:
                shown.append(f"{label} ({len(items)})")

    if (
        on(12)
        and is_article
        and word_count > _parsers.StubMaxWordCount
        and s.Stub.is_match(templates)
    ):
        shown.append("Long article with a stub tag.")
    if on(14) and cat_count == 0 and not namespace.is_talk(info.name):
        shown.append("No category (may be one in a template)")
    if on(7) and is_article and info.has_morefootnotes_and_many_references:
        shown.append("Has 'No/More footnotes' template yet many references")
    if on(6) and info.has_ref_after_reflist:
        shown.append("Has a <ref> after <references/>")
    if on(3) and info.is_disambiguation_page_with_refs:
        shown.append("DAB page with <ref>s")
    if on(16) and is_article and text.startswith("=="):
        shown.append("Starts with heading")
    if on(19) and info.has_bare_references:
        shown.append("Unformatted references")
    if on(13) and len(s.Defaultsort.matches(templates)) > 1:
        shown.append("Multiple DEFAULTSORTs")
    counted(4, "Dead links", info.dead_links)
    counted(1, "Ambiguous citation dates", info.ambiguous_cite_template_dates)
    counted(17, "Unbalanced brackets", info.unbalanced_brackets)
    counted(9, "Invalid citation parameter(s)", info.bad_cite_parameters)
    counted(11, "Links with no target", info.targetless_links)
    counted(10, "Links with double pipes", info.doublepipe_links)
    counted(
        5,
        "Duplicate parameter(s) in WPBannerShell",
        info.duplicate_wiki_project_banner_shell_parameters,
    )
    unknown = info.unknown_wiki_project_banner_shell_parameters() if on(21) else []
    if unknown:
        shown.append(
            "Unknown parameters in WikiProject banner shell:  "
            f"({len(unknown)}) " + ",".join(unknown)
        )
    unknown = info.unknown_multiple_issues_parameters() if on(20) else []
    if unknown:
        shown.append(
            f"Unknown parameters in Multiple issues:  ({len(unknown)}) " + ", ".join(unknown)
        )
    counted(8, "Header(s) with wikilinks", info.wiki_linked_headers)
    counted(18, "Unclosed tag(s)", info.unclosed_tags)
    if on(15) and info.has_see_also_after_notes_references_or_external_links:
        shown.append("See also section out of place")
    if (on(2) or typo_fixing) and info.has_sic_tag:
        shown.append("Contains 'sic' tag")
    if is_article:
        counted(22, "Editor's signature or link to user space", info.user_signature)

    images = s.ImagesCountOnly.matches(text)
    no_images_urls = W.ExternalLinksHTTPOnlyQuick.replace(
        tools.replace_with_spaces(text, images), ""
    )
    dates = tools.dates_count(no_images_urls)
    locale = _parsers.DateLocale
    stats = PageStatistics(
        words=word_count,
        links=tools.link_count(text),
        images=len(images),
        categories=cat_count,
        interwiki_links=tools.interwiki_count(text),
        dates_iso=dates[locale.ISO],
        dates_international=dates[locale.INTERNATIONAL],
        dates_american=dates[locale.AMERICAN],
    )
    return PageInfo(stats, tuple(shown), tuple(tools.duplicate_wiki_links(text)))


def page_errors(
    text: str, article: Article, alerts: Collection[int] = ()
) -> tuple[tuple[int, int], ...]:
    """MainForm.HighlightErrors' sources, for Options ▸ Highlight errors: (start, length) of
    each problem the shown alerts count (alerts as for page_info), in text, first source first
    where two start at the same place, sorted by position."""
    info = Article(article.name, text, article.namespace_key)
    found: dict[int, int] = {}
    checks: list[tuple[int, Callable[[], dict[int, int]]]] = [
        (17, info.unbalanced_brackets),
        (9, info.bad_cite_parameters),
        (5, info.duplicate_wiki_project_banner_shell_parameters),
        (4, info.dead_links),
        (1, info.ambiguous_cite_template_dates),
        (18, info.unclosed_tags),
        (8, info.wiki_linked_headers),
        (11, info.targetless_links),
        (10, info.doublepipe_links),
    ]
    sources = [check() for alert_id, check in checks if not alerts or alert_id in alerts]
    if (not alerts or 15 in alerts) and info.has_see_also_after_notes_references_or_external_links:
        see_also = W.for_site(current_site()).SeeAlso
        heading = next((h for h in W.Headings.matches(text) if see_also.is_match(h.value)), None)
        if heading is not None:
            sources.append({heading.index: heading.length})
    if info.namespace_key == namespace.Namespace.ARTICLE and (not alerts or 22 in alerts):
        sources.append(info.user_signature())
    for errors in sources:
        for start, length in errors.items():
            found.setdefault(start, length)
    return tuple(sorted(found.items()))


_ParserReport = DotNetRegex(
    r"<!--(?:(?!-->).)*?(?:NewPP limit report|Transclusion expansion time report|"
    r"Saved in parser cache)(?:(?!-->).)*-->",
    DotNetOptions.SINGLELINE,
)
_EmptyParagraph = DotNetRegex(r"<p><br ?/?></p>\n")


def same_rendering(
    before_html: str, before_links: Sequence[str], after_html: str, after_links: Sequence[str]
) -> bool:
    """Article.OnlyCosmeticChanged: the edit changes nothing readers see (same categories and
    language links, same HTML once parser reports and empty paragraphs are removed). The
    caller parses the saved page and the edited text (WikiSession.rendering)."""
    if sorted(before_links) != sorted(after_links):
        return False

    def clean(html: str) -> str:
        return _EmptyParagraph.replace(_ParserReport.replace(html, ""), "").strip()

    return clean(before_html) == clean(after_html)
