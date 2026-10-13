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
# Ported from AutoWikiBrowser WikiFunctions/Parse/Parsers.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Port of Parse/Parsers.cs: general fixes and checks, and the Parsers class.

AWB's Parsers is one partial class over many files; here each file is a module of
pyawb.core.parsers and pyawb.core.genfixes gathers them. Static methods are module functions;
the instance methods (which hold a HideText and settings) are on Parsers. Overloads with an
"out bool noChange" return (text, no_change) from a *_no_change variant, or are dropped where the
plain version suffices.
"""

# ruff: noqa: E501

from __future__ import annotations

import datetime
import enum
import unicodedata
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pyawb.core import namespace, rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import (
    boldtitle as _boldtitle,
)
from pyawb.core.parsers import (
    categorydefaultsort as _cds,
)
from pyawb.core.parsers import (
    fixdates as _fixdates,
)
from pyawb.core.parsers import (
    fixheadings as _fixheadings,
)
from pyawb.core.parsers import (
    fixsyntax as _fixsyntax,
)
from pyawb.core.parsers import (
    multipleissues as _mi,
)
from pyawb.core.parsers import (
    references as _refs,
)
from pyawb.core.parsers import (
    sortmetadata as _sortmeta,
)
from pyawb.core.parsers import (
    tagger as _tagger,
)
from pyawb.core.parsers import templates as _templates
from pyawb.core.parsers import wikilinks as _wikilinks
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import Namespace, SiteConfig, current_site
from pyawb.core.textutil import (
    first_letter_case_insensitive,
    html_decode,
    nested_template_regex,
    remove_hash_from_page_title,
    turn_first_to_lower,
    turn_first_to_upper,
    url_decode,
    wiki_decode,
)

if TYPE_CHECKING:
    from pyawb.core.parsers.metadatasorter import InterWikiOrderEnum, MetaDataSorter

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741


class DateLocale(enum.Enum):
    INTERNATIONAL = "International"
    AMERICAN = "American"
    ISO = "ISO"
    UNDETERMINED = "Undetermined"


# -- static regexes (generated from Parsers.cs by tools/porting/cs2py.py, then edited) -----------

_PageRangeIncorrectMdash = _R(
    r"(pages\s*=\s*|pp\.?\s*)((?:&nbsp;)?\d+\s*)(?:\-\-?|—|&mdash;|&#8212;)(\s*\d+)", O.IGNORE_CASE
)

# avoid dimensions in format 55-66-77
_UnitTimeRangeIncorrectMdash = _R(
    r"(?<!-)(\b[1-9]?\d+\s*)(?:-|—|&mdash;|&#8212;)(\s*[1-9]?\d+)(\s+|&nbsp;)((?:years|months|weeks|days|hours|minutes|seconds|[km]g|kb|[ckm]?m|[Gk]?Hz|miles|mi\.|%|feet|foot|ft|met(?:er|re)s)\b|in\))"
)

_DollarAmountIncorrectMdash = _R(
    r"(\$[1-9]?\d{1,3}\s*)(?:-|—|&mdash;|&#8212;)(\s*\$?[1-9]?\d{1,3})"
)

_AMPMIncorrectMdash = _R(
    r"([01]?\d:[0-5]\d\s*([AP]M)\s*)(?:-|—|&mdash;|&#8212;)(\s*[01]?\d:[0-5]\d\s*([AP]M))",
    O.IGNORE_CASE,
)

_AgeIncorrectMdash = _R(r"([Aa]ge[sd])\s([1-9]?\d\s*)(?:-|—|&mdash;|&#8212;)(\s*[1-9]?\d)")

_SentenceClauseIncorrectMdash = _R(r"(?!xn--)(\w{2}|⌊⌊⌊⌊M\d+⌋⌋⌋⌋)\s*--\s*(\w)")

_SuperscriptMinus = _R(r"(<sup>)(?:-|–|—)(?=\d+</sup>)")

# Matches the {{birth date}} family of templates
_BirthDate = nested_template_regex(
    (
        r"birth date",
        r"birth-date",
        r"dob",
        r"bda",
        r"birth date and age",
        r"birthdate and age",
        r"Date of birth and age",
        r"BDA",
        r"Birthdateandage",
        r"Birth Date and age",
        r"birthdate",
    )
)

# Matches the {{death date}} family of templates
_DeathDate = nested_template_regex(
    (r"death date", r"death-date", r"dda", r"death date and age", r"deathdateandage", r"deathdate")
)

_BrTwoNewlines = _R("(?:<br */?> *)\r\n\r\n", O.IGNORE_CASE)

_FourOrMoreNewlines = _R("(\r\n){4,}")

_NewlinesBelowExternalLinks = _R(r"==External links==[\r\n\s]*\*")

_HorizontalRule = _R(r"----+$")

_MultipleTabs = _R(r"  +", O.COMPILED)

_SpacesThenTwoNewline = _R(r"[ \u00a0]+\r\n\r\n", O.COMPILED)

_WikiListWithMultipleSpaces = _R(r"^([\*#]+) +", O.COMPILED | O.MULTILINE)

_SpacedDashes = _R(r" (—|&#15[01];|&mdash;|&#821[12];|&#x201[34];) ", O.COMPILED)

_NewlinesWithinLists = _R(r"(\r\n\*.*)\r\n[\t ]*\r\n\*", O.COMPILED)

_TwoLists = _R(r"\r\n\*.*\r\n\r\n\r\n\*")

_DateFields = (r"date", r"accessdate", r"access-date", r"archivedate", r"airdate")

_RegexMainArticle = _R(
    r"^:?'{0,5}Main article:\s?'{0,5}\[\[([^\|\[\]]*?)(\|([^\[\]]*?))?\]\]\.?'{0,5}\.?\s*?(?=($|[\r\n]))",
    O.IGNORE_CASE | O.MULTILINE,
)

_SeeAlsoLink = _R(
    r"^:?'{0,5}See also:\s?'{0,5}\[\[([^\|\[\]]*?)(\|([^\[\]]*?))?\]\]\.?'{0,5}\.?\s*?(?=($|[\r\n]))",
    O.IGNORE_CASE | O.MULTILINE,
)

_SeeAlsoMainArticleQuick = _R(r"\s*[:']*(See also|Main article):", O.IGNORE_CASE)

_TemplateArg = _R(r"\|([^=\|}}]+)(?:\||}})")

_ExternalLinksSection = _R(
    r"=\s*(?:external)?\s*links\s*=", O.COMPILED | O.IGNORE_CASE | O.RIGHT_TO_LEFT
)

_NewlinesBeforeHTTP = _R("(\r\n|\n)?(\r\n|\n)(\\[?http)", O.COMPILED)

_HeadingQuick = _R(r"^=+[^=\r\n]+=", O.MULTILINE)

_WordWhitespaceEndofline = _R(r"(\w+)\s+$", O.COMPILED)

_TripleBraceNumIfExist = _R(r"({{{\d}}}|{{#ifexist)", O.COMPILED)

_Temperature = _R(r"(?:&deg;|&ordm;|º|°)(?:&nbsp;)?\s*([CcFf])(?![A-Za-z])", O.COMPILED)

_LineSeparatorZeroWidthSpaceStartOfLine = _R(r"^(\u2028|\u200B)+", O.MULTILINE)

_NDash = _R(r"&#150;|&#8211;|&#x2013;", O.COMPILED)

_MDash = _R(r"&#151;|&#8212;|&#x2014;", O.COMPILED)

_MathTagStart = _R(r"<[Mm]ath|[Cc]hem>", O.COMPILED)

_InUniverse = nested_template_regex(r"In-universe")

_CategoryCharacters = _R(r"\[\[Category:[^\[\]]*?[Cc]haracters", O.COMPILED)

_SeeAlsoOrMain = nested_template_regex((r"See also", r"Seealso", r"Main"))

_RefImproveBLP = nested_template_regex(r"RefimproveBLP")

_IMA = nested_template_regex((r"Infobox musical artist", r"Infobox singer"))

BLPUnsourced = nested_template_regex((r"BLP unsourced", r"BLP unreferenced"))

_BLPUnsourcedSection = nested_template_regex(
    (r"BLP unsourced section", r"BLP sources section", r"BLP unreferenced section")
)

_NotPersonArticles = _R(
    r"(^(((?:First )?(?:Premiership|Presidency|Governor|Mayoralty)|Murder|Atlanta murders|Disappearance|Suicide|Adoption) of|Deaths|The |Second |Brothers |Attack on|[12]\d{3}\b|\d{2,} )|Assembly of|(Birth|Death) rates|(discography|(?:film|bibli)ography| deaths| rebellion| haunting| native| children| campaign(?:, \d+)?| groups| (?:families|boom|case|syndrome|family|murders|people|sisters|brothers|quartet|team|twins|martyrs|mystery|center|\((?:artists|publisher|\w* ?(team|family))\)))(?: \(|$)|[^\(]*\w+,? (and|&|from) \w+|.* (in |Service))",
    O.IGNORE_CASE,
)

_NobleFamilies = _R(r"\[\[Category:[^\[\]\|]*(([nN]oble|[Rr]oyal) families| families(\||\]\]))")

_NotAboutAPersonCategories = _R(
    r"\[\[Category:(\d{4} (establishments|animal|introductions)|.*(?:Animation|Business|Comedy|Criminal|Entertainer|Filmmaking|Tribes|Screenwriting|Sibling|Sibling musical|Sports|Writing) (duos|trios)|Articles about multiple people|Positions |Groups |Married couples|Fictional|Presidencies|Companies|Military careers|Parables of|[^\[\]\|\r\n]*(?:[Mm]usic(?:al)? groups| bands| gods| groups| troupes| nicknames| given names| pageants| teams and stables| magazines| titles| populated places)|Internet memes|[^\[\]\|\r\n]*Diaspora|Performing groups|Military animals|Collective pseudonyms|Sibling filmmakers|Surnames|Baronies)",
    O.IGNORE_CASE,
)

_NotPersonInfoboxes = nested_template_regex(
    (
        r"Infobox cricketer tour biography",
        r"Infobox political party",
        r"Infobox settlement",
        r"italic title",
        r"Infobox animal",
        r"Infobox racehorse",
        r"Infobox named horse",
    )
)

_ThreeOrMoreDigits = _R(r"[0-9]{3,}", O.COMPILED)

_BirthsSortKey = _R(r"\|.*?\]\]", O.COMPILED)

UncertainWordings = _R(
    r"(?:\b(about|abt|approx\.?|before|\?\?\?|by|or \d+|later|after|near|either|probably|missing|prior to|around|late|[Cc]irca|between|be?tw\.?|[Bb]irth based on age as of date|\d{3,4}(?:\]\])?/(?:\[\[)?\d{1,4}|or +(?:\[\[)?\d{3,})\b|\d{3} *\?|\bca?(?:'')?\.|\b[Cc]a?\b|\b(bef|abt|est)\.|~|/|''fl''\.?)",
    O.IGNORE_CASE,
)

ReignedRuledUnsure = _R(
    r"(?:\?|[Rr](?:uled|eign(?:ed)?\b)|\br\.|(chr|fl(?:\]\])?)\.|\b(?:[Ff]lo(?:urished|ruit)|active|baptized)\b)"
)

_AgeBrackets = _R(
    r"(?:< *[Bb][Rr] */? *> *)?\s*[,;]?\s*\(? *[Aa]ged? +\d{1,3}(?: +or +\d{1,3})? *\)?$",
    O.COMPILED,
)

_NoFootnotes = nested_template_regex(r"no footnotes")

_ConversionsCnCommons = nested_template_regex(
    (r"citation needed", r"commons", r"commons cat", r"commons category")
)


_CommonsCategory = _R(r"\{\{\s*[Cc]ommons\s?\|\s*[Cc]ategory:\s*([^{}]+?)\s*\}\}")

_SectionTemplates = nested_template_regex(
    (
        r"unreferenced",
        r"refimprove",
        r"BLP sources",
        r"expand",
        r"BLP unsourced",
        r"BLP unreferenced",
        r"More citations needed",
    )
)

_BotsAllow = _R(r"{{\s*(?:[Nn]obots|[Bb]ots)\s*\|\s*allow\s*=(.*?)}}", O.SINGLELINE | O.COMPILED)

_ExtToIn = _R(
    r'(?<![*#:;]{2})\[https?://([a-z0-9\-]{2})\.(?:(wikt)ionary|wiki(n)ews|wiki(b)ooks|wiki(q)uote|wiki(s)ource|wiki(v)ersity|(w)ikipedia)\.(?:com|net|org)/w(?:iki)?/([^][{|}\s"]*) +([^\n\]]+)\]',
    O.COMPILED,
)

_MetaCommonsIncubatorQualityExternalLink = _R(
    r'(?<![*#:;]{2})\[https?://(?:(m)eta|(commons)|(incubator)|(quality))\.wikimedia\.(?:com|net|org)/w(?:iki)?/([^][{|}\s"]*) +([^\n\]]+)\]',
    O.COMPILED,
)

_WikiaExternalLink = _R(
    r'(?<![*#:;]{2})\[http://([a-z0-9\-]+)\.wikia\.(?:com|net|org)/wiki/([^][{|}\s"]+) +([^\n\]]+)\]',
    O.COMPILED,
)

_coinsR = _R(r'"coins": "([^"]+)')

_coinsParam = _R(r"[&;]rft\.([a-z0-9]+)=([^&]+)")

_SicTypo = nested_template_regex((r"Sic", r"Typo"))

_SicTag = _R(r"[\(\[{]\s*[Ss]ic!?\s*[\)\]}]")

_GRTemplateDecimal = _R(r"{{GR\|\d}}", O.COMPILED)

_ReflistQuick = _R(r"\{\{\s*(?:ref(?:-?li(?:st|nk)|erence)|[Ll]istaref)", O.IGNORE_CASE)
_CategoryLivingPeople = r"[[Category:Living people"

# Regexes AWB builds with WikiRegexes.MonthsNoGroup at static initialisation (English).
_MONTHS = W.for_site(SiteConfig.english()).MonthsNoGroup
_BoldToBracket = _R(r"('''(?:[^']+|.*?[^'])'''\s*\()(.*)")
_DiedDateRegex = _R(
    r"^d\.\s*(\[*(?:"
    + _MONTHS
    + r"\s+0?([1-3]?\d)|0?([1-3]?\d)\s*"
    + _MONTHS
    + r")?\]*,?\s*\[*[12]?\d{3}\]*[\),])",
    O.IGNORE_CASE,
)
_DOBRegex = _R(
    r"^(?:b\.|[Bb]orn(?::+| +on)?)\s*(\[*(?:"
    + _MONTHS
    + r"\s+0?([1-3]?\d)|0?([1-3]?\d)\s*"
    + _MONTHS
    + r")?[\]\s,]*\[*[12]?\d{3}\]*(?:[\),]| +in +))",
    O.IGNORE_CASE,
)
_DOBRegexDash = _R(
    r"(?<![\*#].*)('''(?:[^']+|.*?[^'])'''\s*\()(\[*(?:"
    + _MONTHS
    + r"\s+0?([1-3]?\d)|0?([1-3]?\d)\s*"
    + _MONTHS
    + r")?\]*\s*\[*[12]?\d{3}\]*)\s*(?:\-|–|&ndash;)\s*\)",
    O.IGNORE_CASE,
)
_DOBRegexDashQuick = _R(r"(?<=(?:\-|–|&ndash;)\s*)\)")
_BornDeathRegex = _R(
    r"^(?:[Bb]orn|b\.)\s*(\[*(?:"
    + _MONTHS
    + r"\s+0?(?:[1-3]?\d)|0?(?:[1-3]?\d)\s*"
    + _MONTHS
    + r")?\]*,?\s*\[*[12]?\d{3}\]*)\s*(.|&.dash;)\s*(?:[Dd]ied|d\.)\s+(\[*(?:"
    + _MONTHS
    + r"\s+0?(?:[1-3]?\d)|0?(?:[1-3]?\d)\s*"
    + _MONTHS
    + r")\]*,?\s*\[*[12]?\d{3}\]*\)\s*)",
    O.IGNORE_CASE,
)

# Filled in AWB's static constructor; order matters.
_RegexUnicode: tuple[tuple[DotNetRegex, str], ...] = (
    # look bad if changed
    (
        _R(
            "&(apos|ndash|mdash|minus|times|lt|gt|nbsp|thinsp|zwnj|shy|lrm|rlm|[Pp]rime|ensp|emsp|#x2011|#820[13]|#8239);"
        ),
        "&amp;$1;",
    ),
    # IE6 does like these
    (_R("&#(705|803|596|620|699|700|8652|9408|9848|12288|160|61|x27|39);"), "&amp;#$1;"),
    # Decoder doesn't like these
    (_R("&#(x109[0-9A-Z]{2});"), "&amp;#$1;"),
    (_R("&#((?:277|119|84|x1D|x100)[A-Z0-9a-z]{2,3});"), "&amp;#$1;"),
    (_R("&#(x12[A-Za-z0-9]{3}|65536|769);"), "&amp;#$1;"),
    # can't change 5-digit hex strings, broken by HttpUtility.HtmlDecode
    (_R("&#(x[A-Fa-f0-9]{5});"), "&amp;#$1;"),
    # interfere with wiki syntax
    (_R("&#(0?13|126|x5[BD]|x7[bcd]|0?9[13]|0?12[345]|0?0?3[92]);", O.IGNORE_CASE), "&amp;#$1;"),
    # badmd5 error from the API on save (WebRequest::normalizeUnicode)
    (_R("&#(x232[A9]);"), "&amp;#$1;"),
    # .NET did not like the Unicode versions of these
    (_R("&#(x2[0-9AB][0-9A-Fa-f]{3});"), "&amp;#$1;"),
)
_RegexConversion: tuple[tuple[DotNetRegex, str], ...] = (
    (_R(r"({{[Cc]ommons cat(?:egory)?\|\s*)([^{}\|]+?)\s*\|\s*\2\s*}}"), r"$1$2}}"),
    (
        _R(
            r"({{\s*[Cc]itation needed\s*\|)\s*(?:[Dd]ate:)?([A-Z][a-z]+ 20\d\d)\s*\|\s*(date\s*=\s*\2\s*}})",
            O.IGNORE_CASE,
        ),
        r"$1$3",
    ),
)

StubMaxWordCount = 500


# -- born/died dates ------------------------------------------------------------------------------

_BoldBracketQuick = _R(r"'''\s*\([BbDd]")


def fix_living_things_related_dates(article_text: str) -> str:
    """'''Foo''' (b. 1950) -> (born 1950); (d. ...) -> (died ...); (born X died Y) -> (X – Y)."""
    # the three born/died regexes wrapped like this for performance
    if _BoldBracketQuick.is_match(article_text):

        def me(m: DotNetMatch) -> str:
            new_value = m.group(2)
            new_value = _DiedDateRegex.replace(new_value, "died $1")  # date of death
            new_value = _DOBRegex.replace(new_value, "born $1")  # date of birth
            new_value = _BornDeathRegex.replace(new_value, "$1 – $3")  # birth and death
            return m.group(1) + new_value

        article_text = _BoldToBracket.replace(article_text, me)

    if _DOBRegexDashQuick.is_match(article_text) and not _DOBRegexDash.is_match(
        W.InfoBox.match(article_text).value
    ):
        article_text = _DOBRegexDash.replace(article_text, "$1born $2)")  # date of birth - dash
    return article_text


# -- position checks ------------------------------------------------------------------------------


def _dictionary_of_matches(article_text: str, r: DotNetRegex) -> dict[int, int]:
    from pyawb.core import tools

    article_text = tools.replace_with_spaces(article_text, W.Comments)
    return {m.index: m.length for m in r.matches(article_text)}


def dead_links(article_text: str) -> dict[int, int]:
    """Index -> length of each {{dead link}}."""
    if not _templates.template_exists(_templates.get_all_templates(article_text), W.DeadLink):
        return {}
    return _dictionary_of_matches(article_text, W.DeadLink)


def target_less_links(article_text: str) -> dict[int, int]:
    return _dictionary_of_matches(article_text, W.TargetLessLink)


def double_pipe_links(article_text: str) -> dict[int, int]:
    # performance: only if some link has two pipes
    if any(lnk.count("|") > 1 for lnk in _wikilinks.get_all_wiki_links(article_text)):
        return _dictionary_of_matches(article_text, W.DoublePipeLink)
    return {}


def has_see_also_after_notes_references_or_external_links(article_text: str) -> bool:
    s = W.for_site(current_site())
    # performance: only the level 2 headings
    headings = [m.value for m in W.Headings.matches(article_text) if not m.value.startswith("===")]
    article_text = "\r\n" + "\r\n".join(headings)

    see_also = s.SeeAlso.match(article_text).index
    if see_also <= 0:
        return False
    external_links = s.ExternalLinksHeader.match(article_text).index
    if 0 < external_links < see_also:
        return True
    references = W.ReferencesHeader.match(article_text).index
    if 0 < references < see_also:
        return True
    notes = W.NotesHeader.match(article_text).index
    return 0 < notes < see_also


# -- whitespace -----------------------------------------------------------------------------------


def remove_white_space(article_text: str, fix_optional_whitespace: bool = True) -> str:
    """Remove excess whitespace: <br /> before blank lines, trailing spaces, extra blank lines
    (not in <poem>), gaps in bulleted lists (WP:LISTGAP), trailing horizontal rules."""
    s = W.for_site(current_site())
    # <br /> followed by a blank line, not in blockquotes
    if _BrTwoNewlines.is_match(article_text) and not W.Blockquote.is_match(article_text):
        while _BrTwoNewlines.is_match(article_text):
            article_text = _BrTwoNewlines.replace(article_text.strip(), "\r\n\r\n")

    while _SpacesThenTwoNewline.is_match(article_text):
        article_text = _SpacesThenTwoNewline.replace(article_text, "\r\n\r\n")

    # excessive newlines: not within <poem>; keep one or two before a stub; don't merge two lists
    if "\r\n\r\n\r\n" in article_text:
        ok = True
        p = article_text.lower().find("poem")
        if p > -1:
            for m in W.Poem.matches(article_text[max(p - 50, 0) :]):
                if "\r\n\r\n" in m.value:
                    ok = False
                    break
        if ok:
            if s.Stub.is_match(article_text) or _TwoLists.is_match(article_text):
                article_text = _FourOrMoreNewlines.replace(article_text, "\r\n\r\n")
            else:
                article_text = W.ThreeOrMoreNewlines.replace(article_text, "\r\n\r\n")

    article_text = _NewlinesBelowExternalLinks.replace(article_text, "==External links==\r\n*")
    # WP:LISTGAP: no blank lines between bulleted list items
    while _NewlinesWithinLists.is_match(article_text):
        article_text = _NewlinesWithinLists.replace(article_text, "$1\r\n*")

    article_text = _HorizontalRule.replace(article_text.strip(), "")
    return article_text.replace("\r\n|\r\n\r\n", "\r\n|\r\n").strip()


def remove_all_white_space(article_text: str) -> str:
    article_text = article_text.replace("\t", " ")
    article_text = remove_white_space(article_text)
    article_text = article_text.replace("\r\n\r\n*", "\r\n*")
    article_text = _MultipleTabs.replace(article_text, " ")
    article_text = article_text.replace("==\r\n\r\n", "==\r\n")
    article_text = _NewlinesBelowExternalLinks.replace(article_text, "==External links==\r\n*")
    # one space after bullets, not several
    article_text = _WikiListWithMultipleSpaces.replace(article_text, "$1 ")
    # dash spacing
    article_text = _SpacedDashes.replace(article_text, "$1")
    return article_text.strip()


# -- dates ----------------------------------------------------------------------------------------


def predominant_dates(article_text: str) -> str:
    """Convert citation dates to the article's predominant date format (en only)."""
    from pyawb.core import tools

    if current_site().lang_code != "en":
        return article_text
    locale = determine_predominant_date_locale(article_text, True, True)
    if locale == DateLocale.UNDETERMINED:
        return article_text
    s = W.for_site(current_site())
    for m in W.CiteTemplate.matches(article_text):
        new_value = m.value
        for field in _DateFields:
            value = tools.get_template_parameter_value(new_value, field)
            if (
                W.ISODates.is_match(value)
                or s.AmericanDates.is_match(value)
                or s.InternationalDates.is_match(value)
            ):
                new_value = tools.update_template_parameter_value(
                    new_value, field, tools.convert_date(value, locale)
                )
        if m.value != new_value:
            article_text = article_text.replace(m.value, new_value)
    return article_text


