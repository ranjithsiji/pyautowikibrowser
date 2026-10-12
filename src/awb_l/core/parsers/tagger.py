# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/Parse/Tagger.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Maintenance tagging (port of Parse/Tagger.cs): add or remove stub, uncategorised, orphan,
dead end, underlinked, ibid and empty section tags; date undated tags; tag redirects.

AWB asked the wiki for the page's categories, incoming links and outgoing links (and used fixed
values in unit tests). Here that data comes from a TaggerLookups object, so this module stays
offline: awb_l.api provides one backed by the wiki.
"""

# ruff: noqa: E501

from __future__ import annotations

import datetime
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from awb_l.core import namespace, rx
from awb_l.core import wikiregexes as W
from awb_l.core.parsers import templates as _templates
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.rx import DotNetMatch, DotNetRegex
from awb_l.core.site import EN_MONTH_NAMES, Namespace, current_site
from awb_l.core.textutil import (
    char_upper,
    nested_template_regex,
    turn_first_to_upper,
    turn_first_to_upper_no_project_check,
)

if TYPE_CHECKING:
    from awb_l.core.parsers.metadatasorter import MetaDataSorter

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

MinIncomingLinksToBeConsideredAnOrphan = 3


# -- wiki data -------------------------------------------------------------------------------------


class TaggerLookups(Protocol):
    """Page data from the wiki that Tagger needs."""

    def total_categories(self, article_title: str, categories_in_text: int) -> int:
        """Regular (not stub, not proposed deletion) categories of the page. AWB counts the
        [[Category:]] links in the text and, only if there are none, asks the wiki (templates
        can add categories)."""
        ...

    def orphan_status(
        self, article_title: str, restrict_orphan_tagging: bool
    ) -> tuple[bool, bool, int]:
        """(orphaned, orphaned for tagging, incoming links). orphaned: fewer than
        MinIncomingLinksToBeConsideredAnOrphan mainspace links to the page and its redirects;
        for tagging, with restrict_orphan_tagging, only pages with no incoming links count. On an
        error AWB treats the page as not orphaned: (False, False, 0)."""
        ...

    def mainspace_links(self, article_title: str) -> int:
        """Mainspace links on the rendered page, including those from templates."""
        ...


@dataclass
class OfflineTaggerLookups:
    """No wiki access: count categories in the text only, never treat a page as an orphan, and
    assume template links so that no dead end tag is added."""

    def total_categories(self, article_title: str, categories_in_text: int) -> int:
        return categories_in_text

    def orphan_status(
        self, article_title: str, restrict_orphan_tagging: bool
    ) -> tuple[bool, bool, int]:
        return False, False, 0

    def mainspace_links(self, article_title: str) -> int:
        return 1


@dataclass
class UnitTestTaggerLookups:
    """AWB's Globals.UnitTestMode: the category count is int_value whatever the text has, the
    page is orphaned if bool_value, and the API reports no outgoing links."""

    int_value: int = 0
    bool_value: bool = False

    def total_categories(self, article_title: str, categories_in_text: int) -> int:
        return self.int_value

    def orphan_status(
        self, article_title: str, restrict_orphan_tagging: bool
    ) -> tuple[bool, bool, int]:
        return self.bool_value, self.bool_value, 0

    def mainspace_links(self, article_title: str) -> int:
        return 0


_default_tagger_lookups: TaggerLookups = OfflineTaggerLookups()


def set_default_tagger_lookups(lookups: TaggerLookups) -> None:
    """The lookups for Parsers objects that have none of their own (AWB's tests set the
    Globals.UnitTestMode values this way; the app sets one backed by the wiki)."""
    global _default_tagger_lookups
    _default_tagger_lookups = lookups


# -- static regexes --------------------------------------------------------------------------------

_ImproveCategories = nested_template_regex("improve categories")
_ProposedDeletionDatedEndorsed = nested_template_regex(
    ["Proposed deletion/dated", "Proposed deletion endorsed", "Prod blp/dated"]
)
_Unreferenced = nested_template_regex("unreferenced")
_Drugbox = nested_template_regex(["Drugbox", "Chembox", "PBB", "PBB Summary"])
_MinorPlanetListFooter = nested_template_regex("MinorPlanetListFooter")
_BulletedText = _R(r"\r\n[\*#: ].*")
_TemplateParameter2 = _R(r" \{\{\{2\|\}\}\}", O.COMPILED)
_Rq = nested_template_regex("Rq")
_OtherNonOrphanPageTemplates = nested_template_regex("List of lists")
_IbidOpCitRef = _R(r"<\s*ref\b[^<>]*>\s*(ibid\.?|op\.?\s*cit\.?|loc\.?\s*cit\.?)\b", O.IGNORE_CASE)
_EmptyLevelTwo = _R(r"==\s+==[^=]")
_DeadEndInMultipleIssues = _R(r"\bdead ?end\b")
_Sfn = nested_template_regex("sfn")
_MoreCitationsNeeded = nested_template_regex("More citations needed")
_BLPSourcesTemplate = nested_template_regex("BLP sources")
_Underlinked = nested_template_regex("underlinked")
_CurlyBraceEnd = _R(r"(?:\| *)?}}$", O.COMPILED)
_DateDash = _R(r"(\|\s*[Dd]ate\s*)- *=*", O.COMPILED)
_SpaceLowerLetter = _R(r"( [a-z])")
_CommonPunctuation = _R(r"[\"',\.;:`!\(\)\[\]\?\-–/]", O.COMPILED)


def _month_year() -> DotNetRegex:
    # AWB builds this once with WikiRegexes.MonthsNoGroup of the first wiki
    return _R(r"^\s*" + W.for_site(current_site()).MonthsNoGroup + r" +20\d\d\s*$", O.COMPILED)


# -- Tagger ----------------------------------------------------------------------------------------


class TaggerMixin:
    """Instance methods of Parsers from Tagger.cs."""

    _tagger_lookups: TaggerLookups | None = None

    @property
    def sorter(self) -> MetaDataSorter:  # provided by Parsers
        raise NotImplementedError

    @property
    def tagger_lookups(self) -> TaggerLookups:
        """Where Tagger gets the page's categories and links (the module default if not set)."""
        return _default_tagger_lookups if self._tagger_lookups is None else self._tagger_lookups

    @tagger_lookups.setter
    def tagger_lookups(self, value: TaggerLookups) -> None:
        self._tagger_lookups = value

    def tagger_no_change(
        self, article_text: str, article_title: str, restrict_orphan_tagging: bool
    ) -> tuple[str, bool, str]:
        """Tagger, then TagUpdater. AWB's overload with out noChange and ref summary: returns
        (text, no_change, summary)."""
        new_text, summary = self.tagger(article_text, article_title, restrict_orphan_tagging)
        new_text = tag_updater(new_text)
        return new_text, new_text == article_text, summary

    def tagger(
        self, article_text: str, article_title: str, restrict_orphan_tagging: bool
    ) -> tuple[str, str]:
        """Add or remove cleanup tags (stub, uncategorised, orphan, dead end, underlinked, ibid,
        empty section). AWB's ref summary: returns (text, edit summary of the tag changes)."""
        from awb_l.core import tools
        from awb_l.core.parsers import fixheadings as _fixheadings
        from awb_l.core.parsers import parsers as _parsers
        from awb_l.core.parsers import references as _refs

        if not tagger_permitted(article_text, article_title):
            return article_text, ""

        site = current_site()
        lang = site.lang_code
        s = W.for_site(site)
        self._tags_removed: list[str] = []
        self._tags_added: list[str] = []
        tags_removed, tags_added = self._tags_removed, self._tags_added
        tagsrenamed = 0

        # Performance: check templates against the list of templates used, not the whole text.
        # Due to old-style Multiple issues template need to add full value of any MI templates back in
        templates = " ".join("{{" + t + "}}" for t in _templates.get_all_templates(article_text))
        if W.MultipleIssues.is_match(templates):
            for mi in W.MultipleIssues.matches(article_text):
                templates += mi.value

        comments_stripped = W.Comments.replace(article_text, "")
        comments_categories_stripped = s.Category.replace(comments_stripped, "")
        if s.Defaultsort.is_match(templates):
            comments_categories_stripped = s.Defaultsort.replace(comments_categories_stripped, "")
        comments_stripped, _ = self.sorter.interwikis(comments_stripped, False)

        # remove stub tags from long articles, don't move section stubs
        if s.Stub.is_match(templates) and s.Stub.is_match(comments_stripped):
            # bulleted or indented text should weigh less than simple text.
            # for example, actor stubs may contain large filmographies
            crap_stripped = _BulletedText.replace(
                W.NestedTemplates.replace(comments_categories_stripped, " "), ""
            )
            words = (
                tools.word_count(comments_categories_stripped, 999)
                + tools.word_count(crap_stripped, 999)
            ) // 2
            if words > _parsers.StubMaxWordCount:
                article_text = s.Stub.replace(article_text, _stub_checker).strip()
                tags_removed.append(
                    {"ar": "بذرة", "arz": "تقاوى", "hy": "Անավարտ", "fa": "خرد"}.get(lang, "stub")
                )

        # refresh
        if tags_removed:
            comments_stripped = W.Comments.replace(article_text, "")
            comments_categories_stripped = s.Category.replace(comments_stripped, "")

        # remove disambiguation if disambiguation cleanup exists (en-wiki only)
        if (
            lang == "en"
            and W.DisambigsCleanup.is_match(templates)
            and W.DisambigsCleanup.is_match(comments_stripped)
        ):
            article_text = W.DisambigsGeneral.replace(article_text, "").strip()

        # do orphan tagging before template analysis for categorisation tags
        if site.project != "wikia":
            article_text = self._tag_orphans(article_text, article_title, restrict_orphan_tagging)

        article_text = self._tag_refs_ibid(article_text)
        article_text = self._tag_empty_section(article_text)

        # ignore commented out wikilinks, and any in {{Proposed deletion/dated}}
        for_link_count = comments_stripped
        if _ProposedDeletionDatedEndorsed.is_match(templates):
            for_link_count = _ProposedDeletionDatedEndorsed.replace(for_link_count, "")

        # discount persondata, comments, infoboxes and categories from wikify/underlinked and stub evaluation
        lengthtext = comments_categories_stripped
        if s.Persondata.is_match(templates):
            lengthtext = s.Persondata.replace(comments_categories_stripped, "")
        if W.InfoBox.is_match(templates):
            lengthtext = W.InfoBox.replace(lengthtext, "")
        if _Drugbox.is_match(templates):
            lengthtext = _Drugbox.replace(lengthtext, "")
        if s.ReferenceList.is_match(templates):
            lengthtext = s.ReferenceList.replace(lengthtext, "")

        length = len(lengthtext) + 1
        link_limit = int(0.0025 * length) + 1
        wiki_link_count = tools.link_count(for_link_count, link_limit)
        underlinked = wiki_link_count < 0.0025 * length

        # disable addition of {{underlinked}} for en-wiki
        if site.is_wikipedia_en:
            underlinked = False

        # stubs add non-hidden stub categories, don't count these in categories count; also don't
        # count "Proposed deletion..." cats. Templates may add categories that are not
        # [[Category...]] links, so the lookup asks the wiki when the text has none.
        total_categories = self.tagger_lookups.total_categories(
            article_title, len(regular_categories(comments_stripped, False))
        )

        # remove dead end if > 0 explicit wikilinks on page (don't count any links transcluded from templates)
        if wiki_link_count > 0 and s.DeadEnd.is_match(templates):
            if lang in ("ar", "arz"):
                article_text = s.DeadEnd.replace(article_text, "")
            else:
                text = article_text
                article_text = s.DeadEnd.replace(
                    article_text,
                    lambda m: m.value if tools.is_section_or_reason_template(m.value, text) else "",
                ).lstrip()

            if not s.DeadEnd.is_match(article_text):
                tags_removed.append(
                    {"ar": "نهاية مسدودة", "arz": "نهاية مسدودة", "fa": "بن‌بست"}.get(
                        lang, "deadend"
                    )
                )

        if (
            length <= 300
            and not s.Stub.is_match(comments_categories_stripped)
            and not s.Disambigs.is_match(comments_categories_stripped)
            and not s.SIAs.is_match(comments_categories_stripped)
            and not W.SoftRedirectTemplates.is_match(comments_categories_stripped)
            and not W.NonDeadEndPageTemplates.is_match(comments_categories_stripped)
            # add stub tag. Exclude pages their title starts with "List of..."
            and not _fixheadings.ListOf.is_match(article_title)
            and not W.MeaningsOfMinorPlanetNames.is_match(article_title)
        ):
            stub_tags = {
                "ar": "بذرة",
                "arz": "تقاوى",
                "fa": "خرد",
                "hy": "Անավարտ",
                "sq": "cung",
            }
            if lang in stub_tags:
                article_text += tools.newline("{{" + stub_tags[lang] + "}}", 3)
                tags_added.append(stub_tags[lang])
            elif site.is_wikipedia_en:
                # T382578: WP:STUBSPACING is now one blank line only for en-wiki
                article_text += tools.newline("{{stub}}", 2)
                tags_added.append("stub")
            else:
                article_text += tools.newline("{{stub}}", 3)
                tags_added.append("stub")

            comments_stripped = W.Comments.replace(article_text, "")

        # rename existing {{improve categories}} else add uncategorized tag
        if total_categories == 0 and _ImproveCategories.is_match(templates):
            article_text = tools.rename_template(
                article_text, "improve categories", "Uncategorized"
            )
            templates = tools.rename_template(templates, "improve categories", "Uncategorized")

        # nl wiki doesn't use {{Uncategorized}} template; prevent wictionary redirects from being
        # tagged as uncategorised
        if (
            total_categories == 0
            and not s.Uncategorized.is_match(templates)
            and lang != "nl"
            and site.project != "wikia"
        ):
            # bulleted or indented text should weigh less than simple text.
            # for example, actor stubs may contain large filmographies
            crap_stripped = _BulletedText.replace(
                W.NestedTemplates.replace(comments_categories_stripped, " "), ""
            )
            words = (
                tools.word_count(comments_categories_stripped, 10)
                + tools.word_count(crap_stripped, 10)
            ) // 2

            if words > 6:
                date = s.DateYearMonthParameter
                if s.Stub.is_match(comments_stripped):
                    # add uncategorized stub tag
                    template, tag = {
                        "ar": ("بذرة غير مصنفة", "[[تصنيف:مقالات غير مصنفة|غير مصنفة]]"),
                        "arz": ("تقاوى مش متصنفه", "[[قالب:تقاوى مش متصنفه|تقاوى مش متصنفه]]"),
                        # same template for uncat and uncat stub
                        "fa": ("مقاله‌های خرد رده‌بندی‌نشده", "مقاله‌های رده‌بندی‌نشده"),
                        "hy": ("Կատեգորիա չկա", "Կատեգորիա չկա"),
                        "ru": ("Нет категорий", "Нет категорий"),
                        "sv": ("Okategoriserad", "[[Mall:Okategoriserad|okategoriserad]]"),
                        "en": ("Uncategorized", "[[CAT:UNCAT|uncategorised]]"),
                    }.get(lang, ("Uncategorized stub", "[[CAT:UNCAT|uncategorised]]"))
                else:
                    template, tag = {
                        "ar": ("غير مصنفة", "[[CAT:UNCAT|مقالات غير مصنفة]]"),
                        "arz": ("مش متصنفه", "[[CAT:UNCAT|مش متصنفه]]"),
                        "el": ("Ακατηγοριοποίητο", "[[Πρότυπο:Ακατηγοριοποίητο|ακατηγοριοποίητο]]"),
                        "fa": ("رده‌بندی‌نشده", "رده‌بندی‌نشده"),
                        "hy": ("Կատեգորիա չկա", "Կատեգորիա չկա"),
                        "ru": ("Нет категорий", "Нет категорий"),
                        "sv": ("Okategoriserad", "[[Mall:Okategoriserad|okategoriserad]]"),
                    }.get(lang, ("Uncategorized", "[[CAT:UNCAT|uncategorised]]"))
                article_text += tools.newline("{{" + template + "|", 2) + date + "}}"
                tags_added.append(tag)

        # remove {{Uncategorized}} if > 0 real categories (stub categories not counted)
        if s.Uncategorized.is_match(templates):
            if total_categories > 0:
                article_text = s.Uncategorized.replace(article_text, "").lstrip()
                tags_removed.append(
                    {"ar": "غير مصنفة", "arz": "مش متصنفه", "fa": "رده‌بندی‌نشده"}.get(
                        lang, "uncategorised"
                    )
                )
            elif s.Stub.is_match(comments_stripped):
                # rename uncat to uncat stub if no uncat stub. If uncat and uncat stub, remove uncat.
                uncatstub = any(
                    s.Stub.is_match(u.value) for u in s.Uncategorized.matches(article_text)
                )

                def uncat_me(u2: DotNetMatch) -> str:
                    nonlocal tagsrenamed
                    if not uncatstub:  # rename
                        tagsrenamed += 1
                        renamed = {
                            "ar": "بذرة غير مصنفة",
                            "arz": "تقاوى مش متصنفه",
                            "fa": "خرد رده‌بندی‌نشده",
                        }.get(lang)
                        if renamed is not None:
                            return tools.rename_template(u2.value, renamed)
                    elif not s.Stub.is_match(u2.value):
                        # already uncat stub so remove plain uncat - not enwiki
                        removed = {"ar": "غير مصنفة", "arz": "مش متصنفه", "fa": "رده‌بندی‌نشده"}.get(
                            lang
                        )
                        if removed is not None:
                            tags_removed.append(removed)
                        elif lang != "en":
                            tags_removed.append("uncategorised")
                        return ""
                    return u2.value

                article_text = s.Uncategorized.replace(article_text, uncat_me)

        if (
            wiki_link_count == 0
            and not s.DeadEnd.is_match(article_text)
            and not s.SIAs.is_match(templates)
            and not W.NonDeadEndPageTemplates.is_match(templates)
            and not W.MeaningsOfMinorPlanetNames.is_match(article_title)
            and site.project != "wikia"  # no dead end tag for wikia
        ):
            # use the wiki's count of (mainspace) links, which includes links from templates
            if self.tagger_lookups.mainspace_links(article_title) == 0:
                date = s.DateYearMonthParameter
                # add dead-end tag; no blank line between dead end and orphan tags for ar/arz
                if lang == "ar":
                    article_text = (
                        "{{نهاية مسدودة|"
                        + date
                        + "}}\r\n"
                        + ("" if s.Orphan.is_match(article_text) else "\r\n")
                        + article_text
                    )
                    tags_added.append("[[:تصنيف:مقالات نهاية مسدودة|نهاية مسدودة]]")
                    # if dead end then remove underlinked/wikify
                    if s.Wikify.is_match(article_text):
                        article_text = s.Wikify.replace(article_text, "").lstrip()
                        tags_removed.append("وصلات قليلة")
                elif lang == "arz":
                    article_text = "{{نهايه مسدوده|" + date + "}}\r\n" + article_text
                    tags_added.append("[[:قالب:نهايه مسدوده|نهايه مسدوده]]")
                    if s.Wikify.is_match(article_text):
                        article_text = s.Wikify.replace(article_text, "").lstrip()
                        tags_removed.append("ويكى")
                elif lang == "fa":
                    article_text = "{{بن‌بست|" + date + "}}\r\n" + article_text
                    tags_added.append("بن‌بست")
                    if s.Wikify.is_match(article_text):
                        article_text = s.Wikify.replace(article_text, "").lstrip()
                        tags_removed.append("کم‌پیوند")
                elif (
                    lang != "sv"
                    and not W.Centuryinbox.is_match(article_text)
                    and not _DeadEndInMultipleIssues.is_match(
                        W.MultipleIssues.match(article_text).value.lower()
                    )
                    and not _MinorPlanetListFooter.is_match(article_text)
                ):
                    # Don't add excess newlines between new tags
                    article_text = (
                        "{{Dead end|"
                        + date
                        + "}}"
                        + ("\r\n" if tags_added else "\r\n\r\n")
                        + article_text
                    )
                    tags_added.append("[[CAT:DE|deadend]]")
                    # if dead end then remove underlinked
                    if "underlinked" in article_text.lower():
                        article_text = _Underlinked.replace(article_text, "").lstrip()
                        tags_removed.append("underlinked")

        # add underlinked/wikify tag, don't add underlinked/wikify if {{dead end}} already present
        # Don't tag SIA pages, may create wikilinks from templates
        elif (
            wiki_link_count < 3
            and underlinked
            and length > 400
            and not s.Wikify.is_match(article_text)
            and "wikify" not in W.MultipleIssues.match(article_text).value.lower()
            and not s.DeadEnd.is_match(article_text)
            and not s.SIAs.is_match(article_text)
            and not s.Disambigs.is_match(article_text)
            and not W.NonDeadEndPageTemplates.is_match(article_text)
            and not W.MeaningsOfMinorPlanetNames.is_match(article_title)
        ):
            # Avoid excess newlines between templates
            template_end = "}}\r\n" + ("" if article_text.lstrip().startswith("{{") else "\r\n")
            date = s.DateYearMonthParameter

            if lang == "ar":
                article_text = "{{وصلات قليلة|" + date + template_end + article_text.lstrip()
                tags_added.append("[[وب:وصلات قليلة|وصلات قليلة]]")
            else:
                template, tag = {
                    "arz": ("ويكى", "[[قالب:ويكى|ويكى]]"),
                    "fa": ("کم‌پیوند", "کم‌پیوند"),
                    "sv": ("Ickewiki", "[[WP:PW|ickewiki]]"),
                    "fr": ("À wikifier", "À wikifier"),
                }.get(lang, ("Underlinked", "[[CAT:UL|underlinked]]"))
                article_text = "{{" + template + "|" + date + template_end + article_text
                tags_added.append(tag)

        elif wiki_link_count > 3 and not underlinked and s.Wikify.is_match(templates):
            if lang in ("ar", "arz"):
                article_text = s.Wikify.replace(article_text, "")
            else:
                # remove wikify, except section templates or wikify tags with reason parameter specified
                text = article_text
                article_text = s.Wikify.replace(
                    article_text,
                    lambda m: m.value if tools.is_section_or_reason_template(m.value, text) else "",
                ).lstrip()

            if not s.Wikify.is_match(article_text):
                tags_removed.append(
                    {"ar": "وصلات قليلة", "arz": "ويكى", "fa": "کم‌پیوند", "fr": "À wikifier"}.get(
                        lang, "underlinked"
                    )
                )

        page_has_references = (
            _refs.total_refs_not_grouped(comments_categories_stripped)
            + len(_Sfn.matches(comments_categories_stripped))
            > 0
        )

        # rename unreferenced --> More citations needed if has existing refs, update date;
        # if have both unreferenced and More citations needed, and have some refs then just
        # remove unreferenced provided not section template
        if W.Unreferenced.is_match(templates) and page_has_references:
            text = article_text

            def unreferenced_me(m2: DotNetMatch) -> str:
                nonlocal tagsrenamed
                # no change if section template
                if "section" in m2.value:
                    return m2.value
                if _MoreCitationsNeeded.is_match(text):
                    tags_removed.append("unreferenced")
                    return ""
                tagsrenamed += 1
                return tools.update_template_parameter_value(
                    tools.rename_template(m2.value, "more citations needed"),
                    "date",
                    "{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}",
                )

            article_text = _Unreferenced.replace(article_text, unreferenced_me)

        # rename BLP unsourced --> BLP sources if has existing refs, update date;
        # if have both BLP unsourced and BLP sources, and have some refs then just remove unreferenced
        if W.BLPSources.is_match(templates) and page_has_references:
            text = article_text

            def blp_me(m2: DotNetMatch) -> str:
                nonlocal tagsrenamed
                if _BLPSourcesTemplate.is_match(text):
                    tags_removed.append("BLP unsourced")
                    return ""
                tagsrenamed += 1
                return tools.update_template_parameter_value(
                    tools.rename_template(m2.value, "BLP sources"),
                    "date",
                    "{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}",
                )

            article_text = _parsers.BLPUnsourced.replace(article_text, blp_me)

        if tags_added or tags_removed or tagsrenamed > 0:
            p = _parsers.Parsers()
            hider = HideText()

            article_text = hider.hide_unformatted(article_text)
            article_text = p.multiple_issues(article_text)
            article_text = _parsers.conversions(article_text)
            article_text = hider.add_back_unformatted(article_text)

            # sort again in case tag removal requires whitespace cleanup
            # Don't sort interwikis, we can't specify the correct InterWikiSortOrder
            p.sort_interwikis = False
            article_text = p.sorter.sort(article_text, article_title)

        return article_text, self._prepare_tagger_edit_summary()

    def _tag_orphans(
        self, article_text: str, article_title: str, restrict_orphan_tagging: bool
    ) -> str:
        """Tag pages with too few incoming links as orphans (localised); remove the tag from pages
        with enough. Disambiguation pages, SIAs and soft redirects are never tagged."""
        from awb_l.core import tools

        lang = current_site().lang_code
        s = W.for_site(current_site())
        orphaned, orphaned2, incoming_links = self.tagger_lookups.orphan_status(
            article_title, restrict_orphan_tagging
        )

        if lang == "ru" and incoming_links == 0 and len(_Rq.matches(article_text)) == 1:
            rq_text = _Rq.match(article_text).value
            if "linkless" not in rq_text:
                return article_text.replace(rq_text, rq_text.replace("}}", "|linkless}}"))

        # add orphan tag if applicable, and no disambig nor SIA
        if (
            lang != "sv"
            and orphaned2
            and not s.Orphan.is_match(article_text)
            and not tools.get_template_parameter_value(
                W.MultipleIssues.match(article_text).value, "orphan"
            )
            and not s.Disambigs.is_match(article_text)
            and not s.SIAs.is_match(article_text)
            and not W.Wi.is_match(article_text)
            and "[[Category:Disambiguation pages]]" not in article_text
            and not _OtherNonOrphanPageTemplates.is_match(article_text)
        ):
            template, tag = {
                "ar": ("يتيمة", "[[تصنيف:يتيمة|يتيمة]]"),
                "arz": ("يتيمه", "[[قالب:يتيمه|يتيمه]]"),
                "el": ("Ορφανό", "[[Κατηγορία:Ορφανά λήμματα|ορφανό]]"),
                "fa": ("یتیم", "[[الگو:یتیم|یتیم]]"),
                "hy": ("Որբ", "[[Կատեգորիա:«Որբ» հոդվածներ|Որբ]]"),
                "tr": ("Öksüz", "[[CAT:O|orphan]]"),
                "fr": ("Orphelin", "Orphelin"),
            }.get(lang, ("Orphan", "[[CAT:O|orphan]]"))
            article_text = (
                "{{" + template + "|" + s.DateYearMonthParameter + "}}\r\n\r\n" + article_text
            )
            self._tags_added.append(tag)

        # otherwise consider orphan tag removal; not when "few" parameter specified, human review
        # required then
        elif (
            not orphaned
            and s.Orphan.is_match(article_text)
            and not tools.get_template_parameter_value(s.Orphan.match(article_text).value, "few")
        ):
            # remove newline after tag if present
            article_text = (
                _R(rx.escape(s.Orphan.match(article_text).value) + r"\r?\n?")
                .replace(article_text, "")
                .lstrip()
            )
            self._tags_removed.append(
                {"ar": "يتيمة", "arz": "يتيمه", "fa": "یتیم", "hy": "Որբ", "fr": "orphelin"}.get(
                    lang, "orphan"
                )
            )

        return article_text

    def _tag_refs_ibid(self, article_text: str) -> str:
        """Tag references of 'ibid' with the {{ibid}} cleanup template (en)."""
        if (
            current_site().lang_code == "en"
            and _IbidOpCitRef.is_match(article_text)
            and not W.Ibid.is_match(article_text)
        ):
            self._tags_added.append("Ibid")
            return (
                "{{Ibid|" + W.for_site(current_site()).DateYearMonthParameter + "}}" + article_text
            )
        return article_text

    def _tag_empty_section(self, article_text: str) -> str:
        """Tag empty level-2 sections with {{Empty section}} (en)."""
        from awb_l.core import tools

        # Regex check for performance
        if current_site().lang_code != "en" or not _EmptyLevelTwo.is_match(article_text):
            return article_text

        originalarticle_text = ""
        tagsadded = 0

        while originalarticle_text != article_text:
            originalarticle_text = article_text
            lastpos = -1
            for m in W.HeadingLevelTwo.matches(
                tools.replace_with(article_text, W.UnformattedText, "x")
            ):
                # empty section if only whitespace between two level-2 headings
                if lastpos > -1 and not article_text[lastpos : m.index].strip():
                    article_text = (
                        article_text[: m.index]
                        + "{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n\r\n"
                        + article_text[m.index :]
                    )
                    tagsadded += 1
                    break

                # don't tag single character headings: alpha list where empty section allowed
                if len(m.group(1)) > 1:
                    lastpos = m.index + m.length

        if tagsadded > 0:
            self._tags_added.append(f"Empty section ({tagsadded})")

        return article_text

    def _prepare_tagger_edit_summary(self) -> str:
        from awb_l.core import tools

        lang = current_site().lang_code
        removed, added = self._tags_removed, self._tags_added
        summary = ""

        if removed:
            joined = tools.list_to_string_comma_separator(removed)
            n = len(removed)
            # Reverse order of words for arwiki and arzwiki
            if lang == "ar":
                tags = " وسم " if n == 1 else " وسمي " if n == 2 else " وسوم "
                summary = " أزال" + tags + joined
            elif lang == "arz":
                tags = " وسم " if n == 1 else " وسمين " if n == 2 else " وسوم "
                summary = " شال" + tags + joined
            elif lang == "el":
                summary = (
                    "αφαιρέθηκε η ετικέτα:" if n == 1 else "αφαιρέθηκαν οι ετικέτες:"
                ) + joined
            elif lang == "eo":
                summary = "forigis " + joined + " etikedo" + ("" if n == 1 else "j")
            elif lang == "fa":
                summary = " برچسب" + joined + " حذف شد "
            elif lang == "fr":
                summary = "retrait " + joined + " balise" + ("" if n == 1 else "s")
            elif lang == "hy":
                summary = "ջնջվեց " + joined + " կաղապար" + ("" if n == 1 else "ներ")
            elif lang == "sq":
                summary = ("hoqa etiketën:" if n == 1 else "hoqa etiketat:") + joined
            elif lang == "sv":
                if n == 1:
                    tags = joined + "-mall"
                else:
                    tags = (
                        tools.list_to_string_with_separator_and_word_suffix(
                            removed, "-", ", ", " och "
                        )
                        + "mallar"
                    )
                summary = "tog bort " + tags
            elif lang == "tr":
                summary = "removed " + joined + (" etiketi" if n == 1 else " etiketleri")
            else:
                summary = "removed " + joined + " tag" + ("" if n == 1 else "s")

        if added:
            if summary:
                summary += "، " if lang in ("ar", "arz", "fa") else ", "

            joined = tools.list_to_string_comma_separator(added)
            n = len(added)
            if lang == "ar":
                tags = " وسم " if n == 1 else " وسمي " if n == 2 else " وسوم "
                summary += "أضاف " + tags + joined
            elif lang == "arz":
                tags = " وسم " if n == 1 else " وسمين " if n == 2 else " وسوم "
                summary += "زود " + tags + joined
            elif lang == "el":
                summary += (
                    "προστέθηκε η ετικέτα: " if n == 1 else "προστέθηκαν οι ετικέτες: "
                ) + joined
            elif lang == "eo":
                # AWB tests the number of removed tags here
                summary += "aldonis " + joined + " etikedo" + ("" if len(removed) == 1 else "j")
            elif lang == "fa":
                summary += "برچسب " + joined + " اضافه شد "
            elif lang == "fr":
                summary += "ajout " + joined + " balise" + ("" if n == 1 else "s")
            elif lang == "hy":
                summary += "ավելացրել է " + joined + " կաղապար" + ("" if n == 1 else "ներ")
            elif lang == "sq":
                summary += ("shtova etiketën: " if n == 1 else "shtova etiketat: ") + joined
            elif lang == "sv":
                if n == 1:
                    tags = joined + "-mall"
                else:
                    tags = (
                        tools.list_to_string_with_separator_and_word_suffix(
                            added, "-", ", ", " och "
                        )
                        + "mallar"
                    )
                summary += "lade till " + tags
            elif lang == "tk":
                summary += "eklendi " + joined + (" etiketi" if n == 1 else " etiketleri")
            else:
                summary += "added " + joined + " tag" + ("" if n == 1 else "s")

        return summary


