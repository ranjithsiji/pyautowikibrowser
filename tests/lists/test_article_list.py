"""ArticleList operations used by the edit loop (AWB ListMaker.SelectedArticle, Remove,
ReplaceArticle)."""

from pyawb.core.article import Article
from pyawb.lists.listmaker import ArticleList


def make(*titles: str) -> ArticleList:
    lst = ArticleList()
    lst.add([Article(t) for t in titles])
    return lst


def names(lst: ArticleList) -> list[str]:
    return [a.name for a in lst]


def test_selected_article_defaults_to_first() -> None:
    assert ArticleList().selected_article() is None
    lst = make("A", "B")
    assert lst.selected_article() == "A" and lst.selected_index == 0


def test_remove_selected_page_selects_the_next() -> None:
    lst = make("A", "B", "C")
    lst.set_selected(1, True)
    assert lst.remove(Article("B"))
    assert names(lst) == ["A", "C"] and lst.selected_article() == "C"
    assert lst.remove("C")
    assert names(lst) == ["A"] and lst.selected_article() == "A"
    assert not lst.remove("Z")
    assert lst.remove("A") and lst.selected_article() is None


def test_remove_unselected_page_removes_first_instance() -> None:
    lst = make("A", "B", "A")
    lst.set_selected(1, True)
    assert lst.remove("A")
    assert names(lst) == ["B", "A"] and lst.selected_index == 0


def test_replace_article_keeps_position() -> None:
    lst = make("A", "Redirect", "Redirect")
    lst.set_selected(2, True)
    lst.replace_article("Redirect", Article("Target"))
    assert names(lst) == ["A", "Redirect", "Target"] and lst.selected_index == 2
    lst.replace_article("A", Article("Ä"))
    assert names(lst) == ["Ä", "Redirect", "Target"] and lst.selected_index == 0
