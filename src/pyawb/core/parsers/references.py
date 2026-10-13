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
# Ported from AutoWikiBrowser WikiFunctions/Parse/References.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""<ref> fixes (port of Parse/References.cs): reordering, punctuation (WP:REFPUNC), duplicate
and named references, derived reference names, {{Reflist}} conversion and tag formatting.
"""

# ruff: noqa: E501

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from pyawb.core import rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import templates as _templates
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import current_site
from pyawb.core.textutil import nested_template_regex

if TYPE_CHECKING:
    from pyawb.core.parsers.parsers import Parsers

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

# -- static regexes (generated from References.cs by tools/porting/cs2py.py, then edited) --------

_InlineCitationCleanupTemplatesRp = r"(?:Author incomplete|Author missing|Citation broken|Citation not found|Clarify|Date missing|Episode|ISBN missing|Page needed|Publisher missing|Season needed|Time needed|Title incomplete|Title missing|Volume needed|Year missing|rp)"

_OutofOrderRefs = (
    '(<ref\\s+name\\s*=\\s*(?:"|\')?([^<>"=]+?)(?:"|\')?\\s*(?:\\/\\s*|>[^<>]+</ref)>)(\\s*{{\\s*'
    + _InlineCitationCleanupTemplatesRp
    + '(?:(?>[^\\{\\}]+|\\{(?<DEPTH>)|\\}(?<-DEPTH>))*(?(DEPTH)(?!))}}))?(\\s*)(<ref\\s+name\\s*=\\s*(?:"|\')?([^<>"=]+?)(?:"|\')?\\s*(?:\\/\\s*|>[^<>]+</ref)>)(\\s*{{\\s*'
    + _InlineCitationCleanupTemplatesRp
    + r"(?:(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}}))?"
)

_OutofOrderRefs1 = _R(
    '(<ref>[^<>]+</ref>)(\\s*)(<ref\\s+name\\s*=\\s*(?:"|\')?([^<>"=]+?)(?:"|\')?\\s*(?:\\/\\s*|>[^<>]+</ref)>)(\\s*{{\\s*'
    + _InlineCitationCleanupTemplatesRp
    + r"(?:(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}}))?",
    O.IGNORE_CASE | O.SINGLELINE,
)

_OutofOrderRefs2 = _R(_OutofOrderRefs, O.IGNORE_CASE | O.SINGLELINE)

# regex below ensures a forced match on second and third of consecutive references
_OutofOrderRefs3 = _R(
    r"(?<=\s*(?:\/\s*|>[^<>]+</ref)>\s*(?:{{\s*"
    + _InlineCitationCleanupTemplatesRp
    + r"\s*\|[^{}]+}})?)"
    + _OutofOrderRefs,
    O.IGNORE_CASE | O.SINGLELINE,
)

_RefsTag = _R(r"<\s*references")

_RefsPunctuation = r"([,\.;:\?\!])"

_NoPunctuation = r"([^,\.:;\?\!])"

_RefsBeforePunctuationR = _R(
    r" *" + W.Refs + r" *" + _RefsPunctuation + r"([^,\.:;\?\!]|$)", O.IGNORE_CASE | O.SINGLELINE
)

_RefsBeforePunctuationQuick = _R(r"(?<=(?:/|ref) *)> *" + _RefsPunctuation)

_RefsAfterDupePunctuation = _R(
    _NoPunctuation + _RefsPunctuation.replace(r"\!", "") + r"\2 *" + W.Refs,
    O.IGNORE_CASE | O.SINGLELINE,
)

_FootnoteTemplatesList = (
    "Efn",
    "Efn-ua",
    "Efn-lr",
    "Sfn",
    "Shortened footnote",
    "Shortened footnote template",
    "Sfnb",
    "Sfnp",
    "Sfnm",
    "SfnRef",
)

# these templates should not have punctuation between the end of a ref and the start of the
# template, in addition to all the footnote ones
_PunctuationBeforeTheseTemplatesList = ("Rp", "Better source")

# private in AWB; Parsers.HasFootnoteTemplate-style checks in parsers.py use it
Footnote = nested_template_regex(_FootnoteTemplatesList)

_PunctuationBeforeTheseTemplates = nested_template_regex(
    list(dict.fromkeys(_FootnoteTemplatesList + _PunctuationBeforeTheseTemplatesList))
)

_PunctuationAfterTemplate = _R(
    r"(?<template>" + str(_PunctuationBeforeTheseTemplates) + r")(?<punc>[,\.;:\?])"
)

_TemplateAfterDupePunctuation = _R(
    _NoPunctuation
    + _RefsPunctuation
    + r"\2 *(?<template>"
    + str(_PunctuationBeforeTheseTemplates)
    + r")"
)

_RefsAfterPunctuationAllowedLangs = ("en", "simple", "ar", "ary", "arz")

_LineStartsSemiColon = _R(r"^;.*", O.MULTILINE)

_LongNamedReferences = _R(
    "(<\\s*ref\\s+name\\s*=\\s*(?:\"|')?([^<>=\\r\\n]+?)(?:\"|')?\\s*>\\s*([^<>]{30,}?)\\s*<\\s*/\\s*ref>)",
    O.COMPILED,
)

_RefNameStart = _R("<\\s*ref\\s+name\\s*=\\s*(\"|')?([^<>=\\r\\n]+?)(?:\"|')?\\s*>", O.IGNORE_CASE)

_RefName = "(?si)<\\s*ref\\s+name\\s*=\\s*(?:\"|')?"

_PageRef = _R(r"\s*(?:(?:[Pp]ages?|[Pp][pg]?[:\.]?)|^)\s*[XVI\d]", O.COMPILED)

_RefNameFromGroup = _R(
    r"<\s*ref\s+name\s*=\s*(?<nm>[^<>]*?)\s*group|group\s*=\s*[^<>]*?\s*name\s*=\s*(?<nm>[^<>]*?)\s*/?\s*>"
)

_ShortNameReference = _R(
    "(<\\s*ref\\s+name\\s*=\\s*(?:\"|')?([^<>=\\r\\n/]+?)(?:\"|')?\\s*>\\s*([^<>]{1,9}?|\\[?[Ss]ee above\\]?|{{\\s*[Cc]ite *\\w+\\s*}})\\s*<\\s*/\\s*ref>)"
)

_CharsToTrim = r".;: {}[]|`?\/$’‘-_–=+,"

# U230A is Floor Left; U230B is Floor Right
_CommentOrFloorNumber = _R(r"(\<\!--.*?--\>|" + "⌊" + r"{3,}\d+" + "⌋" + r"{3,})", O.COMPILED)

_SequenceOfQuotesInDerivedName = _R("(''+|[“‘”\"\\[\\]\\(\\)\\<\\>" + "⌊⌋" + r"])", O.COMPILED)

_WhitespaceInDerivedName = _R(r"(\s{2,}|&nbsp;|\t|\n)", O.COMPILED)

_DateRetrievedOrAccessed = _R(r"(?im)(\s*(date\s+)?(retrieved|accessed)\b|^\d+$)", O.COMPILED)

_NameMask = r"(?-i)\s*(?:sir)?\s*((?:[A-Z]+\.?){0,3}\s*[A-Z][\w-']{2,}[,\.]?\s*(?:\s+\w\.?|\b(?:[A-Z]+\.?){0,3})?(?:\s+[A-Z][\w-']{2,}){0,3}(?:\s+\w(?:\.?|\b)){0,2})\s*(?:[,\.'&;:\[\(“`]|et\s+al)(?i)[^{}<>\n]*?"

_YearMask = r"(\([12]\d{3}\)|\b[12]\d{3}[,\.\)])"

_PageMask = r"('*(?:p+g?|pages?)'*\.?'*(?:&nbsp;)?\s*(?:\d{1,3}|(?-i)[XVICM]+(?i))\.?(?:\s*[-/&\.,]\s*(?:\d{1,3}|(?-i)[XVICM]+(?i)))?\b)"

_CitationCiteBook = _R(
    r"{{[Cc]it[ae]((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}})", O.COMPILED
)

_CiteTemplatePagesParameter = _R(r"(?<=\s*pages?\s*=\s*)([^{}\|<>]+?)(?=\s*(?:\||}}))", O.COMPILED)

_UrlShortDescription = _R(
    r'\s*[^{}<>\n]*?\s*\[*(?:https?://www\.|https?://|www\.)[^\[\]<>"\s]+?\s+([^{}<>\[\]]{4,35}?)\s*(?:\]|<!--|\u230A\u230A\u230A\u230A)',
    O.COMPILED,
)

_UrlDomain = _R(
    r'\s*\w*?[^{}<>]{0,4}?\s*(?:\[?|\{\{\s*cit[^{}<>]*\|\s*url\s*=\s*)\s*(?:https?://www\.|https?://|www\.)([^\[\]<>"\s\/:]+)',
    O.COMPILED,
)

_HarvnbTemplate = _R(
    r"\s*{{ *(?:[Hh]arv(?:(?:col)?(?:nb|txt)|ard citation no brackets)?|[Ss]fn)\s*\|\s*([^{}\|]+?)\s*\|(?:[^{}]*?\|)?\s*(\d{4})\s*(?:\|\s*(?:pp?\s*=\s*)?([^{}\|]+?)\s*)?}}\s*",
    O.COMPILED,
)

_WholeShortReference = _R(r"\s*([^<>{}]{4,35})\s*", O.COMPILED)

_CiteTemplateTitle = _R(
    r"\s*\{\{\s*cit[^{}<>]*\|\s*(?:title|contribution)\s*=\s*([^\/<>{}\|]{4,35})", O.COMPILED
)

_NameYearPage = _R(_NameMask + _YearMask + r"[^{}<>\n]*?" + _PageMask + r"\s*", O.COMPILED)

_NamePage = _R(_NameMask + _PageMask + r"\s*", O.COMPILED)

_NameYear = _R(_NameMask + _YearMask + r"\s*", O.COMPILED)

_CiteDOIPMID = nested_template_regex(("cite doi", "cite pmid"))

BadRefNames = ("http", "https")

# Main regex for {{Reflist}} converter
_ReferenceListTags = _R(
    r'(<(span|div)( class="(references-small|small|references-2column)|)?"(?:\s*style\s*=\s*"[^<>"]+?"\s*)?>[\r\n\s]*){1,2}[\r\n\s]*<references[\s]?/>([\r\n\s]*</(span|div)>){1,2}',
    O.COMPILED | O.IGNORE_CASE,
)

_ReferenceListSmallTags = _R(
    r"(<small>[\r\n\s]*){1,2}[\r\n\s]*<references[\s]?/>([\r\n\s]*</small>){1,2}",
    O.COMPILED | O.IGNORE_CASE,
)

_DivStart = _R(r"<div\b.*?>", O.COMPILED)

_DivEnd = _R(r"< ?/ ?div\b.*?>", O.COMPILED)

_EmptyReferences = _R(
    r"(<ref\s+name\s*=\s*[^<>=\r\n]+?)\s*(?:/\s*)?>\s*<\s*/\s*ref\s*>", O.IGNORE_CASE | O.COMPILED
)

_LinksHeading = _R(r"(?sim)(==+\s*)Links(\s*==+\s*(?:^(?:\*|\d\.?)?\s*\[?\s*http://))", O.COMPILED)

_ReferencesHeadingLevel2 = _R(r"(?i)==\s*'*\s*References?\s*'*\s*==", O.COMPILED)

_ReferencesHeadingLevelLower = _R(r"(?i)(==+\s*'*\s*References?\s*'*\s*==+)", O.COMPILED)

_ExternalLinksHeading = _R(
    r"(?im)(^\s*=+\s*(?:External\s+link|Source|Web\s*link)s?\s*=)", O.COMPILED
)

_ExternalLinksToReferences = _R(
    r"(?sim)(^\s*=+\s*(?:External\s+link|Source|Web\s*link)s?\s*=+.*?)(\r\n==+References==+\r\n{{Reflist}})",
    O.COMPILED,
)

_Category = _R(r"(?im)(^\s*\[\[\s*Category\s*:)", O.COMPILED)

_CategoryToReferences = _R(
    r"(?sim)((?:^\{\{(?!(?:[Tt]racklist|[Ss]\-end)\b)[^{}]+?\}\}\s*)*)(^\s*\[\[\s*Category\s*:.*?)(\r\n==+References==+\r\n{{Reflist}})",
    O.COMPILED,
)

_ReferencesMissingSlash = _R(r"<\s*[Rr]eferences\s*>", O.COMPILED)

_RefSimple: tuple[tuple[DotNetRegex, str], ...] = (
    (_R(r"<\s*(?:\s+ref\s*|\s*ref\s+)>", O.SINGLELINE), "<ref>"),
    # <ref name-"Fred"> or <ref name=="Fred"> or <ref name"=Fred"> --> <ref name="Fred">
    (_R(r'(<\s*ref\s+name\s*)(?:[-\+\:]|= ?=+|(") *=)'), "$1=$2"),
    # <ref name="Fred" /ref> --> <ref name="Fred"/>, <ref name="Fred" //> --> <ref name="Fred"/> or <ref name=Fred //> --> <ref name="Fred"/> but leave <ref name=a/ref>
    (
        _R(
            r'(?:(<\s*ref\s+name\s*=\s*"?[^<>="\/]+?"?)\s*/\s*/|(<\s*ref\s+name\s*=\s*"[^<>="\/]+?")\s*/\s*ref)\s*>',
            O.IGNORE_CASE,
        ),
        "$1$2/>",
    ),
    # <ref name="Fred""> or <ref name="Fred".> or <ref name="Fred".> or <ref name="Fred"=> or <ref name=Fred=> --> <ref name="Fred">
    (
        _R(r'(<\s*ref\s+name\s*=\s*"?[^<>="\/]+?)(?:(")["\.\']|(")?=)(\s*/?)>', O.IGNORE_CASE),
        "$1$2$3$4>",
    ),
    # <ref name=""Fred"> --> <ref name="Fred">
    (_R(r'(<\s*ref\s+name\s*=\s*)[“‘”’"]"([^<>="\/]+?)"*(\s*/?)>', O.IGNORE_CASE), r'$1"$2"$3>'),
    # <ref name = ”Fred”> --> <ref name="Fred">
    (
        _R(
            r'(<\s*ref\s+name\s*=\s*)(?:[“‘”’]+(?<val>[^<>="\/]+?)[“‘”’]*|[“‘”’]*(?<val>[^<>="\/]+?)[“‘”’]+)(\s*/?>)',
            O.IGNORE_CASE,
        ),
        r'$1"${val}"$2',
    ),
    # <ref name = ''Fred'> --> <ref name="Fred"> (two apostrophes) or <ref name = 'Fred''> --> <ref name="Fred"> (two apostrophes)
    (
        _R(
            r'(<\s*ref\s+name\s*=\s*)(?:\'\'+(?<val>[^<>="\/]+?)\'+|\'+(?<val>[^<>="\/]+?)\'\'+)(\s*/?>)',
            O.IGNORE_CASE,
        ),
        r'$1"${val}"$2',
    ),
    # <ref name=foo bar> --> <ref name="foo bar">, match when spaces or /
    (
        _R(r'(<\s*ref\s+name\s*=\s*)([^<>="\']+?[ /][^<>="\'/ ]+?)(\s*/?>)', O.IGNORE_CASE),
        r'$1"$2"$3',
    ),
    # <ref name=foo bar> --> <ref name="foo bar">, match when non-ASCII characters ([\x00-\xff]*)
    (
        _R(
            r'(<\s*ref\s+name\s*=\s*)([^<>="\'\/]*?[^\x00-\xff]+?[^<>="\'\/]*?)(\s*/?>)',
            O.IGNORE_CASE,
        ),
        r'$1"$2"$3',
    ),
    # <ref name=foo bar"> --> <ref name="foo bar"> or <ref name="foo bar> --> <ref name="foo bar">
    (
        _R(
            r'(<\s*ref\s+name\s*=?\s*)(?:[\'`”]*(?<val>[^<>="\/]+?)"|"(?<val>[^<>="\/]+?)[\'`”]*)(\s*/?>)',
            O.IGNORE_CASE,
        ),
        r'$1"${val}"$2',
    ),
    # <ref name "foo bar"> or <ref name "foo bar"=> --> <ref name="foo bar">
    (_R(r'(<\s*ref\s+name\s*)[\+\-"]?(\s*"[^<>="\/]+?"\s*/?)=?>', O.IGNORE_CASE), "$1=$2>"),
    # <ref "foo bar"> --> <ref name="foo bar">
    (_R(r'(<\s*ref\s+)=?\s*("[^<>="\/]+?"\s*/?>)', O.IGNORE_CASE), "$1name=$2"),
    # ref name typos
    (_R(r"(<\s*ref\s+n)(me\s*=)", O.IGNORE_CASE), "$1a$2"),
    # <ref name="Fred" Smith> --> <ref name="Fred Smith">
    (
        _R(
            r'(<\s*ref\s+name\s*=\s*"[^<>="\/]+?)"([^<>="\/]{2,}?)(?<!\s+)(?=\s*/?>)', O.IGNORE_CASE
        ),
        r'$1$2"',
    ),
    # <ref NAME= --> <ref name=
    # <refname= --> <ref name=
    # <ref name="ref name= --> <ref name=
    (
        _R(
            r'<(?:\s*ref(?:\s+NAME|name|\s+name\s*=\s*name|\s+name\s*=\s*"\s*ref\s+name)| +ref name)(\s*=)'
        ),
        "<ref name$1",
    ),
)

# Matches possibly bad ref tags, but not the most common valid formats
_PossiblyBadRefTags = _R(
    r'<\s*[Rr][Ee][Ff][^<>]*>(?<!(?:<ref name *= *[\w0-9\-.]+( ?/)?>|<ref>|<ref name *= *"[^{}"<>]+"( ?/)?>))'
)

# <ref>...<ref/> or <ref>...</red> --> <ref>...</ref>
_RedRef = _R(
    r'(<\s*ref(?:\s+name\s*=[^<>]*?)?\s*>[^<>"]+?)<\s*(?:/\s*red|ref\s*/)\s*>', O.IGNORE_CASE
)

_AllTagsSpace = _R(r"<[^<>]+> *")

_EmptyRefTags = _R(r"<ref>\s*</ref>")

_NamedRefExcessQuotes = _R(r'(<ref\s+name\s*=\s*")([^<>]+?)("\s*/?\s*>)')

# Regex.IsMatch/Replace calls with inline patterns in AWB
_DupePunctuation = _R(r"([,\.;:\?])\1")
_ClosingRef = _R(r"<\s*/\s*ref")
_CiteDoiPmidPrefix = _R(r"[Cc]ite (pmid|doi)\s*\|\s*")
_YearMaskR = _R(_YearMask)
_PageMaskR = _R(_PageMask)
_RefCloseNewline = _R("</ref ?\r\n")
_RefCaseQuick = _R(r"R[Ee][Ff]|r[Ee]F")
_RefCase = _R(r"(<\s*\/?\s*)(?:R[Ee][Ff]|r[Ee]F)(\s*(?:>|name\s*=))")
_SpacesBetweenRefs = _R(
    r"(</ref>|<ref\s*name\s*=[^{}<>]+?\s*\/\s*>) +(?=<ref(?:\s*name\s*=[^{}<>]+?\s*\/?\s*)?>)"
)
_RefThenWord = _R(r"(</ref>|<ref\s*name\s*=[^{}<>]+?\s*\/\s*>)(\w)")
_SpacesAfterPunctuationBeforeRef = _R(r"(?<=[,\.:;]) +(<ref(?:\s*name\s*=[^{}<>]+?\s*\/?\s*)?>)")
_SpacesAtRefStart = _R(r"(<ref[^<>\{\}\/]*>) +")
_BadClosingRef = _R(r"<(?:\s*/(?:\s+ref\s*|\s*ref\s+)|\s+/\s*ref\s*)>")
_SpacesAtRefEnd = _R(r" +</ref>")
_SpacesAfterRefZh = _R(r"(</ref>|<ref\s*name\s*=[^{}<>]+?\s*\/\s*>) +")
_ValidRefTag = _R(r'(?:<ref name *= *[\w0-9\-.]+( ?/)?>|<ref name *= *"[^{}"<>]+"( ?/)?>)|</ref>')
_EmptyNameCondensed = _R(r'name *= *"" */>')
_EmptyRefName = _R(r'<\s*ref\s+name[\s"]*=?[\s"]*(?:group\s*=\s*)?>')
_SplitTemplateOrTag = _R(r"[{<]")


def _parsers_instance() -> Parsers:
    # imported here: parsers.py imports this module
    from pyawb.core.parsers.parsers import Parsers

    return Parsers()


def reorder_references(article_text: str) -> str:
    """Put consecutive named references in order of first use; allows {{rp}}, leaves grouped refs
    ([[WP:REFGROUP]]) and the {{refs}} / <references>...</references> section alone."""
    referencestags = _refs_template_index(article_text)

    # named references and the index of their first occurrence (not in the references section)
    named_refs_indexes: dict[str, int] = {}
    for n in _get_named_refs(article_text):
        if n.index <= referencestags:
            named_refs_indexes.setdefault(n.group(2), n.index)

    for _ in range(9):  # allows for up to 9 consecutive references
        article_text_before = article_text

        for m in _OutofOrderRefs1.matches(article_text):
            ref1 = m.group(1)
            ref1_index = named_refs_indexes.get(m.group(4), 0)
            ref2_index = m.index

            if ref2_index > ref1_index > 0 and m.start(3) < referencestags:
                whitespace = m.group(2)
                rptemplate = m.group(5)
                ref2 = m.group(3)
                article_text = article_text.replace(
                    ref1 + whitespace + ref2 + rptemplate, ref2 + rptemplate + whitespace + ref1
                )

        article_text = _reorder_refs(
            article_text, _OutofOrderRefs2, referencestags, named_refs_indexes
        )
        article_text = _reorder_refs(
            article_text, _OutofOrderRefs3, referencestags, named_refs_indexes
        )

        if article_text_before == article_text:
            break

    return article_text


def _refs_template_index(article_text: str) -> int:
    """Index of {{reflist}}, {{refs}} or <references>, or the text length if there is none."""
    r1 = W.for_site(current_site()).ReferenceList.match(article_text)
    if r1:
        return r1.index
    r2 = _RefsTag.match(article_text)
    if r2:
        return r2.index
    return len(article_text)


def refs_after_punctuation(article_text: str) -> str:
    """Put <ref> and {{sfn}} references after punctuation (WP:REFPUNC); en and a few other wikis."""
    if current_site().lang_code not in _RefsAfterPunctuationAllowedLangs:
        return article_text

    article_text_original = article_text
    has_punctuation_before_these_templates = _templates.template_exists(
        _templates.get_all_templates(article_text), _PunctuationBeforeTheseTemplates
    )

    article_text = _refs_before_punctuation(article_text)

    if has_punctuation_before_these_templates:
        all_refs = [m.value for m in _get_unnamed_refs(article_text)]
        all_refs.extend(m.value for m in _get_named_refs(article_text))

        # do not move punctuation after templates if have any matches on these templates and
        # punctuation within <ref> tags where the punctuation is valid as-is
        if not any(_PunctuationAfterTemplate.is_match(r) for r in all_refs):
            while _PunctuationAfterTemplate.is_match(article_text):
                article_text = _PunctuationAfterTemplate.replace(article_text, "${punc}${template}")
                article_text = _refs_before_punctuation(article_text)

    # Performance: only run the slow "after punctuation" regexes if some piece of text before a
    # template or tag ends in duplicate punctuation
    tex = [t for t in _SplitTemplateOrTag.split(article_text) if t]
    tex = [s[-2:] for s in dict.fromkeys(tex) if len(s) > 1]
    dupe_punctuation_found = any(_DupePunctuation.is_match(s) for s in dict.fromkeys(tex))

    # clean duplicate punctuation before ref, not for !!, could be part of wiki table
    if dupe_punctuation_found:
        article_text = _RefsAfterDupePunctuation.replace(article_text, "$1$2$3")

    if has_punctuation_before_these_templates and dupe_punctuation_found:
        article_text = _TemplateAfterDupePunctuation.replace(article_text, "$1$2${template}")

    # if punctuation moved, it may not have whitespace after it
    if article_text_original != article_text:
        article_text = fix_reference_tags(article_text)

    return article_text


def _refs_before_punctuation(article_text: str) -> str:
    """Move punctuation after <ref> tags to before them; clean dupe punctuation before <ref>."""
    skip = False
    # 'quick' regexes are used for runtime performance saving
    if _RefsBeforePunctuationQuick.is_match(article_text):
        while not skip and _RefsBeforePunctuationR.is_match(article_text):
            current = article_text

            def me(m: DotNetMatch, current: str = current) -> str:
                nonlocal skip
                # do not move punctuation if colon after ref on a line starting with semi colon
                if m.group(2) == ":" and any(
                    m.value in line.value for line in _LineStartsSemiColon.matches(current)
                ):
                    skip = True
                    return m.value
                return m.group(2) + m.group(1) + m.group(3)

            article_text = _RefsBeforePunctuationR.replace(article_text, me)
            article_text = _RefsAfterDupePunctuation.replace(article_text, "$1$2$3")
    return article_text


def _reorder_refs(
    article_text: str,
    outof_order_regex: DotNetRegex,
    referencestagindex: int,
    named_refs_indexes: dict[str, int],
) -> str:
    """Swap pairs of references matched by outof_order_regex that are out of numerical order."""
    for m in outof_order_regex.matches(article_text):
        if m.start(5) >= referencestagindex:
            break  # all further matches beyond refs template
        ref1_index = named_refs_indexes.get(m.group(2), 0)
        ref2_index = named_refs_indexes.get(m.group(6), 0)

        if ref1_index > ref2_index and ref1_index > 0:
            ref1 = m.group(1)
            ref2 = m.group(5)
            whitespace = m.group(4)
            rptemplate1 = m.group(3)
            rptemplate2 = m.group(7)
            article_text = article_text.replace(
                ref1 + rptemplate1 + whitespace + ref2 + rptemplate2,
                ref2 + rptemplate2 + whitespace + ref1 + rptemplate1,
            )
    return article_text


def duplicate_named_references(article_text: str) -> str:
    """Condense repeated named references, and unnamed duplicates of a named one, to <ref name=.../>.

    Leaves refs declared in template calls alone, and leaves the text unchanged if one ref name has
    conflicting values (that needs manual correction).
    """
    from pyawb.core import tools

    article_text_original = article_text
    s = W.for_site(current_site())
    named_refs: dict[str, str] = {}

    # disable if known-incompatible templates present
    no_condensing = s.NoRefCondensingTemplates
    assert no_condensing is not None
    if any(no_condensing.is_match(t) for t in _templates.get_all_template_detail(article_text)):
        return article_text

    while True:
        reparse = False
        named_refs.clear()
        reflist_index = _refs_template_index(article_text)

        # refs declared in template calls: don't condense any of these
        templates = [
            t
            for t in _templates.get_all_template_detail(article_text)
            if W.NamedReferences.is_match(t)
        ]
        ref_names_in_templates = [r.group(2) for r in _get_named_refs(" ".join(templates))]

        for m in [m for m in _get_named_refs(article_text) if m.group(3)]:
            ref_name, named_ref_value = m.group(2), m.group(3)

            if named_ref_value not in named_refs:
                # same ref name with different values: requires manual correction of article
                if ref_name in named_refs.values():
                    return article_text_original
                named_refs[named_ref_value] = ref_name
                continue

            # we've already seen this reference, can condense later ones
            name2 = named_refs.get(named_ref_value, "")
            if name2 and name2 == ref_name and len(named_ref_value) >= 25:
                # don't condense refs in {{reflist...}}
                if 0 < reflist_index < m.index:
                    continue
                # don't condense if declared in template
                if ref_name in ref_names_in_templates:
                    continue
                if m.index > len(article_text):
                    reparse = True
                    break

                # <ref name="Fred">(...)</ref>....<ref name="Fred">\2</ref> --> ..<ref name="Fred"/>,
                # minimum 25 characters to avoid short refs
                texttomatch = article_text[: m.index]
                textaftermatch = article_text[m.index :]

                if m.value in textaftermatch:
                    # retain quote format, if any, of existing named ref
                    quotes_used = _RefNameStart.match(m.value).group(1)
                    textaftermatch, _ = tools.replace_once(
                        textaftermatch,
                        m.value,
                        "<ref name=" + quotes_used + ref_name + quotes_used + "/>",
                    )
                    article_text = texttomatch + textaftermatch
                else:
                    reparse = True
                    break

        # (first named): <ref name="Fred">(...)</ref>....<ref>\2</ref> --> ..<ref name="Fred"/>
        # (second named): <ref>(...)</ref>....<ref name="Fred">\2</ref> --> ..<ref name="Fred"/>
        unr = [m for m in _get_unnamed_refs(article_text) if m.group(1).strip() in named_refs]
        for m in unr:
            newname = named_refs.get(m.group(1).strip())
            if newname is not None:
                article_text = article_text.replace(m.value, '<ref name="' + newname + '"/>')

        if not reparse:
            break

    return article_text


def has_named_references(article_text: str) -> bool:
    """Whether the text has named references in short format <ref name=foo />."""
    article_text = W.Comments.replace(article_text, "")
    return any(
        not _ClosingRef.is_match(m.value)
        for m in W.NamedReferencesIncludingCondensed.matches(article_text)
    )


def duplicate_unnamed_references(article_text: str) -> str:
    """Name duplicate unnamed <ref>s per [[WP:REFNAME]] and condense the later uses."""
    from pyawb.core import tools

    # On en-wiki AWB is asked not to add named references to an article if there are none
    # currently, as some users feel this is a change of citation style ([[WP:CITE]])
    if current_site().lang_code == "en" and not has_named_references(article_text):
        return article_text

    # disable if known-incompatible templates present
    no_condensing = W.for_site(current_site()).NoRefCondensingTemplates
    assert no_condensing is not None
    if any(no_condensing.is_match(t) for t in _templates.get_all_template_detail(article_text)):
        return article_text

    # all unnamed refs, filtered to those with duplicate content (grouped as LINQ GroupBy does:
    # groups in order of first appearance)
    groups: dict[str, list[DotNetMatch]] = {}
    for m in _get_unnamed_refs(article_text):
        groups.setdefault(m.group(1).strip(), []).append(m)
    all_refs = [m for g in groups.values() if len(g) > 1 for m in g]

    # do not apply to refs with ibid/loc cit etc.
    all_refs = [m for m in all_refs if not W.IbidLocCitation.is_match(m.value)]

    if not all_refs:
        return article_text

    # unnamed refs declared in template calls: don't condense any of these
    templates = [t for t in _templates.get_all_template_detail(article_text) if "<ref>" in t]
    ref_values_in_templates = [r.group(1) for r in _get_unnamed_refs(" ".join(templates))]

    ref_name_content: dict[str, str] = {}
    for m in all_refs:
        inner_text = m.group(1).strip()
        friendly_name = ref_name_content.get(inner_text)
        if friendly_name is None:
            friendly_name = derive_reference_name(article_text, inner_text)

            # check reference name was derived
            if len(friendly_name) <= 3:
                continue

            article_text, _ = tools.replace_once(
                article_text, m.value, '<ref name="' + friendly_name + '">' + inner_text + "</ref>"
            )
            ref_name_content[inner_text] = friendly_name
        elif inner_text in ref_values_in_templates:
            # don't condense ref declared in template
            article_text = article_text.replace(
                m.value, '<ref name="' + friendly_name + '">' + inner_text + "</ref>"
            )
        else:
            article_text = article_text.replace(m.value, '<ref name="' + friendly_name + '"/>')

    return article_text


def same_ref_different_name(article_text: str) -> str:
    """Give named references with the same text but different names one name."""
    article_text_original = article_text
    # refs with same name, but one is very short, so just change to <ref name=foo/> notation
    article_text = _same_named_ref_short_text(article_text)

    # loop as could be a set of identical references with multiple different names in use
    current_article_text = ""

    while current_article_text != article_text:
        current_article_text = article_text

        # (ref name, ref content) of named refs with content
        named_refs_list = [
            (m.group(2), m.group(3)) for m in _get_named_refs(article_text) if m.group(3)
        ]

        # filter list to those where ref content occurs more than once (LINQ GroupBy order)
        by_value: dict[str, list[tuple[str, str]]] = {}
        for kvp in named_refs_list:
            by_value.setdefault(kvp[1], []).append(kvp)
        named_refs_list = [kvp for g in by_value.values() if len(g) > 1 for kvp in g]

        if not named_refs_list:
            return article_text

        # ref names used in group refs cannot be changed
        refs_in_group_ref = [
            _RefNameFromGroup.match(m.value).group("nm").strip("'\"")
            for m in W.RefsGrouped.matches(article_text)
        ]

        named_refs: dict[str, str] = {}

        for refname, refvalue in named_refs_list:
            if refvalue not in named_refs:
                named_refs[refvalue] = refname
                continue

            existingname = named_refs[refvalue]

            # don't apply to ibid short ref, don't change if ref name used in a group ref
            if (
                existingname
                and existingname != refname
                and not W.IbidLocCitation.is_match(refvalue)
                and existingname not in refs_in_group_ref
            ):
                new_ref_name, old_ref_name = refname, existingname

                # use longest ref name as the one to keep
                if (
                    len(existingname) > len(refname)
                    and "autogenerated" not in existingname
                    and "ReferenceA" not in existingname
                ) or ("autogenerated" in refname or "ReferenceA" in refname):
                    new_ref_name = existingname
                    old_ref_name = refname

                # rename the named ref and any short named refs of same name (<ref name="Foo" />)
                a = _R(
                    r"""<\s*ref\s+name\s*=\s*(?:"|')?"""
                    + rx.escape(old_ref_name)
                    + r"""(?:"|')?\s*(?=/\s*>|>\s*"""
                    + rx.escape(refvalue)
                    + r"\s*</ref>)"
                )
                article_text = a.replace(article_text, '<ref name="' + new_ref_name + '"')

    # performance: only call if changes made
    if article_text_original != article_text:
        article_text = duplicate_named_references(article_text)

    return article_text


