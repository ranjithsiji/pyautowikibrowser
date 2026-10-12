import urllib.request

import pytest

from awb_l.rules import typos

SAMPLE = (
    '<Typo word="accommodate" find="\\b(a)c(?:c?omm?|om)odat(e[ds]?|ing|ions?)\\b"'
    ' replace="$1ccommodat$2" />\n'
    '<Typo word="Hello" find="\\bHelo\\b" replace="Hello"/>\n'
)


def test_parse_and_apply() -> None:
    tl = typos.load(SAMPLE)
    assert not tl.errors
    assert [e.word for e, _ in tl.rules] == ["accommodate", "Hello"]
    rule = tl.rules[0][1]
    assert rule.apply("we acomodated them").text == "we accommodated them"


def test_duplicates_rejected() -> None:
    with pytest.raises(typos.TypoListError):
        typos.parse('<Typo word="a" find="x" replace="y"/><Typo word="b" find="x" replace="z"/>')


@pytest.mark.network
def test_all_enwiki_rules_compile() -> None:
    req = urllib.request.Request(
        typos.ENWIKI_TYPOS_URL,
        headers={"User-Agent": "AWB-L test suite (https://github.com/; awb-l tests)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    tl = typos.load(text)
    assert len(tl.rules) > 4000
    assert tl.errors == []
