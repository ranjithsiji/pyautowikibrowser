"""The edit box menu commands (AWB Main.cs mnuTextBox handlers, Background.BypassRedirectsFunc)."""

from collections.abc import Mapping
from typing import Any

from pyawb.api.pageinfo import redirect_targets
from pyawb.core.parsers.parsers import Parsers
from pyawb.editor import editcommands as ec
from tests.api.fakes import FakeTransport


def run(edit: Any, text: str) -> str:
    return edit.apply(text)


def test_replace_selection_and_tags() -> None:
    text = "abc def"
    e = ec.replace_selection(text, 4, 7, ec.CLEAR)
    assert run(e, text) == "abc {{subst:clear}}" and e.sel_start == e.sel_end == 19
    e = ec.prepend_tag(text, ec.WIKIFY)
    assert run(e, text) == (
        "{{Wikify|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\n\nabc def"
    )
    assert ec.speedy_delete_tag("  A7 ") == "{{db|A7}}"


def test_comment_selected() -> None:
    e = ec.comment_selected("x y z", 2, 3)
    assert run(e, "x y z") == "x <!-- y --> z"
    e = ec.comment_selected("ab", 1, 1)  # nothing selected: a sample to type over
    assert run(e, "ab") == "a<!-- Comment -->b"
    assert "a<!-- Comment -->b"[e.sel_start : e.sel_end] == "Comment"


def test_convert_list() -> None:
    text = "<ul>\n<li>one</li>\n<li>two</li>\n</ul>"
    e = ec.convert_list(text, 0, len(text), "*")
    assert run(e, text) == "\n* one\n* two\n"  # AWB keeps the <ul> line's line break
    text = "1. one\n2. two"
    assert run(ec.convert_list(text, 0, len(text), "#"), text) == "# one\n# two"


def test_unicodify_and_whitespace() -> None:
    text = "caf&eacute; <!-- &eacute; -->"
    e = ec.unicodify_selected(text, 0, 11, Parsers())
    assert run(e, text) == "café <!-- &eacute; -->"
    text = "a\n\n\n\nb  <!--  x\n\n\n\n-->"
    assert run(ec.fix_all_excess_whitespace(text), text) == "a\n\nb <!--  x\n\n\n\n-->"


def test_human_name_tags() -> None:
    text = "'''John Smith''' was a man."
    e = ec.human_name_defaultsort(text, 0, 0, "John Smith")
    assert run(e, text).startswith("{{DEFAULTSORT:Smith, John}}")
    e = ec.human_name_disambig(text, 0, 0, "John Smith")
    assert run(e, text).startswith("{{Hndis|name=Smith, John}}")


def test_birth_death_categories() -> None:
    text = "'''John Smith''' (1901 – 1975) [[File:X 1850.jpg|1850]] {{cn|date=May 2020}}"
    assert ec.birth_death_categories(text, "John Smith") == (
        "[[Category:1901 births|Smith, John]]\n[[Category:1975 deaths|Smith, John]]"
    )
    # a second year less than 20 years later is not a death
    assert ec.birth_death_categories("born 1950, moved 1960", "Jane Doe") == (
        "[[Category:1950 births|Doe, Jane]]"
    )
    assert ec.birth_death_categories("no years", "X") == ""


def test_insert_birth_death_categories_adds_defaultsort() -> None:
    text = "'''John Smith''' (1901 – 1975) was a man.\n"
    e = ec.insert_birth_death_categories(text, len(text), len(text), "John Smith", Parsers(), False)
    assert e is not None
    new = run(e, text)
    assert "{{DEFAULTSORT:Smith, John}}" in new
    assert "[[Category:1901 births]]" in new and "[[Category:1975 deaths]]" in new
    assert ec.insert_birth_death_categories("none", 0, 0, "X", Parsers(), False) is None
    # "Restrict DEFAULTSORT change/addition" keeps the category sort keys
    e = ec.insert_birth_death_categories(text, len(text), len(text), "John Smith", Parsers(), True)
    assert e is not None and "DEFAULTSORT" not in run(e, text)


