"""Locating and reading a wiki's typo list (RETF)."""

import pytest

from pyawb.api import siteinfo
from pyawb.api.session import WikiSession
from pyawb.api.typolist import (
    ENGLISH_TYPOS_TITLE,
    fetch_english_typo_list,
    fetch_typo_list,
    typo_location,
)

from .fakes import FakeTransport
from .test_session import approved_session


def test_default_location_uses_the_project_namespace() -> None:
    session, _ = approved_session()  # Arabic Wikipedia
    loc = typo_location("", session.site)
    assert loc.title == "ويكيبيديا:AutoWikiBrowser/Typos" and loc.on_this_wiki


@pytest.mark.parametrize(
    ("link", "title", "lang", "project"),
    [
        ("Project:AWB/Typos", "Project:AWB/Typos", None, None),
        ("https://ar.wikipedia.org/wiki/%D9%88:Typos", "و:Typos", None, None),
        ("https://en.wikipedia.org/wiki/" + ENGLISH_TYPOS_TITLE,
         ENGLISH_TYPOS_TITLE, "en", "wikipedia"),
        ("//fr.wikipedia.org/w/index.php?title=Wikip%C3%A9dia:AutoWikiBrowser/Typos&action=raw",
         "Wikipédia:AutoWikiBrowser/Typos", "fr", "wikipedia"),
    ],
)  # fmt: skip
def test_typolink(link: str, title: str, lang: str | None, project: str | None) -> None:
    session, _ = approved_session()
    loc = typo_location(link, session.site)
    assert (loc.title, loc.lang, loc.project) == (title, lang, project)


def test_typolink_off_wikimedia_is_refused() -> None:
    session, _ = approved_session()
    with pytest.raises(ValueError):
        typo_location("https://example.org/typos.txt", session.site)


def test_fetch_from_this_wiki_english_wikipedia_and_another_wiki() -> None:
    session, t = approved_session()
    t.pages["ويكيبيديا:AutoWikiBrowser/Typos"] = '<Typo word="a" find="\\bقط\\b" replace="هر" />'
    loc, text = fetch_typo_list(session, "")
    assert loc.on_this_wiki and "هر" in text

    en = FakeTransport()
    en.pages[ENGLISH_TYPOS_TITLE] = '<Typo find="teh" replace="the" />'
    session2 = WikiSession(t, siteinfo.base_site_config("ar", "wikipedia"), global_transport=en)
    _, text = fetch_typo_list(session2, "https://en.wikipedia.org/wiki/" + ENGLISH_TYPOS_TITLE)
    assert "teh" in text
    assert "teh" in fetch_english_typo_list(session2)

    fr = FakeTransport()
    fr.pages["Typos"] = "fr list"
    asked: list[tuple[str, str]] = []

    def other(lang: str, project: str) -> FakeTransport:
        asked.append((lang, project))
        return fr

    _, text = fetch_typo_list(session, "https://fr.wikipedia.org/wiki/Typos", other)
    assert text == "fr list" and asked == [("fr", "wikipedia")]


def test_missing_list_is_empty() -> None:
    session, _ = approved_session()
    assert fetch_typo_list(session, "")[1] == ""
