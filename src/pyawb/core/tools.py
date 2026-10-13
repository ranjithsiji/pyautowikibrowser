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
# Ported from AutoWikiBrowser WikiFunctions/Tools.cs
# (C) 2007 Martin Richards, (C) 2007 Stephen Kennedy, and the AutoWikiBrowser contributors
# (GPL-2.0-or-later).
"""Port of WikiFunctions/Tools.cs: text, title and template helpers used across AWB.

Names are AWB's in snake_case (Tools.GetTemplateParameterValue -> get_template_parameter_value).
C# overloads become optional parameters. Functions that AWB wrote against the global Variables
use current_site() (see pyawb.core.site.use_site).

Not ported here: HTTP (GetHTML, PostData: pyawb.api), clipboard, sound, message boxes, browser
launching and file logging (pyawb.ui), and ExpandTemplate (needs the API; ported with it).
Text uses AWB's internal "\\r\\n" line endings throughout, whatever the OS.
"""

# ruff: noqa: E501

from __future__ import annotations

import datetime
import hashlib
import ipaddress
import unicodedata
import urllib.parse
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING

from pyawb.core import namespace, rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import parsers as _parsers
from pyawb.core.parsers import templates as _templates
from pyawb.core.parsers import wikilinks as _wikilinks
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import Namespace, current_site
from pyawb.core.textutil import (
    all_case_insensitive,
    char_lower,
    char_upper,
    first_difference,
    first_letter_case_insensitive,
    is_letter,
    is_letter_or_digit,
    nested_template_regex,
    remove_hash_from_page_title,
    strip_namespace_colon,
    template_name_regex,
    turn_first_to_lower,
    turn_first_to_upper,
    turn_first_to_upper_no_project_check,
    url_decode,
    url_encode,
    wiki_decode,
    wiki_encode,
)

if TYPE_CHECKING:
    from pyawb.core.parsers.parsers import DateLocale

__all__ = [
    "Diacritics",
    "SortKeyChars",
    "all_case_insensitive",
    "char_lower",
    "char_upper",
    "first_difference",
    "first_letter_case_insensitive",
    "nested_template_regex",
    "remove_hash_from_page_title",
    "strip_namespace_colon",
    "template_name_regex",
    "turn_first_to_lower",
    "turn_first_to_upper",
    "turn_first_to_upper_no_project_check",
    "url_decode",
    "url_encode",
    "wiki_decode",
    "wiki_encode",
]

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741


def _S() -> W.SiteRegexes:
    return W.for_site(current_site())


# -- redirects and titles -------------------------------------------------------------------------


def is_redirect(article_text: str) -> bool:
    return len(redirect_target(article_text)) > 0


# see Category:Templates_for_soft_redirects
_SoftRedirect = nested_template_regex(
    [
        "Soft redirect",
        "SoftRedirect",
        "Soft Redirect",
        "Softredirect",
        "Softredir",
        "Soft link",
        "Soft redir",
        "Soft",
        "Category redirect",
        "Commons category redirect",
        "Deprecated shortcut",
        "Interwiki redirect",
        "Userrename",
        "Wikisource redirect",
        "Double soft redirect",
    ]
)


def is_redirect_or_soft_redirect(article_text: str) -> bool:
    return len(redirect_target(article_text)) > 0 or _SoftRedirect.is_match(article_text)


def redirect_target(article_text: str) -> str:
    """Target of a #REDIRECT, or "" if the text is not a redirect."""
    m = _S().Redirect.match(W.UnformattedText.replace(first_chars(article_text, 512), ""))
    return wiki_decode(m.group(1)).strip()


def is_wikimedia_project(project: str) -> bool:
    return project not in ("custom", "wikia")


_INVALID_CHARS = "[]{}|<>#"


def is_valid_title(article_title: str) -> bool:
    article_title = wiki_decode(article_title).strip()
    if not article_title or any(c in _INVALID_CHARS for c in article_title):
        return False
    article_title = _parsers.canonicalize_title_aggressively(article_title)
    article_title = remove_namespace_string(article_title)
    return len(article_title) > 0 and not article_title.startswith(":")


def remove_invalid_chars(article_title: str) -> str:
    return "".join(c for c in article_title if c not in _INVALID_CHARS)


def case_insensitive_string_compare(one: str, two: str) -> bool:
    """String.Compare(..., OrdinalIgnoreCase) == 0: per-character simple upper-casing."""
    return len(one) == len(two) and all(
        char_upper(a) == char_upper(b) for a, b in zip(one, two, strict=True)
    )


def regex_match_count(
    regex: str | DotNetRegex, text: str, options: rx.DotNetOptions = O.NONE
) -> int:
    r = regex if isinstance(regex, DotNetRegex) else _R(regex, options)
    return len(r.matches(text))


# -- human category keys --------------------------------------------------------------------------

_PersonOfPlace = _R(
    r"^(?<person>\w+( +\w+)*?)(?<ordinal> [IXV]+)? of (?<place>(\w+ *)+)(?<![IVX]+)$"
)
_WordsOnly = _R(r"^[\w ]+$")
_TrailingBracketed = _R(r"\(.*?\)$")
_ArabicNames = _R(
    r"(\b(Abd[au]ll?ah?|Ahmed|Mustaq|Merza|Kandah[a-z]*|Mohabet|Nasrat|Nazargul|Yasi[mn]|Husayn|Akram|M[ou]hamm?[ae]d\w*|Abd[eu]l|Razzaq|Adil|Anwar|Fahed|Habi[bdr]|Hafiz|Jawad|Hassan|Ibr[ao]him|Khal[ei]d|Karam|Majid|Mustafa|Rash[ie]d|Yusef|[Bb]in|Nasir|Aziz|Rahim|Kareem|Abu|Aminullah|Fahd|Fawaz|Ahmad|Rahman|Hasan|Nassar|A(?:zz|s)am|Jam[ai]l|Tariqe?|Yussef|Said|Wass?im|Wazir|Tarek|Umran|Mahmoud|Malik|Shoaib|Hizani|Abib|Raza|Salim|Iqbal|Saleh|Hajj|Brahim|Zahir|Wasm|Yo?usef|Yunis|Zakim|Shah|Yasser|Samil|Akh[dk]ar|Haji|Uthman|Khadr|Asiri|Rajab|Shakouri|Ishmurat|Anazi|Nahdi|Zaheed|Ramzi|Rasul|Muktar|Muhassen|Radhi|Rafat|Kadir|Zaman|Karim|Awal|Mahmud|Mohammon|Husein|Airat|Alawi|Ullah|Sayaf|Henali|Ismael|Salih|Mahnut|Faha|Hammad|Hozaifa|Ravil|Jehan|Abdah|Djamel|Sabir|Ruhani|Hisham|Rehman|Mesut|Mehdi|Lakhdar|Mourad|Fazal[a-z]*|Mukit|Jalil|Rustam|Jumm?a|Omar Ali)\b|(?:[bdfmtnrz]ullah|alludin|[hm]atulla|r[ao]llah|harudin|millah)\b|\b(?:Abd[aeu][lr]|Nazur| Al[- ][A-Z]| al-[A-Z]))"
)
_JuniorSenior = _R(r"^[SJsj]n?r\.$")


