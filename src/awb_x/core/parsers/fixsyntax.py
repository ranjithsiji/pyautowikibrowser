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
# Ported from AutoWikiBrowser WikiFunctions/Parse/FixSyntax.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Wiki syntax fixes (port of Parse/FixSyntax.cs): HTML to wiki markup, broken brackets and
external links, <br> and <p> clean-up, ISBN/PMID formatting, DEFAULTSORT, small tags and more.

Namespace-dependent regexes are built per wiki (AWB built them once, for the first wiki).
"""

# ruff: noqa: E501

from __future__ import annotations

import datetime
import functools

from awb_x.core import namespace, rx
from awb_x.core import wikiregexes as W
from awb_x.core.parsers import fixdates as _fixdates
from awb_x.core.parsers import templates as _templates
from awb_x.core.parsers import unbalancedbrackets as _ub
from awb_x.core.rx import DotNetMatch, DotNetRegex
from awb_x.core.site import Namespace, SiteConfig, current_site
from awb_x.core.textutil import nested_template_regex

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

# -- static regexes (generated from FixSyntax.cs by tools/porting/cs2py.py, then edited) ----------

# regexes for external link match on balanced bracket
_DoubleBracketAtStartOfExternalLink = _R(
    r"\[\[+(https?:/(?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])",
    O.IGNORE_CASE | O.COMPILED,
)

_DoubleBracketAtEndOfExternalLink = _R(
    r"(\[ *https?:/(?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])\](?!\])",
    O.IGNORE_CASE | O.COMPILED,
)

_TripleBracketAtEndOfExternalLink = _R(
    r"(\[ *https?:/(?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])\]\](?!\])",
    O.IGNORE_CASE | O.COMPILED,
)

_DoubleBracketAtEndOfExternalLinkWithinImage = _R(
    r"(\[https?:/(?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!)))\](?=\]{3})",
    O.IGNORE_CASE | O.COMPILED,
)

_ListExternalLinkEndsCurlyBrace = _R(
    r"^(\* *\[https?://[^<>\[\]]+?)\)\s*$", O.MULTILINE | O.COMPILED
)

_SyntaxRegexWikilinkMissingClosingBracket = _R(
    r"\[\[([^][]*?)\|?\](?=[^\]]*?(?:$|\[|\n))", O.COMPILED
)

_SyntaxRegexWikilinkMissingOpeningBracket = _R(
    r"(?<=(?:^|\]|\n)[^\[]*?)\[([^][]*?)\]\](?!\])", O.COMPILED
)

_ExternalLinksStart = _R(
    r"^\[ *(?:https?|ftp|mailto|irc|gopher|telnet|nntp|worldwind|news|svn)://", O.IGNORE_CASE
)

_SyntaxRegexListRowBrTag = _R(
    r"((?:\r\n|^)[#\*:;]+.*?) *(?:<[/\\]?br ?[/\\]? ?>)+[ \t]*(?=\r\n|$)", O.IGNORE_CASE
)

_SyntaxRegexListRowBrTagMiddle = _R(
    r"^([#\*:;]+.*?)\s*(?:<[/\\]?br ?[/\\]? ?>)+[ \t]*\r\n([#\*:;]+)", O.MULTILINE | O.IGNORE_CASE
)

_SyntaxRegexBrNewline = _R(r"<[/\\]?[Bb][Rr] ?[/\\]? ?>[ \t]*(\r\n|$)")

_SyntaxRegexListRowBrTagStart = _R(r"<[/\\]?br ?[/\\]? ?>[ \t]*(\r\n[#\*:;]+)", O.IGNORE_CASE)

_SyntaxRegexItalicBoldEm = _R(r"< *(i|b) *>(.*?)< */ *\1 *>", O.IGNORE_CASE | O.COMPILED)

# Matches <p> tags only if current line does not start from ! or | (indicator of table cells),
# plus any spaces after
_SyntaxRemoveParagraphs = _R(r"(?<!^[!\|].*)</? ?[Pp]> *", O.MULTILINE)

# Match execss <br> tags only if current line does not start from ! or | (indicator of table
# cells)
_SyntaxRemoveBr = _R(
    r"(?:(?:<br[\s/]*> *){2,}|\r\n<br[\s/]*>\r\n<br[\s/]*>\r\n)(?<!^[!\|].*)",
    O.IGNORE_CASE | O.MULTILINE,
)

_MaintanceTemplateWithBr = _R(
    r"({{" + W.MaintanceTemplatesString + r"\s*\|[^\}]*}}(\r\n)?)\<br[\s/]*\>",
    O.IGNORE_CASE | O.MULTILINE,
)

_SyntaxRemoveBrQuick = _R(r"<br[\s/]*>\s*<br[\s/]*>", O.IGNORE_CASE)

_MultipleHttpInLink = _R(r"(?<=[\s\[>=])(https?(?::?/+|:/*)) *(\1)+", O.IGNORE_CASE)

_MultipleFtpInLink = _R(r"(?<=[\s\[>=])(ftp(?::?/+|:/*))(\1)+", O.IGNORE_CASE)

_PipedExternalLink = _R(
    "(\\[\\w+://[^\\]\\[<>\\\"\\s]*?\\s*)(?: +\\||\\|([ ']))(?=[^\\[\\]\\|]*\\])"
)

_HttpLinks = _R(r"http[htps:/ %]+")

_MissingColonInHttpLink = _R(r"(?<=[\s\[>=](?:ht|f))(tps?)(?://?:?|:(?::+//)?)(\w+)", O.COMPILED)

_SingleTripleSlashInHttpLink = _R(
    r"(?<=[\s\[>=](?:ht|f))(tps?):(?:/|////?)(\w+)", O.IGNORE_CASE | O.COMPILED
)

_CellpaddingTypo = _R(
    r'({\s*\|\s*class\s*=\s*"wikitable[^}]*?)cel(?:lpa|pad?)ding\b', O.IGNORE_CASE
)

_CellpaddingTypoQuick = _R(r"\bcel(?:lpa|pad?)ding\b", O.IGNORE_CASE)

# https://en.wikipedia.org/wiki/Wikipedia_talk:AutoWikiBrowser/Feature_requests#Remove_.3Cfont.3E_
# tags
_RemoveNoPropertyFontTags = _R(r"<font>([^<>]+)</font>", O.IGNORE_CASE)

# for fixing unbalanced brackets
_RefTemplateIncorrectBracesAtEnd = _R(
    r"(?<=<ref(?:\s*name\s*=[^{}<>/]+?\s*)?>\s*)({{\s*[Cc]it[ae][^{}<>]+?)(?:}\]?|\)\))?(?=\s*</ref>)",
    O.COMPILED,
)

_RefExternalLinkUsingBraces = _R(
    r"(?<=<ref(?:\s*name\s*=[^{}<>]+?\s*)?>)\s*{{(\s*https?://[^{}\s\r\n]+)(\s+[^{}]+)?\s*}}\s*(</ref>)",
    O.COMPILED,
)

_RefURLMissingHttp = _R(r"(<ref(?:\s*name\s*=[^{}<>]+?\s*)?>\[?)\s*www\.", O.COMPILED)

_TemplateIncorrectBracesAtStart = _R(r"(?:{\[|\[{)([^{}\[\]]+}})", O.COMPILED)

_CitationTemplateSingleBraceAtStart = _R(r"(?<=[^{])({\s*[Cc]it[ae])", O.COMPILED)

_ReferenceTemplateQuadBracesAtEnd = _R(
    r"(?<=<ref(?:\s*name\s*=[^{}<>]+?\s*)?>\s*{{[^{}]+)}}(}}\s*</ref>)", O.COMPILED
)

_ReferenceTemplateQuadBracesAtEndQuick = _R(r"}}}}\s*</ref>")

_CitationTemplateIncorrectBraceAtStart = _R(
    r"(?<=<ref(?:\s*name\s*=[^{}<>]+?\s*)?>){\[([Cc]it[ae])", O.COMPILED
)

_CitationTemplateIncorrectBracesAtEnd = _R(
    r"(<ref(?:\s*name\s*=[^{}<>]+?\s*)?>\s*{{[Cc]it[ae][^{}]+?)(?:}\]|\]}|{})(?=\s*</ref>)",
    O.COMPILED,
)

_CitationTemplateIncorrectBracesAtEndQuick = _R(r"(?:}\]|\]}|{})(?=\s*</ref>)")

_RefExternalLinkMissingStartBracket = _R(
    r"(<ref(?:\s*name\s*=[^{}<>]+?\s*)?>[^{}\[\]<>]*?){?((?:ht|f)tps?://[^{}\[\]<>]+\][^{}\[\]<>]*</ref>)",
    O.COMPILED | O.IGNORE_CASE,
)

_RefExternalLinkMissingEndBracket = _R(
    r"(<ref(?:\s*name\s*=[^{}<>]+?\s*)?>[^{}\[\]<>]*?\[\s*(?:ht|f)tps?://[^{}\[\]<>]+)}?(</ref>)",
    O.COMPILED | O.IGNORE_CASE,
)

_RefCitationMissingOpeningBraces = _R(
    r"(<\s*ref(?:\s+name\s*=[^<>]*?)?\s*>\s*)\(?\(?([Cc]it[ae][^{}]+}}\s*</ref>)", O.COMPILED
)

_DeadlinkOutsideRef = _R(r"(</ref>) ?(\{\{[Dd]ead ?link\s*\|\s*date\s*=[^{}\|]+\}\})", O.COMPILED)

# refs with wording and bare link: combine the two
_WordingIntoBareExternalLinks = _R(
    r"(<ref(?:\s*name\s*=[^{}<>]+?\s*)?>\s*)([^<>{}\[\]\r\n]{3,70}?)[\.,::]?\s*\[\s*((?:[Hh]ttps?|[Ff]tp|[Mm]ailto)://[^\ \n\r<>]+)\s*\](?=\s*</ref>)",
    O.COMPILED,
)

# space needed between word and external link
_ExternalLinkWordSpacingBefore = _R(
    r"(?<=\w)(\[(?:https?|ftp|mailto|irc|gopher|telnet|nntp|worldwind|news|svn)://.*?\])",
    O.COMPILED,
)

_ExternalLinkWordSpacingAfter = _R(
    r"(\[(?:https?|ftp|mailto|irc|gopher|telnet|nntp|worldwind|news|svn)://[^\]\[<>]*?\])(\w)",
    O.COMPILED,
)

_WikilinkEndsBr = _R(r"<br[\s/]*>\s*\]\]$", O.COMPILED | O.IGNORE_CASE)

# for correcting square brackets within external links
_SquareBracketsInExternalLinks = _R(
    r"(\[https?://(?>[^\[\]<>]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])", O.COMPILED
)

# CHECKWIKI error 2: fix incorrect <br> of <br.>, <\br>, <br\> and <br./> etc.
_IncorrectBr = _R(
    r"<(\\ *br *| *br *\\ *| *br\. */?| *br */([a-z/0-9•\-]|br)| *br *\?|/ *br */?)>",
    O.IGNORE_CASE | O.COMPILED,
)

# CHECKWIKI error 2: https://en.wikipedia.org/wiki/Wikipedia:HTML5#Other_obsolete_attributes
_IncorrectBr2 = _R(
    r'<br\s*clear\s*=\s*"?(both|all|left|right)"?\s*\/?>', O.IGNORE_CASE | O.COMPILED
)

_IncorrectBr3 = _R(
    r'<br\s*style\s*=\s*"?clear\:\s?(all|both|left|right)\;?"?(\s*clear=\s*"?(all|left|right)"?)?\s*/?>',
    O.IGNORE_CASE | O.COMPILED,
)

_IncorrectClosingHtmlTags = _R(r"< */?(center|gallery|small|sub|sup|i) *[\\/] *>")

_SyntaxRegexHorizontalRule = _R(r"^(<hr>|-{5,})", O.COMPILED | O.MULTILINE)

_SyntaxRegexHeadingWithHorizontalRule = _R(
    "(^==?[^=]*==?)\r\n(\r\n)?----+", O.COMPILED | O.MULTILINE
)

_SyntaxRegexHTTPNumber = _R(r"HTTP/\d\.", O.COMPILED)

_SyntaxRegexISBN = _R(r"(?<![:/])(?:ISBN(?:[\-–]1[03])?:|\[\[ISBN\]\]|ISBN ?\t)\s*(\d)", O.COMPILED)

_SyntaxRegexISBN2 = _R(r"(?<![:/])ISBN[\-–](?!1[03]\b)", O.COMPILED)

_SyntaxRegexISBN2a = _R(r"ISBN–(1[03]\b)")

_SyntaxRegexISBN3 = _R(
    r"\[\[ISBN\]\]\s\[\[Special\:BookSources[^\|]*\|(?:<bdi>)?([^\]]*?)(?:</?bdi>)?\]\]", O.COMPILED
)

_SyntaxRegexISBN4 = _R(
    r"\[\[International Standard Book Number\|ISBN\]\]\:?\s\[\[Special\:BookSources[^\|]*\|(?:<bdi>)?([^\]]*?)(?:</?bdi>)?\]\]",
    O.COMPILED,
)

_ISBNEndash = _R(r"ISBN ([0-9][0-9–]+[0-9X])\b")

_ISBNx = _R(r"(ISBN [0-9\-]{9,14})x", O.COMPILED)

_SyntaxRegexPMID = _R(r"(?<!\[\[)(PMID): *(\d)", O.COMPILED)

_SyntaxRegexExternalLinkOnWholeLine = _R(r"^\[(\s*http.*?)\]$", O.COMPILED | O.SINGLELINE)

_SyntaxRegexClosingBracket = _R(r"([^]])\]([^]]|$)", O.COMPILED)

_SyntaxRegexOpeningBracket = _R(r"([^[]|^)\[([^[])", O.COMPILED)

_SimpleTags = _R(r'<[^>"\-=]+>')

_CiteTemplateWithSquareBrackets = _R(
    r"(\<ref[^\[]*)\[\[(cite ?(journal|web|book|news)[^\]]*)\]\](\<\/ref\>)", O.COMPILED
)

# Matches double piped links e.g. [[foo||bar]] (CHECKWIKI error 32)
_DoublePipeInWikiLink = _R(r"(?<=\[\[[^\[\[\r\n\|{}]+)\|\|(?=[^\[\[\r\n\|{}]+\]\])", O.COMPILED)

# Matches empty gallery, center, blockquote, small, nowiki, noinclude, includeonly, sub or sup
# tags (zero or more whitespace). Optionally with additional parameters
_EmptyTags = _R(
    r"<\s*(gallery|center|blockquote|small|noinclude|nowiki|includeonly|su[bp])\s*(\s+[^<>]*)?>\s*<\s*/\s*\1\s*>",
    O.IGNORE_CASE,
)

_ExternalLinkEndsISBN = _R(r"(\[http[^[\]]+? +[^[\]]+?)[,;:]? +(ISBN +[0-9-]+X?\.?) ?\]")

_RedirectBracketsWithPrefix = _R(r"[=:] ?\[\[", O.COMPILED)

_TooManyOpenSquareBrackets = _R(r"\[{3,4}", O.COMPILED)

_TooManyCloseSquareBrackets = _R(r"\]{3,4}", O.COMPILED)


_LegendTemplate = nested_template_regex(r"legend")

_TableEnd = _R(r"^\|}", O.MULTILINE)

_IndexNoIndexMagicWord = _R(r"^__(NO)?INDEX__(\s+|$)", O.MULTILINE)

# names other modules use (Parsers.FixBrParagraphs)
SyntaxRemoveBrQuick = _SyntaxRemoveBrQuick
SyntaxRemoveBr = _SyntaxRemoveBr
SyntaxRemoveParagraphs = _SyntaxRemoveParagraphs
SyntaxRegexListRowBrTagStart = _SyntaxRegexListRowBrTagStart


@functools.lru_cache(maxsize=32)
def _external_link_to_image_url(site: SiteConfig) -> DotNetRegex:
    return _R(
        r"\[?\[" + site.namespaces_case_insensitive[Namespace.FILE] + r"(http:\/\/.*?)\]\]?",
        O.IGNORE_CASE,
    )


@functools.lru_cache(maxsize=32)
def _file_with_http(site: SiteConfig) -> DotNetRegex:
    return _R(r"\[\[" + site.namespaces_case_insensitive[Namespace.FILE] + ":[^]]*http")


@functools.lru_cache(maxsize=32)
def _template_namespace(site: SiteConfig) -> DotNetRegex:
    return _R(site.namespaces_case_insensitive[Namespace.TEMPLATE])


_Disambiguation = nested_template_regex("disambiguation")
_InvalidRefOpening = _R(r"[\.,] ?\/?ref")
_InvalidRefOpeningFix = _R(r"([\.,]) ?ref(\s*name\s*=[^{}<>]+?\s*)?>")
_IOrB = _R(r"<(i|b)\b")
_Whitespace = _R(r"\s")
_GoodHttp = _R(r"^https?://[htps]*$")


def fix_syntax(article_text: str) -> str:
    """Fix wiki syntax errors (many CHECKWIKI errors): see the comments below for each fix."""
    from awb_x.core import tools

    site = current_site()
    all_templates = _templates.get_all_templates(article_text)
    all_templates_detail = _templates.get_all_template_detail(article_text)
    ssb_mc = _ub.SingleSquareBrackets.matches(article_text)
    original = article_text

    if site.lang_code == "en":
        # DEFAULTSORT whitespace - CHECKWIKI error 88, 89
        article_text = _fix_syntax_default_sort(article_text)
        # this category should not be added directly: remove if the template is present, else
        # replace it with the template
        if any(m.value == "[[Category:Disambiguation pages]]" for m in ssb_mc):
            article_text = article_text.replace(
                "[[Category:Disambiguation pages]]",
                ""
                if _templates.template_exists(all_templates, _Disambiguation)
                else "{{Disambiguation}}",
            )
        # <br> after maintenance templates
        article_text = _MaintanceTemplateWithBr.replace(article_text, "$1")

    if _templates.template_exists(all_templates, W.MagicWordTemplates):
        article_text = tools.template_to_magic_word(article_text)

    # the simple html tags (no attributes) used, so html tag fixes run only when needed
    simple_tags = list(
        dict.fromkeys(
            _Whitespace.replace(m.value, "").lower() for m in _SimpleTags.matches(article_text)
        )
    )

    # <sup/>, <sub/>, <center/>, <small/>, <i/> etc.
    if any(s != "<br/>" and (s.endswith("/>") or "\\" in s) for s in simple_tags):
        article_text = _IncorrectClosingHtmlTags.replace(article_text, "</$1>")

    # <strike> is not supported in HTML5 - CHECKWIKI error 42
    if any("strike" in s for s in simple_tags):
        article_text = article_text.replace("<strike>", "<s>").replace("</strike>", "</s>")

    # empty <gallery>, <center>, <blockquote>, <nowiki>, <sub>, <sup> tags (allowing nesting)
    while _EmptyTags.is_match(article_text):
        article_text = _EmptyTags.replace(article_text, "")

    # invalid opening <ref> tags
    if _ub.unclosed_tags(article_text):
        article_text = article_text.replace("<ref<", "<ref>").replace("}}/ref>", "}}</ref>")
        if _InvalidRefOpening.is_match(article_text):
            article_text = _InvalidRefOpeningFix.replace(article_text, "$1<ref$2>")

    # merge consecutive italic/bold html tags
    if any(s.startswith("<b") and not s.startswith("<br") for s in simple_tags):
        article_text = article_text.replace("</b><b>", "")
    if any(s.startswith("<i") for s in simple_tags):
        article_text = article_text.replace("</i><i>", "")

    # html to wiki syntax - CHECKWIKI error 26 and 38
    if any(_IOrB.is_match(s) for s in simple_tags):
        while _SyntaxRegexItalicBoldEm.is_match(article_text):
            article_text = _SyntaxRegexItalicBoldEm.replace(article_text, _bold_italic_me)

    if any(s.startswith("<hr") for s in simple_tags) or "-----" in article_text:
        article_text = _SyntaxRegexHorizontalRule.replace(article_text, "----")

    # double line break after a heading
    article_text = _SyntaxRegexHeadingWithHorizontalRule.replace(article_text, "$1")

    # unnecessary Template: namespace
    template_ns = _template_namespace(site)
    if any(template_ns.is_match(t) for t in all_templates_detail):
        article_text = _templates.remove_template_namespace(article_text)

    # Unicode non-breaking spaces or newlines in template names
    def odd_name(tc: str) -> bool:
        if " " in tc or "　" in tc:
            return True
        # newline before the first bar; a hidden comment there shows as a hidetext marker
        if "|" in tc:
            to_first_bar = tc[: tc.index("|")]
            return (
                len(to_first_bar.strip()) > 2
                and "\r\n" in to_first_bar
                and "⌊⌊⌊⌊" not in to_first_bar
            )
        return False

    for t in [
        n for n in (tools.get_template_name(tc) for tc in all_templates_detail if odd_name(tc)) if n
    ]:
        article_text = tools.rename_template(article_text, t, t, True)

    if _SyntaxRegexBrNewline.is_match(article_text):
        # <br> at the end of list lines - CHECKWIKI error 54
        article_text = _SyntaxRegexListRowBrTag.replace(article_text, "$1")
        # <br> in the middle of lists
        article_text = _SyntaxRegexListRowBrTagMiddle.replace(article_text, "$1\r\n$2")

    # CHECKWIKI error 93
    bad_http_links = any(
        not _GoodHttp.is_match(s)
        for s in dict.fromkeys(m.value for m in _HttpLinks.matches(article_text.lower()))
    )
    if bad_http_links:
        article_text = _MultipleHttpInLink.replace(article_text, "$1")
    article_text = _MultipleFtpInLink.replace(article_text, "$1")

    if bad_http_links and _templates.template_exists(all_templates, W.UrlTemplate):
        article_text = W.UrlTemplate.replace(
            article_text, lambda m: m.value.replace("http://http://", "http://")
        )

    if bad_http_links and not _SyntaxRegexHTTPNumber.is_match(article_text):
        article_text = _MissingColonInHttpLink.replace(article_text, "$1://$2")
        article_text = _SingleTripleSlashInHttpLink.replace(article_text, "$1://$2")
        for a, b in (
            ("https://http://", "https://"),
            ("https:// www.", "https://www."),
            ("http:// www.", "http://www."),
            ("[http%3A//", "[http://"),
            ("[https%3A//", "[https://"),
        ):
            article_text = article_text.replace(a, b)

    if _CellpaddingTypoQuick.is_match(article_text):
        article_text = _CellpaddingTypo.replace(article_text, "$1cellpadding")

    if any("font" in s for s in simple_tags):
        article_text = _RemoveNoPropertyFontTags.replace(article_text, "$1")

    # <ref>[[cite web|url=http://www.foo.com]]</ref>
    article_text = _CiteTemplateWithSquareBrackets.replace(article_text, "$1{{$2}}$4")

    if any("reflist" in s for s in simple_tags):
        article_text = article_text.replace("<<reflist>>", "{{reflist}}")

    # {{Category:foo]] or {{Category:foo}}, and [[Category:foo}}
    article_text = _ub.category_curly_brackets(site).replace(article_text, "[[$1]]")
    article_text = _ub.category_curly_brackets_end(site).replace(article_text, "[[$1]]")

    # missing/unbalanced braces; for performance only if there are unbalanced templates
    without_templates = W.NestedTemplates.replace(article_text, "")
    if "{{" in without_templates or "}}" in without_templates:
        article_text = _RefCitationMissingOpeningBraces.replace(article_text, "$1{{$2")
        article_text = _RefTemplateIncorrectBracesAtEnd.replace(article_text, "$1}}")
        article_text = _TemplateIncorrectBracesAtStart.replace(article_text, "{{$1")
        article_text = _CitationTemplateSingleBraceAtStart.replace(article_text, "{$1")
        if _ReferenceTemplateQuadBracesAtEndQuick.is_match(article_text):
            article_text = _ReferenceTemplateQuadBracesAtEnd.replace(article_text, "$1")
        article_text = _CitationTemplateIncorrectBraceAtStart.replace(article_text, "{{$1")
        if _CitationTemplateIncorrectBracesAtEndQuick.is_match(article_text):
            article_text = _CitationTemplateIncorrectBracesAtEnd.replace(article_text, "$1}}")

    article_text = _RefExternalLinkUsingBraces.replace(article_text, "[$1$2]$3")

    if original != article_text:  # refresh if necessary
        ssb_mc = _ub.SingleSquareBrackets.matches(article_text)
    original = article_text
    no_brackets = tools.replace_with_spaces(article_text, ssb_mc)
    orphaned_single_brackets = "[" in no_brackets or "]" in no_brackets

    if orphaned_single_brackets:
        article_text = _RefExternalLinkMissingStartBracket.replace(article_text, "$1[$2")
        article_text = _RefExternalLinkMissingEndBracket.replace(article_text, "$1]$2")
        ssb_mc = _ub.SingleSquareBrackets.matches(article_text)

    # external links: internal square brackets, newlines or pipes - partly CHECKWIKI error 80
    # performance: only likely external links (with //) that have a pipe, newline or brackets
    ssb = list(dict.fromkeys(m.value for m in ssb_mc))
    ssb_external = [
        m
        for m in ssb
        if "//" in m and ("|" in m or "\r\n" in m or "[" in m[3:] or "]" in m.strip("]"))
    ]
    for s in ssb_external:
        new_value = s
        if (
            "\r\n" in new_value
            and "[" not in new_value[1:]
            and _ExternalLinksStart.is_match(new_value)
        ):
            new_value = new_value.replace("\r\n", " ")
        new_value = _SquareBracketsInExternalLinks.replace(
            new_value, _square_brackets_in_external_links_me
        )
        new_value = _PipedExternalLink.replace(new_value, "$1 $2")
        if s != new_value:
            article_text = article_text.replace(s, new_value)

    # after SquareBracketsInExternalLinks
    if orphaned_single_brackets and not _file_with_http(site).is_match(article_text):
        article_text = _SyntaxRegexWikilinkMissingClosingBracket.replace(article_text, "[[$1]]")
        article_text = _SyntaxRegexWikilinkMissingOpeningBracket.replace(article_text, "[[$1]]")

    # missing http:// in bare URL references - CHECKWIKI error 62
    article_text = _RefURLMissingHttp.replace(article_text, "$1http://www.")

    # bad Image/external links
    if any(":" in m and ":http" in m.lower() for m in ssb):
        article_text = _external_link_to_image_url(site).replace(article_text, "[$1]")

    article_text = _fix_syntax_isbn(article_text, [s for s in ssb if "ISBN]]" in s])

    # T198854 not for hu-wiki
    if "PMID:" in article_text and site.lang_code != "hu":
        article_text = _SyntaxRegexPMID.replace(article_text, "$1 $2")

    # no sup tags on ordinals [[WP:ORDINAL]] - CHECKWIKI error 101
    if any("sup" in s for s in simple_tags):
        article_text = _fixdates.SupOrdinal.replace(article_text, "$1$2")

    # CHECKWIKI error 86
    double_bracket_http = "[[http" in article_text.lower()
    if double_bracket_http:
        article_text = _DoubleBracketAtStartOfExternalLink.replace(article_text, "[$1")

    # unbalanced brackets; trim to clean up after split_to_sections
    article_text = _ub.fix_unbalanced_brackets(article_text).strip()

    if double_bracket_http:
        article_text = _DoubleBracketAtStartOfExternalLink.replace(article_text, "[$1")

    if original != article_text:  # only refresh if changed
        no_brackets = _ub.SingleSquareBrackets.replace(article_text, "")

    if "[" in no_brackets or "]" in no_brackets:
        article_text = _DoubleBracketAtEndOfExternalLink.replace(
            article_text, lambda m: m.value if "\r\n" in m.value else m.group(1)
        )
        article_text = _DoubleBracketAtEndOfExternalLinkWithinImage.replace(article_text, "$1")
        article_text = _ListExternalLinkEndsCurlyBrace.replace(article_text, "$1]")

    # double piped links, e.g. [[foo||bar]] - CHECKWIKI error 32
    if any("||" in s for s in ssb):
        article_text = _DoublePipeInWikiLink.replace(article_text, "|")

    # <br.>, <\br>, <br\> etc. - CHECKWIKI error 02
    if any("br" in s and s not in ("<br>", "<br/>") for s in simple_tags):
        article_text = _IncorrectBr.replace(article_text, "<br />")

    def clear(m: DotNetMatch) -> str:
        side = m.group(1)
        return (
            "{{clear|left}}"
            if side == "left"
            else "{{clear|right}}"
            if side == "right"
            else "{{clear}}"
        )

    article_text = _IncorrectBr2.replace(article_text, clear)
    # <br style="clear:both;" clear="all" /> and <br style="clear:both;" />
    article_text = _IncorrectBr3.replace(article_text, clear)

    # CHECKWIKI errors 55, 63, 66, 77
    if any("small" in s for s in simple_tags):
        article_text = _fix_small_tags(article_text)

    article_text = _WordingIntoBareExternalLinks.replace(article_text, "$1[$3 $2]")

    if _templates.template_exists(all_templates, W.DeadLink):
        article_text = _DeadlinkOutsideRef.replace(article_text, " $2$1")

    if site.lang_code != "zh":
        article_text = _ExternalLinkWordSpacingBefore.replace(article_text, " $1")
        article_text = _ExternalLinkWordSpacingAfter.replace(article_text, "$1 $2")

    # image description ends with a break - CHECKWIKI error 65
    if any("<" in s for s in ssb):
        article_text = W.for_site(site).FileNamespaceLink.replace(
            article_text, lambda m: _WikilinkEndsBr.replace(m.value, "]]")
        )

    # https://phabricator.wikimedia.org/T4700 -- {{subst:}} doesn't work within ref tags
    article_text = fix_syntax_subst_ref_tags(article_text)

    # behaviour switches such as __TOC__ in upper case
    if "__" in no_brackets:
        article_text = W.MagicWordsBehaviourSwitches.replace(
            article_text, lambda m: "__" + m.group(1).upper() + "__"
        )

    return article_text.strip()


def fix_syntax_no_change(article_text: str) -> tuple[str, bool]:
    new_text = fix_syntax(article_text)
    return new_text, new_text == article_text


_IsbnPrefix = _R(r"^ISBN\s*:?\s*")


def _fix_syntax_isbn(article_text: str, ssb_isbn: list[str]) -> str:
    from awb_x.core import tools

    # CHECKWIKI error 69
    isbn_dash = "ISBN-" in article_text or "ISBN–" in article_text
    if (
        isbn_dash
        or "ISBN:" in article_text
        or "ISBN\t" in article_text
        or "ISBN \t" in article_text
        or "[[ISBN]]" in ssb_isbn
    ):
        article_text = _SyntaxRegexISBN.replace(article_text, "ISBN $1")
    if isbn_dash:
        article_text = _SyntaxRegexISBN2.replace(article_text, "ISBN ")
        article_text = _SyntaxRegexISBN2a.replace(article_text, "ISBN-$1")
    if "[[ISBN]]" in ssb_isbn:
        article_text = _SyntaxRegexISBN3.replace(article_text, "ISBN $1")
    if "[[International Standard Book Number|ISBN]]" in ssb_isbn:
        article_text = _SyntaxRegexISBN4.replace(article_text, "ISBN $1")
    # upper case check digit X in ISBN-10
    article_text = _ISBNx.replace(article_text, "$1X")
    # en dash to hyphen in ISBNs
    article_text = _ISBNEndash.replace(
        article_text, lambda m: "ISBN " + m.group(1).replace("–", "-")
    )

    # "ISBN" at the start of isbn= in infoboxes
    if _templates.template_exists(_templates.get_all_templates(article_text), W.InfoBox):
        for infobox in [
            t for t in _templates.get_all_template_detail(article_text) if W.InfoBox.is_match(t)
        ]:
            isbn = tools.get_template_parameter_value(infobox, "isbn")
            if isbn.startswith("ISBN"):
                article_text = article_text.replace(
                    infobox,
                    tools.update_template_parameter_value(
                        infobox, "isbn", _IsbnPrefix.replace(isbn, "")
                    ),
                )

    # ISBN out of the end of an external link
    while _ExternalLinkEndsISBN.is_match(article_text):
        article_text = _ExternalLinkEndsISBN.replace(article_text, "$1] $2")
    return article_text


def _fix_syntax_default_sort(article_text: str) -> str:
    s = W.for_site(current_site())
    # performance: check the DEFAULTSORTs first
    calls = [
        t for t in _templates.get_all_template_detail(article_text) if s.Defaultsort.is_match(t)
    ]
    # must run with no DEFAULTSORT too, as it may be a template with unclosed braces
    if not calls or any(c != s.Defaultsort.replace(c, defaultsort_me) for c in calls):
        article_text = s.Defaultsort.replace(article_text, defaultsort_me)
    return article_text


_CommaSpace = _R(r",(\S..)")


def defaultsort_me(m: DotNetMatch) -> str:
    key = m.group("key")
    # a key that is only whitespace was wrong before and would still be wrong after
    if not key.strip():
        return m.value
    returned = "{{DEFAULTSORT:" + key.strip().rstrip("[]").strip() + "}}"
    # DEFAULTSORT ended by a newline: keep the newline
    end = m.group("end")
    if end.lstrip() != "}}":
        returned += end
    # space after comma, unless the comma ends the key
    return _CommaSpace.replace(returned, ", $1")


def _bold_italic_me(m: DotNetMatch) -> str:
    ret = "'''" if m.group(1).lower() == "b" else "''"
    return ret + m.group(2) + ret


def _square_brackets_in_external_links_me(m: DotNetMatch) -> str:
    # strip off the leading [ and trailing ]
    link = _SyntaxRegexExternalLinkOnWholeLine.replace(m.value, "$1")
    # unmatched double brackets: cannot fix
    if ("[[" in link and "]]" not in link) or ("[[" not in link and "]]" in link):
        return "[" + link + "]"
    # single brackets left need fixing: MediaWiki ends the external link at the first ]
    if not W.Newline.is_match(link) and ("]" in link or "[" in link):
        if "]" in link:
            link = _SyntaxRegexClosingBracket.replace(link, "$1&#93;$2")
        if "[" in link:
            link = _SyntaxRegexOpeningBracket.replace(link, "$1&#91;$2")
    return "[" + link + "]"


_TrailingBracketsOrBraces = _R(r"(\]\]|\]?}|}\])$")


def fix_syntax_redirects(article_text: str) -> str:
    """Fix brackets in #REDIRECT lines and simple bracket problems in redirect templates."""
    from awb_x.core import tools

    s = W.for_site(current_site())
    article_text = s.Redirect.replace(
        article_text,
        lambda m: _TooManyCloseSquareBrackets.replace(
            _TooManyOpenSquareBrackets.replace(
                _RedirectBracketsWithPrefix.replace(m.value.replace("\r\n", " "), " [["), "[["
            ),
            "]]",
        ),
    )
    article_text = tools.template_to_magic_word(article_text)

    # simple bracket fixing for redirect templates
    if "{{" in article_text and "}}" not in article_text:
        # incorrect closing bracket
        article_text = _TrailingBracketsOrBraces.replace(article_text.rstrip(), "}}")
        # missing closing }}
        if "}}" not in article_text:
            article_text += "}}"
    return _templates.remove_template_namespace(article_text)


