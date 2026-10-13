"""Port of AWB UnitTests/FixCitationTemplatesTests.cs: citation template fixes (awb_x.core.parsers.citetemplates).

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


def test_fix_citation_templates_newline_in_param_value() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(
            "now {{cite web| url=a.com|title=hello\r\nworld|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|title=hello world|format=PDF}} was"
    ), r"newline converted to space"
    assert (
        genfixes.fix_citation_templates(
            "now {{cite web| url=a.com|title=hello world|publisher=Foo\r\nBar}} was"
        )
        == r"now {{cite web| url=a.com|title=hello world|publisher=Foo Bar}} was"
    ), r"newline converted to space, any parameter"


def test_unspaced_comma_page_range() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{cite book|url=http://www.stie.com | pages=55,59 }}")
        == r"{{cite book|url=http://www.stie.com | pages=55, 59 }}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=http://www.stie.com | pages=483,491–492 }}"
        )
        == r"{{cite book|url=http://www.stie.com | pages=483, 491–492 }}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=http://www.stie.com | pages=267–268,273,299 }}"
        )
        == r"{{cite book|url=http://www.stie.com | pages=267–268, 273, 299 }}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|url=http://www.stie.com | pages=55, 59 }}")
        == r"{{cite book|url=http://www.stie.com | pages=55, 59 }}"
    ), r"no change when already correct"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=http://www.stie.com | pages=12,354–12,386 }}"
        )
        == r"{{cite book|url=http://www.stie.com | pages=12,354–12,386 }}"
    ), r"no change when already correct"
    assert (
        genfixes.fix_citation_templates(r"{{cite book|url=http://www.stie.com | pages=12,354 }}")
        == r"{{cite book|url=http://www.stie.com | pages=12,354 }}"
    ), r"no change when already correct"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=http://www.stie.com | pages=483,491,492 }}"
        )
        == r"{{cite book|url=http://www.stie.com | pages=483, 491, 492 }}"
    )


def test_fix_citation_templates_quoted_title() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r'now {{cite web| url=a.com|title="hello"|format=PDF}} was')
        == r'now {{cite web| url=a.com|title="hello"|format=PDF}} was'
    ), r"no change: title is quote"
    assert (
        genfixes.fix_citation_templates(r'now {{cite web| url=a.com|title="hello|format=PDF}} was')
        == r"now {{cite web| url=a.com|title=hello|format=PDF}} was"
    ), r"stray starting quote"
    assert (
        genfixes.fix_citation_templates(r'now {{cite web| url=a.com|title=hello"|format=PDF}} was')
        == r"now {{cite web| url=a.com|title=hello|format=PDF}} was"
    ), r"stray end quote"
    assert (
        genfixes.fix_citation_templates(
            r'now {{cite web| url=a.com|trans_title="hello|format=PDF}} was'
        )
        == r"now {{cite web| url=a.com|trans_title=hello|format=PDF}} was"
    ), r"trans title stray starting quote"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|trans_title=hello’s today|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|trans_title=hello's today|format=PDF}} was"
    ), r"single curly quote"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|trans_title=‘hello today’|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|trans_title='hello today'|format=PDF}} was"
    ), r"single curly quote open and close"
    assert (
        genfixes.fix_citation_templates(
            r'now {{cite web| url=a.com|title="hello" world|format=PDF}} was'
        )
        == r'now {{cite web| url=a.com|title="hello" world|format=PDF}} was'
    ), r"no change: partial quote"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|title=now ‹hello› at|format=PDF}} was"
        )
        == r'now {{cite web| url=a.com|title=now "hello" at|format=PDF}} was'
    ), r"partial quote short arrows"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|title=now ‹hello› at ‹hello2› be|format=PDF}} was"
        )
        == r'now {{cite web| url=a.com|title=now "hello" at "hello2" be|format=PDF}} was'
    ), r"partial quote short arrows"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|title=hello» second|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|title=hello» second|format=PDF}} was"
    ), r"no change if » used as section delimeter"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|title=hello> second|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|title=hello> second|format=PDF}} was"
    ), r"no change if > used as section delimeter"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|title=hello « second|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|title=hello « second|format=PDF}} was"
    ), r"no change if « used as section delimeter"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=a.com|title=hello› second|format=PDF}} was"
        )
        == r"now {{cite web| url=a.com|title=hello› second|format=PDF}} was"
    ), r"no change if › used as section delimeter"
    guillemets = r"now {{cite web| url=a.com|title=«hello»|format=PDF}} was"
    assert genfixes.fix_citation_templates(guillemets) == guillemets, r"guillemets not changed"
    lowHigh = r"now {{cite web| url=a.com|title=“hello„|format=PDF}} was"
    assert genfixes.fix_citation_templates(lowHigh) == lowHigh, r"lowHigh quotes not changed"
    lowHigh = r"now {{cite web| url=a.com|title=“Vai devagar”|format=PDF}} was"
    assert genfixes.fix_citation_templates(lowHigh) == lowHigh, r"Valid non-en quotes not changed"


def test_fix_citation_google_books() -> None:
    S = W.for_site(EN)
    correct = r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009}}"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web|title=a |url=http://books.google.com/foo | year=2009}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web|title=a |url=http://books.google.com/foo | year=2009}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web|title=a |url=http://books.google.com/foo | year=2009}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{ Cite web |title=a |url=http://books.google.com/foo | year=2009}}"
        )
        == r"now {{ Cite book |title=a |url=http://books.google.com/foo | year=2009}}"
    )
    assert genfixes.fix_citation_templates(correct) == correct
    noChange = r"now {{Cite book|title=a |url=http://books.google.com/foo | year=2009 | work = some Journal}}"
    assert genfixes.fix_citation_templates(noChange) == noChange, (
        r"journal cites to Google books not changed"
    )


def test_fix_citation_url_no_http() -> None:
    S = W.for_site(EN)
    correct = r"now {{cite web|title=foo | url=http://www.foo.com | date = 1 June 2010 }}"
    assert genfixes.fix_citation_templates(correct.replace(r"http://", r"")) == correct, (
        r"Adds http:// when URL begins www."
    )
    assert genfixes.fix_citation_templates(
        correct.replace(r"http://www", r"Www")
    ) == correct.replace(r"www", r"Www"), r"Adds http:// when URL begins www."
    assert genfixes.fix_citation_templates(
        correct.replace(r"http://www", r"www2")
    ) == correct.replace(r"www", r"www2"), r"Adds http:// when URL begins www2"
    assert genfixes.fix_citation_templates(correct) == correct, r"no change if already correct URL"
    assert genfixes.fix_citation_templates(
        correct.replace(r"url=http://", r"archiveurl=")
    ) == correct.replace(r"url=", r"archiveurl="), r"Adds http:// when archiveurl begins www."
    assert genfixes.fix_citation_templates(
        correct.replace(r"url=http://", r"archive-url=")
    ) == correct.replace(r"url=", r"archive-url="), r"Adds http:// when archive-url begins www."
    assert genfixes.fix_citation_templates(
        correct.replace(r"url=http://", r"contribution-url=")
    ) == correct.replace(r"url=", r"contribution-url="), (
        r"Adds http:// when contribution-url begins www."
    )
    dash = r"now {{cite web|title=foo | url=www-foo.a.com | date = 1 June 2010 }}"
    assert genfixes.fix_citation_templates(dash) == dash.replace(r"www", r"http://www"), (
        r"handles www-"
    )
    assert (
        genfixes.fix_citation_templates(correct.replace(r"http://www", r"http:www")) == correct
    ), r"Adds missing http slashes"


def test_work_in_italics() -> None:
    S = W.for_site(EN)
    correct = r"now {{cite web| url=http://site.net/1.pdf|format=PDF|work=Foo}}"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net/1.pdf|format=PDF|work=''Foo''}}"
        )
        == correct
    )
    assert genfixes.fix_citation_templates(correct) == correct
    website = r"now {{cite web| url=http://site.net/1.pdf|format=PDF|work=''site.net''}}"
    assert genfixes.fix_citation_templates(website) == website, (
        r"italics not removed for work=website"
    )


def test_fix_citation_year() -> None:
    S = W.for_site(EN)
    correct = r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009}}"
    assert genfixes.fix_citation_templates(correct) == correct
    correct2 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009 |page=32}}"
    assert genfixes.fix_citation_templates(correct2) == correct2
    nochange1 = r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009a}}"
    nochange2 = r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009a| date = 2009-05-16}}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1
    assert genfixes.fix_citation_templates(nochange2) == nochange2


def test_fix_citation_templates_date_in_year() -> None:
    S = W.for_site(EN)
    correct1 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009-10-17}}"
    correct2 = (
        r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009-10-17|last=Smith}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17}}"
        )
        == correct1
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17|last=Smith}}"
        )
        == correct2
    )
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17}}".replace(
            r"2009-10-17", r"17 October 2009"
        )
    ) == correct1.replace(r"2009-10-17", r"17 October 2009")
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17}}".replace(
            r"2009-10-17", r"17 October, 2009"
        )
    ) == correct1.replace(r"2009-10-17", r"17 October 2009")
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17|last=Smith}}".replace(
            r"2009-10-17", r"17 October 2009"
        )
    ) == correct2.replace(r"2009-10-17", r"17 October 2009")
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17}}".replace(
            r"2009-10-17", r"October 17, 2009"
        )
    ) == correct1.replace(r"2009-10-17", r"October 17, 2009")
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17|last=Smith}}".replace(
            r"2009-10-17", r"October 17, 2009"
        )
    ) == correct2.replace(r"2009-10-17", r"October 17, 2009")
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009-10-17|last=Smith}}".replace(
            r"2009-10-17", r"October, 17, 2009"
        )
    ) == correct2.replace(r"2009-10-17", r"October 17, 2009")
    assert genfixes.fix_citation_templates(correct1) == correct1
    nochange1 = r"now {{cite book|title=a |url=http://books.google.com/foo | year=2009–2010}}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1


def test_fix_citation_templates_year_within_date() -> None:
    S = W.for_site(EN)
    correct1 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009-10-17}}"
    nochange1 = (
        r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009-10-17 | year=2009a}}"
    )
    nochange1b = (
        r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009 | year=2009a}}"
    )
    nochange2 = (
        r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009-10-17 | year=2004}}"
    )
    nochange2b = r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 October 2009 | year=2004}}"
    nochange2c = r"now {{cite book|title=a |url=http://books.google.com/foo | date=October 17, 2009 | year=2004}}"
    assert genfixes.fix_citation_templates(correct1.replace(r"}}", r"|year=2009}}")) == correct1
    assert genfixes.fix_citation_templates(correct1.replace(r"foo", r"foo |year=2009")) == correct1
    assert genfixes.fix_citation_templates(nochange1) == nochange1, (
        r"Harvard anchors using YYYYa are not removed"
    )
    assert genfixes.fix_citation_templates(nochange1b) == nochange1b, (
        r"Harvard anchor using YYYYa in year and year in date: both needed so not removed"
    )
    assert genfixes.fix_citation_templates(nochange2) == nochange2, (
        r"Year not removed if different to year in ISO date"
    )
    assert genfixes.fix_citation_templates(nochange2b) == nochange2b, (
        r"Year not removed if different to year in International date"
    )
    assert genfixes.fix_citation_templates(nochange2c) == nochange2c, (
        r"Year not removed if different to year in American date"
    )
    correct3 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 May 2009}}"
    nochange4 = (
        r"{{cite book|title=a |url=http://books.google.com/foo | date=May 2009 | year=2009 }}"
    )
    assert genfixes.fix_citation_templates(nochange4) == nochange4, (
        r"Year not removed if date is only 'Month YYYY'"
    )
    assert genfixes.fix_citation_templates(correct3.replace(r"}}", r"|year=2009}}")) == correct3, (
        r"year removed when within date"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|title=a |url=http://books.google.com/foo | date=2009 | year=2009 }}"
        )
        == r"{{cite book|title=a |url=http://books.google.com/foo | year=2009 }}"
    ), r"Date removed if date is YYYY and year same"


def test_fix_citation_templates_month_within_date() -> None:
    S = W.for_site(EN)
    correct = r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 May 2009}}"
    nochange = r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 May 2009 | month=March}}"
    assert genfixes.fix_citation_templates(correct.replace(r"}}", r"|month=May}}")) == correct, (
        r"month removed when within date"
    )
    assert genfixes.fix_citation_templates(nochange) == nochange, (
        r"month not removed if different to month in date"
    )
    assert genfixes.fix_citation_templates(correct.replace(r"}}", r"|month=5}}")) == correct, (
        r"number month removed when within date"
    )
    assert genfixes.fix_citation_templates(correct.replace(r"}}", r"|month=05}}")) == correct, (
        r"number month removed when within date"
    )
    correct2 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 December 2009}}"
    nochange2 = (
        r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 May 2009 | month=2}}"
    )
    assert genfixes.fix_citation_templates(correct2.replace(r"}}", r"|month=12}}")) == correct2, (
        r"number month removed when within date"
    )
    assert genfixes.fix_citation_templates(nochange2) == nochange2, (
        r"nn month not removed if different to month in date"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|last=Mahoney|first=Noreen|date=2010 April 14|year=2010|month=April|volume=58}}"
        )
        == r"{{cite journal|last=Mahoney|first=Noreen|date=2010 April 14|volume=58}}"
    ), r"year not added when date already has it"
    correct3 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=2009-12-17}}"
    assert (
        genfixes.fix_citation_templates(correct3.replace(r"}}", r"|month=December}}")) == correct3
    ), r"number month removed when within date"


def test_fix_citation_templates_day_month_in_date() -> None:
    S = W.for_site(EN)
    correct1 = r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 October 2009 }}"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite book|title=a |url=http://books.google.com/foo | date=17 October |year=2009}}"
        )
        == correct1
    )
    assert genfixes.fix_citation_templates(
        r"now {{cite book|title=a |url=http://books.google.com/foo | date=October 17 |year=2009}}"
    ) == correct1.replace(r"17 October", r"October 17,")
    assert genfixes.fix_citation_templates(correct1) == correct1


def test_citation_publisher_to_work() -> None:
    S = W.for_site(EN)
    correct0 = r"{{cite news|url=http://www.timesonline.co.uk/foo494390.htm | date =2008-09-07 | work=The Times }}"
    correct1 = r"{{cite web|url=http://www.timesonline.co.uk/foo494390.htm | date =2008-09-07 | work=The Times }}"
    correct2 = r"{{citeweb|url=http://www.timesonline.co.uk/foo494390.htm | date =2008-09-07 | work = The Times }}"
    correct3 = r"{{cite web|url=http://www.timesonline.co.uk/foo494390.htm | work= |date =2008-09-07 | work = The Times }}"
    assert genfixes.citation_publisher_to_work(correct0.replace(r"work", r"publisher")) == correct0
    assert genfixes.citation_publisher_to_work(correct1.replace(r"work", r"publisher")) == correct1
    assert genfixes.citation_publisher_to_work(correct2.replace(r"work", r"publisher")) == correct2
    assert (
        genfixes.citation_publisher_to_work(correct3.replace(r"work =", r"publisher =")) == correct3
    )
    workalready1 = r"{{cite web|url=http://www.timesonline.co.uk/foo494390.htm | publisher=Media International |date =2008-09-07 | work = The Times }}"
    assert genfixes.citation_publisher_to_work(workalready1) == workalready1
    assert genfixes.citation_publisher_to_work(correct0) == correct0
    citeJournal = r"{{cite journal|url=http://www.timesonline.co.uk/foo494390.htm | date =2008-09-07 | publisher=The Times }}"
    assert genfixes.citation_publisher_to_work(citeJournal) == citeJournal


def test_fix_citation_dupe_fields() -> None:
    S = W.for_site(EN)
    correct = r"{{cite web|url=a |title=b | accessdate=11 May 2008|year=2008}}"
    correct2 = r"{{cite web|url=a |title=b | accessdate=11 May 2008|year=2008|work=here}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|year=2008}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year= | accessdate=11 May 2008|year=2008}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|year=2008|work=here}}"
        )
        == correct2
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |  year=   2008 | accessdate=11 May 2008|year=2008|work=here}}"
        )
        == correct2
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year= | accessdate=11 May 2008|year=2008|work=here}}"
        )
        == correct2
    )
    correct3 = r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|work=here there}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|work=here there|work=here there}}"
        )
        == correct3
    )
    nochange1 = r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|year=2004}}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1
    nochange2 = r"{{cite web|url=http://www.tise.com/abc|year=2008|page.php=7 |title=b |year=2008 | accessdate=11 May 2008}}"
    assert genfixes.fix_citation_templates(nochange2) == nochange2
    nochange3 = r"{{cite book|title=b |year=2008 | accessdate=11 May 2008|year=2004}}"
    assert genfixes.fix_citation_templates(nochange3) == nochange3
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net |title=|accessdate = 2008-10-08|title=hello}}"
        )
        == r"now {{cite web| url=http://site.net |accessdate = 2008-10-08|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net |title=|accessdate = 2008-10-08|title=hello|work=BBC}}"
        )
        == r"now {{cite web| url=http://site.net |accessdate = 2008-10-08|title=hello|work=BBC}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{Cite web| title = hello | url=http://site.net |accessdate = 2008-10-08|title=}}"
        )
        == r"now {{Cite web| title = hello | url=http://site.net |accessdate = 2008-10-08}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net |title=|accessdate = 2008-10-08| title = hello }}"
        )
        == r"now {{cite web| url=http://site.net |accessdate = 2008-10-08| title = hello }}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| title=hello|title=|url=http://site.net |date = 2008-10-08}}"
        )
        == r"now {{cite web| title=hello|url=http://site.net |date = 2008-10-08}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net |title=hello|first=|accessdate = 2008-10-08|first=}}"
        )
        == r"now {{cite web| url=http://site.net |title=hello|first=|accessdate = 2008-10-08}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| title=hello|url=http://site.net |date = 2008-10-08|title=HELLO}}"
        )
        == r"now {{cite web| title=hello|url=http://site.net |date = 2008-10-08|title=HELLO}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net |title=hello|accessdate = 2008-10-08|name=hello}}"
        )
        == r"now {{cite web| url=http://site.net |title=hello|accessdate = 2008-10-08|name=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net |title=hello|accessdate = 2008-10-08|last1=hello|last1=hello}}"
        )
        == r"now {{cite web| url=http://site.net |title=hello|accessdate = 2008-10-08|last1=hello|last1=hello}}"
    )


def test_merge_cite_web_access_date_year() -> None:
    S = W.for_site(EN)
    correct = r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008}}"
    correct2 = r"{{cite web|url=a |title=b |year=2008 | accessdate=May 11, 2008}}"
    correct3 = r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008 |work=c}}"
    correct4 = r"{{cite book|url=a |title=b |year=2008 | accessdate=11 May 2008 |work=c}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May| accessyear=2008}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May| accessyear = 2008  }}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=May 11| accessyear=2008}}"
        )
        == correct2
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=May 11| accessyear = 2008  }}"
        )
        == correct2
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May | accessyear = 2008 |work=c}}"
        )
        == correct3
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=a |title=b |year=2008 | accessdate=11 May | accessyear = 2008 |work=c}}"
        )
        == correct4
    )
    nochange2 = (
        r"{{cite podcast|url=a |title=b |year=2008 | accessdate=11 May |accessyear=2008 |work=c}}"
    )
    assert genfixes.fix_citation_templates(nochange2) == nochange2


def test_access_day_month_day() -> None:
    S = W.for_site(EN)
    a = r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|accessdaymonth=   }}"
        )
        == a
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|accessmonthday  =   }}"
        )
        == a
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|accessmonth  =   }}"
        )
        == a
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 |accessmonthday  = | accessdate=11 May 2008}}"
        )
        == a
    )
    notempty = (
        r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|accessdaymonth=Foo   }}"
    )
    assert genfixes.fix_citation_templates(notempty) == notempty


def test_fix_citation_templates_access_year() -> None:
    S = W.for_site(EN)
    a = r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|accessyear=2008   }}"
        )
        == a
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008| accessyear =  2008   }}"
        )
        == a
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 |accessyear=2008   | accessdate=11 May 2008}}"
        )
        == a
    )
    yearDoesNotMatch = (
        r"{{cite web|url=a |title=b |year=2008 | accessdate=11 May 2008|accessyear=Winter   }}"
    )
    assert genfixes.fix_citation_templates(yearDoesNotMatch) == yearDoesNotMatch


def test_fix_citation_templates_date_leading_zero() -> None:
    S = W.for_site(EN)
    a = r"{{cite web|url=a |title=b |year=2008 | accessdate=1 May 2008}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=01 May 2008}}"
        )
        == a
    )
    a0 = r"{{cite web|url=a |title=b | accessdate=1 May 2008 | date=May 1, 2008}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b | accessdate=01 May 2008 | date=May 01, 2008}}"
        )
        == a0
    )
    a2 = r"{{cite web|url=a |title=b |year=2008 | accessdate=1 May 1998}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=01 May 1998}}"
        )
        == a2
    )
    assert genfixes.fix_citation_templates(
        r"{{cite web|url=a |title=b |year=2008 | accessdate=01 May 1998 }}"
    ) == a2.replace(r"}}", r" }}")
    b = r"{{cite book|url=a |title=b | date=May 1, 2008}}"
    assert genfixes.fix_citation_templates(r"{{cite book|url=a |title=b | date=May 01, 2008}}") == b
    assert genfixes.fix_citation_templates(r"{{cite book|url=a |title=b | date=May 01 2008}}") == b
    b = r"{{cite book|url=a |title=b | date=May 1, 2020}}"
    assert genfixes.fix_citation_templates(r"{{cite book|url=a |title=b | date=May 01, 2020}}") == b
    c = r"{{cite book|url=a |title=b | date=May 1, 2008|author=Lee}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=a |title=b | date=May 01, 2008|author=Lee}}"
        )
        == c
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|url=a |title=b |year=2008 | date=May 01|author=Lee}}"
        )
        == c
    ), r"handles field merge and leading zero in date"
    URL = r"{{cite web|url=http://www.broadwaytovegas.com/October31,1999.html |title=Out of Chapter 11 bankruptcy |publisher=Broadwaytovegas.com |accessdate=2011-02-12}}"
    assert genfixes.fix_citation_templates(URL) == URL, r"No change to date spacing in URL"
    d = r"{{cite web|url=a |title=b |year=2008 | accessdate=1 Mar 2008}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|url=a |title=b |year=2008 | accessdate=01 Mar 2008}}"
        )
        == d
    )


def test_fix_citation_templates() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|format=HTML}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|format=HTM}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|format = HTML}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009| format  =HTML  }}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|     format=HTM}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{Citation|title=foo|url=http://site.net|format=HTML|year=2009}}"
        )
        == r"{{Citation|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|format=[[HTML]]}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|language={{en icon}}}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009|language=en}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|language={{sv icon}}}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009|language=sv}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|language={{de icon}}}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009|language=de}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|language={{el icon}}|publisher=Ser}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009|language=el|publisher=Ser}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|format=}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009|format=}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net/a.htm|year=2009|format=}}"
        )
        == r"{{cite web|title=foo|url=http://site.net/a.htm|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net/a.html|year=2009|format=}}"
        )
        == r"{{cite web|title=foo|url=http://site.net/a.html|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net/a.HTML|year=2009|format=}}"
        )
        == r"{{cite web|title=foo|url=http://site.net/a.HTML|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|origdate=}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web|title=foo|url=http://site.net|year=2009|origdate=2005}}"
        )
        == r"{{cite web|title=foo|url=http://site.net|year=2009|origdate=2005}}"
    )
    NoChangeSpacedEndashInTitle = r"{{cite web | author=IGN staff | year=2008 | title=IGN Top 100 Games 2008 – 2 Chrono Trigger | url=http://top100.ign.com/2008/ign_top_game_2.html | publisher=IGN | accessdate=March 13, 2009}}"
    assert (
        genfixes.fix_citation_templates(NoChangeSpacedEndashInTitle) == NoChangeSpacedEndashInTitle
    )
    NoChangeFormatGivesSize = (
        r"{{cite web|title=foo|url=http://site.net/asdfsadf.PDF|year=2009|format=150 MB}}"
    )
    assert genfixes.fix_citation_templates(NoChangeFormatGivesSize) == NoChangeFormatGivesSize


def test_fix_citation_templates_id() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|id=ASIN 123456789X|year=2009}}")
        == r"{{cite book|title=foo|asin=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|ID=ASIN 123456789X|year=2009}}")
        == r"{{cite book|title=foo|asin=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|id=ASIN 123456789X |year=2009}}")
        == r"{{cite book|title=foo|asin=123456789X |year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|id=ASIN: 123-45678-9-X|year=2009}}")
        == r"{{cite book|title=foo|asin=123-45678-9-X|year=2009}}"
    )
    correct = r"{{cite journal|title=foo|journal=foo|issn=1234-5678|year=2009}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN 12345678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, unspaced"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN: 12345678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, colon"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN : 12345678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, colon with space"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN= 12345678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, equal sign"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN = 12345678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, equal sign with space"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN 1234 5678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, spaced"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN 1234  5678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, spaced"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN 1234-5678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, dashed"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN 1234 - 5678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, dashed"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=issn 1234-5678|year=2009}}"
        )
        == correct
    ), r"id ISSN conversion, lowercase"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ID=issn 1234-5678|year=2009}}"
        )
        == correct
    ), r"ID ISSN conversion, uppercase ID"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|id=ISSN 1234567X|year=2009}}"
        )
        == r"{{cite journal|title=foo|journal=foo|issn=1234-567X|year=2009}}"
    ), r"id ISSN conversion, unspaced"
    BadISSN = r"{{cite journal|title=foo|journal=foo|id=issn 1234-56789X|year=2009}}"
    assert genfixes.fix_citation_templates(BadISSN) == BadISSN, r"No change, invalid ISSN"
    ExistingISSN = (
        r"{{cite journal|title=foo|journal=foo|id=issn 1234-5678|year=2009|issn= 1234-5678}}"
    )
    assert genfixes.fix_citation_templates(ExistingISSN) == ExistingISSN, (
        r"No change, existing issn"
    )
    ExistingISSN = (
        r"{{cite journal|title=foo|journal=foo|id=issn 1234-5678|year=2009|ISSN= 1234-5678}}"
    )
    assert genfixes.fix_citation_templates(ExistingISSN) == ExistingISSN, (
        r"No change, existing ISSN"
    )


def test_fix_citation_templates_issn_format() -> None:
    S = W.for_site(EN)
    correct = r"{{cite journal|title=foo|journal=foo|ISSN=1234-5678|year=2009}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ISSN=12345678|year=2009}}"
        )
        == correct
    ), r"format ISSN, unspaced"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ISSN=1234–5678|year=2009}}"
        )
        == correct
    ), r"format ISSN, dash"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ISSN=1234 5678|year=2009}}"
        )
        == correct
    ), r"format ISSN, spaced"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ISSN=1234  5678|year=2009}}"
        )
        == correct
    ), r"format ISSN, doublespaced"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ISSN=1234 - 5678|year=2009}}"
        )
        == correct
    ), r"format ISSN, dashed"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|ISSN=1234567X|year=2009}}"
        )
        == r"{{cite journal|title=foo|journal=foo|ISSN=1234-567X|year=2009}}"
    ), r"format ISSN, dashed"
    assert genfixes.fix_citation_templates(correct) == correct, r"No change, already correct"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite journal|title=foo|journal=foo|issn=12345678|year=2009}}"
        )
        == r"{{cite journal|title=foo|journal=foo|issn=1234-5678|year=2009}}"
    ), r"format lowercase issn"


def test_fix_citation_templates_isbn() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|id=ISBN 123456789X|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|id=ISBN 123456789X |year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X |year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|ID=ISBN 123456789X |year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X |year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|id=ISBN: 123-45678-9-X|year=2009}}")
        == r"{{cite book|title=foo|isbn=123-45678-9-X|year=2009}}"
    )
    doubleISBN = r"{{cite book|title=foo|id=ISBN 012345678X, 978012345678X|year=2009}}"
    assert genfixes.fix_citation_templates(doubleISBN) == doubleISBN, (
        r"no changes when two isbns present"
    )
    doubleISBN = r"{{cite book|title=foo|id=ISBN 012345678X ISBN 978012345678X|year=2009}}"
    assert genfixes.fix_citation_templates(doubleISBN) == doubleISBN, (
        r"no changes when two isbns present"
    )
    existingISBN = r"{{cite book|title=foo|id=ISBN 012345678X |isbn= 978012345678X|year=2009}}"
    assert genfixes.fix_citation_templates(existingISBN) == existingISBN, (
        r"no changes when isbn param already has value"
    )
    existingISBN = r"{{cite book|title=foo|id=ISBN 012345678X |ISBN= 978012345678X|year=2009}}"
    assert genfixes.fix_citation_templates(existingISBN) == existingISBN, (
        r"no changes when isbn param already has value"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=ISBN 123456789X|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|ISBN=ISBN 123456789X|year=2009}}")
        == r"{{cite book|title=foo|ISBN=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=ISBN  123456789X|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=ISBN123456789X|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=isbn123456789X|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=ISBN 123456789X.|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123456789X.|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123456789X..|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123456789X,|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123456789X;|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123456789X:|year=2009}}")
        == r"{{cite book|title=foo|isbn=123456789X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123–456–789–X :|year=2009}}")
        == r"{{cite book|title=foo|isbn=123-456-789-X|year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123–4–56789–X |year=2009}}")
        == r"{{cite book|title=foo|isbn=123-4-56789-X |year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123‐4‐56789‐X |year=2009}}")
        == r"{{cite book|title=foo|isbn=123-4-56789-X |year=2009}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|title=foo|isbn=123‒4‒56789‒X |year=2009}}")
        == r"{{cite book|title=foo|isbn=123-4-56789-X |year=2009}}"
    )


def test_fix_citation_templates_orig_year() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book | title=ABC | publisher=Pan  | origyear=1950 }}"
        )
        == r"{{cite book | title=ABC | publisher=Pan  | year=1950 }}"
    ), r"origyear to year when no year/date"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book | title=ABC | publisher=Pan  | origyear=1950 | year =}}"
        )
        == r"{{cite book | title=ABC | publisher=Pan  | year=1950 }}"
    ), r"origyear to year when blank year"
    nochange1 = r"{{cite book | title=ABC | publisher=Pan | year=2004 | origyear=1950 }}"
    nochange2 = r"{{cite book | title=ABC | publisher=Pan | date=May 2004 | origyear=1950 }}"
    nochange3 = r"{{cite book | title=ABC | publisher=Pan | origyear=11 May 1950 }}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1, (
        r"origyear valid when year present"
    )
    assert genfixes.fix_citation_templates(nochange2) == nochange2, (
        r"origyear valid when date present"
    )
    assert genfixes.fix_citation_templates(nochange3) == nochange3, (
        r"origyear not renamed when more than just a year"
    )


def test_fix_citation_templates_en_only() -> None:
    S = W.for_site(EN)
    bad = r"{{cite web|title=foo|url=http://site.net|year=2009|format=HTML}}"
    S = set_lang(r"fr")
    assert genfixes.fix_citation_templates(bad) == bad
    S = set_lang(r"en")
    assert (
        genfixes.fix_citation_templates(bad)
        == r"{{cite web|title=foo|url=http://site.net|year=2009}}"
    )


def test_fix_citation_templates_pages_pp() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=pp. 57–59}}")
        == r"{{cite book|author=Smith|title=Great|pages=57–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=pgs. 57–59}}")
        == r"{{cite book|author=Smith|title=Great|pages=57–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=pg. 57–59}}")
        == r"{{cite book|author=Smith|title=Great|pages=57–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=pp.57–59}}")
        == r"{{cite book|author=Smith|title=Great|pages=57–59}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|author=Smith|title=Great|pages=pp.&nbsp;57–59}}"
        )
        == r"{{cite book|author=Smith|title=Great|pages=57–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages= pp. 57–59}}")
        == r"{{cite book|author=Smith|title=Great|pages= 57–59}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|author=Smith|title=Great|pages=pp. 57-59|year=2007}}"
        )
        == r"{{cite book|author=Smith|title=Great|pages=57–59|year=2007}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|page=p. 57}}")
        == r"{{cite book|author=Smith|title=Great|page=57}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|page=p 57}}")
        == r"{{cite book|author=Smith|title=Great|page=57}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|page=pp 57}}")
        == r"{{cite book|author=Smith|title=Great|page=57}}"
    )
    nochange0 = r"{{cite book|author=Smith|title=Great|page= 57}}"
    nochange1 = r"{{cite book|author=Smith|title=Great|page= para 57}}"
    nochange2 = r"{{cite book|author=Smith|title=Great|page= P57}}"
    assert genfixes.fix_citation_templates(nochange0) == nochange0
    assert genfixes.fix_citation_templates(nochange1) == nochange1
    assert genfixes.fix_citation_templates(nochange2) == nochange2
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|author=Smith|title=Great|pages=pp. 57-59|nopp=yes}}"
        )
        == r"{{cite book|author=Smith|title=Great|pages=pp. 57–59|nopp=yes}}"
    )
    journal = r"{{cite journal|author=Smith|title=Great|page=p.57}}"
    assert genfixes.fix_citation_templates(journal) == journal


def test_fix_citation_templates_page_range_name() -> None:
    S = W.for_site(EN)
    correct = r"{{cite book|author=Smith|title=Great|pages=57–59}}"
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=pp. 57–59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|page=pp. 57–59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=57–59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=57 – 59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=57 – 59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|pages=57--59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|page=57–59}}")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|author=Smith|title=Great|page=57—59}}")
        == correct
    )
    assert genfixes.fix_citation_templates(
        r"{{cite book|author=Smith|title=Great|page=57, 59}}"
    ) == correct.replace(r"–", r", "), r"page -> pages for comma list of page numbers"
    correct = r"{{cite book|author=Smith|title=Great|pages=57&ndash;59}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|author=Smith|title=Great|pages=57 &ndash; 59}}"
        )
        == correct
    )
    nochange = r"{{cite book|author=Smith|title=Great|pages=12,255}}"
    assert genfixes.fix_citation_templates(nochange) == nochange
    correct2 = r"{{cite book |title=Evaluation of x |last=Office |year=2001 |pages=1–2 |accessdate=39 June 2011 }}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book |title=Evaluation of x |last=Office |year=2001 |page=1-2 |pages= |accessdate=39 June 2011 }}"
        )
        == correct2
    )
    correct3 = r"{{cite book | page = ੯-੨ }}"
    assert genfixes.fix_citation_templates(correct3) == correct3, (
        r"No change to non-standard numbers"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book|author=Smith|title=Great|page=59999990—59999999}}"
        )
        == r"{{cite book|author=Smith|title=Great|pages=59999990–59999999}}"
    )
    tooLong = r"{{cite book|author=Smith|title=Great|page=57999999000—59999999000}}"
    assert genfixes.fix_citation_templates(tooLong) == tooLong
    correct4 = r"{{cite book | at = 5-7 }}"
    assert genfixes.fix_citation_templates(correct4) == correct4, r"No change within at parameter"
    correct5 = r"{{cite book | page = [https://site.com/a-1990-1994 123] }}"
    assert genfixes.fix_citation_templates(correct5) == correct5, (
        r"No change to text within link in pages param"
    )


def test_fix_citation_templates_volume() -> None:
    S = W.for_site(EN)
    correct = "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume= 3|issue= 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=Vol. 3|issue=No. 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=Volumes 3|issue=No. 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=vol. 3|issue=No. 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=volume 3|issue=Issue 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=volume 3|issue=Issues 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=volume 3|issue=Issue 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=Vol. 3|issue=Nos. 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=volume 3 Issue 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume= 3| issue = 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=volume 3 Issues 3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume= 3| issue = 3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=3, Nos. 3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=3| issue =  3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
    )
    assert (
        genfixes.fix_citation_templates(
            "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=volume 3 numbers 3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
        )
        == "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume= 3| issue = 3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}} Robert M. Price (ed.), Bloomfield, NJ"
    )
    nochange1 = "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: A Pulp Thriller and Theological Journal |volume=special numbers 3–4|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm}}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1
    nochange2 = "*{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu #19: |volume=3 Issue 3|url=http://www.clare.ltd.new.net/cryptofcthulhu/blreanimator.htm|issue=December}} Robert M. Price (ed.), Bloomfield, NJ"
    assert genfixes.fix_citation_templates(nochange2) == nochange2
    nochange2 = (
        r"*{{cite journal |title=Lia |journal=Control |volume=I Nov 1962 II Dec 1962 |year=1962 }}"
    )
    assert genfixes.fix_citation_templates(nochange2) == nochange2, (
        r"No change to No as part of word in volume param"
    )


def test_cite_templates_page_range() -> None:
    S = W.for_site(EN)
    correct = "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3|pages = 140–148}}"
    assert (
        genfixes.fix_citation_templates(
            "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3|pages = 140-148}}"
        )
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3|pages = 140   - 148}}"
        )
        == correct
    )
    journalstart = "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3| "
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 140   - 148}}")
        == journalstart + r"pages = 140–148}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 140-8}}")
        == journalstart + r"pages = 140–8}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 140 -48}}")
        == journalstart + r"pages = 140–48}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 140   - 148}}")
        == journalstart + r"pages = 140–148}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 940   - 1083}}")
        == journalstart + r"pages = 940–1083}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 140-148, 150, 152-157}}")
        == journalstart + r"pages = 140–148, 150, 152–157}}"
    )
    nochange1 = "{{cite conference\r\n  | first = Owen\r\n  | title = System Lifecycle Cost\r\n  | booktitle = AIAA Space 2007\r\n  | pages = Paper No. AIAA-2007–6023\r\n  | year = 2007\r\n  }}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1


def test_harv_templates_page_range() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{harv|Smith|2005|pp=55–59}}")
        == r"{{harv|Smith|2005|pp=55–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{harvnb|Smith|2005|pp=55–59}}")
        == r"{{harvnb|Smith|2005|pp=55–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{harv|Smith|2005|pp=55 – 59}}")
        == r"{{harv|Smith|2005|pp=55–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{harv|Smith|2005|pp=55–59, 77-81}}")
        == r"{{harv|Smith|2005|pp=55–59, 77–81}}"
    )
    assert genfixes.fix_citation_templates(r"{{harv|Smith|at=7-8}}") == r"{{harv|Smith|at=7-8}}", (
        r"no change within at parameter"
    )
    assert genfixes.fix_citation_templates(r"{{rp|55–59, 77-81}}") == r"{{rp|55–59, 77–81}}"
    assert genfixes.fix_citation_templates(r"{{rp|77-81}}") == r"{{rp|77–81}}"
    assert genfixes.fix_citation_templates(r"{{rp|77}}") == r"{{rp|77}}"
    assert genfixes.fix_citation_templates(r"{{rp|77, 80}}") == r"{{rp|77, 80}}"
    assert genfixes.fix_citation_templates(r"{{rp|at=7-8}}") == r"{{rp|at=7-8}}", (
        r"rp: no change within at parameter"
    )


def test_sfn_templates_page_range() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{sfn|Smith|2005|pp=55-59}}")
        == r"{{sfn|Smith|2005|pp=55–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{sfn|Smith|2005|p=55-59}}")
        == r"{{sfn|Smith|2005|pp=55–59}}"
    )


def test_harv_templates_pp() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{harv|Smith|2005|p=55–59}}")
        == r"{{harv|Smith|2005|pp=55–59}}"
    ), r"renames p to pp for page range"
    assert (
        genfixes.fix_citation_templates(r"{{harvnb|Smith|2005|p=55–59}}")
        == r"{{harvnb|Smith|2005|pp=55–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{harvnb|Smith|2005|p=55&ndash;59}}")
        == r"{{harvnb|Smith|2005|pp=55&ndash;59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{harv|Smith|2005|p=55 – 59}}")
        == r"{{harv|Smith|2005|pp=55–59}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{harv|Smith|2005|p=55–59, 77-81}}")
        == r"{{harv|Smith|2005|pp=55–59, 77–81}}"
    )
    nochange = r"{{Harvnb|Shapiro|2010|p=271 (238–9)}}"
    assert genfixes.fix_citation_templates(nochange) == nochange


def test_cite_templates_page_sections() -> None:
    S = W.for_site(EN)
    journalstart = "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3| "
    nochange1 = "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3|pages = 140–7-2}}"
    assert genfixes.fix_citation_templates(nochange1) == nochange1
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 8-4}}")
        == journalstart + r"pages = 8-4}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 8-8}}")
        == journalstart + r"pages = 8-8}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 8-4, 17-34}}")
        == journalstart + r"pages = 8-4, 17-34}}"
    )
    assert (
        genfixes.fix_citation_templates(journalstart + r"pages = 17-34, 8-4}}")
        == journalstart + r"pages = 17-34, 8-4}}"
    )
    nochange2 = "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3|pages = 140‑7}}"
    nochange3 = "{{cite journal|first=Robert M.|last=Price|year=Candlemas 1984|title=Brian Lumley&mdash;Reanimator|\r\njournal=Crypt of Cthulhu |volume= 3|issue= 3|pages = 140&#8209;7}}"
    assert genfixes.fix_citation_templates(nochange2) == nochange2
    assert genfixes.fix_citation_templates(nochange3) == nochange3
    nochange4 = "*{{cite book\r\n | author = United States Navy\r\n | pages = 4-13 to 4-17\r\n | chapter = 4\r\n}}"
    assert genfixes.fix_citation_templates(nochange4) == nochange4, (
        r"two section links with word to"
    )
    nochange5a = "{{cite book | isbn = 084\r\n | pages = 3-262, 8-106, 15-20\r\n | url =\r\n}}"
    nochange5b = "{{cite book | isbn = 084\r\n | pages = 3-262, 3-106, 15-20\r\n | url =\r\n}}"
    assert genfixes.fix_citation_templates(nochange5a) == nochange5a, r"overlapping ranges"
    assert genfixes.fix_citation_templates(nochange5b) == nochange5b, (
        r"overlapping ranges, same start"
    )


def test_fix_citation_templates_ordinal_dates() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(
            "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=June 3rd, 2009|accessdate=January 15th, 2010}}"
        )
        == "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=June 3, 2009|accessdate=January 15, 2010}}"
    )
    assert (
        genfixes.fix_citation_templates(
            "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=June 3rd, 2009|accessdate=January 15th 2010}}"
        )
        == "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=June 3, 2009|accessdate=January 15, 2010}}"
    )
    assert (
        genfixes.fix_citation_templates(
            "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=June 3rd, 2009|accessdate=January 15, 2010}}"
        )
        == "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=June 3, 2009|accessdate=January 15, 2010}}"
    )
    assert (
        genfixes.fix_citation_templates(
            "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=3rd June 2009|accessdate=15th January 2010}}"
        )
        == "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=3 June 2009|accessdate=15 January 2010}}"
    )
    assert (
        genfixes.fix_citation_templates(
            "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=3rd June 2009|access-date=15th January 2010}}"
        )
        == "{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure as Blears quits|\r\npublisher=The BBC|date=3 June 2009|access-date=15 January 2010}}"
    )
    nochange = r"{{cite web|url=http://news.bbc.co.uk/1/hi/uk_politics/8080777.stm|title=Brown pressure at January 15th, 2010}}"
    assert genfixes.fix_citation_templates(nochange) == nochange
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web | url=http://www.foo.com| title=Bar | date=January 28th, 2013 | accessdate=March 07, 2013 | other=}}"
        )
        == r"{{cite web | url=http://www.foo.com| title=Bar | date=January 28, 2013 | accessdate=March 7, 2013 | other=}}"
    )


def test_uppercase_cite_fields() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(r"{{cite web|FOO=hello|title=hello}}")
        == r"{{cite web|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|uRL=http://members.bib-arch.org|title=hello}}")
        == r"{{cite web|url=http://members.bib-arch.org|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|UrL=http://members.bib-arch.org|title=hello}}")
        == r"{{cite web|url=http://members.bib-arch.org|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|Url=http://members.bib-arch.org|title=hello}}")
        == r"{{cite web|url=http://members.bib-arch.org|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite web|FOO=hello|title=hello}}")
        == r"{{Cite web|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web | FOO=hello|title=hello}}")
        == r"{{cite web | foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web | FOO = hello|title=hello}}")
        == r"{{cite web | foo = hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|FOO=hello|Title=hello}}")
        == r"{{cite web|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|FOO=hello|TITLE=hello}}")
        == r"{{cite web|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|FOO=hello|TITLE=hello | Work=BBC}}")
        == r"{{cite web|foo=hello|title=hello | work=BBC}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite web|FOO=hello|title=hello}}")
        == r"{{cite web|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite book|FOO=hello|title=hello}}")
        == r"{{cite book|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite news|FOO=hello|title=hello}}")
        == r"{{cite news|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite journal|FOO=hello|title=hello}}")
        == r"{{cite journal|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite paper|FOO=hello|title=hello}}")
        == r"{{cite paper|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite press release|FOO=hello|title=hello}}")
        == r"{{cite press release|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite hansard|FOO=hello|title=hello}}")
        == r"{{cite hansard|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{cite encyclopedia|FOO=hello|title=hello}}")
        == r"{{cite encyclopedia|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{citation|FOO=hello|title=hello}}")
        == r"{{citation|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite web|FOO=hello|title=hello}}")
        == r"{{Cite web|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite book|FOO=hello|title=hello}}")
        == r"{{Cite book|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite news|FOO=hello|title=hello}}")
        == r"{{Cite news|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite journal|FOO=hello|title=hello}}")
        == r"{{Cite journal|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite paper|FOO=hello|title=hello}}")
        == r"{{Cite paper|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite press release|FOO=hello|title=hello}}")
        == r"{{Cite press release|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite hansard|FOO=hello|title=hello}}")
        == r"{{Cite hansard|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Cite encyclopedia|FOO=hello|title=hello}}")
        == r"{{Cite encyclopedia|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(r"{{Citation|FOO=hello|title=hello}}")
        == r"{{Citation|foo=hello|title=hello}}"
    )
    assert (
        genfixes.fix_citation_templates(
            r"{{cite book | author=Smith | Title=Great Book | ISBN=15478454 | date=17 May 2004 }}"
        )
        == r"{{cite book | author=Smith | title=Great Book | ISBN=15478454 | date=17 May 2004 }}"
    )
    ISBN = r"{{cite book | author=Smith | title=Great Book | ISBN=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(ISBN) == ISBN
    ISSN = r"{{cite book | author=Smith | title=Great Book | ISSN=1547-8454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(ISSN) == ISSN
    OCLC = r"{{cite book | author=Smith | title=Great Book | OCLC=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(OCLC) == OCLC
    DOI = r"{{cite journal| author=Smith | title=Great Book | DOI=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(DOI) == DOI
    PMID = r"{{cite journal| author=Smith | title=Great Book | PMID=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(PMID) == PMID
    PMC = r"{{cite journal| author=Smith | title=Great Book | PMC=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(PMC) == PMC
    LCCN = r"{{cite journal| author=Smith | title=Great Book | PMC=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(LCCN) == LCCN
    ASIN = r"{{cite journal| author=Smith | title=Great Book | ASIN=15478454 | date=17 May 2004 }}"
    assert genfixes.fix_citation_templates(ASIN) == ASIN
    URL = r"{{cite news|url=http://www.expressbuzz.com/edition/story.aspx?Title=Catching++them+young&artid=rPwTAv2l2BY=&SectionID=fxm0uEWnVpc=&MainSectionID=ngGbWGz5Z14=&SectionName=RtFD/|pZbbWSsbI0jf3F5Q==&SEO=|title=Catching them young|date=August 7, 2009|work=[[The Indian Express]]|accessdate=2009-08-07}}"
    assert genfixes.fix_citation_templates(URL) == URL


def test_fix_citation_templates_dead_link_in_format() -> None:
    S = W.for_site(EN)
    correct = r"{{cite web | url=http://www.site.com/article100.html | title=Foo }} {{dead link|date=May 2010}}"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite web | url=http://www.site.com/article100.html | title=Foo | format= {{dead link|date=May 2010}}}}"
        )
        == correct
    ), r"{{dead link}} taken out of format field"
    assert genfixes.fix_citation_templates(
        r"{{cite web | url=http://www.site.com/article100.html | title=Foo | format= PDF {{dead link|date=May 2010}}}}"
    ) == correct.replace(r"Foo", r"Foo | format= PDF"), (
        r"Only {{dead link}} taken out of format field"
    )
    assert genfixes.fix_citation_templates(correct) == correct, r"no change when already correct"
    NodDead = r"{{cite web | url=http://www.site.com/article100.html | title=Foo | format= PDF}}"
    assert genfixes.fix_citation_templates(NodDead) == NodDead, (
        r"no change when no dead link in format field"
    )


def test_test_brackets_at_cite_template_url() -> None:
    S = W.for_site(EN)
    correct = r"now {{cite web|url=http://site.net|title=hello}} was"
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|url=[http://site.net]|title=hello}} was")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|url=http://site.net]|title=hello}} was")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|url=[http://site.net|title=hello}} was")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|url=[[http://site.net]|title=hello}} was")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|url=[http://site.net]]|title=hello}} was")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|url=[[http://site.net]]|title=hello}} was")
        == correct
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web|url = [http://site.net]  |title=hello}} was"
        )
        == r"now {{cite web|url = http://site.net  |title=hello}} was"
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web|title=hello |url=[www.site.net]}} was")
        == r"now {{cite web|title=hello |url=http://www.site.net}} was"
    ), r"bracket and protocol fix combined"
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite journal|title=hello | url=[http://site.net]] }} was"
        )
        == r"now {{cite journal|title=hello | url=http://site.net }} was"
    )
    assert (
        genfixes.fix_citation_templates(r"now {{cite web| url=http://site.net|title=hello}} was")
        == r"now {{cite web| url=http://site.net|title=hello}} was"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=[http://site.net cool site]|title=hello}} was"
        )
        == r"now {{cite web| url=[http://site.net cool site]|title=hello}} was"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=http://site.net cool site]|title=hello}} was"
        )
        == r"now {{cite web| url=http://site.net cool site]|title=hello}} was"
    )
    assert (
        genfixes.fix_citation_templates(
            r"now {{cite web| url=[http://site.net cool site|title=hello}} was"
        )
        == r"now {{cite web| url=[http://site.net cool site|title=hello}} was"
    )


def test_fix_citation_templates_archive_urls() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_citation_templates(
            r"{{cite news|title=Initiative is withdrawn|url=http://web.archive.org/web/20120930101428/http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|access-date=25 August 2010|newspaper=[[swissinfo]]|date=25 August 2010}}"
        )
        == r"{{cite news|title=Initiative is withdrawn|url=http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|access-date=25 August 2010|newspaper=[[swissinfo]]|date=25 August 2010|archive-url=http://web.archive.org/web/20120930101428/http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|archive-date=2012-09-30}}"
    ), r"URL is web.archive.org"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite news|title=Initiative is withdrawn|url=http://web.archive.org/web/20120930101428/http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|access-date=25 August 2010|website=archive.org|date=25 August 2010}}"
        )
        == r"{{cite news|title=Initiative is withdrawn|url=http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|access-date=25 August 2010|date=25 August 2010|archive-url=http://web.archive.org/web/20120930101428/http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|archive-date=2012-09-30}}"
    ), r"URL is web.archive.org"
    assert (
        genfixes.fix_citation_templates(
            r"{{cite news|title=Initiative is withdrawn|url=http://web.archive.org/web/20120930101428/http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|access-date=25 August 2010|website=web.archive.org|date=25 August 2010}}"
        )
        == r"{{cite news|title=Initiative is withdrawn|url=http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|access-date=25 August 2010|date=25 August 2010|archive-url=http://web.archive.org/web/20120930101428/http://www.swissinfo.ch/eng/swiss_news/Initiative_is_withdrawn.html?cid=26670404|archive-date=2012-09-30}}"
    ), r"URL, website is web.archive.org"
