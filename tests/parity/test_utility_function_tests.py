"""Port of AWB UnitTests/UtilityFunctionTests.cs: utility functions.

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


def test_change_to_default_sort() -> None:
    S = W.for_site(EN)
    assert (
        (_t := genfixes.change_to_default_sort(r"[[Category:Test1|Foooo]]", r"Foo")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1|Foooo]]", r"don't change sorting for single categories"
    assert noChange, r"don't change sorting for single categories"
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooo]][[Category:Test2|Foooo]]", r"Bar"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "[[Category:Test1]][[Category:Test2]]\r\n{{DEFAULTSORT:Foooo}}"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooo]][[Category:Test2|Foooo]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1]][[Category:Test2]]"
    assert not (noChange), r"Should detect a change even if it hasn't added a DEFAULTSORT"
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foo]][[Category:Test2|Foo]]", r"Bar"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1|Foo]][[Category:Test2|Foo]]"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooo]][[Category:Test2]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1]][[Category:Test2]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1]][[Category:Test2|Foooo]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1]][[Category:Test2]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Fooooo]][[Category:Test2]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1|Fooooo]][[Category:Test2]]"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooo]][[Category:Test2|Baaar]]", r"Teeest"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1|Foooo]][[Category:Test2|Baaar]]"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooo]][[Category:Test2|Baaar]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1|Foooo]][[Category:Test2|Baaar]]"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooô]][[Category:Test2|Foooô]]", r"Bar"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "[[Category:Test1]][[Category:Test2]]\r\n{{DEFAULTSORT:Foooo}}"
    assert not (noChange)
    assert (
        (_t := genfixes.change_to_default_sort(r"{{defaultsort| Tést}}", r"Foo")),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}"
    assert not (noChange)
    assert (
        (_t := genfixes.change_to_default_sort(r"{{DEFAULTSORT| Tést}}", r"Foo")),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}"
    assert not (noChange)
    assert (
        (_t := genfixes.change_to_default_sort(r"{{DEFAULTSORT:|Test}}", r"Foo")),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}"
    assert not (noChange)
    assert (
        (_t := genfixes.change_to_default_sort(r"{{DEFAULTSORT: 	}}", r"Foo")),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT: 	}}"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1| Foooo]][[Category:Test2| Foooo]]", r"Bar"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1| Foooo]][[Category:Test2| Foooo]]"
    assert noChange
    (
        (
            _t := genfixes.change_to_default_sort(
                r"{{defaultsort| Tést}}{{DEFAULTSORT: Tést}}", r"Foo"
            )
        ),
        (noChange := _t[1]),
    )[0][0]
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"{{DEFAULTSORT:Test}}[[Category:Test|Test]]", r"Foo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}[[Category:Test]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"{{DEFAULTSORT:Test}}[[Category:Test|TEST]]", r"Foo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}[[Category:Test]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"{{DEFAULTSORT:Test}}[[Category:Test|Not a Test]]", r"Foo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}[[Category:Test|Not a Test]]"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"{{DEFAULTSORT:Test}}[[Category:Test|TEST]][[Category:Foo|Test]][[Category:Bar|test]]",
                r"Foo",
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}[[Category:Test]][[Category:Foo]][[Category:Bar]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"{{DEFAULTSORT:Test}}[[Category:Test|TEST]][[Category:Foo]][[Category:Bar|test]]",
                r"Foo",
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}[[Category:Test]][[Category:Foo]][[Category:Bar]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"{{DEFAULTSORT:Test}}[[Category:Test|TEST]][[Category:Foo|Bar]][[Category:Bar|test]]",
                r"Foo",
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"{{DEFAULTSORT:Test}}[[Category:Test]][[Category:Foo|Bar]][[Category:Bar]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Bronze Wolf awardees|Lainé, Juan]]", r"Hi"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bronze Wolf awardees|Laine, Juan]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Bronze Wolf awardees|Lainİ, Juan]]", r"Hi"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bronze Wolf awardees|LainI, Juan]]", (
        r"unusual one where lowercase of diacritic is a Latin character"
    )
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Bronze Wolf awardees|Laine, Juan]]", r"Hi"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Bronze Wolf awardees|Laine, Juan]]"
    assert noChange
    assert (
        (
            _t := genfixes.change_to_default_sort(
                "foo\r\n{{DEFAULTSORT:Phillips, James M.}}\r\n[[Category:Businesspeople]]\r\n\r\n{{DEFAULTSORT:Phillips, James M.}}\r\nfoo",
                r"Hi",
            )
        ),
        (noChange := _t[1]),
    )[0][
        0
    ] == "foo\r\n\r\n[[Category:Businesspeople]]\r\n\r\n{{DEFAULTSORT:Phillips, James M.}}\r\nfoo"
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "foo\r\n{{DEFAULTSORT:Phillips, James M.}}\r\n[[Category:Businesspeople]]\r\n\r\n{{DEFAULTSORT:Phillips, James M.}}\r\n{{DEFAULTSORT:Phillips, James M.}}\r\nfoo",
                    r"Hi",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "foo\r\n\r\n[[Category:Businesspeople]]\r\n\r\n\r\n{{DEFAULTSORT:Phillips, James M.}}\r\nfoo"
    )
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "foo\r\n{{DEFAULTSORT:Phillips, James M.}}\r\n[[Category:Businesspeople]]\r\n\r\n{{DEFAULTSORT:Fred}}\r\nfoo",
                    r"Hi",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "foo\r\n{{DEFAULTSORT:Phillips, James M.}}\r\n[[Category:Businesspeople]]\r\n\r\n{{DEFAULTSORT:Fred}}\r\nfoo"
    )
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "\r\nfoo {{Infobox biography}}\r\n[[Category:1910 births|Lahiff, Tommy]]\r\n[[Category:Australian players of Australian rules football|Lahiff, Tommy]]\r\n[[Category:Essendon Football Club players|Lahiff, Tommy]]\r\n",
                    r"foo",
                    False,
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "\r\nfoo {{Infobox biography}}\r\n[[Category:1910 births]]\r\n[[Category:Australian players of Australian rules football]]\r\n[[Category:Essendon Football Club players]]\r\n\r\n{{DEFAULTSORT:Lahiff, Tommy}}"
    )
    a = "\r\nfoo {{Infobox biography}}\r\n[[Category:1910 births|Lahiff, Tommy]]\r\n[[Category:Australian players of Australian rules football|Lahiff, Tommy]]\r\n[[Category:Essendon Football Club players|Lahiff, Tommy]]\r\n"
    assert ((_t := genfixes.change_to_default_sort(a, r"foo", True)), (noChange := _t[1]))[0][
        0
    ] == a
    assert (
        ((_t := genfixes.change_to_default_sort(a, r"foo", False)), (noChange := _t[1]))[0][0]
        == "\r\nfoo {{Infobox biography}}\r\n[[Category:1910 births]]\r\n[[Category:Australian players of Australian rules football]]\r\n[[Category:Essendon Football Club players]]\r\n\r\n{{DEFAULTSORT:Lahiff, Tommy}}"
    )
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "\r\nfoo {{Infobox biography}}\r\n[[Category:1910 births|Lahiff, Tommy]]\r\n[[Category:Australian players of Australian rules football|Lahiff, Tommy]]\r\n[[Category:Essendon Football Club players|TOmmy]]\r\n",
                    r"foo",
                    True,
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "\r\nfoo {{Infobox biography}}\r\n[[Category:1910 births|Lahiff, Tommy]]\r\n[[Category:Australian players of Australian rules football|Lahiff, Tommy]]\r\n[[Category:Essendon Football Club players|TOmmy]]\r\n"
    )
    r1 = "[[Category:Franks]]\r\n[[Category:Carolingian dynasty]]\r\n[[Category:Frankish people]]\r\n[[Category:811 deaths]]\r\n[[Category:9th-century rulers]]"
    assert ((_t := genfixes.change_to_default_sort(r1, r"foo", True)), (noChange := _t[1]))[0][
        0
    ] == r1
    assert (
        (
            _t := genfixes.change_to_default_sort(
                "foo\r\n[[Category:All foos]]", r"Category:Special foŏs", False
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "foo\r\n[[Category:All foos]]\r\n{{DEFAULTSORT:Special foos}}"
    assert (
        (
            _t := genfixes.change_to_default_sort(
                "foo\r\n[[Category:All foos]]\r\n[[Category:All foos2]]", r"Rail in İzmir", False
            )
        ),
        (noChange := _t[1]),
    )[0][
        0
    ] == "foo\r\n[[Category:All foos]]\r\n[[Category:All foos2]]\r\n{{DEFAULTSORT:Rail in Izmir}}"
    assert (
        (
            _t := genfixes.change_to_default_sort(
                "foo\r\n{{DEFAULTSORT:Women's Circuit (July–September)}}",
                r"Women's Circuit (July–September)",
                False,
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "foo\r\n{{DEFAULTSORT:Women's Circuit (July-September)}}"
    NoInclude = r"[[Category:Test1|Foooo]][[Category:Test2|Foooo]] <noinclude>foo</noinclude>"
    assert ((_t := genfixes.change_to_default_sort(NoInclude, r"Bar")), (noChange := _t[1]))[0][
        0
    ] == NoInclude
    assert noChange
    S = set_site(unicode_category_collation=True)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|Foooô]][[Category:Test2|Foooô]]", r"Bar"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "[[Category:Test1]][[Category:Test2]]\r\n{{DEFAULTSORT:Foooô}}"
    assert not (noChange), r"retain diacritics when generating a key if uca collation is on"
    assert (
        (_t := genfixes.change_to_default_sort(r"[[Category:Test1]][[Category:Test2]]", r"Foooô")),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1]][[Category:Test2]]"
    assert noChange, r"No change when defaultsort not needed when uca collation on"
    S = set_site(unicode_category_collation=False)


def test_missing_default_sort() -> None:
    S = W.for_site(EN)
    assert not (genfixes.missing_default_sort(r"A", r"A"))
    assert not (genfixes.missing_default_sort(r"A {{DEFAULTSORT:A}}", r"A {{DEFAULTSORT:A}}"))
    assert not (genfixes.missing_default_sort(r"A {{DEFAULTSORT:A}} [[category:A]]", r"A"))
    assert genfixes.missing_default_sort("A\r\n[[Category:1910 births]]", r"John Smith")


def test_change_to_defaultsort_case_insensitive() -> None:
    S = W.for_site(EN)
    CInsensitive = r"x [[Category:Foo]]"
    assert ((_t := genfixes.change_to_default_sort(CInsensitive, r"BAR")), (noChange := _t[1]))[0][
        0
    ] == CInsensitive, r"no change when defaultsort only differs to article title by case"
    assert noChange
    assert ((_t := genfixes.change_to_default_sort(CInsensitive, r"Bar")), (noChange := _t[1]))[0][
        0
    ] == CInsensitive, r"no change when defaultsort only differs to article title by case"
    assert noChange
    assert ((_t := genfixes.change_to_default_sort(CInsensitive, r"Bar foo")), (noChange := _t[1]))[
        0
    ][0] == CInsensitive, r"no change when defaultsort only differs to article title by case"
    assert noChange
    assert (
        (_t := genfixes.change_to_default_sort(CInsensitive, r"Bar (foo)")),
        (noChange := _t[1]),
    )[0][0] == CInsensitive, r"no change when defaultsort only differs to article title by case"
    assert noChange
    CInsensitive2 = r"{{DEFAULTSORT:Bar}} [[Category:Foo]]"
    assert ((_t := genfixes.change_to_default_sort(CInsensitive2, r"BAR")), (noChange := _t[1]))[0][
        0
    ] == CInsensitive2, r"no change when existing defaultsort only differs to article title by case"
    assert noChange
    CInsensitive2 = r"{{DEFAULTSORT:bar}} [[Category:Foo]]"
    assert ((_t := genfixes.change_to_default_sort(CInsensitive2, r"BAR")), (noChange := _t[1]))[0][
        0
    ] == CInsensitive2, r"no change when existing defaultsort only differs to article title by case"
    assert noChange
    CInsensitive2 = r"{{DEFAULTSORT:BAR}} [[Category:Foo]]"
    assert ((_t := genfixes.change_to_default_sort(CInsensitive2, r"BAR")), (noChange := _t[1]))[0][
        0
    ] == CInsensitive2, r"no change when existing defaultsort only differs to article title by case"
    assert noChange


def test_change_to_default_sort_pagename() -> None:
    S = W.for_site(EN)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|{{PAGENAME}}]][[Category:Test2]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1]][[Category:Test2]]"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                r"[[Category:Test1|{{subst:PAGENAME}}]][[Category:Test2]]", r"Foooo"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == r"[[Category:Test1]][[Category:Test2]]"
    assert not (noChange)


def test_change_to_default_sort_multiple() -> None:
    S = W.for_site(EN)
    Multi = "[[Category:Test1|Foooo]][[Category:Test2|Foooo]]\r\n{{DEFAULTSORT:Foooo}}\r\n{{DEFAULTSORTKEY:Foo2oo}}"
    assert ((_t := genfixes.change_to_default_sort(Multi, r"Bar")), (noChange := _t[1]))[0][
        0
    ] == Multi, r"no change when multiple different defaultsorts"
    assert noChange


def test_category_sort_key_partial_cleaning() -> None:
    S = W.for_site(EN)
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "{{DEFAULTSORT:Willis, Bobby}}\r\n[[Category:1999 deaths|Willis]]\r\n[[Category:1942 births]]\r\n[[Category:Cancer deaths in the United Kingdom]]",
                    r"Bobby Willis",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "{{DEFAULTSORT:Willis, Bobby}}\r\n[[Category:1999 deaths]]\r\n[[Category:1942 births]]\r\n[[Category:Cancer deaths in the United Kingdom]]"
    )
    assert not (noChange)
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "{{DEFAULTSORT:Willis, Bobby}}\r\n[[Category:1999 deaths|Willis]]\r\n[[Category:1942 births|Foo]]\r\n[[Category:Cancer deaths in the United Kingdom]]",
                    r"Bobby Willis",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "{{DEFAULTSORT:Willis, Bobby}}\r\n[[Category:1999 deaths]]\r\n[[Category:1942 births|Foo]]\r\n[[Category:Cancer deaths in the United Kingdom]]"
    )
    assert not (noChange)


def test_change_to_default_sort_human() -> None:
    S = W.for_site(EN)
    a = r"Fred Smith blah [[Category:Living people]]"
    b = "\r\n" + r"{{DEFAULTSORT:Smith, Fred}}"
    assert ((_t := genfixes.change_to_default_sort(a, r"Fred Smith")), (noChange := _t[1]))[0][
        0
    ] == a + b
    assert not (noChange)
    a2 = r"Fred Smith blah {{imdb name|id=abc}} [[Category:Living people]]"
    assert ((_t := genfixes.change_to_default_sort(a2, r"Fred Smith")), (noChange := _t[1]))[0][
        0
    ] == a2 + b
    assert not (noChange)
    assert ((_t := genfixes.change_to_default_sort(a, r"Fred Smith", True)), (noChange := _t[1]))[
        0
    ][0] == a
    assert noChange
    c = r"Stéphanie Mahieu blah [[Category:Living people]]"
    d = "\r\n" + r"{{DEFAULTSORT:Mahieu, Stephanie}}"
    assert ((_t := genfixes.change_to_default_sort(c, r"Stéphanie Mahieu")), (noChange := _t[1]))[
        0
    ][0] == c + d
    assert not (noChange)


def test_test_defaultsort_titles_with_diacritics() -> None:
    S = W.for_site(EN)
    assert (
        (_t := genfixes.change_to_default_sort(r"[[Category:Parishes in Asturias]]", r"Abándames")),
        (noChange := _t[1]),
    )[0][0] == "[[Category:Parishes in Asturias]]\r\n{{DEFAULTSORT:Abandames}}"
    assert not (noChange)
    assert (
        (
            _t := genfixes.change_to_default_sort(
                "[[Category:Parishes in Asturias]]\r\n{{DEFAULTSORT:Bert}}", r"Abándames"
            )
        ),
        (noChange := _t[1]),
    )[0][0] == "[[Category:Parishes in Asturias]]\r\n{{DEFAULTSORT:Bert}}"
    assert noChange
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "[[Category:Parishes of the Azores|Agua Retorta]]\r\n[[Category:São Miguel Island]]",
                    r"Água Retorta",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "[[Category:Parishes of the Azores]]\r\n[[Category:São Miguel Island]]\r\n{{DEFAULTSORT:Agua Retorta}}"
    )
    assert not (noChange)
    assert (
        (
            (
                _t := genfixes.change_to_default_sort(
                    "[[Category:Parishes of the Azores]]\r\n[[Category:São Miguel Island]]",
                    r"Água Retorta",
                )
            ),
            (noChange := _t[1]),
        )[0][0]
        == "[[Category:Parishes of the Azores]]\r\n[[Category:São Miguel Island]]\r\n{{DEFAULTSORT:Agua Retorta}}"
    )
    assert not (noChange)


def test_test_is_article_about_a_person() -> None:
    S = W.for_site(EN)
    assert genfixes.is_article_about_a_person(r"Foo {{infobox person|name=smith}}", r"foo")
    assert genfixes.is_article_about_a_person(r"Foo [[Category:1900 deaths]]", r"foo")
    assert genfixes.is_article_about_a_person(r"Foo [[Category:1900 births]]", r"foo")
    assert genfixes.is_article_about_a_person(r"Foo [[Category:Living people]]", r"foo")
    assert genfixes.is_article_about_a_person(
        r"Foo [[Category:Year of birth missing (living people)]]", r"foo"
    )
    assert genfixes.is_article_about_a_person(r"Foo [[Category:Living people|Smith]]", r"foo")
    assert genfixes.is_article_about_a_person(
        r"Foo [[Category:Living people]] [[Category:Living people]]", r"foo"
    ), r"duplicate categories removed, so okay"
    assert genfixes.is_article_about_a_person(r"'''Foo''' {{England-bio-stub}}", r"foo")
    assert genfixes.is_article_about_a_person(r"'''Foo''' {{Switzerland-politician-stub}}", r"foo")
    assert genfixes.is_article_about_a_person(
        r"Some words {{death date and age|1960|01|9}}", r"foo"
    )
    assert genfixes.is_article_about_a_person(r"'''Foo''' {{RefimproveBLP}}", r"foo"), (
        r"BLP template"
    )
    assert genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"foo"), (
        r"BLP sources template"
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"16 and pregnant")
    ), r"BLP sources template"
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP unsourced section|foo=bar}}", r"foo")
    ), r"BLP unsourced template"
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{Infobox actor|name=smith}}", r"Category:foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"List of foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Lists of foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' [[Category:Missing people organizations]]", r"Foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Deaths in 2004")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"First Assembly of X"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Pierre Schaeffer bibliography"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Adoption of x")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo (family)")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo (x family)")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo (x team)")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo (publisher)")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo haunting")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo martyrs")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo quartet")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo team")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo twins")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Attack on x")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Suicide of x")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Presidency of x")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Governor of x")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Mayoralty of x")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"First presidency of x"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"2004 something")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"2004–09 something"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo discography")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo children")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo murders")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo, bar and other"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo & other")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo, bar, and Other"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo One and Other People"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo groups")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"The Foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo people")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo campaign")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo rebellion")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo native")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo center")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Second Foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo x families")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Brothers Foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"X from Y")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo brothers")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo Sisters")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"X Service")
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo (artists)")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo x families (bar)"
        )
    )
    assert not (genfixes.is_article_about_a_person(r"'''Foo''' {{BLP sources|foo=bar}}", r"X in Y"))
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Foo campaign, 2000"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Atlanta murders of 1979–1981"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Death rates in the 20th century"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Birth rates in the 20th century"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Death rates in the 1st century"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Death rates in the 2nd century"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''Foo''' {{BLP sources|foo=bar}}", r"Death rates in the 3nd century"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:1900 deaths]] and [[Category:1905 deaths]]", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo {{infobox some organization|foo=bar}} {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Some noble families]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Noble families]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X teams and stables]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:German families]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:German x families]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X diaspora in y]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:Baronies x]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:Groups x]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X royal families]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X nicknames]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X pageants]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X groups]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X magazines]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:Positions x]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X troupes]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X y groups]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:1900 establishments in X]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X gods]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Companies foo]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:Surnames]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X musical groups]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X bands]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X music groups]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo [[Category:X titles]] {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Performing groups]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X ethnic groups]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:X artist groups in]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Musical groups established in 2000]] {{foo-bio-stub}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo {{infobox television|bye=a}} {{refimproveBLP}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"'''Foo''' {{England-bio-stub}} {{sia}}", r"Foo")
    )
    assert genfixes.is_article_about_a_person(
        r"Foo [[Category:Afrikaner people]] {{foo-bio-stub}}", r"foo"
    ), r"category about people"
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{Infobox settlement}} {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{italic title}} {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{Infobox racehorse}} {{foo-bio-stub}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{Infobox named horse}} {{foo-bio-stub}}", r"foo")
    )
    assert not (genfixes.is_article_about_a_person(r"Foo", r"foo"))
    assert not (genfixes.is_article_about_a_person(r"", r"foo"))
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Married couples]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 animal births]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Comedy duos]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Comedy trios]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Foo Comedy duos]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo {{In-universe}} {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo {{in-universe}} {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo {{Infobox political party}} {{birth date and age|1974|11|26}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Articles about multiple people]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Fictional blah]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[fictional character]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[fictional character|character]] {{infoxbox actor|name=smith}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{dab}} {{infoxbox actor|name=smith}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Internet memes]] {{bda|1980|11|11}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:Military animals]] {{bda|1980|11|11}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 births]] {{infobox Musical artist|Background=group_or_band}}",
            r"foo",
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 births]] {{infobox Musical artist|background=group_or_band}}",
            r"foo",
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 births]] {{infobox musical artist|Background=group_or_band}}",
            r"foo",
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 births]] {{infobox Musical artist|Background=classical_ensemble}}",
            r"foo",
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 births]] {{infobox Band|Background=group_or_band}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo [[Category:2002 births]] {{infobox Musical artist|Background=band}}", r"foo"
        )
    )
    assert genfixes.is_article_about_a_person(
        r"Foo [[Category:2002 births]] {{infobox musical artist|Background=other}}", r"foo"
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"Foo {{infobox person|name=smith}} Foo {{infobox person|name=smith2}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(r"Foo {{death date|2002}} {{death date|2005}}", r"foo")
    )
    assert not (
        genfixes.is_article_about_a_person(
            "{{nat fs player|no=1|pos=GK|name=[[Meg]]|age={{Birth date|1956|01|01}} ({{Age at date|1956|01|01|1995|6|5}})|caps=|club=|clubnat=}}\r\n{{nat fs player|no=2|pos=MF|name=[[Valeria]]|age={{Birth date|1968|09|03}} ({{Age at date|1968|09|03|1995|6|5}})|caps=|club=|clubnat=}}",
            r"foo",
        )
    )
    assert genfixes.is_article_about_a_person(
        r"{{infobox actor|no=1|pos=GK|name=[[Meg]]|age={{Birth date|1956|01|01}} }} {{Birth date|1956|01|01}}",
        r"foo",
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"{{see also|Fred}} Fred Smith is great == foo == {{infoxbox actor}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"{{Main|Fred}} Fred Smith is great == foo == {{infoxbox actor}}", r"foo"
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"'''military career of [[Napoleon Bonaparte]]''' == foo == {{birth date|2008|11|11}}",
            r"foo",
        )
    )
    assert not (
        genfixes.is_article_about_a_person(
            r"foo [[Category:227 characters]] {{infoxbox actor}}", r"foo"
        )
    )
    assert genfixes.is_article_about_a_person(
        "'''Margaret Sidney''' was the [[pseudonym]] of American author '''Harriett Mulford Stone''' (June 22, 1844–August 2, 1924).\r\n[[Category:1844 births]]",
        r"foo",
    ), r"births category"
    AR = "{{Infobox rugby biography\r\n| birth_name = Opeti Fonua\r\n| birth_date ={{birth date and age|df=yes|1986|05|26}}\r\n| birth_place = [[Tonga]]\r\n| height = 1.97 m (6 ft 5.5 in)\r\n| weight = 140 kg (22 st 2 lb, 310 lb)\r\n| ru_position = Backrow, Secondrow\r\n| ru_amateurclubs =\r\n| ru_clubyears = 2005-2007<br />2007-2008<br />2008-\r\n| ru_proclubs = [[SU Agen Lot-et-Garonne|SU Agen]]<br />[[Football club Auch Gers|FC Auch]]<br />[[Sporting union Agen Lot-et-Garonne|SU Agen]]\r\n| ru_clubcaps = 34<ref name=\"itsrugby\"/><br /> 12<ref name=\"itsrugby\">{{Lien web |url=http://www.itsrugby.fr/joueur-3640.html |titre=Opeti Fonua |site=www.itsrugby.fr |consulté le=30</ref><br />81<ref name=\"itsrugby\"/>\r\n| ru_clubpoints = 10 (2 tries)<br />0<br />135 (23 tries)\r\n| ru_nationalyears = 2009-\r\n| ru_nationalteam = {{ru|Tonga}}\r\n| ru_nationalcaps = 2\r\n| ru_nationalpoints = (0)\r\n}}\r\n\r\n'''Opeti Fonua''', born [[26 May]] [[1986]], is a [[Tongan]] [[rugby union]] player who plays as a no.8 for French club [[SU Agen]]. Fonua is known for his immense size and strength (Fonua stands a shade under 6 feet 6 inches, or 197 cm, and weights in at 140 kg, well over 300 lb) but also for his speed and agility, surprising attributes given his huge physical size. Big tackles and strong carries, replete with hand-offs to opponents, are his trademarks. He is also known for bouncing off and running over opponents, often leaving them on the ground on their backsides as he continues galloping forward after smashing into them.\r\n\r\n==References==\r\n{{Reflist}}\r\n"
    assert genfixes.is_article_about_a_person(AR, r"Opeti Fonua"), r"Infobox about a person"


def test_external_url_to_internal_link() -> None:
    S = W.for_site(EN)
    assert len(genfixes.external_url_to_internal_link(r"")) == 0
    assert (
        genfixes.external_url_to_internal_link(
            r"https://secure.wikimedia.org/otrs/index.pl?Action=AgentTicketQueue"
        )
        == r"https://secure.wikimedia.org/otrs/index.pl?Action=AgentTicketQueue"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://ru.wikipedia.org/wiki/Foo Foo]")
        == r"[[w:ru:Foo|Foo]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://meta.wikimedia.org/wiki/Test Test]")
        == r"[[m:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://commons.wikimedia.org/wiki/Test Test]")
        == r"[[commons:Test|Test]]"
    )


def test_external_url_to_internal_link_en() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wiktionary.org/wiki/Test Test]")
        == r"[[wikt:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wiktionary.org/w/Test Test]")
        == r"[[wikt:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikinews.org/wiki/Test Test]")
        == r"[[n:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikibooks.org/wiki/Test Test]")
        == r"[[b:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikiquote.org/wiki/Test Test]")
        == r"[[q:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikisource.org/wiki/Test Test]")
        == r"[[s:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikiversity.org/wiki/Test Test]")
        == r"[[v:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikipedia.org/wiki/Test Test]")
        == r"[[w:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[https://en.wikipedia.org/wiki/Test Test]")
        == r"[[w:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://fr.wiktionary.org/wiki/Test Test]")
        == r"[[wikt:fr:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[http://fr.wikipedia.org/wiki/Test Test]")
        == r"[[w:fr:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[https://fr.wikipedia.org/wiki/Test Test]")
        == r"[[w:fr:Test|Test]]"
    )
    S = set_lang(r"fr")
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikipedia.org/wiki/Test Test]")
        == r"[[w:en:Test|Test]]"
    )
    assert (
        genfixes.external_url_to_internal_link(r"[https://en.wikipedia.org/wiki/Test Test]")
        == r"[[w:en:Test|Test]]"
    )
    S = set_lang(r"en")
    assert (
        genfixes.external_url_to_internal_link(r"[http://en.wikipedia.org/wiki/Test Test]")
        == r"[[w:Test|Test]]"
    )


def test_remove_empty_comments() -> None:
    S = W.for_site(EN)
    assert len(genfixes.remove_empty_comments(r"<!---->")) == 0
    assert len(genfixes.remove_empty_comments(r"<!-- -->")) == 0
    assert genfixes.remove_empty_comments("<!--\r\n\r\n-->") == "<!--\r\n\r\n-->"
    assert len(genfixes.remove_empty_comments(r"<!----><!---->")) == 0
    assert genfixes.remove_empty_comments("<!--\r\n\r\n--><!---->") == "<!--\r\n\r\n-->"
    assert genfixes.remove_empty_comments(r"<!----><!--Test-->") == r"<!--Test-->"
    assert genfixes.remove_empty_comments(r"<!----> <!--Test-->") == r" <!--Test-->"
    assert (
        genfixes.remove_empty_comments("<!--Test\r\nfoo--> <!--Test-->")
        == "<!--Test\r\nfoo--> <!--Test-->"
    )
    assert genfixes.remove_empty_comments(r"<!--Test-->") == r"<!--Test-->"
    assert len(genfixes.remove_empty_comments(r"")) == 0
    assert genfixes.remove_empty_comments(r"test") == r"test"


def test_has_sic_tag_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.has_sic_tag(r"now helo [sic] there")
    assert genfixes.has_sic_tag(r"now helo [sic!] there")
    assert genfixes.has_sic_tag(r"now helo[sic] there")
    assert genfixes.has_sic_tag(r"now helo (sic) there")
    assert genfixes.has_sic_tag(r"now helo (sic!) there")
    assert genfixes.has_sic_tag(r"now helo {sic} there")
    assert genfixes.has_sic_tag(r"now helo [Sic] there")
    assert genfixes.has_sic_tag(r"now helo [ Sic ] there")
    assert genfixes.has_sic_tag(r"now {{sic|helo}} there")
    assert genfixes.has_sic_tag(r"now {{sic|hel|o}} there")
    assert genfixes.has_sic_tag(r"now {{typo|helo}} there")
    assert genfixes.has_sic_tag(r"now helo <!--[sic]-->there")
    assert not (genfixes.has_sic_tag(r"now sickened by"))
    assert not (genfixes.has_sic_tag(r"sic transit gloria mundi"))
    assert not (genfixes.has_sic_tag(r"The Sound Information Company (SIC) is"))


def test_has_morefootnotes_and_many_references_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.has_morefootnotes_and_many_references(
        "Article<ref>A</ref> <ref>B</ref> <ref>C</ref> <ref>B</ref> <ref>E</ref>\r\n==References==\r\n{{reflist}}\r\n{{nofootnotes}}"
    )
    assert genfixes.has_morefootnotes_and_many_references(
        "Article<ref>A</ref> <ref>B</ref> <ref>C</ref> <ref>B</ref> <ref>E</ref>\r\n==References==\r\n{{reflist}}\r\n{{morefootnotes}}"
    )
    assert genfixes.has_morefootnotes_and_many_references(
        "Article<ref name=A>A</ref> <ref name=B>B</ref> <ref>C</ref> <ref>B</ref> <ref>E</ref>\r\n==References==\r\n{{reflist}}\r\n{{Morefootnotes}}"
    )
    assert not (
        genfixes.has_morefootnotes_and_many_references(
            "Article<ref>A</ref> <ref>B</ref> <ref>C</ref> <ref>B</ref>\r\n==References==\r\n{{reflist}}\r\n{{nofootnotes}}"
        )
    )
    assert not (
        genfixes.has_morefootnotes_and_many_references(
            "Article<ref name=A>A</ref> <ref name=B>B</ref> <ref>C</ref> <ref>B</ref> <ref>E</ref>\r\n==References==\r\n{{reflist}}"
        )
    )


def test_has_ref_after_reflist_test() -> None:
    S = W.for_site(EN)
    assert genfixes.has_ref_after_reflist(
        r"blah <ref>a</ref> ==references== {{reflist}} <ref>b</ref>"
    )
    assert genfixes.has_ref_after_reflist(
        "blah <ref>a</ref>\r\n==references== {{reflist}} <ref>b</ref>"
    )
    assert genfixes.has_ref_after_reflist(
        r'blah <ref>a</ref> ==references== {{reflist}} <ref name="b">b</ref>'
    )
    assert not (genfixes.has_ref_after_reflist(r"blah <ref>a</ref> ==references== {{reflist}}"))
    assert not (genfixes.has_ref_after_reflist(r"blah.(Jones 2000)"))
    assert not (
        genfixes.has_ref_after_reflist(
            r"blah <ref>a</ref> ==references== {{reflist}} <!--<ref>b</ref>-->"
        )
    )
    assert not (
        genfixes.has_ref_after_reflist(
            r'blah <ref>a</ref> ==references== {{reflist}} <ref name="b">b</ref> {{reflist}}'
        )
    )
    assert not (
        genfixes.has_ref_after_reflist(
            r"blah <ref>a</ref> ==references== {{reflist|refs=<ref>abc</ref>}}"
        )
    )
    bug1 = "\r\n==References==\r\n<references />\r\n\r\n{{Northampton County, Pennsylvania}}\r\n\r\n[[Category:Boroughs in Pennsylvania]]\r\n[[Category:Northampton County, Pennsylvania]]\r\n[[Category:Settlements established in 1790]]\r\n\r\n[[ht:Tatamy, Pennsilvani]]\r\n[[nl:Tatamy]]\r\n[[pt:Tatamy]]\r\n[[vo:Tatamy]]"
    assert not (genfixes.has_ref_after_reflist(bug1))
    S = set_lang(r"fr")
    assert not (
        genfixes.has_ref_after_reflist(
            "blah <ref>a</ref>\r\n==references== {{reflist}} <ref>b</ref>"
        )
    )
    S = set_lang(r"en")
    assert not (genfixes.has_ref_after_reflist(r""))


def test_has_in_use_tag_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.is_in_use(r"{{inuse}} Hello world")
    assert genfixes.is_in_use(r"{{in creation}} Hello world")
    assert genfixes.is_in_use(r"{{increation}} Hello world")
    assert genfixes.is_in_use(r"{{ inuse  }} Hello world")
    assert genfixes.is_in_use(r"{{Inuse}} Hello world")
    assert genfixes.is_in_use(r"Hello {{inuse}} Hello world")
    assert genfixes.is_in_use(r"{{inuse|5 minutes}} Hello world")
    assert genfixes.is_in_use(r"{{In use}} Hello world")
    assert genfixes.is_in_use(r"{{in use|5 minutes}} Hello world")
    assert not (genfixes.is_in_use(r"<!--{{inuse}}--> Hello world"))
    assert not (genfixes.is_in_use(r"<nowiki>{{inuse}}</nowiki> Hello world"))
    assert not (genfixes.is_in_use(r"<nowiki>{{in use}}</nowiki> Hello world"))
    assert genfixes.is_in_use(r"<!--{{inuse}}--> {{inuse|5 minutes}} Hello world")
    assert genfixes.is_in_use(r"<!--{{inuse}}--> {{in use|5 minutes}} Hello world")
    assert not (genfixes.is_in_use(r"{{INUSE}} Hello world"))
    S = set_lang(r"el")
    assert genfixes.is_in_use(r"{{Σε χρήση}} Hello world"), r"σε χρήση"
    assert genfixes.is_in_use(r"{{inuse}} Hello world"), r"inuse"
    assert not (genfixes.is_in_use(r"{{goceinuse}} Hello world")), r"goceinuse is en-only"


def test_is_missing_references_display_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.is_missing_references_display(r"Hello<ref>Fred</ref>")
    assert genfixes.is_missing_references_display(r'Hello<ref name="F">Fred</ref>')
    assert genfixes.is_missing_references_display(r"Hello{{GR|4}}")
    assert not (genfixes.is_missing_references_display(r"Hello"))
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref> {{reflist}}"))
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref> {{Reflist}}"))
    assert not (
        genfixes.is_missing_references_display(
            "Hello<ref>Fred</ref> {{Reflist\r\n|refs = \r\n{{cite news | title = A { hello }}\r\n}}"
        )
    ), r"Unbalanced brackets within cite template in reflist does not affect logic"
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref> {{ref-list}}"))
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref> {{reflink}}"))
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref> {{references}}"))
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref> <references/>"))
    assert not (
        genfixes.is_missing_references_display(
            r'Hello<ref>Fred</ref> <references group="" responsive="1"></references>'
        )
    )
    assert not (genfixes.is_missing_references_display(r"Hello{{GR|4}} <references/>"))
    assert not (genfixes.is_missing_references_display(r"Hello{{GR|r4}}"))
    assert not (genfixes.is_missing_references_display(r"Hello{{GR|India}}"))
    assert not (
        genfixes.is_missing_references_display(
            "{{Reflist|refs=\r\n<ref name=modern>{{cite news |first=William }}\r\n        }}"
        )
    )
    assert not (genfixes.is_missing_references_display(r"Hello<ref group=X>Fred</ref>"))


def test_is_missing_references_display_tests_en_only() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fr")
    assert not (genfixes.is_missing_references_display(r"Hello<ref>Fred</ref>"))
    assert not (genfixes.is_missing_references_display(r'Hello<ref name="F">Fred</ref>'))
    S = set_lang(r"en")


def test_infobox_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.has_infobox(r"{{Infobox fish | name = Bert }} ''Bert'' is a good fish.")
    assert genfixes.has_infobox("{{Infobox\r\nfish | name = Bert }} ''Bert'' is a good fish.")
    assert genfixes.has_infobox(r"{{infobox fish | name = Bert }} ''Bert'' is a good fish.")
    assert genfixes.has_infobox(r"{{ infobox fish | name = Bert }} ''Bert'' is a good fish.")
    assert genfixes.has_infobox(r"{{ infobox fish | name = Bert }} ''Bert'' is a good <!--fish-->.")
    assert not (genfixes.has_infobox(r"{{INFOBOX fish | name = Bert }} ''Bert'' is a good fish."))
    assert not (genfixes.has_infobox(r"{{infoboxfish | name = Bert }} ''Bert'' is a good fish."))
    assert not (
        genfixes.has_infobox(r"<!--{{infobox fish | name = Bert }}--> ''Bert'' is a good fish.")
    )
    assert not (
        genfixes.has_infobox(
            r"<nowiki>{{infobox fish | name = Bert }}</nowiki> ''Bert'' is a good fish."
        )
    )


def test_infobox_tests_en_only() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fr")
    assert not (genfixes.has_infobox(r"{{Infobox fish | name = Bert }} ''Bert'' is a good fish."))
    assert not (genfixes.has_infobox(r"{{INFOBOX fish | name = Bert }} ''Bert'' is a good fish."))
    S = set_lang(r"en")
    assert genfixes.has_infobox(r"{{Infobox fish | name = Bert }} ''Bert'' is a good fish.")


def test_has_stub_template() -> None:
    S = W.for_site(EN)
    assert genfixes.has_stub_template(r"foo {{foo stub}}")
    assert genfixes.has_stub_template(r"foo {{foo-stub}}")
    assert not (genfixes.has_stub_template(r"foo {{foo tubs}}"))


def test_has_stub_template_ar() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ar")
    assert genfixes.has_stub_template(r"foo {{بذرة ممثل}}"), r"actor stub"
    assert genfixes.has_stub_template(r"foo {{بذرة ألمانيا}}"), r"germany stub"
    S = set_lang(r"en")


def test_is_stub() -> None:
    S = W.for_site(EN)
    assert genfixes.is_stub(r"foo {{foo stub}}")
    assert genfixes.is_stub(r"foo {{foo-stub}}")
    assert genfixes.is_stub(r"foo {{foo tubs}}")
    a = r"fooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
    b = a + a + a + a + a + a
    assert not (genfixes.is_stub(b + b + b + b))


def test_is_stub_ar() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ar")
    assert genfixes.is_stub(r"foo {{بذرة ممثل}}")
    assert genfixes.is_stub(r"foo {{foo tubs}}")
    a = r"fooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
    b = a + a + a + a + a + a
    assert not (genfixes.is_stub(b + b + b + b))
    S = set_lang(r"en")


def test_is_stub_arz() -> None:
    S = W.for_site(EN)
    S = set_lang(r"arz")
    assert genfixes.is_stub(r"foo {{بذرة}}")
    assert genfixes.is_stub(r"foo {{foo tubs}}")
    a = r"fooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo"
    b = a + a + a + a + a + a
    assert not (genfixes.is_stub(b + b + b + b))
    S = set_lang(r"en")


def test_no_bots_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.check_no_bots(r"", r"")
    assert genfixes.check_no_bots(r"{{test}}", r"")
    assert genfixes.check_no_bots(r"lol, test", r"")
    assert genfixes.check_no_bots(r"{{bots}}", r"")
    assert genfixes.check_no_bots(r"{{bots|allow=awb}}", r"")
    assert genfixes.check_no_bots(r"{{bots|allow=test}}", r"test")
    assert genfixes.check_no_bots(r"{{bots|allow=user,test}}", r"test")
    assert genfixes.check_no_bots(r"{{bots|deny=none}}", r"")
    assert genfixes.check_no_bots(r"{{bots|deny=Xenobot Mk V}}", r"Xenobot")
    assert genfixes.check_no_bots(r"{{bots|deny=Xenobot}}", r"Xenobot Mk V")
    assert not (genfixes.check_no_bots(r"{{nobots}}", r""))
    assert not (genfixes.check_no_bots(r"{{bots|deny=all}}", r""))
    assert not (genfixes.check_no_bots(r"<!--comm-->{{bots|deny=all}}", r""))
    assert not (genfixes.check_no_bots("<!--comm\r\n-->{{bots|deny=all}}", r""))
    assert not (genfixes.check_no_bots(r"{{bots|deny=awb}}", r""))
    assert not (genfixes.check_no_bots(r"{{bots|deny=awb,test}}", r""))
    assert not (genfixes.check_no_bots(r"{{bots|deny=awb,test}}", r"test"))
    assert not (genfixes.check_no_bots(r"{{nobots|deny=awb,test}}", r"test"))
    assert not (genfixes.check_no_bots(r"{{bots|deny=test}}", r"test"))
    assert not (genfixes.check_no_bots(r"{{bots|allow=none}}", r""))
    assert not (
        genfixes.check_no_bots(r"{{bots|deny=AWB, MenoBot, MenoBot II}}", r"AWB and other bots")
    )
    assert genfixes.check_no_bots(r"<!-- comm {{bots|deny=all}} -->", r"")
    assert not (genfixes.check_no_bots(r"{{bots|allow=MiszaBot III,SineBot}}", r"otherBot"))
    assert genfixes.check_no_bots(r"{{bots|allow=MiszaBot III,SineBot}}", r"SineBot")
    assert genfixes.check_no_bots(
        r"{{bots|allow=MiszaBot III,SineBot, AWB}}", r"SomeotherBot, AWB last"
    )
    assert genfixes.check_no_bots(
        r"{{bots|allow=AWB, MiszaBot III,SineBot}}", r"SomeotherBot, AWB first"
    )


def test_no_include_include_only_programming_element() -> None:
    S = W.for_site(EN)
    assert genfixes.no_include_include_only_programming_element(r"<noinclude>blah</noinclude>")
    assert genfixes.no_include_include_only_programming_element(r"<includeonly>blah</includeonly>")
    assert genfixes.no_include_include_only_programming_element(r"<onlyinclude>blah</onlyinclude>")
    assert genfixes.no_include_include_only_programming_element(r"{{{1}}}")
    assert genfixes.no_include_include_only_programming_element(r"{{{3}}}")
    assert genfixes.no_include_include_only_programming_element(r"{{#ifexist}}")
    assert genfixes.no_include_include_only_programming_element(r"{{#ifexist:Text|{{For|Text2}} }}")
    assert not (genfixes.no_include_include_only_programming_element(r"hello"))
    assert not (genfixes.no_include_include_only_programming_element(r""))


def test_get_template_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.get_template(r"now {{foo}} was here", r"foo") == r"{{foo}}"
    assert genfixes.get_template(r"now {{Foo}} was here", r"foo") == r"{{Foo}}"
    assert genfixes.get_template(r"now {{foo}} was here", r"Foo") == r"{{foo}}"
    assert genfixes.get_template(r"now {{foo}} was here", r"[Ff]oo") == r"{{foo}}"
    assert (
        genfixes.get_template(r"now {{ foo|bar asdfasdf}} was here", r"foo")
        == r"{{ foo|bar asdfasdf}}"
    )
    assert (
        genfixes.get_template(r"now {{ foo |bar asdfasdf}} was here", r"foo")
        == r"{{ foo |bar asdfasdf}}"
    )
    assert (
        genfixes.get_template("now {{ foo|bar\r\nasdfasdf}} was here", r"foo")
        == "{{ foo|bar\r\nasdfasdf}}"
    )
    assert genfixes.get_template(r"now {{foo}} was here {{foo|1}}", r"foo") == r"{{foo}}"
    assert len(genfixes.get_template(r"now {{ foo|bar asdfasdf}} was here", r"foot")) == 0
    assert len(genfixes.get_template(r"now {{ foo|bar asdfasdf}} was here", r"")) == 0
    assert len(genfixes.get_template(r"", r"foo")) == 0
    assert len(genfixes.get_template(r"now <!--{{foo}} --> was here", r"foo")) == 0
    assert (
        genfixes.get_template(r"now {{foo<!--comm-->}} was here", r"foo") == r"{{foo<!--comm-->}}"
    )
    assert (
        genfixes.get_template(r"now {{foo  |a={{bar}} here}} was here", r"foo")
        == r"{{foo  |a={{bar}} here}}"
    )
    assert (
        genfixes.get_template(r"now <!--{{foo|bar}}--> {{foo}} was here", r"Foo") == r"{{foo|bar}}"
    )


def test_get_templates_tests() -> None:
    S = W.for_site(EN)
    foo1 = r"{{foo|a}}"
    foo2 = r"{{foo|b}}"
    text = r"now " + foo1 + r" and " + foo2
    foo = DotNetRegex(r"{{foo.*?}}")
    fred = []
    for m in foo.matches(text):
        fred.append(m)
    assert str(genfixes.get_templates(text, r"foo")) == str(fred)
    assert str(genfixes.get_templates(text, r"Foo")) == str(fred)
    templates = genfixes.get_templates(text, r"foo")
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert len(templates) == 2
    templates = genfixes.get_templates(text + r" <!-- {{foo|c}} -->", r"foo")
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert len(templates) == 2
    templates = genfixes.get_templates(text + r" <nowiki> {{foo|c}} </nowiki>", r"foo")
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert len(templates) == 2
    foo3 = r"{{ Foo|bar={{abc}}|beer=y}}"
    templates = genfixes.get_templates(r"now " + foo3 + r" there", r"foo")
    assert templates[0].value == foo3
    foo4 = r"{{ Foo }}"
    templates = genfixes.get_templates(r"now " + foo4 + r" there", r"foo")
    assert templates[0].value == foo4
    templates = genfixes.get_templates(r"now " + foo3 + r" there", r"fo")
    assert len(templates) == 0
    templates = genfixes.get_templates(r"{{test}}", r"test")
    assert len(templates) == 1
    templates = genfixes.get_templates("{{test}}\r\n", r"test")
    assert len(templates) == 1


def test_get_templates_embedded_comments() -> None:
    S = W.for_site(EN)
    foo1 = r"{{foo|a}}"
    foo2 = r"{{foo|b}}"
    foo2a = r"{{foo<!--comm-->|b}}"
    foo2b = r"{{foo|b<!--comm-->}}"
    text = r"now " + foo1 + r" and " + foo2
    templates = []
    templates = genfixes.get_templates(text + r" space " + foo2a, r"foo")
    assert len(templates) == 3
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert templates[2].value == foo2a
    templates = genfixes.get_templates(text + r" space " + foo2b, r"foo")
    assert len(templates) == 3
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert templates[2].value == foo2b


def test_get_templates_tests_all_templates() -> None:
    S = W.for_site(EN)
    foo1 = r"{{foo|a}}"
    foo2 = r"{{foo|b}}"
    foo2a = r"{{foo<!--comm-->|b}}"
    foo2b = r"{{foo|b<!--comm-->}}"
    text = r"now " + foo1 + r" and " + foo2
    templates = []
    templates = genfixes.get_templates(text + r" space " + foo2a)
    assert len(templates) == 3
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert templates[2].value == foo2a
    templates = genfixes.get_templates(text + r" space " + foo2b)
    assert len(templates) == 3
    assert templates[0].value == foo1
    assert templates[1].value == foo2
    assert templates[2].value == foo2b
    templates = genfixes.get_templates(r" {{one}} {{two}} {{three|a={{bcd}} |ef=gh}}")
    assert len(templates) == 3


def test_fix_unicode() -> None:
    S = W.for_site(EN)
    assert parser.fix_unicode(r"foo bar") == r"foo bar"
    assert parser.fix_unicode(r"foo" + "\r\n" + r" bar") == "foo\r\nbar"
    assert parser.fix_unicode(r"foo bar") == r"foo bar"
    assert parser.fix_unicode(r"foo" + "\r\n" + r"​​bar") == "foo\r\nbar"


@pytest.mark.skip(
    reason="SubstUserTemplates expands templates through the wiki API (roadmap step 4)"
)
def test_subst_user_templates() -> None:
    S = W.for_site(EN)
    Hello = DotNetRegex(r"{{hello.*?}}")
    assert (
        genfixes.subst_user_templates(r"Text {{hello|2010}}", r"test", Hello)
        == r"Text Expanded template test return<!-- {{hello|2010}} -->"
    ), r"performs single substitution"
    assert (
        genfixes.subst_user_templates(r"Text {{hello}}", r"test", Hello)
        == r"Text Expanded template test return<!-- {{hello}} -->"
    ), r"performs single substitution"
    assert (
        genfixes.subst_user_templates("Text {{hello}}\r\n{{hello2}}", r"test", Hello)
        == "Text Expanded template test return<!-- {{hello}} -->\r\nExpanded template test return<!-- {{hello2}} -->"
    ), r"performs multiple subsitutions"
    Bye = r"Text {{bye}}"
    assert genfixes.subst_user_templates(Bye, r"test", Hello) == Bye, (
        r"no changes if no matching template"
    )
    Subst = r"Now {{{subst:bar}}} text"
    assert genfixes.subst_user_templates(Subst, r"test", Hello) == Subst, r"doesn't change {{{subst"
    Null = None
    assert genfixes.subst_user_templates(Bye, r"test", Null) == Bye, (
        r"no changes when user talk page regex is null"
    )
    T2 = r"Test {{{2|}}}"
    assert genfixes.subst_user_templates(T2, r"test", Hello) == r"Test", (
        r"cleans up the {{{2|}}} template"
    )


def test_format_to_bda() -> None:
    S = W.for_site(EN)
    Correct = r"{{birth date and age|df=y|1990|05|11}}"
    CorrectAmerican = r"{{birth date and age|mf=y|1990|05|11}}"
    assert genfixes.format_to_bda(r"11 May 1990 (age 21)") == Correct
    assert genfixes.format_to_bda(r"11 May 1990 (Age 21)") == Correct
    assert genfixes.format_to_bda(r"11 May 1990, (Age 21)") == Correct
    assert genfixes.format_to_bda(r"11 May 1990; (Age 21)") == Correct
    assert genfixes.format_to_bda(r"11 May 1990 (aged 21)") == Correct
    assert genfixes.format_to_bda(r"11 May [[1990]] (aged 21)") == Correct
    assert genfixes.format_to_bda(r"[[11 May]] [[1990]] (aged 21)") == Correct
    assert genfixes.format_to_bda(r"[[11 May]] 1990 (aged 21)") == Correct
    assert genfixes.format_to_bda(r"11th May 1990 (aged 21)") == Correct
    assert genfixes.format_to_bda(r"11 May 1990 ( aged 21 )") == Correct
    assert genfixes.format_to_bda(r"11 May 1990    ( aged 21 )") == Correct
    assert genfixes.format_to_bda(r"11 May, 1990    ( aged 21 )") == Correct
    assert genfixes.format_to_bda(r"1990-05-11 (age 21)") == Correct
    assert genfixes.format_to_bda(r"1990-5-11 (age 21)") == Correct
    assert genfixes.format_to_bda(r"1990-5-11 <br/>(age 21)") == Correct
    assert genfixes.format_to_bda(r"1990-5-11 <br>(age 21)") == Correct
    assert genfixes.format_to_bda(r"1990-5-11 <br>Age 21") == Correct
    assert genfixes.format_to_bda(r"May 11, 1990 (age 21)") == CorrectAmerican
    assert genfixes.format_to_bda(r"May 11 1990 (age 21)") == CorrectAmerican
    assert genfixes.format_to_bda(r"May 11th 1990 (age 21)") == CorrectAmerican
    assert len(genfixes.format_to_bda(r"")) == 0
    assert genfixes.format_to_bda(r"Test") == r"Test"
    assert genfixes.format_to_bda(r"May 11, 1990") == r"May 11, 1990"
    assert genfixes.format_to_bda(r"May 1990 (age 21)") == r"May 1990 (age 21)"
    assert (
        genfixes.format_to_bda(r"May 11, 1990 (Age 21) and some other text")
        == r"May 11, 1990 (Age 21) and some other text"
    )


def test_coins() -> None:
    S = W.for_site(EN)
    data1 = r'"coins": "ctx_ver=Z39.88-2004&amp;rft_id=info%3Adoi%2Fhttp%3A%2F%2Fdx.doi.org%2F10.1007%2Fs11046-005-4332-4&amp;rfr_id=info%3Asid%2Fcrossref.org%3Asearch&amp;rft.atitle=Morphological+alterations+in+toxigenic+Aspergillus+parasiticus+exposed+to+neem+%28Azadirachta+indica%29+leaf+and+seed+aqueous+extracts&amp;rft.jtitle=Nature+Structural+%26%2338%3B+Molecular+Biology&amp;rft.date=2005&amp;rft.volume=159&amp;rft.issue=4&amp;rft.spage=565&amp;rft.epage=570&amp;rft.aufirst=Mehdi&amp;rft.aulast=Razzaghi-Abyaneh&amp;rft_val_fmt=info%3Aofi%2Ffmt%3Akev%3Amtx%3Ajournal&amp;rft.genre=article&amp;rft.au=Mehdi+Razzaghi-Abyaneh&amp;rft.au=+Abdolamir+Allameh&amp;rft.au=+Taki+Tiraihi&amp;rft.au=+Masoomeh+Shams-Ghahfarokhi&amp;rft.au=+Mehdi+Ghorbanian"'
    res = genfixes.extract_coins(data1)
    assert r"volume" in res
    assert r"issue" in res
    assert r"spage" in res
    assert r"aulast" in res
    assert r"atitle" in res
    assert r"date" in res
    assert r"jtitle" in res
    v = res.get(r"volume")
    assert v == r"159"
    v = res.get(r"jtitle")
    assert v == r"Nature Structural &#38; Molecular Biology"
