"""Tagger's wiki lookups and template expansion over the API."""

from awb_l.api.tagger import WikiTaggerLookups, WikiTemplateExpander, count_incoming_links
from awb_l.core.rx import DotNetRegex

from .fakes import FakeTransport


def test_count_incoming_links_through_redirects() -> None:
    result = {
        "query": {
            "backlinks": [
                {"pageid": 1, "ns": 0, "title": "A"},
                {
                    "pageid": 2,
                    "ns": 0,
                    "title": "Redirect to page",
                    "redirect": True,
                    "redirlinks": [{"pageid": 3, "ns": 0, "title": "B"}],
                },
            ]
        }
    }
    assert count_incoming_links(result) == 2


def test_orphan_status() -> None:
    t = FakeTransport(lambda p: {"query": {"backlinks": [{"pageid": 1, "ns": 0, "title": "A"}]}})
    lookups = WikiTaggerLookups(t)
    assert lookups.orphan_status("X", False) == (True, True, 1)
    assert lookups.orphan_status("X", True) == (True, False, 1)
    p = t.requests[-1][0]
    assert (
        p["blnamespace"] == "0" and p["blfilterredir"] == "nonredirects" and p["blredirect"] == "1"
    )

    def fail(p: dict[str, str]) -> dict[str, object]:
        return {"error": {"code": "internal_api_error", "info": "boom"}}

    assert WikiTaggerLookups(FakeTransport(fail)).orphan_status("X", False) == (False, False, 0)


def test_total_categories_and_links() -> None:
    def handler(p: dict[str, str]) -> dict[str, object]:
        if p.get("prop") == "categories":
            assert p["clshow"] == "!hidden"
            cats = [
                {"ns": 14, "title": "Category:Writers"},
                {"ns": 14, "title": "Category:Writer stubs"},
            ]
            return {"query": {"pages": [{"title": "X", "categories": cats}]}}
        assert p["plnamespace"] == "0"
        return {"query": {"pages": [{"title": "X", "links": [{"ns": 0, "title": "Y"}] * 3}]}}

    lookups = WikiTaggerLookups(FakeTransport(handler))
    assert lookups.total_categories("X", 2) == 2  # text categories: no API call
    assert lookups.total_categories("X", 0) == 1  # stub category not counted
    assert lookups.mainspace_links("X") == 3


def test_template_expander() -> None:
    def handler(p: dict[str, str]) -> dict[str, object]:
        if p["text"] == "{{broken}}":
            return {"error": {"code": "badtitle", "info": "Bad title"}}
        return {"expandtemplates": {"wikitext": "Hi &amp; " + p["title"]}}

    t = FakeTransport(handler)
    expand = WikiTemplateExpander(t)
    regexes = {DotNetRegex(r"\{\{(?:welcome|broken)\}\}"): ""}
    text = "{{welcome}} <!-- {{welcome}} --> {{welcome}} {{broken}}"
    assert expand(text, "User talk:X", regexes, False) == (
        "Hi & User talk:X <!-- Hi & User talk:X --> Hi & User talk:X {{broken}}"
    )
    # AWB replaces every copy of the call, including in comments, once one copy outside a
    # comment matched
    assert expand("{{welcome}}", "T", regexes, True) == "Hi & T<!-- {{welcome}} -->"
