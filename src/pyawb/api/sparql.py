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
"""SPARQL queries (Wikidata Query Service), and the sitelinks that turn items into pages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from pyawb.api.errors import ApiException
from pyawb.api.transport import Transport, load_pywikibot

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
BATCH_SIZE = 50


class SparqlError(ApiException):
    """The query failed (syntax error, timeout of the query service)."""


class Sparql(Protocol):
    def select(self, query: str) -> tuple[Sequence[str], list[dict[str, str]]]:
        """(variables in the query's order, rows as variable -> value). Unbound values are
        left out of a row."""
        ...


def parse_sparql_json(result: Mapping[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    """SPARQL 1.1 query results JSON -> (variables, rows of plain values)."""
    variables = [str(v) for v in result.get("head", {}).get("vars", ())]
    rows: list[dict[str, str]] = []
    for binding in result.get("results", {}).get("bindings", ()):
        rows.append({k: str(v.get("value", "")) for k, v in binding.items()})
    return variables, rows


class PywikibotSparql:
    """The query service through pywikibot's SparqlQuery (our User-Agent, retries, maxlag-like
    back-off on 429)."""

    def __init__(self, endpoint: str = WDQS_ENDPOINT) -> None:
        self.endpoint = endpoint

    def select(self, query: str) -> tuple[Sequence[str], list[dict[str, str]]]:
        load_pywikibot()
        from pywikibot.data.sparql import SparqlQuery

        sq = SparqlQuery(endpoint=self.endpoint, entity_url="http://www.wikidata.org/entity/")
        try:
            data = sq.query(query)
        except Exception as e:  # pywikibot raises several types for HTTP and query errors
            raise SparqlError(str(e)) from e
        if not data:
            raise SparqlError("the query service returned no result")
        return parse_sparql_json(data)


def sitelink_titles(transport: Transport, ids: Sequence[str], site_id: str) -> dict[str, str]:
    """Item id -> page title on one wiki (site_id e.g. "mlwiki"), for the items that have one.
    transport is Wikidata's API; 50 items per request."""
    out: dict[str, str] = {}
    unique = list(dict.fromkeys(ids))
    for i in range(0, len(unique), BATCH_SIZE):
        result = transport.request(
            {
                "action": "wbgetentities",
                "ids": "|".join(unique[i : i + BATCH_SIZE]),
                "props": "sitelinks",
                "sitefilter": site_id,
            }
        )
        entities: Mapping[str, Mapping[str, Any]] = result.get("entities", {})
        for qid, entity in entities.items():
            link = entity.get("sitelinks", {}).get(site_id)
            if link and link.get("title"):
                out[qid] = str(link["title"])
    return out
