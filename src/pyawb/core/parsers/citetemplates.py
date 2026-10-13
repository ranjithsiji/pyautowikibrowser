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
# Ported from AutoWikiBrowser WikiFunctions/Parse/CiteTemplates.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Citation template fixes (port of Parse/CiteTemplates.cs): parameter clean-up, page ranges,
publisher to work, date formats, ambiguous dates and unknown parameters.
"""

# ruff: noqa: E501

from __future__ import annotations

from typing import TYPE_CHECKING

from pyawb.core import rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import fixdates as _fixdates
from pyawb.core.parsers import templates as _templates
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import SiteConfig, current_site
from pyawb.core.textutil import nested_template_regex

if TYPE_CHECKING:
    from pyawb.core.parsers.parsers import Parsers

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

# AWB builds these with WikiRegexes.MonthsNoGroup at static initialisation (English)
_MONTHS = W.for_site(SiteConfig.english()).MonthsNoGroup

# -- static regexes (generated from CiteTemplates.cs by tools/porting/cs2py.py, then edited) -----

_CiteUrl = _R(r'\|\s*url\s*=\s*([^\[\]<>"\s]+)')

_WorkInItalics = _R(r"(\|\s*work\s*=\s*)''([^'{}\|]+)''(?=\s*(?:\||}}))")

_CiteTemplatePagesPP = _R(
    r"(?<=\|\s*pages?\s*=\s*)p(?:p|gs?)?(?:\.|\b)(?:&nbsp;|\s*)(?=[^{}\|]+(?:\||}}))"
)

_CiteTemplatesJournalVolume = _R(
    r"(?<=\|\s*volume\s*=\s*)vol(?:umes?|\.)?(?:&nbsp;|:)?", O.COMPILED | O.IGNORE_CASE
)

_CiteTemplatesJournalVolumeAndIssue = _R(
    r"(?<=\|\s*volume\s*=\s*[0-9VXMILC]+?)(?:[;,]?\s*(?:nos?[\.:; ]|(?:numbers?|issues?|iss)\s*[:; ]))",
    O.COMPILED | O.IGNORE_CASE,
)

_CiteTemplatesJournalIssue = _R(
    r"(?<=\|\s*issue\s*=\s*)(?:issues?|(?:nos?|iss)(?:[\.,;:]|\b)|numbers?[\.,;:]?)(?:&nbsp;)?",
    O.COMPILED | O.IGNORE_CASE,
)

_CiteTemplatesPageRangeName = _R(r"(\|\s*)page(\s*=\s*[0-9]+\s*(?:–|, )\s*[0-9])")

_AccessDateYear = _R(
    r"(?<=\|\s*access\-?date\s*=\s*(?:[1-3]?\d\s+"
    + _MONTHS
    + r"|\s*"
    + _MONTHS
    + r"\s+[1-3]?\d))(\s*)\|\s*accessyear\s*=\s*(20[012]\d)\s*(\||}})"
)

_AccessDayMonthDay = _R(r"\|\s*access(?:daymonth|month(?:day)?|year)\s*=\s*(?=\||}})")

_DateLeadingZero = _R(
    r"(?<=\|\s*(?:access|archive)?\-?date\s*=\s*)(?:0([1-9]\s+[A-Z][a-z]{2,})|(\s*[A-Z][a-z]{2,}\s)+0([1-9],?))(\s+(?:20[012]|1[89]\d)\d)?(\s*(?:\||}}))"
)

_LangTemplate = _R(r"(\|\s*language\s*=\s*)({{(\w{2}) icon}}\s*)(?=\||}})")

_UnspacedCommaPageRange = _R(r"((?:[ ,–]|^)[0-9]+),([0-9]+(?:[ ,–]|$))")

_ParametersToDequote = (r"title", r"trans_title")

_rpTemplate = nested_template_regex(r"rp")

_IdISBN = _R(r"^ISBN ?[:=]?\s*([\d \-]+X?)$")

_IdASIN = _R(r"^ASIN ?[:=]?\s*([\d \-]+X?)$")

_IdISSN = _R(r"^ISSN ?[:=]?\s*([0-9]{4}) *[- –]? *([0-9]{3}[0-9X])$", O.IGNORE_CASE)

YearOnly = _R(r"^[12]\d{3}$", O.COMPILED)

_ISBNDash = _R(r"(\d)[–](\d|X$)")

_BalancedArrows = _R(r"(?:‹([^›]+)›)")

_ArchiveOrgURL = _R(r"^https?://(?:web\.archive\.org|archive\.today)/(?:web/)?(\d{8})(?:\d{6}/)")

_PageFields = (r"page", r"pages", r"p", r"pp")

_PageRange = _R(r"\b([0-9]{1,8})\s*[-—]+\s*([0-9]{1,8})")

_SpacedPageRange = _R(r"(\d+) +(–|&ndash;) +(\d)")

_HiddenRegex = _R(r"⌊⌊⌊⌊(\d*)⌋⌋⌋⌋")

_CiteWebOrNews = nested_template_regex((r"cite web", r"citeweb", r"cite news", r"citenews"))

_PressPublishers = _R(r"(Associated Press|United Press International)", O.COMPILED | O.IGNORE_CASE)

_WorkParameterAndAliases = (r"work", r"newspaper", r"journal", r"periodical", r"magazine")

_SiCitStart = r"(?si)(\|\s*"

_CitAccessdate = _SiCitStart + r"(?:access|archive)\-?date\s*=\s*"

_CitDate = _SiCitStart + r"(?:archive|air)?date2?\s*=\s*"

_CiteTemplateIncorrectISOAccessdates: tuple[tuple[DotNetRegex, str], ...] = (
    (
        _R(_CitAccessdate + r")(1[0-2])[/_\-\.]?(1[3-9])[/_\-\.]?(?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$2-$3",
    ),
    (
        _R(_CitAccessdate + r")(1[0-2])[/_\-\.]?([23]\d)[/_\-\.]?(?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$2-$3",
    ),
    (
        _R(_CitAccessdate + r")(1[0-2])[/_\-\.]?\2[/_\-\.]?(?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$3-$2-$2",
    ),
    (
        _R(_CitAccessdate + r")(1[3-9])[/_\-\.]?(1[0-2])[/_\-\.]?(?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$3-$2",
    ),
    (
        _R(_CitAccessdate + r")(1[3-9])[/_\-\.]?0?([1-9])[/_\-\.]?(?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-0$3-$2",
    ),
    (_R(_CitAccessdate + r")(20[012]\d)0?([01]\d)[/_\-\.]([0-3]\d\s*(?:\||}}))"), "$1$2-$3-$4"),
    (_R(_CitAccessdate + r")(20[012]\d)[/_\-\.]([01]\d)0?([0-3]\d\s*(?:\||}}))"), "$1$2-$3-$4"),
    (
        _R(_CitAccessdate + r")(20[012]\d)[/_\-\.]?([01]\d)[/_\-\.]?([1-9]\s*(?:\||}}))"),
        "$1$2-$3-0$4",
    ),
    (
        _R(_CitAccessdate + r")(20[012]\d)[/_\-\.]?([1-9])[/_\-\.]?([0-3]\d\s*(?:\||}}))"),
        "$1$2-0$3-$4",
    ),
    (
        _R(_CitAccessdate + r")(20[012]\d)[/_\-\.]?([1-9])[/_\-\.]0?([1-9]\s*(?:\||}}))"),
        "$1$2-0$3-0$4",
    ),
    (
        _R(_CitAccessdate + r")(20[012]\d)[/_\-\.]0?([1-9])[/_\-\.]([1-9]\s*(?:\||}}))"),
        "$1$2-0$3-0$4",
    ),
    (_R(_CitAccessdate + r")(20[012]\d)[/_\.]?([01]\d)[/_\.]?([0-3]\d\s*(?:\||}}))"), "$1$2-$3-$4"),
    (
        _R(_CitAccessdate + r")([23]\d)[/_\-\.](1[0-2])[/_\-\.]?(?:20)?([012]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$3-$2",
    ),
    (
        _R(_CitAccessdate + r")([23]\d)[/_\-\.]0?([1-9])[/_\-\.](?:20)?([012]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-0$3-$2",
    ),
    (
        _R(
            _CitAccessdate
            + r")0?([1-9])[/_\-\.]?(1[3-9]|[23]\d)[/_\-\.]?(?:20)?([012]\d)(?=\s*(?:\||}}))"
        ),
        "${1}20$4-0$2-$3",
    ),
    (
        _R(_CitAccessdate + r")0?([1-9])[/_\-\.]?0?\2[/_\-\.]?(?:20)?([012]\d)(?=\s*(?:\||}}))"),
        "${1}20$3-0$2-0$2",
    ),
)
_CiteTemplateIncorrectISODates: tuple[tuple[DotNetRegex, str], ...] = (
    (
        _R(_CitDate + r"\[?\[?)(20\d\d|19[7-9]\d)[/_]?([01]\d)[/_]?([0-3]\d\s*(?:\||}}))"),
        "$1$2-$3-$4",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[0-2])[/_\-\.]?([23]\d)[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)0?([1-9])[/_\-\.]?([23]\d)[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-0$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)([23]\d)[/_\-\.]?0?([1-9])[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-0$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)([23]\d)[/_\-\.]?(1[0-2])[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[0-2])[/_\-\.]([23]\d)[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)0?([1-9])[/_\-\.]([23]\d)[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-0$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)([23]\d)[/_\-\.]0?([1-9])[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-0$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)([23]\d)[/_\-\.](1[0-2])[/_\-\.]?(?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[0-2])[/_\-\.]?(1[3-9])[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-$2-$3",
    ),
    (
        _R(
            _CitDate + r"\[?\[?)0?([1-9])[/_\-\.](1[3-9])[/_\-\.](19[7-9]\d|20\d\d)(?=\s*(?:\||}}))"
        ),
        "$1$4-0$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[3-9])[/_\-\.]?0?([1-9])[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-0$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[3-9])[/_\-\.]?(1[0-2])[/_\-\.]?(19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$4-$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[0-2])[/_\-\.](1[3-9])[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)([1-9])[/_\-\.](1[3-9])[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-0$2-$3",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[3-9])[/_\-\.]([1-9])[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-0$3-$2",
    ),
    (
        _R(_CitDate + r"\[?\[?)(1[3-9])[/_\-\.](1[0-2])[/_\-\.](?:20)?([01]\d)(?=\s*(?:\||}}))"),
        "${1}20$4-$3-$2",
    ),
    (
        _R(_CitDate + r")0?([1-9])[/_\-\.]0?\2[/_\-\.](20\d\d|19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$3-0$2-0$2",
    ),
    (_R(_CitDate + r")0?([1-9])[/_\-\.]0?\2[/_\-\.]([01]\d)(?=\s*(?:\||}}))"), "${1}20$3-0$2-0$2"),
    (
        _R(_CitDate + r")(1[0-2])[/_\-\.]\2[/_\-\.]?(20\d\d|19[7-9]\d)(?=\s*(?:\||}}))"),
        "$1$3-$2-$2",
    ),
    (_R(_CitDate + r")(1[0-2])[/_\-\.]\2[/_\-\.]([01]\d)(?=\s*(?:\||}}))"), "${1}20$3-$2-$2"),
    (
        _R(
            _CitDate
            + r")((?:\[\[)?20\d\d|1[5-9]\d{2})[/_\-\.]([1-9])[/_\-\.]0?([1-9](?:\]\])?\s*(?:\||}}))"
        ),
        "$1$2-0$3-0$4",
    ),
    (
        _R(
            _CitDate
            + r")((?:\[\[)?20\d\d|1[5-9]\d{2})[/_\-\.]0?([1-9])[/_\-\.]([1-9](?:\]\])?\s*(?:\||}}))"
        ),
        "$1$2-0$3-0$4",
    ),
    (
        _R(
            _CitDate
            + r")((?:\[\[)?20\d\d|1[5-9]\d{2})[/_\-\.]?([01]\d)[/_\-\.]?([1-9](?:\]\])?\s*(?:\||}}))"
        ),
        "$1$2-$3-0$4",
    ),
    (
        _R(
            _CitDate
            + r")((?:\[\[)?20\d\d|1[5-9]\d{2})[/_\-\.]?([1-9])[/_\-\.]?([0-3]\d(?:\]\])?\s*(?:\||}}))"
        ),
        "$1$2-0$3-$4",
    ),
    (
        _R(
            _CitDate
            + r")((?:\[\[)?20\d\d|1[5-9]\d{2})([01]\d)[/_\-\.]([0-3]\d(?:\]\])?\s*(?:\||}}))"
        ),
        "$1$2-$3-$4",
    ),
    (
        _R(
            _CitDate
            + r")((?:\[\[)?20\d\d|1[5-9]\d{2})[/_\-\.](0[1-9]|1[0-2])0?([0-3]\d(?:\]\])?\s*(?:\||}}))"
        ),
        "$1$2-$3-$4",
    ),
)

_CiteTemplateAbbreviatedMonthISO = _R(
    r"(?si)(\|\s*(?:archive|air|access)?date2?\s*=\s*)(\d{4}[-/\s][A-Z][a-z]+\.?[-/\s][0-3]?\d)(\s*(?:\||}}))",
    O.COMPILED | O.IGNORE_CASE,
)

_CiteTemplateDateYYYYDDMMFormat = _R(
    _SiCitStart
    + r"(?:archive|air|access)?date2?\s*=\s*(?:\[\[)?20\d\d)-([23]\d|1[3-9])-(0[1-9]|1[0-2])(\]\])?"
)

_CiteTemplateTimeInDateParameter = _R(
    r"(\|\s*(?:archive|air|access)?date2?\s*=\s*(?:(?:20\d\d|19[7-9]\d)-[01]?\d-[0-3]?\d|[0-3]?\d[a-z]{0,2}\s*\w+,?\s*(?:20\d\d|19[7-9]\d)|\w+\s*[0-3]?\d[a-z]{0,2},?\s*(?:20\d\d|19[7-9]\d)))(\s*[,-:]?\s+[0-2]?\d[:\.]?[0-5]\d(?:\:?[0-5]\d)?\s*(?:[^\|\}]*\[\[[^[\]\n]+(?<!\[\[[A-Z]?[a-z-]{2,}:[^[\]\n]+)\]\][^\|\}]*|[^\|\}]*)?)(?<!.*(?:20|1[7-9])\d+\s*)",
    O.IGNORE_CASE | O.SINGLELINE,
)

_WhitespaceEnd = _R(r"(\s+)$")

_CitePodcast = nested_template_regex(r"cite podcast")

_PossibleAmbiguousCiteDate = _R(
    r"(?<=\|\s*(?:access|archive|air)?\-?date2?\s*=\s*)(0?[1-9]|1[0-2])[/_\-\.](0?[1-9]|1[0-2])[/_\-\.](20\d\d|19[7-9]\d|[01]\d)\b"
)

_PossibleAmbiguousCiteDateQuick = _R(
    r"(\|\s*(?:access|archive|air)?\-?date2?\s*=\s*)(0?[1-9]|1[0-2])[/_\-\.](0?[1-9]|1[0-2])[/_\-\.](20\d\d|19[7-9]\d|[01]\d)\b"
)

_CiteArXiv = nested_template_regex((r"cite arxiv", r"cite arXiv"))

_CitationPopulatedParameter = _R(r"\|\s*([\w_\d- ']+)\s*=\s*([^\|}]+)")

_citeWebParameters = _R(
    r"^(access-?date|agency|archive-?date|archive\-format|archive-?url|arxiv|ARXIV|asin|ASIN|asin-tld|ASIN-TLD|at|[Aa]uthor\d*|author\d*-first|author-?format|author\d*-(last|given|surname)|author-?link\d*|author\d*-?link|authors|author-mask|author-name-separator|author-separator|bibcode|BIBCODE|citeseerx|collaboration|date|dead-?url|department|df|dictionary|display-?(authors|subjects)|display-?editors|doi|DOI|DoiBroken|doi-broken|doi-broken-date|doi_brokendate|doi-inactive-date|doi_inactivedate|edition|[Ee]ditor|editor\d*|editor\d*-first|editor-?format|EditorGiven\d*|editor\d*-given|editor\d*-last|editor\d*-?link|editor-?mask|editor-name-separator|EditorSurname\d*|editor\d*-surname|editor-first\d*|editor-given\d*|editor-last\d*|editor-surname\d*|editorlink\d*|v?editors|eissn|[Ee]mbargo|encyclopa?edia|first\d*|format|given\d*|hdl|host|id|ID|ignoreisbnerror|ignore-isbn-error|institution|interviewer(\-(given|surname))?|i?sbn|ISBN|isbn13|ISBN13|issn|ISSN|issue|jfm|JFM|journal|jstor|JSTOR|language|last\d*|lastauthoramp|last-author-amp|lay-?(summary|url)|lccn|LCCN|location|magazine|medium|minutes|mode|mr|MR|name\-list\-style|newspaper|no-?pp|number|oclc|OCLC|ol|OL|orig-?(year|date)|others|osti|pp?|pages?|people|periodical|place|pmc|PMC|pmid|PMID|postscript|publication-?(?:place|date)|publisher|quotation|quote(\-pages?)?|[Rr]ef|registration|rfc|RFC|script\-title|script\-(website|work|quote)|separator|series|series-?link|ssrn|SSRN|subject(\-mask)?|subscription|surname\d*|s2cid(\-access)?|time|title(\-link)?|trans\-(quote|website|work)|trans[_-]title|translator\-(last\d*|surname)|translator(\-link\d*|\d+)?|translator\-(first\d*|given)|type|url|URL|vauthors|version|via|volume|website|work|year|zbl|ZBL)\b",
    O.COMPILED,
)

_citeArXivParameters = _R(
    r"\b(arxiv|asin|ASIN|author\d*|authorlink\d*|author\d*-link|bibcode|class|coauthors?|collaboration|date|day|display\-authors|doi|DOI|doi brokendate|doi inactivedate|eprint|first\d*|format|given\d*|id|in|isbn|ISBN|issn|ISSN|jfm|JFM|jstor|JSTOR|language|last\d*|laydate|laysource|laysummary|lccn|LCCN|mode|month|mr|MR|oclc|OCLC|ol|OL|osti|OSTI|page|pmc|PMC|pmid|PMID|postscript|publication-date|quote|ref|rfc|RFC|separator|seperator|ssrn|SSRN|surname\d*|title|vauthors|version|year|zbl)\b",
    O.COMPILED,
)

_NoEqualsTwoBars = _R(r"\|[^=\|]+\|")


def _parsers_instance() -> Parsers:
    # imported here: parsers.py imports this module's neighbours, which import this one
    from pyawb.core.parsers.parsers import Parsers

    return Parsers()


# Regex.IsMatch/Replace calls with inline patterns in AWB
_UpperCaseIdentifierParam = _R(
    r"(?:IS[BS]N|DOI|PMID|OCLC|PMC|LCCN|ASIN|ARXIV|ASIN\-TLD|BIBCODE|ID|ISBN13|JFM|JSTOR|MR|OL|OSTI|RFC|SSRN|URL|ZBL)"
)
_PageRangeInP = _R(r"\d+\s*(?:–|&ndash;|, )\s*\d")
_DateWithLeadingZero = _R(r"\b0[1-9]")
_CiteWebBookNews = _R(r"[Cc]ite(?: ?web| book| news)")
_ThousandsComma = _R(r"\b[0-9]{1,2},[0-9]{3}\b")
_ArchiveDate = _R(r"(\d{4})(\d\d)(\d\d)")
_IssnFormat = _R(r"^([0-9]{4}) *[- –]* *([0-9]{3}[0-9X])$")
_IsbnPrefix = _R(r"^(?i)ISBN\s*")
_IntParse = _R(r"^\s*[+-]?[0-9]+\s*$")


def _template_name_part(t: str) -> str:
    # t.Substring(0, t.IndexOfAny("}|".ToCharArray())); template calls always contain "}"
    return t[: min(i for i in (t.find("}"), t.find("|")) if i >= 0)]


def fix_citation_templates(article_text: str) -> str:
    """Formatting fixes to citation templates, {{harv}}/{{sfn}} and {{rp}} (en only).

    AWB: Parsers.FixCitationTemplates.
    """
    from pyawb.core import tools

    if current_site().lang_code != "en":
        return article_text

    all_templates = _templates.get_all_templates(article_text)
    all_templates_detail = _templates.get_all_template_detail(article_text)

    # get name of all cite template calls used in article
    cite_templates_used = [t for t in all_templates if W.CiteTemplate.is_match("{{" + t + "|}}")]

    if cite_templates_used:
        # Performance: filter all template calls down to cite templates on name
        for s in all_templates_detail:
            name = _template_name_part(s).lower()
            if not any(c.lower() in name for c in cite_templates_used):
                continue
            res, original = s, ""
            while res != original:
                original = res
                res = W.CiteTemplate.replace(res, _fix_citation_templates_me)
            if res != s:
                article_text = article_text.replace(s, res)

    if _templates.template_exists(all_templates, W.HarvTemplate):
        article_text = W.HarvTemplate.replace(article_text, _fix_harv_sfn_templates_me)

    if _templates.template_exists(all_templates, W.SfnTemplate):
        article_text = W.SfnTemplate.replace(article_text, _fix_harv_sfn_templates_me)

    # Performance: use TemplateDetail cache to avoid regex search on whole article text
    if _templates.template_exists(all_templates, _rpTemplate):
        # filter down to templates with rp in name
        rp_templates = [t for t in all_templates_detail if "rp" in _template_name_part(t).lower()]

        def rp_me(m: DotNetMatch) -> str:
            # rp can be simple {{rp|1-7}} or {{rp|pp=1-7}} so handle both formats
            params = tools.get_template_parameter_values(m.value)
            if params:
                return _fix_page_ranges(m.value, params)
            pagerange = tools.get_template_argument(m.value, 1)
            if pagerange:
                return m.value.replace(pagerange, _fix_page_ranges_value(pagerange))
            return m.value

        for s in rp_templates:
            res = _rpTemplate.replace(s, rp_me)
            if res != s:
                article_text = article_text.replace(s, res)

    return article_text


def _fix_harv_sfn_templates_me(m: DotNetMatch) -> str:
    from pyawb.core import tools

    new_value = _fix_page_ranges(m.value, tools.get_template_parameter_values(m.value))
    page = tools.get_template_parameter_value(new_value, "p")

    # ignore brackets
    if "(" in page:
        page = page[: page.index("(")]

    if _PageRangeInP.is_match(page) and not tools.get_template_parameter_value(new_value, "pp"):
        new_value = tools.rename_template_parameter(new_value, "p", "pp")

    return new_value


def _fix_citation_templates_me(m: DotNetMatch) -> str:
    """Fixes to one citation template call."""
    from pyawb.core import tools
    from pyawb.core.parsers import fixsyntax as _fixsyntax
    from pyawb.core.parsers.parsers import DateLocale

    new_value = tools.remove_excess_template_pipes(m.value)
    templatename = m.group(2)

    params_found: dict[str, str] = {}
    # remove duplicated fields, ensure the URL is not touched (may have pipes in)
    new_value = tools.remove_duplicate_template_parameters(new_value, params_found)

    # fix cite params not in lower case, allowing for ISBN, DOI identifiers being uppercase,
    # avoiding changing text within malformatted URL
    for p in [
        p
        for p in params_found
        if p.lower() != p
        and not _UpperCaseIdentifierParam.is_match(p)
        and p not in _CiteUrl.match(new_value).value
    ]:
        new_value = tools.rename_template_parameter(new_value, p, p.lower())

    def get(*names: str) -> str:
        for n in names:
            if n in params_found:
                return params_found[n]
        return ""

    the_url = get("url")
    id_ = get("id", "ID")
    format_ = get("format")
    the_year = get("year")
    the_date = get("date")
    lang = get("language")
    the_month = get("month")
    the_work = get("work")
    website = get("website")
    nopp = get("nopp")
    the_issue = get("issue")
    the_volume = get("volume")
    accessdate = get("accessdate", "access-date")
    pages = get("pages")
    page = get("page")
    origyear = get("origyear")
    origdate = get("origdate")
    archiveurl = get("archiveurl", "archive-url")
    contributionurl = get("contribution-url")
    isbn = get("isbn", "ISBN")
    issn = get("issn", "ISSN")

    the_url_original = the_url

    # remove the unneeded 'format=HTML' field, or format= with null value when URL is HTML page
    if "format" in params_found and (
        format_.lstrip("[]").upper().startswith("HTM")
        or (not format_ and the_url.upper().rstrip("L").endswith("HTM"))
    ):
        new_value = tools.remove_template_parameter(new_value, "format")

    if "origdate" in params_found and not origdate:
        new_value = tools.remove_template_parameter(new_value, "origdate")

    # newlines to spaces in all parameters
    for key, value in [(k, v) for k, v in params_found.items() if "\r\n" in v]:
        new_value = tools.update_template_parameter_value(
            new_value, key, value.replace("\r\n", " ")
        )

    # {{sv icon}} -> sv in language=
    if "{{" in lang:
        new_value = _LangTemplate.replace(new_value, "$1$3")
        lang = tools.get_template_parameter_value(new_value, "language")

    # remove italics for work field for book/periodical, but not website -- auto italicised by template
    if "''" in the_work and "." not in the_work:
        new_value = _WorkInItalics.replace(new_value, "$1$2")

    # format quotes in title fields, remove stray quotes
    for dequote_param in _ParametersToDequote:
        if dequote_param not in params_found:
            continue
        quotetitle = params_found[dequote_param]
        before = quotetitle
        # convert curly quotes to straight quotes per [[MOS:PUNCT]]
        quotetitle = W.CurlyDoubleQuotes.replace(quotetitle, '"')
        quotetitle = _BalancedArrows.replace(quotetitle, '"$1"')
        quotetitle = quotetitle.replace("’", "'")  # single curly quote close
        quotetitle = quotetitle.replace("‘", "'")  # single curly quote open

        # trim stray quotes (but don't change title in quotes as this may be a title that is
        # itself a quote); don't change if it contains a hidetext marker
        if '"' not in quotetitle.strip('"') and "⌊⌊⌊⌊" not in quotetitle:
            if quotetitle.startswith('"') and not quotetitle.endswith('"'):
                quotetitle = quotetitle.lstrip('"')
            elif quotetitle.endswith('"') and not quotetitle.startswith('"'):
                quotetitle = quotetitle.rstrip('"')

        if before != quotetitle:
            new_value = tools.set_template_parameter_value(new_value, dequote_param, quotetitle)

    is_cite_journal = templatename.lower() == "cite journal"

    # page= and pages= fields don't need p. or pp. in them when nopp not set
    if ("p" in pages or "p" in page) and not is_cite_journal and not nopp:
        new_value = _CiteTemplatePagesPP.replace(new_value, "")
        pages = tools.get_template_parameter_value(new_value, "pages")
        # AWB removes and re-adds the key; .NET's Dictionary reuses the slot, keeping the order
        params_found["pages"] = pages

    # with Lua no need to rename date to year when date = YYYY, just remove year and date
    # duplicating each other
    if len(the_date) == 4 and the_year == the_date:
        new_value = tools.remove_template_parameter(new_value, "date")

    s = W.for_site(current_site())

    # year = full date --> date = full date
    if len(the_year) > 5:
        the_year_corrected = _fixdates.IncorrectCommaInternationalDates.replace(the_year, "$1 $2")
        the_year_corrected = _fixdates.IncorrectCommaAmericanDates.replace(
            the_year_corrected, "$1 $2, $3"
        )

        if the_year_corrected != the_year:
            new_value = tools.update_template_parameter_value(new_value, "year", the_year_corrected)
            the_year = the_year_corrected

        if (
            W.ISODates.is_match(the_year)
            or s.InternationalDates.is_match(the_year)
            or s.AmericanDates.is_match(the_year)
        ):
            the_date = the_year
            the_year = ""
            new_value = tools.rename_template_parameter(new_value, "year", "date")

    # year=YYYY and date=...YYYY -> remove year; not for year=YYYYa
    elif len(the_year) == 4 and the_year in the_date and YearOnly.is_match(the_year):
        the_date = _parsers_instance().fix_dates_a_internal(the_date)

        if (
            s.InternationalDates.is_match(the_date)
            or s.AmericanDates.is_match(the_date)
            or W.ISODates.is_match(the_date)
        ):
            the_year = ""
            new_value = tools.remove_template_parameter(new_value, "year")

    # month=Month and date=...Month... OR month=Month and date=same month (by conversion from ISO
    # format) Or month=nn and date=same month (by conversion to ISO format)
    if (
        (len(the_month) > 2 and the_month in the_date)  # named month within date
        or (
            len(the_month) > 2
            and the_month in tools.convert_date(the_date, DateLocale.INTERNATIONAL)
        )
        or (
            _IntParse.is_match(the_month)
            and _R(r"\-0?" + the_month + r"\-").is_match(
                tools.convert_date(the_date, DateLocale.ISO)
            )
        )
    ):
        new_value = tools.remove_template_parameter(new_value, "month")

    # date = Month DD and year = YYYY --> date = Month DD, YYYY
    if not YearOnly.is_match(the_date) and YearOnly.is_match(the_year):
        if not s.AmericanDates.is_match(the_date) and s.AmericanDates.is_match(
            the_date + ", " + the_year
        ):
            if the_year not in the_date:
                new_value = tools.set_template_parameter_value(
                    new_value, "date", the_date + ", " + the_year
                )
            new_value = tools.remove_template_parameter(new_value, "year")
        elif not s.InternationalDates.is_match(the_date) and s.InternationalDates.is_match(
            the_date + " " + the_year
        ):
            if the_year not in the_date:
                new_value = tools.set_template_parameter_value(
                    new_value, "date", the_date + " " + the_year
                )
            new_value = tools.remove_template_parameter(new_value, "year")

    # correct volume=vol 7... and issue=no. 8 for {{cite journal}} only
    if is_cite_journal:
        if the_volume:
            new_value = _CiteTemplatesJournalVolume.replace(new_value, "")
        if the_issue:
            new_value = _CiteTemplatesJournalIssue.replace(new_value, "")
        else:
            new_value = _CiteTemplatesJournalVolumeAndIssue.replace(new_value, "| issue = ")
    # {{cite web}} for Google books -> {{Cite book}}
    elif "web" in templatename and "http://books.google." in new_value and not the_work:
        new_value = tools.rename_template(new_value, templatename, "Cite book")

    # remove leading zero in day of month
    if any("date" in k and _DateWithLeadingZero.is_match(v) for k, v in params_found.items()):
        new_value = _DateLeadingZero.replace(new_value, "$1$2$3$4$5")
        new_value = _DateLeadingZero.replace(new_value, "$1$2$3$4$5")
        the_date = tools.get_template_parameter_value(new_value, "date")
        accessdate = tools.get_template_parameter_value(new_value, "accessdate")
        if not accessdate:
            accessdate = tools.get_template_parameter_value(new_value, "access-date")

    if any("access" in k and "date" not in k for k in params_found):
        accessyear = params_found.get("accessyear", "")

        if _CiteWebBookNews.is_match(templatename):
            # remove any empty accessdaymonth, accessmonthday, accessmonth and accessyear
            new_value = _AccessDayMonthDay.replace(new_value, "")

            # merge accessdate of 'D Month' or 'Month D' and accessyear of 'YYYY' in cite web
            if len(accessyear) == 4:
                new_value = _AccessDateYear.replace(new_value, " $2$1$3")

        # remove accessyear where accessdate is present and contains said year
        if accessyear and accessyear in accessdate:
            new_value = tools.remove_template_parameter(new_value, "accessyear")

    # fix unspaced comma ranges, avoid pages=12,345 as could be valid page number
    if "," in pages and not _ThousandsComma.is_match(pages):
        while _UnspacedCommaPageRange.is_match(pages):
            pages = _UnspacedCommaPageRange.replace(pages, "$1, $2")
        new_value = tools.update_template_parameter_value(new_value, "pages", pages)
        params_found["pages"] = pages

    # page range should have unspaced en-dash; validate that page is range not section link
    new_value = _fix_page_ranges(new_value, params_found)

    # page range or list should use 'pages' parameter not 'page'
    if page and _CiteTemplatesPageRangeName.is_match(new_value):
        new_value = _CiteTemplatesPageRangeName.replace(new_value, "$1pages$2")
        new_value = tools.remove_duplicate_template_parameters(new_value)

    # remove ordinals from dates
    if _fixdates.Ordinal.is_match(the_date) or _fixdates.Ordinal.is_match(accessdate):
        if _fixdates.OrdinalsInDatesInt.is_match(the_date):
            new_value = tools.update_template_parameter_value(
                new_value, "date", _fixdates.OrdinalsInDatesInt.replace(the_date, "$1$2$3 $4")
            )
        elif _fixdates.OrdinalsInDatesAm.is_match(the_date):
            new_value = tools.update_template_parameter_value(
                new_value, "date", _fixdates.OrdinalsInDatesAm.replace(the_date, "$1 $2$3")
            )

        if _fixdates.OrdinalsInDatesInt.is_match(accessdate):
            fixed = _fixdates.OrdinalsInDatesInt.replace(accessdate, "$1$2$3 $4")
            new_value = tools.update_template_parameter_value(new_value, "accessdate", fixed)
            new_value = tools.update_template_parameter_value(new_value, "access-date", fixed)
        elif _fixdates.OrdinalsInDatesAm.is_match(accessdate):
            fixed = _fixdates.OrdinalsInDatesAm.replace(accessdate, "$1 $2$3")
            new_value = tools.update_template_parameter_value(new_value, "accessdate", fixed)
            new_value = tools.update_template_parameter_value(new_value, "access-date", fixed)

    # catch after any other fixes
    if not _fixdates.IncorrectCommaAmericanDates.is_match(the_url_original):
        new_value = _fixdates.IncorrectCommaAmericanDates.replace(new_value, "$1 $2, $3")

    # URL starting www needs http://
    if the_url.lower().startswith("www"):
        the_url = "http://" + the_url

    # URL http format fix
    if (
        the_url.startswith("http")
        and not the_url.lower().startswith("http://")
        and not the_url.lower().startswith("https://")
    ):
        the_url = _fixsyntax.fix_syntax(" " + the_url).strip()

    if archiveurl.lower().startswith("www"):
        new_value = tools.update_template_parameter_value(
            new_value, "archiveurl", "http://" + archiveurl
        )
        new_value = tools.update_template_parameter_value(
            new_value, "archive-url", "http://" + archiveurl
        )
    if contributionurl.lower().startswith("www"):
        new_value = tools.update_template_parameter_value(
            new_value, "contribution-url", "http://" + contributionurl
        )

    # (part) wikilinked/external linked URL in cite template, don't change when named external
    # link format
    if " " not in the_url:
        the_url = the_url.strip("[").strip("]")

    if the_url_original != the_url:
        new_value = tools.update_template_parameter_value(new_value, "url", the_url)

    # url=...archive to url=original, archive-url=archive
    if _ArchiveOrgURL.is_match(the_url) and not archiveurl:
        new_value = tools.set_template_parameter_value(new_value, "archive-url", the_url)
        new_value = tools.set_template_parameter_value(
            new_value,
            "archive-date",
            _ArchiveDate.replace(_ArchiveOrgURL.match(the_url).group(1), "$1-$2-$3"),
        )
        if website.lower().startswith(("archive", "web.archive")):
            new_value = tools.remove_template_parameter(new_value, "website")
        the_url = _ArchiveOrgURL.replace(the_url, "")
        new_value = tools.update_template_parameter_value(new_value, "url", the_url)

    # {{dead link}} should be placed outside citation, not in format field per [[Template:Dead link]]
    dead_link_match = W.DeadLink.match(format_)
    if dead_link_match:
        dead_link = dead_link_match.value

        if the_url.upper().rstrip("L").endswith("HTM") and format_ == dead_link:
            new_value = tools.remove_template_parameter(new_value, "format")
        else:
            new_value = tools.update_template_parameter_value(
                new_value, "format", format_.replace(dead_link, "")
            )

        new_value += " " + dead_link

    if id_:
        # get id param name, id or ID
        id_param_name = next((k for k in params_found if k in ("ID", "id")), "")

        # id=ISBN fix
        if _IdISBN.is_match(id_) and not isbn:
            new_value = tools.rename_template_parameter(new_value, id_param_name, "isbn")
            new_value = tools.set_template_parameter_value(
                new_value, "isbn", _IdISBN.match(id_).group(1).strip()
            )

        # id=ASIN fix
        if _IdASIN.is_match(id_) and not tools.get_template_parameter_value(
            new_value, "asin", True
        ):
            new_value = tools.rename_template_parameter(new_value, id_param_name, "asin")
            new_value = tools.set_template_parameter_value(
                new_value, "asin", _IdASIN.match(id_).group(1).strip()
            )

        # id=ISSN fix
        id_issn_match = _IdISSN.match(id_)
        if id_issn_match and not issn:
            # 1234-5678 using standard hyphen
            new_issn = id_issn_match.group(1) + "-" + id_issn_match.group(2)
            new_value = tools.rename_template_parameter(new_value, id_param_name, "issn")
            new_value = tools.set_template_parameter_value(new_value, "issn", new_issn)

    # format ISSN: 1234-5678 with hyphen
    if issn:
        new_issn = _IssnFormat.replace(issn, "$1-$2")
        if new_issn != issn:
            issn_param = next((k for k in params_found if k in ("ISSN", "issn")), "")
            new_value = tools.update_template_parameter_value(new_value, issn_param, new_issn)

    if isbn:
        isbn_before = isbn
        # remove ISBN at start, but not if multiple ISBN
        if "isbn" in isbn.lower() and "isbn" not in isbn[4:].lower():
            isbn = _IsbnPrefix.replace(isbn, "")

        # trim unneeded characters
        isbn = isbn.strip(".;,:").strip()

        # fix dashes: only hyphens allowed
        while _ISBNDash.is_match(isbn):
            isbn = _ISBNDash.replace(isbn, "$1-$2")
        isbn = isbn.replace("‐", "-")
        isbn = isbn.replace("‒", "-")

        if isbn != isbn_before:
            if "ISBN" in params_found:
                new_value = tools.update_template_parameter_value(new_value, "ISBN", isbn)
            else:
                new_value = tools.update_template_parameter_value(new_value, "isbn", isbn)

    # origyear --> year when no year/date
    if len(origyear) == 4 and not the_year and not the_date:
        new_value = tools.rename_template_parameter(new_value, "origyear", "year")
        new_value = tools.remove_duplicate_template_parameters(new_value)

    return new_value


def _fix_page_ranges(template_call: str, params: dict[str, str]) -> str:
    """Hyphens to en dashes in page ranges in citation template fields; not where the value has
    hidden text (e.g. a wiki comment) or wiki/external links."""
    from pyawb.core import tools

    for key, value in list(params.items()):
        if key in _PageFields and value and not _HiddenRegex.is_match(value) and "[" not in value:
            res = _fix_page_ranges_value(value)
            if res != value:
                template_call = tools.update_template_parameter_value(template_call, key, res)
    return template_call


def _fix_page_ranges_value(page_range: str) -> str:
    original = page_range
    # fix spaced page ranges e.g. 15 – 20 --> 15–20
    if _SpacedPageRange.is_match(page_range):
        return _SpacedPageRange.replace(page_range, "$1$2$3")

    if len(page_range) > 2 and " to " not in page_range:
        pagerangesokay = False
        page_ranges: dict[int, int] = {}

        for pagerange in _PageRange.matches(page_range):
            page1 = pagerange.group(1)
            page2 = pagerange.group(2)

            # convert 350-2 into 350-352 etc.
            if len(page1) > len(page2):
                page2 = page1[: len(page1) - len(page2)] + page2

            p1, p2 = int(page1), int(page2)
            # check a valid range with difference < 999
            pagerangesokay = p1 < p2 and p2 - p1 < 999

            # check range doesn't overlap with another range found
            if any(k <= p1 <= v or k <= p2 <= v for k, v in page_ranges.items()):
                pagerangesokay = False

            if not pagerangesokay:
                break

            # add to dictionary of ranges found (Dictionary.Add throws on a duplicate key,
            # which the overlap check above rules out)
            page_ranges[p1] = p2

        if pagerangesokay:
            return _PageRange.replace(page_range, "$1–$2")

    return original


def citation_publisher_to_work(citation: str) -> str:
    """{{cite web}}/{{cite news}} with publisher= but no work= or alias: rename publisher to work."""
    from pyawb.core import tools

    # only for {{cite web}} or {{cite news}}
    if not _CiteWebOrNews.is_match(citation):
        return citation

    publisher = tools.get_template_parameter_value(citation, "publisher")

    # nothing to do if no publisher, or publisher is a press publisher
    if not publisher or _PressPublishers.is_match(publisher):
        return citation

    workandaliases = tools.get_template_parameters_values(citation, _WorkParameterAndAliases)

    if not "".join(workandaliases):
        citation = tools.rename_template_parameter(citation, "publisher", "work")
        citation = _WorkInItalics.replace(citation, "$1$2")

    return citation


def cite_template_dates_no_change(article_text: str) -> tuple[str, bool]:
    """AWB's instance overload CiteTemplateDates(articleText, out noChange)."""
    new_text = cite_template_dates(article_text)
    return new_text, new_text == article_text


