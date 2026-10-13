"""Port of AWB UnitTests/CategoryTests.cs: categories and DEFAULTSORT.

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
from awb_x.core.parsers.hidetext import HideText
from awb_x.core.parsers.parsers import DateLocale
from awb_x.core.rx import DotNetRegex
from awb_x.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_project, set_site, utc_month_year
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_test_year_ranges_categories() -> None:
    S = W.for_site(EN)
    genFixes.assert_not_changed("now foo\r\n\r\n[[Category:Abc (2004-present)]]")
    genFixes.assert_change(
        "now abc (2004-present) was\r\nnow foo\r\n\r\n[[Category:Abc (2004-present)]]",
        "now abc (2004–present) was\r\nnow foo\r\n\r\n[[Category:Abc (2004-present)]]",
    )


def test_fix_people_categories_birth() -> None:
    S = W.for_site(EN)
    a1 = r"'''Fred Smith''' (born 1960) is a bloke. {{Infobox actor}}"
    b2 = r"[[Category:1960 births]]"
    assert genfixes.fix_people_categories(a1, r"foo") == a1 + "\r\n" + b2
    a2 = a1 + "\r\n" + r"[[Category:1990 deaths]]"
    assert genfixes.fix_people_categories(a2, r"foo") == a2 + "\r\n" + b2
    b5 = r"Some words {{birth date and age|1960|01|9}}"
    assert genfixes.fix_people_categories(b5, r"foo") == b5 + "\r\n" + b2
    b6 = r"'''Fred Lerdahl''' (born [[March 10]] [[1960]]) [[Category:Living people]]"
    assert genfixes.fix_people_categories(b6, r"foo") == b6 + "\r\n" + b2
    b6a = r"'''Fred Lerdahl''' (born [[March 10]] [[1860]]) [[Category:Living people]]"
    assert genfixes.fix_people_categories(b6a, r"foo") == b6a
    b7 = r"'''William Arthur O'Donnell''' (born May 4, 1960 in [[Springhill, Nova Scotia]], Canada) is [[Category:Living people]]"
    assert genfixes.fix_people_categories(b7, r"foo") == b7 + "\r\n" + b2
    b8 = r"'''Burrell Carver Smith''' (born [[December 16]], [[1960]] in upstate New York) [[Category:Living people]]"
    assert genfixes.fix_people_categories(b8, r"foo") == b8 + "\r\n" + b2
    b9 = r"'''Fredro Starr''' (born '''Fredro Scruggs''' on [[April 18]] [[1960]] in [[Jamaica, Queens]]) is an [[Category:Living people]]"
    assert genfixes.fix_people_categories(b9, r"foo") == b9 + "\r\n" + b2
    b10 = r"'''Phillip Rhodes''' (born [[May 26]], [[1960]]) was a [[Category:Living people]]"
    assert genfixes.fix_people_categories(b10, r"foo") == b10 + "\r\n" + b2
    b11 = "'''Kid 'n Play''' was a [[hip-hop music|hip-hop]] and [[comedy]] duo from [[New York City]] that was popular in the late 1980s and early 1990s. The duo comprised '''[[Christopher Kid Reid]]''' (born [[April 5]] [[1964]] in [[The Bronx|The Bronx, New York City]])\r\nand '''[[Christopher Martin (entertainer)|Christopher Play Martin]]''' (born [[July 10]] [[1962]] in [[Queens, New York City]]). Besides their successful musical careers, Kid 'n Play are also notable for branching out into acting. [[Category:Living people]]"
    assert genfixes.fix_people_categories(b11, r"foo") == b11
    b12 = "{{Infobox actor\r\n| name            = Gianni Capaldi\r\n| birthdate       = <!-- {{Birth date and age|YYYY|MM|DD}} --> age 34 (as of 12 January 2010)<ref>*  Matheson, Shelley.</ref>\r\n| birthplace      = [[Motherwell]], [[Scotland]]<br>{{Citation needed|date=September 2010}}\r\n}}"
    assert genfixes.fix_people_categories(b12, r"foo") == b12
    m1 = "'''Fred Smith''' (born 1960) is a bloke. {{Infobox actor}}\r\n[[Category:Date of birth missing]]"
    assert genfixes.fix_people_categories(m1, r"foo") == m1 + "\r\n" + b2, (
        r"Date of birth missing cat retained when only yob"
    )
    m1 = "'''Fred Smith''' {{birth date and age|1960||}} is a bloke. {{Infobox actor}}\r\n[[Category:Date of birth missing]]"
    assert genfixes.fix_people_categories(m1, r"foo") == m1 + "\r\n" + b2, (
        r"Date of birth missing cat retained when only yob in bda"
    )
    DobMCat = r"[[Category:Date of birth missing]]"
    m2 = r"'''Fred Smith''' {{birth date and age|1960|01|9}} is a bloke. {{Infobox actor}}"
    assert genfixes.fix_people_categories(m2 + "\r\n" + DobMCat, r"foo") == m2 + "\r\n" + b2, (
        r"Date of birth missing cat removed when full date"
    )
    DobMCatL = r"[[Category:Date of birth missing (living people)|Foo]]"
    assert genfixes.fix_people_categories(m2 + "\r\n" + DobMCatL, r"foo") == m2 + "\r\n" + b2, (
        r"Date of birth missing (living people) cat removed when full date"
    )


def test_fix_people_categories_uncat() -> None:
    S = W.for_site(EN)
    a1 = r"'''Fred Smith''' (born 1960) is a bloke. {{Infobox actor}} {{Uncat|date=May 2010}}"
    b2 = r"[[Category:1960 births]]"
    assert (
        genfixes.fix_people_categories(a1, r"foo")
        == a1.replace(r"Uncat", r"Improve categories") + "\r\n" + b2
    ), r"renames uncat to cat improve when cats added"
    assert genfixes.fix_people_categories(a1 + b2, r"foo") == a1 + b2, (
        r"no uncat renaming when cats not added"
    )
    assert (
        genfixes.fix_people_categories(
            a1.replace(r" {{Uncat|date=May 2010}}", r"") + r"{{Cat improve}}", r"foo"
        )
        == a1.replace(r" {{Uncat|date=May 2010}}", r"") + r"{{Cat improve}}" + "\r\n" + b2
    ), r"no Cat improve change when cat improve already there"


def test_fix_people_categories_death() -> None:
    S = W.for_site(EN)
    b2 = r"[[Category:1960 births]]"
    a3 = r"'''Fred Smith''' (died 1960) is a bloke. {{Infobox actor}}"
    b3 = r"[[Category:1960 deaths]]"
    assert genfixes.fix_people_categories(a3, r"foo") == a3 + "\r\n" + b3
    a4 = a3 + "\r\n" + r"[[Category:1990 births]]"
    assert genfixes.fix_people_categories(a4, r"foo") == a4 + "\r\n" + b3
    d = "'''Fred Smith''' (born 11 May 1950 - died 17 August 1990) is a bloke.\r\n[[Category:1960 births|Smith, Fred]]"
    assert (
        genfixes.fix_people_categories(d, r"foo")
        == d + "\r\n" + r"[[Category:1990 deaths|Smith, Fred]]"
    )
    d2 = r"'''Johnny Sandon''' (originally named '''Billy Beck''') (born in 1960, in Lıverpool, Lancashire died 23 December 1990) was {{Infobox actor}}"
    assert (
        genfixes.fix_people_categories(d2, r"foo")
        == d2 + "\r\n" + b2 + "\r\n" + r"[[Category:1990 deaths]]"
    )
    d3 = r"'''Aeacides''' ({{lang-el|Aἰακίδης}}; died 313 BC), king {{Infobox actor}}"
    assert genfixes.fix_people_categories(d3, r"foo") == d3 + "\r\n" + r"[[Category:313 BC deaths]]"
    d4 = r"Some words {{death date and age|1960|01|9}}"
    assert genfixes.fix_people_categories(d4, r"foo") == d4 + "\r\n" + r"[[Category:1960 deaths]]"
    b1 = r"'''Fred Smith''' is a bloke."
    assert genfixes.fix_people_categories(b1, r"foo") == b1
    d5 = r"Some words {{death date and age|1960|01|9}}"
    assert (
        genfixes.fix_people_categories(d4 + r"[[Category:Year of death missing]]", r"foo")
        == d5 + r"[[Category:1960 deaths]]"
    )
    d6 = r"'''Foo''' (died 960) was {{Infobox actor}}"
    assert (
        genfixes.fix_people_categories(d6 + r"[[Category:Year of death missing]]", r"Foo")
        == d6 + r"[[Category:960 deaths]]"
    )


def test_fix_people_categories_already_categorized() -> None:
    S = W.for_site(EN)
    a = "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births]]\r\n[[Category:1990 deaths]]"
    b = "'''Fred Smith''' is a bloke.\r\n[[Category:1960 births]]\r\n[[Category:1990 deaths]]"
    c = "'''Fred Smith''' is a bloke.\r\n[[Category:1960 births|Smith, Fred]]\r\n[[Category:1990 deaths|Smith, Fred]]"
    e = "'''Fred Smith''' (born [[1950]]) is a bloke.\r\n[[Category:1950 births|Smith, Fred]]\r\n{{Recentlydeceased}}"
    f = "'''Fred Smith''' (born 1950) is a bloke.\r\n[[Category:1950 births|Smith, Fred]]\r\n{{recentlydeceased}}"
    g = "'''Fred Smith''' (born 1950) is a bloke.\r\n[[Category:1950 births|Smith, Fred]]\r\n[[Category:Year of death missing]]"
    assert genfixes.fix_people_categories(a, r"foo") == a
    assert genfixes.fix_people_categories(b, r"foo") == b
    assert genfixes.fix_people_categories(c, r"foo") == c
    assert genfixes.fix_people_categories(e, r"foo") == e
    assert genfixes.fix_people_categories(f, r"foo") == f
    assert genfixes.fix_people_categories(g, r"foo") == g
    h = "'''Fred Smith''' (born 1950) is a bloke.\r\n{{}}\r\n[[:Category:1950 births|Smith, Fred]]"
    assert genfixes.fix_people_categories(h, r"User:Foo") == h


def test_fix_people_categories_yob_uncertain() -> None:
    S = W.for_site(EN)
    u = "\r\n" + r"[[Category:Year of birth uncertain]]"
    u2 = r"'''Charles Meik''' (born around 1330 in [[Ghent]] - [[22 July]] [[1387]]) {{Infobox actor}}"
    assert genfixes.fix_people_categories(u2, r"foo") == u2 + u + "\r\n[[Category:1387 deaths]]"
    u2a = r"'''Charles Meik''' (born either 1330 or 1331 in [[Ghent]] - [[22 July]] [[1387]]) {{Infobox actor}}"
    assert genfixes.fix_people_categories(u2a, r"foo") == u2a + u + "\r\n[[Category:1387 deaths]]"
    u2b = r"'''Charles Meik''' (born ~1330 in [[Ghent]] - [[22 July]] [[1387]]) {{Infobox actor}}"
    assert genfixes.fix_people_categories(u2b, r"foo") == u2b + u + "\r\n[[Category:1387 deaths]]"
    u3 = r"'''Yusuf Ibn Muhammad Ibn Yusuf al-Fasi''' ([[1530]]/[[1531|31]]{{Fact|date=February 2007}} in [[Ksar-el-Kebir]], [[Morocco]] – 14 August [[1604]] in [[Fes, Morocco]]) {{Infobox actor}}"
    assert genfixes.fix_people_categories(u3, r"foo") == u3 + u + "\r\n[[Category:1604 deaths]]"
    b12 = r"'''Judith Victor Grabiner''' (born about 1938) is {{Infobox actor}}"
    assert genfixes.fix_people_categories(b12, r"foo") == b12 + u
    b13 = r"'''Judith Victor Grabiner''' (born circa 1938) is {{Infobox actor}}"
    assert genfixes.fix_people_categories(b13, r"foo") == b13 + u
    b14 = r"'''Judith Victor Grabiner''' (born before 1938) is {{Infobox actor}}"
    assert genfixes.fix_people_categories(b14, r"foo") == b14 + u
    b15 = r"'''Judith Victor Grabiner''' (born 1938 or 1939) is {{Infobox actor}}"
    assert genfixes.fix_people_categories(b15, r"foo") == b15 + u
    b16 = r"'''Phillipus Rhodicus''' (born 220 BC) was a {{Infobox actor}}"
    assert (
        genfixes.fix_people_categories(b16, r"foo") == b16 + "\r\n" + r"[[Category:220 BC births]]"
    )
    n1 = r"'''Thomas F. Goreau''' (born in [[Germany]], died 1970 in [[Jamaica]]) was [[Category:1970 deaths]]"
    assert genfixes.fix_people_categories(n1, r"foo") == n1
    n2 = r"'''Charles Meik''' (born? - 1923) was an {{Infobox actor}}"
    assert genfixes.fix_people_categories(n2, r"foo") == n2
    n2a = r"'''Anatoly Rasskazov''' (born 1960(?)) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(n2a, r"foo") == n2a
    n3 = r"'''Johannes Widmann''' (born c. 1460 in [[Cheb|Eger]]; died after 1498 in [[Leipzig]]) [[Category:1460s births]]"
    assert genfixes.fix_people_categories(n3, r"foo") == n3
    n4 = "'''John Hulme''' (born circa 1970) is [[Category:Living people]]\r\n[[Category:Year of birth missing (living people)]]"
    assert genfixes.fix_people_categories(n4, r"foo") == n4
    n4a = "'''John Hulme''' (born c.1970) is [[Category:Living people]]\r\n[[Category:Year of birth missing (living people)]]"
    assert genfixes.fix_people_categories(n4a, r"foo") == n4a
    n4b = "'''John Hulme''' (born C.1970) is [[Category:Living people]]\r\n[[Category:Year of birth missing (living people)]]"
    assert genfixes.fix_people_categories(n4b, r"foo") == n4b


def test_fix_people_categories_limits() -> None:
    S = W.for_site(EN)
    b2 = r"[[Category:1960 births]]"
    u = "\r\n" + r"[[Category:Year of birth uncertain]]"
    n5 = "'''Alexander II''' ({{lang-ka|ალექსანდრე II, '''''Aleksandre II'''''}}) (died [[April 1]], [[1510]]) was a.\r\n* Prince David (born 1505)\r\n[[Category:1510 deaths]]"
    assert (
        genfixes.fix_people_categories(
            "'''Alexander II''' ({{lang-ka|ალექსანდრე II, '''''Aleksandre II'''''}}) (died [[April 1]], [[1510]]) was a.\r\n* Prince David (born 1505)\r\n[[Category:1510 deaths]]",
            r"foo",
        )
        == n5
    )
    n6 = "foo {{Infobox actor}}\r\n== hello ==\r\n{{birth date and age|1960|01|9}}"
    assert genfixes.fix_people_categories(n6, r"foo") == n6
    n7 = r"'''Buck Peterson''' (born in [[Minnesota, United States]]<ref name=extreme_1970/>) {{Infobox actor}}"
    assert genfixes.fix_people_categories(n7, r"foo") == n7
    n8 = r"'''Wilhem Heinrich Kramer''' (born [[Dresden]] – 1765) {{Infobox actor}}"
    assert genfixes.fix_people_categories(n8, r"foo") == n8
    n9 = "'''Æthelstan''' was king of [[East Anglia]] in the 9th century.\r\n\r\nAs with the other kings of East Anglia, there is very little textual information available. He did, however, leave an extensive coinage of both portrait and non-portrait type (for example, Coins of England and the United Kingdom, Spink and Son, London, 2005 and the Fitzwilliam Museum database of early medieval coins. [http://www.fitzmuseum.cam.ac.uk/coins/emc]\r\n\r\nIt is suggested that Æthelstan was probably the king who defeated and killed the Mercian kings [[Beornwulf of Mercia|Beornwulf]] (killed 826) and [[Ludeca of Mercia|Ludeca]] (killed 827). He may have attempted to seize power in [[East Anglia]] on the death of [[Coenwulf of Mercia]] (died 821). If this"
    assert genfixes.fix_people_categories(n9, r"foo") == n9
    n10 = "'''Fred''' blah\r\ndied 2002\r\n{{Infobox actor}}"
    assert genfixes.fix_people_categories(n10, r"foo") == n10
    n11 = r"'''Marcus Caecilius Metellus''' was a son of [[Lucius Caecilius Metellus (died 221 BC)|Lucius Caecilius Metellus]]. Deported {{Infobox actor}}"
    assert genfixes.fix_people_categories(n11, r"foo") == n11
    bd1 = r"''Foo''' (8 May 1920 - 11 June 2004) was {{Infobox actor}}"
    bd1a = "\r\n[[Category:1920 births]]"
    bd1b = "\r\n[[Category:2004 deaths]]"
    assert genfixes.fix_people_categories(bd1, r"foo") == bd1 + bd1a + bd1b
    assert genfixes.fix_people_categories(bd1 + bd1a, r"foo") == bd1 + bd1a + bd1b
    assert genfixes.fix_people_categories(bd1 + bd1b, r"foo") == bd1 + bd1b + bd1a
    image = "[[File:long text here.jpg|thumb|250px|Long text here as well to make sure it is over 100 in total length [[this is a long wilikink]]]]\r\n"
    assert genfixes.fix_people_categories(image + bd1, r"foo") == image + bd1 + bd1a + bd1b, (
        r"Ignore File link at start of page"
    )
    bd2 = r"''Foo''' (8 May 1920 – 11 June 2004) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd2, r"foo") == bd2 + bd1a + bd1b
    bd3 = r"'''Foo''' (8 May 1920 somewhere &ndash;11 June 2004) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd3, r"foo") == bd3 + bd1a + bd1b
    bd4 = r"''Foo''' (Circa 8 May 1920 – 11 June 2004) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd4, r"foo") == bd4 + u + "\r\n[[Category:2004 deaths]]"
    bd5 = "'''Autpert Ambrose (Ambroise)''' (ca. 730 – 784) {{Infobox actor}}\r\n[[Category:778 deaths]]"
    assert genfixes.fix_people_categories(bd5, r"foo") == bd5 + u
    bd6 = "'''Saint Bruno of Querfurt''' (c. 970 – February 14 1009) (also known as ''Brun'' and ''Boniface''  {{Infobox actor}}\r\n[[Category:1009 deaths]]"
    assert genfixes.fix_people_categories(bd6, r"foo") == bd6 + u
    bd7 = "'''Agapetus II''' (born in [[Rome]]; died October, 955) was {{Infobox actor}}\r\n[[Category:955 deaths]]"
    assert genfixes.fix_people_categories(bd7, r"foo") == bd7
    bd8 = "'''Husain''' (d. April or May 1382) was a [[Jalayirids|Jalayirid]] ruler (1374-1382). He was the son of [[Shaikh Uvais]]. {{Infobox actor}}\r\n[[Category:1382 deaths]]"
    assert genfixes.fix_people_categories(bd8, r"foo") == bd8
    bd9 = r"'''Mannalargenna''' (ca. 1770-1835), a [[Tasmanian Aborigine]], was the chief of the Ben Lomond tribe (Plangermaireener). {{Infobox actor}}"
    assert (
        genfixes.fix_people_categories(bd9, r"foo")
        == bd9 + "\r\n[[Category:Year of birth uncertain]]\r\n[[Category:1835 deaths]]"
    )
    bd9b = r"'''Mannalargenna''' (c 1770-1835), a [[Tasmanian Aborigine]], was the chief of the Ben Lomond tribe (Plangermaireener). {{Infobox actor}}"
    assert (
        genfixes.fix_people_categories(bd9b, r"foo")
        == bd9b + "\r\n[[Category:Year of birth uncertain]]\r\n[[Category:1835 deaths]]"
    )
    bd10 = r"'''King Godfred''' (ruled 804 - 810) {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd10, r"foo") == bd10
    bd10b = r"'''King Godfred''' (born Abe Smith, transitioned 2005) {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd10b, r"foo") == bd10b
    bd11 = r"'''Rabat I''' (1616/7 - 1644/5) {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd11, r"foo") == bd11 + u
    bd11b = (
        "'''Rabat I''' (born 1969-1970) {{Infobox actor}}\r\n[[Category:Year of birth uncertain]]"
    )
    assert genfixes.fix_people_categories(bd11b, r"foo") == bd11b
    bd12 = "'''Lorenzo Monaco''' (born  '''Piero di Giovanni''' [[Circa|c.]]1370-1425) {{Infobox actor}}\r\n[[Category:1425 deaths]]"
    assert genfixes.fix_people_categories(bd12, r"foo") == bd12 + u
    bd13 = "'''Mocius''' ('''Mucius''', died 288-295), also kno\r\n[[Category:3rd-century deaths]]"
    assert genfixes.fix_people_categories(bd13, r"foo") == bd13
    bd14 = r"'''Asclepigenia''' (fl. 430  – 485 AD) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd14, r"foo") == bd14
    bd14a = r"'''Asclepigenia''' ([[floruit|fl]]. 430  – 485 AD) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd14a, r"foo") == bd14a
    bd14b = r"'''Asclepigenia''' (flourished 430  – 485 AD) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd14b, r"foo") == bd14b
    bd14c = r"'''Asclepigenia''' ({{fl}} 430) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd14c, r"foo") == bd14c
    bd14d = r"'''Asclepigenia''' ({{floruit}} 430) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd14d, r"foo") == bd14d
    no1 = r"'''Bahram I''' (also spelled ''Varahran'' or ''Vahram'', ''r.'' 273&ndash;276) {{Infobox actor}}"
    assert genfixes.fix_people_categories(no1, r"foo") == no1
    no2 = r"'''Trebellianus''' (d. 260-268), also {{Infobox actor}}"
    assert genfixes.fix_people_categories(no2, r"foo") == no2
    no3 = r"'''[[Grand Ayatollah]] {{unicode|Muhammad Sādiq as-Sadr}}''' ([[Arabic]] محمّد صادق الصدر ) is an [[Iraq]]i [[Twelver]] [[Shi'a]] cleric of high rank. He is the father of [[Muqtada al-Sadr]] (born 1973). Sometimes the son is called by his father's name. He is the cousin of Grand Ayatollah [[Muhammad Baqir al-Sadr]] (died 1980). The al-Sadr family are considered [[Sayyid]], which is used among the Shia to denote persons descending directly from [[Muhammad]]. The family's lineage is traced through Imam [[Jafar al-Sadiq]] and his son Imam [[Musa al-Kazim]] the sixth and seventh Shia Imams respectively."
    assert genfixes.fix_people_categories(no3, r"foo") == no3
    no4 = r"'''Bahram I''' (also spelled ''Varahran'' or ''Vahram'', ''r.'' 273&ndash;276) {{Infobox actor}}"
    assert genfixes.fix_people_categories(no4, r"foo") == no4
    no5 = "'''John Coggeshall''' (chr. December 9, 1601) Charles\r\n[[Category:1835 deaths]]"
    assert genfixes.fix_people_categories(no5, r"foo") == no5
    ISO1 = r"'''Ben Moon''' (born [[1960-06-13]]) is a {{Infobox actor}}"
    assert genfixes.fix_people_categories(ISO1, r"foo") == ISO1 + "\r\n" + b2
    bd15 = r"'''Kristina of Norway''' (born in [[1234]] in [[Bergen]] &ndash; circa [[1262]]), sometimes {{Infobox actor}}"
    assert genfixes.fix_people_categories(bd15, r"foo") == bd15 + "\r\n[[Category:1234 births]]"
    s1 = "'''Claire Hazel Weekes''' (1903&mdash;1990) was {{Infobox actor}}\r\n[[Category:1990 deaths|Weekes, Claire]]"
    assert (
        genfixes.fix_people_categories(s1, r"foo")
        == s1 + "\r\n[[Category:1903 births|Weekes, Claire]]"
    )
    m1 = r"'''Hans G Helms''' (born [[8 June]] [[1960]] in [[Teterow]]; full name: ''Hans Günter Helms''; the bearer of the name does not use a full stop after the initial for his middle name) is a [[Germany|German]] experimental writer, composer, and social and economic analyst and critic. {{Infobox actor}}"
    assert genfixes.fix_people_categories(m1, r"foo") == m1 + "\r\n" + b2
    m2 = "'''Arthur Paunzen''' (born [[4 February]] [[1890]], died ?[[9 August]] [[1940]])\r\n[[Category:1890 births]]"
    assert genfixes.fix_people_categories(m2, r"foo") == m2
    m3 = r"Foo {{death date and age|2008|8|21|1942|7|13|mf=y}} {{Infobox actor}}"
    m3a = "\r\n[[Category:1942 births]]\r\n[[Category:2008 deaths]]"
    assert genfixes.fix_people_categories(m3, r"foo") == m3 + m3a
    bug1 = r"'''Jane Borghesi''' (born 17 June{{Fact|date=January 2009}}, [[Melbourne]]) {{Infobox actor}}"
    assert genfixes.fix_people_categories(bug1, r"foo") == bug1, (
        r"Don't take year from date param of template e.g. maintenance tag"
    )
    miss1 = "'''Alonza J. White''' (ca 1836 &ndash; [[August 29]] [[1912]]) {{Infobox actor}}\r\n{{DEFAULTSORT:White, Alonza J}}\r\n[[Category:1912 deaths]]\r\n[[Category:People from St. John's, Newfoundland and Labrador]]"
    miss2 = r"[[Category:Year of birth missing]]"
    assert genfixes.fix_people_categories(miss1 + "\r\n" + miss2, r"foo") == miss1 + u
    both1 = "'''Mary Ellen Wilson''' (1864–1956)<ref name=\"amhum\">{{foo}}</ref> {{Infobox actor}}"
    both2 = "[[Category:1864 births]]\r\n[[Category:1956 deaths]]"
    assert genfixes.fix_people_categories(both1, r"foo") == both1 + "\r\n" + both2
    bug2 = r"'''Foo''' (born {{circa}} 1925) was {{Infobox actor}}"
    assert genfixes.fix_people_categories(bug2, r"foo") == bug2 + u
    bug3 = "'''Joshua William Allen, 6th Viscount Allen''' [[Master of Arts (Oxbridge)|MA]] ({{circa}} [[1782]]–[[21 September]] [[1845]]) was an [[Irish peerage|Irish peer]].\r\n\r\n{{DEFAULTSORT:Allen, Joshua Allen, 6th Viscount}}\r\n[[Category:1845 deaths]]\r\n[[Category:Viscounts in the Peerage of Ireland]]\r\n[[Category:Year of birth uncertain]]"
    assert genfixes.fix_people_categories(bug3, r"foo") == bug3
    bug4 = "\r\n{{infobox person | birth_date = {{Birth date based on age at death |49 |1994|02|25}}\r\n}}\r\n{{DEFAULTSORT:Goldberg, Robert P.}}\r\n[[Category:American computer businesspeople]]\r\n[[Category:American computer scientists]]\r\n[[Category:Harvard University faculty]]\r\n[[Category:1994 deaths]]\r\n[[Category:Harvard University alumni]]\r\n[[Category:Year of birth missing]]"
    assert genfixes.fix_people_categories(bug4, r"foo") == bug4, (
        r"No birth year available in {{Birth date based on age at death}}"
    )
    bug5 = "\r\n{{infobox person | birth_date = {{Birth based on age at death|49 |1994|02|25}}\r\n}}\r\n{{DEFAULTSORT:Goldberg, Robert P.}}\r\n[[Category:American computer businesspeople]]\r\n[[Category:American computer scientists]]\r\n[[Category:Harvard University faculty]]\r\n[[Category:1994 deaths]]\r\n[[Category:Harvard University alumni]]\r\n[[Category:Year of birth missing]]"
    assert genfixes.fix_people_categories(bug5, r"foo") == bug5, (
        r"No birth year available in {{Birth based on age at death}}"
    )


def test_year_of_birth_missing_category_en_only() -> None:
    S = W.for_site(EN)
    good = "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]"
    bad = "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Year of birth missing (living people)]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]"
    S = set_lang(r"fr")
    assert genfixes.fix_people_categories(bad, r"foo") == bad
    S = set_lang(r"en")
    assert genfixes.fix_people_categories(bad, r"foo") == good


def test_fix_people_categories_from_infobox() -> None:
    S = W.for_site(EN)
    a1 = r"'''Fred Smith''' (born 1960) is a bloke. {{Infobox actor}}"
    infob1 = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John C. Zimmerman, Sr.\r\n|term_start       = 1895\r\n|term_end         = 1896\r\n|predecessor      = [[Arthur C. McCall]]\r\n|successor        = [[Samuel C. Randall]]\r\n|birth_date      = May 12, 1835\r\n|birth_place     = [[Free City of Frankfurt]]\r\n|death_date= October 26, 1935\r\n|death_place=\r\n|restingplace = Glenwood Cemetery, Flint\r\n|restingplacecoordinates =\r\n|alma_mater      =\r\n|occupation      =brickmason, mercha\r\n\r\n}}"
    infob2 = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John Footus\r\n|term_start       = 144 BCE\r\n|term_end         = 127 BCE\r\n|predecessor      = [[Arthur C. McCall]]\r\n|successor        = [[Samuel C. Randall]]\r\n|birth_date      = 193 BC\r\n|birth_place     = [[Free City of Frankfurt]]\r\n|death_date= 127 BCE\r\n|death_place=\r\n|alma_mater      =\r\n|occupation      =brickmason, mercha\r\n\r\n}}"
    infob1a = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John C. Zimmerman, Sr.\r\n|term_start       = 1895\r\n|term_end         = 1896\r\n|predecessor      = [[Arthur C. McCall]]\r\n|successor        = [[Samuel C. Randall]]\r\n|dateofbirth     = May 12, 1835\r\n|birth_place     = [[Free City of Frankfurt]]\r\n|dateofdeath= October 26, 1935\r\n|death_place=\r\n|restingplace = Glenwood Cemetery, Flint\r\n|restingplacecoordinates =\r\n|alma_mater      =\r\n|occupation      =brickmason, mercha\r\n\r\n}}"
    infob1b = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John C. Zimmerman, Sr.\r\n|term_start       = 1895\r\n|term_end         = 1896\r\n|predecessor      = [[Arthur C. McCall]]\r\n|successor        = [[Samuel C. Randall]]\r\n|DateOfBirth     = May 12, 1835\r\n|birth_place     = [[Free City of Frankfurt]]\r\n|DateOfDeath= October 26, 1935\r\n|death_place=\r\n|restingplace = Glenwood Cemetery, Flint\r\n|restingplacecoordinates =\r\n|alma_mater      =\r\n|occupation      =brickmason, mercha\r\n\r\n}}"
    assert (
        genfixes.fix_people_categories(infob1, r"foo")
        == infob1 + "\r\n[[Category:1835 births]]\r\n[[Category:1935 deaths]]"
    )
    assert (
        genfixes.fix_people_categories(infob1a, r"foo")
        == infob1a + "\r\n[[Category:1835 births]]\r\n[[Category:1935 deaths]]"
    )
    assert (
        genfixes.fix_people_categories(infob1b, r"foo")
        == infob1b + "\r\n[[Category:1835 births]]\r\n[[Category:1935 deaths]]"
    )
    assert (
        genfixes.fix_people_categories(infob2, r"foo")
        == infob2 + "\r\n[[Category:193 BC births]]\r\n[[Category:127 BC deaths]]"
    )
    assert (
        genfixes.fix_people_categories(
            infob1 + "\r\n[[Category:1835 births]]\r\n[[Category:1935 deaths]]", r"foo"
        )
        == infob1 + "\r\n[[Category:1835 births]]\r\n[[Category:1935 deaths]]"
    )
    infob3 = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John Foo\r\n|predecessor      = [[Arthur C. McCall]]\r\n|successor        = [[Samuel C. Randall]]\r\n|birth_date      = 1970s\r\n|birth_place     = [[Free City of Frankfurt]]\r\n|death_date=\r\n|death_place=\r\n|alma_mater      =\r\n|occupation      =brickmason, mercha\r\n\r\n}}"
    assert genfixes.fix_people_categories(infob3, r"foo") == infob3, (
        r"no change if only decade of birth"
    )
    infob4 = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John Foo\r\n|predecessor      = [[Arthur C. McCall]]\r\n|successor        = [[Samuel C. Randall]]\r\n|birth_date      = {{floruit|1444}}\r\n|birth_place     = [[Free City of Frankfurt]]\r\n|death_date=\r\n|death_place=\r\n|alma_mater      =\r\n|occupation      =brickmason, mercha\r\n\r\n}}"
    assert genfixes.fix_people_categories(infob4, r"foo") == infob4, r"no change if only floruit"
    unc1 = "'''Aaron Walden''' (born at [[Warsaw]] about 1835, died 1912) was a Polish Jewish [[Talmudist]], editor, and author.\r\n{{DEFAULTSORT:Walden, Aaron}}\r\n[[Category:Polish Jews]]\r\n[[Category:1912 deaths]]\r\n[[Category:Year of birth uncertain]]"
    assert genfixes.fix_people_categories(unc1, r"Aaron Walden") == unc1
    Refs = r"<ref>a</ref> <ref>a</ref> <ref>a</ref> <ref>a</ref> <ref>a</ref> <ref>a</ref> <ref>a</ref>"
    assert (
        genfixes.fix_people_categories(a1 + Refs + Refs + Refs, r"foo") == a1 + Refs + Refs + Refs
    )
    infob1Date = infob1.replace(r"alma_mater      =", r"date=1 March")
    assert (
        genfixes.fix_people_categories(infob1Date, r"foo")
        == infob1Date + "\r\n[[Category:1835 births]]\r\n[[Category:1935 deaths]]"
    ), r"Can use template with date param when date doesn't contain year"
    infob5 = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John Foo\r\n|birth_date      = \r\n|death_date= XXX{{sfn|Smith|2005}}\r\n|death_place=\r\n}}"
    assert genfixes.fix_people_categories(infob5, r"foo") == infob5, r"ignore ref for death year"
    infob6 = "{{Infobox Officeholder\r\n|honorific-prefix   =\r\n|name            = John Foo\r\n|birth_date      = \r\n|death_date= {{birth date|2005|1|1}}\r\n|death_place=\r\n}}\r\n[[Category:2005 births]]"
    assert genfixes.fix_people_categories(infob6, r"foo") == infob6, r"ignore ref for death year"


def test_fix_people_categories_refs() -> None:
    S = W.for_site(EN)
    refs = r"<ref>foo</ref> and <ref>foo</ref> and <ref>foo</ref> and <ref>foo</ref> and <ref>foo</ref> and <ref>foo</ref> "
    Over20Refs = (
        refs + refs + refs + refs + r"'''Fred Smith''' (born 1980) is a bloke. {{Infobox actor}}"
    )
    assert genfixes.fix_people_categories(Over20Refs, r"test") == Over20Refs, (
        r"no change when over 20 refs and no exiting birth/death/living cat"
    )
    assert r"[[Category:1980 births]]" in genfixes.fix_people_categories(
        Over20Refs + r" [[Category:Living people]]", r"test"
    ), r"can add cat when over 20 refs and living people cat already"


def test_fix_people_categories_future_test() -> None:
    S = W.for_site(EN)
    a1 = r"'''Fred Smith''' (born 2060) is a bloke. {{Infobox actor}}"
    assert genfixes.fix_people_categories(a1, r"foo") == a1


def test_year_of_birth_missing_category() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_people_categories(
            "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Year of birth missing (living people)]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]",
            r"foo",
        )
        == "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]"
    )
    assert (
        genfixes.fix_people_categories(
            "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Year of birth missing (living people)]]\r\n[[Category:Living people]]\r\n[[Category : 1944 births]]",
            r"foo",
        )
        == "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Living people]]\r\n[[Category : 1944 births]]"
    ), r"category excess whitespace"
    assert (
        genfixes.fix_people_categories(
            "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Year of birth missing]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]",
            r"foo",
        )
        == "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]"
    )
    assert (
        genfixes.fix_people_categories(
            "A\r\n\r\n[[Category:Year of birth missing]]\r\n[[Category:100 BC births]]", r"foo"
        )
        == "A\r\n\r\n[[Category:100 BC births]]"
    ), r"YOB missing removal for BC birth cat"
    assert (
        genfixes.fix_people_categories(
            "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]",
            r"foo",
        )
        == "[[Category:Pakistani lawyers]]\r\n[[Category:Attorneys General of Pakistan]]\r\n[[Category:Living people]]\r\n[[Category:1944 births]]"
    )
    a = "Mr foo {{Infobox actor}} was great\r\n[[Category:1960 deaths]]"
    assert (
        genfixes.fix_people_categories(a + "\r\n" + r"[[Category:Year of death missing]]", r"test")
        == a + "\r\n"
    )
    b = "Mr foo {{Infobox actor}} was great\r\n[[Category:100 BC deaths]]"
    assert (
        genfixes.fix_people_categories(b + "\r\n" + r"[[Category:Year of death missing]]", r"test")
        == b + "\r\n"
    ), r"YOD Missing is removed for BC death"


def test_get_category_sort_tests() -> None:
    S = W.for_site(EN)
    assert (
        len(
            genfixes.get_category_sort(
                "'''Jonathan Sothcott''' (born [[26 April]] [[1980]]) {{Infobox actor}}\r\n{{DEFAULTSORT:Sothcott, Jonathan}}\r\n[[Category:British television producers|Sothcott, Jonathon]]"
            )
        )
        == 0
    )
    assert (
        genfixes.get_category_sort(
            "'''Jonathan Sothcott''' (born [[26 April]] [[1980]]) {{Infobox actor}}\r\n[[Category:British television producers|Sothcott, Jonathan]]\r\n[[Category:Living people|Sothcott, Jonathan]]"
        )
        == r"Sothcott, Jonathan"
    )
    assert (
        genfixes.get_category_sort(
            "'''Jonathan Sothcott''' (born [[26 April]] [[1980]]) {{Infobox actor}}\r\n[[Category:Living people|Sothcott, Jonathan]]"
        )
        == r"Sothcott, Jonathan"
    )
    assert (
        len(
            genfixes.get_category_sort(
                "'''Jonathan Sothcott''' (born [[26 April]] [[1980]]) {{Infobox actor}}\r\n[[Category:British television producers|Sothcott, Jonathan]]\r\n[[Category:Living people|Sothcott, Jonathan]]\r\n[[Category:1944 births]]"
            )
        )
        == 0
    )


def test_category_match() -> None:
    S = W.for_site(EN)
    assert genfixes.category_match(r"foo [[Category:1990 births]]", r"1990 births")
    assert genfixes.category_match(r"foo [[Category:1990 births ]]", r"1990 births")
    assert genfixes.category_match(r"foo [[Category: 1990 births  ]]", r"1990 births")
    assert genfixes.category_match(r"foo [[Category:1990 Births]]", r"1990 births")
    assert genfixes.category_match(r"foo [[Category:1990 births]]", r"1990 Births")
    assert genfixes.category_match(r"foo [[Category:1990 births|foo]]", r"1990 births")
    assert genfixes.category_match(r"foo [[Category:1990 births | foo]]", r"1990 births")
    assert genfixes.category_match(
        r"foo [[Category:Year of birth missing|Foo, bar]]", r"Year of birth missing"
    )
    assert not (genfixes.category_match(r"foo [[Category:1990 births]]", r"1990"))
    assert not (genfixes.category_match(r"foo [[Category:1990_births]]", r"1990 births"))


def test_living_people_tests() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.living_people(
            "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births|Smith, Fred]]", r"A"
        )
        == "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births|Smith, Fred]][[Category:Living people|Smith, Fred]]"
    )
    assert (
        genfixes.living_people(
            "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births]]", r"A"
        )
        == "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births]][[Category:Living people]]"
    )
    assert (
        genfixes.living_people(
            "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births]]",
            r"Wikipedia:Sandbox",
        )
        == "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births]][[:Category:Living people]]"
    )
    b1 = r"'''Fred Smith''' is a bloke."
    assert genfixes.living_people(b1, r"A") == b1
    a = "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births]]\r\n[[Category:1990 deaths]]"
    b = "'''Fred Smith''' is a bloke.\r\n[[Category:1960 births]]\r\n[[Category:1990 deaths]]"
    b2 = "'''Fred Smith''' is a bloke.\r\n[[Category:1960 births]]\r\n[[Category:1990 suicides]]"
    c = "'''Fred Smith''' is a bloke.\r\n[[Category:1960 births|Smith, Fred]]\r\n[[Category:1990 deaths|Smith, Fred]]"
    d = "'''Fred Smith''' (born 11 May 1950 - died 17 August 1990) is a bloke.\r\n[[Category:1960 births|Smith, Fred]]"
    e = "'''Fred Smith''' (born 1950) is a bloke.\r\n[[Category:1950 births|Smith, Fred]]\r\n{{Recentlydeceased}}"
    f = "'''Fred Smith''' (born 1950) is a bloke.\r\n[[Category:1950 births|Smith, Fred]]\r\n{{recentlydeceased}}"
    g = "'''Fred Smith''' (born 1950) is a bloke.\r\n[[Category:1950 births|Smith, Fred]]\r\n[[Category:Year of death missing]]"
    h = r"'''Fred Smith''' (d. 1950) is a bloke."
    assert genfixes.living_people(a, r"A") == a
    assert genfixes.living_people(b, r"A") == b
    assert genfixes.living_people(b2, r"A") == b2
    assert genfixes.living_people(c, r"A") == c
    assert genfixes.living_people(d, r"A") == d
    assert genfixes.living_people(e, r"A") == e
    assert genfixes.living_people(f, r"A") == f
    assert genfixes.living_people(g, r"A") == g
    assert genfixes.living_people(h, r"A") == h
    d1 = "'''Fred Smith''' (born 1879) is a bloke.\r\n[[Category:1879 births|Smith, Fred]]"
    assert genfixes.living_people(d1, r"A") == d1
    d2 = r"Fred [[Category:15th-century births]]"
    assert genfixes.living_people(d2, r"A") == d2


def test_living_people_tests_en_only() -> None:
    S = W.for_site(EN)
    Before = "'''Fred Smith''' (born 1960) is a bloke.\r\n[[Category:1960 births|Smith, Fred]]"
    S = set_lang(r"sco")
    assert genfixes.living_people(Before, r"A") == Before, r"no changes in Scottish wikipedia"
    S = set_project(r"en", "commons")
    assert genfixes.living_people(Before, r"A") == Before, r"no changes in Commons"
    S = set_project(r"en", "wikipedia")
    assert (
        genfixes.living_people(Before, r"A") == Before + r"[[Category:Living people|Smith, Fred]]"
    )


def test_fix_syntax_category() -> None:
    S = W.for_site(EN)
    correct = r"Now [[Category:2005 albums]] there"
    assert genfixes.fix_syntax(r"Now {{Category:2005 albums]] there") == correct
    assert genfixes.fix_syntax(r"Now {{Category:2005 albums}} there") == correct
    assert genfixes.fix_syntax(r"Now {{ Category:2005 albums]] there") == correct
    assert genfixes.fix_syntax(r"Now [[Category:2005 albums}} there") == correct
    assert genfixes.fix_syntax(r"Now [[  Category:2005 albums}} there") == correct
    assert genfixes.fix_syntax(correct) == correct


def test_test_fix_categories() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_categories(r"[[ categOry : Foo_bar]]") == r"[[Category:Foo bar]]"
    assert genfixes.fix_categories(r"[[ categOry : Foo_bar|boz]]") == r"[[Category:Foo bar|boz]]"
    assert (
        genfixes.fix_categories(r"[[category : foo_bar%20|quux]]") == r"[[Category:Foo bar|quux]]"
    )
    assert genfixes.fix_categories(r"[[Category:Foo_bar]]") == r"[[Category:Foo bar]]"
    assert genfixes.fix_categories(r"[[category:Foo bar]]") == r"[[Category:Foo bar]]"
    assert genfixes.fix_categories(r"[[Category::Foo bar]]") == r"[[Category:Foo bar]]"
    assert genfixes.fix_categories(r"[[Category  :  Foo_bar  ]]") == r"[[Category:Foo bar]]"
    assert genfixes.fix_categories(r"[[CATEGORY: Foo_bar]]") == r"[[Category:Foo bar]]"
    assert (
        genfixes.fix_categories(
            r"[[Category:Public transport in Auckland| Public transport in Auckland]]"
        )
        == r"[[Category:Public transport in Auckland| Public transport in Auckland]]"
    )
    assert (
        genfixes.fix_categories(r"[[Category:Actors|Fred Astaire ]]")
        == r"[[Category:Actors|Fred Astaire]]"
    ), r"trailing space IS removed"
    assert (
        genfixes.fix_categories(r"[[Category:Actors|Fred Astaire    ]]")
        == r"[[Category:Actors|Fred Astaire]]"
    ), r"trailing space IS removed"
    assert (
        genfixes.fix_categories(r"[[Category:Actors| Fred Astaire ]]")
        == r"[[Category:Actors| Fred Astaire]]"
    ), r"trailing space IS removed"
    assert genfixes.fix_categories(r"[[Category:London| ]]") == r"[[Category:London| ]]", (
        r"leading space NOT removed"
    )
    assert (
        genfixes.fix_categories(r"[[Category:Slam poetry| ]] ") == r"[[Category:Slam poetry| ]] "
    ), r"leading space NOT removed"
    assert (
        genfixes.fix_categories(r"[[Category: foo_bar |boz_quux]]")
        == r"[[Category:Foo bar|boz_quux]]"
    )
    assert (
        genfixes.fix_categories(r"[[Category: foo_bar|{{boz_quux}}]]")
        == r"[[Category:Foo bar|{{boz_quux}}]]"
    )
    assert r"{{{boz_quux}}}" in genfixes.fix_categories(r"[[CategorY : foo_bar{{{boz_quux}}}]]")
    assert (
        genfixes.fix_categories(r"[[CategorY : foo_bar|{{{boz_quux}}}]]")
        == r"[[Category:Foo bar|{{{boz_quux}}}]]"
    )
    assert (
        genfixes.fix_categories(
            r"[[Category:Date computing template|{{<noinclude>BASE</noinclude>PAGENAME}}]]"
        )
        == r"[[Category:Date computing template|{{<noinclude>BASE</noinclude>PAGENAME}}]]"
    )
    assert (
        genfixes.fix_categories(r"[[Category:World Scout Committee members|Lainé, Juan]]")
        == r"[[Category:World Scout Committee members|Laine, Juan]]"
    )
    S = set_site(
        namespaces={k: v for k, v in current_site().namespaces.items() if k != Namespace.CATEGORY}
    )
    assert len(genfixes.fix_categories(r"")) == 0, r"Fallback to English category namespace name"
    S = set_site(namespaces={**current_site().namespaces, Namespace.CATEGORY: r"Category:"})


def test_test_fix_categories_ru() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ru")
    assert (
        genfixes.fix_categories(r"[[Category:World Scout Committee members|Lainé, Juan]]")
        == r"[[Category:World Scout Committee members|Lainé, Juan]]"
    ), r"no diacritic removal for sort key on ru-wiki"
    S = set_lang(r"en")
    assert (
        genfixes.fix_categories(r"[[Category:World Scout Committee members|Lainé, Juan]]")
        == r"[[Category:World Scout Committee members|Laine, Juan]]"
    )


def test_test_fix_categories_brackets() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_categories(r"[[Category:London]]]") == r"[[Category:London]]"
    assert genfixes.fix_categories(r"[[Category:London]]]]") == r"[[Category:London]]"
    assert genfixes.fix_categories(r"[[[[Category:London]]]") == r"[[Category:London]]"
    assert genfixes.fix_categories(r"[[[[Category:London]]]]") == r"[[Category:London]]"
    assert genfixes.fix_categories(r"[[Category:London]]") == r"[[Category:London]]"