def _stub_checker(m: DotNetMatch) -> str:
    # if stub tag is a section stub tag, don't remove from section in article
    return m.value if _R(current_site().sect_stub).is_match(m.value) else ""


def tagger_permitted(article_text: str, article_title: str) -> bool:
    """Tagger runs on mainspace pages that are not redirects and have no {{wi}}; also on ar-wiki
    namespace 104."""
    from awb_l.core import tools

    if article_title == "Wikipedia:AutoWikiBrowser/Sandbox":
        return True
    # allow for ar-wiki 104
    if (
        current_site().lang_code == "ar"
        and namespace.determine(article_title) == 104
        and not W.CEHar.is_match(article_text)
    ):
        return True
    return not (
        not namespace.is_main_space(article_title)
        or tools.is_redirect_or_soft_redirect(article_text)
        or W.Wi.is_match(article_text)
        or article_title == "Main Page"
    )


ExpandTemplate = Callable[[str, str, dict[DotNetRegex, str], bool], str]


def subst_user_templates(
    talk_page_text: str,
    talk_page_title: str,
    user_talk_templates_regex: DotNetRegex | None,
    expand_template: ExpandTemplate | None = None,
) -> str:
    """Substitute some user talk templates. Expanding needs the wiki (AWB's Tools.ExpandTemplate,
    through the API): expand_template(text, title, {regex: replacement}, include_comment). Without
    it the text is returned unchanged."""
    if user_talk_templates_regex is None or expand_template is None:
        return talk_page_text

    talk_page_text = talk_page_text.replace("{{{subst", "REPLACE_THIS_TEXT")
    regexes = {user_talk_templates_regex: "{{subst:$2}}"}
    talk_page_text = expand_template(talk_page_text, talk_page_title, regexes, True)
    talk_page_text = _TemplateParameter2.replace(talk_page_text, "")
    return talk_page_text.replace("REPLACE_THIS_TEXT", "{{{subst")