def cite_template_dates(article_text: str) -> str:
    """Correct common formatting errors in dates in citation templates (doesn't link/delink
    dates). Ambiguous dates such as 3-2-2009 are not changed."""
    # cite podcast is non-compliant to citation core standards
    if not current_site().is_wikipedia_en or _templates.template_exists(
        _templates.get_all_templates(article_text), _CitePodcast
    ):
        return article_text

    original_article_text = article_text

    # loop in case a single citation has multiple dates to be fixed
    for s in _templates.get_all_template_detail(article_text):
        res, original = s, ""
        while res != original:
            original = res
            res = W.CiteTemplate.replace(res, _cite_template_me)
        if res != s:
            article_text = article_text.replace(s, res)

    # don't apply fixes when ambiguous dates present; for performance only check if changes made
    if original_article_text != article_text and ambiguous_cite_template_dates(
        original_article_text
    ):
        return original_article_text

    return article_text


def _cite_template_me(m: DotNetMatch) -> str:
    """Invalid date formats (DD-MM-YYYY, MM-DD-YYYY, YYYY-D-M, YYYY-DD-MM, YYYY_MM_DD etc.) to
    ISO YYYY-MM-DD; times removed from date fields."""
    from pyawb.core import tools
    from pyawb.core.parsers.parsers import DateLocale

    new_value = m.value
    params_found = tools.get_template_parameter_values(new_value)

    def get(*names: str) -> str:
        for n in names:
            if n in params_found:
                return params_found[n]
        return ""

    dates = [
        get("accessdate", "access-date"),
        get("archivedate"),
        get("date"),
        get("date2"),
        get("airdate"),
    ]
    journal = get("journal")

    if _cite_template_me_parameter_to_process(dates):
        # accessdate=, archivedate=
        for regex, replacement in _CiteTemplateIncorrectISOAccessdates:
            new_value = regex.replace(new_value, replacement)

        # date=, archivedate=, airdate=, date2=
        for regex, replacement in _CiteTemplateIncorrectISODates:
            new_value = regex.replace(new_value, replacement)

        new_value = _CiteTemplateDateYYYYDDMMFormat.replace(
            new_value, "$1-$3-$2$4"
        )  # YYYY-DD-MM to YYYY-MM-DD

        # date = YYYY-Month-DD fix, not for cite journal PubMed date format
        if not journal:
            new_value = _CiteTemplateAbbreviatedMonthISO.replace(
                new_value,
                lambda m2: (
                    m2.group(1)
                    + tools.convert_date(m2.group(2).replace(".", ""), DateLocale.ISO)
                    + m2.group(3)
                ),
            )

    # all citation dates: Remove time from date fields
    def time_me(m3: DotNetMatch) -> str:
        # keep end whitespace outside comment
        comm, whitespace = m3.group(2), ""
        whm = _WhitespaceEnd.match(comm)
        if whm:
            comm = comm.rstrip()
            whitespace = whm.group(1)
        return m3.group(1) + "<!--" + comm + "-->" + whitespace

    return _CiteTemplateTimeInDateParameter.replace(new_value, time_me)


