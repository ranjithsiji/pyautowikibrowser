# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/SubstTemplates.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Template substitution (the engine half of AWB's SubstTemplates form): {{foo|...}} ->
{{subst:foo|...}} for a list of templates, or expanded in place through the wiki
(expand_recursively, needs an expander from pyawb.api)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from pyawb.core import rx
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.tagger import ExpandTemplate
from pyawb.core.rx import DotNetOptions, DotNetRegex
from pyawb.core.site import Namespace, current_site
from pyawb.core.textutil import first_letter_case_insensitive


@dataclass
class SubstTemplates:
    """Substitute the listed templates."""

    expand_recursively: bool = False  # expand through the wiki instead of adding subst:
    ignore_unformatted: bool = False  # leave templates in comments, nowiki etc. alone
    include_comments: bool = False  # with expand_recursively: keep the original call in a comment
    expand_template: ExpandTemplate | None = None  # needed for expand_recursively
    _template_list: tuple[str, ...] = field(default=(), init=False)
    _regexes: dict[DotNetRegex, str] = field(default_factory=dict[DotNetRegex, str], init=False)

    @property
    def template_list(self) -> tuple[str, ...]:
        return self._template_list

    @template_list.setter
    def template_list(self, value: Sequence[str]) -> None:
        self._template_list = tuple(value)
        self._refresh_regexes()

    def clear(self) -> None:
        self._template_list = ()
        self._regexes.clear()

    def _refresh_regexes(self) -> None:
        self._regexes.clear()
        # optional template namespace prefixes to allow
        templ = current_site().namespaces_case_insensitive[Namespace.TEMPLATE]
        if templ.startswith("("):
            close = templ.index(")")
            templ = "(?:" + templ[:close] + "|[Mm]sg" + templ[close:] + r")?\s*"
        else:
            templ = "(?:" + templ + r"|[Mm]sg:|)\s*"

        for s in self._template_list:
            if not s.strip():
                continue
            regex = DotNetRegex(
                r"\{\{\s*"
                + templ
                + first_letter_case_insensitive(rx.escape(s))
                + r"\s*(\|[^\}]*|)}}",
                DotNetOptions.SINGLELINE,
            )
            self._regexes[regex] = "{{subst:" + s.replace("$", "$$") + "$1}}"

    @property
    def no_of_regexes(self) -> int:
        return len(self._regexes)

    @property
    def has_substitutions(self) -> bool:
        return self.no_of_regexes != 0

    @property
    def has_rules(self) -> bool:
        """core.article.TextRules."""
        return self.has_substitutions

    def substitute_templates(self, article_text: str, article_title: str) -> str:
        if not self.has_substitutions:
            return article_text  # nothing to substitute

        remove_unformatted = HideText(True, False, True)
        if self.ignore_unformatted:
            article_text = remove_unformatted.hide_unformatted(article_text)

        if not self.expand_recursively:
            for regex, replacement in self._regexes.items():
                article_text = regex.replace(article_text, replacement)
        elif self.expand_template is not None:
            article_text = self.expand_template(
                article_text, article_title, self._regexes, self.include_comments
            )

        if self.ignore_unformatted:
            article_text = remove_unformatted.add_back_unformatted(article_text)

        return article_text

    def apply(self, article_text: str, article_title: str) -> str:
        """core.article.TextRules."""
        return self.substitute_templates(article_text, article_title)