def _same_named_ref_short_text(article_text: str) -> str:
    """Refs with the same name where one is very short: use <ref name=foo/> for the short one."""
    # Performance: only attempt replacement if short named refs and matching long ones are found
    just_named_refs = "".join(m.value for m in _get_named_refs(article_text))
    short_named = [m.group(2) for m in _ShortNameReference.matches(just_named_refs)]

    if short_named:
        for m in _LongNamedReferences.matches(article_text):
            refname = m.group(2)

            # don't apply if short ref is a page ref
            if refname in short_named and len(m.group(3)) > 30:
                article_text = _R(
                    r"""(<\s*ref\s+name\s*=\s*(?:"|')?("""
                    + rx.escape(refname)
                    + r""")(?:"|')?\s*>\s*([^<>]{1,9}?|\[?[Ss]ee above\]?|{{\s*[Cc]ite *\w+\s*}})\s*<\s*/\s*ref>)"""
                ).replace(
                    article_text,
                    lambda m2, refname=refname: (
                        m2.value
                        if _PageRef.is_match(m2.group(3))
                        else '<ref name="' + refname + '"/>'
                    ),
                )

    return article_text


def _extract_reference_name_components(
    reference: str, reference_name_mask: DotNetRegex, components: int
) -> str:
    """Reference name from the first `components` groups of reference_name_mask's match."""
    reference_name = ""
    m = reference_name_mask.match(reference)
    if m:
        reference_name = m.group(1)
        if components > 1:
            reference_name += " " + m.group(2)
        if components > 2:
            reference_name += " " + m.group(3)
    return _clean_derived_reference_name(reference_name)


