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
# Ported from AutoWikiBrowser WikiFunctions/Parse/WikiLinks.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Wikilink fixes of Parsers (port of Parse/WikiLinks.cs)."""

# ruff: noqa: E501

from __future__ import annotations

import functools
import unicodedata

from awb_l.core import namespace, rx
from awb_l.core import wikiregexes as W
from awb_l.core.rx import DotNetMatch, DotNetRegex
from awb_l.core.site import Namespace, SiteConfig, current_site
from awb_l.core.textutil import (
    first_letter_case_insensitive,
    nested_template_regex,
    turn_first_to_lower,
    turn_first_to_upper,
    turn_first_to_upper_no_project_check,
)

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

_EN_MONTHS_NO_GROUP = W.for_site(SiteConfig.english()).MonthsNoGroup  # AWB static init: English

_LinkWhitespace1 = _R(r"(.|^)\[\[ +([^\]]+)\]\]", O.MULTILINE)
_LinkWhitespace3 = _R(r"\[\[([^\]]{1,50}?) {2,10}([^\]]{1,50})\]\]")
_LinkWhitespace4 = _R(r"\[\[([^\]\|]{1,30}) \]\](\s)")
_LinkWhitespace5 = _R(r"\[\[([^\]]{1,30}) \]\](?=\w)")
_DateLinkWhitespace = _R(
    r"(?<=\b\[\[(?:\d\d? "
    + _EN_MONTHS_NO_GROUP
    + r"|"
    + _EN_MONTHS_NO_GROUP
    + r" \d\d?)\]\](?:,|,?  ))(\[\[\d{1,4}\]\])\b",
    O.IGNORE_CASE,
)
_SectionLinkWhitespace = _R(r"(\[\[[^\[\]\|]+)(?: +# *| *# +)([^\[\]]+\]\])(?<!\[\[[ACFJ]# .*)")
_WordChar = _R(r"\w")


def fix_link_whitespace(article_text: str, article_title: str) -> str:
    """Remove stray spaces inside wikilinks ([[ foo]], [[foo  bar]], [[foo ]]bar, [[a #b]])."""
    # performance: only run the regexes when some link needs them
    links = list(dict.fromkeys(get_all_wiki_links(article_text)))

    if any(s.startswith("[[ ") for s in links):
        # space from the start of the link; put it before the link if a word character precedes
        def leading(m: DotNetMatch) -> str:
            before = m.group(1)
            if _WordChar.is_match(before):
                before += " "
            return before + "[[" + m.group(2) + "]]"

        article_text = _LinkWhitespace1.replace(article_text, leading)

    # double spaces inside the link (links of up to 101 characters)
    if any("  " in s for s in links):
        while _LinkWhitespace3.is_match(article_text):
            article_text = _LinkWhitespace3.replace(article_text, "[[$1 $2]]")

    # underscore before hash
    if any("_#" in s for s in links):
        article_text = W.WikiLinksOnlyPossiblePipe.replace(
            article_text, lambda m: m.value.replace("_#", "#")
        )

    if any(s.endswith(" ]]") for s in links):
        # space at the end of the link (with whitespace after the link) - first
        article_text = _LinkWhitespace4.replace(
            article_text, lambda m: "[[" + m.group(1).rstrip() + "]]" + m.group(2)
        )
        # space at the end of the link, moved outside it - second
        article_text = _LinkWhitespace5.replace(
            article_text, lambda m: "[[" + m.group(1).rstrip() + "]] "
        )

    # double space between wikilinked dates
    if any("  " in s for s in links):
        article_text = _DateLinkWhitespace.replace(article_text, "$1")

    # [[link #section]] or [[link# section]] -> [[link#section]], unless the text has a hash too
    if any("# " in s or " #" in s for s in links):
        article_text = _SectionLinkWhitespace.replace(
            article_text,
            lambda m: (
                m.group(1).rstrip() + "#" + m.group(2).lstrip()
                if m.value.count("#") == 1
                else m.value
            ),
        )

    # [[page# section]] -> [[page#section]]
    if article_title:
        section_link_whitespace = _R(r"(\[\[" + rx.escape(article_title) + r"\#)\s+([^\[\]]+\]\])")
        return section_link_whitespace.replace(article_text, "$1$2")
    return article_text


_InfoBoxSingleAlbum = nested_template_regex(
    ["Infobox Single", "Infobox single", "Infobox album", "Infobox Album"]
)
_TaxoboxColour = nested_template_regex(["taxobox colour", "taxobox color"])
_TrailingPipe = _R(r"\|\s*\]")
_InterwikiPrefix = _R(r"\[\[[a-z0-9_-]{2,}:")
_HiddenPrefix = _R(r"\[\[⌊⌊⌊⌊M?\d+⌋⌋⌋⌋")


