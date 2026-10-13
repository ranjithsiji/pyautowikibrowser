"""The list maker's sources."""

import pytest

from pyawb.api.sparql import PywikibotSparql
from pyawb.lists import providers as P
from pyawb.lists.sources import (
    SOURCES,
    Input,
    SourceUnavailable,
    WikiContext,
    build,
    criteria,
    source,
)
from pyawb.lists.wikidataquery import WikidataQueryListProvider
from tests.api.fakes import FakeTransport


def test_sources_have_unique_names_and_inputs() -> None:
    names = [s.name for s in SOURCES]
    assert len(names) == len(set(names)) and names[0] == "Manual list"
    assert source("Manual list").input is Input.TEXT
    assert source("Wikidata query (SPARQL)").input is Input.TEXT
    assert source("Category").input is Input.LINE
    assert source("My watchlist").input is Input.NONE
    assert source("Text file (Windows 1252 / ANSI)").input is Input.FILE


def test_namespace_choice() -> None:
    assert source("What links here").takes_namespace
    assert source("Wiki search (title)").takes_namespace
    for name in (
        "What links here (all NS)",
        "Wiki search (text) (all NS)",
        "All categories",
        "All files",
        "Category",
    ):
        assert not source(name).takes_namespace, name


def test_build() -> None:
    assert isinstance(build(source("Manual list"), None), P.ManualListProvider)
    assert not source("Text file (Windows 1252 / ANSI)").needs_wiki
    with pytest.raises(SourceUnavailable):
        build(source("Category"), None)
    wiki = WikiContext(FakeTransport())
    p = build(source("What links here"), wiki, namespace=10)
    assert isinstance(p, P.WhatLinksHereListProvider) and p.namespace == 10
    all_ns = build(source("What links here (all NS)"), wiki, namespace=10)
    assert isinstance(all_ns, P.WhatLinksHereAllNSListProvider) and all_ns.namespace is None
    with pytest.raises(SourceUnavailable):
        build(source("Wikidata query (SPARQL)"), wiki)
    sparql = PywikibotSparql()  # not called
    full = WikiContext(
        FakeTransport(), FakeTransport(), sparql, "mlwiki", "https://ml.wikipedia.org/wiki/$1"
    )
    assert isinstance(build(source("Wikidata query (SPARQL)"), full), WikidataQueryListProvider)


def test_criteria() -> None:
    assert criteria(source("Category"), "A| B||") == ["A", " B"]
    assert criteria(source("Manual list"), "A|B\nC") == ["A|B\nC"]
    assert criteria(source("My watchlist"), "ignored") == []
    assert criteria(source("Manual list"), "  ") == []
