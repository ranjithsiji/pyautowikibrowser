"""Port of the InTemplateRuleTests fixture in AWB UnitTests/MiscellaneousTests.cs: advanced find and replace rules (awb_l.rules.replacespecial).

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
from awb_l.rules.replacespecial import InTemplateRule  # noqa: E402


def test_template_used_in_text() -> None:
    S = W.for_site(EN)
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"bert}} was great")
    assert InTemplateRule.template_used_in_text(r"bert", r"Bert}} was great")
    assert InTemplateRule.template_used_in_text(r"bert", r"bert}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert }} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r" Bert}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert|fo=yes}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", "Bert\r\n|fo=yes}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert |fo=yes}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r" Bert|fo=yes}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", "\r\n    Bert|fo=yes}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert|fo=yes}} was <!--great-->")
    assert InTemplateRule.template_used_in_text(r"Bert", r"<!--thing--> Bert }} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert<!--thing-->}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert", r"Bert<!--thing-->|foo=bar}} was great")
    assert InTemplateRule.template_used_in_text(r"", r"Bert}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert Li", r"Bert Li}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert Li", r"Bert   Li}} was great")
    assert InTemplateRule.template_used_in_text(r"Bert Li", r"Bert_Li}} was great")


def test_template_used_in_text_no_matches() -> None:
    S = W.for_site(EN)
    assert not (InTemplateRule.template_used_in_text(r"Bert", r"{{Bert}} was great"))
    assert not (InTemplateRule.template_used_in_text(r"Bert", r"Bert was great"))
    assert not (InTemplateRule.template_used_in_text(r"Bert", r"[[Bert]] was great"))
    assert not (InTemplateRule.template_used_in_text(r"Bert", r"Tim}} was great"))
    assert not (InTemplateRule.template_used_in_text(r"Bert", r"BERT}} was great"))
    assert not (InTemplateRule.template_used_in_text(r"Bert Li", r"BertLi}} was great"))
    assert not (InTemplateRule.template_used_in_text(r"Bert", r"<!--Bert}}--> was great"))