def fix_links(article_text: str, article_title: str) -> tuple[str, bool]:
    """Clean up wikilinks: canonical targets, bold/italic pipes, stray pipes, self-links, self
    interwikis and the pipe trick. Returns (text, no_change)."""
    from awb_l.core.parsers import templates

    site = current_site()
    at_start = article_text
    esc_title = rx.escape(article_title)

    if templates.template_exists(templates.get_all_templates(article_text), _InfoBoxSingleAlbum):
        article_text = _fix_links_info_box_single_album(article_text, article_title)

    links = list(dict.fromkeys(get_all_wiki_links(article_text)))

    # {{!}} -> a standard pipe
    if "!" in templates.get_all_templates(article_text):
        for e in [lnk for lnk in links if "{{!}}" in lnk and "|" not in lnk]:
            article_text = article_text.replace(e, e.replace("{{!}}", "|"))

    has_any_self_interwikis = any(site.lang_code + ":" in lnk for lnk in links)

    # performance: only links that canonicalisation could change; skip interwiki prefixes (can be
    # part of a URL, e.g. [[iarchive:foo]]) and links starting with hidden text (likely file links)
    for lnk in links:
        if (
            any(c in lnk for c in "&%_")
            and not _InterwikiPrefix.is_match(lnk)
            and not _HiddenPrefix.is_match(lnk)
        ):
            res = W.WikiLink.replace(lnk, _fix_links_wikilink_canonicalize_me)
            if res != lnk:
                article_text = article_text.replace(lnk, res)

    # first check for performance, second to avoid a (dodgy) apostrophe after a link
    if any("|''" in lnk or "| ''" in lnk for lnk in links) and "']]'" not in article_text:
        article_text = W.PipedWikiLink.replace(article_text, _fix_links_wikilink_bold_italics_me)

    # excess trailing pipe
    if any("|" in lnk and _TrailingPipe.is_match(lnk) for lnk in links):
        article_text = W.PipedWikiLink.replace(
            article_text,
            lambda m: (
                "[[" + m.group(1) + "|" + m.group(2).strip().rstrip("|").strip() + "]]"
                if m.group(2).strip().endswith("|")
                else m.value
            ),
        )

    # excess leading pipe, e.g. [[|foo|bar]], avoiding malformed image links
    for pl in links:
        if pl[2:3] == "|" and "|" in pl[3:] and not pl[3:].startswith("thumb"):
            article_text = article_text.replace(pl, "[[" + pl[3:].lstrip())

    # self-links: not with imagemaps or noinclude/includeonly transclusion business
    title_ci = first_letter_case_insensitive(esc_title)
    if (
        _R(r"\[\[\s*(" + title_ci + r")\s*(?:\]|\|)").is_match(article_text)
        and not W.ImageMap.is_match(article_text)
        and not W.IncludeonlyNoinclude.is_match(article_text)
        and not _TaxoboxColour.is_match(article_text)
    ):
        # remove self-links, but not links differing in more than first-letter case
        article_text = _R(r"\[\[\s*(" + title_ci + r")\s*\]\]").replace(article_text, "$1")
        # piped self-links keep their text; a category listing itself is removed
        is_category = namespace.determine(article_title) == Namespace.CATEGORY
        article_text = _R(r"\[\[\s*" + title_ci + r"\s*\|\s*([^\]]+)\s*\]\]").replace(
            article_text, "" if is_category else "$1"
        )

    # self interwikis, not on monolingual projects
    if has_any_self_interwikis and not site.is_wikimedia_monolingual_project:
        article_text = _fix_self_interwikis(article_text)

    article_text = fix_pipe_trick(article_text)
    return article_text, article_text == at_start


def _fix_self_interwikis(article_text: str) -> str:
    lang = current_site().lang_code
    for m in W.PossibleInterwikis.matches(article_text):
        # an interwiki to the wiki itself is a plain wikilink
        if m.group(1) == lang:
            article_text = article_text.replace(m.value, "[[" + m.group(2) + "]]")
        else:
            break
    return article_text


_SectionLink = _R(r"(.+)#(.+)")


def _fix_links_wikilink_canonicalize_me(m: DotNetMatch) -> str:
    from awb_l.core.parsers.parsers import canonicalize_title

    target, y = m.group(1), m.value
    # don't convert %27%27 -- https://phabricator.wikimedia.org/T10932
    if target and "%27%27" not in target:
        sl = _SectionLink.match(target) if "#" in target else None
        if sl:  # canonicalise section links in two parts
            new_target = canonicalize_title(sl.group(1)) + "#" + canonicalize_title(sl.group(2))
        else:
            new_target = canonicalize_title(target)
        return y.replace(target, new_target.replace("%20", " "))
    return y


