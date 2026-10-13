"""Format page titles per displaytitle (AWB ListMaker.lbArticles_DrawItem, extended)."""

from collections.abc import Mapping
from typing import Any

from pyawb.api.pageinfo import display_titles
from pyawb.lists.displaytitle import display_title_html
from tests.api.fakes import FakeTransport


def test_display_title_html() -> None:
    assert display_title_html(None, "X") is None
    assert display_title_html("Foo", "Foo") is None
    assert display_title_html("<i>Foo</i> (film)", "Foo (film)") == "<i>Foo</i> (film)"
    assert display_title_html("iPod", "IPod") == "iPod"  # first letter lower case
    # AWB dropped sub/sup; they are kept here, as are bold and italics
    assert display_title_html("H<sub>2</sub>O", "H2O") == "H<sub>2</sub>O"
    assert display_title_html("<em>A</em> <strong>B</strong>", "A B") == "<i>A</i> <b>B</b>"
    # hidden spans go, other tags are dropped but keep their text
    hidden = '<span style="position:absolute; top:-9999px">Hidden</span>Shown'
    assert display_title_html(hidden, "Shown") is None
    assert display_title_html('<span class="x">Bar</span>', "Bar") is None
    assert display_title_html("A &amp; B", "A & B") is None
    assert display_title_html("<i>ഇ</i>", "ഇ") == "<i>ഇ</i>"


def test_display_titles_in_batches() -> None:
    def handler(p: dict[str, str]) -> Mapping[str, Any]:
        assert p["prop"] == "info" and p["inprop"] == "displaytitle"
        titles = [t[0].upper() + t[1:] for t in p["titles"].split("|")]  # the wiki normalises
        pages: list[dict[str, Any]] = [
            {"title": t, "displaytitle": f"<i>{t}</i>"} for t in titles if t != "Missing"
        ]
        pages.append({"title": "Missing", "missing": True, "displaytitle": "Missing"})
        return {
            "query": {"normalized": [{"from": "foo", "to": "Foo"}], "pages": pages},
        }

    fake = FakeTransport(handler)
    names = ["foo"] + [f"P{i}" for i in range(60)] + ["Missing"]
    result = display_titles(fake, names)
    assert len(fake.requests) == 2
    assert result["foo"] == "<i>Foo</i>" and result["P59"] == "<i>P59</i>"
    assert "Missing" not in result
