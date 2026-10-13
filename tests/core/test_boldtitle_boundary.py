"""Bold title only at the start of a word: a deliberate difference from AWB (BoldTitle.cs bolds
the title inside a longer word, e.g. after the Arabic article ال)."""

import pytest

from pyawb.core.parsers.parsers import Parsers


@pytest.mark.parametrize(
    ("text", "title", "expected"),
    [
        # inside a longer word: AWB would bold these; PyAWB leaves them
        ("القط [[حيوان]] أليف.", "قط", "القط [[حيوان]] أليف."),
        ("Thecat is here.", "Cat", "Thecat is here."),
        ("x2Foo, y", "Foo", "x2Foo, y"),
        # a whole word: bolded as in AWB
        ("قط [[حيوان]] أليف.", "قط", "'''قط''' [[حيوان]] أليف."),
        ("Foo bar is a thing.", "Foo bar", "'''Foo bar''' is a thing."),
        # scripts without spaces between words keep AWB's behaviour
        ("首都北京 是中国的首都。", "北京", "首都'''北京''' 是中国的首都。"),
    ],
)
def test_bold_title_at_word_start(text: str, title: str, expected: str) -> None:
    assert Parsers().bold_title(text, title)[0] == expected
