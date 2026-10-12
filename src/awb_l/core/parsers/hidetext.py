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
# Ported from AutoWikiBrowser WikiFunctions/Parse/HideText.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Hide parts of the text from rules, then put them back (port of Parse/HideText.cs).

Hidden spans become placeholders "⌊⌊⌊⌊n⌋⌋⌋⌋" (hide) or "⌊⌊⌊⌊Mn⌋⌋⌋⌋" (hide_more), exactly as in AWB:
several WikiRegexes patterns match these markers. A HideText instance holds the hidden spans of one
text at a time, so use one per article and call add_back with the processed text.
"""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Iterable

from awb_l.core import rx
from awb_l.core import wikiregexes as W
from awb_l.core.rx import DotNetMatch, DotNetRegex
from awb_l.core.site import current_site
from awb_l.core.textutil import nested_template_regex

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

_NoWikiIgnoreRegex = _R(
    "<!-- ?(cat(egories)?|\\{\\{.*?stub\\}\\}.*?|other languages?|language links?|inter ?(language|wiki)? ?links|inter ?wiki ?language ?links|inter ?wikis?|The below are interlanguage links\\.?) ?-->",
    O.IGNORE_CASE,
)
_CiteTitleYear = _R(r"(?<=\|\s*(?:trans_)?title\s*=\s*)[^\|{}<>]*[12][0-9]{3}\b")
_CiteTitleYearQ = _R(r'(?<=\|\s*(?:trans_)?title\s*=\s*")[^\|{}<>"]*[12][0-9]{3}\b')
_MathCodeTypoTemplates = nested_template_regex(
    ["math", "code", "As written", "Notatypo", "Not a typo", "Proper name", "Typo"]
)
_RetainBraces = _R(r"(?<=\[\[).+(?=\]\])", O.SINGLELINE)
_RetainStartBraces = _R(r"(?<=\[\[).+", O.SINGLELINE)
_RetainEndBraces = _R(r".+(?=\]\])", O.SINGLELINE)
_All = _R(r".+", O.SINGLELINE)
_WikiCommentsLookAround = _R(r"(?<=<!--)(.*?)(?=-->)", O.SINGLELINE)
_AnyTag = _R(r"<([^<>]+)>")
_ImageToBar = _R(r"^.+?\.[a-zA-Z]{3,4}\s*(?=\||\r\n)", O.MULTILINE)
_SimpleRef = _R(r"<ref>[^<>]+</ref>")
_TemplatesWithContentExemptFromHideMore = nested_template_regex(["Short description"])

HiddenRegex = _R("⌊⌊⌊⌊(\\d*)⌋⌋⌋⌋")
_HiddenMoreRegex = _R("⌊⌊⌊⌊M(\\d*)⌋⌋⌋⌋")


def _replace(matches: Iterable[DotNetMatch], text: str, tokens: list[str], prefix: str = "") -> str:
    """Swap each match for a placeholder, appending the hidden text to tokens."""
    out: list[str] = []
    pos = 0
    for m in matches:
        out.append(text[pos : m.index])
        out.append(f"⌊⌊⌊⌊{prefix}{len(tokens)}⌋⌋⌋⌋")
        tokens.append(m.value)
        pos = m.index + len(m.value)
    out.append(text[pos:])
    return "".join(out)


def _any_tags(text: str) -> list[str]:
    return [m.group(1).strip().lower() for m in _AnyTag.matches(text)]


class HideText:
    def __init__(
        self,
        hide_external_links: bool = False,
        leave_meta_headings: bool = False,
        hide_images: bool = False,
    ) -> None:
        self.hide_external_links = hide_external_links
        self.leave_meta_headings = leave_meta_headings
        self.hide_images = hide_images
        self._hidden: list[str] = []
        self._hidden_unformatted: list[str] = []
        self._more: list[str] = []
        # text before hiding and after it, so add_back can skip work when nothing changed
        self._before_hide = ""
        self._after_hide = ""
        self._before_hide_more = ""
        self._after_hide_more = ""

    # -- hide / add_back ---------------------------------------------------------------------

    def hide(self, article_text: str) -> str:
        """Hide source code, math/code/typo-exempt templates, unformatted text (comment contents
        only, keeping <!-- -->), and optionally external links, interwikis and images."""
        tokens = self._hidden
        tokens.clear()
        self._before_hide = article_text

        def hide_in(matches: Iterable[DotNetMatch], text: str) -> str:
            return _replace(matches, text, tokens)

        any_tags = _any_tags(article_text)
        if any(
            t == "tt" or t.startswith("syntaxhighlight") or t == "code" or t.startswith("source")
            for t in any_tags
        ):
            article_text = hide_in(W.SourceCode.matches(article_text), article_text)

        article_text = hide_in(_MathCodeTypoTemplates.matches(article_text), article_text)

        # hide unformatted text; for comments keep the <!-- --> so FixHeadings can see them
        def unformatted(m: DotNetMatch) -> str:
            res = m.value
            if not self.leave_meta_headings or not _NoWikiIgnoreRegex.is_match(m.value):
                if _WikiCommentsLookAround.is_match(res):
                    res = hide_in(_WikiCommentsLookAround.matches(res), res)
                else:
                    res = hide_in(W.UnformattedText.matches(res), res)
            return res

        article_text = W.UnformattedText.replace(article_text, unformatted)

        if self.hide_external_links:
            article_text = hide_in(W.ExternalLinks.matches(article_text), article_text)
            languages = current_site().interwiki_languages
            interwikis = [
                m
                for m in W.PossibleInterwikis.matches(article_text)
                if m.group(1).lower() in languages
            ]
            article_text = hide_in(interwikis, article_text)

        if self.hide_images:
            s = W.for_site(current_site())

            # hide image links but keep any [[ ]] at either end
            def image(m: DotNetMatch) -> str:
                res = m.value
                # keep URL parameters starting www: FixCitationTemplates fixes these
                if res.lstrip().lower().startswith("www."):
                    return res
                if res.startswith("[["):
                    r = _RetainBraces if res.endswith("]]") else _RetainStartBraces
                elif res.endswith("]]"):
                    r = _RetainEndBraces
                else:
                    r = _All
                return hide_in(r.matches(res), res)

            article_text = s.Images.replace(article_text, image)

            if any("imagemap" in t for t in any_tags):
                article_text = hide_in(W.ImageMap.matches(article_text), article_text)

            # title/trans_title parameters with dates in them, allowing for a leading quote
            article_text = hide_in(_CiteTitleYearQ.matches(article_text), article_text)
            article_text = hide_in(_CiteTitleYear.matches(article_text), article_text)

            # <gallery> needs no File: prefix, so hide anything before the pipe
            if any("gallery" in t for t in any_tags):
                article_text = W.GalleryTag.replace(
                    article_text, lambda m: hide_in(_ImageToBar.matches(m.value), m.value)
                )

        self._after_hide = article_text
        return article_text

    def add_back(self, article_text: str) -> str:
        if self._after_hide == article_text:
            article_text = self._before_hide
            self._before_hide = self._after_hide = ""
        else:
            article_text = _add_back(article_text, HiddenRegex, self._hidden)
        self._hidden.clear()
        return article_text

    # -- unformatted text only --------------------------------------------------------------

    def hide_unformatted(self, article_text: str) -> str:
        self._hidden_unformatted.clear()
        return _replace(
            W.UnformattedText.matches(article_text), article_text, self._hidden_unformatted
        )

    def add_back_unformatted(self, article_text: str) -> str:
        article_text = _add_back(article_text, HiddenRegex, self._hidden_unformatted)
        self._hidden_unformatted.clear()
        return article_text

    # -- more thorough hiding (for typo fixing etc.) ----------------------------------------

    def hide_more(
        self,
        article_text: str,
        hide_only_target_of_wikilink: bool = False,
        hide_wiki_links: bool = True,
        hide_italics: bool = True,
    ) -> str:
        """Hide templates, tags, refs, headings, comments, indented text, links (or only their
        targets), images, quotations and optionally italics."""
        tokens = self._more
        tokens.clear()
        self._before_hide_more = article_text

        def more(matches: Iterable[DotNetMatch], text: str) -> str:
            return _replace(matches, text, tokens, "M")

        def template(m: DotNetMatch) -> str:
            res = m.value
            # for these, hide only the name so that e.g. typos can be fixed in the content
            if _TemplatesWithContentExemptFromHideMore.is_match(res):
                name = _TemplatesWithContentExemptFromHideMore.match(res).group(2)
                return more(_R(rx.escape(name)).matches(res), res)
            return more(W.NestedTemplates.matches(res), res)

        article_text = W.NestedTemplates.replace(article_text, template)
        article_text = more(W.AllTags.matches(article_text), article_text)
        # performance: quickly clear out lots of standard refs
        article_text = more(_SimpleRef.matches(article_text), article_text)

        if self.hide_external_links:
            article_text = more(W.ExternalLinksHTTPOnly.matches(article_text), article_text)
            # performance: the all-protocol regex only if needed
            if "//" in article_text:
                article_text = more(W.ExternalLinks.matches(article_text), article_text)

        article_text = more(W.Headings.matches(article_text), article_text)
        article_text = more(W.Comments.matches(article_text), article_text)
        article_text = more(W.IndentedText.matches(article_text), article_text)

        # links with trailing word characters, e.g. [[link]]age; before the other link rules,
        # which would otherwise take the link without its suffix
        if hide_wiki_links:
            article_text = more(W.WikiLinksOnlyPlusWord.matches(article_text), article_text)

        # unless hiding only link targets, hide whole links including the piped text
        if not hide_only_target_of_wikilink and hide_wiki_links:
            article_text = more(W.SimpleWikiLink.matches(article_text), article_text)

        s = W.for_site(current_site())
        # hiding only targets does not apply to category links: hide these whole
        if hide_only_target_of_wikilink and hide_wiki_links:
            article_text = more(s.Category.matches(article_text), article_text)

        article_text = more(W.Refs.matches(article_text), article_text)

        any_tags = _any_tags(article_text)
        # <gallery> needs no File: prefix, so hide anything before the pipe
        if any("gallery" in t for t in any_tags):
            article_text = W.GalleryTag.replace(
                article_text, lambda m: more(_ImageToBar.matches(m.value), m.value)
            )

        # hide only link targets, leaving the piped text exposed
        if hide_wiki_links:
            article_text = more(W.WikiLink.matches(article_text), article_text)

        # images in templates are already hidden with the templates
        if any("gallery" in t for t in any_tags) or "[[" in article_text:
            article_text = more(s.ImagesNotTemplates.matches(article_text), article_text)

        # untemplated quotations (mostly for typo fixing)
        article_text = more(W.UntemplatedQuotes.matches(article_text), article_text)

        if hide_italics:
            article_text = more(W.Italics.matches(article_text), article_text)

        if any("p style" in t for t in any_tags):
            article_text = more(W.Pstyles.matches(article_text), article_text)

        self._after_hide_more = article_text
        return article_text

    def add_back_more(self, article_text: str) -> str:
        if self._after_hide_more == article_text:
            article_text = self._before_hide_more
            self._before_hide_more = self._after_hide_more = ""
        else:
            article_text = _add_back(article_text, _HiddenMoreRegex, self._more)
        self._more.clear()
        return article_text


def _add_back(article_text: str, marker: DotNetRegex, tokens: list[str]) -> str:
    # loop, as hidden text can itself contain placeholders (nested hiding)
    while marker.is_match(article_text):
        article_text = marker.replace(article_text, lambda m: tokens[int(m.group(1))])
    return article_text
