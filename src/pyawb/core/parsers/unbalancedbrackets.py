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
# Ported from AutoWikiBrowser WikiFunctions/Parse/UnbalancedBrackets.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Finding and fixing unbalanced brackets and unclosed tags (port of Parse/UnbalancedBrackets.cs).

AWB builds the namespace-dependent regexes once from the wiki loaded first; here they are built
per wiki (and cached), which matches AWB on English Wikipedia and is right on other wikis.
"""

from __future__ import annotations

import functools

from pyawb.core import rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import hidetext
from pyawb.core.parsers import templates as _templates
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import Namespace, SiteConfig, current_site
from pyawb.core.textutil import char_lower, nested_template_regex

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

SingleCurlyBrackets = _R(
    r"{((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))})", O.EXPLICIT_CAPTURE
)
DoubleCurlyBrackets = _R(
    r"{{(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}}", O.EXPLICIT_CAPTURE
)
DoubleSquareBrackets = _R(
    r"\[\[((?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\]\])", O.EXPLICIT_CAPTURE
)
SingleSquareBrackets = _R(
    r"\[((?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])", O.EXPLICIT_CAPTURE
)
SingleRoundBrackets = _R(
    r"\(((?>[^\(\)]+|\((?<DEPTH>)|\)(?<-DEPTH>))*(?(DEPTH)(?!))\))", O.EXPLICIT_CAPTURE
)
_Tags = _R(r"\<((?>[^\<\>]+|\<(?<DEPTH>)|\>(?<-DEPTH>))*(?(DEPTH)(?!))\>)", O.EXPLICIT_CAPTURE)
_HideNestedBrackets = _R(r"&#9[13];")
_AmountComparison = _R(r"[<>]\s*\d")
_TemplatesWithUnbalancedBrackets = nested_template_regex(["LSJ", ")!", "!(", "C sharp", "Lisp2"])


def unbalanced_brackets(article_text: str) -> tuple[int, int]:
    """(index of the first unbalanced bracket or -1, bracket length 1 or 2).

    Checks {{ }} and [[ ]] first, then { } [ ] ( ) and < >. AWB returns the length in an out
    parameter.
    """
    from pyawb.core import tools

    templ_with_ub = _templates.template_exists(
        _templates.get_all_templates(article_text), _TemplatesWithUnbalancedBrackets
    )

    # &#91; and &#93; replace [ and ] in external link text; turn them back so they are not
    # matched as unbalanced brackets
    article_text = _HideNestedBrackets.replace(
        article_text, lambda m: "]    " if "93" in m.value else "[    "
    )
    # <math>, <code> etc. use curly brackets singly and in pairs
    article_text = tools.replace_with_spaces(article_text, W.MathPreSourceCodeComments)
    # some templates deliberately use unbalanced brackets in their parameters
    if templ_with_ub:
        article_text = tools.replace_with_spaces(article_text, _TemplatesWithUnbalancedBrackets)

    found = _unbalanced(article_text, "{{", "}}", DoubleCurlyBrackets)
    if found > -1:
        return found, 2
    found = _unbalanced(article_text, "[[", "]]", DoubleSquareBrackets)
    if found > -1:
        return found, 2

    # performance: count single brackets; only run detailed checks if some are unbalanced
    counts = {"[": 0, "{": 0, "(": 0, "<": 0}
    closers = {"]": "[", "}": "{", ")": "(", ">": "<"}
    has_unbalanced = False
    for c in article_text:
        if c in counts:
            counts[c] += 1
        elif c in closers:
            counts[closers[c]] -= 1
            if counts[closers[c]] < 0:  # more closing than opening
                has_unbalanced = True
                break
    if not has_unbalanced and not any(counts.values()):
        return -1, 1

    for opening, closing, r in (
        ("{", "}", SingleCurlyBrackets),
        ("[", "]", SingleSquareBrackets),
        ("(", ")", SingleRoundBrackets),
        ("<", ">", _Tags),
    ):
        found = _unbalanced(article_text, opening, closing, r)
        if found > -1:
            return found, 1
    return -1, 1


def _unbalanced(article_text: str, opening: str, closing: str, brackets: DotNetRegex) -> int:
    from pyawb.core import tools

    # performance: the text outside matched brackets (the regexes have no capturing groups)
    if not any(opening in s or closing in s for s in brackets.split(article_text)):
        return -1
    # some unbalanced: blank out matched brackets so we get the index in the original text
    article_text = tools.replace_with_spaces(article_text, brackets)
    # for tags, "> 50 cm" is not unbalanced
    if opening == "<" and _AmountComparison.is_match(article_text):
        return -1
    open_i, closed_i = article_text.find(opening), article_text.find(closing)
    if open_i > -1 or closed_i > -1:
        open_count = article_text.count(opening)
        closed_count = article_text.count(closing)
        if open_count == 0 and closed_count >= 1:
            return closed_i
        if open_count >= 1:
            return open_i
    return -1


_CurlyBraceInsteadOfPipeInWikiLink = _R(
    r"(?<=\[\[[^\[\]{}<>\r\n\|]{1,50})}(?=[^\[\]{}<>\r\n\|]{1,50}\]\])"
)
_CurlyBraceInsteadOfBracketClosing = _R(r"(\([^{}<>\(\)]+[^{}<>\(\)\|])}(?=[^{}])")
_CurlyBraceInsteadOfSquareBracket = _R(r"(?<=\[[^{}<>\[\]]+[^{}<>\(\)\|\]])}(?=[^{}])")
_CurlyBraceInsteadOfBracketOpening = _R(r"(?<=[^{}<>]){(?=[^{}<>\(\)\|][^{}<>\(\)]+\)[^{}\(\)])")
_CurlyBraceInsteadOfBracketOpening2 = _R(r"(?<=\[)\[?{(?=[^{}\[\]<>]+\]\])")
_ExtraBracketOnWikilinkOpening = _R(r"(?<=[^\[\]{}<>])(?:{\[\[?|\[\[\[)(?=[^\[\]{}<>]+\]\])")
_ExtraBracketOnWikilinkOpening2 = _R(r"(?<=\[\[){(?=[^{}\[\]<>]+\]\])")
_ExternalLinkMissingClosing = _R(
    r"(^ *\* *\[ *(?:ht|f)tps?://[^<>{}\[\]\r\n\s]+[^\[\]\r\n]*)(\s$)", O.MULTILINE
)
_ExternalLinkMissingOpening = _R(
    r"(?<=^ *\*) *(?=(?:ht|f)tps?://[^<>{}\[\]\r\n\s]+[^\[\]\r\n]*\]\s$)", O.MULTILINE
)
_CiteTemplateIncorrectBar = _R(r"({{(?:[Cc]it|[Vv]cit)[^{}]+)(?:{|})(\s*[A-Za-z0-9_-]+\s*=)")
_TemplateIncorrectClosingBraces = _R(
    r"(?<={{[^{}<>]{1,400}[^{}<>\|\]])(?:\]}|}\]?|\)\))(?=[^{}]|$)"
)
_TemplateMissingOpeningBrace = _R(r"(?<=[^{}<>\|]|^){(?=\s*\w[^{}<>]{1,400}}})")
_TemplateOpening = _R(r"\(\((\s*\w+\s*}})")
_QuadrupleCurlyBrackets = _R(r"(?<=^{{[^{}\r\n]+}})}}(\s)$", O.MULTILINE)
_WikiLinkOpeningClosing = _R(r"\[(?:\]| +\[)([^\[\]\r\n]+\]\])")
_WikiLinkPunctuation = _R(r"""(\[\[[^\[\]\r\n]+\])([,.;:"' ]{1,2})(\])""")
_WikiLinkDoubleOpening = _R(r"(\[\[[^\[\]\r\n:]{1,55})\[\[")
_UnclosedCatInterwiki = _R(
    r"^(\[\[[^\[\]\r\n]+(?<!File|Image|Media)\:[^\[\]\r\n]+)(\s*)$", O.MULTILINE
)
_RefClosingOpeningBracket = _R(r"\[(\s*</ref>)", O.IGNORE_CASE)
_CiteRefEndsTripleClosingBrace = _R(r"([^}])\}(\}\}\s*</ref>)")
_CiteRefEndsTripleOpeningBrace = _R(r"(>\s*)\{\{\{+(\s*[Cc]ite)")
_CiteRefStartsSingleOpeningBrace = _R(r"(>\s*\{)([^<>{}\r\n]+\}\})")
_RefExternalLinkWrongBracket = _R(r"(<ref[^<>/]*>)\]")
_CurlyToStraightSingleBracket = _R(r"([^{}()]){([^{}()]+)\)")
_TripleBracketAtEndOfExternalLink = _R(
    r"(\[ *https?:/(?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])\]\](?!\])",
    O.IGNORE_CASE,
)
_UnclosedMultipleIssues = _R(
    r"({{[Mm]ultiple issues\s*\|\s*(\s*{{[^{}]+}})+)(?<!.*{{[^{}|]*[Ii]nfobox.*)", O.SINGLELINE
)


@functools.lru_cache(maxsize=32)
def category_curly_brackets(site: SiteConfig) -> DotNetRegex:
    """{{Category:foo]] or {{Category:foo}}."""
    return _R(r"{{ *(" + site.namespaces[Namespace.CATEGORY] + r"[^{}\[\]]+?)(?:}}|\]\])")


@functools.lru_cache(maxsize=32)
def category_curly_brackets_end(site: SiteConfig) -> DotNetRegex:
    """[[Category:foo}}."""
    return _R(r"\[\[ *(" + site.namespaces[Namespace.CATEGORY] + r"[^{}\[\]]+?)(?:}})")


@functools.lru_cache(maxsize=32)
def _file_image_curly_brackets(site: SiteConfig) -> DotNetRegex:
    return _R(r"{{\s*(" + site.namespaces_case_insensitive[Namespace.FILE] + r"\s*)")


def fix_unbalanced_brackets(article_text: str) -> str:
    """Try to fix unbalanced brackets, one section at a time."""
    from pyawb.core import tools

    return "".join(
        _fix_unbalanced_brackets_section(s) for s in tools.split_to_sections(article_text)
    )


def _fix_unbalanced_brackets_section(article_text: str) -> str:
    # these fixes could damage correct syntax, so they are kept only if they rebalance things
    temp = article_text
    unbalanced, bracket_length = unbalanced_brackets(article_text)
    if unbalanced < 0:
        return article_text
    first = unbalanced
    bracket = temp[unbalanced]

    # ]]_]_ : see if removing the bracket makes it all balance
    if (
        bracket_length == 1
        and unbalanced > 2
        and temp[unbalanced] == "]"
        and temp[unbalanced - 1] == "]"
        and temp[unbalanced - 2] == "]"
    ):
        # with ⌊⌊⌊⌊0⌋⌋⌋⌋[[link]]] the real text may be <nowiki>[</nowiki>[[link]]], which is fine
        if not (hidetext.HiddenRegex.is_match(temp) and "⌋⌋⌋⌋[[" in temp):
            temp = temp[:unbalanced] + temp[unbalanced + 1 :]
    elif bracket_length == 1:
        if bracket == "}":
            temp = _CurlyBraceInsteadOfPipeInWikiLink.replace(temp, "|")  # [[blah blah}word]]
            temp = _CurlyBraceInsteadOfBracketClosing.replace(
                temp, "$1)"
            )  # (blah}, not |} (tables)
            temp = _CurlyBraceInsteadOfSquareBracket.replace(temp, "]")  # [blah}
            temp = _CiteRefEndsTripleClosingBrace.replace(temp, "$1$2")  # }}}</ref>
        elif bracket == "{":
            temp = _CurlyBraceInsteadOfBracketOpening.replace(temp, "(")  # {blah), not {| (tables)
            temp = _ExtraBracketOnWikilinkOpening2.replace(temp, "")  # [[{link]]
            temp = _CiteRefEndsTripleOpeningBrace.replace(temp, "$1{{$2")  # <ref>{{{
        elif bracket == "(":
            # ((word): remove the extra opening bracket
            if len(temp) > unbalanced + 1 and article_text[unbalanced + 1] == "(":
                temp = temp[:unbalanced] + temp[unbalanced + 1 :]
        elif bracket == "[":
            temp = _ExternalLinkMissingClosing.replace(temp, "$1]$2")
            temp = _RefClosingOpeningBracket.replace(temp, "]$1")
        elif bracket == "]":
            temp = _ExternalLinkMissingOpening.replace(temp, " [")
            temp = _RefExternalLinkWrongBracket.replace(temp, "$1[")
        elif bracket == ">":
            temp = temp.replace("<ref>>", "<ref>")
        # Chinese brackets （ and ）: change if unbalanced
        elif current_site().lang_code == "en" and temp.count("（") != temp.count("）"):
            temp = temp.replace("）", ")").replace("（", "(")

        # {[link]], {[[link]] or [[[link]]: try [[
        if bracket != ">":
            temp = _ExtraBracketOnWikilinkOpening.replace(temp, "[[")

    if bracket_length == 2:
        temp = _CurlyBraceInsteadOfBracketOpening.replace(temp, "(")
        temp = _CurlyBraceInsteadOfBracketClosing.replace(temp, "$1)")
        temp = _TemplateOpening.replace(temp, "{{$1")  # ((Reflist}} -> {{Reflist}}
        temp = _CiteTemplateIncorrectBar.replace(temp, "$1|$2")  # {{cite web{last=foo...}}
        temp = _TemplateIncorrectClosingBraces.replace(temp, "}}")  # {{foo} or {{foo]}
        temp = _CurlyBraceInsteadOfBracketOpening2.replace(temp, "[")  # {{foo|par=[{Bar]]}}
        temp = _TemplateMissingOpeningBrace.replace(temp, "{{")  # {foo}}

        start_brackets = temp[unbalanced : unbalanced + min(4, len(temp) - unbalanced)]
        end_start = max(0, unbalanced - 2)
        end_brackets = temp[end_start : end_start + min(4, len(temp) - unbalanced + 2)]
        # [[[[link]] or [[link]]]]: remove the two brackets found
        if start_brackets == "[[[[" or end_brackets == "]]]]":
            temp = temp[:unbalanced] + temp[unbalanced + 2 :]

        temp = _WikiLinkOpeningClosing.replace(temp, "[[$1")  # []foo]]
        temp = _QuadrupleCurlyBrackets.replace(temp, "$1")
        # [[foo[[
        if any(m.index == unbalanced for m in _WikiLinkDoubleOpening.matches(temp)):
            temp = _WikiLinkDoubleOpening.replace(temp, "$1]]")
        temp = _UnclosedCatInterwiki.replace(temp, "$1]]$2")  # unclosed category/interwiki
        temp = _file_image_curly_brackets(current_site()).replace(
            temp, "[[$1"
        )  # {{File: -> [[File:
        temp = _CurlyToStraightSingleBracket.replace(temp, "$1($2)")  # {...)
        temp = _WikiLinkPunctuation.replace(temp, "$1$3$2")  # [[foo],]
        temp = _TripleBracketAtEndOfExternalLink.replace(temp, "$1")  # external link excess ]
        # unclosed {{multiple issues, not matching into an infobox
        temp = _UnclosedMultipleIssues.replace(temp, "$1\r\n}}")
        temp = _CiteRefStartsSingleOpeningBrace.replace(temp, "$1{$2")  # <ref>{template}}

    unbalanced, bracket_length = unbalanced_brackets(temp)
    # it worked if all brackets now balance, or the unbalanced one moved well away
    if unbalanced < 0 or (abs(unbalanced - first) > 300 and unbalanced - first > -300):
        article_text = temp
    return article_text


_MathSourceCodeNowikiPreTag = _R(
    r"<!--|(<\s*/?\s*(?:math|(?:source|ref|gallery)\b[^>]*|code|nowiki|pre|small|center|sup|sub)\s*(?:>|$))",
    O.MULTILINE,
)
_CenterTag = _R(
    r"<\s*center\s*>((?>(?!<\s*/?\s*center\s*>).|<\s*center\s*>(?<DEPTH>)|<\s*/\s*center\s*>(?<-DEPTH>))*(?(DEPTH)(?!)))<\s*/\s*center\s*>",
    O.SINGLELINE | O.IGNORE_CASE,
)
_SupTag = _R(
    r"<\s*sup\s*>((?>(?!<\s*/?\s*sup\s*>).|<\s*sup\s*>(?<DEPTH>)|<\s*/\s*sup\s*>(?<-DEPTH>))*(?(DEPTH)(?!)))<\s*/\s*sup\s*>",
    O.SINGLELINE | O.IGNORE_CASE,
)
_SubTag = _R(
    r"<\s*sub\s*>((?>(?!<\s*/?\s*sub\s*>).|<\s*sub\s*>(?<DEPTH>)|<\s*/\s*sub\s*>(?<-DEPTH>))*(?(DEPTH)(?!)))<\s*/\s*sub\s*>",
    O.SINGLELINE | O.IGNORE_CASE,
)
_AnyTag = _R(r"<\s*([A-Za-z/][^<>]+)>")
_SimpleTagPair = _R(r"<([^<>]+)>[^<>]+</\1>")
_CHECKED_TAGS = (
    "math",
    "source",
    "ref",
    "gallery",
    "code",
    "nowiki",
    "pre",
    "small",
    "center",
    "sup",
    "sub",
)
_UnclosedNestedComments = _R(r"<!--(.*?)(?<!<!--.*<!--.*)-->|<!--([^<]*)-->")
# AWB rebuilds these from ToString(), which keeps only the options given here
_RefsSingleline = _R(W.Refs.pattern, O.SINGLELINE)
_SourceCodeSingleline = _R(W.SourceCode.pattern, O.SINGLELINE)


def _lower_same_length(text: str) -> str:
    """string.ToLower() keeping every index: Python's "İ".lower() is two characters."""
    return "".join(char_lower(c) for c in text)


def unclosed_tags(article_text: str) -> dict[int, int]:
    """Index -> length of unclosed <math>, <source>, <ref>, <gallery>, <code>, <nowiki>, <pre>,
    <small>, <center>, <sup>, <sub> tags and <!-- comments."""
    from pyawb.core import tools

    back: dict[int, int] = {}
    # performance: compare counts of opening and closing tags first
    any_tag_matches = _AnyTag.matches(article_text)
    tags = [m.group(1).strip().lower() for m in any_tag_matches]
    # no self-closing tags or comments; tag name only
    tags = [s for s in tags if not s.endswith("/") and not s.startswith("!--")]
    tags = [s[: s.index(" ")].strip() if " " in s else s for s in tags]
    tags = [s for s in tags if s.lstrip("/") in _CHECKED_TAGS]

    counts: dict[str, int] = {}
    for s in tags:
        counts[s] = counts.get(s, 0) + 1
    unmatched = False
    for name, count in counts.items():
        other = name.lstrip("/") if name.startswith("/") else "/" + name
        if counts.get(other) != count:
            unmatched = True
            break

    if not unmatched:
        # any unclosed partial tag?
        no_tags = tools.replace_with_spaces(article_text, any_tag_matches)
        tag_open = no_tags.find("<")
        if tag_open == -1 or (tag_open > 0 and ">" in no_tags[tag_open:]):
            return back

    # full clear down and search; lower case performs better for Refs/SourceCode
    article_text = _lower_same_length(article_text)
    # so that <!-- a <!-- b --> leaves the first <!-- to be reported as unclosed
    article_text = tools.replace_with_spaces(article_text, _UnclosedNestedComments)
    article_text = tools.replace_with_spaces(article_text, W.UnformattedText)
    article_text = tools.replace_with_spaces(article_text, W.GalleryTag, 2)
    article_text = tools.replace_with_spaces(article_text, _RefsSingleline)

    # pages with hundreds of unclosed small/center tags make the nested regexes backtrack: with
    # > 10 unclosed, only remove tags without other tags inside (may misreport some tags)
    if (
        sum(1 for s in tags if not s.startswith("/"))
        > sum(1 for s in tags if s.startswith("/")) + 10
    ):
        while _SimpleTagPair.is_match(article_text):
            article_text = tools.replace_with_spaces(article_text, _SimpleTagPair)
    else:
        article_text = tools.replace_with_spaces(article_text, _SourceCodeSingleline)
        article_text = tools.replace_with_spaces(article_text, _CenterTag, 2)
        article_text = tools.replace_with_spaces(article_text, W.Small)
        article_text = tools.replace_with_spaces(article_text, _SupTag, 2)
        article_text = tools.replace_with_spaces(article_text, _SubTag, 2)

    for m in _MathSourceCodeNowikiPreTag.matches(article_text):
        back[m.index] = m.length
    return back