def make_human_cat_key(name: str, article_text: str) -> str:
    """Sort key for a person ("John Smith" -> "Smith, John"), following WP:NAMESORT."""
    site = current_site()
    name = remove_namespace_string(
        _TrailingBracketed.replace(clean_sort_key(name), "").replace("'", "").strip()
    ).strip()
    orig_name = name

    # ukwiki uses "Lastname Firstname Patronymic"; with {{Chinese name}} etc. the family name is
    # already first
    if (
        " " not in name
        or site.lang_code == "uk"
        or W.SurnameClarificationTemplates.is_match(article_text)
    ):
        return fixup_default_sort(orig_name)

    suffix, presuffix = "", " "
    pos = name.find(",")
    # ruwiki has "Lastname, Firstname Patronymic" convention
    if pos >= 0 and site.lang_code != "ru":
        suffix = name[pos + 1 :].strip()
        presuffix = ", "
        name = name[:pos].strip()

    # Arabic names etc. use "Full Name" format
    if _ArabicNames.is_match(orig_name):
        return fixup_default_sort(orig_name)

    # Person of Place --> Person Of Place, WP:NAMESORT. WordsOnly check avoids backtracking.
    if _WordsOnly.is_match(orig_name) and _PersonOfPlace.is_match(orig_name):

        def person_of_place(m: DotNetMatch) -> str:
            ordinal = m.group("ordinal")
            return (
                m.group("person")
                + (" " + roman_to_int(ordinal) if ordinal else "")
                + " of "
                + m.group("place")
            )

        return fixup_default_sort(_PersonOfPlace.replace(orig_name, person_of_place))

    int_last = name.rfind(" ") + 1
    last_name = name[int_last:].strip()
    if name:
        name = name[:int_last].strip()

    if is_roman_number(last_name) or _JuniorSenior.is_match(last_name):
        if " " in name:
            suffix += last_name  # no extra comma before suffix, so presuffix stays a space
            int_last = name.rfind(" ") + 1
            last_name = name[int_last:]
            name = name[:int_last].strip()
        else:
            # "Peter" "II" "King of Spain", or "Fred" "II": return what we started with
            return fixup_default_sort(orig_name)

    name = (last_name + ", " + (name + presuffix if name else "") + suffix).strip(" ,")
    return fixup_default_sort(name)


def roman_to_int(roman: str) -> str:
    """Roman numeral to a two-digit (at least) decimal string: "IV" -> "04"."""
    converted = 0
    for pair, value in (("IX", 9), ("IV", 4), ("XL", 40), ("XC", 90)):
        if pair in roman:
            converted += value
            roman = roman.replace(pair, "")
    converted += roman.count("C") * 100 + roman.count("L") * 50 + roman.count("X") * 10
    converted += roman.count("V") * 5 + roman.count("I")
    s = str(converted)
    return "0" + s if converted < 10 else s


def is_roman_number(s: str) -> bool:
    return bool(s) and len(s) <= 9 and all(c in "IVXLC" for c in s)


# -- namespaces and page names --------------------------------------------------------------------


def remove_namespace_string(title: str) -> str:
    if namespace.is_main_space(title):
        return title
    pos = title.find(":")
    return title if pos < 0 else title[pos + 1 :].strip()


def get_namespace_string(title: str) -> str:
    ns = namespace.determine(title)
    return "" if ns == 0 else current_site().namespaces[ns].replace(":", "")


def base_page_name(title: str) -> str:
    title = remove_namespace_string(title)
    i = title.find("/")
    return title if i < 0 else title[:i]


def sub_page_name(title: str) -> str:
    title = remove_namespace_string(title)
    i = title.rfind("/")
    return title if i < 0 else title[i + 1 :]


def apply_key_words(title: str, text: str, escape: bool = False) -> str:
    """Expand %%title%%, %%pagename%%, %%key%% etc. (escape: regex-escape the substituted values)."""
    if not text or not title or "%%" not in text:
        return text
    site = current_site()

    def esc(s: str) -> str:
        return rx.escape(s) if escape else s

    title_encoded = wiki_encode(title)
    text = text.replace("%%title%%", esc(title))
    text = text.replace("%%titlee%%", title_encoded)
    text = text.replace("%%fullpagename%%", esc(title))
    text = text.replace("%%fullpagenamee%%", title_encoded)
    text = text.replace("%%key%%", make_human_cat_key(title, text))

    title_no_namespace = remove_namespace_string(title)
    base = base_page_name(title)
    sub = sub_page_name(title)
    the_namespace = get_namespace_string(title)

    text = text.replace("%%pagename%%", esc(title_no_namespace))
    text = text.replace("%%pagenamee%%", wiki_encode(title_no_namespace))
    text = text.replace("%%basepagename%%", esc(base))
    text = text.replace("%%basepagenamee%%", wiki_encode(base))
    text = text.replace("%%namespace%%", the_namespace)
    text = text.replace("%%namespacee%%", wiki_encode(the_namespace))
    text = text.replace("%%subpagename%%", sub)
    text = text.replace("%%subpagenamee%%", wiki_encode(sub))
    text = text.replace("%%server%%", site.url)
    text = text.replace("%%scriptpath%%", site.script_path)
    return text.replace("%%servername%%", server_name(site.url))


def title_case_en(text: str) -> str:
    """English title case (TextInfo.ToTitleCase, en-GB): words already all upper-case are kept,
    unless the whole text is upper-case."""
    if text.upper() == text:
        text = text.lower()
    out: list[str] = []
    word: list[str] = []

    def flush() -> None:
        if word:
            w = "".join(word)
            letters = [c for c in w if is_letter(c)]
            if letters and all(c == char_upper(c) and c != char_lower(c) for c in letters):
                out.append(w)
            else:
                out.append(char_upper(w[0]) + "".join(char_lower(c) for c in w[1:]))
            word.clear()

    for c in text.strip():
        if is_letter(c) or (word and c in "'’"):
            word.append(c)
        else:
            flush()
            out.append(c)
    flush()
    return "".join(out)


def newline(s: str, n: int = 1) -> str:
    """s with n "\\r\\n" in front, or "" for empty s."""
    return "\r\n" * n + s if s else s


# -- counting -------------------------------------------------------------------------------------

_RegexWordCountTable = _R(r"\{\|.*?\|\}", O.SINGLELINE)


def word_count(text: str, limit: int = 999999) -> int:
    """Words outside tables, templates and comments, counting up to limit."""
    text = _RegexWordCountTable.replace(text, "")
    text = W.NestedTemplates.replace(text, " ")
    text = W.Comments.replace(text, "")
    words = 0
    i = 0
    n = len(text)
    while i < n:
        if not is_letter_or_digit(text[i]):
            i += 1
            while i < n and not is_letter_or_digit(text[i]):
                i += 1
        else:
            words += 1
            i += 1
            while i < n and is_letter_or_digit(text[i]):
                i += 1
            if words == limit:
                return words
    return words


def interwiki_count(text: str) -> int:
    languages = current_site().interwiki_languages
    links = [lnk for lnk in _wikilinks.get_all_wiki_links(text) if ":" in lnk]
    return sum(
        1 for s in links if W.PossibleInterwikis.match(s + "]]").group(1).lower() in languages
    )


