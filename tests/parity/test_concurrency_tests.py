"""Port of the ConcurrencyTests fixture in AWB UnitTests/MiscellaneousTests.cs: two Parsers objects
hide text independently.

Converted mechanically from the C# by tools/porting/nunit2py.py.
"""

from awb_l.core import genfixes


def test_parser() -> None:
    p1 = genfixes.Parsers()
    p2 = genfixes.Parsers()
    s1 = p1.hide_text(r"<pre>foo bar</pre>")
    s2 = p2.hide_text(r"<source>quux</source>")
    assert p1.add_back_text(s1) == r"<pre>foo bar</pre>"
    assert p2.add_back_text(s2) == r"<source>quux</source>"
