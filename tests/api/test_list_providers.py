"""List providers against a fake API: parameters, continuation, limits, filters."""

from pathlib import Path
from typing import Any

import pytest

from awb_x.lists import providers as P
from awb_x.lists.pagegenerators import split_options

from .fakes import FakeTransport


def page(title: str, ns: int = 0, **extra: Any) -> dict[str, Any]:
    return {"ns": ns, "title": title, **extra}


def test_continuation_and_limit() -> None:
    def handler(p: dict[str, str]) -> dict[str, Any]:
        start = int(p.get("cmcontinue", "0"))
        members = [page(f"P{i}") for i in range(start, start + 3)]
        return {
            "continue": {"cmcontinue": str(start + 3), "continue": "-||"},
            "query": {"categorymembers": members},
        }

    t = FakeTransport(handler)
    provider = P.CategoryListProvider(t, limit=7)
    titles = [a.name for a in provider.make_list("Category:Foo bar#x")]
    # AWB checks the limit before each request, so the last batch is kept whole
    assert titles == [f"P{i}" for i in range(9)]
    first = t.requests[0][0]
    assert first["cmtitle"] == "Category:Foo bar" and first["continue"] == ""
    assert t.requests[1][0]["cmcontinue"] == "3"


def test_prepare_categories() -> None:
    assert P.prepare_categories(["category:Foo_bar", "Category : Baz#s", "Plain"]) == [
        "Foo bar",
        "Baz",
        "Plain",
    ]


def test_category_recursive() -> None:
    tree = {
        "Category:Top": [page("A"), page("Category:Sub", 14), page("Category:Loop", 14)],
        "Category:Sub": [page("B"), page("Category:Deeper", 14)],
        "Category:Loop": [page("Category:Top", 14)],
        "Category:Deeper": [page("C")],
    }
    t = FakeTransport(lambda p: {"query": {"categorymembers": tree[p["cmtitle"]]}})
    names = [a.name for a in P.CategoryRecursiveListProvider(t).make_list("Top")]
    assert names == [
        "A",
        "Category:Sub",
        "Category:Loop",
        "B",
        "Category:Deeper",
        "C",
        "Category:Top",
    ]
    one = [a.name for a in P.CategoryRecursiveOneLevelListProvider(t).make_list("Top")]
    assert one == ["A", "Category:Sub", "Category:Loop", "B", "Category:Deeper", "Category:Top"]
    assert P.CategoryRecursiveListProvider(t, depth=99).depth == 30


def test_what_links_here_variants() -> None:
    result = {
        "query": {
            "backlinks": [
                page("A"),
                page("Redirect", redirect=True, redirlinks=[page("Via redirect")]),
            ]
        }
    }
    t = FakeTransport(lambda p: result)
    assert [a.name for a in P.WhatLinksHereListProvider(t).make_list("[[target]]")] == [
        "A",
        "Redirect",
        "Via redirect",
    ]
    assert t.last("query")["bltitle"] == "Target" and t.last("query")["blnamespace"] == "0"

    direct = P.WhatLinksHereAndPageRedirectsExcludingTheRedirectsListProvider(t)
    assert [a.name for a in direct.make_list("Target")] == ["A", "Via redirect"]
    p = t.last("query")
    assert p["blredirect"] == "1" and p["blfilterredir"] == "nonredirects"

    P.WhatLinksHereAllNSListProvider(t).make_list("Target")
    assert "blnamespace" not in t.last("query")
    P.RedirectsListProvider(t).make_list("Target")
    assert t.last("query")["blfilterredir"] == "redirects"


def test_prop_providers() -> None:
    result = {
        "query": {
            "pages": [
                {
                    "title": "X",
                    "links": [page("L1"), page("Talk:L2", 1)],
                    "categories": [page("Category:C", 14)],
                }
            ]
        }
    }
    t = FakeTransport(lambda p: result)
    links = P.LinksOnPageListProvider(t).make_list("x")
    assert [(a.name, a.namespace_key) for a in links] == [("L1", 0), ("Talk:L2", 1)]
    assert t.last("query")["pllimit"] == "max" and t.last("query")["titles"] == "X"
    assert [a.name for a in P.CategoriesOnPageNoHiddenListProvider(t).make_list("X")] == [
        "Category:C"
    ]
    assert t.last("query")["clshow"] == "!hidden"


def test_red_and_blue_links() -> None:
    result = {"query": {"pages": [page("Exists", pageid=1), page("Missing", missing=True)]}}
    t = FakeTransport(lambda p: result)
    assert [a.name for a in P.LinksOnPageOnlyRedListProvider(t).make_list("X")] == ["Missing"]
    assert [a.name for a in P.LinksOnPageOnlyBlueListProvider(t).make_list("X")] == ["Exists"]
    assert t.last("query")["generator"] == "links"