_SUBST_MONTH_YEAR = "{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
_EN_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def fix_syntax_subst_ref_tags(article_text: str) -> str:
    """{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}} inside refs, image links and galleries
    (where subst does not work, T4700) -> the current month and year."""
    if current_site().lang_code == "en" and _SUBST_MONTH_YEAR in article_text:
        now = datetime.datetime.now(datetime.UTC)
        month_year = f"{_EN_MONTHS[now.month - 1]} {now.year}"

        def me(m: DotNetMatch) -> str:
            return m.value.replace(_SUBST_MONTH_YEAR, month_year)

        article_text = W.Refs.replace(article_text, me)
        article_text = W.for_site(current_site()).Images.replace(article_text, me)
        article_text = W.GalleryTag.replace(article_text, me)
    return article_text


# Filled in AWB's Parsers static constructor.
_SmallTagRegexes: tuple[DotNetRegex, ...] = (
    W.SupSub,
    W.for_site(SiteConfig.english()).FileNamespaceLink,
    W.Refs,
    W.Small,
)


def _fix_small_tags(article_text: str) -> str:
    sm = W.Small.match(article_text)
    # performance: only the part of the text with small tags
    if not sm:
        return article_text
    cutoff = max(0, sm.index - 999)  # <ref><small> needs some offset before the <small>
    before_small = article_text[:cutoff]
    article_text = article_text[cutoff:]
    # not with unclosed tags
    if not _ub.unclosed_tags(article_text):
        for r in _SmallTagRegexes:
            article_text = r.replace(article_text, _fix_small_tags_me)
        # small tags around ref/sup/sub tags
        article_text = W.Small.replace(article_text, _fix_small_tags_me2)
    return before_small + article_text