def _fix_links_wikilink_bold_italics_me(m: DotNetMatch) -> str:
    """[[Foo|'''Foo''']] -> '''[[Foo]]''' (and italics, bold italics)."""
    text, y = m.group(2), m.value
    if text and turn_first_to_upper(m.group(1).strip()) == turn_first_to_upper(
        m.group(2).strip().strip("'").strip()
    ):
        stripped = text.strip()
        if W.Bold.match(text).value == stripped:
            y = "'''" + y.replace(text, W.Bold.replace(text, "$1").strip()) + "'''"
        elif W.Italics.match(text).value == stripped:
            y = "''" + y.replace(text, W.Italics.replace(text, "$1").strip()) + "''"
        elif W.BoldItalics.match(text).value == stripped:
            y = "'''''" + y.replace(text, W.BoldItalics.replace(text, "$1").strip()) + "'''''"
    return y


def _fix_links_info_box_single_album(article_text: str, article_title: str) -> str:
    """In {{Infobox single/album}}, "this single/album" self-links become bold, not delinked."""
    esc = rx.escape(article_title)
    lower = turn_first_to_lower(esc)
    prefix = r"(?s)(?<={{[Ii]nfobox (?:[Ss]ingle|[Aa]lbum).*?\|\s*[Tt]his (?:[Ss]ingle|[Aa]lbum)\s*=[^{}]*?)(?:''')?\[\[\s*"
    tail = r"(?=[^{}\|]*(?:\||}}))"
    # AWB passes the title into the .NET replacement string unescaped; kept as is
    article_text = _R(prefix + esc + r"\s*\]\](?:''')?" + tail).replace(
        article_text, "'''" + article_title + "'''"
    )
    article_text = _R(prefix + lower + r"\s*\]\](?:''')?" + tail).replace(
        article_text, "'''" + lower + "'''"
    )
    article_text = _R(prefix + esc + r"\s*\|\s*([^\]]+)\s*\]\](?:''')?" + tail).replace(
        article_text, "'''$1'''"
    )
    return _R(prefix + lower + r"\s*\|\s*([^\]]+)\s*\]\](?:''')?" + tail).replace(
        article_text, "'''$1'''"
    )


_ParenPipeLink = _R(r"(\(\[\[[^[\]\(\)]+\|[^[\]\(\)]+) *\) *\]\]")
_PipeSpaces = _R(r" *\| *")


def _is_lower(c: str) -> bool:
    """char.IsLower."""
    return unicodedata.category(c) == "Ll"


def simplify_links(article_text: str) -> str:
    """[[Dog|dog]] -> [[dog]], [[Dog|dogs]] -> [[dog]]s, [[dog|(dog)]] -> ([[dog]]), whitespace."""
    from awb_l.core.parsers.parsers import canonicalize_title

    site = current_site()
    # T377260 ([[dog|dogs)]] -> ([[dog]]s)
    article_text = _ParenPipeLink.replace(article_text, "$1]])")

    piped_links = [lnk for lnk in dict.fromkeys(get_all_wiki_links(article_text)) if "|" in lnk]

    category_ns = site.namespaces.get(Namespace.CATEGORY, "Category:")
    whitespace_trim_needed = any(
        ("| " in s and category_ns not in s) or " |" in s or ("| ]]" not in s and " ]]" in s)
        for s in piped_links
    )

    for piped_link in piped_links:
        m = W.PipedWikiLink.match(piped_link)
        # skip if only part of the link matched, e.g. [[Image:...]] with nested links
        if len(piped_link) != m.length:
            continue

        a, b = m.group(1).strip(), m.group(2)

        # the space after the pipe must stay in the Category namespace
        if whitespace_trim_needed:
            b = (
                m.group(2).strip()
                if namespace.determine(a) != Namespace.CATEGORY
                else m.group(2).rstrip(" ")
            )
            if not b:
                continue

        lb, la = turn_first_to_upper_no_project_check(b), turn_first_to_upper_no_project_check(a)

        if any(c in piped_link for c in "&%_"):  # check for performance
            cb = turn_first_to_upper_no_project_check(canonicalize_title(b))
            ca = turn_first_to_upper_no_project_check(canonicalize_title(a))
            # same target and text after cleanup and case conversion, e.g. [[Foo_bar|Foo bar]]
            if ca == cb:
                article_text = article_text.replace(piped_link, "[[" + b.replace("_", " ") + "]]")

        for punct in (".", ","):
            if lb == la + punct:
                article_text = article_text.replace(piped_link, "[[" + b[:-1] + "]]" + punct)

        # [[dog|(dog)]] -> ([[dog]])
        if (
            lb.startswith("(")
            and "(" + turn_first_to_upper_no_project_check(lb.strip("()")) + ")"
            == "(" + turn_first_to_upper_no_project_check(la) + ")"
        ):
            # T317207: links with a trailing ) outside, e.g. [[Ермітаж|(Ермітаж]])
            if piped_link + ")" in article_text:
                article_text = article_text.replace(piped_link + ")", piped_link)
            article_text = article_text.replace(piped_link, "([[" + b.strip("()") + "]])")

        if lb.startswith(la):  # target is a prefix of the text, e.g. [[Dog|Dogs]] -> [[Dog]]s
            if not all(_is_lower(ch) for ch in b[len(a) :]):
                continue
            article_text = article_text.replace(piped_link, "[[" + b[: len(a)] + "]]" + b[len(a) :])
        elif whitespace_trim_needed:  # trim whitespace around the pipe
            new_link = "[[" + a + "|" + b + "]]"
            # all pipe whitespace in file/image links
            if W.for_site(site).FileNamespaceLink.is_match(new_link):
                new_link = _PipeSpaces.replace(new_link, "|")
            if new_link != piped_link:
                article_text = article_text.replace(piped_link, new_link)

    return article_text


