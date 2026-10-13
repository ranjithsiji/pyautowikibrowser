"""Lists from a Wikidata Query Service (SPARQL) query."""

from collections.abc import Sequence
from typing import Any

import pytest

from pyawb.api.sparql import parse_sparql_json
from pyawb.lists.providers import ManualListProvider
from pyawb.lists.wikidataquery import WikidataQueryListProvider, page_column
from tests.api.fakes import FakeTransport

E = "http://www.wikidata.org/entity/"


class FakeSparql:
    def __init__(self, variables: Sequence[str], rows: list[dict[str, str]]) -> None:
        self.result = (variables, rows)
        self.queries: list[str] = []

    def select(self, query: str) -> tuple[Sequence[str], list[dict[str, str]]]:
        self.queries.append(query)
        return self.result


def sitelinks(params: dict[str, str]) -> dict[str, Any]:
    links = {"Q146": "പൂച്ച", "Q42": "ഡഗ്ലസ് ആഡംസ്"}  # Q1 has no mlwiki page
    return {
        "entities": {
            q: {"id": q, "sitelinks": {"mlwiki": {"site": "mlwiki", "title": links[q]}}}
            if q in links
            else {"id": q, "sitelinks": {}}
            for q in params["ids"].split("|")
        }
    }


def provider(
    sparql: FakeSparql, site_id: str = "mlwiki"
) -> tuple[WikidataQueryListProvider, FakeTransport]:
    t = FakeTransport(sitelinks)
    url = (
        "https://www.wikidata.org/wiki/$1"
        if site_id == "wikidatawiki"
        else "https://ml.wikipedia.org/wiki/$1"
    )
    return WikidataQueryListProvider(sparql, t, site_id, url), t


def test_items_become_sitelinked_pages_in_query_order() -> None:
    rows = [
        {"item": E + "Q42", "label": "x"},
        {"item": E + "Q1"},
        {"item": E + "Q146"},
        {"item": E + "Q42"},
    ]
    p, t = provider(FakeSparql(["item", "label"], rows))
    assert [a.name for a in p.make_list("SELECT ...")] == ["ഡഗ്ലസ് ആഡംസ്", "പൂച്ച"]
    params = t.last("wbgetentities")
    assert params["ids"] == "Q42|Q1|Q146" and params["sitefilter"] == "mlwiki"


def test_article_column_with_page_urls() -> None:
    rows = [
        {
            "item": E + "Q146",
            "article": "https://ml.wikipedia.org/wiki/%E0%B4%AA%E0%B5%82%E0%B4%9A%E0%B5%8D%E0%B4%9A",
        },
        {"item": E + "Q2", "article": "https://ml.wikipedia.org/wiki/Foo_bar"},
        {"item": E + "Q3", "article": "https://en.wikipedia.org/wiki/Elsewhere"},
    ]
    p, t = provider(FakeSparql(["item", "article"], rows))
    assert [a.name for a in p.make_list("q")] == ["പൂച്ച", "Foo bar"]
    assert not t.requests  # no item lookups needed


def test_wikidata_itself() -> None:
    rows = [{"x": E + "Q42"}, {"x": E + "P31"}, {"x": "L7"}]
    p, t = provider(FakeSparql(["x"], rows), "wikidatawiki")
    assert [a.name for a in p.make_list("q")] == ["Q42", "Property:P31", "Lexeme:L7"]
    assert not t.requests


def test_empty_results() -> None:
    p, _ = provider(FakeSparql([], []))
    assert p.make_list("q") == [] and p.make_list("  ") == []


def test_page_column() -> None:
    assert page_column(["item", "article"]) == "article"
    assert page_column(["x", "y"]) == "x"
    assert page_column([]) is None


def test_parse_sparql_json() -> None:
    data = {
        "head": {"vars": ["item", "itemLabel"]},
        "results": {"bindings": [{"item": {"type": "uri", "value": E + "Q1"}}]},
    }
    assert parse_sparql_json(data) == (["item", "itemLabel"], [{"item": E + "Q1"}])


@pytest.mark.parametrize(
    ("text", "titles"),
    [
        ("foo\r\nബാർ\n\n  ", ["Foo", "ബാർ"]),
        ("[[Bar]]|https://en.wikipedia.org/wiki/Caf%C3%A9#History", ["Bar", "Café"]),
    ],
)
def test_manual_list(text: str, titles: list[str]) -> None:
    assert [a.name for a in ManualListProvider().make_list(text)] == titles
