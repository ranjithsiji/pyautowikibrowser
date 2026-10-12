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
# Ported from AutoWikiBrowser WikiFunctions/WikiRegexes.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Port of WikiFunctions/WikiRegexes.cs: the common regexes used across AWB.

Patterns are copied byte-for-byte from AWB and translated at load time by awb_l.core.dotnet_regex.
Names are kept exactly as in AWB so the C# source and tests can be followed side by side.

Module-level names are AWB's static readonly fields; like AWB, the ones built with
nested_template_regex use English Wikipedia's template namespace. Everything that depends on the
wiki is on SiteRegexes (see for_site).

The static section below was generated from WikiRegexes.cs; edit it by hand from now on.
"""

# ruff: noqa: E501

from __future__ import annotations

import functools
from collections.abc import Iterable

from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.rx import DotNetRegex, escape
from awb_l.core.site import CANONICAL_NAMESPACES, Namespace, SiteConfig
from awb_l.core.textutil import first_difference, nested_template_regex, template_name_regex

_R = DotNetRegex


def _union(a: Iterable[str], b: Iterable[str]) -> tuple[str, ...]:
    """Enumerable.Union: a then b, without duplicates, keeping first occurrences."""
    return tuple(dict.fromkeys([*a, *b]))


# -- Static regexes (AWB static readonly fields) --------------------------------------------------

_InUseList = (
    r"Inuse",
    r"In use",
    r"GOCEinuse",
    r"goceinuse",
    r"in creation",
    r"increation",
    r"GOCE inuse",
    r"GOCE in use",
    r"Goce in use",
    r"Goce inuse",
    r"GOCE in-use",
    r"Big edit",
    r"Currently editing",
    r"Edited",
    r"Editing",
    r"In Use",
    r"IN USE",
    r"In-use",
    r"Inuse-elapsed",
    r"Inusefor",
    r"Iu",
    r"Major edit",
    r"Majoredit",
    r"PageRefurb",
    r"Refactoring",
    r"Wait",
    r"Wip",
    r"WIP",
)

_MultipleIssuesList = (
    r"multipleissues",
    r"multiple issues",
    r"mi",
    r"MI",
    r"multiple",
    r"issues",
    r"Articleissues",
    r"Article issues",
)

# Matches all wikilinks, categories, images etc. with nested links on same line. Group 1 is the
# link content
SimpleWikiLink = _R(r"\[\[((?>[^\[\]\n]+|\[\[(?<DEPTH>)|\]\](?<-DEPTH>))*(?(DEPTH)(?!)))\]\]")

# Matches only internal wiki links
WikiLinksOnly = _R(r"\[\[[^[\]\n]+(?<!\[\[[A-Z]?[a-z-]{2,}:[^[\]\n]+)\]\]")

# Matches only internal wiki links, possibly with pipe; group 1 is target, group 2 is pipe text,
# if piped link
WikiLinksOnlyPossiblePipe = _R(
    r"\[\[([^[\]\|\n]+)(?<!\[\[[A-Z]?[a-z-]{2,}:[^[\]\n]+)(?:\|([^[\]\|\n]+))?\]\]"
)

# Matches only internal wikilinks (with or without pipe) with extra word character(s) e.g.
# [[link]]age or [[here|link]]age https://en.wikipedia.org/wiki/Wikipedia_talk:AutoWikiBrowser/Fea
# ture_requests#Improve_HideText.HideMore.28.29
WikiLinksOnlyPlusWord = _R(r"\[\[[^\[\]\n]+\]\](\w+)")

# Matches all wikilinks (including interwikis, images, categories etc.) up to pipe or end of
# wikilink. Group 1 is the target of the wikilink
WikiLink = _R(r"\[\[([^\]\|]+)(?:\]\]|\|)")

# Matches piped wikilinks, group 1 is target, group 2 the text
PipedWikiLink = _R(r"\[\[([^[\]\n]*?)\|([^[\]\n]*?)\]\]")

# Matches unpiped wikilinks, group 1 is text
UnPipedWikiLink = _R(r"\[\[([^\|\n]*?)\]\]")

# List of Magic words from [[Category:Pages_which_use_a_template_in_place_of_a_magic_word]]
MagicWordTemplates = nested_template_regex(
    (
        r"BASEPAGENAME",
        r"DEFAULTSORT",
        r"DISPLAYTITLE",
        r"Displaytitle",
        r"FULLPAGENAME",
        r"Fullpagename",
        r"Namespace",
        r"Numberofarticles",
        r"PAGENAME",
        r"PAGESIZE",
        r"PROTECTIONLEVEL",
        r"Pagename",
        r"SUBPAGENAME",
        r"Subpagename",
        r"padleft",
    )
)

# List of magic words behaviour switches from
# https://en.wikipedia.org/wiki/Help:Magic_words#Behavior_switches
MagicWordsBehaviourSwitches = _R(
    r"__(NOTOC|FORCETOC|TOC|NOEDITSECTION|NEWSECTIONLINK|NONEWSECTIONLINK|NOGALLERY|HIDDENCAT|INDEX|NOINDEX|STATICREDIRECT)__",
    O.IGNORE_CASE,
)

# Matches headings of all levels, group 1 being the heading name
Headings = _R(
    r"^={1,6} *(.*?) *={1,6}(?: *⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->|< *[Bb][Rr] */ *>)?\s*$", O.MULTILINE
)

# Matches headings of all levels and the whitespace before them, group 2 being the heading name
HeadingsWhitespaceBefore = _R(
    r"\s+(?:< *[Bb][Rr] *\/? *>\s*)*^ *(={1,6}(.*?)={1,6}[\t ]*)(?=\r\n)", O.MULTILINE
)

# Matches level 2 headings
HeadingLevelTwo = _R(r"^==([^=](?:.*?[^=])?)==(?: *⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->)?\s*$", O.MULTILINE)

# Matches level 3 headings
HeadingLevelThree = _R(
    r"^===([^=](?:.*?[^=])?)===(?: *⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->)?\s*$", O.MULTILINE
)

# Matches the whole of a level 2 section including heading and any subsections up to but not
# including the next level 2 section
SectionLevelTwo = _R(
    r"^==[^=][^\r\n]*?[^=]==.*?(?=^==[^=][^\r\n]*?[^=]==(\r\n?|\n)$)", O.MULTILINE | O.SINGLELINE
)

# Matches the first section of an article, if the article has sections, else the whole article
ZerothSection = _R(r"(^.+?(?===+)|^.+$)", O.SINGLELINE)

# Matches article text up to but not including first level 2 heading
ArticleToFirstLevelTwoHeading = _R(
    r"^.*?(?=[^=]==[^=][^\r\n]*?[^=]==(?: *⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->)?(\r\n?|\n))", O.SINGLELINE
)

# Matches text indented with a :
IndentedText = _R(r"^:.*", O.MULTILINE)

# Matches indented, bulleted or numbered text
BulletedText = _R(r"^[\*#: ].*", O.MULTILINE)

# Matches single line templates, NOT nested templates
Template = _R(r"{{[^{\n]*?}}")

# Matches the end of a template call including trailing whitespace
TemplateEnd = _R(r"( ?(?:\r\n ?)*) *}}$")

# Matches single and multiline templates, NOT nested templates
TemplateMultiline = _R(r"{{[^{]*?}}")

# Matches single and multiline templates, AND those with nested templates
NestedTemplates = _R(r"{{(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}}")

# Matches templates: group 1 matches the names of templates. Not for templates including the
# template namespace prefix
TemplateName = _R(r"{{\s*([^\|{}]+?)(?:\s*<!--.*?-->\s*)?\s*(?:\||}})")

# Matches start of links to all Wikimedia-supported protocols except http, https: ftp, mailto,
# irc, gopher, telnet, nntp, worldwind, news, svn
NonHTTPProtocols = _R(
    r"(?<=ftp|mailto|irc|gopher|telnet|nntp|worldwind|news|svn)://", O.IGNORE_CASE
)

# (Slowly) Matches external links to all Wikimedia-supported protocols http, https, ftp, mailto,
# irc, gopher, telnet, nntp, worldwind, news, svn, protocol-relative HTTP(S) Group 1 is the
# protocol name
ExternalLinks = _R(
    "(?:(https?|ftp|mailto|irc|gopher|telnet|nntp|worldwind|news|svn):)?//(?:[\\w\\._\\-~!/\\*\"'\\(\\):;@&=+$,\\\\\\?%#\\[\\]]+?(?=}})|[\\w\\._\\-~!/\\*\"'\\(\\):;@&=+$,\\\\\\?%#\\[\\]]*)|\\[(?:(https?|ftp|mailto|irc|gopher|telnet|nntp|worldwind|news|svn):)?//.*?\\]",
    O.IGNORE_CASE,
)

# Matches external links only to http, https protocols
ExternalLinksHTTPOnly = _R(
    "(https?)://(?:[\\w\\._\\-~!/\\*\"'\\(\\):;@&=+$,\\\\\\?%#\\[\\]]+?(?=}})|[\\w\\._\\-~!/\\*\"'\\(\\):;@&=+$,\\\\\\?%#\\[\\]]*)|(\\[https?)://.*?\\]",
    O.IGNORE_CASE,
)

# Matches external links only to http, https protocols. For performance, protocol is not part of
# match value
ExternalLinksHTTPOnlyQuick = _R(
    "(?<=https?)://(?:[\\w\\._\\-~!/\\*\"'\\(\\):;@&=+$,\\\\\\?%#\\[\\]]+?(?=}})|[\\w\\._\\-~!/\\*\"'\\(\\):;@&=+$,\\\\\\?%#\\[\\]]*)|(?<=\\[https?)://.*?\\]",
    O.IGNORE_CASE,
)

# Matches links that may be interwikis, i.e. containing colon, group 1 being the wiki language,
# group 2 being the link target, group 3 any comment after the link
PossibleInterwikis = _R(
    r"\[\[\s*([-a-zA-Z]{2,12})(?<!File|Image|Media|MOS)\s*:+\s*([^\]\[]*?)\s*\]\]( *<!--.*?-->)?",
    O.SINGLELINE,
)

# Matches unformatted text regions: nowiki, pre, math, chem, html comments, timelines
UnformattedText = _R(
    r"<nowiki>.*?</\s*nowiki>|<(pre|math|chem|timeline)\b.*?>.*?</\s*\1>|<!--.*?-->", O.SINGLELINE
)

# Matches &lt;blockquote> tags
Blockquote = _R(r"<\s*blockquote[^<>]*>(.*?)<\s*/\s*blockquote\s*>", O.IGNORE_CASE | O.SINGLELINE)

# Matches &lt;poem> tags
Poem = _R(r"<\s*poem[^<>]*>(.*?)<\s*/\s*poem\s*>", O.IGNORE_CASE | O.SINGLELINE)

# Matches &lt;imagemap&gt; tags
ImageMap = _R(r"<\s*imagemap\b[^<>]*>(.*?)<\s*/\s*imagemap\s*>", O.IGNORE_CASE | O.SINGLELINE)

# Matches all tags: &lt;nowiki>, &lt;pre>, &lt;math>, &lt;chem>,&lt;timeline>, &lt;code>,
# &lt;source>, &lt;cite>, &lt;syntaxhighlight>, &lt;blockquote>, &lt;poem>, &lt;imagemap>,
# &lt;includeonly>, &lt;onlyinclude>, &lt;noinclude>, &lt;hiero>, &lt;score>
AllTags = _R(
    r"<\s*(nowiki|pre|math|chem|timeline|code|source|cite|syntaxhighlight|blockquote|poem|imagemap|includeonly|onlyinclude|noinclude|hiero|score)[^<>]*>(?>(?!<\s*\1[^<>]*>|<\s*/\s*\1\b[^<>]*>).|<\s*\1[^<>]*>(?<Depth>)|<\s*/\s*\1\b[^<>]*>(?<-Depth>))*(?(Depth)(?!))<\s*/\s*\1\b[^<>]*>",
    O.SINGLELINE | O.IGNORE_CASE,
)

# Matches &lt;gallery&gt; tags, group 1 is any tag parameters, group 2 is the tag contents
GalleryTag = _R(r"< *gallery\b([^>]*?)>([\s\S]*?)</ *gallery *>", O.IGNORE_CASE)

# Matches three or more consecutive new lines
ThreeOrMoreNewlines = _R("(\r\n){3,}")

# Matches &lt;noinclude&gt; tags
Noinclude = _R(r"<\s*noinclude\s*>(.*?)<\s*/\s*noinclude\s*>", O.IGNORE_CASE | O.SINGLELINE)

# Matches &lt;includeonly&gt; and &lt;onlyinclude&gt; tags
Includeonly = _R(
    r"<\s*(includeonly|onlyinclude)\s*>.*?<\s*/\s*\1\s*>", O.IGNORE_CASE | O.SINGLELINE
)

# Matches &lt;includeonly&gt; and &lt;onlyinclude&gt; and &lt;noinclude&gt; tags
IncludeonlyNoinclude = _R(
    r"<\s*(includeonly|onlyinclude|noinclude)\s*>.*?<\s*/\s*\1\s*>", O.IGNORE_CASE | O.SINGLELINE
)

RFromModificationString = r"{{R from modification}}"

RFromModificationList = (
    r"R from alternative punctuation",
    r"R mod",
    r"R from modification",
    r"R from alternate punctuation",
)

RFromTitleWithoutDiacriticsString = r"{{R to diacritic}}"

RFromTitleWithoutDiacriticsList = (
    r"R to diacritic",
    r"R to accents",
    r"Redirects from title without diacritics",
    r"RDiacr",
    r"R to unicode name",
    r"R to unicode",
    r"R to title with diacritics",
    r"R from name without diacritics",
    r"R from original name without diacritics",
    r"R without diacritics",
    r"R diacritics",
    r"Redirect from title without diacritics",
    r"Redirect to Unicode",
    r"R to Unicode",
    r"Redirect without diacritics",
    r"R to Unicode name",
    r"Redirect to Unicode name",
    r"Redirect from name without diacritics",
    r"R from title without diacritics",
    r"R to diacritical marks",
    r"R to diacritical mark",
    r"R without accents",
    r"Redirect to diacritics",
    r"R to diacritics",
    r"Redirect to diacritic",
    r"R to accent",
    r"Redirects from titles without diacritics",
    r"R from name without diacritic",
    r"R without diacritic",
)

RFromOtherCapitalisationString = r"{{R from other capitalisation}}"

RFromOtherCapitaliastionList = (
    r"R cap",
    r"R for alternate capitalisation",
    r"R for alternate capitalization",
    r"R for alternative capitalisation",
    r"R for alternative capitalization",
    r"R from Capitalisation",
    r"R from Capitalization",
    r"R from alt cap",
    r"R from alt case",
    r"R from alternate capitalisation",
    r"R from alternate capitalization",
    r"R from alternative capitalisation",
    r"R from alternative capitalization",
    r"R from another capitalisation",
    r"R from another capitalization",
    r"R from cap",
    r"R from capitalisation",
    r"R from capitalization",
    r"R from caps",
    r"R from different capitalization ",
    r"R from lowercase",
    r"R from miscapitalization",
    r"R from other Capitalization",
    r"R from other capitalisation",
    r"R from other capitalization",
    r"R from other caps",
    r"R to Capitalization",
    r"R to alternate capitalisation",
    r"Redirect from capitalisation",
)

# Matches newline
Newline = _R(r"\n")

# Matches words, and allows words with apostrophes to be treated as one whole word
RegexWordApostrophes = _R(r"\w+(?:['’]\w+)?")

# Matches &lt;source&gt;&lt;/source&gt;, &lt;syntaxhighlight&gt;, &lt;code&gt;&lt;/code&gt;,
# &lt;tt&gt;&lt;/tt&gt; tags, group 1 is the tag contents
SourceCode = _R(
    r"<\s*(?<tag>source|syntaxhighlight|code|tt)(?:\s.*?|)>(.*?)<\s*/\s*\k<tag>\s*>",
    O.IGNORE_CASE | O.SINGLELINE,
)

# Matches math, pre, source, code, syntaxhighlight tags or comments
MathPreSourceCodeComments = _R(
    r'<pre>.*?</pre>|<!--.*?-->|<math(?: chem| *display *= *" *(?:inline|block) *" *)?>.*?</math>|<chem>.*?</chem>|'
    + str(SourceCode),
    O.IGNORE_CASE | O.SINGLELINE,
)

# Matches anything starting with Meanings of minor planet names
MeaningsOfMinorPlanetNames = _R(r"^Meanings of minor planet names", O.COMPILED)

# Matches general disambig templates (en-wiki only)
DisambigsGeneral = nested_template_regex((r"Disamb", r"Disambig", r"Disambiguation", r"Dab"))

# Matches disambig cleanup templates (en-wiki only)
DisambigsCleanup = nested_template_regex(
    (r"Disambig-cleanup", r"Disambig cleanup", r"Disambiguation cleanup")
)

# Matches Wiktionary redirect and Wikiquote redirect templates (en only)
Wi = nested_template_regex(
    (
        r"Wiktionary redirect",
        r"Wi",
        r"Widirect",
        r"Moved to Wiktionary",
        r"RedirecttoWiktionary",
        r"Seewiktionary",
        r"Wikiquote redirect",
        r"Wikivoyage redirect",
    )
)

# Matches Current events header in arwiki
CEHar = nested_template_regex((r"رأس الأحداث الجارية",))

# Matches templates with many wikilinks to avoid tagging the transcluding page as dead-end and/or
# stub (en only)
NonDeadEndPageTemplates = nested_template_regex(
    (
        r"Events by year for decade",
        r"Events by year for decade BC",
        r"SCOTUSRow",
        r"ATC codes lead",
        r"Portal:Current events/Month Inclusion",
        r"Ukrsrow",
        r"PBB",
    )
)

# Matches soft redirect templates - https://en.wikipedia.org/wiki/Category:Soft_redirect_templates
SoftRedirectTemplates = nested_template_regex(
    (
        r"Wikibooks redirect",
        r"Wikimedia Commons redirect",
        r"Wikinews redirect",
        r"Wikiquote redirect",
        r"Wikisource redirect",
        r"Wikispecies redirect",
        r"Wikivoyage redirect",
        r"Wiktionary redirect",
    )
)

# Matches quotations outside of templates but within a pair of quotation marks, notably exlcuding
# straight single quotes see https://en.wikipedia.org/wiki/Quotation_mark_glyphs https://en.wikipe
# dia.org/wiki/Wikipedia_talk:AutoWikiBrowser/Feature_requests#Ignoring_spelling_errors_within_quo
# tation_marks.3F
UntemplatedQuotes = _R(
    r'(?<=[^\w]|^)["«»‘’“”‛‟‹›“”„‘’`’“‘”].{1,2000}?["«»‘’“”‛‟‹›“”„‘’`’“‘”](?=[^\w])', O.SINGLELINE
)

# Matches common curly double quotes, see [[MOS:PUNCT]] - exludes low-high etc. as these are
# allowed in non-English text per MOS:QUOTEMARK
CurlyDoubleQuotes = _R(r"[‟″]")

# covered by TestFixNonBreakingSpaces Matches abbreviated SI units without a non-breaking space,
# notably does not correct millimetres without a space due to firearms articles using this
# convention https://en.wikipedia.org/wiki/Wikipedia_talk:AutoWikiBrowser/Feature_requests#Non_bre
# aking_spaces
UnitsWithoutNonBreakingSpaces = _R(
    r"(\b\d?\.?\d+)[\s\u00a0]*([cmknuµ][mgWN]|m?mol|cd|mi|lb[fs]?|b?hp|mph|ft|dB|[kGM]?Hz|m/s|°[CF])\b(?<!(\d?\.?\d+)mm)"
)

# covered by TestFixNonBreakingSpaces Matches "50m (170&amp;nbsp;ft)"
MetresFeetConversionNonBreakingSpaces = _R(
    r"(\d+(?:\.\d+)?)[\s\u00a0]?m(?= \(\d+(?:[\.,]\d+)?&nbsp;ft\.?\))"
)

# Matches abbreviated in, oz, feet when in brackets e.g. (3 in); avoids false positives such as "3
# in 4..."
ImperialUnitsInBracketsWithoutNonBreakingSpaces = _R(
    r"(\(\d+(?:\.\d+)?(?:\s*(?:-|–|&mdash;)[\s\u00a0]*\d+(?:\.\d+)?)?)[\s\u00a0]*((?:in|ft|oz)\))"
)

# Matches {{Not a typo}} template and redirects
NotATypo = nested_template_regex(
    (r"As written", r"Notatypo", r"Not a typo", r"Proper name", r"Typo")
)

# Matches the {{use dmy dates}} family of templates and redirects
UseDatesTemplate = nested_template_regex(
    (r"DMY", r"dmy", r"use dmy dates", r"MDY", r"mdy", r"use mdy dates", r"ISO", r"use ymd dates")
)

# strictly should accept year form 1583 Matches ISO 8601 format dates – YYYY-DD-MM – between 1600
# and 2099
ISODates = _R(r"\b(20\d\d|1[6-9]\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")

# Quickly matches ISO 8601 format dates – YYYY-DD-MM – between 1600 and 2099. For counting matches
ISODatesQuick = _R(r"(?<=\b(20\d\d|1[6-9]\d\d))-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")

# Matches the {{talk header}} templates and its redirects. Also matches to whitespace after
# template, but not newline before a heading following
TalkHeaderTemplate = _R(
    r"\{\{\s*(?:template *:)?\s*(talk[ _]?(page)?(header)?)\s*(?:\|[^{}]*)?\}\}(?:\s*?(?=\r\n==)|\s*)",
    O.IGNORE_CASE,
)

# Matches the {{skip to talk}} template and its redirects
SkipTOCTemplateRegex = _R(
    r"\{\{\s*(template *:)?\s*(skiptotoctalk|Skiptotoc|Skip to talk|skip to toc)\s*\}\}\s*",
    O.EXPLICIT_CAPTURE | O.IGNORE_CASE,
)

# Matches the {{WikiProject banner shell}} templates and its redirects
WikiProjectBannerShellTemplate = nested_template_regex(
    (
        r"WikiProject banner shell",
        r"WPBS",
        r"Wpbs",
        r"WPB",
        r"Wpb",
        r"WP banner shell",
        r"WP Banner Shell",
        r"WPBannerShell",
        r"WikiProject Banner Shell",
        r"WikiProjectBannerShell",
        r"Wikiprojectbannershell",
        r"WikiProject Banners",
        r"WikiProjectBanners",
        r"WPBannerShell",
        r"Bannershell",
        r"banner shell",
        r"Shell",
    )
)

# Matches {{no footnotes}} OR {{more footnotes}} templates
MoreNoFootnotes = nested_template_regex(
    (r"no footnotes", r"nofootnotes", r"more footnotes", r"morefootnotes", r"more footnotes needed")
)

# Matches the various {{BLP unsourced}} templates
BLPSources = _R(
    r"{{\s*([Bb](LP|lp) ?(sources|[Uu]n(sourced|ref(?:erenced)?))|[Uu]n(sourced|referenced) ?[Bb](LP|lp))\b"
)

ReferencesTemplates = r'(\{\{\s*(?:[Rr]ef(?:-?li(?:st|nk)|erence)|[Ll]istaref|[Ll]ist of botanists by author abbreviation footer|[Aa]irline codes page/bottom|[Ss]COTUS-justice-listframe|[Mm]inorPlanetNameMeaningsFooter00|[Mm]inorPlanetNameMeaningsFooter|[Mm]inorPlanetNameMeaningsFooter10k)(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))\}\}|<\s*[Rr]eferences\s*(?:responsive\s*(?:= *" *\d *" *)?)?/>|\{\{refs|<\s*references\s*(?:group *= *""\s*)?(?:responsive\s*(?:= *" *\d *" *)?)?>.*</\s*references\s*>)'

# Matches a closing &lt;/ref&gt; tag
ReferenceEnd = r"(?:</ref>)"

# Matches any of the recognised templates for displaying cite references e.g. {{reflist}},
# {{refs}}, &lt;references/&gt;
ReferencesTemplate = _R(ReferencesTemplates, O.SINGLELINE)

# Matches any of the recognised templates for displaying cite references followed by a &gt;ref&lt;
# reference
RefAfterReflist = _R(ReferencesTemplates + r".*?" + ReferenceEnd, O.IGNORE_CASE | O.SINGLELINE)

# Matches a line with a bare external link (no description or name of link)
BareExternalLink = _R(r"^ *\*? *(?:[Hh]ttps?|[Ff]tp|[Mm]ailto)://[^\ \n\r<>]+\s+$", O.MULTILINE)

# Matches a bare external link (URL only, no title) within a &lt;ref&gt; tag, group 1 being the
# URL
BareRefExternalLink = _R(
    r"<\s*ref\b[^<>]*>\s*(?<brace>\[+)?\s*((?:https?|ftp|mailto)://[^\ \n\r<>]+?)\s*(?(brace)\]+|)[\.,:;\s]*<\s*/\s*ref\s*>",
    O.IGNORE_CASE,
)

# (?<test>a)?b(?(test)c|d) Matches an external link (URL only, no title) within a &lt;ref&gt; tag
# with a bot generated title or no title, group 1 being the URL, group 2 being the title, if any
BareRefExternalLinkBotGenTitle = _R(
    r'<\s*ref\b[^<>]*>\s*\[*\s*((?:https?|ftp|mailto)://[^\ \n\r<>]+?)\s*(?:\s+([^<>{}]+?)\s*<!--\s*Bot generated title\s*-->)?\]*[\.,:;\s"]*<\s*/\s*ref\s*>',
    O.IGNORE_CASE,
)

# Matches the various citation templates {{citation}}, {{cite web}} etc. on en-wiki
CiteTemplate = nested_template_regex(
    (
        r"cite web",
        r"cite news",
        r"cite journal",
        r"cite book",
        r"citation",
        r"cite conference",
        r"cite hansard",
        r"cite manual",
        r"cite paper",
        r"cite press release",
        r"cite encyclopedia",
        r"cite AV media",
        r"vcite2 journal",
        r"cite magazine",
        r"cite report",
    )
)

# Matches the various url templates {{URL}} etc. on en-wiki
UrlTemplate = nested_template_regex((r"URL", r"Website", r"Url", r"Official website"))

# Matches the various Harvard citation templates on en-wiki
HarvTemplate = nested_template_regex(
    (
        r"Harvard citation",
        r"harv",
        r"harvsp",
        r"Harvard citation no brackets",
        r"harvnb",
        r"Harvard citation text",
        r"harvtxt",
        r"Harvcol",
        r"Harvcolnb",
        r"Harvcoltxt",
    )
)

# Matches the various sfn citation templates on en-wiki
SfnTemplate = nested_template_regex(
    (r"Sfn", r"Shortened footnote template", r"Shortened footnote", r"Sf", r"Snf", r"Hf", r"Sfnnb")
)

# Matches the various categories for dead people on en wiki, and the living people category
DeathsOrLivingCategory = _R(
    r"\[\[\s*Category *:[ _]?(\d{1,2}\w{0,2}[- _]century(?: BC)?[ _]deaths|[0-9s]{3,5}(?: BC)?[ _](deaths|suicides)|Missing[ _]people|Living[ _]people|(?:Date|Year)[ _]of[ _]death[ _](?:missing|unknown|uncertain)|Possibly[ _]living[ _]people|People[ _]declared[ _]dead[ _]in[ _]absentia) *(?:\|.*?)?\]\]",
    O.IGNORE_CASE | O.RIGHT_TO_LEFT,
)

# Matches the {{recentlydeceased}} templates and its redirects
LivingPeopleRegex2 = _R(r"\{\{\s*(Template:)?(Recent ?death|Recentlydeceased)\}\}", O.IGNORE_CASE)

# Matches the XXXX births / xxth Century / XXXX BC births categories (en only)
BirthsCategory = _R(
    r"\[\[ ?Category ?:[ _]?(?:(\d{3,4})(?:s| BC)?|\d{1,2}\w{0,2}[- _]century)[ _]births(\|.*?)?\]\]",
    O.IGNORE_CASE | O.RIGHT_TO_LEFT,
)

# Matches the "People from ..." en-wiki categories
PeopleFromCategory = _R(r"\[\[ ?Category ?: *People from .*?\]\]")

# Matches the various {{birth date and age}} templates, group 1 being the year of birth
DateBirthAndAge = _R(
    r"{{\s*[Bb](?:(?:da|irth ?date(?: and age)?)\s*(?:\|\s*[md]f\s*=\s*y(?:es)?\s*)?\|\s*|irth-date(?: and age)?\s*\|[^{}\|]*?)(?:year *= *)?\b([12]\d{3})\s*(?:\|[^{}]*}}|}})"
)

# Matches the various {{death date}} templates, group 1 being the year of death
DeathDate = _R(
    r"{{\s*[Dd]eath(?: date(?: and age)?\s*(?:\|\s*[md]f\s*=\s*y(?:es)?\s*)?\|\s*|-date\s*\|[^{}\|]*?)(?:year *= *)?\b([12]\d{3})\s*(?:\||}})"
)

# Matches the {{death date and age}} template, group 1 being the year of death, group 2 being the
# year of birth
DeathDateAndAge = _R(
    r"{{\s*[Dd](?:eath[ -]date and age|da)\s*\|(?:[^{}]*?\|)?\s*([12]\d{3})\s*\|[^{}]+?\|\s*([12]\d{3})\s*\|.*}}"
)

# Matches {{Centuryinbox}} template and its redirects
Centuryinbox = nested_template_regex((r"Centuryinbox",))

# Matches {{dead link}} template and its redirects
DeadLink = nested_template_regex(
    (
        r"dead link",
        r"deadlink",
        r"broken link",
        r"brokenlink",
        r"link broken",
        r"linkbroken",
        r"404",
        r"dl",
        r"dl-s",
        r"cleanup-link",
    )
)

# Matches wikilinks with no target e.g. [[|foo]]
_AllowedCharacters = "([\\w\\s\\-–\\+\\(\\),\\'\\.&\\!\\?\\$\\#\"]*)"

TargetLessLink = _R(r"\[\[\|" + _AllowedCharacters + r"\]\]")

# Matches wikilinks with double pipes e.g. [[text|text2|text3]] and [[text||text3]]
DoublePipeLink = _R(
    r"\[\[" + _AllowedCharacters + r"\|" + _AllowedCharacters + r"\|" + _AllowedCharacters + r"\]\]"
)

# Mathes the {{circa}} template and [[circa]] links
CircaLinkTemplate = _R(r"({{[Cc]irca}}|\[\[[Cc]irca *(?:\|[Cc]a?\.?)?\]\]|\[\[[Cc]a?\.?\]*\.?)")

UnlinkedFloruit = _R(r"\(\s*(?:[Ff]l)\.*\s*(\d\d)")

# Matches the {{Cat improve}} template and its redirects
CatImprove = nested_template_regex(
    (
        r"CI",
        r"Cleanup-cat",
        r"Cleanup cat",
        r"Few categories",
        r"Few cats",
        r"Fewcategories",
        r"Fewcats",
        r"Improve-categories",
        r"Improve-cats",
        r"Improve categories",
        r"Improve cats",
        r"Improvecategories",
        r"Improvecats",
        r"More categories",
        r"More category",
        r"Morecat",
        r"Morecategories",
        r"Morecats",
        r"Cat-improve",
        r"Category-improve",
        r"Categories-improve",
        r"Category improve",
        r"Categories improve",
        r"Catimprove",
        r"More cats",
    )
)

# Matches the {{Multiple issues}} template
MultipleIssues = nested_template_regex(_MultipleIssuesList)

# Matches the {{New unreviewed article}} template
NewUnReviewedArticle = nested_template_regex(r"new unreviewed article")

# The cleanup templates that can be moved into the {{multiple issues}} template (see
# Wikipedia:Template_messages/Cleanup)
MaintanceTemplatesString = r"([Aa]bbreviations|[Aa]dvert|[Aa]utobiography|[Bb]iased|[Bb]lpdispute|BLPrefimprove|BLP IMDB refimprove|BLP ?sources|BLPunref(?:erenced)?|BLP ?unsourced|[Cc]itations missing|[Cc]itation ?style|[Cc]ite ?check|[Cc]leanup|[Cc]leanup-laundry|[Cc]leanup-link rot|[Cc]leanup-reorgani[sz]e|[Cc]leanup-spam|COI|[Cc]oi|[Cc]olloquial|[Cc]onfusing|[Cc]ontext|[Cc]ontradict|[Cc]opy ?edit|[Cc]riticisms|[Cc]riticism section|[Cc]rystal|[Dd]ead ?end|[Dd]isputed|[Dd]o-attempt|[Ee]ssay(?:\-like)?|[Ee]xample ?farm|[Ee]xpand|[Ee]xpert|[Ee]xpert-subject|[Ee]xternal links|[Ff]ancruft|[Ff]anpov|[Ff]ansite|[Ff]iction|[Gg]ame ?guide|[Gg]lobalize|[Gg]rammar|[Hh]istinfo|[Hh]oax|[Hh]owto|[Ii]nappropriate person|[Ii]n-universe|[Ii]ncomplete|[Ii]ntro(?: length|\-too(?:long|short))|[Ii]ntromissing|[Ii]ntrorewrite|[Cc]leanup-jargon|[Ll]aundry(?:lists)?|[Ll]ead (?:missing|rewrite|too long|too short)|[Ll]ike ?resume|(?:[Vv]ery ?l|[Ll])ong|[Mm]ore footnotes|[Mm]ore citations needed|[Nn]ews ?release|[Nn]o footnotes|[Nn]otab(?:le|ility)|[Oo]ne ?source|[Oo]riginal[ -][Rr]esearch|[Oo]rphan|[Oo]ut of date|[Oo]verly detailed|[Oo]ver-quotation|[Pp]eacock|[Pp]lot|N?POV|n?pov|[Pp]ov\-check|POV-check|[Pp]rimary ?sources|[Pp]rose(?:line)?|[Qq]uotefarm|[Rr]ecent(?:ism)?|[Rr]efimprove(?:BLP)?|[Rr]estructure|[Rr]eview|(?:[Cc]leanup\-r|[Rr])ewrite|[Ss]ections|[Ss]elf-published|[Ss]pam|[Ss]tory|[Ss]ynthesis|[Tt]echnical|[Ii]nappropriate tone|[Tt]one|[Tt]oo(?:short|long)|[Tt]ravel ?guide|[Tt]rivia|[Uu]nbalanced|[Uu]nderlinked|[Uu]nencyclopedic|[Uu]nref(?:erenced(?:BLP)?|BLP)?|[Uu]nreliable sources|[Uu]pdate|[Ww]easel|[Ww]ikify|COI|POV)"

_BotsNoBotsList = (r"bots", r"nobots")

# Matches {{bots}} and {{nobots}} templates
BotsNoBots = nested_template_regex(_BotsNoBotsList)

_MultipleIssuesArticleMaintenanceTemplatesList: tuple[str, ...] = (
    r"Abbreviations",
    r"Academic booster",
    r"Accessibility dispute",
    r"AI-generated",
    r"All plot",
    r"Alumni",
    r"Anachronism",
    r"Autobiography",
    r"Being translated",
    r"Better sources needed",
    r"Biblio",
    r"Blacklisted-links",
    r"BLP IMDb-only refimprove",
    r"BLP IMDb refimprove",
    r"BLP more footnotes needed",
    r"BLP no footnotes",
    r"BLP one source",
    r"BLP primary sources",
    r"BLP self-published",
    r"BLP sources",
    r"BLP unreferenced",
    r"Broaden",
    r"Buzzword",
    r"Catholic cleanup",
    r"Cherry-picked",
    r"Chinese script needed",
    r"Circular",
    r"Citations broken",
    r"Citation style",
    r"Citations broken",
    r"Cite check",
    r"Cleanup",
    r"Cleanup AfD",
    r"Cleanup bare URLs",
    r"Cleanup biography",
    r"Cleanup book",
    r"Cleanup colors",
    r"Cleanup Congress bio",
    r"Cleanup film",
    r"Cleanup gallery",
    r"Cleanup higher education",
    r"Cleanup HTML",
    r"Cleanup ICHD",
    r"Cleanup image captions",
    r"Cleanup images",
    r"Cleanup infobox",
    r"Cleanup lang",
    r"Cleanup list",
    r"Cleanup merge",
    r"Cleanup MOS",
    r"Cleanup press release",
    r"Cleanup red links",
    r"Cleanup reorganize",
    r"Cleanup rewrite",
    r"Cleanup school",
    r"Cleanup split",
    r"Cleanup tense",
    r"Cleanup translation",
    r"Cleanup weighted",
    r"Close paraphrasing",
    r"Coatrack",
    r"COI",
    r"Colloquial",
    r"Confusing",
    r"Content",
    r"Context",
    r"Contradicts other",
    r"Contradicts others",
    r"Convert to Episode table",
    r"Copy edit",
    r"Copy to Wikibooks",
    r"Copy to Wikiquote",
    r"Copy to Wikisource",
    r"Copy to Wikiversity",
    r"Copy to Wikivoyage",
    r"Copypaste",
    r"Create list",
    r"Criticism section",
    r"Current",
    r"Current election",
    r"Current person",
    r"Current related",
    r"Current spaceflight",
    r"Current sport",
    r"Current weather event",
    r"Dablinks",
    r"Dead end",
    r"Deprecated archival service",
    r"Dicdef",
    r"Directory",
    r"Dispute about",
    r"Disputed",
    r"Disputed category",
    r"Disputed chem",
    r"Disputed list",
    r"Disputed map",
    r"Duplicated citations",
    r"Duplication",
    r"EBD POV",
    r"Essay",
    r"Essay-like",
    r"Excessive citations",
    r"Excessive examples",
    r"Exit list",
    r"Expert needed",
    r"External links",
    r"Famous",
    r"Fan POV",
    r"Fiction",
    r"Fiction trivia",
    r"Format footnotes",
    r"Fringe theories",
    r"Full citations needed",
    r"Further reading cleanup",
    r"Game guide",
    r"Generalize",
    r"Geographic imbalance",
    r"Globalize",
    r"Hoax",
    r"Hook",
    r"How-to",
    r"Improve images",
    r"Inappropriate person",
    r"Incoming links",
    r"incomplete disambiguation",
    r"Incomplete list",
    r"Inc-personnel",
    r"Inc-results",
    r"Independent sources",
    r"In popular culture",
    r"In-universe",
    r"Infobox too large",
    r"Lacking ISBN",
    r"Lacking overview",
    r"Lead extra info",
    r"Lead missing",
    r"Lead rewrite",
    r"Lead too long",
    r"Lead too short",
    r"List missing criteria",
    r"list scope",
    r"List to table",
    r"List years",
    r"Localist",
    r"Long plot",
    r"Media IMDb refimprove",
    r"Merge",
    r"Merge from",
    r"Merge portions from",
    r"Merge to",
    r"Merging from",
    r"Missing information",
    r"Missing taxobox",
    r"More citations needed",
    r"More footnotes needed",
    r"More medical citations needed",
    r"More plot",
    r"More science citations needed",
    r"Mycomorphbox missing",
    r"Needs table",
    r"Neologism",
    r"New name",
    r"No footnotes",
    r"No plot",
    r"No reliable sources",
    r"No significant coverage",
    r"No significant coverage (sports)",
    r"Non-free",
    r"Notability",
    r"Not English",
    r"NPOV language",
    r"NRIS only",
    r"Obituary",
    r"Off topic",
    r"Old news",
    r"One other topic",
    r"One source",
    r"Only primary sources",
    r"Original research",
    r"Orphan",
    r"Outdated as of",
    r"Overlinked",
    r"Overly detailed",
    r"Over-quotation",
    r"Page numbers improve",
    r"Page numbers needed",
    r"Paid contributions",
    r"Parenthetical referencing",
    r"Peacock",
    r"POV",
    r"POV lead",
    r"POV map",
    r"Political POV",
    r"Primary sources",
    r"Pro and con list",
    r"Proofreader needed",
    r"Promotional",
    r"Prose",
    r"Recategorize",
    r"Recent birth",
    r"Recent death",
    r"Recentism",
    r"Recently revised",
    r"Religious text primary",
    r"Renamed",
    r"Renamed from",
    r"Research paper",
    r"Resume-like",
    r"Review",
    r"Rough translation",
    r"Science review",
    r"Section move from",
    r"Sections",
    r"Self-contradictory",
    r"Self-published",
    r"Self-reference cleanup",
    r"Self-sourcing examples",
    r"Shallow references",
    r"Sources exist",
    r"Spam references",
    r"Spam-request",
    r"Specific",
    r"Speculation",
    r"Split",
    r"Split portions",
    r"Story",
    r"Subsections",
    r"Summary style",
    r"Synthesis",
    r"Technical",
    r"Term paper",
    r"Text-source",
    r"Textbook",
    r"Time-context",
    r"Title change",
    r"Tone",
    r"Too few opinions",
    r"Too many charts",
    r"Too many photos",
    r"Too many list sections",
    r"Too many sections",
    r"Translated page",
    r"Travel guide",
    r"Trivia",
    r"Unbalanced",
    r"Unclear date",
    r"Under construction",
    r"Underlinked",
    r"Undisclosed paid",
    r"Undue weight",
    r"Unfocused",
    r"Units attention",
    r"Unreferenced",
    r"Unreferenced category",
    r"Unreferenced law",
    r"Unreliable sources",
    r"Unsorted list",
    r"Update",
    r"Update-EB",
    r"Upscaled images",
    r"USgovtPOV",
    r"User-generated",
    r"Verifiability",
    r"Verify sources",
    r"Very long",
    r"Weasel",
    r"Wikify",
    r"You",
    r"Expand Afrikaans",
    r"Expand Albanian",
    r"Expand Amharic",
    r"Expand Arabic",
    r"Expand Aragonese",
    r"Expand Armenian",
    r"Expand Assamese",
    r"Expand Asturian",
    r"Expand Azerbaijani",
    r"Expand Basque",
    r"Expand Bavarian",
    r"Expand Belarusian",
    r"Expand Belarusian (Taraškievica orthography)",
    r"Expand Bengali",
    r"Expand Bishnupriya Manipuri",
    r"Expand Bosnian",
    r"Expand Breton",
    r"Expand Bulgarian",
    r"Expand Burmese",
    r"Expand Cantonese",
    r"Expand Catalan",
    r"Expand Cebuano",
    r"Expand Central Bikol",
    r"Expand Central Kurdish",
    r"Expand Chewa",
    r"Expand Chinese",
    r"Expand Colognian",
    r"Expand Corsican",
    r"Expand Crimean Tatar",
    r"Expand Croatian",
    r"Expand Czech",
    r"Expand Danish",
    r"Expand Dutch",
    r"Expand Dutch Low Saxon",
    r"Expand Egyptian Arabic",
    r"Expand Emiliano-Romagnolo",
    r"Expand Esperanto",
    r"Expand Estonian",
    r"Expand Ewe",
    r"Expand Faroese",
    r"Expand Finnish",
    r"Expand French",
    r"Expand Friulian",
    r"Expand Galician",
    r"Expand Georgian",
    r"Expand German",
    r"Expand Greek",
    r"Expand Gujarati",
    r"Expand Haitian Creole",
    r"Expand Hausa",
    r"Expand Hawaiian",
    r"Expand Hebrew",
    r"Expand Hindi",
    r"Expand Hungarian",
    r"Expand Icelandic",
    r"Expand Ido",
    r"Expand Igbo",
    r"Expand Indonesian",
    r"Expand Irish",
    r"Expand Italian",
    r"Expand Japanese",
    r"Expand Javanese",
    r"Expand Kannada",
    r"Expand Kazakh",
    r"Expand Khmer",
    r"Expand Korean",
    r"Expand Kurdish",
    r"Expand Kyrgyz",
    r"Expand language",
    r"Expand Lao",
    r"Expand Latin",
    r"Expand Latvian",
    r"Expand Lezgian",
    r"Expand Limburgish",
    r"Expand Lithuanian",
    r"Expand Lojban",
    r"Expand Lombard",
    r"Expand Luxembourgish",
    r"Expand Macedonian",
    r"Expand Malagasy",
    r"Expand Malay",
    r"Expand Malayalam",
    r"Expand Maltese",
    r"Expand Maori",
    r"Expand Marathi",
    r"Expand Minangkabau",
    r"Expand Mingrelian",
    r"Expand Mongolian",
    r"Expand Neapolitan",
    r"Expand Nepali",
    r"Expand North Frisian",
    r"Expand Norwegian",
    r"Expand Norwegian (Nynorsk)",
    r"Expand Odia",
    r"Expand Ossetian",
    r"Expand Papiamento",
    r"Expand Pashto",
    r"Expand Persian",
    r"Expand Polish",
    r"Expand Portuguese",
    r"Expand Punjabi Gurmukhi",
    r"Expand Quechua",
    r"Expand Romanian",
    r"Expand Russian",
    r"Expand Samoan",
    r"Expand Samogitian",
    r"Expand Sanskrit",
    r"Expand Sardinian",
    r"Expand Saterland Frisian",
    r"Expand Scots",
    r"Expand Scottish Gaelic",
    r"Expand Serbian",
    r"Expand Serbo-Croatian",
    r"Expand Shona",
    r"Expand Sicilian",
    r"Expand Sindhi",
    r"Expand Sinhala",
    r"Expand Slovak",
    r"Expand Slovene",
    r"Expand Somali",
    r"Expand Sotho",
    r"Expand Spanish",
    r"Expand Sundanese",
    r"Expand Swahili",
    r"Expand Swedish",
    r"Expand Tagalog",
    r"Expand Tajik",
    r"Expand Tamil",
    r"Expand Tatar",
    r"Expand Telugu",
    r"Expand Testlish",
    r"Expand Thai",
    r"Expand Tibetan",
    r"Expand Tongan",
    r"Expand Tswana",
    r"Expand Turkish",
    r"Expand Ukrainian",
    r"Expand Urdu",
    r"Expand Uzbek",
    r"Expand Vietnamese",
    r"Expand Volapük",
    r"Expand Võro",
    r"Expand Walloon",
    r"Expand Waray",
    r"Expand warning",
    r"Expand Welsh",
    r"Expand Western Frisian",
    r"Expand West Flemish",
    r"Expand Xhosa",
    r"Expand Yiddish",
    r"Expand Yoruba",
    r"Expand Zulu",
)

# Maintenance templates, sorted per MOS:ORDER level 6, but not to be included in {{Multiple
# issues}} - no visible rendering on page
_OtherArticleMaintenanceTemplatesList = (
    r"Alt text missing",
    r"Alternative text missing",
    r"cbtalkonly",
)

# Matches the cleanup templates that can be moved into the {{multiple issues}} article-level
# template
MultipleIssuesArticleMaintenanceTemplates = nested_template_regex(
    _MultipleIssuesArticleMaintenanceTemplatesList
)

# Matches the cleanup templates that can be moved into the {{multiple issues}} section-level
# template
MultipleIssuesSectionMaintenanceTemplates = nested_template_regex(
    (
        r"BLP sources section",
        r"BLP unsourced section",
        r"BLP unreferenced section",
        r"Cleanup section",
        r"Confusing section",
        r"Copy edit-section",
        r"Criticism section",
        r"Disputed-section",
        r"Expand section",
        r"Importance-section",
        r"POV-section",
        r"Refimprove section",
        r"More citations needed section",
        r"Rewrite section",
        r"Unreferenced section",
        r"Update section",
        r"Wikify section",
    )
)

MosLevel6MaintenanceCleanupDispute = nested_template_regex(
    _union(
        _union(
            _union(
                _union(_MultipleIssuesArticleMaintenanceTemplatesList, _InUseList), _BotsNoBotsList
            ),
            _MultipleIssuesList,
        ),
        _OtherArticleMaintenanceTemplatesList,
    )
)

# Matches language maintenance templates from Category:Language maintenance templates and
# Category:Script_talk_header_templates
LanguageMaintenanceTemplates = nested_template_regex(
    (
        r"Arabic script needed",
        r"Armenian script needed",
        r"Bengali script needed",
        r"Berber script needed",
        r"Burmese script needed",
        r"Cherokee script needed",
        r"Chinese script needed",
        r"Chinese script needed inline span",
        r"Contains special characters",
        r"Cyrillic script needed",
        r"Devanagari script needed",
        r"Egyptian hieroglyphic script needed",
        r"Ge'ez script needed",
        r"Georgian script needed",
        r"Greek script needed",
        r"Hebrew script needed",
        r"Hiragana script needed",
        r"IPA-ga notice",
        r"Japanese script needed",
        r"Key needed",
        r"Khmer script needed",
        r"Korean script needed",
        r"Lao script needed",
        r"Meitei script needed",
        r"Needchunom",
        r"Needhanja",
        r"Needkanji",
        r"Needs IPA",
        r"Nepali script needed",
        r"Persian script needed",
        r"Romanization needed",
        r"Samoan script needed",
        r"Script needed",
        r"Syriac script needed",
        r"Tamil script needed",
        r"Thai script needed",
        r"Tibetan script needed",
        r"Tok Pisin script needed",
        r"Verify spelling",
        r"Vietnamese script needed",
        r"Yiddish script needed",
    )
)

# Matches infoboxes, including chembox, group 1 being the template name of the infobox Avoids
# matching "cleanup infobox" maintenance template
InfoBox = _R(
    r"(?:{{[\s_]*)(?::?[\s_]*(?:(?i:Template)\s*|[Mm]sg)[\s_]*:[\s_]*\s*)?((?:[Ii]nfo|[Cc]hem)box(?:[\s_]+[^{}\|\s][^{}\|]+?)?|[^{}\|]+?(?<!([Cc]leanup|Incomplete)[- ]*)[Ii]nfobox)([\s_]*(?:<!--[^>]*?-->\s*|⌊⌊⌊⌊M?\d+⌋⌋⌋⌋\s*)?(\|((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))))?\}\})"
)

# Matches {{DISPLAYTITLE}}, {{Lowercase title}}, {{Italic title}} and their redirects
# "Miscapitalization", ""Lowercase-user", ""Techlim", ""User lowercase", ""Lower case",
# ""Lowercase", ""Lower case title", ""Lower-case title", ""Lowercasetitle", ""Smalltitle",
# ""Uncapitalized title", ""Uncapitalised title", ""Redirect lowercase title", ""Redirect
# Lowercase title", ""Lot"
DisplayLowerCaseItalicTitle = _R(
    r"{{ *([Dd]ISPLAYTITLE||[Dd]isplay[ -]?title) *:[^{}]+}}|"
    + str(
        nested_template_regex(
            (
                r"Lowercase title",
                r"Miscapitalization",
                r"Lowercase-user",
                r"Techlim",
                r"User lowercase",
                r"Lower case",
                r"Lowercase",
                r"Lower case title",
                r"Lower-case title",
                r"Lowercasetitle",
                r"Smalltitle",
                r"Uncapitalized title",
                r"Uncapitalised title",
                r"Redirect lowercase title",
                r"Redirect Lowercase title",
                r"Lot",
                r"Italic title",
                r"Ital",
                r"Italictitle",
                r"Italicizetitle",
                r"Italicstitle",
                r"Italic title infobox",
                r"Italics title",
                r"Italics",
                r"Italic",
                r"ITALICTITLE",
                r"Italicize title",
                r"Title italic",
                r"Italicizedtitle",
                r"Italicized title",
                r"Italicised title",
                r"Italicisedtitle",
                r"Redirect italic title",
                r"Italtitle",
                r"Title language",
                r"italic disambiguation",
                r"italic title prefixed",
            )
        )
    )
)

# Matches people infoxboxes from [[Category:People infobox templates]]
PeopleInfoboxTemplates = nested_template_regex(
    (
        r"Figure skating infobox medals",
        r"Infobox AFL biography",
        r"Infobox AM",
        r"Infobox Ambassador",
        r"Infobox American Indian chief",
        r"Infobox British Touring Car Championship record",
        r"Infobox Calvinist theologian",
        r"Infobox Canadian Football League biography",
        r"Infobox Canadian MP",
        r"Infobox Canadian senator",
        r"Infobox CanadianMP",
        r"Infobox CanadianSenator",
        r"Infobox Champ Car driver",
        r"Infobox Chancellor",
        r"Infobox Chief Executive",
        r"Infobox Chief Justice",
        r"Infobox Christian leader",
        r"Infobox Congressional Candidate",
        r"Infobox Congressman",
        r"Infobox Congresswoman",
        r"Infobox Defense Minister",
        r"Infobox Deputy First Minister",
        r"Infobox Deputy Prime Minister",
        r"Infobox Doge",
        r"Infobox Dutch royalty styles",
        r"Infobox Eritrea Cabinet official",
        r"Infobox Eritrea cabinet official",
        r"Infobox F1 driver",
        r"Infobox FBI Ten Most Wanted",
        r"Infobox First Lady",
        r"Infobox First Minister",
        r"Infobox French royalty styles",
        r"Infobox Gaelic games manager",
        r"Infobox Gaelic games player",
        r"Infobox General Secretary",
        r"Infobox Governor",
        r"Infobox Governor General",
        r"Infobox Governor-Elect",
        r"Infobox Governor-General",
        r"Infobox Governor-elect",
        r"Infobox Indian government official",
        r"Infobox Indian politician",
        r"Infobox Instagram personality",
        r"Infobox Jewish leader",
        r"Infobox Judge",
        r"Infobox LDSGA",
        r"Infobox Le Mans driver",
        r"Infobox Lt Governor",
        r"Infobox MEP",
        r"Infobox MLA",
        r"Infobox MLB player",
        r"Infobox MP",
        r"Infobox MSP",
        r"Infobox Magic: The Gathering player",
        r"Infobox Mayor",
        r"Infobox Member of Parliament",
        r"Infobox Minister",
        r"Infobox Motocross rider",
        r"Infobox Muslim scholar",
        r"Infobox NASCAR driver",
        r"Infobox NCAA athlete",
        r"Infobox NFL player",
        r"Infobox Native American leader",
        r"Infobox New York State Senator",
        r"Infobox Officeholder",
        r"Infobox OntarioMPP",
        r"Infobox PM",
        r"Infobox Playboy Cyber Girl",
        r"Infobox Playboy Playmate",
        r"Infobox Politician",
        r"Infobox Politician (general)",
        r"Infobox Portuguese royalty styles",
        r"Infobox Premier",
        r"Infobox President",
        r"Infobox President-elect",
        r"Infobox Prime Minister",
        r"Infobox Prime Minister-elect",
        r"Infobox QuebecMNA",
        r"Infobox Representative Elect",
        r"Infobox Representative-elect",
        r"Infobox Rugby Union biography",
        r"Infobox SCC Chief Justice",
        r"Infobox SCC Puisne Justice",
        r"Infobox SCC chief justice",
        r"Infobox SCC puisne justice",
        r"Infobox Secretary-General",
        r"Infobox Senator",
        r"Infobox Senator-Elect",
        r"Infobox Senator-elect",
        r"Infobox Spanish royalty styles",
        r"Infobox Speaker",
        r"Infobox State Representative",
        r"Infobox State SC Associate Justice",
        r"Infobox State SC Justice",
        r"Infobox State Senator",
        r"Infobox TikTok personality",
        r"Infobox Twitch streamer",
        r"Infobox US Ambassador",
        r"Infobox US Associate Justice",
        r"Infobox US Cabinet official",
        r"Infobox US Chief Justice",
        r"Infobox US Territorial Governor",
        r"Infobox US ambassador",
        r"Infobox US associate justice",
        r"Infobox US cabinet official",
        r"Infobox US chief justice",
        r"Infobox US territorial governor",
        r"Infobox Uruguayan politician",
        r"Infobox V8 Supercar record",
        r"Infobox Vice President",
        r"Infobox WRC driver",
        r"Infobox War on Terror detainee",
        r"Infobox Welsh Assembly member",
        r"Infobox YouTube personality",
        r"Infobox academic",
        r"Infobox actor",
        r"Infobox adult biography",
        r"Infobox adult female",
        r"Infobox adult male",
        r"Infobox alpine ski racer",
        r"Infobox amateur wrestler",
        r"Infobox ambassador",
        r"Infobox archbishop styles",
        r"Infobox architect",
        r"Infobox art historian",
        r"Infobox artist",
        r"Infobox artist discography",
        r"Infobox artist list",
        r"Infobox astronaut",
        r"Infobox aviator",
        r"Infobox badminton player",
        r"Infobox bandy biography",
        r"Infobox basketball biography",
        r"Infobox basketball official",
        r"Infobox biathlete",
        r"Infobox bishop",
        r"Infobox bishop styles",
        r"Infobox bodybuilder",
        r"Infobox boxer",
        r"Infobox boxer (amateur)",
        r"Infobox bullfighting career",
        r"Infobox candidate",
        r"Infobox cardinal",
        r"Infobox cardinal styles",
        r"Infobox chancellor",
        r"Infobox checkers biography",
        r"Infobox chef",
        r"Infobox chess player",
        r"Infobox choir",
        r"Infobox civil servant",
        r"Infobox clan",
        r"Infobox classical composer",
        r"Infobox clergy",
        r"Infobox climber",
        r"Infobox college coach",
        r"Infobox college football player",
        r"Infobox comedian",
        r"Infobox comics creator",
        r"Infobox congressional candidate",
        r"Infobox congressman",
        r"Infobox consort styles",
        r"Infobox cricketer",
        r"Infobox criminal",
        r"Infobox culinary career",
        r"Infobox curler",
        r"Infobox cyclist",
        r"Infobox dancer",
        r"Infobox darts player",
        r"Infobox defense minister",
        r"Infobox deputy first minister",
        r"Infobox deputy prime minister",
        r"Infobox disc golfer",
        r"Infobox doge",
        r"Infobox economist",
        r"Infobox engineer",
        r"Infobox engineering career",
        r"Infobox equestrian",
        r"Infobox family",
        r"Infobox fashion designer",
        r"Infobox fencer",
        r"Infobox field hockey player",
        r"Infobox figure skater",
        r"Infobox first lady",
        r"Infobox first minister",
        r"Infobox football biography",
        r"Infobox football official",
        r"Infobox go player",
        r"Infobox golfer",
        r"Infobox governor",
        r"Infobox governor general",
        r"Infobox governor-elect",
        r"Infobox governor-general",
        r"Infobox gridiron football person",
        r"Infobox gymnast",
        r"Infobox handball biography",
        r"Infobox hereditary title",
        r"Infobox horseracing personality",
        r"Infobox ice hockey player",
        r"Infobox imam",
        r"Infobox journalist",
        r"Infobox judge",
        r"Infobox judoka",
        r"Infobox lacrosse player",
        r"Infobox lt governor",
        r"Infobox male model",
        r"Infobox manner of address",
        r"Infobox martial artist",
        r"Infobox martyrs",
        r"Infobox mass murderer",
        r"Infobox mayor",
        r"Infobox medical details",
        r"Infobox medical person",
        r"Infobox member of the Knesset",
        r"Infobox military person",
        r"Infobox minister",
        r"Infobox minister of religion",
        r"Infobox model",
        r"Infobox monarchy",
        r"Infobox motorcycle rider",
        r"Infobox mountaineer",
        r"Infobox murderer",
        r"Infobox musical artist",
        r"Infobox netball biography",
        r"Infobox nobility",
        r"Infobox noble",
        r"Infobox officeholder",
        r"Infobox pageant titleholder",
        r"Infobox pelotari",
        r"Infobox performer",
        r"Infobox person",
        r"Infobox pharaoh",
        r"Infobox philosopher",
        r"Infobox pirate",
        r"Infobox poker player",
        r"Infobox police officer",
        r"Infobox politician",
        r"Infobox politician (general)",
        r"Infobox pool player",
        r"Infobox pope",
        r"Infobox pope styles",
        r"Infobox premier",
        r"Infobox presenter",
        r"Infobox president",
        r"Infobox president styles",
        r"Infobox president-elect",
        r"Infobox pretender",
        r"Infobox prime minister",
        r"Infobox prime minister-elect",
        r"Infobox pro football player",
        r"Infobox producer discography",
        r"Infobox professional bowler",
        r"Infobox professional wrestler",
        r"Infobox racing driver",
        r"Infobox racing driver series section",
        r"Infobox rebbe",
        r"Infobox religious biography",
        r"Infobox representative-elect",
        r"Infobox royal styles",
        r"Infobox royalty",
        r"Infobox rugby biography",
        r"Infobox rugby league biography",
        r"Infobox rugby union biography",
        r"Infobox sailor",
        r"Infobox saint",
        r"Infobox scientist",
        r"Infobox secretary-general",
        r"Infobox senator",
        r"Infobox senator-elect",
        r"Infobox serial killer",
        r"Infobox skier",
        r"Infobox snooker player",
        r"Infobox speaker",
        r"Infobox speed skater",
        r"Infobox speedway rider",
        r"Infobox sport wrestler",
        r"Infobox sports announcer",
        r"Infobox sports announcer details",
        r"Infobox sportsperson",
        r"Infobox spy",
        r"Infobox squash player",
        r"Infobox state SC associate justice",
        r"Infobox state SC justice",
        r"Infobox state representative",
        r"Infobox state senator",
        r"Infobox sumo wrestler",
        r"Infobox surfer",
        r"Infobox swimmer",
        r"Infobox table tennis player",
        r"Infobox tennis biography",
        r"Infobox tennis player season",
        r"Infobox theologian",
        r"Infobox theological work",
        r"Infobox tribe",
        r"Infobox university chancellor",
        r"Infobox vandal",
        r"Infobox vice president",
        r"Infobox viceroy styles",
        r"Infobox video game player",
        r"Infobox volleyball biography",
        r"Infobox water polo biography",
        r"Infobox writer",
        r"Ordination",
    )
)

# Matches the {{circa}} template
CircaTemplate = nested_template_regex((r"Circa", r"c."))

# Matches full named references in format &lt;ref name="foo"&gt;text&lt;/ref&gt; Ref name is group
# 2, ref value is group 3
NamedReferences = _R(
    "(<\\s*ref\\s+name\\s*=\\s*(?:\"|')?([^<>=\\r\\n/]+?)(?:\"|')?\\s*>\\s*(.*?)\\s*<\\s*/\\s*ref\\s*>)",
    O.SINGLELINE | O.IGNORE_CASE,
)

# Matches named references in format &lt;ref name="foo"&gt;text&lt;/ref&gt; or &lt;ref name="foo"
# /&gt; Ref name is group 2, ref value is group 3
NamedReferencesIncludingCondensed = _R(
    "(<\\s*ref\\s+(?i)name(?-i)\\s*=\\s*(?:\"|')?([^<>=\\r\\n]+?)(?:\"|')?\\s*(?:>\\s*(.*?)\\s*<\\s*/\\s*ref|/)\\s*>)",
    O.SINGLELINE,
)

# Matches unnamed references in format &lt;ref&gt;...&lt;/ref&gt; group 1 being the reference text
UnnamedReferences = _R(
    r"<\s*ref\s*>((?>.(?<!<\s*ref\s*>|<\s*/\s*ref\s*>)|<\s*ref\s*>(?<DEPTH>)|<\s*/\s*ref\s*>(?<-DEPTH>))*(?(DEPTH)(?!)))<\s*/\s*ref\s*>",
    O.SINGLELINE,
)

# Matches dablinks, including hatnotes for names from
# https://en.wikipedia.org/wiki/Category:Hatnote_templates_for_names
DablinksList = (
    r"about",
    r"about-distinguish",
    r"about-distinguish-text",
    r"about other people",
    r"about year",
    r"broader",
    r"confused journal",
    r"correct title",
    r"distinguish",
    r"for",
    r"for introduction",
    r"for LMST",
    r"for-multi",
    r"for outline",
    r"for timeline",
    r"for-text",
    r"further",
    r"further interlanguage link",
    r"further-text",
    r"hatnote",
    r"highway detail hatnote",
    r"Inc-up",
    r"introductory article",
    r"other people",
    r"other places",
    r"Other Pennsylvania townships",
    r"other ships",
    r"other storms",
    r"other uses",
    r"other uses of",
    r"redirect",
    r"redirect2",
    r"redirect-distinguish",
    r"redirect-distinguish-for",
    r"redirect-distinguish-text",
    r"redirect-multi",
    r"redirect-several",
    r"redirect-synonym",
    r"see also",
    r"see also-text",
    r"See Wiktionary",
    r"self-reference",
    r"similar names",
    r"technical reasons",
    r"transcluding article",
    r"wikiIPA",
    r"Family name hatnote",
    r"Baptismal name",
    r"Bhutanese name",
    r"British barrelled name",
    r"Burmese name",
    r"Dinka name",
    r"Dutch name capitalization",
    r"Ethiopian name",
    r"Fijian name",
    r"Given name hatnote",
    r"Hungarian name",
    r"Icelandic name",
    r"Indian patronymic",
    r"Indonesian name",
    r"Lotuko name",
    r"Malay name",
    r"Maldivian Name",
    r"Matronymic name",
    r"Medieval Italian name",
    r"Meitei name",
    r"Norse name",
    r"Pakistani name",
    r"Patronymic name",
    r"Patronymic names",
    r"Philippine name",
    r"Portuguese name",
    r"Renaissance Florentine name",
    r"Spanish colonial name",
    r"Spanish married name",
    r"Tamil name",
    r"Traditional Norwegian name",
    r"Welsh name",
    r"Western name order",
    r"Western Slavic name",
)

# covered by DablinksTests Finds article disamiguation links from
# https://en.wikipedia.org/wiki/Wikipedia:Template_messages/General#Disambiguation_and_redirection
# and https://en.wikipedia.org/wiki/Template:Hatnote_templates (en only)
Dablinks = nested_template_regex(DablinksList)

# Matches {{short description}} template and its redirects, and {{Oscars short description}}
ShortDescriptionTemplate = nested_template_regex(
    (
        r"Short description",
        r"Brief description",
        r"Short desc",
        r"Short-description",
        r"Shortdescription",
        r"Oscars short description",
    )
)

DeletionProtectionTagsList: tuple[str, ...] = (
    r"Bne",
    r"Cc-by-nc-2.0",
    r"Cc-by-nc-sa",
    r"Cc-by-nc-sa-2.0",
    r"Cc-nc",
    r"D",
    r"DB",
    r"DELETE",
    r"Db",
    r"Db doc",
    r"Db-Reason",
    r"Db-a1",
    r"Db-a10",
    r"Db-a11",
    r"Db-a2",
    r"Db-a3",
    r"Db-a4",
    r"Db-a5",
    r"Db-a6",
    r"Db-a7",
    r"Db-a9",
    r"Db-ad",
    r"Db-advert",
    r"Db-advertising",
    r"Db-album",
    r"Db-animal",
    r"Db-attack",
    r"Db-author",
    r"Db-band",
    r"Db-banned",
    r"Db-because",
    r"Db-bio",
    r"Db-bio-notenglish",
    r"Db-biography",
    r"Db-blank",
    r"Db-blanked",
    r"Db-blp",
    r"Db-bn",
    r"Db-bne",
    r"Db-c1",
    r"Db-cat-empty",
    r"Db-ce",
    r"Db-club",
    r"Db-cm",
    r"Db-comp",
    r"Db-company",
    r"Db-contact",
    r"Db-content",
    r"Db-context",
    r"Db-copypaste",
    r"Db-copyvio",
    r"Db-corp",
    r"Db-disambig",
    r"Db-e",
    r"Db-ec",
    r"Db-empty",
    r"Db-emptycat",
    r"Db-error",
    r"Db-event",
    r"Db-f1",
    r"Db-f10",
    r"Db-f2",
    r"Db-f3",
    r"Db-f7",
    r"Db-f9",
    r"Db-fake",
    r"Db-foreign",
    r"Db-fpcfail",
    r"Db-g1",
    r"Db-g10",
    r"Db-g11",
    r"Db-g12",
    r"Db-g13",
    r"Db-g2",
    r"Db-g3",
    r"Db-g4",
    r"Db-g5",
    r"Db-g6",
    r"Db-g7",
    r"Db-g8",
    r"Db-gallery",
    r"Db-gfdl",
    r"Db-group",
    r"Db-hoax",
    r"Db-house",
    r"Db-imagepage",
    r"Db-imgcopyvio",
    r"Db-inc",
    r"Db-internet",
    r"Db-intertubes",
    r"Db-invented",
    r"Db-madeup",
    r"Db-maint",
    r"Db-maintenance",
    r"Db-meta",
    r"Db-misrepresent",
    r"Db-misrepresentation",
    r"Db-move",
    r"Db-movedab",
    r"Db-mt",
    r"Db-multiple",
    r"Db-negublp",
    r"Db-nn",
    r"Db-nocontent",
    r"Db-nocontext",
    r"Db-noncom",
    r"Db-noncommercial",
    r"Db-nonsense",
    r"Db-notenglish",
    r"Db-notwebhost",
    r"Db-org",
    r"Db-owner",
    r"Db-p1",
    r"Db-p2",
    r"Db-pagemove",
    r"Db-peo",
    r"Db-people",
    r"Db-person",
    r"Db-promo",
    r"Db-r1",
    r"Db-r2",
    r"Db-r3",
    r"Db-redirect",
    r"Db-redirmisnomer",
    r"Db-redirnone",
    r"Db-repost",
    r"Db-self",
    r"Db-site",
    r"Db-song",
    r"Db-spam",
    r"Db-spamuser",
    r"Db-subpage",
    r"Db-t2",
    r"Db-t3",
    r"Db-talk",
    r"Db-templatecat",
    r"Db-test",
    r"Db-transwiki",
    r"Db-tw",
    r"Db-u",
    r"Db-u1",
    r"Db-u2",
    r"Db-u3",
    r"Db-u5",
    r"Db-user",
    r"Db-userpage",
    r"Db-vand",
    r"Db-vandalism",
    r"Db-web",
    r"Db-webhost",
    r"Db-website",
    r"Db-xfd",
    r"Dbe",
    r"Declinedsd",
    r"Delbecause",
    r"Delete",
    r"Delete because",
    r"Delete when empty",
    r"DeleteVanity",
    r"Deletebecause",
    r"Deletevanity",
    r"Duplicate",
    r"Dv",
    r"Empty",
    r"Hang on",
    r"Hangon click preload",
    r"Hangon preload C1",
    r"Nocontent",
    r"Nocontext",
    r"Notg4",
    r"Oldcsd",
    r"Oldcsdfull",
    r"Salt",
    r"Sdd",
    r"Sdd2",
    r"Sdd3",
    r"Should be a user space test page please delete",
    r"Speedy",
    r"Speedy delete",
    r"Speedy deletion templates",
    r"Speedydelete",
    r"Db-speedy delete if article",
    r"Speedy deletion-nonfree galleries",
    r"Speedy deletion-foreign language",
    r"Speedy deletion-technical",
    r"Speedy deletion-no content",
    r"Speedy deletion-unpopulated category",
    r"Speedy deletion-vandalism",
    r"Speedy deletion-blocked user",
    r"Speedy deletion-duplicate template",
    r"Speedy deletion-nonexistent user",
    r"Speedy deletion-test page",
    r"Speedy deletion-previously deleted",
    r"Speedy deletion-musical recording",
    r"Speedy deletion-attack",
    r"Speedy deletion-duplicate article",
    r"Speedy deletion-no context",
    r"Speedy deletion-nonsense",
    r"Speedy deletion-advertising",
    r"Speedy deletion-copyright violation",
    r"Speedy deletion-author request",
    r"Speedy deletion",
    r"Book-prod",
    r"BPRODNote",
    r"BPRODWarning",
    r"Dated book prod",
    r"Deprod",
    r"Deprod-afd",
    r"Deprod-article",
    r"Deprod-contro",
    r"Deprod-disagree",
    r"Deprod-m",
    r"Deprod-reprod",
    r"Old prod full",
    r"Please prod",
    r"Polite-prod",
    r"Prod backlog",
    r"Prod backlog inner",
    r"Prod blp",
    r"Prod contested",
    r"Prod hint",
    r"Prod NFC use",
    r"Prod pending",
    r"Prod subcategory starter",
    r"Prod-nn",
    r"Prod-reason",
    r"Prod-speedy",
    r"Prod-summary",
    r"Prod-tip",
    r"Prod2",
    r"BLP prodded",
    r"Prodded",
    r"PRODNote",
    r"PRODWarning",
    r"PRODWarning-notalk",
    r"ProdwarningBLP",
    r"Proposed deletion",
    r"Proposed deletion endorsed",
    r"Proposed deletion notify",
    r"PrSpam",
    r"Tprod",
    r"Transwiki",
    r"C-uploaded",
    r"Editnotice explanation",
    r"Hprotected",
    r"M-cropped",
    r"M-protected",
    r"Mcropped",
    r"Mpimgprotected",
    r"Mpprotected",
    r"Mprotect",
    r"Mprotected2",
    r"OFFICE",
    r"Office",
    r"PP-protected",
    r"Padlock",
    r"Protection padlock",
    r"Permanently protected",
    r"Pp",
    r"Pp-blp",
    r"Pp-create",
    r"Pp-dispute",
    r"Pp-extended",
    r"Pp-full",
    r"Pp-jupe",
    r"Pp-main-page",
    r"Pp-meta",
    r"Pp-move",
    r"Pp-move-dispute",
    r"Pp-move-indef",
    r"Pp-move-vandalism",
    r"Pp-office",
    r"Pp-office-dmca",
    r"Pp-pc",
    r"Pp-pc1",
    r"Pp-protect",
    r"Pp-protected",
    r"Pp-reset",
    r"Pp-salt",
    r"Pp-semi",
    r"Pp-semi-indef",
    r"Pp-semi-prot",
    r"Pp-semi-protect",
    r"Pp-semi-protected",
    r"Pp-semi-protection",
    r"Pp-semiprotected",
    r"Pp-sock",
    r"Pp-template",
    r"Pp-usertalk",
    r"Pp-vandalism",
    r"Protected article title",
    r"Protected image",
    r"Protected sister project logo",
    r"Protected title",
    r"ProtectedMainPageImage",
    r"R fully protected",
    r"R semi-protected",
    r"R template protected",
    r"Semiprotected",
    r"Soft redirect protection",
    r"Sprot",
    r"Sprotect",
    r"Sprotect2",
    r"Sprotected",
    r"Sprotected2",
    r"Temporarily protected",
    r"Unblock-abuse",
    r"Unblockabuse",
    r"Uploaded from Commons",
    r"Uprotect",
    r"Usertalk-sprotect",
    r"Usertalk-vprotect",
    r"Vutprotected",
    r"Prod blp/dated",
    r"Proposed deletion/dated",
    r"Transwiki/dated",
    r"Article for deletion/dated",
    r"Article for deletion",
    r"Afd-merge to",
)

# matches speedy deletion templates (from Category:Speedy_deletion_templates), deletion templates
# (Category:Proposed_deletion-related_templates) and protection templates
# (Category:Protection_templates) Plus optional wiki comment(s) before and/or after -- comments
# before must start on newline (to not pick up comments following a template above on same line as
# that template)
DeletionProtectionTags = _R(
    str(nested_template_regex(DeletionProtectionTagsList)) + r"(?:\s*<!--\s*[^<>\r\n]+\s*-->\s*?)*"
)

# Matches "Featured list", "Featured article", "Good article" templates
GoodFeaturedArticleTemplates = nested_template_regex(
    (r"Featured list", r"Featured article", r"Good article")
)

# Matches "Use mdy dates", "Use dmy dates" and "Use xxx English" templates, plus others sorted at
# same level - item 7 per MOS:ORDER.
UseDatesEnglishTemplates = nested_template_regex(
    (
        r"Use mdy dates",
        r"Use dmy dates",
        r"Use American English",
        r"Use Antiguan and Barbudan English",
        r"Use Australian English",
        r"Use Bangladeshi English",
        r"Use British English",
        r"Use Oxford spelling",
        r"Use Canadian English",
        r"Use Ghanaian English",
        r"Use Hiberno-English",
        r"Use Hong Kong English",
        r"Use Indian English",
        r"Use Jamaican English",
        r"Use Kenyan English",
        r"Use Liberian English",
        r"Use Malaysian English",
        r"Use New Zealand English",
        r"Use Nigerian English",
        r"Use Pakistani English",
        r"Use Philippine English",
        r"Use Singapore English",
        r"Use South African English",
        r"Use Sri Lankan English",
        r"Use Tanzanian English",
        r"Use Trinidad and Tobago English",
        r"Use Ugandan English",
        r"EngvarB",
        r"cs1 config",
        r"CS1 config",
        r"Use shortened footnotes",
    )
)

# Matches the sister links templates such as {{wiktionary}}
SisterLinks = nested_template_regex(
    (
        r"wiktionary",
        r"sisterlinks",
        r"sister links",
        r"sister project links",
        r"wikibooks",
        r"wikimedia",
        r"wikiversity",
    )
)

# Matches the maintenance tags (en-wiki only) such as orphan, cleanup; with optional same-line
# wiki comment after
MaintenanceTemplates = _R(
    str(MultipleIssuesArticleMaintenanceTemplates) + r"(?: *<!--.*?-->(?=\r\n|$))?", O.MULTILINE
)

# Matches the {{Unreferenced}} template
Unreferenced = nested_template_regex((r"unreferenced", r"unreferenced stub"))

# Matches {{Portal}} template
PortalTemplate = nested_template_regex(r"portal")

# to find only matching comments use
# <!--(?>(?!<!--|-->).|<!--(?<Depth>)|-->(?<-Depth>))*(?(Depth)(?!))--> Matches &lt;!-- comments
# --&gt;
Comments = _R(r"<!--.*?-->", O.SINGLELINE)

# Matches text within &lt;p style...&gt;...&lt;/p&gt; HTML tags
Pstyles = _R(r"<p style\s*=\s*[^<>]+>.*?<\s*/p>", O.IGNORE_CASE | O.SINGLELINE)

# Matches empty comments (zero or more whitespace)
EmptyComments = _R(r"<!--[^\S\r\n]*-->")

# Matches empty bold wikitags (zero or more whitespace)
EmptyBold = _R(r"'{3}\s*'{3}")

# Matches {{Short pages monitor}} plus comment, generated from {{subst:Long comment}}
ShortPagesMonitor = _R(r"\s*{{[sS]hort pages monitor}}<!--[^<>]+-->")

# Matches &lt;ref&gt; tags, including named references and condensed named references
Refs = _R(
    r"(<\s*ref\s+(?:name|group|details)\s*=\s*[^<>]*?/\s*>|<\s*ref\b[^<>]*>(?>.(?<!<\s*ref\b[^>/]*?>|<\s*/\s*ref\s*>)|<\s*ref\b[^>/]*>(?<DEPTH>)|<\s*/\s*ref\s*>(?<-DEPTH>))*(?(DEPTH)(?!))<\s*/\s*ref\s*>)",
    O.IGNORE_CASE | O.SINGLELINE,
)

# Matches &lt;ref&gt; tags with group parameter, optionally named as well. Does not match regular
# named references
RefsGrouped = _R(
    r"(<\s*ref\s+(?:name\s*=\s*[^<>]*?\s*)?(?:group|details)\s*=\s*[^<>]*?/\s*>|<\s*ref\s+(?:name\s*=\s*[^<>]*?\s*)?(?:group|details)\s*=\s*[^<>]*?>(?>.(?<!<\s*ref\s+(?:group|details)\b[^>/]*?>|<\s*/\s*ref\s*>)|<\s*ref\s+(?:group|details)\b[^>/]*?>(?<DEPTH>)|<\s*/\s*ref\s*>(?<-DEPTH>))*(?(DEPTH)(?!))<\s*/\s*ref\s*>)",
    O.IGNORE_CASE | O.SINGLELINE,
)

# Matches &lt;/i&gt;...&lt;i&gt; reversed italics tags, group 1 being the content between the tags
ReversedItalics = _R(r"< */ *i *>([^<]*)< *i *>(?![^<]*< */ *i *>)")

# Matches &lt;nowiki&gt; tags
Nowiki = _R(r"<nowiki\s*>.*?</nowiki\s*>", O.SINGLELINE | O.IGNORE_CASE)

# Matches &lt;small&gt; tags, including nested tags. Group 1 is the text within the tags
Small = _R(
    r"<\s*small\s*>((?>(?!<\s*/?\s*small\s*>).|<\s*small\s*>(?<DEPTH>)|<\s*/\s*small\s*>(?<-DEPTH>))*(?(DEPTH)(?!)))<\s*/\s*small\s*>",
    O.SINGLELINE | O.IGNORE_CASE,
)

# Matches &lt;big&gt; tags
Big = _R(
    r"<\s*big\s*>((?>(?!<\s*big\s*>|<\s*/\s*big\s*>).|<\s*big\s*>(?<DEPTH>)|<\s*/\s*big\s*>(?<-DEPTH>))*(?(DEPTH)(?!)))<\s*/\s*big\s*>",
    O.SINGLELINE | O.IGNORE_CASE,
)

# Matches &lt;sup&gt; and &lt;sub&gt; tags
SupSub = _R(r"<(?<key>su(?:p|b))>(.*?)</\k<key>>", O.SINGLELINE | O.IGNORE_CASE)

# Matches bold italic text, group 1 being the text in bold italics (wiki format ''''' only)
BoldItalics = _R(r"(?<!')'{5}((?:[^']+|.*?[^'])?)'{5}(?!')")

# Matches italic text, group 1 being the text in italics (wiki format '' only)
Italics = _R(r"(?<!')'{2}((?:[^']+|[^'].*?[^'])?)'{2}(?!')")

# Matches bold text, group 1 being the text in bold (wiki format ''' only)
Bold = _R(r"(?<!')'{3}((?:[^']+|.*?[^'])?)'{3}(?!')")

# Matches the &lt;br/&gt; tag and valid variants
Br = _R(r"< *br */?>", O.IGNORE_CASE)

# Matches a row beginning with an asterisk, allowing for spaces before
StarRows = _R(r"^ *(\*)(.*)", O.MULTILINE)

# Matches the References level 2 heading
ReferencesHeader = _R(r"== *References *==", O.IGNORE_CASE | O.RIGHT_TO_LEFT)

# Matches the Notes level 2 heading
NotesHeader = _R(r"== *Notes *==", O.IGNORE_CASE | O.RIGHT_TO_LEFT)

# Matches a number between 1000 and 2999
GregorianYear = _R(r"\b[12][0-9]{3}\b")

# Matches a percentage with a space or a non-breaking space
Percent = _R(r"\s(\(?[-±\+]?\d+\.?\d*)(\s|\s?\&nbsp;)%(\p{P}|\)?\s)")

# Matches a currency symbol with a space or a non-breaking space
Currency = _R(r"(€|£|\$)(\s|\s?\&nbsp;)(\d+\.?\d*(\p{P}|\)?\s))")

# Matches 12-hour clock time without a non-breaking space
ClockTime = _R(r"(\b[01]?[0-9](?::[0-5][0-9])?:[0-5][0-9]) ?([ap]\.m\.)")

# List of known infobox fields holding date of birth
InfoBoxDOBFields = (
    r"yearofbirth",
    r"dateofbirth",
    r"date of birth",
    r"datebirth",
    r"born",
    r"birth date",
    r"birthdate",
    r"birth_date",
    r"birth",
)

# List of known infobox fields holding date of death
InfoBoxDODFields = (
    r"yearofdeath",
    r"datedeath",
    r"dateofdeath",
    r"date of death",
    r"died",
    r"death date",
    r"deathdate",
    r"death_date",
    r"death",
)

InfoBoxPOBFields = (
    r"birthplace",
    r"Birthplace",
    r"birth_place",
    r"placeofbirth",
    r"place of birth",
    r"place_of_birth",
    r"placebirth",
)

InfoBoxPODFields = (
    r"deathplace",
    r"Deathplace",
    r"death_place",
    r"placeofdeath",
    r"place of death",
    r"place_of_death",
    r"placedeath",
    r"place_death",
)

# Matches "ibid" and "op cit"
IbidLocCitation = _R(r"\b(ibid|loc.{1,4}cit|Page ?needed)\b", O.IGNORE_CASE | O.SINGLELINE)

# Matches the {{Ibid}} template
Ibid = nested_template_regex(r"Ibid")

# Matches consecutive whitespace
WhiteSpace = _R(r"\s+")

# List of PAGENAME, PAGENAMEE, BASEPAGENAME, BASEPAGENAMEE templates
BASEPAGENAMETemplatesL = (r"PAGENAME", r"PAGENAMEE", r"BASEPAGENAME", r"BASEPAGENAMEE")

# Matches PAGENAME, PAGENAMEE, BASEPAGENAME, BASEPAGENAMEE templates
BASEPAGENAMETemplates = nested_template_regex(BASEPAGENAMETemplatesL)

# From http://www.dreamincode.net/code/snippet3490.htm
UrlValidator = _R(
    r"^(https?|ftp)\://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,3}(:[a-zA-Z0-9]*)?/?([a-zA-Z0-9\-\._\?\,\'/\\\+&amp;%\$#\=~])*[^\.\,\)\(\s]$",
    O.COMPILED,
)

# Matches templates from [[Category:Hatnote templates for names]], excluding name order templates
SurnameClarificationTemplates = nested_template_regex(
    (
        r"Arabic name",
        r"Basque name",
        r"Cambodian name",
        r"Catalan name",
        r"Chinese Indonesian name",
        r"Chinese name",
        r"Dinka name",
        r"Dutch name",
        r"Eastern Slavic name",
        r"Galician name",
        r"Germanic name",
        r"Habesha name",
        r"Hmong name",
        r"Icelandic name",
        r"Indian name",
        r"Indonesian name",
        r"Japanese name",
        r"Korean name",
        r"Malay name",
        r"Mongolian name",
        r"Multi-word family name",
        r"Philippine name",
        r"Portuguese name",
        r"Romance name",
        r"Slavic name",
        r"Spanish name",
        r"Turkic name",
        r"Vietnamese name",
        r"Welsh name",
        r"Western name order",
    )
)

# Matches magic word behaviour switches from https://en.wikipedia.org/wiki/Help:Magic_words
MagicWordBehaviourSwitches = _R(
    r"^__(TOC|FORCETOC|NOTOC|NOEDITSECTION|ARCHIVEDTALK|NEWSECTIONLINK|NONEWSECTIONLINK|NOGALLERY|HIDDENCAT|INDEX|NOINDEX|STATICREDIRECT|DISAMBIG)__(\s+|$)",
    O.MULTILINE,
)


# -- Per-wiki regexes ----------------------------------------------------------------------------
# Port of MakeNamespaceSpecificRegexes, MakeEnLangRegexes, MakeDefaultSortRegex and
# MakeLangSpecificRegexes. AWB rebuilds static fields when the wiki changes; here each wiki gets its
# own immutable SiteRegexes (see for_site). Runtime data AWB loads from wiki pages
# (TemplateRedirects, DatedTemplates, RenamedTemplateParameters) lives elsewhere.

_IMAGE_IN_TEMPLATE_STRING = r"|{{\s*[Gg]allery\s*(?:\|(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!)))?}}|(?<=\|\s*(?:[a-zA-Z\d][a-zA-Z\d_ ]*\s*=)?)[^\|{}=\r\n\[\]]+?\.(?i:djvu|gif|jpe?g|og[agv]|pdf|png|svg|tiff?|mid|xcf|webm)(?=\s*(?:<!--[^>]*?-->\s*|⌊⌊⌊⌊M?\d+⌋⌋⌋⌋\s*)?(?:\||}}))"


class SiteRegexes:
    """The regexes that depend on the wiki: namespaces, magic words, month names, language."""

    def __init__(self, site: SiteConfig) -> None:
        self.site = site
        self._make_namespace_specific_regexes()
        self._make_en_lang_regexes()
        self._make_default_sort_regex()
        self._make_lang_specific_regexes()

    def _ntr(self, names: str | Iterable[str]) -> DotNetRegex:
        return nested_template_regex(names, self.site)

    def _make_namespace_specific_regexes(self) -> None:
        site = self.site
        nsci = dict(site.namespaces_case_insensitive)
        # A wiki missing a standard namespace (AWB's tests remove one from Variables.Namespaces
        # after the regexes are built) falls back to the canonical English name.
        for ns, name in CANONICAL_NAMESPACES.items():
            nsci.setdefault(ns, "(?i:" + name.rstrip(":").replace(" ", "[ _]") + r")\s*:")
        self.NamespacesCaseInsensitive: dict[int, DotNetRegex] = {k: _R(v) for k, v in nsci.items()}

        category = nsci[Namespace.CATEGORY]
        image = nsci[Namespace.FILE]
        template = nsci[Namespace.TEMPLATE]
        userns = nsci[Namespace.USER]
        usertalkns = nsci[Namespace.USER_TALK]

        self.TemplateStart = r"\{\{\s*(:?" + template + ")?"
        self.TemplateNameRegex = template_name_regex(site)

        self.Category = _R(
            r"\[\[[\s_]*" + category + r"[ _]*([^[\]|\r\n]*?)[ _]*(?:\|([^\|\]]*))?[ _]*\]\]"
        )

        # allow comments between categories, and keep them in the same place, only grab any comment
        # after the last category if on same line. whitespace: remove all whitespace after, but
        # leave a blank newline before a heading (rare case where category not in last section)
        self.RemoveCatsAllCats = _R(
            r"<!--[^<>]*?\[\[\s*"
            + category
            + r".*?(\]\]|\|.*?\]\]).*?-->|\[\["
            + category
            + r".*?(\]\]|\|.*?\]\])(\s*⌊⌊⌊⌊\d{1,4}⌋⌋⌋⌋| *<!--.*?-->|\s*<!--.*?-->(?=\r\n\[\[\s*"
            + category
            + r")|\s*(?=\r\n==)|\s*)?",
            O.SINGLELINE,
        )

        self.CategoryQuick = _R(r"\[\[[\s_]*" + category)

        # Match file name by using allowed character list, then a file extension, then optional
        # closing ]]; handles images within <gallery> and matches all of {{gallery}} too.
        images_string = (
            r"(?:\[\[\s*)?"
            + image
            + r"""[ \%\!"$&'’\(\)\*,\-.\/0-9:;=\?@\w\\\^_`~\x80-\xFF\+–]+\.[a-zA-Z]{3,4}\b(?:\s*(?:\]\]|\|))?"""
        )
        self.Images = _R(images_string + _IMAGE_IN_TEMPLATE_STRING)
        self.ImagesCountOnly = _R(images_string + _IMAGE_IN_TEMPLATE_STRING.replace("(?<=", "(?:"))
        self.ImagesNotTemplates = _R(images_string)

        self.FileNamespaceLink = _R(
            r"\[\[\s*" + image + r"((?>[^\[\]]+|\[\[(?<DEPTH>)|\]\](?<-DEPTH>))*(?(DEPTH)(?!)))\]\]"
        )

        self.Stub = _R(r"{{" + site.stub + r"\s*(?:\|[^{}]+)?}}")

        self.UserSignature = _R(r"\[\[\s*(?:" + userns + r"|" + usertalkns + r")")

        self.TemplateCall = _R(self.TemplateStart + r"\s*([^\]\|]*)\s*(.*)}}", O.SINGLELINE)

        self.LooseCategory = _R(r"\[\[[\s_]*" + category + r"[\s_]*([^\|]*?)(\|.*?)?\]\]")

        self.LooseImage = _R(r"\[\[\s*?(" + image + r")\s*([^\|\]]+)(.*?)\]\]")

        self.Months = "(" + "|".join(site.month_names) + ")"
        self.MonthsNoGroup = "(?:" + "|".join(site.month_names) + ")"
        months = self.Months

        self.Dates = _R("^(0?[1-9]|[12][0-9]|3[01]) " + months + "$")
        self.Dates2 = _R("^" + months + " (0?[1-9]|[12][0-9]|3[01])$")

        self.InternationalDates = _R(
            r"\b([1-9]|[12][0-9]|3[01])(?: +|&nbsp;)" + months + r" +([12]\d{3})\b"
        )
        self.AmericanDates = _R(months + r"(?: +|&nbsp;)([1-9]|[12][0-9]|3[01]),? +([12]\d{3})\b")

        self.DayMonth = _R(r"\b([1-9]|[12][0-9]|3[01])(?: +|&nbsp;)" + months + r"\b")
        self.MonthDay = _R(months + r"(?: +|&nbsp;)([1-9]|[12][0-9]|3[01])\b")

        self.DayMonthRangeSpan = _R(
            r"\b((?:[1-9]|[12][0-9]|3[01])(?:–|&ndash;|{{ndash}}|\/)(?:[1-9]|[12][0-9]|3[01])) "
            + months
            + r"\b"
        )
        self.MonthDayRangeSpan = _R(
            months
            + r" ((?:[1-9]|[12][0-9]|3[01])(?:–|&ndash;|{{ndash}}|\/)(?:[1-9]|[12][0-9]|3[01]))\b"
        )

        magic = site.magic_words.get("redirect")
        redirect_string = "|".join(magic).replace("#", "") if magic is not None else "REDIRECT"

        # Regex contains extra opening/closing brackets and double bot, equal sign so that we fix
        # with FixSyntaxRedirects
        self.Redirect = _R(
            r"#(?:"
            + redirect_string
            + r")\s*[:|=]?\s*\[?\[?\[\[\s*:?\s*([^\|\[\]]*?)\s*(\|.*?)?\]\]\]?\]?",
            O.IGNORE_CASE,
        )

        url, url_long = site.url, site.url_long
        pos = first_difference(url, url_long)
        s = escape(url_long[:pos]).replace(r"https://", r"https?://")
        s += (
            "(?:"
            + escape(url_long[pos:])
            + r"index\.php(?:\?title=|/)|"
            + escape(url[pos:])
            + "/wiki/"
            + ")"
        )
        self.ExtractTitle = _R("^" + s + "([^?&]*)$")

        self.EmptyLink = _R(
            r"\[\[\s*(?:(:?" + category + "|" + image + r")\s*:?\s*(\|.*?)?|[|\s]*)\]\]"
        )
        self.EmptyTemplate = _R(r"{{(" + template + r")?[|\s]*}}")

    def _make_en_lang_regexes(self) -> None:
        """Regexes for en-wiki, which act as the default unless a language overrides them."""
        ntr = self._ntr
        self.DateYearMonthParameter = r"date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
        self.Orphan = ntr("Orphan")
        self.Uncategorized = ntr(
            [
                "Uncategorized",
                "+cat",
                "Categories missing",
                "Categories needed",
                "Categories requested",
                "Categorise",
                "Categorízame",
                "Categorize",
                "Category needed",
                "Categoryneeded",
                "Category requested",
                "Cat needed",
                "Catneeded",
                "CatNeeded",
                "Cats needed",
                "Missing categories",
                "Ncat",
                "Needs cat",
                "Needs categories",
                "Needs cats",
                "Noc",
                "Nocat",
                "No categories",
                "No category",
                "Nocategory",
                "No cats",
                "Nocats",
                "Uncat",
                "Uncategorised",
                "Uncategorised stub",
                "Uncategorisedstub",
                "Uncategorized stub",
                "Uncategorizedstub",
                "Uncat stub",
                "Uncat-stub",
                "Uncatstub",
            ]
        )
        self.DeadEnd = ntr(
            ["Dead end", "Deadend", "Internal links", "Internallinks", "Dep", "Nuevointernallinks"]
        )
        self.Wikify = ntr(["Wikify", "Underlinked"])
        self.InUse = ntr(_InUseList)
        self.LinkFGAs = ntr(["link FA", "link GA"])
        self.ReferenceList = ntr(["reflist", "references-small", "references-2column"])
        self.Persondata = ntr("persondata")
        self.SIAs = ntr(
            [
                "SIA",
                "Animal common name",
                "Chemistry index",
                "Enzyme index",
                "Fungus common name",
                "Given name",
                "Lakeindex",
                "Lake index",
                "Locomotiveindex",
                "Locomotive index",
                "Media set index",
                "Molecular formula index",
                "MolForm Index",
                "MolFormIndex",
                "Mountainindex",
                "Mountain index",
                "Nickname",
                "Painting index",
                "Plant common name",
                "Road index",
                "Roadindex",
                "Set index",
                "Setindex",
                "Set index article",
                "Ship index",
                "Shipindex",
                "Sia",
                "Sport index",
                "Sportindex",
                "Stormindex",
                "Storm index",
                "Surname",
                "Surnames",
            ]
        )
        self.ExternalLinksHeader = _R(r"== *External +links? *==", O.IGNORE_CASE | O.RIGHT_TO_LEFT)
        self.SeeAlso = _R(r"(==+)\s*see +also\s*\1", O.IGNORE_CASE)
        self.Disambigs = _R(
            str(
                ntr(
                    [
                        "Airport disambig",
                        "Airport disambiguation",
                        "Callsigndis",
                        "Call sign disambiguation",
                        "Chinese title disambig",
                        "Chinese title disambiguation",
                        "Dab",
                        "Dis",
                        "Disamb",
                        "Disambig",
                        "Disambig-cleanup",
                        "DisambigG",
                        "Disambiggeo",
                        "DisambigGeo",
                        "Disambiguation",
                        "Disambiguation cleanup",
                        "Disambiguation with potential",
                        "Genus disambig",
                        "Genus disambiguation",
                        "Geodab",
                        "Geo-dis",
                        "Geodis",
                        "Geodisambig",
                        "Geographic disambiguation",
                        "Hndis",
                        "Hndis-cleanup",
                        "Hospitaldis",
                        "Hospital disambiguation",
                        "Human name disambiguation",
                        "Human name disambiguation cleanup",
                        "Hurricane season disambiguation",
                        "LatinNameDisambig",
                        "Letter-NumberCombdisambig",
                        "Letter-NumberCombDisambig",
                        "Letter–number combination disambiguation",
                        "Letter-Number Combination Disambiguation",
                        "Mathdab",
                        "Mathematical disambiguation",
                        "Mathematics disambiguation",
                        "Military unit disambiguation",
                        "Mil-unit-dis",
                        "Molecular formula disambiguation",
                        "MolFormDisambig",
                        "Numberdis",
                        "Number disambiguation",
                        "Place name disambiguation",
                        "Pnd ",
                        "Road disambiguation",
                        "Schooldis",
                        "School disambiguation",
                        "Species Latin name abbreviation disambiguation",
                        "SpeciesLatinNameDisambig",
                        "Species Latin name disambiguation",
                        "Station disambiguation",
                        "Taxonomy disambiguation",
                        "WoO number disambiguation",
                    ]
                )
            )
            + r"(?: *<!--.*?-->(?=\r\n|$))?",
            O.MULTILINE,
        )
        self.NoRefCondensingTemplates: DotNetRegex | None = None

    def _make_default_sort_regex(self) -> None:
        """DEFAULTSORT, using the wiki's defaultsort magic words where known."""
        site = self.site
        magic = site.magic_words.get("defaultsort")
        if magic is not None:
            s = "(?i:" + "|".join(magic).replace(":", "") + ")"
        elif site.lang_code == "en":
            s = "(?:(?i:defaultsort(key|CATEGORYSORT)?))"
        else:
            s = "(?i:defaultsort)"

        # sv-wiki: allow comment on same line as DEFAULTSORT
        end = (
            r"(?<end>\s*}}(?: *<!--[^<>]+-->)?|\r|\n)"
            if site.lang_code == "sv"
            else r"(?<end>\s*}}|\r|\n)"
        )
        self.Defaultsort = _R(
            self.TemplateStart
            + s
            + r"\s*[:\|]\s*(?<key>(?>[^\{\}\r\n]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))|[^\}\r\n]*?)"
            + end,
            O.EXPLICIT_CAPTURE,
        )

    def _make_lang_specific_regexes(self) -> None:
        """Orphan, wikify, uncat, disambiguation, inuse templates, date parameter, link FA/GA."""
        ntr = self._ntr
        disambig: list[str] = []
        match self.site.lang_code:
            case "ar":
                self.Orphan = ntr("يتيمة")
                self.Uncategorized = ntr(
                    [
                        "غير مصنف",
                        "غير مصنفة",
                        "بذرة غير مصنفة",
                        "Uncategorised",
                        "Uncategorized",
                        "Uncategorised stub",
                        "Uncategorized stub",
                        "Uncategorizedstub",
                    ]
                )
                self.DateYearMonthParameter = (
                    r"تاريخ={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
                )
                self.DeadEnd = ntr(
                    ["Dead end", "Deadend", "Internal links", "Internallinks", "نهاية مسدودة"]
                )
                self.Wikify = ntr("وصلات قليلة")
                self.InUse = ntr(
                    [
                        "إنشاء",
                        "تحرر",
                        "Underconstruction",
                        "تحت الإنشاء",
                        "تحت الأنشاء",
                        "يحرر",
                        "إنشاء مقالة",
                        "انشاء مقالة",
                        "Inuse",
                        "تحرير كثيف",
                        "يحرر المقالة",
                        "تحت التحرير",
                        "قيد الاستخدام",
                    ]
                )
                disambig = ["Disambig", "توضيح", "صفحة توضيح", "أسمياء"]
                self.SIAs = ntr("الاسم الشائع للحيوان")
            case "arz":
                self.Orphan = ntr("يتيمه")
                self.Uncategorized = ntr(
                    ["مش متصنفه", "تقاوى مش متصنفه", "Uncategorized", "Uncategorized stub"]
                )
                self.DateYearMonthParameter = (
                    r"تاريخ={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
                )
                self.DeadEnd = ntr(["Dead end", "Deadend", "نهايه مسدوده"])
                self.Wikify = ntr("ويكى")
                disambig = ["Disambig", "صفحة توضيح", "توضيح"]
            case "ca":
                self.InUse = ntr(["Modificant", "Editant-se", "Editant"])
                disambig = ["Desambiguació", "Desambigua", "Disambig"]
            case "ckb":
                self.Orphan = ntr("داڕێژە:ھەتیو")
                self.Uncategorized = self.Orphan = ntr("داڕێژە:بێ پۆل")
                self.DeadEnd = ntr(["Dead end", "Deadend", "داڕێژە:بنبەست"])
                self.Wikify = _R(
                    r"(?:{{\s*(?:داڕێژە:کەمبەستەر)(?:\s*\|\s*(?:"
                    + self.DateYearMonthParameter
                    + r"|.*?))?}})",
                    O.IGNORE_CASE,
                )
            case "de":
                disambig = ["Begriffsklärung"]
                self.Persondata = ntr("personendaten")
            case "el":
                self.Orphan = ntr("Ορφανό")
                self.Uncategorized = ntr(["Ακατηγοριοποίητο"])
                self.DateYearMonthParameter = (
                    r"ημερομηνία={{subst:CURRENTYEAR}} {{subst:CURRENTMONTH}}"
                )
                self.DeadEnd = ntr(["Dead end"])
                self.Wikify = _R(
                    r"(?:{{\s*(?:Underlinked)(?:\s*\|\s*(?:"
                    + self.DateYearMonthParameter
                    + r"|.*?))?}})",
                    O.IGNORE_CASE,
                )
                self.InUse = ntr(["Inuse", "Σε χρήση"])
                disambig = ["Αποσαφήνιση", "Αποσαφ", "Disambig"]
            case "eo":
                self.InUse = ntr(["Redaktas", "Redaktata", "Uzata"])
            case "es":
                self.InUse = ntr(["En uso", "Enuso"])
                disambig = ["Desambiguación", "Desambig", "Des", "Desambiguacion", "Disambig"]
            case "fa":
                self.Orphan = ntr(["یتیم"])
                disambig = ["ابهام‌زدایی", "ابهامزدایی", "ابهام زدایی"]
                self.NoRefCondensingTemplates = ntr(["پک", "پانویس کوتاه‌شده"])
            case "fr":
                self.InUse = ntr(["En cours"])
                self.ReferenceList = ntr(["références", "references", "reflist"])
                self.Orphan = ntr(["orphan", "orphelin", "Article orphelin"])
                self.Wikify = ntr(
                    [
                        "A wikifier",
                        "Article à wikifier",
                        "Underlinked",
                        "Wikif",
                        "Wikification",
                        "Wikifier",
                        "Wikify",
                        "À wikifier",
                    ]
                )
            case "hu":
                self.InUse = ntr(["Építés alatt", "Fejlesztés"])
            case "hy":
                self.Orphan = ntr("Որբ")
                self.Uncategorized = ntr(["Կատեգորիա չկա", "Կչ", "Uncategorized"])
                self.DeadEnd = ntr(["Dead end", "Deadend", "Underlinked", "Փակ"])
                self.Wikify = _R(
                    r"{{\s*Վիքիֆիկացում(?:\s*\|\s*(" + self.DateYearMonthParameter + r"|.*?))?}}",
                    O.IGNORE_CASE,
                )
                self.InUse = ntr(["Խմբագրում եմ"])
            case "it":
                self.InUse = ntr(["WIP", "Wip"])
            case "pl":
                disambig = ["Disambig"]
            case "pt":
                self.InUse = ntr(["Em edição", "Emuso", "Emedição"])
            case "ro":
                self.InUse = ntr(["S-dezvoltare"])
            case "ru":
                self.Uncategorized = ntr(
                    ["Нет категорий", "Uncategorized", "Uncategorized stub", "Nocat"]
                )
                self.Orphan = ntr(["изолированная статья", "Сирота", "Orphan"])
                self.DateYearMonthParameter = (
                    r"date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
                )
                self.DeadEnd = ntr(["Dead end", "Tупиковая статья"])
                self.Wikify = _R(
                    r"({{\s*(?:Wikify|Викифицировать|Тупиковая статья|Underlinked)(?:\s*\|\s*("
                    + self.DateYearMonthParameter
                    + r"|.*?))?}})",
                    O.IGNORE_CASE,
                )
                self.InUse = ntr(
                    [
                        "Редактирую",
                        "Перерабатываю",
                        "Inuse-by",
                        "Пишу",
                        "Inuse",
                        "Правлю",
                        "Перевожу",
                        "In-use",
                        "Processing",
                        "Process",
                        "Статья редактируется",
                        "Викифицирую",
                        "Under construction",
                    ]
                )
                disambig = [
                    "АТДы",
                    "Военные части",
                    "Воинские формирования",
                    "Воинские части",
                    "Горы",
                    "ЖДС",
                    "Ждс",
                    "Многозначность",
                    "НПы",
                    "Неоднозначность",
                    "Неоднозначность2",
                    "Нпы",
                    "Одноименные фильмы",
                    "Одноимённые НП",
                    "Одноимённые воинские части",
                    "Одноимённые горные объекты",
                    "Одноимённые горы",
                    "Одноимённые железнодорожные станции",
                    "Одноимённые координаты",
                    "Одноимённые корабли",
                    "Одноимённые монастыри",
                    "Одноимённые муниципальные образования",
                    "Одноимённые муниципальные образования",
                    "Одноимённые населённые пункты",
                    "Одноимённые объекты АТД",
                    "Одноимённые озёра",
                    "Одноимённые острова",
                    "Одноимённые памятники",
                    "Одноимённые площади",
                    "Одноимённые реки",
                    "Одноимённые станции",
                    "Одноимённые станции метро",
                    "Одноимённые улицы",
                    "Одноимённые фильмы",
                    "Одноимённые храмы",
                    "Однофамильцы-тёзки",
                    "Озёра",
                    "Острова",
                    "Реки",
                    "Список однофамильцев",
                    "Список однофамильцев-тёзок",
                    "Список полных тёзок",
                    "Список тёзок",
                    "Список тёзок-однофамильцев",
                    "Станции",
                    "Тёзки-однофамильцы",
                    "Churchdis",
                    "Coorddis",
                    "Disambig",
                    "Disambiguation",
                    "Metrodis",
                    "Militarydis",
                    "Mondis",
                    "Monumdis",
                    "Mountaindis",
                    "Moviedis",
                    "Placedis",
                    "Riverdis",
                    "Roaddis",
                    "Shipdis",
                    "Stationdis",
                    "Surname",
                ]
            case "simple":
                self.SeeAlso = _R(r"(==+)\s*(related +pages|see +also)\s*\1", O.IGNORE_CASE)
                self.ExternalLinksHeader = _R(
                    r"== *(Other +websites|External +links?) *==", O.IGNORE_CASE | O.RIGHT_TO_LEFT
                )
            case "sq":
                self.Uncategorized = ntr(["Pa kategori", "Uncategorized"])
                self.Orphan = ntr(["Faqe e palidhur", "Orphan"])
                self.DateYearMonthParameter = (
                    r"date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
                )
            case "sv":
                self.Orphan = ntr("Föräldralös")
                self.Uncategorized = ntr(
                    [
                        "Okategoriserad",
                        "Uncategorised",
                        "Uncategorized",
                        "Uncategorised stub",
                        "Uncategorized stub",
                        "Uncategorisedstub",
                        "Uncategorizedstub",
                    ]
                )
                self.DateYearMonthParameter = r"datum={{subst:CURRENTYEAR}}-{{subst:CURRENTMONTH}}"
                self.DeadEnd = ntr(["Dead end"])
                self.Wikify = _R(
                    r"{{\s*Ickewiki(?:\s*\|\s*(" + self.DateYearMonthParameter + r"|.*?))?}}",
                    O.IGNORE_CASE,
                )
                self.InUse = ntr(
                    [
                        "Pågår",
                        "Information kommer",
                        "Pågående uppdateringar",
                        "Ständiga uppdateringar",
                        "PÅGÅR",
                        "Påbörjad",
                        "Bearbetning pågår",
                    ]
                )
                disambig = [
                    "4LA",
                    "Betydelselista",
                    "Dab",
                    "Disambig",
                    "Disambiguation",
                    "Efternamn",
                    "Förgrening",
                    "Förgreningssida",
                    "Flertydig",
                    "Förnamn",
                    "Gaffel",
                    "Gren",
                    "Grensida",
                    "Hndis",
                    "Namnförgrening",
                    "Namngrensida",
                    "Ortnamn",
                    "Robotskapad förgrening",
                    "Trebokstavsförkortning",
                    "Trebokstavsförgrening",
                ]
            case "zh":
                self.DateYearMonthParameter = r"time={{subst:#time:c}}"
                self.Orphan = ntr(["Orphan"])
                self.InUse = ntr(
                    [
                        "Inuse",
                        "UnderConstruction",
                        "工事中",
                        "Inedit",
                        "Editing",
                        "使用中",
                        "2小时内重大修改 ",
                    ]
                )
            case _:
                pass  # AWB calls MakeEnLangRegexes again here; already done in __init__

        if disambig:
            self.Disambigs = _R(str(ntr(disambig)) + r"(?: *<!--.*?-->(?=\r\n|$))?", O.MULTILINE)

        if self.NoRefCondensingTemplates is None:
            self.NoRefCondensingTemplates = ntr(["NOTIMPLEMENTEDDUMMYTEMPLATE"])

        stub = self.site.stub
        self.PossiblyCommentedStub = _R(
            r"(<!-- ?\{\{"
            + stub
            + r"\b\}\}.*?-->|\{\{"
            + stub
            + r"\s*(?:\|(?:[^{}]+|"
            + self.DateYearMonthParameter
            + r"))?}})"
        )


@functools.lru_cache(maxsize=32)
def for_site(site: SiteConfig) -> SiteRegexes:
    """The (cached) regexes for a wiki."""
    return SiteRegexes(site)