class _Named(Protocol):
    @property
    def name(self) -> str: ...


def regular_categories(
    categories: str | Sequence[str | _Named], hide_comments: bool = True
) -> list[str]:
    """Categories that are not stub or proposed deletion categories.

    AWB's overloads: a list of category titles (from the wiki), or wiki text, whose
    [[Category:]] links are used (commented out ones ignored when hide_comments). Returns the
    titles, or for text the category names without namespace.
    """
    from awb_l.core import tools

    if isinstance(categories, str):
        article_text = categories
        # Don't count commented out categories
        if hide_comments:
            article_text = W.MathPreSourceCodeComments.replace(article_text, "")
        s = W.for_site(current_site())
        categories = [m.group(1).strip() for m in s.Category.matches(article_text)]

    def regular(title: str) -> bool:
        name = tools.remove_namespace_string(title)
        return not (
            name.endswith(" stubs")
            or title.endswith(":Stubs")
            or name.startswith("Proposed deletion")
            or "proposed for deletion" in name
            or "proposed deletions" in name
            or name == "Articles created via the Article Wizard"
        )

    titles = [c if isinstance(c, str) else c.name for c in categories]  # titles or Article objects
    return [c for c in titles if regular(c)]


def tag_updater(article_text: str, dated_templates: Iterable[str] | None = None) -> str:
    """Date undated cleanup tags (month and year) from [[WP:AWB/Dated templates]] (by default the
    wiki's SiteConfig.dated_templates), outside unformatted text (comments etc.).

    {{subst:}} within ref tags doesn't work (https://phabricator.wikimedia.org/T4700); AWB
    doesn't do anything about it.
    """
    from awb_l.core.parsers import fixsyntax as _fixsyntax

    dated = frozenset(
        current_site().dated_templates if dated_templates is None else dated_templates
    )
    if not dated:
        return article_text

    # only work to do if article has any of the dated templates in it
    t2 = [t for t in _templates.get_all_templates(article_text) if t in dated]
    if not t2:
        return article_text

    original_article_text = article_text
    r = nested_template_regex(t2)
    article_text = r.replace(article_text, _tag_updater_me)

    # Performance: only worth applying Hide if we made changes to raw articleText
    if original_article_text != article_text:
        ht = HideText()
        article_text = ht.hide(original_article_text)
        article_text = r.replace(article_text, _tag_updater_me)
        article_text = _fixsyntax.fix_syntax_subst_ref_tags(article_text)
        article_text = ht.add_back(article_text)

    return article_text