_DateFormat = _R(r"(ymd|dmy|mdy)")


def determine_predominant_date_locale(
    article_text: str, consider_iso: bool = False, explicit_only: bool = False
) -> DateLocale:
    """The article's date format: from {{Use dmy dates}} etc., else by counting dates."""
    from pyawb.core import tools

    site = current_site()
    s = W.for_site(site)
    # first a template telling us the preference
    dates_t = W.UseDatesTemplate.match(article_text).group(2).lower().replace("iso", "ymd")
    dates_t = _DateFormat.match(dates_t).value
    if site.lang_code == "en" and dates_t:
        return {"dmy": DateLocale.INTERNATIONAL, "mdy": DateLocale.AMERICAN, "ymd": DateLocale.ISO}[
            dates_t
        ]
    if explicit_only:
        return DateLocale.UNDETERMINED

    # then count American and international dates
    americans = len(s.MonthDay.matches(article_text))
    internationals = len(s.DayMonth.matches(article_text))
    if consider_iso:
        isos = len(W.ISODates.matches(article_text))
        if isos > americans and isos > internationals:
            return DateLocale.ISO

    if americans != internationals:
        # C# integer division; the zero checks come first as in AWB (|| short-circuits)
        if (americans == 0 and internationals > 0) or (
            internationals // americans >= 2 and internationals > 4
        ):
            return DateLocale.INTERNATIONAL
        if (internationals == 0 and americans > 0) or (
            americans // internationals >= 2 and americans > 4
        ):
            return DateLocale.AMERICAN

    # explicit df or mf in birth/death templates
    birth = _BirthDate.match(article_text).value
    death = _DeathDate.match(article_text).value
    if tools.get_template_parameter_value(birth, "df").startswith(
        "y"
    ) or tools.get_template_parameter_value(death, "df").startswith("y"):
        return DateLocale.INTERNATIONAL
    if tools.get_template_parameter_value(birth, "mf").startswith(
        "y"
    ) or tools.get_template_parameter_value(death, "mf").startswith("y"):
        return DateLocale.AMERICAN
    return DateLocale.UNDETERMINED


