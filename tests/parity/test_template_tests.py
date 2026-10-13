"""Port of AWB UnitTests/TemplateTests.cs: template helpers (awb_x.core.parsers.templates).

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401
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


def test_get_all_templates() -> None:
    S = W.for_site(EN)
    t = []
    assert genfixes.get_all_templates(r"") == t
    t.append(r"Foo")
    assert genfixes.get_all_templates(r"{{foo}}") == t, r"case converted to first letter upper"
    assert genfixes.get_all_templates(r"{{Foo}}") == t, r"uppercase template first letter handled"
    assert genfixes.get_all_templates(r"{{Foo}} {{foo}}") == t, r"Templates list deduplicated"
    assert genfixes.get_all_templates(r"{{Foo|bar=1}}") == t, r"Support templates with arguments"
    t.append(r"Other")
    assert genfixes.get_all_templates(r"{{Foo|bar=1 {{Other}} }}") == t, r"Support nested templates"
    t.append(r"Other2")
    assert genfixes.get_all_templates(r"{{Foo|bar=1 {{Other| a= {{Other2|}} }} }}") == t, (
        r"Support 2x nested templates"
    )
    assert genfixes.get_all_templates("{{_Foo  |bar=1 {{ Other\r\n| a= {{ Other2_|}} }} }}") == t, (
        r"Ignore whitespace"
    )
    assert (
        genfixes.get_all_templates("{{Foo|bar=1 {{Other\r\n| a= {{Template:Other2_|}} }} }}") == t
    ), r"Ignore Template: prefix"
    t.clear()
    t.append(r"DISPLAYTITLE")
    assert genfixes.get_all_templates(r"{{DISPLAYTITLE:foo}}") == t, (
        r"Supports DISPLAYTITLE template"
    )
    t.clear()
    t.append(r"Template")
    assert genfixes.get_all_templates(r"{{Template:}}") == t, r"Supports empty template"


def test_get_all_template_detail() -> None:
    S = W.for_site(EN)
    t = []
    assert genfixes.get_all_template_detail(r"") == t
    t.append(r"{{foo}}")
    assert genfixes.get_all_template_detail(r"{{foo}}") == t, r"Extracts simple template call"
    assert genfixes.get_all_template_detail(r"{{foo}} {{foo}}") == t, r"Deduplicates"
    t.append(r"{{foo2}}")
    assert genfixes.get_all_template_detail(r"{{foo}} {{foo2}}") == t, (
        r"Extracts each distinct template call"
    )
    t.clear()
    t.append(r"{{foo|param={{foo2}} {{foo3=|bar3={{foo4}}}}}}")
    t.append(r"{{foo2}}")
    t.append(r"{{foo3=|bar3={{foo4}}}}")
    t.append(r"{{foo4}}")
    assert (
        genfixes.get_all_template_detail(r"{{foo|param={{foo2}} {{foo3=|bar3={{foo4}}}}}}") == t
    ), r"Extracts nested template calls"
    t.clear()
    t.append(r"{{DISPLAYTITLE:foo}}")
    assert genfixes.get_all_template_detail(r"{{DISPLAYTITLE:foo}}") == t, (
        r"Supports DISPLAYTITLE template call"
    )


def test_template_exists_tests() -> None:
    S = W.for_site(EN)
    assert genfixes.template_exists(
        genfixes.get_all_templates(r"{{foo}}"), tools.nested_template_regex(r"Foo")
    )
    assert genfixes.template_exists(
        genfixes.get_all_templates(r"{{Template:foo}}"), tools.nested_template_regex(r"Foo")
    )
    assert genfixes.template_exists(
        genfixes.get_all_templates(r"{{ foo }}"), tools.nested_template_regex(r"Foo")
    )
    assert genfixes.template_exists(
        genfixes.get_all_templates(r"{{foo|p=1}}"), tools.nested_template_regex(r"Foo")
    )
    assert not (
        genfixes.template_exists(
            genfixes.get_all_templates(r"{{foo}}"), tools.nested_template_regex(r"Foo2")
        )
    )
