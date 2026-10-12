"""Port of AWB UnitTests/MiscellaneousTests.cs, class HideTextTests: the parity suite for awb_l.core.parsers.hidetext.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: E501, F841, F401
# pyright: reportUnusedVariable=false

import pytest

from awb_l.core import namespace, tools
from awb_l.core import wikiregexes as W
from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig
from tests.parity import regex_assert
from tests.parity.helpers import EN, cs_len, set_lang, set_site
from tests.parity.regex_assert import check_match, check_matches

# -- helpers (the #region Helpers of HideTextTests) ------------------------------------------------

Hidden = r"⌊⌊⌊⌊M?\d+⌋⌋⌋⌋"
AllHidden = r"^(⌊⌊⌊⌊M?\d+⌋⌋⌋⌋)*$"
Hider = HideText()


def hide_more(
    text: str,
    hide_external_links_or_target_only: bool = False,
    leave_meta_headings: bool | None = None,
    hide_images: bool | None = None,
) -> str:
    """HideMore(text), HideMore(text, hideOnlyTargetOfWikilink) or
    HideMore(text, hideExternalLinks, leaveMetaHeadings, hideImages); checks the round trip."""
    global Hider
    if leave_meta_headings is None:
        Hider = HideText()
        s = Hider.hide_more(text, hide_external_links_or_target_only)
    else:
        Hider = HideText(hide_external_links_or_target_only, leave_meta_headings, bool(hide_images))
        s = Hider.hide_more(text)
    assert Hider.add_back_more(s) == text
    return s


def assert_hidden_more(text: str) -> None:
    regex_assert.is_match(Hidden, hide_more(text))


def assert_all_hidden_more(
    text: str, hide_external_links: bool | None = None, message: str = ""
) -> None:
    if hide_external_links is None:
        regex_assert.is_match(AllHidden, hide_more(text))
    else:
        regex_assert.is_match(AllHidden, hide_more(text, hide_external_links, False, True), message)


def hide(
    text: str,
    hide_external_links: bool = True,
    leave_meta_headings: bool = False,
    hide_images: bool = True,
) -> str:
    global Hider
    Hider = HideText(hide_external_links, leave_meta_headings, hide_images)
    s = Hider.hide(text)
    assert Hider.add_back(s) == text
    return s


def assert_hidden(
    text: str,
    hide_external_links: bool = True,
    leave_meta_headings: bool = False,
    hide_images: bool = True,
) -> None:
    regex_assert.is_match(Hidden, hide(text, hide_external_links, leave_meta_headings, hide_images))


def assert_all_hidden(text: str) -> None:
    regex_assert.is_match(AllHidden, hide(text))


def assert_both_hidden(
    text: str,
    hide_external_links: bool = True,
    leave_meta_headings: bool = False,
    hide_images: bool = True,
) -> None:
    global Hider
    Hider = HideText(hide_external_links, leave_meta_headings, hide_images)
    assert_all_hidden(text)
    assert_all_hidden_more(text)


Hidden = r"⌊⌊⌊⌊M?\d+⌋⌋⌋⌋"
AllHidden = r"^(⌊⌊⌊⌊M?\d+⌋⌋⌋⌋)*$"
Caption1 = r"|image_caption=London is a European Parliament constituency. It has water. |"
Caption2 = r"|image_caption= some load of text here. Some more there.}}"
Caption3 = r"|image_caption=some load of text here. Some more there.   }}"
Caption4 = r"|image_caption= some load of text here. Some more there.|"
Caption5 = (
    "|image_caption\r\n            = some load of text here. Some more there.\r\n            |"
)
Field1 = r"field = value |"


def test_hide_more() -> None:
    S = W.for_site(EN)
    Hider = HideText(True, False, True)
    text = Hider.hide_more(r"[[foo]]", False, True)
    regex_assert.is_match(AllHidden, text)
    text = Hider.add_back_more(text)
    assert text == r"[[foo]]"


def test_accept_empty_strings() -> None:
    S = W.for_site(EN)
    assert len(hide(r"")) == 0
    assert len(hide_more(r"")) == 0


def test_hide_links() -> None:
    S = W.for_site(EN)
    assert_hidden_more(r"[[foo]]")
    assert_hidden_more(r"[[foo|bar]]")


def test_leave_link_face() -> None:
    S = W.for_site(EN)
    assert r"bar" in hide_more(r"[[foo|bar]]", True)


def test_hide_italics() -> None:
    S = W.for_site(EN)
    assert r"text" not in hide_more(r"Now ''text'' was")


def test_hide_templates() -> None:
    S = W.for_site(EN)
    assert_all_hidden_more(r"{{foo}}")
    assert_all_hidden_more(r"{{{foo}}}")
    assert_all_hidden_more(r"{{foo|}}")
    assert_all_hidden_more(r"{{foo|bar}}")
    regex_assert.is_match(r"123" + Hidden + r"123", hide_more(r"123{{foo}}123"))
    assert_all_hidden_more(r"{{foo|{{bar}}}}")
    assert_all_hidden_more("{{foo|\r\nabc={{bar}}\r\n|def=hello}}")
    assert_all_hidden_more(r"{{foo|{{bar|{{{1|}}}}}}}")
    assert_all_hidden_more("{{foo|\r\nbar= {blah} blah}}")
    assert_all_hidden_more("{{foo|\r\nbar= {blah} {{{1|{{blah}}}}}}}")
    regex_assert.is_match(
        r"123{{" + Hidden + r"\|foo}}123", hide_more(r"123{{short description|foo}}123")
    )


def test_hide_pstyles() -> None:
    S = W.for_site(EN)
    assert_all_hidden_more(
        r'<p style="margin:0px;font-size:100%"><span style="color:#00ff00">▪</span> <small>Francophone minorities</small></p>'
    )
    assert_all_hidden_more(r'<p style="font-family:monospace; line-height:130%">hello</p>')
    assert_all_hidden_more(r'<p style="font-family:monospace; line-height:130%">hello</P>')
    assert_all_hidden_more('<p style="font-family:monospace; line-height:130%">hello\r\n</P>')


def test_hide_images() -> None:
    S = W.for_site(EN)
    assert r"foo" not in hide(r"[[File:foo.jpg]]"), r"Standard case"
    assert r"foo" not in hide(r"[[File:foo with space and 0004.jpg]]"), r"with space"
    assert r"foo" not in hide(r"[[File:foo.jpeg]]"), r"jpeg"
    assert r"foo" not in hide(r"[[File:foo.JPEG]]"), r"JPEG"
    assert r"foo" not in hide(r"[[Image:foo with space and 0004.jpeg]]"), r"space and jpeg"
    assert r"foo" not in hide(r"[[Image:foo.jpeg]]"), r"Image jpeg"
    assert r"foo" not in hide(r"[[Image:foo with space and 0004.jpg]]"), r"image jpeg space"
    assert r"foo" not in hide(r"[[File:foo.jpg|"), r"To pipe"
    assert r"foo" not in hide(r"[[File:foo with space and 0004.jpg|"), r"Space to pipe"
    assert r"foo" not in hide(r"[[File:foo.jpeg|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo with space and 0004.jpeg|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo.jpeg|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo with SPACE() and 0004.jpg|"), r"Standard case"
    assert r"foo" not in hide(r"[[File:foo.gif|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo with space and 0004.gif|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo.gif|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo with SPACE() and 0004.gif|"), r"Standard case"
    assert r"foo" not in hide(r"[[File:foo.png|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo with space and 0004.png|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo_here.png|"), r"Standard case"
    assert r"foo" not in hide(r"[[Image:foo with SPACE() and 0004.png|"), r"Standard case"
    assert r"westminster.tube.station.jubilee.arp" not in hide(
        r"[[Image:westminster.tube.station.jubilee.arp.jpg|"
    ), r"Dot name"
    assert hide(r"[[File:foo.jpg|thumb|140px|[[Jo]] Assistant [[Ge]]]]").startswith(r"[["), (
        r"Retain starting brackets"
    )
    assert r"thumb|140px|[[Jo]] Assistant [[Ge]]]]" in hide(
        r"[[File:foo.jpg|thumb|140px|[[Jo]] Assistant [[Ge]]]]"
    ), r"Retain ending brackets"
    assert_all_hidden(
        "<imagemap>\r\nFile:Blogs001.jpeg|Description\r\nFile:Blogs002.jpeg|Description\r\n</imagemap>"
    )
    assert r"abc" not in hide_more(r"[[Category:Foo|abc]]", False), (
        r"Category sort key always hidden if hiding wikilinks and not leaving target"
    )
    assert r"abc" not in hide_more(r"[[Category:Foo|abc]]", True), (
        r"Category sort key hidden even if keeping targets"
    )
    h = HideText(True, False, False)
    assert r"abc" in h.hide_more(r"[[Category:Foo|abc]]", False, False), (
        r"Category sort key kept if keeping wikilinks"
    )


def test_hide_images_limits() -> None:
    S = W.for_site(EN)
    assert DotNetRegex(Hidden + r"\|").is_match(
        hide(r"|image_skyline=442px_-_London_Lead_Image.jpg|")
    )
    assert DotNetRegex(Hidden + r" <!--" + Hidden + r"-->\|").is_match(
        hide(r"|image_skyline=442px_-_London_Lead_Image.jpg <!--comm-->|")
    )
    assert DotNetRegex(Hidden + r"   \|").is_match(
        hide(r"|image_map=London (European Parliament constituency).svg   |")
    )
    assert DotNetRegex(Hidden + r"   \|").is_match(
        hide(r"|image_map=London (European Parliament constituency).webm   |")
    )
    assert DotNetRegex(Hidden + r"\|").is_match(
        hide(r"|image_map=westminster.tube.station.jubilee.arp.jpg|")
    )
    assert DotNetRegex(Hidden + r" \|").is_match(hide(r"|Cover  = AmorMexicanaThalia.jpg |"))
    assert DotNetRegex(Hidden + r" \|").is_match(hide(r"|image = AmorMexicanaThalia.jpg |"))
    assert DotNetRegex(Hidden + r" \|").is_match(hide("|\r\nimage = AmorMexicanaThalia.jpg |"))
    assert DotNetRegex(Hidden + "\r\n\\|").is_match(hide("|Img = BBC_logo1.jpg\r\n|"))
    assert DotNetRegex(Hidden + r" \|").is_match(hide(r"| image name = Fred Astaire.jpg |"))
    assert DotNetRegex(Hidden + r" \|").is_match(hide(r"|image2 = AmorMexicanaThalia.jpg |"))
    assert DotNetRegex(Hidden + r" \|").is_match(hide(r"|map = AmorMexicanaThalia.jpg |"))
    assert DotNetRegex(Hidden + r" \|").is_match(hide(r"|AmorMexicanaThalia.jpg |"))


def test_hide_cite_titles() -> None:
    S = W.for_site(EN)
    assert r"foo" in hide(r"{{cite web| title = foo | date = May 2011"), (
        r"Title not hidden if no year"
    )
    assert r"September" not in hide(
        r"{{cite web| title = Now September 20 - September 26, 2010 was | date = May 2011"
    ), r"title hidden when contains year"
    assert (
        cs_len(
            tools.get_template_parameter_value(
                hide(r"{{cite web| title = September 20 - September 26, 2010 | date = May 2011"),
                r"title",
            )
        )
        > 0
    ), r"title parameter has length if hidden"
    assert r"]" in hide(
        r"{{cite web| title = [Now September 20 - September 26, 2010] was | date = May 2011"
    ), r"title hiding, bracket handling"
    assert r"foo" in hide(r"{{cite web| trans_title = foo | date = May 2011"), (
        r"trans_title not hidden if no year"
    )
    assert r"September" not in hide(
        r"{{cite web| trans_title = Now September 20 - September 26, 2010 was | date = May 2011"
    ), r"trans_title hidden when contains year"
    assert (
        cs_len(
            tools.get_template_parameter_value(
                hide(
                    r"{{cite web| trans_title = September 20 - September 26, 2010 | date = May 2011"
                ),
                r"trans_title",
            )
        )
        > 0
    ), r"trans_title parameter has length if hidden"
    assert (
        hide(r"{{cite web | url = www.site.com/a.pdf }}")
        == r"{{cite web | url = www.site.com/a.pdf }}"
    ), r"PDF www URL not hidden"
    assert r"2010" not in hide(
        r"{{cite web| trans_title = Now September 2009 - September 26, 2010 was | date = May 2011"
    ), r"2 years"
    assert r"(in three volumes}" in hide(
        r"{{cite web| trans_title = September 26, 2010 was (in three volumes} | date = May 2011"
    ), r"Don't hide beyond year"


def test_hide_not_a_typo() -> None:
    S = W.for_site(EN)
    assert_all_hidden(r"{{not a typo|foo}}")
    assert_all_hidden(r"{{Not a typo|The pEneLOpe[s]}}")
    assert_all_hidden(r"{{typo|foo}}")
    assert_all_hidden(r"{{proper name|foo}}")
    assert_all_hidden(r"{{as written|foo}}")


def test_hide_images_partial() -> None:
    S = W.for_site(EN)
    assert hide(Caption1) == Caption1
    assert hide(Caption2) == Caption2
    assert hide(Caption3) == Caption3
    assert hide(Caption4) == Caption4
    assert hide(Caption5) == Caption5
    assert hide(r"[[Image:some image name.JPG|thumb|words with typos]]").endswith(
        r"thumb|words with typos]]"
    )
    assert hide(r"[[Image:some image name.JPEG|words with typos]]").endswith(r"words with typos]]")
    assert hide(r"[[Image:some image name.jpg|thumb|words with typos ]]").endswith(
        r"thumb|words with typos ]]"
    )
    assert hide(r"[[Image:some image name.png|20px|words with typos and [[links]] here]]").endswith(
        r"20px|words with typos and [[links]] here]]"
    )
    assert hide(r"[[Image:some image name.svg|thumb|words with typos ]]").endswith(
        r"thumb|words with typos ]]"
    )
    assert hide(
        r"[[Image:some_image_name.further words.tiff|thumb|words with typos<ref name=a/>]]"
    ).endswith(r"thumb|words with typos<ref name=a/>]]")
    assert hide(r"[[Image:some_image_name.for a word.png|thumb|words with typo]]").endswith(
        r"thumb|words with typo]]"
    )
    assert hide(
        r"[[Image:some_image_name.png|thumb|words with typo]] Normal words in text"
    ).endswith(r"thumb|words with typo]] Normal words in text")
    assert hide(r"[[Image:some_image_name.png]] Normal words in text").endswith(
        r" Normal words in text"
    )
    assert hide(Caption4 + Field1).endswith(Field1)


def test_hide_images_misc() -> None:
    S = W.for_site(EN)
    assert r"=Chlorothiazide" not in hide_more(
        "{{Drugbox|\r\n   |IUPAC_name = 6-chloro-1,1-dioxo-2''H''-1,2,4-benzothiadiazine-7-sulfonamide\r\n   | image=Chlorothiazide.svg\r\n   | image2=Chlorothiazide-from-xtal-3D-balls.png\r\n   | CAS_number=58-94-6}}"
    )
    assert_all_hidden(
        "{{ gallery\r\n|title=Lamu images\r\n|width=150\r\n|lines=2\r\n|Image:LamuFort.jpg|Lamu Fort\r\n|Image:LAMU Riyadha Mosque.jpg|Riyadha Mosque\r\n|Image:04 Donkey Hospital (June 30 2001).jpg|Donkey Sanctuary\r\n}}"
    )


def test_hide_images_more() -> None:
    S = W.for_site(EN)
    assert_all_hidden_more(r"[[File:foo.jpg]]")
    assert_all_hidden_more(r"[[File:foo with space and 0004.jpg]]")
    assert_all_hidden_more(r"[[File:foo.jpeg]]")
    assert_all_hidden_more(r"[[File:foo.JPEG]]")
    assert_all_hidden_more(r"[[Image:foo with space and 0004.jpeg]]")
    assert_all_hidden_more(r"[[Image:foo.jpeg]]")
    assert_all_hidden_more(r"[[Image:foo with space and 0004.jpg]]")
    assert_all_hidden_more(r"[[File:foo.jpg|")
    assert_all_hidden_more(r"[[File:foo with space and 0004.jpg|")
    assert_all_hidden_more(r"[[File:foo.jpeg|")
    assert_all_hidden_more(r"[[Image:foo with space and 0004.jpeg|")
    assert_all_hidden_more(r"[[Image:foo.jpeg|")
    assert_all_hidden_more(r"[[Image:foo with SPACE() and 0004.jpg|")
    assert_all_hidden_more(r"[[File:foo.gif|")
    assert_all_hidden_more(r"[[Image:foo with space and 0004.gif|")
    assert_all_hidden_more(r"[[Image:foo.gif|")
    assert_all_hidden_more(r"[[Image:foo with SPACE() and 0004.gif|")
    assert_all_hidden_more(r"[[File:foo.png|")
    assert_all_hidden_more(r"[[Image:foo with space and 0004.png|")
    assert_all_hidden_more(r"[[Image:foo_here.png|")
    assert_all_hidden_more(r"[[Image:foo with SPACE() and 0004.png|")
    assert_all_hidden_more(r"[[Image:westminster.tube.station.jubilee.arp.jpg|")
    assert hide_more(Caption1) == Caption1
    assert hide_more(Caption2) == Caption2
    assert hide_more(Caption3) == Caption3
    assert hide_more(Caption4) == Caption4
    assert hide_more(Caption5) == Caption5
    assert hide_more(r"[[Image:some_image_name.png]] Normal words in text").endswith(
        r" Normal words in text"
    )
    assert hide_more(Caption4 + Field1).endswith(Field1)
    assert r"=Chlorothiazide" not in hide_more(
        "{{Drugbox|\r\n   |IUPAC_name = 6-chloro-1,1-dioxo-2''H''-1,2,4-benzothiadiazine-7-sulfonamide\r\n   | image=Chlorothiazide.svg\r\n   | image2=Chlorothiazide-from-xtal-3D-balls.png\r\n   | CAS_number=58-94-6}}"
    )
    assert_all_hidden_more(
        "<imagemap>\r\nFile:Blogs001.jpeg|Description\r\nFile:Blogs002.jpeg|Description\r\n</imagemap>"
    )


def test_hide_galleries() -> None:
    S = W.for_site(EN)
    assert DotNetRegex("<gallery>\r\n" + Hidden + "|text\r\n</gallery>").is_match(
        hide_more("<gallery>\r\nImage:quux.JPEG|text\r\n</gallery>")
    ), r"Simple case: one image link with namespace hidden, description retained"
    assert DotNetRegex("<gallery>\r\n" + Hidden + "|text\r\n</gallery>").is_match(
        hide_more("<gallery>\r\nquux.JPEG|text\r\n</gallery>")
    ), r"One image link without namespace hidden, description retained"
    assert DotNetRegex("<gallery>\r\n" + Hidden + "|\r\n</gallery>").is_match(
        hide_more("<gallery>\r\nquux.JPEG|\r\n</gallery>")
    ), r"One image link without namespace hidden, blank description"
    assert DotNetRegex("<gallery>\r\n" + Hidden + "\r\n</gallery>").is_match(
        hide_more("<gallery>\r\nquux.JPEG\r\n</gallery>")
    ), r"One image link without namespace hidden, no description "
    assert DotNetRegex(
        "<gallery>\r\n" + Hidden + "|a bar\r\n" + Hidden + "|text\r\n</gallery>"
    ).is_match(
        hide_more("<gallery>\r\nImage:foo.png|a bar\r\nImage:quux.JPEG|text\r\n</gallery>")
    ), r"Multiple image links hidden"
    assert DotNetRegex('<gallery param="a">\r\n' + Hidden + "|text\r\n</gallery>").is_match(
        hide_more('<gallery param="a">\r\nImage:quux.svg|text\r\n</gallery>')
    ), r"Images hidden within gallery tags with parameters"
    assert DotNetRegex(
        "<Gallery>\r\n" + Hidden + "|a bar\r\n" + Hidden + "|text\r\n</gallery>"
    ).is_match(
        hide_more("<Gallery>\r\nImage:foo.png|a bar\r\nImage:quux.JPEG|text\r\n</gallery>")
    ), r"gallery tag casing"
    assert DotNetRegex("<gallery>\r\nImage:foo\r\n" + Hidden + "|text\r\n</gallery>").is_match(
        hide_more("<gallery>\r\nImage:foo\r\nImage:quux.JPEG|text\r\n</gallery>")
    ), r"Image link without file extension not hidden"
    assert DotNetRegex("<gallery>\r\n" + Hidden + "\r\n" + Hidden + "|text\r\n</gallery>").is_match(
        hide_more("<gallery>\r\nFile:foo.png\r\nFile:9th of quux.JPEG|text\r\n</gallery>")
    ), r"image without description hidden OK"
    assert DotNetRegex(
        "<gallery>\r\n" + Hidden + "|text1\r\n" + Hidden + "|text2\r\n</gallery>"
    ).is_match(
        hide_more(
            "<gallery>\r\nFile:bar ă foo.jpg|text1\r\nFile:9th of May, ățuux.JPEG|text2\r\n</gallery>"
        )
    ), r"special characters in image name handled OK"
    assert DotNetRegex(
        "<gallery>\r\n"
        + Hidden
        + r"|"
        + Hidden
        + " barbar\r\n"
        + Hidden
        + "|Winter Festival\r\n"
        + Hidden
        + "|Bar, detail\r\n"
        + Hidden
        + r"|"
        + Hidden
        + " Street\r\n</gallery>"
    ).is_match(
        hide_more(
            "<gallery>\r\nFile:foo1.jpg|[[foobar]] barbar\r\nFile:foo2.jpg|Winter Festival\r\nImage:Foo3.jpg|Bar, detail\r\nFile:9th of June street , Bacău.JPG|[[Romanian War of Independence#Overview|9th of May]] Street\r\n</gallery>"
        )
    ), r"Wiki formatting within image description handled OK"
    assert DotNetRegex("<gallery>\r\n" + Hidden + "|text\r\n</gallery>").is_match(
        hide("<gallery>\r\nquux.JPEG|text\r\n</gallery>")
    ), r"One image link without namespace hidden, description retained"


def test_hide_external_links() -> None:
    S = W.for_site(EN)
    assert_all_hidden_more(r"[http://foo]", True, r"External link no text")
    assert_all_hidden_more(r"[http://foo bar]", True, r"External link with text")
    assert_all_hidden_more(r"[//foo.com bar]", True, r"External link Protocol-relative URL")
    assert_all_hidden_more(r"[http://foo [bar]", True, r"External link unbalanced bracket")
    assert_all_hidden_more(r"[[ru:Link]]", True, r"Possible interwiki, hidemore")
    assert r"Link" not in hide(r"[[ru:Link]]", True, True, True), r"Possible interwiki, hide"
    assert r"date=April 2010|url=" in hide(
        r"date=April 2010|url=http://w/010111a.html}}", True, True, True
    ), r"cite template URL"
    assert r"date=April 2010|url=" in hide(
        r"date=April 2010|url=//w/010111a.html}}", True, True, True
    ), r"Protocol-relative URL"
    assert r"}}" in hide(r"date=April 2010|url=http://w/010111a.html}}", True, True, True), (
        r"Cite template URL, }} retention"
    )


def test_hide_plain_external_links() -> None:
    S = W.for_site(EN)
    assert_all_hidden_more(r"http://foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"https://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"//www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"ftp://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"mailto://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"irc://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"gopher://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"telnet://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"nntp://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"worldwind://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"news://www.foo.com/asdfasdf/asdf.htm", True)
    assert_all_hidden_more(r"svn://www.foo.com/asdfasdf/asdf.htm", True)
    assert r"asdf" not in hide_more(r"http://foo.com/asdfasdf/asdf.htm", True, False, False)
    assert r"asdf" in hide_more(r"http://foo.com/asdfasdf/asdf.htm", False, False, False)


def test_hide_wiki_links_only_plus_word() -> None:
    S = W.for_site(EN)
    assert_all_hidden_more(r"[[Foo]]bar")
    assert_all_hidden_more(r"[[Foo|test]]bar")


def test_simple_hide() -> None:
    S = W.for_site(EN)
    assert_hidden(r"<source>foo</source>")
    assert_hidden(r'<source  lang="foo_bar">\nfoo\n</source>')
    assert_all_hidden("<source>\r\nfoo\r\n</source><source foo>bar</source>")
    assert_hidden(r'<syntaxhighlight  lang="foo_bar">\nfoo\n</syntaxhighlight>')
    assert_hidden(r'<syntaxhighlight  lang="javascript">\nfoo\n</syntaxhighlight>')
    assert_all_hidden("<syntaxhighlight>\r\nfoo\r\n</source><source foo>bar</syntaxhighlight>")
    assert_hidden(r"<tt>foo</tt>")
    assert_hidden("<pre>foo\r\nbar</pre>")
    assert_hidden("<pre style=quux>foo\r\nbar</pre>")
    assert_hidden("<math>foo\r\nbar</math>")
    assert_hidden("<chem>foo\r\nbar</chem>")
    assert_hidden("<math chem>foo\r\nbar</math>")
    assert_hidden("{{math|foo\r\nbar}}")
    assert_hidden("{{code|foo\r\nbar}}")
    assert_hidden("<timeline>foo\r\nbar</timeline>")
    assert_hidden("<timeline foo=bar>foo\r\nbar</timeline>")
    assert_hidden("<nowiki>foo\r\nbar</nowiki>")
    assert_hidden(r"<!--foo-->")
    assert_hidden("<!--foo\r\nbar-->")
    assert DotNetRegex(r"<!--" + Hidden + r"-->").is_match(hide(r"<!--foo-->"))
    assert_hidden(r"[http://foo]")
    assert_hidden(r"[http://foo bar]")
    assert_hidden(r"https://bar")
    assert hide(r"http://foo", False, False, True) == r"http://foo"
    assert_hidden(r"<!--Categories -->")
    assert_hidden(r"<!--foo-->", True, True, True)
    assert hide(r"<!-- categories-->", True, True, True) == r"<!-- categories-->"
    assert_hidden(r"[[Image:foo.JPG]]")
    assert hide(r"[[Image:foo.jpg]]", True, False, False) == r"[[Image:foo.jpg]]"
    assert_hidden(r"[[File:foo.JPG]]")
    assert hide(r"[[File:foo.jpg]]", True, False, False) == r"[[File:foo.jpg]]"
    assert_all_hidden_more(r"<hiero>foo</hiero>")