# -- titles ---------------------------------------------------------------------------------------


def canonicalize_title(title: str) -> str:
    """Link target as MediaWiki would normalise it (decoded, underscores to spaces), unless the
    wiki has a page whose title really contains underscores."""
    from pyawb.core import tools

    # visible parts of links may contain text we shouldn't modify, such as refs and external links
    if not tools.is_valid_title(title) or ":/" in title:
        return title
    s = canonicalize_title_raw(title)
    if turn_first_to_upper(s) in current_site().underscored_titles:
        return url_decode(title.replace("+", "%2B")).strip("_")
    return s


def canonicalize_title_aggressively(title: str) -> str:
    """Title as MediaWiki stores it: decoded, first letter upper, canonical namespace prefix."""
    site = current_site()
    title = remove_hash_from_page_title(title)
    title = wiki_decode(title).strip()
    title = turn_first_to_upper(title, site)
    if title.startswith(":"):
        title = title[1:].strip()
    pos = title.find(":")
    if pos <= 0:
        return title
    title_part = title[: pos + 1]
    for key, regex in W.for_site(site).NamespacesCaseInsensitive.items():
        m = regex.match(title_part)
        if not m.success or m.index != 0:
            continue
        return site.namespaces[key] + turn_first_to_upper(title[pos + 1 :].strip(), site)
    return title