def _external_link_text(m: DotNetMatch) -> str:
    # AWB: m.Value.Substring(m.Value.IndexOf(" ")).TrimEnd(']'). With no space, IndexOf is -1
    # and .NET throws; keep the link text instead of failing the whole general-fixes run.
    space = m.value.find(" ")
    if space < 0:
        return m.value
    return m.value[space:].rstrip("]")


def _clean_derived_reference_name(derived_name: str) -> str:
    """Remove unwanted punctuation and comments from a derived reference name."""
    derived_name = W.PipedWikiLink.replace(derived_name, "$2")  # piped wikilinks -> text value
    derived_name = W.ExternalLinks.replace(derived_name, _external_link_text)

    # remove templates, but not if whole derivedName is a template
    if derived_name != W.Template.match(derived_name).value:
        derived_name = W.Template.replace(derived_name, "")

    # rm comments from ref name, might be masked
    derived_name = _CommentOrFloorNumber.replace(derived_name, "")
    derived_name = derived_name.strip(_CharsToTrim)
    derived_name = _SequenceOfQuotesInDerivedName.replace(derived_name, "")  # remove chars
    derived_name = _WhitespaceInDerivedName.replace(derived_name, " ")  # spacing fixes
    derived_name = derived_name.replace("&ndash;", "–")

    p = _parsers_instance()
    derived_name = p.fix_dates_a(derived_name)
    derived_name = p.fix_dates_b(derived_name, False, False)

    return "" if _DateRetrievedOrAccessed.is_match(derived_name) else derived_name


