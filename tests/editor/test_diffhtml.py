"""action=compare diff rows rebuilt for Qt's rich text."""

# ruff: noqa: E501

from pathlib import Path

import pytest

from pyawb.editor.diffhtml import DiffColors, qt_diff_html, row_lines

# MediaWiki 1.45 action=compare output (shortened)
MODERN = """<tr>
  <td colspan="2" class="diff-lineno">Line 1:</td>
  <td colspan="2" class="diff-lineno">Line 1:</td>
</tr>
<tr>
  <td class="diff-marker" data-marker="−"></td>
  <td class="diff-deletedline diff-side-deleted"><div>القط <del class="diffchange diffchange-inline">[[حيوان|حيوان]]</del> أليف &amp; x</div></td>
  <td class="diff-marker" data-marker="+"></td>
  <td class="diff-addedline diff-side-added"><div>القط <ins class="diffchange diffchange-inline">[[حيوان]]</ins> أليف &amp; x</div></td>
</tr>
<tr>
  <td class="diff-marker"></td>
  <td class="diff-context diff-side-deleted"><div>سطر</div></td>
  <td class="diff-marker"></td>
  <td class="diff-context diff-side-added"><div>سطر</div></td>
</tr>
<tr>
  <td colspan="2" class="diff-empty diff-side-deleted"></td>
  <td class="diff-marker" data-marker="+"></td>
  <td class="diff-addedline diff-side-added"><div><a class="mw-diff-movedpara-right" href="#movedpara_1_0_lhs">&#x26AB;</a>new</div></td>
</tr>"""

COLORS = DiffColors(added="#aaaaff", removed="#ffee00")


def test_modern_rows() -> None:
    out = qt_diff_html(MODERN, COLORS, rtl=True)
    assert out.startswith('<html><body dir="rtl"')
    assert "<del" not in out and "<ins" not in out and "data-marker" not in out
    assert "<a " not in out and "href" not in out
    assert '<span style="background-color:#ffee00; font-weight:bold">[[حيوان|حيوان]]</span>' in out
    assert '<span style="background-color:#aaaaff; font-weight:bold">[[حيوان]]</span>' in out
    assert "−</td>" in out and "+</td>" in out
    assert "&amp; x" in out and "&#x26AB;" in out
    assert "Line 1:" in out
    assert out.count("<td") == out.count("</td>")
    assert out.count("<tr>") == out.count("</tr>") == 4


def test_old_wikidiff2_rows() -> None:
    rows = """<tr>
  <td colspan="2" align="left"><strong><!--LINE 12--></strong></td>
  <td colspan="2" align="left"><strong><!--LINE 13--></strong></td>
</tr>
<tr>
  <td>-</td>
  <td class="diff-deletedline">a <span class="diffchange">b</span></td>
  <td>+</td>
  <td class="diff-addedline">a <span class="diffchange">c</span></td>
</tr>"""
    out = qt_diff_html(rows, COLORS, line_label="Zeile $1:")
    assert "Zeile 12:" in out and "Zeile 13:" in out
    assert '<span style="background-color:#ffee00; font-weight:bold">b</span>' in out
    assert '<span style="background-color:#aaaaff; font-weight:bold">c</span>' in out
    assert 'dir="ltr"' in out


def test_no_difference() -> None:
    assert "Keine Änderung" in qt_diff_html("", no_difference="Keine Änderung")


@pytest.mark.parametrize("name", ["test-a.diff", "test-b.diff"])
def test_wikidiff2_test_outputs_stay_balanced(name: str) -> None:
    path = Path(__file__).parents[3] / "wikidiff2" / "test" / name
    if not path.exists():
        pytest.skip("wikidiff2 checkout not present")
    out = qt_diff_html(path.read_text(encoding="utf-8"))
    assert out.count("<td") == out.count("</td>")
    assert out.count("<span") == out.count("</span>")


def test_rtl_rows_are_mirrored() -> None:
    """Qt ignores dir="rtl" on tables: the cells are written in reverse, so the old text is on
    the right as on an RTL wiki, with the change bars on the marker's side."""
    ltr = qt_diff_html(MODERN, COLORS)
    rtl = qt_diff_html(MODERN, COLORS, rtl=True)
    assert ltr.index("[[حيوان|حيوان]]") < ltr.index("[[حيوان]]</span>")
    assert rtl.index("[[حيوان]]</span>") < rtl.index("[[حيوان|حيوان]]")
    assert ltr.index("−</td>") < ltr.index("+</td>")
    assert rtl.index("+</td>") < rtl.index("−</td>")
    assert "border-right:4px" in rtl and "border-right" not in ltr


def test_row_lines() -> None:
    # header, changed line 1, context line 2, added line 3
    assert row_lines(MODERN) == [None, 1, 2, 3]
    old = """<tr><td colspan="2"><!--LINE 5--></td><td colspan="2"><!--LINE 7--></td></tr>
<tr><td>-</td><td class="diff-deletedline">gone</td><td colspan="2">&nbsp;</td></tr>
<tr><td> </td><td class="diff-context">a</td><td> </td><td class="diff-context">a</td></tr>"""
    assert row_lines(old) == [None, 7, 7]