def canonicalize_title_raw(title: str, trim: bool = True) -> str:
    title = url_decode(title.replace("+", "%2B").replace("_", " "))
    return title.strip() if trim else title


# -- links and templates --------------------------------------------------------------------------

_LineSplit = _R("[\r\n]+")


def fix_main_article(article_text: str) -> str:
    """ "Main article: [[Foo]]" -> {{Main|Foo}}, "See also: [[Foo]]" -> {{See also|Foo}}."""
    # performance: check the first 20 characters of each line containing a colon
    lines = [s[:20] for s in _LineSplit.split(article_text) if s and ":" in s]
    if any(_SeeAlsoMainArticleQuick.is_match(s) for s in dict.fromkeys(lines)):
        article_text = _SeeAlsoLink.replace(
            article_text,
            lambda m: (
                "{{See also|" + m.group(1) + "}}"
                if not m.group(2)
                else "{{See also|" + m.group(1) + "|l1=" + m.group(3) + "}}"
            ),
        )
        article_text = _RegexMainArticle.replace(
            article_text,
            lambda m: (
                "{{Main|" + m.group(1) + "}}"
                if not m.group(2)
                else "{{Main|" + m.group(1) + "|l1=" + m.group(3) + "}}"
            ),
        )
    return article_text


def fix_empty_links_and_templates(article_text: str) -> str:
    """Remove [[]], [[Category:]], {{}} and the like."""
    s = W.for_site(current_site())
    if any(
        s.EmptyLink.is_match(lnk)
        for lnk in dict.fromkeys(_wikilinks.get_all_wiki_links(article_text))
    ):
        while s.EmptyLink.is_match(article_text):
            article_text = s.EmptyLink.replace(article_text, "")
    return s.EmptyTemplate.replace(article_text, "")


def _parse_month_year(value: str) -> datetime.date | None:
    from pyawb.core import tools

    return tools._parse_date("1 " + value)  # pyright: ignore[reportPrivateUsage]


def deduplicate_maintenance_tags(tags: list[str]) -> list[str]:
    """Merge repeated maintenance tags for the same template, keeping the earlier date."""
    from pyawb.core import tools

    def key(t: str) -> str:
        return turn_first_to_lower(tools.get_template_name(t))

    # performance: only work to do if some tags are duplicates
    if len(dict.fromkeys(key(t) for t in tags)) == len(tags):
        return tags

    new_tags: list[str] = []
    original_tags = tags

    # with an unnamed first argument, put tags with the longest part before the first = first,
    # so the unnamed parameter is kept (stable sort, like OrderByDescending)
    if any(_TemplateArg.is_match(t) for t in tags):
        tags = sorted(tags, key=lambda s: -(len(s[: s.index("=")]) if "=" in s else len(s)))

    for t in tags:
        existing = next((nt for nt in new_tags if key(nt) == key(t)), None)
        if existing is None:
            new_tags.append(t)
            continue
        # conflicting first arguments
        e_param = _TemplateArg.match(existing).group(1).strip()
        t_param = _TemplateArg.match(t).group(1).strip()
        if t_param and e_param and e_param != t_param:
            return original_tags

        existing_original = existing
        for k, v in tools.get_template_parameter_values(t).items():
            if not v:
                continue
            existing_value = tools.get_template_parameter_value(existing, k)
            # positional argument plus a non-date named parameter: cannot handle
            if e_param and k != "date":
                return original_tags
            if not existing_value:
                existing = tools.set_template_parameter_value(existing, k, v)
            elif existing_value != v:
                # conflicting values: only dates can be merged, keeping the earlier one
                if k != "date":
                    return original_tags
                existing_date = _parse_month_year(existing_value)
                tag_date = _parse_month_year(v)
                if existing_date is None or tag_date is None:
                    return original_tags
                if tag_date < existing_date:
                    existing = tools.set_template_parameter_value(existing, k, v)
        new_tags.remove(existing_original)
        new_tags.append(existing)
    return new_tags


_BulletExternalHider = HideText(False, True, False)


def bullet_external_links(article_text: str) -> str:
    """Bullet the external links in the External links section."""
    # performance: headings first, filtered to external links ones
    h = [
        m
        for m in _HeadingQuick.matches(article_text)
        if "external" in m.value.lower() and _ExternalLinksSection.is_match(m.value)
    ]
    if h:
        start = h[0].index
        sub = article_text[start:]
        if _NewlinesBeforeHTTP.is_match(sub):
            article_text = article_text[:start]
            sub = _BulletExternalHider.hide_more(sub)
            sub = _NewlinesBeforeHTTP.replace(sub, "$2* $3")
            return article_text + _BulletExternalHider.add_back_more(sub)
    return article_text


def bullet_external_links_no_change(article_text: str) -> tuple[str, bool]:
    """AWB's overload with out noChange: returns (text, no_change)."""
    new_text = bullet_external_links(article_text)
    return new_text, new_text == article_text


