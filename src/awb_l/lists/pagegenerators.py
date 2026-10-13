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
"""pywikibot's page generators as a list provider: any of pywikibot's generator options
("-cat:Foo", "-search:bar", "-ref:Baz", "-newpages:50", "-unconnectedpages", ...) and filters
("-ns:0", "-titleregex:...") make a page list. Not in AWB.

Options are pywikibot's (https://doc.wikimedia.org/pywikibot/stable/api_ref/pagegenerators.html);
several options combine as pywikibot combines them.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from awb_l.core.article import Article
from awb_l.lists.providers import ListProvider

if TYPE_CHECKING:
    import pywikibot.site


class GeneratorOptionError(ValueError):
    """An option pywikibot's generator factory does not know."""


def split_options(text: str) -> list[str]:
    """Options as typed in one box: shell-style quoting keeps spaces in titles."""
    return shlex.split(text)


@dataclass
class PagegeneratorsListProvider(ListProvider):
    """Pages from pywikibot.pagegenerators.GeneratorFactory."""

    display_text: ClassVar[str] = "pywikibot page generators"
    user_input_text: ClassVar[str] = "Options:"

    site: pywikibot.site.APISite
    limit: int = 25000

    def make_list(self, *criteria: str) -> list[Article]:
        from pywikibot import pagegenerators

        factory = pagegenerators.GeneratorFactory(self.site)
        options = [o for c in criteria for o in split_options(c)]
        for option in options:
            if not factory.handle_arg(option):
                raise GeneratorOptionError(f"unknown page generator option: {option}")
        gen = factory.getCombinedGenerator()
        if gen is None:
            return []
        out: list[Article] = []
        for page in gen:
            out.append(Article(page.title(), namespace_key=page.namespace().id))
            if len(out) >= self.limit:
                break
        return out
