"""encapsulate/replace actions.

The first test is ported from MediaWiki core's tests/qunit/resources/jquery.textSelection.test.js
(encapsulateText); the others cover WikiEditor's doAction (regex/regexReplace) and the toolbar data.
"""

from __future__ import annotations

import pytest

from pyawb.editor.messages import Messages
from pyawb.editor.textselection import (
    EncapsulateOptions,
    TextAction,
    do_action,
    encapsulate_selection,
)
from pyawb.editor.toolbar import Toolbar, build_toolbar

SIG = EncapsulateOptions(pre="--~~~~")
BOLD = EncapsulateOptions(pre="'''", peri="Bold text", post="'''")
# core's test also passes regex/regexReplace, which encapsulateSelection ignores
H2 = EncapsulateOptions(pre="== ", peri="Heading 2", post=" ==", ownline=True)
ULIST = EncapsulateOptions(
    pre="* ", peri="Bulleted list item", post="", ownline=True, splitlines=True
)

ENCAPSULATE_CASES = {
    "Adding sig to end of text": ("Wikilove dude! ", 15, 15, SIG, "Wikilove dude! --~~~~", ""),
    "Adding bold to empty": ("", 0, 0, BOLD, "'''Bold text'''", "Bold text"),
    "Adding bold to existing text": (
        "Now is the time for all good men to come to the aid of their country",
        20,
        32,
        BOLD,
        "Now is the time for '''all good men''' to come to the aid of their country",
        "",
    ),
    "ownline option: adding new h2": (
        "Before\nAfter",
        7,
        7,
        H2,
        "Before\n== Heading 2 ==\nAfter",
        "Heading 2",
    ),
    "ownline option: turn a whole line into new h2": (
        "Before\nMy heading\nAfter",
        7,
        17,
        H2,
        "Before\n== My heading ==\nAfter",
        "",
    ),
    "ownline option: turn a partial line into new h2": (
        "BeforeMy headingAfter",
        6,
        16,
        H2,
        "Before\n== My heading ==\nAfter",
        "",
    ),
    "splitlines option: no selection, insert new list item": (
        "Before\nAfter",
        7,
        7,
        ULIST,
        "Before\n* Bulleted list item\nAfter",
        None,
    ),
    "splitlines option: single partial line selection, insert new list item": (
        "BeforeMy List ItemAfter",
        6,
        18,
        ULIST,
        "Before\n* My List Item\nAfter",
        None,
    ),
    "splitlines option: multiple lines": (
        "Before\nFirst\nSecond\nThird\nAfter",
        7,
        25,
        ULIST,
        "Before\n* First\n* Second\n* Third\nAfter",
        None,
    ),
}


@pytest.mark.parametrize("case", ENCAPSULATE_CASES)
def test_encapsulate_text(case: str) -> None:
    text, start, end, options, after, selected = ENCAPSULATE_CASES[case]
    edit = encapsulate_selection(text, start, end, options)
    new = edit.apply(text)
    assert new == after
    if selected is not None:
        assert new[edit.sel_start : edit.sel_end] == selected


def test_spaces_stay_outside_the_markup() -> None:
    edit = encapsulate_selection("a  word b", 1, 7, BOLD)
    assert edit.apply("a  word b") == "a  '''word''' b"


def test_selection_start_option_overrides_the_selection() -> None:
    options = EncapsulateOptions(pre="[[", post="]]", selection_start=0, selection_end=3)
    assert encapsulate_selection("foo bar", 5, 5, options).apply("foo bar") == "[[foo]] bar"


def test_replace_without_selecting_peri() -> None:
    action = TextAction("replace", EncapsulateOptions(peri="–", select_peri=False))
    edit = do_action("a b", 1, 2, action)
    assert edit.apply("a b") == "a–b"
    assert edit.sel_start == edit.sel_end == 2


def test_malayalam_and_astral_text_are_not_split() -> None:
    text = "𠀀 മലയാളം"
    start = text.index("മ")
    edit = encapsulate_selection(text, start, len(text), BOLD)
    assert edit.apply(text) == "𠀀 '''മലയാളം'''"


@pytest.fixture(scope="module")
def toolbar() -> Toolbar:
    return build_toolbar(Messages("en"))


def _tool_action(toolbar: Toolbar, tool_id: str) -> TextAction:
    tool = next(t for t in toolbar.tools() if t.id == tool_id)
    assert isinstance(tool.action, TextAction)
    return tool.action


def _heading_action(toolbar: Toolbar, level: int) -> TextAction:
    heading = next(t for t in toolbar.tools() if t.id == "heading")
    action = heading.options[level - 2].action
    assert isinstance(action, TextAction)
    return action


def test_heading_menu_changes_an_existing_heading_level(toolbar: Toolbar) -> None:
    text = "Intro\n== History ==\nText"
    start = text.index("==")
    end = text.index("\nText")
    edit = do_action(text, start, end, _heading_action(toolbar, 3))
    assert edit.apply(text) == "Intro\n=== History ===\nText"


def test_heading_menu_wraps_plain_text(toolbar: Toolbar) -> None:
    text = "Intro\nHistory\nText"
    edit = do_action(text, 6, 13, _heading_action(toolbar, 4))
    assert edit.apply(text) == "Intro\n==== History ====\nText"


def test_heading_menu_inserts_an_example(toolbar: Toolbar) -> None:
    edit = do_action("abc", 3, 3, _heading_action(toolbar, 2))
    new = edit.apply("abc")
    assert new == "abc\n== Heading text ==\n"
    assert new[edit.sel_start : edit.sel_end] == "Heading text"


def test_bulleted_list_converts_numbered_lines(toolbar: Toolbar) -> None:
    text = "# one\n#two\nthree"
    edit = do_action(text, 0, len(text), _tool_action(toolbar, "ulist"))
    assert edit.apply(text) == "#* one\n#* two\n* three\n"


def test_bold_example_is_selected(toolbar: Toolbar) -> None:
    edit = do_action("", 0, 0, _tool_action(toolbar, "bold"))
    new = edit.apply("")
    assert new == "'''Bold text'''"
    assert new[edit.sel_start : edit.sel_end] == "Bold text"