def no_include_include_only_programming_element(article_text: str) -> bool:
    return W.IncludeonlyNoinclude.is_match(article_text) or _TripleBraceNumIfExist.is_match(
        article_text
    )


def fix_images(article_text: str) -> str:
    """Normalise the File: prefix and canonicalise the file name in image links."""
    return W.for_site(current_site()).LooseImage.replace(article_text, _fix_images_me)


def _fix_images_me(m: DotNetMatch) -> str:
    image_name = m.group(2)
    # only the image name (group 2); don't convert %27%27 -- https://phabricator.wikimedia.org/T10932
    return (
        "[["
        + namespace.normalize(m.group(1), Namespace.FILE)
        + (image_name if "%27%27" in image_name else canonicalize_title(image_name).strip())
        + m.group(3).strip()
        + "]]"
    )


def fix_temperatures(article_text: str) -> str:
    """&deg;C, º F etc. -> °C, °F."""
    return _Temperature.replace(article_text, lambda m: "°" + m.group(1).upper())


def remove_empty_comments(article_text: str) -> str:
    return W.EmptyComments.replace(article_text, "")


def replace_image(old_image: str, new_image: str, article_text: str) -> str:
    """Replace uses of one file with another."""
    site = current_site()
    article_text = fix_images(article_text)
    file_ns = site.namespaces[Namespace.FILE]
    # remove image prefix
    old_image = wiki_decode(_R("^" + file_ns, O.IGNORE_CASE).replace(old_image, ""))
    new_image = wiki_decode(_R("^" + file_ns, O.IGNORE_CASE).replace(new_image, ""))
    old_image = rx.escape(old_image).replace("\\ ", "[ _]")
    old_image = (
        "((?i:"
        + site.generate_namespace_regex(Namespace.FILE, Namespace.MEDIA)
        + r"))\s*:\s*"
        + first_letter_case_insensitive(old_image)
    )
    # AWB passes the new file name into the .NET replacement string unescaped; kept as is
    return _R(old_image).replace(article_text, "$1:" + new_image)


def replace_image_no_change(old_image: str, new_image: str, article_text: str) -> tuple[str, bool]:
    """AWB's overload with out noChange: returns (text, no_change)."""
    new_text = replace_image(old_image, new_image, article_text)
    return new_text, new_text == article_text


def remove_image(image: str, article_text: str, comment_out: bool, comment: str) -> str:
    """Remove (or comment out) uses of a file."""
    if not image:
        return article_text
    site = current_site()
    file_ns_ci = site.namespaces_case_insensitive[Namespace.FILE]
    # remove image prefix
    image = wiki_decode(_R("^" + file_ns_ci, O.IGNORE_CASE).replace(image, ""))
    # first-letter case insensitive file name
    image = first_letter_case_insensitive(url_decode(rx.escape(image).replace("\\ ", "[ _]")))
    article_text = fix_images(article_text)

    # standard [[File:blah...]] links
    r = _R(
        r"\[\[\s*:?\s*(?i:"
        + site.generate_namespace_regex(Namespace.FILE, Namespace.MEDIA)
        + r")\s*:\s*"
        + image
        + r"((?>[^\[\]]+|\[\[(?<DEPTH>)|\]\](?<-DEPTH>))*(?(DEPTH)(?!)))\]\]",
        O.SINGLELINE,
    )
    # fall back to File:blah... in galleries etc., or just the file name (infoboxes etc.)
    if not r.matches(article_text):
        r = _R("(" + file_ns_ci + ")?" + image + r"(?: *\|[^\r\n=]+(?=\s*$))?", O.MULTILINE)
    return r.replace(
        article_text, lambda m: "<!-- " + comment + " " + m.value + " -->" if comment_out else ""
    )


def remove_image_no_change(
    image: str, article_text: str, comment_out: bool, comment: str
) -> tuple[str, bool]:
    """AWB's overload with out noChange: returns (text, no_change)."""
    new_text = remove_image(image, article_text, comment_out, comment)
    return new_text, new_text == article_text


# -- people ---------------------------------------------------------------------------------------


def is_article_about_a_person(
    article_text: str, article_title: str, parse_talk_page: bool = False
) -> bool:
    """Heuristic: is this an article about one person (for DEFAULTSORT, Living people etc.)?"""
    from pyawb.core import tools
    from pyawb.core.parsers import metadatasorter as _mds

    site = current_site()
    s = W.for_site(site)
    if (
        site.lang_code != "en"
        or namespace.determine(article_title) == Namespace.CATEGORY
        or _NotPersonArticles.is_match(article_title)
        or _fixheadings.ListOf.is_match(article_title)
        or "[[fictional character" in article_text
        or s.Disambigs.is_match(article_text)
        or _InUniverse.is_match(article_text)
        or _NotAboutAPersonCategories.is_match(article_text)
        or _NobleFamilies.is_match(article_text)
        or _CategoryCharacters.is_match(article_text)
        or "organization" in W.InfoBox.match(article_text).group(1).lower()
        or _NotPersonInfoboxes.is_match(article_text)
        or s.SIAs.is_match(article_text)
        or len(W.PeopleInfoboxTemplates.matches(article_text)) > 1
    ):
        return False

    m2 = _IMA.match(article_text)
    if m2:
        background = tools.get_template_parameter_value(m2.value, "Background", True)
        if "band" in background or "classical_ensemble" in background or "temporary" in background:
            return False

    zeroth = tools.get_zeroth_section(article_text)
    # not about a person if it's not the principal article on the subject
    if _SeeAlsoOrMain.is_match(zeroth):
        return False

    # not about one person if there are different birth or death date templates
    for r in (_BirthDate, _DeathDate):
        seen: list[str] = []
        for m in r.matches(article_text):
            if seen and m.value not in seen:
                return False
            seen.append(m.value)

    # duplicate living people categories must not count as an article about several people
    article_text, cats = _mds.MetaDataSorter().remove_cats(article_text, article_title)
    article_text += cats

    if len(W.DeathsOrLivingCategory.matches(cats)) > 1:
        return False

    if (
        "-bio-stub}}" in article_text
        or "-politician-stub}}" in article_text
        or "-writer-stub}}" in article_text
        or _CategoryLivingPeople in cats
        or len(W.PeopleInfoboxTemplates.matches(zeroth)) == 1
        or _cds.category_match(cats, _cds.YearOfBirthMissingLivingPeople)
    ):
        return True

    # bold text linking to another article may link to the main article on the person,
    # e.g. '''military career of [[Napoleon Bonaparte]]'''
    zeroth_no_templates = W.Template.replace(zeroth, "")
    for m in W.Bold.matches(zeroth_no_templates):
        if W.WikiLink.is_match(m.value):
            return False

    if len(_BirthDate.matches(zeroth)) == 1 or len(_DeathDate.matches(zeroth)) == 1:
        return True

    if W.InfoBox.is_match(zeroth) and not W.PeopleInfoboxTemplates.is_match(zeroth):
        return False

    return (
        W.DeathsOrLivingCategory.is_match(cats)
        or W.LivingPeopleRegex2.is_match(article_text)
        or W.BirthsCategory.is_match(cats)
        or W.PeopleFromCategory.is_match(cats)
        or W.BLPSources.is_match(_BLPUnsourcedSection.replace(article_text, ""))
        or _RefImproveBLP.is_match(article_text)
    )


def living_people(article_text: str, article_title: str) -> str:
    """Add [[Category:Living people]] to articles with a recent "XXXX births" category and no
    sign of death."""
    site = current_site()
    if site.lang_code == "sco" or site.is_wikimedia_monolingual_project:
        return article_text
    m = W.BirthsCategory.match(_cds.get_cats(article_text))
    # only with an 'XXXX births' category
    if not m:
        return article_text
    # not if dead, or thought to be dead
    # (AWB builds these with ToString() of the regexes, which drops their IgnoreCase option)
    if (
        W.DeathsOrLivingCategory.is_match(article_text)
        or W.LivingPeopleRegex2.is_match(article_text)
        or _R(_BornDeathRegex.pattern.replace("^", r"('''(?:[^']+|.*?[^'])'''\s*\()")).is_match(
            article_text
        )
        or _R(_DiedDateRegex.pattern.replace("^", r"('''(?:[^']+|.*?[^'])'''\s*\()")).is_match(
            article_text
        )
    ):
        return article_text

    birth_cat = m.value
    byear = m.group(1)
    birth_year = int(byear) if _ThreeOrMoreDigits.is_match(byear) else 0
    # per [[:Category:Living people]] and [[WP:BDP]], not if born > 115 years ago
    if birth_year < datetime.date.today().year - 115:
        return article_text
    # sort key from the 'XXXX births' category
    cat_key = _BirthsSortKey.match(birth_cat).value if "|" in birth_cat else "]]"
    return (
        article_text
        + "[["
        + ("" if namespace.is_main_space(article_title) else ":")
        + "Category:Living people"
        + cat_key
    )


