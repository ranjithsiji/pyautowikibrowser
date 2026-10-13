"""Port of AWB UnitTests/MiscellaneousTests.cs, class NamespaceTests: the parity suite for pyawb.core.namespace.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: E501, F841, F401
# pyright: reportUnusedVariable=false

import pytest

from pyawb.core import namespace, tools
from pyawb.core import wikiregexes as W
from pyawb.core.dotnet_regex import DotNetOptions as O
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import Namespace, SiteConfig
from tests.parity import regex_assert
from tests.parity.helpers import EN, set_lang, set_site
from tests.parity.regex_assert import check_match, check_matches


def test_determine() -> None:
    S = W.for_site(EN)
    assert namespace.determine(r"test") == 0
    assert namespace.determine(r" test ") == 0
    assert namespace.determine(r":test") == 0
    assert namespace.determine(r"test:test") == 0
    assert namespace.determine(r"My Project:Foo") == 0
    assert namespace.determine(r"Magic: The Gathering") == 0
    assert namespace.determine(r"User:") == Namespace.USER
    assert namespace.determine(r"Talk:foo") == Namespace.TALK
    assert namespace.determine(r"Talk%3Afoo") == Namespace.TALK, r"Handles URL encoded colon"
    assert namespace.determine(r"User talk:bar") == Namespace.USER_TALK
    assert namespace.determine(r"File:foo") == Namespace.FILE
    assert namespace.determine(r"Image:foo") == Namespace.FILE
    assert namespace.determine(r"Wikipedia:Foo") == Namespace.PROJECT
    assert namespace.determine(r"Project:Foo") == Namespace.PROJECT
    assert namespace.determine(r"Talk:ʿAyn") == Namespace.TALK, (
        r"handles pages with spacing modifier Unicode characters at start of name"
    )
    assert namespace.determine(r"Module:foo") == Namespace.MODULE
    assert namespace.determine(r"Module talk:foo") == Namespace.MODULE_TALK
    assert namespace.determine(r"MOS:foo") == Namespace.MOS
    assert namespace.determine(r"MOS talk:foo") == Namespace.MOS_TALK
    assert namespace.determine(r"TimedText:foo") == Namespace.TIMEDTEXT
    assert namespace.determine(r"TimedText talk:foo") == Namespace.TIMEDTEXT_TALK
    assert namespace.determine(r"Draft:foo") == Namespace.DRAFT
    assert namespace.determine(r"Draft talk:foo") == Namespace.DRAFT_TALK


def test_determine_deviations() -> None:
    S = W.for_site(EN)
    assert namespace.determine(r"File : foo") == Namespace.FILE
    assert namespace.determine(r"File :foo") == Namespace.FILE
    assert namespace.determine(r"File: foo") == Namespace.FILE
    assert namespace.determine(r"File :  foo") == Namespace.FILE
    assert namespace.determine(r"user:foo") == Namespace.USER
    assert namespace.determine(r"user_talk:foo") == Namespace.USER_TALK
    assert namespace.determine(r"user%20talk:foo") == Namespace.USER_TALK


def test_other_languages() -> None:
    from pyawb.core.site import current_site

    set_lang("fr")
    set_site(namespaces={**current_site().namespaces, 1: "Discussion:"})
    assert namespace.determine(r"Discussion:foo") == Namespace.TALK


def test_is_talk() -> None:
    S = W.for_site(EN)
    assert namespace.is_talk(Namespace.TALK)
    assert namespace.is_talk(Namespace.USER_TALK)
    assert not (namespace.is_talk(Namespace.USER))
    assert not (namespace.is_talk(Namespace.PROJECT))
    assert not (namespace.is_talk(Namespace.SPECIAL))
    assert not (namespace.is_talk(Namespace.MEDIA))
    assert namespace.is_talk(r"Talk:Test")
    assert namespace.is_talk(r"User talk:Test")
    assert not (namespace.is_talk(r"Test"))
    assert not (namespace.is_talk(r"User:Test"))


def test_is_main_space() -> None:
    S = W.for_site(EN)
    assert namespace.is_main_space(Namespace.ARTICLE)
    assert not (namespace.is_main_space(Namespace.TALK))
    assert namespace.is_main_space(r"Test")
    assert not (namespace.is_main_space(r"User:"))
    assert not (namespace.is_main_space(r"Talk:Test"))
    assert not (namespace.is_main_space(r"User:Test"))
    assert not (namespace.is_main_space(r"User talk:Test"))
    assert not (namespace.is_main_space(r"File:Test"))
    assert not (namespace.is_main_space(r"Image:Test"))


def test_is_important() -> None:
    S = W.for_site(EN)
    assert namespace.is_important(r"Test")
    assert namespace.is_important(r"File:Test.jpg")
    assert namespace.is_important(r"Template:Test")
    assert namespace.is_important(r"Category:Test")
    assert not (namespace.is_important(r"Talk:Test"))
    assert not (namespace.is_important(r"File talk:Test"))
    assert not (namespace.is_important(r"Template talk:Test"))
    assert not (namespace.is_important(r"Category talk:Test"))
    assert not (namespace.is_important(r"User:Test"))


def test_is_user_space() -> None:
    S = W.for_site(EN)
    assert namespace.is_user_space(r"User:Test")
    assert namespace.is_user_space(r"User talk:Test")
    assert not (namespace.is_user_space(r"User"))
    assert not (namespace.is_user_space(r"Test"))
    assert not (namespace.is_user_space(r"Project:User"))


def test_is_user_talk() -> None:
    S = W.for_site(EN)
    assert namespace.is_user_talk(r"User talk:Test")
    assert not (namespace.is_user_talk(r"User:Test"))
    assert not (namespace.is_user_talk(r"Test"))
    assert not (namespace.is_user_talk(r"Project:User"))


def test_is_user_page() -> None:
    S = W.for_site(EN)
    assert namespace.is_user_page(r"User:Test")
    assert not (namespace.is_user_page(r"User talk:Test"))
    assert not (namespace.is_user_page(r"Test"))
    assert not (namespace.is_user_page(r"Project:User"))


def test_is_special() -> None:
    S = W.for_site(EN)
    assert namespace.is_special(Namespace.MEDIA)
    assert namespace.is_special(Namespace.SPECIAL)
    assert not (namespace.is_special(Namespace.ARTICLE))
    assert not (namespace.is_special(Namespace.TEMPLATE_TALK))


def test_normalize_namespace() -> None:
    S = W.for_site(EN)
    assert namespace.normalize(r"User:", 2) == r"User:"
    assert namespace.normalize(r"user :", 2) == r"User:"
    assert namespace.normalize(r"User_talk:", 3) == r"User talk:"
    assert namespace.normalize(r"image:", 6) == r"Image:"
    assert namespace.normalize(r"file:", 6) == r"File:"
    assert namespace.normalize(r"image talk:", 7) == r"Image talk:"
    assert namespace.normalize(r"user :", 7) == r"user:", (
        r"only changes colon for incorrect namespace number"
    )
    assert namespace.normalize(r"user:", 7) == r"user:", (
        r"only changes colon for incorrect namespace number"
    )


def test_verify() -> None:
    from pyawb.core.site import CANONICAL_NAMESPACES

    assert namespace.verify_namespaces(CANONICAL_NAMESPACES)
    ns = dict(CANONICAL_NAMESPACES)
    ns[0] = ""
    assert not namespace.verify_namespaces(ns)
    del ns[0]
    ns[1] = "Talk"
    assert not namespace.verify_namespaces(ns)
    del ns[1]
    assert not namespace.verify_namespaces(ns)
