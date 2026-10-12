"""Port of AWB UnitTests/SummaryTests.cs: edit summaries.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from awb_l.core import genfixes, namespace, tools
from awb_l.core import wikiregexes as W
from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.parsers.parsers import DateLocale
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_project, set_site, utc_month_year
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser
from awb_l.core import summary as Summary  # noqa: E402


def test_is_correct() -> None:
    # Hand-ported (the for loop building the string was not converted).
    # too long
    assert not Summary.is_correct("x" * 256)

    # no wikilinks
    assert Summary.is_correct("")
    assert Summary.is_correct("test")
    assert Summary.is_correct("[")
    assert Summary.is_correct("]")
    assert Summary.is_correct("[test]")
    assert Summary.is_correct("[test]]")
    assert Summary.is_correct("[[]]")

    # correctly (sort of..) terminated wikilinks
    assert Summary.is_correct("[[test]]")
    assert Summary.is_correct("[[test]] [[foo]]")

    # broken wikilinks, should be found to be invalid
    assert not Summary.is_correct("[[")
    assert not Summary.is_correct("[[[")
    assert not Summary.is_correct("[[test]")
    assert not Summary.is_correct("[[test]] [[")
    assert not Summary.is_correct("[[123456789 123456789 123456789 1[[WP:AWB]]")
    assert not Summary.is_correct("[[foo[[]]]")


def test_trim() -> None:
    S = W.for_site(EN)
    assert Summary.trim(r"test") == r"test"
    bug1 = r"replaced category 'Actual event ballads' → 'Songs based on actual events' per [[Wikipedia:Categories for discussion/Log/2009 November 6|CfD 2009 Nov 6]]"
    waffle = r"some waffle here to make the edit summary too long"
    assert Summary.trim(bug1) == bug1
    assert Summary.trim(waffle + bug1) == waffle + bug1
    assert (
        Summary.trim(waffle + waffle + bug1)
        == waffle
        + waffle
        + r"replaced category 'Actual event ballads' → 'Songs based on actual events' per..."
    )


def test_modified_section() -> None:
    S = W.for_site(EN)
    assert len(Summary.modified_section(r"", r"")) == 0, r"No change to text"
    assert len(Summary.modified_section(r"foo", r"foo")) == 0, r"No change to text 2"
    assert Summary.modified_section(r"foo", r"bar") == r"top", (
        r"Zeroth section change, no other sections"
    )
    assert Summary.modified_section("foo\r\n==sec==\r\na", "bar\r\n==sec==\r\na") == r"top", (
        r"Zeroth section change"
    )
    assert Summary.modified_section("==foo==\r\n123", "==foo==\r\ntest") == r"foo", (
        r"Section 1 change, no zeroth section"
    )
    assert Summary.modified_section("rawr\r\n==foo==\r\n123", "rawr\r\n==foo==\r\ntest") == r"foo"
    assert Summary.modified_section("==foo==\r\n123", "== foo ==\r\ntest") == r"foo"
    assert Summary.modified_section("==foo==\r\n123", "==bar==\r\ntest") == r"bar"
    assert len(Summary.modified_section("==foo==\r\nbar", "test\r\n==foo==\r\nbar")) == 0
