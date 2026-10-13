"""Port of AWB UnitTests/TaggerTests.cs: maintenance tagging, tag dates, redirect tagging.

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
from awb_x.core.article import Article  # noqa: E402

Uncat = r"{{Uncategorized|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
UncatStub = r"{{Uncategorized stub|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
Orphan = r"{{orphan|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
Wikify = r"{{Wikify|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
Deadend = r"{{Deadend|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
Stub = r"{{stub}}"
ShortText = r"Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sit amet tortor nec neque faucibus pharetra. Fusce lorem arcu, tempus et, imperdiet a, commodo a, pede. Nulla sit amet turpis gravida elit dictum cursus. Praesent tincidunt velit eu urna."
LongText = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Suspendisse dictum ultrices augue. Fusce sem diam, vestibulum sit amet, vehicula id, congue a, nisl. Phasellus pulvinar posuere purus. Donec elementum justo mattis nulla. Sed a purus dictum lacus pharetra adipiscing. Nam non dui non ante viverra iaculis. Fusce euismod lacus id nulla vulputate gravida. Suspendisse lectus pede, tempus sed, tristique id, pharetra eget, urna. Integer mattis libero vel quam accumsan suscipit. Vivamus molestie dapibus est. Quisque quis metus eget nisl accumsan aliquet. Donec tempus pellentesque tellus. Aliquam lacinia gravida justo. Aliquam erat volutpat. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Mauris ultricies suscipit urna. Ut mollis tempor leo. Pellentesque fringilla mattis enim. Proin sapien enim, congue non, aliquet et, sollicitudin nec, mauris. Sed porta.\r\n\r\nCurabitur luctus mollis massa. Nullam consectetur mollis lacus. Suspendisse turpis. Fusce velit. Morbi egestas dui. Donec commodo ornare lorem. Vestibulum sodales. Curabitur egestas libero ut metus. Sed eget orci a ligula consectetur vestibulum. Cras sapien.\r\n\r\nSed libero. Ut volutpat massa. Donec nulla pede, porttitor eu, sodales et, consectetur nec, quam. Pellentesque vestibulum hendrerit est. Nulla facilisi. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Duis et nibh eu lacus iaculis pretium. Fusce sed turpis. In cursus. Etiam interdum augue. Morbi commodo auctor ligula. In imperdiet, neque nec hendrerit consequat, lacus purus tristique turpis, eu hendrerit ipsum ligula at libero. Duis varius nunc vel tortor. Praesent tempor. Nunc non pede at velit congue feugiat. Curabitur gravida, nisl quis mattis porttitor, purus nulla viverra dui, non suscipit augue nunc ac libero. Donec lacinia est non augue.\r\n\r\nNulla quam dui, tristique id, condimentum sed, sodales in, ante. Vestibulum vitae diam. Integer placerat ante non orci. Nulla gravida. Integer magna enim, iaculis ut, ornare dignissim, ultrices a, urna. Donec urna. Fusce fringilla, pede vitae pulvinar ullamcorper, est nisi eleifend ipsum, ac adipiscing odio massa vehicula neque. Sed blandit est. Morbi faucibus, nisl vel commodo vulputate, mi ipsum tincidunt sem, id ornare orci orci et velit. Morbi commodo sollicitudin ligula. Pellentesque vitae urna. Duis massa arcu, accumsan id, euismod eu, tincidunt et, odio. Phasellus purus leo, rhoncus sed, condimentum nec, vestibulum vel, lacus. In egestas, lectus vitae lacinia tristique, elit magna consequat risus, id sodales metus nulla ac pede. Suspendisse potenti.\r\n\r\nFusce massa. Nullam lacinia purus nec ipsum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Suspendisse potenti. Proin augue. Donec mi magna, interdum a, elementum quis, bibendum sit amet, felis. Donec vel libero eget magna hendrerit ultrices. Suspendisse potenti. Sed scelerisque lacinia nisi. Quisque elementum, nunc nec luctus iaculis, ante quam aliquet orci, et ullamcorper dui ipsum at mi. Vestibulum a dolor id tortor posuere elementum. Sed mauris nisl, ultrices a, malesuada non, convallis ac, velit. Sed aliquam elit id metus. Donec malesuada, lorem ut pharetra auctor, mi risus viverra enim, vitae pulvinar urna metus at lorem. Vivamus id lorem. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Nulla facilisi. Ut vel odio. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Pellentesque lobortis sem.\r\n\r\nProin in odio. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Vivamus bibendum arcu nec risus. Nulla iaculis ligula in purus. Etiam vulputate nibh sit amet lectus. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Suspendisse potenti. Suspendisse eleifend. Donec blandit nibh hendrerit turpis. Integer accumsan posuere odio. Ut commodo augue malesuada risus. Curabitur augue. Praesent volutpat nunc a diam. Nulla lobortis interdum dolor. Nunc imperdiet, ipsum ac tempor iaculis, nunc.\r\n"
ShortTextWithLongComment = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur sit amet tortor nec neque faucibus pharetra. Fusce lorem arcu, tempus et, imperdiet a, commodo a, pede. Nulla sit amet turpis gravida elit dictum cursus. Praesent tincidunt velit eu urna.\r\n\r\n<!--Curabitur luctus mollis massa. Nullam consectetur mollis lacus. Suspendisse turpis. Fusce velit. Morbi egestas dui. Donec commodo ornare lorem. Vestibulum sodales. Curabitur egestas libero ut metus. Sed eget orci a ligula consectetur vestibulum. Cras sapien.\r\n\r\nSed libero. Ut volutpat massa. Donec nulla pede, porttitor eu, sodales et, consectetur nec, quam. Pellentesque vestibulum hendrerit est. Nulla facilisi. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Duis et nibh eu lacus iaculis pretium. Fusce sed turpis. In cursus. Etiam interdum augue. Morbi commodo auctor ligula. In imperdiet, neque nec hendrerit consequat, lacus purus tristique turpis, eu hendrerit ipsum ligula at libero. Duis varius nunc vel tortor. Praesent tempor. Nunc non pede at velit congue feugiat. Curabitur gravida, nisl quis mattis porttitor, purus nulla viverra dui, non suscipit augue nunc ac libero. Donec lacinia est non augue.\r\n\r\nNulla quam dui, tristique id, condimentum sed, sodales in, ante. Vestibulum vitae diam. Integer placerat ante non orci. Nulla gravida. Integer magna enim, iaculis ut, ornare dignissim, ultrices a, urna. Donec urna. Fusce fringilla, pede vitae pulvinar ullamcorper, est nisi eleifend ipsum, ac adipiscing odio massa vehicula neque. Sed blandit est. Morbi faucibus, nisl vel commodo vulputate, mi ipsum tincidunt sem, id ornare orci orci et velit. Morbi commodo sollicitudin ligula. Pellentesque vitae urna. Duis massa arcu, accumsan id, euismod eu, tincidunt et, odio. Phasellus purus leo, rhoncus sed, condimentum nec, vestibulum vel, lacus. In egestas, lectus vitae lacinia tristique, elit magna consequat risus, id sodales metus nulla ac pede. Suspendisse potenti.\r\n\r\nFusce massa. Nullam lacinia purus nec ipsum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Suspendisse potenti. Proin augue. Donec mi magna, interdum a, elementum quis, bibendum sit amet, felis. Donec vel libero eget magna hendrerit ultrices. Suspendisse potenti. Sed scelerisque lacinia nisi. Quisque elementum, nunc nec luctus iaculis, ante quam aliquet orci, et ullamcorper dui ipsum at mi. Vestibulum a dolor id tortor posuere elementum. Sed mauris nisl, ultrices a, malesuada non, convallis ac, velit. Sed aliquam elit id metus. Donec malesuada, lorem ut pharetra auctor, mi risus viverra enim, vitae pulvinar urna metus at lorem. Vivamus id lorem. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Nulla facilisi. Ut vel odio. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Pellentesque lobortis sem.\r\n\r\nProin in odio. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Vivamus bibendum arcu nec risus. Nulla iaculis ligula in purus. Etiam vulputate nibh sit amet lectus. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Suspendisse potenti. Suspendisse eleifend. Donec blandit nibh hendrerit turpis. Integer accumsan posuere odio. Ut commodo augue malesuada risus. Curabitur augue. Praesent volutpat nunc a diam. Nulla lobortis interdum dolor. Nunc imperdiet, ipsum ac tempor iaculis, nunc.-->\r\n"
ShortTextWithSingleLink = "'''KH Fakhruddin''' is regarded as a [[National Hero of Indonesia]].<ref>{{Cite book|last=Mirnawati|title=Kumpulan Pahlawan Indonesia Terlengkap|trans_title=Most Complete Collection of Indonesian Heroes|language=Indonesian|date=2012|location=Jakarta|publisher=CIF|isbn=978-979-788-343-0}}</ref>\r\n\r\n==References==\r\n{{Reflist}}\r\n\r\n{{National Heroes of Indonesia}}\r\n\r\n<!-- comments do not affect page length and therefore do not affect page tagging as well -->"


def test_add_uncat_to_stub() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text), r"page is deadend"
    assert r"Underlinked" not in text
    assert S.Stub.is_match(text), r"page is stub"
    assert S.Uncategorized.is_match(text), r"page is uncategorised"
    unit_test.int_value = 0
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(LongText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert not (S.Stub.is_match(text))
    assert S.Uncategorized.is_match(text)
    assert UncatStub not in text
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{uncat}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"uncat page and orphan"
    assert S.DeadEnd.is_match(text), r"uncat page and deadend"
    assert S.Stub.is_match(text)
    assert tools.nested_template_regex(r"uncat").is_match(text)
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{uncat}}", r"List of Tests", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert not (S.Stub.is_match(text))
    assert tools.nested_template_regex(r"uncat").is_match(text)
    assert not (tools.nested_template_regex(r"uncategorized stub").is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{uncat}}", r"Lists of Tests", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert not (S.Stub.is_match(text))
    assert tools.nested_template_regex(r"uncat").is_match(text)
    assert not (tools.nested_template_regex(r"uncategorized stub").is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                "one two three four five six seven eight nine ten {{Centuryinbox\r\n| in?=in poetry\r\n| cpa=19\r\n| cpb=th century\r\n| c=20th century\r\n| cn1=21st century\r\n}} eleven twelve",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"Tag for orphan"
    assert not (S.Wikify.is_match(text)), r"Don't tag for underlinked"
    assert not (S.DeadEnd.is_match(text)), r"Don't tag for deadend"
    assert S.Stub.is_match(text), r"Tag for stub"
    assert tools.nested_template_regex(r"uncategorized").is_match(text), r"Tag for uncat"
    text = (
        (_t := parser.tagger_no_change(r"A {{MinorPlanetListFooter|A}} B", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.DeadEnd.is_match(text)), r"Don't tag for deadend"


def test_rename_uncategorised() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r"{{stub}} {{Uncategorisedstub|date=May 2010}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (tools.nested_template_regex(r"Uncategorized stub").is_match(text)), (
        r"uncatstub not renamed when already present"
    )
    assert S.Stub.is_match(text)
    text = (
        (
            _t := parser.tagger_no_change(
                LongText + r"{{Uncategorised|date=May 2010}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (tools.nested_template_regex(r"Uncategorized stub").is_match(text)), (
        r"uncategorized not renamed when not stub"
    )
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                LongText + r"{{stub}} {{Uncategorised|date=May 2010}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert tools.nested_template_regex(r"Uncategorised").is_match(text), (
        r"Uncategorised not renamed when stub removed"
    )
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText
                + r"{{stub}} {{Uncategorized stub|date=May 2010}} {{Uncategorised|date=May 2010}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert tools.nested_template_regex(r"Uncategorized stub").is_match(text), r"Uncat stub retained"
    assert not (tools.nested_template_regex(r"Uncategorised").is_match(text)), (
        r"Uncategorised removed when already uncat stub"
    )
    assert S.Stub.is_match(text)
    text = (
        (
            _t := parser.tagger_no_change(
                LongText
                + r"{{stub}} {{Uncategorized stub|date=May 2010}} {{Uncategorised|date=May 2010}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert tools.nested_template_regex(r"Uncategorised").is_match(text), (
        r"Uncategorised not renamed when stub removed"
    )
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{wikify}}" + DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{wikify|reason=something}}" + DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"),
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Wikify.is_match(text), r"wikify tag with reason NOT removed"
    unit_test.int_value = 4
    text = (
        (_t := parser.tagger_no_change(r"{{uncategorised}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{uncategorised|date=January 2009}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{uncategorised|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{uncategorised|date=January 2009}} {{foo}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text)), r"Uncat removed even if other template present"
    unit_test.int_value = 0
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText
                + "{{dead end}}\r\n{{reflist}}\r\n{{Uncategorised|date=May 2010}}{{stub}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Uncategorised|date=May 2010}}" in text


def test_rename_unreferenced() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = False
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r"{{unreferenced|date=May 2010}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"unreferenced" in text, r"Unref when no refs"
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r"{{unreferenced|date=May 2010}} <!--<ref>foo</ref>-->", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"unreferenced" in text, r"Unref when no refs 2"
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r"{{unreferenced|date=May 2010}} <ref>foo</ref>", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (W.Unreferenced.is_match(text)), r"Unref to more citations needed when no refs 3"
    assert r"more citations needed" in text, r"Unref when no refs 4"
    assert (
        tools.get_template_parameter_value(
            tools.nested_template_regex(r"more citations needed").match(text).value, r"date"
        )
        == r"{{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
    ), r"Date updated on change of template name"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{Multiple issues|{{COI|date= February 2009}}{{unreferenced|date= April 2007}}}} <ref>foo</ref>",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (W.Unreferenced.is_match(text)), r"Unref to refimprove when has refs"
    assert r"more citations needed" in text, (
        r"Renames unreferenced to more citations needed in MI when existing refs"
    )
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r"{{unreferenced|date=May 2010}} <ref group=X>foo</ref>", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert W.Unreferenced.is_match(text), r"Unref remains when only grouped footnote refs"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{Multiple issues|{{COI|date= February 2009}}{{unreferenced|date= April 2007}}}} {{sfn|Smith|2004}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (W.Unreferenced.is_match(text)), r"Unref to refimprove when has sfn refs"
    assert r"more citations needed" in W.MultipleIssues.match(text).value, (
        r"Renames unreferenced to more citations needed in MIwhen existing refs"
    )
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{Multiple issues|{{COI|date= February 2009}}{{unreferenced|date= April 2007}}}} {{efn|A clarification.<ref name=Smith2009/>}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (W.Unreferenced.is_match(text)), r"Unref to more citations needed when has efn refs"
    assert r"more citations needed" in W.MultipleIssues.match(text).value, (
        r"Renames unreferenced to more citations needed in MI when existing refs"
    )
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText
                + r"{{unreferenced|date=May 2010}} {{more citations needed|date=May 2010}} <ref>foo</ref>",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (W.Unreferenced.is_match(text)), r"Unref removed when more citations needed"
    assert len(tools.nested_template_regex(r"more citations needed").matches(text)) == 1
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText
                + "==Sec==\r\n{{unreferenced|section=yes|date=May 2010}} {{more citations needed|date=May 2010}} <ref>foo</ref>",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert W.Unreferenced.is_match(text), r"Unref retained when section template"
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText
                + r"{{BLP unsourced|date=May 2010}} {{BLP sources|date=May 2010}} <ref>foo</ref>",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert len(tools.nested_template_regex(r"BLP unsourced").matches(text)) == 0
    assert len(tools.nested_template_regex(r"BLP sources").matches(text)) == 1
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r"{{BLP unsourced|date=May 2010}} <ref>foo</ref>", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert len(tools.nested_template_regex(r"BLP unsourced").matches(text)) == 0
    assert len(tools.nested_template_regex(r"BLP sources").matches(text)) == 1
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText
                + "{{multiple issues|\r\n{{unreferenced|date=May 2010}}\r\n{{more citations needed|date=May 2010}}\r\n}} <ref>foo[[bar]]</ref>",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (W.Unreferenced.is_match(text)), r"Unref removed when refimprove"
    assert len(tools.nested_template_regex(r"more citations needed").matches(text)) == 1
    assert len(tools.nested_template_regex(r"multiple issues").matches(text)) == 0, (
        r"Multiple issues removed if unref removed ant MI no longer needed"
    )


def test_add_dead_end() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{Underlinked}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"Underlinked" not in text, r"underlinked removed when dead end"
    assert S.DeadEnd.is_match(text), r"page is deadend"
    assert r"removed underlinked" in summary
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{shipindex}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.DeadEnd.is_match(text)), r"SIA page not tagged as deadend"


def test_add_multiple_tags_wihtespace() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert (
        "{{Dead end|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n{{Orphan|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
        in text
    ), r"No excess blank line between multiple tags"


def test_add() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert r"Underlinked" not in text
    assert S.DeadEnd.is_match(text), r"page is deadend"
    assert S.Stub.is_match(text), r"page is stub"
    assert tools.nested_template_regex(r"Uncategorized").is_match(text), r"page is uncategorised"
    text = (
        (_t := parser.tagger_no_change(ShortTextWithLongComment, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert S.Stub.is_match(text)
    assert tools.nested_template_regex(r"Uncategorized").is_match(text)
    text = (
        (_t := parser.tagger_no_change(ShortTextWithLongComment, r"List of Tests", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert not (S.Stub.is_match(text))
    assert not (tools.nested_template_regex(r"Uncategorized stub").is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                ShortTextWithLongComment, r"Meanings of minor planet names: 3001–4000", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert not (S.DeadEnd.is_match(text)), r"page is not dead end"
    assert not (S.Stub.is_match(text)), r"page is not stub"
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + Stub + Uncat + Wikify + Orphan + Deadend, r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert tools.regex_match_count(rx.escape(Stub), text) == 1
    assert tools.regex_match_count(rx.escape(Wikify), text) == 1
    assert tools.regex_match_count(rx.escape(Orphan), text) == 1
    assert tools.regex_match_count(rx.escape(Deadend), text) == 1
    text = (
        (_t := parser.tagger_no_change(ShortText + Stub, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert UncatStub not in text
    assert S.Stub.is_match(text)
    assert Uncat in text
    assert tools.regex_match_count(rx.escape(Stub), text) == 1
    text = (
        (_t := parser.tagger_no_change(ShortText + ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert S.Uncategorized.is_match(text)
    assert UncatStub not in text
    assert not (S.Stub.is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Main Page", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert ShortText == text, r"nothing changed"
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + ShortText + r"{{improve categories}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Uncategorized.is_match(text)
    assert not (tools.nested_template_regex(r"improve categories").is_match(text))
    unit_test.int_value = 3
    text = (
        (_t := parser.tagger_no_change(Deadend + ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert not (S.Uncategorized.is_match(text))
    unit_test.int_value = 5
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert S.Stub.is_match(text)
    assert UncatStub not in text
    assert not (S.Uncategorized.is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText + ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert S.DeadEnd.is_match(text)
    assert not (S.Stub.is_match(text))
    assert UncatStub not in text
    assert not (S.Uncategorized.is_match(text))
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert S.DeadEnd.is_match(text)
    assert S.Stub.is_match(text)
    assert not (S.Orphan.is_match(text))
    assert UncatStub not in text
    assert not (S.Uncategorized.is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText + ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert S.DeadEnd.is_match(text)
    assert not (S.Stub.is_match(text))
    assert not (S.Orphan.is_match(text))
    assert UncatStub not in text
    assert not (S.Uncategorized.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText.replace(r"consectetur", r"[[consectetur]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Stub.is_match(text)
    assert not (S.Wikify.is_match(text))
    assert not (S.DeadEnd.is_match(text))
    assert not (S.Orphan.is_match(text))
    assert UncatStub not in text
    assert not (S.Uncategorized.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(ShortText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    assert not (S.Wikify.is_match(text))
    assert not (S.DeadEnd.is_match(text))
    assert not (S.Orphan.is_match(text))
    assert UncatStub not in text
    assert not (S.Uncategorized.is_match(text))
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(ShortText + r" {{hndis|Bar, Foo}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText + r" {{surname|Smith, John}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText + r" {{wikispecies redirect}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r" {{Events by year for decade|79}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + r" {{Events by year for decade BC|79}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    unit_test.int_value = 0
    text = (
        (_t := parser.tagger_no_change(r"{{improve categories}}\r\n" + ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Uncategorized.is_match(text)
    unit_test.int_value = 0
    text = (
        (_t := parser.tagger_no_change(ShortTextWithSingleLink, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Uncategorized.is_match(text), r"uncat"
    assert not (S.Stub.is_match(text)), r"Stub"
    assert not (S.Wikify.is_match(text)), r"underlinked"
    assert not (S.DeadEnd.is_match(text)), r"deadend"
    assert not (S.Orphan.is_match(text)), r"orphan"
    assert UncatStub not in text
    unit_test.int_value = 1
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + ShortText + r"[[Category:Living people]]", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.DeadEnd.is_match(text)
    assert not (S.Uncategorized.is_match(text))


def test_add_wikify() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    t1 = "'''Ae0bgz2CNta0Qib4dK3''' VcnyafUE0bqIUdr5e 9zggyDHmIye [[PoPUJrqLG 3a8vnqpgy]].<ref>EdOkQE5gA 7u9P9ZZtd dFw0g9Fsf 99924876231</ref>\r\n\r\n==References==\r\n{{Reflist}}\r\n\r\n{{DEFAULTSORT:bJqnzFm7e, opFhLKq7z}}\r\n[[Category:Albanian people]]\r\n[[Category:Albanian Declaration of Independence]]\r\n\r\n\r\n{{Albania-bio-stub}}"
    text = (
        (_t := parser.tagger_no_change(t1, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert S.Stub.is_match(text)
    t1 = "{{infobox something\r\n|param1=text long text\r\n|param2=text long text\r\n|param3=text long text\r\n|param4=text long text\r\n|param5=text long text\r\n}}\r\n'''Ae0bgz2CNta0Qib4dK3''' VcnyafUE0bqIUdr5e 9zggyDHmIye [[PoPUJrqLG 3a8vnqpgy]].<ref>EdOkQE5gA 7u9P9ZZtd dFw0g9Fsf 99924876231</ref>\r\n\r\n==References==\r\n{{Reflist}}\r\n\r\n{{DEFAULTSORT:bJqnzFm7e, opFhLKq7z}}\r\n[[Category:Albanian people]]\r\n[[Category:Albanian Declaration of Independence]]\r\n\r\n\r\n{{Albania-bio-stub}}"
    text = (
        (_t := parser.tagger_no_change(t1, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert S.Stub.is_match(text)


def test_add_underlinked() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 1
    unit_test.bool_value = False
    S = set_lang(r"simple")
    t1 = "{{temp}}'''Ae0bgz2CNta0Qib4dK3''' VcnyafUE0bqIUdr5e 9zggyDHmIye [[PoPUJrqLG 3a8vnqpgy]].<ref>EdOkQE5gA 7u9P9ZZtd dFw0g9Fsf 99924876231</ref>\r\n\r\n==References==\r\n{{Reflist}}\r\n\r\n{{DEFAULTSORT:bJqnzFm7e, opFhLKq7z}}"
    text = (
        (_t := parser.tagger_no_change(t1 + LongText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Wikify.is_match(text)
    assert text.startswith(
        "{{Underlinked|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n{{temp}}"
    ), r"no excess newlines on tag addition"
    t1 = "{{dead end}}{{temp}}'''Ae0bgz2CNta0Qib4dK3''' VcnyafUE0bqIUdr5e 9zggyDHmIye [[PoPUJrqLG 3a8vnqpgy]].<ref>EdOkQE5gA 7u9P9ZZtd dFw0g9Fsf 99924876231</ref>\r\n\r\n==References==\r\n{{Reflist}}\r\n\r\n{{DEFAULTSORT:bJqnzFm7e, opFhLKq7z}}"
    text = (
        (_t := parser.tagger_no_change(t1 + LongText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Wikify.is_match(text)
    assert text.startswith(
        "{{Underlinked|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n{{temp}}"
    ), r"no excess newlines on tag change"
    text = (
        (_t := parser.tagger_no_change(r"{{shipindex}}" + LongText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Underlinked|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in text, (
        r"SIA pages not tagged as underlinked"
    )
    text = (
        (_t := parser.tagger_no_change(r"{{disambiguation}} [[a]]" + LongText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Underlinked|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in text, (
        r"disambig pages with 1 link not tagged as underlinked"
    )
    S = set_lang(r"en")
    text = (
        (_t := parser.tagger_no_change(t1 + LongText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (
        text.startswith(
            "{{Underlinked|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n{{temp}}"
        )
    ), r"Don't add underlinked for en-wiki"


def test_add_sv() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    S = set_lang(r"sv")
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"orphan"
    assert S.Stub.is_match(text), r"stub"
    assert not (S.DeadEnd.is_match(text)), r"dead end"
    assert not (S.Wikify.is_match(text)), r"wikify"
    assert r"{{Wikify|" + S.DateYearMonthParameter + "}}\r\n\r\n" not in text
    assert tools.nested_template_regex(r"Okategoriserad").is_match(text)
    assert S.Stub.is_match(text)
    S = set_lang(r"en")


def test_add_dead_end_ar() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    S = set_lang(r"ar")
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.DeadEnd.is_match(text), r"page is deadend"
    assert text.startswith(
        "{{نهاية مسدودة|تاريخ={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n{{يتيمة|تاريخ={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n\r\nLorem ipsum"
    ), r"no blank line between dead end and orphan"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{وصلات قليلة}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.DeadEnd.is_match(text), r"page is deadend"
    assert not (S.Wikify.is_match(text)), r"wikify should not be present which dead end added"
    assert r"وصلات قليلة" not in text, r"wikify removed when dead end"
    assert r"وصلات قليلة" in summary
    S = set_lang(r"en")


def test_add_ar() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    S = set_lang(r"ar")
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"orphan"
    assert r"{{وصلات قليلة|" + S.DateYearMonthParameter + r"}}" not in text, r"wikify in Arabic"
    assert not (S.Wikify.is_match(text)), r"wikify"
    assert S.DeadEnd.is_match(text), r"dead end"
    assert tools.nested_template_regex(r"بذرة غير مصنفة").is_match(text), r"Uncategorized stub"
    assert r"Uncategorized" not in text, r"no en-wiki uncat tags"
    assert S.Stub.is_match(text), r" stub"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{يتيمة|" + S.DateYearMonthParameter + r"}}" not in text, r"orphan"
    assert not (S.Stub.is_match(text)), r"stub"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{توضيح}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{يتيمة|" + S.DateYearMonthParameter + r"}}" not in text, r"orphan"
    assert not (S.Stub.is_match(text)), r"stub"
    assert not (S.Wikify.is_match(text)), r"wikify"
    assert r"{{وصلات قليلة|" + S.DateYearMonthParameter + r"}}" not in text, r"wikify"
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText.replace(r"consectetur", r"[[consectetur]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Stub.is_match(text)
    assert not (S.Wikify.is_match(text)), r"wikify"
    assert not (S.DeadEnd.is_match(text)), r"deadend"
    assert S.Orphan.is_match(text), r"orphan"
    assert UncatStub not in text, r"english uncatstub"
    assert S.Uncategorized.is_match(text), r"uncat"
    text = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(ShortText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text)), r"stub"
    assert not (S.Wikify.is_match(text)), r"wikify"
    assert not (S.DeadEnd.is_match(text)), r"deadend"
    assert S.Orphan.is_match(text), r"orphan"
    assert UncatStub not in text, r"english uncatstub"
    assert S.Uncategorized.is_match(text), r"uncat"
    text = (
        (
            _t := parser.tagger_no_change(
                "{{نهاية مسدودة|تاريخ=نوفمبر 2013}}\r\n{{يتيمة|تاريخ=نوفمبر 2013}}\r\n\r\n[[link]]"
                + LongText,
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.DeadEnd.is_match(text)), r"deadend"
    assert S.Orphan.is_match(text), r"orphan"
    assert S.Wikify.is_match(text), r"wikify"
    assert r"}}" + "\r\n\r\n" + r"{{" not in text
    unit_test.bool_value = True
    text = (
        (
            _t := parser.tagger_no_change(
                ShortText + ShortText + ShortText + ShortText, r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"Uncategorized" not in text, r"no en-wiki uncat tags"
    S = set_lang(r"en")


def test_add_arz() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    S = set_lang(r"arz")
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{يتيمه|" + S.DateYearMonthParameter + r"}}" in text, r"orphan"
    assert tools.nested_template_regex(r"تقاوى مش متصنفه").is_match(text), r"Uncategorized stub"
    assert S.Stub.is_match(text), r"stub tag added"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{يتيمه|" + S.DateYearMonthParameter + r"}}" not in text, r"orphan not added"
    assert not (S.Stub.is_match(text)), r"stub tag not added"
    assert r"{{ويكى|" + S.DateYearMonthParameter + r"}}" not in text, r"wikify not added"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{توضيح}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{يتيمه|" + S.DateYearMonthParameter + r"}}" not in text, r"orphan not added"
    assert not (S.Stub.is_match(text)), r"stub not added"
    assert r"{{ويكى|" + S.DateYearMonthParameter + r"}}" not in text, r"wikify not added"
    S = set_lang(r"en")


def test_add_orphan() -> None:
    S = W.for_site(EN)
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{Widirect}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"pages using {{wi}} not tagged as orphan"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{List of lists}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"pages using {{List of lists}} not tagged as orphan"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{Wi}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"pages using {{wi}} not tagged as orphan"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{soft redirect}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"soft redirect not tagged as orphan"
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{Infobox foo bar|great=yes}}" + ShortText, r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{multiple issues|foo={{subst:CURRENTMONTH}} |orphan={{subst:FOOBAR}} }}"
                + ShortText,
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"tags with subst"
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(ShortText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))


def test_add_tags_wikia() -> None:
    S = W.for_site(EN)
    S = set_project(r"en", "wikia")
    unit_test.bool_value = True
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{Infobox foo bar|great=yes}}" + ShortText, r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text)), r"No orphan tag added on Wikia"
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{Underlinked}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.DeadEnd.is_match(text)), r"page is deadend"
    assert not (S.Uncategorized.is_match(text)), r"uncat"
    unit_test.bool_value = False
    S = set_project(r"en", "wikipedia")


def test_add_linkless_ru() -> None:
    S = W.for_site(EN)
    unit_test.int_value = 0
    unit_test.bool_value = True
    S = set_lang(r"ru")
    textIn = r"Foo bar {{rq|wikify|style}} here"
    textIn2 = r"Foo bar"
    text = (
        (_t := parser.tagger_no_change(textIn, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert r"{{rq|wikify|style|linkless}}" in text
    text = (
        (_t := parser.tagger_no_change(textIn.replace(r"}}", r"|linkless}}"), r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{rq|wikify|style|linkless}}" in text
    text = (
        (_t := parser.tagger_no_change(textIn2, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text)
    assert r"|linkless}}" not in text
    text = (
        (_t := parser.tagger_no_change(textIn + textIn, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text)
    assert r"|linkless}}" not in text
    S = set_lang(r"en")
    text = (
        (_t := parser.tagger_no_change(textIn, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"
    assert r"{{rq|wikify|style|linkless}}" not in text


def test_remove() -> None:
    S = W.for_site(EN)
    text = (
        (_t := parser.tagger_no_change(ShortText + Stub, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Stub.is_match(text)
    text = (
        (_t := parser.tagger_no_change(LongText + Stub, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{wikify}}" + DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    text1 = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    text2 = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]" + Stub), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert text1 == text, r"check whether wikify tag is removed properly"
    assert text2 == text1, r"check whether stub tag is removed properly"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{wikify|reason=something}}" + DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"),
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Wikify.is_match(text)
    unit_test.int_value = 4
    text = (
        (_t := parser.tagger_no_change(r"{{uncategorised}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{uncategorised|date=January 2009}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{uncategorised|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{uncategorised|date=January 2009}} {{foo}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Uncategorized.is_match(text)), r"Uncat removed even if other template present"


def test_remove_disambig() -> None:
    S = W.for_site(EN)
    unit_test.bool_value = False
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{disambig|date=September 2013}}{{disambig cleanup|date=September 2013}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert W.DisambigsCleanup.is_match(text), r"keeps disambig cleanup"
    assert not (W.DisambigsGeneral.is_match(text)), r"removes disambig"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{disambiguation|date=September 2013}}{{disambig cleanup|date=September 2013}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert W.DisambigsCleanup.is_match(text), r"keeps disambig cleanup"
    assert not (W.DisambigsGeneral.is_match(text)), r"removes disambig"
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{disambig cleanup|date=September 2013}}{{disambig|date=September 2013}}",
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert W.DisambigsCleanup.is_match(text), r"keeps disambig cleanup"
    assert not (W.DisambigsGeneral.is_match(text)), r"removes disambig"
    unit_test.bool_value = True


def test_remove_orphan() -> None:
    S = W.for_site(EN)
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change("{{orphan}}\r\n\r\n[[foo]]", r"List of Tests", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"[[foo]]"
    text = (
        (_t := parser.tagger_no_change(r"{{orphan|few=a}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text)
    text = (
        (
            _t := parser.tagger_no_change(
                "{{multiple issues|\r\n{{orphan}}\r\n}}[[foo]]", r"List of Tests", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert not (W.MultipleIssues.is_match(text))
    assert text == r"[[foo]]"
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Orphan.is_match(text), r"page is orphan"


def test_remove_orphan_ar() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ar")
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{يتيمة}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}[[foo]]{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"{{orphan}}[[foo]]{{disambig}}"
    text = (
        (_t := parser.tagger_no_change(r"{{يتيمة}}[[foo]]{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"[[foo]]{{disambig}}"
    unit_test.bool_value = True
    S = set_lang(r"en")


def test_remove_orphan_arz() -> None:
    S = W.for_site(EN)
    S = set_lang(r"arz")
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{يتيمه}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}[[foo]]{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"{{orphan}}[[foo]]{{disambig}}"
    text = (
        (_t := parser.tagger_no_change(r"{{يتيمه}}[[foo]]{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"[[foo]]{{disambig}}"
    unit_test.bool_value = True
    S = set_lang(r"en")


def test_remove_orphan_sv() -> None:
    S = W.for_site(EN)
    S = set_lang(r"sv")
    unit_test.bool_value = False
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{Föräldralös}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    text = (
        (_t := parser.tagger_no_change(r"{{orphan}}[[foo]]{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"{{orphan}}[[foo]]{{disambig}}"
    text = (
        (_t := parser.tagger_no_change(r"{{Föräldralös}}[[foo]]{{disambig}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Orphan.is_match(text))
    assert text == r"[[foo]]{{disambig}}"
    unit_test.bool_value = True
    S = set_lang(r"en")


def test_remove_ar() -> None:
    S = W.for_site(EN)
    text = r""
    S = set_lang(r"ar")
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{بذرة}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Stub.is_match(text)
    text = (
        (_t := parser.tagger_no_change(LongText + r"{{بذرة}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{وصلات قليلة}}" + DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"),
                r"Test",
                False,
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    text1 = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    text2 = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]") + r"{{بذرة}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert text2 == text1, r"check whether stub tag is removed properly"
    S = set_lang(r"en")


def test_remove_arz() -> None:
    S = W.for_site(EN)
    text = r""
    S = set_lang(r"arz")
    unit_test.bool_value = True
    text = (
        (_t := parser.tagger_no_change(ShortText + r"{{بذرة}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert S.Stub.is_match(text)
    text = (
        (_t := parser.tagger_no_change(LongText + r"{{بذرة}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Stub.is_match(text))
    text = (
        (
            _t := parser.tagger_no_change(
                r"{{ويكى}}" + DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    text1 = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]"), r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    text2 = (
        (
            _t := parser.tagger_no_change(
                DotNetRegex(r"(\w+)").replace(LongText, r"[[$1]]") + r"{{بذرة}}", r"Test", False
            )
        ),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert text2 == text1, r"check whether stub tag is removed properly"
    S = set_lang(r"en")


def test_multiple_issues_new_tags() -> None:
    S = W.for_site(EN)
    Text = LongText + r"{{Multiple issues | COI=May 2010 | POV=May 2010 }}"
    Text = (
        (_t := parser.tagger_no_change(Text, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(Text)), r"added tags go in existing multipleIssues"


def test_remove_dead_end() -> None:
    S = W.for_site(EN)
    assert not (
        S.DeadEnd.is_match(
            (
                (
                    _t := parser.tagger_no_change(
                        r"foo {{deadend|date=May 2010}} [[a]] and [[b]] and [[b]]", r"Test", False
                    )
                ),
                (noChange := _t[1]),
                (summary := _t[2]),
            )[0][0]
        )
    )
    assert r"removed deadend tag" in summary
    unit_test.bool_value = False
    assert (
        (
            (
                _t := parser.tagger_no_change(
                    "{{multiple issues|\r\n{{dead end|date=September 2012}}\r\n{{expert-subject|1=History|date=September 2012}}\r\n{{Unreferenced|date=December 2006}}\r\n}}\r\n\r\n''Now'' [[a]] and [[b]] and [[b]]",
                    r"Test",
                    False,
                )
            ),
            (noChange := _t[1]),
            (summary := _t[2]),
        )[0][0]
        == "{{multiple issues|\r\n{{expert-subject|1=History|date=September 2012}}\r\n{{Unreferenced|date=December 2006}}\r\n}}\r\n\r\n''Now'' [[a]] and [[b]] and [[b]]\r\n\r\n{{stub}}"
    )
    unit_test.bool_value = True
    assert r"removed deadend tag" in summary
    assert not (
        S.DeadEnd.is_match(
            (
                (
                    _t := parser.tagger_no_change(
                        r"foo {{Multiple issues|COI = May 2010 |POV = June 2010 | dead end=May 2010}} [[a]] and [[b]] and [[b]]",
                        r"Test",
                        False,
                    )
                ),
                (noChange := _t[1]),
                (summary := _t[2]),
            )[0][0]
        )
    )
    assert S.DeadEnd.is_match(
        (
            (
                _t := parser.tagger_no_change(
                    r"foo==x== {{deadend|section|date=May 2010}} [[a]] and [[b]] and [[b]]",
                    r"Test",
                    False,
                )
            ),
            (noChange := _t[1]),
            (summary := _t[2]),
        )[0][0]
    ), r"does not remove section tags"
    assert r"removed deadend tag" not in summary
    assert S.DeadEnd.is_match(
        (
            (
                _t := parser.tagger_no_change(
                    r"foo==x== {{deadend|date=May 2010}} {{Proposed deletion/dated|[[a]] and [[b]] and [[b]]}}",
                    r"Test",
                    False,
                )
            ),
            (noChange := _t[1]),
            (summary := _t[2]),
        )[0][0]
    ), r"does not remove {{dead end}} when links are within prod template"
    assert S.DeadEnd.is_match(
        (
            (
                _t := parser.tagger_no_change(
                    r"foo==x== {{deadend|date=May 2010}} {{Proposed deletion endorsed|[[a]] and [[b]] and [[b]]}}",
                    r"Test",
                    False,
                )
            ),
            (noChange := _t[1]),
            (summary := _t[2]),
        )[0][0]
    ), r"does not remove {{dead end}} when links are within prod template, 2"
    assert r"removed deadend tag" not in summary


def test_remove_dead_end_ar() -> None:
    S = W.for_site(EN)
    S = set_lang(r"ar")
    assert not (
        S.DeadEnd.is_match(
            (
                (
                    _t := parser.tagger_no_change(
                        r"foo {{نهاية مسدودة|تاريخ=ديسمبر 2012}} [[a]] and [[b]] and [[b]]",
                        r"Test",
                        False,
                    )
                ),
                (noChange := _t[1]),
                (summary := _t[2]),
            )[0][0]
        )
    )
    assert r"نهاية مسدودة" in summary
    assert not (
        S.DeadEnd.is_match(
            (
                (
                    _t := parser.tagger_no_change(
                        r"foo {{dead end|date=December 2012}} [[a]] and [[b]] and [[b]]",
                        r"Test",
                        False,
                    )
                ),
                (noChange := _t[1]),
                (summary := _t[2]),
            )[0][0]
        )
    )
    assert r"نهاية مسدودة" in summary
    S = set_lang(r"en")


def test_update_fact_tag() -> None:
    S = W.for_site(EN)
    S = set_site(dated_templates=())
    S = set_site(dated_templates=(*current_site().dated_templates, r"Fact"))
    text = (
        (_t := parser.tagger_no_change(r"{{fact}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{fact|date={{subst:CURRENTMONTHNAME}}" in text
    assert r"{{fact}}" not in text
    text = (
        (_t := parser.tagger_no_change(r"{{template:fact}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{fact|date={{subst:CURRENTMONTHNAME}}" in text
    assert r"{{fact}}" not in text
    text = (
        (_t := parser.tagger_no_change(r"{{fact|}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{fact|date={{subst:CURRENTMONTHNAME}}" in text
    assert r"{{fact}}" not in text


def test_update_citation_needed_tag() -> None:
    S = W.for_site(EN)
    unit_test.bool_value = False
    S = set_site(dated_templates=())
    S = set_site(dated_templates=(*current_site().dated_templates, r"Citation needed"))
    text = (
        (_t := parser.tagger_no_change(r"{{citation needed}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{citation needed|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text
    text = (
        (_t := parser.tagger_no_change(r"{{template:citation needed  }}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{citation needed  |date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text
    text = (
        (_t := parser.tagger_no_change(r"{{ citation needed}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{ citation needed|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text
    text = (
        (_t := parser.tagger_no_change(r"{{Citation needed}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Citation needed|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text
    text = (
        (_t := parser.tagger_no_change(r"{{citation needed|reason=something}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert (
        r"{{citation needed|reason=something|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
        in text
    )
    correctcn = r"{{citation needed|reason=something|date=May 2009}}"
    text = (
        (_t := parser.tagger_no_change(correctcn, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert correctcn in text
    commentText = r"<!--{{citation needed}}-->"
    text = (
        (_t := parser.tagger_no_change(commentText, r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert commentText in text, r"tag not dated when commented out"
    text = (
        (_t := parser.tagger_no_change(r"{{Citation needed|Date=May 2009}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Citation needed|date=May 2009}}" in text, r"Date -> date"
    text = (
        (_t := parser.tagger_no_change(r"{{Citation needed|date=May 2009}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Citation needed|date=May 2009}}" in text, r"if tag already dated, no change"


def test_update_wikify_tag() -> None:
    S = W.for_site(EN)
    S = set_site(dated_templates=())
    S = set_site(dated_templates=(*current_site().dated_templates, r"Wikify"))
    S = set_site(dated_templates=(*current_site().dated_templates, r"Wikify section"))
    correct = r"{{wikify|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    text = (
        (_t := parser.tagger_no_change(r"{{wikify}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert correct in text
    assert r"{{wikify}}" not in text
    text = (
        (_t := parser.tagger_no_change(r"{{template:wikify  }}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text
    text = (
        (_t := parser.tagger_no_change(r"{{wikify section}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{wikify section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text
    text = (
        (_t := parser.tagger_no_change(r"{{Wikify section}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert r"{{Wikify section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" in text


def test_tag_updater_add_date() -> None:
    S = W.for_site(EN)
    S = set_site(dated_templates=())
    S = set_site(dated_templates=(*current_site().dated_templates, r"Wikify"))
    correct = r"{{wikify|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    assert genfixes.tag_updater(r"{{wikify}}") == correct, r"tags undated tag"
    assert genfixes.tag_updater(r"{{wikify|date=}}") == correct, r"tags undated tag"
    assert genfixes.tag_updater(r"{{wikify|dates=}}") == correct, r"tags undated tag"
    assert genfixes.tag_updater(r"{{wikify|date}}") == correct, r"tags undated tag"
    assert genfixes.tag_updater(r"{{wikify|Date=}}") == correct, r"tags undated tag"
    assert genfixes.tag_updater(r"{{Template:wikify}}") == correct, (
        r"tags undated tag, removes template namespace"
    )
    assert genfixes.tag_updater(r"{{template:wikify}}") == correct, (
        r"tags undated tag, removes template namespace"
    )
    assert genfixes.tag_updater(r"{{Wikify}}") == correct.replace(r"wik", r"Wik"), (
        r"tags undated tag, keeping existing template case"
    )
    assert genfixes.tag_updater(r"{{wikify|Date=May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects Date --> date"
    )
    assert genfixes.tag_updater(r"{{wikify|Date-May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects date- --> date="
    )
    assert genfixes.tag_updater(r"{{wikify|date-=May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects date-= --> date="
    )
    assert genfixes.tag_updater(r"{{wikify|Date-=May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects date-= --> date="
    )
    assert genfixes.tag_updater(r"{{wikify|date-May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects date- --> date="
    )
    assert genfixes.tag_updater(r"{{wikify|May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects unnamed date parameter"
    )
    assert genfixes.tag_updater(r"{{wikify|May 2010 }}") == r"{{wikify|date=May 2010 }}", (
        r"corrects unnamed date parameter"
    )
    assert (
        genfixes.tag_updater(r"{{multiple issues {{wikify|May 2010 }} }}")
        == r"{{multiple issues {{wikify|date=May 2010 }} }}"
    ), r"corrects unnamed date parameter, nested template"
    assert (
        genfixes.tag_updater(r"{{wikify|section}}")
        == r"{{wikify|section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    ), r"supports templates with additional arguments"
    assert (
        genfixes.tag_updater(r"{{wikify|section|other={{foo}} bar}}")
        == r"{{wikify|section|other={{foo}} bar|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    ), r"supports templates with additional arguments"
    assert (
        genfixes.tag_updater(r"{{wikify|section|other={{foo}}}}")
        == r"{{wikify|section|other={{foo}}|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    ), r"supports templates with additional arguments"
    assert genfixes.tag_updater(r"{{wikify|date=May, 2010}}") == r"{{wikify|date=May 2010}}", (
        r"removes excess comma"
    )
    assert genfixes.tag_updater(r"{{wikify|date=May 2, 2010}}") == r"{{wikify|date=May 2, 2010}}", (
        r"American date not altered"
    )
    S = set_site(dated_templates=())
    S = set_site(dated_templates=(*current_site().dated_templates, r"Wikify"))
    assert genfixes.tag_updater(r"{{wikify}}") == correct, (
        r"first letter casing of template rule does not matter"
    )
    commentedOut = r"<!-- {{wikify}} -->"
    assert genfixes.tag_updater(commentedOut) == commentedOut, r"ignores commented out tags"
    S = set_site(dated_templates=(*current_site().dated_templates, r"Clarify"))
    nochange = r"{{Clarify|date=May 2014|reason=Use Template:Cite web or similar}}"
    assert genfixes.tag_updater(nochange) == nochange


def test_tag_updater_format_date() -> None:
    S = W.for_site(EN)
    S = set_site(dated_templates=(*current_site().dated_templates, r"Dead link"))
    S = set_site(dated_templates=(*current_site().dated_templates, r"Wikify"))
    assert (
        genfixes.tag_updater(
            r"<ref>{{cite web | title=foo| url=http://www.site.com }} {{dead link}}</ref>"
        )
        == r"<ref>{{cite web | title=foo| url=http://www.site.com }} {{dead link|date="
        + utc_month_year()
        + r"}}</ref>"
    )
    assert genfixes.tag_updater(r"{{wikify|date=may 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects lower case month name"
    )
    assert genfixes.tag_updater(r"{{wikify|date=May, 2010}}") == r"{{wikify|date=May 2010}}", (
        r"removes comma between month and year"
    )
    assert genfixes.tag_updater(r"{{wikify|date=11 May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"removes day in International date"
    )
    assert genfixes.tag_updater(r"{{wikify|date=07 May 2010}}") == r"{{wikify|date=May 2010}}", (
        r"removes day in International date"
    )
    assert genfixes.tag_updater(r"{{wikify|date=11 may 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects lower case month name, removes day in International date"
    )
    assert genfixes.tag_updater(r"{{wikify|date=2010-05-13}}") == r"{{wikify|date=May 2010}}", (
        r"corrects lower case month name"
    )
    assert genfixes.tag_updater(r"{{wikify|date=MAY 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects upper case month name"
    )
    assert genfixes.tag_updater(r"{{wikify|date=MAy 2010}}") == r"{{wikify|date=May 2010}}", (
        r"corrects mixed case month name"
    )
    subst = r"{{wikify|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}"
    assert genfixes.tag_updater(subst) == subst, r"no change when value is subst month/year"
    notSubst = r"{{wikify|date={{CURRENTMONTHNAME}} {{CURRENTYEAR}}}}"
    assert genfixes.tag_updater(notSubst) == notSubst, (
        r"no change when value is non-subst month/year keywords"
    )
    assert (
        genfixes.tag_updater(
            r"{{wikify|date=December 2024<!-- primarily from edits on 2024-03-21 by User: -->}}"
        )
        == r"{{wikify|date=December 2024<!-- primarily from edits on 2024-03-21 by User: -->}}"
    ), r"Handles comment"


def test_tag_updater_localize_date() -> None:
    S = W.for_site(EN)
    S = set_site(dated_templates=tuple(genfixes.load_dated_templates(r"{{tl|wikify}}")))
    S = set_lang(r"ar")
    assert genfixes.tag_updater(r"{{wikify|date=May 2010}}") == r"{{wikify|تاريخ=May 2010}}", (
        r"Renames date= when localized"
    )
    S = set_lang(r"en")
    assert genfixes.tag_updater(r"{{wikify|date=May 2010}}") == r"{{wikify|date=May 2010}}", r""


def test_general() -> None:
    S = W.for_site(EN)
    unit_test.bool_value = False
    assert (
        (_t := parser.tagger_no_change(r"#REDIRECT [[Test]]", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0] == r"#REDIRECT [[Test]]"
    assert noChange
    assert (
        (_t := parser.tagger_no_change(ShortText, r"Talk:Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0] == ShortText
    assert noChange
    text = (
        (_t := parser.tagger_no_change(r"{{Test Template}}", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (S.Wikify.is_match(text))
    assert S.DeadEnd.is_match(text)
    assert S.Stub.is_match(text)
    assert not (noChange)
    text = (
        (_t := parser.tagger_no_change(r"hello {{pt}} hello", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (noChange)
    text = (
        (_t := parser.tagger_no_change(r"hello {{Pt}} hello", r"Test", False)),
        (noChange := _t[1]),
        (summary := _t[2]),
    )[0][0]
    assert not (noChange)


def test_tagger_permitted() -> None:
    S = W.for_site(EN)
    assert genfixes.tagger_permitted(r"A", r"Wikipedia:AutoWikiBrowser/Sandbox")
    assert not (genfixes.tagger_permitted(r"A", r"Wikipedia:ABC"))
    assert not (genfixes.tagger_permitted(r"A {{wi}}", r"ABC"))
    assert not (genfixes.tagger_permitted(r"A", r"Main Page"))
    assert not (genfixes.tagger_permitted(r"#REDIRECT [[A]]", r"ABC"))
    assert not (genfixes.tagger_permitted(r"{{soft redirect}}", r"ABC"))
    S = set_lang(r"ar")
    assert not (genfixes.tagger_permitted(r"A", r"Talk:A"))
    S = set_site(namespaces={**current_site().namespaces, 104: r"Special104:"})
    assert genfixes.tagger_permitted(r"A", r"Special104:A")
    S = set_site(namespaces={k: v for k, v in current_site().namespaces.items() if k != 104})
    S = set_lang(r"en")


def test_conversions_tests_citation_needed() -> None:
    S = W.for_site(EN)
    correct = r"{{citation needed|date=May 2010}}"
    assert genfixes.conversions(r"{{citation needed|May 2010|date=May 2010}}") == correct
    assert genfixes.conversions(r"{{citation needed|may 2010|date=May 2010}}") == correct
    assert genfixes.conversions(r"{{citation needed|  May 2010  |date=May 2010}}") == correct
    assert genfixes.conversions(r"{{Citation needed|May 2010|date=May 2010}}") == correct.replace(
        r"ci", r"Ci"
    )


def test_multiple_issues_no_tags() -> None:
    S = W.for_site(EN)
    assert len(parser.multiple_issues(r"{{multiple issues}}")) == 0
    assert (
        parser.multiple_issues(r"{{multiple issues}}{{Advert|date=May 2012}}")
        == r"{{Advert|date=May 2012}}"
    )


def test_multiple_issues_limits() -> None:
    S = W.for_site(EN)
    bug2 = "{{multiple issues|article=y\r\n|update=November 2008\r\n|out of date=July 2009\r\n|cleanup=July 2009\r\n|wikify=July 2009}}"
    assert genfixes.conversions(bug2) == bug2
    ManyInSection = "==Section==\r\n{{multiple issues |\r\n{{orphan}}\r\n}}\r\n{{dead end}}\r\n{{multiple issues |\r\n{{refimprove}}\r\n}}"
    assert parser.multiple_issues(ManyInSection) == ManyInSection
    dupe = "{{unreferenced}}\r\n{{unreferenced}}"
    assert parser.multiple_issues(dupe) == dupe
    LaterInSection = "Bats.\r\n\r\n==Con==\r\n{{More citations needed section|date=January 2009}}\r\nThe.\r\n\r\n{{multiple issues|section = yes|\r\n{{unreferenced section|date = November 2014}}\r\n{{confusing section |date = November 2014}}\r\n}}\r\n\r\nChris."
    assert parser.multiple_issues(LaterInSection) == LaterInSection


def test_redirect_tagger_mod_dashes() -> None:
    S = W.for_site(EN)
    correct = r"#REDIRECT:[[Foo–bar]] {{R from modification}}"
    redirectendash = r"#REDIRECT:[[Foo–bar]]"
    assert genfixes.redirect_tagger(redirectendash, r"Foo-bar") == correct
    assert genfixes.redirect_tagger(correct, r"Foo-bar") == correct
    assert genfixes.redirect_tagger(redirectendash, r"Foo barism") == redirectendash


def test_redirect_tagger_mod_punct() -> None:
    S = W.for_site(EN)
    correct = r"#REDIRECT:[[Foo .bar]] {{R from modification}}"
    redirectpunct = r"#REDIRECT:[[Foo .bar]]"
    assert genfixes.redirect_tagger(redirectpunct, r"Foo bar") == correct
    assert genfixes.redirect_tagger(redirectpunct, r"Foo /bar") == correct
    assert genfixes.redirect_tagger(redirectpunct, r"Foo ..bar") == correct
    assert genfixes.redirect_tagger(redirectpunct, r"Foo ..bar (long)") == redirectpunct


def test_redirect_tagger_diacr() -> None:
    S = W.for_site(EN)
    correct = r"#REDIRECT:[[Fiancée]] {{R to diacritic}}"
    redirectaccent = r"#REDIRECT:[[Fiancée]]"
    assert genfixes.redirect_tagger(redirectaccent, r"Fiancee") == correct
    assert genfixes.redirect_tagger(correct, r"Fiancee") == correct
    assert genfixes.redirect_tagger(redirectaccent, r"Fiancee-bar") == redirectaccent


def test_redirect_tagger() -> None:
    S = W.for_site(EN)
    redirecttext = r"#REDIRECT:[[Foo bar]]"
    redirecttext2 = r"#REDIRECT:[[foo bar]]"
    assert genfixes.redirect_tagger(redirecttext, r"Foo bar") == redirecttext
    assert genfixes.redirect_tagger(redirecttext2, r"Foo bar") == redirecttext2
    assert genfixes.redirect_tagger(redirecttext, r"foo bar") == redirecttext
    notredirect = r"Now foo bar"
    assert genfixes.redirect_tagger(notredirect, r"Foo bar") == notredirect
    alreadytagged = r"#REDIRECT [[Bethune's Gully]] {{R from alternative spelling}}"
    assert genfixes.redirect_tagger(alreadytagged, '"Bethune\'s Gully"') == alreadytagged


def test_redirect_tagger_capitalisation() -> None:
    S = W.for_site(EN)
    correct = r"#REDIRECT:[[FooBar]] {{R from other capitalisation}}"
    redirectCap = r"#REDIRECT:[[FooBar]]"
    assert genfixes.redirect_tagger(redirectCap, r"Foobar") == correct
    assert genfixes.redirect_tagger(redirectCap, r"foobar") == correct
    assert genfixes.redirect_tagger(redirectCap, r"FOObar") == correct


def test_redirect_tagger_other_namespace() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Project:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Project:FooBar]] {{R to project namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Help:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Help:FooBar]] {{R to help namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Portal:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Portal:FooBar]] {{R to portal namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Template:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Template:FooBar]] {{R to template namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Category:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Category:FooBar]] {{R to category namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[User:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[User:FooBar]] {{R to user namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Talk:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Talk:FooBar]] {{R to talk namespace}}"
    )
    assert (
        genfixes.redirect_tagger(r"#REDIRECT:[[Template talk:FooBar]]", r"FooBar")
        == r"#REDIRECT:[[Template talk:FooBar]]"
    ), r"No change for unsupported namespace"
    correct = r"#REDIRECT:[[Category:FooBar]] {{R to category namespace}}"
    redirectNam = r"#REDIRECT:[[Category:FooBar]]"
    assert genfixes.redirect_tagger(correct, r"FooBar") == correct, r"No change when already tagged"
    assert genfixes.redirect_tagger(redirectNam, r"Template:FooBar") == redirectNam, (
        r"Not tagged when redirect not in mainspace"
    )


def test_redirect_tagger_section() -> None:
    S = W.for_site(EN)
    correct = r"#REDIRECT:[[Foo#Bar]] {{R to section}}"
    assert genfixes.redirect_tagger(r"#REDIRECT:[[Foo#Bar]]", r"Foo") == correct, (
        r"Tag r to section"
    )
    assert genfixes.redirect_tagger(correct, r"Foo") == correct, r"No change when already tagged"


def test_tag_refs_ibid() -> None:
    S = W.for_site(EN)
    returned = (
        (_t := parser.tagger(r"now<ref>ibid</ref> was", r"test", False)),
        (summary := _t[1]),
    )[0][0]
    assert r"{{Ibid|date=" in returned
    assert r"Ibid" in summary
    returned = (
        (_t := parser.tagger(r'now<ref name="again">ibid</ref> was', r"test", False)),
        (summary := _t[1]),
    )[0][0]
    assert r"{{Ibid|date=" in returned
    assert r"Ibid" in summary
    returned = (
        (_t := parser.tagger(r"now<ref>foo</ref> was", r"test", False)),
        (summary := _t[1]),
    )[0][0]
    assert r"{{Ibid|date=" not in returned
    assert r"Ibid" not in summary
    returned = (
        (_t := parser.tagger(r'now<Ref name="again">IBID</ref> was', r"test", False)),
        (summary := _t[1]),
    )[0][0]
    assert r"{{Ibid|date=" in returned, r"Case-insensitive check for ibid"


def test_tag_empty_section() -> None:
    S = W.for_site(EN)
    twoTwos = "==Foo1==\r\n==Foo2==\r\n"
    commentedOutTwoTwos = "\r\n<!--\r\ntext\r\n==Foo1==\r\n==Foo2==\r\ntext -->\r\n"
    returned = ((_t := parser.tagger(twoTwos, r"test", False)), (summary := _t[1]))[0][0]
    assert (
        "==Foo1==\r\n{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n\r\n==Foo2==\r\n"
        in returned
    ), r"Commented out text not changed"
    assert r"Empty section (1)" in summary
    twoTwos = "==Foo1==\r\n\r\n==Foo2==\r\n"
    returned = ((_t := parser.tagger(twoTwos, r"test", False)), (summary := _t[1]))[0][0]
    assert (
        "{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n\r\n==Foo2==\r\n"
        in returned
    ), r"Standard empty section is tagged"
    summary = r""
    returned = (
        (_t := parser.tagger(twoTwos + "\r\n" + twoTwos, r"test", False)),
        (summary := _t[1]),
    )[0][0]
    assert (
        "{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}\r\n\r\n==Foo2==\r\n"
        in returned
    ), r"Extra whitespace handled"
    assert r"Empty section (3)" in summary
    twoTwos = "==Foo1==\r\nx\r\n==Foo2==\r\n"
    returned = ((_t := parser.tagger(twoTwos, r"test", False)), (summary := _t[1]))[0][0]
    assert (
        r"{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in returned
    ), r"Section not empty"
    twoTwos = "===Foo1===\r\n\r\n===Foo2===\r\n"
    returned = ((_t := parser.tagger(twoTwos, r"test", False)), (summary := _t[1]))[0][0]
    assert (
        r"{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in returned
    ), r"Empty level 3 sections not tagged"
    returned = ((_t := parser.tagger(commentedOutTwoTwos, r"test", False)), (summary := _t[1]))[0][
        0
    ]
    assert (
        r"{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in returned
    )
    returned = ((_t := parser.tagger("==F==\r\n==G==", r"test", False)), (summary := _t[1]))[0][0]
    assert (
        r"{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in returned
    )
    returned = (
        (
            _t := parser.tagger(
                twoTwos.replace(r"==Foo1==", "==Foo1==\r\n<pre>\r\nfoo\r\n</pre>"), r"test", False
            )
        ),
        (summary := _t[1]),
    )[0][0]
    assert (
        r"{{Empty section|date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}}}" not in returned
    )


def test_regular_categories() -> None:
    S = W.for_site(EN)
    Cats = []
    assert len(genfixes.regular_categories(Cats)) == 0
    Cats.append(Article(r"Category:Foo"))
    assert len(genfixes.regular_categories(Cats)) == 1
    Cats.append(Article(r"Category:Bar"))
    Cats.append(Article(r"Category:Some stubs"))
    Cats.append(Article(r"Category:A :Stubs"))
    Cats.append(Article(r"Category:Stubs"))
    assert len(genfixes.regular_categories(Cats)) == 2
    Cats.append(Article(r"Category:Proposed deletion"))
    Cats.append(Article(r"Category:Foo proposed deletions"))
    Cats.append(Article(r"Category:Foo proposed for deletion"))
    Cats.append(Article(r"Category:Articles created via the Article Wizard"))
    assert len(genfixes.regular_categories(Cats)) == 2
    Cats.clear()
    assert len(genfixes.regular_categories(r"")) == 0
    assert len(genfixes.regular_categories(r"[[Category:Foo]]")) == 1
    assert len(genfixes.regular_categories(r"[[Category:Foo]] [[Category:Some stubs]]")) == 1
    assert len(genfixes.regular_categories(r"[[Category:Foo]] <!--[[Category:Bar]]-->")) == 1
