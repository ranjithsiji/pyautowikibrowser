"""Port of AWB UnitTests/GenfixesTests.cs: general fixes through the Article pipeline.

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
assert_change = genFixes.assert_change  # GenfixesTestsBase methods
assert_not_changed = genFixes.assert_not_changed
gen_fixes = genFixes.gen_fixes
talk_gen_fixes = genFixes.talk_gen_fixes
from awb_x.core.article import Article, CategorisationOptions  # noqa: E402
from awb_x.core.article import SkipOptions as MockSkipOptions  # noqa: E402


def test_undersore_removal_in_external_link() -> None:
    S = W.for_site(EN)
    assert_not_changed(r"testing http://some_link testing")
    assert_not_changed(r"[http://some_link]")
    assert_change(r"[[http://some_link]] testing", r"[http://some_link] testing")


def test_dablinks_html_comments() -> None:
    S = W.for_site(EN)
    a1 = r"{{about||a|b}}"
    a2 = r"{{about||c|d}}"
    assert_not_changed(r"<!--" + a1 + a2 + r"-->")


def test_only_redirect_tagger_on_redirects() -> None:
    S = W.for_site(EN)
    genFixes.article_text = r"#REDIRECT [[Action of 12-17 January 1640]]"
    gen_fixes(r"Action of 12–17 January 1640")
    assert (
        genFixes.article_text
        == r"#REDIRECT [[Action of 12-17 January 1640]] {{R from modification}}"
    )


def test_external_links_in_image_captions() -> None:
    S = W.for_site(EN)
    assert_not_changed(
        r"[[Image:foo.jpg|Some http://some_crap.com]]",
        r"Test",
        r"Unlinked external link in image description",
    )
    assert_not_changed(
        r"[[Image:foo.jpg|Some [http://some_crap.com]]]",
        r"Test",
        r"Linked external link at end of image description",
    )
    assert_not_changed(
        r"[[File:foo.jpg|Some [http://some_crap.com]]]",
        r"Test",
        r"Linked external link at end of image description 2",
    )
    genFixes.article_text = r"[[Image:foo.jpg|Some [[http://some_crap.com]]]]"
    gen_fixes()
    assert genFixes.article_text.startswith(r"[[Image:foo.jpg|Some [http://some_crap.com]]]")


def test_link_whitespace() -> None:
    S = W.for_site(EN)
    assert_change(r"[[a ]]b", r"[[a]] b")
    assert_change(r"a[[ b]]", r"a [[b]]")
    assert_change(r"[[Foo bar|Foo_bar]]", r"[[Foo bar]]")
    assert_change(
        r"* [[ http://www.site.com/abcdef-abcdef-abcdef-abcdef-abcdef-abcdef-abcdef]]",
        r"* [http://www.site.com/abcdef-abcdef-abcdef-abcdef-abcdef-abcdef-abcdef]",
    )


def test_bullet_external_link() -> None:
    S = W.for_site(EN)
    assert_change(
        "==External link==\r\n[http://www.site.com Foo]",
        "==External links==\r\n* [http://www.site.com Foo]",
    )
    assert_change(
        "==External link==\r\n[http://www.site.com Foo]\r\n\r\n[http://www.site2.com Foo2]",
        "==External links==\r\n* [http://www.site.com Foo]\r\n* [http://www.site2.com Foo2]",
    )


def test_date_range() -> None:
    S = W.for_site(EN)
    assert_change(r"over July 09-11, 2009", r"over July 9–11, 2009")
    assert_change(
        r"{{Citation | title = Admiralty notice | date = March 1st – March 5th, 1747 | page = 1}}",
        r"{{Citation | title = Admiralty notice | date = March 1–5, 1747 | page = 1}}",
    )
    assert_not_changed(
        "First was won on 2007 February 7. \r\nIn 2007 May 22 team has won gold medals."
    )


def test_double_br() -> None:
    S = W.for_site(EN)
    assert_change(r"a<br><br>b", "a\r\n\r\nb")
    assert_change(r"a<br /><bR>b", "a\r\n\r\nb")
    assert_change(r"a<BR> <Br/>b", "a\r\n\r\nb")
    assert_change(r"<br><br>", r"")
    assert_change(r"a<br/br>b", r"a<br />b")
    assert_not_changed("a<br/>\r\n<br>b")
    assert_change("a\r\n<br/>\r\n<br>\r\nb", "a\r\n\r\nb")
    assert_change(r"{{foo|bar=a<br><br>b}}<br><br>quux", "{{foo|bar=a<br><br>b}}\r\n\r\nquux")
    assert_not_changed("<blockquote>\r\n<br><br></blockquote>")
    assert_not_changed(r"|a<br><br>b")
    assert_not_changed(r"!a<br><br>b")
    assert_not_changed(r"| foo || a<br><br>b")
    assert_not_changed(r"! foo !! a<br><br>b")
    assert_change(r"[[foo|bar]] a<br><br>b", "[[foo|bar]] a\r\n\r\nb")
    assert_change(r"foo! a<br><br>b", "foo! a\r\n\r\nb")
    assert_change(r"{{Orphan|date=September 2015}}<br>", r"{{Orphan|date=September 2015}}")
    assert_change(
        r"* {{Polish2|Krzepice (województwo dolnośląskie)|[[24 November]] [[2007]]}}<br><br>  a",
        "* {{Polish2|Krzepice (województwo dolnośląskie)|[[24 November]] [[2007]]}}\r\n\r\na",
    )


def test_test_paragraph_formatter() -> None:
    S = W.for_site(EN)
    assert_change(r"<p>", r"")
    assert_change(r"a</p>b", "a\r\n\r\nb")
    assert_change(r"<p>a</p>b", "a\r\n\r\nb")
    assert_change("a\r\n<p>b", "a\r\n\r\nb")
    assert_not_changed(r"| a<p>b")
    assert_not_changed(r"! a<p>b")
    assert_not_changed("foo\r\n| a<p>b")
    assert_not_changed("foo\r\n! a<p>b")
    assert_not_changed("foo! a\r\n\r\nb")
    assert_not_changed("{{foo|bar}} a\r\n\r\nb")
    assert_not_changed(r"!<p>")
    assert_not_changed(r"|<p>")
    assert_not_changed(r"<blockquote>a<p>b</blockquote>")
    assert_not_changed("<blockquote>\r\na<p>b\r\n</blockquote>")
    assert_not_changed(r"{{cquote|a<p>b}}")
    assert_not_changed("{{cquote|foo\r\na<p>b}}")


def test_dont_rename_image_to_file() -> None:
    S = W.for_site(EN)
    assert_not_changed(r"[[Image:foo]]")
    assert_not_changed(r"[[File:foo]]")


def test_cite_two_date_fixes() -> None:
    S = W.for_site(EN)
    assert_change(
        r"{{cite web | url = http://www.census.gov/popest/geographic/boundary_changes/index.html | year=2010 |title = Boundary Changes | date = 2010-1-1 }}",
        r"{{cite web | url = http://www.census.gov/popest/geographic/boundary_changes/index.html |title = Boundary Changes | date = 2010-01-01 }}",
    )
    assert_change(r"Over March 4th - March 10th, 2012 then.", r"Over March 4–10, 2012 then.")
    assert_change(
        r"{{cite web| url=http://www.site.com/f | title=A | date= June 29th, 2012 08:44}}",
        r"{{cite web| url=http://www.site.com/f | title=A | date= June 29, 2012<!-- 08:44-->}}",
    )
    assert_change(
        r"{{cite web| url=http://www.site.com/f | title=A | date= 29 June, 2012| year=2012}}",
        r"{{cite web| url=http://www.site.com/f | title=A | date= 29 June 2012}}",
    )


def test_cite_work_link() -> None:
    S = W.for_site(EN)
    assert_change(r"{{cite news|work=''[[foo|foo]]''}}", r"{{cite news|work=[[foo]]}}")


def test_unbalanced_bracket_rename_template_parameter() -> None:
    S = W.for_site(EN)
    S = set_site(renamed_template_parameters_text="")
    S = set_site(
        renamed_template_parameters_text=r"{{AWB rename template parameter|cite web|acccessdate|accessdate}}"
    )
    assert_change(
        r"A.<ref>{{cite web| url=http://www.site.com | title = ABC | acccessdate = 20 May 2012</ref> {{reflist}}",
        r"A.<ref>{{cite web| url=http://www.site.com | title = ABC | accessdate = 20 May 2012}}</ref> {{reflist}}",
    )


def test_unbalanced_bracket_cite() -> None:
    S = W.for_site(EN)
    assert_change(
        "<ref>{{cite web}lastl=Levine|firstl=Syndey|title=Cannes15|url=http://blogs.i.com/s|website=I.com|accessdate=May 17, 2015}}</ref>\r\n{{reflist}}",
        "<ref>{{cite web|lastl=Levine|firstl=Syndey|title=Cannes15|url=http://blogs.i.com/s|website=I.com|accessdate=May 17, 2015}}</ref>\r\n{{reflist}}",
    )
    assert_change(
        "<ref>{{cite web{lastl=Levine|firstl=Syndey|title=Cannes15|url=http://blogs.i.com/s|website=I.com|accessdate=May 17, 2015}}</ref>\r\n{{reflist}}",
        "<ref>{{cite web|lastl=Levine|firstl=Syndey|title=Cannes15|url=http://blogs.i.com/s|website=I.com|accessdate=May 17, 2015}}</ref>\r\n{{reflist}}",
    )
    assert_change(
        "Foo<ref>a</ref>\r\n\r\n==References==\r\n((Reflist}}",
        "Foo<ref>a</ref>\r\n\r\n==References==\r\n{{Reflist}}",
    )
    assert_not_changed(
        "'''Peroni''' is<ref>{{cite web|url=http://www.assobirra.it|form.\r\n\r\n==Nastro Azzurro==\r\nW.<ref>[http://www.millerbrands.co.uk]. 0.</ref> T\r\n\r\n==References==\r\n{{reflist}}"
    )
    assert_not_changed(
        "'''J''' [http://foo.com|title=2014] in [[W–S|A]].\r\n\r\n{{DEFAULTSORT:P, A}}\r\n[[Category:1960]]"
    )


def test_unbalanced_brackets_template_redirects() -> None:
    S = W.for_site(EN)
    S = set_site(template_redirects_text="")
    S = set_site(template_redirects_text=r"{{tl|facts}} → {{tl|citation needed}}")
    assert_change(r"Foo.{facts}}", r"Foo.{{citation needed}}")


def test_wikia() -> None:
    S = W.for_site(EN)
    S = set_project(r"en", "wikia")
    assert_not_changed(
        "{{BLP sources|date=May 2010}}\r\n'''Bob Jones''' (born 1987 in Smith).<ref>a</ref>\r\n\r\n==References==\r\n{{reflist}}\r\n\r\n{{DEFAULTSORT:Jones, Bob}}\r\n[[Category:Living people]]\r\n[[Category:1987 births]]",
        r"nothing added",
    )
    assert_not_changed(
        "{{Unreferenced|date=December 2009}}\r\n{{Dead end|date=November 2006}}\r\n{{Notability|1=Music|date=September 2010}}\r\n{{Advert|date=December 2007}}\r\n'''Band''' is.\r\n\r\n[[Category:Blues rock groups]]\r\n\r\n\r\n{{Norway-band-stub}}",
        r"no multiple issues added",
    )
    S = set_project(r"en", "wikipedia")


def test_cite_missing_closing_curly_brace_pair_table() -> None:
    S = W.for_site(EN)
    MissingClosingCurlyBracePair = "'''Foo''' is great.\r\n\r\n{|\r\n||\r\n||Foo<ref>{{cite web | title = foo2 | year=2010 | url=http://www.site.com </ref>\r\n||\r\n||x\r\n||y\r\n|}\r\n\r\n==Refs==\r\n{{reflist}}"
    assert_change(
        MissingClosingCurlyBracePair, MissingClosingCurlyBracePair.replace(r" </ref>", r"}}</ref>")
    )


def test_multiple_issues() -> None:
    S = W.for_site(EN)
    before = "{{Unreferenced|auto=yes|date=December 2009}}\r\n{{Underlinked|date=November 2006}}\r\n{{Notability|1=Music|date=September 2010}}\r\n{{Autobiography|date=December 2007}}\r\n'''Band''' is.\r\n\r\n[[Category:Blues rock groups]]\r\n\r\n\r\n{{Norway-band-stub}}"
    after = "{{Multiple issues|\r\n{{Unreferenced|date=December 2009}}\r\n{{Underlinked|date=November 2006}}\r\n{{Notability|1=Music|date=September 2010}}\r\n{{Autobiography|date=December 2007}}\r\n}}\r\n\r\n'''Band''' is.\r\n\r\n[[Category:Blues rock groups]]\r\n\r\n{{Norway-band-stub}}"
    assert_change(before, after)
    genFixes.article_text = "{{POV|date=May 2016}}\r\n{{NPOV|date=May 2016}}\r\n{{Orphan|date=May 2016}}\r\n{{Dead end|date=May 2016}}\r\n\r\nMinor bug"
    S = set_site(template_redirects_text="")
    S = set_site(template_redirects_text=r"{{tl|NPOV}} → {{tl|POV}}")
    gen_fixes(r"A")
    assert (
        "{{Multiple issues|\r\n{{POV|date=May 2016}}\r\n{{Orphan|date=May 2016}}\r\n{{Dead end|date=May 2016}}\r\n}}"
        in genFixes.article_text
    ), r"No excess pipes left when MI incorporates duplicate tags"


def test_heading_whitespace() -> None:
    S = W.for_site(EN)
    foo = "x\r\n\r\n== Events ==\r\n<onlyinclude>\r\n=== By place ===\r\n==== Roman Empire ====\r\n* Emperor "
    foo2 = "x\r\n\r\n== Events ==\r\n<onlyinclude>\r\n\r\n=== By place ===\r\n==== Roman Empire ====\r\n* Emperor"
    assert_change(foo, foo2)
    HeadingWithOptionalSpace = "x\r\n\r\n== Events ==\r\ny"
    assert_not_changed(HeadingWithOptionalSpace)
    HeadingWithoutOptionalSpace = "x\r\n\r\n==Events==\r\ny"
    assert_not_changed(HeadingWithoutOptionalSpace)
    CommentThenHeading = "x\r\n\r\n<!-- comment here-->\r\n==Events==\r\ny"
    assert_not_changed(CommentThenHeading)


def test_embolden_born() -> None:
    S = W.for_site(EN)
    genFixes.article_text = r"John Smith (1985-) was great."
    gen_fixes(r"John Smith")
    assert genFixes.article_text == r"'''John Smith''' (born 1985) was great."


def test_fix_citation_templates() -> None:
    S = W.for_site(EN)
    assert_not_changed(
        r"* {{cite book |editor1-first=T |editor1-last=C |title=A |edition=E |publisher=M |page=7-124<!--HYPHEN PAGE--> }}",
        r"Text",
        r"No change to hyphen in page when comment",
    )
    assert_not_changed(
        "{{Infobox settlement\r\n<!--See the Table at Infobox Settlement for all fields and descriptions of usage-->\r\n<!-- Basic info  ---------------->| name = Z}}",
        r"ABC",
        r"Template with newline, comment, newline in name",
    )
    assert_not_changed(
        r'{{cite web |url=https://d.gov/t72|title= "2020 Census: Puerto Rico"|website=A}}'
    )
    assert_not_changed(
        r'{{cite news|title="Herald" Week-End Magazine The wreek of the malabar, Easter 1931.|url=http://trove.nla.gov.au/newspaper/|date=29 March 1947}}'
    )
    assert_not_changed(
        r'{{cite web |author=I|date=17 February 2017 |title=Solar Impulse: "1000 solutions pour un monde durable" |url=http://www.a.com}}'
    )


def test_refs_punctuation_reorder() -> None:
    S = W.for_site(EN)
    S = set_project(r"en", "wikisource")
    genFixes.article_text = "* Andrew influences.<ref name=HerdFly>{{cite book |last=Herd |first=Andrew Dr |title=The Fly }}</ref>\r\n\r\n* Hills  works<ref>{{cite book |last=McDonald }}</ref>,<ref>{{cite book |last=Gingrich }}</ref>,<ref>{{cite book |location=Norwalk, CT }}</ref>,<ref name=HerdFly/> {{Reflist}}"
    correct = "* Andrew influences.<ref name=HerdFly>{{cite book |last=Herd |first=Andrew Dr |title=The Fly }}</ref>\r\n\r\n* Hills  works,<ref name=HerdFly/><ref>{{cite book |last=McDonald }}</ref><ref>{{cite book |last=Gingrich }}</ref><ref>{{cite book |location=Norwalk, CT }}</ref> {{Reflist}}"
    gen_fixes(r"Test")
    assert genFixes.article_text == correct
    genFixes.article_text = "A<ref>ABC</REF>.\r\n\r\n==References==\r\n{{reflist}}"
    gen_fixes(r"Test")
    assert genFixes.article_text == "A.<ref>ABC</ref>\r\n\r\n==References==\r\n{{reflist}}"
    S = set_project(r"en", "wikipedia")


def test_merge_refs_errors() -> None:
    S = W.for_site(EN)
    genFixes.article_text = "A.<ref name=”XXL Mag”>{{cite web|url=http://www.somesite.com/online/?p=70413 |title=a}}</ref><ref name=c>x</ref>\r\n\r\nB.<ref name=c />\r\nC.<ref name=”XXL Mag”>{{cite web|url=http://www.somesite.com/online/?p=70413 |title=a}}</ref>\r\n\r\n==References==\r\n{{reflist}}"
    gen_fixes(r"Test")
    assert (r'<ref name="XXL Mag">' in genFixes.article_text) and (
        r'<ref name="XXL Mag"/>' in genFixes.article_text
    ), r"Fix the ref quote errors, then merge them"


def test_ref_punctuation_spacing() -> None:
    S = W.for_site(EN)
    genFixes.article_text = (
        r"Targ<ref>[http://www.site.com] Lubawskiego</ref>.It adopted {{reflist}}"
    )
    gen_fixes(r"Test")
    correct = r"Targ.<ref>[http://www.site.com] Lubawskiego</ref> It adopted {{reflist}}"
    assert genFixes.article_text == correct


def test_reorder_punctuation() -> None:
    S = W.for_site(EN)
    S = set_project(r"en", "wikisource")
    correct = 'FOOBAR decreases.<ref name="G">{{cite journal | author = M| title = R by p53: s}}</ref><ref name="Bensaad"/> It catalyses the removal of a phosphate group from fructose (F-2,6-BP):<ref name="G"/><ref name="B"/>\r\n\r\n==References==\r\n{{Reflist}}'
    genFixes.article_text = 'FOOBAR decreases<ref name="G">{{cite journal | author = M| title = R by p53: s}}</ref><ref name="Bensaad"/>. It catalyses the removal of a phosphate group from fructose (F-2,6-BP)<ref name="B"/><ref name="G"/>:\r\n\r\n==References==\r\n{{Reflist}}'
    gen_fixes(r"Test")
    assert genFixes.article_text == correct, r"References section exists"
    genFixes.article_text = r'FOOBAR decreases<ref name="G">{{cite journal | author = M| title = R by p53: s}}</ref><ref name="Bensaad"/>. It catalyses the removal of a phosphate group from fructose (F-2,6-BP)<ref name="B"/><ref name="G"/>:'
    gen_fixes(r"Test")
    assert genFixes.article_text == correct, r"References section does not exist"
    S = set_project(r"en", "wikipedia")


def test_perform_universal_general_fixes() -> None:
    S = W.for_site(EN)
    H = HideText()
    S = MockSkipOptions()
    ar1 = Article(r"Hello", r" '''Hello''' world text")
    ar1.perform_universal_general_fixes()
    ar1.perform_general_fixes(parser, H, S, False, False, False)
    assert ar1.article_text == r"'''Hello''' world text"


def test_only_general_fixes_changed() -> None:
    S = W.for_site(EN)
    H = HideText()
    S = MockSkipOptions()
    ar1 = Article(r"Hello", r" '''Hello''' world text")
    ar1.perform_universal_general_fixes()
    ar1.perform_general_fixes(parser, H, S, False, False, False)
    assert ar1.only_general_fixes_changed, r"Universal genfixes made change"
    ar2 = Article(r"Category:Hello", r" Text [[Category:Foo]]")
    ar2.categorisation(CategorisationOptions(1), parser, False, r"Foo", r"Foo2", False)
    assert ar2.article_text == r" Text [[Category:Foo2]]", r"Category rename operation"
    ar2.perform_universal_general_fixes()
    assert ar2.article_text == r"Text [[Category:Foo2]]", r"Universal genfix trim"
    ar2.perform_general_fixes(parser, H, S, False, False, False)
    assert not (ar2.only_general_fixes_changed), r"Categorisation did cause change"


def test_external_links_br() -> None:
    S = W.for_site(EN)
    genFixes.article_text = "==External links==\r\n[http://foo.com]</br>\r\n[http://foo2.com]</br>\r\n\r\n[[Category:A]]"
    gen_fixes(r"Test")
    correct = (
        "==External links==\r\n* [http://foo.com]\r\n* [http://foo2.com]\r\n\r\n[[Category:A]]"
    )
    assert genFixes.article_text == correct, r"Clean br at end of lists"
    genFixes.article_text = "==External links==\r\n[http://foo.com]\r\n<br>\r\n[http://foo2.com]"
    correct = "==External links==\r\n* [http://foo.com]\r\n* [http://foo2.com]"
    gen_fixes(r"Test")
    assert genFixes.article_text == correct, r"Clean br between list items"


def test_bold_title() -> None:
    # Hand-ported (the for loop was not converted).
    genFixes.article_text = "\r\n==Foo.(here)==\r\nFoo.(here) is a bar While remaining upright may be the primary goal of beginning riders"
    gen_fixes(r"Foo.(here)")
    assert (
        genFixes.article_text
        == "'''Foo.(here)''' is a bar While remaining upright may be the primary goal of beginning riders"
    )

    genFixes.article_text = (
        "{{Short description|Japanese video game developer}}\r\n\r\n{{nihongo foot|'''Treasure Co., Ltd.'''|株式会社トレジャー|''Kabushiki-gaisha Torejā''||lead=yes|group=lower-alpha}} is a Japanese\r\nTreasure grew a [[cult following]]."
        + "Some long test to make article long enough so 5 percent rule is relevant." * 100
    )
    original_article_text = genFixes.article_text
    gen_fixes(r"Treasure (company)")
    assert genFixes.article_text == original_article_text


def test_redirects_simplify_links() -> None:
    S = W.for_site(EN)
    genFixes.article_text = r"#REDIRECT[[foo|foo]]"
    gen_fixes(r"test")
    assert genFixes.article_text == r"#REDIRECT[[foo]]"


def test_redirects_defaultsort() -> None:
    S = W.for_site(EN)
    genFixes.article_text = "#REDIRECT[[Foo]]\r\n[[Category:One]]"
    gen_fixes(r"Foé")
    assert (
        genFixes.article_text == "#REDIRECT[[Foo]]\r\n\r\n{{DEFAULTSORT:Foe}}\r\n[[Category:One]]"
    )


def test_cats_and_default_sort() -> None:
    S = W.for_site(EN)
    genFixes.article_text = "{{infobox person}}\r\n'''John Smith''' (born 11 April 1990) is great."
    gen_fixes(r"John Smith")
    assert r"[[Category:1990 births]]" in genFixes.article_text, r"birth category"
    assert r"[[Category:Living people]]" in genFixes.article_text, r"living people"
    assert r"{{DEFAULTSORT:Smith, John}}" in genFixes.article_text, r"human name defaultsort"


def test_cats_and_default_sort2() -> None:
    S = W.for_site(EN)
    genFixes.article_text = (
        "{{infobox person}}\r\n'''Cecilia Uddén''' (born 11 April 1990) is great."
    )
    gen_fixes(r"Cecilia Uddén")
    assert r"[[Category:1990 births]]" in genFixes.article_text, r"birth category"
    assert r"[[Category:Living people]]" in genFixes.article_text, r"living people"
    assert r"{{DEFAULTSORT:Udden, Cecilia}}" in genFixes.article_text, (
        r"human name defaultsort without special characters"
    )
    genFixes.article_text = (
        "{{infobox person}}\r\n'''İbrahim Smith''' (born 12 April 1991) is great."
    )
    gen_fixes(r"İbrahim Smith")
    assert r"{{DEFAULTSORT:Ibrahim Smith}}" in genFixes.article_text, (
        r"human name defaultsort (diacritics removed)"
    )


def test_named_and_unnamed_refs() -> None:
    S = W.for_site(EN)
    genFixes.article_text = 'Z<ref name = "Smith63">Smith (2004), p.&nbsp;63</ref> in all probability.<ref>Smith (2004), p.&nbsp;63</ref> For.<ref>Smith (2004), p.&nbsp;63</ref>\r\n\r\nA.<ref name="S63">Smith (2004), p.&nbsp;63</ref>\r\n\r\nGod.<ref name="S63" />\r\n\r\n==References==\r\n{{reflist|2}}'
    gen_fixes()
    assert (
        genFixes.article_text
        == 'Z<ref name = "Smith63">Smith (2004), p.&nbsp;63</ref> in all probability.<ref name="Smith63"/> For.<ref name="Smith63"/>\r\n\r\nA.<ref name="Smith63">Smith (2004), p.&nbsp;63</ref>\r\n\r\nGod.<ref name="Smith63"/>\r\n\r\n==References==\r\n{{reflist|2}}'
    )


def test_cite_url() -> None:
    S = W.for_site(EN)
    assert_not_changed(
        r"*{{cite thesis |last=A |first=S |title=Categorizing |url=http://urn.fi/URN:ISBN:978-999-61-9999-2 |year=2010 }}"
    )
    assert_change(
        r"{{cite web | url = www.site.com/a.pdf | title = Something }}",
        r"{{cite web | url = http://www.site.com/a.pdf | title = Something }}",
    )
    assert_change(
        r"{{cite web | url = WWW.site.com/a.pdf | title = Something }}",
        r"{{cite web | url = http://WWW.site.com/a.pdf | title = Something }}",
    )


def test_living_people() -> None:
    S = W.for_site(EN)
    genFixes.article_text = "{{Multiple issues|{{More citations needed|date=July 2015}}{{BLP sources|date=July 2015}}}}\r\n\r\n{{Infobox football biography\r\n| name = Am\r\n| birth_date  = 3 May 1983\r\n}}\r\n\r\n'''Amir'''  is.<ref>http://ca.soccerway.com/players/</ref>\r\n\r\n==References==\r\n<references/>\r\n\r\n{{iran-footy-bio-stub}}\r\n\r\n{{DEFAULTSORT:Amir}}\r\n[[Category:A players]]"
    gen_fixes()
    assert r"{Multiple issues" not in genFixes.article_text
    assert r"Category:Living people" in genFixes.article_text


def test_fix_syntax_images() -> None:
    S = W.for_site(EN)
    t = "Foo\r\n<Gallery>\r\nFile:T（p13 T2).jpg|\r\nFile:T（ｐ16_T3）.jpg|a\r\nFile:T（ｐ22 T5）.jpg|aa\r\n</Gallery>\r\n\r\nBar"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, (
        r"No change to unbalanced brackets in images, Chinese brackets"
    )
    t = "Foo\r\n\r\nOther [[Image:A.png|Now [[foo]]]]\r\nBar"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to unbalanced brackets in images, simple"
    t = "Foo\r\n\r\nOther [[Image:A.png|foo [[bar]] there]]\r\nBar"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to unbalanced brackets in images, simple 2"
    t = r"[[File:Miguel.jpg|x120px|thumb|[[Miguel Enríquez (privateer)|Miguel Enríquez]]]][[File:Demetrio O'Daly.jpg|x120px|thumb|[[Demetrio O'Daly]]]] [[File:Antonio Valero Bernabe.gif|x120px|thumb|[[Antonio Valero de Bernabé]]]] [[File:Manuel Rojas drawing.jpg|x120px|thumb|[[Manuel Rojas (independence leader)|Manuel Rojas]]]] [[File:CIVILWAR,PRSOLDIERsmall2.jpg|x120px|thumb|[[Augusto Rodríguez (soldier)|Augusto Rodríguez]]]] [[File:General Juan Luis Rivera.jpg|x120px|thumb|[[Juan Ríus Rivera]]]] [[File:GenSemidei.jpg|x120px|thumb|[[José Semidei Rodríguez]]]]"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to unbalanced brackets in images, 3"
    t = r"[[File:Mat.pdf|thumb|Same|link=https://en.wikipedia.org/wiki/File:Mat.pdf?page=2]]"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to brackets/images, 4"
    t = r"[[File:Milky way.jpg|sans_cadre|centre|Representation]]"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to underscores in image parameters"


def test_fix_syntax_brackets() -> None:
    S = W.for_site(EN)
    t = "*[https://www.site.com [XXX<nowiki>]</nowiki> XXX]\r\n\r\n{{s | title=[[Party (1931)|XXX]] | before=}}"
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to unbalanced brackets from nowiki"
    t = r"A <nowiki>[</nowiki>[[sub-creation]]] story."
    genFixes.article_text = t
    gen_fixes()
    assert t == genFixes.article_text, r"No change to unbalanced brackets from nowiki, 2"


def test_reorder_references_not_en_wp() -> None:
    S = W.for_site(EN)
    t = "'''Article''' is great.<ref name = \"Fred1\">So says Fred</ref>\r\nArticle started off pretty good,<ref>So says John</ref><ref name = \"Fred1\" /> and finished well.\r\nEnd of.\r\n\r\n==References\r\n{{Reflist}}"
    genFixes.article_text = t
    gen_fixes()
    assert genFixes.article_text == t, (
        r"No change: ReorderReferences not applied within en-wp genfixes"
    )
    S = set_lang(r"uk")
    t = "'''Article''' is great.<ref name = \"Fred1\">So says Fred</ref>\r\nArticle started off pretty good,<ref>So says John</ref><ref name = \"Fred1\" /> and finished well.\r\nEnd of.\r\n\r\n==References\r\n{{Reflist}}"
    genFixes.article_text = t
    gen_fixes()
    assert genFixes.article_text == t, (
        r"No change: ReorderReferences not applied within uk-wp genfixes"
    )
    S = set_lang(r"en")
    S = set_lang(r"ru")
    t = "'''Article''' is great.<ref name = \"Fred1\">So says Fred</ref>\r\nArticle started off pretty good,<ref>So says John</ref><ref name = \"Fred1\" /> and finished well.\r\nEnd of.\r\n\r\n==References\r\n{{Reflist}}"
    genFixes.article_text = t
    gen_fixes()
    assert genFixes.article_text == t, (
        r"No change: ReorderReferences not applied within ru-wp genfixes"
    )
    S = set_lang(r"en")


def test_fix_unbalanced_brackets() -> None:
    S = W.for_site(EN)
    unfixable = "Symbolist style: [[he abandoned realism and steered his work towards a more mythical and aestheticizing, almost evasionist tone, as denoted in his decorative plafonds for the [[Cau Ferrat]] of [[Sitges]] in 1896 (''La Pintura'', ''La Poesía'', ''La Música'').<ref name=\":19\">{{harvtxt|Hofstätter|1981|p=257}}</ref> With the beginning of the 20th century he moved more towards landscape painting, still with a certain symbolist stamp but with a greater tendency towards realism.<ref>{{harvtxt|Socías|1987|p=45}}</ref>\r\n[[File:Alexandre_de_Riquer_-_Composition_with_winged_nymph_at_sunrise_-_Google_Art_Project.jpg|left|thumb|''Composition with winged nymph at sunrise'' (1887), by [[Alexandre de Riquer]], [[National Art Museum of Catalonia]], [[Barcelona]]]]\r\n[[Alexandre de Riquer]] was a painter, engraver, decorator, illustrator and poster artist, as well as a poet and art theorist. He lived for a time in London, where he was influenced by preraphaelitism and the [[Arts & Crafts]] movement. He excelled especially in book illustration (''Crisantemes'', 1899; ''Anyoranses'', 1902) and in the design of [[Ex Libris (bookplate)|ex-libris]], a genre he raised to heights of great quality.<ref>{{harvtxt|Hofstätter|1981|pp=256–257}}</ref>\r\n[[File:Somni_Joan_Brull.jpg|thumb|''Ensueño'' (1897) by [[Joan Brull]], National Museum of Art of Catalonia, Barcelona]]\r\n[[Joan Llimona]], founder of the [[Cercle Artístic de Sant Lluc]], leaned towards a mysticism of strong religiosity, as denoted in his paintings for the dome of the camarín of the church of the [[Monastery of Montserrat]] (1898) or the murals of the dining room of the Recolons house in Barcelona (1905).<ref name=\":19\" /> Trained at the [[Escola de la Llotja]], he furthered his studies in Italy for four years. His first works were of genre costumbrista, but by 1890 his painting focused on religion, with compositions that combine formal realism with the idealism of the subjects, with a style sometimes compared to [[Jean-François Millet|Millet]] and Puvis de Chavannes.<ref>{{harvtxt|Socías|1987|pp=39–41}}</ref>\r\n\r\n==References==\r\n{{reflist}}"
    genFixes.article_text = unfixable
    gen_fixes()
    assert genFixes.article_text == unfixable, r"no change to unfixable square brackets"


def test_add_wiki_project_banner_shell() -> None:
    S = W.for_site(EN)
    AllCommented = "<!-- {{WikiProject a|text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject c|text}\r\n{{WikiProject d|text}} -->"
    genFixes.article_text = AllCommented
    talk_gen_fixes()
    assert genFixes.article_text == AllCommented, (
        r"no WikiProject banner shell addition when templates all commented out"
    )
    a = "{{Talk header}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject a |text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject Biography|living=yes}}\r\n{{WikiProject c|text}}\r\n| blp=yes\r\n}}\r\n"
    genFixes.article_text = "{{Talk header}}\r\n{{WikiProject a |text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject Biography|living=yes}}\r\n{{WikiProject c|text}}"
    talk_gen_fixes()
    assert genFixes.article_text == a, r"Adds WikiProject banner shell below talk header"
    a = "{{Talk header}}\r\n{{WikiProject banner shell|1=\r\n{{WikiProject a |text}}\r\n{{WikiProject d|text}}\r\n{{WikiProject c|text}}\r\n}}\r\n"
    genFixes.article_text = "{{Talk header}}\r\n{{WikiProject a |text}}\r\n{{WikiProject d|text}}\r\n{{WikiProject c|text}}"
    talk_gen_fixes()
    assert genFixes.article_text == a, r"Adds WikiProject banner shell when 3 wikiproject links"
    genFixes.article_text = "{{Talk header}}\r\n{{wikiProject a |text}}\r\n{{wikiProject d|text}}\r\n{{wiki project c|text}}"
    talk_gen_fixes()
    assert genFixes.article_text == a.replace(r"WikiProject c", r"wiki project c").replace(
        r"WikiProject a", r"wikiProject a"
    ).replace(r"WikiProject d", r"wikiProject d"), (
        r"Adds WikiProject banner shell when 3 wikiProject links, wikiproject name variations"
    )


def test_add_wiki_project_banner_shell_whitespace() -> None:
    S = W.for_site(EN)
    genFixes.article_text = "{{WikiProject Biography|living=yes}}\r\n{{WikiProject a |text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject c|text}}"
    a = "{{WikiProject banner shell|1=\r\n{{WikiProject Biography|living=yes}}\r\n{{WikiProject a |text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject c|text}}\r\n| blp=yes\r\n}}\r\n"
    talk_gen_fixes()
    assert genFixes.article_text == a, (
        r"Adds WikiProject banner shell when 3 wikiproject links, cleans whitespace"
    )
    genFixes.article_text = "{{WikiProject Biography|living=yes}}\r\n{{WikiProject a |text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject c|text}}\r\n\r\n==First==\r\nWord.\r\n\r\n\r\n\r\n\r\nSecond."
    a = "{{WikiProject banner shell|1=\r\n{{WikiProject Biography|living=yes}}\r\n{{WikiProject a |text}}\r\n{{WikiProject b|text}}\r\n{{WikiProject c|text}}\r\n| blp=yes\r\n}}\r\n\r\n==First==\r\nWord.\r\n\r\n\r\n\r\n\r\nSecond."
    talk_gen_fixes()
    assert genFixes.article_text == a, (
        r"Adds WikiProject banner shell when 3 wikiproject links, cleans whitespace"
    )
