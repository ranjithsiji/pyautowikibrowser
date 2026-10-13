"""Port of AWB UnitTests/FormattingTests.cs: headings, whitespace, templates and other formatting fixes.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from awb_x.core import genfixes, namespace, tools
from awb_x.core import wikiregexes as W
from awb_x.core.dotnet_regex import DotNetOptions as O
from awb_x.core.parsers.parsers import DateLocale
from awb_x.core.rx import DotNetRegex
from awb_x.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_site
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_test_br_converter() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax("*a<br>\r\nb") == "*a\r\nb"
    assert genfixes.fix_syntax(r"*a<br>") == r"*a", (
        r"Br removed at end of list when list is end of text"
    )
    assert genfixes.fix_syntax("*a<br><br>\r\nb") == "*a\r\nb"
    assert genfixes.fix_syntax("\r\n*a<br>\r\nb") == "*a\r\nb"
    assert genfixes.fix_syntax("foo\r\n*a<br>\r\nb") == "foo\r\n*a\r\nb"
    correct1 = "foo\r\n*a<br>b"
    assert genfixes.fix_syntax(correct1) == correct1, r"No change to br tag in middle of list line"
    assert genfixes.fix_syntax("*a<br>\r\n") == r"*a"
    assert genfixes.fix_syntax("*a<br\\>\r\n") == r"*a"
    assert genfixes.fix_syntax("*a<br/>\r\n") == r"*a"
    assert genfixes.fix_syntax("*a <br\\> \r\n") == r"*a"
    assert genfixes.fix_syntax("*a </br/> \r\n") == r"*a"
    assert genfixes.fix_syntax("*a<br\\> \r\n") == r"*a"
    assert genfixes.fix_syntax("*a <\\br\\>\r\n") == r"*a"
    assert genfixes.fix_syntax("*a     <br\\>    \r\n") == r"*a"
    assert genfixes.fix_syntax("*a <br/>\r\n") == r"*a"
    assert genfixes.fix_syntax("*a <br/ >\r\n") == r"*a"
    assert genfixes.fix_syntax("*a <br / >\r\n") == r"*a"
    assert genfixes.fix_syntax("*a <br / >\t\r\n") == r"*a", r"Contains trailing tabs"
    assert genfixes.fix_syntax("*a <br / >\t\t\r\n") == r"*a", r"Contains trailing tabs"
    assert genfixes.fix_syntax("*:#;a<br>\r\n*b") == "*:#;a\r\n*b"
    assert genfixes.fix_syntax("###;;;:::***a<br />\r\nb") == "###;;;:::***a\r\nb"
    assert genfixes.fix_syntax("*&a<br/>\r\nb") == "*&a\r\nb"
    assert genfixes.fix_syntax("*&a<br/>\t\r\nb") == "*&a\r\nb"
    assert genfixes.fix_syntax("&*a<br>\r\nb") == "&*a<br>\r\nb"
    assert genfixes.fix_syntax("*a\r\n<br>\r\nb") == "*a\r\n<br>\r\nb"


def test_br_after_maintance_template() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"{{Orphan|date=September 2015}}<br>")
        == r"{{Orphan|date=September 2015}}"
    ), r"br after a maintance template"
    assert (
        genfixes.fix_syntax(r"{{Orphan|date=September 2015}}<br/>")
        == r"{{Orphan|date=September 2015}}"
    ), r"br after a maintance template"
    assert (
        genfixes.fix_syntax(r"{{Orphan|date=September 2015}}<br />")
        == r"{{Orphan|date=September 2015}}"
    ), r"br after a maintance template"
    assert (
        genfixes.fix_syntax(r"{{Orphan|date=September 2015}}{{Infobox person|name=John<br>Smith}}")
        == r"{{Orphan|date=September 2015}}{{Infobox person|name=John<br>Smith}}"
    ), r"do not affect any other br tags"
    assert genfixes.fix_syntax(r"{{long ton|37|10}}<br>") == r"{{long ton|37|10}}<br>", (
        r"avoid replacements in after inline templates"
    )


def test_syntax_regex_list_row_br_tag_start() -> None:
    S = W.for_site(EN)
    assert parser.fix_br_paragraphs("x<br>\r\n*abc") == "x\r\n*abc"
    assert parser.fix_br_paragraphs("x<br> \r\n*abc") == "x\r\n*abc"
    assert parser.fix_br_paragraphs("x<br/> \r\n*abc") == "x\r\n*abc"
    assert parser.fix_br_paragraphs("x<br /> \r\n*abc") == "x\r\n*abc"
    assert parser.fix_br_paragraphs("x<br / > \r\n*abc") == "x\r\n*abc"
    genFixes.assert_not_changed("{{{Foo|\r\nparam=<br>\r\n**text\r\n**text1 }}")
    assert (
        parser.fix_br_paragraphs("** Blog x\r\n<br>\r\n<br>\r\n'''No") == "** Blog x\r\n\r\n'''No"
    )


def test_test_fix_headings() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings(r"=='''foo'''==", r"Heading with bold") == r"==foo=="
    assert genfixes.fix_headings(r"== '''foo''' ==", r"Heading with bold and space") == r"== foo =="
    assert (
        genfixes.fix_headings(r"==  '''foo'''  ==", r"Heading with bold and more than one space")
        == r"==  foo  =="
    )
    assert genfixes.fix_headings("=='''foo'''==\r\n", r"test").startswith(r"==foo==")
    assert (
        genfixes.fix_headings("quux\r\n=='''foo'''==\r\nbar", r"test")
        == "quux\r\n\r\n==foo==\r\nbar"
    )
    assert (
        genfixes.fix_headings("quux\r\n=='''foo'''==\r\n\r\nbar", r"test")
        == "quux\r\n\r\n==foo==\r\n\r\nbar"
    )
    assert genfixes.fix_headings(r"==foo==", r"No change") == r"==foo=="
    assert genfixes.fix_headings(r"== foo ==", r"No change") == r"== foo =="
    assert (
        genfixes.fix_headings("hi.\r\n ==News==\r\nSome news here.", r"test")
        == "hi.\r\n\r\n==News==\r\nSome news here."
    )
    assert (
        genfixes.fix_headings("hi.\r\n ==News place==\r\nSome news here.", r"test")
        == "hi.\r\n\r\n==News place==\r\nSome news here."
    )
    assert (
        genfixes.fix_headings("hi.\r\n    ==News place==\r\nSome news here.", r"test")
        == "hi.\r\n\r\n==News place==\r\nSome news here."
    )
    assert (
        genfixes.fix_headings("hi.\r\n==News place==\r\nSome news here.", r"test")
        == "hi.\r\n\r\n==News place==\r\nSome news here."
    )
    assert (
        genfixes.fix_headings("hi.\r\n\r\n==News place==\r\nSome news here.", r"test")
        == "hi.\r\n\r\n==News place==\r\nSome news here."
    ), r"space trimmed from end of paragraph"
    assert (
        genfixes.fix_headings("hi.\r\n<br>\r\n==News place==\r\nSome news here.", r"test")
        == "hi.\r\n\r\n==News place==\r\nSome news here."
    ), r"space trimmed from end of paragraph when br replaces newline"
    assert (
        genfixes.fix_headings(
            "hi.\r\n<br>\r\n<BR>\r\n<BR>\r\n==News place==\r\nSome news here.", r"test"
        )
        == "hi.\r\n\r\n==News place==\r\nSome news here."
    ), r"space trimmed from end of paragraph when br replaces newline"


def test_test_fix_headings_renaming() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings(r"==REFERENCES==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==REFERENCE:==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==REFERENSES==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==REFERENCE==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==REFERENCE:==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"== REFERENCES ==", r"a") == r"== References =="
    assert genfixes.fix_headings(r"==Reference==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==Refferences==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==Referrences==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==Refferrences==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==Refrences==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==Reffrences==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==Refrence==", r"a") == r"==References=="
    assert genfixes.fix_headings(r"==SOURCES==", r"a") == r"==Sources=="
    assert genfixes.fix_headings(r"==sources==", r"a") == r"==Sources=="
    assert genfixes.fix_headings(r"==source==", r"a") == r"==Sources=="
    assert genfixes.fix_headings(r"==source:==", r"a") == r"==Sources=="
    assert genfixes.fix_headings(r"== SOURCES ==", r"a") == r"== Sources =="
    assert genfixes.fix_headings(r"==  SOURCES  ==", r"a") == r"==  Sources  =="
    assert (
        genfixes.fix_headings(
            "==Further reading==\r\n            bar bar\r\n            \r\n==External Links==\r\n*http://foo.com",
            r"a",
        )
        == "==Further reading==\r\n            bar bar\r\n            \r\n==External links==\r\n*http://foo.com"
    )
    assert (
        genfixes.fix_headings("some text\r\n\r\n==Also see==", r"test")
        == "some text\r\n\r\n==See also=="
    ), r"rename also see to see also section"
    assert genfixes.fix_headings(r"==Also see==", r"test") == r"==See also==", (
        r"rename also see to see also section"
    )
    assert genfixes.fix_headings(r"==Internal links==", r"test") == r"==See also==", (
        r"rename to see also section"
    )
    assert genfixes.fix_headings(r"==Related articles==", r"test") == r"==See also==", (
        r"rename to see also section"
    )
    assert (
        genfixes.fix_headings("Foo\r\n\r\n==See Also==\r\nBar", r"test")
        == "Foo\r\n\r\n==See also==\r\nBar"
    ), r"See Also capitalization"
    assert genfixes.fix_headings(r"===Related articles===", r"test") == r"===Related articles===", (
        r"do nothing if level 3"
    )
    assert (
        genfixes.fix_headings("some text\r\n\r\n===Related articles===", r"test")
        == "some text\r\n\r\n===Related articles==="
    ), r"do nothing if level 3"
    assert (
        genfixes.fix_headings("Foo\r\n\r\n==External Links==\r\nBar", r"test")
        == "Foo\r\n\r\n==External links==\r\nBar"
    ), r"External Links capitalization"


def test_test_fix_headings_heading_equal_title() -> None:
    S = W.for_site(EN)
    HeadingEqualTitle = genfixes.fix_headings("\r\n==Foo==\r\nB", r"Foo")
    assert r"Foo" not in HeadingEqualTitle, r"Heading same as title"
    HeadingEqualTitle = genfixes.fix_headings(
        "Words here\r\n==Section==\r\nWords there.\r\n==Foo==\r\nB", r"Foo"
    )
    assert r"Foo" in HeadingEqualTitle, r"Heading same as title in later section retained"
    assert (
        genfixes.fix_headings("'''The'''.\r\n\r\n== History ==\t \r\n \t\t \r\nFive", r"a")
        == "'''The'''.\r\n\r\n== History ==\r\n\r\nFive"
    )


def test_test_fix_headings_colon() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings("== hello world: ==\r\n", r"a") == "== hello world ==\r\n", (
        r"removes colon"
    )
    assert genfixes.fix_headings("== hello world : ==\r\n", r"a") == "== hello world  ==\r\n", (
        r"removes colon with space"
    )
    assert genfixes.fix_headings("=== hello world: ===\r\n", r"a") == "== hello world ==\r\n", (
        r"removes colon - header level 3"
    )
    assert (
        genfixes.fix_headings("== hello world: ==\r\n== hello world2: ==\r\n", r"a")
        == "== hello world ==\r\n\r\n== hello world2 ==\r\n"
    ), r"removes colons from multiple places"
    assert (
        genfixes.fix_headings("== hello world: == \r\n== hello world2: ==\r\n", r"a")
        == "== hello world ==\r\n\r\n== hello world2 ==\r\n"
    ), r"fixes colon in heading when excess whitespace after heading end"
    assert genfixes.fix_headings("== hello:world ==\r\n", r"a") == "== hello:world ==\r\n"
    assert genfixes.fix_headings("== : ==\r\n", r"a") == "== : ==\r\n"
    assert (
        genfixes.fix_headings("A\r\n == hello world: ==\r\n", r"a")
        == "A\r\n\r\n== hello world ==\r\n"
    )


def test_test_fix_headings_br_removal() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings(r"==Foo<br>==", r"a") == r"==Foo=="
    assert genfixes.fix_headings(r"==Foo<br />==", r"a") == r"==Foo=="
    assert genfixes.fix_headings(r"==Foo< BR >==", r"a") == r"==Foo=="


def test_test_fix_headings_big_removal() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings(r"==<big>Foo</big>==", r"a") == r"==Foo=="
    assert genfixes.fix_headings(r"==<Big>Foo</big>==", r"a") == r"==Foo=="


def test_test_fix_headings_remove_two_levels() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings("====hello====\r\ntext", r"a") == "==hello==\r\ntext"
    assert (
        genfixes.fix_headings(
            "====hello====\r\ntext\r\n==== hello2 ====\r\ntexty\r\n===== hello3 =====\r\n", r"a"
        )
        == "==hello==\r\ntext\r\n\r\n== hello2 ==\r\ntexty\r\n\r\n=== hello3 ===\r\n"
    )
    assert (
        genfixes.fix_headings("=level1=\r\ntext\r\n====hello====\r\n", r"a")
        == "==level1==\r\ntext\r\n\r\n==hello==\r\n"
    )
    assert (
        genfixes.fix_headings("==hi==\r\n\r\n====hello====\r\n", r"a")
        == "==hi==\r\n\r\n====hello====\r\n"
    )
    assert (
        genfixes.fix_headings("====hello====\r\ntext\r\n==References==\r\nfoo", r"a")
        == "==hello==\r\ntext\r\n\r\n==References==\r\nfoo"
    )
    assert (
        genfixes.fix_headings("====hello====\r\ntext\r\n==External links==\r\nfoo", r"a")
        == "==hello==\r\ntext\r\n\r\n==External links==\r\nfoo"
    )
    assert genfixes.fix_headings(
        "====hello====\r\ntext\r\n\r\n==See also==\r\n\r\n==External links==\r\nfoo", r"a"
    ).startswith("==hello==\r\ntext\r\n\r\n==See also==")
    assert (
        genfixes.fix_headings("==hello==\r\ntext\r\n\r\n==References==\r\nfoo", r"a")
        == "==hello==\r\ntext\r\n\r\n==References==\r\nfoo"
    )
    a = "====hello====\r\ntext\r\n\r\n==External links==\r\nfoo\r\n\r\n===bar===\r\nfoo2"
    assert genfixes.fix_headings(a, r"a") == a
    a2 = "text\r\n\r\n==External links==\r\nfoo\r\n\r\n===bar===\r\nfoo2"
    assert genfixes.fix_headings(a2, r"a") == a2
    assert genfixes.fix_headings("====hello====\r\ntext", r"Talk:foo") == "====hello====\r\ntext"


def test_test_fix_headings_bold_removal() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_headings(r"=== '''Caernarvon''' 1536-1832 ===", r"a")
        == r"=== Caernarvon 1536-1832 ==="
    )
    assert (
        genfixes.fix_headings(r"=== <b>Caernarvon</b> 1536-1832 ===", r"a")
        == r"=== Caernarvon 1536-1832 ==="
    )
    assert (
        genfixes.fix_headings(r"=== <B>Caernarvon</B> 1536-1832 ===", r"a")
        == r"=== Caernarvon 1536-1832 ==="
    )
    assert (
        genfixes.fix_headings(r"==='''Caernarvon''' 1536-1832===", r"a")
        == r"===Caernarvon 1536-1832==="
    )
    assert (
        genfixes.fix_headings(r"=== Caernarvon '''1536-1832''' ===", r"a")
        == r"=== Caernarvon 1536-1832 ==="
    )
    assert (
        genfixes.fix_headings(r"=== '''Caernarvon 1536-1832''' ===", r"a")
        == r"=== Caernarvon 1536-1832 ==="
    )
    assert (
        genfixes.fix_headings(r"==== '''Caernarvon 1536-1832''' ====", r"a")
        == r"==== Caernarvon 1536-1832 ===="
    )
    assert (
        genfixes.fix_headings(r"== '''Caernarvon''' 1536-1832 ==", r"a")
        == r"== '''Caernarvon''' 1536-1832 =="
    )
    assert (
        genfixes.fix_headings(r"= '''Caernarvon''' 1536-1832 =", r"a")
        == r"== '''Caernarvon''' 1536-1832 =="
    )
    assert genfixes.fix_headings(r"=='''See Also'''==", r"test") == r"==See also==", (
        r"remove bold and fix casing at once"
    )
    assert (
        genfixes.fix_headings(r"=='''Header with bold'''==<br/>", r"test")
        == r"==Header with bold=="
    )


def test_test_fix_headings_level1() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings(r"=See also=", r"a") == r"==See also==", (
        r"L1 converted to L2 on mainspace"
    )
    assert genfixes.fix_headings(r"=See also=", r"Talk:A") == r"=See also=", (
        r"No change when not mainspace"
    )


def test_test_fix_headings_empyty_bold_removal() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_headings(r"==''''''Foo==", r"test") == r"==Foo==", (
        r"empty tag in the beginning"
    )
    assert genfixes.fix_headings(r"==Foo''''''==", r"test") == r"==Foo==", r"empty tag at the end"
    assert genfixes.fix_headings(r"==Foo''' ''' bar==", r"test") == r"==Foo bar==", (
        r"empty tag in the middle"
    )
    assert genfixes.fix_headings(r"== Foo''' ''' bar ==", r"test") == r"== Foo bar ==", (
        r"empty tag in the middle and spaces around"
    )
    assert genfixes.fix_headings(r"==Foo'''   ''' bar==", r"test") == r"==Foo bar==", r"more spaces"
    assert genfixes.fix_headings(r"== '''Foo''' ''' bar''' ==", r"test") == r"== Foo bar =="


def test_test_fix_headings_blank_line_before() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n\r\n==1920s==\r\nBar"
    assert genfixes.fix_headings("Foo\r\n\r\n==1920s==\r\nBar", r"Test") == correct, (
        r"no change when already one blank line"
    )
    assert genfixes.fix_headings("Foo\r\n\r\n\r\n==1920s==\r\nBar", r"Test") == correct, (
        r"fixes excess blank lines"
    )
    assert genfixes.fix_headings("Foo\r\n==1920s==\r\nBar", r"Test") == correct, (
        r"inserts blank line if one missing"
    )
    assert (
        genfixes.fix_headings("====4====\r\n==2==\r\ntext", r"Test")
        == "====4====\r\n\r\n==2==\r\ntext"
    ), r"fixes excess blank lines, sub-heading then heading"
    assert (
        genfixes.fix_headings("==2==\r\n====4====\r\ntext", r"Test") == "==2==\r\n====4====\r\ntext"
    ), r"Don't add blank line between heading and sub-heading"
    assert (
        genfixes.fix_headings("x\r\n\r\n====Major championships====\r\n==Wins==\r\nx", r"test")
        == "x\r\n\r\n====Major championships====\r\n\r\n==Wins==\r\nx"
    )
    assert (
        genfixes.fix_headings("x\r\n\r\n==Major championships==\r\n====Wins====\r\nx", r"test")
        == "x\r\n\r\n==Major championships==\r\n====Wins====\r\nx"
    )
    assert (
        genfixes.fix_headings("x\r\n==Major championships==\r\n====Wins====\r\nx", r"test")
        == "x\r\n\r\n==Major championships==\r\n====Wins====\r\nx"
    )
    assert (
        genfixes.fix_headings(
            "==Foo 1==\r\nx\r\n===Major championships===\r\n====Wins====\r\nx", r"test"
        )
        == "==Foo 1==\r\nx\r\n\r\n===Major championships===\r\n====Wins====\r\nx"
    )
    assert (
        genfixes.fix_headings(
            "== Events ==\r\nx\r\n=== By place ===\r\n==== Roman Empire ====\r\nx", r"test"
        )
        == "== Events ==\r\nx\r\n\r\n=== By place ===\r\n==== Roman Empire ====\r\nx"
    )
    assert (
        genfixes.fix_headings("x\r\n==Major championships==\r\n====Wins====\t\r\nx", r"test")
        == "x\r\n\r\n==Major championships==\r\n====Wins====\r\nx"
    ), r"Excess tab whitespace in second header handled"
    indented = "A\r\n == some code here === and here ==\r\n Done"
    assert genfixes.fix_headings(indented, r"Test") == indented, (
        r"No change to indented text with other == in"
    )
    consecutiveSubHeadings = "==2==\r\n===3===\r\n====4====\r\ntext"
    assert genfixes.fix_headings(consecutiveSubHeadings, r"Test") == consecutiveSubHeadings, (
        r"Don't add blank line between heading and sub-heading, consecutive"
    )
    consecutiveSubHeadings = "==2==\r\n===3===\r\n====4====\r\n=====5=====\r\ntext"
    assert genfixes.fix_headings(consecutiveSubHeadings, r"Test") == consecutiveSubHeadings, (
        r"Don't add blank line between heading and sub-heading, consecutive x2"
    )


def test_test_fix_headings_anchor() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{Anchor|Nineteentwenties}}\r\n==1920s==\r\nBar"
    assert genfixes.fix_headings(correct, r"Test") == correct, (
        r"no change to anchor just before L2 heading"
    )
    correct = "Foo\r\n\r\n==Some heading==\r\nSome text.\r\n{{Anchors|Nineteentwenties}}\r\n===1920s===\r\nBar"
    assert genfixes.fix_headings(correct, r"Test") == correct, (
        r"no change to anchor just before L3 heading"
    )
    correct = "Foo\r\n\r\n==Some heading==\r\nSome text.\r\n{{Anchors|Nineteentwenties}}\r\n===1920s===\r\n\r\nBar"
    assert genfixes.fix_headings(correct, r"Test") == correct, (
        r"no change to anchor just before L3 heading - newline after"
    )


def test_test_fix_headings_blank_line_before_en_only() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n\r\n==1920s==\r\nBar"
    S = set_lang(r"fr")
    assert genfixes.fix_headings("Foo\r\n==1920s==\r\nBar", r"Test") == "Foo\r\n==1920s==\r\nBar", (
        r"No change – not en wiki"
    )
    S = set_lang(r"en")
    assert genfixes.fix_headings("Foo\r\n==1920s==\r\nBar", r"Test") == correct, (
        r"inserts blank line if one missing"
    )


def test_test_fix_headings_blank_line_comment_before() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n\r\n<!--comm-->\r\n==1920s==\r\nBar"
    assert genfixes.fix_headings(correct, r"Test") == correct, (
        r"no change when already one blank line -comment before"
    )
    correct = "Foo\r\n<!--comm-->\r\n==1920s==\r\nBar"
    assert genfixes.fix_headings(correct, r"Test") == correct, r"no change when comment before"


def test_test_fix_headings_bad_headers() -> None:
    S = W.for_site(EN)
    assert r"==Introduction==" not in genfixes.fix_headings(
        "==Introduction==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start"
    assert r"==Introduction:==" not in genfixes.fix_headings(
        "==Introduction:==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start, with colon"
    assert r"Introduction" not in genfixes.fix_headings(
        "=='''Introduction'''==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start, with bold"
    assert r"=='''Introduction:'''==" not in genfixes.fix_headings(
        "=='''Introduction:'''==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start, with bold and colon"
    assert r"===Introduction===" not in genfixes.fix_headings(
        "===Introduction===\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start, level 3"
    assert r"==About==" not in genfixes.fix_headings("==About==\r\n'''Foo''' great.", r"Foo"), (
        r"Excess heading at start About"
    )
    assert r"==Description==" not in genfixes.fix_headings(
        "==Description==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start Description"
    assert r"==Overview==" not in genfixes.fix_headings(
        "==Overview==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start Overview"
    assert r"==Definition==" not in genfixes.fix_headings(
        "==Definition==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start Definition"
    assert r"==Profile==" not in genfixes.fix_headings("==Profile==\r\n'''Foo''' great.", r"Foo"), (
        r"Excess heading at start Profile"
    )
    assert r"==General information==" not in genfixes.fix_headings(
        "==General information==\r\n'''Foo''' great.", r"Foo"
    ), r"Excess heading at start General information"
    assert (
        genfixes.fix_headings("==Introduction==\r\n'''Foo''' great.", r"Foo")
        == "\r\n'''Foo''' great."
    ), r"Removes unnecessary general headers from start of article"
    assert genfixes.fix_headings("==Foo==\r\nReally great", r"Foo") == r"Really great", (
        r"Removes heading if it matches pagetitle"
    )
    L3 = "Great article\r\n\r\n==A==\r\n\r\n===Foo===\r\nReally great"
    assert genfixes.fix_headings(L3, r"Foo") == L3, (
        r"Does not remove level 3 heading that matches pagetitle"
    )
    HeadingNotAtStart = "Foo is great.\r\n\r\n==Overview==\r\nHere there"
    assert genfixes.fix_headings(HeadingNotAtStart, r"Foo") == HeadingNotAtStart, (
        r"Heading not removed when not at start of article"
    )
    assert genfixes.fix_headings("==Weblinks==\r\n* Foo", r"foo") == "==External links==\r\n* Foo"
    assert (
        genfixes.fix_headings("==Outside links==\r\n* Foo", r"foo") == "==External links==\r\n* Foo"
    )
    assert (
        genfixes.fix_headings("==external Links==\r\n* Foo", r"foo")
        == "==External links==\r\n* Foo"
    )


def test_test_fix_headings_dupe_headings() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_headings(
            "Article.<ref>a</ref>\r\n\r\n==References==\r\n\r\n==References==\r\n{{reflist}}",
            r"foo",
        )
        == "Article.<ref>a</ref>\r\n\r\n==References==\r\n{{reflist}}"
    )
    assert (
        genfixes.fix_headings(
            "Article.<ref>a</ref>\r\n\r\n==References==\r\n\r\n== References ==\r\n{{reflist}}",
            r"foo",
        )
        == "Article.<ref>a</ref>\r\n\r\n==References==\r\n{{reflist}}"
    )
    assert (
        genfixes.fix_headings(
            "Article.<ref>a</ref>\r\n\r\n== References ==\r\n\r\n== References ==\r\n{{reflist}}",
            r"foo",
        )
        == "Article.<ref>a</ref>\r\n\r\n== References ==\r\n{{reflist}}"
    )
    assert (
        genfixes.fix_headings(
            "Article.\r\n\r\n== Random heading ==\r\n\r\n== Random heading ==\r\nText.", r"foo"
        )
        == "Article.\r\n\r\n== Random heading ==\r\nText."
    )


def test_unbalanced_headings() -> None:
    S = W.for_site(EN)
    assert r"==External links==" in genfixes.fix_headings("==External links=\r\n*Foo", r"Bar")
    assert r"==References==" in genfixes.fix_headings("==References=\r\n{{Reflist}}", r"Bar")
    assert r"==See also==" in genfixes.fix_headings("==See also=\r\n*Foo1\r\n*Foo2", r"Bar")


def test_newlinesin_lists() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.remove_white_space("The following items:\r\n* ab\r\n\r\n* ac")
        == "The following items:\r\n* ab\r\n* ac"
    )
    assert (
        genfixes.remove_white_space("The following items:\r\n* ab\r\n     \r\n* ac")
        == "The following items:\r\n* ab\r\n* ac"
    ), r"Newlines with spaces cleaned"
    assert (
        genfixes.remove_white_space("The following items:\r\n\r\n* ab\r\n\r\n* ac\r\n\r\n* ad")
        == "The following items:\r\n\r\n* ab\r\n* ac\r\n* ad"
    )
    TwoNewLines = "The following items:\r\n\r\n* ab\r\n* ac\r\n\r\n\r\n* ba\r\n* bb"
    assert genfixes.remove_white_space(TwoNewLines) == TwoNewLines, (
        r"No change to two or more newlines between list items, could be two separate lists"
    )
    TwoNewLines = (
        "The following items:\r\n\r\n* ab\r\n* ac\r\n\r\n\r\n* [http://www.foo.com ba]\r\n* bb"
    )
    assert genfixes.remove_white_space(TwoNewLines) == TwoNewLines, (
        r"No change to two or more newlines between list items, could be two separate lists"
    )


def test_test_mdashes_page_ranges() -> None:
    S = W.for_site(EN)
    assert parser.mdashes(r"pp. 55-57", r"test") == r"pp. 55–57"
    assert parser.mdashes(r"pp. 55--57", r"test") == r"pp. 55–57"
    assert parser.mdashes(r"pp.&nbsp;55-57", r"test") == r"pp.&nbsp;55–57"
    assert parser.mdashes(r"pp. 55 - 57", r"test") == r"pp. 55 – 57"
    assert parser.mdashes(r"Pp. 55 - 57", r"test") == r"pp. 55 – 57"
    assert parser.mdashes(r"pp 55-57", r"test") == r"pp 55–57"
    assert parser.mdashes(r"pp 1155-1157", r"test") == r"pp 1155–1157"
    assert parser.mdashes(r"pages= 55-57", r"test") == r"pages= 55–57"
    assert parser.mdashes(r"pages = 55-57", r"test") == r"pages = 55–57"
    assert parser.mdashes(r"pages=55-57", r"test") == r"pages=55–57"
    assert parser.mdashes(r"pages=55—57", r"test") == r"pages=55–57"
    assert parser.mdashes(r"pages=55&#8212;57", r"test") == r"pages=55–57"
    assert parser.mdashes(r"pages=55&mdash;57", r"test") == r"pages=55–57"
    assert parser.mdashes(r"pages=55–57", r"test") == r"pages=55–57"


def test_test_mdashes_other_ranges() -> None:
    S = W.for_site(EN)
    assert parser.mdashes(r"55-57 miles", r"test") == r"55–57 miles"
    assert parser.mdashes(r"55-57 kg", r"test") == r"55–57 kg"
    assert parser.mdashes(r"55 - 57 kg", r"test") == r"55 – 57 kg"
    assert parser.mdashes(r"55&#8212;57 kg", r"test") == r"55–57 kg"
    assert parser.mdashes(r"55&mdash;57 kg", r"test") == r"55–57 kg"
    assert parser.mdashes(r"55-57&nbsp;kg", r"test") == r"55–57&nbsp;kg"
    assert parser.mdashes(r"55-57 Hz", r"test") == r"55–57 Hz"
    assert parser.mdashes(r"55-57 GHz", r"test") == r"55–57 GHz"
    assert parser.mdashes(r"55 - 57 m long", r"test") == r"55 – 57 m long"
    assert parser.mdashes(r"55 - 57 feet", r"test") == r"55 – 57 feet"
    assert parser.mdashes(r"55 - 57 foot", r"test") == r"55 – 57 foot"
    assert parser.mdashes(r"long (55 - 57 in) now", r"test") == r"long (55 – 57 in) now"
    assert parser.mdashes(r"55-57 meters", r"test") == r"55–57 meters"
    assert parser.mdashes(r"55-57 metres", r"test") == r"55–57 metres"
    dimensions = r"around 34-24-34 in (86-60-86&nbsp;cm) and"
    assert parser.mdashes(dimensions, r"test") == dimensions
    assert parser.mdashes(r"$55-57", r"test") == r"$55–57"
    assert parser.mdashes(r"$55 - 57", r"test") == r"$55 – 57"
    assert parser.mdashes(r"$55-57", r"test") == r"$55–57"
    assert parser.mdashes(r"$1155-1157", r"test") == r"$1155–1157"
    assert parser.mdashes(r"$55&mdash;57", r"test") == r"$55–57"
    assert parser.mdashes(r"$55&#8212;57", r"test") == r"$55–57"
    assert parser.mdashes(r"$55—57", r"test") == r"$55–57"
    assert parser.mdashes(r"5:17 AM - 5:19 AM", r"test") == r"5:17 AM – 5:19 AM"
    assert parser.mdashes(r"5:17 am - 5:19 am", r"test") == r"5:17 am – 5:19 am"
    assert parser.mdashes(r"05:17 AM - 05:19 AM", r"test") == r"05:17 AM – 05:19 AM"
    assert parser.mdashes(r"11:17 PM - 11:19 PM", r"test") == r"11:17 PM – 11:19 PM"
    assert parser.mdashes(r"11:17 pm - 11:19 pm", r"test") == r"11:17 pm – 11:19 pm"
    assert parser.mdashes(r"11:17 pm &mdash; 11:19 pm", r"test") == r"11:17 pm – 11:19 pm"
    assert parser.mdashes(r"11:17 pm &#8212; 11:19 pm", r"test") == r"11:17 pm – 11:19 pm"
    assert parser.mdashes(r"11:17 pm — 11:19 pm", r"test") == r"11:17 pm – 11:19 pm"
    assert parser.mdashes(r"Aged 5–9", r"test") == r"Aged 5–9"
    assert parser.mdashes(r"Aged 5–11", r"test") == r"Aged 5–11"
    assert parser.mdashes(r"Aged 5 – 9", r"test") == r"Aged 5 – 9"
    assert parser.mdashes(r"Aged 15–19", r"test") == r"Aged 15–19"
    assert parser.mdashes(r"Ages 15–19", r"test") == r"Ages 15–19"
    assert parser.mdashes(r"Aged 15–19", r"test") == r"Aged 15–19"
    assert parser.mdashes(r"(ages 15-18)", r"test") == r"(ages 15–18)"
    assert parser.mdashes(r"Now 1…3 was", r"test") == r"Now 1...3 was"
    S = set_lang(r"fr")
    assert parser.mdashes(r"Now 1…3 was", r"test") == r"Now 1…3 was", (
        r"No elipsis change on fr-wiki"
    )
    S = set_lang(r"uk")
    assert parser.mdashes(r"Now 1…3 was", r"test") == r"Now 1…3 was", (
        r"No elipsis change on uk-wiki"
    )
    S = set_lang(r"en")


def test_test_mdashes() -> None:
    S = W.for_site(EN)
    assert (
        parser.mdashes(
            r"Djali Zwan made their live debut as a quartet -- Corgan, Sweeney, Pajo and Chamberlin -- at the end of 2001",
            r"test",
        )
        == r"Djali Zwan made their live debut as a quartet—Corgan, Sweeney, Pajo and Chamberlin—at the end of 2001"
    )
    assert (
        parser.mdashes(
            r"Djali Zwan made their live debut as a quartet --  Corgan, Sweeney, Pajo and Chamberlin --at the end of 2001",
            r"test",
        )
        == r"Djali Zwan made their live debut as a quartet—Corgan, Sweeney, Pajo and Chamberlin—at the end of 2001"
    )
    assert (
        parser.mdashes(
            r"Djali Zwan made their live debut as a quartet -- Corgan, Sweeney, Pajo and Chamberlin--at the end of 2001",
            r"test",
        )
        == r"Djali Zwan made their live debut as a quartet—Corgan, Sweeney, Pajo and Chamberlin—at the end of 2001"
    )
    assert parser.mdashes(r"Eugene Ormandy--who later", r"test") == r"Eugene Ormandy—who later"
    genFixes.assert_change(r"[[Eugene Ormandy]]--who later", r"[[Eugene Ormandy]]—who later")
    genFixes.assert_not_changed(r"now the domain xn-- was")
    genFixes.assert_not_changed(
        r"Djali Zwan made their live debut as a quartet -- Corgan, Sweeney, Pajo and Chamberlin -- at the end of 2001",
        r"Template:test",
    )
    assert (
        parser.mdashes(
            r"Djali Zwan made their live debut as a quartet --- Corgan, Sweeney, Pajo and Chamberlin - at the end of 2001",
            r"test",
        )
        == r"Djali Zwan made their live debut as a quartet --- Corgan, Sweeney, Pajo and Chamberlin - at the end of 2001"
    )
    assert parser.mdashes(r"m<sup>-33</sup>", r"test") == r"m<sup>−33</sup>"
    assert parser.mdashes(r"m<sup>-3324</sup>", r"test") == r"m<sup>−3324</sup>"
    assert parser.mdashes(r"m<sup>-2</sup>", r"test") == r"m<sup>−2</sup>"
    assert parser.mdashes(r"m<sup>–2</sup>", r"test") == r"m<sup>−2</sup>"
    assert parser.mdashes(r"m<sup>—2</sup>", r"test") == r"m<sup>−2</sup>"
    assert parser.mdashes(r"m<sup>−2</sup>", r"test") == r"m<sup>−2</sup>"
    assert parser.mdashes(r"m<sup>2</sup>", r"test") == r"m<sup>2</sup>"
    assert parser.mdashes(r"beaten 55 - 57 in 2004", r"test") == r"beaten 55 - 57 in 2004"
    assert (
        parser.mdashes(r"from 1904 – 11 May 1956 there", r"test")
        == r"from 1904 – 11 May 1956 there"
    )
    assert parser.mdashes(r"55--77", r"test") == r"55–77"


def test_test_title_dashes() -> None:
    S = W.for_site(EN)
    assert (
        parser.mdashes(r"The Alpher-Bethe-Gamow paper is great.", r"Alpher–Bethe–Gamow paper")
        == r"The Alpher–Bethe–Gamow paper is great."
    )
    assert (
        parser.mdashes(
            r"The Alpher-Bethe-Gamow paper is great. The Alpher-Bethe-Gamow paper is old.",
            r"Alpher—Bethe—Gamow paper",
        )
        == r"The Alpher—Bethe—Gamow paper is great. The Alpher—Bethe—Gamow paper is old."
    )
    assert (
        parser.mdashes(r"The Alpher-Bethe-Gamow paper is great.", r"Alpher-Bethe-Gamow paper")
        == r"The Alpher-Bethe-Gamow paper is great."
    )


def test_test_bullet_list_whitespace() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.remove_all_white_space("*    item\r\n*            item2\r\n* item3")
        == "* item\r\n* item2\r\n* item3"
    )
    assert (
        genfixes.remove_all_white_space("#    item\r\n#            item2\r\n# item3")
        == "# item\r\n# item2\r\n# item3"
    )
    assert (
        genfixes.remove_all_white_space("#    item\r\n#            item2\r\n#item3")
        == "# item\r\n# item2\r\n#item3"
    )


def test_remove_all_white_space_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.remove_all_white_space(r"now a") == r"now a"
    assert genfixes.remove_all_white_space("now\r\n\r\n* foo") == "now\r\n* foo"
    assert genfixes.remove_all_white_space(r"now   was") == r"now was"
    assert genfixes.remove_all_white_space("now\r\nwas") == "now\r\nwas"
    assert genfixes.remove_all_white_space("==hi==\r\n\r\nwas") == "==hi==\r\nwas"
    assert (
        genfixes.remove_all_white_space(r"18 March 1980 – 12 June 1993")
        == r"18 March 1980 – 12 June 1993"
    ), r"endash spacing not changed, may be correct"
    assert genfixes.remove_all_white_space(r"in 1980 &mdash; very") == r"in 1980&mdash;very", (
        r"mdash spacing cleaned"
    )


def test_fix_temperatures_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_temperatures(r"5ºC today") == r"5°C today"
    assert genfixes.fix_temperatures(r"5ºc today") == r"5°C today"
    assert genfixes.fix_temperatures(r"5º C today") == r"5°C today"
    assert genfixes.fix_temperatures(r"5°C today") == r"5°C today"
    assert genfixes.fix_temperatures(r"5&nbsp;°C today") == r"5&nbsp;°C today"
    assert genfixes.fix_temperatures(r"5&nbsp;ºC today") == r"5&nbsp;°C today"
    assert genfixes.fix_temperatures(r"5°    C today") == r"5°C today"
    assert genfixes.fix_temperatures(r"5°C today") == r"5°C today"
    assert genfixes.fix_temperatures(r"5°F today") == r"5°F today"
    assert genfixes.fix_temperatures(r"75°f today") == r"75°F today"
    assert genfixes.fix_temperatures(r"5ºCC") == r"5ºCC"


def test_fix_ordinal_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"1<sup>st</sup> day at school") == r"1st day at school", r"1st"
    assert genfixes.fix_syntax(r"2<sup>nd</sup> day at school") == r"2nd day at school", r"2nd"
    assert genfixes.fix_syntax(r"3<sup>rd</sup> day at school") == r"3rd day at school", r"3rd"
    assert genfixes.fix_syntax(r"4<sup>th</sup> day at school") == r"4th day at school", r"4th"
    assert genfixes.fix_syntax(r"1<sup>st </sup> day at school") == r"1st day at school", (
        r"1st with whitespace"
    )
    assert genfixes.fix_syntax(r"1<sup> st </sup> day at school") == r"1st day at school", (
        r"1st with whitespace"
    )


def test_fix_small_tags() -> None:
    S = W.for_site(EN)
    s1 = r"<small>foo</small>"
    assert genfixes.fix_syntax(s1) == s1
    assert genfixes.fix_syntax(r"<ref><small>foo</small></ref>") == r"<ref>foo</ref>", (
        r"removes small from ref tags"
    )
    assert genfixes.fix_syntax(r"<REF><small>foo</small></REF>") == r"<REF>foo</REF>", (
        r"removes small from ref tags"
    )
    assert genfixes.fix_syntax(r"<sup><small>foo</small></sup>") == r"<sup>foo</sup>", (
        r"removes small from sup tags"
    )
    assert genfixes.fix_syntax(r"<sub><small>foo</small></sub>") == r"<sub>foo</sub>", (
        r"removes small from sub tags"
    )
    assert (
        genfixes.fix_syntax(r"<small>a <small>foo</small> b</small>") == r"<small>a foo b</small>"
    ), r"removes nested small from small tags"
    assert genfixes.fix_syntax(r"<small><ref>foo</ref></small>") == r"<ref>foo</ref>", (
        r"removes small around ref tags"
    )
    assert genfixes.fix_syntax(r"<small><REF>foo</REF></small>") == r"<REF>foo</REF>", (
        r"removes small around ref tags"
    )
    assert genfixes.fix_syntax(r"<small><sup>foo</sup></small>") == r"<sup>foo</sup>", (
        r"removes small around sup tags"
    )
    assert genfixes.fix_syntax(r"<small><sub>foo</sub></small>") == r"<sub>foo</sub>", (
        r"removes small around sub tags"
    )
    unclosedTag = r"<ref><small>foo</small></ref> now <small>"
    assert genfixes.fix_syntax(unclosedTag) == unclosedTag
    unclosedTag2 = "<small>\r\n{|\r\n...<small><ref>foo</ref></small>...\r\n|}</small>"
    assert genfixes.fix_syntax(unclosedTag2) == unclosedTag2, (
        r"No change to small tags across table end, implies multiple incorrect small tags"
    )
    NoSmall = r"<ref>foo</ref> <small>A</small>"
    assert genfixes.fix_syntax(NoSmall) == NoSmall, (
        r"No change when no small that should be removed"
    )


def test_fix_small_tags_image_descriptions() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"[[File:foo.jpg|<small>bar</small>]]") == r"[[File:foo.jpg|bar]]", (
        r"removes small from image descriptions"
    )
    assert (
        genfixes.fix_syntax(r"[[File:foo.jpg|thumb|<small>bar</small>]]")
        == r"[[File:foo.jpg|thumb|bar]]"
    ), r"removes small from image descriptions when other parameters too"
    FileCaptionLegend = "[[File:foo.jpg|This text is a caption\r\n{{legend|foo|<small>a</small>}}\r\n{{legend|foo2|<small>b</small>}}\r\n]]"
    assert genfixes.fix_syntax(FileCaptionLegend) == FileCaptionLegend, (
        r"small tag not removed from legend template"
    )


def test_load_template_redirects() -> None:
    # Hand-ported. AWB returns Dictionary<Regex, string> and sets WikiRegexes.AllTemplateRedirects;
    # AWB-X returns a TemplateRedirectRules holding both.
    template_redirects = []
    assert list(genfixes.load_template_redirects("").rules) == template_redirects, (
        "returns empty dictionary when no rules present"
    )
    template_redirects.append("Citation needed")
    rules = genfixes.load_template_redirects("{{tl|Cn}} → {{tl|Citation needed}}")
    assert [v for _, v in rules.rules] == template_redirects, "loads single redirect rules"
    rules = genfixes.load_template_redirects("{{tl|Cn}} → '''{{tl|Citation needed}}'''")
    assert [v for _, v in rules.rules] == template_redirects, "loads single redirect rules"
    assert rules.all_redirects_regex is not None
    assert rules.all_redirects_regex.is_match("{{cn}}")
    rules = genfixes.load_template_redirects("{{tl|Cn}}, {{tl|fact}} → {{tl|Citation needed}}")
    assert [v for _, v in rules.rules] == template_redirects, "loads multiple redirect rules"
    assert rules.all_redirects_regex is not None
    assert rules.all_redirects_regex.is_match("{{cn}}")
    assert rules.all_redirects_regex.is_match("{{fact}}")


def test_load_dated_templates() -> None:
    S = W.for_site(EN)
    DatedTemplates = []
    assert genfixes.load_dated_templates(r"") == DatedTemplates, (
        r"returns empty list when no rules present"
    )
    assert genfixes.load_dated_templates(r"<!--{{tl|wikif-->") == DatedTemplates, (
        r"ignores commented out rules"
    )
    DatedTemplates.append(r"Wikify")
    assert str(genfixes.load_dated_templates(r"{{tl|wikify}}")) == str(DatedTemplates), (
        r"loads single rule"
    )
    DatedTemplates.append(r"Citation needed")
    assert str(genfixes.load_dated_templates("{{tl|wikify}}\r\n{{tl|citation needed}}")) == str(
        DatedTemplates
    ), r"loads multiple rules"


def test_template_redirects() -> None:
    S = W.for_site(EN)
    # AWB: empty dictionary and WikiRegexes.AllTemplateRedirects = null
    TemplateRedirs = genfixes.TemplateRedirectRules()
    assert genfixes.template_redirects(r"now {{Cn}} was", TemplateRedirs) == r"now {{Cn}} was", (
        r"no change when redirects dictionary not built"
    )
    TemplateRedirs = genfixes.load_template_redirects(
        r"{{tl|Cn}}, {{tl|fact}} → {{tl|Citation needed}}"
    )
    assert genfixes.template_redirects(r"now was", TemplateRedirs) == r"now was", (
        r"no change when no templates in text"
    )
    assert (
        genfixes.template_redirects(r"now {{Cn}} was", TemplateRedirs)
        == r"now {{Citation needed}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{cn}} was", TemplateRedirs)
        == r"now {{citation needed}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{cn}} was{{fact}} or", TemplateRedirs)
        == r"now {{citation needed}} was{{citation needed}} or"
    ), r"renames multiple different redirects"
    assert (
        genfixes.template_redirects(r"now {{cn}} was{{cn}} or", TemplateRedirs)
        == r"now {{citation needed}} was{{citation needed}} or"
    ), r"renames multiple redirects"
    assert (
        genfixes.template_redirects("now {{one|\r\n{{cn}} \r\n}}", TemplateRedirs)
        == "now {{one|\r\n{{citation needed}} \r\n}}"
    ), r"renames when template nested"
    assert (
        genfixes.template_redirects("now {{fact|\r\n{{cn}} \r\n}}", TemplateRedirs)
        == "now {{citation needed|\r\n{{citation needed}} \r\n}}"
    ), r"renames nested templates, both levels"
    assert (
        genfixes.template_redirects("now {{one|\r\n{{two|\r\n{{cn}} \r\n}}}}", TemplateRedirs)
        == "now {{one|\r\n{{two|\r\n{{citation needed}} \r\n}}}}"
    ), r"renames when template double nested"
    TemplateRedirs = genfixes.load_template_redirects(
        r"{{tl|Cn}}, {{tl|fact}} → {{tl|citation needed}}"
    )
    assert (
        genfixes.template_redirects(r"now {{cn}} was", TemplateRedirs)
        == r"now {{citation needed}} was"
    ), r"follows case of new template name"
    assert (
        genfixes.template_redirects(r"now {{Cn}} was", TemplateRedirs)
        == r"now {{Citation needed}} was"
    ), r"follows case of new template name"
    TemplateRedirs = genfixes.load_template_redirects(
        "{{tl|Cn}}, {{tl|fact}} → {{tl|citation needed}}\r\n{{tl|foo}} → {{tl|bar}}"
    )
    assert (
        genfixes.template_redirects(r"now {{cn}} was", TemplateRedirs)
        == r"now {{citation needed}} was"
    ), r"follows case of new template name"
    TemplateRedirs = genfixes.load_template_redirects(
        "{{tl|Articleissues}} → {{tl|multiple issues}}\r\n{{tl|Rewrite}} → {{tl|cleanup-rewrite}}\r\n{{tl|Cn}}, {{tl|fact}} → {{tl|citation needed}}"
    )
    assert (
        genfixes.template_redirects(
            "now {{Articleissues|\r\n{{Refimprove|date=July 2012}}\r\n{{Citation style|date=July 2012}}\r\n{{Rewrite|date=July 2012}}\r\n}} was",
            TemplateRedirs,
        )
        == "now {{Multiple issues|\r\n{{Refimprove|date=July 2012}}\r\n{{Citation style|date=July 2012}}\r\n{{Cleanup-rewrite|date=July 2012}}\r\n}} was"
    ), r"nested template example"
    A = "{{Infobox musical artist\r\n| name       = A\r\n| birth_date  = {{Birth date and age|1989|10|17}}\r\n| genre      = [[Compas music|Konpa]]{{Cn|date=January 2013}}\r\n| label      = Recording\r\n| website        = {{URL|a.com}}\r\n}}"
    assert genfixes.template_redirects(A, TemplateRedirs) == A.replace(
        r"{{Cn", r"{{Citation needed"
    )
    B = r"{{ONE | {{TWO | {{THREE | {{Cn}} }} }} }}"
    assert genfixes.template_redirects(B, TemplateRedirs) == B.replace(
        r"{{Cn", r"{{Citation needed"
    )
    TemplateRedirs = genfixes.load_template_redirects(r"{{tl|Infobox Play}} → {{tl|Infobox play}}")
    assert (
        genfixes.template_redirects(r"{{Infobox_Play}}", TemplateRedirs) == r"{{Infobox play}}"
    ), r""
    TemplateRedirs = genfixes.load_template_redirects(
        r"{{tl|Display title}}, {{tl|Displaytitle}} → {{tl|DISPLAYTITLE}}"
    )
    assert (
        genfixes.template_redirects(r"now {{display title|Foo}} was", TemplateRedirs)
        == r"now {{DISPLAYTITLE:Foo}} was"
    ), r"Magic word template redirected and formatted"
    assert (
        genfixes.template_redirects(r"now {{displaytitle|Foo}} was", TemplateRedirs)
        == r"now {{DISPLAYTITLE:Foo}} was"
    ), r"Magic word template redirected and formatted"
    assert (
        genfixes.template_redirects(r"now {{Displaytitle|Foo}} was", TemplateRedirs)
        == r"now {{DISPLAYTITLE:Foo}} was"
    ), r"Magic word template redirected and formatted"


def test_template_redirects_acronyms() -> None:
    S = W.for_site(EN)
    theTemplateRedirects = genfixes.load_template_redirects(
        r"{{tl|fb}}, {{tl|foob}} → {{tl|FOO bar}}"
    )
    assert (
        genfixes.template_redirects(r"now {{fb}} was", theTemplateRedirects)
        == r"now {{FOO bar}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{Fb}} was", theTemplateRedirects)
        == r"now {{FOO bar}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{foob}} was", theTemplateRedirects)
        == r"now {{FOO bar}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{Foob}} was", theTemplateRedirects)
        == r"now {{FOO bar}} was"
    )
    theTemplateRedirects = genfixes.load_template_redirects(
        r"{{tl|fb}}, {{tl|foob}} → {{tl|fOO bar}}"
    )
    assert (
        genfixes.template_redirects(r"now {{fb}} was", theTemplateRedirects)
        == r"now {{fOO bar}} was"
    ), r"first letter case respected for non-acronym template"
    assert (
        genfixes.template_redirects(r"now {{Fb}} was", theTemplateRedirects)
        == r"now {{FOO bar}} was"
    )
    theTemplateRedirects = genfixes.load_template_redirects(
        r"{{tl|yt}}, {{tl|youtube}} → {{tl|YouTube}}"
    )
    assert (
        genfixes.template_redirects(r"now {{yt}} was", theTemplateRedirects)
        == r"now {{YouTube}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{Yt}} was", theTemplateRedirects)
        == r"now {{YouTube}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{youtube}} was", theTemplateRedirects)
        == r"now {{YouTube}} was"
    )
    assert (
        genfixes.template_redirects(r"now {{Youtube}} was", theTemplateRedirects)
        == r"now {{YouTube}} was"
    )


def test_rename_template_parameters() -> None:
    S = W.for_site(EN)
    RenamedTemplateParameters = genfixes.load_renamed_template_parameters(
        r"{{AWB rename template parameter|cite web|acccessdate|accessdate}}"
    )
    correct = (
        r"{{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}"
    )
    assert (
        genfixes.rename_template_parameters(
            correct.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == correct
    ), r"renames parameter in simple template call"
    correct2 = r"<ref>{{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}</ref><ref>{{cite web | url=http://www.site2.com | title = Testing2 | accessdate = 2 May 2009 }}</ref>"
    assert (
        genfixes.rename_template_parameters(
            correct2.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == correct2
    ), r"renames parameter in simple template call"
    correct2a = r"<ref>{{cite web | url=http://www.site.com | title = Testing |accessdate=20 May 2009 }}</ref><ref>{{cite web | url=http://www.site2.com | title = Testing2 |accessdate=2 May 2009 }}</ref>"
    assert (
        genfixes.rename_template_parameters(
            correct2a.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == correct2a
    ), r"renames parameter in simple template call, unspaced"
    correct2b = "<ref>{{cite web | url=http://www.site.com | title = Testing\r\n|accessdate=20 May 2009 }}</ref><ref>{{cite web | url=http://www.site2.com | title = Testing2 |accessdate=2 May 2009 }}</ref>"
    assert (
        genfixes.rename_template_parameters(
            correct2b.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == correct2b
    ), r"renames parameter in simple template call, newline"
    correct3 = (
        r"{{Cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}"
    )
    assert (
        genfixes.rename_template_parameters(
            correct3.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == correct3
    ), r"renames parameter in simple template call, handles first letter casing of template name"
    correct4 = (
        r"{{ cite_web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}"
    )
    assert (
        genfixes.rename_template_parameters(
            correct4.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == correct4
    ), r"renames parameter in simple template call, handles underscore in template name"
    Dupe = r"{{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2012 | acccessdate = 11 June 2012 }}"
    assert genfixes.rename_template_parameters(Dupe, RenamedTemplateParameters) == Dupe, (
        r"no change when target parameter already has a value"
    )
    Dupe2 = r"{{cite web | url=http://www.site.com | title = Testing | accessdate = | acccessdate = 11 June 2012 }}"
    assert (
        genfixes.rename_template_parameters(Dupe2, RenamedTemplateParameters)
        == r"{{cite web | url=http://www.site.com | title = Testing | accessdate = | accessdate = 11 June 2012 }}"
    ), r"changed when target parameter present without value"
    nested = r"{{reflist|refs={{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}}}"
    assert (
        genfixes.rename_template_parameters(
            nested.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == nested
    ), r"renames parameter in nested template call"
    nested2 = "{{reflist|refs={{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}\r\n{{cite web | url=http://www.site2.com | title = Testing2 | accessdate = 20 June 2009 }}}}"
    assert (
        genfixes.rename_template_parameters(
            nested2.replace(r"accessdate", r"acccessdate"), RenamedTemplateParameters
        )
        == nested2
    ), r"renames parameter in nested and unnested template calls"
    nomatch = (
        r"{{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }}"
    )
    assert genfixes.rename_template_parameters(nomatch, RenamedTemplateParameters) == nomatch, (
        r"No change when no matched parameters"
    )
    nomatch = r"{{cite web | url=http://www.site.com | title = Testing | accessdate = 20 May 2009 }} {{cn}}"
    assert genfixes.rename_template_parameters(nomatch, RenamedTemplateParameters) == nomatch, (
        r"No change when no matched parameters, other template"
    )
    nomatch = (
        r"{{cite news | url=http://www.site.com | title = Testing | acccessdate = 20 May 2009 }}"
    )
    assert genfixes.rename_template_parameters(nomatch, RenamedTemplateParameters) == nomatch, (
        r"No change when no matched templates"
    )


def test_load_renamed_template_parameters() -> None:
    # Hand-ported (foreach over the list was not converted).
    renamed = genfixes.load_renamed_template_parameters(
        "{{AWB rename template parameter|cite web|acccessdate|accessdate}}"
    )
    assert len(renamed) == 1
    for tp in renamed:
        assert tp.template_name == "cite web"
        assert tp.old_parameter == "acccessdate"
        assert tp.new_parameter == "accessdate"
    renamed = genfixes.load_renamed_template_parameters(
        "\r\n{{AWB rename template parameter|cite web|acccessdate|accessdate}}"
        "\r\n{{AWB rename template parameter|cite web|acessdate|accessdate}}"
    )
    assert len(renamed) == 2
