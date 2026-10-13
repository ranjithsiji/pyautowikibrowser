"""Find and replace table rows (AWB's grid) to rules, validation, and the engine."""

from pyawb.core.rx import DotNetOptions
from pyawb.rules.findreplace import ReplacementRow, find_and_replace_from_rows, row_error


def test_row_defaults_match_awb_new_row() -> None:
    row = ReplacementRow("a")
    rep = row.to_replacement()
    assert rep.enabled and not rep.minor and not rep.is_regex and not rep.before_or_after
    assert rep.options == DotNetOptions.IGNORE_CASE  # case sensitive is unchecked


def test_row_options() -> None:
    rep = ReplacementRow(
        "a.b", "c", case_sensitive=True, is_regex=True, multiline=True, singleline=True,
        minor=True, after_fixes=True, enabled=False, comment="note",
    ).to_replacement()  # fmt: skip
    assert rep.find == "a.b" and rep.replace == "c" and rep.comment == "note"
    assert rep.options == DotNetOptions.MULTILINE | DotNetOptions.SINGLELINE
    assert rep.minor and rep.before_or_after and not rep.enabled
    # plain text is escaped
    assert ReplacementRow("a.b").to_replacement().find == r"a\.b"


def test_row_error() -> None:
    assert row_error(ReplacementRow("(a", is_regex=True)) is not None
    assert row_error(ReplacementRow("(a")) is None  # plain text
    assert row_error(ReplacementRow(r"%%title%%\b", is_regex=True)) is None
    assert row_error(ReplacementRow("")) is None


def test_engine_from_rows_skips_empty_rows() -> None:
    far = find_and_replace_from_rows(
        [ReplacementRow("قط", "هر"), ReplacementRow(""), ReplacementRow("x", enabled=False)],
        ignore_links=True,
    )
    assert len(far.replacements) == 2 and far.ignore_links and far.add_to_summary
    text, summary, major = far.multiple_find_and_replace("قط و x", "T", False)
    assert text == "هر و x" and major and "قط" in summary
