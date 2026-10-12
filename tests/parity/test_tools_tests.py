"""Port of AWB UnitTests/ToolsTests.cs: the parity suite for awb_l.core.tools.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: E501, F841, F401
# pyright: reportUnusedVariable=false

import pytest

from awb_l.core import namespace, tools
from awb_l.core import wikiregexes as W
from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.parsers.parsers import DateLocale
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig
from tests.parity import regex_assert
from tests.parity.helpers import EN, set_lang, set_site
from tests.parity.regex_assert import check_match, check_matches


def test_is_valid_title() -> None:
    S = W.for_site(EN)
    assert tools.is_valid_title(r"test")
    assert tools.is_valid_title(r"This is a_test")
    assert tools.is_valid_title(r"123")
    assert tools.is_valid_title(r"А & Б сидели на трубе! ة日?")
    assert not (tools.is_valid_title(r"")), r"Empty strings are not supposed to be valid titles"
    assert not (tools.is_valid_title(r" "))
    assert not (tools.is_valid_title(r"%20"))
    assert not (tools.is_valid_title(r"_"))
    assert not (tools.is_valid_title(r"[xxx"))
    assert not (tools.is_valid_title(r"]abc"))
    assert not (tools.is_valid_title(r"{duh!"))
    assert not (tools.is_valid_title(r"}yoyo"))
    assert not (tools.is_valid_title(r"|pwn3d"))
    assert not (tools.is_valid_title(r"<1337"))
    assert not (tools.is_valid_title(r">nooooo"))
    assert not (tools.is_valid_title(r"#yeee-hooo"))
    assert not (tools.is_valid_title(r"[test]#1"))
    assert not (tools.is_valid_title(r"_ _")), r"Titles should be normalised before checking"
    assert tools.is_valid_title(r"http://www.wikipedia.org")
    assert tools.is_valid_title(r"index.php/Viagra")
    assert tools.is_valid_title(r"index.php?title=foobar")
    assert not (tools.is_valid_title(r"::Foo"))
    assert not (tools.is_valid_title(r"User:"))
    assert not (tools.is_valid_title(r"User::"))
    assert not (tools.is_valid_title(r"User::Foo"))
    assert tools.is_valid_title(r":Foo")
    assert tools.is_valid_title(r":User:Foo")


def test_remove_invalid_chars() -> None:
    S = W.for_site(EN)
    assert tools.remove_invalid_chars(r"tesT 123!") == r"tesT 123!"
    assert tools.remove_invalid_chars(r"тест, ёпта") == r"тест, ёпта"
    assert len(tools.remove_invalid_chars(r"")) == 0
    assert tools.remove_invalid_chars(r"{<[test]>}") == r"test"
    assert len(tools.remove_invalid_chars(r"#|#")) == 0
    assert tools.remove_invalid_chars(r"http://www.wikipedia.org") == r"http://www.wikipedia.org"


def test_roman_numbers() -> None:
    S = W.for_site(EN)
    assert tools.is_roman_number(r"XVII")
    assert tools.is_roman_number(r"I")
    assert tools.is_roman_number(r"LI")
    assert tools.is_roman_number(r"LXXXIII")
    assert tools.is_roman_number(r"CCLXXXIII")
    assert not (tools.is_roman_number(r"xvii"))
    assert not (tools.is_roman_number(r"V II"))
    assert not (tools.is_roman_number(r"AAA"))
    assert not (tools.is_roman_number(r"123"))
    assert not (tools.is_roman_number(r" "))
    assert not (tools.is_roman_number(r""))


def test_first_letter_case_insensitive() -> None:
    S = W.for_site(EN)
    assert tools.first_letter_case_insensitive(r"Abc") == r"[Aa]bc"
    assert tools.first_letter_case_insensitive(r"abc") == r"[Aa]bc"
    assert tools.first_letter_case_insensitive(r"aBC") == r"[Aa]BC"
    assert tools.first_letter_case_insensitive(r"abc[de]") == r"[Aa]bc[de]"
    assert tools.first_letter_case_insensitive(r"Σbc") == r"[Σσ]bc"
    assert tools.first_letter_case_insensitive(r"abc ") == r"[Aa]bc"
    assert tools.first_letter_case_insensitive(r" abc") == r" abc"
    assert len(tools.first_letter_case_insensitive(r"")) == 0
    assert tools.first_letter_case_insensitive(r"123") == r"123"
    assert tools.first_letter_case_insensitive(r"-") == r"-"
    assert tools.first_letter_case_insensitive(r"[Aa]bc") == r"[Aa]bc"
    r = DotNetRegex(tools.first_letter_case_insensitive(r"test"))
    assert r.is_match(r"test 123")
    assert r.match(r"Test").value == r"Test"
    assert not (r.is_match(r"tEst"))
    r = DotNetRegex(tools.first_letter_case_insensitive(r"Test"))
    assert r.is_match(r"test 123")
    assert r.match(r"Test").value == r"Test"
    assert not (r.is_match(r"TEst"))
    r = DotNetRegex(tools.first_letter_case_insensitive(r"#test#"))
    assert r.is_match(r"#test#")
    assert not (r.is_match(r"#Test#"))
    assert not (r.is_match(r"test"))


def test_all_case_insensitive() -> None:
    S = W.for_site(EN)
    assert len(tools.all_case_insensitive(r"")) == 0
    assert tools.all_case_insensitive(r"123") == r"123"
    assert tools.all_case_insensitive(r"-") == r"-"
    r = DotNetRegex(tools.all_case_insensitive(r"tEsT"))
    assert r.is_match(r"Test 123")
    assert r.match(r"Test").value == r"Test"
    assert not (r.is_match(r"teZt"))
    r = DotNetRegex(tools.all_case_insensitive(r"[test}"))
    assert r.is_match(r"[test}")
    assert r.is_match(r"[tEsT}")
    assert not (r.is_match(r"test"))


def test_case_insensitive_string_compare() -> None:
    S = W.for_site(EN)
    assert tools.case_insensitive_string_compare(r"test", r"test")
    assert tools.case_insensitive_string_compare(r"test", r"TEST")
    assert tools.case_insensitive_string_compare(r"TEST", r"TEST")
    assert tools.case_insensitive_string_compare(r"testDING", r"TESTding")
    assert tools.case_insensitive_string_compare(r"sCr1pTkIdDy", r"sCr1pTkIdDy")
    assert not (tools.case_insensitive_string_compare(r"test", r"not a test"))
    assert not (tools.case_insensitive_string_compare(r"test ", r" test"))


def test_turn_first_to_upper() -> None:
    S = W.for_site(EN)
    assert len(tools.turn_first_to_upper(r"")) == 0
    assert tools.turn_first_to_upper(r"ASDA") == r"ASDA"
    assert tools.turn_first_to_upper(r"aSDA") == r"ASDA"
    assert tools.turn_first_to_upper(r"test") == r"Test"
    assert tools.turn_first_to_upper(r"%test") == r"%test"
    assert tools.turn_first_to_upper(r"ыыыы") == r"Ыыыы"


def test_turn_first_to_upper_capitalize_first_letter() -> None:
    S = W.for_site(EN)
    S = set_site(capitalize_first_letter=False)
    assert tools.turn_first_to_upper(r"test") == r"test"
    assert tools.turn_first_to_upper(r"Test") == r"Test"
    S = set_site(capitalize_first_letter=True)
    assert tools.turn_first_to_upper(r"test") == r"Test"


def test_first_to_upper_and_remove_hash_on_array() -> None:
    a = ["Abc#f", "efh "]
    b = ["Abc", "Efh"]
    assert tools.first_to_upper_and_remove_hash_on_array(a) == b
    a[1] = "[[Efh]]"
    assert tools.first_to_upper_and_remove_hash_on_array(a) == b
    assert tools.first_to_upper_and_remove_hash_on_array(None) is None


def test_turn_first_to_lower() -> None:
    S = W.for_site(EN)
    assert len(tools.turn_first_to_lower(r"")) == 0
    assert tools.turn_first_to_lower(r"test") == r"test"
    assert tools.turn_first_to_lower(r"%test") == r"%test"
    assert tools.turn_first_to_lower(r"Ыыыы") == r"ыыыы"
    assert tools.turn_first_to_lower(r"TEST") == r"tEST"
    assert tools.turn_first_to_lower(r"Test") == r"test"


def test_title_case_en() -> None:
    S = W.for_site(EN)
    assert tools.title_case_en(r"FOO") == r"Foo"
    assert tools.title_case_en(r"mastermind's interrogation") == r"Mastermind's Interrogation"
    assert tools.title_case_en(r" FOO ") == r"Foo"
    assert tools.title_case_en(r"FOO BAR") == r"Foo Bar"
    assert tools.title_case_en(r"FOO-BAR") == r"Foo-Bar"
    assert tools.title_case_en(r"FOO~BAR") == r"Foo~Bar"
    assert tools.title_case_en(r"foo bar") == r"Foo Bar"
    assert tools.title_case_en(r"foo Bar") == r"Foo Bar"
    assert tools.title_case_en(r"FOO BAR a") == r"FOO BAR A", r"Not all text uppercase"
    assert tools.title_case_en(r"JANE E") == r"Jane E", r"doesn't reformat initials"
    assert tools.title_case_en(r"JANE E.") == r"Jane E.", r"doesn't reformat initials"


def test_word_count() -> None:
    S = W.for_site(EN)
    assert tools.word_count(r"") == 0
    assert tools.word_count(r"    ") == 0
    assert tools.word_count(r".") == 0
    assert tools.word_count(r"1") == 1
    assert tools.word_count(r"  1 ") == 1
    assert tools.word_count(r"foo") == 1
    assert tools.word_count(r"foo-bar") == 2
    assert tools.word_count(r"Превед медвед") == 2
    assert tools.word_count(r"123") == 1
    assert tools.word_count("foo\nbar\r\nboz") == 3
    assert tools.word_count(r"foo.bar") == 2
    assert tools.word_count(r"foo.bar", 10) == 2
    assert tools.word_count(r"foo.bar", 1) == 1
    assert tools.word_count(r"foo<!-- bar boz -->") == 1
    assert tools.word_count(r"foo<!--bar-->quux") == 1
    assert tools.word_count("foo <!--\r\nbar--> quux") == 2
    assert tools.word_count(r"foo {{template| bar boz box}} quux") == 2
    assert tools.word_count("foo{{template\r\n|boz = quux}}bar") == 2
    assert (
        tools.word_count(
            "foo\r\n{|\r\n! test !! test\r\n|-\r\n| test\r\n| test || test\r\n|-\r\n|}bar"
        )
        == 2
    )
    assert (
        tools.word_count(
            "foo\r\n{|\r\n! test !! test\r\n|-\r\n| test\r\n| test || test\r\n|-\r\n|}\r\nbar"
        )
        == 2
    )
    assert (
        tools.word_count(
            "foo\r\n{|\r\n! test !! {{test}}\r\n|-\r\n| test\r\n| test || test\r\n|-\r\n|}\r\nbar"
        )
        == 2
    )
    assert (
        tools.word_count(
            'foo\r\n{| class="wikitable"\r\n! test !! test\r\n|- style="color:red"\r\n| test\r\n| test || test\r\n|-\r\n|}'
        )
        == 1
    )


def test_line_endings() -> None:
    # AWB skips the conversions under Mono; AWB-L always uses "\r\n" internally.
    assert tools.convert_to_local_line_endings("") == ""
    assert tools.convert_to_local_line_endings("foo bar") == "foo bar"
    assert tools.convert_to_local_line_endings("\nfoo\nbar\n") == "\r\nfoo\r\nbar\r\n"
    assert tools.convert_from_local_line_endings("") == ""
    assert tools.convert_from_local_line_endings("foo bar") == "foo bar"
    assert tools.convert_from_local_line_endings("\r\nfoo\r\nbar\r\n") == "\nfoo\nbar\n"


def test_replace_part_of_string() -> None:
    S = W.for_site(EN)
    assert tools.replace_part_of_string(r"abcdef", 3, 1, r"123") == r"abc123ef"
    assert tools.replace_part_of_string(r"abc", 0, 0, r"123") == r"123abc"
    assert tools.replace_part_of_string(r"abc", 3, 0, r"123") == r"abc123"
    assert tools.replace_part_of_string(r"", 0, 0, r"123") == r"123"
    assert tools.replace_part_of_string(r"abc", 1, 0, r"") == r"abc"
    assert tools.replace_part_of_string(r"abc", 0, 3, r"123") == r"123"
    assert tools.replace_part_of_string(r"abc", 0, 1, r"1") == r"1bc"
    assert tools.replace_part_of_string(r"abc", 2, 1, r"3") == r"ab3"


def test_replace_once() -> None:
    # AWB has StringBuilder and ref-string overloads; AWB-L returns (text, replaced).
    def replace_once(text: str, old: str, new: str) -> str:
        return tools.replace_once(text, old, new)[0]

    assert replace_once("", "foo", "bar") == ""
    assert replace_once("test foo!", "foo", "bar") == "test bar!"
    assert replace_once("barbar", "bar", "foo") == "foobar"
    assert tools.replace_once("barbar", "bar", "foo") == ("foobar", True)
    assert tools.replace_once("barbar", "x", "foo") == ("barbar", False)
    y = "Șen"
    assert replace_once(y, y, "z") == "z", "Handle combining diacritic letter"


def test_base_page_name() -> None:
    S = W.for_site(EN)
    assert len(tools.base_page_name(r"")) == 0
    assert tools.base_page_name(r"Foo") == r"Foo"
    assert tools.base_page_name(r"Project:Foo") == r"Foo"
    assert tools.base_page_name(r"Foo/Bar") == r"Foo"
    assert tools.base_page_name(r"Foo/Bar/Boz") == r"Foo"
    assert tools.base_page_name(r"Project:Foo/Bar/Boz") == r"Foo"


def test_sub_page_name() -> None:
    S = W.for_site(EN)
    assert len(tools.sub_page_name(r"")) == 0
    assert tools.sub_page_name(r"Foo") == r"Foo"
    assert tools.sub_page_name(r"Foo/Bar") == r"Bar"
    assert tools.sub_page_name(r"Foo/Bar/Boz") == r"Boz"
    assert tools.sub_page_name(r"Project:Foo") == r"Foo"
    assert tools.sub_page_name(r"Image:Foo/Bar") == r"Bar"


def test_server_name() -> None:
    S = W.for_site(EN)
    assert tools.server_name(r"http://foo") == r"foo"
    assert tools.server_name(r"http://foo/") == r"foo"
    assert tools.server_name(r"http://foo.bar.com/path/script?a=foo/bar") == r"foo.bar.com"


def test_wiki_encode() -> None:
    S = W.for_site(EN)
    assert tools.wiki_encode(r"foo") == r"foo"
    assert tools.wiki_encode(r"Foo") == r"Foo"
    assert tools.wiki_encode(r"foo bar") == r"foo_bar"
    assert tools.wiki_encode(r"foo_bar") == r"foo_bar"
    assert tools.wiki_encode(r"foo/bar") == r"foo/bar"
    assert tools.wiki_encode(r"foo:bar") == r"foo:bar"
    assert (tools.wiki_encode(r"Café")).lower() == (r"Caf%C3%A9").lower()
    assert (tools.wiki_encode(r"тест:тест")).lower() == (
        r"%D1%82%D0%B5%D1%81%D1%82:%D1%82%D0%B5%D1%81%D1%82"
    ).lower()
    assert tools.wiki_encode(r"foo+bar") == r"foo%2bbar"


def test_wiki_decode() -> None:
    S = W.for_site(EN)
    assert tools.wiki_decode(r"foo") == r"foo"
    assert tools.wiki_decode(r"Foo") == r"Foo"
    assert tools.wiki_decode(r"foo_bar") == r"foo bar"
    assert tools.wiki_decode(r"foo bar") == r"foo bar"
    assert tools.wiki_decode(r"foo/bar") == r"foo/bar"
    assert tools.wiki_decode(r"foo:bar") == r"foo:bar"
    assert tools.wiki_decode(r"foo+bar") == r"foo+bar"
    assert tools.wiki_decode(r"foo%2bbar") == r"foo+bar"


def test_split_to_sections() -> None:
    S = W.for_site(EN)
    sections = tools.split_to_sections("foo\r\n==bar=\r\nboo1\r\n\r\n= boz =\r\n==quux==")
    assert sections == ["foo\r\n", "==bar=\r\nboo1\r\n\r\n", "= boz =\r\n", "==quux==\r\n"]
    sections = tools.split_to_sections("==bar=\r\nboo2\r\n\r\n= boz =\r\n==quux==")
    assert sections == ["==bar=\r\nboo2\r\n\r\n", "= boz =\r\n", "==quux==\r\n"]
    sections = tools.split_to_sections("\r\n==bar=\r\nboo3\r\n\r\n= boz =\r\n==quux==")
    assert sections == ["\r\n", "==bar=\r\nboo3\r\n\r\n", "= boz =\r\n", "==quux==\r\n"]
    sections = tools.split_to_sections("\r\n==bar=\r\nboo4\r\n\r\n=== boz ===\r\n==quux==")
    assert sections == ["\r\n", "==bar=\r\nboo4\r\n\r\n", "=== boz ===\r\n", "==quux==\r\n"]
    sections = tools.split_to_sections(r"")
    assert sections == ["\r\n"]
    sections = tools.split_to_sections(r"==foo==")
    assert sections == ["==foo==\r\n"]


def test_get_zeroth_section() -> None:
    S = W.for_site(EN)
    assert tools.get_zeroth_section(r"Hello" + "\r\n" + r"==Heading==") == r"Hello" + "\r\n"
    assert tools.get_zeroth_section(r"Hello" + "\r\n" + r"===Heading===") == r"Hello" + "\r\n"
    assert tools.get_zeroth_section(r"Hello" + "\r\n") == r"Hello" + "\r\n"


def test_remove_matches() -> None:
    matches = DotNetRegex("[ce]").matches("abc bce cde def")
    assert tools.remove_matches("abc bce cde def", matches) == "ab b d df"
    matches = DotNetRegex("test").matches("")
    assert tools.remove_matches("test", matches) == "test"
    assert tools.remove_matches("abc", matches) == "abc"
    assert tools.remove_matches("", matches) == ""
    matches = DotNetRegex("(123|abc)").matches("abc123")
    assert tools.remove_matches("abc123", matches) == ""
    matches = DotNetRegex("[Tt]est").matches("test")
    assert tools.remove_matches("test", matches) == ""
    assert tools.remove_matches("test", []) == "test"
    matches = DotNetRegex("abc").matches("world abc then abc after that then")
    assert (
        tools.remove_matches("world abc then abc after that then", matches)
        == "world  then  after that then"
    )


def test_remove_hash_from_page_title() -> None:
    S = W.for_site(EN)
    assert tools.remove_hash_from_page_title(r"ab c") == r"ab c"
    assert tools.remove_hash_from_page_title(r"foo#bar") == r"foo"
    assert tools.remove_hash_from_page_title(r"foo##bar#") == r"foo"
    assert tools.remove_hash_from_page_title(r"foo#") == r"foo"
    assert len(tools.remove_hash_from_page_title(r"#")) == 0
    assert len(tools.remove_hash_from_page_title(r"")) == 0


def test_deduplicate_list() -> None:
    S = W.for_site(EN)
    A = []
    assert tools.deduplicate_list(A) == A
    A.append(r"hello")
    assert tools.deduplicate_list(A) == A
    A.append(r"hello2")
    assert tools.deduplicate_list(A) == A
    A.append(r"hello")
    assert len(tools.deduplicate_list(A)) == 2


def test_split_lines() -> None:
    S = W.for_site(EN)
    assert len(tools.split_lines(r"")) == 0
    test = [r"foo"]
    assert tools.split_lines(r"foo") == test
    assert tools.split_lines("foo\r") == test
    assert tools.split_lines("foo\n") == test
    assert tools.split_lines("foo\r\n") == test
    test = [r"foo", r"bar"]
    assert tools.split_lines("foo\r\nbar") == test
    assert tools.split_lines("foo\rbar") == test
    assert tools.split_lines("foo\rbar") == test
    test = [r""]
    assert tools.split_lines("\n") == test
    assert tools.split_lines("\r\n") == test
    assert tools.split_lines("\r") == test
    test = [r"", r""]
    assert tools.split_lines("\n\n") == test
    assert tools.split_lines("\r\n\r\n") == test
    assert tools.split_lines("\r\r") == test
    test = [r"", r"foo", r"", r"bar"]
    assert tools.split_lines("\r\nfoo\r\n\r\nbar") == test
    assert tools.split_lines("\rfoo\r\rbar") == test
    assert tools.split_lines("\nfoo\n\nbar") == test


def test_first_chars() -> None:
    S = W.for_site(EN)
    assert len(tools.first_chars(r"", 0)) == 0
    assert len(tools.first_chars(r"", 3)) == 0
    assert len(tools.first_chars(r"123", 0)) == 0
    assert tools.first_chars(r"12", 2) == r"12"
    assert tools.first_chars(r"12", 3) == r"12"
    assert tools.first_chars(r"123", 2) == r"12"


def test_newline() -> None:
    S = W.for_site(EN)
    assert tools.newline(r"foo") == "\r\n" + r"foo"
    assert tools.newline(r"foo", 1) == "\r\n" + r"foo"
    assert tools.newline(r"foo", 2) == "\r\n\r\n" + r"foo"
    assert len(tools.newline(r"")) == 0
    assert len(tools.newline(r"", 2)) == 0


def test_is_redirect() -> None:
    S = W.for_site(EN)
    assert tools.is_redirect(r"#REDIRECT  [[Foo]]")
    assert tools.is_redirect(r"#REDIRECT  [[Foo|bar]]")
    assert tools.is_redirect(r"#redirecT[[:Foo]]")
    assert tools.is_redirect("should work!\r\n#REDIRECT [[Foo]]")
    assert not (tools.is_redirect(r"#REDIRECT you to [[Hell]]"))
    assert not (tools.is_redirect(r"REDIRECT [[Foo]]"))
    assert tools.is_redirect(r"#REDIRECT:[[Foo]]")
    assert tools.is_redirect(r"#REDIRECT : [[Foo]]")
    assert not (tools.is_redirect(r"<nowiki>#REDIRECT  [[Foo]]</nowiki>"))


def test_is_redirect_or_soft_redirect() -> None:
    S = W.for_site(EN)
    assert tools.is_redirect_or_soft_redirect(r"#REDIRECT  [[Foo]]")
    assert tools.is_redirect_or_soft_redirect(r"#redirecT[[:Foo]]")
    assert tools.is_redirect_or_soft_redirect("should work!\r\n#REDIRECT [[Foo]]")
    assert tools.is_redirect_or_soft_redirect(r"{{soft redirect|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{soft|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{category redirect|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{Interwiki redirect|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{Userrename|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{Commons category redirect|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{Deprecated shortcut|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{Wikisource redirect|Foo}}")
    assert tools.is_redirect_or_soft_redirect(r"{{Double soft redirect|Foo}}")
    assert not (tools.is_redirect_or_soft_redirect(r"{{software|Foo}}"))


def test_redirect_target() -> None:
    S = W.for_site(EN)
    assert tools.redirect_target(r"#redirect [[Foo]]") == r"Foo"
    assert tools.redirect_target(r"#redirect [[Foo]] {{R from something}}") == r"Foo"
    assert tools.redirect_target(r"#REDIRECT[[Foo]]") == r"Foo"
    assert tools.redirect_target(r"#redirect[[:Foo bar ]]") == r"Foo bar"
    assert tools.redirect_target(r"#redirect[[ :  Foo bar ]]") == r"Foo bar"
    assert tools.redirect_target("{{delete}}\r\n#redirect [[Foo]]") == r"Foo"
    assert tools.redirect_target(r"#REDIRECT [[Foo|bar]]") == r"Foo"
    assert tools.redirect_target(r"#REDIRECT[[Foo%2C_bar]]") == r"Foo, bar"
    assert tools.redirect_target(r"#REDIRECT[[%D0%A5%D1%83%D0%B9]]") == r"Хуй"
    assert tools.redirect_target(r"#REDIRECT:[[Foo]]") == r"Foo"
    assert tools.redirect_target(r"#REDIRECT : [[Foo]]") == r"Foo"
    assert tools.redirect_target(r"#REDIRECT [[Foo#bar]]") == r"Foo#bar", r"redirect to section"
    assert tools.redirect_target(r"#REDIRECT [[Foo#bar|other]]") == r"Foo#bar", (
        r"redirect to section, piped link"
    )
    assert len(tools.redirect_target(r"<nowiki>#REDIRECT  [[Foo]]</nowiki>")) == 0
    assert (
        len(
            tools.redirect_target(
                "{{Refimprove|date=October 2008}}\r\n{{Infobox Military Conflict\r\n|conflict=1383–1385 Crisis\r\n|image=\r\n|caption=\r\n|partof=\r\n|date=April 1383 - October 1385\r\n|place=[[Portugal]] and [[Crown of Castile|Castille]]\r\n|result=Victory for John I of Portugal\r\n|combatant1=[[File:PortugueseFlag1385.svg|22px]] [[Kingdom of Portugal]]&lt;br&gt;''Supported by:''&lt;br&gt;[[Image:England Arms 1405.svg|22px]] [[Kingdom of England]]\r\n|combatant2=[[Image:Escudo Corona de Castilla.png|22px]] [[Crown of Castile]]&lt;br&gt;''Supported by:''&lt;br&gt;[[Image:France Ancient.svg|22px]] [[Kingdom of France]]\r\n|commander1=[[John I of Portugal]]&lt;br&gt;[[Nuno Álvares Pereira]]\r\n|commander2=[[John I of Castile]]&lt;br&gt;[[Fernando Sanchez de Tovar]]&lt;br&gt;[[Pedro Álvares Pereira]]\r\n|strength1=\r\n|strength2=\r\n|casualties1=\r\n|casualties2=\r\n|\r\n}}\r\n{{Campaignbox Portuguese Crisis 1383}}\r\n\r\n\r\n{{History of Portugal|\r\nimage=[[Image:AljubarrotaBattle.jpg|250px]]|\r\ncaption=Battle of Aljubarrota}}\r\nThe '''1383–1385 Crisis''' was a period of [[civil war]] in [[History of Portugal|Portuguese history]] that began with the [[death]] of [[King of Portugal|King]] [[Ferdinand I of Portugal]], who left no male [[heir]]s, and ended with the accession to the [[throne]] of King [[John I of Portugal|John I]] in 1385, in the wake of the [[Battle of Aljubarrota]].\r\n\r\nIn Portugal, this period is also known as the &quot;Portuguese [[Interregnum]]&quot;, since it is a period when no crowned [[monarch|king]] reigned. The period is interpreted in Portuguese popular history as a Portuguese national &quot;resistance movement&quot; countering Castilian intervention, as the &quot;great revealer of national consciousness&quot;, as Robert Durand expressed it.&lt;ref&gt;Robert Durand, in ''Encyclopedia of the Middle Ages'' (Routledge, 2000), ''s.v.'' &quot;Portugal&quot;, p 1173; see also Armíndo de Sousa, &quot;Portugal&quot; in ''The New Cambridge Medieval History'' 2004, vol. II p. 629.&lt;/ref&gt; The role of the burgesses and nobles that established the Aviz dynasty securely on an independent throne can be contrasted with the centrifugal pull of aristocratic factions against a centralised monarchy in the English [[War of the Roses]] and with national and political aspects of the [[Hundred Years' War]] being waged in France.\r\n\r\n==Prelude=="
            )
        )
        == 0
    )


def test_get_title_from_url() -> None:
    S = W.for_site(EN)
    assert tools.get_title_from_url(r"https://en.wikipedia.org/wiki/foo_bar") == r"foo bar"
    assert tools.get_title_from_url(r"https://en.wikipedia.org/wiki/%D0%A5%D1%83%D0%B9") == r"Хуй"
    assert tools.get_title_from_url(r"https://en.wikipedia.org/w/index.php?title=foo") == r"foo"
    assert tools.get_title_from_url(r"https://en.wikipedia.org/w/index.php/foo") == r"foo"
    assert tools.get_title_from_url(r"http://en.wikipedia.org/w/index.php/foo") == r"foo"
    assert tools.get_title_from_url(r"") is None
    assert tools.get_title_from_url(r"foo") is None
    assert tools.get_title_from_url(r"https://en.wikipedia.org") is None
    assert tools.get_title_from_url(r"https://en.wikipedia.org/wiki/") is None
    assert (
        tools.get_title_from_url(r"https://en.wikipedia.org/w/index.php?title=foo&action=delete")
        is None
    )
    assert tools.get_title_from_url(r"https://en.wikipedia.org/wiki/index.html?curid=666") is None
    assert tools.get_title_from_url(r"https://en.wikipedia.org/wiki/foo?action=delete") is None
    assert (
        tools.get_title_from_url(r"https://en.wikipedia.org/w/index.php?title=foo&action=delete")
        is None
    )
    assert tools.get_title_from_url(r"https://en.wikipedia.org/w/index.php/foo?action=bar") is None


def test_first_difference() -> None:
    S = W.for_site(EN)
    assert tools.first_difference(r"a", r"b") == 0
    assert tools.first_difference(r"", r"a") == 0
    assert tools.first_difference(r"a", r"") == 0
    assert tools.first_difference(r"aa", r"ab") == 1
    assert tools.first_difference(r"ab", r"aa") == 1
    assert tools.first_difference(r"foo", r"foobar") == 3
    assert tools.first_difference(r"football", r"foobar") == 3
    assert tools.first_difference(r"foo", r"foo") == 3


def test_apply_key_words() -> None:
    S = W.for_site(EN)
    assert (
        tools.apply_key_words(
            r"Wikipedia talk:AutoWikiBrowser/Sandbox",
            "%%pagename%%\r\n%%pagenamee%%\r\n\r\n%%basepagename%%\r\n%%basepagenamee%%\r\n\r\n%%namespace%%\r\n%%namespacee%%\r\n\r\n%%subpagename%%\r\n%%subpagenamee%%\r\n\r\n%%fullpagename%%\r\n%%fullpagenamee%%\r\n\r\n%%title%%\r\n%%namespace%%",
        )
        == "AutoWikiBrowser/Sandbox\r\nAutoWikiBrowser/Sandbox\r\n\r\nAutoWikiBrowser\r\nAutoWikiBrowser\r\n\r\nWikipedia talk\r\nWikipedia_talk\r\n\r\nSandbox\r\nSandbox\r\n\r\nWikipedia talk:AutoWikiBrowser/Sandbox\r\nWikipedia_talk:AutoWikiBrowser/Sandbox\r\n\r\nWikipedia talk:AutoWikiBrowser/Sandbox\r\nWikipedia talk"
    )
    assert (
        tools.apply_key_words(r"n/a", "%%server%%\r\n%%scriptpath%%\r\n%%servername%%")
        == "https://en.wikipedia.org\r\n/w\r\nen.wikipedia.org"
    )
    assert len(tools.apply_key_words(r"", r"")) == 0
    assert len(tools.apply_key_words(r"%%foo%%", r"")) == 0
    assert tools.apply_key_words(r"", r"%%foo%%") == r"%%foo%%"
    assert tools.apply_key_words(r"foo(bar)", r"%%title%% was", True) == r"foo\(bar\) was", (
        r"%%title%% escaped if requested"
    )
    assert tools.apply_key_words(r"foo(bar)", r"%%pagename%% was", True) == r"foo\(bar\) was", (
        r"%%pagename%% escaped if requested"
    )
    assert tools.apply_key_words(r"foo(bar)", r"%%basepagename%% was", True) == r"foo\(bar\) was", (
        r"%%basepagename%% escaped if requested"
    )
    assert tools.apply_key_words(r"foo(bar)", r"%%title%% was", False) == r"foo(bar) was", (
        r"%%title%% not escaped if not requested"
    )


def test_is_wikimedia_project() -> None:
    for p in (
        "wikipedia",
        "commons",
        "meta",
        "species",
        "wikibooks",
        "wikinews",
        "wikiquote",
        "wikisource",
        "wikiversity",
        "wikivoyage",
        "wiktionary",
        "mediawiki",
    ):
        assert tools.is_wikimedia_project(p), p
    assert not tools.is_wikimedia_project("custom")
    assert not tools.is_wikimedia_project("wikia")


@pytest.mark.skip(reason="AWB's ProjectEnum ordering; AWB-L identifies projects by name")
def test_orde_of_wikimedia_projects() -> None:
    pass


def test_strip_namespace_colon() -> None:
    S = W.for_site(EN)
    s = tools.strip_namespace_colon(r"User:")
    assert r":" not in s
    s = tools.strip_namespace_colon(r"Project:")
    assert r":" not in s


def test_remove_namespace_string() -> None:
    S = W.for_site(EN)
    assert tools.remove_namespace_string(r"Test") == r"Test"
    assert tools.remove_namespace_string(r"User:Test") == r"Test"
    assert tools.remove_namespace_string(r"User talk:Test") == r"Test"
    assert tools.remove_namespace_string(r"Category:Test") == r"Test"


def test_get_namespace_string() -> None:
    S = W.for_site(EN)
    assert len(tools.get_namespace_string(r"Test")) == 0
    assert tools.get_namespace_string(r"User:Test") == r"User"
    assert tools.get_namespace_string(r"User talk:Test") == r"User talk"
    assert tools.get_namespace_string(r"Category:Test") == r"Category"
    assert tools.get_namespace_string(r"Help:Test") == r"Help"


def test_filter_some_articles() -> None:
    articles = ["Test", "Commons:Test", "MediaWiki:Test", "MediaWiki talk: test", "User talk:Test"]
    res = tools.filter_some_articles(articles)
    assert len(res) == 2
    for a in res:
        ns = namespace.determine(a)
        assert not a.startswith("Commons:")
        assert ns not in (Namespace.MEDIAWIKI, Namespace.MEDIAWIKI_TALK)
        assert ns >= Namespace.ARTICLE


def test_replace_with_spaces_tests() -> None:
    S = W.for_site(EN)
    foo = DotNetRegex(r"foo")
    assert len(tools.replace_with_spaces(r"", foo)) == 0
    assert tools.replace_with_spaces(r"foo", foo) == r"   "
    assert tools.replace_with_spaces(r"foobarfoo", foo) == r"   bar   "
    assert tools.replace_with_spaces(r"foobarfoo", foo, 1) == r"   bar   "
    foo = DotNetRegex(r"f(o)o")
    assert tools.replace_with_spaces(r"foo", foo, 1) == r" o "
    assert tools.replace_with_spaces(r"foobarfoo", foo, 1) == r" o bar o "


def test_replace_with_tests() -> None:
    S = W.for_site(EN)
    foo = DotNetRegex(r"foo")
    assert len(tools.replace_with(r"", foo, "#")) == 0
    assert tools.replace_with(r"foo", foo, "#") == r"###"
    assert tools.replace_with(r"foobarfoo", foo, "#") == r"###bar###"
    foo = DotNetRegex(r"f(o)o")
    assert len(tools.replace_with(r"", foo, "#")) == 0
    assert tools.replace_with(r"foo", foo, "#") == r"###"
    assert tools.replace_with(r"foobarfoo", foo, "#") == r"###bar###"
    assert len(tools.replace_with(r"", foo, "#", 1)) == 0
    assert tools.replace_with(r"foo", foo, "#", 1) == r"#o#"
    assert tools.replace_with(r"foobarfoo", foo, "#", 1) == r"#o#bar#o#"


def test_html_list_to_wiki() -> None:
    S = W.for_site(EN)
    assert tools.html_list_to_wiki(r"Fred", r"*") == r"* Fred", r"simple case"
    assert tools.html_list_to_wiki(r"Fred" + "\r\n", r"*") == r"* Fred" + "\r\n", (
        r"simple case, trailing newline"
    )
    assert tools.html_list_to_wiki("Fred\r\nJones", r"*") == "* Fred\r\n* Jones", r"Two entries"
    assert tools.html_list_to_wiki(r"Fred<BR>", r"*") == r"* Fred", r"br handling"
    assert tools.html_list_to_wiki(r"Fred<br/>", r"*") == r"* Fred", r"br handling"
    assert tools.html_list_to_wiki(r"Fred", r"#") == r"# Fred", r"simple case #"
    assert tools.html_list_to_wiki(r"<OL>Fred</OL>", r"#") == r"# Fred", r"ol handling"
    assert tools.html_list_to_wiki(r"<li>Fred</li>", r"#") == r"# Fred", r"li handling"
    assert tools.html_list_to_wiki(r":Fred", r"*") == r"* Fred", r"trim colon"
    assert tools.html_list_to_wiki(r"*Fred", r"*") == r"* Fred", r"already a list"
    assert (
        tools.html_list_to_wiki(r"#Fred Smith [[Foo#bar]]", r"*") == r"* Fred Smith [[Foo#bar]]"
    ), r"number to bullet conversion"
    assert tools.html_list_to_wiki(r"Fred Smith:here", r"*") == r"* Fred Smith:here", (
        r"normal colon retained"
    )
    assert tools.html_list_to_wiki("1 Fred\r\n2 Jones", r"*") == "* Fred\r\n* Jones", (
        r"number to bullet conversion 2 entries"
    )
    assert tools.html_list_to_wiki("11. Fred\r\n12. Jones", r"*") == "* Fred\r\n* Jones", (
        r"dot number conversion"
    )
    assert tools.html_list_to_wiki("(1) Fred\r\n(2) Jones", r"*") == "* Fred\r\n* Jones", (
        r"full bracket number conversion 1 digit"
    )
    assert tools.html_list_to_wiki("1) Fred\r\n2) Jones", r"*") == "* Fred\r\n* Jones", (
        r"bracket number conversion 1 digit"
    )
    assert tools.html_list_to_wiki("(11) Fred\r\n(12) Jones", r"*") == "* Fred\r\n* Jones", (
        r"bracket number conversion 2 digits"
    )
    assert tools.html_list_to_wiki("(998) Fred\r\n(999) Jones", r"*") == "* Fred\r\n* Jones", (
        r"bracket number conversion 3 digits"
    )
    assert tools.html_list_to_wiki("1980 Fred\r\n2004 Jones", r"*") == "* 1980 Fred\r\n* 2004 Jones"
    assert tools.html_list_to_wiki("Fred\r\nTim\r\nJohn", r"*") == "* Fred\r\n* Tim\r\n* John", (
        r"do not add list to blank lines/lines with just whitespace"
    )
    assert (
        tools.html_list_to_wiki("Fred\r\n \r\nTim\r\n \r\nJohn", r"*")
        == "* Fred\r\n \r\n* Tim\r\n \r\n* John"
    ), r"do not add list to blank lines/lines with just whitespace 2"


def test_remove_syntax() -> None:
    S = W.for_site(EN)
    assert len(tools.remove_syntax(r"")) == 0
    assert len(tools.remove_syntax(r" ")) == 0
    assert tools.remove_syntax(r"* foo") == r"foo"
    assert tools.remove_syntax(r"# foo") == r"foo"
    assert tools.remove_syntax(r":foo") == r"foo"
    assert tools.remove_syntax(r"foo_bar") == r"foo bar"
    assert tools.remove_syntax(r"foo_bar:the great") == r"foo bar:the great"
    assert tools.remove_syntax(r"[foo]") == r"foo"
    assert tools.remove_syntax(r"[[foo]]") == r"foo"
    assert tools.remove_syntax(r"#[[foo]]") == r"foo"
    assert tools.remove_syntax(r"#[[ foo ]]") == r"foo"
    assert tools.remove_syntax(r"foo&amp;bar") == r"foo&bar"
    assert tools.remove_syntax(r"* [http://site.com words]") == r"http://site.com words"
    assert tools.remove_syntax(r"* [https://site.com words]") == r"https://site.com words"
    assert tools.remove_syntax(r"foo &quot;bar&quot; here") == r'foo "bar" here'
    assert tools.remove_syntax(r"foo�bar") == r"foobar"
    assert tools.remove_syntax(r"  * foo") == r"foo"


def test_string_between() -> None:
    S = W.for_site(EN)
    assert tools.string_between(r"now foo here", r"now ", r" here") == r"foo"
    assert tools.string_between(r"now foo here foo", r"now", r" here") == r" foo"
    assert len(tools.string_between(r"now foo av", r"now ", r" here")) == 0
    assert tools.string_between(r"now foo here blah here", r"now ", r" here") == r"foo"
    assert tools.string_between(r"now foo here now foo2 here", r"now ", r" here") == r"foo"


def test_regex_match_count() -> None:
    S = W.for_site(EN)
    assert tools.regex_match_count(r"a", r"a") == 1
    assert tools.regex_match_count(r"\w", r"abcde") == 5
    assert tools.regex_match_count(r"a", r"aAAa", O.IGNORE_CASE) == 4
    assert tools.regex_match_count(r"\w+", r"test case") == 2


def test_interwiki_count() -> None:
    S = W.for_site(EN)
    S = set_site(interwiki_languages=frozenset([r"de", r"es", r"fr", r"it", r"sv"]))
    assert tools.interwiki_count(r"now [[foo]] was great") == 0
    assert tools.link_count(r"now [[Template:foo]] was great") == 0
    assert tools.link_count(r"now [[Category:foo]] was great") == 0
    assert tools.interwiki_count(r"now [[de:foo]] was great") == 1
    assert tools.interwiki_count(r"now [[de:foo]] was great [[aa:now]] here") == 1
    assert tools.interwiki_count(r"now [[de:foo]] was great [[aa:now]] here [[fr:bye]]") == 2


def test_link_count_tests() -> None:
    S = W.for_site(EN)
    assert tools.link_count(r"foo") == 0, r"No links"
    assert tools.link_count(r"[foo]") == 0, r"broken links not counted"
    assert tools.link_count(r"[[Image:foo.png]]") == 0, r"Image links not counted"
    assert tools.link_count(r"[[File:foo.png]]") == 0, r"File links not counted"
    assert tools.link_count(r"[[Template:Dn]]") == 0, r"Templates not counted"
    assert tools.link_count(r"now [[en:foo]] was great") == 1, r"Interwikis are counted"
    assert tools.link_count(r"[[foo]]") == 1
    assert tools.link_count(r"[[foo]] and [[foo]]") == 2, r"counts repeated links"
    assert tools.link_count(r"[[Image:foo.png]] and [[foo]]") == 1
    assert tools.link_count(r"[[foo]]s and [[barbie|bar]]") == 2, r"counts piped links"
    assert tools.link_count(r"{{flagIOC}}") == 1
    assert tools.link_count(r"{{speciesbox}}") == 1
    assert tools.link_count(r"{{automatic taxobox}}") == 1
    assert tools.link_count(r"now [[Magic: the gathering]] was great") == 1, (
        r"handles mainspace wikilink with colon"
    )
    assert tools.link_count(r"[[foo]]s and [[barbie|bar]] {{flagIOC}}") == 3, (
        r"counts flagIOC template as a link"
    )
    assert tools.link_count(r"[[foo]]s and [[barbie|bar]] and [[foo2]]", 1) == 1, (
        r"count capped at limit"
    )
    assert tools.link_count(r"[[foo]]s and [[barbie|bar]] and [[foo2]]", 2) == 2, (
        r"count capped at limit"
    )
    assert tools.link_count(r"{{flagIOC}} {{flagIOC}} {{flagIOC}}", 2) == 2, (
        r"count capped at limit, flagIOC"
    )
    assert tools.link_count(r"[[Foo|ʿUrwa]]") == 1, r"Handling of Unicode modifier letters"


def test_dates_count() -> None:
    S = W.for_site(EN)
    results = {}
    results[DateLocale.ISO] = 1
    results[DateLocale.INTERNATIONAL] = 1
    results[DateLocale.AMERICAN] = 0
    assert tools.dates_count(r"2015-01-01 and 11 January 2010") == results, (
        r"zero dates of a type reported"
    )
    results.clear()
    results[DateLocale.ISO] = 1
    results[DateLocale.INTERNATIONAL] = 1
    results[DateLocale.AMERICAN] = 1
    assert tools.dates_count(r"2015-01-01 and 11 January 2010 and March 5, 2011") == results, (
        r"each date type reported"
    )
    assert tools.dates_count(r"2015-01-01 and| 11 January 2010 and| March 5, 2011") == results, (
        r"each date type reported when split"
    )
    results.clear()
    results[DateLocale.ISO] = 2
    results[DateLocale.INTERNATIONAL] = 1
    results[DateLocale.AMERICAN] = 1
    assert tools.dates_count(r"2015-01-01 and 2015-01-01 and 11 January and March 5") == results, (
        r"Duplicate dates counted, short format matched"
    )


def test_duplicate_wiki_links() -> None:
    S = W.for_site(EN)
    dupeWikiLinks = []
    dupeWikiLinks.append(r"Foo (2)")
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]]") == dupeWikiLinks, (
        r"Simple case two plain links same case"
    )
    assert tools.duplicate_wiki_links(r"[[foo]] [[foo]]") == dupeWikiLinks, (
        r"Simple case two plain links same lower case"
    )
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[Bar]]") == dupeWikiLinks, (
        r"Don't count single link"
    )
    assert tools.duplicate_wiki_links(r"[[Foo|bar2]] [[Foo|bar]]") == dupeWikiLinks, (
        r"Simple case two piped links same case"
    )
    assert tools.duplicate_wiki_links(r"[[Foo]] [[foo]]") == dupeWikiLinks, (
        r"convert first letter case for compare"
    )
    assert tools.duplicate_wiki_links(r"[[ Foo |bar]] [[ Foo ]]") == dupeWikiLinks, (
        r"Ignore excess whitespace"
    )
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[Bar]] [[Bar2]]") == dupeWikiLinks, (
        r"Match on whole link name"
    )
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[|x]] [[|x]]") == dupeWikiLinks, (
        r"Ignore targetless links"
    )
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[1 May]] [[1 May]]") == dupeWikiLinks, (
        r"Ignore dates (int format)"
    )
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[May 1]] [[May 1]]") == dupeWikiLinks, (
        r"Ignore dates (Am format)"
    )
    dupeWikiLinks.clear()
    dupeWikiLinks.append(r"Foo (3)")
    assert tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[Foo|bar]]") == dupeWikiLinks, (
        r"Includes count after link name"
    )
    assert (
        tools.duplicate_wiki_links(r"[[Foo]] [[Foo]] [[Foo|bar]] <!-- [[Foo]] -->") == dupeWikiLinks
    ), r"Ingore commented out link"
    dupeWikiLinks.append(r"Get (3)")
    assert (
        tools.duplicate_wiki_links(r"[[Foo]] [[Get]] [[Foo]] [[Get]] [[Foo|bar]] [[Get]]")
        == dupeWikiLinks
    ), r"List returned is sorted"
    dupeWikiLinks.clear()
    dupeWikiLinks.append(r"Foo (2)")
    assert tools.duplicate_wiki_links(r"[[Foo|ʿUrwa]] [[Foo|ʿUrwa]]") == dupeWikiLinks, (
        r"Handling of Unicode modifier letters"
    )


def test_convert_date() -> None:
    S = W.for_site(EN)
    iso = r"2009-06-11"
    iso2 = r"1890-07-04"
    assert tools.convert_date(iso, DateLocale.INTERNATIONAL) == r"11 June 2009"
    assert tools.convert_date(iso, DateLocale.INTERNATIONAL, False) == r"11 June 2009"
    assert tools.convert_date(iso, DateLocale.INTERNATIONAL, True) == r"11 June 2009"
    assert tools.convert_date(iso, DateLocale.AMERICAN) == r"June 11, 2009"
    assert tools.convert_date(iso, DateLocale.ISO) == iso
    assert tools.convert_date(iso, DateLocale.UNDETERMINED) == iso
    assert tools.convert_date(iso2, DateLocale.INTERNATIONAL) == r"4 July 1890"
    wrong = r"foo"
    assert tools.convert_date(wrong, DateLocale.INTERNATIONAL) == wrong
    assert tools.convert_date(r"2009-10", DateLocale.INTERNATIONAL) == r"2009-10", (
        r"day not added to year month combo"
    )
    assert tools.convert_date(r"11 June 2009", DateLocale.INTERNATIONAL) == r"11 June 2009"
    assert tools.convert_date(r"June 11, 2009", DateLocale.INTERNATIONAL) == r"11 June 2009"
    assert tools.convert_date(r"June 11, 2009", DateLocale.INTERNATIONAL, True) == r"11 June 2009"
    assert tools.convert_date(r"Jan 15 2008", DateLocale.INTERNATIONAL) == r"15 January 2008"
    assert tools.convert_date(r"Jan 15 2008", DateLocale.INTERNATIONAL, True) == r"15 January 2008"
    assert tools.convert_date(r"Jan 15 2008", DateLocale.INTERNATIONAL, False) == r"15 January 2008"
    assert tools.convert_date(r"Jan 15 998", DateLocale.INTERNATIONAL) == r"15 January 998"
    AmericanDate = r"06/11/2009"
    UKDate = r"11/06/2009"
    assert tools.convert_date(AmericanDate, DateLocale.ISO, True) == iso, (
        r"Converts MM/DD/YYYY format dates when flagged"
    )
    assert tools.convert_date(UKDate, DateLocale.ISO, False) == iso, (
        r"Converts DD/MM/YYYY format dates when flagged"
    )
    assert tools.convert_date(UKDate, DateLocale.ISO) == iso, (
        r"Assumes DD/MM/YYYY format dates when NOT flagged"
    )
    assert tools.convert_date(r"May 2009", DateLocale.INTERNATIONAL) == r"May 2009", (
        r"day not added to month year combo"
    )
    assert tools.convert_date(r" May 2009", DateLocale.INTERNATIONAL) == r"May 2009", (
        r"day not added to month year combo"
    )
    assert tools.convert_date(r"2008-Jan-15", DateLocale.INTERNATIONAL) == r"15 January 2008"
    assert tools.convert_date(r"2008 Jan 15", DateLocale.INTERNATIONAL) == r"15 January 2008"
    assert tools.convert_date(r"2008 Jan. 15", DateLocale.INTERNATIONAL) == r"15 January 2008"
    assert tools.convert_date(r"2008 January 15", DateLocale.INTERNATIONAL) == r"15 January 2008"


def test_date_before_today() -> None:
    import datetime

    assert tools.date_before_today("11 May 2009")
    assert tools.date_before_today("May 11, 2009")
    assert tools.date_before_today("2013-12-31")
    # AWB formats DateTime.Now in the user's culture; ISO stands in for that here.
    now = datetime.datetime.now()
    assert tools.date_before_today(
        (now - datetime.timedelta(days=1)).isoformat(sep=" ", timespec="seconds")
    )
    assert not tools.date_before_today(
        (now + datetime.timedelta(days=31)).isoformat(sep=" ", timespec="seconds")
    )
    assert not tools.date_before_today("foo")


def test_convert_date_en_only() -> None:
    S = W.for_site(EN)
    iso2 = r"1890-07-04"
    S = set_lang(r"fr")
    assert tools.convert_date(iso2, DateLocale.INTERNATIONAL) == iso2
    S = set_lang(r"en")
    assert tools.convert_date(iso2, DateLocale.INTERNATIONAL) == r"4 July 1890"


def test_append_parameter_to_template() -> None:
    S = W.for_site(EN)
    assert len(tools.append_parameter_to_template(r"", r"location", r"London")) == 0
    assert (
        tools.append_parameter_to_template(r"{{cite|title=abc}}", r"location", r"London")
        == r"{{cite|title=abc | location=London}}"
    )
    assert (
        tools.append_parameter_to_template(r"{{cite|title=abc}}", r"location", r"")
        == r"{{cite|title=abc | location=}}"
    )
    assert (
        tools.append_parameter_to_template(r"{{cite|title=abc }}", r"location", r"London")
        == r"{{cite|title=abc | location=London }}"
    )
    assert (
        tools.append_parameter_to_template(
            r"{{cite|title=abc|last=a|first=b|date=2009-12-12}}", r"location", r"London"
        )
        == r"{{cite|title=abc|last=a|first=b|date=2009-12-12|location=London}}"
    ), r"no newlines/excess spaces in template"
    assert (
        tools.append_parameter_to_template(
            r"{{cite | title=abc | last=a | first=b | date=2009-12-12 }}", r"location", r"London"
        )
        == r"{{cite | title=abc | last=a | first=b | date=2009-12-12 | location=London }}"
    ), r"spaced parameters in template"
    assert (
        tools.append_parameter_to_template(
            r"{{cite | title = abc | last = a | first = b | date = 2009-11-11 }}",
            r"location",
            r"London",
        )
        == r"{{cite | title = abc | last = a | first = b | date = 2009-11-11 | location = London }}"
    ), r"=spaced parameters in template"
    assert (
        tools.append_parameter_to_template(
            r"{{cite | title= abc | last= a | first= b | date= 2009-11-11 }}",
            r"location",
            r"London",
        )
        == r"{{cite | title= abc | last= a | first= b | date= 2009-11-11 | location= London }}"
    ), r"= half spaced parameters in template"
    assert (
        tools.append_parameter_to_template(r"{{cite|title=abc}}", r"location", r"London", False)
        == r"{{cite|title=abc | location=London}}"
    )
    assert (
        tools.append_parameter_to_template(r"{{cite|title=abc}}", r"location", r"London", True)
        == r"{{cite|title=abc|location=London}}"
    )
    assert (
        tools.append_parameter_to_template("{{cite\r\n|title=abc }}", r"location", r"London")
        == "{{cite\r\n|title=abc | location=London }}"
    ), r"insufficient newlines – space used"
    assert (
        tools.append_parameter_to_template(
            "{{cite\r\n|title=abc\r\n|date=2009-12-12 }}", r"location", r"London"
        )
        == "{{cite\r\n|title=abc\r\n|date=2009-12-12 | location=London }}"
    ), r"insufficient newlines – space used"
    assert (
        tools.append_parameter_to_template(
            "{{cite\r\n|title=abc\r\n|last=a\r\n|first=b\r\n|date=2009-12-12}}",
            r"location",
            r"London",
        )
        == "{{cite\r\n|title=abc\r\n|last=a\r\n|first=b\r\n|date=2009-12-12\r\n|location=London}}"
    ), r"newline set when > 2 existing"
    assert (
        tools.append_parameter_to_template(
            "{{cite\r\n|title=abc\r\n|last=a\r\n|first=b\r\n|date=2009-12-12        }}",
            r"location",
            r"London",
        )
        == "{{cite\r\n|title=abc\r\n|last=a\r\n|first=b\r\n|date=2009-12-12\r\n|location=London }}"
    ), r"existing template end spaces cleaned"
    assert (
        tools.append_parameter_to_template(
            "{{cite\r\n|title=abc\r\n|last=a\r\n|first=b\r\n|date=2009-12-12\r\n}}",
            r"location",
            r"London",
        )
        == "{{cite\r\n|title=abc\r\n|last=a\r\n|first=b\r\n|date=2009-12-12\r\n|location=London\r\n}}"
    ), r"template end on blank line"
    assert (
        tools.append_parameter_to_template(
            "{{cite\r\n  |title=abc\r\n  |last=a\r\n  |first=b\r\n  |date=2009-12-12\r\n}}",
            r"location",
            r"London",
        )
        == "{{cite\r\n  |title=abc\r\n  |last=a\r\n  |first=b\r\n  |date=2009-12-12\r\n  |location=London\r\n}}"
    ), r"template with multiple spaces prior to bar, all params on newline"
    assert (
        tools.append_parameter_to_template(
            "{{cite\r\n |title=abc\r\n |last=a\r\n |first=b\r\n |date=2009-12-12\r\n}}",
            r"location",
            r"London",
        )
        == "{{cite\r\n |title=abc\r\n |last=a\r\n |first=b\r\n |date=2009-12-12\r\n |location=London\r\n}}"
    ), r"template with single prior to bar, all params on newline"
    assert (
        tools.append_parameter_to_template(
            "{{cite journal\r\n | quotes =\r\n | doi = 10.2307/904183\r\n | id =\r\n | url = http://links.jstor.org/sici?sici=0027-4666(19060101)47%3A755%3C27%3AMSIC(J%3E2.0.CO%3B2-N\r\n | publisher = The Musical Times, Vol. 47, No. 755\r\n }}",
            r"jstor",
            r"904183",
        )
        == "{{cite journal\r\n | quotes =\r\n | doi = 10.2307/904183\r\n | id =\r\n | url = http://links.jstor.org/sici?sici=0027-4666(19060101)47%3A755%3C27%3AMSIC(J%3E2.0.CO%3B2-N\r\n | publisher = The Musical Times, Vol. 47, No. 755\r\n | jstor = 904183\r\n }}"
    )


def test_get_template_parameter_value() -> None:
    S = W.for_site(EN)
    assert tools.get_template_parameter_value(r"{{cite|param1=here}}", r"param1") == r"here"
    assert tools.get_template_parameter_value(r"{{cite|param1 = here }}", r"param1") == r"here"
    assert (
        tools.get_template_parameter_value("{{cite\r\n| param1=here\r\n|param=there}}", r"param1")
        == r"here"
    )
    assert tools.get_template_parameter_value(r"{{cite|param1=here|foo=bar}}", r"param1") == r"here"
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 = [[1892]]-[[1893]]}}", r"param1")
        == r"[[1892]]-[[1893]]"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1=here {{t1|foo|bar}} there|foo=bar}}", r"param1"
        )
        == r"here {{t1|foo|bar}} there"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1=here <!--comm|bar--> there|foo=bar}}", r"param1"
        )
        == r"here <!--comm|bar--> there"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 = here [[piped|link]]}}", r"param1")
        == r"here [[piped|link]]"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = [[piped|link]], [[another|piped link]] here}}", r"param1"
        )
        == r"[[piped|link]], [[another|piped link]] here"
    )
    assert len(tools.get_template_parameter_value(r"{{cite|param2=here}}", r"param1")) == 0
    assert (
        len(tools.get_template_parameter_value(r"{{cite|param1 {{test}} =here}}", r"param1")) == 0
    )
    assert (
        len(tools.get_template_parameter_value(r"{{cite|param1 [[test|2]] =here}}", r"param1")) == 0
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 <!--comm--> =here}}", r"param1")
        == r"here"
    )
    assert len(tools.get_template_parameter_value(r"{{cite|param1= }}", r"param1")) == 0
    assert (
        len(tools.get_template_parameter_value(r"{{cite|<!--param1=foo-->other=yes }}", r"param1"))
        == 0
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|<!--param1=foo-->other=yes }}", r"other")
        == r"yes"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|other<!--param1=foo-->=yes }}", r"other")
        == r"yes"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1<!--comm--> = [[1892]]-[[1893]]}}", r"param1"
        )
        == r"[[1892]]-[[1893]]"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|<!--comm-->param1 = [[1892]]-[[1893]]}}", r"param1"
        )
        == r"[[1892]]-[[1893]]"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1=here|foo=bar|param1=there}}", r"param1")
        == r"here"
    )
    assert tools.get_template_parameter_value(r"{{cite|PARAM1=here}}", r"param1", True) == r"here"
    assert tools.get_template_parameter_value(r"{{cite|param 1=here}}", r"param 1") == r"here"
    assert (
        tools.get_template_parameter_value(r"{{cite|param other=here}}", r"param other") == r"here"
    )


def test_get_template_parameter_values() -> None:
    back = {
        "accessdate": "2012-05-15",
        "title": "Hello",
        "url": "http://www.site.com/abc",
        "author": "",
    }
    g = tools.get_template_parameter_values
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author = | accessdate = 2012-05-15 }}"
        )
        == back
    )
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello |<!-- comm--> author = | accessdate = 2012-05-15 }}"
        )
        == back
    ), "ignores comments between parameters"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author <!-- comm--> = | accessdate = 2012-05-15 }}"
        )
        == back
    ), "ignores comments between parameters 2"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello |author =|accessdate = 2012-05-15 }}"
        )
        == back
    )
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author = | accessdate = 2012-05-15 | url=}}"
        )
        == back
    ), "ignores second parameter call (no value)"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author = | accessdate = 2012-05-15 | url=http://site2.com}}"
        )
        == back
    ), "ignores second parameter call (with value)"

    back["author"] = "<!-- comm-->"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author = <!-- comm--> | accessdate = 2012-05-15 }}"
        )
        == back
    ), "Reports parameter value of comment"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | accessdate = 2012-05-15 | author = <!-- comm--> }}"
        )
        == back
    ), "Reports parameter value of comment: last param"

    back["author"] = ""
    back["format"] = "{{PDF|test}}"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author = | accessdate = 2012-05-15 | format={{PDF|test}} }}"
        )
        == back
    ), "handles nested templates"
    back["last1"] = "Jones"
    assert (
        g(
            r"{{cite web|url=http://www.site.com/abc|title=Hello | author = | accessdate = 2012-05-15 | format={{PDF|test}} |last1=Jones}}"
        )
        == back
    ), "handles parameters with numbers"
    back["trans_title"] = "Here \r\nThere"
    assert (
        g(
            "{{cite web|url=http://www.site.com/abc|title=Hello | author = | accessdate = 2012-05-15 | format={{PDF|test}} |last1=Jones|trans_title=Here \r\nThere}}"
        )
        == back
    ), "handles parameters with newlines"

    back = {"ONE": "somevalue"}
    assert g(r"{{test|ONE=somevalue}}") == back, "handles uppercase parameters"
    back["V_TWO"] = "some_value"
    assert g(r"{{test|ONE=somevalue|V_TWO=some_value}}") == back, "handles uppercase parameters"

    # parameters with space in name
    back = {"ONE": "somevalue"}
    assert g(r"{{test|ONE=somevalue}}") == back
    back["V TWO"] = "some_value"
    assert g(r"{{test|ONE=somevalue|V TWO=some_value}}") == back
    assert g(r"{{test|ONE=somevalue|V TWO  =  some_value}}") == back

    assert g(r"{{test|name = <timeline>abc</timeline>X}}") == {
        "name": "<timeline>abc</timeline>X"
    }, "handles parameters including unformatted text"
    assert g(r"{{test|name = X [http://site.com A | B]|other=Y}}") == {
        "name": "X [http://site.com A | B]",
        "other": "Y",
    }, "handles parameters including external link with pipe"
    assert g(r"{{test|name = X |other1/2=Y}}") == {"name": "X", "other1/2": "Y"}, (
        "handles parameter name with forward slash"
    )


def test_get_template_parameter_value_advanced_cases() -> None:
    S = W.for_site(EN)
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 = here {{foo}}}}", r"param1")
        == r"here {{foo}}"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 = here {{foo|bar}}}}", r"param1")
        == r"here {{foo|bar}}"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 = here <!--foo|bar-->}}", r"param1")
        == r"here <!--foo|bar-->"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1 = <!--foo-->}}", r"param1")
        == r"<!--foo-->"
    ), r"Reports comment when param value just comment"
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = <!--foo--> | param2 = bar }}", r"param1"
        )
        == r"<!--foo-->"
    ), r"Reports comment when param value just comment"
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = [[File:abc.png|asdf|dsfjk|a]] }}", r"param1"
        )
        == r"[[File:abc.png|asdf|dsfjk|a]]"
    )
    assert (
        tools.get_template_parameter_value(
            "{{cite|param1 = [[File:abc.png|asdf|dsfjk|a]]\r\n}}", r"param1"
        )
        == r"[[File:abc.png|asdf|dsfjk|a]]"
    )
    assert (
        tools.get_template_parameter_value(
            "{{cite|param1 = [[File:abc.png|asdf|dsfjk|a]]\r\n|param2=other}}", r"param1"
        )
        == r"[[File:abc.png|asdf|dsfjk|a]]"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = here <nowiki>|</nowiki> there}}", r"param1"
        )
        == r"here <nowiki>|</nowiki> there"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = here <nowiki>|</nowiki> there|parae=aaa}}", r"param1"
        )
        == r"here <nowiki>|</nowiki> there"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = here <pre>|</pre> there|parae=aaa}}", r"param1"
        )
        == r"here <pre>|</pre> there"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = here <ref>|</ref> there|parae=aaa}}", r"param1"
        )
        == r"here <ref>|</ref> there"
    ), r"Ref with pipe"
    assert (
        tools.get_template_parameter_value(
            r'{{cite|param1 = here <ref name="a|b">C</ref> there|parae=aaa}}', r"param1"
        )
        == r'here <ref name="a|b">C</ref> there'
    ), r"Ref name with pipe"
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = here <math>foo</math> there|parae=aaa}}", r"param1"
        )
        == r"here <math>foo</math> there"
    )
    assert (
        tools.get_template_parameter_value(
            r"{{cite|param1 = here <timeline>foo</timeline> there|parae=aaa}}", r"param1"
        )
        == r"here <timeline>foo</timeline> there"
    )
    ItFilm = "{{Film\r\n|titoloitaliano= Matrix\r\n|immagine= [[image:Matrix.png|200px|Il codice di Matrix]]\r\n|didascalia= Il codice di Matrix\r\n|titolooriginale= The Matrix\r\n|nomepaese= [[Stati Uniti d'America|USA]]\r\n|annoproduzione= [[1999]]\r\n|durata= 136 min\r\n|tipocolore= colore\r\n|tipoaudio= sonoro}}"
    assert tools.get_template_parameter_value(ItFilm, r"annoproduzione") == r"[[1999]]"
    assert (
        tools.get_template_parameter_value(
            ItFilm.replace(r"[[1999]]", r"[[1999]"), r"annoproduzione"
        )
        == r"[[1999]"
    )
    assert (
        tools.get_template_parameter_value(
            ItFilm.replace(r"[[1999]]", r"[[1999"), r"annoproduzione"
        )
        == r"[[1999"
    )
    assert (
        tools.get_template_parameter_value(
            ItFilm.replace(r"[[1999]]", r"1999]]"), r"annoproduzione"
        )
        == r"1999]]"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1= here {and} was }}", r"param1")
        == r"here {and} was"
    )
    assert (
        tools.get_template_parameter_value(r"{{cite|param1/2 = here }}", r"param1/2") == r"here"
    ), r"Param name forward slash"


def test_get_template_parameters_values() -> None:
    returned: list[str] = []
    parameters: list[str] = []
    template = (
        r"{{cite web| title=abc |date=1 May 2009 | author=Smith, Ed | work=Times | location=Here }}"
    )
    assert tools.get_template_parameters_values(template, parameters) == returned
    assert len(returned) == 0
    parameters.append("title")
    returned.append("abc")
    assert tools.get_template_parameters_values(template, parameters) == returned
    parameters.append("date")
    returned.append("1 May 2009")
    assert tools.get_template_parameters_values(template, parameters) == returned
    assert tools.get_template_parameters_values(template, parameters)[0] == "abc"
    assert tools.get_template_parameters_values(template, parameters)[1] == "1 May 2009"
    parameters.append("page")
    returned.append("")
    assert tools.get_template_parameters_values(template, parameters) == returned
    assert len(returned) == 3, "zero length string added to return list if parameter not found"
    assert "".join(returned) == "abc1 May 2009"


def test_get_template_argument() -> None:
    S = W.for_site(EN)
    assert tools.get_template_argument(r"{{abc|foo}}", 1) == r"foo"
    assert tools.get_template_argument(r"{{abc| foo}}", 1) == r"foo"
    assert tools.get_template_argument(r"{{abc |  foo  }}", 1) == r"foo"
    assert tools.get_template_argument(r"{{abc |  foo  |bar}}", 1) == r"foo"
    assert tools.get_template_argument(r"{{abc |  foo  |bar }}", 2) == r"bar"
    assert len(tools.get_template_argument(r"{{abc ||  foo  |bar }}", 1)) == 0
    assert (
        tools.get_template_argument(r"{{abc |  foo  |bar [[piped|link]] }}", 2)
        == r"bar [[piped|link]]"
    )
    assert tools.get_template_argument(r"{{abc|foo=def}}", 1) == r"foo=def"
    assert tools.get_template_argument(r"{{Cleanup|section|date=May 2024}}", 1) == r"section"


def test_get_template_argument_index() -> None:
    S = W.for_site(EN)
    assert tools.get_template_argument_index(r"{{abc|foo=yes}}", 1) == 6
    assert tools.get_template_argument_index(r"{{abc|" + r"foo=yes}}", 1) == 6
    assert tools.get_template_argument_index(r"{{abc|  foo=yes|bar=no}}", 1) == 6
    assert tools.get_template_argument_index(r"{{abc|foo=yes}}", 2) == -1


def test_get_template_argument_count() -> None:
    S = W.for_site(EN)
    assert tools.get_template_argument_count(r"{{foo}}") == 0
    assert tools.get_template_argument_count(r"{{foo}}", True) == 0
    assert tools.get_template_argument_count(r"{{foo|}}") == 1
    assert tools.get_template_argument_count(r"{{foo|bar}}") == 1, r"counts unnamed parameters"
    assert tools.get_template_argument_count(r"{{foo|bar}}", True) == 0, (
        r"counts populated named parameters only when requested"
    )
    assert tools.get_template_argument_count(r"{{foo|bar=}}", True) == 0, (
        r"counts populated named parameters only when requested"
    )
    assert tools.get_template_argument_count(r"{{foo|bar=yes}}") == 1, r"counts named parameters"
    assert tools.get_template_argument_count(r"{{foo|bar=yes}}", True) == 1, (
        r"counts named parameters"
    )
    assert (
        tools.get_template_argument_count(r"{{foo|bar=yes|asdf=iiuu|asdfsadf=|eaa=ef}}", True) == 3
    ), r"counts named parameters"
    assert tools.get_template_argument_count(r"{{foo|bar|here|yte}}") == 3, (
        r"counts multiple parameters"
    )
    assert tools.get_template_argument_count(r"{{foo|bar={{yes|foo}}}}") == 1, (
        r"doesn't count nested template calls"
    )


def test_rename_template_parameter() -> None:
    S = W.for_site(EN)
    assert (
        tools.rename_template_parameter(r"{{cite |param1=bar|param2=great}}", r"param2", r"param3")
        == r"{{cite |param1=bar|param3=great}}"
    )
    assert (
        tools.rename_template_parameter(
            r"{{cite |param1=bar| param2 = great}}", r"param2", r"param3"
        )
        == r"{{cite |param1=bar| param3 = great}}"
    )
    assert (
        tools.rename_template_parameter(
            "{{cite\r\n|param1=bar\r\n|param2=great}}", r"param2", r"param3"
        )
        == "{{cite\r\n|param1=bar\r\n|param3=great}}"
    )
    assert (
        tools.rename_template_parameter(
            r"{{cite |param1=bar|param2=great|param=here}}", r"param2", r"param3"
        )
        == r"{{cite |param1=bar|param3=great|param=here}}"
    )
    assert (
        tools.rename_template_parameter(
            r"{{cite |param1=bar|<!--comm-->param2=great}}", r"param2", r"param3"
        )
        == r"{{cite |param1=bar|<!--comm-->param3=great}}"
    )
    assert (
        tools.rename_template_parameter(
            r"{{cite |param1=bar|param2<!--comm-->=great}}", r"param2", r"param3"
        )
        == r"{{cite |param1=bar|param3<!--comm-->=great}}"
    )


def test_rename_template_parameter_list() -> None:
    S = W.for_site(EN)
    Params = list([r"param1"])
    assert (
        tools.rename_template_parameter(r"{{cite |param1=bar|param2=great}}", Params, r"paramx")
        == r"{{cite |paramx=bar|param2=great}}"
    )
    Params.append(r"param2")
    assert (
        tools.rename_template_parameter(r"{{cite |param1=bar|param2=great}}", Params, r"paramx")
        == r"{{cite |paramx=bar|paramx=great}}"
    )
    Params.append(r"param3")
    assert (
        tools.rename_template_parameter(r"{{cite |param1=bar|param2=great}}", Params, r"paramx")
        == r"{{cite |paramx=bar|paramx=great}}"
    )
    assert (
        tools.rename_template_parameter(r"{{cite |param1=bar|param4=great}}", Params, r"paramx")
        == r"{{cite |paramx=bar|param4=great}}"
    )


def test_rename_template_parameter_dictionary() -> None:
    S = W.for_site(EN)
    Params = {}
    Params[r"accesdate"] = r"accessdate"
    Params[r"acessdate"] = r"accessdate"
    assert (
        tools.rename_template_parameter(r"{{cite | accesdate=2011-01-24 | title=yes }}", Params)
        == r"{{cite | accessdate=2011-01-24 | title=yes }}"
    )
    assert (
        tools.rename_template_parameter(r"{{cite | acessdate=2011-01-24 | title=yes }}", Params)
        == r"{{cite | accessdate=2011-01-24 | title=yes }}"
    )


def test_rename_template_article_text() -> None:
    S = W.for_site(EN)
    correct = r"Now {{bar}} was {{bar|here}} there"
    correct2 = "Now {{bar}} was {{bar\r\n|here\r\n|other}} there"
    correct3 = r"Now {{bar man}} was {{bar man|here}} there"
    correct4 = r"Now {{bar man<!--comm-->}} was {{bar man<!--comm-->|here}} there"
    assert tools.rename_template(r"Now {{foo}} was {{foo|here}} there", r"foo", r"bar") == correct
    assert tools.rename_template(r"Now {{foo}} was {{foo|here}} there", r"Foo", r"bar") == correct
    assert (
        tools.rename_template(r"Now {{foo}} was {{ foo |here}} there", r"foo", r"bar")
        == r"Now {{bar}} was {{ bar |here}} there"
    )
    assert (
        tools.rename_template("Now {{foo}} was {{foo\r\n|here\r\n|other}} there", r"Foo", r"bar")
        == correct2
    )
    assert tools.rename_template(correct, r"bar2", r"foo") == correct
    assert (
        tools.rename_template(r"Now {{foo man}} was {{foo man|here}} there", r"foo man", r"bar man")
        == correct3
    )
    assert (
        tools.rename_template(r"Now {{foo man}} was {{foo man|here}} there", r"Foo man", r"bar man")
        == correct3
    )
    assert (
        tools.rename_template(r"Now {{foo_man}} was {{foo man|here}} there", r"Foo man", r"bar man")
        == correct3
    )
    assert (
        tools.rename_template(
            r"Now {{foo_man<!--comm-->}} was {{foo man<!--comm-->|here}} there",
            r"Foo man",
            r"bar man",
        )
        == correct4
    )
    assert tools.rename_template(correct, r"foo(", r"bar") == correct
    assert tools.rename_template(r"{{foo}} {{foo}}", r"foo", r"bar", 1) == r"{{bar}} {{foo}}", (
        r"count applied correctly"
    )
    assert (
        tools.rename_template(r"{{foo|here1}} {{foo|here2}}", r"foo", r"bar|", 1)
        == r"{{bar||here1}} {{foo|here2}}"
    ), r"rename to add pipe"


def test_rename_template() -> None:
    r = tools.rename_template
    assert r(r"{{foo}}", "bar") == r"{{bar}}"
    assert r(r"{{ foo }}", "bar") == r"{{ bar }}", "space kept"
    assert r(r"{{Foo}}", "bar", False) == r"{{bar}}"
    assert r(r"{{Foo}}", "bar", True) == r"{{Bar}}"
    assert r(r"{{Foo}}", "Bar") == r"{{Bar}}"
    assert r(r"{{Foo}}", "Bar", True) == r"{{Bar}}"
    assert r(r"{{Foo|parameters=adsfjk}}", "bar", False) == r"{{bar|parameters=adsfjk}}"
    assert r(r"{{Foo |parameters=adsfjk}}", "bar", False) == r"{{bar |parameters=adsfjk}}"
    assert r(r"{{foo |parameters=adsfjk}}", "Bar", True) == r"{{bar |parameters=adsfjk}}"
    assert r(r"{{foo man<!--comm-->|here}}", "bar man") == r"{{bar man<!--comm-->|here}}"
    assert r(r"{{foo man <!--comm-->|here}}", "bar man") == r"{{bar man <!--comm-->|here}}"
    assert r("{{foo man <!--comm-->\r\n|here}}", "bar man") == "{{bar man <!--comm-->\r\n|here}}"
    hider = HideText()
    assert (
        hider.add_back(r(hider.hide(r"{{foo man <!--comm-->|here}}"), "bar man"))
        == r"{{bar man <!--comm-->|here}}"
    )
    # special case of subst:, first letter case rule does not apply
    assert r(r"{{PAGENAME}}", "PAGENAME", "subst:PAGENAME") == r"{{subst:PAGENAME}}"
    assert r(r"{{PAGENAME}}", "PAGENAME", "subst:PAGENAME", False) == r"{{subst:PAGENAME}}"
    assert r(r"{{PAGENAME}}", "PAGENAME", "subst:PAGENAME", True) == r"{{subst:PAGENAME}}"


def test_remove_template_parameter_template_name() -> None:
    S = W.for_site(EN)
    correct = r"{{cite web|url=http://www.site.com |title=here |year=2008 }}"
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy }}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 | dateformat =   mdy}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=<!--comm-->mdy}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy<!--comm-->}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=[[200]]-[[288]]}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat = [[200]]-[[288]]}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web<!--foo-->|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}",
            r"cite web",
            r"dateformat",
        )
        == r"{{cite web<!--foo-->|url=http://www.site.com |title=here |year=2008 }}"
    )
    citeweb = r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}"
    assert (
        tools.remove_template_parameter(citeweb + citeweb, r"cite web", r"dateformat")
        == correct + correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}",
            r"Cite web",
            r"dateformat",
        )
        == correct
    )
    assert tools.remove_template_parameter(correct, r"cite web", r"dateformat") == correct
    assert tools.remove_template_parameter(correct, r"cite web", r"yea") == correct
    assert tools.remove_template_parameter(correct, r"cite webs", r"year") == correct
    nochange = r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}"
    assert tools.remove_template_parameter(nochange, r"cite web", r"Dateformat") == nochange


def test_remove_template_parameter_single_template() -> None:
    S = W.for_site(EN)
    correct = r"{{cite web|url=http://www.site.com |title=here |year=2008 }}"
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy }}",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=}}",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 | dateformat =   mdy}}",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}",
            r"dateformat",
            False,
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}",
            r"dateformat",
            True,
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}",
            r"dateformat",
        )
        == correct
    )
    assert tools.remove_template_parameter(correct, r"dateformat") == correct
    assert tools.remove_template_parameter(correct, r"yea") == correct
    nochange = r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}"
    assert tools.remove_template_parameter(nochange, r"Dateformat") == nochange
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 |dateformat=foo}}",
            r"dateformat",
            True,
        )
        == r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}"
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 |dateformat=foo}}",
            r"dateformat",
            False,
        )
        == r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=foo}}"
    )
    assert (
        tools.remove_template_parameter(
            r"{{foo|first=abc|second=def|second=def}}", r"second", False
        )
        == r"{{foo|first=abc|second=def}}"
    )


def test_remove_template_parameters_single_template() -> None:
    S = W.for_site(EN)
    Params = []
    Params.append(r"dateformat")
    correct = r"{{cite web|url=http://www.site.com |title=here |year=2008 }}"
    assert (
        tools.remove_template_parameters(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy}}", Params
        )
        == correct
    )
    assert (
        tools.remove_template_parameters(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=mdy }}", Params
        )
        == correct
    )
    assert (
        tools.remove_template_parameters(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=}}", Params
        )
        == correct
    )
    assert (
        tools.remove_template_parameters(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 | dateformat =   mdy}}",
            Params,
        )
        == correct
    )
    assert (
        tools.remove_template_parameters(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 }}", Params
        )
        == correct
    )
    Params.append(r"format")
    assert (
        tools.remove_template_parameters(
            r"{{cite web|url=http://www.site.com |title=here | dateformat=mdy|year=2008 |format=DOC}}",
            Params,
        )
        == correct
    )


def test_remove_template_parameter_advanced_cases() -> None:
    S = W.for_site(EN)
    correct = r"{{cite web|url=http://www.site.com |title=here |year=2008 }}"
    assert (
        tools.remove_template_parameter(
            "{{cite web|url=http://www.site.com |title=here |year=2008 |\r\ndateformat=mdy}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            "{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat\r\n=mdy}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat=[[Foo|bar]]}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat= now [[Foo|bar]] and [[Foo|bar]] again}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat= {{foo|mdy}} bar}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat= {{foo|mdy}} bar {{here}}}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat= <!--now|--> bar}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |date_format= A<nowiki>|</nowiki>B bar}}",
            r"cite web",
            r"date_format",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |year=2008 |dateformat= [[File:foo.JPG|bar|here]] bar}}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |title=here |dateformat= [[File:foo.JPG|bar|here]] bar|year=2008 }}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |dateformat= <!--now|--> bar|title=here |year=2008 }}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    assert (
        tools.remove_template_parameter(
            r"{{cite web|url=http://www.site.com |dateformat= {{some template|foo={{a}}|bar=b}} bar|title=here |year=2008 }}",
            r"cite web",
            r"dateformat",
        )
        == correct
    )
    correct = r"{{Fred | first=Bar | upper={{Bert|lower=yes}} }}"
    assert (
        tools.rename_template_parameter(
            r"{{Fred | first=Bar | lower={{Bert|lower=yes}} }}", r"lower", r"upper"
        )
        == correct
    ), r"Parameter within nested template not renamed"
    assert (
        tools.rename_template_parameter(
            r"{{Fred | last=Bar | upper={{Bert|lower=yes}} }}", r"last", r"first"
        )
        == correct
    ), r"Template parameters can be rename when nested templates present"
    correct = r"{{Fred | first=Bar | upper={{Bert|lower=yes|2={{great}} }} }}"
    assert (
        tools.rename_template_parameter(
            r"{{Fred | first=Bar | lower={{Bert|lower=yes|2={{great}} }} }}", r"lower", r"upper"
        )
        == correct
    ), r"Parameter within nested nested template not renamed"


def test_remove_duplicate_template_parameters() -> None:
    r = tools.remove_duplicate_template_parameters
    assert r(r"{{foo|first=abc|second=def|second=def}}") == r"{{foo|first=abc|second=def}}"
    assert r(r"{{foo|first=abc|second=def|second = def}}") == r"{{foo|first=abc|second = def}}", (
        "first removed if both the same"
    )
    assert r(r"{{foo|first=abc|second=def|second=}}") == r"{{foo|first=abc|second=def}}", (
        "null dupe param removed"
    )
    assert (
        r("{{foo|first=abc|second=def|second=\r\ndef\r\n}}")
        == "{{foo|first=abc|second=\r\ndef\r\n}}"
    ), "dupe param removed ignoring leading/trailing whitespace"
    assert r(r"{{foo|first=abc|second=|second=def}}") == r"{{foo|first=abc|second=def}}", (
        "null dupe param removed"
    )
    assert (
        r(r"{{foo|first=abc|second=def|second=def|second=def}}") == r"{{foo|first=abc|second=def}}"
    ), "multiple duplicates removed"
    assert (
        r(r"{{foo|first=abc|first=abc|second=def|second=def|second=def}}")
        == r"{{foo|first=abc|second=def}}"
    ), "multiple duplicates removed"
    no_dupe2 = r"{{foo|first=abc|second=def|Second=def}}"
    assert r(no_dupe2) == no_dupe2, "case sensitive parameter name matching"
    assert (
        r(r"{{foo|first=abc|second=dex|second=dex|second=defg}}")
        == r"{{foo|first=abc|second=dex|second=defg}}"
    ), "non-duplicates not removed"
    assert (
        r(r"{{foo|first=abc|second={{def|bar}}|second={{def|bar}}}}")
        == r"{{foo|first=abc|second={{def|bar}}}}"
    )

    params: dict[str, str] = {}
    r(r"{{foo|first=abc|second=def|second=def}}", params)
    assert len(params) == 2
    params.clear()
    r(no_dupe2, params)
    assert len(params) == 3
    params.clear()
    r(r"{{foo|first=abc||second=  def <!--com-->  }}", params)
    assert params.get("second") == "def <!--com-->", (
        "parameter with space and comment retrieved correctly"
    )
    assert (
        r(r"{{foo|first=abc|second2=def|second2=def}}")
        == r"{{foo|first=abc|second2=def|second2=def}}"
    )


def test_remove_duplicate_template_parameters_ur_ls() -> None:
    S = W.for_site(EN)
    withUnescapedPipes = (
        r"{{cite web|foo=bar|url=http://site.com/news/foo|bar=yes|bar=yes|other.stm | date=2010}}"
    )
    assert tools.remove_duplicate_template_parameters(withUnescapedPipes) == withUnescapedPipes, (
        r"no change when URL could be borken"
    )
    assert (
        tools.remove_duplicate_template_parameters(
            r"{{foo|first=abc|url= | url=http://site.com/news }}"
        )
        == r"{{foo|first=abc| url=http://site.com/news }}"
    )
    assert (
        tools.remove_duplicate_template_parameters(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|year=2008}}"
        )
        == r"{{cite web|url=a |title=b | accessdate=11 May 2008|year=2008}}"
    )


def test_duplicate_template_parameters() -> None:
    S = W.for_site(EN)
    Dupes = {}
    assert tools.duplicate_template_parameters(r"{{cite web|url=here |title=there}}") == Dupes
    Dupes[32] = 9
    assert (
        tools.duplicate_template_parameters(r"{{cite web|url=here |title=there|url=here}}") == Dupes
    ), r"dupes if the same"
    assert (
        tools.duplicate_template_parameters(r"{{cite web|url=here |title=there|url=her2}}") == Dupes
    ), r"dupes if not the same"
    Dupes.clear()
    Dupes[36] = 5
    assert (
        tools.duplicate_template_parameters(r"{{cite web|url=here |title=therehere|url=}}") == Dupes
    ), r"dupes if the same"
    Dupes.clear()
    Dupes[32] = 9
    Dupes[41] = 12
    assert (
        tools.duplicate_template_parameters(
            r"{{cite web|url=here |title=there|url=here|title=there}}"
        )
        == Dupes
    ), r"multiple dupes reported"


def test_unknown_template_parameters() -> None:
    S = W.for_site(EN)
    Unknowns = []
    Knowns = list([r"title", r"date", r"url"])
    assert tools.unknown_template_parameters(r"{{cite web|title=a|date=2010}}", Knowns) == Unknowns
    assert tools.unknown_template_parameters(r"{{cite web|TITLE=a|DATE=2010}}", Knowns) == Unknowns
    Unknowns.append(r"foo")
    assert (
        tools.unknown_template_parameters(r"{{cite web|title=a|date=2010|foo=}}", Knowns)
        == Unknowns
    ), r"reported even if blank"
    assert (
        tools.unknown_template_parameters(r"{{cite web|title=a|date=2010|foo=b}}", Knowns)
        == Unknowns
    ), r"unknown parameter reported"
    Unknowns.append(r"bar")
    assert (
        tools.unknown_template_parameters(r"{{cite web|title=a|date=2010|foo=b|bar=}}", Knowns)
        == Unknowns
    ), r"multiple unknowns reported"


def test_remove_excess_template_pipes() -> None:
    S = W.for_site(EN)
    assert (
        tools.remove_excess_template_pipes(r"{{foo||param1=before}}") == r"{{foo|param1=before}}"
    ), r"excess pipe removed"
    assert (
        tools.remove_excess_template_pipes(r"{{foo||param1=before|}}") == r"{{foo|param1=before}}"
    ), r"excess pipes removed"
    assert (
        tools.remove_excess_template_pipes(r"{{foo| |param1=before}}") == r"{{foo|param1=before}}"
    ), r"excess spaced pipe removed"
    assert (
        tools.remove_excess_template_pipes("{{foo|\r\n\t\t|param1=before}}")
        == r"{{foo|param1=before}}"
    ), r"space is newline"
    assert (
        tools.remove_excess_template_pipes(r"{{foo|     |param1=before}}")
        == r"{{foo|param1=before}}"
    )
    assert (
        tools.remove_excess_template_pipes(r"{{foo||param1=before||param2=b}}")
        == r"{{foo|param1=before|param2=b}}"
    ), r"mulitple excess pipes"
    assert (
        tools.remove_excess_template_pipes(r"{{foo||param1=before|}}") == r"{{foo|param1=before}}"
    ), r"excess pipe at end"
    nested = r"{{foo| one={{bar|a||c}}|two=x}}"
    assert tools.remove_excess_template_pipes(nested) == nested, (
        r"pipes within nested templates not changed"
    )


def test_update_template_parameter_value() -> None:
    S = W.for_site(EN)
    assert (
        tools.update_template_parameter_value(r"{{foo|param1=before}}", r"param1", r"valueafter")
        == r"{{foo|param1=valueafter}}"
    )
    assert (
        tools.update_template_parameter_value(r"{{foo|param1= before }}", r"param1", r"valueafter")
        == r"{{foo|param1= valueafter }}"
    ), r"whitespace kept"
    assert (
        tools.update_template_parameter_value("{{foo|param1=\r\nbefore}}", r"param1", r"valueafter")
        == "{{foo|param1=\r\nvalueafter}}"
    ), r"newline before populated parameter kept"
    assert (
        tools.update_template_parameter_value(
            "{{foo\r\n|param1=before\r\n|param2=okay}}", r"param1", r"valueafter"
        )
        == "{{foo\r\n|param1=valueafter\r\n|param2=okay}}"
    ), r"existing newline kept"
    assert (
        tools.update_template_parameter_value(
            "{{foo\r\n|param1= before\r\n|param2=okay}}", r"param1", r"valueafter"
        )
        == "{{foo\r\n|param1= valueafter\r\n|param2=okay}}"
    ), r"existing newline & whitespace kept"
    assert (
        tools.update_template_parameter_value(
            r"{{foo|param1<!--comm-->= before }}", r"param1", r"valueafter"
        )
        == r"{{foo|param1<!--comm-->= valueafter }}"
    )
    assert (
        tools.update_template_parameter_value(
            r"{{foo|<!--comm-->param1= before }}", r"param1", r"valueafter"
        )
        == r"{{foo|<!--comm-->param1= valueafter }}"
    )
    assert (
        tools.update_template_parameter_value(
            r"{{foo|param1=[[1891]]-[[1892]]}}", r"param1", r"[[1891]]–[[1892]]"
        )
        == r"{{foo|param1=[[1891]]–[[1892]]}}"
    )
    assert (
        tools.update_template_parameter_value(
            r"{{foo|param1= [[1891]]-[[1892]] }}", r"param1", r"[[1891]]–[[1892]]"
        )
        == r"{{foo|param1= [[1891]]–[[1892]] }}"
    )
    assert (
        tools.update_template_parameter_value(
            r"{{foo|param1=before|param2=before}}", r"param1", r"valueafter"
        )
        == r"{{foo|param1=valueafter|param2=before}}"
    )
    assert (
        tools.update_template_parameter_value(
            r"{{foo|param1=before<!--comm-->|param2=before}}", r"param1", r"valueafter<!--comm-->"
        )
        == r"{{foo|param1=valueafter<!--comm-->|param2=before}}"
    )
    assert (
        tools.update_template_parameter_value(
            r"{{foo|param1=<!--comm-->before|param2=before}}", r"param1", r"<!--comm-->valueafter"
        )
        == r"{{foo|param1=<!--comm-->valueafter|param2=before}}"
    )
    assert (
        tools.update_template_parameter_value(r"{{foo|param1=before}}", r"param2", r"valueafter")
        == r"{{foo|param1=before}}"
    )
    assert (
        tools.update_template_parameter_value(r"{{foo|param1=}}", r"param1", r"valueafter")
        == r"{{foo|param1=valueafter}}"
    )
    input = "{{cite news\r\n|author=\r\n|title=Obituary 1 -- No Title\r\n|date=\r\n|work=[[New York Times]]\r\n|url=http://query.nytimes.com/gst/abstra\r\n|accessdate=2008-08-08\r\n}}"
    assert tools.update_template_parameter_value(input, r"date", r"April 4, 1922") == input.replace(
        r"|date=", r"|date=April 4, 1922"
    )
    input = "{{cite news\r\n|author=\r\n|title=Obituary 1 -- No Title\r\n|date=\r\n\r\n\r\n|work=[[New York Times]]\r\n|url=http://query.nytimes.com/gst/abstra }}"
    assert tools.update_template_parameter_value(input, r"date", r"April 4, 1922") == input.replace(
        r"|date=", r"|date=April 4, 1922"
    )


def test_add_template_parameter_value() -> None:
    S = W.for_site(EN)
    assert (
        tools.add_template_parameter_value(
            r"{{foo|param1=oldvalue}}", r"param1", r"newvalue", False
        )
        == r"{{foo|param1=oldvalue}}"
    )
    assert (
        tools.add_template_parameter_value(r"{{foo}}", r"param1", r"newvalue", False)
        == r"{{foo | param1=newvalue}}"
    )
    assert (
        tools.add_template_parameter_value(r"{{foo}}", r"param1", r"newvalue", True)
        == r"{{foo | param1= newvalue}}"
    )


def test_set_template_parameter_value() -> None:
    S = W.for_site(EN)
    assert (
        tools.set_template_parameter_value(r"{{foo|param1=before}}", r"param1", r"valueafter")
        == r"{{foo|param1=valueafter}}"
    )
    assert (
        tools.set_template_parameter_value(r"{{foo|param1= before }}", r"param1", r"valueafter")
        == r"{{foo|param1= valueafter }}"
    )
    assert (
        tools.set_template_parameter_value(r"{{foo|param1=before}}", r"param1", r"valueafter", True)
        == r"{{foo|param1= valueafter}}"
    )
    assert (
        tools.set_template_parameter_value(
            r"{{foo|param1=before}}", r"param1", r"valueafter", False
        )
        == r"{{foo|param1=valueafter}}"
    )
    assert (
        tools.set_template_parameter_value(
            r"{{foo|param1=before|param2=before}}", r"param1", r"valueafter"
        )
        == r"{{foo|param1=valueafter|param2=before}}"
    )
    assert (
        tools.set_template_parameter_value(r"{{foo|param1=before}}", r"param2", r"valueafter")
        == r"{{foo|param1=before | param2=valueafter}}"
    )
    assert (
        tools.set_template_parameter_value(
            r"{{foo|param1=before|param3=a}}", r"param2", r"valueafter"
        )
        == r"{{foo|param1=before|param3=a | param2=valueafter}}"
    )
    assert (
        tools.set_template_parameter_value(
            r"{{foo|param1=w|param2=x|param3=y|param4=z}}", r"param5", r"a"
        )
        == r"{{foo|param1=w|param2=x|param3=y|param4=z|param5=a}}"
    )
    assert (
        tools.set_template_parameter_value(
            r"{{foo| param1=w | param2=x | param3=y | param4=z }}", r"param5", r"a"
        )
        == r"{{foo| param1=w | param2=x | param3=y | param4=z | param5=a }}"
    ), r"retain template call end space"
    assert (
        tools.set_template_parameter_value(r"{{foo|param1=}}", r"param1", r"valueafter")
        == r"{{foo|param1=valueafter}}"
    )
    bug1 = "{{Infobox college coach|\r\n| Name          = Bill\r\n| CurrentRecord = 202–43 ({{Winning percentage|202|43}})\r\n| OverallRecord = 409-148 ({{Winning percentage|409|148}})\r\n| Player        = *\r\n| CollegeHOFID  =\r\n| BBallHOF      =\r\n}}}"
    assert tools.set_template_parameter_value(
        bug1, r"OverallRecord", r"409–148 ({{Winning percentage|409|148}})"
    ) == bug1.replace(r"409-148 ({{Winning percentage", r"409–148 ({{Winning percentage")
    input = "{{cite news\r\n|author=\r\n|title=Obituary 1 -- No Title\r\n|date=\r\n|work=[[New York Times]]\r\n|url=http://query.nytimes.com/gst/abstra\r\n|accessdate=2008-08-08\r\n}}"
    assert tools.set_template_parameter_value(input, r"date", r"April 4, 1922") == input.replace(
        r"|date=", r"|date=April 4, 1922"
    )
    assert (
        tools.set_template_parameter_value(r"{{foo|param1=valueafter}}", r"param1", r"valueafter")
        == r"{{foo|param1=valueafter}}"
    )


def test_nested_template_regex_single_word() -> None:
    foo = tools.nested_template_regex("foo")
    assert foo.match(r"{{  foo}}").group(1) == r"{{  "
    assert foo.match(r"{{foo}}").group(2) == r"foo"
    assert foo.match(r"{{ Foo}}").group(2) == r"Foo"
    assert foo.match(r"{{ Foo|title=abc}}").group(3) == r"|title=abc}}"
    for t in [
        "{{foo}}",
        "{{___foo___}}",
        "{{Foo}}",
        "{{ foo}}",
        "{{ foo|}}",
        "{{foo|title=abc}}",
        "{{foo|\r\ntitle=abc\r\n|other=yes}}",
        "{{foo\r\n|title=abc\r\n|other=yes}}",
        "{{foo<!--comm-->|title=abc}}",
        "{{foo <!--comm--> |title=abc}}",
        "{{foo ⌊⌊⌊⌊0⌋⌋⌋⌋ |title=abc}}",
        "{{\r\nfoo<!--comm-->|title=abc\r\n}}",
        "{{foo|title={{abc}}}}",
        "{{foo|title={{abc}}|last=Fred}}",
        "{{foo|\r\ntitle={{abc|fdkjdsfjk=fdaskjlfds\r\n|fdof=affdsa}}\r\n|last=Fred}}",
        "{{foo|title={abc} def|last=Fred}}",
    ]:
        assert foo.is_match(t), t
    for t in ["{{foo|title={abc def|last=Fred}}", "{{foobar}}", "{{foo", "{{foo}", "{foo}"]:
        assert not foo.is_match(t), t
    foo = tools.nested_template_regex("Foo")
    for t in (
        r"{{foo}}",
        r"{{Foo}}",
        r"{{ foo}}",
        r"{{Template:foo}}",
        r"{{:Template:foo}}",
        r"{{:Msg:foo}}",
        r"{{Msg:foo}}",
        r"{{_:_Template_:_foo_}}",
    ):
        assert foo.is_match(t), t
    assert not foo.is_match(r"{{Template foo}}")
    foo = tools.nested_template_regex("foo")
    assert foo.match(r"{{  foo}}").group(1) == r"{{  "
    # AWB returns null for an empty name; AWB-L raises.
    with pytest.raises(ValueError):
        tools.nested_template_regex("")
    # A wiki without a Template namespace entry falls back to "[Tt]emplate:".
    from dataclasses import replace

    from awb_l.core.site import current_site

    # AWB removes Template from Variables.NamespacesCaseInsensitive only; build the regex
    # directly for a site without it, since SiteRegexes needs the namespace.
    namespaces = {k: v for k, v in current_site().namespaces.items() if k != Namespace.TEMPLATE}
    no_template_ns = replace(current_site(), namespaces=namespaces)
    assert tools.nested_template_regex("Foo", no_template_ns).is_match(r"{{Template:foo}}")


def test_nested_template_regex_rtl() -> None:
    S = W.for_site(EN)
    ArTemplate = tools.nested_template_regex(r"وصلات قليلة")
    assert ArTemplate.is_match(r"{{وصلات قليلة|تاريخ=ديسمبر 2012}}")
    assert len(ArTemplate.replace(r"{{وصلات قليلة|تاريخ=ديسمبر 2012}}", r"")) == 0
    assert len(ArTemplate.replace(r"{{وصلات قليلة|تاريخ=يناير_2009}}", r"")) == 0


def test_nested_template_regex_two_words() -> None:
    S = W.for_site(EN)
    FooTemplate2 = tools.nested_template_regex(r"foo bar")
    assert FooTemplate2.is_match(r"{{foo bar}}")
    assert FooTemplate2.is_match(r"{{foo_bar}}")
    assert FooTemplate2.is_match(r"{{foo_____bar}}")
    assert FooTemplate2.is_match(r"{{Foo bar}}")
    assert FooTemplate2.is_match(r"{{Foo      bar}}")
    assert not (FooTemplate2.is_match(r"{{foo}}"))
    assert not (FooTemplate2.is_match(r"{{foo b_ar}}"))
    assert not (tools.nested_template_regex(r"birth date").is_match(r"{{birth-date|May 11, 1980}}"))
    nonbreakingspace = r" "
    assert FooTemplate2.is_match(r"{{Foo" + nonbreakingspace + r"bar}}")
    assert DotNetRegex(r"\u00a0").is_match(r"{{Foo" + nonbreakingspace + r"bar}}")
    nonbreakingspace = r"　"
    assert FooTemplate2.is_match(r"{{Foo" + nonbreakingspace + r"bar}}")
    assert DotNetRegex(r"\u3000").is_match(r"{{Foo" + nonbreakingspace + r"bar}}")


def test_nested_template_regex_limits() -> None:
    S = W.for_site(EN)
    # AWB returns null for an empty name; AWB-L raises, so callers never get an unexpected None.
    with pytest.raises(ValueError):
        tools.nested_template_regex(r"")


def test_nested_template_regex_list_single() -> None:
    S = W.for_site(EN)
    ListOfTemplates = []
    # AWB returns null for an empty list; AWB-L raises (see test_nested_template_regex_limits).
    with pytest.raises(ValueError):
        tools.nested_template_regex(ListOfTemplates)
    ListOfTemplates.append(r"Foo")
    multipleTemplates = tools.nested_template_regex(ListOfTemplates)
    assert multipleTemplates.match(r"{{foo}}").group(2) == r"foo", r"Group 2 is template name"
    assert multipleTemplates.match(r"{{ Foo}}").group(2) == r"Foo", r"Group 2 is template name"
    assert multipleTemplates.match(r"{{ Foo|bar}}").group(3) == r"|bar}}", (
        r"Group 3 is template from bar to end"
    )
    assert (
        multipleTemplates.match(r"{{ Foo|bar=one|he=there}}").group(3) == r"|bar=one|he=there}}"
    ), r"Group 3 is template from bar to end"
    assert (
        multipleTemplates.match(r"{{ Foo|bar={{one}}|he=there}}").group(3)
        == r"|bar={{one}}|he=there}}"
    ), r"Group 3 is template from bar to end"
    assert (
        multipleTemplates.match(r"{{ Foo|bar={{one}}|he=ther {{e}}}}").group(3)
        == r"|bar={{one}}|he=ther {{e}}}}"
    ), r"Group 3 is template from bar to end"
    assert (
        multipleTemplates.match(r"{{ Foo|bar={{one}}|he=there}}").group(4)
        == r"|bar={{one}}|he=there"
    ), r"Group 4 is template from bar to end excluding end }}"
    assert (
        multipleTemplates.match(r"{{ Foo|bar={{one}}|he=ther {{e}}}}").group(4)
        == r"|bar={{one}}|he=ther {{e}}"
    ), r"Group 4 is template from bar to end excluding end }}"
    assert multipleTemplates.is_match(r"{{foo}}")
    assert multipleTemplates.is_match(r"{{Foo}}")
    assert multipleTemplates.is_match(r"{{ foo}}")
    assert multipleTemplates.is_match(r"{{ foo|}}")
    assert multipleTemplates.is_match(r"{{foo|title=abc}}")
    assert multipleTemplates.is_match("{{foo|\r\ntitle=abc\r\n|other=yes}}")
    assert multipleTemplates.is_match("{{foo\r\n|title=abc\r\n|other=yes}}")
    assert multipleTemplates.is_match(r"{{foo<!--comm-->|title=abc}}")
    assert multipleTemplates.is_match(r"{{foo <!--comm--> |title=abc}}")
    assert multipleTemplates.is_match("{{\r\nfoo<!--comm-->|title=abc\r\n}}")
    assert multipleTemplates.is_match(r"{{foo|title={{abc}}}}")
    assert multipleTemplates.is_match(r"{{foo|title={{abc}}|last=Fred}}")
    assert not (multipleTemplates.is_match(r"{{a}}"))
    assert not (multipleTemplates.is_match(r""))
    ListOfTemplates.clear()
    ListOfTemplates.append(r"Foo ")
    multipleTemplates = tools.nested_template_regex(ListOfTemplates)
    assert multipleTemplates.match(r"{{foo}}").group(2) == r"foo", (
        r"matches correctly from input template name with trailing whitespace"
    )


def test_nested_template_regex_list_multiple() -> None:
    S = W.for_site(EN)
    listOfTemplates = list([r"Foo", r"bar"])
    multipleTemplates = tools.nested_template_regex(listOfTemplates)
    assert multipleTemplates.match(r"{{foo}}").group(2) == r"foo"
    assert multipleTemplates.match(r"{{Template:foo}}").group(2) == r"foo"
    assert multipleTemplates.match(r"{{ template :foo}}").group(2) == r"foo"
    assert multipleTemplates.match(r"{{ Foo}}").group(2) == r"Foo"
    assert multipleTemplates.match(r"{{Bar |akjldasf=a}}").group(2) == r"Bar"
    assert multipleTemplates.match("{{bar\r\n}}").group(2) == r"bar"
    assert multipleTemplates.match(r"{{ foo}}").group(1) == r"{{ "
    assert multipleTemplates.match(r"{{ foo |akjldasf=a}}").group(3) == r" |akjldasf=a}}"
    assert multipleTemplates.is_match(r"{{foo}}")
    assert multipleTemplates.is_match(r"{{Foo}}")
    assert multipleTemplates.is_match(r"{{ foo}}")
    assert multipleTemplates.is_match(r"{{ foo|}}")
    assert multipleTemplates.is_match(r"{{foo|title=abc}}")
    assert multipleTemplates.is_match("{{foo|\r\ntitle=abc\r\n|other=yes}}")
    assert multipleTemplates.is_match("{{foo\r\n|title=abc\r\n|other=yes}}")
    assert multipleTemplates.is_match(r"{{foo<!--comm-->|title=abc}}")
    assert multipleTemplates.is_match(r"{{foo <!--comm--> |title=abc}}")
    assert multipleTemplates.is_match("{{\r\nfoo<!--comm-->|title=abc\r\n}}")
    assert multipleTemplates.is_match(r"{{foo|title={{abc}}}}")
    assert multipleTemplates.is_match(r"{{foo|title={{abc}}|last=Fred}}")
    assert multipleTemplates.is_match(r"{{bar}}")
    assert multipleTemplates.is_match(r"{{ bar}}")
    assert multipleTemplates.is_match(r"{{Bar}}")
    assert not (multipleTemplates.is_match(r"{{a}}"))
    assert not (multipleTemplates.is_match(r""))


def test_merge_template_parameters_template_name() -> None:
    S = W.for_site(EN)
    correct = r"{{Foo | e=b d }}"
    ToMerge = list([r"a", r"c"])
    assert (
        tools.merge_template_parameters_values(r"{{Foo|a= b|c= d}}", ToMerge, r"e", True) == correct
    ), r"single spaces"
    assert (
        tools.merge_template_parameters_values(r"{{Foo|a=b|c=d}}", ToMerge, r"e", True) == correct
    ), r"no spaces"
    assert (
        tools.merge_template_parameters_values(r"{{Foo|a=   b|c=d}}", ToMerge, r"e", True)
        == correct
    ), r"big spaces"


def test_get_meta_content_value() -> None:
    S = W.for_site(EN)
    assert (
        tools.get_meta_content_value(r'<meta name="PubDate"  content="2009-03-02">', r"PubDate")
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(r"<meta name='PubDate'  content='2009-03-02'>", r"PubDate")
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(
            r'< META NAME = "PubDate"  content = "2009-03-02"  />', r"PubDate"
        )
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(
            r'< meta itemprop = "PubDate"  content = "2009-03-02"  />', r"PubDate"
        )
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(r'<meta name  ="PubDate" CONTENT=" 2009-03-02 ">', r"PUBDATE")
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(
            r'<meta name  ="PubDate" scheme="URI" CONTENT=" 2009-03-02 ">', r"PUBDATE"
        )
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(
            r'<meta property  ="PubDate" scheme="URI" CONTENT=" 2009-03-02 ">', r"PUBDATE"
        )
        == r"2009-03-02"
    )
    assert (
        tools.get_meta_content_value(
            r'<meta property="og:title" content="Football: Ken P is headed to X" data-meta-updatable/>',
            r"og:title",
        )
        == r"Football: Ken P is headed to X"
    )
    assert (
        len(
            tools.get_meta_content_value(
                r'<meta name  ="PubDate" CONTENT=" 2009-03-02 ">', r"PUBDATEXX"
            )
        )
        == 0
    )
    assert (
        len(
            tools.get_meta_content_value(
                r'<meta name  ="PubDateX" CONTENT=" 2009-03-02 ">', r"PUBDATE"
            )
        )
        == 0
    )
    assert (
        len(tools.get_meta_content_value(r'<meta name  ="PubDateX" CONTENT=" 2009-03-02 ">', r""))
        == 0
    )
    assert len(tools.get_meta_content_value(r"", r"PUBDATE")) == 0
    assert (
        tools.get_meta_content_value(
            r'<meta xmlns="http://www.w3.org/1999/xhtml" name="citation_doi" content="10.1111/j.1096-0031.2009.00267.x" />',
            r"citation_doi",
        )
        == r"10.1111/j.1096-0031.2009.00267.x"
    )
    assert (
        tools.get_meta_content_value(
            r'<meta content="10.1093/nar/27.19.3821" name="DC.Identifier" />', r"DC.Identifier"
        )
        == r"10.1093/nar/27.19.3821"
    )
    assert (
        tools.get_meta_content_value(
            r'<meta content="10.1101/gr.7.4.359" name="DC.Identifier" />', r"DC.Identifier"
        )
        == r"10.1101/gr.7.4.359"
    )
    assert (
        tools.get_meta_content_value(
            '<meta id="og_title" property="og:title" content="Air wasn\'t x"/>', r"og:title"
        )
        == r"Air wasn't x"
    )
    assert (
        tools.get_meta_content_value(
            '<meta property="og:title" content="Air wasn\'t x">', r"og:title"
        )
        == r"Air wasn't x"
    )
    assert (
        tools.get_meta_content_value(
            '<meta data-ephemeral="true" property="og:title" content="Air wasn\'t x"/>', r"og:title"
        )
        == r"Air wasn't x"
    )
    assert (
        tools.get_meta_content_value(
            '<meta data-react-helmet="true" property="og:title" content="Air wasn\'t x"/>',
            r"og:title",
        )
        == r"Air wasn't x"
    )
    assert (
        tools.get_meta_content_value(
            '<meta ng-attr-content="{{meta.title}}" property="og:title" content="Air wasn\'t x"/>',
            r"og:title",
        )
        == r"Air wasn't x"
    )


def test_unescape_xml() -> None:
    S = W.for_site(EN)
    assert tools.unescape_xml(r"<tag>value</tag>") == r"<tag>value</tag>"
    assert len(tools.unescape_xml(r"")) == 0
    assert tools.unescape_xml(r"<tag>A&amp;B</tag>") == r"<tag>A&B</tag>"


def test_get_template_name() -> None:
    g = tools.get_template_name
    assert g(r"{{Start date and age|1833|7|11}}") == "Start date and age"
    assert g(r"{{ Start date and age |1833|7|11}}") == "Start date and age"
    assert g("{{\r\nStart date and age\r\n|1833|7|11}}") == "Start date and age"
    assert g(r"{{start date and age <!--comm--> |1833|7|11}}") == "start date and age", (
        "handles embedded comments"
    )
    assert g(r"{{start date and age <!--comm-->}}") == "start date and age", (
        "handles embedded comments"
    )
    assert g(r"{{start date and age ⌊⌊⌊⌊1⌋⌋⌋⌋}}") == "start date and age", (
        "handles embedded comments (hidetext)"
    )
    assert g(r"{{Start date and age|1833|7|") == "Start date and age", "works on part templates"
    assert g(r"{{Template:Foo|1=yes}}") == "Foo", "Template namespace removed"
    assert g(r"{{ Template : Foo |1=yes}}") == "Foo", "Template namespace removed"
    assert g(r"{{template:Foo|1=yes}}") == "Foo", "Template namespace removed"
    assert g(r"{{Foo_one|1=yes}}") == "Foo one", "underscore cleaned"
    assert g(r"{{_Foo_one|1=yes}}") == "Foo one", "Leading underscore cleaned"
    assert g(r"{{Foo___one|1=yes}}") == "Foo one", "underscores cleaned"
    assert g(r"{{Foo   one|1=yes}}") == "Foo one", "underscores cleaned"
    assert g("{{Foo\u00a0one|1=yes}}") == "Foo one", "Unicode non-breaking spaces cleaned"
    assert g(r"{{DISPLAYTITLE:11}}") == "DISPLAYTITLE"
    assert g(r"{{DISPLAYTITLE:}}") == "DISPLAYTITLE"
    assert g("") == ""
    # AWB removes Template from NamespacesCaseInsensitive; check the fallback regex directly.
    from dataclasses import replace

    from awb_l.core.site import current_site

    namespaces = {k: v for k, v in current_site().namespaces.items() if k != Namespace.TEMPLATE}
    no_template_ns = replace(current_site(), namespaces=namespaces)
    assert tools.template_name_regex(no_template_ns).match("").group(1) == ""


def test_re_add_diacritics() -> None:
    S = W.for_site(EN)
    assert tools.re_add_diacritics(r"Floué, John", r"Floue, John") == r"Floué, John", (
        r"diacritics reapplied"
    )
    assert tools.re_add_diacritics(r"Floué", r"Floue") == r"Floué", r"diacritics reapplied"
    assert tools.re_add_diacritics(r" Floué, John ", r"Floue, John") == r"Floué, John", (
        r"diacritics reapplied"
    )
    assert tools.re_add_diacritics(r" Floué, John ", r" Floue, John ") == r" Floué, John ", (
        r"diacritics reapplied"
    )
    assert tools.re_add_diacritics(r"John Floué", r"Floue, John") == r"Floué, John", (
        r"diacritics reapplied, word order irrelevant"
    )
    assert tools.re_add_diacritics(r"John von Floué", r"Floue, John") == r"Floué, John", (
        r"diacritics reapplied, word order irrelevant"
    )
    assert tools.re_add_diacritics(r"Greatère, Véry", r"Greatere, Very") == r"Greatère, Véry", (
        r"multiple words changed"
    )
    assert tools.re_add_diacritics(r"Véry Greatère", r"Greatere, Very") == r"Greatère, Véry", (
        r"multiple words changed"
    )
    assert (
        tools.re_add_diacritics(r"Véry Greatère", r"Greatere, Very der Very")
        == r"Greatère, Very der Very"
    ), r"when multiple matches for same word without, that word not changed"
    assert (
        tools.re_add_diacritics(r"Véry de Vèry Greatère", r"Greatere, Very der Very")
        == r"Greatère, Very der Very"
    ), r"when multiple matches for same word without, that word not changed"


def test_is_ip() -> None:
    S = W.for_site(EN)
    assert tools.is_ip(r"192.168.0.1")
    assert tools.is_ip(r"8.8.8.8")
    assert not (tools.is_ip(r"www.google.com"))


@pytest.mark.skip(reason=".NET ServicePointManager settings; HTTP is configured in awb_l.api")
def test_service_point_config() -> None:
    pass


def test_build_post_data_string() -> None:
    nvc = {"param1": "value1"}
    assert tools.build_post_data_string(nvc) == "param1=value1"
    nvc["param2"] = "value2"
    assert tools.build_post_data_string(nvc) == "param1=value1&param2=value2"
    nvc["param3"] = "A B C"
    assert tools.build_post_data_string(nvc) == "param1=value1&param2=value2&param3=A+B+C"


@pytest.mark.skip(reason="browser launching is UI code (awb_l.ui), not part of core")
def test_open_in_b_rowser() -> None:
    pass


def test_template_to_magic_word() -> None:
    S = W.for_site(EN)
    assert tools.template_to_magic_word(r"{{DEFAULTSORT|Foo}}") == r"{{DEFAULTSORT:Foo}}"
    assert tools.template_to_magic_word(r"{{DISPLAYTITLE|Foo}}") == r"{{DISPLAYTITLE:Foo}}"
    assert tools.template_to_magic_word(r"{{Displaytitle|Foo}}") == r"{{DISPLAYTITLE:Foo}}"
    assert tools.template_to_magic_word(r"{{FULLPAGENAME|Foo}}") == r"{{FULLPAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{Fullpagename|Foo}}") == r"{{FULLPAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{Namespace|Foo}}") == r"{{namespace:Foo}}"
    assert tools.template_to_magic_word(r"{{Numberofarticles|Foo}}") == r"{{numberofarticles:Foo}}"
    assert tools.template_to_magic_word(r"{{PAGENAME|Foo}}") == r"{{PAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{PAGESIZE|Foo}}") == r"{{PAGESIZE:Foo}}"
    assert tools.template_to_magic_word(r"{{PROTECTIONLEVEL|Foo}}") == r"{{PROTECTIONLEVEL:Foo}}"
    assert tools.template_to_magic_word(r"{{Pagename|Foo}}") == r"{{PAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{pagename|Foo}}") == r"{{PAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{SUBPAGENAME|Foo}}") == r"{{SUBPAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{Subpagename|Foo}}") == r"{{SUBPAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{padleft|Foo}}") == r"{{padleft:Foo}}"
    assert tools.template_to_magic_word(r"{{ DEFAULTSORT |Foo}}") == r"{{DEFAULTSORT:Foo}}"
    assert tools.template_to_magic_word(r"{{DISPLAYTITLE|''Foo''}}") == r"{{DISPLAYTITLE:''Foo''}}"
    assert (
        tools.template_to_magic_word(r"{{DISPLAYTITLE|''Foo''}} {{DEFAULTSORT|Foo}}")
        == r"{{DISPLAYTITLE:''Foo''}} {{DEFAULTSORT:Foo}}"
    )
    assert tools.template_to_magic_word(r"{{BASEPAGENAME|Foo}}") == r"{{BASEPAGENAME:Foo}}"
    assert tools.template_to_magic_word(r"{{FULLPAGENAME}}") == r"{{FULLPAGENAME}}"


def test_is_section_or_reason_template() -> None:
    S = W.for_site(EN)
    assert tools.is_section_or_reason_template(r"{{wikify|reason=foo}}")
    assert tools.is_section_or_reason_template(r"{{wikify|date=May 2012|reason=foo}}")
    assert tools.is_section_or_reason_template(r"{{wikify|section|date=May 2012}}")
    assert tools.is_section_or_reason_template(r"{{wikify|section|date=May 2012}}", r"")
    assert tools.is_section_or_reason_template(
        r"{{foo}}", r"{{multiple issues|section=y|POV=May 2012}}"
    )
    assert not (tools.is_section_or_reason_template(r"{{abc|param1=foo}}"))
    assert not (tools.is_section_or_reason_template(r"{{abc|section=foo}}"))
    assert not (tools.is_section_or_reason_template(r"{{abc}}"))


def test_how_much_starts_with_tests() -> None:
    S = W.for_site(EN)
    assert (
        tools.how_much_starts_with("{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), False)
        == 9
    )
    assert (
        tools.how_much_starts_with("{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), True)
        == 9
    )
    assert (
        tools.how_much_starts_with(
            "{{foo}}\r\nhello {{foo}}", tools.nested_template_regex(r"foo"), False
        )
        == 9
    )
    assert (
        tools.how_much_starts_with(" {{foo}}\r\nhello", tools.nested_template_regex(r"foo"), False)
        == 10
    )
    assert (
        tools.how_much_starts_with(
            "hello{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), False
        )
        == 0
    )
    assert (
        tools.how_much_starts_with(
            "==hello==\r\n{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), False
        )
        == 0
    )
    assert (
        tools.how_much_starts_with(
            "hello{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), True
        )
        == 0
    )
    assert (
        tools.how_much_starts_with(
            "{{foo}}\r\n{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), False
        )
        == 18
    )
    assert (
        tools.how_much_starts_with(
            "{{foo}}\r\n{{foo|bar}}\r\nhello", tools.nested_template_regex(r"foo"), False
        )
        == 22
    )
    assert (
        tools.how_much_starts_with(
            "==hello==\r\n{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), True
        )
        == 20
    )
    assert (
        tools.how_much_starts_with(
            "===hello===\r\n{{foo}}\r\nhello", tools.nested_template_regex(r"foo"), True
        )
        == 22
    )
    assert (
        tools.how_much_starts_with(
            "{{foo}}\r\nhello {{foo}}\r\n==hi==\r\ntext", tools.nested_template_regex(r"foo"), False
        )
        == 9
    )
    assert (
        tools.how_much_starts_with(
            "{{foo}}\r\nhello {{foo}}\r\n==hi==\r\ntext", tools.nested_template_regex(r"foo"), True
        )
        == 9
    )
    assert (
        tools.how_much_starts_with(
            "===hello===\r\nhello", tools.nested_template_regex(r"foo"), True
        )
        == 0
    )


def test_pipe_cleaned_template() -> None:
    S = W.for_site(EN)
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A}}", True)
        == r"{{cite journal|title=A}}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A <!-- a --> }}", True)
        == r"{{cite journal|title=A ~~~~~~~~~~ }}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A [[here|there]] }}", True)
        == r"{{cite journal|title=A ############## }}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A [[here]] }}", True)
        == r"{{cite journal|title=A ######## }}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A {{here}} }}", True)
        == r"{{cite journal|title=A ######## }}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A <pre>a</pre> }}", True)
        == r"{{cite journal|title=A ############ }}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A <code>a</code> }}", True)
        == r"{{cite journal|title=A ############## }}"
    )
    assert (
        tools.pipe_cleaned_template(r"{{cite journal|title=A <ref>a</ref> }}", True)
        == r"{{cite journal|title=A ############ }}"
    )


def test_unformatted_text_not_changed() -> None:
    S = W.for_site(EN)
    assert tools.unformatted_text_not_changed(r"", r"")
    assert tools.unformatted_text_not_changed(r"A", r"A")
    assert tools.unformatted_text_not_changed(r"<nowiki>A</nowiki>", r"<nowiki>A</nowiki>")
    assert tools.unformatted_text_not_changed(
        r"<nowiki>A</nowiki> <nowiki>B</nowiki>", r"<nowiki>A</nowiki> <nowiki>B</nowiki>"
    )
    assert tools.unformatted_text_not_changed(
        r"<nowiki>A</nowiki> <nowiki>B</nowiki>", r"<nowiki>A</nowiki>"
    ), r"Unformatted text entirely removed, true"
    assert tools.unformatted_text_not_changed(r"<nowiki>A</nowiki>", r""), (
        r"Unformatted text entirely removed, true"
    )
    assert not (
        tools.unformatted_text_not_changed(
            r"<nowiki>A</nowiki> <nowiki>B</nowiki>", r"<nowiki>C</nowiki>"
        )
    )
    assert not (tools.unformatted_text_not_changed(r"<nowiki>A</nowiki>", r"<nowiki></nowiki>"))
    assert not (tools.unformatted_text_not_changed(r"<nowiki>A</nowiki>", r"<nowiki>B</nowiki>")), (
        r"Unformatted text changed removed, false"
    )
    assert not (tools.unformatted_text_not_changed(r"<nowiki>A</nowiki>", r"<nowiki></nowiki>B")), (
        r"Unformatted text changed (no content) removed, false"
    )


def test_get_md5_sum() -> None:
    S = W.for_site(EN)
    assert tools.get_md5_sum(r"hello") == r"5d41402abc4b2a76b9719d911017c592"


def test_sort_dictionary_pairs() -> None:
    S = W.for_site(EN)
    assert tools.sort_dictionary_pairs(
        {r"InfoA": r"foo", r"InfoB": r"Bar", r"InfoC": r"Baz"}, [r"InfoC", r"InfoA", r"InfoB"]
    ) == {r"InfoC": r"Baz", r"InfoA": r"foo", r"InfoB": r"Bar"}
    assert tools.sort_dictionary_pairs(
        {r"InfoA": r"foo", r"InfoB": r"Bar", r"InfoC": r"Baz", r"InfoZ": r"Zed", r"InfoY": r"Why"},
        [r"InfoC", r"InfoA", r"InfoB"],
    ) == {r"InfoC": r"Baz", r"InfoA": r"foo", r"InfoB": r"Bar", r"InfoZ": r"Zed", r"InfoY": r"Why"}


def test_sort_template_call_parameters() -> None:
    S = W.for_site(EN)
    assert (
        tools.sort_template_call_parameters(
            "{{MyTemplate\r\n| InfoA = foo\r\n| InfoB = Bar\r\n| InfoC = Baz\r\n}}",
            [r"InfoC", r"InfoA", r"InfoB"],
        )
        == "{{MyTemplate | InfoC=Baz | InfoA=foo | InfoB=Bar\r\n}}"
    )


def test_make_human_cat_key_one_word_names() -> None:
    assert tools.make_human_cat_key("OneWordName", "") == "OneWordName"
    assert tools.make_human_cat_key("ONEWORDNAME", "") == "ONEWORDNAME"
    assert tools.make_human_cat_key("Onewordname", "") == "Onewordname"
    assert tools.make_human_cat_key("onewordname", "") == "onewordname"
    assert (
        len(
            tools.make_human_cat_key(
                r"Friends of the Mission Clinic of Our Lady of Guadalupe, Inc.", "Test"
            )
        )
        > 0
    )


def test_make_human_cat_key_person_of_place() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"Foo of London", r"") == r"Foo of London"
    assert tools.make_human_cat_key(r"Foé of London", r"") == r"Foe of London"
    assert tools.make_human_cat_key(r"Foo II of London", r"") == r"Foo 02 of London"
    assert tools.make_human_cat_key(r"Foo XI of London", r"") == r"Foo 11 of London"
    assert tools.make_human_cat_key(r"Clinoch of Alt Clut", r"") == r"Clinoch of Alt Clut", (
        r"Person of place with two-word place name"
    )
    assert (
        tools.make_human_cat_key(r"Byzantine Master of the Crucifix of Pisa", r"")
        == r"Byzantine Master of the Crucifix of Pisa"
    )


def test_make_human_cat_key_with_roman_numbers() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"John Doe III", r"") == r"Doe, John III"
    assert tools.make_human_cat_key(r"John III", r"") == r"John III"
    assert tools.make_human_cat_key(r"XVII", r"") == r"XVII"
    assert (
        tools.make_human_cat_key(r"John Doe King of Spain III", r"")
        == r"Spain, John Doe King of III"
    )


def test_make_human_cat_key_with_jr_sr() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"John Doe Jr.", r"") == r"Doe, John Jr."
    assert tools.make_human_cat_key(r"John Doe Sr.", r"") == r"Doe, John Sr."
    assert tools.make_human_cat_key(r"John Doe Jnr.", r"") == r"Doe, John Jnr."
    assert tools.make_human_cat_key(r"John Doe Snr.", r"") == r"Doe, John Snr."
    assert tools.make_human_cat_key(r"Carey Elmore Morgan Jr.", r"") == r"Morgan, Carey Elmore Jr."
    assert tools.make_human_cat_key(r"John Doe Snr.", r"") == r"Doe, John Snr."
    assert tools.make_human_cat_key(r"Steven A. Hickham Jr.", r"") == r"Hickham, Steven A. Jr."
    assert tools.make_human_cat_key(r"Steven A. Hickham Jnr.", r"") == r"Hickham, Steven A. Jnr."
    assert tools.make_human_cat_key(r"Steven Hickham Jr.", r"") == r"Hickham, Steven Jr."


def test_make_human_cat_key_with_apostrophes() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"J'ohn D'Doe", r"") == r"DDoe, John"
    assert tools.make_human_cat_key(r"'Test", r"") == r"Test"
    assert tools.make_human_cat_key(r"Lillian O’Donnell", r"") == r"ODonnell, Lillian"
    assert tools.make_human_cat_key(r", Word", r"") == r"Word"


def test_make_human_cat_key_with_prefixes() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"John de Doe", r"") == r"Doe, John de"


def test_make_human_cat_key_diacritics() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"Ďöê", r"") == r"Doe"
    assert tools.make_human_cat_key(r"Ĵǒħń Ďöê", r"") == r"Doe, John"
    assert (
        tools.make_human_cat_key(r"Gu, Prince Imperial Hoeun", r"") == r"Gu, Prince Imperial Hoeun"
    )
    assert tools.make_human_cat_key(r"Ёпрстий", r"") == r"Eпрcтии"


def test_make_human_cat_key_arabic_names() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"Ahmed Mohammed Mukit", r"") == r"Ahmed Mohammed Mukit", (
        r"no change"
    )
    assert tools.make_human_cat_key(r"AHMED Mohammed MUKIT", r"") == r"AHMED Mohammed MUKIT", (
        r"no change"
    )
    assert tools.make_human_cat_key(r"ahmed Mohammed mukit", r"") == r"ahmed Mohammed mukit", (
        r"no change"
    )
    assert tools.make_human_cat_key(r"John Smith", r"") == r"Smith, John"


def test_make_human_cat_key_mc_name() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"John McSmith", r"") == r"McSmith, John"
    assert tools.make_human_cat_key(r"John MacSmith", r"") == r"MacSmith, John"
    assert tools.make_human_cat_key(r"John Mcsmith", r"") == r"Mcsmith, John"
    assert tools.make_human_cat_key(r"John Smith", r"") == r"Smith, John"
    assert tools.make_human_cat_key(r"John Macintosh", r"") == r"Macintosh, John"


def test_make_human_cat_key_family_name() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"Kong Qingdong", r"{{Chinese name}}") == r"Kong Qingdong"
    assert tools.make_human_cat_key(r"Kong Qingdong", r"{{foo}") == r"Qingdong, Kong"


def test_remove_diacritics() -> None:
    for a, b in tools.Diacritics:
        assert tools.remove_diacritics(a) == b, a
    rd = tools.remove_diacritics
    assert rd(r"ầắạảằẩ") == r"aaaaaa", "a"
    assert rd(r"ḉćĉçċ") == r"ccccc", "c"
    assert rd(r"ḕềẹĕ") == r"eeee", "e"
    assert rd(r"ĥḫ") == r"hh", "h"
    assert rd(r"ịỉíįí") == r"iiiii", "i"
    assert rd(r"İ") == r"I", "I"
    assert rd(r"òỏøờồȱȯȭȫoỗơ") == r"oooooooooooo", "o"
    assert rd(r"Ø") == r"O", "null"
    assert rd(r"š") == r"s", "s"
    assert rd(r"ụủữự") == r"uuuu", "u"
    assert rd(r"x̌") == r"x", "x"
    assert rd(r"ỳỵ") == r"yy", "y"
    assert rd(r"ḏ p̄ Ś̄") == r"d p S", "Random"
    assert rd(r"²") == r"2", "2"
    assert rd(r"Ǣ") == r"Ae"
    assert rd(r"ǣ") == r"ae"
    assert (
        rd(r"ȦȧḂḃĊċḊḋĖėḞḟĠġḢḣİıṀṁṄṅȮȯṖṗṘṙṠṡṪṫẆẇẊẋẎẏŻż")
        == r"AaBbCcDdEeFfGgHhIiMmNnOoPpRrSsTtWwXxYyZz"
    ), "letters with dot above sign"
    assert (
        rd(
            r"ĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŔŕŖŗŘř"
        )
        == r"AaAaAaCcCcCcCcDdDdEeEeEeEeEeGgGgGgGgHhHhIiIiIiIiIiJjKkkLlLlLlLlLlNnNnNnnNnOoOoOoRrRrRr"
    ), "extended Latin-A part 1"
    assert (
        rd(r"ŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽžſ") == r"SsSsSsSsTtTtTtUuUuUuUuUuUuWwYyYZzZzZzs"
    ), "extended Latin-A part 2"
    assert (
        rd(r"ǍǎǏǐǑǒǓǔǕǖǗǘǙǚǛǜǝǞǟǠǡǤǥǦǧǨǩǪǫǬǭǸǹǺǻǾǿȀȁȂȃȄȅȆȇȈȉȊȋȌȍȎȏȐȑȒȓȔȕȖȗȘșȚț")
        == r"AaIiOoUuUuUuUuUueAaAaGgGgKkOoOoNnAaOoAaAaEeEeIiIiOoOoRrRrUuUuSsTt"
    ), "extended Latin-B"
    assert (
        rd(r"ḀḁḂḃḄḅḆḇḈḉḊḋḌḍḎḏḐḑḒḓḔḕḖḗḘḙḚḛḜḝḞḟḠḡḢḣḤḥḦḧḨḩḪḫḬḭḮḯḰḱḲḳḴḵḶḷḸḹḺḻḼḽḾḿṀṁṂṃṄṅṆṇṈṉṊṋ")
        == r"AaBbBbBbCcDdDdDdDdDdEeEeEeEeEeFfGgHhHhHhHhHhIiIiKkKkKkLlLlLlLlMmMmMmNnNnNnNn"
    ), "Latin Extended Additional A-N"


def test_clean_sort_key() -> None:
    S = W.for_site(EN)
    assert tools.clean_sort_key(r"&") == r"and", r"per SORTKEY"
    assert tools.clean_sort_key(r"A & B") == r"A and B", r"&"
    assert tools.clean_sort_key(r"ǀAi-ǀAis") == r"Ai-Ais", r"removes weird character"
    assert (
        tools.clean_sort_key(r"ǀAi-ǀAis/Richtersveld Transfrontier Park")
        == r"Ai-Ais Richtersveld Transfrontier Park"
    ), r"removes weird character"
    assert tools.clean_sort_key(r"Der Nachtkurier meldet…") == r"Der Nachtkurier meldet...", (
        r"replaces …"
    )
    assert tools.clean_sort_key(r"A·L") == r"A L", r"replaces · with space"
    assert (
        tools.clean_sort_key(r"Ḇḇ, Ḏḏ, ẖ, Ḵḵ, Ḻḻ, Ṉṉ, Ṟṟ, Ṯṯ") == r"Bb, Dd, h, Kk, Ll, Nn, Rr, Tt"
    ), r"letters with macron below"
    assert (
        tools.clean_sort_key(r"ɓ, ƈ, ɗ, ƒ, ɠ, ɦ, ƙ, ɲ, ƥ, ʠ, ƭ, ʋ, ⱳ, ƴ")
        == r"b, c, d, f, g, h, k, n, p, q, t, v, w, y"
    ), r"letters with hook"
    assert (
        tools.clean_sort_key(r"ᶀ, ᶁ, ᶂ, ᶃ, ᶄ, ᶅ, ᶆ, ᶇ, ᶈ, ᶉ, ᶊ, ƫ, ᶌ, ᶍ, ᶎ")
        == r"b, d, f, g, k, l, m, n, p, r, s, t, y, x, z"
    ), r"letters with palatal hook"
    assert tools.clean_sort_key(r"Ąą, Ęę, Įį, Ǫǫ, Ųų") == r"Aa, Ee, Ii, Oo, Uu", (
        r"letters using ogonek sign"
    )
    assert tools.clean_sort_key(r"Ȃȃ, Ȇȇ, Ȋȋ, Ȏȏ, Ȗȗ, Ȓȓ") == r"Aa, Ee, Ii, Oo, Uu, Rr", (
        r"letters using inverted breve"
    )
    assert tools.clean_sort_key(r"D̦d̦, Șș, Țț") == r"Dd, Ss, Tt", r"letters using comma sign"
    assert tools.clean_sort_key(r"’‘ʻ`´“”") == r"'''''''", r"quotes"
    assert tools.clean_sort_key(r"1–2–3") == r"1-2-3", r"endash"
    assert tools.clean_sort_key(r"1–2&ndash;3") == r"1-2-3", r"&ndash;"
    assert tools.clean_sort_key(r"A       ") == r"A ", r"Excess whitespace"
    assert tools.clean_sort_key(r"A/B") == r"A B", r"Forward slash"
    assert (
        tools.clean_sort_key(r"{{<noinclude>BASE</noinclude>PAGENAME}}")
        == r"{{<noinclude>BASE</noinclude>PAGENAME}}"
    ), r"noinclude tags, no change"


def test_clean_sort_key_lang() -> None:
    S = W.for_site(EN)
    S = set_site(unicode_category_collation=True)
    S = set_lang(r"ru")
    assert tools.clean_sort_key(r"Hellõ") == r"Hellõ", (
        r"no diacritic removal for defaultsort key on ru-wiki"
    )
    S = set_lang(r"fr")
    assert tools.clean_sort_key(r"Hellõ") == r"Hellõ", (
        r"no diacritic removal for defaultsort key on fr-wiki"
    )
    S = set_lang(r"pl")
    assert tools.clean_sort_key(r"Hellõ") == r"Hellõ", (
        r"no diacritic removal for defaultsort key on pl-wiki"
    )
    S = set_site(unicode_category_collation=False)
    S = set_lang(r"en")
    assert tools.fixup_default_sort(r"Hellõ") == r"Hello", r"do remove diacritics on en-wiki"


def test_has_diacritics() -> None:
    S = W.for_site(EN)
    assert tools.has_diacritics(r"hellõ")
    assert tools.has_diacritics(r"hellõ there")
    assert tools.has_diacritics(r"hẽllõ there")
    assert tools.has_diacritics(r"hẽllo there")
    assert tools.has_diacritics(r"İzmir")
    assert not (tools.has_diacritics(r"hello"))
    assert not (tools.has_diacritics(r"abcdefghijklmnopqrstuvwxyz")), r"standard Latin alphabet"
    assert not (tools.has_diacritics(r"0123456789")), r"digits"
    assert not (tools.has_diacritics(r"")), r"empty string"
    assert not (tools.has_diacritics(r"   ")), r"whitespace"


def test_fix_up_default_sort_tests() -> None:
    S = W.for_site(EN)
    assert tools.fixup_default_sort(r"hellõ") == r"hello"
    assert tools.fixup_default_sort(r"hellõ   ") == r"hello"
    assert tools.fixup_default_sort(r"fred smithson") == r"fred smithson"
    assert tools.fixup_default_sort(r"De Meriño, Fernando Arturo") == r"De Merino, Fernando Arturo"
    assert tools.fixup_default_sort(r"OneWordItem") == r"OneWordItem"
    assert tools.fixup_default_sort(r"Foo (bar)") == r"Foo (bar)"
    assert tools.fixup_default_sort(r"Kwakwaka'wakw mythology") == r"Kwakwaka'wakw mythology"
    assert tools.fixup_default_sort(r"Peewee's Playhouse") == r"Peewee's Playhouse"
    assert tools.fixup_default_sort(r"Peewee’s Playhouse") == r"Peewee's Playhouse"
    assert (
        tools.fixup_default_sort(r"2010 ITF Women's Circuit (July–September)")
        == r"2010 ITF Women's Circuit (July-September)"
    )
    assert tools.fixup_default_sort(r"List of Foo") == r"Foo"
    assert tools.fixup_default_sort(r"List of foos") == r"Foos"


def test_fix_up_default_sort_human_name() -> None:
    S = W.for_site(EN)
    assert tools.fixup_default_sort(r"O'connor, Fred", True) == r"Oconnor, Fred", (
        r"apostrophe removed for bio sortkey per [[WP:MCSTJR]]"
    )
    assert tools.fixup_default_sort(r"O'connor Trading", False) == r"O'connor Trading", (
        r"apostrophes not removed on non-bio sortkey"
    )
    assert tools.fixup_default_sort(r"Jones,Fred", True) == r"Jones, Fred", r"comma spacing"
    assert tools.fixup_default_sort(r"Jones ,Fred", True) == r"Jones, Fred", r"comma spacing"
    assert tools.fixup_default_sort(r"Jones, Fred", True) == r"Jones, Fred", (
        r"comma spacing: no change if already correct"
    )


def test_fix_up_default_sort_bad_chars() -> None:
    S = W.for_site(EN)
    assert tools.fixup_default_sort(r"fred smitHº") == r"fred smitH"
    assert tools.fixup_default_sort(r'fred "smitH"') == r"fred smitH"
    assert tools.fixup_default_sort(r'Fred "Smith"') == r"Fred Smith"


def test_fix_up_default_sort_tests_ru() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ru")
    S = set_site(unicode_category_collation=True)
    assert tools.fixup_default_sort(r"Hellõ") == r"Hellõ", (
        r"no diacritic removal for defaultsort key on ru-wiki"
    )
    S = set_lang(r"en")
    S = set_site(unicode_category_collation=False)
    assert tools.fixup_default_sort(r"Hellõ") == r"Hello"


def test_remove_namespace() -> None:
    S = W.for_site(EN)
    assert tools.make_human_cat_key(r"Wikipedia:John Doe", r"") == r"Doe, John"


def test_fuzz_test() -> None:
    import random

    allowed = "abcdefghijklmnopqrstuvwxyzйцукенфывапролдж              ,,,,,"
    spaces = DotNetRegex(r"\s{2,}")
    rnd = random.Random(20261012)  # AWB uses an unseeded Random; fixed here for reproducibility
    for _ in range(10000):
        name = "".join(rnd.choice(allowed) for _ in range(rnd.randrange(45)))
        name = spaces.replace(name, " ").strip(" ,")
        name = tools.make_human_cat_key(name, "")
        assert "  " not in name, f"Sorting key shouldn't contain consecutive spaces ({name})"
        assert not name.startswith(" "), "Sorting key shouldn't start with spaces"
        assert not name.endswith(" "), "Sorting key shouldn't end with spaces"


def test_roman_to_int() -> None:
    S = W.for_site(EN)
    assert tools.roman_to_int(r"I") == r"01"
    assert tools.roman_to_int(r"II") == r"02"
    assert tools.roman_to_int(r"III") == r"03"
    assert tools.roman_to_int(r"IV") == r"04"
    assert tools.roman_to_int(r"V") == r"05"
    assert tools.roman_to_int(r"VI") == r"06"
    assert tools.roman_to_int(r"VII") == r"07"
    assert tools.roman_to_int(r"VIII") == r"08"
    assert tools.roman_to_int(r"IX") == r"09"
    assert tools.roman_to_int(r"X") == r"10"
    assert tools.roman_to_int(r"XI") == r"11"
    assert tools.roman_to_int(r"XIV") == r"14"
    assert tools.roman_to_int(r"XVI") == r"16"
    assert tools.roman_to_int(r"XXVI") == r"26"
    assert tools.roman_to_int(r"LXXVI") == r"76"


def test_convert_to_talk() -> None:
    t = tools.convert_to_talk
    assert t("Foo") == "Talk:Foo"
    assert t("Foo bar") == "Talk:Foo bar"
    assert t("Foo:Bar") == "Talk:Foo:Bar"
    assert t("Wikipedia:Foo") == "Wikipedia talk:Foo"
    assert t("File:Foo bar") == "File talk:Foo bar"
    assert t("File talk:Foo bar") == "File talk:Foo bar"
    assert t("Special:Foo") == "Special:Foo"
    assert t("Media:Bar") == "Media:Bar"


def test_to_talk_on_list() -> None:
    titles = ["Foo", "Talk:Foo bar", "File:Foo", "Special:Foo"]
    assert sorted(tools.convert_to_talk_list(titles)) == sorted(
        ["Talk:Foo", "Talk:Foo bar", "File talk:Foo", "Special:Foo"]
    )


def test_convert_from_talk() -> None:
    f = tools.convert_from_talk
    assert f("Talk:Foo") == "Foo"
    assert f("Foo") == "Foo"
    assert f("Foo:Bar") == "Foo:Bar"
    assert f("Talk:Foo:Bar") == "Foo:Bar"
    assert f("User:Foo bar") == "User:Foo bar"
    assert f("File talk:Bar") == "File:Bar"
    assert f("Template talk:Bar") == "Template:Bar"
    assert f("Category talk:Foo bar") == "Category:Foo bar"
    assert f("Special:Foo") == "Special:Foo"
    assert f("Media:Bar") == "Media:Bar"


def test_from_talk_on_list() -> None:
    titles = ["Foo", "Talk:Foo bar", "User talk:Foo", "Special:Foo"]
    assert sorted(tools.convert_from_talk_list(titles)) == sorted(
        ["Foo", "Foo bar", "User:Foo", "Special:Foo"]
    )