def living_people_no_change(article_text: str, article_title: str) -> tuple[str, bool]:
    """AWB's overload with out noChange: returns (text, no_change)."""
    new_text = living_people(article_text, article_title)
    return new_text, new_text == article_text


def format_to_bda(date_and_age: str) -> str:
    """ "May 2, 1950 (age 75)" -> {{birth date and age|mf=y|1950|05|02}}."""
    from pyawb.core import tools

    original = date_and_age
    # clean up the date format if possible
    date_and_age = Parsers().fix_date_ordinals_and_of(" " + date_and_age, "test")
    # remove date wikilinks
    date_and_age = W.WikiLinksOnlyPossiblePipe.replace(date_and_age, "$1").strip()
    # must end with (age xx)
    if not _AgeBrackets.is_match(date_and_age):
        return original
    date_and_age = _AgeBrackets.replace(date_and_age, "")
    iso_date = tools.convert_date(date_and_age, DateLocale.ISO)
    if iso_date == date_and_age and not W.ISODates.is_match(date_and_age):
        return original
    american = W.for_site(current_site()).AmericanDates.is_match(date_and_age)
    return (
        "{{birth date and age|"
        + ("mf=y|" if american else "df=y|")
        + iso_date.replace("-", "|")
        + "}}"
    )


def interwiki_conversions(article_text: str) -> str:
    """Obsolete interwiki prefixes: zh-tw -> zh, nb -> no, dk -> da."""
    if not current_site().is_wikimedia_project:
        return article_text
    possible = [
        lnk for lnk in dict.fromkeys(_wikilinks.get_all_wiki_links(article_text)) if ":" in lnk
    ]
    for old, new in (("[[zh-tw:", "[[zh:"), ("[[nb:", "[[no:"), ("[[dk:", "[[da:")):
        if any(lnk.startswith(old) for lnk in possible):
            article_text = article_text.replace(old, new)
    return article_text


def interwiki_conversions_no_change(article_text: str) -> tuple[str, bool]:
    """AWB's overload with out noChange: returns (text, no_change)."""
    new_text = interwiki_conversions(article_text)
    return new_text, new_text == article_text


def conversions(article_text: str) -> str:
    """Template conversions: {{msg:}}, {{commons|Category:X}}, BASEPAGENAME substitution,
    {{no footnotes}} -> {{more footnotes needed}}, {{x|section}} -> {{x section}}, BLP variants
    on articles about living people, portal and section template merging, infobox names,
    dablinks."""
    from pyawb.core import tools

    site = current_site()
    article_text = article_text.replace("{{msg:", "{{")

    # performance: get the templates so the functions below only run when needed
    all_templates = _templates.get_all_templates(article_text)

    if _templates.template_exists(all_templates, _ConversionsCnCommons):
        if site.is_wikimedia_project:
            article_text = _CommonsCategory.replace(article_text, r"{{Commons category|$1}}")
        for r, repl in _RegexConversion:
            article_text = r.replace(article_text, repl)

    if _templates.template_exists(all_templates, W.BASEPAGENAMETemplates):
        basepagename_in_refs = any(
            W.BASEPAGENAMETemplates.is_match(m.value) for m in W.Refs.matches(article_text)
        )
        if not basepagename_in_refs and "{{#ifeq:{" not in article_text:
            for t in W.BASEPAGENAMETemplatesL:
                article_text = tools.rename_template(article_text, t, "subst:" + t)

    # {{no footnotes}} -> {{more footnotes needed}} if there are <ref>s or {{sfn}}s, unless the
    # template has section/reason arguments
    if _templates.template_exists(all_templates, _NoFootnotes) and (
        _templates.template_exists(all_templates, _refs.Footnote)
        or _refs.total_refs_not_grouped(article_text) > 0
    ):
        article_text = _NoFootnotes.replace(
            article_text, lambda m: _only_article_blp_template_me(m, "more footnotes needed")
        )

    # {{foo|section|...}} -> {{foo section|...}}
    if _templates.template_exists(all_templates, _SectionTemplates):
        article_text = _SectionTemplates.replace(article_text, _section_template_conversions_me)
        all_templates = _templates.get_all_templates(article_text)

    # articles in [[Category:Living people]]
    if site.is_wikipedia_en and _cds.category_match(article_text, "Living people"):
        article_text = _blp_conversions(article_text, all_templates)

    if _templates.template_exists(all_templates, W.PortalTemplate):
        article_text = _sortmeta.merge_portals(article_text)

    if (
        sum(
            1 for t in all_templates if _sortmeta.SectionMergedTemplatesR.is_match("{{" + t + "|}}")
        )
        > 1
    ):
        article_text = _sortmeta.merge_templates_by_section(article_text)

    # clean up Template: and underscores in infobox names
    if _templates.template_exists(all_templates, W.InfoBox):

        def infobox(m: DotNetMatch) -> str:
            new_name = canonicalize_title(m.group(1))
            return m.value if new_name == m.group(1) else tools.rename_template(m.value, new_name)

        article_text = W.InfoBox.replace(article_text, infobox)

    if _templates.template_exists(all_templates, W.Dablinks):
        article_text = _sortmeta.dablinks(article_text)
    return article_text


def conversions_no_change(article_text: str) -> tuple[str, bool]:
    """AWB's overload with out noChange: returns (text, no_change)."""
    new_text = conversions(article_text)
    return new_text, new_text == article_text


def _blp_conversions(article_text: str, all_templates: Sequence[str]) -> str:
    from pyawb.core import tools

    def to_blp(text: str, name: str, blp_name: str, existing_blp: DotNetRegex) -> str:
        # {{name}} -> {{blp_name}} if there is one call with no free-text first argument
        mc = nested_template_regex(name).matches(text)
        if len(mc) == 1:
            call = mc[0].value
            if (
                turn_first_to_lower(tools.get_template_argument(call, 1)).startswith("date")
                or tools.get_template_argument_count(call) == 0
            ):
                # with an existing BLP tag, remove the other one
                if existing_blp.is_match(text):
                    text = nested_template_regex(name).replace(text, "")
                    text = W.MultipleIssues.replace(text, Parsers().multiple_issues_single_tag_me)
                else:
                    text = tools.rename_template(text, name, blp_name, False)
        return text

    if "Unreferenced" in all_templates:
        article_text = to_blp(article_text, "unreferenced", "BLP unreferenced", BLPUnsourced)
    for old, new in (
        ("Unreferenced section", "BLP unreferenced section"),
        ("Primary sources", "BLP primary sources"),
        ("One source", "BLP one source"),
        ("Self-published", "BLP self-published"),
        ("No footnotes", "BLP no footnotes"),
    ):
        if old in all_templates:
            article_text = tools.rename_template(
                article_text, old if old == "No footnotes" else old.lower(), new, False
            )
    if "More citations needed" in all_templates:
        article_text = to_blp(
            article_text,
            "More citations needed",
            "BLP sources",
            nested_template_regex("BLP sources"),
        )
    if "More citations needed section" in all_templates:
        article_text = tools.rename_template(
            article_text, "More citations needed section", "BLP sources section", False
        )
    return article_text


_SectionArg = _R(r"\|\s*[Ss]ection\s*\|")
_TypeSectionArg = _R(r"\|\s*type\s*=\s*[Ss]ection\s*\|")
_ListArg = _R(r"\|\s*list\s*\|")