def _tag_updater_me(m: DotNetMatch) -> str:
    """Date an undated tag, correct date parameter names, remove the template namespace."""
    from awb_l.core import tools

    site = current_site()
    s = W.for_site(site)
    templatecall = m.value

    # rename incorrect template parameter names
    if site.lang_code == "en":
        templatecall = tools.rename_template_parameter(templatecall, "Date", "date")
        templatecall = tools.rename_template_parameter(templatecall, "dates", "date")

        # date- or Date- --> date=
        if (
            tools.get_template_argument(templatecall, 1)
            .lower()
            .replace(" ", "")
            .startswith("date-")
        ):
            templatecall = _DateDash.replace(templatecall, lambda m2: m2.group(1).lower() + "=")

    # remove template namespace in template name
    templatecall = _templates.remove_template_namespace(templatecall)

    # check if template already dated (date= parameter, localised for some wikis)
    date_year_month = s.DateYearMonthParameter
    dateparam = date_year_month[: date_year_month.index("=")]

    # rename date= if localized
    if dateparam != "date":
        templatecall = tools.rename_template_parameter(templatecall, "date", dateparam)

    # date tag needed?
    if not tools.get_template_parameter_value(templatecall, dateparam):
        # remove empty 'date='
        templatecall = tools.remove_template_parameter(templatecall, dateparam)

        # find any dates without date= parameter given, add it
        if site.lang_code == "en" and tools.get_template_argument_count(templatecall) == 1:
            first_arg = tools.get_template_argument(templatecall, 1)
            if _month_year().is_match(first_arg):
                pos = templatecall.index(first_arg)
                templatecall = templatecall[:pos] + "date=" + templatecall[pos:]
            elif first_arg == dateparam:
                pos = templatecall.index(first_arg) + len(first_arg)
                templatecall = templatecall[:pos] + "=" + templatecall[pos:]
                templatecall = tools.remove_template_parameter(templatecall, dateparam)

        if not tools.get_template_parameter_value(templatecall, dateparam):
            return _CurlyBraceEnd.replace(
                templatecall, "|" + date_year_month.replace("$", "$$") + "}}"
            )
    else:
        date_field_value = tools.get_template_parameter_value(templatecall, dateparam)

        # May, 2010 --> May 2010
        if "," in date_field_value and not s.AmericanDates.is_match(date_field_value):
            templatecall = tools.set_template_parameter_value(
                templatecall, dateparam, date_field_value.replace(",", "")
            )
            date_field_value = tools.get_template_parameter_value(templatecall, dateparam)

        # leading zero removed
        if date_field_value.startswith("0"):
            templatecall = tools.set_template_parameter_value(
                templatecall, dateparam, date_field_value.lstrip("0")
            )
            date_field_value = tools.get_template_parameter_value(templatecall, dateparam)

        # full International date?
        if s.InternationalDates.is_match(
            _SpaceLowerLetter.replace(date_field_value, lambda u: u.group(1).upper())
        ):
            space = date_field_value.find(" ")
            if space >= 0:  # AWB's Substring would throw on a date with only &nbsp;
                templatecall = tools.set_template_parameter_value(
                    templatecall, dateparam, date_field_value[space:].strip()
                )
                date_field_value = tools.get_template_parameter_value(templatecall, dateparam)
        # ISO date?
        elif W.ISODates.match(date_field_value).value == date_field_value:
            iso = W.ISODates.match(date_field_value)
            try:
                dt = datetime.date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
            except ValueError:
                # AWB's Convert.ToDateTime throws on an impossible date (2010-02-31); leave it
                dt = None
            if dt is not None:
                date_field_value = f"{EN_MONTH_NAMES[dt.month - 1]} {dt.year}"
                templatecall = tools.set_template_parameter_value(
                    templatecall, dateparam, date_field_value
                )

        # date field starts lower case?
        if (
            site.lang_code != "zh"
            and "CURRENTMONTH" not in date_field_value
            and date_field_value != turn_first_to_upper(date_field_value.lower())
        ):
            templatecall = tools.set_template_parameter_value(
                templatecall, dateparam, turn_first_to_upper(date_field_value.lower())
            )

    return templatecall


