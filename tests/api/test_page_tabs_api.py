"""History and What links here from the API (the tabs AWB showed as web pages)."""

from collections.abc import Mapping
from typing import Any

from pyawb.api.pageinfo import page_history, what_links_here
from tests.api.fakes import FakeTransport


def test_page_history_with_size_changes() -> None:
    def handler(p: Mapping[str, str]) -> Mapping[str, Any]:
        assert p["prop"] == "revisions" and p["rvlimit"] == "3"
        revs = [
            {"revid": 3, "parentid": 2, "timestamp": "2026-10-01T10:00:00Z", "user": "A",
             "comment": "ശുചീകരണം", "size": 120, "minor": True},
            {"revid": 2, "parentid": 1, "timestamp": "2026-09-01T10:00:00Z", "user": "B",
             "comment": "", "size": 100},
            {"revid": 1, "parentid": 0, "timestamp": "2026-08-01T10:00:00Z", "user": "C",
             "comment": "new", "size": 130},
        ]  # fmt: skip
        return {"query": {"pages": [{"title": "X", "revisions": revs}]}}

    revs = page_history(FakeTransport(handler), "X", limit=2)
    assert [r.revid for r in revs] == [3, 2]
    assert revs[0].size_change == 20 and revs[0].minor and revs[0].comment == "ശുചീകരണം"
    assert revs[1].size_change == -30  # from the extra, older revision


def test_history_of_a_missing_page() -> None:
    t = FakeTransport(lambda p: {"query": {"pages": [{"title": "X", "missing": True}]}})
    assert page_history(t, "X") == []


def test_what_links_here() -> None:
    def handler(p: Mapping[str, str]) -> Mapping[str, Any]:
        if p.get("list") == "embeddedin":
            return {"query": {"embeddedin": [{"title": "Template:Box", "ns": 10}]}}
        if p.get("blfilterredir") == "redirects":
            return {"query": {"backlinks": [{"title": "Old name", "ns": 0}]}}
        return {"query": {"backlinks": [{"title": "Old name", "ns": 0}, {"title": "قط", "ns": 0}]}}

    links = what_links_here(FakeTransport(handler), "X")
    assert [(b.title, b.kind) for b in links] == [
        ("قط", "link"),
        ("Old name", "redirect"),
        ("Template:Box", "transclusion"),
    ]
