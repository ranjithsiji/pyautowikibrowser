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
# Ported from AutoWikiBrowser WikiFunctions/Parse/Templates.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Port of Parse/Templates.cs (in progress)."""

from __future__ import annotations

import functools

from awb_l.core import rx
from awb_l.core.site import SiteConfig, current_site

_NESTED_TEMPLATES = rx.DotNetRegex(
    r"{{\s*([^{}\|]*)((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!)))}}"
)


@functools.lru_cache(maxsize=10)
def _all_templates(article_text: str, site: SiteConfig) -> tuple[str, ...]:
    from awb_l.core import tools

    names: dict[str, None] = {}  # ordered set, like .NET HashSet without removals
    text = article_text
    while True:
        matches = _NESTED_TEMPLATES.matches(text)
        if not matches:
            break
        names.update(dict.fromkeys(m.group(1) for m in matches))
        # process the template contents again for any (further) nested templates
        inner = dict.fromkeys(m.group(2) for m in matches)
        text = ",".join(inner)

    exact = (tools.turn_first_to_upper(tools.get_template_name("{{" + s + "}}")) for s in names)
    return tuple(dict.fromkeys(exact))


def get_all_templates(article_text: str) -> list[str]:
    """Distinct template names used (first letter upper), at any level of nesting."""
    return list(_all_templates(article_text, current_site()))


def template_exists(templates_found: list[str], r: rx.DotNetRegex) -> bool:
    """Whether r matches any of the (first letter upper) template names."""
    return any(r.is_match("{{" + s + "|}}") for s in templates_found)
