"""Advanced find and replace (AWB's ReplaceSpecial has no unit tests of its own)."""

from awb_l.core.rx import DotNetOptions as O
from awb_l.rules.replacespecial import (
    InTemplateRule,
    ReplaceSpecial,
    Rule,
    RuleType,
    TemplateParamRule,
)


def test_plain_rule_is_escaped_and_repeated() -> None:
    rs = ReplaceSpecial([Rule(replace="a.b", with_="x")])
    assert rs.apply_rules("a.b acb", "T") == "x acb"

    rs = ReplaceSpecial([Rule(replace="aa", with_="a", num_of_times=3)])
    assert rs.apply_rules("aaaaaaaa", "T") == "a"


def test_regex_rule_with_keywords_and_newlines() -> None:
    rs = ReplaceSpecial([Rule(replace="(%%title%%)", with_="$1\\n", regex=True)])
    assert rs.apply_rules("Foo bar", "Foo") == "Foo\n bar"


def test_conditions() -> None:
    rule = Rule(replace="x", with_="y", if_contains="KEEP", if_not_contains="STOP")
    rs = ReplaceSpecial([rule])
    assert rs.apply_rules("x KEEP", "T") == "y KEEP"
    assert rs.apply_rules("x", "T") == "x"
    assert rs.apply_rules("x KEEP STOP", "T") == "x KEEP STOP"

    rule.if_regex_options = O.IGNORE_CASE
    assert rs.apply_rules("x keep", "T") == "y keep"


def test_inside_template_with_children() -> None:
    child = Rule(replace="b", with_="c")
    rule = Rule(rule_type=RuleType.INSIDE_TEMPLATE, if_contains="foo", children=[child])
    rs = ReplaceSpecial([rule])
    assert rs.apply_rules("b {{foo|b}} {{bar|b}}", "T") == "b {{foo|c}} {{bar|b}}"


def test_in_template_rule_renames_and_runs_children() -> None:
    rule = InTemplateRule(
        template_names=["cite web"],
        do_replace=True,
        replace_with="Cite news",
        children=[TemplateParamRule(param_name="acessdate", new_param_name="access-date")],
    )
    rs = ReplaceSpecial([rule])
    assert (
        rs.apply_rules("{{cite web|acessdate=1}} {{other|acessdate=1}}", "T")
        == "{{Cite news|access-date=1}} {{other|acessdate=1}}"
    )


def test_disabled_rule_does_nothing() -> None:
    rs = ReplaceSpecial([Rule(replace="a", with_="b", enabled=False)])
    assert rs.apply_rules("a", "T") == "a"
    assert ReplaceSpecial().has_rules is False


def test_timed_out_rule_leaves_text_unchanged() -> None:
    rule = Rule(replace="(a|aa)+$", with_="", regex=True)
    rs = ReplaceSpecial([rule], timeout=0.05)
    text = "a" * 40 + "b"
    assert rs.apply_rules(text, "T") == text
    assert rs.timed_out == [rule]
