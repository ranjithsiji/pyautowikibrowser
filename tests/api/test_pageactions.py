"""Move, delete and protect (AWB ApiEdit.Move/Delete/Protect, ArticleActionDialog)."""

from collections.abc import Mapping
from typing import Any

from pyawb.api import pageactions as pa
from tests.api.fakes import FakeTransport

DROPDOWN = "* أسباب عامة\n** تخريب\n** محتوى غير مناسب\n*Other\n**Spam\n"


def test_parse_dropdown() -> None:
    assert pa.parse_dropdown(DROPDOWN) == ["تخريب", "محتوى غير مناسب", "Spam"]
    assert pa.parse_dropdown("* only a group") == []


def test_reasons_from_the_wiki_or_awb() -> None:
    def wiki(p: Mapping[str, str]) -> Mapping[str, Any]:
        assert p["ammessages"] == "deletereason-dropdown" and p["amlang"] == "content"
        return {"query": {"allmessages": [{"name": p["ammessages"], "content": DROPDOWN}]}}

    assert pa.reasons(FakeTransport(wiki), pa.PageAction.DELETE)[0] == "تخريب"
    missing = FakeTransport(lambda p: {"query": {"allmessages": [{"name": "x", "missing": True}]}})
    assert pa.reasons(missing, pa.PageAction.MOVE) == list(pa.AWB_REASONS[pa.PageAction.MOVE])


def test_requests() -> None:
    t = FakeTransport(lambda p: {p["action"]: {"title": "X"}})
    pa.move(t, "Old", pa.MoveRequest("New", "typo", no_redirect=True, watch=True))
    p, post, token = t.requests[-1]
    assert post and token == "csrf"
    assert (p["from"], p["to"], p["movetalk"], p["noredirect"], p["watchlist"]) == (
        "Old", "New", "1", "1", "watch",
    )  # fmt: skip
    pa.delete(t, "Old", "spam")
    p, _, _ = t.requests[-1]
    assert p["title"] == "Old" and "watchlist" not in p
    pa.protect(t, "Old", pa.ProtectRequest("vandalism", edit="sysop", expiry="1 week"))
    p, _, _ = t.requests[-1]
    assert p["protections"] == "edit=sysop|move=all" and p["expiry"] == "1 week|1 week"
    assert "cascade" not in p


def test_tag_and_levels() -> None:
    assert (
        pa.with_tag("spam", " using [[Project:AWB|AWB]]", True)
        == "spam (using [[Project:AWB|AWB]])"
    )
    assert pa.with_tag("spam", " using AWB", False) == "spam"
    assert pa.protection_levels({"restrictions": {"levels": ["", "autoconfirmed", "sysop"]}}) == [
        "",
        "autoconfirmed",
        "sysop",
    ]
    assert pa.protection_levels({}) == list(pa.DEFAULT_LEVELS)