def _cite_template_me_parameter_to_process(parameters: list[str]) -> bool:
    months = W.for_site(current_site()).MonthsNoGroup
    return any(
        len(s) > 4 and not W.ISODates.is_match(s) and not _R(r"^(\d{1,2} *)?" + months).is_match(s)
        for s in parameters
    )


def ambiguous_cite_template_dates(article_text: str) -> bool:
    """Whether the text has ambiguous cite template dates in XX-XX-YYYY or XX-XX-YY format."""
    return bool(ambig_cite_template_dates(article_text))


def ambig_cite_template_dates(article_text: str) -> dict[int, int]:
    """Ambiguous cite template dates in XX-XX-YYYY or XX-XX-YY format: {index: length}."""
    ambig_dates: dict[int, int] = {}

    # check for performance
    if _PossibleAmbiguousCiteDateQuick.is_match(
        "".join(t for t in _templates.get_all_template_detail(article_text) if "date" in t)
    ):
        for m in W.CiteTemplate.matches(article_text):
            for m2 in _PossibleAmbiguousCiteDate.matches(m.value):
                # for YYYY-AA-BB date, ambiguous if AA and BB not the same
                if m2.group(1) != m2.group(2):
                    ambig_dates[m.index + m2.index] = m2.length

    return ambig_dates


