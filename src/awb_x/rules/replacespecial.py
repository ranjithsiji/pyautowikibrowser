# AWB-X: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-X contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/ReplaceSpecial/*.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Advanced find and replace (AWB's ReplaceSpecial): a tree of rules. A rule's children run on the
text the rule matched (the whole page, or inside each matching template).

Rule kinds: Rule (find and replace, optionally only where some text is or isn't present),
InTemplateRule (run children inside calls of given templates, optionally renaming them) and
TemplateParamRule (rename a template parameter).

Regexes run with a timeout; a rule that times out leaves the text unchanged and is listed in
ReplaceSpecial.timed_out.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from awb_x.core import rx, tools
from awb_x.core import wikiregexes as W
from awb_x.core.parsers import templates as _templates
from awb_x.core.rx import DotNetOptions, DotNetRegex
from awb_x.core.textutil import first_letter_case_insensitive, turn_first_to_upper_no_project_check

DEFAULT_TIMEOUT = 10.0
"""Seconds one rule's regex may run against one page."""


class _Run:
    """State for one apply: the page title and the rules that timed out."""

    def __init__(self, title: str, timeout: float) -> None:
        self.title = title
        self.timeout = timeout
        self.timed_out: list[IRule] = []

    def replace(
        self, rule: IRule, pattern: str, options: DotNetOptions, text: str, replacement: str
    ) -> str:
        try:
            return DotNetRegex(pattern, options).replace(text, replacement, timeout=self.timeout)
        except TimeoutError:
            self.timed_out.append(rule)
            return text

    def is_match(self, rule: IRule, pattern: str, options: DotNetOptions, text: str) -> bool | None:
        try:
            return DotNetRegex(pattern, options).is_match(text, timeout=self.timeout)
        except TimeoutError:
            self.timed_out.append(rule)
            return None


@dataclass
class IRule:
    """A rule in the tree."""

    name: str = ""
    enabled: bool = True
    children: list[IRule] = field(default_factory=list["IRule"])

    def apply(self, text: str, run: _Run) -> str:
        raise NotImplementedError

    def _apply_children(self, text: str, run: _Run) -> str:
        for child in self.children:
            text = child.apply(text, run)
        return text


class RuleType(enum.Enum):
    ON_WHOLE_PAGE = 0
    INSIDE_TEMPLATE = 1


@dataclass
class Rule(IRule):
    """Find and replace, on the whole page or inside each template call, if the text contains
    if_contains and does not contain if_not_contains; repeated num_of_times (at most 100)."""

    name: str = "Rule"
    rule_type: RuleType = RuleType.ON_WHOLE_PAGE
    replace: str = ""
    with_: str = ""
    if_contains: str = ""
    if_not_contains: str = ""
    regex: bool = False
    if_is_regex: bool = False
    num_of_times: int = 1
    if_regex_options: DotNetOptions = DotNetOptions.NONE
    regex_options: DotNetOptions = DotNetOptions.NONE

    def apply(self, text: str, run: _Run) -> str:
        if not text or not self.enabled:
            return text
        for _ in range(min(self.num_of_times, 100)):
            text = self._apply_once(text, run)
        return text

    def _apply_once(self, text: str, run: _Run) -> str:
        if self.rule_type == RuleType.ON_WHOLE_PAGE:
            return self._apply_on(text, run)
        result = text
        for m in _templates.get_all_template_detail(text):
            if self._check_if(m, run):
                result = result.replace(m, self._apply_on(m, run))
        return result

    def _check_if(self, text: str, run: _Run) -> bool:
        ignore_case = bool(self.if_regex_options & DotNetOptions.IGNORE_CASE)

        def contains(needle: str) -> bool | None:
            if self.if_is_regex:
                return run.is_match(self, needle, self.if_regex_options, text)
            return (needle.lower() in text.lower()) if ignore_case else (needle in text)

        if self.if_contains and not contains(self.if_contains):
            return False
        return not (self.if_not_contains and contains(self.if_not_contains) is not False)

    def _apply_on(self, text: str, run: _Run) -> str:
        if not self._check_if(text, run):
            return text
        if self.replace:
            replace = tools.apply_key_words(run.title, self.replace, True)
            with_ = tools.apply_key_words(run.title, self.with_)
            if not self.regex:
                replace = rx.escape(replace)
            # stop \r\n being interpreted literally
            with_ = with_.replace("\\r", "\r").replace("\\n", "\n")
            text = run.replace(self, replace, self.regex_options, text, with_)
        return self._apply_children(text, run)


@dataclass
class InTemplateRule(IRule):
    """Run the children inside each call of the named templates; optionally rename the template
    to replace_with."""

    name: str = "In Template Rule"
    template_names: list[str] = field(default_factory=list[str])
    replace_with: str = ""
    do_replace: bool = False

    def apply(self, text: str, run: _Run) -> str:
        if not self.enabled or not text:
            return text
        for template in self.template_names:
            text = self._apply_inside_template(template, text, run)
        return text

    def _apply_inside_template(self, template: str, text: str, run: _Run) -> str:
        # all template calls in text, including nested, with the given name
        wanted = turn_first_to_upper_no_project_check(template)
        for t in _templates.get_all_template_detail(text):
            if turn_first_to_upper_no_project_check(tools.get_template_name(t)) == wanted:
                text = text.replace(t, self._replace_on(template, t, run))
        return text

    @staticmethod
    def template_used_in_text(template: str, text: str) -> bool:
        """Whether text (the inside of a template call, after "{{") starts with the template name;
        not in comments."""
        if not template:
            return True
        # allow match on spaces or underscores
        pattern = (
            r"^\s*"
            + first_letter_case_insensitive(template).replace(" ", "[ _]+")
            + r"\s*(?:}}|\|)"
        )
        # don't match on comments
        text = W.Comments.replace(text, "")
        return DotNetRegex(pattern).is_match(text)

    def _replace_on(self, template: str, text: str, run: _Run) -> str:
        text = self._apply_children(text, run)
        if self.do_replace and self.replace_with:
            if not template:
                return text
            # AWB's pattern starts with ^([\s]*): it expected the inside of the call, but since
            # AWB switched to GetAllTemplateDetail it gets "{{name|...}}" and never renamed
            # anything. Allowing the braces restores the intended renaming.
            pattern = (
                r"^(\{\{[\s]*|[\s]*)"
                + first_letter_case_insensitive(template)
                + r"([\s]*(?:<!--.*-->)?[\s]*(\}\}|\|))"
            )
            pattern = pattern.replace(" ", "[ _]+")
            replace = tools.apply_key_words(run.title, self.replace_with, False)
            text = run.replace(self, pattern, DotNetOptions.NONE, text, "$1" + replace + "$2")
        return text


@dataclass
class TemplateParamRule(IRule):
    """Rename parameter param_name to new_param_name (param_name is a regex)."""

    name: str = "Template Parameter Rule"
    param_name: str = ""
    new_param_name: str = ""

    def apply(self, text: str, run: _Run) -> str:
        if not text or not self.enabled:
            return text
        pattern = "(\\|[\\s]*)" + self.param_name + "([\\s]*=)"
        text = run.replace(
            self, pattern, DotNetOptions.NONE, text, "$1" + self.new_param_name + "$2"
        )
        return self._apply_children(text, run)


@dataclass
class ReplaceSpecial:
    """The rule tree (the top-level rules, in order)."""

    rules: list[IRule] = field(default_factory=list[IRule])
    timeout: float = DEFAULT_TIMEOUT
    timed_out: list[IRule] = field(default_factory=list[IRule])

    @property
    def no_of_rules(self) -> int:
        return len(self.rules)

    @property
    def has_rules(self) -> bool:
        return bool(self.rules)

    def apply_rules(self, text: str, title: str) -> str:
        run = _Run(title, self.timeout)
        for r in self.rules:
            text = r.apply(text, run)
        self.timed_out = run.timed_out
        return text

    def apply(self, article_text: str, article_title: str) -> str:
        """core.article.TextRules."""
        return self.apply_rules(article_text, article_title)