def derive_reference_name(article_text: str, reference: str) -> str:
    """Name for a reference from author and date, website, title etc., not already used in
    article_text; "" if none could be derived."""
    from pyawb.core import tools
    from pyawb.core.parsers import citetemplates as _cite

    derived_reference_name = ""

    # try parameters from a citation: lastname, year and page
    citation_template = _CitationCiteBook.match(reference).value

    if len(citation_template) > 10:
        last = tools.get_template_parameter_value(reference, "last")
        if len(last) < 1:
            last = tools.get_template_parameter_value(reference, "author")

        if len(last) > 1:
            derived_reference_name = last
            year = tools.get_template_parameter_value(reference, "year")
            pages = _CiteTemplatePagesParameter.match(reference).value.strip()

            if len(year) > 3:
                derived_reference_name += " " + year
            else:
                date = _cite.YearOnly.match(
                    tools.get_template_parameter_value(reference, "date")
                ).value
                if len(date) > 3:
                    derived_reference_name += " " + date

            if pages:
                derived_reference_name += " " + pages

            derived_reference_name = _clean_derived_reference_name(derived_reference_name)
        else:
            # otherwise try title - trans-title first to prefer local language
            title = tools.get_template_parameter_value(reference, "trans-title")
            if not title:
                title = tools.get_template_parameter_value(reference, "title")

            if 3 < len(title) < 35:
                derived_reference_name = title
            derived_reference_name = _clean_derived_reference_name(derived_reference_name)

            # try publisher, then work
            for parameter in ("publisher", "work"):
                if len(derived_reference_name) < 4:
                    title = tools.get_template_parameter_value(reference, parameter)
                    if 3 < len(title) < 35:
                        derived_reference_name = title
                    derived_reference_name = _clean_derived_reference_name(derived_reference_name)

    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # description of a simple external link; website URL, allowing a name before the link;
    # Harvnb template {{Harvnb|Young|1852|p=50}}
    for mask, components in ((_UrlShortDescription, 1), (_UrlDomain, 1), (_HarvnbTemplate, 3)):
        derived_reference_name = _extract_reference_name_components(reference, mask, components)
        if _reference_name_valid(article_text, derived_reference_name):
            return derived_reference_name

    # cite pmid / cite doi
    derived_reference_name = _CiteDoiPmidPrefix.replace(
        _extract_reference_name_components(reference, _CiteDOIPMID, 3), "$1"
    )
    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # now just try to use the whole reference if it's short (<35 characters)
    if len(reference) < 35:
        derived_reference_name = _extract_reference_name_components(
            reference, _WholeShortReference, 1
        )
    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # now try title of a citation
    derived_reference_name = _extract_reference_name_components(reference, _CiteTemplateTitle, 1)
    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # name...year...page. Regex checks to avoid excessive backtracking
    if _YearMaskR.is_match(reference) and _NameYear.is_match(reference):
        derived_reference_name = _extract_reference_name_components(reference, _NameYearPage, 3)
    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # name...page
    if _PageMaskR.is_match(reference):
        derived_reference_name = _extract_reference_name_components(reference, _NamePage, 2)
    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # name...year
    if _YearMaskR.is_match(reference):
        derived_reference_name = _extract_reference_name_components(reference, _NameYear, 2)
    if _reference_name_valid(article_text, derived_reference_name):
        return derived_reference_name

    # fallback: generic ReferenceA to ReferenceZ
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        derived_reference_name = "Reference" + c
        if _reference_name_valid(article_text, derived_reference_name):
            return derived_reference_name

    return (
        derived_reference_name
        if _reference_name_valid(article_text, derived_reference_name)
        else ""
    )