def _equals_ordinal_ignore_case(a: str, b: str) -> bool:
    """String.Equals(..., StringComparison.OrdinalIgnoreCase): char by char, simple case mapping."""
    return len(a) == len(b) and all(
        char_upper(x) == char_upper(y) for x, y in zip(a, b, strict=True)
    )


def redirect_tagger(article_text: str, article_title: str) -> str:
    """Tag untagged en-wiki redirects with templates from [[Wikipedia:Template messages/Redirect
    pages]], following [[WP:REDCAT]]."""
    from awb_l.core import tools

    # only for untagged en-wiki redirects
    if (
        not tools.is_redirect(article_text)
        or not current_site().is_wikipedia_en
        or W.Template.is_match(article_text)
    ):
        return article_text

    redirecttarget = tools.redirect_target(article_text)

    # skip self redirects
    if turn_first_to_upper_no_project_check(redirecttarget) == turn_first_to_upper_no_project_check(
        article_title
    ):
        return article_text

    # {{R to xxx namespace}} template for project/help/portal/category/template/user/talk
    if (
        namespace.is_main_space(article_title)
        and not namespace.is_main_space(redirecttarget)
        and not W.NestedTemplates.is_match(article_text)
    ):
        template = {
            Namespace.PROJECT: "{{R to project namespace}}",
            Namespace.HELP: "{{R to help namespace}}",
            Namespace.PORTAL: "{{R to portal namespace}}",
            Namespace.CATEGORY: "{{R to category namespace}}",
            Namespace.TEMPLATE: "{{R to template namespace}}",
            Namespace.USER: "{{R to user namespace}}",
            Namespace.TALK: "{{R to talk namespace}}",
        }.get(namespace.determine(redirecttarget), "")  # some other namespace, cannot tag
        return article_text + " " + template if template else article_text

    # {{R from modification}}: difference is extra/removed/changed punctuation
    target_no_punctuation = _CommonPunctuation.replace(redirecttarget, "")
    if (
        not nested_template_regex(W.RFromModificationList).is_match(article_text)
        and target_no_punctuation != redirecttarget
        and target_no_punctuation == _CommonPunctuation.replace(article_title, "")
    ):
        return article_text + " " + W.RFromModificationString

    # {{R from title without diacritics}}: title and redirect target the same if diacritics
    # removed from redirect target
    no_diacritics = tools.remove_diacritics(redirecttarget)
    if (
        redirecttarget != no_diacritics
        and no_diacritics == article_title
        and not nested_template_regex(W.RFromTitleWithoutDiacriticsList).is_match(article_text)
    ):
        return article_text + " " + W.RFromTitleWithoutDiacriticsString

    # {{R from other capitalisation}}
    if _equals_ordinal_ignore_case(redirecttarget, article_title) and not nested_template_regex(
        W.RFromOtherCapitaliastionList
    ).is_match(article_text):
        return article_text + " " + W.RFromOtherCapitalisationString

    # {{R to section}}
    if "#" in redirecttarget:
        return article_text + " {{R to section}}"

    return article_text