@functools.lru_cache(maxsize=10)
def _all_wiki_links(article_text: str) -> tuple[str, ...]:
    text = article_text
    links: list[str] = []
    while True:
        matches = W.SimpleWikiLink.matches(text)
        if not matches:
            break
        links.extend(m.value for m in matches)
        # process the link contents again for any (further) nested links
        text = ",".join(m.group(1) for m in matches)
    return tuple(links)


def get_all_wiki_links(article_text: str) -> list[str]:
    """All wikilinks, including those nested in other links (e.g. in image captions).

    Returns a new list each time (AWB returned its cached list, which callers then modified).
    """
    return list(_all_wiki_links(article_text))


def sticky_links(article_text: str) -> str:
    """Join nearby words with links: "[[Russian literature|Russian]] literature" ->
    "[[Russian literature]]" (disabled as a genfix in AWB)."""
    for m in W.PipedWikiLink.matches(article_text):
        a, b = m.group(1), m.group(2)
        if not b.strip() or "," in a:
            continue
        if turn_first_to_lower(a).startswith(turn_first_to_lower(b)):
            has_space = len(a) > len(b) and a[len(b)] == " "
            search = (
                r"\[\["
                + rx.escape(a)
                + r"\|"
                + rx.escape(b)
                + r"\]\]"
                + ("[ ]+" if has_space else "")
                + rx.escape(a[len(b) + (1 if has_space else 0) :])
                + r"\b"
            )
            # first character capitalised as in the visible part of the link
            a = b[0] + a[1:]
            article_text = _R(search).replace(article_text, "[[" + a + "]]")
    return article_text


_DuplicatePipedLinks = _R(r"\[\[([^\]\|]+)\|([^\]]*)\]\](.*[.\n]*)\[\[\1\|\2\]\]")
_DuplicateUnpipedLinks = _R(r"\[\[([^\]]+)\]\](.*[.\n]*)\[\[\1\]\]")


def remove_duplicate_wiki_links(article_text: str) -> str:
    article_text = _DuplicatePipedLinks.replace(article_text, "[[$1|$2]]$3$2")
    return _DuplicateUnpipedLinks.replace(article_text, "[[$1]]$2$1")


_PipeTrickLinkBracket = _R(r"\[\[(.*?)( *\(.*\) *)\|\]\]")
_PipeTrickLinkComma = _R(r"\[\[(.*?)(,.*)\|\]\]")


def fix_pipe_trick(article_text: str) -> str:
    """Expand the pipe trick: [[Foo (bar)|]] -> [[Foo (bar)|Foo]], [[Foo, bar|]] -> [[Foo, bar|Foo]]."""
    from awb_l.core import tools

    links = list(
        dict.fromkeys(lnk for lnk in get_all_wiki_links(article_text) if lnk.endswith("|]]"))
    )
    for lnk in links:

        def expand(li: DotNetMatch) -> str:
            return (
                "[["
                + li.group(1)
                + li.group(2)
                + "|"
                + tools.remove_namespace_string(li.group(1))
                + "]]"
            )

        if _PipeTrickLinkBracket.is_match(lnk):
            new = _PipeTrickLinkBracket.replace(lnk, expand)
        else:
            new = _PipeTrickLinkComma.replace(lnk, expand)
        article_text = article_text.replace(lnk, new)
    return article_text