def _reference_name_valid(article_text: str, derived_reference_name: str) -> bool:
    """Name at least 3 characters, not 'http', and not already used in the article."""
    return (
        not _R(_RefName + rx.escape(derived_reference_name) + r"""(?:"|')?\s*/?\s*>""").is_match(
            article_text
        )
        and len(derived_reference_name) >= 3
        and derived_reference_name not in BadRefNames
    )


def _reflist_match_evaluator(m: DotNetMatch) -> str:
    # don't change anything if div tags mismatch
    if len(_DivStart.matches(m.value)) != len(_DivEnd.matches(m.value)):
        return m.value

    # {{reflist}} template not used on sv-wiki
    if current_site().lang_code == "sv":
        return "<references/>"

    if "references-2column" in m.value or "column-count:2" in m.value:
        return "{{Reflist|2}}"

    return "{{Reflist}}"


def fix_reference_list_tags(article_text: str) -> str:
    """Replace old reference list markup with {{Reflist}} (<references/> on sv-wiki)."""
    # check for performance
    if "<references" not in article_text.lower():
        return article_text

    article_text = _ReferenceListSmallTags.replace(article_text, _reflist_match_evaluator)
    return _ReferenceListTags.replace(article_text, _reflist_match_evaluator)


def simplify_reference_tags(article_text: str) -> str:
    """<ref name="blah"></ref> --> <ref name="blah" />."""
    return _EmptyReferences.replace(article_text, "$1 />")


