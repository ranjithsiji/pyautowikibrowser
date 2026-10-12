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
# Ported from AutoWikiBrowser WikiFunctions/Tools.cs
# (C) 2007 Martin Richards, (C) 2007 Stephen Kennedy, and the AutoWikiBrowser contributors
# (GPL-2.0-or-later).
"""Low-level helpers from Tools.cs that wikiregexes, namespace and tools all build on.

Kept separate from tools.py so that wikiregexes can import them without a cycle. Import them
through awb_l.core.tools in ported code.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable

from awb_l.core import rx
from awb_l.core.site import Namespace, SiteConfig, current_site

# -- characters (System.Char semantics) -----------------------------------------------------------


def char_upper(c: str) -> str:
    """char.ToUpper: one character in, one out (Python's "ß".upper() is "SS")."""
    u = c.upper()
    return u if len(u) == 1 else c


def char_lower(c: str) -> str:
    low = c.lower()
    return low if len(low) == 1 else c


def is_letter(c: str) -> bool:
    """char.IsLetter (categories L*). Astral letters count, unlike .NET's UTF-16 halves."""
    return unicodedata.category(c)[0] == "L"


def is_letter_or_digit(c: str) -> bool:
    """char.IsLetterOrDigit: L* or Nd (not other numerics such as "²", unlike str.isalnum)."""
    cat = unicodedata.category(c)
    return cat[0] == "L" or cat == "Nd"


# -- strings --------------------------------------------------------------------------------------


def strip_namespace_colon(ns: str) -> str:
    """ "User:" -> "User"."""
    return ns.rstrip(":")


def first_difference(a: str, b: str) -> int:
    """Index of the first character that differs, or the shorter length."""
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    return min(len(a), len(b))


def turn_first_to_upper_no_project_check(text: str) -> str:
    return char_upper(text[0]) + text[1:] if text else ""


def turn_first_to_upper(text: str, site: SiteConfig | None = None) -> str:
    """Upper-case the first letter, unless the wiki has $wgCapitalLinks off (e.g. Wiktionary)."""
    if not (site or current_site()).capitalize_first_letter:
        return text
    return turn_first_to_upper_no_project_check(text)


def turn_first_to_lower(text: str) -> str:
    return char_lower(text[0]) + text[1:] if text else ""


def first_letter_case_insensitive(text: str) -> str:
    """ "Category" -> "[Cc]ategory". No escaping: callers pass regex text."""
    if text and text[0].isalpha() and char_upper(text[0]) != char_lower(text[0]):
        text = text.strip()
        return "[" + char_upper(text[0]) + char_lower(text[0]) + "]" + text[1:]
    return text


def all_case_insensitive(text: str) -> str:
    """ "Cat" -> "[Cc][Aa][Tt]"."""
    if not text:
        return text
    return "".join(f"[{char_upper(c)}{char_lower(c)}]" if c.isalpha() else c for c in text.strip())


# -- URL encoding (System.Web.HttpUtility semantics) -----------------------------------------------

_URL_SAFE = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.!*()")


def url_encode(text: str) -> str:
    """HttpUtility.UrlEncode: space -> "+", others as UTF-8 "%xx" with lower-case hex."""
    out: list[str] = []
    for c in text:
        if c in _URL_SAFE:
            out.append(c)
        elif c == " ":
            out.append("+")
        else:
            out.extend(f"%{b:02x}" for b in c.encode("utf-8", "surrogatepass"))
    return "".join(out)


_HEX = frozenset("0123456789abcdefABCDEF")


def _is_hex(s: str, length: int) -> bool:
    return len(s) == length and set(s) <= _HEX


def url_decode(text: str) -> str:
    """HttpUtility.UrlDecode: "+" -> space, "%xx" UTF-8 bytes and "%uxxxx"; bad escapes kept."""
    buf = bytearray()
    out: list[str] = []

    def flush() -> None:
        if buf:
            out.append(buf.decode("utf-8", "replace"))
            buf.clear()

    i = 0
    while i < len(text):
        c = text[i]
        if c == "+":
            flush()
            out.append(" ")
            i += 1
        elif c == "%" and _is_hex(text[i + 1 : i + 3], 2):
            buf.append(int(text[i + 1 : i + 3], 16))
            i += 3
        elif c == "%" and text[i + 1 : i + 2] in ("u", "U") and _is_hex(text[i + 2 : i + 6], 4):
            flush()
            out.append(chr(int(text[i + 2 : i + 6], 16)))
            i += 6
        else:
            flush()
            out.append(c)
            i += 1
    flush()
    return "".join(out)


def wiki_encode(title: str) -> str:
    """Title as used in a URL: spaces to underscores, then URL-encoded, keeping "/" and ":"."""
    return url_encode(title.replace(" ", "_")).replace("%2f", "/").replace("%3a", ":")


def wiki_decode(title: str) -> str:
    """URL-decode a title and turn underscores into spaces ("+" stays "+")."""
    return url_decode(title.replace("+", "%2B")).replace("_", " ")


def remove_hash_from_page_title(title: str) -> str:
    pos = title.find("#")
    return title if pos < 0 else title[:pos]


# -- regex builders -------------------------------------------------------------------------------

_TRAILING_NS_COLON_LAZY = rx.DotNetRegex(r"(.+?):$")
_TRAILING_COLON = rx.DotNetRegex(r":$")


def _template_namespace(site: SiteConfig) -> str:
    return site.namespaces_case_insensitive.get(Namespace.TEMPLATE, "[Tt]emplate:")


def template_name_regex(site: SiteConfig | None = None) -> rx.DotNetRegex:
    """Group 1 is the template name."""
    ns = _TRAILING_COLON.replace(_template_namespace(site or current_site()), r"[\s_]*:")
    return rx.DotNetRegex(
        r"{{\s*(?::?[\s_]*"
        + ns
        + r"[\s_]*)?([^\|{}]+?)(?:\s*(?:<!--.*?-->|⌊⌊⌊⌊M?\d+⌋⌋⌋⌋)\s*)?\s*(?:\||:|}})"
    )


_NESTED_TEMPLATE_REGEX_START = r"({{[\s_]*)(?:"
_NESTED_TEMPLATE_REGEX_END = (
    r"([\s_]*(?:<!--[^>]*?-->\s*|⌊⌊⌊⌊M?\d+⌋⌋⌋⌋\s*)?"
    r"(\|((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))))?\}\})"
)


def nested_template_regex(
    template_names: str | Iterable[str], site: SiteConfig | None = None
) -> rx.DotNetRegex:
    """Matches calls of the named templates, including nested templates in their arguments.

    Groups: 1 = "{{" plus any namespace prefix, 2 = the name as written, 3 = everything after
    the name up to and including "}}", 4 = "|" and the arguments, 5 = the arguments.
    AWB returns null for an empty list; this raises ValueError.
    """
    site = site or current_site()
    names = [template_names] if isinstance(template_names, str) else list(template_names)
    if not names or names == [""]:
        raise ValueError("no template names")

    ns = _template_namespace(site)
    if site.lang_code in ("", "en"):  # support (deprecated) {{msg:Foo}} syntax
        ns = _TRAILING_NS_COLON_LAZY.replace(ns, "(?:$1|[Mm]sg):")
    ns = _TRAILING_COLON.replace(ns, r"[\s_]*:")  # allow whitespace before colon

    alternatives = (
        first_letter_case_insensitive(
            rx.escape(n.strip().replace("_", " ")).replace("\\ ", r"[_\s]+")
        )
        for n in names
    )
    return rx.DotNetRegex(
        _NESTED_TEMPLATE_REGEX_START
        + r":?[\s_]*"
        + ns
        + r"[\s_]*\s*)?("
        + "|".join(alternatives)
        + ")"
        + _NESTED_TEMPLATE_REGEX_END
    )
