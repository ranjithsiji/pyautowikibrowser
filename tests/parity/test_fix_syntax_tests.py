"""Port of AWB UnitTests/FixSyntaxTests.cs: wiki syntax fixes.

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
from awb_l.core.parsers.parsers import DateLocale
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_site, utc_month_year
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_fix_isbn_format() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"ISBN: 1245781549") == r"ISBN 1245781549", (
        r"removes colon after ISBN"
    )
    assert genfixes.fix_syntax(r"[[ISBN]] 1245781549") == r"ISBN 1245781549", (
        r"removes wikilink around ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN-10: 1245781549") == r"ISBN 1245781549", (
        r"removes colon after ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN-13: 9781245781549") == r"ISBN 9781245781549", (
        r"removes colon after ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN 1245781549") == r"ISBN 1245781549", (
        r"no change if already correct"
    )
    assert genfixes.fix_syntax(r"ISBN:1245781549") == r"ISBN 1245781549", (
        r"removes colon after ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN	1245781549") == r"ISBN 1245781549", r"ISBN with tab"
    assert genfixes.fix_syntax(r"ISBN 	1245781549") == r"ISBN 1245781549", (
        r"ISBN with space and tab"
    )
    assert genfixes.fix_syntax(r"ISBN-1245781549") == r"ISBN 1245781549", (
        r"removes minus after ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN-1045781549") == r"ISBN 1045781549", (
        r"removes minus after ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN–1245781549") == r"ISBN 1245781549", r"removes dash after ISBN"
    assert genfixes.fix_syntax(r"ISBN–13 9781245781549") == r"ISBN-13 9781245781549", (
        r"Fix ISBN–13 endash to dash"
    )
    assert genfixes.fix_syntax(r"ISBN–10 12345781549") == r"ISBN-10 12345781549", (
        r"Fix ISBN–10 endash to dash"
    )
    assert genfixes.fix_syntax(r"ISBN-10 12345781549") == r"ISBN-10 12345781549", r"do nothing"
    assert genfixes.fix_syntax(r"ISBN-13 9781245781549") == r"ISBN-13 9781245781549", r"do nothing"
    assert genfixes.fix_syntax(r"ISBN 0-9752298-0-x") == r"ISBN 0-9752298-0-X", r"capitalise X"
    assert genfixes.fix_syntax(r"ISBN 097522980x") == r"ISBN 097522980X", r"capitalise X"
    assert genfixes.fix_syntax(r"ISBN 978–92–0–103709–1") == r"ISBN 978-92-0-103709-1", (
        r"endash to hyphen within ISBN"
    )
    assert genfixes.fix_syntax(r"ISBN 978–92–0–103709–X") == r"ISBN 978-92-0-103709-X", (
        r"endash to hyphen within ISBN"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.hup.harvard.edu/catalog.php?isbn=9780674372993 example]")
        == r"[http://www.hup.harvard.edu/catalog.php?isbn=9780674372993 example]"
    ), r"no change inside url"
    assert (
        genfixes.fix_syntax(r'foo<ref name="isbn0-19-517234-5" />')
        == r'foo<ref name="isbn0-19-517234-5" />'
    ), r"no change inside ref"
    assert (
        genfixes.fix_syntax(r"[[ISBN]] [[Special:BookSources/9711005522|9711005522]]")
        == r"ISBN 9711005522"
    ), r"ISBNT substed"
    assert (
        genfixes.fix_syntax(r"[[ISBN]] [[Special:BookSources/9780881925166|9780881925166]]")
        == r"ISBN 9780881925166"
    ), r"ISBNT substed"
    assert (
        genfixes.fix_syntax(
            r"[[ISBN]] [[Special:BookSources/9780881925166|<bdi>9780881925166</bdi>]]"
        )
        == r"ISBN 9780881925166"
    ), r"ISBNT substed bdi tags"
    assert (
        genfixes.fix_syntax(
            r"[[International Standard Book Number|ISBN]] [[Special:BookSources/9780881925166|9780881925166]]"
        )
        == r"ISBN 9780881925166"
    ), r"ISBNT substed"
    assert (
        genfixes.fix_syntax(
            r"[[International Standard Book Number|ISBN]] [[Special:BookSources/9780881925166|<bdi>9780881925166</bdi>]]"
        )
        == r"ISBN 9780881925166"
    ), r"ISBNT substed bdi tags"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info ISBN 978-92-0-103709-X]")
        == r"[http://www.site.com info] ISBN 978-92-0-103709-X"
    ), r"ISBN out of end of http external link"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info ISBN 978-92-0-103709-X.]")
        == r"[http://www.site.com info] ISBN 978-92-0-103709-X."
    ), r"ISBN out of end of http external link"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info ISBN 978-92-0-103709-X. ]")
        == r"[http://www.site.com info] ISBN 978-92-0-103709-X."
    ), r"ISBN out of end of http external link"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info ISBN 978920103709X]")
        == r"[http://www.site.com info] ISBN 978920103709X"
    ), r"ISBN out of end of http external link, ISBN ends X"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info ISBN 9789201037091]")
        == r"[http://www.site.com info] ISBN 9789201037091"
    ), r"ISBN out of end of http external link, ISBN ends number"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info, ISBN 9789201037091]")
        == r"[http://www.site.com info] ISBN 9789201037091"
    ), r"ISBN out of end of http external link, comma"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info; ISBN 9789201037091]")
        == r"[http://www.site.com info] ISBN 9789201037091"
    ), r"ISBN out of end of http external link, semicolon"
    assert (
        genfixes.fix_syntax(r"[http://www.site.com info ISBN 978920103709X ISBN 9789201037091]")
        == r"[http://www.site.com info] ISBN 978920103709X ISBN 9789201037091"
    ), r"ISBN out of end of http external link, 2x"
    nochange = r"[http://www.site.com ISBN 978-92-0-103709-X]"
    assert genfixes.fix_syntax(nochange) == nochange, (
        r"No change to ISBN at end of external link when no other link text"
    )
    nochange = r"{{cite web |title=Markus |url=https://www.lesestoff.ch/de/detail/ISBN-9783426227817/Heitz |access-date=2 August 2023 }}"
    assert genfixes.fix_syntax(nochange) == nochange, (
        r"No change to ISBN at end of external link when no other link text"
    )


def test_fix_isbn_infobox() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"{{infobox foo|isbn=ISBN 9711005522 }}")
        == r"{{infobox foo|isbn=9711005522 }}"
    ), r"ISBN removed in infobox isbn parameter"
    assert (
        genfixes.fix_syntax(r"{{infobox foo|isbn=ISBN: 9711005522 }}")
        == r"{{infobox foo|isbn=9711005522 }}"
    ), r"ISBN: removed in infobox isbn parameter"
    assert (
        genfixes.fix_syntax(r"{{infobox foo|isbn=ISBN : 9711005522 }}")
        == r"{{infobox foo|isbn=9711005522 }}"
    ), r"ISBN : removed in infobox isbn parameter"
    assert (
        genfixes.fix_syntax(r"{{infobox foo|isbn=ISBN  9711005522 }}")
        == r"{{infobox foo|isbn=9711005522 }}"
    ), r"ISBN removed in infobox isbn parameter, extra space"
    assert (
        genfixes.fix_syntax(
            r"{{infobox foo|isbn=ISBN 9711005522 }} {{infobox foo|isbn=ISBN 9744005522 }}"
        )
        == r"{{infobox foo|isbn=9711005522 }} {{infobox foo|isbn=9744005522 }}"
    ), r"ISBN removed in infobox isbn parameter, multiple infoxboxes"
    assert (
        genfixes.fix_syntax(r"{{infobox foo|isbn=9711005522 }}")
        == r"{{infobox foo|isbn=9711005522 }}"
    ), r"No change when isbn= already correct"
    assert (
        genfixes.fix_syntax(r"{{infobox foo|foo=ISBN 9711005522 }}")
        == r"{{infobox foo|foo=ISBN 9711005522 }}"
    ), r"No change to non-isbn parameter"


def test_fix_pmid_format() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"PMID: 1245781549") == r"PMID 1245781549", (
        r"removes colon after PMID"
    )
    assert genfixes.fix_syntax(r"PMID:1245781549") == r"PMID 1245781549", (
        r"removes colon after PMID"
    )
    assert genfixes.fix_syntax(r"PMID:    1245781549") == r"PMID 1245781549", (
        r"removes colon after PMID"
    )
    assert genfixes.fix_syntax(r"PMID 1245781549") == r"PMID 1245781549", (
        r"No change if alrady correct"
    )
    assert genfixes.fix_syntax(r"[[PMID:1245781549]]") == r"[[PMID:1245781549]]", (
        r"No change if alrady correct - magic link"
    )
    S = set_lang(r"hu")
    assert genfixes.fix_syntax(r"PMID:1245781549") == r"PMID:1245781549"
    S = set_lang(r"en")
    assert genfixes.fix_syntax(r"PMID: 1245781549") == r"PMID 1245781549", (
        r"removes colon after PMID"
    )


def test_fix_html_tags_syntax() -> None:
    S = W.for_site(EN)
    corr = r"Foo<small>bar</small> was the 1<sub>st</sub> to drink H<sup>2</sup>O"
    assert (
        genfixes.fix_syntax(r"Foo<small>bar<small/> was the 1<sub>st<sub/> to drink H<sup>2<sup/>O")
        == corr
    )
    assert (
        genfixes.fix_syntax(
            r"Foo<small>bar<small/> was the 1<sub>st</sub/> to drink H<sup>2</sup/>O"
        )
        == corr
    )
    assert genfixes.fix_syntax(corr) == corr
    assert (
        genfixes.fix_syntax(r"<center>Centered text<center/>") == r"<center>Centered text</center>"
    )


def test_fix_syntax_horizontal_rule() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<hr>") == r"----"
    assert genfixes.fix_syntax(r"-----") == r"----"
    assert genfixes.fix_syntax("A\r\n<hr>\r\nB") == "A\r\n----\r\nB"
    Nochange = r"A<hr>"
    assert genfixes.fix_syntax(Nochange) == Nochange
    Nochange = r"A----"
    assert genfixes.fix_syntax(Nochange) == Nochange


def test_fix_syntax_redirects() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax_redirects("#REDIRECT\r\n[[Foo]]") == r"#REDIRECT [[Foo]]", r"newline"
    assert genfixes.fix_syntax_redirects(r"#REDIRECT [[[Foo]]]") == r"#REDIRECT [[Foo]]", (
        r"extra opening/closing bracket"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT [[Foo]]]") == r"#REDIRECT [[Foo]]", (
        r"one extra closing bracket"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT [[[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"one extra opening bracket"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT [[[[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"two extra opening brackets"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT [[Foo]]]]") == r"#REDIRECT [[Foo]]", (
        r"two extra closing brackets"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT [[[[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"two extra opening/closing brackets"
    )
    assert genfixes.fix_syntax_redirects("#REDIRECT\r\n[[[Foo]]]") == r"#REDIRECT [[Foo]]", (
        r"extra brackets and newline"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT:[[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"double dot unspaced"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT: [[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"double dot with space"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT=[[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"equal sign unspaced"
    )
    assert genfixes.fix_syntax_redirects(r"#REDIRECT= [[Foo]]") == r"#REDIRECT [[Foo]]", (
        r"equal sihn with space"
    )
    assert genfixes.fix_syntax_redirects("#REDIRECT=\r\n[[[Foo]]]") == r"#REDIRECT [[Foo]]", (
        r"extra brackets, equal sign and newline"
    )
    assert (
        genfixes.fix_syntax_redirects(r"#REDIRECT[[Foo]] {{Template:R from move}}")
        == r"#REDIRECT[[Foo]] {{R from move}}"
    ), r"template prefix"


def test_fix_syntax_redirects_brackets() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax_redirects(r"#REDIRECT[[Foo]] {{Template:R from move")
        == r"#REDIRECT[[Foo]] {{R from move}}"
    ), r"Missing }}"
    assert (
        genfixes.fix_syntax_redirects(r"#REDIRECT[[Foo]] {{Template:R from move" + "\r\n")
        == r"#REDIRECT[[Foo]] {{R from move}}"
    ), r"Missing }} with newline"
    assert (
        genfixes.fix_syntax_redirects(r"#REDIRECT[[Foo]] {{R from move}")
        == r"#REDIRECT[[Foo]] {{R from move}}"
    ), r"Missing }"
    assert (
        genfixes.fix_syntax_redirects(r"#REDIRECT[[Foo]] {{R from move}]")
        == r"#REDIRECT[[Foo]] {{R from move}}"
    ), r"Has }]"
    assert (
        genfixes.fix_syntax_redirects(r"#REDIRECT[[Foo]] {{R from move]}")
        == r"#REDIRECT[[Foo]] {{R from move}}"
    ), r"Has ]}"


def test_external_links_newline() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax("here [http://www.site.com text\r\nhere]")
        == r"here [http://www.site.com text here]"
    ), r"newline removed"
    assert (
        genfixes.fix_syntax("here [http://www.site.com text here2\r\n]")
        == r"here [http://www.site.com text here2 ]"
    ), r"newline removed2"
    assert (
        genfixes.fix_syntax("here [http://www.site.com text\r\nhere\r\nthere]")
        == r"here [http://www.site.com text here there]"
    ), r"multiple newlines removed"
    assert (
        genfixes.fix_syntax("here [http://www.site.com |text\r\nhere]")
        == r"here [http://www.site.com text here]"
    ), r"newline removed3"
    assert (
        genfixes.fix_syntax(r"here [http://www.site.com text here]")
        == r"here [http://www.site.com text here]"
    ), r"no change if no new line"


def test_unbalanced_brackets() -> None:
    S = W.for_site(EN)
    bracketLength = 0
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {{now}")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {{now} abc")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {{now} abc {{def}}")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} [[now]")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello [[bye]] {{now}")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} [now words [here]")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} now] words [here]")),
        (bracketLength := _t[1]),
    )[0][0] == 21
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {now}}")),
        (bracketLength := _t[1]),
    )[0][0] == 22
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"[http://www.site.com a link [cool]]")),
        (bracketLength := _t[1]),
    )[0][0] == 33
    assert bracketLength == 2
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {now")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {abyea} {now")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {now {{here}} a")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {now {here} a {{a}}")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} now {here} a {{a}}}")),
        (bracketLength := _t[1]),
    )[0][0] == 36
    assert bracketLength == 1
    assert ((_t := genfixes.unbalanced_brackets(r"{bye")), (bracketLength := _t[1]))[0][0] == 0
    assert bracketLength == 1
    assert ((_t := genfixes.unbalanced_brackets(r"<bye")), (bracketLength := _t[1]))[0][0] == 0
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello [words [here&#93; end] now]")),
        (bracketLength := _t[1]),
    )[0][0] == 36
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {{now} or {{now} was")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {{now} or [[now] was")),
        (bracketLength := _t[1]),
    )[0][0] == 18
    assert (
        (
            _t := genfixes.unbalanced_brackets(
                "==External links==\r\n*[http://www.transfermarkt.de/profil.html]&section=p&teamid=458 Profile] at Transfermarkt.de\r\n*[http://www.vi.nl/Spelers\r\n"
            )
        ),
        (bracketLength := _t[1]),
    )[0][0] == 115
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"{{Infobox|foo=bar (OMG} }}")),
        (bracketLength := _t[1]),
    )[0][0] == 0
    assert ((_t := genfixes.unbalanced_brackets(r"now [[link],] at")), (bracketLength := _t[1]))[0][
        0
    ] == 4
    assert bracketLength == 2


def test_unbalanced_brackets_none() -> None:
    S = W.for_site(EN)
    bracketLength = 0
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} {{now}}")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello [[bye]] {{now}}")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} [now]")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert ((_t := genfixes.unbalanced_brackets(r"now hello")), (bracketLength := _t[1]))[0][
        0
    ] == -1
    assert (
        (
            _t := genfixes.unbalanced_brackets(
                "<ref>[http://www.pubmedcentral.nih.gov/articlerender.fcgi?artid=32159 Message to\r\ncomplementary and alternative medicine: evidence is a better friend than power. Andrew J Vickers]</ref>"
            )
        ),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"[http://www.site.com a link [cool&#93;]")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"[http://www.site.com a link &#91;cool&#93; here]")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (
            _t := genfixes.unbalanced_brackets(
                r"*[http://external.oneonta.edu/html A&#91;lbert&#93; T. 1763]"
            )
        ),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} <pre>{now}}</pre>")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} <math>{a{b}}</math>")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{bye}} <code>{now}}</code>")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{LSJ|foo(bar}}")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert ((_t := genfixes.unbalanced_brackets(r"now hello {{)!}}")), (bracketLength := _t[1]))[0][
        0
    ] == -1
    assert ((_t := genfixes.unbalanced_brackets(r"now hello {{!(}}")), (bracketLength := _t[1]))[0][
        0
    ] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{Lisp2|foo(bar}}")),
        (bracketLength := _t[1]),
    )[0][0] == -1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now hello {{C sharp|foo(bar}}")),
        (bracketLength := _t[1]),
    )[0][0] == -1


def test_unbalanced_tags() -> None:
    S = W.for_site(EN)
    bracketLength = 0
    assert ((_t := genfixes.unbalanced_brackets(r"now <b>hello /b>")), (bracketLength := _t[1]))[0][
        0
    ] == 15
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"<a>asdf</a> now <b>hello /b>")),
        (bracketLength := _t[1]),
    )[0][0] == 27
    assert bracketLength == 1
    assert (
        (_t := genfixes.unbalanced_brackets(r"now was < 50 cm long")),
        (bracketLength := _t[1]),
    )[0][0] == -1


def test_test_wording_into_bare_external_links() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(
            r"<ref>B'er Chayim Temple, National Park Service, [ http://www.nps.gov/history/nr/travel/cumberland/ber.htm]</ref>"
        )
        == r"<ref>[http://www.nps.gov/history/nr/travel/cumberland/ber.htm B'er Chayim Temple, National Park Service]</ref>"
    )
    assert (
        genfixes.fix_syntax(
            r"<ref>[http://www.nps.gov/history] [http://www.nps.gov/history/nr/travel/cumberland/ber.htm]</ref>"
        )
        == r"<ref>[http://www.nps.gov/history] [http://www.nps.gov/history/nr/travel/cumberland/ber.htm]</ref>"
    )


def test_fix_syntax_subst_ref_tags() -> None:
    S = W.for_site(EN)
    assert r"{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}" not in genfixes.fix_syntax(
        r"<ref>{{cite web | title=foo| url=http://www.site.com }} {{dead link|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}</ref>"
    ), r"subst converted within ref tags"
    assert (
        genfixes.fix_syntax(
            r"<ref>{{cite web | title=foo| url=http://www.site.com }} {{dead link|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}</ref>"
        )
        == r"<ref>{{cite web | title=foo| url=http://www.site.com }} {{dead link|date="
        + utc_month_year()
        + r"}}</ref>"
    )
    assert r"{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}" in genfixes.fix_syntax(
        r"* {{cite web | title=foo| url=http://www.site.com }} {{dead link|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    ), r"subst not converted when outside ref tags"
    assert (
        genfixes.fix_syntax(
            "<gallery>\r\n Foo.JPG |Foo great{{citation needed|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n</gallery>"
        )
        == "<gallery>\r\n Foo.JPG |Foo great{{citation needed|date="
        + utc_month_year()
        + "}}\r\n</gallery>"
    ), r"subst converted within gallery tags"


def test_fix_syntax_template_namespace() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"{{Template:foo}}") == r"{{foo}}"
    assert genfixes.fix_syntax(r"{{ Template:foo}}") == r"{{ foo}}"
    assert genfixes.fix_syntax(r"{{ template :foo}}") == r"{{ foo}}"
    assert genfixes.fix_syntax("{{\r\nTemplate:foo}}") == "{{\r\nfoo}}"
    assert genfixes.fix_syntax("{{Template:foo\r\n|bar=yes}}") == "{{foo\r\n|bar=yes}}"


def test_fix_syntax_template_whitespace() -> None:
    S = W.for_site(EN)
    nonbreakingspace = r" "
    templateCallWithNonBreakingSpace = r"{{Foo" + nonbreakingspace + r"one|1=yes}}"
    assert genfixes.fix_syntax(templateCallWithNonBreakingSpace) == r"{{Foo one|1=yes}}", (
        r"Unicode non-breaking space clean from template name"
    )
    nonbreakingspace = r"　"
    templateCallWithNonBreakingSpace = r"{{Foo" + nonbreakingspace + r"one|1=yes}}"
    assert genfixes.fix_syntax(templateCallWithNonBreakingSpace) == r"{{Foo one|1=yes}}", (
        r"Unicode IDEOGRAPHIC SPACE clean from template name"
    )
    assert genfixes.fix_syntax("{{foo \r\nbar|val=one}}") == r"{{foo bar|val=one}}"
    assert genfixes.fix_syntax("{{Foo \r\nbar|val=one}}") == r"{{Foo bar|val=one}}"
    assert (
        genfixes.fix_syntax("{{Foo \r\nbar|val=one}} {{\r\n |val2=a}}")
        == "{{Foo bar|val=one}} {{\r\n |val2=a}}"
    ), r"Unnamed template handling"
    tableInTemplate = '{{Foo | {{\r\n{| class="standard sortable" style=text-align:right\r\n!N\r\n|-\r\n|0\r\n|}\r\n}}}}'
    assert genfixes.fix_syntax(tableInTemplate) == tableInTemplate, (
        r"Table in unnamed template handling"
    )


def test_fix_syntax_external_link_brackets() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"[http://example.com] site") == r"[http://example.com] site"
    assert genfixes.fix_syntax(r"[[http://example.com] site2") == r"[http://example.com] site2"
    assert genfixes.fix_syntax(r"[[[http://example.com] site3") == r"[http://example.com] site3"
    assert genfixes.fix_syntax(r"[http://example.com]] site4") == r"[http://example.com] site4"
    assert genfixes.fix_syntax(r"[[http://example.com]] site5") == r"[http://example.com] site5"
    assert genfixes.fix_syntax(r"[[[http://example.com]]] site6") == r"[http://example.com] site6"
    assert (
        genfixes.fix_syntax(genfixes.fix_link_whitespace(r"[[ http://example.com]] site7", r"Test"))
        == r"[http://example.com] site7"
    )
    assert (
        genfixes.fix_syntax("[[http://example.com\r\n* List 2")
        == "[http://example.com]\r\n* List 2"
    )
    assert genfixes.fix_syntax(r"[https://example.com]] site") == r"[https://example.com] site"
    assert genfixes.fix_syntax(r"[[https://example.com] site") == r"[https://example.com] site"
    assert genfixes.fix_syntax(r"<ref>[http://test.com}</ref>") == r"<ref>[http://test.com]</ref>"
    assert genfixes.fix_syntax(r"<ref>[http://test.com</ref>") == r"<ref>[http://test.com]</ref>"
    assert (
        genfixes.fix_syntax(r"<ref>[http://test.com foo" + "\r\n" + r"bar</ref>")
        == r"<ref>[http://test.com foo bar]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"{{cite web | url = http:http://test.com |title=a }}")
        == r"{{cite web | url = http://test.com |title=a }}"
    )
    assert genfixes.fix_syntax(r"* [http://www.site.com text)") == r"* [http://www.site.com text]"
    assert genfixes.fix_syntax(r"* [http://www.site.com text) ") == r"* [http://www.site.com text]"
    Correct = r"* [http://www.site.com text (here) there]"
    assert genfixes.fix_syntax(Correct) == Correct


def test_fix_syntax_external_links() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"[http://test.com]") == r"[http://test.com]", (
        r"do nothing if everything is OK"
    )
    assert genfixes.fix_syntax(r"[http://http://test.com]") == r"[http://test.com]", r"double http"
    assert genfixes.fix_syntax(r"[http:// http://test.com]") == r"[http://test.com]", r"double http"
    assert genfixes.fix_syntax(r"[http:// www.test.com]") == r"[http://www.test.com]", (
        r"http www spacing"
    )
    assert genfixes.fix_syntax(r"[https:// www.test.com]") == r"[https://www.test.com]", (
        r"https www spacing"
    )
    assert genfixes.fix_syntax(r"[http%3A//www.test.com]") == r"[http://www.test.com]", (
        r"http colon encoding"
    )
    assert genfixes.fix_syntax(r"[https%3A//www.test.com]") == r"[https://www.test.com]", (
        r"https colon encoding"
    )
    assert genfixes.fix_syntax(r"[http:http://test.com]") == r"[http://test.com]", (
        r"double http with first lacking slashes"
    )
    assert genfixes.fix_syntax(r"[http://http://http://test.com]") == r"[http://test.com]", (
        r"more than two"
    )
    assert genfixes.fix_syntax(r"[https://https://test.com]") == r"[https://test.com]", (
        r"double https"
    )
    assert genfixes.fix_syntax(r"[ftp://ftp://test.com]") == r"[ftp://test.com]", r"double ftp"
    assert genfixes.fix_syntax(r"[ftp://ftp://ftp://test.com]") == r"[ftp://test.com]", (
        r"triple ftp"
    )
    assert genfixes.fix_syntax(r"{{url|http://http://test.com}}") == r"{{url|http://test.com}}", (
        r"double http inside url template"
    )
    assert (
        genfixes.fix_syntax(r"{{official website|http://http://test.com}}")
        == r"{{official website|http://test.com}}"
    ), r"double http inside official website template"
    assert (
        genfixes.fix_syntax(r"{{foo|http://http://test.com}}") == r"{{foo|http://http://test.com}}"
    ), r"no change in a random template"
    assert genfixes.fix_syntax(r"[[Image:http://test.com/a.png]]") == r"[http://test.com/a.png]", (
        r"Image http 1"
    )
    assert genfixes.fix_syntax(r"[Image:http://test.com/a.png]") == r"[http://test.com/a.png]", (
        r"Image http 2"
    )
    assert genfixes.fix_syntax(r"[https:http://test.com]") == r"[https://test.com]", (
        r"https and http"
    )


def test_test_fix_syntax_disambig_cat() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"Foo [[Category:Disambiguation pages]]") == r"Foo {{Disambiguation}}"
    ), r"Cat to template"
    assert (
        genfixes.fix_syntax("Foo {{Disambiguation}}\r\n[[Category:Disambiguation pages]]")
        == r"Foo {{Disambiguation}}"
    ), r"Remove cat when template also present"


def test_test_fix_syntax_remove_empty_tags() -> None:
    S = W.for_site(EN)
    assert len(genfixes.fix_syntax(r"<gallery></gallery>")) == 0
    assert len(genfixes.fix_syntax("<gallery>\r\n</gallery>")) == 0
    assert len(genfixes.fix_syntax(r"<gallery>   </gallery>")) == 0
    assert len(genfixes.fix_syntax(r"< Gallery >   </gallery>")) == 0
    assert len(genfixes.fix_syntax(r"< GALLERY >   </gallery>")) == 0
    assert len(genfixes.fix_syntax(r"<gallery mode=a></gallery>")) == 0
    assert len(genfixes.fix_syntax(r"<gallery mode=a foo=b></gallery>")) == 0
    assert len(genfixes.fix_syntax(r"<blockquote mode=a foo=b></blockquote>")) == 0
    assert len(genfixes.fix_syntax(r"<center mode=a foo=b></center>")) == 0
    assert len(genfixes.fix_syntax(r"<sup mode=a foo=b></sup>")) == 0
    assert len(genfixes.fix_syntax(r"<sub mode=a foo=b></sub>")) == 0
    assert len(genfixes.fix_syntax(r"<small>   </small>")) == 0
    assert len(genfixes.fix_syntax(r"<includeonly>   </includeonly>")) == 0
    assert len(genfixes.fix_syntax(r"<noinclude>   </noinclude>")) == 0
    assert len(genfixes.fix_syntax(r"<nowiki>   </nowiki>")) == 0
    Gallery = r"<gallery>Image1.jpeg</gallery>"
    assert genfixes.fix_syntax(Gallery) == Gallery
    assert (
        len(genfixes.fix_syntax(r"<gallery> <gallery><gallery>   </gallery></gallery></gallery>"))
        == 0
    ), r"Cleans nested empty gallery tags"
    assert len(genfixes.fix_syntax(r"<center></center>")) == 0
    assert len(genfixes.fix_syntax(r"<gallery> <center></center> </gallery>")) == 0
    assert len(genfixes.fix_syntax(r"<blockquote></blockquote>")) == 0
    assert len(genfixes.fix_syntax(r"<sup></sup>")) == 0
    assert len(genfixes.fix_syntax(r"<sub></sub>")) == 0
    assert (
        genfixes.fix_syntax(r"[[hello]] <sub></sub>and<sub></sub> [[bye]]<sub></sub>")
        == r"[[hello]] and [[bye]]"
    )


def test_fix_syntax_html_tags() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<b>foo</b> bar") == r"'''foo''' bar"
    assert genfixes.fix_syntax(r"<B>foo</B> bar") == r"'''foo''' bar"
    assert genfixes.fix_syntax(r"< b >foo</b> bar") == r"'''foo''' bar"
    assert genfixes.fix_syntax(r"<b>foo< /b > bar") == r"'''foo''' bar"
    assert genfixes.fix_syntax(r"<b>foo<b> bar") == r"<b>foo<b> bar"
    assert genfixes.fix_syntax(r"<b>foo</b><b>bar</b>") == r"'''foobar'''"
    assert genfixes.fix_syntax(r"<i>foo</i> bar") == r"''foo'' bar"
    assert genfixes.fix_syntax(r"< i >foo</i> bar") == r"''foo'' bar"
    assert genfixes.fix_syntax(r"< i >foo< / i   > bar") == r"''foo'' bar"
    assert genfixes.fix_syntax(r"<i>foo< /i > bar") == r"''foo'' bar"
    assert genfixes.fix_syntax(r"<i>foo<i /> bar") == r"''foo'' bar"
    assert genfixes.fix_syntax(r"<i>foo<i\> bar") == r"''foo'' bar"
    assert genfixes.fix_syntax(r"<i>foo<i> bar") == r"<i>foo<i> bar"
    assert genfixes.fix_syntax(r"<i>foo</i><i>bar</i>") == r"''foobar''"
    assert genfixes.fix_syntax(r"<i>foo<i/><i>bar</i>") == r"''foobar''"
    assert genfixes.fix_syntax(r"<b><i>foo</i></b> bar") == r"'''''foo''''' bar"
    EmTemplate = r"{{em|foo}}"
    assert genfixes.fix_syntax(EmTemplate) == EmTemplate


def test_fix_syntax_strike() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<strike>hello</strike>") == r"<s>hello</s>"


def test_extra_bracket_in_external_link() -> None:
    S = W.for_site(EN)
    valid = r"now [http://www.site.com a [[a]] site] was"
    assert genfixes.fix_syntax(valid) == valid
    assert (
        genfixes.fix_syntax(r"now [http://www.site.com a b site]] was")
        == r"now [http://www.site.com a b site] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[http://www.site.com a c site] was")
        == r"now [http://www.site.com a c site] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[http://www.site.com a d3 site]] was")
        == r"now [http://www.site.com a d3 site] was"
    )
    assert (
        genfixes.fix_syntax(
            r"now [[Image:Fred1211212.JPG| here [http://www.site.com a [[e]] site]]] was"
        )
        == r"now [[Image:Fred1211212.JPG| here [http://www.site.com a [[e]] site]]] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[Image:Fred12.JPG| here [[http://www.site.com a g site]]] was")
        == r"now [[Image:Fred12.JPG| here [http://www.site.com a g site]]] was"
    )
    assert (
        genfixes.fix_syntax(r"now [http://www.site.com a [[b]] site]] was")
        == r"now [http://www.site.com a [[b]] site] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[http://www.site.com a [[c]] site] was")
        == r"now [http://www.site.com a [[c]] site] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[http://www.site.com a [[d]] or [[d2]] site]] was")
        == r"now [http://www.site.com a [[d]] or [[d2]] site] was"
    )
    assert (
        genfixes.fix_syntax(
            r"now [[Image:Fred12.JPG| here [http://www.site.com a [[f]] site]]]] was"
        )
        == r"now [[Image:Fred12.JPG| here [http://www.site.com a [[f]] site]]] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[Image:Fred12.JPG| here [http://www.site.com a g site]]]] was")
        == r"now [[Image:Fred12.JPG| here [http://www.site.com a g site]]] was"
    )
    assert (
        genfixes.fix_syntax(r"now [[Image:Fred12.JPG| here [[http://www.site.com a g site]]]] was")
        == r"now [[Image:Fred12.JPG| here [http://www.site.com a g site]]] was"
    )
    assert (
        genfixes.fix_syntax(r"[[Image:foo.jpg|Some [[http://some_crap.com]]]]")
        == r"[[Image:foo.jpg|Some [http://some_crap.com]]]"
    )
    assert (
        genfixes.fix_syntax(r"[[File:foo.jpg|Some [[https://some_crap.com]]]]")
        == r"[[File:foo.jpg|Some [https://some_crap.com]]]"
    )


def test_cite_template_with_square_brackets_tests() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(
            r"<ref name=Test>[[cite web|url=http://foo.com|accessdate=2015-07-07]]</ref>"
        )
        == r"<ref name=Test>{{cite web|url=http://foo.com|accessdate=2015-07-07}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>[[cite web|url=http://foo.com|accessdate=2015-07-07]]</ref>")
        == r"<ref>{{cite web|url=http://foo.com|accessdate=2015-07-07}}</ref>"
    )
    assert (
        genfixes.fix_syntax(
            r"<ref>[[cite web | url = http://collection.whitney.org/object/11823 | accessdate: 25 June 2015 | publisher = [[Whitney Museum of American Art]] | title = Houston, Texas, 1977 from Women are Better than Men]].</ref>"
        )
        == r"<ref>[[cite web | url = http://collection.whitney.org/object/11823 | accessdate: 25 June 2015 | publisher = [[Whitney Museum of American Art]] | title = Houston, Texas, 1977 from Women are Better than Men]].</ref>"
    )


def test_square_brackets_in_external_links_tests() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some stuff [great]]")
        == r"[http://www.site.com some stuff &#91;great&#93;]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some stuff [great] free]")
        == r"[http://www.site.com some stuff &#91;great&#93; free]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some stuff [great] free [here]]")
        == r"[http://www.site.com some stuff &#91;great&#93; free &#91;here&#93;]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some stuff [great] free [[now]]]")
        == r"[http://www.site.com some stuff &#91;great&#93; free [[now]]]"
    )
    assert (
        genfixes.fix_syntax(
            r"*This: [http://www.privacyinternational.org/article.shtml?cmd[347]=x-347-359656&als[theme]=AT+Law+and+Policy Terrorism Profile - Uganda] Privacy International"
        )
        == r"*This: [http://www.privacyinternational.org/article.shtml?cmd&#91;347&#93;=x-347-359656&als&#91;theme&#93;=AT+Law+and+Policy Terrorism Profile - Uganda] Privacy International"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some great stuff]")
        == r"[http://www.site.com some great stuff]"
    )
    assert (
        genfixes.fix_syntax(r"now [http://www.site.com some great stuff] here")
        == r"now [http://www.site.com some great stuff] here"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some [[great]] stuff]")
        == r"[http://www.site.com some [[great]] stuff]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some great [[stuff]]]")
        == r"[http://www.site.com some great [[stuff]]]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com [[some great stuff|loads of stuff]]]")
        == r"[http://www.site.com [[some great stuff|loads of stuff]]]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com [[some great stuff|loads of stuff]] here]")
        == r"[http://www.site.com [[some great stuff|loads of stuff]] here]"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com some </ref> [stuff] here]")
        == r"[http://www.site.com some </ref> [stuff] here]"
    )
    assert (
        genfixes.fix_syntax(
            "* [http://www.site.com some stuff\r\n* [http://site2.com stuff 2]\r\nOther\r\n]"
        )
        == "* [http://www.site.com some stuff\r\n* [http://site2.com stuff 2]\r\nOther\r\n]"
    )


def test_fix_deadlink_outside_ref() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"<ref>foo</ref> {{dead link|date=July 2014}} boo")
        == r"<ref>foo {{dead link|date=July 2014}}</ref> boo"
    ), r"only {{dead link}} taken inside ref"
    assert (
        genfixes.fix_syntax(r"<ref>foo</ref> {{Dead link | date=July 2014 }} boo")
        == r"<ref>foo {{Dead link | date=July 2014 }}</ref> boo"
    ), r"only {{dead link}} taken inside ref"
    assert (
        genfixes.fix_syntax(r"<ref>foo</ref> {{Dead link|date=July 2014}} boo")
        == r"<ref>foo {{Dead link|date=July 2014}}</ref> boo"
    ), r"only {{dead link}} taken inside ref"
    assert (
        genfixes.fix_syntax(
            r"<ref>{{cite web | url=http://www.site.com/article100.html | title=Foo }}</ref> {{dead link|date=July 2014}}"
        )
        == r"<ref>{{cite web | url=http://www.site.com/article100.html | title=Foo }} {{dead link|date=July 2014}}</ref>"
    ), r"{{dead link}} taken inside ref"


def test_fix_images_br() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"[[File:Foo.png|description<br>]]") == r"[[File:Foo.png|description]]"
    )
    assert (
        genfixes.fix_syntax(r"[[File:Foo.png|description<br >]]") == r"[[File:Foo.png|description]]"
    )
    assert (
        genfixes.fix_syntax(r"[[File:Foo.png|description<br/>]]") == r"[[File:Foo.png|description]]"
    )
    assert (
        genfixes.fix_syntax(r"[[File:Foo.png|description<BR>]]") == r"[[File:Foo.png|description]]"
    )
    assert (
        genfixes.fix_syntax(r"[[File:Foo.png|description<br />]]")
        == r"[[File:Foo.png|description]]"
    )
    assert (
        genfixes.fix_syntax("[[File:Foo.png|description<br />\r\n]]")
        == r"[[File:Foo.png|description]]"
    )
    nochange1 = r"[[File:Foo.png|description<br>here]]"
    assert genfixes.fix_syntax(nochange1) == nochange1


def test_test_fix_image_self_links() -> None:
    S = W.for_site(EN)
    p = genfixes.Parsers()
    assert (
        p.fix_image_self_links(r"[[File:Foo.jpg|link=http://en.wikipedia.org/wiki/File:Foo.jpg]]")
        == r"[[File:Foo.jpg]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Foo_bar.jpg|link=http://en.wikipedia.org/wiki/File:Foo_bar.jpg]]"
        )
        == r"[[File:Foo_bar.jpg]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Foo bar.jpg|link=http://en.wikipedia.org/wiki/File:Foo_bar.jpg]]"
        )
        == r"[[File:Foo bar.jpg]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Foo_bar.jpg|link=http://en.wikipedia.org/wiki/File:Foo_bar.jpg|thumb]]"
        )
        == r"[[File:Foo_bar.jpg|thumb]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Foo_bar.jpg|link=http://en.wikipedia.org/wiki/File:Foo_bar.jpg|thumb|alt=hello]]"
        )
        == r"[[File:Foo_bar.jpg|thumb|alt=hello]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Foo_bar.jpg|link=http://en.wikipedia.org/wiki/File:Foo_bar.jpg|thumb|alt=hello {{world}}]]"
        )
        == r"[[File:Foo_bar.jpg|thumb|alt=hello {{world}}]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Foo_bar.jpg|link=http://en.wikipedia.org/wiki/File:Foo_bar.jpg|thumb|desc with [[link]]]]"
        )
        == r"[[File:Foo_bar.jpg|thumb|desc with [[link]]]]"
    )
    assert (
        p.fix_image_self_links(
            r"[[File:Bonasone,_Bologna_1555.jpg|link=https://en.wikipedia.org/wiki/File:Bonasone,_Bologna_1555.jpg|thumb|Socrates 1555.]]"
        )
        == r"[[File:Bonasone,_Bologna_1555.jpg|thumb|Socrates 1555.]]"
    )
    nochange1 = r"[[File:Foo.pdf|link=http://en.wikipedia.org/wiki/File:Foo.pdf?page=1]]"
    assert p.fix_image_self_links(nochange1) == nochange1, (
        r"No change to link with extra URL parameters"
    )


def test_fix_syntax_defaultsort() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax("{{DEFAULTSORT:\r\nFoo}}") == r"{{DEFAULTSORT:Foo}}"
    assert genfixes.fix_syntax(r"{{DEFAULTSORT: Foo }}") == r"{{DEFAULTSORT:Foo}}"
    assert genfixes.fix_syntax("{{DEFAULTSORT:Foo\r\n}}") == r"{{DEFAULTSORT:Foo}}"
    assert genfixes.fix_syntax(r"{{DEFAULTSORT:Jones,Andy}}") == r"{{DEFAULTSORT:Jones, Andy}}", (
        r"Add space after comma"
    )
    assert genfixes.fix_syntax(r"{{DEFAULTSORT:Jones,}}") == r"{{DEFAULTSORT:Jones,}}", (
        r"No change: comma at end"
    )


def test_fix_syntax_font_tags() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<font>hello</font>") == r"hello"
    assert genfixes.fix_syntax(r"<font>hello</FONT>") == r"hello"
    assert genfixes.fix_syntax("<font>hello\r\nworld</font>") == "hello\r\nworld"
    assert genfixes.fix_syntax(r"<font name=ab>hello</font>") == r"<font name=ab>hello</font>"


def test_fix_syntax_http_format() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"<ref>http//www.site.com</ref>") == r"<ref>http://www.site.com</ref>"
    ), r"missing colon"
    assert (
        genfixes.fix_syntax(r"<ref>https//www.site.com</ref>") == r"<ref>https://www.site.com</ref>"
    ), r"missing colon"
    assert (
        genfixes.fix_syntax(r"<ref>http:://www.site.com</ref>") == r"<ref>http://www.site.com</ref>"
    ), r"double colon"
    assert (
        genfixes.fix_syntax(r"<ref>http:www.site.com</ref>") == r"<ref>http://www.site.com</ref>"
    ), r"missing slashes"
    assert (
        genfixes.fix_syntax(r"<ref>http:///www.site.com</ref>") == r"<ref>http://www.site.com</ref>"
    ), r"triple slashes"
    assert (
        genfixes.fix_syntax(r"<ref>http:////www.site.com</ref>")
        == r"<ref>http://www.site.com</ref>"
    ), r"four slashes"
    assert genfixes.fix_syntax(r"at http//www.site.com") == r"at http://www.site.com"
    assert (
        genfixes.fix_syntax(r"<ref>[http:/www.site.com a website]</ref>")
        == r"<ref>[http://www.site.com a website]</ref>"
    ), r"missing a slash"
    assert (
        genfixes.fix_syntax(r"*[http//www.site.com a website]")
        == r"*[http://www.site.com a website]"
    )
    assert genfixes.fix_syntax(r"|url=http//www.site.com") == r"|url=http://www.site.com"
    assert genfixes.fix_syntax(r"|url = http:/www.site.com") == r"|url = http://www.site.com"
    assert genfixes.fix_syntax(r"[http/www.site.com]") == r"[http://www.site.com]"
    bug1 = r"now http://members.bib-arch.org/nph-proxy.pl/000000A/http/www.basarchive.org/bswbSearch was"
    assert genfixes.fix_syntax(bug1) == bug1
    bug2 = r"now http://sunsite.utk.edu/math_archives/.http/contests/ was"
    assert genfixes.fix_syntax(bug2) == bug2
    assert genfixes.fix_syntax(r"the HTTP/0.9 was") == r"the HTTP/0.9 was"
    assert genfixes.fix_syntax(r"the HTTP/1.0 was") == r"the HTTP/1.0 was"
    assert genfixes.fix_syntax(r"the HTTP/1.1 was") == r"the HTTP/1.1 was"
    assert genfixes.fix_syntax(r"the HTTP/1.2 was") == r"the HTTP/1.2 was"
    a = r"the HTTP/FTP was"
    assert genfixes.fix_syntax(a) == a
    assert genfixes.fix_syntax(r"the HTTP/1.2 protocol") == r"the HTTP/1.2 protocol"
    assert (
        genfixes.fix_syntax(r"<ref>[http://cdiac.esd.ornl.gov/ftp/cdiac74/a.pdf chapter 5]</ref>")
        == r"<ref>[http://cdiac.esd.ornl.gov/ftp/cdiac74/a.pdf chapter 5]</ref>"
    )


def test_fix_syntax_magic_words() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"{{Fullpagename|Foo}}") == r"{{FULLPAGENAME:Foo}}"


def test_fix_syntax_magic_words_behaviour_switches() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"__ToC__") == r"__TOC__"
    assert genfixes.fix_syntax(r"__toC__") == r"__TOC__"
    assert genfixes.fix_syntax(r"__TOC__") == r"__TOC__"
    assert genfixes.fix_syntax(r"__NoToC__") == r"__NOTOC__"


def test_fix_syntax_pipes_in_external_links() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"[http://www.site.com|''my cool site'']")
        == r"[http://www.site.com ''my cool site'']"
    )
    assert (
        genfixes.fix_syntax(r"[http://www.site.com/here/there.html|''my cool site'']")
        == r"[http://www.site.com/here/there.html ''my cool site'']"
    )
    assert (
        genfixes.fix_syntax(
            r'port [[http://www.atoc.org/general/ConnectingCommunitiesReport_S10.pdf |"Connecting Communities - Expanding Access to the Rail Network"]] consid'
        )
        == r'port [http://www.atoc.org/general/ConnectingCommunitiesReport_S10.pdf "Connecting Communities - Expanding Access to the Rail Network"] consid'
    )
    nochange1 = r"[http://www.site.com|''my cool site''"
    nochange2 = "{{Infobox Singapore School\r\n| name = Yuan Ching Secondary School\r\n| established = 1978\r\n| city/town = [[Jurong]]\r\n| enrolment = over 1,300\r\n| homepage = [http://schools.moe.edu.sg/ycss/\r\n| border_color = #330066\r\n| uniform_color = #66CCFF\r\n}}"
    assert genfixes.fix_syntax(nochange1) == nochange1
    assert genfixes.fix_syntax(nochange2) == nochange2


def test_fix_unbalanced_brackets_chinese_brackets() -> None:
    S = W.for_site(EN)
    CB = r"now （there) was"
    S = set_lang(r"fr")
    assert genfixes.cite_template_dates(CB) == CB
    S = set_lang(r"en")
    assert genfixes.fix_syntax(CB) == r"now (there) was"
    CB2 = r"now （there） was"
    assert genfixes.fix_syntax(CB2) == CB2, r"No change when brackets are balanced"


def test_fix_unbalanced_brackets_cite_templates() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b}]</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b))</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref> {{cite web|url=a|title=b} </ref>")
        == r"<ref> {{cite web|url=a|title=b}} </ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=Fred>{{cite web|url=a|title=b}</ref>")
        == r"<ref name=Fred>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">{{cite web|url=a|title=b}</ref>')
        == r'<ref name="Fred">{{cite web|url=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>{cite web|url=a|title=b}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref> {cite web|url=a|title=b}} </ref>")
        == r"<ref> {{cite web|url=a|title=b}} </ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=Fred>{Cite web|url=a|title=b}}</ref>")
        == r"<ref name=Fred>{{Cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">{cite web|url=a|title=b}}</ref>')
        == r'<ref name="Fred">{{cite web|url=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>{citation|url=a|title=b}}</ref>")
        == r"<ref>{{citation|url=a|title=b}}</ref>"
    )
    assert genfixes.fix_syntax(r"<ref> {Citation|title=}}") == r"<ref> {{Citation|title=}}"
    assert genfixes.fix_syntax(r"<ref> {cite web|title=}}") == r"<ref> {{cite web|title=}}"
    assert genfixes.fix_syntax(r"* {Citation|title=}}") == r"* {{Citation|title=}}"
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b}}}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref> {{cite web|url=a|title=b}}}} </ref>")
        == r"<ref> {{cite web|url=a|title=b}} </ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=Fred>{{Cite web|url=a|title=b}}}}</ref>")
        == r"<ref name=Fred>{{Cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">{{cite web|url=a|title=b}}}}</ref>')
        == r'<ref name="Fred">{{cite web|url=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{citation|url=a|title=b}}}}</ref>")
        == r"<ref>{{citation|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b {{rp}}}}</ref>")
        == r"<ref>{{cite web|url=a|title=b {{rp}}}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{[cite web|url=a|title=b}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref> {[cite web|url=a|title=b}} </ref>")
        == r"<ref> {{cite web|url=a|title=b}} </ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=Fred>{[Cite web|url=a|title=b}}</ref>")
        == r"<ref name=Fred>{{Cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">{[cite web|url=a|title=b}}</ref>')
        == r'<ref name="Fred">{{cite web|url=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>{[citation|url=a|title=b}}</ref>")
        == r"<ref>{{citation|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b{}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref> {{cite web|url=a|title=b}] </ref>")
        == r"<ref> {{cite web|url=a|title=b}} </ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=Fred>{{Cite web|url=a|title=[[b]]}</ref>")
        == r"<ref name=Fred>{{Cite web|url=a|title=[[b]]}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">{{cite web|url=a|title=b{}</ref>')
        == r'<ref name="Fred">{{cite web|url=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{citation|url=a|title=b}]</ref>")
        == r"<ref>{{citation|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>cite web|url=a|title=b}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Smith">cite web|url=a|title=b}}</ref>')
        == r'<ref name="Smith">{{cite web|url=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax('<ref name="Smith">cite web|\r\nurl=a|title=b}}</ref>')
        == '<ref name="Smith">{{cite web|\r\nurl=a|title=b}}</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>cite book|url=a|title=b}}</ref>")
        == r"<ref>{{cite book|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>Citation|url=a|title=b}}</ref>")
        == r"<ref>{{Citation|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>((cite web|url=a|title=b}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b}}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    ), r"fixes cite ending in three closing braces"
    assert (
        genfixes.fix_syntax("<ref>{{cite web|url=a|title=b}}}\r\n\t\t\t</ref>")
        == "<ref>{{cite web|url=a|title=b}}\r\n\t\t\t</ref>"
    ), r"fixes cite ending in three closing braces, newline before ref end"
    assert (
        genfixes.fix_syntax(r"<ref>{{{cite web|url=a|title=b}}</ref>")
        == r"<ref>{{cite web|url=a|title=b}}</ref>"
    ), r"fixes cite starting in three opening braces"
    assert (
        genfixes.fix_syntax(r'<ref name="foo">{{{cite web|url=a|title=b}}</ref>')
        == r'<ref name="foo">{{cite web|url=a|title=b}}</ref>'
    ), r"fixes cite starting in three opening braces"
    CiteDeadLink = r"<ref>{{cite web|url=a|title=b}} {{dead link|date=May 2011}}</ref>"
    assert genfixes.fix_syntax(CiteDeadLink) == CiteDeadLink
    CiteDeadLink = r"<ref>{{cite web|url=a|title=b {{dead link|date=May 2011}}}}</ref>"
    assert genfixes.fix_syntax(CiteDeadLink) == CiteDeadLink
    citeReprint = r"{{cite book |last=S |first=G |title=Freedom of the press {reprint) |publisher=New York, Da Capo Press |year=1971 }}"
    assert genfixes.fix_syntax(citeReprint) == citeReprint.replace(r"{r", r"(r")
    citeReprint = r"{{cite book |last=S |first=G |title=Freedom of the press (in three volumes} |publisher=New York, Da Capo Press |year=1971 }}"
    assert genfixes.fix_syntax(citeReprint) == citeReprint.replace(r"s}", r"s)")
    citeReprint = "* {{cite book |last=S |first=G |title=Freedom of the press {reprint) |publisher=New York, Da Capo Press |year=1971 }}\r\n* {{cite book |last=S |first=G |title=Freedom of the press (reprint} |publisher=New York, Da Capo Press |year=1971 }}"
    assert genfixes.fix_syntax(citeReprint) == citeReprint.replace(r"t}", r"t)").replace(
        r"{r", r"(r"
    )


def test_fix_unbalanced_brackets_general() -> None:
    S = W.for_site(EN)
    CorrectCat = "[[Category:Foo]]\r\n[[Category:Foo2]]"
    assert genfixes.fix_syntax("[[Category:Foo\r\n[[Category:Foo2]]") == CorrectCat, (
        r"closes unclosed cats"
    )
    assert genfixes.fix_syntax(CorrectCat) == CorrectCat
    assert genfixes.fix_syntax("[[es:Foo\r\n[[fr:Foo2]]") == "[[es:Foo]]\r\n[[fr:Foo2]]", (
        r"closes unclosed interwikis"
    )
    CorrectFileLink = r"[[File:foo.jpeg|eflkjfdslkj]]"
    assert genfixes.fix_syntax(r"{{File:foo.jpeg|eflkjfdslkj]]") == CorrectFileLink
    assert genfixes.fix_syntax(CorrectFileLink) == CorrectFileLink
    CorrectFileLink2 = r"[[Image:foo.jpeg|eflkjfdslkj]]"
    assert genfixes.fix_syntax(r"{{Image:foo.jpeg|eflkjfdslkj]]") == CorrectFileLink2
    assert genfixes.fix_syntax(CorrectFileLink2) == CorrectFileLink2
    CorrectFileLink3 = r"[[file:foo.jpeg|eflkjfdslkj]]"
    assert genfixes.fix_syntax(r"{{file:foo.jpeg|eflkjfdslkj]]") == CorrectFileLink3
    assert genfixes.fix_syntax(CorrectFileLink3) == CorrectFileLink3
    NoFix1 = "==Charact==\r\n[[Image:X.jpg|thumb\r\n|alt=\r\n|xx.]]\r\n\r\nJapanese classification systemJapanese classification systemJapanese classification systemJapanese classification systemJapanese classification systemJapanese classification systemJapanese classification system\r\n\r\n<gallery>\r\nImage:X.JPG|Japanese classification systemJapanese classification systemJapanese classification system]]\r\n</gallery>"
    assert genfixes.fix_syntax(NoFix1) == NoFix1
    assert genfixes.fix_syntax(r"[ [Foo]]") == r"[[Foo]]", r"fixes link spacing"
    assert genfixes.fix_syntax(r"[[Foo]]]]") == r"[[Foo]]", r"fixes excess link bracketss"
    assert genfixes.fix_syntax(r"[[Foo],]") == r"[[Foo]],", r"fixes links broken by punctuation"
    assert genfixes.fix_syntax(r"[[Foo].]") == r"[[Foo]].", r"fixes links broken by punctuation"
    assert genfixes.fix_syntax(r"[[Foo]:]") == r"[[Foo]]:", r"fixes links broken by punctuation"
    assert genfixes.fix_syntax(r"[[Foo] ] bar") == r"[[Foo]]  bar", (
        r"fixes links broken by punctuation"
    )
    assert genfixes.fix_syntax(r"[[Foo]'']") == r"[[Foo]]''", r"fixes links broken by punctuation"
    assert (
        genfixes.fix_link_whitespace(
            genfixes.fix_syntax(r"[panka  Smith]] (Local national)"), r"Test"
        )
        == r"[[panka Smith]] (Local national)"
    ), r"bracket and whitespace fix in one"
    Football = "{{Infobox football biography\r\n| playername     = D\r\n| image          = \r\n| dateofdeath    = 1940 {aged 57)<ref name=A/>\r\n| cityofdeath    = [[S]]\r\n| years3         = 1911–19?? }}"
    assert genfixes.fix_syntax(Football) == Football.replace(r"{aged", r"(aged")
    assert genfixes.fix_syntax("{{DEFAULTSORT:Foo\r\n") == r"{{DEFAULTSORT:Foo}}", (
        r"fixes DEFAULTSORT ending"
    )
    assert (
        genfixes.fix_syntax(r"{{foo|par=[[Bar[[|par2=Bar2}}") == r"{{foo|par=[[Bar]]|par2=Bar2}}"
    ), r"reversed brackets"
    assert genfixes.fix_syntax(r"{{foo|par=[{Bar]]|par2=Bar2}}") == r"{{foo|par=[[Bar]]|par2=Bar2}}"
    Unfixable1 = r"Ruth singled and Meusel [[bunt (baseball)|ed him over, but Ruth split his pants sliding into second, [[announcer|Radio announcer]] [[Graham McNamee]]"
    assert genfixes.fix_syntax(Unfixable1) == Unfixable1
    assert genfixes.fix_syntax(r"{{DEFAULTSORT:Foo))") == r"{{DEFAULTSORT:Foo}}", (
        r"fixes Template )) ending"
    )
    Unfixable2 = "Ruth [[File:One.JPEG|A [http://www.site.com/a]]]\r\nXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\r\nXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\r\nXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\r\nXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\r\nNow [[Fred was"
    assert genfixes.fix_syntax(Unfixable2) == Unfixable2
    assert (
        genfixes.fix_syntax(Unfixable2 + "\r\n==Heading==\r\nNow [[A],] was.")
        == Unfixable2 + "\r\n==Heading==\r\nNow [[A]], was."
    )
    MI = "{{Multiple issues|\r\n{{autobiography|date=April 2015}}\r\n{{notability|Biographies|date=April 2015}}\r\n"
    Infobox = "{{Infobox foo\r\n|a1=a\r\n|a2=b\r\n}}"
    assert genfixes.fix_syntax(MI) == MI + r"}}"
    assert genfixes.fix_syntax(MI + "\r\n" + Infobox) == MI + r"}}" + "\r\n\r\n" + Infobox
    BrokenWikiLinkInExternalLink = r"[http://a.site.edu/text/ [[ABC] {{wayback|url=http://a.site.edu/text/ |date=20100522200011 }}] Words here]"
    assert genfixes.fix_syntax(BrokenWikiLinkInExternalLink) == BrokenWikiLinkInExternalLink, (
        r"No change when broken wikilink in external link"
    )


def test_fix_unbalanced_brackets_math_set_notation() -> None:
    S = W.for_site(EN)
    MathSet1 = r"{[0], [1], [2]}"
    Foo = r"Foo { ..."
    assert genfixes.fix_syntax(Foo + MathSet1) == Foo + MathSet1


def test_fix_unbalanced_brackets_ref() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"now <ref>>foo</ref>") == r"now <ref>foo</ref>"
    assert (
        genfixes.fix_syntax(r"now <ref>[http://foo.com/bar/ text here[</ref>")
        == r"now <ref>[http://foo.com/bar/ text here]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>]http://www.foo.com bar]</ref>")
        == r"<ref>[http://www.foo.com bar]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=A>]http://www.foo.com bar]</ref>")
        == r"<ref name=A>[http://www.foo.com bar]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>]http://www.foo.com bar] this one</ref>")
        == r"<ref>[http://www.foo.com bar] this one</ref>"
    )
    assert (
        genfixes.fix_syntax(r"1 November 1900<ref>{in lang|pl}} Some text</ref>")
        == r"1 November 1900<ref>{{in lang|pl}} Some text</ref>"
    ), r"Fix missing leading { in template at start of ref"


def test_test_cellpadding_typo() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r'now {| class="wikitable" celpadding=2')
        == r'now {| class="wikitable" cellpadding=2'
    )
    assert (
        genfixes.fix_syntax(r'now {| class="wikitable" cellpading=2')
        == r'now {| class="wikitable" cellpadding=2'
    )
    assert (
        genfixes.fix_syntax(r'now {| class="wikitable" Celpading=2')
        == r'now {| class="wikitable" cellpadding=2'
    )
    assert genfixes.fix_syntax(r"now the cellpading of the") == r"now the cellpading of the"
    assert (
        genfixes.fix_syntax(r'now {| class="wikitable" cellpadding=2')
        == r'now {| class="wikitable" cellpadding=2'
    )


def test_test_fix_obsolete_br_attributes() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<br clear=both />") == r"{{clear}}"
    assert genfixes.fix_syntax(r"<Br clear=both />") == r"{{clear}}"
    assert genfixes.fix_syntax(r'<br clear="both" />') == r"{{clear}}"
    assert genfixes.fix_syntax(r"<br clear=all />") == r"{{clear}}"
    assert genfixes.fix_syntax(r'<br clear="all" />') == r"{{clear}}"
    assert genfixes.fix_syntax(r"<br clear=left />") == r"{{clear|left}}"
    assert genfixes.fix_syntax(r'<br clear="left" />') == r"{{clear|left}}"
    assert genfixes.fix_syntax(r"<br clear=right />") == r"{{clear|right}}"
    assert genfixes.fix_syntax(r'<br clear="right" />') == r"{{clear|right}}"
    assert genfixes.fix_syntax(r'<br style="clear:both;" clear="all" />') == r"{{clear}}"
    assert genfixes.fix_syntax(r'<br style="clear:left;" clear="all" />') == r"{{clear|left}}"
    assert genfixes.fix_syntax(r'<br style="clear:right;" clear="all" />') == r"{{clear|right}}"
    assert genfixes.fix_syntax(r'<br style="clear:both;" />') == r"{{clear}}"
    assert genfixes.fix_syntax(r'<br style="clear:left;" />') == r"{{clear|left}}"
    assert genfixes.fix_syntax(r'<br style="clear:right;" />') == r"{{clear|right}}"
    assert genfixes.fix_syntax(r"<br style=clear:both; />") == r"{{clear}}"
    assert genfixes.fix_syntax(r"<br style=clear:left; />") == r"{{clear|left}}"
    assert genfixes.fix_syntax(r"<br style=clear:right; />") == r"{{clear|right}}"


def test_test_fix_syntax_unbalanced_brackets() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"<ref>{{http://www.site.com}}</ref>")
        == r"<ref>[http://www.site.com]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{http://www.site.com }}</ref>")
        == r"<ref>[http://www.site.com]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref>{{http://www.site.com cool site}}</ref>")
        == r"<ref>[http://www.site.com cool site]</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">{{http://www.site.com}}</ref>')
        == r'<ref name="Fred">[http://www.site.com]</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref> {{http://www.site.com}} </ref>")
        == r"<ref>[http://www.site.com]</ref>"
    )
    assert genfixes.fix_syntax(r"{[hello}}") == r"{{hello}}"
    assert genfixes.fix_syntax(r"[{hello}}") == r"{{hello}}"
    assert genfixes.fix_syntax(r"{hello}}") == r"{{hello}}"
    assert genfixes.fix_syntax(r"<ref>http://site.com]</ref>") == r"<ref>[http://site.com]</ref>"
    assert genfixes.fix_syntax(r"<ref>[http://site.com</ref>") == r"<ref>[http://site.com]</ref>"
    assert genfixes.fix_syntax(r"<REF>[http://site.com</ref>") == r"<REF>[http://site.com]</ref>"
    assert (
        genfixes.fix_syntax(r"<ref>Smith, 2004 http://site.com]</ref>")
        == r"<ref>[http://site.com Smith, 2004]</ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref> http://site.com] </ref>") == r"<ref> [http://site.com] </ref>"
    )
    assert (
        genfixes.fix_syntax(r"<ref name=Fred>http://site.com cool]</ref>")
        == r"<ref name=Fred>[http://site.com cool]</ref>"
    )
    assert (
        genfixes.fix_syntax(r'<ref name="Fred">http://site.com]</ref>')
        == r'<ref name="Fred">[http://site.com]</ref>'
    )
    assert (
        genfixes.fix_syntax(r"<ref>http://site.com great site-here]</ref>")
        == r"<ref>[http://site.com great site-here]</ref>"
    )
    assert (
        genfixes.fix_syntax(
            r"<ref>Antara News [http://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon</ref>"
        )
        == r"<ref>Antara News [http://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon]</ref>"
    )
    assert (
        genfixes.fix_syntax(
            r"<ref>Antara News [ftp://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon</ref>"
        )
        == r"<ref>Antara News [ftp://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon]</ref>"
    ), r"handles FTP protocol"
    assert (
        genfixes.fix_syntax(
            r"<ref name=Smith>Antara News [http://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon</ref>"
        )
        == r"<ref name=Smith>Antara News [http://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon]</ref>"
    )
    assert (
        genfixes.fix_syntax(
            r"<ref name=Smith>Antara News [http://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon]</ref>"
        )
        == r"<ref name=Smith>Antara News [http://www.antara.co.id/arc/2009/1/9/kri-lebanon/ KRI Lebanon]</ref>"
    )
    a = r"<ref>Smith and Jones, 2005, p46}}</ref>"
    assert genfixes.fix_syntax(a) == a
    assert (
        genfixes.fix_syntax(r"{{DEFAULTSORT:Astaire, Fred]}}") == r"{{DEFAULTSORT:Astaire, Fred}}"
    )
    assert (
        genfixes.fix_syntax(r"{{DEFAULTSORT:Astaire, Fred]]}}") == r"{{DEFAULTSORT:Astaire, Fred}}"
    )
    assert (
        genfixes.fix_syntax(r"{{DEFAULTSORT:Astaire, Fred]]]}}") == r"{{DEFAULTSORT:Astaire, Fred}}"
    )
    assert (
        genfixes.fix_syntax(r"{{DEFAULTSORT:Astaire, Fred[]}}") == r"{{DEFAULTSORT:Astaire, Fred}}"
    )
    assert (
        genfixes.fix_syntax(r"Great.{{fact|date=May 2008} Now")
        == r"Great.{{fact|date=May 2008}} Now"
    )
    assert (
        genfixes.fix_syntax(r"Great.{{fact|date=May 2008]} Now")
        == r"Great.{{fact|date=May 2008}} Now"
    )
    assert genfixes.fix_syntax(r"Great.{{foo|} Now") == r"Great.{{foo|} Now"
    assert genfixes.fix_syntax(r"Great (not really} now") == r"Great (not really) now"
    assert (
        genfixes.fix_syntax(r"# [[Herbert H. H. Fox]] ([[1934 - 1939]]}<ref>foo</ref>")
        == r"# [[Herbert H. H. Fox]] ([[1934 - 1939]])<ref>foo</ref>"
    )
    assert genfixes.fix_syntax(r"Great { but (not really} now") == r"Great { but (not really} now"
    assert genfixes.fix_syntax(r"Great (not really)} now") == r"Great (not really)} now"
    assert genfixes.fix_syntax(r"great (in 2001 | blah |} now") == r"great (in 2001 | blah |} now"
    cite1 = r"Great.<ref>{{cite web | url=http://www.site.com | title=abc } year=2009}}</ref>"
    assert (
        genfixes.fix_syntax(cite1)
        == r"Great.<ref>{{cite web | url=http://www.site.com | title=abc | year=2009}}</ref>"
    )
    cite1 = cite1.replace(r"cite web", r"vcite web")
    assert (
        genfixes.fix_syntax(cite1)
        == r"Great.<ref>{{vcite web | url=http://www.site.com | title=abc | year=2009}}</ref>"
    )
    assert genfixes.fix_syntax(r"then ((but often) for") == r"then (but often) for"
    assert genfixes.fix_syntax(r"then ((but often)) for") == r"then ((but often)) for"
    assert genfixes.fix_syntax(r"then ((but often)} for") == r"then ((but often)} for"
    assert genfixes.fix_syntax(r"then ((but often) for(") == r"then ((but often) for("
    assert (
        genfixes.fix_syntax(
            "# [[Daniel Sylvester Tuttle|Daniel S. Tuttle]], (1867 - 1887)\r\n# Ethelbert Talbot, (1887 - 1898),\r\n# James B. Funsten, (1899 - 1918)\r\n# Herman Page, (1919 - 1919}\r\n# Frank H. Touret, (1919 - 1924)\r\n# Herbert H. H. Fox, (1925 - 1926)\r\n# [[Middleton S. Barnwell]], (1926 - 1935)\r\n# Frederick B. Bartlett, (1935 - 1941)\r\n# Frak A. Rhea, (1942 - 1968)\r\n# Norman L. Foote, (1957 - 1972)\r\n# Hanford L. King, Jr., (1972 - 1981)\r\n# David B. Birney, IV, (1982 - 1989)\r\n# John S. Thornton. (1990 - 1998\r\n# Harry B. Bainbridge, III, (1998 - 2008)\r\n# Brian J. Thom  (2008 - Present)"
        )
        == "# [[Daniel Sylvester Tuttle|Daniel S. Tuttle]], (1867 - 1887)\r\n# Ethelbert Talbot, (1887 - 1898),\r\n# James B. Funsten, (1899 - 1918)\r\n# Herman Page, (1919 - 1919)\r\n# Frank H. Touret, (1919 - 1924)\r\n# Herbert H. H. Fox, (1925 - 1926)\r\n# [[Middleton S. Barnwell]], (1926 - 1935)\r\n# Frederick B. Bartlett, (1935 - 1941)\r\n# Frak A. Rhea, (1942 - 1968)\r\n# Norman L. Foote, (1957 - 1972)\r\n# Hanford L. King, Jr., (1972 - 1981)\r\n# David B. Birney, IV, (1982 - 1989)\r\n# John S. Thornton. (1990 - 1998\r\n# Harry B. Bainbridge, III, (1998 - 2008)\r\n# Brian J. Thom  (2008 - Present)"
    )
    assert (
        genfixes.fix_syntax(
            "The '''Zach Feuer Gallery''' is a [[contemporary art]] gallery located in [[Chelsea, Manhattan|Chelsea]], [[New York City|New York]].\r\n\r\n==History==\r\n\r\nThe Zach Feuer Gallery was founded in 2000 as the LFL Gallery, by Nick Lawrence, Russell LaMontagne and Zach Feuer.  It was originally located on a fourth floor space on 26th Street.    In 2002 the gallery moved to a first floor space on 24th Street, briefly sharing space with an art book gallery owned by one of the partners.  In 2004  Zach Feuer purchased the gallery from his partners and changed the gallery name to Zach Feuer Gallery.\r\n\r\nSome artists represented by Zach Feuer Gallery are [[Phoebe Washburn]], [[Jules de Balincourt]], [[Nathalie Djurberg]]], [[Justin Lieberman]], [[Stuart Hawkins]],  [[Johannes Vanderbeek]], [[Sister Corita Kent]], [[Tamy Ben Tor]], [[Anton Henning]], [[Dana Schutz]], and [[Mark Flood]].\r\n\r\n==External links==\r\n* [http://www.zachfeuer.com Zach Feuer Gallery] website\r\n\r\n{{coord missing|New York}}\r\n\r\n[[Category:Contemporary art galleries]]\r\n[[Category:2000 establishments]]\r\n[[Category:Art galleries in Manhattan]]"
        )
        == "The '''Zach Feuer Gallery''' is a [[contemporary art]] gallery located in [[Chelsea, Manhattan|Chelsea]], [[New York City|New York]].\r\n\r\n==History==\r\n\r\nThe Zach Feuer Gallery was founded in 2000 as the LFL Gallery, by Nick Lawrence, Russell LaMontagne and Zach Feuer.  It was originally located on a fourth floor space on 26th Street.    In 2002 the gallery moved to a first floor space on 24th Street, briefly sharing space with an art book gallery owned by one of the partners.  In 2004  Zach Feuer purchased the gallery from his partners and changed the gallery name to Zach Feuer Gallery.\r\n\r\nSome artists represented by Zach Feuer Gallery are [[Phoebe Washburn]], [[Jules de Balincourt]], [[Nathalie Djurberg]], [[Justin Lieberman]], [[Stuart Hawkins]],  [[Johannes Vanderbeek]], [[Sister Corita Kent]], [[Tamy Ben Tor]], [[Anton Henning]], [[Dana Schutz]], and [[Mark Flood]].\r\n\r\n==External links==\r\n* [http://www.zachfeuer.com Zach Feuer Gallery] website\r\n\r\n{{coord missing|New York}}\r\n\r\n[[Category:Contemporary art galleries]]\r\n[[Category:2000 establishments]]\r\n[[Category:Art galleries in Manhattan]]"
    )
    assert (
        genfixes.fix_syntax(
            r"<ref>{http://www.findagrave.com/cgi-bin/fg.cgi?page=gr&GRid=5194 Find A Grave]</ref>"
        )
        == r"<ref>[http://www.findagrave.com/cgi-bin/fg.cgi?page=gr&GRid=5194 Find A Grave]</ref>"
    )
    assert genfixes.fix_syntax(r"hello [[[[link]] there") == r"hello [[link]] there"
    assert genfixes.fix_syntax(r"hello [[[[link]] there]]") == r"hello [[[[link]] there]]"
    assert genfixes.fix_syntax(r"hello {link) there") == r"hello (link) there"
    assert genfixes.fix_syntax(r"hello {|table|blah) there") == r"hello {|table|blah) there"
    assert (
        genfixes.fix_syntax(r"{{cite web|title=a|url=http://www.site.com|publisher=ABC)|year=2006}")
        == r"{{cite web|title=a|url=http://www.site.com|publisher=ABC)|year=2006}"
    )
    assert (
        genfixes.fix_syntax(
            r"*[http://aeiou.visao.pt/Pages/Lusa.aspx?News=200808068620453 Obituary notice} here"
        )
        == r"*[http://aeiou.visao.pt/Pages/Lusa.aspx?News=200808068620453 Obituary notice] here"
    )
    assert (
        genfixes.fix_syntax(
            r"[http://aeiou.visao.pt/Pages/Lusa.aspx?News=200808068620453 Obituary notice}}"
        )
        == r"[http://aeiou.visao.pt/Pages/Lusa.aspx?News=200808068620453 Obituary notice}}"
    )
    assert genfixes.fix_syntax(r"[[blah blah}word]]") == r"[[blah blah|word]]"
    assert genfixes.fix_syntax(r"[[blah}word]]") == r"[[blah|word]]"
    assert genfixes.fix_syntax(r"now []link]] was") == r"now [[link]] was"
    assert genfixes.fix_syntax(r"now []link|a]] was") == r"now [[link|a]] was"
    assert genfixes.fix_syntax(r"{ here [[blah blah}word]]") == r"{ here [[blah blah}word]]"
    assert genfixes.fix_syntax(r"now {[link]] was") == r"now [[link]] was"
    assert genfixes.fix_syntax(r"now {[[link]] was") == r"now [[link]] was"
    assert genfixes.fix_syntax(r"now [[[link]] was") == r"now [[link]] was"
    assert genfixes.fix_syntax(r"now [[{link]] was") == r"now [[link]] was"
    assert genfixes.fix_syntax(r"now {[link]]} was") == r"now {[[link]]} was"
    assert genfixes.fix_syntax(r"now [[[link]] was]") == r"now [[[link]] was]"
    assert genfixes.fix_syntax(r"hello [[link]]]] there") == r"hello [[link]] there"
    assert genfixes.fix_syntax(r"[[hello [[link]]]] there") == r"[[hello [[link]]]] there"
    assert (
        genfixes.fix_syntax("{|\r\n\t\t\t|-\r\n\t\t\t| [[foo||bar]\r\n\t\t\t|}")
        == "{|\r\n\t\t\t|-\r\n\t\t\t| [[foo|bar]]\r\n\t\t\t|}"
    )
    assert (
        genfixes.fix_syntax(
            "blah\r\n* [http://www.site.com a site\r\n* [http://www.site2.com another]"
        )
        == "blah\r\n* [http://www.site.com a site]\r\n* [http://www.site2.com another]"
    )
    assert (
        genfixes.fix_syntax(
            "blah\r\n* http://www.site.com a site]\r\n* [http://www.site2.com another]"
        )
        == "blah\r\n* [http://www.site.com a site]\r\n* [http://www.site2.com another]"
    )
    assert genfixes.fix_syntax(r"now ({lang-el|foo}}) was") == r"now ({{lang-el|foo}}) was"
    table = '{| class="wikitable"\r\n|-\r\n|Test\r\n|Drive\r\n|-\r\n|1\r\n|2\r\n|}}'
    assert genfixes.fix_syntax(table) == table, r"No change to table with excess closing }"
    assert genfixes.fix_syntax(r"] now") == r"] now"
    assert genfixes.fix_syntax("{{DEFAULTSORT:hello\r\nnow") == "{{DEFAULTSORT:hello}}\r\nnow"
    assert (
        genfixes.fix_syntax(
            "|[[Belmont (Durham) railway station|Belmont]] {[[Durham]])\r\n|[[North Eastern Railway (UK)|NER]]\r\n|1857"
        )
        == "|[[Belmont (Durham) railway station|Belmont]] ([[Durham]])\r\n|[[North Eastern Railway (UK)|NER]]\r\n|1857"
    )
    Choisir = "{{Thoroughbred\r\n| horsename = Choisir\r\n| image =\r\n| caption =\r\n| sire = [[Danehill Dancer]]\r\n| grandsire = [[Danehill (horse)|Danehill]]\r\n| dam = [[Great Selection]]\r\n| damsire =\r\n| sex =\r\n| foaled =\r\n| country = [[Australia|Australian]]}\r\n| colour =\r\n| breeder =\r\n| owner = T\r\n| trainer = [[Paul Perry]]\r\n}}\r\n'''Choisir'''"
    assert genfixes.fix_syntax(Choisir) == Choisir
    Nochange = r"** >> {[[Sei Young Animation Co., Ltd.|Animação Retrô]]}"
    assert genfixes.fix_syntax(Nochange) == Nochange
    assert (
        genfixes.fix_syntax(r"<ref>{{cite web|url=a|title=b (ABC} }}</ref>")
        == r"<ref>{{cite web|url=a|title=b (ABC) }}</ref>"
    )


def test_fix_syntax_opening_ref_tag() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"Now.ref>foo</ref>") == r"Now.<ref>foo</ref>", (
        r"Simple case invalid opening tag"
    )
    assert genfixes.fix_syntax(r"Now. ref>foo</ref>") == r"Now.<ref>foo</ref>", (
        r"Simple case invalid opening tag, space"
    )
    assert genfixes.fix_syntax(r"Now. ref name=boo>foo</ref>") == r"Now.<ref name=boo>foo</ref>", (
        r"Simple case invalid opening named tag, space"
    )
    assert genfixes.fix_syntax(r"Now.ref name=boo>foo</ref>") == r"Now.<ref name=boo>foo</ref>", (
        r"Simple case invalid opening named tag"
    )
    assert (
        genfixes.fix_syntax(r'Now. ref name="boo">foo</ref>') == r'Now.<ref name="boo">foo</ref>'
    ), r"Simple case invalid opening tag, space"
    nochange = r"Now.<ref name=fooref>foo</ref>"
    assert genfixes.fix_syntax(nochange) == nochange, r"valid, ref in ref name"
    nochange = r"Now./ref>foo</ref>"
    assert genfixes.fix_syntax(nochange) == nochange, r"invalid slash"
    assert genfixes.fix_syntax(r"Now.<ref<foo</ref>") == r"Now.<ref>foo</ref>", r"Simple case <ref<"
    assert genfixes.fix_syntax(r"Now.<ref>{{foo}}/ref>") == r"Now.<ref>{{foo}}</ref>", (
        r"Simple case missing final <"
    )


def test_test_fix_syntax_external_link_spacing() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_syntax(r"their new[http://www.site.com site]")
        == r"their new [http://www.site.com site]"
    )
    assert (
        genfixes.fix_syntax(r"their new [http://www.site.com site]was")
        == r"their new [http://www.site.com site] was"
    )
    assert (
        genfixes.fix_syntax(r"their new[http://www.site.com site]was")
        == r"their new [http://www.site.com site] was"
    )
    assert (
        genfixes.fix_syntax(r"their new [http://www.site.com site]")
        == r"their new [http://www.site.com site]"
    )
    assert (
        genfixes.fix_syntax(r"their new [http://www.site.com site] was")
        == r"their new [http://www.site.com site] was"
    )
    assert (
        genfixes.fix_syntax(r"their new [http://www.site.com site] was [[blog]]ger then")
        == r"their new [http://www.site.com site] was [[blog]]ger then"
    )
    nochange1 = r"their [[play]]ers"
    nochange2 = (
        r"ts borders.<ref>[http://cyber.law.harvard.edu/filtering/a/ Saudi Arabia]</ref> A Saudi"
    )
    assert genfixes.fix_syntax(nochange1) == nochange1
    assert genfixes.fix_syntax(nochange2) == nochange2
    assert (
        genfixes.fix_syntax(r"their new[https://www.site.com site]")
        == r"their new [https://www.site.com site]"
    )
    assert (
        genfixes.fix_syntax(r"their new [https://www.site.com site]was")
        == r"their new [https://www.site.com site] was"
    )
    assert (
        genfixes.fix_syntax(r"their new[https://www.site.com site]was")
        == r"their new [https://www.site.com site] was"
    )
    assert (
        genfixes.fix_syntax(r"their new [https://www.site.com site]")
        == r"their new [https://www.site.com site]"
    )
    assert (
        genfixes.fix_syntax(r"their new [https://www.site.com site] was")
        == r"their new [https://www.site.com site] was"
    )
    assert (
        genfixes.fix_syntax(r"their new [https://www.site.com site] was [[blog]]ger then")
        == r"their new [https://www.site.com site] was [[blog]]ger then"
    )
    nochange3 = (
        r"ts borders.<ref>[https://cyber.law.harvard.edu/filtering/a/ Saudi Arabia]</ref> A Saudi"
    )
    assert genfixes.fix_syntax(nochange3) == nochange3
    S = set_lang(r"zh")
    assert (
        genfixes.fix_syntax(r"their new[http://www.site.com site]")
        == r"their new[http://www.site.com site]"
    )
    assert (
        genfixes.fix_syntax(r"their new [http://www.site.com site]was")
        == r"their new [http://www.site.com site]was"
    )
    assert (
        genfixes.fix_syntax(r"their new[http://www.site.com site]was")
        == r"their new[http://www.site.com site]was"
    )
    S = set_lang(r"en")
    assert (
        genfixes.fix_syntax(r"their new[http://www.site.com site]")
        == r"their new [http://www.site.com site]"
    )


def test_test_fix_syntax_references_with_no_http() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<ref>www.foo.com</ref>") == r"<ref>http://www.foo.com</ref>", (
        r"missing http"
    )
    assert (
        genfixes.fix_syntax(r"<ref>[www.foo.com bar]</ref>")
        == r"<ref>[http://www.foo.com bar]</ref>"
    ), r"missing http inside brackets"
    assert (
        genfixes.fix_syntax(r"<ref name=test>www.foo.com</ref>")
        == r"<ref name=test>http://www.foo.com</ref>"
    ), r"missing http inside named ref"
    assert genfixes.fix_syntax(r"<ref>       www.foo.com</ref>") == r"<ref>http://www.foo.com</ref>"
    assert genfixes.fix_syntax(r"Visit www.foo.com") == r"Visit www.foo.com", (
        r"no changes outside references"
    )
    assert (
        genfixes.fix_syntax(r"<ref>[www-foo.a.com bar]</ref>") == r"<ref>[www-foo.a.com bar]</ref>"
    ), r"No change for www-"


def test_test_fix_incorrect_br() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax(r"<br.>") == r"<br />"
    assert genfixes.fix_syntax(r"<BR.>") == r"<br />"
    assert genfixes.fix_syntax(r"<br\>") == r"<br />"
    assert genfixes.fix_syntax(r"<BR\>") == r"<br />"
    assert genfixes.fix_syntax(r"<\br>") == r"<br />"
    assert genfixes.fix_syntax(r"<br./>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /a>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /v>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /r>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /s>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /t>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /z>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /0>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /1>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /2>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /9>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /•>") == r"<br />"
    assert genfixes.fix_syntax(r"<br/•>") == r"<br />"
    assert genfixes.fix_syntax(r"<br /br>") == r"<br />"
    assert genfixes.fix_syntax(r"<br ?>") == r"<br />"
    assert genfixes.fix_syntax(r"<br?>") == r"<br />"
    assert genfixes.fix_syntax(r"<br//>") == r"<br />"
    assert genfixes.fix_syntax(r"</br>") == r"<br />"
    assert genfixes.fix_syntax(r"</br >") == r"<br />"
    assert genfixes.fix_syntax(r"</br />") == r"<br />"
    assert genfixes.fix_syntax(r"</br/>") == r"<br />"
    assert genfixes.fix_syntax(r"<br/>") == r"<br/>"
    assert genfixes.fix_syntax(r"<br />") == r"<br />"


def test_test_fix_syntax_mainspace() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_syntax_mainspace(r"__NOINDEX__", r"A") == r""
    assert genfixes.fix_syntax_mainspace(r"__INDEX__", r"A") == r""
    assert (
        genfixes.fix_syntax_mainspace("__INDEX__\r\n\r\n{{DEFAULTSORT:A}}", r"A")
        == r"{{DEFAULTSORT:A}}"
    )
