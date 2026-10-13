"""List filter (AWB ListFilterForm.btnApply_Click)."""

import pytest
import regex

from pyawb.core.article import Article
from pyawb.lists.listfilter import ListFilter, SetOperation


def arts(*titles: str) -> list[Article]:
    return [Article(t) for t in titles]


def names(items: list[Article]) -> list[str]:
    return [a.name for a in items]


PAGES = arts("Zeta", "Talk:Alpha", "Beta", "User:Gamma", "Beta", "Template:Delta")


def test_defaults_remove_duplicates_and_sort() -> None:
    assert names(ListFilter().apply(PAGES)) == [
        "Beta",
        "Talk:Alpha",
        "Template:Delta",
        "User:Gamma",
        "Zeta",
    ]
    assert names(ListFilter(remove_duplicates=False, sort=False).apply(PAGES)) == names(PAGES)


def test_namespaces_to_keep() -> None:
    f = ListFilter(namespaces=frozenset({0, 10}), sort=False)
    assert names(f.apply(PAGES)) == ["Zeta", "Beta", "Template:Delta"]


def test_titles_containing() -> None:
    f = ListFilter(remove_containing="eta", sort=False)
    assert names(f.apply(PAGES)) == ["Talk:Alpha", "User:Gamma", "Template:Delta"]
    f = ListFilter(keep_containing="e:D", sort=False)  # literal unless regex
    assert names(f.apply(PAGES)) == ["Template:Delta"]
    f = ListFilter(keep_containing="^[A-Z][a-z]+$", is_regex=True, sort=False)
    assert names(f.apply(PAGES)) == ["Zeta", "Beta"]
    with pytest.raises((ValueError, regex.error)):
        ListFilter(keep_containing="(", is_regex=True).apply(PAGES)


def test_set_operations_keep_order() -> None:
    other = ("Beta", "Template:Delta", "Nowhere")
    f = ListFilter(other=other, sort=False)
    assert names(f.apply(PAGES)) == ["Zeta", "Talk:Alpha", "User:Gamma"]
    f = ListFilter(other=other, operation=SetOperation.INTERSECTION, sort=False)
    assert names(f.apply(PAGES)) == ["Beta", "Template:Delta"]
