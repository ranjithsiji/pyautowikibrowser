"""Replace Special, template substitution, the find and replace Search box and the regex tester
(AWB ReplaceSpecial.cs, SubstTemplates.cs, FindandReplace.cs, RegexTester.cs)."""

from typing import Any

import pytest
from pytestqt.qtbot import QtBot

from pyawb.core.rx import DotNetOptions
from pyawb.rules.findreplace import ReplacementRow
from pyawb.rules.replacespecial import InTemplateRule, Rule, RuleType, TemplateParamRule
from pyawb.ui.find_replace_dialog import FindReplaceDialog, FindReplaceSettings
from pyawb.ui.options_panel import OptionsPanel
from pyawb.ui.regex_tester import RegexTesterDialog
from pyawb.ui.replace_special_dialog import ReplaceSpecialDialog
from pyawb.ui.subst_templates_dialog import SubstSettings, SubstTemplatesDialog
from tests.ui.test_main_loop import window


def dialog(qtbot: QtBot, rules: list[Any] | None = None) -> ReplaceSpecialDialog:
    d = ReplaceSpecialDialog(rules or [])
    qtbot.addWidget(d)
    return d


def top(d: ReplaceSpecialDialog, i: int) -> Any:
    item = d.tree.topLevelItem(i)
    assert item is not None
    return item


def test_new_rules_and_editing(qtbot: QtBot) -> None:
    d = dialog(qtbot)
    d.new_rule(Rule())
    ed = d.rule_editor
    ed.header.name.setText("Cats")
    ed.find_text.setPlainText(r"\bcat\b")
    ed.replace_with.setPlainText("dog")
    ed.is_regex.setChecked(True)
    ed.case.setChecked(False)
    ed.type.setCurrentIndex(1)
    ed.times.setValue(3)
    ed.if_contains.setPlainText("animal")
    d.new_rule(TemplateParamRule(), sub=True)
    d.param_editor.param.setText("accessdate")
    d.param_editor.new_name.setText("access-date")
    rules = d.rules()
    assert len(rules) == 1
    r = rules[0]
    assert isinstance(r, Rule) and r.name == "Cats" and r.replace == r"\bcat\b"
    assert r.regex and r.regex_options & DotNetOptions.IGNORE_CASE
    assert r.rule_type is RuleType.INSIDE_TEMPLATE and r.num_of_times == 3
    assert r.if_contains == "animal"
    child = r.children[0]
    assert isinstance(child, TemplateParamRule) and child.new_param_name == "access-date"


def test_tree_editing_undo_and_clipboard(qtbot: QtBot) -> None:
    d = dialog(qtbot, [Rule(name="A"), InTemplateRule(name="B", template_names=["Cite web"])])
    d.tree.setCurrentItem(top(d, 1))
    assert d.template_editor.templates.count() == 1
    d.move_rule(-1)
    assert [r.name for r in d.rules()] == ["B", "A"]
    d.undo()
    assert [r.name for r in d.rules()] == ["A", "B"]
    d.redo()
    assert [r.name for r in d.rules()] == ["B", "A"]
    d.tree.setCurrentItem(top(d, 0))
    d.copy()
    d.paste()
    assert [r.name for r in d.rules()] == ["B", "B", "A"]
    d.delete()
    assert [r.name for r in d.rules()] == ["B", "A"]


def test_disabled_rules_are_red(qtbot: QtBot) -> None:
    d = dialog(qtbot, [Rule(name="Off", enabled=False), Rule(name="On")])
    off, on = d.tree.topLevelItem(0), d.tree.topLevelItem(1)
    assert off is not None and on is not None
    assert off.background(0).style() != on.background(0).style()


def test_the_dialog_edits_a_copy(qtbot: QtBot) -> None:
    rules: list[Any] = [Rule(name="A")]
    d = dialog(qtbot, rules)
    d.tree.setCurrentItem(top(d, 0))
    d.rule_editor.header.name.setText("Changed")
    d.rules()
    assert rules[0].name == "A"  # Cancel leaves the caller's rules alone


def test_subst_dialog(qtbot: QtBot) -> None:
    d = SubstTemplatesDialog(SubstSettings(templates=("Unsigned",)))
    qtbot.addWidget(d)
    assert d.expand.isChecked()  # AWB's default: expand recursively
    d.templates.setPlainText("Unsigned\n\n  Tl  \n")
    assert d.value().templates == ("Unsigned", "Tl")
    d.expand.setChecked(False)
    assert not d.comment.isEnabled() and not d.value().expand_recursively


def test_options_build_the_engines(qtbot: QtBot) -> None:
    p = OptionsPanel()
    qtbot.addWidget(p)
    p.set_replace_special([Rule(name="A", replace="a", with_="b")])
    p.set_subst_templates(SubstSettings(templates=("Unsigned",), expand_recursively=False))
    assert p.find_replace.isChecked()
    assert "1 advanced rule(s)" in p.far_count.text()
    o = p.loop_options("x", "Alice").process
    assert o.find_and_replace is not None and o.replace_special is not None
    assert o.subst_templates is not None
    assert o.subst_templates.apply("{{unsigned|Bob}}", "X") == "{{subst:Unsigned|Bob}}"
    p.find_replace.setChecked(False)
    o = p.loop_options("x", "Alice").process
    assert o.replace_special is None and o.subst_templates is None


def test_advanced_rules_run_in_the_loop(qtbot: QtBot) -> None:
    w, _ = window(qtbot, {"قط": "حيوان [[أليف|أليف]] صغير."})
    w.options.set_replace_special([Rule(name="R", replace="صغير", with_="كبير")])
    w.start()
    qtbot.waitUntil(lambda: w.current is not None and not w.busy, timeout=5000)
    assert w.editor.toPlainText() == "حيوان [[أليف]] كبير."


def test_find_replace_search(qtbot: QtBot) -> None:
    rows = (ReplacementRow("foo", "bar"), ReplacementRow("baz", "foo"))
    d = FindReplaceDialog(FindReplaceSettings(rows))
    qtbot.addWidget(d)
    d.search.setText("foo")
    assert d.search_go.isEnabled()
    assert d.search_next() and (d.table.currentRow(), d.table.currentColumn()) == (0, 0)
    assert d.search_next() and (d.table.currentRow(), d.table.currentColumn()) == (1, 1)
    d.search.setText("nothing")
    assert not d.search_next()


def test_regex_tester(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    t = RegexTesterDialog(r"(\d+)", "<$1>", text="a 12 b 3")
    qtbot.addWidget(t)
    t.run_find()
    assert t.result_box.toPlainText().startswith("2 match(es)")
    t.run_replace()
    assert t.result_box.toPlainText() == "a <12> b <3>"
    t.find_box.setPlainText("(")
    t.run_find()
    assert t.status.text() and "match" not in t.status.text()