_TemplatesGeneratingWikilinks = nested_template_regex(
    ["flagIOC", "speciesbox", "automatic taxobox"]
)


def link_count(text: str, limit: int = 9999999) -> int:
    """Number of mainspace wikilinks (plus templates known to generate links), up to limit."""
    res = 0
    if _templates.template_exists(
        _templates.get_all_templates(text), _TemplatesGeneratingWikilinks
    ):
        res = len(_TemplatesGeneratingWikilinks.matches(text))
        if res >= limit:
            return limit

    targets: dict[str, int] = {}
    for lnk in _wikilinks.get_all_wiki_links(text):
        target = (lnk[: lnk.index("|")] if "|" in lnk else lnk).strip("[]")
        targets[target] = targets.get(target, 0) + 1

    res += sum(count for target, count in targets.items() if namespace.is_main_space(target))
    return min(res, limit)


_DateSplit = _R(r"[|=\r\n()]+")


def dates_count(text: str) -> dict[DateLocale, int]:
    """How many ISO, international (day month) and American (month day) dates the text has."""
    s = _S()
    possible = [
        d for d in _DateSplit.split(text) if len(d) > 4 and any(c in "123456789" for c in d)
    ]
    DateLocale = _parsers.DateLocale
    return {
        DateLocale.ISO: sum(len(W.ISODatesQuick.matches(d)) for d in possible),
        DateLocale.INTERNATIONAL: sum(len(s.DayMonth.matches(d)) for d in possible),
        DateLocale.AMERICAN: sum(len(s.MonthDay.matches(d)) for d in possible),
    }


def _culture_sort_key(s: str) -> tuple[str, str]:
    # Approximates .NET's culture-aware List<string>.Sort(): case-insensitive first, then lower
    # case before upper case.
    return (s.casefold(), s.swapcase())


def duplicate_wiki_links(text: str) -> list[str]:
    """ "Target (count)" for each link target linked more than once, sorted."""
    s = _S()
    all_links = _wikilinks.get_all_wiki_links(text)

    # ignore links in commented out text etc.
    unformatted = " ".join(m.value for m in W.UnformattedText.matches(text))
    for lnk in (m.value for m in W.SimpleWikiLink.matches(unformatted)):
        if lnk in all_links:
            all_links.remove(lnk)

    # first letter upper so that [[proton]] and [[Proton]] count as the same
    counts: dict[str, int] = {}
    for lnk in all_links:
        target = turn_first_to_upper((lnk[: lnk.index("|")] if "|" in lnk else lnk).strip("[] "))
        counts[target] = counts.get(target, 0) + 1

    dupes = [
        f"{k} ({v})"
        for k, v in counts.items()
        if v > 1 and k and not s.Dates.is_match(k) and not s.Dates2.is_match(k)
    ]
    return sorted(dupes, key=_culture_sort_key)


# -- text helpers ---------------------------------------------------------------------------------


def remove_syntax(text: str) -> str:
    """Strip list markers, brackets and some entities from a line of a page list."""
    if not text:
        return text
    text = text.strip()
    if not text:
        return text
    if text[0] in "#*":
        text = text[1:]
    text = text.replace("_", " ").strip()
    text = text.strip("[]")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("�", "")
    return text.lstrip(":").strip()


_MetaId = _R(r'< *meta id *= *"[^"]+"')
_NgAttr = _R(r'\bng\-attr\-content *= *"{{[^"]+}}"')


def get_meta_content_value(page_source: str, meta_name: str) -> str:
    """Value of the HTML <meta name=... content=...> tag with the given name, or ""."""
    if not page_source or not meta_name:
        return ""
    page_source = page_source.replace("data-meta-updatable", "")
    page_source = page_source.replace('data-ephemeral="true"', "")
    page_source = page_source.replace('data-react-helmet="true"', "")
    page_source = _MetaId.replace(page_source, "<meta ")
    page_source = _NgAttr.replace(page_source, "")

    name = rx.escape(meta_name)
    meta_content = _R(
        r'< *meta +(?:xmlns="http://www\.w3\.org/1999/xhtml" +)?(?:name|property|itemprop) *= *(?:"|\')'
        + name
        + r'(?:"|\')[^<>/]+content *= *(?:"|\')([^"<>]+?)(?:"|\') */? *>',
        O.IGNORE_CASE,
    )
    meta_content2 = _R(
        r'< *meta +(?:xmlns="http://www\.w3\.org/1999/xhtml" +)?[^<>/]*content *= *(?:"|\')([^"<>]+?)(?:"|\') *(?:name|property) *= *(?:"|\')'
        + name
        + r'(?:"|\') */? *>',
        O.IGNORE_CASE,
    )
    m = meta_content.match(page_source)
    if m:
        return m.group(1).strip()
    return meta_content2.match(page_source).group(1).strip()


def split_to_sections(article_text: str) -> list[str]:
    """The text split before each heading; the last section gets an extra "\\r\\n"."""
    sections: list[str] = []
    last = 0
    for m in W.Headings.matches(article_text):
        if m.index > 0:  # no empty first section if the page starts with a heading
            sections.append(article_text[last : m.index])
        last = m.index
    sections.append(article_text[last:] + "\r\n")
    return sections


_HeadingStart = _R(r"^==", O.MULTILINE)


def get_zeroth_section(article_text: str) -> str:
    m = _HeadingStart.match(article_text)
    return article_text[: m.index] if m else article_text


def how_much_starts_with(text: str, items: DotNetRegex, allow_heading: bool) -> int:
    """Length of the text's start that is made of items matches (and whitespace), optionally
    after a first heading."""
    heading = 0
    if allow_heading:
        m = W.Headings.match(text)
        if m.index == 0:
            text = W.Headings.replace(text, "", 1)
            heading = m.length
    mc = items.matches(text)
    if not mc:
        return 0
    replaced = replace_with_spaces(text, mc).lstrip()
    return len(text) - len(replaced) + heading


def remove_matches(text: str, matches: Sequence[DotNetMatch]) -> str:
    """text without the given matches (which must come from text, in order)."""
    if not matches:
        return text
    out: list[str] = []
    pos = 0
    for m in matches:
        out.append(text[pos : m.index])
        pos = m.index + len(m.value)
    out.append(text[pos:])
    return "".join(out)


# -- diacritics and sort keys ---------------------------------------------------------------------