def add_missing_reflist(article_text: str) -> str:
    """Fix <references> missing its '/'; otherwise, if the article uses refs but has nothing to
    display them, add {{Reflist}} in the appropriate place (en only)."""
    from pyawb.core.parsers import parsers as _parsers

    if not _parsers.is_missing_references_display(article_text) or current_site().lang_code != "en":
        return article_text

    if _ReferencesMissingSlash.is_match(article_text):
        return _ReferencesMissingSlash.replace(article_text, "<references/>")

    # Rename ==Links== to ==External links==
    article_text = _LinksHeading.replace(article_text, "$1External links$2")

    # add to any existing references section if present
    if _ReferencesHeadingLevel2.is_match(article_text):
        article_text = _ReferencesHeadingLevelLower.replace(article_text, "$1\r\n{{Reflist}}")
    else:
        article_text += "\r\n==References==\r\n{{Reflist}}"

        # now sort metadata in case Category at top of article
        article_text = _parsers_instance().sort_meta_data(article_text, "A", False)

        if _ExternalLinksHeading.is_match(article_text):
            # try to move just above external links
            article_text = _ExternalLinksToReferences.replace(article_text, "$2\r\n$1")
        elif _Category.is_match(article_text):
            # try to move just above categories
            article_text = _CategoryToReferences.replace(article_text, "$3\r\n$1$2")
        else:
            # not moved, so extra blank line required before heading
            article_text = article_text.replace("\r\n==References==", "\r\n\r\n==References==")

    return article_text


