"""Port of AWB UnitTests/ParserTests.cs: parser fixes: conversions, images, multiple issues, bold title, unicodify, main article, MOS.

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


def test_test_fix_date_month_of_year() -> None:
    S = W.for_site(EN)
    assert (
        parser.fix_date_ordinals_and_of(r"Now in July of 2007 a new", r"test")
        == r"Now in July 2007 a new"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"Now ''Plaice'' in July of 2007 a new", r"test")
        == r"Now ''Plaice'' in July 2007 a new"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"Now in January of 1907 a new", r"test")
        == r"Now in January 1907 a new"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"Now in January of 1807 a new", r"test")
        == r"Now in January 1807 a new"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"Now in January of 1807 and May of 1804 a new", r"test")
        == r"Now in January 1807 and May 1804 a new"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 28 July of 2006 – 14 October of 2008 was", r"test")
        == r"On 28 July 2006 – 14 October 2008 was"
    )
    genFixes.assert_not_changed(r'Now "in July of 2007" a new')
    genFixes.assert_not_changed(r"Now {{quote|in July of 2007}} a new")
    genFixes.assert_not_changed(r'Now "in July of 1707" a new')
    genFixes.assert_not_changed(r"Now a march of 2007 resulted")
    genFixes.assert_not_changed(r"Now the June of 2007 was")


def test_test_fix_date_ordinals() -> None:
    S = W.for_site(EN)
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th March elections were", r"test")
        == r"On 14 March elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th June elections were", r"test")
        == r"On 14 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"14th June elections were", r"test")
        == r"14 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On March 14th elections were", r"test")
        == r"On March 14 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 21st elections were", r"test")
        == r"On June 21 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 21<sup>st</sup> elections were", r"test")
        == r"On June 21 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 21<sup> st </sup> elections were", r"test")
        == r"On June 21 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 21<SUP>st</SUP> elections were", r"test")
        == r"On June 21 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th March 2008 elections were", r"test")
        == r"On 14 March 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th June 2008 elections were", r"test")
        == r"On 14 June 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th June, 2008 elections were", r"test")
        == r"On 14 June 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14<sup>th</sup> June, 2008 elections were", r"test")
        == r"On 14 June 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On March 14th, 2008 elections were", r"test")
        == r"On March 14, 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June   21st, 2008 elections were", r"test")
        == r"On June 21, 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June   21st 2008 elections were", r"test")
        == r"On June 21, 2008 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th-15th June elections were", r"test")
        == r"On 14-15 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th - 15th June elections were", r"test")
        == r"On 14 - 15 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th to 15th June elections were", r"test")
        == r"On 14 to 15 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 14th to 15th elections were", r"test")
        == r"On June 14 to 15 elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th,15th June elections were", r"test")
        == r"On 14,15 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 3rd and 15th June elections were", r"test")
        == r"On 3 and 15 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On March 12th, 13th, 14th, 2008 elections were", r"test")
        == r"On March 12, 13, 14, 2008 elections were"
    )
    genFixes.assert_not_changed(r"On 14th march was")
    genFixes.assert_not_changed(r"Now the 14th February was")
    genFixes.assert_not_changed(r"Now the February 14th was")
    genFixes.assert_not_changed(r"Observance of 5th November Act")
    genFixes.assert_not_changed(r"'''6th October City''' is", r"6th October City")
    genFixes.assert_not_changed(r"<blockquote>On March 14th, 2008 elections were</blockquote>")


def test_fix_date_ordinals_and_of_en_only() -> None:
    S = W.for_site(EN)
    c1 = r"On 14th March elections were"
    S = set_lang(r"fr")
    assert parser.fix_date_ordinals_and_of(c1, r"test") == c1
    S = set_lang(r"en")
    assert parser.fix_date_ordinals_and_of(c1, r"test") == r"On 14 March elections were"


def test_test_fix_date_day_of_month() -> None:
    S = W.for_site(EN)
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th of February was", r"test")
        == r"On 14 February was"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 4th of February was", r"test") == r"On 4 February was"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 14th of  February was", r"test")
        == r"On 14 February was"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"14th of February 2009 was", r"test")
        == r"14 February 2009 was"
    )
    assert parser.fix_date_ordinals_and_of(r"24th of June 2009 was", r"test") == r"24 June 2009 was"
    genFixes.assert_not_changed(r"On the 14th of February 2009 was")
    genFixes.assert_not_changed(r"now foo [[File:9th of June street.jpg]] was")
    genFixes.assert_not_changed(r"now foo [[File:9th of June street , City.JPG|Caption]] was")
    genFixes.assert_not_changed(
        r"now foo [[File:9th of June street , City.JPG|On [[Main Article#Overview|9th of June]] Street]] was here"
    )
    genFixes.assert_not_changed(
        r"now foo [[File:9th of June street , Bacău.JPG|[[Main Article#Overview|9th of June]] Street]] was here"
    )
    genFixes.assert_not_changed(r"now foo <gallery>File:9th of June street.JPG</gallery> was here")
    genFixes.assert_not_changed(
        r"now foo <gallery>File:9th of June street , B.JPG</gallery> was here"
    )
    genFixes.assert_not_changed(
        "n<gallery>\r\nFile:9th of May_street, Bacău.jpg| Street\r\n</gallery>"
    )


def test_dates_leading_zeros() -> None:
    S = W.for_site(EN)
    assert (
        parser.fix_date_ordinals_and_of(r"On 03 June elections were", r"test")
        == r"On 3 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 07 June elections were", r"test")
        == r"On 7 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 07, elections were", r"test")
        == r"On June 7, elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On June 07 2008, elections were", r"test")
        == r"On June 7, 2008, elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 03rd June elections were", r"test")
        == r"On 3 June elections were"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 2 June 07, elections were", r"test")
        == r"On 2 June 07, elections were"
    )
    assert parser.fix_date_ordinals_and_of(r"The 007 march was", r"test") == r"The 007 march was"
    assert (
        parser.fix_date_ordinals_and_of(r"In June '08 there was", r"test")
        == r"In June '08 there was"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"In June 2008 there was", r"test")
        == r"In June 2008 there was"
    )
    assert (
        parser.fix_date_ordinals_and_of(r"On 00 June elections were", r"test")
        == r"On 00 June elections were"
    )
    assert parser.fix_date_ordinals_and_of(r"The 007 May was", r"test") == r"The 007 May was"
    assert (
        parser.fix_date_ordinals_and_of(r"On 27 June 2nd and 3rd Panzer Groups", r"test")
        == r"On 27 June 2nd and 3rd Panzer Groups"
    )


def test_determine_predominant_date_locale() -> None:
    S = W.for_site(EN)
    none = r"hello"
    American1 = r"On July 17, 2009 a"
    International1 = r"on 17 July 2009 a"
    ISO = r"now {{use ymd dates}} here"
    American2 = r"now {{use mdy dates}} here"
    International2 = r"{{use dmy dates}}"
    ISOmajority = r"on July 11, 2004 and 2009-11-12 and 2009-11-12 a"
    assert genfixes.determine_predominant_date_locale(none) == DateLocale.UNDETERMINED
    assert genfixes.determine_predominant_date_locale(none, True) == DateLocale.UNDETERMINED
    assert genfixes.determine_predominant_date_locale(American1) == DateLocale.AMERICAN
    assert genfixes.determine_predominant_date_locale(International1) == DateLocale.INTERNATIONAL
    assert genfixes.determine_predominant_date_locale(American2) == DateLocale.AMERICAN
    assert genfixes.determine_predominant_date_locale(International2) == DateLocale.INTERNATIONAL
    assert genfixes.determine_predominant_date_locale(ISO) == DateLocale.ISO
    assert genfixes.determine_predominant_date_locale(ISOmajority, True) == DateLocale.ISO
    assert genfixes.determine_predominant_date_locale(ISOmajority, False) == DateLocale.AMERICAN
    assert (
        genfixes.determine_predominant_date_locale(
            American1 + International1 + r"and 2009-01-04 the", True
        )
        == DateLocale.UNDETERMINED
    ), r"undetermined if count of all dates equal"
    assert (
        genfixes.determine_predominant_date_locale(
            American1 + International1 + International1 + r"and 2009-01-04 the", True
        )
        == DateLocale.UNDETERMINED
    ), r"undetermined if count of all dates too similar"
    bddf = r"{{birth date|df=y|1950|4|7}}"
    bdnone = r"{{birth date|1950|4|7}}"
    bdmf = r"{{birth date|mf=y|1950|4|7}}"
    assert genfixes.determine_predominant_date_locale(bddf) == DateLocale.INTERNATIONAL, (
        r"uses df=y as fallback"
    )
    assert genfixes.determine_predominant_date_locale(bdnone) == DateLocale.UNDETERMINED
    assert genfixes.determine_predominant_date_locale(bdmf) == DateLocale.AMERICAN, (
        r"uses mf=y as fallback"
    )


def test_predominant_dates() -> None:
    S = W.for_site(EN)
    c1 = r"{{cite web|url=http://www.foo.com/bar | title=text | date=2010-04-11 }}"
    useDMY = r"{{use dmy dates}}"
    c2 = r"{{cite web|url=http://www.foo.com/bar | title=text | date=2010-04-11 | accessdate= 2010-04-11 }}"
    assert genfixes.predominant_dates(c1) == c1, r"no change when no use xxx template"
    assert (
        genfixes.predominant_dates(c1 + useDMY)
        == c1.replace(r"2010-04-11", r"11 April 2010") + useDMY
    ), r"converts date to predominant format"
    assert (
        genfixes.predominant_dates(c2 + useDMY)
        == c2.replace(r"2010-04-11", r"11 April 2010") + useDMY
    ), r"converts multiple dates in same cite to predominant format"
    assert (
        genfixes.predominant_dates(c1.replace(r"2010-04-11", r"11 April 2010") + useDMY)
        == c1.replace(r"2010-04-11", r"11 April 2010") + useDMY
    ), r"no change when already correct"


def test_predominant_dates_en_only() -> None:
    S = W.for_site(EN)
    c1 = r"{{cite web|url=http://www.foo.com/bar | title=text | date=2010-04-11 }}"
    useDMY = r"{{use dmy dates}}"
    S = set_lang(r"fr")
    assert genfixes.predominant_dates(c1 + useDMY) == c1 + useDMY, r"no change on non-en wiki"
    S = set_lang(r"en")
    assert (
        genfixes.predominant_dates(c1 + useDMY)
        == c1.replace(r"2010-04-11", r"11 April 2010") + useDMY
    ), r"converts date to predominant format"


def test_removal() -> None:
    S = W.for_site(EN)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"Foo.jpg", r"[[Image:Foo.jpg]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"Foo.jpg", r"[[:Image:Foo.jpg]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"foo.jpg", r"[[Image: foo.jpg]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"Foo, bar", r"[[File:foo%2C_bar|quux]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"Foo%2C_bar", r"[[File:foo, bar|quux]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"foo.jpg", r"[[Media:foo.jpg]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"foo.jpg", r"[[:media : foo.jpg]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        (_t := genfixes.remove_image_no_change(r"foo", r"{{infobox|image=foo}}", False, r"")),
        (noChange := _t[1]),
    )[0][0] == r"{{infobox|image=}}"
    assert not (noChange)
    assert (
        (
            _t := genfixes.remove_image_no_change(
                r"foo", r"{{infobox|image=foo|other=bar}}", False, r""
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{infobox|image=|other=bar}}"
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"Foo, bar", r"[[File:foo%2C_bar|quux [[here]] there]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        (
            _t := genfixes.remove_image_no_change(
                r"Image:Bar.jpg",
                "<gallery>\r\nImage:foo.jpg\r\nImage:Bar.jpg</gallery>",
                False,
                r"",
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "<gallery>\r\nImage:foo.jpg\r\n</gallery>"
    assert (
        (
            _t := genfixes.remove_image_no_change(
                r"Image:Bar.jpg",
                "<gallery>\r\nImage:foo.jpg\r\nImage:Bar.jpg|Some text description\r\n</gallery>",
                False,
                r"",
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "<gallery>\r\nImage:foo.jpg\r\n\r\n</gallery>"
    assert (
        (
            (
                _t := genfixes.remove_image_no_change(
                    r"Image:Bar.jpg",
                    "<gallery>\r\nImage:foo.jpg\r\nImage:Bar.jpg|Some text description\r\n</gallery>",
                    True,
                    r"x",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "<gallery>\r\nImage:foo.jpg\r\n<!-- x Image:Bar.jpg|Some text description -->\r\n</gallery>"
    )
    assert (
        (_t := genfixes.remove_image_no_change(r"FOO.jpg", r"[[Media:foo.jpg]]", False, r"")),
        (noChange := _t[1]),
    )[0][0] == r"[[Media:foo.jpg]]", r"image name is case sensitive"
    assert noChange
    assert (
        (_t := genfixes.remove_image_no_change(r"", r"[[Media:foo.jpg]]", False, r"")),
        (noChange := _t[1]),
    )[0][0] == r"[[Media:foo.jpg]]", r"no change when blank image name input"
    assert noChange


def test_removal_multiple_lines() -> None:
    S = W.for_site(EN)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_image_no_change(
                        r"Foo, bar", "[[File:foo%2C_bar|quux [[here]]\r\nthere]]", False, r""
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        (
            _t := genfixes.remove_image_no_change(
                r"Foo, bar", r"[[File:foo%2C_bar|quux [[here]] there]] [[now]]", False, r""
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r" [[now]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.remove_image_no_change(
                r"Foo, bar", r"[[File:foo%2C_bar|quux there]] [[now]]", False, r""
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r" [[now]]"
    assert not (noChange)


def test_replacement() -> None:
    S = W.for_site(EN)
    assert (
        len(((_t := genfixes.replace_image_no_change(r"", r"", r"")), (noChange := _t[1]))[0][0])
        == 0
    )
    assert noChange
    assert (
        (_t := genfixes.replace_image_no_change(r"foo", r"bar", r"[[File:Foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[File:bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.replace_image_no_change(r"foo", r"bar", r"[[image:Foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Image:bar]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.replace_image_no_change(
                r"Foo%2C_bar", r"bar", r"[[FIle:foo, bar|boz!|666px]]"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[File:bar|boz!|666px]]"
    assert not (noChange)
    assert (
        (_t := genfixes.replace_image_no_change(r"foo", r"bar", r"[[Media:foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Media:bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.replace_image_no_change(r"foo", r"bar", r"[[:media : foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[:media:bar]]"
    assert not (noChange)


def test_dont_embolden_images_and_templates() -> None:
    S = W.for_site(EN)
    assert (
        r"'''Foo'''"
        not in ((_t := parser.bold_title(r"[[Image:Foo.jpg]]", r"Foo")), (noChangeBack := _t[1]))[
            0
        ][0]
    )
    assert (
        r"'''Foo'''"
        not in ((_t := parser.bold_title(r"{{Foo}}", r"Foo")), (noChangeBack := _t[1]))[0][0]
    )
    assert (
        r"'''Foo'''"
        not in (
            (_t := parser.bold_title(r"{{template| Foo is a bar}}", r"Foo")),
            (noChangeBack := _t[1]),
        )[0][0]
    )


def test_dates_not_changed() -> None:
    S = W.for_site(EN)
    assert (
        (_t := parser.bold_title(r"May 31 is a great day", r"May 31")),
        (noChangeBack := _t[1]),
    )[0][0] == r"May 31 is a great day"
    assert noChangeBack
    assert (
        (_t := parser.bold_title(r"March 1 is a great day", r"March 1")),
        (noChangeBack := _t[1]),
    )[0][0] == r"March 1 is a great day"
    assert noChangeBack
    assert (
        (_t := parser.bold_title(r"31 May is a great day", r"31 May")),
        (noChangeBack := _t[1]),
    )[0][0] == r"31 May is a great day"
    assert noChangeBack


def test_similar_links_with_different_case_not_changed() -> None:
    S = W.for_site(EN)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo is this one, now [[FOO]] is another While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is this one, now [[FOO]] is another While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"'''Foo''' is this one, now [[FOO]] is another While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is this one, now [[FOO]] is another While remaining upright may be the primary goal of beginning riders"
    )
    assert noChangeBack


def test_dont_change_if_already_bold() -> None:
    S = W.for_site(EN)
    assert ((_t := parser.bold_title(r"'''Foo''' is this one", r"Foo")), (noChangeBack := _t[1]))[
        0
    ][0] == r"'''Foo''' is this one"
    assert noChangeBack
    assert (
        (_t := parser.bold_title(r"Foo is a bar, '''Foo''' moar", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"Foo is a bar, '''Foo''' moar"
    assert noChangeBack
    assert (
        (_t := parser.bold_title(r"{{Infobox | name = Foo | age=11}} '''Foo''' is a bar", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"{{Infobox | name = Foo | age=11}} '''Foo''' is a bar"
    assert noChangeBack
    assert (
        (
            _t := parser.bold_title(
                "{{Infobox\r\n| age=11}} '''John David Smith''' is a bar", r"John Smith"
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == "{{Infobox\r\n| age=11}} '''John David Smith''' is a bar"
    assert noChangeBack
    assert (
        (
            _t := parser.bold_title(
                r"{{Infobox| age=11}} '''John David Smith''' is a bar, John Smith", r"John Smith"
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"{{Infobox| age=11}} '''John David Smith''' is a bar, John Smith"
    assert noChangeBack
    assert (
        (
            _t := parser.bold_title(
                "{{Infobox\r\n| age=11}}{{box2}}} '''John David Smith''' is a bar", r"John Smith"
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == "{{Infobox\r\n| age=11}}{{box2}}} '''John David Smith''' is a bar"
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    r"'''Now''' Foo is a bar While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Now''' Foo is a bar While remaining upright may be the primary goal of beginning riders"
    )
    assert noChangeBack
    assert ((_t := parser.bold_title(r"''Foo'' is this one", r"Foo")), (noChangeBack := _t[1]))[0][
        0
    ] == r"''Foo'' is this one"
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    "{{Infobox martial art| website      = }}\r\n{{Nihongo|'''Aikido'''|???|aikido}} is a. Aikido was",
                    r"Aikido",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Infobox martial art| website      = }}\r\n{{Nihongo|'''Aikido'''|???|aikido}} is a. Aikido was"
    )
    assert noChangeBack
    assert (
        (
            _t := parser.bold_title(
                "{{Infobox martial art| name='''Aikido'''| website      = }}\r\nAikido was",
                r"Aikido",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == "{{Infobox martial art| name='''Aikido'''| website      = }}\r\n'''Aikido''' was", (
        r"Bold text in infobox ignored"
    )
    assert not (noChangeBack)
    NoChangeImages = "[[Image:098098889899899889089980890890.png|2390823424890243 23980324 234098234980]] [[Image:098098889899899889089980890890.png|2390823424890243 23980324 234098234980]]\r\n            [[Image:098098889899899889089980890890.png|2390823424890243 23980324 234098234980]] [[Image:098098889899899889089980890890.png|2390823424890243 23980324 234098234980]]\r\n'''A''' was. Foo One here"
    assert ((_t := parser.bold_title(NoChangeImages, r"Foo One")), (noChangeBack := _t[1]))[0][
        0
    ] == NoChangeImages
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    r"{{year article header}} Foo is a bar While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"{{year article header}} Foo is a bar While remaining upright may be the primary goal of beginning riders"
    )
    assert noChangeBack
    assert (
        (
            _t := parser.bold_title(
                r"{{bio}} Foo is a bar While remaining upright may be the primary goal of beginning riders",
                r"Foo",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][
        0
    ] == r"{{bio}} Foo is a bar While remaining upright may be the primary goal of beginning riders"
    assert noChangeBack
    assert (
        (_t := parser.bold_title(r"<dfn>Foo</dfn> is this one", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"<dfn>Foo</dfn> is this one"
    assert noChangeBack


def test_exceptions() -> None:
    S = W.for_site(EN)
    Section = r"<section>'''[[Foo]]''' bar</section>"
    assert ((_t := parser.bold_title(Section, r"Foo")), (noChange := _t[1]))[0][0] == Section, (
        r"No change when article text contains <section> tags"
    )
    Section = r"{{year article header}} Foo bar."
    assert ((_t := parser.bold_title(Section, r"Foo")), (noChange := _t[1]))[0][0] == Section, (
        r"No change when article text contains {{year article header}}"
    )
    Section = r"{{bio}} Foo bar."
    assert ((_t := parser.bold_title(Section, r"Foo")), (noChange := _t[1]))[0][0] == Section, (
        r"No change when article text contains {{bio}}"
    )
    x = r"While remaining upright may be the primary goal of beginning riders"
    Section = (
        r"{{Terme défini|Foo}} is a bar. Foo while remaining upright may be the primary goal of beginning riders."
        + x
        + x
        + x
        + x
        + x
        + x
    )
    assert ((_t := parser.bold_title(Section, r"Foo")), (noChange := _t[1]))[0][0] == Section, (
        r"No change when article text contains {{Terme défini}}"
    )


def test_standard_cases() -> None:
    S = W.for_site(EN)
    assert (
        (
            _t := parser.bold_title(
                r"Foo is a bar While remaining upright may be the primary goal of beginning riders",
                r"Foo",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][
        0
    ] == r"'''Foo''' is a bar While remaining upright may be the primary goal of beginning riders"
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo (here) is a bar While remaining upright may be the primary goal of beginning riders",
                    r"Foo (here)",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' (here) is a bar While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo.(here) is a bar While remaining upright may be the primary goal of beginning riders",
                    r"Foo.(here)",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo.(here)''' is a bar While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo is a bar While remaining upright may be the primary goal of beginning riders Foo",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is a bar While remaining upright may be the primary goal of beginning riders Foo"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    "The Foo is a bar While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "The '''Foo''' is a bar While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo in the wild is a bar While remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders",
                    r"Foo in the wild",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo in the wild''' is a bar While remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo is a bar, Foo moar While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is a bar, Foo moar While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            _t := parser.bold_title(
                r"F^o^o is a bar While remaining upright may be the primary goal of beginning riders",
                r"F^o^o",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][
        0
    ] == r"'''F^o^o''' is a bar While remaining upright may be the primary goal of beginning riders"
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    "{{Infobox | name = Foo | age=11}}\r\nFoo is a bar While remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Infobox | name = Foo | age=11}}\r\n'''Foo''' is a bar While remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (_t := parser.bold_title("{{Infobox abc| name = Foo | age=11}}\r\nFoo is a bar", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == "{{Infobox abc| name = Foo | age=11}}\r\n'''Foo''' is a bar"
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo (Band album) is a CD While remaining upright may be the primary goal of beginning riders",
                    r"Foo (Band album)",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' (Band album) is a CD While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert ((_t := parser.bold_title(r"Fooo is a bar", r"Foo")), (noChangeBack := _t[1]))[0][
        0
    ] == r"Fooo is a bar"
    assert noChangeBack
    ImageBold = "[[Image...]]\r\n'''Something''' is a bar"
    assert ((_t := parser.bold_title(ImageBold, r"Foo")), (noChangeBack := _t[1]))[0][
        0
    ] == ImageBold
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    "Foo is a '''bar''' While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "Foo is a '''bar''' While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders"
    )
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    r"{{unicode|'''Ł̣'''}} ([[Lower case|minuscule]]: {{unicode|'''ł̣'''}}) is a letter of the [[Latin alphabet]], derived from [[Ł̣]] with a diacritical",
                    r"Ł̣",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"{{unicode|'''Ł̣'''}} ([[Lower case|minuscule]]: {{unicode|'''ł̣'''}}) is a letter of the [[Latin alphabet]], derived from [[Ł̣]] with a diacritical"
    )
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    "[[Image:1.JPEG|Now Smith here]] Now Smith here While remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders",
                    r"Smith",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "[[Image:1.JPEG|Now Smith here]] Now '''Smith''' here While remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            _t := parser.bold_title(
                "{{unreferenced|date=November 2010}}\r\nVodafone Qatar started", r"Vodafone Qatar"
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == "{{unreferenced|date=November 2010}}\r\n'''Vodafone Qatar''' started"


def test_with_delinking() -> None:
    S = W.for_site(EN)
    assert (
        (
            _t := parser.bold_title(
                r"[[Foo]] is a bar While remaining upright may be the primary goal of beginning riders",
                r"Foo",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][
        0
    ] == r"'''Foo''' is a bar While remaining upright may be the primary goal of beginning riders"
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"[[Foo]] is a bar, Foo moar While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is a bar, Foo moar While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo is a bar, now [[Foo]] here While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"Foo is a bar, now '''Foo''' here While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"Foo is a bar, now [[foo]] here While remaining upright may be the primary goal of beginning riders, foo here",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"Foo is a bar, now '''foo''' here While remaining upright may be the primary goal of beginning riders, foo here"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"[[Foo]] is a [[bar]] While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is a [[bar]] While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"'''Foo''' is a bar, now [[Foo]] here While remaining upright may be the primary goal of beginning riders",
                    r"Foo",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Foo''' is a bar, now [[Foo]] here While remaining upright may be the primary goal of beginning riders"
    )
    assert noChangeBack
    assert (
        (
            (
                _t := parser.bold_title(
                    "[[Image:Head of serpent column.jpg|250px|thumb|[[Kukulkan]] at the base of the west face of the northern stairway of [[El Castillo, Chichen Itza]]]]\r\n\r\n[[Image:ChichenItzaEquinox.jpg|250px|thumb|Kukulkan at Chichen Itza during the [[Equinox]]. The famous decent of the snake March 2009]]\r\n\r\n[[Kukulkan]] (''Plumed Serpent'', ''Feathered Serpent'') is a god in the pantheon of [[Maya mythology]]. In [[Yucatec]] the name is spelt '''K'uk'ulkan''' and in [[Tzotzil language|Tzotzil]] it is '''K'uk'ul-chon'''.<ref>Freidel et al 1993, p.289.</ref> The depiction of the [[Feathered Serpent (deity)|feathered serpent deity]] is present in other cultures of [[Mesoamerica]] and Kukulkan is closely related to ''[[Gukumatz]]'' of the [[K'iche']] Maya tradition and ''[[Quetzalcoatl]]'' of [[Aztec mythology]].<ref>Read & Gonzalez 2000, pp.180-2.</ref> Little is known of the mythology of the [[pre-Columbian]] deity.<ref>Read & Gonzalez 2000, p.201.</ref>\r\n\r\nAlthough heavily Mexicanised, Kukulkan has his origins among the Maya of the [[Mesoamerican chronology|Classic Period]], when he was known as ''Waxaklahun Ubah Kan'', the War Serpent, and he has been identified as the Postclassic version of the [[Vision Serpent]] of Classic Maya art.<ref>Freidel et al 1993, pp.289, 325, 441n26.</ref>\r\n\r\nThe cult of Kukulkan/Quetzalcoatl was the first Mesoamerican religion to transcend the old Classic Period linguistic and ethnic divisions.<ref>Sharer & Traxler 2006, pp582-3.</ref> This cult facilitated communication and peaceful trade among peoples of many different social and ethnic backgrounds.<ref>Sharer & Traxler 2006, pp582-3.</ref> Although the cult was originally centred on the ancient city of [[Chichen Itza|Chichén Itzá]] in the modern [[Mexico|Mexican]] state of [[Yucatán]], it spread as far as the [[Guatemala]]n highlands.<ref>Sharer & Traxler 2006, p.619.</ref>\r\n\r\nIn Yucatán, references to the deity Kukulkan are confused by references to a named individual who bore the name of the god. Because of this, the distinction between the two has become blurred.<ref>Miller & Taube 1993, p.142.</ref> This individual appears to have been a ruler or priest at Chichen Itza, who first appeared around the 10th century.<ref>Read & González 2000, p.201.</ref>\r\nAlthough Kukulkan was mentioned as a historical person by Maya writers of the 16th century, the earlier 9th century texts at Chichen Itza never identified him as human and artistic representations depicted him as a Vision Serpent entwined around the figures of nobles.<ref>Freidel et al 1993, p.325.</ref> At Chichen Itza, Kukulkan is also depicted presiding over sacrifice scenes.<ref>Freidel et al 1993, p.478n60.</ref>\r\n\r\nSizeable temples to Kukulkan are found at archaeological sites throughout the north of the [[Yucatán Peninsula]], such as Chichen Itza, [[Uxmal]] and [[Mayapan]].<ref>Read & González 2000, p.201.</ref>\r\n\r\n==Etymology==\r\nThe Yucatec form of the name is formed from the word",
                    r"Kukulkan",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "[[Image:Head of serpent column.jpg|250px|thumb|'''Kukulkan''' at the base of the west face of the northern stairway of [[El Castillo, Chichen Itza]]]]\r\n\r\n[[Image:ChichenItzaEquinox.jpg|250px|thumb|Kukulkan at Chichen Itza during the [[Equinox]]. The famous decent of the snake March 2009]]\r\n\r\n'''Kukulkan''' (''Plumed Serpent'', ''Feathered Serpent'') is a god in the pantheon of [[Maya mythology]]. In [[Yucatec]] the name is spelt '''K'uk'ulkan''' and in [[Tzotzil language|Tzotzil]] it is '''K'uk'ul-chon'''.<ref>Freidel et al 1993, p.289.</ref> The depiction of the [[Feathered Serpent (deity)|feathered serpent deity]] is present in other cultures of [[Mesoamerica]] and Kukulkan is closely related to ''[[Gukumatz]]'' of the [[K'iche']] Maya tradition and ''[[Quetzalcoatl]]'' of [[Aztec mythology]].<ref>Read & Gonzalez 2000, pp.180-2.</ref> Little is known of the mythology of the [[pre-Columbian]] deity.<ref>Read & Gonzalez 2000, p.201.</ref>\r\n\r\nAlthough heavily Mexicanised, Kukulkan has his origins among the Maya of the [[Mesoamerican chronology|Classic Period]], when he was known as ''Waxaklahun Ubah Kan'', the War Serpent, and he has been identified as the Postclassic version of the [[Vision Serpent]] of Classic Maya art.<ref>Freidel et al 1993, pp.289, 325, 441n26.</ref>\r\n\r\nThe cult of Kukulkan/Quetzalcoatl was the first Mesoamerican religion to transcend the old Classic Period linguistic and ethnic divisions.<ref>Sharer & Traxler 2006, pp582-3.</ref> This cult facilitated communication and peaceful trade among peoples of many different social and ethnic backgrounds.<ref>Sharer & Traxler 2006, pp582-3.</ref> Although the cult was originally centred on the ancient city of [[Chichen Itza|Chichén Itzá]] in the modern [[Mexico|Mexican]] state of [[Yucatán]], it spread as far as the [[Guatemala]]n highlands.<ref>Sharer & Traxler 2006, p.619.</ref>\r\n\r\nIn Yucatán, references to the deity Kukulkan are confused by references to a named individual who bore the name of the god. Because of this, the distinction between the two has become blurred.<ref>Miller & Taube 1993, p.142.</ref> This individual appears to have been a ruler or priest at Chichen Itza, who first appeared around the 10th century.<ref>Read & González 2000, p.201.</ref>\r\nAlthough Kukulkan was mentioned as a historical person by Maya writers of the 16th century, the earlier 9th century texts at Chichen Itza never identified him as human and artistic representations depicted him as a Vision Serpent entwined around the figures of nobles.<ref>Freidel et al 1993, p.325.</ref> At Chichen Itza, Kukulkan is also depicted presiding over sacrifice scenes.<ref>Freidel et al 1993, p.478n60.</ref>\r\n\r\nSizeable temples to Kukulkan are found at archaeological sites throughout the north of the [[Yucatán Peninsula]], such as Chichen Itza, [[Uxmal]] and [[Mayapan]].<ref>Read & González 2000, p.201.</ref>\r\n\r\n==Etymology==\r\nThe Yucatec form of the name is formed from the word"
    )


def test_examples_from_bug_report() -> None:
    S = W.for_site(EN)
    assert (
        (
            (
                _t := parser.bold_title(
                    r"[[Michael Bavaro]] is a [[filmmaker]] based in [[Manhattan]]. While remaining upright may be the primary goal of beginning riders, a bike must lean in order to maintain balance",
                    r"Michael Bavaro",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == r"'''Michael Bavaro''' is a [[filmmaker]] based in [[Manhattan]]. While remaining upright may be the primary goal of beginning riders, a bike must lean in order to maintain balance"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    "{{Unreferenced|date=October 2007}}\r\nSteve Cook is a songwriter for Sovereign Grace. While remaining upright may be the primary goal of beginning riders. While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders",
                    r"Steve Cook",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Unreferenced|date=October 2007}}\r\n'''Steve Cook''' is a songwriter for Sovereign Grace. While remaining upright may be the primary goal of beginning riders. While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := parser.bold_title(
                    "{{Unreferenced|date=October 2007}}\r\n[[Steve Cook]] is a songwriter for Sovereign Grace. While remaining upright may be the primary goal of beginning riders. While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders [[Steve Cook]]\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders",
                    r"Steve Cook",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Unreferenced|date=October 2007}}\r\n'''Steve Cook''' is a songwriter for Sovereign Grace. While remaining upright may be the primary goal of beginning riders. While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders '''Steve Cook'''\r\nWhile remaining upright may be the primary goal of beginning riders While remaining upright may be the primary goal of beginning riders"
    )
    assert not (noChangeBack)
    assert (
        (
            (
                _t := genfixes.fix_links(
                    (
                        (
                            _t := parser.bold_title(
                                "The 2009 Indian Premier League While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\n==sec== [[2009 Indian Premier League|2009]]<br>",
                                r"2009 Indian Premier League",
                            )
                        ),
                        (noChangeBack := _t[1]),
                    )[0][0],
                    r"2009 Indian Premier League",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "The '''2009 Indian Premier League''' While remaining upright may be the primary goal of beginning riders\r\nWhile remaining upright may be the primary goal of beginning riders\r\n==sec== 2009<br>"
    )
    OutsideZerothSection = "Text here.\r\n==Bio==\r\nJohn Smith was great."
    assert (
        (_t := parser.bold_title(OutsideZerothSection, r"John Smith")),
        (noChangeBack := _t[1]),
    )[0][0] == OutsideZerothSection


def test_self_links_with_bold() -> None:
    S = W.for_site(EN)
    assert (
        (
            _t := parser.bold_title(
                r"'''[[Marie-Madeleine-Marguerite d'Aubray, Marquise de Brinvilliers]]'''",
                r"Marie-Madeleine-Marguerite d'Aubray, Marquise de Brinvilliers",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Marie-Madeleine-Marguerite d'Aubray, Marquise de Brinvilliers'''"
    assert ((_t := parser.bold_title(r"'''[[foo]]'''", r"Foo")), (noChangeBack := _t[1]))[0][
        0
    ] == r"'''foo'''"
    assert (
        (
            _t := parser.bold_title(
                r"''[[Marie-Madeleine-Marguerite d'Aubray, Marquise de Brinvilliers]]''",
                r"Marie-Madeleine-Marguerite d'Aubray, Marquise de Brinvilliers",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''''Marie-Madeleine-Marguerite d'Aubray, Marquise de Brinvilliers'''''"


def test_bolded_self_links() -> None:
    S = W.for_site(EN)
    assert (
        (
            (
                _t := parser.bold_title(
                    "{{Infobox Album <!-- See Wikipedia:WikiProject_Albums -->\r\n| Name        = ''It Crawled into My Hand, Honest''\r\n| Type        = studio\r\n| Artist      = [[The Fugs]]\r\n| Cover       =\r\n| Released    = 1968\r\n| Recorded    = 1968\r\n| Genre       = [[Rock and roll|Rock]], [[protopunk]], [[Psychedelic music|psychedelic]] [[Folk-rock]]\r\n| Length      =\r\n| Label       = [[Folkways Records|Folkways]]<br />[[ESP-Disk]]\r\n| Producer    = [[Ed Sanders]], [[Harry Everett Smith|Harry Smith]]\r\n| Reviews     =\r\n| Last album  = ''[[Tenderness Junction]]''<br />(1968)\r\n| This album  = '''''[[It Crawled into My Hand, Honest]]'''''<br />(1968)\r\n| Next album  = ''[[Belle of Avenue A]]''<br /> (1969)\r\n}}",
                    r"It Crawled into My Hand, Honest",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Infobox Album <!-- See Wikipedia:WikiProject_Albums -->\r\n| Name        = ''It Crawled into My Hand, Honest''\r\n| Type        = studio\r\n| Artist      = [[The Fugs]]\r\n| Cover       =\r\n| Released    = 1968\r\n| Recorded    = 1968\r\n| Genre       = [[Rock and roll|Rock]], [[protopunk]], [[Psychedelic music|psychedelic]] [[Folk-rock]]\r\n| Length      =\r\n| Label       = [[Folkways Records|Folkways]]<br />[[ESP-Disk]]\r\n| Producer    = [[Ed Sanders]], [[Harry Everett Smith|Harry Smith]]\r\n| Reviews     =\r\n| Last album  = ''[[Tenderness Junction]]''<br />(1968)\r\n| This album  = '''''It Crawled into My Hand, Honest'''''<br />(1968)\r\n| Next album  = ''[[Belle of Avenue A]]''<br /> (1969)\r\n}}"
    )
    assert (
        (
            _t := parser.bold_title(
                r"<noinclude> = '''''[[It Crawled into My Hand, Honest]]'''''<br /> </noinlcude>",
                r"[[It Crawled into My Hand, Honest]]",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"<noinclude> = '''''[[It Crawled into My Hand, Honest]]'''''<br /> </noinlcude>"
    assert ((_t := parser.bold_title(r"[[foo]]", r"Foo")), (noChangeBack := _t[1]))[0][
        0
    ] == r"'''foo'''"
    assert (
        (_t := parser.bold_title(r"'''[[foo (here)|Foo]]'''", r"foo (here)")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo'''"
    NoChange = r"{{abc|The [[foo]] was}} A."
    assert ((_t := parser.bold_title(NoChange, r"Foo")), (noChangeBack := _t[1]))[0][0] == NoChange
    NoChange = r"<noinclude>'''[[foo (here)|Foo]]'''</noinclude> A."
    assert ((_t := parser.bold_title(NoChange, r"Foo")), (noChangeBack := _t[1]))[0][
        0
    ] == NoChange, r"no change when noinclude/includeonly"


def test_basic_behaviour() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: [[Foo]]") == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: [[Foo]].")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article:\\r\\n [[Foo]]")
        == "A==Sec==\r\nMain article:\\r\\n [[Foo]]"
    )


def test_piped_links() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: [[Foo|Bar]]")
        == "A==Sec==\r\n{{Main|Foo|l1=Bar}}"
    )


def test_support_indenting() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\n:Main article: [[Foo]]")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n:Main article: [[Foo]].")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n:''Main article: [[Foo]]''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n'':Main article: [[Foo]]''")
        == "A==Sec==\r\n'':Main article: [[Foo]]''"
    )


def test_support_bold_and_italic() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: '[[Foo]]'")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: ''[[Foo]]''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: '''[[Foo]]'''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: '''''[[Foo]]'''''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n'Main article: [[Foo]]'")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n''Main article: [[Foo]]''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n'''Main article: [[Foo]]'''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n'''''Main article: [[Foo]]'''''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n''Main article: '''[[Foo]]'''''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n'''Main article: ''[[Foo]]'''''")
        == "A==Sec==\r\n{{Main|Foo}}"
    )


def test_case_insensitivity() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\nmain Article: [[foo]]") == "A==Sec==\r\n{{Main|foo}}"
    )


def test_dont_eat_too_much() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\nFoo is a bar, see main article: [[Foo]]")
        == "A==Sec==\r\nFoo is a bar, see main article: [[Foo]]"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nMain article: [[Foo]], bar")
        == "A==Sec==\r\nMain article: [[Foo]], bar"
    )


def test_single_link_only() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\n:Main article: [[Foo]] and [[Bar]]")
        == "A==Sec==\r\n:Main article: [[Foo]] and [[Bar]]"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\n:Main article: [[Foo|f00]] and [[Bar]]")
        == "A==Sec==\r\n:Main article: [[Foo|f00]] and [[Bar]]"
    )


def test_newlines() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("test\r\nMain article: [[Foo]]\r\ntest")
        == "test\r\n{{Main|Foo}}\r\ntest"
    )
    assert (
        genfixes.fix_main_article("test\r\n\r\nMain article: [[Foo]]\r\n\r\ntest")
        == "test\r\n\r\n{{Main|Foo}}\r\n\r\ntest"
    )


def test_see_also() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_main_article("A==Sec==\r\nSee also: [[Foo|Bar]]")
        == "A==Sec==\r\n{{See also|Foo|l1=Bar}}"
    )
    assert (
        genfixes.fix_main_article("A==Sec==\r\nSee also: [[Foo]]") == "A==Sec==\r\n{{See also|Foo}}"
    )


def test_self_link_removal() -> None:
    S = W.for_site(EN)
    assert (
        (_t := genfixes.fix_links(r"'''Foo''' is great. [[Foo]] is cool", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo''' is great. Foo is cool"
    assert not (noChangeBack)
    assert (
        (_t := genfixes.fix_links(r"'''Foo''' is great. [[Foo]] is cool and [[foo]] now", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo''' is great. Foo is cool and foo now"
    assert not (noChangeBack)
    assert (
        (
            _t := genfixes.fix_links(
                r"'''Foo''' is great. [[Foo]] is cool and [[foo|bar]] now", r"Foo"
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo''' is great. Foo is cool and bar now"
    assert not (noChangeBack)
    assert (
        (_t := genfixes.fix_links(r"'''Foo''' is great. [[Foo|Bar]] is cool", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo''' is great. Bar is cool"
    assert not (noChangeBack)
    assert (
        (_t := genfixes.fix_links(r"'''Foo bar''' is great. [[Foo bar]] is cool", r"Foo bar")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo bar''' is great. Foo bar is cool"
    assert not (noChangeBack)
    assert (
        (_t := genfixes.fix_links(r"'''Foo bar''' is great. [[Foo_bar]] is cool", r"Foo bar")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo bar''' is great. Foo bar is cool"
    assert not (noChangeBack)
    assert (
        (
            _t := genfixes.fix_links(
                r"'''Foo''' is great. Foo is cool.{{cite web|url=a|title=b|publisher=[[Foo]]}}",
                r"Foo",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo''' is great. Foo is cool.{{cite web|url=a|title=b|publisher=Foo}}"
    assert not (noChangeBack)
    assert (
        (_t := genfixes.fix_links(r"'''Foo''' is great. [[Foo#Bar|Bar]] is cool", r"Foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''Foo''' is great. [[Foo#Bar|Bar]] is cool"
    assert noChangeBack
    assert (
        (
            _t := genfixes.fix_links(
                r"'''the''' extreme [[anti-cult movement|anti-cult activist]]s resort",
                r"Anti-cult movement",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''the''' extreme anti-cult activists resort"
    assert not (noChangeBack)
    assert (
        (
            _t := genfixes.fix_links(
                r"'''the''' extreme [[Anti-cult movement|anti-cult activist]]s resort",
                r"Anti-cult movement",
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"'''the''' extreme anti-cult activists resort"
    assert not (noChangeBack)
    assert (
        (_t := genfixes.fix_links(r"<imagemap> [[foo]] </imagemap>", r"foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"<imagemap> [[foo]] </imagemap>"
    assert noChangeBack
    assert (
        (_t := genfixes.fix_links(r"{{taxobox color| [[foo]] }}", r"foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"{{taxobox color| [[foo]] }}"
    assert noChangeBack
    assert (
        (_t := genfixes.fix_links(r"<noinclude> [[foo]] </noinclude>", r"foo")),
        (noChangeBack := _t[1]),
    )[0][0] == r"<noinclude> [[foo]] </noinclude>"
    assert noChangeBack
    assert ((_t := genfixes.fix_links(r"[[foo bar]]", r"Foo bar")), (noChangeBack := _t[1]))[0][
        0
    ] == r"foo bar"
    assert ((_t := genfixes.fix_links(r"[[Foo bar]]", r"foo bar")), (noChangeBack := _t[1]))[0][
        0
    ] == r"Foo bar"


def test_more_self_link_removal() -> None:
    S = W.for_site(EN)
    assert (
        (
            _t := genfixes.fix_links(
                r"[[Þorsteins saga Víkingssonar| Thorsten]]", r"Þorsteins saga Víkingssonar"
            )
        ),
        (noChangeBack := _t[1]),
    )[0][0] == r"Thorsten"
    assert (
        (
            (
                _t := genfixes.fix_links(
                    '{{Infobox Single\r\n| Name = Feels So Right\r\n| Cover =\r\n| Artist =  [[Alabama (band)|Alabama]]\r\n| from Album = [[Feels So Right (album)|Feels So Right]]\r\n| A-side         = "Feels So Right"\r\n| B-side         = "See the Embers, Feel the Flame"\r\n| Released = May 1, 1981 <small>([[United States|U.S.]])</small>\r\n| Format         = [[7-inch single|7"]]\r\n| Recorded       = August 26, 1980\r\n| Genre = [[Country music|Country]]\r\n| Length         = 3:36\r\n| Label          = [[RCA Records]] <small>12236</small>\r\n| Writer = [[Randy Owen]]\r\n| Producer       = [[Harold Shedd]] and [[Alabama (band)|Alabama]]\r\n| Last single = "[[Old Flame (song)|Old Flame]]"<br />(1981)\r\n| This single = "[[Feels So Right (song)|Feels So Right]]" <br />(1981)\r\n| Next single = "[[Love in the First Degree (Alabama song)|Love in the First Degree]]" <br />(1981)\r\n}}',
                    r"Feels So Right (song)",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == '{{Infobox Single\r\n| Name = Feels So Right\r\n| Cover =\r\n| Artist =  [[Alabama (band)|Alabama]]\r\n| from Album = [[Feels So Right (album)|Feels So Right]]\r\n| A-side         = "Feels So Right"\r\n| B-side         = "See the Embers, Feel the Flame"\r\n| Released = May 1, 1981 <small>([[United States|U.S.]])</small>\r\n| Format         = [[7-inch single|7"]]\r\n| Recorded       = August 26, 1980\r\n| Genre = [[Country music|Country]]\r\n| Length         = 3:36\r\n| Label          = [[RCA Records]] <small>12236</small>\r\n| Writer = [[Randy Owen]]\r\n| Producer       = [[Harold Shedd]] and [[Alabama (band)|Alabama]]\r\n| Last single = "[[Old Flame (song)|Old Flame]]"<br />(1981)\r\n| This single = "\'\'\'Feels So Right\'\'\'" <br />(1981)\r\n| Next single = "[[Love in the First Degree (Alabama song)|Love in the First Degree]]" <br />(1981)\r\n}}'
    )
    assert (
        (
            (
                _t := genfixes.fix_links(
                    '{{Infobox Single\r\n| Name = Feels So Right\r\n| Cover =\r\n| Artist =  [[Alabama (band)|Alabama]]\r\n| from Album = [[Feels So Right (album)|Feels So Right]]\r\n| A-side         = "Feels So Right"\r\n| B-side         = "See the Embers, Feel the Flame"\r\n| Released = May 1, 1981 <small>([[United States|U.S.]])</small>\r\n| Format         = [[7-inch single|7"]]\r\n| Recorded       = August 26, 1980\r\n| Genre = [[Country music|Country]]\r\n| Length         = 3:36\r\n| Label          = [[RCA Records]] <small>12236</small>\r\n| Writer = [[Randy Owen]]\r\n| Producer       = [[Harold Shedd]] and [[Alabama (band)|Alabama]]\r\n| Last single = "[[Old Flame (song)|Old Flame]]"<br />(1981)\r\n| This single = "[[Feels So Right]]" <br />(1981)\r\n| Next single = "[[Love in the First Degree (Alabama song)|Love in the First Degree]]" <br />(1981)\r\n}}',
                    r"Feels So Right",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == '{{Infobox Single\r\n| Name = Feels So Right\r\n| Cover =\r\n| Artist =  [[Alabama (band)|Alabama]]\r\n| from Album = [[Feels So Right (album)|Feels So Right]]\r\n| A-side         = "Feels So Right"\r\n| B-side         = "See the Embers, Feel the Flame"\r\n| Released = May 1, 1981 <small>([[United States|U.S.]])</small>\r\n| Format         = [[7-inch single|7"]]\r\n| Recorded       = August 26, 1980\r\n| Genre = [[Country music|Country]]\r\n| Length         = 3:36\r\n| Label          = [[RCA Records]] <small>12236</small>\r\n| Writer = [[Randy Owen]]\r\n| Producer       = [[Harold Shedd]] and [[Alabama (band)|Alabama]]\r\n| Last single = "[[Old Flame (song)|Old Flame]]"<br />(1981)\r\n| This single = "\'\'\'Feels So Right\'\'\'" <br />(1981)\r\n| Next single = "[[Love in the First Degree (Alabama song)|Love in the First Degree]]" <br />(1981)\r\n}}'
    )
    assert (
        (
            (
                _t := genfixes.fix_links(
                    "{{Infobox Single\r\n| Name = Feels So Right\r\n| Last single = \"[[Old Flame (song)|Old Flame]]\"<br />(1981)\r\n| This single = '''''[[Feels So Right]]''''' <br />(1981)\r\n| Next single = \"[[Love in the First Degree (Alabama song)|Love in the First Degree]]\" <br />(1981)\r\n}}",
                    r"Feels So Right",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Infobox Single\r\n| Name = Feels So Right\r\n| Last single = \"[[Old Flame (song)|Old Flame]]\"<br />(1981)\r\n| This single = '''''Feels So Right''''' <br />(1981)\r\n| Next single = \"[[Love in the First Degree (Alabama song)|Love in the First Degree]]\" <br />(1981)\r\n}}"
    )
    assert (
        (
            (
                _t := genfixes.fix_links(
                    "{{Infobox Album  <!-- See Wikipedia:WikiProject_Albums -->\r\n|Name        = Feels So Right\r\n|Type        = [[Album]]\r\n|Artist      = [[Alabama (band)|Alabama]]\r\n|Cover       = Alabama - Feels So Right.jpg\r\n|Released    = [[1981 in country music|1981]]</br>[[July 7]], [[1987]] (re-release)\r\n|Recorded    = | [[1980 in country music|1980]]\r\n|Genre       = [[Country music|Country]]\r\n|Length      = 34:59\r\n|Label       = [[RCA Records]]\r\n|Producer    = Larry McBride, [[Harold Shedd]], Alabama\r\n|Reviews     = *[[Allmusic]] {{Rating|4|5}} [http://allmusic.com/cg/amg.dll?p=amg&token=&sql=10:kjfixql5ldae]\r\n|Chronology = [[Alabama (band)|Alabama]]\r\n|Last album  = ''[[My Home's in Alabama (album)|My Home's In Alabama]]''<br />(1980)\r\n|This album  = ''[[Feels So Right (album)|Feels So Right]]''<br />(1981)\r\n|Next album  = ''[[Mountain Music (album)|Mountain Music]]''<br />(1982)\r\n}}",
                    r"Feels So Right (album)",
                )
            ),
            (noChangeBack := _t[1]),
        )[0][0]
        == "{{Infobox Album  <!-- See Wikipedia:WikiProject_Albums -->\r\n|Name        = Feels So Right\r\n|Type        = [[Album]]\r\n|Artist      = [[Alabama (band)|Alabama]]\r\n|Cover       = Alabama - Feels So Right.jpg\r\n|Released    = [[1981 in country music|1981]]</br>[[July 7]], [[1987]] (re-release)\r\n|Recorded    = | [[1980 in country music|1980]]\r\n|Genre       = [[Country music|Country]]\r\n|Length      = 34:59\r\n|Label       = [[RCA Records]]\r\n|Producer    = Larry McBride, [[Harold Shedd]], Alabama\r\n|Reviews     = *[[Allmusic]] {{Rating|4|5}} [http://allmusic.com/cg/amg.dll?p=amg&token=&sql=10:kjfixql5ldae]\r\n|Chronology = [[Alabama (band)|Alabama]]\r\n|Last album  = ''[[My Home's in Alabama (album)|My Home's In Alabama]]''<br />(1980)\r\n|This album  = '''''Feels So Right'''''<br />(1981)\r\n|Next album  = ''[[Mountain Music (album)|Mountain Music]]''<br />(1982)\r\n}}"
    )


def test_bare_references_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.has_bare_references("\r\nfoo\r\n==References==\r\n* http://www.site.com\r\n")
    assert genfixes.has_bare_references(
        "\r\nfoo\r\n==References==\r\n* http://www.site.com\r\n==External links==\r\n* http://www.site2.com\r\n"
    )
    assert genfixes.has_bare_references(
        "\r\nfoo\r\n==References==\r\n* [http://www.site.com/site a site]\r\n* http://www.site.com\r\n==External links==\r\n* http://www.site2.com\r\n"
    )
    assert genfixes.has_bare_references(
        "\r\nfoo\r\n==References==\r\n* http://www.site.com\r\n* [http://www.site.com/site a site]\r\n==External links==\r\n* http://www.site2.com\r\n"
    )
    assert genfixes.has_bare_references(
        "\r\nfoo\r\n==External links==\r\n* http://www.site2.com\r\n==References==\r\n* http://www.site.com\r\n* [http://www.site.com/site a site]\r\n"
    )
    assert not (
        genfixes.has_bare_references(
            "\r\nfoo\r\n==References==\r\n* [http://www.site.com/site a site]\r\n==External links==\r\n* http://www.site2.com\r\n"
        )
    )
    assert not (
        genfixes.has_bare_references(
            "\r\nfoo\r\n* [http://www.site.com/site a site]\r\n==External links==\r\n* http://www.site2.com\r\n"
        )
    )
    assert not (genfixes.has_bare_references(r""))
    assert not (genfixes.has_bare_references(r"foo"))


def test_dablinks_about_about() -> None:
    S = W.for_site(EN)
    AboutAbout = r"{{About|about a historical district in the foo|the modern district|Nurfoo District, Republic of Bar}}"
    assert genfixes.dablinks(AboutAbout) == AboutAbout.replace(r"about ", r""), (
        r"removes about...about"
    )
    assert genfixes.dablinks(AboutAbout.replace(r"about ", r"  About ")) == AboutAbout.replace(
        r"about ", r""
    ), r"removes about...about, allows extra whitespace"
    assert genfixes.dablinks(AboutAbout.replace(r"about ", r" about")) == AboutAbout.replace(
        r"about ", r""
    ), r"no change if already correct"


def test_dablinks_no_zeroth_section() -> None:
    S = W.for_site(EN)
    NoZerothSection1 = "\r\n===fpfp===\r\nwords"
    assert genfixes.dablinks(NoZerothSection1) == NoZerothSection1
    NoZerothSection2 = "===fpfp===\r\nwords"
    assert genfixes.dablinks(NoZerothSection2) == NoZerothSection2


def test_dablinks_otheruses4() -> None:
    S = W.for_site(EN)
    OU = r"{{Otheruses4|foo|bar}}"
    assert genfixes.dablinks(OU) == r"{{About|foo|bar}}"


def test_dablinks_merging_for() -> None:
    S = W.for_site(EN)
    AboutBefore = r"{{about|Foo|a|b}}"
    forBefore = r"{{for|c|d}}"
    aboutAfter = r"{{about|Foo|a|b|c|d}}"
    assert genfixes.dablinks(AboutBefore + forBefore) == aboutAfter, (
        r"merges for into about (3 args)"
    )
    assert genfixes.dablinks(forBefore + AboutBefore) == aboutAfter, (
        r"merges for into about – for first"
    )
    assert genfixes.dablinks(forBefore) == forBefore, r"single for not changed"
    assert genfixes.dablinks(AboutBefore) == AboutBefore, r"single about not changed"
    for1 = r"{{for|a|b}}"
    about1 = r"{{about||a|b|c|d}}"
    assert genfixes.dablinks(for1 + forBefore) == about1
    singleAbout = r"{{about|foo}}"
    assert genfixes.dablinks(singleAbout + forBefore) == singleAbout + forBefore, (
        r"no merge if {{about}} has <2 arguments"
    )
    About2Before = r"{{about|foo|a}}"
    assert genfixes.dablinks(About2Before + forBefore) == r"{{about|foo|a||c|d}}", (
        r"merges for into about (2 args)"
    )
    assert (
        genfixes.dablinks(About2Before + forBefore + r"{{for|e|f}}") == r"{{about|foo|a||c|d|e|f}}"
    ), r"two for merges"
    assert (
        genfixes.dablinks(for1 + "\r\n==foo==" + forBefore) == for1 + "\r\n==foo==" + forBefore
    ), r"only merges dablinks in zeroth section"
    For3 = r"{{for|c|d|e}}"
    assert genfixes.dablinks(for1 + For3) == r"{{about||a|b|c|d|and|e}}", (
        r"merge for with 1 and 3 arguments"
    )
    assert genfixes.dablinks(For3 + for1) == r"{{about||a|b|c|d|and|e}}", (
        r"merge for with 1 and 3 arguments"
    )
    assert (
        genfixes.dablinks(r"{{for|a|b}}{{for|c|d}}{{for|e|f|g|h}}")
        == r"{{about||a|b|c|d}}{{for|e|f|g|h}}"
    ), r"do not merge for with 4 arguments"
    assert (
        genfixes.dablinks(r"{{for|a|b|c|d}}{{for|e|f|g|h}}") == r"{{for|a|b|c|d}}{{for|e|f|g|h}}"
    ), r"do not merge for with 4 arguments"
    ForTwoCats = r"{{for|the city in California|Category:Lancaster, California}}{{for|the city in Pennsylvania|Category:Lancaster, Pennsylvania}}"
    assert (
        genfixes.dablinks(ForTwoCats)
        == r"{{about||the city in California|:Category:Lancaster, California|the city in Pennsylvania|:Category:Lancaster, Pennsylvania}}"
    )
    assert (
        genfixes.dablinks(r"{{about||a|b|c|d}}{{for||e}}") == r"{{about||a|b|c|d|other uses|e}}"
    ), r"for with first argument empty"
    assert (
        genfixes.dablinks(r"{{about|foo|a|b|c|d}}{{for||e}}")
        == r"{{about|foo|a|b|c|d|other uses|e}}"
    ), r"for with first argument empty"
    assert (
        genfixes.dablinks(r"{{about|1|2|3|4|5|6|7|8|9}}{{for|a|b}}")
        == r"{{about|1|2|3|4|5|6|7|8|9}}{{for|a|b}}"
    ), r"don't do anything if about has 9 arguments"
    assert (
        genfixes.dablinks(
            r"{{about||ended|List of ended}}{{about||original|Lists of original|specials|List of specials}}{{about||exclusive|List of exclusive}}"
        )
        == r"{{about||ended|List of ended|original|Lists of original|specials|List of specials|exclusive|List of exclusive}}"
    ), r"Combine multiple in || mode"


def test_dablinks_merging_about() -> None:
    S = W.for_site(EN)
    AboutAfter = r"{{about||a|b|c|d}}"
    a1 = r"{{about||a|b}}"
    a2 = r"{{about||c|d}}"
    assert genfixes.dablinks(a1 + a2) == AboutAfter, r"merges abouts with same reason: null reason"
    assert genfixes.dablinks(AboutAfter) == AboutAfter, r"no change if already correct"
    AboutAfterFoo = r"{{about|Foo|a|b|c|d}}"
    a1Foo = r"{{about|Foo|a|b}}"
    a2Foo = r"{{about|Foo|c|d}}"
    assert genfixes.dablinks(a1Foo + a2Foo) == AboutAfterFoo, (
        r"merges abouts with same reason: reason given"
    )
    assert genfixes.dablinks(AboutAfterFoo) == AboutAfterFoo, r"no change if already correct"
    a2Bar = r"{{about|Bar|c|d}}"
    assert genfixes.dablinks(a2Bar + a2Foo) == a2Bar + a2Foo, r"not merged when reason different"
    m1 = "{{About||the film adaptation|The League of Extraordinary Gentlemen (film)}}\r\n{{About||a list of the characters and their origins|Characters in The League of Extraordinary Gentlemen}}\r\n{{About||the British comedy|The League of Gentlemen}}"
    m1a = r"{{About||the film adaptation|The League of Extraordinary Gentlemen (film)|a list of the characters and their origins|Characters in The League of Extraordinary Gentlemen|the British comedy|The League of Gentlemen}}"
    assert genfixes.dablinks(m1) == m1a + "\r\n\r\n"
    zerosec = r"{{about|foo||a}}{{about|foo||b}}"
    assert genfixes.dablinks(zerosec) == r"{{about|foo||a|and|b}}"
    assert genfixes.dablinks(a1Foo + a2) == r"{{about|Foo|a|b|c|d}}"


def test_dablinks_merging_about_namespace() -> None:
    S = W.for_site(EN)
    a2Foo = r"{{about|Foo|Category:Bar|d}}"
    assert genfixes.dablinks(a2Foo) == a2Foo.replace(r"|C", r"|:C"), (
        r"escapes category in {{about}}"
    )


def test_dablinks_en_only() -> None:
    S = W.for_site(EN)
    zerosec = r"{{about|foo||a}}{{about|foo||b}}"
    S = set_lang(r"fr")
    assert genfixes.dablinks(zerosec) == zerosec
    S = set_lang(r"en")
    assert genfixes.dablinks(zerosec) == r"{{about|foo||a|and|b}}"


def test_dablinks_merging_distinguish() -> None:
    S = W.for_site(EN)
    AB = r"{{Distinguish|a|b}}"
    assert genfixes.dablinks(r"{{Distinguish|a}}{{Distinguish|b}}") == AB, (
        r"merges when single argument"
    )
    assert genfixes.dablinks(r"{{Distinguish|a|b}}{{Distinguish|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.dablinks(r"{{Distinguish|a}}{{Distinguish|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.dablinks(AB) == AB, r"no change if already merged"
    AB = r"{{Distinguish|text=a}}{{Distinguish|text=b}}"
    assert genfixes.dablinks(AB) == AB, r"no change if using text= parameter"
    AB = r"{{Distinguish|A}}{{Distinguish|text=b}}"
    assert genfixes.dablinks(AB) == AB, r"no change if using text= parameter, second only"


def test_merge_templates_by_section() -> None:
    S = W.for_site(EN)
    AB = r"{{See also|a|b}}"
    assert genfixes.merge_templates_by_section(r"{{See also|a}}{{See also|b}}") == AB, (
        r"merges when single argument"
    )
    assert genfixes.merge_templates_by_section(r"{{See also|a|b}}{{See also|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.merge_templates_by_section(r"{{See also|a}}{{See also|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.merge_templates_by_section(r"{{See also|a}}{{see also|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"different capitalition"
    AB = r"{{See also|a{{!}}b}}"
    assert genfixes.merge_templates_by_section(
        r"{{See also|a{{!}}b}}{{see also|c|d}}"
    ) == AB.replace(r"b}}", r"b|c|d}}"), r"With {{!}}"
    assert genfixes.merge_templates_by_section(AB) == AB, r"no change if already merged"
    AB = r"{{See also2|a|b}}"
    assert genfixes.merge_templates_by_section(r"{{See also2|a}}{{See also2|b}}") == AB, (
        r"merges when single argument"
    )
    assert genfixes.merge_templates_by_section(r"{{See also2|a|b}}{{See also2|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.merge_templates_by_section(r"{{See also2|a}}{{See also2|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.merge_templates_by_section(
        r"{{See also2|a}}{{See also2|b|[[c]]}}"
    ) == AB.replace(r"}}", r"|[[c]]}}"), r"merges multiple arguments, one with link"
    assert genfixes.merge_templates_by_section(r"{{See also2|a}}{{see also2|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"different capitalition"
    assert genfixes.merge_templates_by_section(AB) == AB, r"no change if already merged"
    AB = r"{{Main|a|b}}"
    assert genfixes.merge_templates_by_section(r"{{Main|a}}{{Main|b}}") == AB, (
        r"merges when single argument"
    )
    assert genfixes.merge_templates_by_section(r"{{Main|a|b}}{{Main|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.merge_templates_by_section(r"{{Main|a}}{{Main|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"merges multiple arguments"
    assert genfixes.merge_templates_by_section(r"{{Main|a}}{{Main|b|[[c]]}}") == AB.replace(
        r"}}", r"|[[c]]}}"
    ), r"merges multiple arguments, one with link"
    assert genfixes.merge_templates_by_section(r"{{Main|a}}{{main|b|c}}") == AB.replace(
        r"}}", r"|c}}"
    ), r"different capitalition"
    assert genfixes.merge_templates_by_section(AB) == AB, r"no change if already merged"
    AB = r"{{Main|a}}{{Main|b|l1=d}}"
    assert genfixes.merge_templates_by_section(AB) == AB, r"no change when link params used"
    SeparateSections = "==One==\r\n{{see also|A}}\r\n==Two==\r\n{{see also|B}}"
    assert genfixes.merge_templates_by_section(SeparateSections) == SeparateSections, (
        r"does not merge templates in different sections"
    )
    NotStartOfSection = "==One==\r\n{{see also|A}}\r\nText\r\n{{see also|B}}"
    assert genfixes.merge_templates_by_section(NotStartOfSection) == NotStartOfSection, (
        r"does not merge templates not at top of section"
    )
    assert (
        genfixes.merge_templates_by_section("==One==\r\n{{see also|A}}\r\n{{see also|B}}")
        == "==One==\r\n{{see also|A|B}}"
    ), r"does not merge templates not at top of section"


def test_merge_templates_by_section_en_only() -> None:
    S = W.for_site(EN)
    AB = r"{{See also|a|b}}"
    ABSeparate = r"{{See also|a}}{{See also|b}}"
    S = set_lang(r"fr")
    assert genfixes.merge_templates_by_section(ABSeparate) == ABSeparate, (
        r"No merge when not en-wiki"
    )
    S = set_lang(r"en")
    assert genfixes.merge_templates_by_section(ABSeparate) == AB, r"merges when single argument"


def test_merge_portals() -> None:
    S = W.for_site(EN)
    assert len(genfixes.merge_portals(r"")) == 0, r"no change when no portals"
    assert genfixes.merge_portals(r"{{portal|Foo|Bar}}") == r"{{portal|Foo|Bar}}", (
        r"no change when already OK"
    )
    assert genfixes.merge_portals(r"==see also==") == r"==see also==", r"no change when no portals"
    singlePortal = "Foo\r\n==See also==\r\n{{Portal|Bar}}"
    assert genfixes.merge_portals(singlePortal) == singlePortal, r"no change when single portal"
    PortalBox1 = "Foo\r\n==See also==\r\n{{Portal|Bar|Foo2}}\r\n"
    assert (
        genfixes.merge_portals("Foo\r\n==See also==\r\n{{Portal|Bar}}\r\n{{Portal|Foo2 }}")
        == PortalBox1
    ), r"merges multiple portals to single portal"
    NoSeeAlso = "{{Portal|Bar}}\r\n===One===\r\n{{Portal|Foo2 }}"
    assert genfixes.merge_portals(NoSeeAlso) == NoSeeAlso, (
        r"no merging if no portal and no see also, separate sections"
    )
    MultipleArguments = "Foo\r\n==See also==\r\n{{Portal|Bar}}\r\n{{Portal|Foo2|other=here}}"
    assert genfixes.merge_portals(MultipleArguments) == MultipleArguments, (
        r"no merging of portal with named arguments"
    )
    MultipleArguments = "Foo\r\n==See also==\r\n{{Portal|Foo2|other=here}}\r\n{{Portal|Bar}}\r\n"
    assert genfixes.merge_portals(MultipleArguments) == MultipleArguments, (
        r"no merging of portal with named arguments 2"
    )
    SameSection = "Foo\r\n==Section==\r\n{{Portal|Bar}}\r\n{{Portal|Foo}}\r\n==Other=="
    assert (
        genfixes.merge_portals(SameSection)
        == "Foo\r\n==Section==\r\n{{Portal|Bar|Foo}}\r\n==Other=="
    ), r"portals merged to first portal location when all in same section"
    differentSection = "Foo\r\n==Section==\r\n{{Portal|Bar}}\r\n==Other==\r\n{{Portal|Foo}}"
    assert genfixes.merge_portals(differentSection) == differentSection, (
        r"not merged when portals in different sections"
    )
    TwoSeeAlso = "Foo\r\n==See also==\r\n{{Portal|Bar}}\r\n==See also==\r\n{{Portal|Foo}}"
    assert genfixes.merge_portals(TwoSeeAlso) == TwoSeeAlso, (
        r"not merged when multiple see also sections"
    )
    SingleSection = "Foo\r\n{{Portal|Bar}}\r\n{{Portal|Foo}}\r\n"
    assert genfixes.merge_portals(SingleSection) == "Foo\r\n{{Portal|Bar|Foo}}\r\n", (
        r"portals merged to first portal location when article has no sections"
    )
    Dupes = "Foo\r\n{{Portal|Bar}}\r\n{{Portal|Bar}}\r\n"
    assert genfixes.merge_portals(Dupes) == "Foo\r\n{{Portal|Bar}}\r\n", r"portals deduplicated"
    assert (
        genfixes.merge_portals("Foo\r\n{{Portal|Bar|Bar2}}\r\n{{Portal|Foo|Foo2}}\r\n")
        == "Foo\r\n{{Portal|Bar|Bar2|Foo|Foo2}}\r\n"
    ), r"portals with multiple arguments combined"
    assert (
        genfixes.merge_portals("Foo\r\n{{Portal|Bar|Bar2|Foo}}\r\n{{Portal|Foo2}}\r\n")
        == "Foo\r\n{{Portal|Bar|Bar2|Foo|Foo2}}\r\n"
    ), r"portals with multiple arguments combined 2"
    assert (
        genfixes.merge_portals("Foo\r\n{{Portal|Bar|Bar2|Foo1}}\r\n{{Portal|Foo2}}\r\n")
        == "Foo\r\n{{Portal|Bar|Bar2|Foo1|Foo2}}\r\n"
    ), r"portals with multiple arguments combined and deduplicated"
    assert (
        genfixes.merge_portals("Foo\r\n{{Portal|Bar|Bar2|Foo1|Abc}}\r\n{{Portal|Foo2|Abc}}\r\n")
        == "Foo\r\n{{Portal|Bar|Bar2|Foo1|Abc|Foo2}}\r\n"
    ), r"portals with multiple arguments combined and deduplicated"
    assert (
        genfixes.merge_portals("Foo\r\n{{Portal|Bar|Foo1}}\r\n{{Portal|Abc}}\r\n==Head==\r\n")
        == "Foo\r\n{{Portal|Bar|Foo1|Abc}}\r\n==Head==\r\n"
    ), r"portals with multiple arguments combined, zeroth section"
    stack = "Foo\r\n==See also==\r\n{{stack|{{portal|Foo|bar}}}}\r\n"
    assert genfixes.merge_portals(stack) == stack, r"No change when portal in stack template"


def test_merge_portals_en_only() -> None:
    S = W.for_site(EN)
    PortalBox1 = "Foo\r\n==See also==\r\n{{Portal|Bar|Foo2}}\r\n"
    input = "Foo\r\n==See also==\r\n{{Portal|Bar}}\r\n{{Portal|Foo2 }}"
    S = set_lang(r"fr")
    assert genfixes.merge_portals(input) == input
    S = set_lang(r"en")
    assert genfixes.merge_portals(input) == PortalBox1


def test_preserve_tm() -> None:
    S = W.for_site(EN)
    assert parser.unicodify(r"test™") == r"test™"


def test_dont_change_certain_entities() -> None:
    S = W.for_site(EN)
    assert parser.unicodify(r"&emsp;&#013;") == r"&emsp;&#013;"
    assert parser.unicodify(r"The F&#x2011;22 plane") == r"The F&#x2011;22 plane"
    assert (
        parser.unicodify(r"the exclamation mark&#8201;! was") == r"the exclamation mark&#8201;! was"
    )
    assert (
        parser.unicodify(r"the exclamation mark&#8239;! was") == r"the exclamation mark&#8239;! was"
    )
    assert parser.unicodify(r" hello &#8203; bye") == r" hello &#8203; bye"
    assert parser.unicodify(r" hello &#x20000; bye") == r" hello &#x20000; bye"
    assert parser.unicodify(r" hello &#x2000f; bye") == r" hello &#x2000f; bye"
    assert parser.unicodify(r"A &#x2329; B") == r"A &#x2329; B"
    assert parser.unicodify(r"A &#x232A; B") == r"A &#x232A; B"
    assert parser.unicodify(r"A &#x10A80; B") == r"A &#x10A80; B"
    assert parser.unicodify(r"A &#x20A80; B") == r"A &#x20A80; B"
    assert (
        parser.unicodify(r"''Foo''&apos;s work was the best since ''bar''&apos;s")
        == r"''Foo''&apos;s work was the best since ''bar''&apos;s"
    )
    ColonLine = "; Heading&#58;\r\nText"
    assert parser.unicodify(ColonLine) == ColonLine


def test_ignore_math() -> None:
    S = W.for_site(EN)
    assert parser.unicodify(r"<math>&laquo;</math>") == r"<math>&laquo;</math>"
    assert parser.unicodify(r"<math chem>&laquo;</math>") == r"<math chem>&laquo;</math>"
    assert parser.unicodify(r"<chem>&laquo;</chem>") == r"<chem>&laquo;</chem>"


def test_casing() -> None:
    S = W.for_site(EN)
    assert parser.unicodify(r"A&dagger; B&Dagger;") == r"A† B‡", (
        r"supports lowercase and first-upper HTML characters"
    )


def test_templates() -> None:
    S = W.for_site(EN)
    assert (
        parser.unicodify(r"A&dagger; B{{template|&dagger;}} C{{template2|one=&dagger;}}")
        == r"A† B{{template|†}} C{{template2|one=†}}"
    ), r"can support characters within templates"


def test_addition() -> None:
    S = W.for_site(EN)
    assert ((_t := parser.add_category_no_change(r"Foo", r"", r"bar")), (noChange := _t[1]))[0][
        0
    ] == "\r\n\r\n[[Category:Foo]]"
    assert not (noChange)
    assert ((_t := parser.add_category_no_change(r"Foo", r"bar", r"bar")), (noChange := _t[1]))[0][
        0
    ] == "bar\r\n\r\n[[Category:Foo]]"
    assert not (noChange)
    assert (
        (_t := parser.add_category_no_change(r"Bar", r"test[[Category:Foo|bar]]", r"foo")),
        (noChange := _t[1]),
    )[0][0] == "test\r\n\r\n[[Category:Foo|bar]]\r\n[[Category:Bar]]"
    assert not (noChange)
    assert (
        (_t := parser.add_category_no_change(r"Foo", r"[[Category:Foo]]", r"bar")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Foo]]"
    assert noChange
    assert DotNetRegex(r"\[\[Category:Foo[ _]bar\]\]").is_match(
        (
            (_t := parser.add_category_no_change(r"Foo bar", r"[[Category:Foo_bar]]", r"bar")),
            (noChange := _t[1]),
        )[0][0]
    )
    assert noChange
    assert (
        (
            _t := parser.add_category_no_change(
                r"Foo bar", r"[[category : foo_bar%20|quux]]", r"bar"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[category : foo_bar%20|quux]]"
    assert noChange
    assert (
        (_t := parser.add_category_no_change(r"Foo", r"test", r"Template:foo")),
        (noChange := _t[1]),
    )[0][0] == "test<noinclude>\r\n[[Category:Foo]]\r\n</noinclude>"
    assert not (noChange)
    Newlineheading = "==Persian==\r\n\r\n===Pronunciation==="
    assert (
        (_t := parser.add_category_no_change(r"Foo", Newlineheading, r"bar")),
        (noChange := _t[1]),
    )[0][0] == Newlineheading + "\r\n\r\n" + r"[[Category:Foo]]"


def test_recategorizer_tests_replacement() -> None:
    S = W.for_site(EN)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"-Foo bar-", r"Bar", r"[[Category:-Foo bar-]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"-Bar II-", r"[[Category:Foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:-Bar II-]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[ catEgory: Foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:foo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo|boz]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar|boz]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"foo? Bar!", r"Bar", r"[[ category:Foo?_Bar! | boz]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar| boz]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.re_categoriser(
                r"Foo", r"Bar", "[[Category:Boz]]\r\n[[Category:foo]]\r\n[[Category:Quux]]"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "[[Category:Boz]]\r\n[[Category:Bar]]\r\n[[Category:Quux]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"test[[Category:Foo]]test")),
        (noChange := _t[1]),
    )[0][0] == r"test[[Category:Bar]]test"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Fooo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Fooo]]"
    assert noChange


def test_replacement_sortkeys() -> None:
    S = W.for_site(EN)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo|key]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar|key]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo|key here]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar|key here]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo|key]]", False)),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar|key]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo|key]]", True)),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar]]"
    assert not (noChange)
    assert (
        (_t := genfixes.re_categoriser(r"Foo", r"Bar", r"[[Category:Foo|key here]]", True)),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bar]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.re_categoriser(
                r"Foo", r"Bar", r"[[Category:Foo|key]] [[Category:Bar|key]]"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r" [[Category:Bar|key]]"
    assert not (noChange)


def test_recategorizer_tests_removal() -> None:
    S = W.for_site(EN)
    assert (
        len(
            (
                (_t := genfixes.remove_category_no_change(r"Foo", r"[[Category:Foo]]")),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (_t := genfixes.remove_category_no_change(r"-Foo bar-", r"[[Category:-Foo bar-]]")),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (_t := genfixes.remove_category_no_change(r"Foo", r"[[ category: foo | bar]]")),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        len(
            (
                (_t := genfixes.remove_category_no_change(r"Foo", r"[[Category:Foo|]]")),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        (_t := genfixes.remove_category_no_change(r"Foo", r" [[Category:Foo]] ")),
        (noChange := _t[1]),
    )[0][0] == r"  "
    assert not (noChange)
    assert (
        len(
            (
                (_t := genfixes.remove_category_no_change(r"Foo", "[[Category:Foo]]\r\n")),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        (_t := genfixes.remove_category_no_change(r"Foo", "[[Category:Foo]]\r\n\r\n")),
        (noChange := _t[1]),
    )[0][0] == "\r\n"
    assert not (noChange)
    assert (
        len(
            (
                (
                    _t := genfixes.remove_category_no_change(
                        r"Foo? Bar!", r"[[Category:Foo?_Bar!|boz]]"
                    )
                ),
                (noChange := _t[1]),
            )[0][0]
        )
        == 0
    )
    assert not (noChange)
    assert (
        (_t := genfixes.remove_category_no_change(r"Foo", r"[[Category:Fooo]]")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Fooo]]"
    assert noChange


def test_conversions_tests_info_box() -> None:
    S = W.for_site(EN)
    correct = r"{{infobox foo|date=May 2010}}"
    assert genfixes.conversions(r"{{infobox_foo|date=May 2010}}") == correct
    assert genfixes.conversions(correct) == correct
    correct = "{{infobox foo\r\n|date=May 2010}}"
    assert genfixes.conversions(correct) == correct
    correct = "{{infobox\r\n|date=May 2010}}"
    assert genfixes.conversions(correct) == correct
    correct = r"{{infobox foo|date=May 2010}}"
    assert genfixes.conversions(r"{{Template:infobox_foo|date=May 2010}}") == correct


def test_conversions_tests_unreferenced() -> None:
    S = W.for_site(EN)
    correct = r"{{Unreferenced section|date=May 2010}}"
    assert genfixes.conversions(r"{{Unreferenced|section|date=May 2010}}") == correct
    assert genfixes.conversions(r"{{Unreferenced|Section|date=May 2010}}") == correct
    assert genfixes.conversions(r"{{Unreferenced|  section |date=May 2010}}") == correct
    assert genfixes.conversions(correct) == correct
    assert genfixes.conversions(r"{{unreferenced|section|date=May 2010}}") == correct.replace(
        r"U", r"u"
    )
    assert (
        genfixes.conversions(r"{{Unreferenced|list|date=May 2010}}")
        == r"{{Unreferenced section|date=May 2010}}"
    )
    assert (
        genfixes.conversions(r"{{Unreferenced|type=section|date=May 2010}}")
        == r"{{Unreferenced section|date=May 2010}}"
    )
    assert (
        genfixes.conversions(r"{{Unreferenced|type=Section|date=May 2010}}")
        == r"{{Unreferenced section|date=May 2010}}"
    )
    assert (
        genfixes.conversions(r"{{Unreferenced|date=May 2010|auto=yes}}")
        == r"{{Unreferenced|date=May 2010}}"
    )
    assert (
        genfixes.conversions(r"{{Unreferenced|date=May 2010|auto=YES}}")
        == r"{{Unreferenced|date=May 2010}}"
    )
    assert r"unreferenced" in genfixes.conversions(
        "{{unreferenced|date=October 2011}}\r\n'''Gretchen F''' known as is a Filipina model.\r\n\r\n==Reference==\r\n*http://www.pep.ph/p\r\n{{DEFAULTSORT:Gretchen F}}\r\n[[Category:1980 births]]"
    ), r"no template renaming when within multiple issues"


def test_conversions_tests_section_templates() -> None:
    S = W.for_site(EN)
    correct = r"{{Unreferenced section|date=May 2010}}"
    assert genfixes.conversions(r"{{Unreferenced|section|date=May 2010}}") == correct
    correct = r"{{refimprove section|date=May 2010}}"
    assert genfixes.conversions(r"{{refimprove|section|date=May 2010}}") == correct
    correct = r"{{More citations needed section|date=May 2010}}"
    assert genfixes.conversions(r"{{More citations needed|section|date=May 2010}}") == correct
    correct = r"{{BLP sources section|date=May 2010}}"
    assert genfixes.conversions(r"{{BLP sources|section|date=May 2010}}") == correct
    correct = r"{{expand section|date=May 2010}}"
    assert genfixes.conversions(r"{{expand|section|date=May 2010}}") == correct
    correct = r"{{BLP unsourced section|date=May 2010}}"
    assert genfixes.conversions(r"{{BLP unsourced|section|date=May 2010}}") == correct


def test_remove_excess_template_pipes() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{cite web | url=http://www.site.com || title=hello}}")
        == r"{{cite web | url=http://www.site.com | title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web || url=http://www.site.com || title=hello}}")
        == r"{{cite web | url=http://www.site.com | title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web | url=http://www.site.com | | title=hello}}")
        == r"{{cite web | url=http://www.site.com | title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite wikisource|bar||foo}}")
        == r"{{cite wikisource|bar||foo}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite uscgll|bar||foo}}") == r"{{cite uscgll|bar||foo}}"
    )
    assert genfixes.fix_citation_templates(r"{{cite ngall|bar||foo}}") == r"{{cite ngall|bar||foo}}"
    assert (
        genfixes.fix_citation_templates(r"{{Cite Legislation AU|bar||foo}}")
        == r"{{Cite Legislation AU|bar||foo}}"
    )
    UnclosedCiteInTable = "\r\n|\r\n|Yes<ref>{{cite web | title=A </ref>\r\n|\r\n|"
    assert genfixes.fix_citation_templates(UnclosedCiteInTable) == UnclosedCiteInTable, (
        r"Does not alter table pipes following unclosed ref cite"
    )


def test_conversion_tests_commons_cat() -> None:
    S = W.for_site(EN)
    assert genfixes.conversions(r"{{commons|Category:XXX}}") == r"{{Commons category|XXX}}"
    assert genfixes.conversions(r"{{commons |Category:XXX}}") == r"{{Commons category|XXX}}"
    assert genfixes.conversions(r"{{Commons|category:XXX}}") == r"{{Commons category|XXX}}"
    assert genfixes.conversions(r"{{Commons| category:XXX }}") == r"{{Commons category|XXX}}"
    assert (
        genfixes.conversions(r"{{commons|Category:Backgammon|Backgammon}}")
        == r"{{Commons category|Backgammon}}"
    )
    assert (
        genfixes.conversions(r"{{commons|Category:Backgammon | Backgammon  }}")
        == r"{{Commons category|Backgammon}}"
    )
    assert (
        genfixes.conversions(r"{{Commons|Category:Backgammon|Backgammon main}}")
        == r"{{Commons category|Backgammon|Backgammon main}}"
    )
    assert (
        genfixes.conversions(
            r"{{commons cat|Gander International Airport|Gander International Airport}}"
        )
        == r"{{commons cat|Gander International Airport}}"
    )
    assert (
        genfixes.conversions(
            r"{{Commons cat|Gander International Airport|Gander International Airport}}"
        )
        == r"{{Commons cat|Gander International Airport}}"
    )
    S = set_site(lang_code=r"en", project="wikia")
    assert (
        genfixes.conversions(r"{{commons|Category:Backgammon|Backgammon}}")
        == r"{{commons|Category:Backgammon|Backgammon}}"
    ), r"{{Commons category}} not used on Wikia"
    S = set_site(lang_code=r"en", project="wikipedia")


def test_conversion_tests_more_footnotes() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.conversions(
            "Article <ref>A</ref>\r\n            ==References==\r\n            {{no footnotes}}\r\n            {{reflist}}"
        )
        == "Article <ref>A</ref>\r\n            ==References==\r\n            {{more footnotes needed}}\r\n            {{reflist}}"
    )
    assert (
        genfixes.conversions(
            "Article <ref>A</ref>\r\n            ==References==\r\n            {{no footnotes}}\r\n            {{reflist}}"
        )
        == "Article <ref>A</ref>\r\n            ==References==\r\n            {{more footnotes needed}}\r\n            {{reflist}}"
    )
    assert (
        genfixes.conversions(
            "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{no footnotes}}\r\n            {{reflist}}"
        )
        == "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{more footnotes needed}}\r\n            {{reflist}}"
    )
    assert (
        genfixes.conversions(
            "Article {{efn|Converting at a rate of Kr 20 = £1}}\r\n            ==References==\r\n            {{no footnotes}}\r\n            {{reflist}}"
        )
        == "Article {{efn|Converting at a rate of Kr 20 = £1}}\r\n            ==References==\r\n            {{more footnotes needed}}\r\n            {{reflist}}"
    )
    assert (
        genfixes.conversions(
            "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{no footnotes|date=May 2012}}\r\n            {{reflist}}"
        )
        == "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{more footnotes needed|date=May 2012}}\r\n            {{reflist}}"
    )
    assert (
        genfixes.conversions(
            "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{no footnotes|BLP=yes|date=May 2012}}\r\n            {{reflist}}"
        )
        == "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{more footnotes needed|BLP=yes|date=May 2012}}\r\n            {{reflist}}"
    )
    assert (
        genfixes.conversions(
            "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{no footnotes|article=yes|date=May 2012}}\r\n            {{reflist}}"
        )
        == "Article {{sfn|Smith|2004}}\r\n            ==References==\r\n            {{more footnotes needed|article=yes|date=May 2012}}\r\n            {{reflist}}"
    )
    NoChange = "Article\r\n            ==References==\r\n            {{no footnotes}}"
    assert genfixes.conversions(NoChange) == NoChange
    NoFootnotesSection = "Article <ref>A</ref>\r\n            ==Sec==\r\n            {{no footnotes|section}}\r\n            ==References==\r\n            {{reflist}}"
    assert genfixes.conversions(NoFootnotesSection) == NoFootnotesSection
    NoFootnotesReason = "Article <ref>A</ref>\r\n            ==Sec==\r\n            {{no footnotes|some reason}}\r\n            ==References==\r\n            {{reflist}}"
    assert genfixes.conversions(NoFootnotesReason) == NoFootnotesReason
    NoChange2 = "Article<ref name=A group=B>A</ref>\r\n            ==References==\r\n            {{no footnotes}}"
    assert genfixes.conversions(NoChange2) == NoChange2


def test_conversion_tests_blp_unsourced() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP unreferenced}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{unreferenced}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct
    assert genfixes.conversions(correct) == correct
    assert genfixes.conversions(nochange) == nochange
    nochange = r"Foo {{unreferenced|blah}}" + r"[[Category:Living people]]"
    assert genfixes.conversions(nochange) == nochange, (
        r"no change when free-format text in unreferenced first argument"
    )
    assert (
        genfixes.conversions("Foo\r\n{{unreferenced|date=May 2010}}\r\n[[Category:Living people]]")
        == "Foo\r\n{{BLP unreferenced|date=May 2010}}\r\n[[Category:Living people]]"
    )
    assert (
        genfixes.conversions("Foo\r\n{{unreferenced|Date=May 2010}}\r\n[[Category:Living people]]")
        == "Foo\r\n{{BLP unreferenced|Date=May 2010}}\r\n[[Category:Living people]]"
    )
    assert (
        genfixes.conversions(
            "Foo\r\n{{BLP unsourced|date=May 2010}}\r\n{{unreferenced|date=May 2010}}\r\n[[Category:Living people]]"
        )
        == "Foo\r\n{{BLP unsourced|date=May 2010}}\r\n\r\n[[Category:Living people]]"
    )
    assert (
        genfixes.conversions(
            "Foo\r\n{{BLP unreferenced|date=May 2010}}\r\n{{unreferenced|date=May 2010}}\r\n[[Category:Living people]]"
        )
        == "Foo\r\n{{BLP unreferenced|date=May 2010}}\r\n\r\n[[Category:Living people]]"
    )


def test_conversion_tests_blp_unsourced_section() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP unreferenced section}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{unreferenced section}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct
    assert (
        genfixes.conversions(
            "Foo\r\n{{unreferenced section}}" + "\r\n" + r"[[Category:Living people]]"
        )
        == correct
    )
    assert genfixes.conversions(correct) == correct
    assert genfixes.conversions(nochange) == nochange


def test_conversion_tests_blp_primary_sources() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP primary sources}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{primary sources}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct
    assert (
        genfixes.conversions("Foo\r\n{{primary sources}}" + "\r\n" + r"[[Category:Living people]]")
        == correct
    )
    assert genfixes.conversions(correct) == correct
    assert genfixes.conversions(nochange) == nochange


def test_conversion_tests_blp_one_source() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP one source}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{One source}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct
    assert (
        genfixes.conversions("Foo\r\n{{One source}}" + "\r\n" + r"[[Category:Living people]]")
        == correct
    )
    assert genfixes.conversions(correct) == correct
    assert genfixes.conversions(nochange) == nochange


def test_conversion_tests_self_published() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP self-published}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{self-published}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct, (
        r"BLP conv 1"
    )
    assert (
        genfixes.conversions("Foo\r\n{{self-published}}" + "\r\n" + r"[[Category:Living people]]")
        == correct
    ), r"BLP conv 2"
    assert genfixes.conversions(correct) == correct, r"No change already correct"
    assert genfixes.conversions(nochange) == nochange, r"no change not BLP"


def test_conversion_tests_no_footnotes() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP no footnotes}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{No footnotes}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct, (
        r"BLP conv 1"
    )
    assert (
        genfixes.conversions("Foo\r\n{{No footnotes}}" + "\r\n" + r"[[Category:Living people]]")
        == correct
    ), r"BLP conv 2"
    assert genfixes.conversions(correct) == correct, r"No change already correct"
    assert genfixes.conversions(nochange) == nochange, r"no change not BLP"


def test_conversion_tests_blp_sources() -> None:
    S = W.for_site(EN)
    correct = "Foo\r\n{{BLP sources}}\r\n[[Category:Living people]]"
    nochange = "Foo\r\n{{More citations needed}}"
    assert genfixes.conversions(nochange + "\r\n" + r"[[Category:Living people]]") == correct
    assert genfixes.conversions(
        nochange + "\r\n" + r"[[Category : Living people]]"
    ) == correct.replace(r":", r" : ")
    assert (
        genfixes.conversions(
            "Foo\r\n{{More citations needed}}" + "\r\n" + r"[[Category:Living people]]"
        )
        == correct
    )
    assert genfixes.conversions(correct) == correct
    assert genfixes.conversions(nochange) == nochange
    nochange = r"Foo {{More citations needed|blah}}" + r"[[Category:Living people]]"
    assert genfixes.conversions(nochange) == nochange, (
        r"no change when free-format text in More citations needed first argument"
    )
    assert (
        genfixes.conversions(
            "Foo\r\n{{More citations needed|date=May 2010}}\r\n[[Category:Living people]]"
        )
        == "Foo\r\n{{BLP sources|date=May 2010}}\r\n[[Category:Living people]]"
    ), r"do conversion"
    assert (
        genfixes.conversions(
            "Foo\r\n{{BLP sources|Date=May 2010}}\r\n{{More citations needed|Date=May 2010}}\r\n[[Category:Living people]]"
        )
        == "Foo\r\n{{BLP sources|Date=May 2010}}\r\n\r\n[[Category:Living people]]"
    ), r"when have existing BLP sources then remove More citations needed"
    assert (
        genfixes.conversions(
            "Foo\r\n{{multiple issues|\r\n{{BLP sources|Date=May 2010}}\r\n{{More citations needed|Date=May 2010}}\r\n}}\r\n[[Category:Living people]]"
        )
        == "Foo\r\n{{BLP sources|Date=May 2010}}\r\n[[Category:Living people]]"
    ), r"when have existing BLP sources then remove More citations needed"
    assert (
        genfixes.conversions(
            "Foo\r\n{{More citations needed|section|date=May 2010}}\r\n[[Category:Living people]]"
        )
        == "Foo\r\n{{BLP sources section|date=May 2010}}\r\n[[Category:Living people]]"
    )


def test_conversion_tests_interwiki_migration() -> None:
    S = W.for_site(EN)
    S = set_site(lang_code=r"en", project="wikia")
    assert genfixes.interwiki_conversions(r"[[zh-tw:foo]]") == r"[[zh-tw:foo]]"
    S = set_site(lang_code=r"en", project="wikipedia")
    assert genfixes.conversions(r"{{msg:hello}}") == r"{{hello}}"
    assert genfixes.interwiki_conversions(r"[[zh-tw:foo]]") == r"[[zh:foo]]"
    assert genfixes.interwiki_conversions(r"[[nb:foo]]") == r"[[no:foo]]"
    assert genfixes.interwiki_conversions(r"[[dk:foo]]") == r"[[da:foo]]"


def test_page_name_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.conversions(r"{{PAGENAME}}") == r"{{subst:PAGENAME}}"
    assert genfixes.conversions(r"{{PAGENAMEE}}") == r"{{subst:PAGENAMEE}}"
    assert genfixes.conversions(r"{{template:PAGENAME}}") == r"{{subst:PAGENAME}}"
    assert genfixes.conversions(r"{{BASEPAGENAME}}") == r"{{subst:BASEPAGENAME}}"
    assert (
        genfixes.conversions(r"{{DEFAULTSORT:{{PAGENAME}}}}")
        == r"{{DEFAULTSORT:{{subst:PAGENAME}}}}"
    )
    RefPAGENAME = r"<ref> Some text {{PAGENAME}} here</ref>"
    assert genfixes.conversions(RefPAGENAME) == RefPAGENAME, r"No subst: within ref tags"
    assert (
        genfixes.conversions(r"<ref>a</ref> {{BASEPAGENAME}}")
        == r"<ref>a</ref> {{subst:BASEPAGENAME}}"
    ), r"Subst oustide ref tags"
    IfEqPageName = r"{{#ifeq:{{PAGENAME}}|Thing 1|Thing 2}}"
    assert genfixes.conversions(IfEqPageName) == IfEqPageName, r"No subst: #ifeq template"


def test_test_remove_empty_multiple_issues() -> None:
    S = W.for_site(EN)
    assert len(parser.multiple_issues(r"{{Multiple issues}}")) == 0
    assert len(parser.multiple_issues(r"{{Multiple issues|section = y}}")) == 0
    assert len(parser.multiple_issues(r"{{Multiple issues|section= y}}")) == 0
    assert len(parser.multiple_issues(r"{{Multiple issues | section= y}}")) == 0


def test_deduplicate_maintenance_tags() -> None:
    S = W.for_site(EN)
    tags = []
    tags.append(r"{{orphan}}")
    tags.append(r"{{orphan}}")
    tags2 = []
    tags2.append(r"{{orphan}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"exact dupes"
    tags.append(r"{{Orphan}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"casing of template name"
    tags.clear()
    tags.append(r"{{orphan|date=May 2012}}")
    tags.append(r"{{orphan|date=May 2012}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=May 2012}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"exact dupes with param"
    tags.clear()
    tags.append(r"{{orphan}}")
    tags.append(r"{{orphan|date=May 2012}}")
    tags2.clear()
    tags2.append(r"{{orphan | date=May 2012}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"only one with param"
    tags.clear()
    tags.append(r"{{orphan|date=May 2012}}")
    tags.append(r"{{orphan|date=May 2012}}")
    tags.append(r"{{cleanup|date=May 2012}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=May 2012}}")
    tags2.append(r"{{cleanup|date=May 2012}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"Non-dupe tag retained"
    tags.clear()
    tags.append(r"{{orphan|date=May 2012}}")
    tags.append(r"{{Orphan|date=May 2015}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=May 2012}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"use earlier date param"
    tags.clear()
    tags.append(r"{{orphan|date=May 2012}}")
    tags.append(r"{{Orphan|date=May 2015|other=foo}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=May 2012 | other=foo}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, r"Take other params"
    tags.clear()
    tags.append(r"{{orphan|date=May 2012|other=bar}}")
    tags.append(r"{{Orphan|date=May 2015|other=foo}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=May 2012|other=bar}}")
    tags2.append(r"{{Orphan|date=May 2015|other=foo}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, (
        r"cannot dedupe if conflicting parameters"
    )
    tags.clear()
    tags.append(r"{{orphan|date=foo}}")
    tags.append(r"{{Orphan|date=foo}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=foo}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, (
        r"Take non-date date param if identical"
    )
    tags.clear()
    tags.append(r"{{orphan|date=foo}}")
    tags.append(r"{{Orphan|date=foo2}}")
    tags2.clear()
    tags2.append(r"{{orphan|date=foo}}")
    tags2.append(r"{{Orphan|date=foo2}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, (
        r"Cannot process conflicting non-date date params"
    )
    tags.clear()
    tags.append(r"{{notability|date=May 2012}}")
    tags.append(r"{{notability|Biography|date=May 2015}}")
    tags2.clear()
    tags2.append(r"{{notability|Biography|date=May 2012}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, (
        r"Retain template argument, in second tag"
    )
    tags.clear()
    tags.append(r"{{notability|Biography|date=May 2012}}")
    tags.append(r"{{notability|date=May 2015}}")
    tags2.clear()
    tags2.append(r"{{notability|Biography|date=May 2012}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, (
        r"Retain template argument, in first tag"
    )
    tags.clear()
    tags.append(r"{{Expert-subject|Science fiction|date=February 2009}}")
    tags.append(r"{{Expert-subject|Military history/Weaponry task force|date=February 2009}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags, (
        r"Retain both: template argument in both"
    )
    tags.clear()
    tags.append(r"{{Redirect|ATF}}")
    tags.append(
        r"{{Redirect|BATF|the gene|BATF (gene){{!}}''BATF'' (gene)|the former Indian taskforce|Bangalore Agenda Task Force}}"
    )
    assert genfixes.deduplicate_maintenance_tags(tags) == tags, (
        r"Retain both: template argument in both - Redirect"
    )
    tags.clear()
    tags.append(r"{{distinguish|Foo}}")
    tags.append(r"{{distinguish|text=Something}}")
    tags2.clear()
    tags2.append(r"{{distinguish|Foo}}")
    tags2.append(r"{{distinguish|text=Something}}")
    assert genfixes.deduplicate_maintenance_tags(tags) == tags2, (
        r"No change when non-date named param"
    )


def test_multiple_issues_new_zeroth_tag_lines() -> None:
    S = W.for_site(EN)
    assert len(parser.multiple_issues(r"")) == 0
    assert (
        parser.multiple_issues(r"{{wikify}} {{unreferenced}} {{POV}}")
        == "{{Multiple issues|\r\n{{wikify}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}"
    ), r"preserves tag order adding new tags"
    assert (
        parser.multiple_issues("{{wikify}}{{unreferenced}}{{POV}}\r\n==hello==")
        == "{{Multiple issues|\r\n{{wikify}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n==hello=="
    ), r"takes tags from same line"
    assert (
        parser.multiple_issues("{{wikify}}\r\n{{unreferenced}}\r\n{{POV}}\r\n==hello==")
        == "{{Multiple issues|\r\n{{wikify}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n\r\n\r\n==hello=="
    ), r"takes tags from separate lines, takes tags without dates"
    assert (
        parser.multiple_issues(
            "{{wikify}}\r\n{{unreferenced}}\r\n{{POV}} Article starts.\r\n\r\n==hello=="
        )
        == "{{Multiple issues|\r\n{{wikify}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n\r\nArticle starts.\r\n\r\n==hello=="
    ), r"Tag trailing whitespace handling"


def test_multiple_issues_new_zeroth_tag_parameters() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues("{{underlinked|date=May 2012}}{{unreferenced}}{{POV}}\r\n==hello==")
        == "{{Multiple issues|\r\n{{underlinked|date=May 2012}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n==hello=="
    ), r"takes tags with dates"
    assert (
        parser.multiple_issues(
            "{{underlinked|date=May 2012|reason=x}}{{unreferenced}}{{POV}}\r\n==hello=="
        )
        == "{{Multiple issues|\r\n{{underlinked|date=May 2012|reason=x}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n==hello=="
    ), r"takes tags with extra parameters"


def test_multiple_issues_new_tag_zeroth() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues(
            "{{underlinked|date=May 2012}}{{unreferenced}}\r\nText\r\n{{POV}}\r\n==hello=="
        )
        == "{{Multiple issues|\r\n{{underlinked|date=May 2012}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\nText\r\n\r\n==hello=="
    ), r"takes tags from anywhere in zeroth section"
    assert (
        parser.multiple_issues(
            "Text\r\n{{underlinked|date=May 2012}}{{unreferenced}}{{POV}}\r\n==hello=="
        )
        == "{{Multiple issues|\r\n{{underlinked|date=May 2012}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\nText\r\n\r\n==hello=="
    ), r"takes tags from anywhere in zeroth section: all after"


def test_merge_multiple_mi() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues(
            "{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n{{Multiple issues|\r\n{{cleanup}}\r\n{{wikify}}\r\n}}\r\n\r\nFoo"
        )
        == "{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n{{cleanup}}\r\n{{wikify}}\r\n}}\r\n\r\n\r\n\r\nFoo"
    ), r"merge multiple MI"
    assert (
        parser.multiple_issues(
            "{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n{{Multiple issues|\r\n}}\r\n\r\nFoo"
        )
        == "{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n\r\n\r\nFoo"
    ), r"merge multiple MI, second empty"
    assert (
        parser.multiple_issues(
            "{{Multiple issues|\r\n{{unreferenced}}\r\n}}\r\n\r\n{{Multiple issues|\r\n{{POV}}\r\n}}\r\n\r\nFoo"
        )
        == "{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n\r\n\r\nFoo"
    ), r"merge multiple MI, one tag"
    assert (
        parser.multiple_issues(
            "{{Multiple issues|\r\n{{unreferenced}}\r\n}}\r\n\r\n{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\nFoo"
        )
        == "{{Multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n\r\n\r\nFoo"
    ), r"merge multiple MI, dedupe tag"
    assert (
        parser.multiple_issues(
            "{{Multiple issues|\r\n{{unreferenced|date=June 2012}}\r\n}}\r\n\r\n{{Multiple issues|\r\n{{unreferenced|date=May 2015}}\r\n{{POV}}\r\n}}\r\n\r\nFoo"
        )
        == "{{Multiple issues|\r\n{{unreferenced|date=June 2012}}\r\n{{POV}}\r\n}}\r\n\r\n\r\n\r\nFoo"
    ), r"merge multiple MI, dedupe tag, using earlier date"
    assert (
        parser.multiple_issues(
            "{{Multiple issues|\r\n{{unreferenced}}\r\n}}\r\n\r\n{{Multiple issues|\r\n{{unreferenced}}\r\n}}\r\n\r\nFoo"
        )
        == "{{unreferenced}}\r\n\r\n\r\n\r\nFoo"
    ), r"merge multiple MI, only dupe tags, convert to standalone tag"
    NoChange = "{{multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\n\r\n{{Multiple issues|section|\r\n{{cleanup}}\r\n{{wikify}}\r\n}}\r\n\r\nFoo"
    assert parser.multiple_issues(NoChange) == NoChange, r"no change when one MI is a section one"


def test_multiple_issues_new_zeroth_existing_mi_not_changed() -> None:
    S = W.for_site(EN)
    ThreeTagNew = "{{multiple issues|\r\n{{underlinked|date=May 2012}}\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\nText\r\n\r\n==hello=="
    TwoTagNew = "{{multiple issues|\r\n{{unreferenced}}\r\n{{POV}}\r\n}}\r\nText\r\n\r\n==hello=="
    assert parser.multiple_issues(ThreeTagNew) == ThreeTagNew, (
        r"no change to existing 3-tag MI new style"
    )
    assert parser.multiple_issues(TwoTagNew) == TwoTagNew, (
        r"no change to existing 2-tag MI new style"
    )


def test_multiple_issues_new_zeroth_existing_mi_more_tags() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{POV}}\r\n}}\r\n{{unreferenced}}\r\n\r\n==hello=="
        )
        == "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{POV}}\r\n{{unreferenced}}\r\n}}\r\n\r\n\r\n==hello=="
    ), r"adds tags to existing MI, MI new style"
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{advert}}\r\n}}\r\n{{POV}}\r\n{{unreferenced}}\r\n\r\n==hello=="
        )
        == "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{advert}}\r\n{{POV}}\r\n{{unreferenced}}\r\n}}\r\n\r\n\r\n\r\n==hello=="
    ), r"adds tags to existing MI, MI new style"
    assert (
        parser.multiple_issues(
            "{{unreferenced}}{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{POV}}\r\n}}\r\n\r\n==hello=="
        )
        == "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{POV}}\r\n{{unreferenced}}\r\n}}\r\n\r\n==hello=="
    ), r"adds tags to existing MI, MI new style, tags before MI"
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n}}\r\n{{unreferenced}}\r\n\r\n==hello=="
        )
        == "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{unreferenced}}\r\n}}\r\n\r\n\r\n==hello=="
    ), r"adds 1 tag to existing MI with 1 tag, MI new style"
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{POV}}\r\n{{unreferenced}}\r\n}}\r\n{{unreferenced}}\r\n\r\n==hello=="
        )
        == "{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n{{peacock}}\r\n{{POV}}\r\n{{unreferenced}}\r\n}}\r\n\r\n\r\n==hello=="
    ), r"duplicate tags not added"


def test_multiple_issues_new_zeroth_single_tag() -> None:
    S = W.for_site(EN)
    assert parser.multiple_issues("{{multiple issues|\r\n{{wikify}}\r\n}}") == r"{{wikify}}", (
        r"converts new style 1-tag MI to single template"
    )
    assert (
        parser.multiple_issues("{{multiple issues|\r\n{{wikify|date=May 2012}}\r\n}}")
        == r"{{wikify|date=May 2012}}"
    ), r"converts new style 1-tag MI to single template, tag with date"
    assert (
        parser.multiple_issues("{{multiple issues|\r\n{{wikify|reason=links}}\r\n}}")
        == r"{{wikify|reason=links}}"
    ), r"converts new style 1-tag MI to single template, tag with extra parameter"


def test_multiple_issues_new_section_tag_lines() -> None:
    S = W.for_site(EN)
    assert len(parser.multiple_issues(r"")) == 0
    assert (
        parser.multiple_issues("==sec==\r\n{{wikify section}} {{expand section}} {{POV-section}}")
        == "==sec==\r\n{{Multiple issues|section=yes|\r\n{{wikify section}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}"
    ), r"preserves tag order adding new tags"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{wikify section}}{{expand section}}{{POV-section}}\r\nA\r\n==hello=="
        )
        == "==sec==\r\n{{Multiple issues|section=yes|\r\n{{wikify section}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nA\r\n==hello=="
    ), r"takes tags from same line"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{wikify section}}\r\n{{expand section}}\r\n{{POV-section}}\r\nA\r\n==hello=="
        )
        == "==sec==\r\n{{Multiple issues|section=yes|\r\n{{wikify section}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nA\r\n==hello=="
    ), r"takes tags from separate lines, takes tags without dates"


def test_multiple_issues_new_section_tag_parameters() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{wikify section|date=May 2012}}{{expand section}}{{POV-section}}\r\nA\r\n==hello=="
        )
        == "==sec==\r\n{{Multiple issues|section=yes|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nA\r\n==hello=="
    ), r"takes tags with dates"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{wikify section|date=May 2012|reason=x}}{{expand section}}{{POV-section}}\r\nA\r\n==hello=="
        )
        == "==sec==\r\n{{Multiple issues|section=yes|\r\n{{wikify section|date=May 2012|reason=x}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nA\r\n==hello=="
    ), r"takes tags with extra parameters"


def test_multiple_issues_new_tag_section() -> None:
    S = W.for_site(EN)
    After = "==sec==\r\n{{wikify section|date=May 2012}}\r\nText\r\n{{POV-section}}\r\n==hello=="
    assert parser.multiple_issues(After) == After, r"Does not take tags from after text in section"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{wikify section|date=May 2012}}{{expand section}}{{POV-section}}\r\nText\r\n{{unreferenced section}}\r\n==hello=="
        )
        == "==sec==\r\n{{Multiple issues|section=yes|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nText\r\n{{unreferenced section}}\r\n==hello=="
    ), r"takes tags before tag in section"


def test_multiple_issues_new_section_existing_mi_not_changed() -> None:
    S = W.for_site(EN)
    ThreeTagNew = "==sec==\r\n{{multiple issues|section=yes|\r\n{{wikify|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nText\r\n\r\n==hello=="
    TwoTagNew = "==sec==\r\n{{multiple issues|section=yes|\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\nText\r\n\r\n==hello=="
    assert parser.multiple_issues(ThreeTagNew) == ThreeTagNew, (
        r"no change to existing 3-tag MI new style"
    )
    assert parser.multiple_issues(TwoTagNew) == TwoTagNew, (
        r"no change to existing 2-tag MI new style"
    )


def test_multiple_issues_new_section_existing_mi_more_tags() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\n{{unreferenced section}}\r\n\r\n==hello=="
        )
        == "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n{{unreferenced section}}\r\n}}\r\n==hello=="
    ), r"adds tags to existing MI, MI new style"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|section=yes|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\n{{unreferenced section}}\r\n\r\n==hello=="
        )
        == "==sec==\r\n{{multiple issues|section=yes|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n{{unreferenced section}}\r\n}}\r\n==hello=="
    ), r"adds tags to existing MI, MI new style"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{unreferenced section}}{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n}}\r\n\r\n==hello=="
        )
        == "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n{{unreferenced section}}\r\n}}\r\n==hello=="
    ), r"adds tags to existing MI, MI new style, tags before MI"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n}}\r\n{{unreferenced section}}\r\n\r\n==hello=="
        )
        == "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{unreferenced section}}\r\n}}\r\n==hello=="
    ), r"adds 1 tag to existing MI with 1 tag, MI new style"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n{{unreferenced section}}\r\n}}\r\n{{unreferenced section}}\r\n\r\n==hello=="
        )
        == "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n{{expand section}}\r\n{{POV-section}}\r\n{{unreferenced section}}\r\n}}\r\n==hello=="
    ), r"duplicate tags not added"


def test_multiple_issues_new_section_single_tag() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues("==sec==\r\n{{multiple issues|\r\n{{wikify section}}\r\n}}")
        == "==sec==\r\n{{wikify section}}"
    ), r"converts new style 1-tag MI to single template"
    assert (
        parser.multiple_issues("==sec==\r\n{{multiple issues|1=\r\n{{wikify section}}\r\n}}")
        == "==sec==\r\n{{wikify section}}"
    ), r"converts new style 1-tag MI to single template, removing 1="
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|section=yes|\r\n{{wikify section}}\r\n}}"
        )
        == "==sec==\r\n{{wikify section}}"
    ), r"converts new style 1-tag MI to single template"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|\r\n{{wikify section|date=May 2012}}\r\n}}"
        )
        == "==sec==\r\n{{wikify section|date=May 2012}}"
    ), r"converts new style 1-tag MI to single template, tag with date"
    assert (
        parser.multiple_issues(
            "==sec==\r\n{{multiple issues|\r\n{{wikify section|reason=links}}\r\n}}"
        )
        == "==sec==\r\n{{wikify section|reason=links}}"
    ), r"converts new style 1-tag MI to single template, tag with extra parameter"


def test_multiple_issues_new_cleanup() -> None:
    S = W.for_site(EN)
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{wikify}}\r\n\r\n{{underlinked}}\r\n{{POV}}\r\n}}"
        )
        == "{{multiple issues|\r\n{{wikify}}\r\n{{underlinked}}\r\n{{POV}}\r\n}}"
    ), r"Cleans up excess newlines"
    assert (
        parser.multiple_issues("{{multiple issues|\r\n{{POV}}\r\n{{wikify}}\r\n}}\r\n{{wikify}}")
        == "{{multiple issues|\r\n{{POV}}\r\n{{wikify}}\r\n}}"
    ), r"De-duplicates tags"
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{POV}}\r\n{{wikify|date=May 2012}}\r\n}}\r\n{{wikify|date=May 2015}}"
        )
        == "{{multiple issues|\r\n{{POV}}\r\n{{wikify|date=May 2012}}\r\n}}"
    ), r"De-duplicates tags, takes earlier date"
    assert (
        parser.multiple_issues(
            "{{multiple issues|\r\n{{POV}}\r\n{{wikify|date=May 2012}}\r\n{{wikify|date=May 2015}}\r\n}}"
        )
        == "{{multiple issues|\r\n{{POV}}\r\n{{wikify|date=May 2012}}\r\n}}"
    ), r"De-duplicates tags within MI, takes earlier date"
    assert (
        parser.multiple_issues("{{multiple issues|\r\n{{wikify}}\r\n}}\r\n{{wikify}}")
        == r"{{wikify}}"
    ), r"De-duplicates tags, removes MI if only one tag remains"


def test_has_sic_tag() -> None:
    S = W.for_site(EN)
    assert genfixes.has_sic_tag(r"now helo [sic] there")
    assert genfixes.has_sic_tag(r"now helo[sic] there")
    assert genfixes.has_sic_tag(r"now helo (sic) there")
    assert genfixes.has_sic_tag(r"now helo {sic} there")
    assert genfixes.has_sic_tag(r"now helo [Sic] there")
    assert genfixes.has_sic_tag(r"now {{sic|helo}} there")
    assert genfixes.has_sic_tag(r"now {{sic|hel|o}} there")
    assert genfixes.has_sic_tag(r"now {{typo|helo}} there")
    assert not (genfixes.has_sic_tag(r"now sickened by"))
    assert not (genfixes.has_sic_tag(r"now helo sic there"))