# fmt: off
Diacritics: tuple[tuple[str, str], ...] = ((r"Ɯ", r"W"), (r"ß", r"ss"), (r"Ŀ", r"L"), (r"ŀ", r"l"), (r"Ð", r"D"), (r"ð", r"d"), (r"Þ", r"Th"), (r"þ", r"th"), (r"Œ", r"Oe"), (r"œ", r"oe"), (r"Æ", r"Ae"), (r"æ", r"ae"), (r"Ə", r"E"), (r"ə", r"e"), (r"ĸ", r"k"), (r"ŉ", r"n"), (r"ſ", r"s"), (r"Ё", r"E"), (r"ё", r"e"), (r"б", r"b"), (r"л", r"l"), (r"К", r"K"), (r"к", r"k"), (r"М", r"M"), (r"м", r"m"), (r"Ӳ", r"Y"), (r"ӳ", r"y"), (r"о", r"o"), (r"О", r"O"), (r"а", r"a"), (r"А", r"A"), (r"с", r"c"), (r"С", r"C"), (r"е", r"e"), (r"Е", r"E"), (r"і", r"i"), (r"І", r"I"), (r"х", r"x"), (r"Х", r"X"), (r"Đ", r"D"), (r"đ", r"d"), (r"Ǣ", r"Ae"), (r"ǣ", r"ae"), (r"Ǽ", r"Ae"), (r"ǽ", r"ae"), (r"Ǿ", r"O"), (r"ǿ", r"o"), (r"ı", r"i"), (r"Ⱥ", r"A"), (r"ⱥ", r"a"), (r"Ƀ", r"B"), (r"ƀ", r"b"), (r"Ȼ", r"C"), (r"ȼ", r"c"), (r"Ɇ", r"E"), (r"ɇ", r"e"), (r"Ǥ", r"G"), (r"ǥ", r"g"), (r"Ħ", r"H"), (r"ħ", r"h"), (r"Ɨ", r"I"), (r"ɨ", r"i"), (r"Ɉ", r"J"), (r"ɉ", r"j"), (r"Ł", r"L"), (r"ł", r"l"), (r"Ø", r"O"), (r"ø", r"o"), (r"Ᵽ", r"P"), (r"ᵽ", r"p"), (r"Ɍ", r"R"), (r"ɍ", r"r"), (r"Ŧ", r"T"), (r"ŧ", r"t"), (r"Ʉ", r"U"), (r"ʉ", r"u"), (r"Ɏ", r"Y"), (r"ɏ", r"y"), (r"Ƶ", r"Z"), (r"ƶ", r"z"), (r"Ɓ", r"B"), (r"ɓ", r"b"), (r"Ƈ", r"C"), (r"ƈ", r"c"), (r"Ɗ", r"D"), (r"ɗ", r"d"), (r"Ƒ", r"F"), (r"ƒ", r"f"), (r"Ɠ", r"G"), (r"ɠ", r"g"), (r"ɦ", r"h"), (r"Ƙ", r"K"), (r"ƙ", r"k"), (r"Ɲ", r"N"), (r"ɲ", r"n"), (r"Ƥ", r"P"), (r"ƥ", r"p"), (r"ʠ", r"q"), (r"Ƭ", r"T"), (r"ƭ", r"t"), (r"Ʋ", r"V"), (r"ʋ", r"v"), (r"Ⱳ", r"W"), (r"ⱳ", r"w"), (r"Ƴ", r"Y"), (r"ƴ", r"y"), (r"ᶀ", r"b"), (r"ᶁ", r"d"), (r"ᶂ", r"f"), (r"ᶃ", r"g"), (r"ᶄ", r"k"), (r"ᶅ", r"l"), (r"ᶆ", r"m"), (r"ᶇ", r"n"), (r"ᶈ", r"p"), (r"ᶉ", r"r"), (r"ᶊ", r"s"), (r"ƫ", r"t"), (r"ᶌ", r"y"), (r"ᶍ", r"x"), (r"ᶎ", r"z"), (r"Ʈ", r"T"), (r"ʈ", r"t"), (r"ʐ", r"z"), (r"ƌ", r"d"), (r"ƚ", r"l"), (r"ƞ", r"n"), (r"ȡ", r"d"), (r"ȥ", r"z"), (r"ȴ", r"l"), (r"ȵ", r"n"), (r"ȶ", r"t"), (r"ȿ", r"s"), (r"ɀ", r"z"), (r"Ɖ", r"D"), (r"ɖ", r"d"), (r"Ƌ", r"D"), (r"Ǝ", r"E"), (r"Ɛ", r"E"), (r"Ɵ", r"O"), (r"ɵ", r"o"), (r"ǅ", r"Dz"), (r"ǈ", r"Lj"), (r"ǋ", r"Nj"), (r"ǝ", r"e"), (r"ǲ", r"Dz"), (r"Ƞ", r"N"), (r"Ȥ", r"Z"), (r"Ƚ", r"L"), (r"Ⱦ", r"T"), (r"Ⱡ", r"L"), (r"ⱡ", r"l"), (r"Ɫ", r"L"), (r"Ɽ", r"R"), (r"ⱦ", r"t"), (r"Ⱨ", r"H"), (r"ⱨ", r"h"), (r"Ⱪ", r"K"), (r"ⱪ", r"k"), (r"Ⱬ", r"Z"), (r"ⱬ", r"z"), (r"ⱴ", r"v"), (r"ẚ", r"a"), (r"²", r"2"), (r"Ŋ", r"N"), (r"ŋ", r"n"), (r"ﬂ", r"fl"), (r"ǉ", r"lg"), (r"ǌ", r"ng"), (r"№", r"No"))
SortKeyChars: tuple[tuple[str, str], ...] = ((r"&", r"and"), (r"/", r" "), (r"×", r"x"), (r"ǀ", r""), (r"…", r"..."), (r"·", r" "), (r"’", r"'"), (r"‘", r"'"), (r"ʻ", r"'"), (r"`", r"'"), (r"´", r"'"), (r"′", r"'"), (r"ʹ", r"'"), (r"“", r"'"), (r"”", r"'"), (r"„", r"'"), (r"‟", r"'"), (r"–", r"-"), (r"—", r"-"), (r"‐", r"-"), (r"‑", r"-"), (r"‒", r"-"), (r"−", r"-"), (r"¡", r""), (r"¿", r""), (r"ʾ", r"'"), (r"ʿ", r"'"), (r"̧ ", r""))
# fmt: on


def remove_diacritics(s: str) -> str:
    for a, b in Diacritics:
        s = s.replace(a, b)
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def has_diacritics(s: str) -> bool:
    return s != remove_diacritics(s)


_BadDsChars = _R(r"[\"º]")
_NameComma = _R(r"(\w) *,(\w)")


def fixup_default_sort(defaultsort: str, is_article_about_a_person: bool = False) -> str:
    defaultsort = clean_sort_key(defaultsort)
    defaultsort = _BadDsChars.replace(defaultsort, "")
    if is_article_about_a_person:
        defaultsort = defaultsort.replace("'", "")
        defaultsort = _NameComma.replace(defaultsort, "$1, $2")  # space after comma between names
    if current_site().is_wikipedia_en and defaultsort.startswith("List of "):
        defaultsort = turn_first_to_upper_no_project_check(defaultsort.replace("List of ", ""))
    return defaultsort.strip()


def clean_sort_key(defaultsort: str) -> str:
    # no diacritic removal on wikis using Unicode (uca-*) category collation, e.g. fr/pl/ru
    if not current_site().unicode_category_collation:
        defaultsort = remove_diacritics(defaultsort)
    defaultsort = defaultsort.replace("&ndash;", "–")
    defaultsort = defaultsort.replace("&mdash;", "—")
    while "  " in defaultsort:
        defaultsort = defaultsort.replace("  ", " ")
    # skip when tags are present, to avoid e.g. removing the slash of a closing tag
    if not W.AllTags.is_match(defaultsort):
        for a, b in SortKeyChars:
            defaultsort = defaultsort.replace(a, b)
    return defaultsort


