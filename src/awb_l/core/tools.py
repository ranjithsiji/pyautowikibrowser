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
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Port of WikiFunctions/Tools.cs. Functions are added as the code that needs them is ported."""

from __future__ import annotations

from collections.abc import Iterable

from awb_l.core import rx
from awb_l.core.site import Namespace, SiteConfig

ENGLISH = SiteConfig.english()


def _upper(c: str) -> str:
    """char.ToUpper: one character in, one out (Python's "ß".upper() is "SS")."""
    u = c.upper()
    return u if len(u) == 1 else c


def _lower(c: str) -> str:
    low = c.lower()
    return low if len(low) == 1 else c


def strip_namespace_colon(ns: str) -> str:
    """ "User:" -> "User"."""
    return ns.rstrip(":")


def first_difference(a: str, b: str) -> int:
    """Index of the first character that differs, or the shorter length."""
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    return min(len(a), len(b))


def first_letter_case_insensitive(text: str) -> str:
    """ "Category" -> "[Cc]ategory". No escaping: callers pass regex text."""
    if text and text[0].isalpha() and _upper(text[0]) != _lower(text[0]):
        text = text.strip()
        return "[" + _upper(text[0]) + _lower(text[0]) + "]" + text[1:]
    return text


def all_case_insensitive(text: str) -> str:
    """ "Cat" -> "[Cc][Aa][Tt]"."""
    if not text:
        return text
    return "".join(f"[{_upper(c)}{_lower(c)}]" if c.isalpha() else c for c in text.strip())


_TRAILING_NS_COLON_LAZY = rx.DotNetRegex(r"(.+?):$")
_TRAILING_COLON = rx.DotNetRegex(r":$")
_WHITESPACE_RUN = rx.DotNetRegex(r"[\s_]+")


def _template_namespace(site: SiteConfig) -> str:
    return site.namespaces_case_insensitive.get(Namespace.TEMPLATE, "[Tt]emplate:")


def template_name_regex(site: SiteConfig = ENGLISH) -> rx.DotNetRegex:
    """Group 1 is the template name."""
    ns = _TRAILING_COLON.replace(_template_namespace(site), r"[\s_]*:")
    return rx.DotNetRegex(
        r"{{\s*(?::?[\s_]*"
        + ns
        + r"[\s_]*)?([^\|{}]+?)(?:\s*(?:<!--.*?-->|⌊⌊⌊⌊M?\d+⌋⌋⌋⌋)\s*)?\s*(?:\||:|}})"
    )


def get_template_name(template_call: str, site: SiteConfig = ENGLISH) -> str:
    name = template_name_regex(site).match(template_call).group(1)
    return _WHITESPACE_RUN.replace(name, " ").strip()


_NESTED_TEMPLATE_REGEX_START = r"({{[\s_]*)(?:"
_NESTED_TEMPLATE_REGEX_END = (
    r"([\s_]*(?:<!--[^>]*?-->\s*|⌊⌊⌊⌊M?\d+⌋⌋⌋⌋\s*)?"
    r"(\|((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))))?\}\})"
)


def nested_template_regex(
    template_names: str | Iterable[str], site: SiteConfig = ENGLISH
) -> rx.DotNetRegex:
    """Matches calls of the named templates, including nested templates in their arguments.

    Groups: 1 = "{{" plus any namespace prefix, 2 = the name as written, 3 = everything after
    the name up to and including "}}", 4 = "|" and the arguments, 5 = the arguments.
    AWB returns null for an empty list; this raises ValueError.
    """
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
