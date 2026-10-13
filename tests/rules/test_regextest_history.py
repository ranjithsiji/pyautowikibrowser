"""The regex tester's work and Replace Special's undo history."""

from pyawb.rules import regextest
from pyawb.rules.replacespecial import Rule, RuleHistory


def test_find_and_describe() -> None:
    t = regextest.find(r"(\w)(?<n>\d)", regextest.options_from(), "a1 b2")
    assert [m.value for m in t.matches] == ["a1", "b2"] and t.groups == 2
    text = regextest.describe(t)
    assert "2 match(es)" in text and "$1 = 'a'" in text and "$2 = '1'" in text


def test_replace_and_options() -> None:
    t = regextest.replace("CAT", "$0s", regextest.options_from(ignore_case=True), "cat Cat")
    assert t.result == "cats Cats" and len(t.matches) == 2
    t = regextest.find("^b", regextest.options_from(multiline=True), "a\nb")
    assert len(t.matches) == 1


def test_errors_are_reported() -> None:
    t = regextest.find("(", regextest.options_from(), "x")
    assert t.error and regextest.describe(t) == t.error
    assert regextest.describe(regextest.find("z", regextest.options_from(), "x")) == "No matches"


def test_rule_history() -> None:
    h = RuleHistory()
    first = [Rule(name="A")]
    assert not h.can_undo
    h.save(first)
    second = [Rule(name="A"), Rule(name="B")]
    back = h.undo(second)
    assert [r.name for r in back] == ["A"] and h.can_redo
    again = h.redo(back)
    assert [r.name for r in again] == ["A", "B"]
    first[0].name = "changed"  # snapshots are copies
    assert [r.name for r in h.undo(again)] == ["A"]
