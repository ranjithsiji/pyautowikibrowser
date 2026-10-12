"""Port of AWB UnitTests/LinkTests.cs: link fixes (awb_l.core.parsers.wikilinks and others).

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: E501, F841, F401
# pyright: reportUnusedVariable=false

import pytest

from awb_l.core import genfixes, namespace, tools
from awb_l.core import wikiregexes as W
from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.parsers.parsers import DateLocale
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_site
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_test_sticky_links() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.sticky_links(r"[[Russian literature|Russian]] literature")
        == r"[[Russian literature]]"
    )
    assert (
        genfixes.sticky_links(r"[[Russian literature|Russian]]  literature")
        == r"[[Russian literature]]"
    )
    assert (
        genfixes.sticky_links(r"[[russian literature|Russian]] literature")
        == r"[[Russian literature]]"
    )
    assert (
        genfixes.sticky_links(r"[[Russian literature|russian]] literature")
        == r"[[russian literature]]"
    )
    assert (
        genfixes.sticky_links("[[Russian literature|Russian]]\nliterature")
        == "[[Russian literature|Russian]]\nliterature"
    )
    assert (
        genfixes.sticky_links(r"   [[Russian literature|Russian]] literature  ")
        == r"   [[Russian literature]]  "
    )
    assert (
        genfixes.sticky_links(r"[[Russian literature|Russian]] Literature")
        == r"[[Russian literature|Russian]] Literature"
    )
    assert (
        genfixes.sticky_links(
            r"[[Sacramento, California|Sacramento]], California's [[capital city]]"
        )
        == r"[[Sacramento, California|Sacramento]], California's [[capital city]]"
    )
    assert (
        genfixes.sticky_links(r"[[Russian literature|Russian literature]] was")
        == r"[[Russian literature|Russian literature]] was"
    ), r"bugfix – no exception when pipe same length as target"


def test_test_simplify_links() -> None:
    S = W.for_site(EN)
    assert genfixes.simplify_links(r"[[dog|dogs]]") == r"[[dog]]s"
    assert genfixes.simplify_links(r"[[Dog|dogs]]") == r"[[dog]]s"
    assert genfixes.simplify_links(r"[[dog|Dogs]]") == r"[[Dog]]s"
    assert genfixes.simplify_links(r"[[Dog|dog]]") == r"[[dog]]"
    assert genfixes.simplify_links(r"[[dog|Dog]]") == r"[[Dog]]"
    assert genfixes.simplify_links(r"[[Dog|Dog]]") == r"[[Dog]]"
    assert genfixes.simplify_links(r"[[Dog|dogs]]") == r"[[dog]]s"
    assert genfixes.simplify_links(r"[[dog|Dogs]]") == r"[[Dog]]s"
    assert genfixes.simplify_links(r"[[Dog|Dogs]]") == r"[[Dog]]s"
    assert genfixes.simplify_links(r"#REDIRECT[[dog|Dog]]") == r"#REDIRECT[[Dog]]"
    assert genfixes.simplify_links(r"[[funcy dog|funcy dogs]]") == r"[[funcy dog]]s"
    assert genfixes.simplify_links(r"[[dog|dog.]]") == r"[[dog]].", r"point inside wikilink"
    assert genfixes.simplify_links(r"[[Dog|dog.]]") == r"[[dog]].", r"point inside wikilink"
    assert genfixes.simplify_links(r"[[Dog|dog,]]") == r"[[dog]],", r"comma inside wikilink"
    assert genfixes.simplify_links(r"[[dog|dog,]]") == r"[[dog]],", r"comma inside wikilink"
    assert genfixes.simplify_links(r"([[dog|dogs)]]") == r"([[dog]]s)", (
        r"Bracket half inside wikilink"
    )
    assert genfixes.simplify_links(r"[[dog|(dog)]]") == r"([[dog]])", r"brackets inside wikilink"
    assert genfixes.simplify_links(r"[[funcy dog|funcy_dog]]") == r"[[funcy dog]]", (
        r"handles underscore in text: text"
    )
    assert genfixes.simplify_links(r"[[funcy_dog|funcy dog]]") == r"[[funcy dog]]", (
        r"handles underscore in text: target"
    )
    assert genfixes.simplify_links(r"[[funcy_dog|Funcy dog]]") == r"[[Funcy dog]]", (
        r"handles underscore in text: target"
    )
    S = set_site(underscored_titles=current_site().underscored_titles | {r"Funcy dog"})
    assert genfixes.simplify_links(r"[[funcy dog|funcy_dog]]") == r"[[funcy dog|funcy_dog]]", (
        r"handles underscore in text where article with underscore in title"
    )
    S = set_site(underscored_titles=current_site().underscored_titles - {r"Funcy dog"})
    assert genfixes.simplify_links(r"[[dog|dOgs]]") == r"[[dog|dOgs]]"
    assert genfixes.simplify_links(r"[[foo|foo3]]") == r"[[foo|foo3]]"
    assert genfixes.simplify_links(r"[[FOO|FOOBAR]]") == r"[[FOO|FOOBAR]]"
    assert genfixes.simplify_links(r"[[foo|fooBAR]]") == r"[[foo|fooBAR]]"
    assert genfixes.simplify_links(r"[[Elizabeth Gunn | Elizabeth Gunn]]") == r"[[Elizabeth Gunn]]"
    assert (
        genfixes.simplify_links(r"[[Big Bend, Texas | Big Bend]]")
        == r"[[Big Bend, Texas|Big Bend]]"
    )
    assert genfixes.simplify_links(r"{{foo|[[bar]] | boz}}]]") == r"{{foo|[[bar]] | boz}}]]"
    assert genfixes.simplify_links("{{foo|[[bar]]\r\n| boz}}]]") == "{{foo|[[bar]]\r\n| boz}}]]"
    assert genfixes.simplify_links(r"[[foo| bar]]") == r"[[foo|bar]]"
    assert genfixes.simplify_links(r"[[foo| bar ]]") == r"[[foo|bar]]"
    assert genfixes.simplify_links(r"[[Category:foo| bar]]") == r"[[Category:foo| bar]]"
    assert genfixes.simplify_links(r"[[Category:foo| bar ]]") == r"[[Category:foo| bar]]"
    assert genfixes.simplify_links(r"[[dog|]]") == r"[[dog|]]"
    nochange = r"[[File:T and E.jpg|right|thumbnail|With [[EW|E]] in 2004]]"
    assert genfixes.simplify_links(nochange) == nochange
    assert (
        genfixes.simplify_links(r"[[File:T and E.jpg|right|thumbnail|With [[dog|dogs]] in 2004]]")
        == r"[[File:T and E.jpg|right|thumbnail|With [[dog]]s in 2004]]"
    ), r"nested link handling"
    assert (
        genfixes.simplify_links(r"[[File:Lego cathedral.JPG | right | thumb | Lego cathedral]]")
        == r"[[File:Lego cathedral.JPG|right|thumb|Lego cathedral]]"
    ), r"Multiple whitespace cleanup around pipes"
    assert (
        genfixes.simplify_links(r"[[İstanbul Cup|Istanbul Cup]]")
        == r"[[İstanbul Cup|Istanbul Cup]]"
    ), r"No change when diacritics on first letter of page mean lowercase happens to match"
    assert genfixes.simplify_links(r"[[Нью-Мексико|(Нью-Мексико]]") == r"([[Нью-Мексико]])"
    assert genfixes.simplify_links(r"[[Ермітаж|(Ермітаж]])") == r"([[Ермітаж]])"


def test_fix_dates_html() -> None:
    S = W.for_site(EN)
    assert parser.fix_br_paragraphs(r"<p>some text") == "\r\n\r\nsome text"
    assert parser.fix_br_paragraphs(r"<p>[[some text|bar]]") == "\r\n\r\n[[some text|bar]]"
    assert parser.fix_br_paragraphs(r"<p>some text</p>") == "\r\n\r\nsome text\r\n\r\n"
    assert parser.fix_br_paragraphs(r"<p> some text") == "\r\n\r\nsome text"
    assert parser.fix_br_paragraphs(r"<br><br>some text") == "\r\n\r\nsome text"
    assert parser.fix_br_paragraphs(r"some text<p>") == "some text\r\n\r\n"
    assert parser.fix_br_paragraphs(r"some text<br><br>") == "some text\r\n\r\n"
    assert parser.fix_br_paragraphs(r"some text<br><br>word") == "some text\r\n\r\nword"
    assert parser.fix_br_paragraphs(r"|<p>some text") == r"|<p>some text"
    assert parser.fix_br_paragraphs(r"|<br><br>some text") == r"|<br><br>some text"
    assert parser.fix_br_paragraphs(r"!<p>some text") == r"!<p>some text"
    assert parser.fix_br_paragraphs(r"!<br><br>some text") == r"!<br><br>some text"
    genFixes.assert_not_changed(r"<blockquote><p>some text</blockquote>")
    genFixes.assert_not_changed(r"<blockquote>|<br><br>some text</blockquote>")
    assert (
        parser.fix_br_paragraphs(
            r"* {{Polish2|Krzepice (województwo dolnośląskie)|[[24 November]] [[2007]]}}<br><br>  "
        )
        == "* {{Polish2|Krzepice (województwo dolnośląskie)|[[24 November]] [[2007]]}}\r\n\r\n"
    )
    nochange = r"{{cite web | title = Hello April 14 2009 there | date=2011-11-13 }}"
    assert parser.fix_br_paragraphs(nochange) == nochange


def test_fix_dates_comma_errors() -> None:
    S = W.for_site(EN)
    correct1 = r"Retrieved on April 14, 2009 was"
    assert parser.fix_dates_a(r"Retrieved on April, 14, 2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April , 14 , 2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April , 14 ,2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April 14,2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April 14 ,2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April 14 2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April14,2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April14, 2009 was") == correct1
    assert parser.fix_dates_a(r"Retrieved on April14 2009 was") == correct1
    assert parser.fix_dates_a(correct1) == correct1
    image1 = r"now foo [[Image:Foo July 24 2009.png]] was"
    assert parser.fix_dates_a(image1) == image1
    image2 = r"now foo [[File:Foo July 24 2009.png]] was"
    assert parser.fix_dates_a(image2) == image2
    link1 = r"now [[July 29 1966, P.N.E.]] was"
    assert parser.fix_dates_a(link1) == link1
    correct2 = r"Retrieved on 14 April 2009 was"
    assert parser.fix_dates_a(r"Retrieved on 14 April, 2009 was") == correct2
    assert parser.fix_dates_a(r"Retrieved on 14 April , 2009 was") == correct2
    assert parser.fix_dates_a(r"Retrieved on 14 April,  2009 was") == correct2
    correct3 = r"[[Now]] on 14 April 2009 was"
    assert parser.fix_dates_a(r"[[Now]] on 14 April, 2009 was") == correct3
    nochange1 = r"On 14 April, 2590 people"
    nochange2 = r"Retrieved on April 142009 was"
    assert parser.fix_dates_a(nochange1) == nochange1
    assert parser.fix_dates_a(nochange2) == nochange2
    assert (
        parser.fix_dates_a("#####\r\n'''A''' (1 December 1920 &ndash; 28 May, 2013)")
        == "#####\r\n'''A''' (1 December 1920 &ndash; 28 May 2013)"
    )


def test_fix_dates_en_only() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fr")
    assert (
        parser.fix_dates_a(r"Retrieved on April, 14, 2009 was")
        == r"Retrieved on April, 14, 2009 was"
    )
    assert parser.fix_dates_b(r"from (1900-1933) there", False, False) == r"from (1900-1933) there"
    S = set_lang(r"en")
    correct1 = r"Retrieved on April 14, 2009 was"
    assert parser.fix_dates_a(r"Retrieved on April, 14, 2009 was") == correct1
    correct = r"from (1900–1933) there"
    assert parser.fix_dates_b(r"from (1900-1933) there", False, False) == correct


def test_fix_dates_ranges() -> None:
    S = W.for_site(EN)
    correct1 = r"On 3–17 May 2009 a dog"
    assert parser.fix_dates_a(r"On 3-17 May 2009 a dog") == correct1
    assert parser.fix_dates_a(r"On 3 - 17 May 2009 a dog") == correct1
    assert parser.fix_dates_a(r"On 3 -17 May 2009 a dog") == correct1
    assert parser.fix_dates_a(r"On 3 May-17 May 2009 a dog") == correct1
    assert parser.fix_dates_a(r"On 3 May - 17 May 2009 a dog") == correct1
    assert parser.fix_dates_a(r"On 3 May – 17 May 2009 a dog") == correct1
    assert parser.fix_dates_a(r"On 3 May – 17 May, 2009 a dog") == correct1
    correct2 = r"On May 3–17, 2009 a dog"
    assert parser.fix_dates_a(r"On May 3-17, 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3-17 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3 - 17 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3   -17 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3 - May 17 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3 - May 17, 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3 – May 17 2009 a dog") == correct2
    assert parser.fix_dates_a(r"On May 3 – May 17, 2009 a dog") == correct2
    nochange1 = r"May 17 - 13,009 dogs"
    assert parser.fix_dates_a(nochange1) == nochange1
    nochange2 = r"May 2-4-0"
    assert parser.fix_dates_a(nochange2) == nochange2
    correct3 = r"May–June 2010"
    assert parser.fix_dates_a(r"May-June 2010") == correct3, r"endash set for month range"
    assert parser.fix_dates_a(correct3) == correct3
    assert parser.fix_dates_a(r"from 1904 – 11 May 1956 there") == r"from 1904 – 11 May 1956 there"
    DateToYear = r"'''Nowell''' (May 16, 1872 - 1940), was"
    genFixes.assert_change(DateToYear, DateToYear.replace(r"-", r"–"))
    genFixes.assert_change(DateToYear.replace(r" - ", r"-"), DateToYear.replace(r"-", r"–"))
    DateToYear2 = r"'''Nowell''' (16 May 1872–1940), was"
    genFixes.assert_change(DateToYear2, DateToYear2.replace(r"–", r" – "))
    genFixes.assert_change(DateToYear2.replace(r"–", r"-"), DateToYear2.replace(r"–", r" – "))
    genFixes.assert_not_changed(r"Volume 1, 2001–2004 was")
    genFixes.assert_not_changed(r"ISBN 1-883402-17-4 February 1998, hardcover")


def test_test_full_year_ranges() -> None:
    S = W.for_site(EN)
    correct = r"from (1900–1933) there"
    assert parser.fix_dates_b(r"from (1900-1933) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900  –  1933) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900 -1933) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900 - 1933) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900 -  1933) there", False, False) == correct
    assert (
        parser.fix_dates_b(r"from (1900 - 1901) there", False, False) == r"from (1900–1901) there"
    )
    assert (
        parser.fix_dates_b(r"from (1900-1933, 2000) there", False, False)
        == r"from (1900–1933, 2000) there"
    )
    assert (
        parser.fix_dates_b(r"from (1900-1933, 2000-2002) there", False, False)
        == r"from (1900–1933, 2000–2002) there"
    )
    assert (
        parser.fix_dates_b(r"from ( 1900-1933) there", False, False) == r"from ( 1900–1933) there"
    )
    assert parser.fix_dates_b(r"from 1950-1960,", False, False) == r"from 1950–1960,"
    assert parser.fix_dates_b(r"|1950-1960|", False, False) == r"|1950–1960|"
    assert (
        parser.fix_dates_b(r"(1950-1960 and 1963-1968)", False, False)
        == r"(1950–1960 and 1963–1968)"
    )
    assert parser.fix_dates_b(r"or 1900 - 1901,", False, False) == r"or 1900–1901,"
    assert parser.fix_dates_b(r"for 1900 - 1901,", False, False) == r"for 1900–1901,"
    genFixes.assert_not_changed(r"from (1900–1870) there")
    genFixes.assert_not_changed(r"from (1900&ndash;1933) there")
    genFixes.assert_not_changed(r"from (1900–1933) there")
    assert (
        parser.fix_dates_b("now between 1900-1920\r\nwas", False, False)
        == "now between 1900–1920\r\nwas"
    )
    BadRange = r"from 1950-1920,"
    assert parser.fix_dates_b(BadRange, False, False) == BadRange
    BadRange = r"from 1950 – 1920,"
    assert parser.fix_dates_b(BadRange, False, False) == BadRange
    BadRange = r"from 1980-70,"
    assert parser.fix_dates_b(BadRange, False, False) == BadRange
    assert (
        parser.fix_dates_b(r"over 1 April 2004-5 July 2009.", False, False)
        == r"over 1 April 2004 – 5 July 2009."
    )
    assert (
        parser.fix_dates_b(r"over April 1, 2004–July 5, 2009.", False, False)
        == r"over April 1, 2004 – July 5, 2009."
    )


def test_circa_year_ranges() -> None:
    S = W.for_site(EN)
    assert parser.fix_dates_b(r"c. 1950 - 1960,", False, False) == r"c. 1950 – 1960,"
    assert parser.fix_dates_b(r"ca. 1950 - 1960,", False, False) == r"ca. 1950 – 1960,"
    assert parser.fix_dates_b(r"circa 1950 - 1960,", False, False) == r"circa 1950 – 1960,"
    genFixes.assert_not_changed(r"{{Circa}} 1950 – 1960,")
    genFixes.assert_not_changed(r"[[c.]] 1950 - 1960,")
    genFixes.assert_not_changed(r"[[c]]. 1950 - 1960,")
    genFixes.assert_not_changed(r"[[c]] 1950 - 1960,")
    genFixes.assert_not_changed(r"[[circa]] 1950 - 1960,")
    genFixes.assert_not_changed(r"[[circa|c.]] 1950 - 1960,")
    genFixes.assert_not_changed(r"[[circa|c]]. 1950 - 1960,")
    genFixes.assert_not_changed(r"{{circa}} 1950 - 1960,")
    genFixes.assert_not_changed(r"{{Circa}} 1950 - 1960,")
    genFixes.assert_not_changed(r"circle 1950 - 1960,")
    genFixes.assert_not_changed(r"[[Foo (1950-1960)|Foo]]")
    genFixes.assert_not_changed(r"[[Foo (1950 - 1960)|Foo]]")


def test_test_year_to_present_ranges() -> None:
    S = W.for_site(EN)
    present = r"from 2002–present was"
    assert parser.fix_dates_b(r"from 2002-present was", False, False) == present
    assert parser.fix_dates_b(r"from 2002 -   present was", False, False) == present
    assert parser.fix_dates_b(r"from 2002–present was", False, False) == present
    assert parser.fix_dates_b(r"from 2002-Present was", False, False) == r"from 2002–Present was"
    present2 = "== Members ==\r\n* [[Nick Hexum]] - Vocals, [[Rhythm Guitar]], Programming (1989 - present)\r\n* [[S. A. Martinez|Doug Martinez]] - Vocals, [[Phonograph|Turntables]], DJ (1992 - present)\r\n* [[Tim Mahoney (guitarist)|Tim Mahoney]] - [[Lead Guitar]] (1991 - present)\r\n* [[P-Nut|Aaron Wills]] - [[Bass guitar]] (1989 - present)\r\n* [[Chad Sexton]] - [[Drum]]s, Programming, Percussion (1989 - present)"
    assert parser.fix_dates_b(present2, False, False) == present2.replace(r" - p", r"–p")
    genFixes.assert_not_changed(r"* 2000 - presented")


def test_test_date_to_present_ranges() -> None:
    S = W.for_site(EN)
    assert (
        parser.fix_dates_b(r"from May 2002 - present was", False, False)
        == r"from May 2002 – present was"
    )
    assert (
        parser.fix_dates_b(r"from May 2002-present was", False, False)
        == r"from May 2002 – present was"
    )
    assert (
        parser.fix_dates_b(r"from May 11, 2002-present was", False, False)
        == r"from May 11, 2002 – present was"
    )
    assert (
        parser.fix_dates_b(r"from May 11, 2002 - present was", False, False)
        == r"from May 11, 2002 – present was"
    )
    assert (
        parser.fix_dates_b(r"from 2002 - present was", False, False) == r"from 2002–present was"
    ), r"year range, becomes unspaced"
    assert parser.fix_dates_b(r"from 2002-present was", False, False) == r"from 2002–present was", (
        r"year range, unspaced"
    )
    assert (
        parser.fix_dates_b(r"Deputy-leader 2008-11, 2014-present", False, False)
        == r"Deputy-leader 2008-11, 2014–present"
    ), r"Endash unspaced when year to present, ignore previous year range"


def test_test_shortened_year_ranges() -> None:
    S = W.for_site(EN)
    correct = r"from (1900–33) there"
    assert parser.fix_dates_b(r"from (1900-33) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900 -33) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900 - 33) there", False, False) == correct
    assert parser.fix_dates_b(r"from (1900 -  33) there", False, False) == correct
    assert (
        parser.fix_dates_b(r"from (1900 - 1901) there", False, False) == r"from (1900–1901) there"
    )
    assert (
        parser.fix_dates_b(r"from (1900-33, 2000) there", False, False)
        == r"from (1900–33, 2000) there"
    )
    assert (
        parser.fix_dates_b(r"from (1900-33, 2000-2002) there", False, False)
        == r"from (1900–33, 2000–2002) there"
    )
    assert parser.fix_dates_b(r"from ( 1900-33) there", False, False) == r"from ( 1900–33) there"
    assert parser.fix_dates_b(r"from 1950-60,", False, False) == r"from 1950–60,"
    assert (
        parser.fix_dates_b(r"x the 2010-11, 2011-12 and 2013-14 x", False, False)
        == r"x the 2010–11, 2011–12 and 2013–14 x"
    )
    assert parser.fix_dates_b(r"(1950-60 and 1963-68)", False, False) == r"(1950–60 and 1963–68)"
    genFixes.assert_not_changed(r"from (1920–18) there")
    genFixes.assert_not_changed(r"from (1900&ndash;33) there")
    genFixes.assert_not_changed(r"from (1900–33) there")


def test_fix_living_things_related_dates() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_living_things_related_dates(r"test text") == r"test text"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b. [[21 February]] [[2008]])")
        == r"'''John Doe''' (born [[21 February]] [[2008]])"
    ), r"b. expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John O'Doe''' (b. [[21 February]] [[2008]])")
        == r"'''John O'Doe''' (born [[21 February]] [[2008]])"
    ), r"b. expanded, name has apostrophe"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b. 21 February 2008)")
        == r"'''John Doe''' (born 21 February 2008)"
    ), r"non-wikilinked dates supported"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' ([[21 February]] [[2008]]–)")
        == r"'''John Doe''' (born [[21 February]] [[2008]])"
    ), r"dash for born expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John O'Doe''' ([[21 February]] [[2008]]–)")
        == r"'''John O'Doe''' (born [[21 February]] [[2008]])"
    ), r"dash for born expanded, name has apostrophe"
    assert (
        genfixes.fix_living_things_related_dates(
            r"'''John Doe''' ([[21 February]] [[2008]] &ndash;)"
        )
        == r"'''John Doe''' (born [[21 February]] [[2008]])"
    ), r"dash for born expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (born: [[21 February]] [[2008]])")
        == r"'''John Doe''' (born [[21 February]] [[2008]])"
    ), r"born: tidied"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (Born: [[21 February]] [[2008]])")
        == r"'''John Doe''' (born [[21 February]] [[2008]])"
    ), r"born: tidied"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b. March 6, 2008)")
        == r"'''John Doe''' (born March 6, 2008)"
    ), r"b. expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b. 2008)")
        == r"'''John Doe''' (born 2008)"
    ), r"b. expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b.2008)")
        == r"'''John Doe''' (born 2008)"
    ), r"b. expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (born on 2008)")
        == r"'''John Doe''' (born 2008)"
    ), r"born on fixed"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (Born 2008)")
        == r"'''John Doe''' (born 2008)"
    ), r"Born fixed"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b. March 6, 2008, London)")
        == r"'''John Doe''' (born March 6, 2008, London)"
    ), r"b. expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (b. March 6, 2008 in London)")
        == r"'''John Doe''' (born March 6, 2008 in London)"
    ), r"b. expanded"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (born on March 6, 2008, London)")
        == r"'''John Doe''' (born March 6, 2008, London)"
    ), r"born on fixed"
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (d. [[21 February]] [[2008]])")
        == r"'''John Doe''' (died [[21 February]] [[2008]])"
    )
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (d.[[21 February]] [[2008]])")
        == r"'''John Doe''' (died [[21 February]] [[2008]])"
    )
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (d.2008)")
        == r"'''John Doe''' (died 2008)"
    )
    assert (
        genfixes.fix_living_things_related_dates(r"'''John Doe''' (d. February 21, 2008)")
        == r"'''John Doe''' (died February 21, 2008)"
    )
    assert (
        genfixes.fix_living_things_related_dates(r"'''John O'Doe''' (d. [[21 February]] [[2008]])")
        == r"'''John O'Doe''' (died [[21 February]] [[2008]])"
    )
    assert (
        genfixes.fix_living_things_related_dates(
            r"'''Willa Klug Baum''' (born [[October 4]], [[1926]], died May 18, 2006)"
        )
        == r"'''Willa Klug Baum''' ([[October 4]], [[1926]] – May 18, 2006)"
    )
    assert (
        genfixes.fix_living_things_related_dates(
            r"'''Willa Klug Baum''' (b.1926, died May 18, 2006)"
        )
        == r"'''Willa Klug Baum''' (1926 – May 18, 2006)"
    )
    Nochange = "{{Infobox baseball team|\r\n  FormerNames= '''[[Nishi-Nippon Railroad|Nishitetsu]] Clippers''' (1950)<br>'''Nishitetsu Lions''' (1951-1972)<br>'''Taiheiyo Club Lions''' (1973–1976)<br>'''Crown Lighter Lions''' (1977–1978)<br>'''Seibu Lions''' (1979–2007)<br>'''Saitama Seibu Lions''' (2008–)|\r\n  foo=bar }}"
    assert genfixes.fix_living_things_related_dates(Nochange) == Nochange
    Nochange2 = r"*'''[[Luís Godinho Lopes|Luís Filipe Fernandes David Godinho Lopes]]''' (2011–)"
    assert genfixes.fix_living_things_related_dates(Nochange2) == Nochange2
    Nochange3 = r"** '''1st''' Andy Brown '''52''' (2008-)"
    assert genfixes.fix_living_things_related_dates(Nochange3) == Nochange3
    Nochange4 = r"# '''[[Luís Godinho Lopes|Luís Filipe Fernandes David Godinho Lopes]]''' (2011–)"
    assert genfixes.fix_living_things_related_dates(Nochange4) == Nochange4


def test_unlinked_floruit() -> None:
    S = W.for_site(EN)
    LinkedFloruit = (
        "'''Foo''' ([[floruit|fl.]] 550) was a peasant.\r\n\r\n==Time==\r\nFoo was happy"
    )
    genFixes.assert_not_changed(LinkedFloruit)
    genFixes.assert_change(
        "'''Foo''' (fl. 550) was a peasant.\r\n\r\n==Time==\r\nFoo was happy", LinkedFloruit
    )
    genFixes.assert_change(
        "'''Foo''' (fl 550) was a peasant.\r\n\r\n==Time==\r\nFoo was happy", LinkedFloruit
    )
    genFixes.assert_change(
        "'''Foo''' ( fl. 550) was a peasant.\r\n\r\n==Time==\r\nFoo was happy", LinkedFloruit
    )
    genFixes.assert_change(
        "'''Foo''' (Fl. 550) was a peasant.\r\n\r\n==Time==\r\nFoo was happy", LinkedFloruit
    )
    Floruit550 = "'''Foo''' ([[floruit|fl.]] 550) was a peasant.\r\nFoo was happy\r\nOther (fl. 1645) was also"
    genFixes.assert_not_changed(Floruit550)
    genFixes.assert_change(
        "'''Foo''' (fl. 550) was a peasant.\r\nFoo was happy\r\nOther (fl. 1645) was also",
        Floruit550,
    )
    FloruitLaterSection = "'''Foo''' was a peasant.\r\n\r\n==Other==\r\nOther (fl. 1645) was also"
    FloruitTwice = r"'''Foo''' (fl. 55) was a peasant, related to other (fl. 600)"
    genFixes.assert_not_changed(FloruitLaterSection)
    genFixes.assert_change(
        FloruitTwice, r"'''Foo''' ([[floruit|fl.]] 55) was a peasant, related to other (fl. 600)"
    )
    genFixes.assert_not_changed(
        r"{{cite encyclopedia|encyclopedia=ODNB|url=http://www.oxforddnb.com/view/olddnb/21073 |title=Packe, Christopher (fl. 1796)}}"
    )


def test_fix_people_categories_tests() -> None:
    S = W.for_site(EN)
    a0 = r"'''Fred Smith''' (born 1960) is a bloke."
    assert genfixes.fix_people_categories(a0, r"foo") == a0
    bug1 = "{{BLP unsourced|date=March 2010}}\r\n\r\n'''Z''' (born 2 January{{Year needed|date=January 2010|reason=Fix this date immediately or remove it; it look}} in ."
    assert genfixes.fix_people_categories(bug1, r"Foo") == bug1


def test_get_info_box_field_value() -> None:
    S = W.for_site(EN)
    Year = list([r"year"])
    assert (
        genfixes.get_info_box_field_value(
            "hello {{infobox foo\r\n|year=1990\r\n|other=great}} now", Year
        )
        == r"1990"
    )
    assert (
        genfixes.get_info_box_field_value(
            "hello {{infobox foo\r\n|  year  =  1990\r\n|other=great}} now", Year
        )
        == r"1990"
    )
    assert (
        genfixes.get_info_box_field_value(
            "hello {{infobox foo\r\n|  Year  =  1990\r\n|other=great}} now", Year
        )
        == r"1990"
    )
    assert len(genfixes.get_info_box_field_value(r"hello now", Year)) == 0
    assert (
        len(
            genfixes.get_info_box_field_value(
                "hello {{infobox foo\r\n|  Year  =  1990\r\n|other=great}} now", list([r"yearly"])
            )
        )
        == 0
    )
    assert (
        genfixes.get_info_box_field_value(
            "hello {{infobox foo\r\n|  Year  =  1990  |some=where\r\n|other=great}} now", Year
        )
        == r"1990"
    )
    assert (
        len(
            genfixes.get_info_box_field_value(
                "hello {{infobox foo\r\n|  Year  =  <!--1990-->\r\n|other=great}} now", Year
            )
        )
        == 0
    )
    assert (
        len(
            genfixes.get_info_box_field_value(
                "hello {{infobox foo\r\n|  Year  =  <ref>1990</ref>\r\n|other=great}} now", Year
            )
        )
        == 0
    )
    assert (
        len(
            genfixes.get_info_box_field_value(
                "hello {{infobox foo\r\n|  Year  =  {{efn|1990}}\r\n|other=great}} now", Year
            )
        )
        == 0
    )


def test_remove_duplicate_wiki_links() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.remove_duplicate_wiki_links(r"now [[foo|bar]] was [[foo|bar]] too")
        == r"now [[foo|bar]] was bar too"
    )
    assert (
        genfixes.remove_duplicate_wiki_links(r"now [[foo|bar]] was [[foo|bar]]s too")
        == r"now [[foo|bar]] was bars too"
    )
    assert (
        genfixes.remove_duplicate_wiki_links("now [[foo|bar]]\r\nwas [[foo|bar]] too")
        == "now [[foo|bar]]\r\nwas [[foo|bar]] too"
    )
    assert (
        genfixes.remove_duplicate_wiki_links(r"now [[foo|bar]] was [[Foo|bar]] too")
        == r"now [[foo|bar]] was [[Foo|bar]] too"
    )
    assert (
        genfixes.remove_duplicate_wiki_links(r"now [[foo bar]] was [[Foo bar]] too")
        == r"now [[foo bar]] was [[Foo bar]] too"
    )
    assert (
        genfixes.remove_duplicate_wiki_links(r"now [[foo bar]] was [[foo bar]] too")
        == r"now [[foo bar]] was foo bar too"
    )
    assert (
        genfixes.remove_duplicate_wiki_links(r"now [[foo|bar]] was [[foo]] too")
        == r"now [[foo|bar]] was [[foo]] too"
    )


def test_canonicalize_title_raw_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.canonicalize_title_raw(r"foo_bar") == r"foo bar"
    assert genfixes.canonicalize_title_raw(r"foo%22bar%22") == r'foo"bar"'
    assert genfixes.canonicalize_title_raw(r"foo+bar") == r"foo+bar"
    assert genfixes.canonicalize_title_raw(r"foo_bar", False) == r"foo bar"
    assert genfixes.canonicalize_title_raw(r"foo_bar ", False) == r"foo bar "
    assert genfixes.canonicalize_title_raw(r"foo_bar", True) == r"foo bar"
    assert genfixes.canonicalize_title_raw(r"foo_bar ", True) == r"foo bar"
    assert genfixes.canonicalize_title_raw(r" foo_bar", True) == r"foo bar"
    assert (
        genfixes.canonicalize_title_raw(r"Bugs#If_a_selflink_is_also_bolded%2C_AWB_should")
        == r"Bugs#If a selflink is also bolded, AWB should"
    )


def test_remove_template_namespace() -> None:
    S = W.for_site(EN)
    assert genfixes.remove_template_namespace(r"{{Template:foo}}") == r"{{foo}}"
    assert genfixes.remove_template_namespace(r"{{Template:Foo}}") == r"{{Foo}}"
    assert genfixes.remove_template_namespace(r"{{Template:foo_bar}}") == r"{{foo bar}}"
    assert genfixes.remove_template_namespace(r"Template:Foo") == r"Template:Foo", (
        r"no change if it is not a real template"
    )
    assert genfixes.remove_template_namespace(r"[[Template:Foo]]") == r"[[Template:Foo]]", (
        r"no change if it is not a real template"
    )
    assert (
        genfixes.remove_template_namespace(
            r"{{Clarify|date=May 2014|reason=Use Template:Cite web or similar}}"
        )
        == r"{{Clarify|date=May 2014|reason=Use Template:Cite web or similar}}"
    ), r"no change if it is part of a comment"
    assert (
        genfixes.remove_template_namespace(
            r"{{Template:Foo|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
        )
        == r"{{Foo|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    )


def test_fix_link_whitespace_spacing() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_link_whitespace(r"[[Foo]]", r"Test") == r"[[Foo]]"
    assert genfixes.fix_link_whitespace(r"[[Foo Bar]]", r"Test") == r"[[Foo Bar]]"
    assert genfixes.fix_link_whitespace(r"[[Foo  Bar]]", r"Test") == r"[[Foo Bar]]"
    assert genfixes.fix_link_whitespace(r"[[Foo  Bar  was]]", r"Test") == r"[[Foo Bar was]]", (
        r"fixes multiple double spaces in single link"
    )
    assert genfixes.fix_link_whitespace(r"[[Foo  Bar|Bar]]", r"Test") == r"[[Foo Bar|Bar]]"
    assert (
        genfixes.fix_link_whitespace(
            r"[[64th Fighter Aviation Corps|64th  Fighter Aviation Corps]]", r"Test"
        )
        == r"[[64th Fighter Aviation Corps|64th Fighter Aviation Corps]]"
    ), r"long wikilink double space"
    assert genfixes.fix_link_whitespace(r"[[      Foo    ]] was", r"Test") == r"[[Foo]] was", (
        r"multiple spaces, space after"
    )
    assert genfixes.fix_link_whitespace(r"[[      Foo2    ]]A", r"Test") == r"[[Foo2]] A", (
        r"multiple spaces, word after"
    )
    assert genfixes.fix_link_whitespace(r"[[      Foo3]]", r"Test") == r"[[Foo3]]", (
        r"multiple spaces only at start"
    )


def test_fix_link() -> None:
    S = W.for_site(EN)
    assert ((_t := genfixes.fix_links(r"[[Foo_bar]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo bar]]"
    assert not (nochange)
    doubleApos = r"[[Image:foo%27%27s.jpg|thumb|200px|Bar]]"
    assert ((_t := genfixes.fix_links(doubleApos, r"a")), (nochange := _t[1]))[0][0] == doubleApos
    S = set_site(
        underscored_titles=current_site().underscored_titles
        | frozenset(list([r"Size t", r"Mod perl", r"Mod mono"]))
    )
    assert ((_t := genfixes.fix_links(r"[[size_t]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[size_t]]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[mod_perl]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[mod_perl]]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[mod_mono]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[mod_mono]]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[Mod_mono]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Mod_mono]]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[E|Mod_mono]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[E|Mod_mono]]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[Mod_mono#link]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Mod_mono#link]]"
    assert nochange
    assert (
        (
            (
                _t := genfixes.fix_links(
                    r"[[List of The Amazing Spider-Man issues#The Amazing Spider-Man #648–current x|List of issues]]",
                    r"a",
                )
            ),
            (nochange := _t[1]),
        )[0][0]
        == r"[[List of The Amazing Spider-Man issues#The Amazing Spider-Man #648–current x|List of issues]]"
    ), r"Does not break section links with hash and space"
    assert ((_t := genfixes.fix_links(r"[[Foo#nice%20example|F]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo#nice example|F]]", r"%20 replaced in target"
    assert ((_t := genfixes.fix_links(r"[[Foo|bar|]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo|bar]]", r"Fixes excess trailing pipe"
    assert ((_t := genfixes.fix_links(r"[[Foo|bar | ]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo|bar]]", r"Fixes excess trailing pipe"
    assert ((_t := genfixes.fix_links(r"[[Foo_bar]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo bar]]", r"Fixes underscore"
    assert ((_t := genfixes.fix_links(r"[[Foo_bar#ab_c]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo bar#ab c]]", r"Fixes underscore"
    assert (
        (
            _t := genfixes.fix_links(
                r"[[Mercedes-Benz C-Class#W202 %281993%E2%80%932000%29|Mercedes-Benz C-Class]]",
                r"a",
            )
        ),
        (nochange := _t[1]),
    )[0][0] == r"[[Mercedes-Benz C-Class#W202 (1993–2000)|Mercedes-Benz C-Class]]", (
        r"Fixes percent encoding"
    )
    assert ((_t := genfixes.fix_links(r"[[foo{{!}}bar]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|bar]]", r"Fixes pipe"
    assert ((_t := genfixes.fix_links(r"[[foo{{!}}]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|]]", r"Fixes pipe"
    assert ((_t := genfixes.fix_links(r"[[Repeat sign|{{!}}: ]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[Repeat sign|{{!}}: ]]", r"Do nothing in the only exception"
    assert ((_t := genfixes.fix_links(r"[[|foo]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[|foo]]", r"No change if single leading pipe"
    assert ((_t := genfixes.fix_links(r"[[|foo|bar]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|bar]]", r"Fixes excess leading pipe"
    assert ((_t := genfixes.fix_links(r"[[|  foo|bar]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|bar]]", r"Fixes excess leading pipe & whitespace"
    assert ((_t := genfixes.fix_links(r"[[|thumb|300px]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[|thumb|300px]]", r"Nochange: thumb"
    assert ((_t := genfixes.fix_links(r"[[|thumbnail|300px]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[|thumbnail|300px]]", r"Nochange: thumbnail"
    assert (
        (_t := genfixes.fix_links("A\r\n[[Category:Soldiers|XXX]]", r"Category:Soldiers")),
        (nochange := _t[1]),
    )[0][0] == r"A" + "\r\n", r"Category self link"
    iarchive = r"[[iarchive:a0000camp_y0p5/page/82/mode/2up|Foo]]"
    assert ((_t := genfixes.fix_links(iarchive, r"A")), (nochange := _t[1]))[0][0] == iarchive, (
        r"iarchive"
    )


def test_fix_link_bold_italic() -> None:
    S = W.for_site(EN)
    assert ((_t := genfixes.fix_links(r"[[foo|''foo'']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"''[[foo|foo]]''"
    assert not (nochange)
    assert ((_t := genfixes.fix_links(r"[[foo|'''Foo''']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"'''[[foo|Foo]]'''"
    assert not (nochange)
    assert ((_t := genfixes.fix_links(r"[[foo|'''''Foo''''']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"'''''[[foo|Foo]]'''''"
    assert not (nochange)
    assert ((_t := genfixes.fix_links(r"[[foo|''foo'' ]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"''[[foo|foo]]''"
    assert not (nochange)
    assert ((_t := genfixes.fix_links(r"[[foo| ''foo'']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"''[[foo|foo]]''"
    assert not (nochange)
    assert ((_t := genfixes.fix_links(r"[[foo| ''foo'' ]]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"''[[foo|foo]]''"
    assert not (nochange)
    assert (
        (_t := genfixes.fix_links(r"[[foo|'''Foo''']] [[bar|''bar'']]", r"a")),
        (nochange := _t[1]),
    )[0][0] == r"'''[[foo|Foo]]''' ''[[bar|bar]]''"
    assert ((_t := genfixes.fix_links(r"''[[foo|'''foo''']]''", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"''[[foo|'''foo''']]''"
    assert nochange
    assert (
        (_t := genfixes.fix_links(r"[[foo|'''Foo''']] ''[[foor|bar]]''", r"a")),
        (nochange := _t[1]),
    )[0][0] == r"'''[[foo|Foo]]''' ''[[foor|bar]]''"
    assert ((_t := genfixes.fix_links(r"[[foo|'bar']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|'bar']]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[foo|''bar'']]'", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|''bar'']]'"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[foo|]]", r"a")), (nochange := _t[1]))[0][0] == r"[[foo|]]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[foo|''b'']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|''b'']]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[foo|A ''bar'']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|A ''bar'']]"
    assert nochange
    assert ((_t := genfixes.fix_links(r"[[foo|A '''bar''']]", r"a")), (nochange := _t[1]))[0][
        0
    ] == r"[[foo|A '''bar''']]"
    assert nochange


def test_fix_self_interwikis() -> None:
    S = W.for_site(EN)
    assert ((_t := genfixes.fix_links(r"[[en:Foo]]", r"Bar")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo]]"
    assert ((_t := genfixes.fix_links(r"[[en:Foo|Bar]]", r"T1")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo|Bar]]"
    FrIW = r"Now [[fr:Here]]"
    assert ((_t := genfixes.fix_links(FrIW, r"Bar")), (nochange := _t[1]))[0][0] == FrIW
    assert parser.sort_interwikis
    S = set_site(lang_code=r"en", project="commons")
    EnInterwiki = r"[[en:Foo]]"
    assert ((_t := genfixes.fix_links(EnInterwiki, r"Test")), (nochange := _t[1]))[0][
        0
    ] == EnInterwiki, r"en interwiki not changed on commons"
    S = set_site(lang_code=r"en", project="wikipedia")
    assert ((_t := genfixes.fix_links(EnInterwiki, r"Test")), (nochange := _t[1]))[0][
        0
    ] == r"[[Foo]]", r"self-interwiki converted on en-wiki"


def test_has_see_also_after_notes_references_or_external_links() -> None:
    S = W.for_site(EN)
    start = "start\r\n"
    seeAlso = "Foo\r\n==See also==\r\nx\r\n"
    extlinks = "==External links==\r\nx\r\n"
    notes = "==Notes==\r\nx\r\n"
    references = "== References==\r\nx\r\n"
    notes4 = "==== Notes ====\r\nx\r\n"
    assert not (genfixes.has_see_also_after_notes_references_or_external_links(r"")), (
        r"Empty string check"
    )
    assert not (genfixes.has_see_also_after_notes_references_or_external_links(start + seeAlso)), (
        r"Only see also"
    )
    assert not (
        genfixes.has_see_also_after_notes_references_or_external_links(start + seeAlso + extlinks)
    ), r"see also external links"
    assert genfixes.has_see_also_after_notes_references_or_external_links(
        start + extlinks + seeAlso
    ), r"external links then see also"
    assert genfixes.has_see_also_after_notes_references_or_external_links(
        start + notes + seeAlso
    ), r"notes then see also"
    assert genfixes.has_see_also_after_notes_references_or_external_links(
        start + references + seeAlso
    ), r"refs then see also"
    assert genfixes.has_see_also_after_notes_references_or_external_links(
        start + references + seeAlso + notes
    ), r"refs then see also then notes"
    assert not (
        genfixes.has_see_also_after_notes_references_or_external_links(start + notes4 + seeAlso)
    ), r"L4 notes ignored"


def test_unclosed_tags() -> None:
    S = W.for_site(EN)
    uct = {}
    uct = genfixes.unclosed_tags(r"<pre>bar</pre>")
    assert len(uct) == 0
    uct = genfixes.unclosed_tags(r"<gallery>File:bar</gallery>")
    assert len(uct) == 0
    uct = genfixes.unclosed_tags(r"<math>bar</math>")
    assert len(uct) == 0
    uct = genfixes.unclosed_tags(r"<math chem>bar</math>")
    assert len(uct) == 0
    uct = genfixes.unclosed_tags(r"<source>bar</source> <ref name=Foo>boo</ref>")
    assert len(uct) == 0
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <ref name=Foo>boo</ref>")
    assert len(uct) == 0
    uct = genfixes.unclosed_tags(
        '<source lang="text">\r\n<typename T>\r\n<std::string, T>\r\n<typename T>\r\n<std::string, T>\r\n<std::string, T> \r\n<std::string, int>\r\n<int>\r\n<typename T>\r\n<std::string, T>\r\n<std::string, int>\r\n<int>\r\n</source>'
    )
    assert len(uct) == 0, r"Ignore other tags"
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <math> not ended")
    assert len(uct) == 1, r"math"
    assert 15 in uct
    assert 6 in uct.values()
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <center> not ended")
    assert len(uct) == 1, r"center"
    assert 15 in uct
    assert 8 in uct.values()
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <center> <center>a</center> not ended")
    assert len(uct) == 1, r"center double"
    assert 15 in uct, r"center key"
    assert 8 in uct.values(), r"center value"
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <sup> <sup>a</sup> not ended")
    assert len(uct) == 1
    assert 15 in uct, r"sup key"
    assert 5 in uct.values(), r"sup value"
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <sub> <sub>a</sub> not ended")
    assert len(uct) == 1, r"sub"
    assert 15 in uct, r"sub key"
    assert 5 in uct.values(), r"sub value"
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <ref name=<ref name=Foo/> not ended")
    assert len(uct) == 1, r"ref"
    assert 15 in uct
    assert 35 in uct.values()
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <ref> not ended")
    assert len(uct) == 1, r"ref 2"
    assert 15 in uct
    assert 5 in uct.values()
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <ref name='foo'> not ended")
    assert len(uct) == 1, r"ref name"
    assert 15 in uct
    assert 16 in uct.values()
    uct = genfixes.unclosed_tags(r'<pre>bar</pre> <source lang="bar"> not ended')
    assert len(uct) == 1, r"source"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <small> not ended")
    assert len(uct) == 1, r"small"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> < code> not ended")
    assert len(uct) == 1, r"code"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> < nowiki > not ended")
    assert len(uct) == 1, r"nowiki"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <pre> not ended")
    assert len(uct) == 1, r"pre"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> </pre> not opened")
    assert len(uct) == 1, r"/pre"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <gallery> not ended")
    assert len(uct) == 1, r"gallery"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> </gallery> not opened")
    assert len(uct) == 1, r"/gallery"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<pre>bar</pre> <!-- not ended")
    assert len(uct) == 1, r"<!--"
    assert 15 in uct
    uct = genfixes.unclosed_tags(r"<!--bar--> <!-- not ended")
    assert len(uct) == 1, r"<!-- 2"
    assert 11 in uct
    uct = genfixes.unclosed_tags("<!--not ended\r\n<!--  ended -->")
    assert len(uct) == 1, r"Comment within unclosed comment"
    uct = genfixes.unclosed_tags(r"<gallery> not ended <gallery>bar</gallery>")
    assert len(uct) == 1, r"gallery 2"
    assert 20 in uct
    uct = genfixes.unclosed_tags(r"<gallery other='a'> not ended <gallery other='a'>bar</gallery>")
    assert len(uct) == 1, r"gallery param"
    assert 30 in uct
    uct = genfixes.unclosed_tags(
        r"<gallery>A|<div><small>(1717)</small><br/><small><small>Munich</small></div></gallery>"
    )
    assert len(uct) == 1, r"small div"
    assert 42 in uct
    uct = genfixes.unclosed_tags(
        r"<small><small><small><small><small><small><small><small><small><small><small><small>"
    )
    assert len(uct) == 12, r"multiple unclosed small"
    uct = genfixes.unclosed_tags(
        r"<small><small><small><small><small><small><small><small><small><small><small><small> <!-- <math> -->"
    )
    assert len(uct) == 12, r"multiple unclosed small, ignore comments"
    uct = genfixes.unclosed_tags(
        r"<small><small><small><small><small><small><small><small><small><small><small><small> <small>></small>"
    )
    assert len(uct) == 14, r"multiple unclosed small, but counts tag containing >"
    uct = genfixes.unclosed_tags(
        r"<small><small><small><small><small><small><small><small><small><small><small><small> <ref name=fo>a</ref> <gallery param=a>b</gallery>"
    )
    assert len(uct) == 12, r"multiple unclosed small, don't count ref/gallery with params"
    uct = genfixes.unclosed_tags(
        "<code>a</code><code>a</code><code>a</code><code>a</code><code>a</code><code>a</code>\r\n<code>a</code><code>a</code><code>a</code><code>a</code><code>a</code><code>a</code>\r\n<code> a <some-tag> </code>"
    )
    assert len(uct) == 0, (
        r"No unclosed code tags here, don't report code tags just because of another tag"
    )
    uct = genfixes.unclosed_tags(
        "<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>\r\n<code> a <'foo'> </code>"
    )
    assert len(uct) == 0, r"No unclosed code tags here, ignore what aren't genuine tags"


def test_test_bullet_external_links() -> None:
    S = W.for_site(EN)
    s = genfixes.bullet_external_links(
        "==External links==\r\nhttp://example.com/foo\r\n[http://example.com foo]\r\n{{aTemplate|url=\r\nhttp://example.com }}"
    )
    assert r"* http://example.com/foo" in s
    assert r"* [http://example.com foo]" in s
    assert "\r\nhttp://example.com }}" in s
    NoChange = "==External links==\r\n* http://example.com/foo"
    assert genfixes.bullet_external_links(NoChange) == NoChange


def test_test_fix_link_whitespace() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_link_whitespace(r"b[[ a ]]c", r"foo") == r"b [[a]] c"
    assert genfixes.fix_link_whitespace(r"b   [[ a ]]  c", r"foo") == r"b   [[a]]  c"
    assert genfixes.fix_link_whitespace(r"[[a ]]b", r"foo") == r"[[a]] b"
    assert genfixes.fix_link_whitespace("Now\r\n[[a ]]b", r"foo") == "Now\r\n[[a]] b", (
        r"wikilink on start of line"
    )
    assert genfixes.fix_link_whitespace(r"[[a ]]" + "\r\n", r"foo") == r"[[a]]" + "\r\n"
    assert genfixes.fix_link_whitespace(r"[[foo  bar]]", r"foot") == r"[[foo bar]]"
    assert genfixes.fix_link_whitespace(r"[[foo  bar]]", r"") == r"[[foo bar]]"
    assert genfixes.fix_link_whitespace(r"[[foo     bar]]", r"foot") == r"[[foo bar]]"
    assert (
        genfixes.fix_link_whitespace(r"dat is [[ foo   bar ]] show!", r"foot")
        == r"dat is [[foo bar]] show!"
    )
    assert (
        genfixes.fix_link_whitespace(r"dat is[[ foo   bar ]]show!", r"foot")
        == r"dat is [[foo bar]] show!"
    )
    assert (
        genfixes.fix_link_whitespace(r"His [[Tiger Woods# Career]] was", r"Tiger Woods")
        == r"His [[Tiger Woods#Career]] was"
    )
    assert (
        genfixes.fix_link_whitespace(r"Fred's [[Smith# Career]] was", r"Fred")
        == r"Fred's [[Smith#Career]] was"
    )  # AWB: Is.Not.SameAs, a reference check that always passes; AWB's output is the fixed link
    assert (
        genfixes.fix_link_whitespace(r"[[Category:London| ]]", r"foo") == r"[[Category:London| ]]"
    )
    assert (
        genfixes.fix_link_whitespace(r"[[Category:Slam poetry| ]] ", r"foo")
        == r"[[Category:Slam poetry| ]] "
    )
    assert genfixes.fix_link_whitespace(r"[[foo #bar]]", r"foot") == r"[[foo#bar]]"
    assert genfixes.fix_link_whitespace(r"[[foo # bar]]", r"foot") == r"[[foo#bar]]"
    assert genfixes.fix_link_whitespace(r"[[foo# bar]]", r"foot") == r"[[foo#bar]]"
    assert genfixes.fix_link_whitespace(r"[[foo #bar]]te", r"foot") == r"[[foo#bar]]te"
    assert genfixes.fix_link_whitespace(r"[[foo  #bar|te]]", r"foot") == r"[[foo#bar|te]]"
    assert (
        genfixes.fix_link_whitespace(
            r"[[List of The Amazing Spider-Man issues#The Amazing Spider-Man #648–current x|List of issues]]",
            r"x",
        )
        == r"[[List of The Amazing Spider-Man issues#The Amazing Spider-Man #648–current x|List of issues]]"
    ), r"Does not break section links with hash and space"
    assert genfixes.fix_link_whitespace(r"[[A# code]]", r"Test") == r"[[A# code]]"
    assert genfixes.fix_link_whitespace(r"[[C# code]]", r"Test") == r"[[C# code]]"
    assert genfixes.fix_link_whitespace(r"[[F# code]]", r"Test") == r"[[F# code]]"
    assert genfixes.fix_link_whitespace(r"[[J# code]]", r"Test") == r"[[J# code]]"
    assert (
        genfixes.fix_link_whitespace(
            r"<ref>[[ abcdef-abcdef-abcdef-abcdef-abcdef-abcdef-abcdef]]</ref>", r"foo"
        )
        == r"<ref>[[abcdef-abcdef-abcdef-abcdef-abcdef-abcdef-abcdef]]</ref>"
    )


def test_test_canonicalize_title() -> None:
    S = W.for_site(EN)
    assert genfixes.canonicalize_title(r"foo_bar") == r"foo bar"
    assert genfixes.canonicalize_title(r"foo bar") == r"foo bar"
    assert genfixes.canonicalize_title(r"foo_%28bar%29") == r"foo (bar)"
    assert genfixes.canonicalize_title(r"foo%2Bbar") == r"foo+bar"
    assert genfixes.canonicalize_title(r"foo_(bar)") == r"foo (bar)"
    assert genfixes.canonicalize_title(r"Template:foo_bar") == r"Template:foo bar"
    assert genfixes.canonicalize_title(r"W202 %281993%E2%80%932000%29") == r"W202 (1993–2000)"
    assert genfixes.canonicalize_title(r"foo_bar}}") == r"foo_bar}}", r"no change to invalid title"
    assert r"{{bar_boz}}" in genfixes.canonicalize_title(r"foo_bar{{bar_boz}}")
    S = set_site(underscored_titles=current_site().underscored_titles | {r"Foo bar"})
    assert genfixes.canonicalize_title(r"foo_bar") == r"foo_bar"
    assert genfixes.canonicalize_title(r"Foo_bar") == r"Foo_bar"


def test_canonicalize_title_aggressively() -> None:
    S = W.for_site(EN)
    assert genfixes.canonicalize_title_aggressively(r"Foo") == r"Foo"
    assert genfixes.canonicalize_title_aggressively(r"foo_%28bar%29#anchor") == r"Foo (bar)"
    assert genfixes.canonicalize_title_aggressively(r"project : foo") == r"Wikipedia:Foo"
    assert genfixes.canonicalize_title_aggressively(r"Image: foo.jpg ") == r"File:Foo.jpg"
    assert genfixes.canonicalize_title_aggressively(r"Romeo+Juliet") == r"Romeo+Juliet"
    assert genfixes.canonicalize_title_aggressively(r":Foo") == r"Foo"
    assert genfixes.canonicalize_title_aggressively(r": Foo") == r"Foo"
    assert genfixes.canonicalize_title_aggressively(r"::Foo") == r":Foo"
    assert genfixes.canonicalize_title_aggressively(r":user:Foo") == r"User:Foo"
    assert genfixes.canonicalize_title_aggressively(r"User talk:Foo") == r"User talk:Foo"


def test_test_fix_empty_links_and_templates() -> None:
    S = W.for_site(EN)
    assert len(genfixes.fix_empty_links_and_templates(r"")) == 0
    assert genfixes.fix_empty_links_and_templates(r"Test") == r"Test"
    assert genfixes.fix_empty_links_and_templates(r"{{Test}}") == r"{{Test}}"
    assert genfixes.fix_empty_links_and_templates("Test\r\n{{Test}}") == "Test\r\n{{Test}}"
    assert len(genfixes.fix_empty_links_and_templates(r"{{}}")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"{{ }}")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"{{|}}")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"{{||||||||||||||||}}")) == 0
    assert (
        len(
            genfixes.fix_empty_links_and_templates(r"{{|||| |||||||                      ||  |||}}")
        )
        == 0
    )
    assert len(genfixes.fix_empty_links_and_templates(r"{{Template:}}")) == 0, r"Template:"
    assert len(genfixes.fix_empty_links_and_templates(r"{{Template: }}")) == 0, (
        r"Template: with space"
    )
    assert len(genfixes.fix_empty_links_and_templates(r"{{Template:     |||}}")) == 0
    assert genfixes.fix_empty_links_and_templates(r"{{  }}{{Test}}{{Template: ||}}") == r"{{Test}}"
    assert genfixes.fix_empty_links_and_templates(r"[[Test]]") == r"[[Test]]"
    assert genfixes.fix_empty_links_and_templates(r"[[Test|Bar]]") == r"[[Test|Bar]]"
    assert genfixes.fix_empty_links_and_templates(r"[[|Bar]]") == r"[[|Bar]]"
    assert len(genfixes.fix_empty_links_and_templates(r"[[]]")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"[[[[  ]]]]")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"[[  ]]")) == 0
    assert genfixes.fix_empty_links_and_templates(r"[[Category:Test]]") == r"[[Category:Test]]"
    assert (
        genfixes.fix_empty_links_and_templates(r"Text [[Category:Test]]")
        == r"Text [[Category:Test]]"
    )
    assert len(genfixes.fix_empty_links_and_templates(r"[[Category:]]")) == 0
    assert genfixes.fix_empty_links_and_templates(r"Text [[Category:]]") == r"Text "
    assert len(genfixes.fix_empty_links_and_templates(r"[[Category:  ]]")) == 0
    assert genfixes.fix_empty_links_and_templates(r"[[Image:Test]]") == r"[[Image:Test]]"
    assert genfixes.fix_empty_links_and_templates(r"Text [[Image:Test]]") == r"Text [[Image:Test]]"
    assert genfixes.fix_empty_links_and_templates(r"[[File:Test]]") == r"[[File:Test]]"
    assert genfixes.fix_empty_links_and_templates(r"Text [[File:Test]]") == r"Text [[File:Test]]"
    assert len(genfixes.fix_empty_links_and_templates(r"[[Image:]]")) == 0
    assert genfixes.fix_empty_links_and_templates(r"Text [[Image:]]") == r"Text "
    assert len(genfixes.fix_empty_links_and_templates(r"[[Image:  ]]")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"[[File:]]")) == 0
    assert genfixes.fix_empty_links_and_templates(r"Text [[File:]]") == r"Text "
    assert len(genfixes.fix_empty_links_and_templates(r"[[File:  ]]")) == 0
    assert len(genfixes.fix_empty_links_and_templates(r"[[File:]][[Image:]]")) == 0
    assert genfixes.fix_empty_links_and_templates(r"[[File:Test]][[Image:]]") == r"[[File:Test]]"


def test_test_fix_pipe_trick() -> None:
    S = W.for_site(EN)
    nochanges = False
    assert genfixes.fix_pipe_trick(r"[[Pipe (computing)|]]") == r"[[Pipe (computing)|Pipe]]"
    assert ((_t := genfixes.fix_links(r"[[Pipe (computing)|]]", r"Title")), (nochanges := _t[1]))[
        0
    ][0] == r"[[Pipe (computing)|Pipe]]"
    assert genfixes.fix_pipe_trick(r"[[Phoenix, Arizona|]]") == r"[[Phoenix, Arizona|Phoenix]]"
    assert (
        genfixes.fix_pipe_trick(r"[[Yours, Mine and Ours (1968 film)|]]")
        == r"[[Yours, Mine and Ours (1968 film)|Yours, Mine and Ours]]"
    )
    assert (
        genfixes.fix_pipe_trick(r"[[Elgin, Kershaw County, South Carolina|]]")
        == r"[[Elgin, Kershaw County, South Carolina|Elgin]]"
    )
    assert (
        genfixes.fix_pipe_trick(r"[[Wikipedia:Manual of Style (Persian)|]]")
        == r"[[Wikipedia:Manual of Style (Persian)|Manual of Style]]"
    )
