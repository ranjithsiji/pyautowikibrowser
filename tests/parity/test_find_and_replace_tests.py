"""Port of the FindAndReplaceTests fixture in AWB UnitTests/MiscellaneousTests.cs: find and replace
rules (awb_x.rules.findreplace).

Converted mechanically from the C# by tools/porting/nunit2py.py, then edited by hand: AWB's summary
properties start as null, AWB-X's as "" (asserted as == "").
"""

# pyright: reportUnusedVariable=false

from awb_x.core.dotnet_regex import DotNetOptions as O
from awb_x.rules.findreplace import FindAndReplace as FindandReplace
from awb_x.rules.findreplace import Replacement, arrow


def test_find_and_replace() -> None:
    r = Replacement(r"foo", r"bar", True, True, True, True, O.NONE, r"")
    fr = FindandReplace()
    changemade = False
    assert ((_t := fr.perform_find_and_replace(r, r"the was", r"Test")), (changemade := _t[1]))[0][
        0
    ] == r"the was"
    assert not (changemade)
    assert fr.replaced_summary == "", r"No match: no edit summary"
    assert ((_t := fr.perform_find_and_replace(r, r"the foo was", r"Test")), (changemade := _t[1]))[
        0
    ][0] == r"the bar was"
    assert changemade
    assert fr.replaced_summary == r"foo" + arrow() + r"bar", r"One match: a to b"
    fr = FindandReplace()
    changemade = False
    assert (
        (_t := fr.perform_find_and_replace(r, r"the foo was or foo was", r"Test")),
        (changemade := _t[1]),
    )[0][0] == r"the bar was or bar was"
    assert fr.replaced_summary == r"foo" + arrow() + r"bar (2)", r"Match count shown"
    fr = FindandReplace()
    changemade = False
    assert (
        (_t := fr.perform_find_and_replace(r, r"the foo was or foo was foo", r"Test")),
        (changemade := _t[1]),
    )[0][0] == r"the bar was or bar was bar"
    assert fr.replaced_summary == r"foo" + arrow() + r"bar (3)", r"Match count shown, 3"
    r = Replacement(r"foot?", r"bar", True, True, True, True, O.NONE, r"")
    fr = FindandReplace()
    changemade = False
    assert (
        (_t := fr.perform_find_and_replace(r, r"the foot was or foo was", r"Test")),
        (changemade := _t[1]),
    )[0][0] == r"the bar was or bar was"
    assert changemade
    assert fr.replaced_summary == r"foot" + arrow() + r"bar (2)", (
        r"Different matches, match text of first used"
    )
    r = Replacement(r"fooo?", r"foo", True, True, True, True, O.NONE, r"")
    fr = FindandReplace()
    changemade = False
    assert (
        (_t := fr.perform_find_and_replace(r, r"the foo was a fooo it", r"Test")),
        (changemade := _t[1]),
    )[0][0] == r"the foo was a foo it"
    assert changemade
    assert fr.replaced_summary == r"fooo" + arrow() + r"foo", r"No-change match ignored"
    fr = FindandReplace()
    changemade = False
    assert ((_t := fr.perform_find_and_replace(r, r"the foo was", r"Test")), (changemade := _t[1]))[
        0
    ][0] == r"the foo was"
    assert not (changemade), r"only match is no-change on replace, so no change made"
    assert fr.replaced_summary == "", r"Only match is No-change match, no edit summary"


def test_find_and_replace_new_lines() -> None:
    r = Replacement("foo\n", r"bar ", True, True, True, True, O.NONE, r"")
    fr = FindandReplace()
    changemade = False
    assert ((_t := fr.perform_find_and_replace(r, "the foo\nwas", r"Test")), (changemade := _t[1]))[
        0
    ][0] == r"the bar was"
    assert changemade
    r = Replacement("foo\n", r"bar ", False, True, True, True, O.NONE, r"")
    assert ((_t := fr.perform_find_and_replace(r, "the foo\nwas", r"Test")), (changemade := _t[1]))[
        0
    ][0] == r"the bar was"
    assert changemade


def test_find_and_replace_remove() -> None:
    r = Replacement(r"foo", r"", True, True, True, True, O.NONE, r"")
    fr = FindandReplace()
    changemade = False
    assert ((_t := fr.perform_find_and_replace(r, r"the was", r"Test")), (changemade := _t[1]))[0][
        0
    ] == r"the was"
    assert not (changemade)
    assert fr.replaced_summary == "", r"No match: no edit summary"
    assert fr.removed_summary == "", r"No match: no edit summary"
    assert ((_t := fr.perform_find_and_replace(r, r"the foo was", r"Test")), (changemade := _t[1]))[
        0
    ][0] == r"the  was"
    assert changemade
    assert fr.removed_summary == r"foo", r"One match: removed a"
    fr = FindandReplace()
    changemade = False
    assert (
        (_t := fr.perform_find_and_replace(r, r"the foo was or foo was", r"Test")),
        (changemade := _t[1]),
    )[0][0] == r"the  was or  was"
    assert fr.removed_summary == r"foo (2)", r"Match count shown"
    r = Replacement(r"foot?", r"", True, True, True, True, O.NONE, r"")
    fr = FindandReplace()
    changemade = False
    assert (
        (_t := fr.perform_find_and_replace(r, r"the foot was or foo was", r"Test")),
        (changemade := _t[1]),
    )[0][0] == r"the  was or  was"
    assert changemade
    assert fr.removed_summary == r"foot (2)", r"Different matches, match text of first used"


def test_find_and_replace_properties() -> None:
    r = Replacement(r"foo", r"bar", True, True, True, True, O.NONE, r"")
    r2 = Replacement(r"foo2", r"bar2", True, True, True, False, O.NONE, r"")
    r2Disabled = Replacement(r"foo2", r"bar2", True, False, True, False, O.NONE, r"")
    fr = FindandReplace()
    fr.add_new(r)
    assert fr.has_after_processing_replacements
    assert fr.has_processing_replacements(True)
    assert not (fr.has_processing_replacements(False))
    fr.add_new(r2)
    assert fr.has_after_processing_replacements
    assert fr.has_processing_replacements(True)
    assert fr.has_processing_replacements(False)
    fr.clear()
    fr.add_new(r2)
    assert not (fr.has_after_processing_replacements)
    assert not (fr.has_processing_replacements(True))
    assert fr.has_processing_replacements(False)
    fr.clear()
    fr.add_new(r2Disabled)
    assert not (fr.has_after_processing_replacements)
    assert not (fr.has_processing_replacements(True))
    assert not (fr.has_processing_replacements(False))
    fr.clear()
    l = []
    l.append(r)
    l.append(r2)
    fr.add_new(l)
    assert fr.has_replacements
    assert l == fr.get_list()
