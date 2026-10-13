"""Port of the TalkHeaderTests fixture in AWB UnitTests/MiscellaneousTests.cs: talk page fixes (awb_x.core.talkpagefixes).

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from awb_x.core import genfixes, namespace, rx, tools
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
from awb_x.core import talkpagefixes as TalkPageFixes  # noqa: E402
from awb_x.core.talkpagefixes import DefaultSortChange as DEFAULTSORT  # noqa: E402

articleTextHeader = "{{talkheader|noarchive=no}}\r\n[[Category:Foo bar]]"
comment = "\r\nHello world comment."
comment = "\r\nHello world comment."
allInTemplate = "{{archive box|\r\n*[[/Archive: GA review|Good Article review]]}}\r\n\r\n== Explanation of Wright's work in ''Certaine Errors'' =="
allAfterTemplate = "{{archive box|words}} extra foo\r\n\r\n{{another one}}"
VitalArticle = "{{WikiProject banner shell|1={{WPBiography|foo=bar}}\r\n{{WikiProject foo}}\r\n{{Vital article|level=4|topic=Biology|class=FA}}}}\r\n"
otherUnnamed = r"{{WikiProject banner shell|random}}"
a = r"{{WikiProject banner shell|blp=yes|1={{WPBiography|foo=bar|living=yes}}}}"
a = r"{{WikiProject banner shell|blpo=yes|1={{WPBiography|foo=bar}}}}"
a = "{{wpbs|banner collapsed=no|\r\n{{WPBiography|living=yes|class=Start|priority=|listas=Hill, A}}\r\n{{WikiProject Gender Studies}}\r\n{{WikiProject Oklahoma}}\r\n}}"
b = "{{WikiProject banner shell|banner collapsed=no|\r\n{{WPBiography|living=yes|class=Start|priority=|listas=Hill, A}}\r\n{{WikiProject Gender Studies}}\r\n{{WikiProject Oklahoma}}\r\n| blp=yes\r\n}}"
a = r"{{WikiProject a|text}}"
b = r"{{WikiProject b|text}}"
c = r"{{WikiProject c|text}}"
d = r"{{WikiProject d|text}}"
e = "{{talk header}}\r\n{{WikiProject Biography|listas=Bar, F|living=yes|class=Start|priority=mid|sports-work-group=yes}}\r\n{{WikiProject F|class=Start|importance=mid|italy=y}}\r\n{{WikiProject X|class=Start|importance=Mid}}\r\n{{WikiProject D|class=Start|importance=Low}}"
f = "{{WikiProject banner shell|1=\r\n{{WikiProject Biography|listas=Bar, F|living=yes|class=Start|priority=mid|sports-work-group=yes}}\r\n{{WikiProject F|class=Start|importance=mid|italy=y}}\r\n{{WikiProject X|class=Start|importance=Mid}}\r\n{{WikiProject D|class=Start|importance=Low}}\r\n| blp=yes\r\n}}{{talk header}}\r\n\r\n"


def test_move_banners() -> None:
    S = W.for_site(EN)
    a = r"{{Skip to talk}}"
    b = r"{{Talk header}}"
    c = r"{{GA nominee}}"
    d = r"{{Controversial}}"
    e = r"{{Not a forum}}"
    f = r"{{British English}}"
    g = r"{{FailedGA}}"
    correct = (
        c + "\r\n" + a + "\r\n" + b + "\r\n" + d + "\r\n" + e + "\r\n" + f + "\r\n" + g + "\r\n"
    )
    articleText = b + "\r\n" + a + "\r\n" + c + "\r\n" + d + "\r\n" + e + "\r\n" + f + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefg with newlines"
    articleText = a + b + c + d + e + f + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefg"
    articleText = b + a + c + d + e + f + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefg without newlines"
    articleText = a + c + b + d + e + f + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"acbdefg"
    articleText = a + b + c + e + d + f + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcedfg"
    articleText = a + e + c + b + d + f + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"aecbdfg"
    articleText = a + e + c + b + d + g + f
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"aecbdgf"
    articleText = a + c + d + e + f + b + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"acdefbg"
    articleText = f + a + c + b + d + e + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"facbdeg"
    articleText = f + e + d + c + b + a + g
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"fedcbag"
    h = r"{{WikiProject banner shell|1={{WikiProject Greece|class=}}}}"
    i = r"{{Image requested}}"
    j = r"{{Connected contributor|John Doe}}"
    correct = correct + h + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefgh"
    correct = correct + i + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghi"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + i
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgi"
    correct = correct + j + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghij"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgji"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
        + "\r\n"
        + "\r\n"
        + "\r\n"
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgji with newlines at the end"
    articleText = (
        b
        + "\r\n"
        + "\r\n"
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + "\r\n"
        + "\r\n"
        + i
        + "\r\n"
        + "\r\n"
        + "\r\n"
    )
    k = r"{{To do}}"
    m = r"{{Find sources notice}}"
    n = r"{{Split from|foo}}"
    correct = correct + k + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghijk"
    cop = correct + r"{{Copied}}" + "\r\n"
    articleText = cop
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == cop, r"Templates including {{Copied}}"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + k
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
        + "\r\n"
        + h
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefkgjih"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgji with newlines at the end and in the middle"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + k
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
        + "\r\n"
        + h
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefkgjlih"
    correct = correct + m + "\r\n" + n + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghijklmn"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + k
        + "\r\n"
        + n
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + m
        + "\r\n"
        + i
        + "\r\n"
        + h
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefkngjmlih"
    articleText = r"{{some other template}}" + "\r\n" + r"==Untitled==" + "\r\n" + r"some text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, r"no changes if nothing is detected; starts with template"
    articleText = "{{GA|21:12, 11 May 2013 (UTC)|topic=Geography|page=1|oldid=554646767}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Canada|geography=yes|class=Start|importance=Mid|bc=yes}}\r\n{{WikiProject Protected areas|class=Start|importance=Mid}}\r\n{{WikiProject Greece|class=Start}}\r\n}}\r\n{{DYK talk|17 April|2013|entry=... that Canada}}\r\n{{some random template}}"
    articleText2 = "{{GA|21:12, 11 May 2013 (UTC)|topic=Geography|page=1|oldid=554646767}}\r\n{{DYK talk|17 April|2013|entry=... that Canada}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Canada|geography=yes|class=Start|importance=Mid|bc=yes}}\r\n{{WikiProject Protected areas|class=Start|importance=Mid}}\r\n{{WikiProject Greece|class=Start}}\r\n}}\r\n\r\n{{some random template}}"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"articleilestonene templates above wikiproject banners; contains WPBS"
    )
    articleText = "{{GA|21:12, 11 May 2013 (UTC)|topic=Geography|page=1|oldid=554646767}}\r\n{{WikiProject Canada|geography=yes|class=Start|importance=Mid|bc=yes}}\r\n{{WikiProject Protected areas|class=Start|importance=Mid}}\r\n{{some random template}}"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if everything is in place; contains 2 Wikiprojects"
    )


def test_move_banners_and_wiki_projects() -> None:
    S = W.for_site(EN)
    a = r"{{Skip to talk}}"
    b = r"{{Talk header}}"
    c = r"{{GA nominee}}"
    d = r"{{Controversial}}"
    e = r"{{Not a forum}}"
    f = r"{{British English}}"
    g = r"{{FailedGA}}"
    h = r"{{WikiProject Greece|class=}}"
    i = r"{{Image requested}}"
    j = r"{{Connected contributor|John Doe}}"
    correct = (
        c
        + "\r\n"
        + a
        + "\r\n"
        + b
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + g
        + "\r\n"
        + h
        + "\r\n"
        + i
        + "\r\n"
    )
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghi"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + i
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgi"
    articleText = (
        h
        + "\r\n"
        + c
        + "\r\n"
        + a
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + b
        + "\r\n"
        + g
        + "\r\n"
        + i
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"hcadefbgi"
    articleText = (
        d
        + "\r\n"
        + c
        + "\r\n"
        + a
        + "\r\n"
        + h
        + "\r\n"
        + f
        + "\r\n"
        + e
        + "\r\n"
        + b
        + "\r\n"
        + i
        + "\r\n"
        + g
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"dcahfebig"
    correct = correct + j + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghij"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgji"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
        + "\r\n"
        + "\r\n"
        + "\r\n"
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgji with newlines at the end"
    articleText = (
        b
        + "\r\n"
        + "\r\n"
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + h
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + "\r\n"
        + "\r\n"
        + i
        + "\r\n"
        + "\r\n"
        + "\r\n"
    )
    k = r"{{To do}}"
    correct = correct + k + "\r\n"
    articleText = correct
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"abcdefghijk"
    articleText = (
        b
        + "\r\n"
        + a
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + e
        + "\r\n"
        + f
        + "\r\n"
        + k
        + "\r\n"
        + g
        + "\r\n"
        + j
        + "\r\n"
        + i
        + "\r\n"
        + h
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefkgjih"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == correct, r"bacdefhgji with newlines at the end and in the middle"


def test_move_banners_and_spacing() -> None:
    S = W.for_site(EN)
    articleText = r"==Untitled==" + "\r\n" + r"some text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, r"no changes if nothing is detected; starts with header"
    articleText = "{{afd-merged-from|George Piggins Medal|George Piggins Medal|10 June 2012}}\r\n\r\n{{User:WildBot/m04|sect={{User:WildBot/m03|1|History of rugby league#Professional rugby begins in Australia|schism}}|m04}}\r\n{{ArticleHistory\r\n|action1=FAC\r\n\r\n|currentstatus=GA\r\n|topic=Everydaylife}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Rugby league|class=GA|importance=High}}\r\n}}\r\n\r\n== older entries ==\r\nThe"
    articleText2 = "{{ArticleHistory\r\n|action1=FAC\r\n\r\n|currentstatus=GA\r\n|topic=Everydaylife}}\r\n{{afd-merged-from|George Piggins Medal|George Piggins Medal|10 June 2012}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Rugby league|class=GA|importance=High}}\r\n}}\r\n\r\n{{User:WildBot/m04|sect={{User:WildBot/m03|1|History of rugby league#Professional rugby begins in Australia|schism}}|m04}}\r\n\r\n== older entries ==\r\nThe"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, r"unknown templates get below known ones"
    articleText = "{{Talk header}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Architecture|class=Start |importance=Low }}\r\n{{WikiProject Virginia|class=Start |importance=Low }}\r\n{{WikiProject National Register of Historic Places|class=start|importance=low}}\r\n{{Image requested|in=Virginia}}\r\n}}"
    articleText2 = "{{Talk header}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Architecture|class=Start |importance=Low }}\r\n{{WikiProject Virginia|class=Start |importance=Low }}\r\n{{WikiProject National Register of Historic Places|class=start|importance=low}}\r\n}}\r\n{{Image requested|in=Virginia}}\r\n"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"image requested is moved away from WPBS; at some point we could fix the whitespace inside WPBS"
    )
    articleText = "{{Talk header|search=yes}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if nothing is detected; starts with talk header"
    )
    articleText = "{{Not a forum}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if nothing is detected; starts with not a forum"
    )
    articleText = "{{Random template}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if nothing is detected; starts with a random template"
    )
    articleText = "{{Random template}}\r\n{{Yet another random template}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if nothing is detected; starts with two random templates"
    )
    articleText = "{{Skip to talk}}\r\n{{Talk header}}\r\n{{Random template}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if nothing is detected; starts with two skt, th and a random template"
    )
    articleText = "{{Skip to talk}}\r\n{{Not a forum}}\r\n{{Random template}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, (
        r"no changes if nothing is detected; starts with skt, naf and a random template"
    )
    articleText = "{{Not a forum}}\r\n{{Skip to talk}}\r\n{{Random template}}\r\n\r\n==Random header==\r\nSome text"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, r"moves skip to talk on the top 1"
    articleText = "{{Talk header}}\r\n{{Skip to talk}}\r\n{{Random template}}\r\n\r\n==Random header==\r\nSome text"
    articleText2 = "{{Skip to talk}}\r\n{{Talk header}}\r\n{{Random template}}\r\n\r\n==Random header==\r\nSome text"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, r"moves skip to talk on the top 2"
    articleText = "{{Talk header}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject Iraq|class=C|importance=mid}}\r\n{{WikiProject Crime|class=C|importance=low}}\r\n{{WikiProject Terrorism|class=C|importance=low}}\r\n}}\r\n{{image requested}}\r\n\r\n== Reliable sources =="
    articleText2 = articleText
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == articleText2, r"No change, heading whitespace not affected"


def test_move_talk_header() -> None:
    S = W.for_site(EN)
    talkheader = (
        r"{{talk header|noarchive=no|search=no|arpol=no|wp=no|disclaimer=no|shortcut1|shortcut2}}"
    )
    talkrest = "==hello==\r\nhello talk"
    articleText = talkrest + "\r\n" + talkheader
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == talkheader.replace(r"{{talk", r"{{Talk") + "\r\n" + talkrest + "\r\n", (
        r"move talk header"
    )
    WPBS = "{{WikiProject banner shell|blp=yes|1=\r\n{{OH-Project|class=B|importance=Low|nested=yes}}\r\n{{WPBiography|living=yes|class=B|priority=Low|filmbio-work-group=yes|nested=yes|listas=Parker, Sarah Jessica}}\r\n{{WikiProject Cincinnati|class=B|importance=mid|nested=yes}}\r\n}}"
    rest = (
        "\r\n\r\n"
        + "==Song Jessie by Joshua Kadison==\r\nIn the article it says that above mentioned"
    )
    articleText = WPBS + r"{{Talkheader}}" + rest
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == r"{{Talk header}}" + "\r\n" + WPBS + rest, (
        r"talk header on same line as other template"
    )
    articleText = talkheader + "\r\n" + talkrest
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == talkheader + "\r\n" + talkrest, r"talk header already on top"
    articleText = talkrest
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == talkrest, r"no talk header"
    talkheader = r"{{Talk header}}"
    talkrest = "==hello==\r\nhello talk"
    articleText = talkrest + "\r\n" + talkheader + "\r\n{{GA nominee}}"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == "{{GA nominee}}\r\n" + talkheader + "\r\n" + talkrest + "\r\n", (
        r"GA nominee involved"
    )


def test_rename_talk_header() -> None:
    S = W.for_site(EN)
    talkheader = r"{{talkheader|noarchive=no}}"
    talkrest = "==hello==\r\nhello talk"
    articleText = talkrest + "\r\n" + talkheader
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == r"{{Talk header|noarchive=no}}" + "\r\n" + talkrest + "\r\n", (
        r"renamed to upper case with space"
    )


def test_talk_header_defaultsort_change() -> None:
    S = W.for_site(EN)
    start = "\r\n==Foo==\r\nbar"
    df = r"{{DEFAULTSORT:Bert}}"
    articleText = start + "\r\n" + df
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.MOVE_TO_BOTTOM)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == start + "\r\n" + "\r\n" + df, r"removes second newline"
    articleText = start + df
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.MOVE_TO_TOP)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == df + "\r\n" + start, r"moves df after text"
    articleText = start + df
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == start + df, r"no changes"
    df2 = r"{{DEFAULTSORT:}}"
    articleText = start + df2
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.MOVE_TO_BOTTOM)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == start, r"defaultsort with no key removed"
    articleText = start + df2
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.MOVE_TO_TOP)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == start, r"defaultsort with no key removed"


def test_skip_to_talk() -> None:
    S = W.for_site(EN)
    articleText = r"{{Skiptotoc}}"
    stt = r"{{Skip to talk}}"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == stt + "\r\n"
    articleText = r"{{skiptotoctalk}}"
    (
        (_t := TalkPageFixes.process_talk_page(articleText, DEFAULTSORT.NO_CHANGE)),
        (articleText := _t[0]),
    )[0][1]
    assert articleText == stt + "\r\n"


def test_add_missing_first_comment_header() -> None:
    S = W.for_site(EN)
    comment = "\r\nHello world comment."
    articleTextIn = articleTextHeader + comment
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == articleTextHeader + "\r\n" + "\r\n==Untitled==\r\nHello world comment."
    articleTextIn = articleTextHeader + "\r\n*Hello world comment2."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert (
        articleTextIn == articleTextHeader + "\r\n" + "\r\n==Untitled==\r\n*Hello world comment2."
    )
    articleTextIn = articleTextHeader + "\r\n:Hello world comment3."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert (
        articleTextIn == articleTextHeader + "\r\n" + "\r\n==Untitled==\r\n:Hello world comment3."
    )
    articleTextIn = articleTextHeader + '\r\n"Hello world comment4".'
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert (
        articleTextIn == articleTextHeader + "\r\n" + '\r\n==Untitled==\r\n"Hello world comment4".'
    )
    articleTextIn = articleTextHeader + "\r\n" + "===Foo bar===\r\n*Hello world comment2."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert r"==Foo bar==" in articleTextIn
    assert r"==Untitled==" not in articleTextIn
    articleTextIn = articleTextHeader + "\r\n" + "=Foo bar=\r\n*Hello world comment2."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert r"==Foo bar==" in articleTextIn
    assert r"==Untitled==" not in articleTextIn
    articleTextIn = comment
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "==Untitled==\r\nHello world comment.", (
        r"don't add blank line when header is on the top"
    )
    articleTextIn = r"{{Football}}" + "\r\n" + comment
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "{{Football}}\r\n\r\n==Untitled==\r\nHello world comment.", (
        r"add header between template and text"
    )


def test_add_missing_first_comment_header_localization() -> None:
    S = W.for_site(EN)
    S = set_lang(r"zh")
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProject banner shell|blp=yes|blp=yes}}")
        == r"{{WikiProject banner shell|blp=yes|blp=yes}}"
    )
    comment = "\r\nHello world comment."
    articleTextIn = articleTextHeader + comment
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == articleTextHeader + "\r\n" + "\r\n==無標題==\r\nHello world comment."
    S = set_lang(r"en")


def test_add_missing_first_comment_header_no_changes() -> None:
    S = W.for_site(EN)
    articleTextIn = articleTextHeader + "\r\n==Question==\r\n:Hello world comment3."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == articleTextHeader + "\r\n==Question==\r\n:Hello world comment3."
    articleTextIn = "\r\n{{Some template}}\r\n==Question==\r\n:Hello world comment3."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n{{Some template}}\r\n==Question==\r\n:Hello world comment3."
    articleTextIn = "\r\n==Question==\r\n{{Some template}}\r\n:Hello world comment3."
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n==Question==\r\n{{Some template}}\r\n:Hello world comment3."
    articleTextIn = "\r\n==Question==\r\n{{Some template}}"
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n==Question==\r\n{{Some template}}"
    articleTextIn = "\r\n{{foo|\r\nbar|\r\nend}}"
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n{{foo|\r\nbar|\r\nend}}"
    articleTextIn = "\r\n<!--\r\nfoo\r\n-->"
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n<!--\r\nfoo\r\n-->"
    articleTextIn = "\r\n__TOC__"
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n__TOC__"
    allInTemplate = "{{archive box|\r\n*[[/Archive: GA review|Good Article review]]}}\r\n\r\n== Explanation of Wright's work in ''Certaine Errors'' =="
    articleTextIn = allInTemplate
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == allInTemplate
    allAfterTemplate = "{{archive box|words}} extra foo\r\n\r\n{{another one}}"
    articleTextIn = allAfterTemplate
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == allAfterTemplate
    articleTextIn = (
        "\r\n<gallery>\r\nFile:Example.jpg|Caption1\r\nFile:Example.jpg|Caption2\r\n</gallery>"
    )
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert (
        articleTextIn
        == "\r\n<gallery>\r\nFile:Example.jpg|Caption1\r\nFile:Example.jpg|Caption2\r\n</gallery>"
    )
    articleTextIn = "\r\n{|\r\n|Foo\r\nbar\r\n|}"
    (
        (_t := TalkPageFixes.process_talk_page(articleTextIn, DEFAULTSORT.NO_CHANGE)),
        (articleTextIn := _t[0]),
    )[0][1]
    assert articleTextIn == "\r\n{|\r\n|Foo\r\nbar\r\n|}"


def test_wiki_project_banner_shell_redirects() -> None:
    S = W.for_site(EN)
    red1 = r"{{WPBS}}"
    red2 = r"{{Wikiprojectbannershell}}"
    red3 = r"{{wpb}}"
    red4 = r"{{WPB}}"
    WikiProjectBannerShell = r"{{WikiProject banner shell}}"
    WikiProjectBanners = r"{{WikiProjectBanners}}"
    assert TalkPageFixes.wiki_project_banner_shell(red1) == WikiProjectBannerShell
    assert TalkPageFixes.wiki_project_banner_shell(red2) == WikiProjectBannerShell
    assert TalkPageFixes.wiki_project_banner_shell(WikiProjectBannerShell) == WikiProjectBannerShell
    assert TalkPageFixes.wiki_project_banner_shell(red3) == WikiProjectBannerShell
    assert TalkPageFixes.wiki_project_banner_shell(red4) == WikiProjectBannerShell
    assert TalkPageFixes.wiki_project_banner_shell(WikiProjectBanners) == WikiProjectBannerShell


def test_wiki_project_banner_shell_en_only() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fr")
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProject banner shell|blp=yes|blp=yes}}")
        == r"{{WikiProject banner shell|blp=yes|blp=yes}}"
    )
    S = set_lang(r"en")
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProject banner shell|blp=yes|blp=yes}}")
        == r"{{WikiProject banner shell|blp=yes}}"
    )


def test_wiki_project_banner_shell_dupe_parameters() -> None:
    S = W.for_site(EN)
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProject banner shell|blp=yes|blp=yes}}")
        == r"{{WikiProject banner shell|blp=yes}}"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blpo=yes|blpo=yes|blp=yes|blp=yes}}"
        )
        == r"{{WikiProject banner shell|blpo=yes|blp=yes}}"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|collapsed=yes|collapsed=yes|collapsed=yes}}"
        )
        == r"{{WikiProject banner shell|collapsed=yes}}"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProject banner shell||collapsed=yes}}")
        == r"{{WikiProject banner shell|collapsed=yes}}"
    ), r"excess pipes cleaned"


def test_wiki_project_banner_shell_unneeded_params() -> None:
    S = W.for_site(EN)
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blp=no|collapsed=no|blpo=no}}"
        )
        == r"{{WikiProject banner shell|blp=no}}"
    ), r"Retain blp=no"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blp=no|collapsed=yes|blpo=no}}"
        )
        == r"{{WikiProject banner shell|blp=no|collapsed=yes}}"
    ), r"Retain blp=no"
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProjectBanners|collapsed=no|blpo=no}}")
        == r"{{WikiProject banner shell}}"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(r"{{WikiProjectBanners|collapsed=yes|blpo=no}}")
        == r"{{WikiProject banner shell|collapsed=yes}}"
    )


def test_wiki_project_banner_shell_wp_biography() -> None:
    S = W.for_site(EN)
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|1={{WPBiography|foo=bar}}}}"
        )
        == r"{{WikiProject banner shell|1={{WPBiography|foo=bar}}}}"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blp=|1={{WPBiography|foo=bar|living=yes}}}}"
        )
        == r"{{WikiProject banner shell|blp=yes|1={{WPBiography|foo=bar|living=yes}}}}"
    ), r"appends blp=yes to WPBS"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blp=|1={{WikiProject Biography|foo=bar|living=yes}}}}"
        )
        == r"{{WikiProject banner shell|blp=yes|1={{WikiProject Biography|foo=bar|living=yes}}}}"
    ), r"appends blp=yes to WPBS"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blpo=|1={{WPBiography|foo=bar|blpo=yes}}}}"
        )
        == r"{{WikiProject banner shell|blpo=yes|1={{WPBiography|foo=bar|blpo=yes}}}}"
    ), r"appends blpo=yes to WPBS"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blpo=|1={{WPBiography|foo=bar|blpo=no}}}}"
        )
        == r"{{WikiProject banner shell|blpo=|1={{WPBiography|foo=bar|blpo=no}}}}"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            r"{{WikiProject banner shell|blp=yes|1={{WPBiography|foo=bar|living=no}}}}"
        )
        == r"{{WikiProject banner shell|1={{WPBiography|foo=bar|living=no}}}}"
    )


def test_wiki_project_banner_shell_adding_wiki_projects() -> None:
    S = W.for_site(EN)
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject banner shell|1={{WPBiography|foo=bar}}}}\r\n{{WikiProject foo}}"
        )
        == "{{WikiProject banner shell|1={{WPBiography|foo=bar}}\r\n{{WikiProject foo}}}}\r\n"
    ), r"WikiProjects pulled into WPBS"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject banner shell|1={{WPBiography|foo=bar}}}}\r\n{{WikiProject foo}}\r\n{{WikiProject bar}}"
        )
        == "{{WikiProject banner shell|1={{WPBiography|foo=bar}}\r\n{{WikiProject foo}}\r\n{{WikiProject bar}}}}\r\n\r\n"
    ), r"WikiProjects pulled into WPBS"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject Biography|living=yes|foo=bar}}{{WikiProject banner shell|1={{WikiProject foo}}\r\n{{WikiProject bar}}}}"
        )
        == "{{WikiProject banner shell|1={{WikiProject foo}}\r\n{{WikiProject bar}}\r\n{{WikiProject Biography|living=yes|foo=bar}} | blp=yes}}"
    ), r"WikiProjects pulled into WPBS, WPBIO contains living=yes"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject bar}}\r\n\r\n{{WikiProject banner shell|1={{WPBiography|foo=bar}}}}\r\n{{WikiProject foo}}"
        )
        == "{{WikiProject banner shell|1={{WPBiography|foo=bar}}\r\n{{WikiProject bar}}\r\n{{WikiProject foo}}}}\r\n"
    ), r"WikiProjects pulled into WPBS, no excess whitespace left"
    VitalArticle = "{{WikiProject banner shell|1={{WPBiography|foo=bar}}\r\n{{WikiProject foo}}\r\n{{Vital article|level=4|topic=Biology|class=FA}}}}\r\n"
    assert TalkPageFixes.wiki_project_banner_shell(VitalArticle) == VitalArticle, (
        r"Support Vital article - already inside"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{Vital article|level=4|topic=Biology|class=FA}}\r\n{{WikiProject banner shell|1={{WPBiography|foo=bar}}\r\n{{WikiProject foo}}}}\r\n"
        )
        == VitalArticle
    ), r"Support Vital article - put inside"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject banner shell|{{WPBiography|foo=bar}}}}\r\n{{WikiProject foo}}"
        )
        == "{{WikiProject banner shell|{{WPBiography|foo=bar}}\r\n{{WikiProject foo}}}}\r\n"
    ), r"WikiProjects pulled into WPBS - new style WPBS without 1="
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject banner shell|class=A|{{WPBiography|foo=bar}}}}\r\n{{WikiProject foo}}"
        )
        == "{{WikiProject banner shell|class=A|{{WPBiography|foo=bar}}\r\n{{WikiProject foo}}}}\r\n"
    ), r"WikiProjects pulled into WPBS - new style WPBS with class"
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject banner shell|class=A}}\r\n{{WikiProject foo}}\r\n{{WikiProject bar}}"
        )
        == "{{WikiProject banner shell|class=A|\r\n{{WikiProject foo}}\r\n{{WikiProject bar}}}}\r\n\r\n"
    ), r"WikiProjects pulled into WPBS - new style WPBS with class, no existing WPB"


def test_wiki_project_banner_shell_unnamed_param() -> None:
    S = W.for_site(EN)
    assert (
        TalkPageFixes.wiki_project_banner_shell(
            "{{WikiProject banner shell|\r\n{{WPBiography|foo=bar}}}}"
        )
        == "{{WikiProject banner shell|\r\n{{WPBiography|foo=bar}}}}"
    )
    otherUnnamed = r"{{WikiProject banner shell|random}}"
    assert TalkPageFixes.wiki_project_banner_shell(otherUnnamed) == otherUnnamed, (
        r"other unknown parameter not named 1="
    )


def test_wiki_project_banner_shell_blp() -> None:
    S = W.for_site(EN)
    a = r"{{WikiProject banner shell|blp=yes|1={{WPBiography|foo=bar|living=yes}}}}"
    assert TalkPageFixes.wiki_project_banner_shell(a + r"{{Blp}}") == a, r"removes redundant banner"
    assert (
        TalkPageFixes.wiki_project_banner_shell(a.replace(r"blp=yes", r"blp=") + r"{{Blp}}") == a
    ), r"empty parameter in WPBS"
    assert TalkPageFixes.wiki_project_banner_shell(r"{{Blp}}") == r"{{Blp}}"


def test_wiki_project_banner_shell_blpo() -> None:
    S = W.for_site(EN)
    a = r"{{WikiProject banner shell|blpo=yes|1={{WPBiography|foo=bar}}}}"
    assert TalkPageFixes.wiki_project_banner_shell(a + r"{{Blpo}}") == a, (
        r"removes redundant banner"
    )
    assert TalkPageFixes.wiki_project_banner_shell(a + r"{{BLPO}}") == a, (
        r"removes redundant banner"
    )
    assert TalkPageFixes.wiki_project_banner_shell(a + r"{{BLP others}}") == a, (
        r"removes redundant banner"
    )
    assert (
        TalkPageFixes.wiki_project_banner_shell(a.replace(r"blpo=yes", r"blpo=") + r"{{Blpo}}") == a
    ), r"empty parameter in WPBS"
    assert TalkPageFixes.wiki_project_banner_shell(r"{{Blpo}}") == r"{{Blpo}}"


def test_wiki_project_banner_shell_misc() -> None:
    S = W.for_site(EN)
    a = "{{wpbs|banner collapsed=no|\r\n{{WPBiography|living=yes|class=Start|priority=|listas=Hill, A}}\r\n{{WikiProject Gender Studies}}\r\n{{WikiProject Oklahoma}}\r\n}}"
    b = "{{WikiProject banner shell|banner collapsed=no|\r\n{{WPBiography|living=yes|class=Start|priority=|listas=Hill, A}}\r\n{{WikiProject Gender Studies}}\r\n{{WikiProject Oklahoma}}\r\n| blp=yes\r\n}}"
    assert TalkPageFixes.wiki_project_banner_shell(a) == b


def test_add_wiki_project_banner_shell() -> None:
    S = W.for_site(EN)
    a = r"{{WikiProject a|text}}"
    b = r"{{WikiProject b|text}}"
    c = r"{{WikiProject c|text}}"
    d = r"{{WikiProject d|text}}"
    assert TalkPageFixes.wiki_project_banner_shell(a) == a
    assert TalkPageFixes.wiki_project_banner_shell(a + b) == a + b
    assert (
        TalkPageFixes.wiki_project_banner_shell(a + b + c)
        == r"{{WikiProject banner shell|1=" + "\r\n" + a + "\r\n" + b + "\r\n" + c + "\r\n" + r"}}"
    ), r"banner shell added for 3 or more wikiproject links"
    assert (
        TalkPageFixes.wiki_project_banner_shell(a + b + c + d)
        == r"{{WikiProject banner shell|1="
        + "\r\n"
        + a
        + "\r\n"
        + b
        + "\r\n"
        + c
        + "\r\n"
        + d
        + "\r\n"
        + r"}}"
    )
    e = "{{talk header}}\r\n{{WikiProject Biography|listas=Bar, F|living=yes|class=Start|priority=mid|sports-work-group=yes}}\r\n{{WikiProject F|class=Start|importance=mid|italy=y}}\r\n{{WikiProject X|class=Start|importance=Mid}}\r\n{{WikiProject D|class=Start|importance=Low}}"
    f = "{{WikiProject banner shell|1=\r\n{{WikiProject Biography|listas=Bar, F|living=yes|class=Start|priority=mid|sports-work-group=yes}}\r\n{{WikiProject F|class=Start|importance=mid|italy=y}}\r\n{{WikiProject X|class=Start|importance=Mid}}\r\n{{WikiProject D|class=Start|importance=Low}}\r\n| blp=yes\r\n}}{{talk header}}\r\n\r\n"
    assert TalkPageFixes.wiki_project_banner_shell(e) == f, (
        r"adds WPBS, ignores non-wikiproject templates"
    )


def test_remove_template_namespace() -> None:
    S = W.for_site(EN)
    T1 = r"{{Template:Foo}}"
    T2 = "{{Template:Foo}}\r\n==Section==\r\n{{Template:Bar}}"
    assert not (
        ((_t := TalkPageFixes.process_talk_page(T1, DEFAULTSORT.NO_CHANGE)), (T1 := _t[0]))[0][1]
    )
    assert T1 == r"{{Foo}}", r"template namespace removed"
    assert not (
        ((_t := TalkPageFixes.process_talk_page(T2, DEFAULTSORT.NO_CHANGE)), (T2 := _t[0]))[0][1]
    )
    assert T2 == "{{Foo}}\r\n==Section==\r\n{{Template:Bar}}", (
        r"changes only made in zeroth section"
    )


def test_wp_biography_top_billing() -> None:
    S = W.for_site(EN)
    a = "{{WPBiography|foo=yes|living=yes}}\r\n{{WikiProject London}}\r\n"
    b = "{{WikiProject banner shell|banner collapsed=no|1=\r\n{{WPBiography|living=yes|class=Start|priority=|listas=Hill, A}}\r\n{{WikiProject Gender Studies}}\r\n{{WikiProject Oklahoma}}\r\n| blp=yes\r\n}}"
    c = "{{WPBiography|foo=yes|living=no}}\r\n{{WikiProject London}}"
    assert (
        TalkPageFixes.wp_biography("{{WikiProject London}}\r\n{{WPBiography|foo=yes|living=yes}}")
        == a
    ), r"WPBiography moved above WikiProjects"
    assert TalkPageFixes.wp_biography(a) == a, r"no change when WPBiography ahead of WikiProjects"
    assert TalkPageFixes.wp_biography(b) == b, r"no change when WPBS present"
    assert TalkPageFixes.wp_biography(c) == c, r"no change when not living"
    assert TalkPageFixes.wp_biography(c + r"{{blp}}") == c + r"{{blp}}", (
        r"no change when not living"
    )
    assert TalkPageFixes.wp_biography(a + r"{{blp}}") == a, r"blp template removed when living=y"


def test_wp_songs() -> None:
    S = W.for_site(EN)
    a = r"{{WPSongs}}"
    assert TalkPageFixes.wp_songs(a + r"{{sir}}") == a.replace(r"}}", r" | needs-infobox=yes}}"), (
        r"Add sir to WPSongs"
    )
    assert TalkPageFixes.wp_songs(
        a.replace(r"}}", r" | needs-infobox=}}" + r"{{sir}}")
    ) == a.replace(r"}}", r" | needs-infobox=yes}}"), r"Add sir to WPSongs with empty parameter"
    assert TalkPageFixes.wp_songs(
        a.replace(r"}}", r" | needs-infobox=}}" + r"{{Single infobox request}}")
    ) == a.replace(r"}}", r" | needs-infobox=yes}}"), (
        r"Add Single infobox request to WPSongs with empty parameter"
    )
    assert TalkPageFixes.wp_songs(
        a.replace(r"}}", r" | needs-infobox=yes}}") + r"{{sir}}"
    ) == a.replace(r"}}", r" | needs-infobox=yes}}"), (
        r"Remove sir when WPSongs with needs-infobox=yes exists"
    )
    assert TalkPageFixes.wp_songs(a) == a, r"Do nothing"
    assert TalkPageFixes.wp_songs(a.replace(r"}}", r"|importance=yes}}")) == a, r"Remove importance"
    assert TalkPageFixes.wp_songs(a.replace(r"}}", r"|needs-infobox=no}}")) == a, (
        r"Remove needs-infobox=no"
    )
    assert TalkPageFixes.wp_songs(a.replace(r"}}", r"|importance=yes|needs-infobox=no}}")) == a, (
        r"Remove importance and needs-infobox=no"
    )
    b = r"{{WikiProject Songs}}"
    assert TalkPageFixes.wp_songs(b + r"{{sir}}") == b.replace(r"}}", r" | needs-infobox=yes}}"), (
        r"Add sir to WPSongs"
    )
    assert TalkPageFixes.wp_songs(
        b.replace(r"}}", r" | needs-infobox=}}" + r"{{sir}}")
    ) == b.replace(r"}}", r" | needs-infobox=yes}}"), r"Add sir to WPSongs with empty parameter"
    assert TalkPageFixes.wp_songs(
        b.replace(r"}}", r" | needs-infobox=}}" + r"{{Single infobox request}}")
    ) == b.replace(r"}}", r" | needs-infobox=yes}}"), (
        r"Add Single infobox request to WPSongs with empty parameter"
    )
    assert TalkPageFixes.wp_songs(
        b.replace(r"}}", r" | needs-infobox=yes}}") + r"{{sir}}"
    ) == b.replace(r"}}", r" | needs-infobox=yes}}"), (
        r"Remove sir when WPSongs with needs-infobox=yes exists"
    )
    assert TalkPageFixes.wp_songs(b) == b, r"Do nothing"


def test_wp_jazz() -> None:
    S = W.for_site(EN)
    a = r"{{WPJazz}}"
    assert TalkPageFixes.wp_jazz(a + r"{{WPSongs}}") == a.replace(
        r"}}", r" | song=yes}}{{WPSongs}}"
    ), r"Add song to WPJazz"
    assert TalkPageFixes.wp_jazz(a + r"{{WPAlbums}}") == a.replace(
        r"}}", r" | album=yes}}{{WPAlbums}}"
    ), r"Add album to WPJazz"
    assert TalkPageFixes.wp_jazz(
        a.replace(r"}}", r" | song=}}" + r"{{WikiProject Songs}}")
    ) == a.replace(r"}}", r" | song=yes}}{{WikiProject Songs}}"), (
        r"Add song to WPJazz with empty parameter"
    )
    assert TalkPageFixes.wp_jazz(
        a.replace(r"}}", r" | album=}}" + r"{{WikiProject Albums}}")
    ) == a.replace(r"}}", r" | album=yes}}{{WikiProject Albums}}"), (
        r"Add album to WPJazz with empty parameter"
    )
    assert TalkPageFixes.wp_jazz(a) == a, r"Do nothing"
    assert TalkPageFixes.wp_jazz(a.replace(r"}}", r"|needs-infobox=no}}")) == a, (
        r"Remove needs-infobox=no"
    )
    b = r"{{WikiProject Jazz}}"
    assert TalkPageFixes.wp_jazz(b + r"{{WPSongs}}") == b.replace(
        r"}}", r" | song=yes}}{{WPSongs}}"
    ), r"Add song to WikiProject Jazz"
    assert TalkPageFixes.wp_jazz(b + r"{{WPAlbums}}") == b.replace(
        r"}}", r" | album=yes}}{{WPAlbums}}"
    ), r"Add album to WikiProject Jazz"
    assert TalkPageFixes.wp_jazz(
        b.replace(r"}}", r" | song=}}" + r"{{WikiProject Songs}}")
    ) == b.replace(r"}}", r" | song=yes}}{{WikiProject Songs}}"), (
        r"Add song to WPJAzz with empty parameter"
    )
    assert TalkPageFixes.wp_jazz(b) == b, r"Do nothing"
    assert TalkPageFixes.wp_jazz(b.replace(r"}}", r"|needs-infobox=no}}")) == b, (
        r"Remove needs-infobox=no"
    )
