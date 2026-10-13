# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/Parse/FixHeadings.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Heading fixes (port of Parse/FixHeadings.cs): standard section names, bold and colons in
headings, blank lines before headings, heading levels (CHECKWIKI errors 7, 8, 44, 57).
"""

# ruff: noqa: E501

from __future__ import annotations

from awb_x.core import namespace, rx
from awb_x.core import wikiregexes as W
from awb_x.core.rx import DotNetMatch, DotNetRegex
from awb_x.core.site import current_site
from awb_x.core.textutil import nested_template_regex

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

# -- static regexes (generated from FixHeadings.cs by tools/porting/cs2py.py, then edited) -------

_RegexHeadingsSeeAlso = _R(
    "^(== *)(?:see also|related topics|related articles|internal links|also see):?( *==)",
    O.IGNORE_CASE,
)

_RegexHeadingsExternalLink = _R(
    r"(== *)(external links?|external sites?|outside links?|web ?links?|exterior links?):?( *==)",
    O.IGNORE_CASE,
)

_RegexHeadingsReferencess = _R(r"(== *)(?:reff?e?rr?en[sc]es?:?)( *==)", O.IGNORE_CASE)

_RegexHeadingsSources = _R(r"(== *)(?:sources?:?)( *==)", O.IGNORE_CASE)

_RegexHeadingsFurtherReading = _R(r"(== *)(further readings?:?)( *==)", O.IGNORE_CASE)

_RegexHeadingsLife = _R(r"(== *)(Early|Personal|Adult|Later) Life( *==)", O.IGNORE_CASE)

_RegexHeadingsMembers = _R(r"(== *)(Current|Past|Prior) Members( *==)", O.IGNORE_CASE)

_RegexHeadingsBold = _R(r"^(=+\s*)(?:'''|<[Bb]>)(.*?)(?:'''|</[Bb]>)(\s*=+\s*)$")

_RegexHeadingsTrackListing = _R(r"(== *)track listing( *==)", O.IGNORE_CASE)

_RegexHeadingsLifeCareer = _R(r"(== *)Life and Career( *==)", O.IGNORE_CASE)

_RegexHeadingsCareer = _R(r"(== ?)([a-zA-Z]+) Career( ?==)", O.IGNORE_CASE)

_RegexBadHeaderStartOfArticle = _R(
    r"^={1,4} ?'*(about|description|overview|definition|profile|(?:general )?information|background|intro(?:duction)?|summary|bio(?:graphy)?)'* ?={1,4}",
    O.IGNORE_CASE,
)

_RegexHeadingUpOneLevel = _R(r"^=(==+[^=].*?[^=]==+)=(\r\n?|\n)$", O.MULTILINE)

_ReferencesExternalLinksSeeAlso = _R(
    r"== *([Rr]eferences|[Ee]xternal +[Ll]inks|[Ss]ee +[Aa]lso) *==\s"
)

_ReferencesExternalLinksSeeAlsoValid = _R(r"^== *(References|External links|See also) *==\s")

_ReferencesExternalLinksSeeAlsoUnbalancedRight = _R(
    r"(== *(?:[Rr]eferences|[Ee]xternal +[Ll]inks?|[Ss]ee +[Aa]lso) *=) *\r\n"
)

_RegexHeadingColonAtEnd = _R(r"^(=+)(\s*[^=\s].*?)\:(\s*\1\s*)$")

_RegexHeadingWithBold = _R(r"(?<====+.*?)(?:'''|<[Bb]>)(.*?)(?:'''|</[Bb]>)(?=.*?===+)")

_BadHeadings = (
    r"career",
    r"track listing",
    r" members",
    r"further reading",
    r"related ",
    r" life",
    r"source",
    r" links",
    r"weblink",
    r"external",
    r"also",
    r"reff",
    r"refer",
    r"refr",
    r"<",
    r"	",
    r"'''",
    r":",
)

ListOf = _R(r"^Lists? of", O.COMPILED)

_Anchor2NewlineHeader = _R(
    str(nested_template_regex((r"Anchor", r"Anchors", r"Anchor for redirect", r"ANCHOR", r"Anc")))
    + "\r\n(\r\n)+==",
    O.MULTILINE,
)

_HeadingsIncorrectWhitespaceBefore = _R(
    r"(?<=\S *(?:(\r\n){3,}|\r\n|\s*< *[Bb][Rr] *\/? *>\s*) *)="
)

_HeadingSubHeading = _R(r"^(==+)(.*)\1((?:\r\n\1=+.*\1=+\s*)+)\r\n", O.MULTILINE)

_CommentThenHeading = _R(r"-->\r\n={1,6}(.*?)={1,6}")

_HeadingLevelOne = _R(
    r"^=([^=](?:.*?[^=])?)=(?=(?: *⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->)?\s*$)", O.MULTILINE
)

_DuplicatedSameLevelHeadings = _R(r"^((={2,6}) *([^=\r\n<>]+) *\2)\s+\2 *\3 *\2", O.MULTILINE)

_SpaceNewLineEnd = _R(r" +(\s+)$")


def fix_headings_no_change(article_text: str, article_title: str) -> tuple[str, bool]:
    """AWB's overload FixHeadings(articleText, articleTitle, out noChange); the text is trimmed."""
    new_text = fix_headings(article_text, article_title)
    return new_text.strip(), new_text == article_text


