"""Port of AWB UnitTests/CiteTemplateDatesTests.cs: citation template dates (awb_x.core.parsers.citetemplates).

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


def test_test_cite_template_dates() -> None:
    S = W.for_site(EN)
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 25/03/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 25/11/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-11-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 25/3/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 4/21/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04/21/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04/04/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 4/4/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 25/03/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 30/03/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-30 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 25/3/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 4/21/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04/21/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04/04/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 4/4/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04.21.08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04.21.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 21.05.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 21.5.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 13.5.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-05-13 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04-21-08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 04-21-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 21-04-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 21-5-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|accessdate = 21-5-2011 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2011-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{Cite web | url=http://site.it | title=hello|accessdate = 21-5-08 }} was"
        )
        == r"now {{Cite web | url=http://site.it | title=hello|accessdate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 25/03/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 25/11/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-11-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 25/3/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 4/21/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04/21/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04/04/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 4/4/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 25/03/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 30/03/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-03-30 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 25/3/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 4/21/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04/21/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04/04/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 4/4/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04.21.08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04.21.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 21.05.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 21.5.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 13.5.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-05-13 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04-21-08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 04-21-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 21-04-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 21-5-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 21-5-2011 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2011-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{Cite web | url=http://site.it | title=hello|archivedate = 21-5-08 }} was"
        )
        == r"now {{Cite web | url=http://site.it | title=hello|archivedate = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 25/03/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 25/11/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-11-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 25/3/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 4/21/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04/21/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04/21/1980 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 1980-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04/04/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 4/4/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 25/03/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 30/03/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-30 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 25/3/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-25 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 4/21/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04/21/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04/04/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 4/4/08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-04 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04.21.08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04.21.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 21.05.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 21.5.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 13.5.2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-05-13 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04-21-08 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 04-21-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 21-04-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 21-5-2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 21-5-2011 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2011-05-21 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{Cite web | url=http://site.it | title=hello|date = 21-5-08 |publisher=BBC}} was"
        )
        == r"now {{Cite web | url=http://site.it | title=hello|date = 2008-05-21 |publisher=BBC}} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{Cite web | url=http://site.it | title=hello|date = 21-5-08|publisher=BBC}} was"
        )
        == r"now {{Cite web | url=http://site.it | title=hello|date = 2008-05-21|publisher=BBC}} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Jan-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-01-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Feb-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-02-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Mar-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Apr-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-May-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-05-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Jun-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-06-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Jul-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-07-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Aug-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-08-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Sep-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-09-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Oct-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-10-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Nov-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-11-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Dec-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-12-11 }} was"
    )
    PubMed = r"now {{cite journal | journal=BMJ | title=hello|date = 2008-Dec-11 }} was"
    assert genfixes.cite_template_dates(PubMed) == PubMed, (
        r"no change to PubMed date format in scientific journal cite"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-January-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-01-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-February-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-02-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-March-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-April-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-June-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-06-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-July-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-07-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-August-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-08-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-September-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-09-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-October-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-10-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-November-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-11-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-December-11 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-12-11 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Jan.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-01-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Feb.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-02-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Mar.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-03-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Apr.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-04-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Jun.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-06-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Jul.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-07-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Aug.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-08-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Sep.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-09-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Oct.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-10-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Nov.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-11-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008-Dec.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-12-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now <ref>{{cite news|url=http://www.a1gp.com/News/NewsArticle.aspx?newsId=42370|title=It's all about the bumps|accessdate=2008-Nov-16|date=2008-Nov-07|publisher=a1gp.com}}</ref> "
        )
        == r"now <ref>{{cite news|url=http://www.a1gp.com/News/NewsArticle.aspx?newsId=42370|title=It's all about the bumps|accessdate=2008-11-16|date=2008-11-07|publisher=a1gp.com}}</ref> "
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008 Jan. 07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-01-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2008 Jan 07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-01-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2020 Jan 07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2020-01-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 1998 January 07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 1998-01-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-Dec.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|archivedate = 2008-12-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|airdate = 2008-Dec.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|airdate = 2008-12-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date2 = 2008-Dec.-07 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date2 = 2008-12-07 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"<ref>{{cite web|url=http://www.nuclearweaponarchive.org/Russia/TsarBomba.html|title=The Tsar Bomba (King of Bombs)|accessdate=11-05-2006}}</ref>"
        )
        == r"<ref>{{cite web|url=http://www.nuclearweaponarchive.org/Russia/TsarBomba.html|title=The Tsar Bomba (King of Bombs)|accessdate=11-05-2006}}</ref>"
    )
    assert (
        genfixes.cite_template_dates(
            r"<ref>{{cite web|url=http://www.nuclearweaponarchive.org/Russia/TsarBomba.html|title=The Tsar Bomba (King of Bombs)|accessdate=2010-12}}</ref>"
        )
        == r"<ref>{{cite web|url=http://www.nuclearweaponarchive.org/Russia/TsarBomba.html|title=The Tsar Bomba (King of Bombs)|accessdate=2010-12}}</ref>"
    )
    CitePodcast = "{{cite podcast\r\n| url =http://www.heretv.com/APodcastDetailPage.php?id=24\r\n| title =The Ben and Dave Show\r\n| host =Harvey, Ben and Rubin, Dave\r\n| accessdate =11-08\r\n| accessyear =2007\r\n}}"
    assert genfixes.cite_template_dates(CitePodcast) == CitePodcast
    assert (
        genfixes.cite_template_dates(r"{{cite web|date=2008-December-11|accessdate=2008-Aug.-07}}")
        == r"{{cite web|date=2008-12-11|accessdate=2008-08-07}}"
    )
    assert (
        genfixes.cite_template_dates(r"{{cite web|date=2008-Dec.-11|accessdate=2008-Aug.-07}}")
        == r"{{cite web|date=2008-12-11|accessdate=2008-08-07}}"
    )
    ambig = "now {{cite web | url=http://site.it | title=hello|date = 5-4-1998}} was\r\nnow {{cite web | url=http://site.it | title=hello|date = 5-5-1998}} was"
    assert genfixes.cite_template_dates(ambig) == ambig
    Y4M2 = r"now {{cite web | url=http://site.it | title=hello|date = 2010-03 }} was"
    assert genfixes.cite_template_dates(Y4M2) == Y4M2
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 2/15/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-02-15 }} was"
    )
    assert (
        genfixes.cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 02/15/2008 }} was"
        )
        == r"now {{cite web | url=http://site.it | title=hello|date = 2008-02-15 }} was"
    )
    YearRange = r"{{cite web | url=http://site.it | title=hello|date = 1910-1911 }}"
    assert genfixes.cite_template_dates(YearRange) == YearRange


def test_cite_template_dates_time_stamp() -> None:
    S = W.for_site(EN)
    correctpart = r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-25"
    datestamp = r" 12:12:54 BST"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + "\r\n}} was")
        == correctpart + r"<!--" + datestamp + "-->\r\n}} was"
    )
    datestamp = r" 12:30 BST"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    datestamp = r" 12:30 CET"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    datestamp = r" 12:30 GMT, 13:30 RST"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    datestamp = r" 12:30 GMT, 13:30 [[RST]]"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    datestamp = r" 12:30 GMT, 13:30 [[Foo|RST]]"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    datestamp = r" 12.30 BST"
    assert (
        genfixes.cite_template_dates(correctpart + datestamp + r"}} was")
        == correctpart + r"<!--" + datestamp + r"-->}} was"
    )
    assert (
        genfixes.cite_template_dates(
            correctpart.replace(r"2018-03-25", r"25 March 2018") + datestamp + r"}} was"
        )
        == correctpart.replace(r"2018-03-25", r"25 March 2018") + r"<!--" + datestamp + r"-->}} was"
    )
    assert (
        genfixes.cite_template_dates(
            correctpart.replace(r"2018-03-25", r"March 25, 2018") + datestamp + r"}} was"
        )
        == correctpart.replace(r"2018-03-25", r"March 25, 2018")
        + r"<!--"
        + datestamp
        + r"-->}} was"
    )
    assert (
        genfixes.cite_template_dates(
            correctpart.replace(r"2018-03-25", r"March 25th, 2018") + datestamp + r"}} was"
        )
        == correctpart.replace(r"2018-03-25", r"March 25th, 2018")
        + r"<!--"
        + datestamp
        + r"-->}} was"
    )
    YearList = r"{{cite web | url=http://www.site.com | title=a | date=2004, 2006, 2009 }}"
    assert genfixes.cite_template_dates(YearList) == YearList


def test_cite_template_dates_en_only() -> None:
    S = W.for_site(EN)
    bad = r"now {{cite web | url=http://site.it | title=hello|accessdate = 25/03/2008 }} was"
    S = set_lang(r"fr")
    assert genfixes.cite_template_dates(bad) == bad
    S = set_lang(r"en")
    assert (
        genfixes.cite_template_dates(bad)
        == r"now {{cite web | url=http://site.it | title=hello|accessdate = 2008-03-25 }} was"
    )


def test_ambiguous_cite_template_dates() -> None:
    S = W.for_site(EN)
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|date = 5-4-1998}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|accessdate = 5-4-1998}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|access-date = 5-4-1998}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|date = 5/4/1998}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|date = 05-04-1998}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|date = 11-4-1998}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|archivedate = 11-4-2008}} was"
    )
    assert genfixes.ambiguous_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=hello|date = 5-11-09}} was"
    )
    assert not (
        genfixes.ambiguous_cite_template_dates(
            r"now {{cite web | url=http://site.it | title=hello|date = 5-5-1998}} was"
        )
    )


def test_ambiguous_cite_template_dates2() -> None:
    S = W.for_site(EN)
    ambigDates = {}
    ambigDates = genfixes.ambig_cite_template_dates(
        r"now {{cite web | url=http://site.it | title=a |date=7-6-2005 }}"
    )
    assert len(ambigDates) == 1
    assert 52 in ambigDates
    assert 8 in ambigDates.values()
