"""Port of AWB UnitTests/FixNonBreakingSpacesTests.cs: non-breaking spaces.

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
from tests.parity.helpers import EN, cs_len, set_lang, set_site, utc_month_year
from tests.parity.regex_assert import check_match, check_matches

parser = genfixes.Parsers()  # AWB's RequiresParser


def test_test_fix_percent() -> None:
    S = W.for_site(EN)
    assert parser.fix_non_breaking_spaces(r"a 15 % ") == r"a 15% ", r"remove space"
    assert parser.fix_non_breaking_spaces(r"a -15 % ") == r"a -15% ", r"remove space (minus sign)"
    assert parser.fix_non_breaking_spaces(r"a +15 % ") == r"a +15% ", r"remove space (plus sign)"
    assert parser.fix_non_breaking_spaces(r"a ±15 % ") == r"a ±15% ", (
        r"remove space (plus-minus sign)"
    )
    assert parser.fix_non_breaking_spaces(r"a 15&nbsp;% ") == r"a 15% ", (
        r"remove non breaking space"
    )
    assert parser.fix_non_breaking_spaces(r"a 15 &nbsp;%.") == r"a 15%.", (
        r"remove space and nbsp and maintain point"
    )
    assert parser.fix_non_breaking_spaces(r"a 15 % ") == r"a 15% ", r"remove space"
    assert parser.fix_non_breaking_spaces(r"a 15&nbsp;%.") == r"a 15%.", (
        r"remove non breaking space and maintain point"
    )
    assert parser.fix_non_breaking_spaces(r"a 15 %,") == r"a 15%,", (
        r"remove space and maintain comma"
    )
    assert parser.fix_non_breaking_spaces(r"a 15&nbsp;%,") == r"a 15%,", (
        r"remove non breaking space  and maintain comma"
    )
    assert parser.fix_non_breaking_spaces(r"a 15 %!") == r"a 15%!", (
        r"remove space and maintain mark"
    )
    assert parser.fix_non_breaking_spaces(r"a 15&nbsp;%!") == r"a 15%!", (
        r"remove non breaking space  and maintain mark"
    )
    assert parser.fix_non_breaking_spaces(r"a 15  %") == r"a 15  %", r"no changes"
    assert parser.fix_non_breaking_spaces(r"5a21 %") == r"5a21 %", r"no changes"
    assert parser.fix_non_breaking_spaces(r"a15 %") == r"a15 %", r"no changes"
    assert parser.fix_non_breaking_spaces(r"a 15 %a") == r"a 15 %a", r"no changes (character)"
    assert parser.fix_non_breaking_spaces(r"a 15 %2") == r"a 15 %2", r"no changes (character)"
    assert parser.fix_non_breaking_spaces(r"a 15.2 % ") == r"a 15.2% ", r"catch decimal numbers"
    assert parser.fix_non_breaking_spaces(r"acid (15.2 %) ") == r"acid (15.2%) ", (
        r"decimal numbers in parenthenses"
    )
    assert parser.fix_non_breaking_spaces(r"a 15.a2 % ") == r"a 15.a2 % ", r"avoid weird things"
    S = set_lang(r"sv")
    assert parser.fix_non_breaking_spaces(r"a 15 % ") == r"a 15 % ", (
        r"Don't remove space in svwiki per sv:Procent"
    )
    S = set_lang(r"simple")
    assert parser.fix_non_breaking_spaces(r"a 15 % ") == r"a 15% ", r"Remove space in simple"
    S = set_lang(r"en")
    assert parser.fix_non_breaking_spaces(r"a 15 % ") == r"a 15% ", r"remove space"


def test_test_fix_currency() -> None:
    S = W.for_site(EN)
    assert parser.fix_non_breaking_spaces(r"£ 123 ") == r"£123 ", r"remove space (Pound sign)"
    assert parser.fix_non_breaking_spaces(r"€ 123 ") == r"€123 ", r"remove space (Euro sign)"
    assert parser.fix_non_breaking_spaces(r"$ 123 ") == r"$123 ", r"remove space (Dollar sign)"
    assert parser.fix_non_breaking_spaces(r"£&nbsp;123 ") == r"£123 ", r"remove non breaking space"
    assert parser.fix_non_breaking_spaces(r"£ &nbsp;123.") == r"£123.", (
        r"remove space and nbsp and maintain point"
    )
    assert parser.fix_non_breaking_spaces(r"£ 12.3,") == r"£12.3,", (
        r"remove space and maintain comma"
    )
    S = set_lang(r"sv")
    assert parser.fix_non_breaking_spaces(r"£ 123 ") == r"£ 123 ", r"Don't remove space in svwiki"
    S = set_lang(r"simple")
    assert parser.fix_non_breaking_spaces(r"£ 123 ") == r"£123 ", r"Remove space in simple"
    S = set_lang(r"en")
    assert parser.fix_non_breaking_spaces(r"£ 123 ") == r"£123 ", r"remove space"


def test_test_fix_clock_time() -> None:
    S = W.for_site(EN)
    assert parser.fix_non_breaking_spaces(r"2:35a.m.") == r"2:35&nbsp;a.m."
    assert parser.fix_non_breaking_spaces(r"9:59a.m.") == r"9:59&nbsp;a.m."
    assert parser.fix_non_breaking_spaces(r"12:35a.m.") == r"12:35&nbsp;a.m."
    assert parser.fix_non_breaking_spaces(r"12:35 a.m.") == r"12:35&nbsp;a.m."
    assert parser.fix_non_breaking_spaces(r"12:35p.m.") == r"12:35&nbsp;p.m."
    assert parser.fix_non_breaking_spaces(r"12:35 p.m.") == r"12:35&nbsp;p.m."
    assert parser.fix_non_breaking_spaces(r"02:35a.m.") == r"2:35&nbsp;a.m.", r"starts with zero"
    assert parser.fix_non_breaking_spaces(r"09:59a.m.") == r"9:59&nbsp;a.m."
    assert parser.fix_non_breaking_spaces(r"2:35p.m.") == r"2:35&nbsp;p.m."
    assert parser.fix_non_breaking_spaces(r"12:35p.m.") == r"12:35&nbsp;p.m."
    assert parser.fix_non_breaking_spaces(r"02:35p.m.") == r"2:35&nbsp;p.m.", r"starts with zero"
    assert parser.fix_non_breaking_spaces(r"2:75a.m.") == r"2:75a.m.", r"invalid minutes number"
    assert parser.fix_non_breaking_spaces(r"36:15a.m.") == r"36:15a.m.", r"invalid hours number"
    assert parser.fix_non_breaking_spaces(r"16:15c.m.") == r"16:15c.m.", r"invalid suffix"
    assert parser.fix_non_breaking_spaces(r"(8:00:57 p.m. EST)") == r"(8:00:57&nbsp;p.m. EST)"


def test_test_fix_non_breaking_spaces() -> None:
    S = W.for_site(EN)
    assert parser.fix_non_breaking_spaces(r"a 50 km road") == r"a 50&nbsp;km road"
    assert (
        parser.fix_non_breaking_spaces(r"a 50 m (170 ft) road") == r"a 50&nbsp;m (170&nbsp;ft) road"
    )
    assert (
        parser.fix_non_breaking_spaces(r"a 50.2 m (170 ft) road")
        == r"a 50.2&nbsp;m (170&nbsp;ft) road"
    )
    assert (
        parser.fix_non_breaking_spaces(r"a 5002 m (17,000 ft) road")
        == r"a 5002&nbsp;m (17,000&nbsp;ft) road"
    )
    assert parser.fix_non_breaking_spaces(r"a long (50 km) road") == r"a long (50&nbsp;km) road"
    assert parser.fix_non_breaking_spaces(r"a 50km road") == r"a 50&nbsp;km road"
    assert parser.fix_non_breaking_spaces(r"a 50 kg dog") == r"a 50&nbsp;kg dog"
    assert parser.fix_non_breaking_spaces(r"a 50kg dog") == r"a 50&nbsp;kg dog"
    assert parser.fix_non_breaking_spaces(r"a 50Hz rod") == r"a 50&nbsp;Hz rod"
    assert parser.fix_non_breaking_spaces(r"a 50kHz rod") == r"a 50&nbsp;kHz rod"
    assert parser.fix_non_breaking_spaces(r"a 50 cm road") == r"a 50&nbsp;cm road"
    assert parser.fix_non_breaking_spaces(r"a 50cm road") == r"a 50&nbsp;cm road"
    assert parser.fix_non_breaking_spaces(r"a 50.247cm road") == r"a 50.247&nbsp;cm road"
    assert parser.fix_non_breaking_spaces(r"a 50.247nm laser") == r"a 50.247&nbsp;nm laser"
    assert parser.fix_non_breaking_spaces(r"a 50.247 mm pen") == r"a 50.247&nbsp;mm pen"
    assert parser.fix_non_breaking_spaces(r"a 50.247  nm laser") == r"a 50.247&nbsp;nm laser"
    assert parser.fix_non_breaking_spaces(r"a 50.247µm laser") == r"a 50.247&nbsp;µm laser"
    assert parser.fix_non_breaking_spaces(r"a 50.247 cd light") == r"a 50.247&nbsp;cd light"
    assert parser.fix_non_breaking_spaces(r"a 50.247cd light") == r"a 50.247&nbsp;cd light"
    assert (
        parser.fix_non_breaking_spaces(r"a 50.247mmol solution") == r"a 50.247&nbsp;mmol solution"
    )
    assert parser.fix_non_breaking_spaces(r"a 0.3mol solution") == r"a 0.3&nbsp;mol solution"
    assert parser.fix_non_breaking_spaces(r"a 50.247 kW laser") == r"a 50.247&nbsp;kW laser"
    assert parser.fix_non_breaking_spaces(r"a 50.247 mW laser") == r"a 50.247&nbsp;mW laser"
    assert parser.fix_non_breaking_spaces(r"a 50m/s car") == r"a 50&nbsp;m/s car"
    assert parser.fix_non_breaking_spaces(r"at 5°C today") == r"at 5&nbsp;°C today"
    assert parser.fix_non_breaking_spaces(r"at 5 °C today") == r"at 5&nbsp;°C today"
    assert parser.fix_non_breaking_spaces(r"at 55°F today") == r"at 55&nbsp;°F today"
    assert parser.fix_non_breaking_spaces(r"at 55  °F today") == r"at 55&nbsp;°F today"
    assert parser.fix_non_breaking_spaces(r"at 55 °F today") == r"at 55&nbsp;°F today", (
        r"invisible nbsp (Unicode U+00A0) before unit"
    )
    assert (
        parser.fix_non_breaking_spaces(r"a 50.2 m (170 ft) road")
        == r"a 50.2&nbsp;m (170&nbsp;ft) road"
    ), r"invisible nbsp (Unicode U+00A0) before m and ft"
    genFixes.assert_not_changed(r"nearly 5m people")
    genFixes.assert_not_changed(r"nearly 5 in 10 people")
    genFixes.assert_not_changed(r"a 3CD set")
    genFixes.assert_not_changed(r"its 3 feet are")
    genFixes.assert_not_changed(r"http://site.com/View/3356 A show")
    genFixes.assert_not_changed(r"a 50&nbsp;km road")
    genFixes.assert_not_changed(r"over $200K in cash")
    genFixes.assert_not_changed(r"now {{a 50kg dog}} was")
    genFixes.assert_not_changed(r"now a [[50kg dog]] was")
    genFixes.assert_not_changed(r"now “a 50kg dog” was")
    genFixes.assert_not_changed(r"now <!--a 50kg dog--> was")
    genFixes.assert_not_changed(r"now <nowiki>a 50kg dog</nowiki> was")
    genFixes.assert_not_changed(r"*[http://site.com/blah_20cm_long Site here]")
    genFixes.assert_not_changed(r"a 50 gram rod")
    genFixes.assert_not_changed(r"a long (50 foot) toad")
    assert parser.fix_non_breaking_spaces(r"the 50mm gun") == r"the 50mm gun"
    assert parser.fix_non_breaking_spaces(r"a long (50 in) toad") == r"a long (50&nbsp;in) toad"
    assert parser.fix_non_breaking_spaces(r"a long (50 ft) toad") == r"a long (50&nbsp;ft) toad"
    assert parser.fix_non_breaking_spaces(r"a long (50in) toad") == r"a long (50&nbsp;in) toad"
    assert (
        parser.fix_non_breaking_spaces(r"a long (50-52in) toad") == r"a long (50-52&nbsp;in) toad"
    )
    assert (
        parser.fix_non_breaking_spaces(r"a long (50–52in) toad") == r"a long (50–52&nbsp;in) toad"
    )
    assert parser.fix_non_breaking_spaces(r"a long (50.5 in) toad") == r"a long (50.5&nbsp;in) toad"
    assert parser.fix_non_breaking_spaces(r"a big (50.5 oz) toad") == r"a big (50.5&nbsp;oz) toad"


def test_test_fix_non_breaking_spaces_de() -> None:
    S = W.for_site(EN)
    S = set_lang(r"fr")
    parser = genfixes.Parsers()
    assert parser.fix_non_breaking_spaces(r"a 50.247µm laser") == r"a 50.247&nbsp;µm laser"
    assert parser.fix_non_breaking_spaces(r"a 50.247um laser") == r"a 50.247um laser"
    S = set_lang(r"en")
    parser = genfixes.Parsers()
    assert parser.fix_non_breaking_spaces(r"a 50.247um laser") == r"a 50.247&nbsp;um laser"


def test_fix_non_breaking_spaces_pagination() -> None:
    S = W.for_site(EN)
    assert parser.fix_non_breaking_spaces(r"Smith 2004, p. 40") == r"Smith 2004, p.&nbsp;40"
    assert parser.fix_non_breaking_spaces(r"Smith 2004, p.  40") == r"Smith 2004, p.&nbsp;40"
    assert parser.fix_non_breaking_spaces(r"Smith 2004, p.40") == r"Smith 2004, p.&nbsp;40"
    assert parser.fix_non_breaking_spaces(r"Smith 2004, p. XI") == r"Smith 2004, p.&nbsp;XI"
    assert parser.fix_non_breaking_spaces(r"Smith 2004, pp. 40-44") == r"Smith 2004, pp.&nbsp;40-44"
    assert parser.fix_non_breaking_spaces(r"Smith 2004, Pp. 40-44") == r"Smith 2004, Pp.&nbsp;40-44"
    assert parser.fix_non_breaking_spaces(r"Smith 2004, p.&nbsp;40") == r"Smith 2004, p.&nbsp;40"
    assert (
        parser.fix_non_breaking_spaces(r"Smith 200 pp. ISBN 12345678X")
        == r"Smith 200 pp. ISBN 12345678X"
    ), r"No change for number of pages in book"