def test_add_category_removes_uncategorized() -> None:
    text = "{{Uncategorized|date=May 2020}}\nText"
    new = run(ec.add_category(text, "Category:Foo"), text)
    assert new == "\nText\n\n[[Category:Foo]]"


def test_bypass_redirects() -> None:
    text = "[[Old]] and [[old|text]] and [[:Old]] and [[Kept]]"
    assert ec.link_targets(text) == ["Old", "Kept"]
    assert ec.bypass_redirects(text, {"Old": "New#Part"}) == (
        "[[New#Part|Old]] and [[New#Part|text]] and [[New#Part|Old]] and [[Kept]]"
    )


def test_redirect_targets_query() -> None:
    def handler(p: Mapping[str, str]) -> Mapping[str, Any]:
        assert p["redirects"] == "1"
        return {
            "query": {
                "normalized": [{"from": "old", "to": "Old"}],
                "redirects": [{"from": "Old", "to": "New", "tofragment": "Part"}],
            }
        }

    assert redirect_targets(FakeTransport(handler), ["old", "Kept"]) == {"old": "New#Part"}


def test_go_to_line_and_urls() -> None:
    text = "a\nbb\nccc"
    assert [ec.line_start(text, n) for n in (1, 2, 3, 9)] == [0, 2, 5, 5]
    assert ec.is_url(" https://example.org/x ")
    assert ec.is_url("http://")  # AWB opens anything starting with http as a link
    assert not ec.is_url("Main Page")


def test_undo_line_changes() -> None:
    original = "one\ntwo\nthree\nfour"
    current = "one\nTWO\nthree\nfour\nfive"
    assert ec.undo_line_changes(original, current, 2) == "one\ntwo\nthree\nfour\nfive"
    assert ec.undo_line_changes(original, current, 5) == "one\nTWO\nthree\nfour"
    assert ec.undo_line_changes(original, current, 1) is None
    # adjacent changed lines: only the clicked one
    assert ec.undo_line_changes("a\nb\nc", "A\nB\nc", 2) == "A\nb\nc"
    # a deleted line comes back where it was
    assert ec.undo_line_changes(original, "one\nthree\nfour", 2) == original


def test_find_all() -> None:
    text = "Cat cat CAT\nFoo"
    assert ec.find_all(text, "cat", False, False, "X") == [(0, 3), (4, 3), (8, 3)]
    assert ec.find_all(text, "cat", False, True, "X") == [(4, 3)]
    assert ec.find_all(text, "T\\nF", False, True, "X") == [(10, 3)]  # \n is a newline
    assert ec.find_all(text, r"c\w+", True, False, "X") == [(0, 3), (4, 3), (8, 3)]
    assert ec.find_all("Foo is Foo", "%%title%%", False, True, "Foo") == [(0, 3), (7, 3)]
    assert ec.find_all(text, "", False, False, "X") == []


def test_next_error_wraps() -> None:
    errors = [(5, 2), (20, 3)]
    assert ec.next_error(errors, 0) == (5, 2)
    assert ec.next_error(errors, 5) == (20, 3)
    assert ec.next_error(errors, 25) == (5, 2)
    assert ec.next_error([], 0) is None


def test_duplicate_link_pattern() -> None:
    from pyawb.core.rx import DotNetRegex

    rx = DotNetRegex(ec.duplicate_link_pattern("Foo bar (3)"))
    assert rx.is_match("[[foo bar]]") and rx.is_match("[[Foo bar|x]]")
    assert not rx.is_match("[[Foo Bar]]")


def test_delink_selection() -> None:
    assert ec.delink_selection("[[Foo]]") == "Foo"
    assert ec.delink_selection("[[Foo|bar]]") == "bar"
    # the pipe trick shows the title without namespace and bracketed part (AWB was off here)
    assert ec.delink_selection("[[Help:Foo (bar)|]]") == "Foo"
    assert ec.delink_selection("[[Foo|]]") == "Foo"
    assert ec.delink_selection("Foo") is None