def _fix_small_tags_me(m: DotNetMatch) -> str:
    # keep <small> within {{legend}}, where it is not unreasonable
    if not _LegendTemplate.is_match(m.value) and not _TableEnd.is_match(m.value):
        s = W.Small.match(m.value)
        if s:
            if s.index > 0:
                return W.Small.replace(m.value, "$1")
            # nested small
            return m.value[:7] + W.Small.replace(m.value[7:], "$1")
    return m.value


def _fix_small_tags_me2(m: DotNetMatch) -> str:
    content = m.group(1).strip()
    if "<" not in content:
        return m.value
    if W.Refs.match(content).value == content or W.SupSub.match(content).value == content:
        return content
    return m.value


def fix_syntax_mainspace(article_text: str, article_title: str) -> str:
    """Remove __INDEX__/__NOINDEX__ from articles (they have no effect there)."""
    if not namespace.is_main_space(article_title):
        return article_text
    return _IndexNoIndexMagicWord.replace(article_text, "")


class FixSyntaxMixin:
    def fix_image_self_links(self, article_text: str) -> str:
        """Remove link= from image links whose link target is the file itself."""
        from awb_x.core import tools

        def me(m: DotNetMatch) -> str:
            res = m.value
            # the link parameter, cleaned of URL parts
            link_param = tools.get_template_parameter_value("{{" + m.group(1) + "}}", "link")
            if link_param:
                link_param = tools.remove_syntax(tools.normalize_title_core(link_param))
                target = W.WikiLink.match(m.value).group(1)
                if link_param == tools.remove_syntax(target):
                    # use the template functions to adjust parameters
                    res = tools.remove_template_parameter("{{" + res[2:-2] + "}}", "link")
                    res = "[[" + res[2:-2] + "]]"
            return res

        return W.for_site(current_site()).FileNamespaceLink.replace(article_text, me)
