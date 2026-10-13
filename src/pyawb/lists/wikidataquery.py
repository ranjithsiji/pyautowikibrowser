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
"""Make a list from a Wikidata Query Service (SPARQL) query. Not in AWB.

The pages come from one column: ?article if the query has it, else the first variable. A value
may be
- a Wikidata item ("http://www.wikidata.org/entity/Q42" or "Q42"): the page linked to it on the
  wiki being edited (items without such a sitelink are left out), or the item itself when the
  wiki is Wikidata;
- a page URL on the wiki being edited (from `?article schema:about ?item; schema:isPartOf
  <https://ml.wikipedia.org/>`): that page.
Order follows the query's results; repeats are dropped.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import unquote

import regex

from pyawb.api.sparql import Sparql, sitelink_titles
from pyawb.api.transport import Transport
from pyawb.core.article import Article
from pyawb.lists.providers import ListProvider

_ENTITY = regex.compile(r"(?:https?://www\.wikidata\.org/entity/)?([QPL][1-9][0-9]*)")
_ENTITY_NAMESPACES = {"P": "Property:", "L": "Lexeme:"}

EXAMPLE_QUERY = """# Pages about cats (Q146 is "house cat"): instance of (P31) house cat
SELECT ?item WHERE {
  ?item wdt:P31 wd:Q146 .
}
LIMIT 100"""


def page_column(variables: Sequence[str]) -> str | None:
    """The variable whose values are the pages: ?article, else the first."""
    if "article" in variables:
        return "article"
    return variables[0] if variables else None


@dataclass
class WikidataQueryListProvider(ListProvider):
    """Pages from a SPARQL query on the Wikidata Query Service.

    wikidata: Wikidata's API (for sitelinks). site_id: the wiki being edited, as Wikidata names
    it ("mlwiki", siteinfo's wikiid). article_url: its article path with "$1" ("https://ml.
    wikipedia.org/wiki/$1"), to recognise page URLs.
    """

    display_text: ClassVar[str] = "Wikidata query (SPARQL)"
    user_input_text: ClassVar[str] = "SPARQL query:"

    sparql: Sparql
    wikidata: Transport
    site_id: str
    article_url: str
    limit: int = 25000

    def make_list(self, *criteria: str) -> list[Article]:
        titles: list[str] = []
        for query in criteria:
            if query.strip():
                titles.extend(self._titles(query))
        return [Article(t) for t in dict.fromkeys(titles)][: self.limit]

    def _titles(self, query: str) -> list[str]:
        variables, rows = self.sparql.select(query)
        column = page_column(variables)
        if column is None:
            return []
        prefix, _, suffix = self.article_url.partition("$1")
        plain_prefix = prefix.removeprefix("https:").removeprefix("http:")
        values: list[tuple[str, str]] = []  # ("item", id) or ("title", title)
        for row in rows:
            value = row.get(column, "").strip()
            if not value:
                continue
            m = _ENTITY.fullmatch(value)
            if m:
                values.append(("item", m.group(1)))
                continue
            for p in (prefix, "https:" + plain_prefix, "http:" + plain_prefix):
                if p and value.startswith(p) and value.endswith(suffix):
                    title = value[len(p) : len(value) - len(suffix) if suffix else None]
                    values.append(("title", unquote(title).replace("_", " ")))
                    break

        if self.site_id == "wikidatawiki":
            links = {
                v: _ENTITY_NAMESPACES.get(v[0], "") + v for kind, v in values if kind == "item"
            }
        else:
            ids = [v for kind, v in values if kind == "item"]
            links = sitelink_titles(self.wikidata, ids, self.site_id) if ids else {}
        out: list[str] = []
        for kind, v in values:
            if kind == "title":
                out.append(v)
            elif v in links:
                out.append(links[v])
        return out
