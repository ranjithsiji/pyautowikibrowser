"""Port of AWB UnitTests/RetfTests.cs: typo fixing with RegExTypoFix (awb_x.rules.typos).

Ported by hand (the C# fixture's helper methods become a small class). Every AWB assertion is kept.
"""

import pytest

from awb_x.rules.typos import RegExTypoFix


class Retf:
    """The C# fixture: a typo list filled by each test, and a RegExTypoFix built on first use."""

    def __init__(self) -> None:
        self.typos: dict[str, str] = {}
        self.retf: RegExTypoFix | None = None
        self.summary = ""

    def _get(self) -> RegExTypoFix:
        if self.retf is None:
            if not self.typos:
                raise AssertionError("You forgot to provide a list of typos!")
            self.retf = RegExTypoFix(self.typos)
        return self.retf

    def fix_typos(self, article_text: str, article_title: str = "Test") -> str:
        text, _no_change, self.summary = self._get().perform_typo_fixes(article_text, article_title)
        return text

    def detect_typo(self, article_text: str, article_title: str = "Test") -> bool:
        return self._get().detect_typo(article_text, article_title)

    def assert_fix(self, expected: str, article_text: str, article_title: str = "Test") -> None:
        assert self.fix_typos(article_text, article_title) == expected

    def assert_no_fix(self, article_text: str, article_title: str = "Test") -> None:
        assert self.fix_typos(article_text, article_title) == article_text


@pytest.fixture
def t() -> Retf:
    return Retf()


def test_simple_typos(t: Retf) -> None:
    t.typos["foo"] = "bar"

    t.assert_no_fix("")
    t.assert_no_fix("test")

    t.assert_fix("the bars are cute", t.fix_typos("the foos are cute"))
    t.assert_fix("the bars are cute bars", t.fix_typos("the foos are cute foos"))


def test_no_typos(t: Retf) -> None:
    t.typos["foo"] = "bar"
    t.assert_no_fix("spellfixno foos are")


def test_detect_typo(t: Retf) -> None:
    t.typos["foo"] = "bar"
    assert t.detect_typo("The foo was")
    assert t.detect_typo("The foo was ")
    assert not t.detect_typo("The x was")
    assert not t.detect_typo("The foo {{sic}} was")


def test_case_sensitivity(t: Retf) -> None:
    t.typos["foo"] = "bar"
    t.typos["[Bb]oz"] = "quux"
    t.typos["(?i:fubar)"] = "fur"

    # fixes matching case
    t.assert_fix("bars", "foos")
    # ...but not mismatching
    t.assert_no_fix("Foobar")

    # should handle case-insensitive regex constructs properly
    t.assert_fix("quux", "boz")
    t.assert_fix("quux", "Boz")
    t.assert_no_fix("BOZ")
    t.assert_fix("furbag", "FuBaRbag")


def test_dont_change_urls(t: Retf) -> None:
    t.typos["foo"] = "bar"
    t.assert_no_fix("http://foo.com/asdfasdf/asdf.htm")
    t.assert_no_fix("[http://foo.com/asdfasdf/asdf.htm Foo's best]")
    t.assert_no_fix("http://foo.com/asdfasdf/foo.htm")


def test_backreferences(t: Retf) -> None:
    t.typos["(taht)"] = "that"
    t.typos[r"\b(a|the)\b\s+\1\b"] = "$1"

    # all rules must function separately
    t.assert_fix("that", "taht")
    t.assert_fix("the", "the the")
    t.assert_no_fix("a the")  # just in case

    # matches from other rules must not pollute backreferences
    t.assert_fix("that the", "taht the the")


def test_summary_tests(t: Retf) -> None:
    t.typos["f[oO0]{2}"] = "foo"
    t.typos["(?<=ten )bar"] = "BAR"

    t.assert_fix("foo foo", "foo fO0")
    assert "foo → foo" not in t.summary
    assert "2" not in t.summary

    t.assert_fix("ten BAR", "ten bar")
    assert "bar → BAR" in t.summary, (
        "regex with lookbehind such that regex does not match its own match value still "
        "generates edit summary based on match value"
    )
    assert "ten" not in t.summary, (
        "for regex with lookbehind, edit summary based on match value without groups outside "
        "match value"
    )


def test_fix_link_faces(t: Retf) -> None:
    t.typos["foo"] = "bar"

    t.assert_no_fix("[[foo]]")
    t.assert_fix("[[Fred|bar]]", "[[Fred|foo]]")


def test_dont_change_when_wikilinked(t: Retf) -> None:
    t.typos["foo"] = "bar"

    t.assert_no_fix("now [[foo]] was foo here")  # No change: typo matches wikilink
    t.assert_no_fix("now [[foo|bo]] was foo here")  # No change: typo matches piped wikilink
    t.assert_no_fix("now [[Mr foo oft]] was foo here")  # No change: typo matches within wikilink
    # No change: typo matches within wikilink
    t.assert_no_fix("now [[Mr foo oft]] was foo here [[Image:foo.png]] a")

    # Change: typo matches image name which doesn't matter
    t.assert_fix("now [[Image:foo.png]] was bar here", "now [[Image:foo.png]] was foo here")
    # Change: typo matches interwiki name which doesn't matter
    t.assert_fix("now [[sv:foo]] was bar here", "now [[sv:foo]] was foo here")
    # Change: typo matches category name which doesn't matter
    t.assert_fix("now [[Category:A foo]] was bar here", "now [[Category:A foo]] was foo here")

    t.assert_fix("now bar [[Foo]] was", "now foo [[Foo]] was")


def test_all_three_groups(t: Retf) -> None:
    t.typos[r"\booze\b"] = "booze!"
    t.typos[r"foo(\w*)\b"] = "bar$1"
    t.typos[r"\b(a|the)\b\s+\1\b"] = "$1"

    t.assert_fix("barwards viva the booze!", "foowards viva the the ooze")


def test_dont_fix_certain_stuff(t: Retf) -> None:
    t.typos["(T|t)eh"] = "the"

    t.assert_no_fix(
        "{{teh}} http://tehcrappe.org/TehCrappe [[teh]] [http://tehcrappe.org/TehCrappe]"
    )


def test_dont_change_title(t: Retf) -> None:
    t.typos["teh"] = "the"
    t.typos["foo"] = "bar"

    t.assert_fix("teh bar", "teh foo", "teh")
    t.assert_fix("teh bar", "teh foo", "teh crap")
    t.assert_no_fix("teh home", "teh")


# AWB-X additions: behaviour AWB had through message boxes, and the per-rule timeout


def test_bad_rule_loads_nothing() -> None:
    retf = RegExTypoFix({"foo": "bar", "(unclosed": "x"})
    assert not retf.typos_loaded
    assert retf.typo_count == 0
    assert retf.error is not None and "(unclosed" in retf.error


def test_typo_summary_tag() -> None:
    retf = RegExTypoFix({"teh": "the"})
    text, no_change, summary = retf.perform_typo_fixes("teh cat", "Test")
    assert (text, no_change) == ("the cat", False)
    assert summary == "typos fixed: teh → the"