def bad_cite_parameters(article_text: str) -> dict[int, int]:
    """Unknown or invalid parameters in citation templates: {index: length}."""
    from pyawb.core import tools

    found: dict[int, int] = {}

    def unknown_parameters(m: DotNetMatch, known: DotNetRegex) -> None:
        # ignore parameters in templates within cite
        cite = "{{" + tools.replace_with_spaces(m.value[2:], W.NestedTemplates.matches(m.value[2:]))
        for m2 in _CitationPopulatedParameter.matches(cite):
            if not known.is_match(m2.group(1)) and tools.get_template_parameter_value(
                cite, m2.group(1)
            ):
                found[m.index + m2.start(1)] = len(m2.group(1))

    # unknown parameters in cite arXiv, TemplateExists check for performance
    if _templates.template_exists(_templates.get_all_templates(article_text), _CiteArXiv):
        for m in _CiteArXiv.matches(article_text):
            unknown_parameters(m, _citeArXivParameters)

    for m in W.CiteTemplate.matches(article_text):
        # unknown parameters in cite web
        if m.group(2).endswith("web"):
            unknown_parameters(m, _citeWebParameters)

        pipecleaned = tools.pipe_cleaned_template(m.value, False)

        # no equals between two separator pipes
        if "=" in pipecleaned:
            m2 = _NoEqualsTwoBars.match(pipecleaned)
            if m2:
                found[m.index + m2.index] = m2.length

        # URL has space in it
        urlpos = m.value.find("url")
        if urlpos > 0:
            url = tools.get_template_parameter_value(m.value, "url")
            if (
                " " in url
                and " " in W.UnformattedText.replace(W.NestedTemplates.replace(url, ""), "").strip()
            ):
                # value of url may be in another earlier parameter, report correct position
                from_url = m.value[urlpos:]
                found[m.index + urlpos + from_url.find(url)] = len(url)

    return found