def _section_template_conversions_me(m: DotNetMatch) -> str:
    from pyawb.core import tools

    new_value = m.value
    name = tools.get_template_name(new_value)
    if (
        tools.get_template_argument(new_value, 1) in ("section", "Section")
        or tools.get_template_parameter_value(new_value, "type").lower() == "section"
    ):
        new_value = tools.rename_template(_SectionArg.replace(new_value, "|"), name + " section")
    if tools.get_template_parameter_value(new_value, "type").lower() == "section":
        new_value = tools.remove_template_parameter(new_value, "section")
        new_value = tools.rename_template(
            _TypeSectionArg.replace(new_value, "|"), name + " section"
        )
    # {{Unreferenced}}: also the list parameter
    if name.lower() == "unreferenced" and tools.get_template_argument(new_value, 1) == "list":
        new_value = tools.rename_template(_ListArg.replace(new_value, "|"), name + " section")
    # {{Unreferenced}}: auto=yes is deprecated
    if (
        name.lower() == "unreferenced"
        and tools.get_template_parameter_value(new_value, "auto").lower() == "yes"
    ):
        new_value = tools.remove_template_parameter(new_value, "auto")
    return new_value


def _only_article_blp_template_me(m: DotNetMatch, new_template_name: str) -> str:
    from pyawb.core import tools

    new_value = tools.remove_template_parameter(m.value, "BLP")
    new_value = tools.remove_template_parameter(new_value, "article")
    new_value = tools.remove_template_parameter(new_value, "date")
    if tools.get_template_argument_count(new_value) > 0:
        return m.value
    return tools.rename_template(m.value, new_template_name)


def check_no_bots(article_text: str, user: str) -> bool:
    """Whether {{bots}}/{{nobots}} allow the user (and AWB) to edit the page."""
    user = unicodedata.normalize("NFC", user)
    article_text = W.UnformattedText.replace(article_text, "")
    bot = _BotsAllow.match(article_text)
    if bot:
        return _R(r"(?:^|,)\s*(?:" + user + r"|awb)\s*(?:,|$)", O.IGNORE_CASE).is_match(
            bot.group(1)
        )
    return not _R(
        r"\{\{\s*(?:nobots|(nobots|bots)\|(allow=none|deny=(?!none).*("
        + user
        + r"|awb|all)|optout=all))\s*(?:\}\}|,)",
        O.IGNORE_CASE,
    ).is_match(article_text)


def external_url_to_internal_link(article_text: str) -> str:
    """[https://en.wikipedia.org/wiki/Foo text] -> [[w:en:Foo|text]] etc."""
    article_text = _ExtToIn.replace(article_text, "[[$2$3$4$5$6$7$8:$1:$9|$10]]")
    article_text = _MetaCommonsIncubatorQualityExternalLink.replace(
        article_text, "[[$1$2$3$4:$5|$6]]"
    )
    article_text = _WikiaExternalLink.replace(article_text, "[[wikia:$1:$2|$3]]")
    same_language = _R(
        r"(\[\[(?:wikt|[nbqsvw]):)" + current_site().lang_code + r":([^\[\]\|]+\|[^\[\]\|]+\]\])"
    )
    return same_language.replace(article_text, "$1$2")


def extract_coins(text: str) -> dict[str, str]:
    """COinS (rft.*) metadata from a Zotero/citoid JSON response."""
    data: dict[str, str] = {}
    text = _coinsR.match(text).group(1)
    for m in _coinsParam.matches(text):
        data.setdefault(m.group(1), url_decode(m.group(2)))
    return data


# -- property checks ------------------------------------------------------------------------------


def has_stub_template(article_text: str) -> bool:
    return W.for_site(current_site()).Stub.is_match(article_text)


def is_stub(article_text: str) -> bool:
    return has_stub_template(article_text) or len(article_text) < StubMaxWordCount


def has_infobox(article_text: str) -> bool:
    if current_site().lang_code != "en":
        return False
    return W.InfoBox.is_match(W.UnformattedText.replace(article_text, ""))


def is_in_use(article_text: str) -> bool:
    return W.for_site(current_site()).InUse.is_match(W.UnformattedText.replace(article_text, ""))


def has_sic_tag(article_text: str) -> bool:
    return _templates.template_exists(
        _templates.get_all_templates(article_text), _SicTypo
    ) or _SicTag.is_match(article_text)


def has_dead_links(article_text: str) -> bool:
    return W.DeadLink.is_match(W.Comments.replace(article_text, ""))


def has_target_less_links(article_text: str) -> bool:
    return W.TargetLessLink.is_match(W.Comments.replace(article_text, ""))


def has_double_pipe_links(article_text: str) -> bool:
    return W.DoublePipeLink.is_match(W.Comments.replace(article_text, ""))


def has_morefootnotes_and_many_references(article_text: str) -> bool:
    return (
        _templates.template_exists(_templates.get_all_templates(article_text), W.MoreNoFootnotes)
        and W.MoreNoFootnotes.is_match(
            W.Comments.replace("".join(_templates.get_all_template_detail(article_text)), "")
        )
        and len(W.Refs.matches(article_text)) > 4
    )


def user_signature(article_text: str) -> dict[int, int]:
    s = W.for_site(current_site())
    if any(s.UserSignature.is_match(lnk) for lnk in _wikilinks.get_all_wiki_links(article_text)):
        return _dictionary_of_matches(article_text, s.UserSignature)
    return {}


def is_missing_references_display(article_text: str) -> bool:
    """Has refs but no {{reflist}}/<references />."""
    if current_site().lang_code != "en" or _templates.template_exists(
        _templates.get_all_templates(article_text), _ReflistQuick
    ):
        return False
    # list-defined references with unbalanced braces can stop ReferencesTemplate matching
    return (
        not _ReflistQuick.is_match(article_text)
        and not W.ReferencesTemplate.is_match(article_text)
        and (
            _refs.total_refs_not_grouped(article_text) > 0
            or _GRTemplateDecimal.is_match(article_text)
        )
    )


_ReferenceEnd = _R(W.ReferenceEnd)


def has_ref_after_reflist(article_text: str) -> bool:
    if current_site().lang_code != "en" or not article_text:
        return False
    refs_index = ref_length = 0
    max_len = min(len(article_text), 1000)
    original = article_text
    # performance: {{reflist}} is normally near the end, so look at the last 1000 characters, then
    # the last 2000 and so on
    for i in range(max_len, len(original) + 1, max_len):
        article_text = original[len(original) - i :]
        for m in W.ReferencesTemplate.matches(article_text):
            if refs_index > 0:
                return False  # several {{reflist}}: not supported
            refs_index, ref_length = m.index, m.length
        article_text = article_text[refs_index + ref_length :]
        article_text = W.Comments.replace(article_text, "")
        if refs_index > 0:
            return _ReferenceEnd.is_match(article_text)
    return False


def has_bare_references(article_text: str) -> bool:
    references_index = W.ReferencesHeader.match(article_text).index
    if references_index < 2:
        return False
    external_links_index = W.for_site(current_site()).ExternalLinksHeader.match(article_text).index
    # the references section: to External links or the end, whichever is earlier
    if external_links_index > references_index:
        refs_area = article_text[references_index:external_links_index]
    else:
        refs_area = article_text[references_index:]
    return W.BareExternalLink.is_match(refs_area)


# -- the Parsers class (instance methods) ---------------------------------------------------------

_Number = _R(r"^\d+$")
_PercentQuick = _R(r"%(\p{P}|\)?\s)")
_PagesQuick = _R(r"(p\.) *[0-9IVXCL][^S]")
_PagesNbsp = _R(r"(\b[Pp]?p\.) *(?=[\dIVXCL][^S])")
_NumText = _R(r"\b[0-9]+[  ]*[B-Wc-zµ/°]{1,4}\b")
_LeadingZeroHour = _R(r"^0(\d:)")
_Dashed = _R(r"(?:—|-|&#8212;|&mdash;)+\s*[0-9].{0,12}")