def fix_reference_tags(article_text: str) -> str:
    """Formatting fixes to <ref> tags: case, whitespace (WP:REFPUNC), quotes, broken names."""
    # Performance: collect the tags that look like ref tags, ignoring valid ones, and only apply
    # regexes where relevant tags are found
    all_tags_list = list(
        dict.fromkeys(
            m.value
            for m in _AllTagsSpace.matches(article_text)
            if m.value.lower().find("re") > 0
            and m.value != "<ref>"
            and m.value != "</ref>"
            and not m.value.startswith("<references")
        )
    )

    # fix incorrect closing </ref>
    article_text = _RefCloseNewline.replace(article_text, "</ref>\r\n")

    # <REF>, </REF> and <Ref> to lowercase ref
    if any(_RefCaseQuick.is_match(s) for s in all_tags_list):
        article_text = _RefCase.replace(article_text, "$1ref$2")

    # remove any spaces between consecutive references -- WP:REFPUNC
    if any(s.endswith(" ") for s in all_tags_list):
        article_text = _SpacesBetweenRefs.replace(article_text, "$1")

    # ensure a space between a reference and text (reference within a paragraph) -- WP:REFPUNC
    article_text = _RefThenWord.replace(article_text, "$1 $2")

    # remove spaces between punctuation and references -- WP:REFPUNC
    if " <ref" in article_text:
        article_text = _SpacesAfterPunctuationBeforeRef.replace(article_text, "$1")

    # empty <ref>...</ref> tags
    while _EmptyRefTags.is_match(article_text):
        article_text = _EmptyRefTags.replace(article_text, "")

    # Trailing spaces at the beginning of a reference, within the reference
    if any(s.endswith(" ") for s in all_tags_list):
        article_text = _SpacesAtRefStart.replace(article_text, "$1")

    # whitespace cleaning of </ref>
    if any(_BadClosingRef.is_match(s) for s in all_tags_list):
        article_text = _BadClosingRef.replace(article_text, "</ref>")

    # trim trailing spaces at the end of a reference, within the reference
    if " </ref>" in article_text:
        article_text = _SpacesAtRefEnd.replace(article_text, "</ref>")

    if any(s.startswith(("<ref/>", "</red>")) for s in all_tags_list):
        article_text = _RedRef.replace(article_text, "$1</ref>")

    # Chinese do not use spaces to separate sentences
    if current_site().lang_code == "zh":
        article_text = _SpacesAfterRefZh.replace(article_text, "$1")

    # Performance: apply ref tag fixes only if have ref tags that might be invalid
    if any(not _ValidRefTag.is_match(s) for s in all_tags_list):
        # empty ref name: <ref name=> or <ref name = group =>
        # T199058: <ref name="">x</ref> then <ref name=""/> is valid, don't remove former if latter also exists
        if not any(_EmptyNameCondensed.is_match(t) for t in all_tags_list):
            article_text = _EmptyRefName.replace(article_text, "<ref>")

        article_text = _PossiblyBadRefTags.replace(article_text, _fix_reference_tags_me)

        # remove double quotes inside a ref name in double quotes, ignore group refs
        def excess_quotes(m: DotNetMatch) -> str:
            if W.RefsGrouped.is_match(m.value if "/" in m.group(3) else m.value + "a</ref>"):
                return m.value
            return m.group(1) + m.group(2).replace('"', "") + m.group(3)

        article_text = _NamedRefExcessQuotes.replace(article_text, excess_quotes)

    return article_text


def _fix_reference_tags_me(m: DotNetMatch) -> str:
    current = m.value
    for regex, replacement in _RefSimple:
        current = regex.replace(current, replacement)
    return current


# AWB caches the last 10 results of each, with a lock; lru_cache is thread-safe.
@functools.lru_cache(maxsize=10)
def _unnamed_refs(article_text: str) -> tuple[DotNetMatch, ...]:
    return tuple(W.UnnamedReferences.matches(article_text))


@functools.lru_cache(maxsize=10)
def _named_refs(article_text: str) -> tuple[DotNetMatch, ...]:
    return tuple(W.NamedReferencesIncludingCondensed.matches(article_text))


def _get_unnamed_refs(article_text: str) -> tuple[DotNetMatch, ...]:
    """All unnamed refs in the text (cached)."""
    return _unnamed_refs(article_text)


def _get_named_refs(article_text: str) -> tuple[DotNetMatch, ...]:
    """All named refs, including condensed ones, in the text (cached)."""
    return _named_refs(article_text)


def total_refs_not_grouped(article_text: str) -> int:
    """Number of <ref> references, excluding grouped refs."""
    return len(W.Refs.matches(article_text)) - len(W.RefsGrouped.matches(article_text))
