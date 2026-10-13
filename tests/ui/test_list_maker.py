"""The list maker's context menu, List menu actions and new inputs (AWB ListMaker.cs)."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog
from pytestqt.qtbot import QtBot

from pyawb.core.article import Article
from pyawb.core.site import current_site
from pyawb.lists.listfilter import ListFilter
from pyawb.lists.sources import WikiContext, source
from pyawb.ui.list_dialogs import ListFilterDialog
from pyawb.ui.list_maker import RICH_ROLE, ListMaker
from tests.api.fakes import FakeTransport


def make(qtbot: QtBot, *titles: str) -> ListMaker:
    lm = ListMaker()
    qtbot.addWidget(lm)
    lm.articles.add([Article(t) for t in titles])
    lm.refresh()
    return lm


def names(lm: ListMaker) -> list[str]:
    return [a.name for a in lm.articles]


def select(lm: ListMaker, *rows: int) -> None:
    lm.list.clearSelection()
    for r in rows:
        lm.list.item(r).setSelected(True)


def menu_titles(lm: ListMaker) -> list[str]:
    return [a.text() for a in lm.context_menu().actions() if not a.isSeparator()]


def test_context_menu_items_and_enabling(qtbot: QtBot) -> None:
    lm = make(qtbot, "A")
    lm.list.clearSelection()
    assert menu_titles(lm) == [
        "Open in browser",
        "Open history in browser",
        "Cut",
        "Copy",
        "Paste",
        "Select",
        "Remove",
        "Add selected to list from",
        "Move to top",
        "Move to bottom",
        "Convert to talk pages",
        "Convert from talk pages",
        "Format page titles per displaytitle",
        "Filter…",
        "Save list…",
        "Sort alphabetically",
        "Sort reverse alphabetically",
    ]
    lm.context_menu()
    assert not lm.open_action.isEnabled() and not lm.cut_action.isEnabled()
    assert not lm.sort_action.isEnabled()  # one page: nothing to sort (AWB)
    select(lm, 0)
    lm.context_menu()
    assert lm.open_action.isEnabled() and lm.cut_action.isEnabled()


def test_copy_cut_paste(qtbot: QtBot) -> None:
    lm = make(qtbot, "A", "B", "C")
    select(lm, 0, 2)
    lm.copy()
    assert QApplication.clipboard().text() == "A\nC"
    lm.cut()
    assert names(lm) == ["B"]
    QApplication.clipboard().setText("[[foo]]\nhttps://en.wikipedia.org/wiki/Bar_baz|Qux")
    lm.paste()
    assert names(lm) == ["B", "Foo", "Bar baz", "Qux"]


def test_select_and_move(qtbot: QtBot) -> None:
    lm = make(qtbot, "A", "B", "C", "D")
    select(lm, 1)
    lm.invert_selection()
    assert sorted(i.row() for i in lm.list.selectedIndexes()) == [0, 2, 3]
    select(lm, 2, 3)
    lm.move_selected(True)
    assert names(lm) == ["C", "D", "A", "B"]
    assert sorted(i.row() for i in lm.list.selectedIndexes()) == [0, 1]
    lm.select_all()
    assert len(lm.list.selectedIndexes()) == 4
    lm.select_none()
    assert not lm.list.selectedIndexes()


def test_list_menu_toggles(qtbot: QtBot) -> None:
    lm = make(qtbot, "B", "Talk:X", "A", "B")
    lm.filter_duplicates.setChecked(True)
    assert names(lm) == ["B", "Talk:X", "A"]
    lm.keep_alphabetized.setChecked(True)
    assert names(lm) == ["A", "B", "Talk:X"]
    lm.filter_non_main.setChecked(True)
    assert names(lm) == ["A", "B"]
    lm.add_line.setText("[[Talk:Zed]]")
    lm.add_typed_page()  # not main space: not added while the toggle is on
    lm.add_line.setText("c")
    lm.add_typed_page()
    assert names(lm) == ["A", "B", "C"] and lm.add_line.text() == ""
    assert [a.text() if a else None for a in lm.list_menu_actions()][:3] == [
        "Keep alphabetized",
        "Remove duplicates",
        "Remove non-main space",
    ]
    assert lm.keep_alphabetized.shortcut().toString() == "Ctrl+Shift+A"


def test_convert_talk_pages(qtbot: QtBot) -> None:
    lm = make(qtbot, "Foo", "User:Bar")
    lm.convert_to_talk_pages()
    assert names(lm) == ["Talk:Foo", "User talk:Bar"]
    lm.convert_from_talk_pages()
    assert names(lm) == ["Foo", "User:Bar"]


def test_clear_asks_for_long_lists(qtbot: QtBot, message_boxes: list[tuple[str, str]]) -> None:
    lm = make(qtbot, *[f"P{i}" for i in range(101)])
    lm.ask_clear()  # the test answers No
    assert len(lm.articles) == 101 and message_boxes[-1][0] == "question"
    lm = make(qtbot, "A")
    lm.ask_clear()
    assert len(lm.articles) == 0


def test_filter_keeps_current_page(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    lm = make(qtbot, "Zeta", "Talk:Beta", "Alpha", "Alpha")
    lm.select_index(2)
    lm.apply_filter(ListFilter(namespaces=frozenset({0})))
    assert names(lm) == ["Alpha", "Zeta"]
    assert lm.articles.selected_article() == "Alpha"

    def accept(dialog: ListFilterDialog) -> int:
        dialog.remove_check.setChecked(True)
        dialog.remove_text.setText("eta")
        dialog._apply()
        return dialog.result()

    monkeypatch.setattr(ListFilterDialog, "exec", accept)
    lm.filter()
    assert names(lm) == ["Alpha"] and lm.list_filter.remove_containing == "eta"


def test_filter_dialog_namespaces(qtbot: QtBot) -> None:
    dialog = ListFilterDialog(current_site(), ListFilter(namespaces=frozenset({0, 1})))
    qtbot.addWidget(dialog)
    assert dialog.value().namespaces == {0, 1}
    dialog.talk_all.setChecked(True)
    assert {0, 1, 3, 5} <= dialog.value().namespaces
    dialog.content_all.setChecked(True)
    dialog.content_all.setChecked(False)
    assert 0 not in dialog.value().namespaces


def test_save_list(qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lm = make(qtbot, "A", "B")
    target = tmp_path / "pages"

    def ask(*args: Any) -> tuple[str, str]:
        filters = args[3].split(";;")
        return str(target), filters[2]  # CSV

    monkeypatch.setattr(QFileDialog, "getSaveFileName", ask)
    lm.save_list()
    assert (tmp_path / "pages.txt").read_text(encoding="utf-8") == "A, B"


def test_number_option_shows_for_its_sources(qtbot: QtBot) -> None:
    lm = make(qtbot)
    lm.source.setCurrentIndex(lm.source.findData("Category (recurse user defined level)"))
    assert lm.option.isVisibleTo(lm) and lm.option.maximum() == 30
    lm.source.setCurrentIndex(lm.source.findData("Category"))
    assert not lm.option.isVisibleTo(lm)


def test_stop_drops_the_result(qtbot: QtBot) -> None:
    lm = make(qtbot)
    lm._generation = 5
    lm._set_busy(True)
    assert lm.stop_button.isVisibleTo(lm)
    lm.stop()
    lm._list_made([Article("Late")], generation=5)
    assert names(lm) == [] and not lm.busy and not lm.stop_button.isVisibleTo(lm)


def test_add_selected_from(qtbot: QtBot) -> None:
    calls: list[Mapping[str, str]] = []

    def handler(p: Mapping[str, str]) -> Mapping[str, Any]:
        calls.append(p)
        return {"query": {"pages": [{"title": "A", "links": [{"ns": 0, "title": "Linked"}]}]}}

    lm = make(qtbot, "A")
    lm.set_wiki(WikiContext(FakeTransport(handler)), current_site())
    select(lm, 0)
    lm.add_selected_from(source("Links on page"))
    qtbot.waitUntil(lambda: not lm.busy)
    assert names(lm) == ["A", "Linked"] and calls[0]["titles"] == "A"


def test_display_titles(qtbot: QtBot) -> None:
    def handler(p: Mapping[str, str]) -> Mapping[str, Any]:
        return {"query": {"pages": [{"title": "Foo (film)", "displaytitle": "<i>Foo</i> (film)"}]}}

    lm = make(qtbot, "Foo (film)", "Bar")
    lm.set_wiki(WikiContext(FakeTransport(handler)), current_site())
    lm.format_display_title.setChecked(True)
    qtbot.waitUntil(lambda: lm.list.item(0).data(RICH_ROLE) is not None)
    assert lm.list.item(0).data(RICH_ROLE) == "<i>Foo</i> (film)"
    assert lm.list.item(1).data(RICH_ROLE) is None
    lm.format_display_title.setChecked(False)
    assert lm.list.item(0).data(RICH_ROLE) is None
