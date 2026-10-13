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
# Ported from AutoWikiBrowser WikiFunctions/Parse/BoldTitle.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Bold title (port of Parse/BoldTitle.cs): '''embolden''' the first occurrence of the article
title in the lead, after cleaning up bolded and plain self links.
"""

from __future__ import annotations

from pyawb.core import rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import templates as _templates
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import current_site
from pyawb.core.textutil import nested_template_regex, turn_first_to_lower

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

_BracketedAtEndOfLine = _R(r" \(.*?\)$", O.COMPILED)
_BoldTitleAlready3 = _R(r"^\s*({{[^\{\}]+}}\s*)*'''('')?\s*\w", O.COMPILED)
_BoldTitleAlready4 = _R(r"^\s*'''", O.MULTILINE)
_DfnTag = _R(r"<\s*dfn\s*>", O.IGNORE_CASE)
# bio used on it-wiki, automatically bolds link
_NoBoldTitle = nested_template_regex(["year article header", "bio", "Terme défini"])
_RegexFirstBold = _R(r"^(.*?)'''", O.SINGLELINE | O.COMPILED)


def _bolded_self_links(article_title: str, article_text: str) -> str:
    """Delink all bolded self links."""
    esc_title = rx.escape(article_title)
    either = esc_title + "|" + turn_first_to_lower(esc_title)
    plain_link = _R(r"'''\[\[\s*(" + either + r")\s*\]\]'''")
    piped_link = _R(r"'''\[\[\s*(?:" + either + r")\s*\|\s*([^\[\]]+?)\s*\]\]'''")

    article_text = plain_link.replace(article_text, "'''$1'''")
    return piped_link.replace(article_text, "'''$1'''")


def _self_links(zeroth_section: str, article_title: str) -> str:
    zeroth_section_original = zeroth_section
    esc_title = rx.escape(article_title)

    if "'''" + article_title + "'''" not in zeroth_section:
        r1 = _R(r"\[\[\s*" + esc_title + r"\s*\]\]")
        r3 = _R(r"\[\[\s*" + esc_title + r"\s*\|\s*([^\[\]]+?)\s*\]\]")
        # the title is a literal here, so escape $ for the .NET replacement string
        zeroth_section = r1.replace(
            zeroth_section, "'''" + article_title.replace("$", "$$") + "'''"
        )
        zeroth_section = r3.replace(zeroth_section, "'''$1'''")

    lower_title = turn_first_to_lower(article_title)
    if (
        zeroth_section_original == zeroth_section
        and "'''" + lower_title + "'''" not in zeroth_section
    ):
        lower_esc_title = turn_first_to_lower(esc_title)
        r2 = _R(r"\[\[\s*" + lower_esc_title + r"\s*\]\]")
        r4 = _R(r"\[\[\s*" + lower_esc_title + r"\s*\|\s*([^\[\]]+?)\s*\]\]")
        zeroth_section = r2.replace(zeroth_section, "'''" + lower_title.replace("$", "$$") + "'''")
        zeroth_section = r4.replace(zeroth_section, "'''$1'''")

    return zeroth_section


def _added_bold_is_valid(article_text: str, escaped_title: str) -> bool:
    """Whether the bold just added is the first bold in the article and within the first 5% of
    the HideMore article (or immediately after the infobox)."""
    hider2 = HideText(True, True, True)
    regex_bold_added = _R(r"^(.*?)'''(" + escaped_title + ")", O.SINGLELINE | O.IGNORE_CASE)

    bold_added_pos = regex_bold_added.match(article_text).start(2)
    first_bold_pos = _RegexFirstBold.match(article_text).length

    article_text = W.NestedTemplates.replace(article_text, "")
    article_text = hider2.hide_more(article_text)

    # was bold added in first 5% of article?
    in_first_5_percent = False
    articlelength = len(article_text)
    if articlelength > 5:
        # AWB's Substring throws if the trimmed text is shorter than the length; slicing does not
        in_first_5_percent = "'''" in article_text.strip()[: max(articlelength // 20, 5)]

    return in_first_5_percent and bold_added_pos <= first_bold_pos


class BoldTitleMixin:
    """Instance methods of Parsers from BoldTitle.cs."""

    def bold_title(self, article_text: str, article_title: str) -> tuple[str, bool]:
        """'''Embolden''' the first occurrence of the title, if not already bold: clean up bolded
        self wikilinks, then self wikilinks, then add bold. Returns (text, no_change)."""
        from pyawb.core import tools

        all_templates = _templates.get_all_templates(article_text)

        # don't apply in exception cases (<section> used to transclude text in other articles so
        # a self link is a valid use case)
        if _templates.template_exists(all_templates, _NoBoldTitle) or "<section" in article_text:
            return article_text, True

        hider2, hider3 = HideText(), HideText(True, True, True)

        # 1) clean up bolded self links first, provided no noinclude use in article
        after_self_links = _bolded_self_links(article_title, article_text)
        if after_self_links != article_text and not W.IncludeonlyNoinclude.is_match(article_text):
            article_text = after_self_links

        # 2) Clean up self wikilinks
        article_text_at_start = article_text
        zeroth_section = tools.get_zeroth_section(article_text)
        rest_of_article = article_text[len(zeroth_section) :]

        # self links and no bold title: convert first link to bold and return; not if bold in the
        # lead section already or some noinclude transclusion business
        if _self_links(
            zeroth_section, article_title
        ) != zeroth_section and not W.IncludeonlyNoinclude.is_match(article_text):
            # can't hide image descriptions above the lead sentence without hiding the self links
            zeroth_section_hidden = hider2.hide_more(zeroth_section, False, False, False)
            zeroth_section_hidden_original = zeroth_section_hidden
            zeroth_section_hidden = _self_links(zeroth_section_hidden, article_title)
            zeroth_section = hider2.add_back_more(zeroth_section_hidden)

            if zeroth_section_hidden_original != zeroth_section_hidden:
                return zeroth_section + rest_of_article, False

        # Performance check: if article title not in zeroth section have nothing further to do
        title_no_brackets = _BracketedAtEndOfLine.replace(article_title, "")
        if title_no_brackets.lower() not in zeroth_section.lower():
            return article_text_at_start, True

        # 3) '''Embolden''' the first occurrence of the article title

        # ignore date articles (date in American or international format)
        s = W.for_site(current_site())
        if s.Dates2.is_match(article_title) or s.Dates.is_match(article_title):
            return article_text_at_start, True

        esc_title = rx.escape(article_title)
        esc_title_no_brackets = rx.escape(title_no_brackets)
        bold_title_already1 = _R(
            r"'''\s*(" + esc_title + "|" + turn_first_to_lower(esc_title) + ")"
        )
        bold_title_already2 = _R(
            r"'''\s*("
            + esc_title_no_brackets
            + "|"
            + turn_first_to_lower(esc_title_no_brackets)
            + ")"
        )

        # if title in bold already exists in article, or paragraph starts with something in bold,
        # don't change anything; ignore any bold in infoboxes
        if _BoldTitleAlready4.is_match(
            tools.replace_with_spaces(zeroth_section, W.InfoBox.matches(zeroth_section))
        ) or _DfnTag.is_match(zeroth_section):
            return article_text_at_start, True

        article_text_no_infobox = tools.replace_with_spaces(
            article_text, W.InfoBox.matches(article_text)
        )
        if (
            bold_title_already1.is_match(article_text_no_infobox)
            or bold_title_already2.is_match(article_text_no_infobox)
            or _BoldTitleAlready3.is_match(article_text_no_infobox)
        ):
            return article_text_at_start, True

        # so no self links to remove, check for the need to add bold
        article_text_no_templates = W.NestedTemplates.replace(article_text, "")

        # first quick check: ignore articles with some bold in first 5% of article, ignoring
        # infoboxes, dablinks etc.
        fivepc = len(article_text_no_templates) // 20
        if "'''" in article_text_no_templates[:fivepc]:
            return article_text_at_start, True

        regex_bold_no_brackets = _R(
            r"([^\[]|^)("
            + esc_title_no_brackets
            + "|"
            + turn_first_to_lower(esc_title_no_brackets)
            + ")([ ,.:;])"
        )

        zeroth_section_hidden = hider3.hide_more(zeroth_section)
        zeroth_section_hidden_original = zeroth_section_hidden

        # first try title with brackets removed
        zeroth_section_hidden = regex_bold_no_brackets.replace(
            zeroth_section_hidden, "$1'''$2'''$3", 1
        )

        zeroth_section = hider3.add_back_more(zeroth_section_hidden)
        article_text = zeroth_section + rest_of_article

        # check that the bold added is the first bit in bold in the main body of the article
        if zeroth_section_hidden_original != zeroth_section_hidden and _added_bold_is_valid(
            article_text, esc_title_no_brackets
        ):
            return article_text, False

        return article_text_at_start, True
