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
# Ported from AutoWikiBrowser WikiFunctions/TalkPageFixes.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Talk page general fixes (port of WikiFunctions/TalkPageFixes.cs): talk page header and banner
order per [[WP:TPL]], {{WikiProject banner shell}} clean-up, a heading before the first comment.
Much of it is en-wiki only.
"""

from __future__ import annotations

import enum

from pyawb.core import rx, tools
from pyawb.core import wikiregexes as W
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import current_site
from pyawb.core.textutil import nested_template_regex, turn_first_to_upper

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741


class DefaultSortChange(enum.Enum):
    """What to do with a {{DEFAULTSORT}} on the talk page (AWB's DEFAULTSORT enum)."""

    NO_CHANGE = 0
    MOVE_TO_TOP = 1
    MOVE_TO_BOTTOM = 2


_GANomineeTemplate = nested_template_regex(["GA nominee", "GAnominee", "GA"])
_TalkWarningTemplates = nested_template_regex(
    [
        "Community article probation",
        "Censor",
        "Controversial",
        "BLP others",
        "COI editnotice",
        "Notice",
        "warning",
        "Austrian economics sanctions",
    ]
)
_TalkGuidelineTemplates = nested_template_regex(
    ["Not a forum", "Recurring themes", "FAQ", "Round in circles", "Calm", "Pbneutral"]
)
_EnglishVariationsTemplates = nested_template_regex(
    [
        "American English",
        "American English editnotice",
        "Antiguan and Barbudan English",
        "Australian English",
        "Australian English editnotice",
        "Bangladeshi English",
        "British English",
        "British English editnotice",
        "British English Oxford spelling",
        "British English Oxford spelling editnotice",
        "Canadian English",
        "Canadian English editnotice",
        "Ghanaian English",
        "Hiberno-English",
        "Hong Kong English",
        "Indian English",
        "IUPAC spelling",
        "IUPAC spelling US",
        "Jamaican English",
        "Kenyan English",
        "Liberian English",
        "New Zealand English",
        "Nigerian English",
        "Pakistani English",
        "Philippine English",
        "Scottish English",
        "Sierra Leonean English",
        "Singaporean English",
        "South African English",
        "Sri Lankan English",
        "Trinidadian English",
        "Ugandan English",
    ]
)
_TalkHistoryTemplates = nested_template_regex(["Article history", "ArticleHistory"])
_TalkHistoryBTemplates = nested_template_regex(
    [
        "FailedGA",
        "Old prod",
        "Old prod full",
        "Oldprodfull",
        "Afd-merged-from",
        "Old AfD multi",
        "Old AfD",
        "Oldafdfull ",
        "Old peer review",
        "Old CfD",
        "Old RfD",
        "Old XfD multi",
        "Old XfD",
    ]
)
_MilestoneTemplates = nested_template_regex(["DYK talk", "ITN talk", "On this day"])
_ImageRequested = nested_template_regex(["Image requested", "Reqphoto"])
_PressConnected = nested_template_regex(
    ["Press", "Connected contributor", "Wikipedian-bio", "Notable Wikipedian"]
)
_TodoTemplate = nested_template_regex(["To do", "Todo", "To-do"])
_FindSource = nested_template_regex(
    ["Find sources notice", "Reliable sources for medical articles", "Friendly search suggestions"]
)
_Copied = nested_template_regex(["Copied"])
_SplitTemplates = nested_template_regex(["Split from", "Split to"])
_MergeTemplates = nested_template_regex(["Merge from", "Merge-to"])
_WikiProjects = _R(
    nested_template_regex("foo").pattern.replace("[Ff]oo", r"[Ww]ikiProject\b[^{}\|]+")
)

_FirstComment = _R(r"^ {0,4}[:\*\w'\"](?<!_)", O.COMPILED | O.MULTILINE)
_SingleCurlyBrackets = _R(r"{((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))})")
HeadingLevelOne = _R(r"^=([^=](?:.*?[^=])?)=(?:= *⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->)?\s*$", O.MULTILINE)

_BannerShellRedirects = (
    "Article assessment",
    "banner shell",
    "Bannershell",
    "Coopshell",
    "Multiple wikiprojects",
    "Project banner holder",
    "Project shell",
    "Scope shell",
    "WikiProject banner",
    "Wikiproject banner holder",
    "Wikiprojectbanners",
    "WikiProject Banners",
    "WikiProjectBanners",
    "Wikiprojectbannershell",
    "WikiprojectBannerShell",
    "WikiProject bannershell",
    "WikiProject Banner Shell",
    "WikiProject BannerShell",
    "WikiProjectBanner Shell",
    "WikiProjectBannerShell",
    "WikiProject Banners Shell",
    "WikiProject cooperation shell",
    "WikiProject shell",
    "WikiProject Shell",
    "Wpb",
    "WPB",
    "Wpbannershell",
    "WP banner shell",
    "WP Banner Shell",
    "WPBannerShell",
    "Wpbs",
    "WPBS",
)
_Nos = ("blpo",)
_BLPRegex = nested_template_regex(["blp", "BLP", "Blpinfo"])
_BLPORegex = nested_template_regex(["blpo", "BLPO", "BLP others"])
_WPBiographyR = nested_template_regex(
    ["WPBiography", "Wikiproject Biography", "WikiProject Biography", "WPBIO", "Bio"]
)
_WPSongsR = nested_template_regex(
    [
        "WikiProject Songs",
        "WikiProjectSongs",
        "WP Songs",
        "Song",
        "WPSongs",
        "Songs",
        "WikiProject Song",
    ]
)
_WPJazzR = nested_template_regex(
    [
        "WikiProject Jazz",
        "WPJAZZ",
        "WPJazz",
        "WP Jazz",
        "Wikiproject Jazz",
        "WikiProject Jazz music",
        "Jazz-music-project",
    ]
)
_WPAlbumR = nested_template_regex(
    ["WikiProject Albums", "Albums", "WP Albums", "WPAlbums", "Album", "WPALBUMS"]
)
_SirRegex = nested_template_regex(["sir", "Single infobox request"])

_WikiProjectsWPBS = 2
_WikiProject = _R(r"^[Ww]iki ?[Pp]roject ")


def process_talk_page(article_text: str, move_defaultsort: DefaultSortChange) -> tuple[str, bool]:
    """Order the talk page header templates per [[WP:TPL]], move any {{DEFAULTSORT}}, add a
    heading before the first comment if missing. AWB's ref articleText: returns (text, whether a
    {{Skip to talk}} or {{DEFAULTSORT}} was found)."""
    found_skip_to_talk = False
    found_default_sort = False
    default_sort_key = ""

    def skip_toc_me(m: DotNetMatch) -> str:
        nonlocal found_skip_to_talk
        found_skip_to_talk = True
        return ""

    article_text = W.SkipTOCTemplateRegex.replace(article_text, skip_toc_me, 1)
    zeroth_section_original = W.ZerothSection.match(article_text).value
    article_text_original = article_text

    # Correct order per [[WP:TPL]] (reordered below from last to first):
    # 1. {{GA nominee}} 2. {{Skip to talk}} 3. {{Talk header}} 5. warnings 6. talk guidelines
    # 7. English variety 8. article history and milestones 9. WikiProject banner shell
    # 10. {{Image requested}} 11. {{Press}}, {{Connected contributor}} 12. {{To do}}
    # 13. {{Find sources notice}} 14. {{Copied}} 15. {{Split from}}/{{Split to}} 16. merge templates
    wpbs_before = W.WikiProjectBannerShellTemplate.match(article_text).value
    blanklines_in_wpbs_before = "\r\n\r\n" in wpbs_before

    for r in (_MergeTemplates, _SplitTemplates, _Copied, _FindSource):
        article_text = _move_talk_templates(article_text, r)
    article_text = _move_talk_template(article_text, _TodoTemplate)
    article_text = _move_talk_templates(article_text, _PressConnected)
    article_text = _move_talk_template(article_text, _ImageRequested)

    # if template moving leaves blank lines in WPBS then clean this up
    if wpbs_before and not blanklines_in_wpbs_before:
        article_text = W.WikiProjectBannerShellTemplate.replace(
            article_text, lambda m: m.value.replace("\r\n\r\n", "\r\n")
        )

    article_text = wiki_project_banner_shell(article_text)

    article_text = _move_talk_template(article_text, W.WikiProjectBannerShellTemplate)
    if not W.WikiProjectBannerShellTemplate.is_match(article_text):
        article_text = _move_talk_templates(article_text, _WikiProjects)
    article_text = _move_talk_templates(article_text, _MilestoneTemplates)
    article_text = _move_talk_templates(article_text, _TalkHistoryBTemplates)
    article_text = _move_talk_templates(article_text, _TalkHistoryTemplates)
    article_text = _move_talk_template(article_text, _EnglishVariationsTemplates)
    article_text = _move_talk_templates(article_text, _TalkGuidelineTemplates)
    article_text = _move_talk_templates(article_text, _TalkWarningTemplates)

    # 3. {{Talk header}}
    article_text = _move_talk_template(article_text, W.TalkHeaderTemplate)

    # 2. {{Skip to talk}}
    if found_skip_to_talk:
        article_text = "{{Skip to talk}}\r\n" + article_text

    # 1. {{GA nominee}}
    article_text = _move_talk_template(article_text, _GANomineeTemplate)

    if move_defaultsort != DefaultSortChange.NO_CHANGE:

        def defaultsort_me(m: DotNetMatch) -> str:
            nonlocal found_default_sort, default_sort_key
            found_default_sort = True
            captures = m.captures("key")
            if captures:
                default_sort_key = captures[0].strip()
            return ""

        article_text = W.for_site(current_site()).Defaultsort.replace(
            article_text, defaultsort_me, 1
        )
        if found_default_sort and default_sort_key:
            article_text = _set_default_sort(default_sort_key, move_defaultsort, article_text)

    article_text = _add_missing_first_comment_header(article_text)
    article_text = wp_biography(article_text)
    article_text = wp_songs(article_text)
    article_text = wp_jazz(article_text)

    # remove redundant Template: in templates in zeroth section;
    # clean up excess blank lines after template move
    zeroth_section = W.ZerothSection.match(article_text).value
    if zeroth_section:
        # have we only added whitespace? then reset articletext
        if len(zeroth_section) > len(zeroth_section_original) and W.WhiteSpace.replace(
            zeroth_section, ""
        ) == W.WhiteSpace.replace(zeroth_section_original, ""):
            article_text = article_text_original
        else:
            from pyawb.core.parsers import templates as _templates

            zerothbefore = zeroth_section
            # clean excess blank lines at end of zeroth section, leave only one newline;
            # not when later sections: would remove blank line before heading
            if (
                len(zeroth_section) == len(article_text)
                and len(zeroth_section) - len(zeroth_section.strip()) > 2
            ):
                zeroth_section = zeroth_section.strip() + "\r\n"

            zeroth_section = W.ThreeOrMoreNewlines.replace(zeroth_section, "\r\n\r\n")
            zeroth_section = _templates.remove_template_namespace(zeroth_section)
            article_text = article_text.replace(zerothbefore, zeroth_section)

    return article_text, found_skip_to_talk or found_default_sort


def format_default_sort(article_text: str) -> str:
    """{{DEFAULTSORT:key}} format for any defaultsort."""
    return W.for_site(current_site()).Defaultsort.replace(article_text, "{{DEFAULTSORT:${key}}}")


def _set_default_sort(key: str, location: DefaultSortChange, article_text: str) -> str:
    if location == DefaultSortChange.MOVE_TO_TOP:
        return "{{DEFAULTSORT:" + key + "}}\r\n" + article_text
    if location == DefaultSortChange.MOVE_TO_BOTTOM:
        return article_text + "\r\n{{DEFAULTSORT:" + key + "}}"
    return ""


def _move_talk_template(article_text: str, r: DotNetRegex) -> str:
    """Move the (first) matching template to the top of the talk page."""
    m = r.match(article_text)
    if m and m.index > 0:
        # remove existing template – handle case where not at beginning of line
        article_text = article_text.replace(
            m.value, "" if "\r\n" + m.value in article_text else "\r\n"
        )
        # write existing template to top
        article_text = m.value.rstrip() + "\r\n" + article_text.lstrip()
        # ensure any talk header template is now named {{talk header}}
        if "talk" in m.group(1).lower():
            article_text = tools.rename_template(article_text, m.group(1), "Talk header", False)
    return article_text


def _move_talk_templates(article_text: str, r: DotNetRegex) -> str:
    """Move all the matching templates in the zeroth section to the top (en)."""
    original_article_text = article_text
    zeroth_section = W.ZerothSection.match(article_text).value

    # avoid moving commented out tags
    if current_site().lang_code != "en" or not r.is_match(W.Comments.replace(zeroth_section, "")):
        return article_text

    rest_of_article = article_text[len(zeroth_section) :]
    str_tags = ""
    for m in r.matches(zeroth_section):
        str_tags += m.value + "\r\n"
        # additionally, remove whitespace after tag
        zeroth_section = _R(rx.escape(m.value) + r" *(?:\r\n)?").replace(zeroth_section, "")

    article_text = str_tags + zeroth_section + rest_of_article

    # avoid moving commented out tags, round 2
    if tools.unformatted_text_not_changed(original_article_text, article_text):
        return article_text
    return original_article_text


def _add_missing_first_comment_header(article_text: str) -> str:
    """Add a level 2 heading before the first comment if the talk page has none there."""
    # don't match on lines within templates or wiki tables
    spaced = tools.replace_with_spaces(article_text, _SingleCurlyBrackets.matches(article_text))
    spaced = tools.replace_with_spaces(spaced, W.UnformattedText.matches(spaced))
    spaced = tools.replace_with_spaces(spaced, W.GalleryTag.matches(spaced))

    first = _FirstComment.match(spaced)
    if not first:
        return article_text
    first_comment_index = first.index
    level_two = W.HeadingLevelTwo.match(article_text)
    first_level_two_heading = level_two.index if level_two else 99999999

    if first_comment_index < first_level_two_heading:
        # is there a heading level 1 or 3? If yes, change to level 2
        articletexttofirstcomment = article_text[:first_comment_index]
        untitled = current_site().untitled_heading
        if W.HeadingLevelThree.is_match(articletexttofirstcomment):
            article_text = W.HeadingLevelThree.replace(article_text, "==$1==", 1)
        elif HeadingLevelOne.is_match(articletexttofirstcomment):
            article_text = HeadingLevelOne.replace(article_text, "==$1==", 1)
        else:
            article_text = (
                article_text[:first_comment_index]
                + "\r\n=="
                + untitled
                + "==\r\n"
                + article_text[first_comment_index:]
            ).lstrip()
            # whitespace clean
            article_text = article_text.replace(
                "\r\n\r\n\r\n==" + untitled, "\r\n\r\n==" + untitled
            )
    return article_text


def wiki_project_banner_shell(articletext: str) -> str:
    """Fix {{WikiProject banner shell}}: redirects, duplicate and default parameters, blp/blpo
    flags; move other WikiProject banners into it (en)."""
    if current_site().lang_code != "en":
        return articletext

    articletext = _add_wiki_project_banner_shell(articletext)
    wpbs_r = W.WikiProjectBannerShellTemplate
    if not wpbs_r.is_match(articletext):
        return articletext

    # rename redirects
    for redirect in _BannerShellRedirects:
        articletext = tools.rename_template(
            articletext, redirect, "WikiProject banner shell", False
        )

    for m in wpbs_r.matches(articletext):
        new_value = tools.remove_excess_template_pipes(m.value)
        shell_template = tools.get_template_name(new_value).lower().endswith("shell")

        # remove duplicate parameters
        new_value = tools.remove_duplicate_template_parameters(new_value)

        # clean blp=no, blpo=no, collapsed=no
        for the_no in _Nos:
            if tools.get_template_parameter_value(new_value, the_no) == "no":
                new_value = tools.remove_template_parameter(new_value, the_no)

        collapsed_param = tools.get_template_parameter_value(new_value, "collapsed")
        if (shell_template and collapsed_param == "no") or (
            not shell_template and collapsed_param == "yes"
        ):
            new_value = tools.remove_template_parameter(new_value, "collapsed")

        # If {{blpo}} then add blpo=yes to WPBS and remove {{blpo}}
        blpom = _BLPORegex.match(articletext)
        if blpom:
            new_value = tools.set_template_parameter_value(new_value, "blpo", "yes")
            articletext = articletext.replace(blpom.value, "")

        # If {{BLP}} then add blp=yes to WPBS and remove {{BLP}}
        blpm = _BLPRegex.match(articletext)
        if blpm:
            new_value = tools.set_template_parameter_value(new_value, "blp", "yes")
            articletext = articletext.replace(blpm.value, "")

        # merge changes to article text
        if new_value != m.value:
            articletext = articletext.replace(m.value, new_value)

    # Move WikiProjects into WPBS
    if len(wpbs_r.matches(articletext)) == 1:
        wpbs = wpbs_r.match(articletext).value
        new_params = ""
        for m in W.NestedTemplates.matches(articletext):
            template_name = turn_first_to_upper(tools.get_template_name(m.value))
            if (
                template_name.startswith("WikiProject ") or template_name == "Vital article"
            ) and m.value not in wpbs:
                articletext = articletext.replace(m.value, "")
                new_params += tools.newline(m.value)

        if new_params:
            # use old-style 1= if already there
            param1 = tools.get_template_parameter_value(wpbs, "1")
            if param1:
                articletext = articletext.replace(
                    wpbs, tools.set_template_parameter_value(wpbs, "1", param1 + new_params)
                ).lstrip()
            else:
                # new-style, don't create 1=, will require | if no existing templates inside
                if not W.NestedTemplates.is_match(wpbs[2:]):
                    new_params = "|" + new_params
                articletext = articletext.replace(wpbs, wpbs[:-2] + new_params + "}}").lstrip()

    # check living, blpo flags against WPBiography
    for m in wpbs_r.matches(articletext):
        new_value = m.value
        m2 = _WPBiographyR.match(new_value)
        if m2:
            wp_biography_call = m2.value
            living_param = tools.get_template_parameter_value(wp_biography_call, "living")
            if living_param == "yes":
                new_value = tools.set_template_parameter_value(new_value, "blp", "yes")
            elif (
                living_param == "no"
                and tools.get_template_parameter_value(new_value, "blp") == "yes"
            ):
                new_value = tools.remove_template_parameter(new_value, "blp")
            if tools.get_template_parameter_value(wp_biography_call, "blpo") == "yes":
                new_value = tools.set_template_parameter_value(new_value, "blpo", "yes")

        # merge changes to article text
        if new_value != m.value:
            articletext = articletext.replace(m.value, new_value)

    return articletext


def wp_biography(articletext: str) -> str:
    """Fixes to {{WPBiography}}; with living=yes move it above other WikiProjects (en)."""
    if current_site().lang_code != "en":
        return articletext

    m = _WPBiographyR.match(articletext)
    if m:
        newvalue = m.value
        # If {{BLP}} then add living=yes to WPBiography and remove {{BLP}}
        blpm = _BLPRegex.match(articletext)
        if blpm and not tools.get_template_parameter_value(newvalue, "living").lower().startswith(
            "n"
        ):
            newvalue = tools.set_template_parameter_value(newvalue, "living", "yes")
            articletext = _BLPRegex.replace(articletext, "")
        if newvalue and m.value != newvalue:
            articletext = articletext.replace(m.value, newvalue)

    # refresh
    m = _WPBiographyR.match(articletext)
    if not m or not tools.get_template_parameter_value(m.value, "living").lower().startswith("y"):
        return articletext

    # remove {{blp}} if {{WPBiography|living=yes}}
    articletext = _BLPRegex.replace(articletext, "")

    # move above any other WikiProject
    if not W.WikiProjectBannerShellTemplate.is_match(articletext):
        for n in W.NestedTemplates.matches(articletext):
            if n.index < m.index and tools.get_template_name(n.value).startswith("WikiProject "):
                articletext = articletext.replace(m.value, "")
                articletext = articletext[: n.index] + m.value + "\r\n" + articletext[n.index :]
                break

    return articletext


def wp_songs(articletext: str) -> str:
    """Fixes to {{WikiProject Songs}} (en)."""
    if current_site().lang_code != "en":
        return articletext

    m = _WPSongsR.match(articletext)
    if m:
        newvalue = m.value
        # Remove needs-infobox=no
        if tools.get_template_parameter_value(newvalue, "needs-infobox") == "no":
            newvalue = tools.remove_template_parameter(newvalue, "needs-infobox")
        # Remove importance. WPSongs doesn't do importance
        newvalue = tools.remove_template_parameter(newvalue, "importance")
        articletext = articletext.replace(m.value, newvalue)

        # If {{sir}} then add needs-infobox=yes to WPsongs and remove {{sir}}
        if _SirRegex.is_match(articletext):
            newvalue = tools.set_template_parameter_value(newvalue, "needs-infobox", "yes")
            articletext = articletext.replace(m.value, newvalue)
            articletext = _SirRegex.replace(articletext, "")

    return articletext


def wp_jazz(articletext: str) -> str:
    """Fixes to {{WikiProject Jazz}} (en)."""
    if current_site().lang_code != "en":
        return articletext

    m = _WPJazzR.match(articletext)
    if m:
        newvalue = m.value
        # Remove needs-infobox=no
        if tools.get_template_parameter_value(newvalue, "needs-infobox") == "no":
            newvalue = tools.remove_template_parameter(newvalue, "needs-infobox")
        articletext = articletext.replace(m.value, newvalue)

        # If {{WPSongs}} then add song=yes to WPJazz
        if _WPSongsR.is_match(articletext):
            newvalue = tools.set_template_parameter_value(newvalue, "song", "yes")
            articletext = articletext.replace(m.value, newvalue)

        # If {{WPAlbums}} then add album=yes to WPJazz
        if _WPAlbumR.is_match(articletext):
            newvalue = tools.set_template_parameter_value(newvalue, "album", "yes")
            articletext = articletext.replace(m.value, newvalue)

    return articletext


def _add_wiki_project_banner_shell(articletext: str) -> str:
    """Add {{WikiProject banner shell}} when there are 3 or more WikiProject banners and none."""
    if W.WikiProjectBannerShellTemplate.is_match(articletext):
        return articletext

    wiki_project_templates = 0
    wpbs1 = ""
    articletext_local = articletext
    for m in W.NestedTemplates.matches(articletext_local):
        if not _WikiProject.is_match(tools.get_template_name(m.value)):
            continue
        wiki_project_templates += 1
        wpbs1 += tools.newline(m.value)
        articletext_local = articletext_local.replace(m.value, "")

    if wiki_project_templates > _WikiProjectsWPBS:
        # add a WikiProject banner shell
        articletext = (
            "{{WikiProject banner shell|1=" + wpbs1 + tools.newline("}}") + articletext_local
        )

        # clean up excess whitespace
        zeroth_section = W.ZerothSection.match(articletext).value
        rest_of_article = articletext.replace(zeroth_section, "")
        zeroth_section = W.ThreeOrMoreNewlines.replace(zeroth_section, "\r\n\r\n")
        articletext = zeroth_section + rest_of_article

    return articletext