def deduplicate_list(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


_WholeLine = _R(r"^(.*)$(?<!^\s*$)", O.MULTILINE)
_HtmlBr = _R("<br ?/?>", O.IGNORE_CASE)
_HtmlListTags = _R("</?(ol|ul|li)>", O.IGNORE_CASE)
_HtmlListTagLine = _R("^</?(ol|ul|li)>\r\n", O.MULTILINE | O.IGNORE_CASE)
_ListMarkers = _R(r"^(\:|\*|#|\(? ?\d{1,3}\b ?\)|\d{1,3}\b\.?)", O.MULTILINE)


def html_list_to_wiki(text: str, bullet: str) -> str:
    """HTML or plain list lines to wiki list lines starting with bullet."""
    text = text.replace("\r\n\r\n", "\r\n")
    text = _HtmlBr.replace(text, "")
    text = _HtmlListTags.replace(text, "")
    text = _HtmlListTagLine.replace(text, "")
    text = _ListMarkers.replace(text, "")
    # bullet on every line except empty or whitespace-only ones
    return _WholeLine.replace(text, lambda m: bullet + " " + m.group(1).lstrip())


def is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
    except ValueError:
        return False
    return True


def string_between(source: str, start: str, end: str) -> str:
    # Same arithmetic as AWB, including when start is missing (find() returns -1).
    start_pos = source.find(start) + len(start)
    end_pos = source.find(end)
    if start_pos >= 0 and end_pos >= 0 and start_pos <= end_pos:
        return source[start_pos:end_pos]
    return ""


def replace_part_of_string(source: str, position: int, length: int, replace: str) -> str:
    return source[:position] + replace + source[position + length :]


def replace_once(text: str, old: str, new: str) -> tuple[str, bool]:
    """Replace the first occurrence; returns (text, whether anything was replaced).

    AWB modifies a ref string or StringBuilder in place; Python strings are immutable.
    """
    index = text.find(old)
    if index < 0:
        return text, False
    return text[:index] + new + text[index + len(old) :], True


_DIFF_EDIT_URL = r"/w(?:(?:iki)?/index\.php5?\?|/\?)title=(.*?)(?:&(?:action|diff|oldid|pe|offset|curid|redirect|type)=.*|$)"
_HttpScheme = _R(r"https?://")


def normalize_title_core(s: str) -> str:
    """A page title from a wiki URL (history/diff/edit or /wiki/ form) or a section link.

    Port of ListMaker.NormalizeTitleCore (WikiFunctions/Controls/Lists/ListMaker.cs).
    """
    site = current_site()
    original = s
    history_diff = _R(
        _HttpScheme.replace(rx.escape(site.url), "(?:https?://|//)?") + _DIFF_EDIT_URL
    )
    s = history_diff.replace(s, lambda m: m.group(1).replace("+", "_"))
    # assumption flaw (AWB's): every wiki uses /wiki/ as its article path
    if "https:" in site.url:
        s = s.replace("http://", "https://")  # support HTTP and HTTPS links
    s = s.replace(site.url + "/wiki/", "").strip()
    # section links
    if s.find("#") > 0:
        s = s[: s.index("#")]
    if original != s:
        s = wiki_decode(s)
    # left-to-right marks
    return s.replace("\u200e", "").strip()


def first_chars(s: str, count: int) -> str:
    return s if len(s) <= count else s[:count]


def convert_to_local_line_endings(text: str) -> str:
    """\\n to AWB's internal \\r\\n (Environment.NewLine on Windows, where AWB ran)."""
    return text.replace("\n", "\r\n")


def convert_from_local_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n")


def server_name(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def get_title_from_url(link: str) -> str | None:
    """Page title from a URL of the current wiki, or None."""
    link = _S().ExtractTitle.match(link).group(1)
    return wiki_decode(link) if link else None


def first_to_upper_and_remove_hash_on_array(items: list[str] | None) -> list[str] | None:
    if items is None:
        return None
    return [turn_first_to_upper(remove_hash_from_page_title(s.strip("[] \t"))) for s in items]


def split_lines(source: str) -> list[str]:
    """Split on \\r\\n, \\n or \\r. No empty last element for a trailing line break."""
    res: list[str] = []
    pos = 0
    n = len(source)
    while pos < n:
        eol = -1
        for j in range(pos, n):
            if source[j] in "\r\n":
                eol = j
                break
        if eol < 0:
            res.append(source[pos:])
            pos = n
        else:
            res.append(source[pos:eol])
            ch = source[eol]
            eol += 1
            if ch == "\r" and eol < n and source[eol] == "\n":
                eol += 1
            pos = eol
    return res


def unformatted_text_not_changed(original_article_text: str, article_text: str) -> bool:
    """Whether every comment/nowiki/pre/math block in the new text was already in the old one."""
    if original_article_text == article_text:
        return True
    after = [m.value for m in W.UnformattedText.matches(article_text)]
    if not after:
        return True
    for s in (m.value for m in W.UnformattedText.matches(original_article_text)):
        if s in after:
            after.remove(s)
    return not after


def convert_to_talk(title: str) -> str:
    site = current_site()
    ns = namespace.determine(title)
    if namespace.is_special(ns) or namespace.is_talk(ns):
        return title
    if ns == Namespace.ARTICLE:
        return site.namespaces[Namespace.TALK] + title
    return site.namespaces[ns + 1] + remove_namespace_string(title)


def convert_from_talk(title: str) -> str:
    site = current_site()
    ns = namespace.determine(title)
    if namespace.is_talk(ns):
        if ns == Namespace.TALK:
            return remove_namespace_string(title)
        return site.namespaces[ns - 1] + remove_namespace_string(title)
    return title


def convert_to_talk_list(titles: Iterable[str]) -> list[str]:
    return [convert_to_talk(t) for t in titles]


def convert_from_talk_list(titles: Iterable[str]) -> list[str]:
    return [convert_from_talk(t) for t in titles]


def convert_namespace(title: str, new_namespace: int) -> str:
    site = current_site()
    if namespace.is_special(namespace.determine(title)) or new_namespace not in site.namespaces:
        return title
    return site.namespaces[new_namespace] + remove_namespace_string(title)


def filter_some_articles(titles: Iterable[str]) -> list[str]:
    """Drop special pages, MediaWiki: pages and Commons: titles; deduplicate."""
    items: list[str] = []
    for t in titles:
        ns = namespace.determine(t)
        if (
            ns >= Namespace.ARTICLE
            and ns not in (Namespace.MEDIAWIKI, Namespace.MEDIAWIKI_TALK)
            and not t.startswith("Commons:")
            and t not in items
        ):
            items.append(t)
    return items


def build_post_data_string(postvars: Mapping[str, str]) -> str:
    return "&".join(f"{k}={url_encode(v)}" for k, v in postvars.items())


# -- replacing matches with filler characters -----------------------------------------------------


def replace_with(
    text: str,
    matches: Iterable[DotNetMatch] | DotNetRegex,
    rwith: str,
    keep_group: int = 0,
) -> str:
    """text with each match overwritten by rwith characters, keeping its length (and optionally
    the text of group keep_group)."""
    if isinstance(matches, DotNetRegex):
        matches = matches.matches(text)
    out: list[str] = []
    length = 0
    for m in matches:
        out.append(text[length : m.index])
        length = m.index
        if keep_group < 1 or not m.group(keep_group):
            out.append(rwith * m.length)
        else:
            g_start = m.start(keep_group)
            g_value = m.group(keep_group)
            out.append(rwith * (g_start - m.index))
            out.append(g_value)
            out.append(rwith * (m.index + m.length - g_start - len(g_value)))
        length = m.index + m.length
    out.append(text[length:])
    return "".join(out)


def replace_with_spaces(
    text: str, matches: Iterable[DotNetMatch] | DotNetRegex, keep_group: int = 0
) -> str:
    return replace_with(text, matches, " ", keep_group)


# -- dates ----------------------------------------------------------------------------------------

_YearMon = _R(r"^\d{4}\-[0-3]\d$")
_MonthYear = _R(r"^\w+ \d{4}$")
_MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        (
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
        ),
        start=1,
    )
}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})
_MONTHS["sept"] = 9
_DateShape = rx.compile(r"^[\s,./-]*(?:(?:[^\W\d_]+\.?|\d+)[\s,./-]*)+$")
_DateToken = rx.compile(r"[^\W\d_]+|\d+")