class Parsers(
    _sortmeta.SortMetaDataMixin,
    _cds.CategoryDefaultSortMixin,
    _fixdates.FixDatesMixin,
    _fixsyntax.FixSyntaxMixin,
    _mi.MultipleIssuesMixin,
    _boldtitle.BoldTitleMixin,
    _tagger.TaggerMixin,
):
    """AWB's Parsers instance: general fixes that keep state (hiding, settings)."""

    def __init__(
        self, stub_word_count: int | None = None, add_human_key: bool | None = None
    ) -> None:
        self._hider = HideText()
        self._hider_hide_ext_links_images = HideText(True, True, True)
        self._sorter: MetaDataSorter | None = None
        global StubMaxWordCount
        if stub_word_count is not None:
            StubMaxWordCount = stub_word_count
        if add_human_key is not None:
            self.sorter.add_cat_key = add_human_key

    @property
    def sorter(self) -> MetaDataSorter:
        from pyawb.core.parsers.metadatasorter import MetaDataSorter

        if self._sorter is None:
            self._sorter = MetaDataSorter()
        return self._sorter

    @property
    def sort_interwikis(self) -> bool:
        return self.sorter.sort_interwikis

    @sort_interwikis.setter
    def sort_interwikis(self, value: bool) -> None:
        self.sorter.sort_interwikis = value

    @property
    def inter_wiki_order(self) -> InterWikiOrderEnum:
        return self.sorter.inter_wiki_order

    @inter_wiki_order.setter
    def inter_wiki_order(self, value: InterWikiOrderEnum) -> None:
        self.sorter.inter_wiki_order = value

    # hiding

    def hide_text(self, article_text: str) -> str:
        return self._hider.hide(article_text)

    def add_back_text(self, article_text: str) -> str:
        return self._hider.add_back(article_text)

    def hide_text_images(self, article_text: str) -> str:
        return self._hider_hide_ext_links_images.hide(article_text)

    def add_back_text_images(self, article_text: str) -> str:
        return self._hider_hide_ext_links_images.add_back(article_text)

    def hide_more_text(self, article_text: str, hide_only_target_of_wikilink: bool = False) -> str:
        return self._hider_hide_ext_links_images.hide_more(
            article_text, hide_only_target_of_wikilink
        )

    def add_back_more_text(self, article_text: str) -> str:
        return self._hider_hide_ext_links_images.add_back_more(article_text)

    # fixes

    def fix_br_paragraphs(self, article_text: str) -> str:
        if _fixsyntax.SyntaxRemoveBrQuick.is_match(article_text):  # check for performance
            article_text = _fixsyntax.SyntaxRemoveBr.replace(article_text, "\r\n\r\n")
        article_text = _fixsyntax.SyntaxRemoveParagraphs.replace(article_text, "\r\n\r\n")
        return _fixsyntax.SyntaxRegexListRowBrTagStart.replace(article_text, "$1")

    def mdashes(self, article_text: str, article_title: str) -> str:
        """Hyphens to en/em dashes in page, time, money, age and number ranges; title dashes;
        '--' between words; "…" to "..." (en); minus signs in superscripts."""
        back = 12
        # performance: pick out the ends of ranges and run the regexes on those first
        dashed = list(
            dict.fromkeys(
                article_text[m.index - back : m.index + m.length]
                if m.index > back
                else article_text[: m.length + m.index]
                for m in _Dashed.matches(article_text)
            )
        )

        if any(_PageRangeIncorrectMdash.is_match(s) for s in dashed):

            def pages(m: DotNetMatch) -> str:
                part = m.group(1)
                if "Pp" in part:
                    part = part.lower()
                return part + m.group(2) + "–" + m.group(3)

            article_text = _PageRangeIncorrectMdash.replace(article_text, pages)
        if any(_UnitTimeRangeIncorrectMdash.is_match(s) for s in dashed):
            article_text = _UnitTimeRangeIncorrectMdash.replace(article_text, "$1–$2$3$4")
        if any(_DollarAmountIncorrectMdash.is_match(s) for s in dashed):
            article_text = _DollarAmountIncorrectMdash.replace(article_text, "$1–$2")
        if any(_AMPMIncorrectMdash.is_match(s) for s in dashed):
            article_text = _AMPMIncorrectMdash.replace(article_text, "$1–$3")
        if any(_AgeIncorrectMdash.is_match(s) for s in dashed):
            article_text = _AgeIncorrectMdash.replace(article_text, "$1 $2–$3")

        # if the title has en or em dashes, use them where the text has the title with hyphens
        if "–" in article_title or "—" in article_title:
            hyphenated = article_title.replace("–", "-").replace("—", "-")
            # AWB passes the title into the .NET replacement string unescaped; kept as is
            article_text = _R(rx.escape(hyphenated)).replace(article_text, article_title)

        # '--' between alphanumerics: em dash, or en dash between numbers
        if namespace.determine(article_title) == Namespace.ARTICLE and "--" in article_text:
            article_text = _SentenceClauseIncorrectMdash.replace(
                article_text,
                lambda m: (
                    m.group(1)
                    + (
                        "–"
                        if _Number.is_match(m.group(1)) and _Number.is_match(m.group(2))
                        else "—"
                    )
                    + m.group(2)
                ),
            )

        # T337532 MOS:ELLIPSIS
        if current_site().is_wikipedia_en:
            article_text = article_text.replace("…", "...")

        # minus sign in superscripts, [[Wikipedia:MOSNUM#Common_mathematical_symbols]]
        return _SuperscriptMinus.replace(article_text, "$1−")

    def fix_non_breaking_spaces(self, article_text: str) -> str:
        """&nbsp; between numbers and units, after p./pp., in 12-hour times; percent and
        currency spacing (en)."""
        lang = current_site().lang_code
        # Chinese does not use spaces to separate sentences/words
        if lang != "zh":
            num_text = list(dict.fromkeys(m.value for m in _NumText.matches(article_text)))
            if any(W.UnitsWithoutNonBreakingSpaces.is_match(s) for s in num_text):
                # "um" (micrometre) only on English wikis, to avoid the German word "um"
                article_text = W.UnitsWithoutNonBreakingSpaces.replace(
                    article_text,
                    lambda m: (
                        m.value
                        if m.group(2).startswith("um") and lang != "en"
                        else m.group(1) + "&nbsp;" + m.group(2)
                    ),
                )
            if any(s.endswith(("in", "ft", "oz")) for s in num_text):
                article_text = W.ImperialUnitsInBracketsWithoutNonBreakingSpaces.replace(
                    article_text, "$1&nbsp;$2"
                )
            if "&nbsp;ft" in article_text:  # check for performance
                article_text = W.MetresFeetConversionNonBreakingSpaces.replace(
                    article_text, "$1&nbsp;m"
                )
            # non-breaking space after pp. for pages
            if _PagesQuick.is_match(article_text):  # check for performance
                article_text = _PagesNbsp.replace(article_text, "$1&nbsp;")

        # 12-hour clock times [[MOS:TIME]], dotted lower-case a.m./p.m. only
        if lang in ("en", "simple"):
            if ".m." in article_text:  # check for performance; also trims a leading zero
                article_text = W.ClockTime.replace(
                    article_text,
                    lambda m: _LeadingZeroHour.replace(m.group(1), "$1") + "&nbsp;" + m.group(2),
                )
            # no space before percent, [[WP:PERCENT]]
            if _PercentQuick.is_match(article_text):
                article_text = W.Percent.replace(article_text, " $1%$3")
            # no space after symbol-only currencies, [[WP:CURRENCY]]
            article_text = W.Currency.replace(article_text, "$1$3")
        return article_text

    def fix_unicode(self, article_text: str) -> str:
        """Paragraph/line separators to spaces; remove line separators and zero-width spaces at
        the start of lines (CHECKWIKI error 16)."""
        article_text = article_text.replace(" ", " ")
        article_text = _LineSeparatorZeroWidthSpaceStartOfLine.replace(article_text, "")
        return article_text.replace(" ", " ")

    def unicodify(self, article_text: str) -> str:
        """Convert HTML entities to characters, except those that must stay entities."""
        if _MathTagStart.is_match(article_text):
            return article_text
        article_text = _NDash.replace(article_text, "&ndash;")
        article_text = _MDash.replace(article_text, "&mdash;")
        article_text = article_text.replace(" &amp; ", " & ")
        article_text = article_text.replace("&amp;", "&amp;amp;")
        article_text = article_text.replace("&#153;", "™")
        article_text = article_text.replace("&#149;", "•")
        # a line starting ; ending : uses : as indent, so &#58; at end of line must stay
        article_text = article_text.replace("&#58;\r\n", "&amp;#58;\r\n")
        for r, repl in _RegexUnicode:
            article_text = r.replace(article_text, repl)
        return html_decode(article_text)

    def unicodify_no_change(self, article_text: str) -> tuple[str, bool]:
        new_text = self.unicodify(article_text)
        return new_text, new_text == article_text
