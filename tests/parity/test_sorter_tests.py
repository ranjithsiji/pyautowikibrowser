"""Port of AWB UnitTests/SorterTests.cs: metadata sorting.

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from pyawb.core import genfixes, namespace, tools
from pyawb.core import wikiregexes as W
from pyawb.core.dotnet_regex import DotNetOptions as O
from pyawb.core.parsers.parsers import DateLocale
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import EN, cs_len, set_lang, set_site
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser
parser2 = genfixes.Parsers()  # AWB's RequiresParser2


def test_remove_stubs() -> None:
    S = W.for_site(EN)
    s = '==foo==\r\nbar<ref name="123"/>{{boz}}'
    assert len(((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1]) == 0
    assert s == '==foo==\r\nbar<ref name="123"/>{{boz}}'
    s = r"{{foo}}{{some-stub}}{{foo-stub}}bar{{sect-stub}}{{not a|stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][
        1
    ] == "{{some-stub}}\r\n{{foo-stub}}\r\n"
    assert s == r"{{foo}}bar{{sect-stub}}{{not a|stub}}"
    s = r"{{foo}}{{my-stub}}{{foo-stub|date=May 2012}}bar{{sect-stub}}{{not a|stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][
        1
    ] == "{{my-stub}}\r\n{{foo-stub|date=May 2012}}\r\n"
    s = r""
    assert len(((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1]) == 0
    assert len(s) == 0
    s = r"{{stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{stub}}\r\n"
    assert len(s) == 0
    s = r"{{foo}}{{stub}}{{stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{stub}}\r\n", (
        r"deduplication, same case"
    )
    s = r"{{foo}}{{Stub}}{{stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{Stub}}\r\n", (
        r"deduplication, different case"
    )
    s = r"<!-- {{stub}} -->"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][
        1
    ] == r"<!-- {{stub}} -->" + "\r\n", r"Extract commented out stubs"
    s = "#REDIRECT [[X]]\r\n<!--\r\n'''X''' is a x in the [[x]] of [[x]] in [[x]]. It lies to the east of [[x]].\r\n{{stub}}\r\n-->"
    assert len(((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1]) == 0, (
        r"Don't pull stubs out of comments"
    )


def test_remove_dupelicate_stubs() -> None:
    S = W.for_site(EN)
    stub = r"{{foo stub}}"
    articleTextBack = r""
    articletext = stub + r" " + stub
    articleTextBack = parser2.sort_meta_data(articletext, r"test")
    assert len(S.Stub.matches(articleTextBack)) == 1
    articletext = stub + r" " + r"{{fOO stub}}"
    articleTextBack = parser2.sort_meta_data(articletext, r"test")
    assert len(S.Stub.matches(articleTextBack)) == 2
    articletext = stub + r" " + r"<!--{{foo stub}}-->"
    articleTextBack = parser2.sort_meta_data(articletext, r"test")
    assert len(S.Stub.matches(articleTextBack)) == 2
    s = r"{{foo}}{{stub}}{{foo-stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{foo-stub}}\r\n", (
        r"removes {{stub}} if more detailed stub"
    )
    s = r"{{foo}}{{ Stub }}{{foo-stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{foo-stub}}\r\n", (
        r"removes {{stub}} if more detailed stub"
    )
    s = r"{{foo}}{{-stub}}{{foo-stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{foo-stub}}\r\n", (
        r"removes {{-stub}} if more detailed stub"
    )
    s = r"{{foo}}{{-stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][1] == "{{-stub}}\r\n", (
        r"retain {{-stub}} if only stub tag"
    )
    s = r"{{foo}}{{uncategorized stub}}{{stub}}"
    assert ((_t := genfixes.remove_stubs(s)), (s := _t[0]))[0][
        1
    ] == "{{uncategorized stub}}\r\n{{stub}}\r\n", (
        r"retain {{stub}} if other tag is {{uncategorized stub}}"
    )


def test_interwiki_spacing() -> None:
    S = W.for_site(EN)
    parser2.sort_interwikis = False
    parser2.sorter.possible_interwikis = [r"de", r"es", r"fr", r"it", r"sv", r"ar", r"bs", r"br"]
    correct = "\r\n\r\n[[Category:Pub chains in the United Kingdom]]\r\n[[Category:Companies established in 1997]]\r\n\r\n[[es:Punch Taverns]]\r\n[[fr:Punch Taverns]]"
    assert parser2.sort_meta_data(correct, r"no change") == correct
    assert (
        parser2.sort_meta_data(
            "\r\n\r\n[[Category:Pub chains in the United Kingdom]]\r\n[[Category:Companies established in 1997]]\r\n\r\n\r\n\r\n[[es:Punch Taverns]]\r\n[[fr:Punch Taverns]]",
            r"two newlines before interwikis",
        )
        == correct
    )
    assert (
        parser2.sort_meta_data(
            "\r\n\r\n[[Category:Pub chains in the United Kingdom]]\r\n[[Category:Companies established in 1997]]\r\n[[es:Punch Taverns]]\r\n\r\n[[fr:Punch Taverns]]\r\n",
            r"an interwiki immediatelly after categories",
        )
        == correct
    )


def test_move_person_data_tests() -> None:
    S = W.for_site(EN)
    b1 = "{{Persondata\r\n|NAME= Hodgson, Jane Elizabeth\r\n|ALTERNATIVE NAMES=\r\n|SHORT DESCRIPTION= [[Physician]], [[obstetrician]], [[gynecologist]]\r\n|DATE OF BIRTH= 1915-1-23\r\n|PLACE OF BIRTH= [[Crookston, Minnesota]]\r\n|DATE OF DEATH= 2006-10-23\r\n|PLACE OF DEATH= [[Rochester, Minnesota]]\r\n}}"
    b2 = "{{Persondata\r\n|NAME= Hodgson, Jane Elizabeth\r\n|ALTERNATIVE NAMES=\r\n|SHORT DESCRIPTION= [[Physician]], [[obstetrician]], [[gynecologist]]\r\n|DATE OF BIRTH= {{birth date|1915|1|23}}\r\n|PLACE OF BIRTH= [[Crookston, Minnesota]]\r\n|DATE OF DEATH= 2006-10-23\r\n|PLACE OF DEATH= [[Rochester, Minnesota]]\r\n}}"
    c1 = b1
    c2 = b2
    ((_t := genfixes.remove_person_data(c1)), (c1 := _t[0]))[0][1]
    assert c1 == r""
    ((_t := genfixes.remove_person_data(c2)), (c2 := _t[0]))[0][1]
    assert c2 == r""
    ((_t := genfixes.remove_person_data(b1)), (b1 := _t[0]))[0][1]
    assert b1 == r""
    d1 = "{{Persondata\r\n|NAME= Becker, Gary\r\n|ALTERNATIVE NAMES=\r\n|SHORT DESCRIPTION= [[Economics|Economist]]\r\n|DATE OF BIRTH= [[December 2]], [[1930]]\r\n|PLACE OF BIRTH= [[Pottsville, Pennsylvania]]\r\n|DATE OF DEATH=\r\n|PLACE OF DEATH=\r\n}}"
    d2 = "{{Winners of the National Medal of Science|behav-social}}\r\n"
    d3 = "\r\n[[Category:Members of the National Academy of Sciences]]"
    e = d2 + d1 + d3
    f = ((_t := genfixes.remove_person_data(e)), (e := _t[0]))[0][1]
    assert f == d1
    assert e == d2 + d3
    e = d2 + d1 + d1.replace(r"[[December 2]]", r"") + d3
    f = ((_t := genfixes.remove_person_data(e)), (e := _t[0]))[0][1]
    assert f == d1 + "\r\n" + d1.replace(r"[[December 2]]", r""), (
        r"duplicate persondata: order not changed"
    )
    commented = r"<!--{{Persondata}}-->"
    assert len(((_t := genfixes.remove_person_data(commented)), (commented := _t[0]))[0][1]) == 0, (
        r"commented out persondata not extracted"
    )


def test_move_dablinks_tests() -> None:
    S = W.for_site(EN)
    d = "Fred is a doctor.\r\nFred has a dog.\r\n[[Category:Dog owners]]\r\n{{some template}}\r\n"
    e0 = r"{{redirect|foo|bar}}"
    e = r"{{other people|Fred the dancer|Fred Smith (dancer)}}"
    assert genfixes.move_template(d + e, W.Dablinks) == e + "\r\n" + d
    assert genfixes.move_template(d + e + e, W.Dablinks) == e + "\r\n" + d, (
        r"Deduplication of identical tags"
    )
    e = r"{{For|Fred the dancer|Fred Smith (dancer)}}"
    assert genfixes.move_template(d + e, W.Dablinks) == e + "\r\n" + d, r"odering plus add newline"
    assert genfixes.move_template(e + r" " + d, W.Dablinks) == e + "\r\n" + d, (
        r"whitepsace handling"
    )
    e = r"{{redirect2|Fred the dancer|Fred Smith (dancer)}}"
    assert genfixes.move_template(d + e, W.Dablinks) == e + "\r\n" + d, (
        r"odering plus add newline, redirect2"
    )
    e = r"{{redirect2|Fred the {{dancer}}|Fred Smith (dancer)}}"
    assert genfixes.move_template(d + e, W.Dablinks) == e + "\r\n" + d, (
        r"odering plus add newline, redirect2, nested"
    )
    e = "{{redirect2|Fred the {{dancer}}|Fred Smith (dancer)}}\r\n"
    assert genfixes.move_template(d + r":" + e, W.Dablinks) == e + d, (
        r"colons before dablinks removed"
    )
    f = "Article words\r\n== heading ==\r\n{{redirect2|Fred the dancer|Fred Smith (dancer)}}\r\nwords"
    assert genfixes.move_template(f, W.Dablinks) == f
    assert (
        genfixes.move_template(r"[[Category:Confederate Navy officers|Captains]]", W.Dablinks)
        == r"[[Category:Confederate Navy officers|Captains]]"
    )
    g = r"Some words"
    h = "==heading==\r\nmore words\r\n[[Category:Foo]]"
    e = r"{{redirect2|Fred the {{dancer}}|Fred Smith (dancer)}}"
    assert (
        genfixes.move_template(g + "\r\n" + e + "\r\n" + h, W.Dablinks)
        == e + "\r\n" + g + "\r\n" + h
    )
    assert genfixes.move_template(d + e + e0, W.Dablinks) == e + "\r\n" + e0 + "\r\n" + d, (
        r"multi tag ordering"
    )
    assert (
        genfixes.move_template(e + e0 + "\r\n\r\n" + d, W.Dablinks)
        == e + "\r\n" + e0 + "\r\n\r\n" + d
    ), r"Don't affect whitespace after tags"
    assert genfixes.move_template(e + "\r\n" + d, W.Dablinks) == e + "\r\n" + d
    assert genfixes.move_template(e + "\r\n" + e0 + d, W.Dablinks) == e + "\r\n" + e0 + "\r\n" + d
    assert (
        genfixes.move_template(e + "\r\n" + e0 + "\r\n" + d, W.Dablinks)
        == e + "\r\n" + e0 + "\r\n" + d
    )
    assert (
        genfixes.move_template(e + "\r\n" + e0 + "\r\n\r\n" + d, W.Dablinks)
        == e + "\r\n" + e0 + "\r\n\r\n" + d
    )
    assert (
        genfixes.move_template(e + "\r\n" + e0 + e0 + "\r\n\r\n" + d, W.Dablinks)
        == e + "\r\n" + e0 + "\r\n\r\n" + d
    ), r"Dupe tag removal"
    assert (
        genfixes.move_template(
            e + "\r\n" + r"{{short description|foo}}" + "\r\n" + d, W.ShortDescriptionTemplate
        )
        == r"{{short description|foo}}" + "\r\n" + e + "\r\n" + d
    )
    shortDescNone = r'{{Short description|none}} <!-- "none" is preferred when the title is sufficiently descriptive; see [[WP:SDNONE]] -->'
    assert (
        genfixes.move_template(e + "\r\n" + shortDescNone + "\r\n" + d, W.ShortDescriptionTemplate)
        == shortDescNone + "\r\n" + e + "\r\n" + d
    )
    i = "{{Short description|American character encoding standard}}\r\n{{hatnote group|\r\n{{other uses}}\r\n{{Distinguish|text=MS [[Windows-1252]] or other types of [[Extended ASCII]]}}\r\n}}\r\n{{Use mdy dates|date=June 2013|cs1-dates=y}}\r\nArticle"
    assert parser2.sort_meta_data(i, r"Don't pull hatnotes out of hatnote group") == i


def test_zeroth_section_sorting() -> None:
    S = W.for_site(EN)
    correct = "{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello"
    assert parser2.sort_meta_data(correct, r"Title") == correct, (
        r"Use mdy dates - already correctly ordered"
    )
    assert (
        parser2.sort_meta_data(
            "{{Use mdy dates}}\r\n{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Use American English}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello",
            r"Title",
        )
        == correct
    ), r"Use mdy dates starting at top"
    assert (
        parser2.sort_meta_data(
            "{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello",
            r"Title",
        )
        == correct
    ), r"Use mdy dates and American English starting at top"
    assert (
        parser2.sort_meta_data(
            "{{featured article}}\r\n{{Short description|American character}}\r\n{{other uses}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Prod blp}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello",
            r"Title",
        )
        == correct
    ), r"featured article starting at top"
    correct2 = "{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{multiple issues|\r\n{{Cleanup}}\r\n{{Expert needed}}\r\n}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello"
    assert parser2.sort_meta_data(correct2, r"Title") == correct2, (
        r"Already correctly ordered with use mdy, use American and MI"
    )
    correct3 = "{{Short description|American character with section word}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Cleanup}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Infobox actor}}\r\nHello"
    assert parser2.sort_meta_data(correct3, r"Title") == correct3, (
        r"Already correctly ordered with use mdy, use American and single maintenance template"
    )
    correct4 = "{{Short description|American character with section word}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Cleanup}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Infobox actor|fiddles with articletitle}}\r\n{{lowercase title}}\r\nHello"
    assert parser2.sort_meta_data(correct4, r"Title") == correct4, (
        r"Already correct - {{lowercase title}} after infobox"
    )
    correct5 = "{{Short description|American character with section word}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Cleanup}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{lowercase title}}\r\n{{Infobox actor|doesn't fiddle with articletitle}}\r\nHello"
    assert parser2.sort_meta_data(correct5, r"Title") == correct5, (
        r"Already correct - {{lowercase title}} just before infobox"
    )
    correct6 = "{{Short description|Operating system for Apple computers}}\r\n{{Lowercase title}}\r\n{{Redirect2|OSX|OS X}}\r\n{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{pp-semi-indef}}\r\n{{Use mdy dates|date=August 2019}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct6, r"MacOS") == correct6, (
        r"Already correct - {{lowercase title}} after {{short description}}"
    )
    assert (
        parser2.sort_meta_data(
            "{{Short description|Operating system for Apple computers}}\r\n{{Redirect2|OSX|OS X}}\r\n{{Lowercase title}}\r\n{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{pp-semi-indef}}\r\n{{Use mdy dates|date=August 2019}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally.",
            r"MacOS",
        )
        == correct6
    ), r"Move {{lowercase title}} - incorrectly placed, not attached to infobox"
    correct7 = "{{Short description|Operating system for Apple computers}}\r\n{{Redirect2|OSX|OS X}}\r\n{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{pp-semi-indef}}\r\n{{Use mdy dates|date=August 2019}}\r\n{{Lowercase title}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct7, r"MacOS") == correct7, (
        r"Already correct - {{lowercase title}} just before infobox"
    )
    correct8 = "{{Short description|Operating system for Apple computers}}\r\n{{Redirect2|OSX|OS X}}\r\n{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{pp-semi-indef}}\r\n{{Use mdy dates|date=August 2019}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{Lowercase title}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct8, r"MacOS") == correct8, (
        r"Already correct - {{lowercase title}} after infobox"
    )
    correct9 = "{{Short description|Operating system for Apple computers}}\r\n{{Redirect2|OSX|OS X}}\r\n{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{pp-semi-indef}}\r\n{{bots}}\r\n{{in use}}\r\n{{Excessive citations}}\r\n{{Use mdy dates|date=August 2019}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{Lowercase title}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct9, r"MacOS") == correct9, (
        r"Already correct - {{bots}} and {{in use}}"
    )
    correct10 = "{{Oscars short description|Operating}}\r\n{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{Excessive citations}}\r\n{{Use mdy dates|date=August 2019}} <!--comm-->\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{Lowercase title}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct10, r"MacOS") == correct10, (
        r"Handles {{oscars short description}}"
    )
    correct11 = "{{About|macOS version 10.0 and later|Mac OS 9 and earlier}}\r\n{{Excessive citations}}\r\n<!--comm re mdy-->\r\n{{Use mdy dates|date=August 2019}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}\r\n{{Lowercase title}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct11, r"MacOS") == correct11, (
        r"Handles comment before use mdy dates"
    )
    noinclude = "\r\n==Heading==\r\n<noinclude>something</noinclude>\r\nText"
    assert (
        parser2.sort_meta_data(
            "{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello"
            + noinclude,
            r"Title",
        )
        == correct + noinclude
    ), r"Zeroth section still sorted OK if later section has noinclude"
    zerothWithNoInclude = "{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Prod blp}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\n<noinclude>something</noinclude>\r\nHello"
    assert parser2.sort_meta_data(zerothWithNoInclude, r"Title") == zerothWithNoInclude, (
        r"Zeroth section NOT sorted if has noinclude"
    )
    infoboxWithComment = "{{Short description|American character}}\r\n{{other uses}}\r\n{{featured article}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n<!-- comment before infobox -->{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello"
    assert parser2.sort_meta_data(infoboxWithComment, r"Title") == infoboxWithComment, (
        r"Handles infobox with comment first"
    )
    shortDescWithComment = "{{Short description|American character}}<!--a comment-->\r\n{{other uses}}\r\n{{featured article}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello"
    assert parser2.sort_meta_data(shortDescWithComment, r"Title") == shortDescWithComment, (
        r"Handles short description with comment after"
    )
    shortDescWithComment2 = '{{Short description|American character}} <!-- "none" is preferred when the title is sufficiently descriptive; see [[WP:SDNONE]] -->\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello'
    assert parser2.sort_meta_data(shortDescWithComment2, r"Title") == shortDescWithComment2, (
        r"Handles short description with comment after, then infobox"
    )
    templateWithCommentMultiLine = "{{Short description|American character}}<!--\r\na comment\r\nover multiple lines\r\n-->\r\n{{other uses}}\r\n{{featured article}}\r\n{{Use mdy dates}}\r\n{{Use American English}}\r\n{{Infobox actor}}\r\n{{Japanese script needed}}\r\nHello"
    assert (
        parser2.sort_meta_data(templateWithCommentMultiLine, r"Title")
        == templateWithCommentMultiLine
    ), r"Handles template with comment after, multiline comment"
    multipleInfoxbox = "{|{{Infobox ship begin|infobox caption=PTF-3}}\r\n{{Infobox ship image\r\n}}\r\n{{Infobox ship career\r\n}}\r\n{{Infobox ship characteristics\r\n}}\r\n|}"
    assert parser2.sort_meta_data(multipleInfoxbox, r"Title") == multipleInfoxbox, (
        r"Don't sort when wikitable"
    )
    hatnoteGroupHatnote = "{{Short description|Band}}\r\n{{hatnote group|{{redirect|Jo1||JO1 (disambiguation)}}{{distinguish|jol (disambiguation){{!}}jol|joi (disambiguation){{!}}JOI}}}}\r\n{{Western name order}}\r\n{{Use mdy dates|date=October 2020}}\r\n{{Infobox musical artist}}\r\nHello"
    assert parser2.sort_meta_data(hatnoteGroupHatnote, r"Title") == hatnoteGroupHatnote, (
        r"Handles hatnote group and hatnote"
    )


def test_zeroth_section_sorting_errors() -> None:
    S = W.for_site(EN)
    unbalancedMultiInfobox = "{{Short description|A}}\r\n{{pp-blp|small=yes}}\r\n{{Use American English|date=September 2020}}\r\n{{Use mdy dates|date=August 2023}}\r\n{{Infobox person\r\n| name               = A\r\n| module             = {{Infobox TikTok personality\r\n| subbox               =yes    \r\n<!-- Use the stats_update section of the {{Infobox YouTube personality -->\r\n}}\r\n| module2            = {{Infobox musical artist\r\n| embed              = yes\r\n}}\r\n}}"
    assert parser2.sort_meta_data(unbalancedMultiInfobox, r"Title") == unbalancedMultiInfobox, (
        r"Handle unbalanced brackets in comments"
    )
    stackTemplate = "{{Short description|A}}\r\n{{pp-blp|small=yes}}\r\n{{Use American English|date=September 2020}}\r\n{{Use mdy dates|date=August 2023}}\r\n{{stack begin}}\r\n{{Infobox person\r\n| name               = A\r\n| module             = }}\r\n{{stack end}}"
    assert parser2.sort_meta_data(stackTemplate, r"Title") == stackTemplate, (
        r"Don't sort when stack begin/stack end present"
    )
    stackTemplate = "{{Short description|A}}\r\n{{pp-blp|small=yes}}\r\n{{Use American English|date=September 2020}}\r\n{{Use mdy dates|date=August 2023}}\r\n{{stack|\r\n    {{Infobox person\r\n    | name               = A\r\n    | module             = }}\r\n}}"
    assert parser2.sort_meta_data(stackTemplate, r"Title") == stackTemplate, (
        r"Don't sort when stack present"
    )
    stackTemplate = "{{Short description|A}}\r\n{{pp-blp|small=yes}}\r\n{{Use American English|date=September 2020}}\r\n{{Use mdy dates|date=August 2023}}\r\n{{Collapsed infobox section begin}}\r\n{{Infobox person\r\n| name               = A\r\n| module             = }}\r\n{{Collapsed infobox section end}}"
    assert parser2.sort_meta_data(stackTemplate, r"Title") == stackTemplate, (
        r"Don't sort when Collapsed infobox section begin/end present"
    )
    correct9 = (
        "{{Short description|Operating system for Apple computers}}\r\n{{Infobox OS\r\n| name = macOS\r\n| support_status = Supported\r\n}}"
        + "\t\r\n\r\n"
        + r"'''macOS''', originally."
    )
    assert parser2.sort_meta_data(correct9, r"MacOS") == correct9.replace(r"	", r""), (
        r"Stray tab whitespace handled"
    )
    ub = "{{Short description|A}}\r\n{{BLP sources|date=June 2012}}\r\n\r\n{{Infobox person\r\n| name               = A\r\n| image              = A\r\n| caption            = A\r\n| birth_date         = {{Birth date and age|1955|07|07}}}<ref>A</ref>\r\n| birth_place        = A\r\n}}"
    assert parser2.sort_meta_data(ub, r"A") == ub, (
        r"No sort if zeroth section has unbalanced brackets"
    )
    magicWord = "{{Short description|A}}\r\n{{BLP sources|date=June 2012}}\r\n__FORCETOC__\r\n{{Infobox person\r\n| name               = A\r\n| image              = A\r\n| caption            = A\r\n| birth_place        = A\r\n}}"
    assert parser2.sort_meta_data(magicWord, r"A") == magicWord, (
        r"No sort if zeroth section contains magic word behaviour switch"
    )
    manyComments = "{{unreferenced|date=June 2018}}\r\n{{Infobox rugby union season\r\n| name             = 2018\r\n| image            =\r\n| Caption          =\r\n| relegated        =\r\n| matches          = 180\r\n| attendance       =\r\n| tries            = {{#expr:\r\n<!-- Round 1 -->\r\n<!-- Round 2 -->\r\n<!-- Round 3 -->\r\n<!-- Round 4 -->\r\n<!-- Round 5 -->\r\n<!-- Round 6 -->\r\n<!-- Round 7 -->\r\n<!-- Round 8 -->\r\n<!-- Round 9 -->\r\n<!-- Round 10 -->\r\n<!-- Round 11 -->\r\n<!-- Round 12 -->\r\n<!-- Round 13 -->\r\n<!-- Round 14 -->\r\n<!-- Round 15 -->\r\n<!-- Round 16 -->\r\n<!-- Round 17 -->\r\n<!-- Round 18 -->\r\n<!-- Round 19 -->\r\n<!-- Round 20 -->\r\n<!-- Round 21 -->\r\n<!-- Round 22 -->\r\n<!-- Round 23 -->\r\n<!-- Round 24 -->\r\n<!-- Round 25 -->\r\n<!-- Round 26 -->\r\n<!-- Playoffs -->\r\n}}\r\n| top point scorer =\r\n| top try scorer   =\r\n}}\r\n\r\nThe 2018 competition"
    assert parser2.sort_meta_data(manyComments, r"A") == manyComments, (
        r"Handle many comments in zeroth section"
    )
    foldedInfoboxes = "{{Short description|Category 4 Pacific hurricane}}\r\n{{Infobox weather event\r\n| name = Hurricane Rosa\r\n| formed = September 25, 2018\r\n| low = October 2, 2018\r\n}}{{Infobox weather event/NWS\r\n| winds = 130\r\n| pressure = 936\r\n}}{{Infobox weather event/Effects\r\n| year = 2018\r\n| damage = 51880000\r\n}}{{Infobox weather event/Footer\r\n| season = [[2018 Pacific hurricane season]]\r\n}}\r\n\r\n'''Hurricane Rosa''' was"
    assert parser2.sort_meta_data(foldedInfoboxes, r"A") == foldedInfoboxes, (
        r"Handle folded infoboxes in zeroth section"
    )
    commentBeforeOpeningSentence = "{{Short description|English naturalist and biologist (1809–1882)}}\r\n{{Other people}}\r\n{{Featured article}}\r\n{{pp-move}}\r\n{{Use British English|date=October 2024}}\r\n{{Use dmy dates|date=October 2024}}\r\n{{Infobox person\r\n| name               = Charles Darwin\r\n}}\r\n<!--Please consider discussing changes on the talk page...-->\r\n\r\n'''Charles Robert Darwin'''"
    assert (
        parser2.sort_meta_data(commentBeforeOpeningSentence, r"A") == commentBeforeOpeningSentence
    ), r"Handle comment before opening sentence in zeroth section"


def test_zeroth_section_sorting_extras() -> None:
    S = W.for_site(EN)
    otherMaintenanceTemplates = "{{Short description|Sculpture Chicago}}\r\n{{Featured article}}\r\n{{pp-move}}\r\n{{Alt text missing|Featured}}\r\n{{Use mdy dates|date=February 2025}}\r\n{{Use American English|date=January 2025}}\r\n{{Infobox artwork\r\n | image = A.JPG\r\n | image_size = 400px\r\n}}\r\nThe text"
    assert parser2.sort_meta_data(otherMaintenanceTemplates, r"A") == otherMaintenanceTemplates, (
        r"Handle other maintenance templates in zeroth section"
    )


def test_move_deletion_protection() -> None:
    S = W.for_site(EN)
    deletiontag = r"{{Prod blp}}"
    dablink = r"{{other people|Fred the dancer|Fred Smith (dancer)}}"
    maintenancetemp = r"{{cleanup}}"
    foo = r"The rest of the article"
    infobox = r"{{infobox hello}}"
    mi = "{{multiple issues|\r\n{{cleanup}}\r\n{{orphan}}            \r\n}}"
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"no change if already OK"
    assert (
        parser2.sort_meta_data(
            deletiontag + "\r\n" + dablink + "\r\n" + maintenancetemp + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"dablink above deletion"
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + maintenancetemp + "\r\n" + deletiontag + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"deletion above maintenance"
    deletiontag = r"{{Prod blp/dated}}"
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + maintenancetemp + "\r\n" + deletiontag + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"deletion above maintenance, dated prod"
    deletiontag = r"{{Article for deletion/dated}} <!-- foo -->"
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + maintenancetemp + "\r\n" + deletiontag + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"deletion above maintenance, AfD with comment"
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + mi + "\r\n" + deletiontag + "\r\n" + infobox + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + mi + "\r\n" + infobox + "\r\n" + foo
    ), r"deletion above multipleissues and mi above infobox"
    deletiontag = r'{{Prod blp/dated|concern=|month=September|day=2|year=2015|time=13:57|timestamp=2015|user=}} <!-- Do not use the "prod blp/dated" template directly; the above line is generated by "subst:prod blp|reason" -->'
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + maintenancetemp + "\r\n" + deletiontag + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"deletion above maintenance, dated prod and comment"
    deletiontag = (
        "<!-- foo -->\r\n{{Article for deletion/dated}} <!-- foo2 -->\r\n<!-- \r\nfoo3 \r\n-->"
    )
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + maintenancetemp + "\r\n" + deletiontag + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"deletion above maintenance, dated prod with multiple comments"
    maintenancetemp = r"{{unreferenced|date=March 2024}}"
    deletiontag = "<!-- Please do not remove or change this AfD message until the discussion has been closed. -->\r\n<!-- The nomination page for this article already...\r\n-->{{Article for deletion/dated|page=Foo|timestamp=20240331140235|year=2024|month=March|day=31|substed=yes}}\r\n<!-- Once discussion is closed, please place on talk page: {{Old AfD multi|page=Foo|date=31 March 2024|result='''keep'''}} -->\r\n<!-- End of AfD message, feel free to edit beyond this point -->"
    assert (
        parser2.sort_meta_data(
            dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo, r"Foo"
        )
        == dablink + "\r\n" + deletiontag + "\r\n" + maintenancetemp + "\r\n" + foo
    ), r"deletion then maintenance, dated prod with multiple comments inc newlines"
    correct10 = "{{short description|Operating}} <!--comm1-->\r\n<!-- Please do not remove or change this AfD message until the discussion has been closed. -->\r\n<!-- The nomination page for this article already...\r\n-->{{Article for deletion/dated|page=Foo|timestamp=20240331140235|year=2024|month=March|day=31|substed=yes}}\r\n<!-- Once discussion is closed, please place on talk page: {{Old AfD multi|page=Foo|date=31 March 2024|result='''keep'''}} -->\r\n<!-- End of AfD message, feel free to edit beyond this point -->\r\n{{Excessive citations}}\r\n{{macOS sidebar}}\r\n\r\n'''macOS''', originally."
    assert parser2.sort_meta_data(correct10, r"MacOS") == correct10, (
        r"Handles comment after {{short description}} that isn't part of AFD comments"
    )


def test_move_dablinks_comments_tests() -> None:
    S = W.for_site(EN)
    d = "Fred is a doctor.\r\nFred has a dog.\r\n[[Category:Dog owners]]\r\n{{some template}}\r\n"
    e = r"<!-- {{otheruses}} this allows users with [[WP:POPUPS|popups]] to disambiguate links.-->"
    assert genfixes.move_template(d + e, W.Dablinks) == d + e
    f = "{{for|the book by René Descartes|The World (Descartes)}}\r\n<!--\r\nMight eventually be relevant on a disambig page?  But these are a redirect and a not direct reference, so they're pretty irrelevant for now.\r\n{{For|the song by the [[Thievery Corporation]]|Le Monde (song)}}\r\n{{For|the drum & bass dj [[Lemon D]]| Lemon D}}\r\n-->"
    assert genfixes.move_template(f, W.Dablinks) == f


def test_remove_disambig() -> None:
    S = W.for_site(EN)
    dab = r"{{dab}}"
    foo = r"foo"
    a = dab + "\r\n" + foo
    assert ((_t := genfixes.remove_disambig(a)), (a := _t[0]))[0][1] == dab
    assert a == "\r\n" + foo
    a = foo
    assert len(((_t := genfixes.remove_disambig(a)), (a := _t[0]))[0][1]) == 0
    assert a == foo
    a = r"<!--" + dab + r"-->" + "\r\n" + foo
    assert len(((_t := genfixes.remove_disambig(a)), (a := _t[0]))[0][1]) == 0
    assert a == r"<!--" + dab + r"-->" + "\r\n" + foo
    a = dab + "<!--comm-->\r\n" + foo
    assert ((_t := genfixes.remove_disambig(a)), (a := _t[0]))[0][1] == dab + r"<!--comm-->", (
        r"Handles disambig template with comment after"
    )
    assert a == "\r\n" + foo


def test_move_maintenance_tags_tests() -> None:
    S = W.for_site(EN)
    d = "Fred is a doctor.\r\nFred has a dog.\r\n[[Category:Dog owners]]\r\n{{some template}}\r\n"
    e = r"{{Underlinked|date=May 2008}}"
    assert genfixes.move_template(d + e, W.MaintenanceTemplates) == e + "\r\n" + d
    e = r"{{underlinked|date=May 2008}}"
    assert genfixes.move_template(d + e, W.MaintenanceTemplates) == e + "\r\n" + d
    e = r"{{underlinked|date=May 2008}} <!-- some comment to keep here-->"
    assert genfixes.move_template(d + e, W.MaintenanceTemplates) == e + "\r\n" + d
    e = r"{{cleanup|date=May 2008}}"
    assert genfixes.move_template(d + e, W.MaintenanceTemplates) == e + "\r\n" + d, (
        r"template moved when not a section one"
    )
    e = r"{{cleanup|section|date=May 2008}}"
    assert genfixes.move_template(d + e, W.MaintenanceTemplates) == d + e, (
        r"section templates not moved"
    )
    f = "{{cleanup|date=June 2009}}\r\n" + e + d
    assert genfixes.move_template(f, W.MaintenanceTemplates) == f
    g = "{{BLP unreferenced|date=August 2009|bot=yes}}\r\n{{Underlinked|date=February 2008}}\r\n'''Charles M. McKim'''"
    assert genfixes.move_template(g, W.MaintenanceTemplates) == g
    h1 = r"{{Infobox foo| sdajklfsdjk | dDJfsdjkl }}"
    h2 = r"{{Underlinked|date=February 2008}}"
    h3 = r"'''Charles M. McKim'''"
    assert (
        genfixes.move_template(h2 + "\r\n" + h1 + "\r\n" + h3, W.MaintenanceTemplates)
        == h2 + "\r\n" + h1 + "\r\n" + h3
    )
    assert (
        genfixes.move_template(h1 + "\r\n" + h2 + "\r\n\r\n" + h3, W.MaintenanceTemplates)
        == h2 + "\r\n" + h1 + "\r\n\r\n" + h3
    )
    h2 = r"{{Notability|Web|date=February 2008}}"
    assert (
        genfixes.move_template(h2 + "\r\n" + h1 + "\r\n" + h3, W.MaintenanceTemplates)
        == h2 + "\r\n" + h1 + "\r\n" + h3
    )
    assert (
        genfixes.move_template(h1 + "\r\n" + h2 + "\r\n\r\n" + h3, W.MaintenanceTemplates)
        == h2 + "\r\n" + h1 + "\r\n\r\n" + h3
    )
    i1 = r"{{cleanup|date=June 2009}}"
    e = r"{{underlinked|date=May 2008}}"
    assert (
        genfixes.move_template(e + "\r\nfoo\r\n" + i1, W.MaintenanceTemplates)
        == e + "\r\n" + i1 + "\r\nfoo\r\n"
    )
    CommentedOut = (
        r"<!---sufficient-?---{{Cleanup|date=January 2010}}--{{Wikify|date=January 2010}}---?--->"
    )
    assert genfixes.move_template(CommentedOut, W.MaintenanceTemplates) == CommentedOut, (
        r"no change to commented out tags"
    )
    NewMultipleIssues = r"{{multiple issues|{{Cleanup|date=January 2010}}}}"
    assert parser2.sort_meta_data(NewMultipleIssues, r"A") == NewMultipleIssues, (
        r"don't pull tags from new-style {{multiple issues}}"
    )
    LaterSection = "hello\r\n==Sec==\r\n{{cleanup|date=May 2012}}\r\nEnd"
    assert parser2.sort_meta_data(LaterSection, r"A") == LaterSection, (
        r"maintenance tags outside of zeroth section not moved"
    )


def test_move_maintenance_tags_dupes() -> None:
    S = W.for_site(EN)
    d = "Fred is a doctor.\r\nFred has a dog.\r\n[[Category:Dog owners]]\r\n{{some template}}"
    e = r"{{Underlinked|date=May 2008}}"
    assert (
        genfixes.move_template(d + "\r\n" + e + "\r\n" + e, W.MaintenanceTemplates)
        == e + "\r\n" + d + "\r\n"
    ), r"move and dedupe"
    assert (
        genfixes.move_template(e + "\r\n" + e + "\r\n" + d, W.MaintenanceTemplates)
        == e + "\r\n" + d
    ), r"dedupe when move not required"
    assert (
        genfixes.move_template(
            "{{pp-pc}}\r\n{{pp-pc|small=yes}}\r\n\r\nFoo", W.DeletionProtectionTags
        )
        == "{{pp-pc | small=yes}}\r\n\r\nFoo"
    ), r"dedupe when move not required - deletion tags"


def test_move_multiple_issues() -> None:
    S = W.for_site(EN)
    correct = "{{multiple issues|\r\n{{orphan}}\r\n{{cleanup}}\r\n}}\r\n{{infobox foo}}\r\n\r\nFred has a dog.\r\n[[Category:Dog owners]]"
    assert (
        genfixes.move_multiple_issues(
            "{{infobox foo}}\r\n{{multiple issues|\r\n{{orphan}}\r\n{{cleanup}}\r\n}}\r\nFred has a dog.\r\n[[Category:Dog owners]]"
        )
        == correct
    ), r"mi moved above infobox"
    assert genfixes.move_multiple_issues(correct) == correct, r"no change when already correct"
    commented = "{{infobox foo}}\r\n<!--{{multiple issues|\r\n{{orphan}}\r\n{{cleanup}}\r\n}}-->\r\nFred has a dog.\r\n[[Category:Dog owners]]"
    assert genfixes.move_multiple_issues(commented) == commented, (
        r"commented out infobox so nothing to do"
    )
    noinfobox = "{{foo}}\r\n{{multiple issues|\r\n{{orphan}}\r\n{{cleanup}}\r\n}}\r\nFred has a dog.\r\n[[Category:Dog owners]]"
    assert genfixes.move_multiple_issues(noinfobox) == noinfobox, r"nothing to move if no infobox"
    noMI = "{{infobox foo}}\r\n{{something|\r\n{{one}}\r\n{{two}}\r\n}}\r\nFred has a dog.\r\n[[Category:Dog owners]]"
    assert genfixes.move_multiple_issues(noMI) == noMI, r"nothing to move if no MultipleIssues"


def test_move_portal_templates_tests() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
    ), r"example 1"
    assert (
        genfixes.move_portal_templates(
            "text here {{Portal|Football}}\r\ntext here2\r\n== see also ==\r\nsome words"
        )
        == "text here \r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
    ), r"example 2"
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
    ), r"whitespace at end of line after portal template"
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Sport}}\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\n{{Portal|Sport}}\r\nsome words"
    ), r"example 3"
    assert (
        genfixes.move_portal_templates(
            "{{Portal|Football}}\r\ntext here\r\ntext here2\r\n== see also ==\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
    ), r"example 4"
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|abc}}\r\ntext here2\r\n== see also==\r\n* Fred"
        )
        == "text here\r\ntext here2\r\n== see also==\r\n{{Portal|abc}}\r\n* Fred"
    ), r"example 4"
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\n* Fred\r\n== hello ==\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\n* Fred\r\n== hello ==\r\nsome words"
    ), r"example 5"
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\n* Fred\r\n=== hello ===\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\n* Fred\r\n=== hello ===\r\nsome words"
    ), r"example 6"
    assert (
        genfixes.move_portal_templates(
            "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
    ), r"if portal is already in 'see also', don't move it"
    assert (
        genfixes.move_portal_templates(
            "text here\r\ntext here2\r\n== see also ==\r\n* Fred\r\n{{Portal|Football}}\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n* Fred\r\n{{Portal|Football}}\r\nsome words"
    )
    assert (
        genfixes.move_portal_templates(
            "text here\r\ntext here2\r\n== see also ==\r\n* Fred\r\n=== portals ===\r\n{{Portal|Football}}\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n* Fred\r\n=== portals ===\r\n{{Portal|Football}}\r\nsome words"
    )


def test_move_template_to_see_also_section() -> None:
    S = W.for_site(EN)
    Commented = "A\r\n<!-- {{ext}} -->\r\n== See also==\r\n* [[Other]]"
    assert (
        genfixes.move_template_to_see_also_section(Commented, tools.nested_template_regex(r"ext"))
        == Commented
    )


def test_move_template_to_end_of_article() -> None:
    S = W.for_site(EN)
    textBefore = "{{short description|Text}}\r\n{{coord}}\r\n\r\nText.\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    textAfter = "{{short description|Text}}\r\n\r\nText.\r\n==Last section==\r\n\r\n{{coord}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textAfter, (
        r"Move coord to last section above DEFAULTSORT/cats"
    )
    assert parser2.sort_meta_data(textAfter, r"A") == textAfter, (
        r"No change when template already in last section"
    )
    textBefore = "{{short description|Text}}\r\n{{coord}}\r\n{{coord|2}}\r\n\r\nText.\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    textAfter = "{{short description|Text}}\r\n\r\nText.\r\n==Last section==\r\n\r\n{{coord}}\r\n{{coord|2}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textAfter, (
        r"Move coord to last section - 2 templates"
    )
    textBefore = "{{short description|Text}}\r\n{{coord}}\r\n\r\nText.\r\n==Last section==\r\n{{authority control}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    textAfter = "{{short description|Text}}\r\n\r\nText.\r\n==Last section==\r\n{{authority control}}\r\n\r\n{{coord}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textAfter, (
        r"Move coord to last section - another template in last section"
    )
    textBefore = "{{short description|Text}}\r\n{{coord missing}}\r\n\r\nText.\r\n==Last section==\r\n{{authority control}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    textAfter = "{{short description|Text}}\r\n\r\nText.\r\n==Last section==\r\n{{authority control}}\r\n\r\n{{coord missing}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textAfter, (
        r"Move coord missing to last section"
    )
    textBefore = "{{short description|Text}}\r\n{{Infobox something|\r\nloc={{coord}}\r\nparam=a}}\r\nText.\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textBefore, (
        r"Template not moved - nested in another"
    )
    textBefore = "{{short description|Text}}\r\n{{Infobox something|\r\nloc=\r\n{{coord}}\r\nparam=a}}\r\nText.\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textBefore, (
        r"Template not moved - nested in another, start of line"
    )
    textBefore = "{{short description|Text}}\r\n{{coord}}\r\n{{Infobox something|\r\nloc={{coord|2}}\r\nparam=a}}\r\nText.\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    textAfter = "{{short description|Text}}\r\n{{Infobox something|\r\nloc={{coord|2}}\r\nparam=a}}\r\nText.\r\n==Last section==\r\n\r\n{{coord}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textAfter, (
        r"One a lone and one nested in another"
    )
    notzeroth = "{{short description|Text}}\r\nText.\r\n==First section==\r\n{{coord}}\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(notzeroth, r"A") == notzeroth, (
        r"Templates not moved beyond zeroth section"
    )
    textBefore = "{{short description|Text}}\r\n{{coord}}\r\n\r\n==A section==\r\n{{coord|2}}\r\n\r\n==Last section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    textAfter = "{{short description|Text}}\r\n\r\n==A section==\r\n{{coord|2}}\r\n\r\n==Last section==\r\n\r\n{{coord}}\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(textBefore, r"A") == textAfter, (
        r"Templates only taken from zeroth section"
    )
    commentedOut = "{{short description|Text}}\r\nText.\r\n<!--{{coord}}-->\r\n==First section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(commentedOut, r"A") == commentedOut, (
        r"Templates not moved out of comments"
    )
    commentedOut = "{{short description|Text}}\r\nText.\r\n<!--\r\n{{coord}}-->\r\n==First section==\r\n\r\n{{DEFAULTSORT:Something}}\r\n[[Category:One]]"
    assert parser2.sort_meta_data(commentedOut, r"A") == commentedOut, (
        r"Templates not moved out of comments, 2"
    )


def test_move_portal_templates_tests_duplicates() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Football}}\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\nsome words"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words"
    )
    assert (
        genfixes.move_portal_templates(
            "text here\r\n{{Portal|Football}}\r\ntext here2\r\n== see also ==\r\nsome words\r\n==other==\r\n{{Portal|Football}}"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words\r\n==other==\r\n"
    )
    assert (
        genfixes.move_portal_templates(
            "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words\r\n==other==\r\n{{Portal|Football}}"
        )
        == "text here\r\ntext here2\r\n== see also ==\r\n{{Portal|Football}}\r\nsome words\r\n==other==\r\n"
    )


def test_move_sister_links_test() -> None:
    S = W.for_site(EN)
    WiktInExtLinks = "text here\r\ntext here2\r\n== External links ==\r\n{{wiktionary}}\r\n* Fred"
    assert (
        genfixes.move_sisterlinks(
            "text here\r\n{{wiktionary}}\r\ntext here2\r\n== External links ==\r\n* Fred\r\n== other ==\r\nx"
        )
        == "text here\r\ntext here2\r\n== External links ==\r\n{{wiktionary}}\r\n* Fred\r\n== other ==\r\nx"
    ), r"another section at end"
    assert (
        genfixes.move_sisterlinks(
            "text here\r\n{{Sister project links|Programming languages|wikt=programming language|b=Computer Programming|s=How to Think Like a Computer Scientist|commons=Category:Programming languages}}\r\ntext here2\r\n== External links ==\r\n* Fred\r\n== other ==\r\nx"
        )
        == "text here\r\ntext here2\r\n== External links ==\r\n{{Sister project links|Programming languages|wikt=programming language|b=Computer Programming|s=How to Think Like a Computer Scientist|commons=Category:Programming languages}}\r\n* Fred\r\n== other ==\r\nx"
    ), r"sister project links may contain many parameters"
    assert (
        genfixes.move_sisterlinks(
            "text here\r\n{{wiktionary}}\r\ntext here2\r\n== External links ==\r\n* Fred"
        )
        == WiktInExtLinks
    ), r"ext links is last section"
    assert genfixes.move_sisterlinks(WiktInExtLinks) == WiktInExtLinks, r"wikt already in ext links"
    CommentedOut = "text here\r\n<!--{{wiktionary}}-->\r\ntext here2\r\n== External links ==\r\n* Fred\r\n== other ==\r\nx"
    assert genfixes.move_sisterlinks(CommentedOut) == CommentedOut, r"no change if commented out"
    NoExtLinks = "text here\r\n{{wiktionary}}\r\ntext here2\r\n== other ==\r\nx"
    assert genfixes.move_sisterlinks(NoExtLinks) == NoExtLinks, r"no ext links sections"


def test_move_more_no_footnotes_tests() -> None:
    S = W.for_site(EN)
    a = r"{{nofootnotes}}"
    a2 = r"{{Morefootnotes}}"
    b = "\r\n'''Article''' words.\r\n== section ==\r\nwords.\r\n"
    c = "== References ==\r\n"
    d = "== Notes ==\r\n"
    e = "== Footnotes ==\r\n"
    f = "'''Article''' words.\r\n== section ==\r\n{{nofootnotes}}\r\nwords.\r\n"
    g = r"words"
    assert (
        genfixes.move_template_to_references_section(a + b + c + g, W.MoreNoFootnotes, True)
        == b + c + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + d + g, W.MoreNoFootnotes, True)
        == b + d + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + e + g, W.MoreNoFootnotes, True)
        == b + e + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + e, W.MoreNoFootnotes, True)
        == b + e + a + "\r\n"
    )
    assert (
        genfixes.move_template_to_references_section(a2 + b + e, W.MoreNoFootnotes, True)
        == b + e + a2 + "\r\n"
    )
    assert (
        genfixes.move_template_to_references_section(a2 + b + e, W.MoreNoFootnotes, False)
        == b + e + a2 + "\r\n"
    )
    assert (
        genfixes.move_template_to_references_section(
            a + b + d.replace(r"Notes", r"Notes and references") + g, W.MoreNoFootnotes, True
        )
        == b + d.replace(r"Notes", r"Notes and references") + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(f + c + g, W.MoreNoFootnotes, True)
        == f + c + g
    )
    assert (
        genfixes.move_template_to_references_section(f + d + g, W.MoreNoFootnotes, True)
        == f + d + g
    )
    assert (
        genfixes.move_template_to_references_section(f + e + g, W.MoreNoFootnotes, True)
        == f + e + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + c + c + g, W.MoreNoFootnotes, True)
        == b + c + a + "\r\n" + c + g
    )


def test_move_ibid_tests() -> None:
    S = W.for_site(EN)
    a = r"{{Ibid|date=May 2009}}"
    b = "\r\n'''Article''' words<ref>ibid</ref>.\r\n== section ==\r\nwords.\r\n"
    c = "== References ==\r\n"
    d = "== Notes ==\r\n"
    e = "== Footnotes ==\r\n"
    f = "'''Article''' words.\r\n== section ==\r\n{{Ibid|date=May 2009}}\r\nwords.\r\n"
    g = r"more words"
    assert (
        genfixes.move_template_to_references_section(a + b + c + g, W.Ibid, True)
        == b + c + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + d + g, W.Ibid, True)
        == b + d + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + e + g, W.Ibid, True)
        == b + e + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + e, W.Ibid, True) == b + e + a + "\r\n"
    )
    assert (
        genfixes.move_template_to_references_section(a + b + c + g, W.Ibid, False)
        == b + c + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + d + g, W.Ibid, False)
        == b + d + a + "\r\n" + g
    )
    assert (
        genfixes.move_template_to_references_section(a + b + e + g, W.Ibid)
        == b + e + a + "\r\n" + g
    )
    assert genfixes.move_template_to_references_section(a + b + e, W.Ibid) == b + e + a + "\r\n"
    assert (
        genfixes.move_template_to_references_section(a + b + c + d + g, W.Ibid, False)
        == b + c + d + a + "\r\n" + g
    ), r"move to Notes ahead of References"
    assert (
        genfixes.move_template_to_references_section(b + d + a + "\r\n" + c + g, W.Ibid)
        == b + d + a + "\r\n" + c + g
    ), r"No change: ibid already in notes section"
    assert (
        genfixes.move_template_to_references_section(f + c + g, W.Ibid, False)
        == "'''Article''' words.\r\n== section ==\r\n\r\nwords.\r\n" + c + a + "\r\n" + g
    )
    e = "== Sources ==\r\n"
    assert genfixes.move_template_to_references_section(a + b + e, W.Ibid) == b + e + a + "\r\n"


def test_move_external_links_tests() -> None:
    S = W.for_site(EN)
    a = "'''article'''\r\n== blah ==\r\nwords<ref>abc</ref>"
    b = "== external links ==\r\n* [http://www.site.com a site]"
    c = "== References ==\r\n{{reflist}}"
    d = "=== another section ===\r\nblah"
    e = r"[[Category:Foos]]"
    f = r"{{some footer thing}}"
    g = "== another section ==\r\nblah"
    h = r"{{DEFAULTSORT:Foo, bar}}"
    assert (
        genfixes.move_external_links(a + "\r\n" + b + "\r\n" + c + "\r\n" + e)
        == a + "\r\n" + c + "\r\n" + b + "\r\n" + e
    )
    assert (
        genfixes.move_external_links(a + "\r\n" + b + "\r\n" + c + "\r\n" + h)
        == a + "\r\n" + c + "\r\n" + b + "\r\n" + h
    )
    assert (
        genfixes.move_external_links(a + "\r\n" + b + "\r\n" + c + "\r\n" + g)
        == a + "\r\n" + c + "\r\n" + b + "\r\n" + g
    )
    assert genfixes.move_external_links(a + "\r\n" + c + "\r\n" + b) == a + "\r\n" + c + "\r\n" + b
    assert (
        genfixes.move_external_links(a + "\r\n" + c + "\r\n" + b + "\r\n" + g)
        == a + "\r\n" + c + "\r\n" + b + "\r\n" + g
    )
    assert (
        genfixes.move_external_links(a + "\r\n" + b + "\r\n" + c + "\r\n" + f)
        == a + "\r\n" + b + "\r\n" + c + "\r\n" + f
    )
    assert (
        genfixes.move_external_links(a + "\r\n" + b + "\r\n" + c + "\r\n" + d)
        == a + "\r\n" + b + "\r\n" + c + "\r\n" + d
    )
    ExtLinkRef = a + "\r\n" + b + "<ref>foo</ref>\r\n" + c + "\r\n" + e
    assert genfixes.move_external_links(ExtLinkRef) == ExtLinkRef
    assert (
        genfixes.move_external_links(
            a + "\r\n" + b + "\r\n" + c.replace(r"References", r"Notes") + "\r\n" + e
        )
        == a + "\r\n" + c.replace(r"References", r"Notes") + "\r\n" + b + "\r\n" + e
    ), r"Notes"


def test_move_see_also() -> None:
    S = W.for_site(EN)
    a = "'''article'''\r\n== blah ==\r\nwords<ref>abc</ref>"
    b = "== See also ==\r\n* [http://www.site.com a site]"
    c = "== References ==\r\n{{reflist}}"
    d = "== another section ==\r\nblah"
    assert (
        genfixes.move_see_also(a + "\r\n" + c + "\r\n" + b + "\r\n" + d)
        == a + "\r\n" + b + "\r\n\r\n" + c + "\r\n" + d
    ), r"reorder"
    assert (
        genfixes.move_see_also(a + "\r\n" + b + "\r\n" + c + "\r\n" + d)
        == a + "\r\n" + b + "\r\n" + c + "\r\n" + d
    ), r"no change when already correct"
    TwoReferencesSection = a + "\r\n" + c + "\r\n" + b + "\r\n" + c + "\r\n" + d
    assert genfixes.move_see_also(TwoReferencesSection) == TwoReferencesSection, (
        r"no change when two references sections"
    )
    assert (
        genfixes.move_see_also(
            a + "\r\n" + c.replace(r"References", r"Notes") + "\r\n" + b + "\r\n" + d
        )
        == a + "\r\n" + b + "\r\n\r\n" + c.replace(r"References", r"Notes") + "\r\n" + d
    ), r"reorder, Notes"


def test_categories_for_deletion() -> None:
    S = W.for_site(EN)
    a = r"[[Category:Railway companies established in 1851]]"
    b1 = r"[[Category:Pages for deletion]]"
    b2 = r"[[Category:Categories for deletion]]"
    b3 = r"[[Category:Articles for deletion]]"
    k = a + "\r\n" + b1
    assert ((_t := parser2.sorter.remove_cats(k, r"test")), (k := _t[0]))[0][1] == a + "\r\n", (
        r"Pages for deletion cat not kept"
    )
    k = a + "\r\n" + b2
    assert ((_t := parser2.sorter.remove_cats(k, r"test")), (k := _t[0]))[0][1] == a + "\r\n", (
        r"Categories for deletion cat not kept"
    )
    k = a + "\r\n" + b3
    assert ((_t := parser2.sorter.remove_cats(k, r"test")), (k := _t[0]))[0][1] == a + "\r\n", (
        r"Articles for deletion cat not kept"
    )


def test_category_and_comment_tests() -> None:
    S = W.for_site(EN)
    i = "#REDIRECT [[Ohio and Mississippi Railway]]\r\n\r\n"
    j = "[[Category:Predecessors of the Baltimore and Ohio Railroad]]\r\n<!--Illinois company:-->\r\n[[Category:Railway companies established in 1851]]\r\n[[Category:Railway companies disestablished in 1862]]\r\n[[Category:Defunct Illinois railroads]]\r\n<!--Indiana company:-->\r\n[[Category:Railway companies established in 1848]]\r\n[[Category:Railway companies disestablished in 1867]]\r\n[[Category:Defunct Indiana railroads]]\r\n[[Category:Defunct Ohio railroads]]"
    k = i + j
    assert ((_t := parser2.sorter.remove_cats(k, r"test")), (k := _t[0]))[0][1] == j + "\r\n", (
        r"comments between cats"
    )
    l = i + j + "\r\n<!--foo-->"
    assert ((_t := parser2.sorter.remove_cats(l, r"test")), (l := _t[0]))[0][1] == j + "\r\n", (
        r"comment after cat"
    )
    assert "\r\n" + r"<!--foo-->" in l, r"comment after cat 2"
    m = "[[Category:American women writers]]\r\n[[Category:Autism activists]]\r\n<!--LBGT categories are not to be used on bios of living people unless they self-identify with the label and it is relevant to their public lives[[Category:Bisexual actors]]\r\n[[Category:LGBT models]]\r\n[[Category:LGBT people from the United States]]\r\n[[Category:LGBT television personalities]]-->\r\n[[Category:Parents of people on the autistic spectrum]]"
    n = m
    assert ((_t := parser2.sorter.remove_cats(n, r"test")), (n := _t[0]))[0][1] == m + "\r\n", (
        r"cats not pulled out of comments"
    )
    o = "[[Category:Canadian Aviation Hall of Fame inductees]]\r\n[[Category:Canadian World War I pilots]] <!-- If he was a Flying Ace, use the Canadian subcategory -->\r\n[[Category:Canadian World War II pilots]] <!-- If he was a Flying Ace, use the subcategory -->\r\n[[Category:Foo]]"
    p = o
    assert ((_t := parser2.sorter.remove_cats(p, r"test")), (p := _t[0]))[0][1] == o + "\r\n", (
        r"comments on line"
    )
    q = "#REDIRECT [[Alton Railroad]]\r\n\r\n"
    r = "{{DEFAULTSORT:Joliet Chicago  Railroad}}\r\n[[Category:Predecessors of the Alton Railroad]]\r\n[[Category:Railway companies established in 1855]]\r\n[[Category:Railway companies disestablished in 1950]]<!--http://bulk.resource.org/courts.gov/c/F2/264/264.F2d.445.12430_1.html-->\r\n[[Category:Defunct Illinois railroads]]"
    s = q + r
    assert ((_t := parser2.sorter.remove_cats(s, r"test")), (s := _t[0]))[0][1] == r + "\r\n", (
        r"comments on line end"
    )
    r2 = "{{DEFAULTSORT:Joliet Chicago  Railroad}}\r\n[[Category:Predecessors of the Alton Railroad]]\r\n[[Category:Railway companies established in 1855]]\r\n[[Category:Railway companies disestablished in 1950]]\r\n[[Category:Defunct Illinois railroads]]  <!--comm-->"
    s = q + r2
    assert ((_t := parser2.sorter.remove_cats(s, r"test")), (s := _t[0]))[0][1] == r2 + "\r\n", (
        r"comment after last cat on same line not moved"
    )
    bug1a = "[[Category:Emory University]]\r\n[[Category:Law schools in Georgia (U.S. state)]]\r\n<!-- A work in progress to incorporate into nav\r\n[[Category:Southern Law Schools]]\r\n[[Category:South Atlantic Law Schools]]\r\n -->"
    bug1b = "\r\n\r\n{{lawschool-stub}}"
    t = bug1a + bug1b
    assert ((_t := parser2.sorter.remove_cats(t, r"test")), (t := _t[0]))[0][1] == bug1a + "\r\n", (
        r"commented out cats"
    )
    bug1c = "<!-- foo bar-->\r\n{{info}}\r\ntext\r\n"
    t = bug1c + bug1a + bug1b
    assert ((_t := parser2.sorter.remove_cats(t, r"test")), (t := _t[0]))[0][1] == bug1a + "\r\n", (
        r"commented out plus comments"
    )
    bug2 = "{{DEFAULTSORT:A}}\r\n<!--The 1951 birth date has been upheld in court, please do not add this category.[[Category:1941 births]]-->\r\n[[Category:Living People]]"
    t = bug2
    assert ((_t := parser2.sorter.remove_cats(t, r"test")), (t := _t[0]))[0][1] == bug2 + "\r\n", (
        r"commented out and not"
    )
    nw = "Hello\r\n<nowiki>[[Category:LGBT people from the United States]]\r\n[[Category:LGBT television personalities]]</nowiki>\r\n\r\n[[Category:American women writers]]\r\n[[Category:Autism activists]]\r\n[[Category:Parents of people on the autistic spectrum]]"
    assert (
        ((_t := parser2.sorter.remove_cats(nw, r"test")), (nw := _t[0]))[0][1]
        == "[[Category:American women writers]]\r\n[[Category:Autism activists]]\r\n[[Category:Parents of people on the autistic spectrum]]\r\n"
    ), r"Don't pull cats from nowiki"
    nw = "Hello\r\n<nowiki>[[Category:LGBT people from the United States]]\r\n[[Category:LGBT television personalities]]</nowiki>\r\n\r\n[[Category:American women writers]]\r\n[[Category:Autism activists]]\r\n[[Category:Parents of people on the autistic spectrum]]"
    assert (
        r"[[Category:LGBT people from the United States]]"
        not in ((_t := parser2.sorter.remove_cats(nw, r"test")), (nw := _t[0]))[0][1]
    ), r"Don't pull cats from nowiki 2"
    iw1 = "[[Category:Hampshire|  ]]\r\n[[Category:Articles including recorded pronunciations (UK English)]]\r\n[[Category:Non-metropolitan counties]]"
    iw2 = "\r\n\r\n<!--interwiki-->\r\n[[af:Hampshire]]"
    iwall = iw1 + iw2
    assert ((_t := parser2.sorter.remove_cats(iwall, r"test")), (iwall := _t[0]))[0][
        1
    ] == iw1 + "\r\n", r"don't pull the interwiki comment"
    assert r"<!--interwiki-->" in iwall, r"don't pull the interwiki comment"
    writers = "[[Category:Writers from Alabama]]\r\n[[Category:Writers from North Carolina]]\r\n[[Category:Writers from North Carolina]]\r\n\r\n<!-- novelists tree -->\r\n[[Category:20th-century American novelists]]"
    assert (
        ((_t := parser2.sorter.remove_cats(writers, r"test")), (writers := _t[0]))[0][1]
        == "[[Category:Writers from Alabama]]\r\n[[Category:Writers from North Carolina]]\r\n\r\n<!-- novelists tree -->\r\n[[Category:20th-century American novelists]]"
        + "\r\n"
    ), r"Dupe cat removed if second has comment"
    comm = r"<!--[[Category:foo]]-->" + "\r\n"
    assert len(((_t := parser2.sorter.remove_cats(comm, r"test")), (comm := _t[0]))[0][1]) == 0, (
        r"Don't move commented out cats"
    )
    comm = "#REDIRECT [[X]]\r\n<!-- XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX \r\n XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX \r\n XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX \r\n XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX \r\n XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX \r\n XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX XXXXXXXXXX \r\n\r\n[[Category:Foo]]\r\n[[Category:Foo2]]\r\n -->"
    assert len(((_t := parser2.sorter.remove_cats(comm, r"test")), (comm := _t[0]))[0][1]) == 0, (
        r"Don't move commented out cats, large comment"
    )
    longComment = "Hello\r\n<!--{{Navboxes\r\n|title=Candinho managerial positions\r\n|list1=\r\n{{Esporte Clube São Bento managers}}\r\n{{Clube Atlético Juventus managers}}\r\n{{Al-Hilal FC managers}}\r\n{{Grêmio Foot-Ball Porto Alegrense managers}}\r\n{{Santos Futebol Clube managers}}\r\n{{Clube de Regatas do Flamengo managers}}\r\n{{Fluminense Football Club managers}}\r\n{{Esporte Clube Bahia managers}}\r\n{{Clube Atlético Bragantino managers}}\r\n{{Guarani Futebol Clube managers}}\r\n{{Esporte Clube Vitória managers}}\r\n{{Sport Club Corinthians Paulista managers}}\r\n{{Associação Portuguesa de Desportos managers}}\r\n{{Goiás Esporte Clube managers}}\r\n{{Al-Ittihad managers}}\r\n{{Brazil national football team managers}}\r\n{{Sociedade Esportiva Palmeiras managers}}\r\n}} [[Category:Pages where template include size is exceeded]]-->\r\n\r\n{{DEFAULTSORT:Candinho}}\r\n[[Category:1945 births]]\r\n[[Category:Living people]]"
    assert (
        r"[[Category:Pages where template include size is exceeded]]"
        not in ((_t := parser2.sorter.remove_cats(longComment, r"test")), (longComment := _t[0]))[
            0
        ][1]
    ), r"Don't pull out of long comment section"
    sameCatInComment = "<!-- [[Category:1980s cars]] Not needed because [[Category:Cars introduced in 1985]] parent cat overrules it. See [[WP:SUBCAT]] -->\r\n[[Category:1990s cars]]\r\n[[Category:Cars introduced in 1985]]\r\n[[Category:Honda vehicles|Today]]\r\n[[Category:Kei cars]]\r\n[[Category:Cars discontinued in 1998]]"
    sameCatInComment2 = sameCatInComment
    assert (
        (_t := parser2.sorter.remove_cats(sameCatInComment, r"Test")),
        (sameCatInComment := _t[0]),
    )[0][1] == sameCatInComment2 + "\r\n", r"Handle a cat that is also in a comment"


def test_category_and_comment_tests2() -> None:
    S = W.for_site(EN)
    correct = "{{DEFAULTSORT:2024-25 Turkish Basketball Super League}}\r\n[[Category:Basketbol Süper Ligi seasons]]\r\n[[Category:2024–25 in European basketball leagues|Turkish]]\r\n[[Category:2024–25 in Turkish basketball|1]]\r\n[[Category:Current basketball seasons|Turkey]]\r\n<!-- [[Category:Current basketball seasons|Turkey]] -->"
    sameCatInComment = correct
    assert (
        (_t := parser2.sorter.remove_cats(sameCatInComment, r"Test")),
        (sameCatInComment := _t[0]),
    )[0][1] == correct + "\r\n", r"Handle a cat that is also in a comment - comment after"
    correct2 = "[[Category:1985 x in the United Kingdom]] <!-- Text... a parent of [[Category:1985 y in the United Kingdom]] -->\r\n[[Category:1985 in London]]\r\n[[Category:1985 y in the United Kingdom]]\r\n[[Category:1980s c in London]] <!-- Text... a parent of [[Category:1980s z in London]] -->\r\n[[Category:1980s z in London]]\r\n[[Category:20th century in a]]"
    sameCatInComment = correct2
    assert (
        (_t := parser2.sorter.remove_cats(sameCatInComment, r"Test")),
        (sameCatInComment := _t[0]),
    )[0][1] == correct2 + "\r\n", r"Handle a cat that is also in a comment - comment before"
    correct3 = "{{DEFAULTSORT:Juba, Master}}\r\n[[Category:1820s births]]\r\n[[Category:1850s deaths]]\r\n[[Category:19th-century American dancers]]\r\n[[Category:African-American male dancers]]\r\n[[Category:Blackface minstrel performers]]\r\n[[Category:Dancers from Rhode Island]]\r\n[[Category:People from Five Points, Manhattan]]\r\n[[Category:People from Providence, Rhode Island]]\r\n<!--The categories are either included by more detailed ones above, or not supported by the text (no mention of him being known as an actor or musician)\r\n[[Category:African-American male actors]]\r\n[[Category:American male actors]]\r\n[[Category:African-American male dancers]] -->"
    sameCatInComment = correct3
    assert (
        (_t := parser2.sorter.remove_cats(sameCatInComment, r"Test")),
        (sameCatInComment := _t[0]),
    )[0][1] == correct3 + "\r\n", r"Handle a cat that is also in a comment - comment block after"


def test_category_dupe_removal() -> None:
    S = W.for_site(EN)
    cats = "[[Category:One]]\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n", r"Duplicate category removed, no sortkey"
    cats = "[[Category:One]]\r\n[[Category:Two]]\r\n[[Category:One]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n", r"Duplicate categories removed, no sortkey"
    cats = "[[Category:One|A]]\r\n[[Category:Two]]\r\n[[Category:One|A]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|A]]\r\n[[Category:Two]]\r\n", r"Duplicate category removed, same sortkey"
    cats = "[[Category:One]] <!--comm-->\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]] <!--comm-->\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, first with comment"
    )
    cats = "[[Category:One|A]]\r\n[[Category:Two]]\r\n[[Category:One|B]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|A]]\r\n[[Category:Two]]\r\n[[Category:One|B]]\r\n", (
        r"Duplicate category NOT removed, conflicting sortkey"
    )
    cats = "[[Category:One]] <!--comm-->\r\n[[Category:Two]]\r\n[[Category:One]] <!--comm2-->"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]] <!--comm-->\r\n[[Category:Two]]\r\n[[Category:One]] <!--comm2-->\r\n", (
        r"Duplicate category NOT removed, conflicting comments"
    )
    cats = "[[Category:One|A]]\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|A]]\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, one without sortkey"
    )
    cats = "[[Category:One|A]]\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"A")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|A]]\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, one without sortkey"
    )
    cats = "[[Category:One|A]]\r\n[[Category:Two]]\r\n[[Category:One|a]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|A]]\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, same sortkey ignoring first letter case"
    )
    cats = "[[Category:One|foo]]\r\n[[Category:Two]]\r\n[[Category:One|foo]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|foo]]\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, lowercase sortkey"
    )
    cats = "[[Category:One|Foo]]\r\n[[Category:Two]]\r\n[[Category:One|Foo]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|Foo]]\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, uppercase sortkey"
    )
    cats = "[[Category:One|Foo Bar]]\r\n[[Category:Two]]\r\n[[Category:One|Foo]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One|Foo Bar]]\r\n[[Category:Two]]\r\n", (
        r"Duplicate category removed, one sortkey substring of another"
    )
    cats = "[[Category:One|Foo]]\r\n[[Category:Two]]\r\n[[Category:One|Foo Bar]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:Two]]\r\n[[Category:One|Foo Bar]]\r\n", (
        r"Duplicate category removed, one sortkey substring of another, longer second"
    )
    cats = "[[Category:One Foo]]\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One Foo]]\r\n[[Category:Two]]\r\n[[Category:One]]\r\n", (
        r"No change, cat substring rule only applies to sortkeys, longer first"
    )
    cats = "[[Category:One]]\r\n[[Category:Two]]\r\n[[Category:One Foo]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n[[Category:One Foo]]\r\n", (
        r"No change, cat substring rule only applies to sortkeys, longer second"
    )


def test_category_dupe_uncat_tag_removal() -> None:
    S = W.for_site(EN)
    cats = "[[Category:One]]\r\n{{uncat|date=August 2014}}\r\n{{uncat|date=August 2014}}\r\n"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n{{uncat|date=August 2014}}\r\n", r"Duplicate uncat tags removed"


def test_category_dupe_removal_wikis() -> None:
    S = W.for_site(EN)
    S = set_site(lang_code=r"en", project="species")
    cats = "[[Category:One]]\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n", r"Duplicate category removed, no sortkey"
    S = set_site(lang_code=r"en", project="commons")
    cats = "[[Category:One]]\r\n[[Category:Two]]\r\n[[Category:One]]"
    assert ((_t := parser2.sorter.remove_cats(cats, r"test")), (cats := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n", r"Duplicate category removed, no sortkey"
    S = set_site(lang_code=r"en", project="wikipedia")


def test_category_comment_tests() -> None:
    S = W.for_site(EN)
    cats = "[[Category:Hampshire|  ]]\r\n[[Category:Articles including recorded pronunciations (UK English)]]\r\n[[Category:Non-metropolitan counties]]"
    comm = r"<!-- cat -->"
    a = cats + "\r\n" + comm
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == comm + "\r\n" + cats + "\r\n"
    b = "Text\r\n[[Category:One]]\r\n\r\n==References==\r\n{{reflist}}\r\n[[Category:Two]]"
    assert ((_t := parser2.sorter.remove_cats(b, r"test")), (b := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n"
    assert b == "Text\r\n\r\n==References==\r\n{{reflist}}\r\n", (
        r"Blank newline before heading retained"
    )
    b = "A\r\n==Text==\r\n{{foo}}[[Category:One]]\r\n{| class=table |}\r\n\r\n==References==\r\n{{reflist}}\r\n[[Category:Two]]"
    assert ((_t := parser2.sorter.remove_cats(b, r"test")), (b := _t[0]))[0][
        1
    ] == "[[Category:One]]\r\n[[Category:Two]]\r\n"
    assert (
        b
        == "A\r\n==Text==\r\n{{foo}}\r\n{| class=table |}\r\n\r\n==References==\r\n{{reflist}}\r\n"
    ), r"Newline retained when category not on own line"


def test_category_redirects() -> None:
    S = W.for_site(EN)
    redirect = r"#REDIRECT [[Category:Foo]]"
    a = redirect
    assert len(((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][1]) == 0
    assert a == redirect, r"cats not pulled from redirect target"


def test_category_uncat_improve_cat() -> None:
    S = W.for_site(EN)
    a = "[[Category:Foo]]\r\n{{improve categories}}\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n{{improve categories}}\r\n"
    a = "{{improve categories}}\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n{{improve categories}}\r\n"
    a = "{{uncategorized}}\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n{{uncategorized}}\r\n"
    a = "{{multiple issues|{{uncategorized}}}}\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n{{uncategorized}}\r\n"
    assert a.strip() == r"", r"Clean up {{multiple issues}} after {{uncategorized}} move"
    a = "{{uncategorized}}\r\n== Section ==\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n", r"Don't pull uncat out of zeroth section"
    a = "A\r\n== Section ==\r\n{{improve categories}}\r\n== Section 2 ==\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n", r"Don't pull {{improve categories}} out of earlier section"
    a = "A\r\n== Section ==\r\n<!--{{improve categories}}-->\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n", r"Don't pull commented out template"
    a = "A\r\n== Section ==\r\n{{improve categories}}\r\n== Section 2 ==\r\n{{improve categories}}\r\n[[Category:Foo]]\r\n"
    assert ((_t := parser2.sorter.remove_cats(a, r"test")), (a := _t[0]))[0][
        1
    ] == "[[Category:Foo]]\r\n", r"Don't pull improve categories if in earlier and last section"


def test_remove_cats_key() -> None:
    S = W.for_site(EN)
    cats = "[[Category:1980 births]]\r\n[[Category:Local people]]"
    cats2 = "[[Category:1980 births|Jones, Andrew]]\r\n[[Category:Local people|Jones, Andrew]]"
    parser2.sorter.add_cat_key = True
    assert ((_t := parser2.sorter.remove_cats(cats, r"Andrew Jones")), (cats := _t[0]))[0][
        1
    ] == cats2 + "\r\n"
    parser2.sorter.add_cat_key = False
    at = "Text.\r\n\r\n== References ==\r\n{{reflist}}\r\n{{Uncategorized}}"
    assert ((_t := parser2.sorter.remove_cats(at, r"Andrew Jones")), (at := _t[0]))[0][
        1
    ] == r"{{Uncategorized}}" + "\r\n", r"uncat moved"
    assert not (S.Uncategorized.is_match(at))
    at = "Text.\r\n\r\n<!--{{Uncategorized}}-->\r\n== References ==\r\n{{reflist}}"
    assert (
        len(((_t := parser2.sorter.remove_cats(at, r"Andrew Jones")), (at := _t[0]))[0][1]) == 0
    ), r"commented out uncat not moved"
    at = "Text.\r\n\r\n== References ==\r\n{{reflist}}\r\n{{Uncategorized stub}}"
    assert ((_t := parser2.sorter.remove_cats(at, r"Andrew Jones")), (at := _t[0]))[0][
        1
    ] == r"{{Uncategorized stub}}" + "\r\n", r"uncat stub moved - redirect to uncat"
    at = "{{multiple issues|\r\n{{a}}\r\n{{Uncategorized}}\r\n{{b}}\r\n}}\r\n== References ==\r\n{{reflist}}"
    assert (
        "{{multiple issues|\r\n{{a}}\r\n{{Uncategorized}}\r\n{{b}}\r\n}}"
        in parser2.sort_meta_data(at, r"Andrew Jones")
    ), r"no blank line left in MI"


def test_remove_cats_sl_wiki_lifetime() -> None:
    S = W.for_site(EN)
    S = set_lang(r"sl")
    c = r"[[Category:Hampshire]]"
    l = r"{{Lifetime|1899|LIVING|Surname, Name}}"
    waffle = "waffle here\r\n"
    articleText = waffle + c + "\r\n" + l
    assert ((_t := parser2.sorter.remove_cats(articleText, r"test")), (articleText := _t[0]))[0][
        1
    ] == l + "\r\n" + c + "\r\n", r"lifetime treated like DEFAULTSORT on sl-wiki"
    S = set_lang(r"es")
    l = r"{{NF|1980||Nieto, Pablo}}"
    articleText = waffle + c + "\r\n" + l
    assert ((_t := parser2.sorter.remove_cats(articleText, r"test")), (articleText := _t[0]))[0][
        1
    ] == l + "\r\n" + c + "\r\n", r"NF treated like DEFAULTSORT on es-wiki"
    S = set_lang(r"en")
    articleText = waffle + c + "\r\n" + l
    assert ((_t := parser2.sorter.remove_cats(articleText, r"test")), (articleText := _t[0]))[0][
        1
    ] == c + "\r\n", r"lifetime/NF is just another template on en-wiki"


def test_default_sort_and_comment_tests() -> None:
    S = W.for_site(EN)
    a = r"Foo"
    b = r"[[Category:Predecessors of the Alton Railroad]]"
    c = r"{{DEFAULTSORT:Joliet Chicago  Railroad}}"
    e = r"<!--{{DEFAULTSORT:Joliet Chicago  Railroad}}-->"
    d = a + "\r\n" + b + "\r\n" + c
    f = a + "\r\n" + b + "\r\n" + e
    g = c + "\r\n" + r"{{DEFAULTSORT:Joliet Chicago  Railroad 2nd different}}"
    assert ((_t := parser2.sorter.remove_cats(d, r"test")), (d := _t[0]))[0][
        1
    ] == c + "\r\n" + b + "\r\n", r"standard case, return defaultsort then category"
    assert ((_t := parser2.sorter.remove_cats(f, r"test")), (f := _t[0]))[0][1] == b + "\r\n", (
        r"Don't return commented out defaultsort"
    )
    assert len(((_t := parser2.sorter.remove_cats(g, r"test")), (g := _t[0]))[0][1]) == 0, (
        r"does not modify page with multiple defaultsorts"
    )
    d = a + "\r\n" + b + "\r\n" + c + r" <!--foo -->"
    assert ((_t := parser2.sorter.remove_cats(d, r"test")), (d := _t[0]))[0][
        1
    ] == c + " <!--foo -->\r\n" + b + "\r\n", r"Retain comment on same line as defaultsort"
    g = c + "\r\n" + c
    assert ((_t := parser2.sorter.remove_cats(g, r"test")), (g := _t[0]))[0][1] == c + "\r\n", (
        r"Exact dupe DEFAULTSORT removed"
    )


def test_inter_wiki_tests() -> None:
    S = W.for_site(EN)
    parser2.sort_interwikis = False
    parser2.sorter.possible_interwikis = [
        r"de",
        r"es",
        r"fr",
        r"it",
        r"sv",
        r"ar",
        r"bs",
        r"br",
        r"en",
        r"jbo",
    ]
    a = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
    b = a
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", r"no changes"
    comm = r"<!-- other languages -->"
    a = (
        "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
        + comm
    )
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == comm + "\r\n" + b + "\r\n"
    comm = r"<!--Interwikis-->"
    a = (
        "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
        + comm
    )
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == comm + "\r\n" + b + "\r\n"
    comm = r"<!--Other wikis-->"
    a = (
        "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
        + comm
    )
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == comm + "\r\n" + b + "\r\n"
    comm = r"<!-- interwiki links to this article in other languages, below -->"
    a = (
        "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
        + comm
    )
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == comm + "\r\n" + b + "\r\n"
    c = "{{Canadianmetros}}\r\n\r\n<!--\r\nThe following links are here to prevent the interwiki bot from adding them to the list above.  The links below point to disambiguation pages and not to a translated article about Canadian National Railway.\r\n[[it:CN]]\r\n[[sv:CN]]\r\n-->"
    assert len(((_t := parser2.sorter.interwikis(c)), (c := _t[0]))[0][1]) == 0, (
        r"interwikis not taken out of wiki comments"
    )
    c2 = c + r"[[sv:CN]]"
    assert ((_t := parser2.sorter.interwikis(c2)), (c2 := _t[0]))[0][1] == r"[[sv:CN]]" + "\r\n", (
        r"interwiki returned even if the same one exists commented out elsewhere"
    )
    c = "{{Canadianmetros}}\r\n\r\n<!--\r\nThe following links are here to prevent the interwiki bot from adding them to the list above.  The links below point to disambiguation pages and not to a translated article about Canadian National Railway.\r\n[[it:CN]]\r\n[[sv:CN]]\r\n-->\r\nsecond comment <!-- [[it:CN]] -->"
    assert len(((_t := parser2.sorter.interwikis(c)), (c := _t[0]))[0][1]) == 0, (
        r"interwikis not taken out of wiki comments"
    )
    d = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
    assert ((_t := parser2.sorter.interwikis(d)), (d := _t[0]))[0][1] == b + "\r\n"
    e1 = "{{DEFAULTSORT:Boleyn, Anne}}\r\n\r\n"
    e2 = "{{Link FA|bs}}\r\n{{Link FA|no}}\r\n{{Link FA|sv}}\r\n[[ar:آن بولين]]\r\n[[bs:Anne Boleyn]]\r\n[[br:Anne Boleyn]]"
    f = e2
    g = e1 + e2
    assert ((_t := parser2.sorter.interwikis(g)), (g := _t[0]))[0][1] == f + "\r\n"
    h = "[[de:Canadian National Railway]]\r\n[[en:Canadian National]]\r\n[[fr:Canadien National]]"
    assert ((_t := parser2.sorter.interwikis(h)), (h := _t[0]))[0][
        1
    ] == "[[de:Canadian National Railway]]\r\n[[fr:Canadien National]]" + "\r\n", (
        r"interwikis to own wiki are removed"
    )
    a = "[[de:Canadian National Railway]]\r\n[[es::Canadian National]]\r\n[[fr:Canadien National]]"
    b = a.replace(r"::", r":")
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"double colon in interwiki removed"
    )
    a = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[es:canadian National]]\r\n[[fr:Canadien National]]"
    b = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"duplicate interwiki removed, variation in first letter casing only"
    )
    a = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[es:Canadian National]]<!-- comm-->\r\n[[fr:Canadien National]]"
    b = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"duplicate interwiki removed, inline comment second"
    )
    a = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]<!-- comm-->\r\n[[es:Canadian National]]\r\n[[fr:Canadien National]]"
    b = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]]<!-- comm-->\r\n[[fr:Canadien National]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"duplicate interwiki removed, inline comment first"
    )
    a = "[[de:Canadian National Railway]]\r\n[[jbo:canadian National]]\r\n[[fr:Canadien National]]"
    assert (
        ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1]
        == "[[de:Canadian National Railway]]\r\n[[jbo:canadian National]]\r\n[[fr:Canadien National]]\r\n"
    ), r"first letter casing retained for jbo-wiki links"
    i = "{{Canadianmetros|\r\n[[it:CN]]\r\n[[sv:CN]]\r\n}}"
    assert len(((_t := parser2.sorter.interwikis(i)), (i := _t[0]))[0][1]) == 0, (
        r"interwikis not taken out of templates"
    )


def test_inter_wiki_tests_multiple() -> None:
    S = W.for_site(EN)
    parser2.sort_interwikis = False
    parser2.sorter.possible_interwikis = [
        r"de",
        r"es",
        r"fr",
        r"it",
        r"sv",
        r"ar",
        r"bs",
        r"br",
        r"en",
    ]
    a = "[[de:Canadian National Railway]]\r\n[[fr:Canadian National (foo)]]\r\n[[fr:Canadien National]]"
    b = a
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n"
    a = "[[fr:Sénatus-consultes sous Napoléon III]]\r\n[[fr:Sénatus-consulte]]"
    b = a
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n"


def test_interwiki_sorting() -> None:
    S = W.for_site(EN)
    parser2.sort_interwikis = True
    parser2.sorter.possible_interwikis = [r"ar", r"de", r"en", r"ru", r"sq"]
    a = "[[sq:Foo]]\r\n[[ru:Bar]]"
    b = "[[ru:Bar]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"reorder if neccessary"
    )
    a = "[[ru:Bar]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"no change Diff everything is sorted"
    )
    parser2.inter_wiki_order = genfixes.InterWikiOrderEnum.ALPHABETICAL
    a = "[[ru:Bar]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"alphabetical order"
    )
    parser2.inter_wiki_order = genfixes.InterWikiOrderEnum.LOCAL_LANGUAGE_FIRST_WORD
    a = "[[ru:Bar]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"local language"
    )
    parser2.inter_wiki_order = genfixes.InterWikiOrderEnum.ALPHABETICAL_EN_FIRST
    a = "[[ru:Bar]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"alphabetical order with en firsth"
    )
    S = set_lang(r"de")
    parser2.inter_wiki_order = genfixes.InterWikiOrderEnum.ALPHABETICAL_EN_FIRST
    a = "[[ar:Bar]]\r\n[[en:Hello]]\r\n[[sq:Foo]]"
    b = "[[en:Hello]]\r\n[[ar:Bar]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n"
    parser2.inter_wiki_order = genfixes.InterWikiOrderEnum.ALPHABETICAL
    a = "[[ar:Bar]]\r\n[[en:Hello]]\r\n[[sq:Foo]]"
    b = "[[ar:Bar]]\r\n[[en:Hello]]\r\n[[sq:Foo]]"
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n"
    S = set_lang(r"en")
    parser2.sort_interwikis = False


def test_inter_wiki_tests_inline_comments() -> None:
    S = W.for_site(EN)
    parser2.sort_interwikis = False
    parser2.sorter.possible_interwikis = [
        r"de",
        r"es",
        r"fr",
        r"it",
        r"sv",
        r"ar",
        r"bs",
        r"br",
        r"en",
    ]
    a = "[[de:Canadian National Railway]]\r\n[[es:Canadian National]] <!--comm-->\r\n[[fr:Canadien National]] <!--comm2 -->"
    b = a
    assert ((_t := parser2.sorter.interwikis(a)), (a := _t[0]))[0][1] == b + "\r\n", (
        r"inline comment kept with interwiki"
    )


def test_self_interwikis_en() -> None:
    S = W.for_site(EN)
    assert len(parser2.sort_meta_data(r"<!-- [[en:Foo]]-->", r"Test")) == 0, (
        r"Commented out en interwikis removed"
    )
    EnInterwiki = r"[[en:Foo]]"
    S = set_site(lang_code=r"en", project="commons")
    assert parser2.sort_meta_data(EnInterwiki, r"Test") == "\r\n\r\n" + EnInterwiki, (
        r"en interwiki not removed on commons"
    )
    S = set_site(lang_code=r"en", project="species")
    assert parser2.sort_meta_data(EnInterwiki, r"Test") == "\r\n\r\n" + EnInterwiki, (
        r"en interwiki not removed on species"
    )
    S = set_site(lang_code=r"en", project="wikipedia")
    assert len(parser2.sort_meta_data(EnInterwiki, r"Test")) == 0, (
        r"en interwiki removed on en-wiki"
    )


def test_sorter_namespace_tests() -> None:
    S = W.for_site(EN)
    cat = r"[[Category:Foo]]"
    assert parser2.sort_meta_data(cat, r"Category:Bar") == cat, r"Full trim on category namespace"
    assert parser2.sort_meta_data(cat, r"Template:Bar") == cat, r"no sorting on template namespace"
    assert parser2.sort_meta_data(cat, r"Module:Bar") == cat, r"no sorting on Module namespace"
    assert parser2.sort_meta_data(cat, r"Bar") == "\r\n\r\n" + cat, r"sorting applied on mainspace"
    CatPopStub = "Text\r\n{{popstub}}\r\nText"
    assert parser2.sort_meta_data(CatPopStub, r"Category:Foo") == CatPopStub, (
        r"no stub sorting on Category namespace"
    )


def test_no_include_include_only_tests() -> None:
    S = W.for_site(EN)
    a = r"<noinclude>"
    b = "[[ar:قالب:بذرة موسيقي]]\r\n[[bg:Шаблон:Музика-мъниче]]\r\n[[ca:Plantilla:Esborrany de música]]\r\n[[cs:Šablona:Hudební pahýl]]\r\n[[cs:Šablona:Hudební pahýl]]\r\n[[vi:Tiêu bản:Music-stub]]"
    c = r"</noinclude>"
    assert parser2.sort_meta_data(a + b + c, r"foo") == a + b + c
    assert parser2.sort_meta_data(b, r"foo") != b
    d = r"[[Category:Foo]]"
    e = r"[[Category:More foo]]"
    f = r"<includeonly>blah[[Category:Foo]]</includeonly>"
    assert parser2.sort_meta_data(a + d + c + e, r"foo") == a + d + c + e
    assert parser2.sort_meta_data(d + e, r"foo") != d + "\r\n" + e
    assert parser2.sort_meta_data(f + d, r"foo") == f + d
    magicWord = "__FORCETOC__\r\n\r\n[[Category:Foo]]"
    assert parser2.sort_meta_data(magicWord, r"foo") == magicWord, r"magic word above cats"
    magicWord = "[[Category:Foo]]\r\n__FORCETOC__"
    assert parser2.sort_meta_data(magicWord, r"foo") == magicWord, r"magic word below cats"


def test_sort_other_languages() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ru")
    parser2.sorter.possible_interwikis = [r"en", r"zh"]
    parser2.sorter.sort_interwikis = False
    before = "== Литература ==\r\n* Taylor, Peter. (1989).\r\n{{ref-en}}\r\n\r\n[[Category:Флора Африки]]\r\n[[Category:Хищные растения]]\r\n[[Category:Эндемики Африки]]\r\n[[Category:Пузырчатковые]]\r\n[[Category:Таксоны растений, названные в честь людей]]\r\n\r\n{{botanics-stub}}\r\n\r\n[[en:Utricularia pobeguinii]]\r\n[[zh:波贝甘狸藻]]"
    after = "== Литература ==\r\n* Taylor, Peter. (1989).\r\n{{ref-en}}\r\n\r\n{{botanics-stub}}\r\n\r\n[[Category:Флора Африки]]\r\n[[Category:Хищные растения]]\r\n[[Category:Эндемики Африки]]\r\n[[Category:Пузырчатковые]]\r\n[[Category:Таксоны растений, названные в честь людей]]\r\n\r\n[[en:Utricularia pobeguinii]]\r\n[[zh:波贝甘狸藻]]"
    assert parser2.sort_meta_data(before, r"a") == after, (
        r"Even if RemoveStubs not run on ru-wiki, no excess whitespace left from meta data sorting"
    )
    S = set_lang(r"uk")
    beforeUK = "Andy\r\n{{botanist-stub}}\r\n[[Category:ABC]]"
    afterUK = "Andy\r\n\r\n\r\n{{botanist-stub}}\r\n\r\n[[Category:ABC]]"
    assert parser2.sort_meta_data(beforeUK, r"a") == afterUK, (
        r"uk sort order: stubs NOT below categories"
    )
    S = set_lang(r"uk")
    beforeDK = "Andy\r\n{{botanist-dk-stub}}\r\n[[Category:ABC]]"
    afterDK = "Andy\r\n\r\n\r\n{{botanist-dk-stub}}\r\n\r\n[[Category:ABC]]"
    assert parser2.sort_meta_data(beforeDK, r"a") == afterDK, (
        r"dk sort order: stubs NOT below categories"
    )
    S = set_lang(r"sl")
    beforeSl = "Andy\r\n{{botanist-stub}}\r\n{{Persondata}}\r\n[[Category:ABC]]"
    afterSl = "Andy\r\n\r\n{{botanist-stub}}\r\n\r\n[[Category:ABC]]\r\n\r\n{{Persondata}}"
    assert parser2.sort_meta_data(beforeSl, r"a") == afterSl, r"Sl sort order"
    S = set_lang(r"de")
    beforeDe = "Andy\r\n{{botanist-stub}}\r\n{{Personendaten}}\r\n[[Category:ABC]]\r\n[[en:Test]]"
    afterDe = "Andy\r\n\r\n\r\n{{botanist-stub}}\r\n\r\n[[Category:ABC]]\r\n\r\n{{Personendaten}}\r\n\r\n[[en:Test]]"
    assert parser2.sort_meta_data(beforeDe, r"a") == afterDe, r"De sort order"
    S = set_lang(r"it")
    beforeIt = "{{S|foo}}\r\n\r\nAndy\r\n{{Persondata}}\r\n[[Category:ABC]]\r\n[[en:Test]]"
    afterIt = "{{S|foo}}\r\n\r\nAndy\r\n\r\n{{Persondata}}\r\n[[Category:ABC]]\r\n\r\n[[en:Test]]"
    assert parser2.sort_meta_data(beforeIt, r"a") == afterIt, r"It sort order"
    S = set_site(lang_code=r"it", project="wikiquote")
    afterIt2 = "{{S|foo}}\r\n\r\nAndy\r\n\r\n{{Persondata}}\r\n[[Category:ABC]]\r\n\r\n[[en:Test]]"
    assert parser2.sort_meta_data(beforeIt, r"a") == afterIt2, r"It wikiquote sort order"
    S = set_site(lang_code=r"en", project="wikipedia")


def test_commented_references() -> None:
    S = W.for_site(EN)
    CommentedRef = "'''George May''' (3 May 1876 - 1955) was.\r\n\r\n<!--\r\n==References==\r\n<references />\r\n-->\r\n\r\n==External links==\r\n* {{CanParlbio|ID=6}}\r\n\r\n{{Persondata <!-- Metadata: see [[Wikipedia:Persondata]]. -->\r\n| NAME              =May, George\r\n| ALTERNATIVE NAMES =\r\n| SHORT DESCRIPTION = politician\r\n| DATE OF BIRTH     =3 May 1876\r\n| PLACE OF BIRTH    =Ontario\r\n| DATE OF DEATH     = 1955\r\n| PLACE OF DEATH    =\r\n}}\r\n{{DEFAULTSORT:Macleod, George}}\r\n[[Category:1876 births]]\r\n[[Category:1955 deaths]]"
    assert parser2.sort_meta_data(CommentedRef, r"George May") == CommentedRef


def test_short_pages_monitor() -> None:
    S = W.for_site(EN)
    A = "'''Seyyed Ahmadi''' ({{lang-fa|سيداحمدي\u200e}}) may refer to:\r\n* [[Seyyed Ahmadi, Fars]]\r\n* [[Seyyed Ahmadi, Hormozgan]]\r\n\r\n{{geodis}}\r\n\r\n{{Short pages monitor}}<!-- This long comment was added to the page to prevent it from being listed on Special:Shortpages. It and the accompanying monitoring template were generated via Template:Long comment. Please do not remove the monitor template without removing the comment as well.-->"
    assert parser2.sort_meta_data(A, r"Test") == A, (
        r"{{Short pages monitor}} kept at end of article text: template before"
    )
    B = "'''Seyyed Ahmadi''' ({{lang-fa|سيداحمدي\u200e}}) may refer to:\r\n* [[Seyyed Ahmadi, Fars]]\r\n* [[Seyyed Ahmadi, Hormozgan]]\r\n\r\n[[de:Foo]]\r\n\r\n{{Short pages monitor}}<!-- This long comment -->"
    assert parser2.sort_meta_data(B, r"Test") == B, (
        r"{{Short pages monitor}} kept at end of article text: interwiki before"
    )
    B = B.replace("\r\n{{Short page", r"{{Short page")
    assert parser2.sort_meta_data(B, r"Test") == B, r"Number of newlines before spm preserved"
    assert parser2.sort_meta_data(B.replace(r"-->", "-->\r\n"), r"Test") == B, (
        r"Page trim still done when spm present"
    )


def test_redirects_dablinks() -> None:
    S = W.for_site(EN)
    x = "#REDIRECT [[Foo]]\r\n\r\n{{distinguish|A}}"
    assert parser2.sort_meta_data(x, r"Test") == x, (
        r"No sorting of zeroth section templates for redirects"
    )