def _parse_date(text: str, american: bool = False) -> datetime.date | None:
    """Parse a date roughly as Convert.ToDateTime does for en-GB (or en-US if american).

    Accepts numeric day/month/year (or month/day/year), ISO year-month-day, and dates with an
    English month name or abbreviation in any order. Two-digit years: 00-49 -> 20xx, 50-99 -> 19xx.
    """
    text = text.strip()
    if not _DateShape.match(text):
        return None
    tokens = _DateToken.findall(text)
    names = [t for t in tokens if not t.isdigit()]
    numbers = [t for t in tokens if t.isdigit()]
    if any(t.lower() not in _MONTHS for t in names) or len(names) > 1:
        return None

    def year_of(t: str) -> int:
        y = int(t)
        if len(t) <= 2:
            y += 2000 if y <= 49 else 1900
        return y

    try:
        if names:
            month = _MONTHS[names[0].lower()]
            if len(numbers) == 2:
                if len(numbers[0]) >= 3:
                    year, day = year_of(numbers[0]), int(numbers[1])
                else:
                    day, year = int(numbers[0]), year_of(numbers[1])
            elif len(numbers) == 1:
                if len(numbers[0]) >= 3:
                    year, day = year_of(numbers[0]), 1
                else:
                    year, day = datetime.date.today().year, int(numbers[0])
            else:
                return None
        elif len(numbers) == 3:
            a, b, c = numbers
            if len(a) >= 3:
                year, month, day = year_of(a), int(b), int(c)
            elif american:
                month, day, year = int(a), int(b), year_of(c)
            else:
                day, month, year = int(a), int(b), year_of(c)
        else:
            return None
        return datetime.date(year, month, day)
    except ValueError:
        return None


