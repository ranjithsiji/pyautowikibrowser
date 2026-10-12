"""Port of AWB UnitTests/FootnotesTests.cs: <ref> fixes (awb_l.core.parsers.references).

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from awb_l.core import genfixes, namespace, rx, tools
from awb_l.core import wikiregexes as W
from awb_l.core.dotnet_regex import DotNetOptions as O
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.parsers.parsers import DateLocale
from awb_l.core.rx import DotNetRegex
from awb_l.core.site import Namespace, SiteConfig, current_site
from tests.parity import regex_assert
from tests.parity.genfixes_base import genFixes
from tests.parity.helpers import (
    EN,
    cs_len,
    set_lang,
    set_project,
    set_site,
    unit_test,
    utc_month_year,
)
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_test_tag_boundaries() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.simplify_reference_tags(r'<ref name="foo"><br></ref>')
        == r'<ref name="foo"><br></ref>'
    )


def test_test_simplify_reference_tags() -> None:
    S = W.for_site(EN)
    assert genfixes.simplify_reference_tags(r'<ref name= "foo"></ref>') == r'<ref name= "foo" />'
    assert genfixes.simplify_reference_tags(r'<ref name = "foo"></ref>') == r'<ref name = "foo" />'
    assert genfixes.simplify_reference_tags(r'<ref name="foo" >< / ref >') == r'<ref name="foo" />'
    assert genfixes.simplify_reference_tags(r'<ref name="foo" ></ref>') == r'<ref name="foo" />'
    assert (
        genfixes.simplify_reference_tags(r'<ref name="foo bar" ></ref>')
        == r'<ref name="foo bar" />'
    )
    assert (
        genfixes.simplify_reference_tags(r"<ref name='foo bar' >    </ref>")
        == r"<ref name='foo bar' />"
    )
    assert genfixes.simplify_reference_tags(r'<refname="foo"></ref>') == r'<refname="foo"></ref>'
    assert (
        genfixes.simplify_reference_tags(r"<ref name='aftermath'> </ref>")
        == r"<ref name='aftermath' />"
    )
    assert (
        genfixes.simplify_reference_tags(r"<ref name='aftermath' /> </ref>")
        == r"<ref name='aftermath' />"
    )


def test_test_fix_reference_list_tags() -> None:
    S = W.for_site(EN)
    assert genfixes.fix_reference_list_tags(r"<references/>") == r"<references/>"
    assert (
        genfixes.fix_reference_list_tags(r"<div><references/></div>") == r"<div><references/></div>"
    )
    assert (
        genfixes.fix_reference_list_tags(r"<references>foo</references>")
        == r"<references>foo</references>"
    )
    assert (
        genfixes.fix_reference_list_tags('<div class="references-small"><references/>\r\n</div>')
        == r"{{Reflist}}"
    )
    assert (
        genfixes.fix_reference_list_tags(r'<div class="references-2column"><references/></div>')
        == r"{{Reflist|2}}"
    )
    assert (
        genfixes.fix_reference_list_tags(
            '<div class="references-2column"><div class="references-small">\r\n<references/></div></div>'
        )
        == r"{{Reflist|2}}"
    )
    assert (
        genfixes.fix_reference_list_tags(
            '<div class="references-small"><div class="references-2column"> <references/>\r\n</div></div>'
        )
        == r"{{Reflist|2}}"
    )
    assert r"{{Reflist" not in genfixes.fix_reference_list_tags(
        '<div class="references-small"><div class="references-2column">\r\n<references/></div>* some other ref</div>'
    )
    assert r"{{Reflist" not in genfixes.fix_reference_list_tags(
        '<div class="references-small"><div class="references-2column">\r\n<references/></div>'
    )
    assert (
        genfixes.fix_reference_list_tags(
            '<div class="references-small" style="-moz-column-count:2; column-count:2;">\r\n<references/>\r\n</div>'
        )
        == r"{{Reflist|2}}"
    ), r"Converts to reflist|2 when column-count:2"
    assert genfixes.fix_reference_list_tags(r"<small><references/></small>") == r"{{Reflist}}"
    assert genfixes.fix_reference_list_tags(r"<small><references /></small>") == r"{{Reflist}}"
    S = set_lang(r"sv")
    assert (
        genfixes.fix_reference_list_tags('<div class="references-small"><references/>\r\n</div>')
        == r"<references/>"
    )
    S = set_lang(r"en")
    assert (
        genfixes.fix_reference_list_tags('<div class="references-small"><references/>\r\n</div>')
        == r"{{Reflist}}"
    )


def test_test_fix_reference_tags() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.fix_reference_tags(r"now < ref>[http://www.site.com a site]</ref> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"leading"
    assert (
        genfixes.fix_reference_tags(r"now < ref   >[http://www.site.com a site]</ref> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"both sides"
    assert (
        genfixes.fix_reference_tags(r"now <ref >[http://www.site.com a site]</ref> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"trailing"
    assert (
        genfixes.fix_reference_tags(r"now < ref>[http://www.site.com a site]< /ref> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"leading in borth opening and closing tag"
    assert (
        genfixes.fix_reference_tags(r"now <ref>[http://www.site.com a site]</ ref> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"in closing tag"
    assert (
        genfixes.fix_reference_tags(r"now <ref>[http://www.site.com a site]</ref > was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"in closing tag"
    assert (
        genfixes.fix_reference_tags(r"now <    ref  >[http://www.site.com a site]< / ref > was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    ), r"everywhere"
    assert (
        genfixes.fix_reference_tags(r"now <ref name=foo bar>and") == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name=foo bar /> and")
        == r'now <ref name="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name = foo bar >and")
        == r'now <ref name = "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name=foo/bar>and") == r'now <ref name="foo/bar">and'
    ), r"Use of slash needs quotes"
    assert (
        genfixes.fix_reference_tags(r"now <ref name=foo/bar />") == r'now <ref name="foo/bar" />'
    ), r"Use of slash needs quotes, short ref"
    assert (
        genfixes.fix_reference_tags(r"now<ref name=a.com/2014/11/1744>")
        == r'now<ref name="a.com/2014/11/1744">'
    ), r"Use of multiple slashes needs quotes"
    assert (
        genfixes.fix_reference_tags(r"now<ref name=a.com/2014/11/1744 />")
        == r'now<ref name="a.com/2014/11/1744" />'
    ), r"Use of multiple slashes needs quotes"
    nochange = "<ref name=VulgarisAerae1\r\n/>"
    assert genfixes.fix_reference_tags(nochange) == nochange
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar"">and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar"" >and')
        == r'now <ref name="foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=foo bar"">and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=""foo bar"">and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name""foo bar">and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar".>and')
        == r'now <ref name="foo bar">and'
    ), r"Excess . after ref name"
    assert (
        genfixes.fix_reference_tags('now <ref name="foo bar"\'>and')
        == r'now <ref name="foo bar">and'
    ), r"Excess ' after ref name"
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar"=>and')
        == r'now <ref name="foo bar">and'
    ), r"Excess = after ref name"
    assert (
        genfixes.fix_reference_tags(r'now <ref name"foo bar"=>and')
        == r'now <ref name="foo bar">and'
    ), r"= after ref name not before"
    assert genfixes.fix_reference_tags(r"now <ref name=foo=>and") == r"now <ref name=foo>and", (
        r"Excess = after ref name, no quotes"
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=""foo "bar" x">and')
        == r'now <ref name="foo bar x">and'
    ), r"Excess internal quotes removed"
    assert (
        genfixes.fix_reference_tags(r'now <ref name=""foo "bar" x" /> and')
        == r'now <ref name="foo bar x" /> and'
    ), r"Excess internal quotes removed, short ref"
    grouped = r'<ref name="Foo" group="A" />'
    assert genfixes.fix_reference_tags(grouped) == grouped, r"No change to valid group ref"
    grouped2 = r'<ref name="Foo" group=A>test</ref>'
    assert genfixes.fix_reference_tags(grouped2) == grouped2, r"No change to valid group ref"
    grouped3 = r'<ref name="Foo" group="A">test</ref>'
    assert genfixes.fix_reference_tags(grouped3) == grouped3, (
        r"No change to valid group ref, quotes"
    )
    grouped4 = r'<ref name="Foo/Bar" group="A">test</ref>'
    assert genfixes.fix_reference_tags(grouped4) == grouped4, r"No change to valid group ref, slash"
    details1 = r'<ref name="Fred" details="p. 1">test</ref>'
    assert genfixes.fix_reference_tags(details1) == details1, r"No change to valid details ref"
    details2 = r'<ref name="Fred" group="A" details="p. 1">test</ref>'
    assert genfixes.fix_reference_tags(details2) == details2, r"No change to valid details ref"
    details3 = r'<ref name="Fred" details="p. 1" group="A">test</ref>'
    assert genfixes.fix_reference_tags(details3) == details3, r"No change to valid details ref"
    details4 = r'<ref group="A" details="p. 1">test</ref>'
    assert genfixes.fix_reference_tags(details4) == details4, r"No change to valid details ref"
    nochange = r'now <ref name="foo bar">and'
    assert genfixes.fix_reference_tags(nochange) == nochange
    nochange = r"now <ref name=foo/   > and"
    assert genfixes.fix_reference_tags(nochange) == nochange
    nochange = r"now <ref name=foo / > and"
    assert genfixes.fix_reference_tags(nochange) == nochange
    assert (
        genfixes.fix_reference_tags(r"now<ref name=WWOS/ref>Foo</ref>")
        == r'now<ref name="WWOS/ref">Foo</ref>'
    )
    assert genfixes.fix_reference_tags(r"now<ref name=WWOS/ref />") == r'now<ref name="WWOS/ref" />'
    assert (
        genfixes.fix_reference_tags(r'now <ref name=""foo bar">and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=""foo bar>and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=""foo bar" >and')
        == r'now <ref name="foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=“"foo bar" >and')
        == r'now <ref name="foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name=foo bar">and') == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name foo bar">and')
        == r'now <ref name ="foo bar">and'
    ), r"missing = and first quotes"
    assert (
        genfixes.fix_reference_tags(r'now <ref name=foo bar" /> and')
        == r'now <ref name="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name = foo bar" >and')
        == r'now <ref name = "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar>and') == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar /> and')
        == r'now <ref name="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name = "foo bar >and')
        == r'now <ref name = "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name=''foo bar'>and")
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name='foo bar'' /> and")
        == r'now <ref name="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name = ''foo bar'' >and")
        == r'now <ref name = "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name "foo bar">and')
        == r'now <ref name ="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name "foo bar" /> and')
        == r'now <ref name ="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name -"foo bar">and')
        == r'now <ref name ="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name -"foo bar" /> and')
        == r'now <ref name ="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name -  "foo bar" >and')
        == r'now <ref name =  "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name +"foo bar">and')
        == r'now <ref name ="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name +"foo bar" /> and')
        == r'now <ref name ="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name +  "foo bar" >and')
        == r'now <ref name =  "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name +"foo bar>and')
        == r'now <ref name ="foo bar">and'
    ), r"Plus and missing ending quote"
    assert (
        genfixes.fix_reference_tags(r'now <ref name +foo bar">and')
        == r'now <ref name ="foo bar">and'
    ), r"Plus and missing opening quote"
    assert genfixes.fix_reference_tags(r'now <ref "foo bar">and') == r'now <ref name="foo bar">and'
    assert (
        genfixes.fix_reference_tags(r'now <ref "foo bar" /> and')
        == r'now <ref name="foo bar" /> and'
    )
    assert genfixes.fix_reference_tags(r'now <ref ="foo bar">and') == r'now <ref name="foo bar">and'
    assert (
        genfixes.fix_reference_tags(r'now <ref name="Fred" /ref>was')
        == r'now <ref name="Fred"/>was'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="Fred A" /ref>was')
        == r'now <ref name="Fred A"/>was'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="Fred A" / /> was')
        == r'now <ref name="Fred A"/> was'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="Fred A" //> was')
        == r'now <ref name="Fred A"/> was'
    )
    assert genfixes.fix_reference_tags(r"now <ref name=Fred //> was") == r"now <ref name=Fred/> was"
    assert genfixes.fix_reference_tags(r'now <ref name="Fred"?>was') == r'now <ref name="Fred"?>was'
    assert (
        genfixes.fix_reference_tags(r"now <ref>[http://www.site.com a site]<ref/> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref>[http://www.site.com a site]<ref/> was")
        == r"now <ref>[http://www.site.com a site]</ref> was"
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref>[http://www.site.com a site]</red>was")
        == r"now <ref>[http://www.site.com a site]</ref>was"
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref>[http://www.site.com a site]</red>was")
        == r"now <ref>[http://www.site.com a site]</ref>was"
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar">and')
        == r'now <ref name="foo bar">and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name="foo bar" /> and')
        == r'now <ref name="foo bar" /> and'
    )
    assert (
        genfixes.fix_reference_tags(r'now <ref name = "foo bar" >and')
        == r'now <ref name = "foo bar" >and'
    )
    assert (
        genfixes.fix_reference_tags(r"now <ref name = 'foo bar' >and")
        == r"now <ref name = 'foo bar' >and"
    )
    assert genfixes.fix_reference_tags(r"now <ref>Smith 2004</ref>") == r"now <ref>Smith 2004</ref>"
    assert genfixes.fix_reference_tags(r"now <Ref>Smith 2004</ref>") == r"now <ref>Smith 2004</ref>"
    assert genfixes.fix_reference_tags(r"now <REF>Smith 2004</REF>") == r"now <ref>Smith 2004</ref>"
    assert genfixes.fix_reference_tags(r"now <reF>Smith 2004</ref>") == r"now <ref>Smith 2004</ref>"
    assert (
        genfixes.fix_reference_tags(r"now <reF name=S1>Smith 2004</ref>")
        == r"now <ref name=S1>Smith 2004</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r"now <REF> Smith 2004 </REF>") == r"now <ref>Smith 2004</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r"<ref>foo</ref> <ref>foo2</ref>")
        == r"<ref>foo</ref><ref>foo2</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r"<ref>foo</ref>     <ref>foo2</ref>")
        == r"<ref>foo</ref><ref>foo2</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r"<ref>foo</ref> <ref name=Bert />")
        == r"<ref>foo</ref><ref name=Bert />"
    )
    assert (
        genfixes.fix_reference_tags(r"<ref>foo</ref> <ref name=Bert>Bert2</ref>")
        == r"<ref>foo</ref><ref name=Bert>Bert2</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r"<REF>foo</REF> <REF>foo2</REF>")
        == r"<ref>foo</ref><ref>foo2</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r'<ref name="Tim"/> <ref>foo2</ref>')
        == r'<ref name="Tim"/><ref>foo2</ref>'
    )
    assert (
        genfixes.fix_reference_tags(r"<ref name=Tim/>     <ref>foo2</ref>")
        == r"<ref name=Tim/><ref>foo2</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r"<ref name=Tim/> <ref name=Bert />")
        == r"<ref name=Tim/><ref name=Bert />"
    )
    assert (
        genfixes.fix_reference_tags(r"<ref name=Tim/> <ref name=Bert>Bert2</ref>")
        == r"<ref name=Tim/><ref name=Bert>Bert2</ref>"
    )
    assert (
        genfixes.fix_reference_tags(r'<ref name="Tim"><ref>foo2</ref>')
        == r'<ref name="Tim"><ref>foo2</ref>'
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly,<ref>Smith 2004</ref>he was")
        == r"Now clearly,<ref>Smith 2004</ref> he was"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly,<ref>Smith 2004</ref>2 were")
        == r"Now clearly,<ref>Smith 2004</ref> 2 were"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly,<ref name=Smith/>2 were")
        == r"Now clearly,<ref name=Smith/> 2 were"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly, <ref>Smith 2004</ref> he was")
        == r"Now clearly,<ref>Smith 2004</ref> he was"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly: <ref>Smith 2004</ref> he was")
        == r"Now clearly:<ref>Smith 2004</ref> he was"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly; <ref>Smith 2004</ref> he was")
        == r"Now clearly;<ref>Smith 2004</ref> he was"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly.   <ref name=Smith/> 2 were")
        == r"Now clearly.<ref name=Smith/> 2 were"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly. <ref name=Smith/> 2 were")
        == r"Now clearly.<ref name=Smith/> 2 were"
    )
    assert (
        genfixes.fix_reference_tags(r"Now clearly. <Ref name=Smith/> 2 were")
        == r"Now clearly.<ref name=Smith/> 2 were"
    )
    assert genfixes.fix_reference_tags(r"<ref>foo </ref>") == r"<ref>foo</ref>"
    assert genfixes.fix_reference_tags(r"<ref>foo    </ref>") == r"<ref>foo</ref>"
    assert genfixes.fix_reference_tags("<ref>foo\r\n</ref>") == "<ref>foo\r\n</ref>"
    assert genfixes.fix_reference_tags(r"<ref>  foo </ref>") == r"<ref>foo</ref>"
    assert genfixes.fix_reference_tags(r"<REF>  foo </REF>") == r"<ref>foo</ref>"
    assert len(genfixes.fix_reference_tags(r"<ref> </ref>")) == 0
    assert len(genfixes.fix_reference_tags(r"<ref><ref> </ref></ref>")) == 0
    assert genfixes.fix_reference_tags(r'<ref name="Fred" Smith />') == r'<ref name="Fred Smith" />'
    assert (
        genfixes.fix_reference_tags(r'<ref name = "Fred" Smith />')
        == r'<ref name = "Fred Smith" />'
    )
    assert genfixes.fix_reference_tags(r'<ref name="Fred"-Smith />') == r'<ref name="Fred-Smith" />'
    assert genfixes.fix_reference_tags(r'<ref name="Fred"-Smith/>') == r'<ref name="Fred-Smith"/>'
    assert (
        genfixes.fix_reference_tags(r'<ref name="Fred"-Smith >text</ref>')
        == r'<ref name="Fred-Smith" >text</ref>'
    )
    assert genfixes.fix_reference_tags(r'<ref name-"Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'<ref name+"Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'<ref name:"Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'<ref name=="Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'<ref name= ="Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'<ref name-"Fred">') == r'<ref name="Fred">'
    assert genfixes.fix_reference_tags(r"<ref name-Fred />") == r"<ref name=Fred />"
    assert genfixes.fix_reference_tags(r'< ref name-"Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'< ref name+"Fred" />') == r'<ref name="Fred" />'
    assert genfixes.fix_reference_tags(r'< ref NAME="Fred" />') == r'<ref name="Fred" />', (
        r"ref NAME"
    )
    assert genfixes.fix_reference_tags(r'<ref NAME ="Fred" />') == r'<ref name ="Fred" />', (
        r"ref NAME"
    )
    assert genfixes.fix_reference_tags(r'<ref name = name ="Fred" />') == r'<ref name ="Fred" />', (
        r"ref name=name="
    )
    assert genfixes.fix_reference_tags(r'<ref name=name ="Fred" />') == r'<ref name ="Fred" />', (
        r"ref name=name="
    )
    assert genfixes.fix_reference_tags(r'<ref name="ref name="Fred"/>') == r'<ref name="Fred"/>', (
        r'ref name="ref name="'
    )
    assert (
        genfixes.fix_reference_tags(r'<ref name = " ref name = "Fred"/>') == r'<ref name = "Fred"/>'
    ), r'ref name="ref name="'
    assert genfixes.fix_reference_tags(r'<refname="Fred" />') == r'<ref name="Fred" />', r"refname"
    assert genfixes.fix_reference_tags(r'<ref name"=Fred" />') == r'<ref name="Fred" />', (
        r'ref name"= 1'
    )
    assert genfixes.fix_reference_tags(r'<ref name"=Fred">') == r'<ref name="Fred">', (
        r'ref name"= 2'
    )
    assert genfixes.fix_reference_tags(r'<ref name"=Fred>') == r'<ref name="Fred">', r'ref name"= 3'
    assert genfixes.fix_reference_tags(r"<ref name=>") == r"<ref>"
    assert genfixes.fix_reference_tags(r"<ref name =  >") == r"<ref>"
    assert genfixes.fix_reference_tags(r'<ref name = "" >') == r"<ref>"
    assert genfixes.fix_reference_tags(r'<ref name ""=>') == r"<ref>"
    assert genfixes.fix_reference_tags(r"<ref name = group = >") == r"<ref>"
    assert genfixes.fix_reference_tags(r'<ref name">') == r"<ref>"
    assert genfixes.fix_reference_tags(r'<ref name"">') == r"<ref>"
    assert (
        genfixes.fix_reference_tags(r'A<ref name="">Hello</ref>, B<ref name=""/>')
        == r'A<ref name="">Hello</ref>, B<ref name=""/>'
    )
    assert (
        genfixes.fix_reference_tags("A.<ref>[http://www.site.com a site]</ref\r\nThen")
        == "A.<ref>[http://www.site.com a site]</ref>\r\nThen"
    ), r"incorrect closing </ref>"
    assert genfixes.fix_reference_tags(r'< ref name="Fred" />') == r'<ref name="Fred" />', (
        r"< ref name"
    )
    S = set_lang(r"zh")
    assert genfixes.fix_reference_tags(r"</ref> some text") == r"</ref>some text", (
        r"Chinese put no space before/after the reference tags"
    )
    assert (
        genfixes.fix_reference_tags(r'<ref name="foo" />      some text')
        == r'<ref name="foo" />some text'
    ), r"Chinese put no space before/after the reference tags"
    S = set_lang(r"en")
    assert genfixes.fix_reference_tags(r"</ref> some text") == r"</ref> some text", (
        r"English put a space after the reference tags"
    )


def test_reorder_references_tests() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = \"Fred1\">So says Fred</ref>\r\nArticle started off pretty good, <ref>So says John</ref> <ref name = \"Fred1\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = \"Fred1\">So says Fred</ref>\r\nArticle started off pretty good, <ref name = \"Fred1\" /> <ref>So says John</ref> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = \"Fred2\">So says Fred</ref>\r\nArticle started off pretty good, <ref name = \"John1\" >So says John</ref> <ref name = \"Fred2\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = \"Fred2\">So says Fred</ref>\r\nArticle started off pretty good, <ref name = \"Fred2\" /> <ref name = \"John1\" >So says John</ref> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            '\'\'\'Article\'\'\' is great.<ref name = "Fred8">So says Fred</ref><ref name = "John3" />\r\nArticle started off pretty good, <ref>Third</ref><ref name = "John3" >So says John</ref> <ref name = "Fred8" /> and finished well.\r\nEnd of.'
        )
        == '\'\'\'Article\'\'\' is great.<ref name = "Fred8">So says Fred</ref><ref name = "John3" />\r\nArticle started off pretty good, <ref name = "Fred8" /><ref name = "John3" >So says John</ref> <ref>Third</ref> and finished well.\r\nEnd of.'
    )
    assert (
        genfixes.reorder_references(
            '\'\'\'Article\'\'\' is great.<ref name = "Fred9">So says Fred</ref><ref name = "John3" /><ref name = "Tim1">ABC</ref>\r\nArticle started off pretty good, <ref name = "Tim1"/><ref name = "John3" >So says John</ref> <ref name = "Fred9" /> and finished well.\r\nEnd of.'
        )
        == '\'\'\'Article\'\'\' is great.<ref name = "Fred9">So says Fred</ref><ref name = "John3" /><ref name = "Tim1">ABC</ref>\r\nArticle started off pretty good, <ref name = "Fred9" /><ref name = "John3" >So says John</ref> <ref name = "Tim1"/> and finished well.\r\nEnd of.'
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/><ref name = 'John3' >So says John</ref> <ref name = 'Fred9' /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Fred9' /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/><ref name = 'John3' >So says John</ref> <ref name = Fred9 /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = Fred9 /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/><ref name = 'John3' >So says John</ref> <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/>{{rp|11}}<ref name = 'John3' >So says John</ref> <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/>{{rp|11}} and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/>{{rp|11{{--}}12}}<ref name = 'John3' >So says John</ref> <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/>{{rp|11{{--}}12}} and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/>{{rp |11}}<ref name = 'John3' >So says John</ref> <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/>{{rp |11}} and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/>{{rp|needed=y|May 2008}}<ref name = 'John3' >So says John</ref> <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/>{{rp|needed=y|May 2008}} and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/>{{rp|11}}<ref name = 'John3' >So says John</ref> <ref name = \"Fred9\" />{{Rp|12}} and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" />{{Rp|12}}<ref name = 'John3' >So says John</ref> <ref name = 'Tim1'/>{{rp|11}} and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/><ref name = 'John3' >So says John</ref>{{rp|11}} <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref>{{rp|11}} <ref name = 'Tim1'/> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/><ref name = 'John3' >So says John</ref>{{rp|needed=y|May 2008}} <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref>{{rp|needed=y|May 2008}} <ref name = 'Tim1'/> and finished well.\r\nEnd of."
    )
    assert (
        genfixes.reorder_references(
            "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = 'Tim1'/><ref name = 'John3' >So says John</ref>{{Page needed|needed=y|May 2008}} <ref name = \"Fred9\" /> and finished well.\r\nEnd of."
        )
        == "'''Article''' is great.<ref name = 'Fred9'>So says Fred</ref><ref name = 'John3' /><ref name = 'Tim1'>ABC</ref>\r\nArticle started off pretty good, <ref name = \"Fred9\" /><ref name = 'John3' >So says John</ref>{{Page needed|needed=y|May 2008}} <ref name = 'Tim1'/> and finished well.\r\nEnd of."
    )
    a = "'''Article''' is great.<ref name = \"Fred3\">So says Fred</ref>\r\nArticle started off pretty good, <ref name = \"Fred3\" /> <ref name = \"John2\" >So says John</ref> and finished well.\r\nEnd of."
    b = "'''Article''' is great.<ref name = \"Fred4\">So says Fred</ref>\r\nArticle started off pretty good, <ref>So says Tim</ref> <ref>So says John</ref> and finished well.\r\nEnd of."
    c = "'''Article''' is great.<ref name = \"Fred5\">So says Fred</ref>\r\nArticle started off pretty good,<ref name = \"Fred5\" /> <ref>So says John</ref> and finished well.\r\nEnd of."
    d = "'''Article''' is great.<ref name = \"Fred6\">So says Fred</ref>\r\nArticle started off pretty good, <ref>So says John</ref> <ref name = \"A\">So says A</ref> and finished well.\r\nEnd of."
    e = '\'\'\'Article\'\'\' is great.<ref name = "John2" />\r\nArticle is new.<ref name = "Fred7">So says Fred</ref>\r\nArticle started off pretty good, <ref name = "John2" >So says John</ref> <ref name = "Fred7" /> and finished well.\r\nEnd of.'
    assert genfixes.reorder_references(a) == a
    assert genfixes.reorder_references(b) == b
    assert genfixes.reorder_references(c) == c
    assert genfixes.reorder_references(d) == d
    assert genfixes.reorder_references(e) == e
    nochange = '* [[Algeria]]<ref name="UNESCO"/><ref name="oic">[http://www.sesrtcic.org/members/default.shtml OIC members and Palestine] \'\'The Statistical, Economic and Social Research and Training Centre for Islamic Countries\'\'<br> [https://english.people.com.cn/200604/14/eng20060414_258351.html OIC members urge recognition of Hamas] \'\'People\'s Daily\'\'</ref><ref name="MEDEA"/>\r\n* [[Angola]]<ref name="UNESCO">{{cite web|url=http://unesdoc.unesco.org/images/0008/000827/082711eo.pdf|title=Request for the admission of the State of Palestine to Unesco as a Member State|date=12 May 1989|publisher=[[UNESCO]]|accessdate=2009-08-22}}</ref><ref name="MEDEA"/>\r\n* [[Benin]]<ref name="UNESCO"/><ref name="oic"/><ref name="MEDEA"/>'
    assert genfixes.reorder_references(nochange) == nochange


def test_reorder_references_not_within_reflist() -> None:
    S = W.for_site(EN)
    a = '\r\n<references>\r\n<ref>So says John</ref>\r\n<ref name = "Fred1" />\r\n</references>'
    b = '{{reflist|3|refs=\r\n<ref>So says John</ref>\r\n<ref name = "Fred1" />\r\n}}'
    correctpart = "'''Article''' is great.<ref name = \"Fred1\">So says Fred</ref>\r\nArticle started off pretty good, <ref name = \"Fred1\" /> <ref>So says John</ref> and finished well.\r\nEnd of."
    assert genfixes.reorder_references(correctpart + a) == correctpart + a
    assert genfixes.reorder_references(correctpart + b) == correctpart + b
    S = set_lang(r"fr")
    assert genfixes.reorder_references(
        correctpart + b.replace(r"reflist", r"références")
    ) == correctpart + b.replace(r"reflist", r"références")
    S = set_lang(r"en")
    assert genfixes.reorder_references(correctpart + b) == correctpart + b


def test_reorder_references_ref_groups() -> None:
    S = W.for_site(EN)
    refgroup = "'''Article''' is great.<ref name = \"Fred8\" group=a>So says Fred</ref><ref name = \"John3\" />\r\nArticle started off pretty good, <ref>Third</ref><ref name = \"Fred8\" group=a/> and finished well.\r\nEnd of."
    assert genfixes.reorder_references(refgroup) == refgroup


def test_duplicate_named_references_condense() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred">The Honourable Fred Smith, 2002</ref> was'
        )
        == r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"> The Honourable Fred Smith, 2002  </ref> was'
        )
        == r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"/> was'
    ), r"excess whitespace"
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred" >The Honourable Fred Smith, 2002</ref>but later than<ref name = "Fred">The Honourable Fred Smith, 2002</ref> was'
        )
        == r'now<ref name="Fred" >The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name = "Fred">The Honourable Fred Smith, 2002 </ref>but later than<ref name="Fred">The Honourable Fred Smith, 2002</ref> was'
        )
        == r'now<ref name = "Fred">The Honourable Fred Smith, 2002 </ref>but later than<ref name="Fred"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred" >The Honourable Fred Smith, 2002< /ref> was'
        )
        == r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            "now<ref name='Fred'>The Honourable Fred Smith, 2002</ref>but later than<ref name=\"Fred\" >The Honourable Fred Smith, 2002< /ref> was"
        )
        == "now<ref name='Fred'>The Honourable Fred Smith, 2002</ref>but later than<ref name=\"Fred\"/> was"
    )
    assert (
        genfixes.duplicate_named_references(
            "now<ref name='Fred'>The Honourable Fred Smith, <br>2002</ref>but later than<ref name=\"Fred\" >The Honourable Fred Smith, <br>2002< /ref> was"
        )
        == "now<ref name='Fred'>The Honourable Fred Smith, <br>2002</ref>but later than<ref name=\"Fred\"/> was"
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref> and here<ref name="Fred">The Honourable Fred Smith, 2002</ref> but later than<ref name="Fred">The Honourable Fred Smith, 2002</ref> was'
        )
        == r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref> and here<ref name="Fred"/> but later than<ref name="Fred"/> was'
    )
    a = r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred">The Honourable Fred Smith, 2005</ref> was'
    b = r'now<ref name="Fred">The Honourable Fred Smith, 2004</ref>but later than<ref name="Fred">The Honourable FRED SMITH, 2004</ref> was'
    c = r'now<ref name="Fred">The Honourable Fred Smith, 2003</ref>but later than<ref name="Fred2">The Honourable Fred Smith, 2003</ref> was'
    c2 = r'now<ref name="Fred">Fred Smith, 2003</ref>but later than<ref name="Fred">Fred Smith, 2003</ref> was'
    assert genfixes.duplicate_named_references(a) == a
    assert genfixes.duplicate_named_references(b) == b
    assert genfixes.duplicate_named_references(c) == c
    assert genfixes.duplicate_named_references(c2) == c2
    infobox = r"{{infobox foo | badparam=A<ref name=Fred>The Honourable Fred Smith, 2002</ref> | otherparam = yes}}"
    rest = (
        "Now.<ref name=Fred>The Honourable Fred Smith, 2002</ref>\r\n==References==\r\n{{reflist}}"
    )
    assert rest in genfixes.duplicate_named_references(infobox + "\r\n" + rest), (
        r"Ref that was declared in template not condensed"
    )
    assert (
        genfixes.duplicate_named_references(
            "{{infobox foo | badparam=A<ref name=Fred /> | otherparam = yes}}\r\nNow.<ref name=Fred>The Honourable Fred Smith, 2002</ref> And.<ref name=Fred>The Honourable Fred Smith, 2002</ref>\r\n==References==\r\n{{reflist}}"
        )
        == "{{infobox foo | badparam=A<ref name=Fred /> | otherparam = yes}}\r\nNow.<ref name=Fred>The Honourable Fred Smith, 2002</ref> And.<ref name=Fred/>\r\n==References==\r\n{{reflist}}"
    ), r"Ref that was used in short form in template can be condensed elsewhere"
    Lewis = 'Hello<ref name="Lewis">{{cite journal |authors=Lewis JT |title=Low-grade cases |journal=Am J Surg Pathol |pmid=22301502}}</ref> recommended.\r\n\r\nA<ref name="Wang">{{cite journal |authors=Wang X |title=Recurrent |journal=Nat Genet |pmid=24859338}}</ref> only. Surgery.<ref name="Lewis">{{cite journal |authors=Lewis JT |title=Low-grade cases |journal=Am J Surg Pathol |pmid=22301502}}</ref>\r\n\r\n== References ==\r\n{{Reflist}}\r\n\r\n<ref name="Wang">{{cite journal |authors=Wang X |title=Recurrent |journal=Nat Genet |pmid=24859338}}</ref>\r\n<ref name="Lewis">{{cite journal |authors=Lewis JT |title=Low-grade cases |journal=Am J Surg Pathol |pmid=22301502}}</ref>'
    assert (
        genfixes.duplicate_named_references(Lewis)
        == 'Hello<ref name="Lewis">{{cite journal |authors=Lewis JT |title=Low-grade cases |journal=Am J Surg Pathol |pmid=22301502}}</ref> recommended.\r\n\r\nA<ref name="Wang">{{cite journal |authors=Wang X |title=Recurrent |journal=Nat Genet |pmid=24859338}}</ref> only. Surgery.<ref name="Lewis"/>\r\n\r\n== References ==\r\n{{Reflist}}\r\n\r\n<ref name="Wang">{{cite journal |authors=Wang X |title=Recurrent |journal=Nat Genet |pmid=24859338}}</ref>\r\n<ref name="Lewis">{{cite journal |authors=Lewis JT |title=Low-grade cases |journal=Am J Surg Pathol |pmid=22301502}}</ref>'
    ), r"When dupe cite to condense, and another one after reflist, don't condense both"


def test_duplicate_named_references_condense_fa_wiki() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fa")
    a = r'{{پک}}now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred">The Honourable Fred Smith, 2002</ref> was'
    assert genfixes.duplicate_named_references(a) == a
    S = set_lang(r"en")
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred">The Honourable Fred Smith, 2002</ref> was'
        )
        == r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"/> was'
    )


def test_duplicate_named_references_condense_quotes() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.duplicate_named_references(
            r"now<ref name=Fred>The Honourable Fred Smith, 2002</ref>but later than<ref name=Fred>The Honourable Fred Smith, 2002</ref> was"
        )
        == r"now<ref name=Fred>The Honourable Fred Smith, 2002</ref>but later than<ref name=Fred/> was"
    ), r"Don't add quotes around ref name if none there currently"
    assert (
        genfixes.duplicate_named_references(
            r"now<ref name=Fred>The Honourable Fred Smith, 2002</ref>but later than<ref name='Fred'>The Honourable Fred Smith, 2002</ref> was"
        )
        == r"now<ref name=Fred>The Honourable Fred Smith, 2002</ref>but later than<ref name='Fred'/> was"
    ), r"Retain single quotes around ref name"
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name=Fred>The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred">The Honourable Fred Smith, 2002</ref> was'
        )
        == r'now<ref name=Fred>The Honourable Fred Smith, 2002</ref>but later than<ref name="Fred"/> was'
    ), r"Retain double quotes around ref name"


def test_duplicate_named_references_tests() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Bert">The Honourable Bert Smith, 2002</ref>but later than<ref> The Honourable Bert Smith, 2002  </ref> was'
        )
        == r'now<ref name="Bert">The Honourable Bert Smith, 2002</ref>but later than<ref name="Bert"/> was'
    ), r"first named excess whitespace"
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Bert" >The Honourable Bert Smith, 2002</ref>but later than<ref>The Honourable Bert Smith, 2002</ref> was'
        )
        == r'now<ref name="Bert" >The Honourable Bert Smith, 2002</ref>but later than<ref name="Bert"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name = "Bert">The Honourable Bert Smith, 2002 </ref>but later than<ref>The Honourable Bert Smith, 2002</ref> was'
        )
        == r'now<ref name = "Bert">The Honourable Bert Smith, 2002 </ref>but later than<ref name="Bert"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Bert">The Honourable Bert Smith, 2002</ref>but later than<ref>The Honourable Bert Smith, 2002< /ref> was'
        )
        == r'now<ref name="Bert">The Honourable Bert Smith, 2002</ref>but later than<ref name="Bert"/> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r"now<ref name='Bert'>The Honourable Bert Smith, 2002</ref>but later than<ref>The Honourable Bert Smith, 2002< /ref> was"
        )
        == "now<ref name='Bert'>The Honourable Bert Smith, 2002</ref>but later than<ref name=\"Bert\"/> was"
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Bert">The Honourable Bert <small>Smith</small>, 2002</ref>but later than<ref> The Honourable Bert <small>Smith</small>, 2002  </ref> was'
        )
        == r'now<ref name="Bert">The Honourable Bert <small>Smith</small>, 2002</ref>but later than<ref name="Bert"/> was'
    ), r"nested tag support"
    d = r'now<ref name="Bert">The Honourable Bert Smith, 2002</ref>but later than<ref>The Honourable Bert Smith, 2005</ref> was'
    e = r'now<ref name="Bert">The Honourable Bert Smith, 2004</ref>but later than<ref>The Honourable BERT SMITH, 2004</ref> was'
    assert genfixes.duplicate_named_references(d) == d
    assert genfixes.duplicate_named_references(e) == e
    assert (
        genfixes.duplicate_named_references(
            r'now<ref>The Honourable John Smith, 2002</ref>but later than<ref name="John" > The Honourable John Smith, 2002  </ref> was'
        )
        == r'now<ref name="John"/>but later than<ref name="John" > The Honourable John Smith, 2002  </ref> was'
    ), r"second named excess whitespace"
    assert (
        genfixes.duplicate_named_references(
            r'now<ref>The Honourable John Smith, 2002</ref>but later than<ref name="John" >The Honourable John Smith, 2002</ref> was'
        )
        == r'now<ref name="John"/>but later than<ref name="John" >The Honourable John Smith, 2002</ref> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref>The Honourable John Smith, 2002 </ref>but later than<ref name = "John">The Honourable John Smith, 2002</ref> was'
        )
        == r'now<ref name="John"/>but later than<ref name = "John">The Honourable John Smith, 2002</ref> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref>The Honourable John Smith, 2002</ref>but later than<ref name="John">The Honourable John Smith, 2002< /ref> was'
        )
        == r'now<ref name="John"/>but later than<ref name="John">The Honourable John Smith, 2002< /ref> was'
    )
    assert (
        genfixes.duplicate_named_references(
            r"now<ref>The Honourable John Smith, 2002</ref>but later than<ref name='John'>The Honourable John Smith, 2002< /ref> was"
        )
        == "now<ref name=\"John\"/>but later than<ref name='John'>The Honourable John Smith, 2002< /ref> was"
    )
    assert (
        genfixes.duplicate_named_references(
            r'now<ref>The Honourable John Smith, 2002</ref>but later than<ref name="John 2" > The Honourable John Smith, 2002  </ref> was'
        )
        == r'now<ref name="John 2"/>but later than<ref name="John 2" > The Honourable John Smith, 2002  </ref> was'
    )
    f = r'now<ref>The Honourable John Smith, 2002</ref>but later than<ref name="John">The Honourable John Smith, 2005</ref> was'
    g = r'now<ref>The Honourable John Smith, 2004</ref>but later than<ref name="John">The HONOURABLE JOHN SMITH, 2004</ref> was'
    assert genfixes.duplicate_named_references(f) == f
    assert genfixes.duplicate_named_references(g) == g
    RefInReflist = "Foo<ref name='first'>690nBTivR9o2mJ6vMYccwmjl5TO9BxvhF9deev2VSi17H</ref>here.\r\n            \r\n            ==Notes==\r\n            {{reflist|2|refs=\r\n            \r\n            <ref name='first'>690nBTivR9o2mJ6vMYccwmjl5TO9BxvhF9deev2VSi17H</ref>\r\n            \r\n            }}"
    assert genfixes.duplicate_named_references(RefInReflist) == RefInReflist
    h = r'now<ref name="Fred">The Honourable Fred Smith, 2002</ref>but later than first<ref name="Fred">The Honourable Fred Smith, 2002</ref> and second<ref name="Fred">The Honourable Fred Smith, 2005</ref> was'
    assert genfixes.duplicate_named_references(h) == h


def test_duplicate_named_references_reparse() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.duplicate_named_references(
            r'now<ref name="Fred">The Honourable Fred Smith, 2002 wcK63lPneu8pqiK6bxxYMgRSL7ySo4XaOIl4Kr24XB8Hd</ref>but later<ref name=Fred2>text words random 3b3HmI0viQTbmiLIDiGnjTAIX8mpebT520I1 words</ref> than<ref name="Fred">The Honourable Fred Smith, 2002 wcK63lPneu8pqiK6bxxYMgRSL7ySo4XaOIl4Kr24XB8Hd</ref> was<ref name="Fred2">text words random 3b3HmI0viQTbmiLIDiGnjTAIX8mpebT520I1 words</ref>'
        )
        == r'now<ref name="Fred">The Honourable Fred Smith, 2002 wcK63lPneu8pqiK6bxxYMgRSL7ySo4XaOIl4Kr24XB8Hd</ref>but later<ref name=Fred2>text words random 3b3HmI0viQTbmiLIDiGnjTAIX8mpebT520I1 words</ref> than<ref name="Fred"/> was<ref name="Fred2"/>'
    ), r"reparse used to fix all duplicate refs"


def test_duplicate_unnamed_references() -> None:
    S = W.for_site(EN)
    namedref = r"now <ref name=foo>foo</ref> and <ref name=foo/>"
    assert len(genfixes.duplicate_unnamed_references(r"")) == 0
    assert genfixes.duplicate_unnamed_references(namedref) == namedref
    nonamedref = r'<ref>"bookrags.com"</ref> foo <ref> "bookrags.com" </ref>'
    assert genfixes.duplicate_unnamed_references(nonamedref) == nonamedref
    assert (
        genfixes.duplicate_unnamed_references(
            r'<ref>"bookrags.com"</ref> foo <ref> "bookrags.com" </ref>' + namedref
        )
        == r'<ref name="bookrags.com">"bookrags.com"</ref> foo <ref name="bookrags.com"/>'
        + namedref
    ), r"named ref 1"
    assert (
        genfixes.duplicate_unnamed_references(
            r'<ref>"bookrags.com"</ref> foo bar <ref>abcde</ref> now <ref>abcde</ref>now <ref>"bookrags.com"</ref>'
            + namedref
        )
        == r'<ref name="bookrags.com">"bookrags.com"</ref> foo bar <ref name="abcde">abcde</ref> now <ref name="abcde"/>now <ref name="bookrags.com"/>'
        + namedref
    ), r"named ref 2"
    assert (
        genfixes.duplicate_unnamed_references(
            r"<ref>http://ecomodder.com/forum/showthread.php/obd-mpguino-gauge-2702.html</ref> foo bar <ref>http://ecomodder.com/wiki/index.php/MPGuino</ref> now <ref>http://ecomodder.com/wiki/index.php/MPGuino</ref>now <ref>http://ecomodder.com/forum/showthread.php/obd-mpguino-gauge-2702.html</ref>"
            + namedref
        )
        == r'<ref name="ecomodder.com">http://ecomodder.com/forum/showthread.php/obd-mpguino-gauge-2702.html</ref> foo bar <ref name="ReferenceA">http://ecomodder.com/wiki/index.php/MPGuino</ref> now <ref name="ReferenceA"/>now <ref name="ecomodder.com"/>'
        + namedref
    ), r"named ref 3"
    Ibid = r"now <ref>ibid</ref> was<ref>ibid</ref> there"
    assert genfixes.duplicate_unnamed_references(Ibid + namedref) == Ibid + namedref
    Pageneeded = r"now <ref>Class 50s in Operation. D Clough {{page needed|date=September 2014}}</ref>  was <ref>Class 50s in Operation. D Clough {{page needed|date=September 2014}}</ref> there"
    assert genfixes.duplicate_unnamed_references(Pageneeded + namedref) == Pageneeded + namedref
    SingleRef = r"now <ref>first</ref> was"
    assert genfixes.duplicate_unnamed_references(SingleRef + namedref) == SingleRef + namedref
    E = r"Foo<ref name=a>a</ref> bar<ref name=a/> was<ref>b</ref> and 1<ref>c</ref> or 2<ref>c</ref>"
    E2 = r'Foo<ref name=a>a</ref> bar<ref name=a/> was<ref>b</ref> and 1<ref name="ReferenceA">c</ref> or 2<ref name="ReferenceA"/>'
    assert genfixes.duplicate_unnamed_references(E) == E2
    F = r'<ref>"book"</ref> foo <ref> "book" </ref> <ref name=book>A</ref><ref name="ReferenceA">"bookA"</ref><ref name="ReferenceB">"bookB"</ref><ref name="ReferenceC">"bookC"</ref>'
    assert genfixes.duplicate_unnamed_references(F) == F
    assert (
        genfixes.duplicate_unnamed_references(
            r'{{infobox foo|bar=1<ref>"bookrags.com"</ref>}} foo <ref> "bookrags.com" </ref>'
            + namedref
        )
        == r'{{infobox foo|bar=1<ref name="bookrags.com">"bookrags.com"</ref>}} foo <ref name="bookrags.com">"bookrags.com"</ref>'
        + namedref
    ), r"Ref named, but not condensed if declared in template"


def test_duplicate_unnamed_references_fa_wiki() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fa")
    namedref = r"now <ref name=foo>foo</ref> and <ref name=foo/>"
    a = r'<ref>"bookrags.com"</ref> foo <ref> "bookrags.com" </ref>'
    template = r"{{پانویس کوتاه‌شده}}"
    assert (
        genfixes.duplicate_unnamed_references(a + template + namedref) == a + template + namedref
    ), r"named ref 1 - fawiki no change"
    S = set_lang(r"en")
    a = r'<ref>"bookrags.com"</ref> foo <ref> "bookrags.com" </ref>'
    assert (
        genfixes.duplicate_unnamed_references(a + namedref)
        == r'<ref name="bookrags.com">"bookrags.com"</ref> foo <ref name="bookrags.com"/>'
        + namedref
    ), r"named ref 1"


def test_has_named_references() -> None:
    S = W.for_site(EN)
    assert genfixes.has_named_references(r"now <ref name=foo />")
    assert genfixes.has_named_references(r'now <ref name="foo" />')
    assert not (genfixes.has_named_references(r"now <ref name=foo>foo</ref>"))
    assert not (genfixes.has_named_references(r'now <ref name="foo">bar</ref>'))
    assert not (genfixes.has_named_references(r"now <ref>foo</ref>"))
    assert not (genfixes.has_named_references(r"now <!--<ref name = foo>foo</ref>-->"))


def test_derive_reference_name_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.derive_reference_name(r"a", r"Smith") == r"Smith"
    assert (
        genfixes.derive_reference_name(
            r"a", r"{{cite book|last=Smith|title=hello|year=2008|foo=bar}}"
        )
        == r"Smith 2008"
    )
    assert (
        genfixes.derive_reference_name(r"a", r"{{cite book|last=Smith|title=hello|year=2008}}")
        == r"Smith 2008"
    )
    assert (
        genfixes.derive_reference_name(
            r"a", r"{{cite book|year=2008|last=Smith|title=hello||foo=bar|pages=17}}"
        )
        == r"Smith 2008 17"
    )
    assert (
        genfixes.derive_reference_name(
            r"a", r"{{citation|pages=17|year=2008|last=Smith|title=hello||foo=bar}}"
        )
        == r"Smith 2008 17"
    )
    assert (
        genfixes.derive_reference_name(
            r"a", r"{{Cite book|title=hello|year=2008|last=Smither Bee|foo=bar}}"
        )
        == r"Smither Bee 2008"
    )
    assert genfixes.derive_reference_name(r"a", r"Oldani (1982: p.8)") == r"Oldani 1982: p.8"
    assert (
        genfixes.derive_reference_name(r"a", r"http://elections.sos.state.tx.us/elchist.exe")
        == r"elections.sos.state.tx.us"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web | url=http://www.imdb.com/title/tt0120992/crazycredits | title=Hypnotist The Incredible BORIS is Boris Cherniak | accessdate=2007-10-15 }}",
        )
        == r"imdb.com"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web | url=hello.imdb.com/tt0120992/ | title=Hypnotist The Incredible BORIS is Boris Cherniak | accessdate=2007-10-15 }}",
        )
        == r"Hypnotist The Incredible BORIS is B"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web | url=hello.imdb.com/tt0120992/ | title=Hypnotist{{!}} The Incredible | accessdate=2007-10-15 }}",
        )
        == r"Hypnotist The Incredible"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web | url=hello.imdb.com/tt0120992/ | trans-title= |title=Hypnotist The Incredible BORIS | accessdate=2007-10-15 }}",
        )
        == r"Hypnotist The Incredible BORIS"
    ), r"title use"
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web | url=hello.imdb.com/tt0120992/ | title=Foreign language|trans-title=Hypnotist The Incredible BORIS | accessdate=2007-10-15 }}",
        )
        == r"Hypnotist The Incredible BORIS"
    ), r"Trans-title use"
    assert (
        genfixes.derive_reference_name(
            r'A<ref name="hello.imdb.com">x</ref>',
            r"{{cite web | url=https://hello.imdb.com/tt0120992/ | title=Hypnotist The Incredible BORIS is Boris Cherniak | accessdate=2007-10-15 }}",
        )
        == r"Hypnotist The Incredible BORIS is B"
    )
    assert (
        genfixes.derive_reference_name(
            r"a", r"Caroline Humphrey, David Sneath-The end of Nomadism?, p.27"
        )
        == r"Caroline Humphrey p.27"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"Dennis, Peter (et al.) (1995) The Oxford Companion to Australian Military History, Melbourne: Oxford University Press, Page 440.",
        )
        == r"Dennis, Peter 1995 Page 440"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            "{{cite journal\r\n  | last = Sepkoski| first = Jack| authorlink =| coauthors =| title =  A compendium of fossil marine animal genera (Trilobita entry)| journal = Bulletins of American Paleontology| volume = 364| issue =| pages = p.560| publisher =| location =| date = 2002| url = http://strata.ummp.lsa.umich.edu/jack/showgenera.php?taxon=307&rank=class| doi =| id =| accessdate = 2008-01-12 }}",
        )
        == r"Sepkoski 2002 p.560"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            "{{Cite journal\r\n  | last = Sepkoski| first = Jack| authorlink =| coauthors =| title =  A compendium of fossil marine animal genera (Trilobita entry)| journal = Bulletins of American Paleontology| volume = 364| issue =| pages = p.560| publisher =| location =| year = 2002| url = http://strata.ummp.lsa.umich.edu/jack/showgenera.php?taxon=307&rank=class| doi =| id =| accessdate = 2008-01-12 }}",
        )
        == r"Sepkoski 2002 p.560"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"[http://www.gillan.com/anecdotage-12.html Ian Gillan's official website: Caramba]",
        )
        == r"gillan.com"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web | title= Founder of China's Born Again Movement Set Free| work= Christianity Today | url= http://www.christianitytoday.com/ct/2000/augustweb-only/22.0.html| accessdate=2008-02-19}}",
        )
        == r"Christianity Today"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"Moscow Bound: Policy, Politics, and the POW/MIA Dilemma, John M. G. Brown, Veteren Press, Eureka Springs, California, 1993, Chapt. 14",
        )
        == r"Moscow Bound 1993"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            "\"Boris Nikolayevich Kampov,\" ''Contemporary Authors Online'', Thomson Gale, 2007.",
        )
        == r"Boris Nikolayevich Kampov 2007"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite book| last = Farlow| first = James O.| coauthors = M. K. Brett-Surmann| title = The Complete Dinosaur| publisher = Indiana University Press| date = 1999| location = Bloomington, Indiana| pages = 8| isbn = 0-253-21313-4}}",
        )
        == r"Farlow 1999 8"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            "JAY STRAFFORD, \"[http://www.timesdispatch.com/rtd/entertainment/books_literature/article/BMYS25_20090121-192837/184966/ Globe-trotting with the Grim Reaper],\" ''Richmond-Times Dispatch'' (January 25, 2009).",
        )
        == r"Globe-trotting with the Grim Reaper"
    )
    assert genfixes.derive_reference_name(r"a", r"") == r"ReferenceA"
    assert (
        genfixes.derive_reference_name(
            r"a", r"* Cf. Ezriel Carlebach entry in the Hebrew Wikipedia"
        )
        == r"ReferenceA"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite book |author=Bray, Warwick |year=1968 |chapter=Everyday Life of The Aztecs |pages=93-96}}",
        )
        == r"Bray, Warwick 1968 93-96"
    )
    assert genfixes.derive_reference_name(r"a", r"{{harv|Olson|2000|p=84}}") == r"Olson 2000 84"
    assert genfixes.derive_reference_name(r"a", r"{{harv|Olson|2000|pp =84}}") == r"Olson 2000 84"
    assert genfixes.derive_reference_name(r"a", r"{{harvnb|Olson|2000 }}") == r"Olson 2000"
    assert genfixes.derive_reference_name(r"a", r"{{Sfn|Olson|2000 }}") == r"Olson 2000"
    assert (
        genfixes.derive_reference_name(r"a", r"{{Harvard citation no brackets|Olson|2000 }}")
        == r"Olson 2000"
    )
    assert (
        genfixes.derive_reference_name(r"a", r"{{harvcolnb|Olson|2000|p=84}}") == r"Olson 2000 84"
    )
    assert (
        genfixes.derive_reference_name(r"a", r"{{Harvcolnb|Olson|2000|p=84}}") == r"Olson 2000 84"
    )
    assert (
        genfixes.derive_reference_name(r"a", r"{{Harvnb|Caggiano|Duncan|1983}}") == r"Caggiano 1983"
    )
    assert (
        genfixes.derive_reference_name(r"a", r"{{Harvnb|Simpson|others|1986}}") == r"Simpson 1986"
    )
    assert (
        genfixes.derive_reference_name(
            r"a", r"Reload Bench [http://reloadbench.com/cartridges/w17bee.html]"
        )
        == r"reloadbench.com"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            "\"-logy.\" ''The Oxford English Dictionary'', Second Edition. Oxford University Press, 1989. retrieved 20 Aug 2008.",
        )
        == r"The Oxford English Dictionary 1989"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite web|title=firstaif|url=http://www.firstaif.info/pages/nz_mounted.htm}}</ref><ref>{{cite web|title=diggerhistory|url=http://www.diggerhistory.info/pages-nz/nzef.htm}}",
        )
        == r"firstaif"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            "{{cite web\r\n  | last =\r\n  | first =\r\n  | title = Welcome to the on-line catalog of Bloom Cigar Company in Pittsburgh, home of Cigar CampTM\r\n  | work =\r\n  | publisher = Bloom Cigar Company\r\n  | date = 2003\r\n  | url = http://www.bloomcigar.com/catalog/\r\n  | accessdate = 2008-11-01\r\n  | archiveurl = http://www.webcitation.org/5c1PcWcc8\r\n  | archivedate = 2008-11-01}}",
        )
        == r"Bloom Cigar Company"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"Kuykendall, R.S. (1967). The Hawaiian Kingdom, Vol. III, 1874-1893: The Kalakaua Dynasty. Honolulu: University of Hawaii Press. p. 628.",
        )
        == r"Kuykendall, R.S. 1967 p. 628"
    )
    assert (
        genfixes.derive_reference_name(r"a", r"[[#Banj1930|Bajanov 2003]]: 2-3")
        == r"Bajanov 2003: 2-3"
    )
    assert (
        genfixes.derive_reference_name(
            r"a<ref name=ReferenceA>foo</ref> now",
            r"* Cf. Ezriel Carlebach entry in the Hebrew Wikipedia",
        )
        == r"ReferenceB"
    )
    assert (
        genfixes.derive_reference_name(
            r"a<ref name=ReferenceA>foo</ref> now <ref name=ReferenceB>foo</ref>",
            r"* Cf. Ezriel Carlebach entry in the Hebrew Wikipedia",
        )
        == r"ReferenceC"
    )
    assert (
        genfixes.derive_reference_name(
            r"a<ref name=ReferenceA>foo</ref> now <ref name=ReferenceB>foo</ref> <ref name=ReferenceC>foo</ref>",
            r"* Cf. Ezriel Carlebach entry in the Hebrew Wikipedia",
        )
        == r"ReferenceD"
    )
    assert (
        genfixes.derive_reference_name(
            r'a <ref name="Smither Bee 2008">a</ref> was',
            r"{{Cite book|title=hello|year=2008|last=Smither Bee|foo=bar|url = http://books.Google.com/special}}",
        )
        == r"books.Google.com"
    )
    assert (
        genfixes.derive_reference_name(
            r"a <ref name='Smither Bee 2008'>a</ref> was",
            r"{{Cite book|title=hello|year=2008|last=Smither Bee|foo=bar|url = http://books.Google.com/special}}",
        )
        == r"books.Google.com"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"<ref>The city of Baeza, March 2, 1476. ''Colección de documentos España'', t. XI, p.396</ref>",
        )
        == r"Baeza, March 2, 1476. p.396"
    ), r"correct date format used"
    assert genfixes.derive_reference_name(r"a", r"{{cite pmid|123456}}") == r"pmid123456"
    assert (
        genfixes.derive_reference_name(r"a", r"{{cite doi|10.1112/123456}}") == r"doi10.1112/123456"
    )
    assert (
        genfixes.derive_reference_name(
            r"abc <ref name=dtic.mil>a</ref>",
            r"http://www.dtic.mil/dtic/tr/fulltext/u2/a168577.pdf |ANALYSIS OF M16A2 RIFLE CHARACTERISTICS AND RECOMMENDED IMPROVEMENTS. Arthur D. Osborne. Mellonics Systems Development Division. Litton Systems, Inc. WD and Seward Smith ARI Field Unit at Fort Benning, Georgia. TRAINING RESEARCH LABORATORY. U. S. Army Research Institute for the Behavioral and Social Sciences. February 1986",
        )
        == r"ReferenceA"
    )
    assert (
        genfixes.derive_reference_name(
            r"a",
            r"{{cite book |last=Perla |first=Peter P. |title=The Art of Wargaming: A Guide for Professionals and Hobbyists |publisher=[[Naval Institute Press]] |location=Annapolis, MD |year=1990 |page=[https://archive.org/details/artofwargaminggu0000perl/page/117/mode/2up?q=%22Eric+Dott%22 117-188] |isbn=0870210505 }}",
        )
        == r"Perla 1990 117-188"
    )


def test_same_ref_different_name() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005</ref> and bar<ref name=J5>Jones 2005</ref>"
        )
        == r'Foo<ref name=Jones>Jones 2005</ref> and bar<ref name="Jones">Jones 2005</ref>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005</ref> and bar<ref name=J5>Jones 2005</ref> and more<ref name=J5/>"
        )
        == r'Foo<ref name=Jones>Jones 2005</ref> and bar<ref name="Jones">Jones 2005</ref> and more<ref name="Jones"/>'
    )
    assert (
        genfixes.same_ref_different_name(
            "Foo<ref name=Jones>Jones 2005</ref> and bar<ref name=J5>\r\nJones 2005</ref>"
        )
        == 'Foo<ref name=Jones>Jones 2005</ref> and bar<ref name="Jones">\r\nJones 2005</ref>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=J5>Jones 2005</ref> and bar<ref name=Jones>Jones 2005</ref>"
        )
        == r'Foo<ref name="Jones">Jones 2005</ref> and bar<ref name=Jones>Jones 2005</ref>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005</ref> and bar<ref name=J5>Jones 2005   </ref>"
        )
        == r'Foo<ref name=Jones>Jones 2005</ref> and bar<ref name="Jones">Jones 2005   </ref>'
    )
    nochange = r"Foo<ref name=Jones>ibid</ref> and bar<ref name =A5>ibid</ref>"
    assert genfixes.same_ref_different_name(nochange) == nochange
    nochange = r"Foo<ref name=Jones group=A/> and bar<ref name =Jones>Text</ref> and <ref name =JonesY>Text</ref>"
    assert genfixes.same_ref_different_name(nochange) == nochange
    nochange = r'Foo<ref name="Jones" group=A/> and bar<ref name ="Jones">Text2</ref> and <ref name =JonesY>Text2</ref>'
    assert genfixes.same_ref_different_name(nochange) == nochange
    nochange = r"Foo<ref name='Jones' group=A/> and bar<ref name =Jones>Text3</ref> and <ref name =JonesY>Text3</ref>"
    assert genfixes.same_ref_different_name(nochange) == nochange
    nochange = r"Foo<ref group=A name=Jones /> and bar<ref name =Jones>Text4</ref> and <ref name =JonesY>Text4</ref>"
    assert genfixes.same_ref_different_name(nochange) == nochange


def test_same_ref_different_name_multi() -> None:
    S = W.for_site(EN)
    before = 'Foo.<ref>{{cite web | url = http://site.com | title = This is a normal title }}</ref>\r\nFoo2.<ref name=A>{{cite web | url = http://site.com | title = This is a normal title }}</ref>\r\nBar3.<ref name=ABCDEF>{{cite web | url = http://site.com | title = This is a normal title }}</ref>\r\nBar4.<ref name="ABCDEFGHI">{{cite web | url = http://site.com | title = This is a normal title }}</ref>\r\n\r\n==References==\r\n{{reflist}}'
    after = 'Foo.<ref name="ABCDEFGHI"/>\r\nFoo2.<ref name="ABCDEFGHI">{{cite web | url = http://site.com | title = This is a normal title }}</ref>\r\nBar3.<ref name="ABCDEFGHI"/>\r\nBar4.<ref name="ABCDEFGHI"/>\r\n\r\n==References==\r\n{{reflist}}'
    assert genfixes.same_ref_different_name(before) == after, (
        r"reparse used to rename multiple refs with same name"
    )


def test_same_ref_different_name_name_derivation() -> None:
    S = W.for_site(EN)
    correct = r'Foo<ref name=Jones>Jones 2005</ref> and bar<ref name="Jones">Jones 2005</ref>'
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005</ref> and bar<ref name=J5>Jones 2005</ref>"
        )
        == correct
    )
    assert (
        genfixes.same_ref_different_name(
            r'Foo<ref name=Jones>Jones 2005</ref> and bar<ref name="Jo">Jones 2005</ref>'
        )
        == correct
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005</ref> and bar<ref name=autogenerated1>Jones 2005</ref>"
        )
        == correct
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005</ref> and bar<ref name= ReferenceA>Jones 2005</ref>"
        )
        == correct
    )


def test_same_named_ref_short_text() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones>a</ref>"
        )
        == r'Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name="Jones"/>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>x</ref> and bar<ref name=Jones>Jones 2005 extra words of interest</ref>"
        )
        == r'Foo<ref name="Jones"/> and bar<ref name=Jones>Jones 2005 extra words of interest</ref>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones>a</ref> and bar2<ref name=Jones>x</ref>"
        )
        == r'Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name="Jones"/> and bar2<ref name="Jones"/>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar2<ref name=Jones>[see above]</ref>"
        )
        == r'Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar2<ref name="Jones"/>'
    )
    assert (
        genfixes.same_ref_different_name(
            r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar2<ref name=Jones>{{cite web}}</ref>"
        )
        == r'Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar2<ref name="Jones"/>'
    )
    pageref1 = r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones>2</ref>"
    pageref2 = r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones> page 2</ref>"
    pageref3 = r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones>pp. 2</ref>"
    pageref4 = r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones>P 2</ref>"
    pageref5 = r"Foo<ref name=Jones>Jones 2005 extra words of interest</ref> and bar<ref name=Jones>Jones P 2</ref>"
    assert genfixes.same_ref_different_name(pageref1) == pageref1
    assert genfixes.same_ref_different_name(pageref2) == pageref2
    assert genfixes.same_ref_different_name(pageref3) == pageref3
    assert genfixes.same_ref_different_name(pageref4) == pageref4
    assert genfixes.same_ref_different_name(pageref5) == pageref5


def test_bad_cite_parameters() -> None:
    S = W.for_site(EN)
    Found = {}
    Found[15] = 3
    assert genfixes.bad_cite_parameters(r"now {{cite web|foo=bar|date=2009}} was") == Found
    Found.pop(15)
    Found[15] = 6
    assert genfixes.bad_cite_parameters(r"now {{cite web|foodoo=bar|date=2009}} was") == Found
    Found.pop(15)
    Found[15] = 6
    assert genfixes.bad_cite_parameters(r"now {{cite web|fooéoo=bar|date=2009}} was") == Found
    Found.pop(15)
    Found[15] = 3
    assert genfixes.bad_cite_parameters(r"now {{cite web|day=11|date=2009}} was") == Found
    Found.pop(15)
    Found[15] = 3
    assert genfixes.bad_cite_parameters(r"now {{cite web|day=1|date=2009}} was") == Found
    Found.pop(15)
    Found[15] = 5
    assert genfixes.bad_cite_parameters(r"now {{cite web|da te=1|date=2009}} was") == Found
    Found.pop(15)
    Found[15] = 9
    assert genfixes.bad_cite_parameters(r"now {{cite web|'language=Thai|date=2009}} was") == Found
    Found.pop(15)
    assert genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009}} was") == Found
    assert (
        genfixes.bad_cite_parameters(
            r"now {{cite web|url=bar|date=2009|title=A|trans-title=B}} was"
        )
        == Found
    )
    assert genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|editor=a}} was") == Found
    assert genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|id=3838}} was") == Found
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|issn=3838-1542}} was")
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|isbn=1234567890}} was")
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|author1=Y|author2=X}} was")
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|deadurl=no}} was") == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url={{Allmusic|class = foo}}|date=2009}} was")
        == Found
    )
    assert genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|at=here}} was") == Found
    assert (
        genfixes.bad_cite_parameters(
            r"now {{cite web|url=bar|date=2009|first1=Foo|last1=Great |first2=Bar|title=here}} was"
        )
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|authorlink1=Smith}} was")
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|authorlink20=Bill}} was")
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|url=bar|date=2009|author=Smith}} was")
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(
            r"now {{cite web|url=bar|date=2009|df=mdy|collaboration=Foo|eissn=1234-5678|hdl=123.456}} was"
        )
        == Found
    )
    assert (
        genfixes.bad_cite_parameters(
            "{{cite web | periodical=, |journal=, |newspaper=, |magazine=, |work=, |website=, |encyclopedia=, |encyclopaedia=, |dictionary=,\r\n|arxiv=, |ARXIV=, |ASIN=, |ASIN-TLD=,\r\n|publicationplace=, |publication-place=,\r\n|date=, |year=, |publicationdate=, |publication-date=,\r\n|series=, |volume=, |issue=, |number=, |page=, |pages=, |at=,\r\n|edition=, |publisher=, |institution=,|interviewer=,|script-website=,\r\n|journal=, |jstor=, |agency=, |archive-date=, |others=, | vauthors =, | veditors =, |translator =, |translator-last=, |translator-first=, |translator-link=, |time=,|citeseerx=,\r\n|name-list-style=a |script-work=, |trans-quote=, |archive-format=, |lay-url=\r\n|author-given=, |author-surname=, |display-subjects=, |interviewer-given=, |interviewer-surname=, |orig-date=, |quote-page=, |quote-pages=, |sbn=, |script-quote=, |subject-mask=, |s2cid=, |s2cid-access=, |title-link=, |trans-quote= , |translator1=, |trans-work= ,\r\n|trans-website=,|subject=,|medium=,|host=,|minutes=,}}"
        )
        == Found
    )
    assert genfixes.bad_cite_parameters(r"now {{cite arxiv|display-authors=0}} was") == Found
    assert (
        genfixes.bad_cite_parameters(
            r"now {{cite arxiv|vauthors=0|mode=cs2|page=0|collaboration=0}} was"
        )
        == Found
    )
    Found[15] = 6
    Found[36] = 4
    assert (
        genfixes.bad_cite_parameters(r"now {{cite web|foodoo=bar|date=2009|bert= false}} was")
        == Found
    )
    Found.clear()
    Found[14] = 11
    assert genfixes.bad_cite_parameters(r"now {{cite web|title-bar|url=foo}}") == Found
    Found.clear()
    Found[24] = 6
    assert genfixes.bad_cite_parameters(r"now {{cite web|title=bar|bee |url=foo}}") == Found
    Found.clear()
    Found[29] = 6
    assert genfixes.bad_cite_parameters(r"now {{cite web|title=bar{{a}}|bee |url=foo}}") == Found
    Found.clear()
    Found[30] = 28
    assert (
        genfixes.bad_cite_parameters(
            r"now {{cite web|title=bar |url=http://www.foo.com/bar text/}}"
        )
        == Found
    ), r"Reports URLs with spaces"
    Found.clear()
    assert (
        genfixes.bad_cite_parameters(
            r"now {{cite web|title=bar |url=http://www.foo.com/bar <!--text comm-->}}"
        )
        == Found
    ), r"Ignores comments with spaces in URLs"
    Found.clear()
    Found[34] = 3
    assert genfixes.bad_cite_parameters(r"now {{cite web|title=bar bee |url=f a}}") == Found
    Found.clear()
    Found[30] = 3
    assert genfixes.bad_cite_parameters(r"now {{cite web|title=f a |url=f a}}") == Found, (
        r"reports position of url not title if have same value"
    )


def test_add_missing_reflist() -> None:
    S = W.for_site(EN)
    SingleRef = r"now <ref>foo</ref>"
    Cat = "\r\n[[Category:Here]]"
    ExtLinks = "==External links==\r\n*[http://www.site.com hello]"
    assert (
        genfixes.add_missing_reflist(SingleRef + Cat)
        == SingleRef + "\r\n\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + Cat
    )
    assert (
        genfixes.add_missing_reflist(Cat + SingleRef)
        == SingleRef + "\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + Cat
    )
    References = "==References==\r\n{{portal|foo}}"
    assert (
        genfixes.add_missing_reflist(SingleRef + "\r\n" + References + Cat)
        == SingleRef + "\r\n" + "==References==\r\n{{Reflist}}\r\n{{portal|foo}}" + Cat
    )
    assert (
        genfixes.add_missing_reflist(SingleRef + "\r\n" + ExtLinks)
        == SingleRef + "\r\n\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + ExtLinks
    )
    assert (
        genfixes.add_missing_reflist(SingleRef + "\r\n" + "==References==\r\n{{Reflist}}" + Cat)
        == SingleRef + "\r\n" + "==References==\r\n{{Reflist}}" + Cat
    )
    Tracklist = "\r\n{{tracklist\r\n| foo = bar\r\n| foo2\r\n}}"
    assert (
        genfixes.add_missing_reflist(SingleRef + Tracklist + Cat)
        == SingleRef + Tracklist + "\r\n\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + Cat
    )
    SEnd = "\r\n{{s-end}}"
    assert (
        genfixes.add_missing_reflist(SingleRef + SEnd + Cat)
        == SingleRef + SEnd + "\r\n\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + Cat
    )
    missingSlash = "Foo <ref>a</ref>\r\n==References==\r\n<references>"
    assert genfixes.add_missing_reflist(missingSlash) == missingSlash.replace(r"s>", r"s/>")
    assert genfixes.add_missing_reflist(
        missingSlash.replace(r"s>", r"s  >")
    ) == missingSlash.replace(r"s>", r"s/>"), r"allows whitespace around <references>"
    missingSlash2 = "Foo <ref>a</ref>\r\n==References==\r\n<References>"
    assert genfixes.add_missing_reflist(missingSlash2) == missingSlash.replace(r"s>", r"s/>")
    LDR = "Foo <ref name='ab'/>\r\n==References==\r\n<references>\r\n<ref name='ab'>abc</ref>\r\n</references>"
    assert genfixes.add_missing_reflist(LDR) == LDR
    assert (
        genfixes.add_missing_reflist(SingleRef)
        == SingleRef + "\r\n\r\n" + "==References==\r\n{{Reflist}}"
    )


def test_add_missing_reflist_en_only() -> None:
    S = W.for_site(EN)
    SingleRef = r"now <ref>foo</ref>"
    Cat = "\r\n[[Category:Here]]"
    assert (
        genfixes.add_missing_reflist(SingleRef + Cat)
        == SingleRef + "\r\n\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + Cat
    ), r"add references sections above categories"
    S = set_lang(r"fr")
    assert genfixes.add_missing_reflist(SingleRef + Cat) == SingleRef + Cat, (
        r"do nothing in non-en sites"
    )
    S = set_lang(r"en")
    assert (
        genfixes.add_missing_reflist(SingleRef + Cat)
        == SingleRef + "\r\n\r\n" + "==References==\r\n{{Reflist}}" + "\r\n" + Cat
    )


def test_refs_after_punctuation() -> None:
    S = W.for_site(EN)
    AllAfter = r"Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The next"
    R1 = r"Foo<ref>bar</ref>. The next"
    ellipsis = r"Foo now<ref>abc</ref> ... was this."
    assert genfixes.refs_after_punctuation(AllAfter.replace(r".<", r"..<")) == AllAfter, (
        r"duplicate punctuation removed"
    )
    assert genfixes.refs_after_punctuation(AllAfter.replace(r".<", r"...<")) == AllAfter.replace(
        r".<", r"...<"
    ), r"ellipsis punctuation NOT changed"
    assert genfixes.refs_after_punctuation(ellipsis + AllAfter) == ellipsis + AllAfter
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo.<ref>bar</ref> The next"
    ), r"ref moved after punctuation when majority are after"
    assert (
        genfixes.refs_after_punctuation(AllAfter + "Foo<ref>ba\r\nr</ref>. The next")
        == AllAfter + "Foo.<ref>ba\r\nr</ref> The next"
    ), r"ref moved after punctuation when majority are after"
    R1 = R1.replace(r"Foo", r"Foo ")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo.<ref>bar</ref> The next"
    ), r"Whitespace before ref cleaned when punctuation moved"
    R1 = R1.replace(r".", r",")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo,<ref>bar</ref> The next"
    ), r"handles commas too"
    assert (
        genfixes.refs_after_punctuation(AllAfter + AllAfter + R1 + R1)
        == AllAfter + AllAfter + r"Foo,<ref>bar</ref> The next" + r"Foo,<ref>bar</ref> The next"
    ), r"multiple conversions"
    R1 = R1.replace(r",", r":")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo:<ref>bar</ref> The next"
    ), r"handles colons too"
    R1 = R1.replace(r":", r"?")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo?<ref>bar</ref> The next"
    ), r"handles question mark"
    R1 = R1.replace(r"?", r"!")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo!<ref>bar</ref> The next"
    ), r"handles exclamation mark"
    R1 = R1.replace(r"!", r"–")
    assert genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + R1, (
        r"ref not moved when before dash"
    )
    TwoRefs = r"Now<ref name=a>bar</ref><ref name=b>bar</ref>. Then"
    assert (
        genfixes.refs_after_punctuation(AllAfter + TwoRefs)
        == AllAfter + r"Now.<ref name=a>bar</ref><ref name=b>bar</ref> Then"
    ), r"punctuation moved through multiple refs"
    R1 = "Foo<ref>bar</ref>.\r\nThe next"
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1)
        == AllAfter + "Foo.<ref>bar</ref>\r\nThe next"
    ), r"doesn't eat newlines after ref punctuation"
    RandomTable = "{|\r\n!title\r\n!<ref>bar</ref>\r\n|}"
    assert genfixes.refs_after_punctuation(RandomTable) == RandomTable, (
        r"does not affect wikitables"
    )
    Multiple = r"works<ref>{{cite book |last=McDonald }}</ref>,<ref>{{cite book |last=Gingrich }}</ref>,<ref>{{cite book |location=Norwalk, CT }}</ref>,<ref name=HerdFly/>"
    assert (
        genfixes.refs_after_punctuation(Multiple)
        == r"works,<ref>{{cite book |last=McDonald }}</ref><ref>{{cite book |last=Gingrich }}</ref><ref>{{cite book |location=Norwalk, CT }}</ref><ref name=HerdFly/>"
    )
    assert (
        genfixes.refs_after_punctuation(r"thing.{{sfn|Jones|2000}}.<ref>foo</ref>")
        == r"thing.{{sfn|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{sfn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{sfn|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{sfn|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{sfn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing{{sfn|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{sfn|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{sfn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing<ref>foo</ref>{{sfn|Jones|2000}}.")
        == r"thing.<ref>foo</ref>{{sfn|Jones|2000}}"
    ), r"Handles {{sfn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{sfnp|Jones|2000}}.<ref>foo</ref>")
        == r"thing.{{sfnp|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{sfnp}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{sfnp|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{sfnp|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{sfnp}}"
    assert (
        genfixes.refs_after_punctuation(r"thing{{sfnp|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{sfnp|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{sfnp}}"
    assert (
        genfixes.refs_after_punctuation(r"thing<ref>foo</ref>{{sfnp|Jones|2000}}.")
        == r"thing.<ref>foo</ref>{{sfnp|Jones|2000}}"
    ), r"Handles {{sfnp}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{efn|Jones|2000}}.<ref>foo</ref>")
        == r"thing.{{efn|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{efn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{efn|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{efn|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{efn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing{{efn|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{efn|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{efn}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{better source|Jones|2000}}.<ref>foo</ref>")
        == r"thing.{{better source|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{better source}}"
    assert (
        genfixes.refs_after_punctuation(r"thing.{{better source|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{better source|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{better source}}"
    assert (
        genfixes.refs_after_punctuation(r"thing{{better source|Jones|2000}}<ref>foo</ref>.")
        == r"thing.{{better source|Jones|2000}}<ref>foo</ref>"
    ), r"Handles {{better source}}"
    assert (
        genfixes.refs_after_punctuation(r"thing<ref>foo</ref>{{better source|Jones|2000}}.")
        == r"thing.<ref>foo</ref>{{better source|Jones|2000}}"
    ), r"Handles {{better source}}"
    assert (
        genfixes.refs_after_punctuation(
            r"Start,{{sfn|S|1983|p=4}}{{sfn|H|1984|p=5}}{{sfn|M|1984|p=9}}, though."
        )
        == r"Start,{{sfn|S|1983|p=4}}{{sfn|H|1984|p=5}}{{sfn|M|1984|p=9}} though."
    )
    assert (
        genfixes.refs_after_punctuation(r"thing{{sfn|Jones|2000}}<ref>foo</ref>{{rp|18}}.")
        == r"thing.{{sfn|Jones|2000}}<ref>foo</ref>{{rp|18}}"
    ), r"Handles {{sfn}} and {{rp}}"
    assert (
        genfixes.refs_after_punctuation(r"thing<ref>foo</ref>{{rp|18}}{{sfn|Jones|2000}}.")
        == r"thing.<ref>foo</ref>{{rp|18}}{{sfn|Jones|2000}}"
    ), r"Handles {{sfn}} and {{rp}}"
    Excl = r"Foo!!<ref>bar</ref>"
    assert genfixes.refs_after_punctuation(Excl) == Excl, (
        r"No change to !! before ref, can be within table"
    )
    Excl = r"Foo{{efn|Jones}}!!"
    assert genfixes.refs_after_punctuation(Excl) == Excl, (
        r"No change to !! after {{efn}}, can be within table"
    )
    assert (
        genfixes.refs_after_punctuation(r"Foo<ref>something</ref>: Bar")
        == r"Foo:<ref>something</ref> Bar"
    ), r"colon as punctuation"
    assert (
        genfixes.refs_after_punctuation(r";Foo<ref>something</ref>: Bar")
        == r";Foo<ref>something</ref>: Bar"
    ), r"no changes, colon is not a punctuation"
    assert (
        genfixes.refs_after_punctuation(r"Sometimes; Foo<ref>something</ref>: Bar")
        == r"Sometimes; Foo:<ref>something</ref> Bar"
    ), r"colon as punctuation"


def test_refs_after_punctuation_sfn_in_ref() -> None:
    S = W.for_site(EN)
    Correct = r"Now.<ref>{{sfn|Wilcox|2017}}; {{harvnb|Anon.|2007a|p=378}}</ref>"
    assert genfixes.refs_after_punctuation(Correct) == Correct, (
        r"No chnage to punct after {{sfn}} etc. when within ref"
    )
    x = r" thing.{{sfn|Jones|2000}}.<ref>foo</ref>"
    assert genfixes.refs_after_punctuation(Correct + x) == Correct + x, (
        r"No change to punctuation around {{sfn}} if also punctuation after {{sfn}} in ref tags"
    )


def test_refs_after_punctuation_specific_languages() -> None:
    S = W.for_site(EN)
    AllAfter = r"Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The next Foo.<ref>bar</ref> The next"
    R1 = r"Foo<ref>bar</ref>. The next"
    S = set_lang(r"fr")
    assert genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + R1, (
        r"No change: disallowed language"
    )
    S = set_lang(r"ar")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo.<ref>bar</ref> The next"
    ), r"ref moved after reflist when majority are after"
    S = set_lang(r"en")
    assert (
        genfixes.refs_after_punctuation(AllAfter + R1) == AllAfter + r"Foo.<ref>bar</ref> The next"
    ), r"ref moved after reflist when majority are after"