def test_user_contribs_and_all_users() -> None:
    t = FakeTransport(
        lambda p: {
            "query": {"usercontribs": [page("A")], "allusers": [{"userid": 1, "name": "Ünal"}]}
        }
    )
    P.UserContribsListProvider(t).make_list("User:alice")
    p = t.last("query")
    # as in AWB: first letter upper before the namespace is removed; MediaWiki normalises it
    assert p["ucuser"] == "alice" and p["uclimit"] == "max" and "ucnamespace" not in p
    P.UserContribsListProvider(t, namespace=0, number_of_edits=40).make_list("Bob")
    p = t.last("query")
    assert p["uclimit"] == "40" and p["ucnamespace"] == "0"
    users = P.AllUsersSpecialPageProvider(t).make_list()
    assert [(a.name, a.namespace_key) for a in users] == [("User:Ünal", 2)]


def test_search_providers() -> None:
    t = FakeTransport(lambda p: {"query": {"search": [page("Hit")]}})
    P.WikiSearchListProvider(t).make_list("മലയാളം")
    p = t.last("query")
    assert p["srsearch"] == "മലയാളം" and p["srnamespace"] == "0" and p["srwhat"] == "text"
    P.WikiTitleSearchListProvider(t).make_list("foo")
    assert t.last("query")["srsearch"] == "intitle:foo"
    P.WikiTitleSearchAllNSListProvider(t).make_list("foo")
    p = t.last("query")
    assert p["srsearch"] == "intitle:foo" and p["srnamespace"] == "*"
    P.WikiSearchAllNSListProvider(t).make_list("foo")
    assert t.last("query")["srsearch"] == "foo"


def test_special_page_providers() -> None:
    t = FakeTransport(
        lambda p: {
            "query": {
                "allpages": [page("A")],
                "exturlusage": [page("E")],
                "embeddedin": [page("D")],
                "random": [page("R")],
                "recentchanges": [page("N")],
            }
        }
    )
    P.PrefixIndexSpecialPageProvider(t).make_list("Pre")
    assert t.last("query")["apprefix"] == "Pre"
    P.AllRedirectsSpecialPageProvider(t, namespace=10).make_list("A")
    p = t.last("query")
    assert p["apfilterredir"] == "redirects" and p["apnamespace"] == "10"
    P.ProtectedPagesSpecialPageProvider(t, protection_level="autoconfirmed").make_list("")
    p = t.last("query")
    assert p["apprtype"] == "edit" and p["apprlevel"] == "autoconfirmed"
    P.LinkSearchSpecialPageProvider(t).make_list("https://example.org/x", "example.com")
    first, second = [r[0] for r in t.requests[-2:]]
    assert (first["euprotocol"], first["euquery"]) == ("https", "example.org/x")
    assert (second["euprotocol"], second["euquery"]) == ("", "example.com")
    assert [a.name for a in P.DisambiguationPagesSpecialPageProvider(t).make_list()] == ["D"]
    assert t.last("query")["eititle"] == "Template:Disambiguation"
    P.RandomRedirectsSpecialPageProvider(t).make_list()
    assert t.last("query")["rnfilterredir"] == "redirects"
    P.NewPagesListProvider(t).make_list()
    p = t.last("query")
    assert p["rctype"] == "new" and p["rcshow"] == "!redirect"


def test_image_file_links_strips_file_namespace() -> None:
    t = FakeTransport(lambda p: {"query": {"imageusage": [page("A")]}})
    P.ImageFileLinksListProvider(t).make_list("Image:Foo.jpg", "file:Bar.png", "Baz.svg")
    titles = [r[0]["iutitle"] for r in t.requests]
    assert titles == ["File:Foo.jpg", "File:Bar.png", "File:Baz.svg"]


def test_titles_from_text() -> None:
    linked = "* [[Foo]]\n* [[:bar|Bar]]\n* [[de:Foo]]\n* [[#Section]]\n* [[simple:X]]"
    assert [a.name for a in P.titles_from_text(linked)] == ["Foo", "Bar"]
    plain = "Foo\r\n\r\nbar baz\r\n<invalid>\r\n"
    assert [a.name for a in P.titles_from_text(plain)] == ["Foo", "Bar baz"]
    assert [a.name for a in P.titles_from_text(plain, validate=False)] == [
        "Foo",
        "Bar baz",
        "<invalid>",
    ]


def test_text_file_providers(tmp_path: Path) -> None:
    f = tmp_path / "list.txt"
    f.write_text("[[കേരളം]]\n[[Ünal]]", encoding="utf-8")
    assert [a.name for a in P.TextFileListProvider().make_list(str(f))] == ["കേരളം", "Ünal"]
    g = tmp_path / "ansi.txt"
    g.write_bytes("Café\r\n".encode("cp1252"))
    assert [a.name for a in P.TextFileListProviderWindows1252().make_list(str(g))] == ["Café"]


def test_provider_catalogue() -> None:
    names = [p.display_text for p in P.API_PROVIDERS]
    assert len(names) == len(set(names))
    assert all(names)


def test_split_generator_options() -> None:
    assert split_options('-cat:"Living people" -ns:0') == ["-cat:Living people", "-ns:0"]


@pytest.mark.network
def test_pagegenerators_against_wikipedia() -> None:  # pragma: no cover - needs internet
    from awb_x.api.transport import pywikibot_site
    from awb_x.lists.pagegenerators import PagegeneratorsListProvider

    provider = PagegeneratorsListProvider(pywikibot_site("en", "wikipedia"), limit=5)
    assert len(provider.make_list("-prefixindex:Wikipedia:AutoWikiBrowser/")) == 5