def fix_headings(article_text: str, article_title: str) -> str:
    """Fix ==See also== and similar section errors; remove unnecessary introductory headings and
    clean excess whitespace (but not the optional single space at the start and end)."""
    # remove unnecessary general header from start of article
    article_text = _RegexBadHeaderStartOfArticle.replace(article_text, "")

    # remove identical duplicated headings with only whitespace in between
    article_text = _DuplicatedSameLevelHeadings.replace(article_text, "$1")

    # one blank line before each heading per MOS:HEAD, but not between headings
    if current_site().is_wikipedia_en and _HeadingsIncorrectWhitespaceBefore.is_match(article_text):
        # headings that have a comment on the line before: these are correct as is
        comment_before_headings = [m.group(1) for m in _CommentThenHeading.matches(article_text)]
        text = article_text

        def whitespace_me(m: DotNetMatch) -> str:
            # avoid special case of indented text that may be code with lots of == that matches a heading
            if "==" in m.group(2):
                return m.value

            # if a sub-heading directly after a heading don't add blank line
            for x in _HeadingSubHeading.matches(text):
                if m.group(1) in x.group(3):
                    return m.value

            # if comment on the line before heading then it's correct as is
            if m.group(2) in comment_before_headings:
                return m.value

            return "\r\n\r\n" + m.group(1)

        article_text = W.HeadingsWhitespaceBefore.replace(article_text, whitespace_me)
        article_text = _Anchor2NewlineHeader.replace(
            article_text, lambda m: m.value.replace("\r\n\r\n==", "\r\n==")
        )

    # custom headings, ignoring normal References, External links, See also sections with
    # correct capitalization
    custom_headings = [
        m.value.lower()
        for m in W.Headings.matches(article_text)
        if not _ReferencesExternalLinksSeeAlsoValid.is_match(m.value)
    ]

    # Removes level 2 heading (at start of article only) if it matches pagetitle
    title_lower = article_title.lower()
    if any(title_lower in h for h in custom_headings):
        article_text = _R(r"^\s*(==) *" + rx.escape(article_title) + r" *\1\r\n").replace(
            article_text, ""
        )

    # Performance: apply fixes to all headings only if a custom heading has a bad headings word
    if any(b in h for h in custom_headings for b in _BadHeadings):
        article_text = W.Headings.replace(article_text, _fix_headings_me)

    # CHECKWIKI error 8. Add missing = in some headers
    if any(h.count("=") == 3 for h in custom_headings):
        article_text = _ReferencesExternalLinksSeeAlsoUnbalancedRight.replace(
            article_text, "$1=\r\n"
        )

    # CHECKWIKI error 7: if no level 2 heading in article, remove a level from all headings
    # ('===blah===' to '==blah==' etc.), not counting References, See also or External links;
    # only if all level 3 headings and lower are before the first of those
    if namespace.is_main_space(article_title):
        if not any(W.HeadingLevelTwo.is_match(s) for s in custom_headings):
            article_text_local = _ReferencesExternalLinksSeeAlso.replace(article_text, "")

            originalarticle_text = ""
            while originalarticle_text != article_text:
                originalarticle_text = article_text
                if not W.HeadingLevelTwo.is_match(article_text_local):
                    # get index of last level 3+ heading
                    upone = 0
                    for m in _RegexHeadingUpOneLevel.matches(article_text):
                        upone = max(upone, m.index)

                    if (
                        not _ReferencesExternalLinksSeeAlso.is_match(article_text)
                        or upone < _ReferencesExternalLinksSeeAlso.match(article_text).index
                    ):
                        article_text = _RegexHeadingUpOneLevel.replace(article_text, "$1$2")

                article_text_local = _ReferencesExternalLinksSeeAlso.replace(article_text, "")

        # level 1 headings to level 2 on mainspace
        if any(_HeadingLevelOne.is_match(s) for s in custom_headings):
            article_text = _HeadingLevelOne.replace(article_text, "==$1==")

    return article_text


def _fix_headings_me(m: DotNetMatch) -> str:
    """Fixes to one heading."""
    h_after = W.Br.replace(m.value, "")
    h_after = W.Big.replace(h_after, "$1").lstrip(" ")

    # clean whitespace
    h_after = h_after.replace("\t", " ")
    while _SpaceNewLineEnd.is_match(h_after):
        h_after = _SpaceNewLineEnd.replace(h_after, "$1")

    # Removes bold from heading - CHECKWIKI error 44
    h_after = _RegexHeadingsBold.replace(h_after, "$1$2$3")

    # Removes colon at end of heading - CHECKWIKI error 57
    h_after = _RegexHeadingColonAtEnd.replace(h_after, "$1$2$3")

    h_after = _RegexHeadingsExternalLink.replace(h_after, "$1External links$3")

    h_after = _RegexHeadingsFurtherReading.replace(h_after, "$1Further reading$3")
    h_after = _RegexHeadingsLife.replace(h_after, "$1$2 life$3")
    h_after = _RegexHeadingsMembers.replace(h_after, "$1$2 members$3")
    h_after = _RegexHeadingsTrackListing.replace(h_after, "$1Track listing$2")
    h_after = _RegexHeadingsLifeCareer.replace(h_after, "$1Life and career$2")
    h_after = _RegexHeadingsCareer.replace(h_after, "$1$2 career$3")
    h_after = _RegexHeadingsSeeAlso.replace(h_after, "$1See also$2")

    # Plural per [[WP:FNNR]]
    h_after = _RegexHeadingsReferencess.replace(
        h_after, lambda m2: m2.group(1) + "References" + m2.group(2)
    )
    h_after = _RegexHeadingsSources.replace(
        h_after, lambda m2: m2.group(1) + "Sources" + m2.group(2)
    )

    # Removes bold from level 3 headers and below, as it makes no visible difference
    h_after = _RegexHeadingWithBold.replace(h_after, "$1")

    return W.EmptyBold.replace(h_after, "")
