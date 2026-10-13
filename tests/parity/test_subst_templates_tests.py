"""Port of the SubstTemplates fixture in AWB UnitTests/MiscellaneousTests.cs: template substitution (pyawb.rules.substtemplates).

Converted mechanically from the C# by tools/porting/nunit2py.py (CRLF line endings in multi-line
strings preserved), then edited by hand. Expectations that differ from AWB on purpose are marked
with a comment explaining why.
"""

# ruff: noqa: F841, F401, E501
# pyright: reportUnusedVariable=false

import pytest

from pyawb.core import genfixes, namespace, rx, tools
from pyawb.core import wikiregexes as W
from pyawb.core.dotnet_regex import DotNetOptions as O
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.parsers import DateLocale
from pyawb.core.rx import DotNetRegex
from pyawb.core.site import Namespace, SiteConfig, current_site
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
from pyawb.rules.substtemplates import SubstTemplates  # noqa: E402


def test_subst_templates_no_expand() -> None:
    S = W.for_site(EN)
    st = SubstTemplates()
    st.expand_recursively = False
    assert st.substitute_templates(r"Now {{foo}}", r"test") == r"Now {{foo}}", (
        r"no change when no templates in list"
    )
    st.template_list = [r"foo", r"bar"]
    assert st.no_of_regexes == 2
    assert st.substitute_templates(r"Now {{foo}}", r"test") == r"Now {{subst:foo}}", r"simple case"
    assert st.substitute_templates(r"Now {{Foo}}", r"test") == r"Now {{subst:foo}}", (
        r"First letter casing handling"
    )
    assert st.substitute_templates(r"Now {{ foo}}", r"test") == r"Now {{subst:foo}}", (
        r"whitespace before"
    )
    assert st.substitute_templates(r"Now {{ foo }}", r"test") == r"Now {{subst:foo}}", (
        r"whitespace after"
    )
    assert (
        st.substitute_templates(r"Now {{foo|first=y}}", r"test") == r"Now {{subst:foo|first=y}}"
    ), r"template with parameters"
    assert st.substitute_templates(r"Now {{foo|first}}", r"test") == r"Now {{subst:foo|first}}", (
        r"template with arguments"
    )
    assert (
        st.substitute_templates(r"Now {{foo}} {{bar}}", r"test")
        == r"Now {{subst:foo}} {{subst:bar}}"
    ), r"Multiple"
    assert st.substitute_templates(r"Now {{Template:foo}}", r"test") == r"Now {{subst:foo}}", (
        r"Template prefix"
    )
    assert st.substitute_templates(r"Now {{template:foo}}", r"test") == r"Now {{subst:foo}}", (
        r"template prefix"
    )
    assert st.substitute_templates(r"Now {{template :foo}}", r"test") == r"Now {{subst:foo}}", (
        r"template spacing after"
    )
    assert st.substitute_templates(r"Now {{ template :foo}}", r"test") == r"Now {{subst:foo}}", (
        r"template spacing before"
    )
    assert st.substitute_templates(r"Now {{ template : foo}}", r"test") == r"Now {{subst:foo}}", (
        r"all whitespace"
    )
    assert st.substitute_templates(r"Now {{Msg:foo}}", r"test") == r"Now {{subst:foo}}", (
        r"Msg prefix"
    )
    assert st.substitute_templates(r"Now {{msg :foo}}", r"test") == r"Now {{subst:foo}}", (
        r"Msg prefix spacing"
    )
    st.template_list = [r"foo (bar)"]
    assert st.no_of_regexes == 1
    assert st.substitute_templates(r"Now {{foo (bar)}}", r"test") == r"Now {{subst:foo (bar)}}", (
        r"template name is escaped"
    )
    assert st.substitute_templates(r"Now {{Foo (bar)}}", r"test") == r"Now {{subst:foo (bar)}}", (
        r"template name is escaped, casing handling"
    )
