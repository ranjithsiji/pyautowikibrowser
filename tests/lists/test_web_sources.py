"""HTML scraper, CheckWiki and user-defined number sources (AWB NonMWListProviders.cs,
AdvancedRegexHtmlScraper.cs, CategoryRecursiveUserDefinedLevel / UserContribUserDefinedNumber)."""

import pytest

from pyawb.lists import providers as P
from pyawb.lists.sources import ADD_FROM_SELECTED, SourceUnavailable, WikiContext, build, source
from tests.api.fakes import FakeTransport


class FakeWeb:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.asked: list[str] = []

    def get_html(self, url: str) -> str:
        self.asked.append(url)
        return self.pages[url]


SCRAPED = (
    "<html><head><title>x</title></head><body>\n<h1>Heading</h1>\nFoo &amp; bar\n"
    "Caf&eacute;<br />\n\nO&quot;Neil\n</body></html>"
)


def test_html_scraper_takes_body_lines() -> None:
    web = FakeWeb({"http://example.org/list": SCRAPED})
    p = P.HTMLPageScraperListProvider(web)
    assert [a.name for a in p.make_list("example.org/list")] == ["Foo & bar", "Café", 'O"Neil']
    assert web.asked == ["http://example.org/list"]  # "http://" added as AWB does


def test_html_scraper_rejects_bad_urls() -> None:
    with pytest.raises(ValueError, match="not valid"):
        P.HTMLPageScraperListProvider(FakeWeb({})).make_list("http://")


CHECKWIKI = "<body>\n<pre>\nO&#039;Brien\nA’b\nC &amp; D\n</pre>\n</body>"


def test_checkwiki_pages() -> None:
    web = FakeWeb({"https://checkwiki.example/x": CHECKWIKI})
    names = [a.name for a in P.CheckWikiListProvider(web).make_list("https://checkwiki.example/x")]
    assert names == ["O'Brien", "A'b", "C & D"]


def test_checkwiki_number_uses_the_wiki_id() -> None:
    url = f"{P.CHECKWIKI_URL}?project=mlwiki&view=bots&id=64&offset=0"
    web = FakeWeb({url: CHECKWIKI})
    p = build(
        source("CheckWiki error (number)"),
        WikiContext(FakeTransport(), site_id="mlwiki", web=web),
    )
    assert [a.name for a in p.make_list("64")] == ["O'Brien", "A'b", "C & D"]
    with pytest.raises(SourceUnavailable):
        build(source("CheckWiki error (number)"), None)


def test_advanced_regex_scraper() -> None:
    html = '<a title="Foo">x</a><A TITLE="Bar &amp; baz">y</A><a title="">z</a>'
    web = FakeWeb({"http://example.org": html})
    src = source("HTML Scraper (advanced regex)")
    assert not src.needs_wiki
    p = build(src, WikiContext(FakeTransport(), web=web), settings={"pattern": r'title="([^"]*)"'})
    assert [a.name for a in p.make_list("http://example.org")] == ["Foo", "Bar & baz"]
    p = build(
        src,
        WikiContext(FakeTransport(), web=web),
        settings={"pattern": r'title="([^"]*)"', "case_sensitive": True},
    )
    assert [a.name for a in p.make_list("http://example.org")] == ["Foo"]
    with pytest.raises(AttributeError):
        build(src, None, settings={"nonsense": 1})


def test_user_defined_numbers_are_clamped() -> None:
    wiki = WikiContext(FakeTransport())
    p = build(source("Category (recurse user defined level)"), wiki, option=99)
    assert isinstance(p, P.CategoryRecursiveUserDefinedLevelListProvider) and p.depth == 30
    p = build(source("Category (recurse user defined level)"), wiki)
    assert isinstance(p, P.CategoryRecursiveUserDefinedLevelListProvider) and p.depth == 1
    p = build(source("User contribs (user defined number)"), wiki, option=0)
    assert isinstance(p, P.UserContribUserDefinedNumberListProvider) and p.number_of_edits == 1
    assert source("Category").option is None


def test_add_selected_from_sources_take_titles() -> None:
    names = {s.name for s in ADD_FROM_SELECTED}
    assert {"Category", "What links here", "Links on page"} <= names
    assert "HTML Scraper" not in names and "Manual list" not in names
    assert "My watchlist" not in names  # no input