_MONTH_NAMES = (
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


def convert_date(input_date: str, locale: DateLocale, american_input_date: bool = False) -> str:
    """Reformat an English date for the given locale; unparseable input is returned (trimmed)."""
    input_date = input_date.strip()
    if (
        current_site().lang_code != "en"
        or _YearMon.is_match(input_date)
        or _MonthYear.is_match(input_date)
    ):
        return input_date
    dt = _parse_date(input_date, american_input_date)
    if dt is None:
        return input_date
    month = _MONTH_NAMES[dt.month - 1]
    DateLocale = _parsers.DateLocale
    match locale:
        case DateLocale.AMERICAN:
            return f"{month} {dt.day}, {dt.year:03d}"
        case DateLocale.INTERNATIONAL:
            return f"{dt.day} {month} {dt.year:03d}"
        case DateLocale.ISO:
            return f"{dt.year:03d}-{dt.month:02d}-{dt.day:02d}"
        case _:
            return input_date


def date_before_today(date: str) -> bool:
    """Whether the date (an English date, optionally ISO with a time) is before today."""
    text = date.strip()
    try:
        dt = datetime.datetime.fromisoformat(text).date()
    except ValueError:
        parsed = _parse_date(text)
        if parsed is None:
            return False
        dt = parsed
    return dt < datetime.date.today()


# -- template parameters --------------------------------------------------------------------------

_Bars = _R(r"\|")
_AfterSpacedBars = _R(r"\| ")
_BeforeSpacedBars = _R(r" +\|")
_Newlines = _R("\r\n")
_SpacedEquals = _R(" = ")
_EqualsSpace = _R("= ")
_TightEquals = _R(r"\S=\S")


def append_parameter_to_template(
    template_call: str, parameter: str, new_value: str, unspaced: bool = False
) -> str:
    """Add "|parameter=new_value" before the closing }}, following the call's spacing style."""
    if not template_call.startswith("{{"):
        return template_call
    separator_before = separator_after = ""
    equals_format = "="

    if not unspaced:
        copy = "{{" + replace_with_spaces(template_call[2:], W.NestedTemplates)
        copy = replace_with_spaces(copy, W.SimpleWikiLink)
        copy = replace_with_spaces(copy, W.UnformattedText)

        bars = len(_Bars.matches(copy))
        newlines = len(_Newlines.matches(copy))

        # use a newline if > 2 newlines and a newline per bar, allowing up to two without
        if newlines > 2 and newlines >= bars - 2:
            separator_before = "\r\n"
            spaces_before_bar = len(_BeforeSpacedBars.match(copy).value) - 1
            if spaces_before_bar >= 1:
                separator_before += _BeforeSpacedBars.match(copy).value.rstrip("|")
        else:
            before_spaced_bars = len(_BeforeSpacedBars.matches(copy))
            separator_before = "" if bars > 3 and before_spaced_bars <= 2 else " "

        after_spaced_bars = len(_AfterSpacedBars.matches(copy))
        separator_after = "" if bars > 3 and after_spaced_bars <= 2 else " "

        spaced = len(_SpacedEquals.matches(copy))
        tight = len(_TightEquals.matches(copy))
        if spaced >= 3 and spaced > tight:
            equals_format = " = "
        elif len(_EqualsSpace.matches(copy)) >= 3 and len(_EqualsSpace.matches(copy)) > tight:
            equals_format = "= "

    # new_value is literal text; escape "$" for the .NET replacement string
    value = (
        separator_before + "|" + separator_after + parameter + equals_format + new_value
    ).replace("$", "$$")
    return W.TemplateEnd.replace(template_call, value + "$1}}")


def get_template_parameter_value(
    template_call: str, parameter: str, case_insensitive_parameter_name: bool = False
) -> str:
    """Trimmed value of the named parameter, or ""."""
    options = O.SINGLELINE | (O.IGNORE_CASE if case_insensitive_parameter_name else O.NONE)
    param_regex = _R(r"\|\s*" + rx.escape(parameter) + r"\s*=([^|]*?)(?=\||}}$)", options)
    m = param_regex.match(pipe_cleaned_template(template_call))
    if m:
        start = m.start(1)
        return template_call[start : start + len(m.group(1))].strip()
    return ""


_param = _R(r"\|\s*([\w0-9_ -/]+?)\s*=([^|}]*)")


def get_template_parameter_values(template_call: str) -> dict[str, str]:
    """Named parameters and their values (first occurrence of each)."""
    found: dict[str, str] = {}
    for m in _param.matches(pipe_cleaned_template(template_call)):
        name = m.group(1)
        if name not in found:
            start = m.start(2)
            found[name] = template_call[start : start + len(m.group(2))].strip()
    return found


def get_template_parameters_values(
    template_call: str, parameters: Iterable[str], case_insensitive_parameter_names: bool = False
) -> list[str]:
    return [
        get_template_parameter_value(template_call, p, case_insensitive_parameter_names)
        for p in parameters
    ]


_arg = _R(r"\|\s*(.*?)\s*(?=\||}}$)", O.SINGLELINE)
_TemplateArgument = _R(r"\|\s*([^{}\|]*?)\s*(?=\||}}$)")


def get_template_argument(template_call: str, argument: int) -> str:
    """The argument-th argument (1-based, named or not) as written, or ""."""
    for count, m in enumerate(_arg.matches(pipe_cleaned_template(template_call)), start=1):
        if count == argument:
            start = m.start(1)
            return template_call[start : start + len(m.group(1))]
    return ""


def get_template_argument_index(template_call: str, argument: int) -> int:
    for count, m in enumerate(
        _TemplateArgument.matches(pipe_cleaned_template(template_call)), start=1
    ):
        if count == argument:
            return m.index + 1
    return -1


def get_template_argument_count(template: str, populated_parameters_only: bool = False) -> int:
    i = 0
    for m in _TemplateArgument.matches(pipe_cleaned_template(template)):
        value = m.group(1)
        if not populated_parameters_only or ("=" in value and not value.endswith("=")):
            i += 1
    return i


def rename_template_parameter(
    template_call: str,
    old_parameter: str | Sequence[str] | Mapping[str, str],
    new_parameter: str = "",
) -> str:
    """Rename a parameter (or any of a list of names) to new_parameter; with a mapping, rename
    each key to its value. Parameters of nested templates are left alone."""
    if isinstance(old_parameter, Mapping):
        for old, new in old_parameter.items():
            template_call = rename_template_parameter(template_call, old, new)
        return template_call
    if isinstance(old_parameter, str):
        old = rx.escape(old_parameter)
    else:
        old = "(?:" + "|".join(rx.escape(p) for p in old_parameter) + ")"
    param_regex = _R(r"(\|\s*(?:<!--.*?-->)?)" + old + r"(\s*(?:<!--.*?-->\s*)?=)")

    nested = W.NestedTemplates.matches("  " + template_call[2:])

    def rename(m: DotNetMatch) -> str:
        for n in nested:
            if n.index > 0 and n.index <= m.index <= n.index + n.length:
                return m.value
        return m.group(1) + new_parameter + m.group(2)

    return param_regex.replace(template_call, rename)


def remove_template_parameter(
    text: str, name_or_parameter: str, parameter_or_last: str | bool = False
) -> str:
    """Two AWB overloads:

    remove_template_parameter(template_call, parameter, remove_last_match=False) removes the
    parameter from one template call (the last occurrence if remove_last_match);
    remove_template_parameter(article_text, template_name, parameter) removes it from every call
    of the named template.
    """
    if isinstance(parameter_or_last, str):
        return nested_template_regex(name_or_parameter).replace(
            text, lambda m: remove_template_parameter(m.value, parameter_or_last)
        )
    template_call, parameter, remove_last_match = text, name_or_parameter, parameter_or_last
    param_regex = _R(r"\|\s*" + rx.escape(parameter) + r"\s*=(.*?)(?=\||}}$)", O.SINGLELINE)
    cleaned = pipe_cleaned_template(template_call)
    m = param_regex.match(cleaned)
    if m:
        if remove_last_match:
            m = param_regex.matches(cleaned)[-1]
        return template_call[: m.index] + template_call[m.index + m.length :]
    return template_call


def remove_template_parameters(template_call: str, parameters: Iterable[str]) -> str:
    for p in parameters:
        template_call = remove_template_parameter(template_call, p, False)
    return template_call


_CiteUrl = _R(r'\|\s*url\s*=\s*([^\[\]<>"\s]+)')
_anyParam = _R(r"\|\s*([^{}\|<>\r\n=]+)\s*=\s*([^}|]*)(?=\||}}$)")
_EndsWithDigit = _R(r".[0-9]$")


def remove_duplicate_template_parameters(
    template_call: str, template_params: dict[str, str] | None = None
) -> str:
    """Remove repeated parameters whose values are equal or blank. template_params, if given, is
    filled with the remaining parameters and values."""
    params: dict[str, str] = {} if template_params is None else template_params
    original = template_call
    updated = ""
    while updated != template_call:
        params.clear()
        cleaned = pipe_cleaned_template(template_call)
        updated = template_call
        for m in _anyParam.matches(cleaned):
            start = m.start(2)
            value = template_call[start : start + len(m.group(2))].strip()
            name = m.group(1).strip()
            if name not in params:
                params[name] = value
                continue
            # names ending in a digit (e.g. last2) more likely need renaming than removing
            if _EndsWithDigit.is_match(name):
                continue
            earlier = params[name]
            if value == earlier or not value or not earlier:
                template_call = remove_template_parameter(template_call, name, not value)
                break

    # don't break URLs with unescaped pipes
    if template_call != original:
        original_url = _CiteUrl.match(original).group(1).rstrip("|")
        if original_url and _CiteUrl.match(template_call).group(1) != original_url:
            return original
    return template_call


def duplicate_template_parameters(template_call: str) -> dict[int, int]:
    """Index -> length of every repeated parameter."""
    dupes: dict[int, int] = {}
    params: dict[str, str] = {}
    for m in _anyParam.matches(pipe_cleaned_template(template_call)):
        start = m.start(2)
        value = template_call[start : start + len(m.group(2))].strip()
        name = m.group(1).strip()
        if name not in params:
            params[name] = value
        else:
            dupes[m.index] = m.length
    return dupes


_SpacedPipes = _R(r"(\|\s*)(?:\||}})")


def remove_excess_template_pipes(template_call: str) -> str:
    """Remove empty parameters ("| |" and "| }}")."""
    if not _SpacedPipes.is_match(template_call):
        return template_call
    original_url = _CiteUrl.match(template_call).group(1).rstrip("|")
    original = template_call
    cleaned = pipe_cleaned_template(template_call)
    while True:
        m = _SpacedPipes.match(cleaned)
        if not m:
            break
        template_call = template_call[: m.index] + template_call[m.index + len(m.group(1)) :]
        cleaned = pipe_cleaned_template(template_call)
    if original_url and _CiteUrl.match(template_call).group(1) != original_url:
        return original
    return template_call


def unknown_template_parameters(template_call: str, known_parameters: Iterable[str]) -> list[str]:
    known = set(known_parameters)
    return [
        name
        for m in _anyParam.matches(pipe_cleaned_template(template_call))
        if (name := m.group(1).strip()).lower() not in known
    ]


_StartWhitespace = _R(r"^\s+")


def update_template_parameter_value(template_call: str, parameter: str, new_value: str) -> str:
    """Replace the value of an existing parameter; the call is unchanged if it has none."""
    # Tildes around the name stand for cleaned HTML comments (see pipe_cleaned_template).
    param_regex = _R(
        r"\|[\s~]*" + rx.escape(parameter) + r"[\s~]*= *\s*?(.*?)\s*(?=(?:\||}}$))", O.SINGLELINE
    )
    m = param_regex.match(pipe_cleaned_template(template_call, True))
    if m:
        start, length = m.start(1), len(m.group(1))
        # keep newlines at the start of the value if the existing parameter has a value
        start_newline = _StartWhitespace.match(m.group(1)).value
        if start_newline and m.group(1).strip():
            new_value = start_newline + new_value
        return template_call[:start] + new_value + template_call[start + length :]
    return template_call


def merge_template_parameters_values(
    template_call: str,
    parameters: Iterable[str],
    new_parameter: str,
    case_insensitive_parameter_names: bool = False,
) -> str:
    combined = ""
    for p in parameters:
        combined += get_template_parameter_value(template_call, p) + " "
        template_call = remove_template_parameter(template_call, p, False)
    return append_parameter_to_template(template_call, new_parameter, combined, False)


_REP_WITH = "#"
_SingleSquareBrackets = _R(
    r"\[((?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\])", O.EXPLICIT_CAPTURE
)


def pipe_cleaned_template(template_call: str, comments_as_tilde: bool = False) -> str:
    """The call with everything that may contain pipes other than parameter separators (nested
    templates, links, tags, comments) overwritten, keeping all offsets the same."""
    if len(template_call) < 5:
        return template_call
    rest = template_call[3:]
    if "{{" in rest:
        rest = replace_with(rest, W.NestedTemplates, _REP_WITH)
    if "[[" in rest:
        rest = replace_with(rest, W.SimpleWikiLink, _REP_WITH)
    if "[" in rest:
        rest = replace_with(rest, _SingleSquareBrackets, _REP_WITH)
    if "<" in rest:
        rest = (
            replace_with(rest, W.Comments, "~")
            if comments_as_tilde
            else replace_with_spaces(rest, W.Comments)
        )
        rest = replace_with(rest, W.AllTags, _REP_WITH)
        rest = replace_with(rest, W.Refs, _REP_WITH)
    return template_call[:3] + rest


def add_template_parameter_value(
    template_call: str, parameter: str, value: str, prepend_space: bool
) -> str:
    """Set the parameter only if the call does not have it yet."""
    if parameter in get_template_parameter_values(template_call):
        return template_call
    return set_template_parameter_value(template_call, parameter, value, prepend_space)


def set_template_parameter_value(
    template_call: str, parameter: str, new_value: str, prepend_space: bool = False
) -> str:
    """Update the parameter's value, or append the parameter if the call does not have it."""
    if get_template_parameter_value(template_call, parameter) == new_value:
        return template_call
    if prepend_space:
        new_value = " " + new_value
    updated = update_template_parameter_value(template_call, parameter, new_value)
    if updated == template_call:
        updated = append_parameter_to_template(template_call, parameter, new_value)
    return updated


_WhitespaceRun = _R(r"[\s_]+")


def get_template_name(template_call: str) -> str:
    name = _S().TemplateNameRegex.match(template_call).group(1)
    return _WhitespaceRun.replace(name, " ").strip()


def _rename_template_me(m: DotNetMatch, new_name: str, keep_first_letter_case: bool) -> str:
    original = m.group(2)
    if keep_first_letter_case and not new_name.startswith("subst:"):
        new_name = (
            turn_first_to_upper(new_name)
            if turn_first_to_upper(original) == original
            else turn_first_to_lower(new_name)
        )
    return m.group(1) + new_name + m.group(3)


def rename_template(text: str, a: str, b: str | bool | None = None, c: bool | int = True) -> str:
    """AWB's RenameTemplate overloads:

    rename_template(article_text, template_name, new_name, keep_first_letter_case=True)
    rename_template(article_text, template_name, new_name, count: int)
    rename_template(template_call, new_name, keep_first_letter_case=True)
    """
    if b is None or isinstance(b, bool):
        keep = True if b is None else b
        return nested_template_regex(get_template_name(text)).replace(
            text, lambda m: _rename_template_me(m, a, keep)
        )
    if isinstance(c, bool):
        return nested_template_regex(a).replace(text, lambda m: _rename_template_me(m, b, c))
    return nested_template_regex(a).replace(text, "$1" + b.replace("$", "$$") + "$3", c)


def is_section_or_reason_template(template_call: str, article_text: str = "") -> bool:
    return (
        (
            W.NestedTemplates.is_match(template_call)
            and get_template_argument(template_call, 1) == "section"
        )
        or get_template_parameter_value(W.MultipleIssues.match(article_text).value, "section")
        == "y"
        or len(get_template_parameter_value(template_call, "reason", True)) > 0
    )


def sort_dictionary_pairs(pairs: Mapping[str, str], order: Sequence[str]) -> dict[str, str]:
    """pairs reordered: keys in order first (in that order), then the rest as they were."""
    position = {k: i for i, k in enumerate(order)}
    return dict(sorted(pairs.items(), key=lambda kv: position.get(kv[0], len(position))))


def sort_template_call_parameters(template_call: str, order: Sequence[str]) -> str:
    existing = get_template_parameter_values(template_call)
    new_template = remove_template_parameters(template_call, list(existing))
    for k, v in sort_dictionary_pairs(existing, order).items():
        new_template = append_parameter_to_template(new_template, k, v)
    return new_template


_LowerMagicWordTemplates = nested_template_regex(["namespace", "numberofarticles", "padleft"])


def template_to_magic_word(article_text: str) -> str:
    """{{PAGENAME}} etc. used as templates with arguments -> magic words ({{PAGENAME:foo}})."""

    def me(m: DotNetMatch) -> str:
        if get_template_argument_count(m.value) == 0:
            return m.value
        # namespace, numberofarticles, padleft must be lowercase, others must be UPPERCASE
        name = (
            m.group(2).lower()
            if _LowerMagicWordTemplates.is_match(m.value.lower())
            else m.group(2).upper()
        )
        return "{{" + name + ":" + m.group(3).strip().lstrip("|")

    return W.MagicWordTemplates.replace(article_text, me)


def list_to_string_comma_separator(items: Iterable[str]) -> str:
    sep = "، " if current_site().lang_code in ("ar", "arz", "fa") else ", "
    return sep.join(items)


def list_to_string_with_separator_and_word_suffix(
    items: Sequence[str], separator: str, suffix: str, last_separator: str
) -> str:
    ret = ""
    for i, item in enumerate(items):
        ret += item + suffix + (last_separator if i + 1 == len(items) else separator)
    return ret


def unescape_xml(s: str) -> str:
    if not s:
        return s
    return (
        s.replace("&apos;", "'")
        .replace("&quot;", '"')
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
    )


def re_add_diacritics(with_diacritics: str, without_diacritics: str) -> str:
    """Put diacritics back into words of without_diacritics that occur in with_diacritics."""
    for m in W.RegexWordApostrophes.matches(with_diacritics):
        word = _R(r"\b" + rx.escape(remove_diacritics(m.value)) + r"\b")
        # only when unambiguous: the plain word occurs exactly once
        if len(word.matches(without_diacritics)) == 1:
            without_diacritics = word.replace(without_diacritics, m.value)
    return without_diacritics


def get_md5_sum(text: str) -> str:
    """MD5 hex digest of the text's UTF-8 bytes (AWB used the Windows ANSI code page)."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()
