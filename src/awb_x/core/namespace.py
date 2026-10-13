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
# Ported from AutoWikiBrowser WikiFunctions/Namespace.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Namespace detection for page titles (port of Namespace.cs). Namespace numbers are in site.py."""

from __future__ import annotations

from collections.abc import Mapping

from awb_x.core import rx
from awb_x.core.site import Namespace, SiteConfig, current_site
from awb_x.core.textutil import turn_first_to_upper, wiki_decode

STANDARD_NAMESPACES: tuple[int, ...] = (
    Namespace.MEDIA,
    Namespace.SPECIAL,
    *(n for n in range(Namespace.TALK, Namespace.CATEGORY_TALK + 1) if n not in (12, 13)),
)

_SPACING_MODIFIER_LETTERS = rx.DotNetRegex(r"\p{IsSpacingModifierLetters}")
_COLON_SPACE = rx.DotNetRegex(r"\s*:\s*")
_NORMALIZE_COLON = rx.DotNetRegex(r"\s*:$")


def determine(title: str, site: SiteConfig | None = None) -> int:
    """The namespace number of a page title (0 for articles)."""
    site = site or current_site()
    title = _COLON_SPACE.replace(title.replace("%3A", ":"), ":")
    # A spacing modifier letter at the start combines with the colon into another character, so
    # "Namespace:" would never be found; replace them first.
    title = _SPACING_MODIFIER_LETTERS.replace(title, "'")
    if ":" not in title:
        return 0
    title = turn_first_to_upper(wiki_decode(title), site)

    for key, name in site.namespaces.items():
        if title.startswith(name):
            return key
    for key, aliases in site.namespace_aliases.items():
        for alias in aliases:
            if title.startswith(alias):
                return key
    for key, name in site.canonical_namespaces.items():
        if title.startswith(name):
            return key
    return 0


def is_main_space(title_or_ns: str | int, site: SiteConfig | None = None) -> bool:
    ns = title_or_ns if isinstance(title_or_ns, int) else determine(title_or_ns, site)
    return ns == Namespace.ARTICLE


def is_important(title_or_ns: str | int, site: SiteConfig | None = None) -> bool:
    ns = title_or_ns if isinstance(title_or_ns, int) else determine(title_or_ns, site)
    return ns in (Namespace.ARTICLE, Namespace.FILE, Namespace.TEMPLATE, Namespace.CATEGORY)


def is_talk(title_or_ns: str | int, site: SiteConfig | None = None) -> bool:
    ns = title_or_ns if isinstance(title_or_ns, int) else determine(title_or_ns, site)
    # C#'s % truncates (-1 % 2 == -1); Python's floors (-1 % 2 == 1). Special/Media are not talk.
    return ns > 0 and ns % 2 == 1


def is_user_talk(title: str, site: SiteConfig | None = None) -> bool:
    return title.startswith((site or current_site()).namespaces[Namespace.USER_TALK])


def is_user_page(title: str, site: SiteConfig | None = None) -> bool:
    return determine(title, site) == Namespace.USER


def is_user_space(title: str, site: SiteConfig | None = None) -> bool:
    return is_user_talk(title, site) or is_user_page(title, site)


def is_special(ns: int) -> bool:
    return ns < 0


def normalize(ns: str, ns_id: int, site: SiteConfig | None = None) -> str:
    """The wiki's spelling of a namespace prefix ("user :" -> "User:"), or ns unchanged."""
    site = site or current_site()
    ns = wiki_decode(_NORMALIZE_COLON.replace(ns, ":"))
    name = site.namespaces[ns_id]
    if name.casefold() == ns.casefold():
        return name
    for alias in site.namespace_aliases.get(ns_id, ()):
        if alias.casefold() == ns.casefold():
            return alias
    return ns


def verify_namespaces(namespaces: Mapping[int, str]) -> bool:
    if any(ns not in namespaces for ns in STANDARD_NAMESPACES):
        return False
    if Namespace.ARTICLE in namespaces:
        return False
    return all(len(s) >= 2 and s.endswith(":") for s in namespaces.values())
