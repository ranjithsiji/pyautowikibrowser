"""The list menu and context menu commands on ArticleList (AWB ListMaker.cs and ListBox2.cs)."""

from pathlib import Path

from pyawb.core import tools
from pyawb.core.article import Article
from pyawb.lists.listmaker import ArticleList, OutputFormat, format_list, save_list


def make(*titles: str) -> ArticleList:
    lst = ArticleList()
    lst.add([Article(t) for t in titles])
    return lst


def names(lst: ArticleList) -> list[str]:
    return [a.name for a in lst]


def test_sort_is_mediawiki_order_and_keeps_the_selection() -> None:
    lst = make("b", "Z", "a", "Ä")
    lst.set_selected(0, True)  # "b"
    lst.sort()
    assert names(lst) == ["Z", "a", "b", "Ä"]  # code point order, not locale order
    assert lst.get_selected_article_list() == ["b"]
    lst.sort(reverse=True)
    assert names(lst) == ["Ä", "b", "a", "Z"]
    assert lst.get_selected_article_list() == ["b"]


def test_keep_alphabetized_sorts_on_add() -> None:
    lst = ArticleList()
    lst.auto_alpha = True
    lst.add([Article("C"), Article("A")])
    lst.add("B")
    assert names(lst) == ["A", "B", "C"]


def test_select_all_none_inverse() -> None:
    lst = make("A", "B", "C")
    lst.set_selected(1, True)
    lst.invert_selection()
    assert lst.selected_indices == [0, 2]
    lst.select_all()
    assert lst.selected_indices == [0, 1, 2]
    lst.select_none()
    assert lst.selected_indices == []


def test_copy_text_is_the_selected_titles() -> None:
    lst = make("A", "B", "C")
    lst.set_selected(0, True)
    lst.set_selected(2, True)
    assert lst.copy_text() == "A\nC"
    assert make("A").copy_text() == ""


def test_move_selected_to_top_and_bottom_keeps_order() -> None:
    lst = make("A", "B", "C", "D", "B")
    lst.set_selected(2, True)  # C
    lst.set_selected(4, True)  # the second B
    lst.move_selected(to_top=True)
    assert names(lst) == ["C", "B", "A", "B", "D"]
    assert lst.selected_indices == [0, 1]
    lst.move_selected(to_top=False)
    assert names(lst) == ["A", "B", "D", "C", "B"]
    assert lst.selected_indices == [3, 4]


def test_convert_to_and_from_talk_pages() -> None:
    lst = make("Foo", "Talk:Bar", "User:Baz", "Special:Random")
    lst.convert_to_talk_pages()
    assert names(lst) == ["Talk:Foo", "Talk:Bar", "User talk:Baz", "Special:Random"]
    lst.convert_from_talk_pages()
    assert names(lst) == ["Foo", "Bar", "User:Baz", "Special:Random"]


def test_convert_goes_through_the_duplicate_filter() -> None:
    lst = make("Foo", "Talk:Foo")
    lst.filter_duplicates = True
    lst.convert_to_talk_pages()
    assert names(lst) == ["Talk:Foo"]


def test_save_list_formats(tmp_path: Path) -> None:
    pages = [Article("A"), Article("Category:B")]
    assert format_list(pages, OutputFormat.WIKI_TEXT) == "# [[:A]]\n# [[:Category:B]]\n"
    assert format_list(pages, OutputFormat.PLAIN_TEXT) == "A\nCategory:B\n"
    assert format_list(pages, OutputFormat.CSV) == "A, Category:B"
    assert format_list(pages, OutputFormat.CSV_WIKI_TEXT) == "[[:A]], [[:Category:B]]"
    assert format_list([], OutputFormat.CSV) == ""
    path = tmp_path / "list.txt"
    save_list([Article("മലയാളം")], path, OutputFormat.PLAIN_TEXT)
    assert path.read_text(encoding="utf-8") == "മലയാളം\n"


def test_history_and_page_urls() -> None:
    assert tools.non_prettified_url("Foo bar/baz") == (
        "https://en.wikipedia.org/w/index.php?title=Foo_bar/baz"
    )
    assert tools.get_article_history_url("A&B").endswith("index.php?title=A%26B&action=history")
    assert tools.get_edit_url("X").endswith("?title=X&action=edit")
