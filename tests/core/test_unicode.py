"""Multilingual behaviour we rely on.

Python's Unicode semantics are a feature (CLAUDE.md rule 3).
"""

import pytest

from pyawb.core import rx

WORDS = [
    pytest.param("الْعَرَبِيَّة", id="arabic-harakat"),
    pytest.param("عـــربي", id="arabic-tatweel"),
    pytest.param("می‌خواهم", id="persian-zwnj"),
    pytest.param("മലയാളം", id="malayalam-mc-signs"),
    pytest.param("അവൻ", id="malayalam-atomic-chillu"),
    pytest.param("അവന്‍", id="malayalam-zwj-chillu"),
    pytest.param("नमस्ते", id="hindi-virama"),
    pytest.param("𠀋𠀌", id="cjk-ext-b-astral"),
    pytest.param("カタカナー", id="japanese-prolonged-mark"),
    pytest.param("ｆｕｌｌ", id="fullwidth"),
    pytest.param("İstanbul", id="turkish-dotted-i"),
    pytest.param("λόγος", id="greek-final-sigma"),
]


@pytest.mark.parametrize("word", WORDS)
def test_word_stays_whole(word: str) -> None:
    m = rx.compile_dotnet(r"\b\w+\b").search(f" {word} ")
    assert m is not None and m.group(0) == word


@pytest.mark.parametrize("digits", ["٠١٢٣", "۰۱۲۳", "൧൨൩", "１２３", "०१२"])
def test_non_ascii_digits(digits: str) -> None:
    assert rx.compile_dotnet(r"^\d+$").match(digits)


def test_astral_is_one_character() -> None:
    assert rx.compile_dotnet(r"^.$").match("𠀋")
    assert rx.compile_dotnet(r"^.$").match("😀")


def test_rlm_is_not_a_word_character() -> None:
    assert rx.compile_dotnet(r"\w+").findall("abc‏def") == ["abc", "def"]


def test_greek_case_insensitive() -> None:
    assert rx.compile_dotnet("(?i)λόγος").match("ΛΌΓΟΣ")
    assert rx.compile_dotnet("(?i)ς").match("Σ")
