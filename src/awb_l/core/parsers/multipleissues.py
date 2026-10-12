# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# Ported from AutoWikiBrowser WikiFunctions/Parse/MultipleIssuesTemplate.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""{{Multiple issues}} handling (port of Parse/MultipleIssuesTemplate.cs): combine maintenance
tags into it, merge and de-duplicate, and unwrap it when only one tag is left. en only."""

from __future__ import annotations

from awb_l.core import rx
from awb_l.core import wikiregexes as W
from awb_l.core.parsers import templates as _templates
from awb_l.core.rx import DotNetMatch, DotNetRegex
from awb_l.core.site import current_site

_R = DotNetRegex

MinCleanupTagsToCombine = 2  # tags needed to combine into {{multiple issues}}

_TrailingBraces = _R(r"\s*}}$")
_Newlines = _R("(\r\n)+")
_OneEquals = _R(r"^1\s*=\s*")


class MultipleIssuesMixin:
    """Instance methods of Parsers from MultipleIssuesTemplate.cs."""

    def multiple_issues(self, article_text: str) -> str:
        """Combine two or more maintenance tags into {{Multiple issues}} (article and section
        level), tidy existing ones, and unwrap one with a single tag (en only)."""
        from awb_l.core import tools

        if current_site().lang_code != "en":
            return article_text

        # performance: only if relevant templates are found
        all_templates = _templates.get_all_templates(article_text)
        has_mi = _templates.template_exists(all_templates, W.MultipleIssues)
        if has_mi:
            # remove {{multiple issues}} with no tags; fix excess newlines
            details = [
                t for t in _templates.get_all_template_detail(article_text) if " issues" in t
            ]
            if any(
                t != W.MultipleIssues.replace(t, self._multiple_issues_zero_tag) for t in details
            ):
                article_text = W.MultipleIssues.replace(
                    article_text, self._multiple_issues_zero_tag
                )

        section_tags = _templates.template_count(
            all_templates, W.MultipleIssuesSectionMaintenanceTemplates
        )
        if (
            has_mi
            or _templates.template_count(all_templates, W.MultipleIssuesArticleMaintenanceTemplates)
            > 1
            or section_tags > 1
        ):
            out: list[str] = []
            for s in tools.split_to_sections(article_text):
                if not s.startswith("="):
                    new_zero = self._mi_zeroth_section(
                        s, W.MultipleIssuesArticleMaintenanceTemplates
                    )
                    # no changes in the zeroth section and no section tags: nothing left to do
                    if new_zero == s and section_tags == 0:
                        return article_text
                    out.append(new_zero)
                elif section_tags > 0:
                    out.append(
                        self._mi_later_section(
                            s, W.MultipleIssuesSectionMaintenanceTemplates
                        ).lstrip()
                    )
                else:
                    out.append(s)
            return "".join(out).rstrip()
        return article_text

    def _mi_zeroth_section(self, zeroth: str, templates: DotNetRegex) -> str:
        from awb_l.core import tools

        # at most one {{multiple issues}} per section is supported
        mimc = W.MultipleIssues.matches(zeroth)
        existing = len(mimc) > 0
        if len(mimc) > 1:
            zeroth = self._merge_multiple_mi(zeroth)
            mimc = W.MultipleIssues.matches(zeroth)
            existing = len(mimc) > 0
            if len(mimc) > 1:
                return zeroth

        no_mi = tools.replace_with_spaces(zeroth, mimc)
        mi_templates = list(dict.fromkeys(m.value for m in templates.matches(no_mi)))

        # multiple issues with one issue -> single issue tag
        if not mi_templates and existing:
            zeroth = W.MultipleIssues.replace(zeroth, self._multiple_issues_de_dupe)
            return W.MultipleIssues.replace(zeroth, self.multiple_issues_single_tag_me)

        # no {{Multiple issues}} and fewer than the minimum number of tags: nothing to do
        if not existing and len(mi_templates) < MinCleanupTagsToCombine:
            return zeroth

        # add the tags to {{Multiple issues}} (new style), creating it if needed
        if not existing:
            zeroth = "{{Multiple issues}}\r\n" + zeroth
        for t in mi_templates:
            # remove the tag and any trailing spaces
            zeroth = _R(rx.escape(t) + " *").replace(zeroth, "")
            mi = W.MultipleIssues.match(zeroth).value
            new_style = W.NestedTemplates.is_match(mi[2:])
            # AWB passes the tag into the .NET replacement string unescaped; kept as is
            zeroth = zeroth.replace(
                mi, _TrailingBraces.replace(mi, ("" if new_style else "|") + "\r\n" + t + "\r\n}}")
            )

        # clean up again for duplicate tags
        zeroth = W.MultipleIssues.replace(zeroth, self._multiple_issues_de_dupe)
        return W.MultipleIssues.replace(zeroth, self.multiple_issues_single_tag_me)

    def _mi_later_section(self, section: str, templates: DotNetRegex) -> str:
        from awb_l.core import tools

        original = section
        mimc = W.MultipleIssues.matches(section)
        existing = len(mimc) > 0
        # at most one {{multiple issues}} per section is supported
        if len(mimc) > 1:
            return original
        if existing:
            section = tools.replace_with_spaces(section, mimc)

        template_portion = 0
        if W.NestedTemplates.is_match(section):
            template_portion = tools.how_much_starts_with(section, templates, True)

        # multiple issues with one issue -> single issue tag
        if template_portion == 0:
            if existing:
                return W.MultipleIssues.replace(original, self.multiple_issues_single_tag_me)
            return original

        heading = W.Headings.match(section).value.strip()
        portion = section[:template_portion]
        portion_original = original[:template_portion]
        rest = original[template_portion:]
        total = len(templates.matches(portion))

        if not existing and total < MinCleanupTagsToCombine:
            return original

        if existing:  # add each tag to the existing {{multiple issues}}
            new_section = W.MultipleIssues.match(portion_original).value
            if not new_section:  # MI later in the section with text in between: can't handle
                return original
            new_style = W.NestedTemplates.is_match(
                tools.get_template_argument(
                    tools.remove_template_parameter(new_section, "section"), 1
                )
            )
            for m in templates.matches(portion):
                if m.value not in new_section:
                    new_section = _TrailingBraces.replace(
                        new_section, ("" if new_style else "|") + "\r\n" + m.value + "\r\n}}"
                    )
        else:  # create {{multiple issues}} with each tag
            new_section = (
                "{{Multiple issues|section=yes|\r\n"
                + "".join(m.value + "\r\n" for m in templates.matches(portion))
                + "}}"
            )
        return heading + "\r\n" + new_section + "\r\n" + rest

    def _merge_multiple_mi(self, article_text: str) -> str:
        from awb_l.core import tools
        from awb_l.core.parsers import parsers as _parsers

        original = article_text
        collected: list[str] = []

        def take(m: DotNetMatch) -> str:
            tags = tools.get_template_argument(m.value, 1)
            # not a section {{multiple issues}}
            if "{{" in tags or tags == "":
                collected.append(tags)
                return ""
            return m.value

        article_text = W.MultipleIssues.replace(article_text, take)
        # a section {{multiple issues}} was found: do nothing
        if W.MultipleIssues.is_match(article_text):
            return original
        mi_tags = _parsers.deduplicate_maintenance_tags(
            [m.value for m in W.NestedTemplates.matches("".join(collected))]
        )
        return "{{Multiple issues|\r\n" + "\r\n".join(mi_tags) + "\r\n}}" + article_text

    def multiple_issues_single_tag_me(self, m: DotNetMatch) -> str:
        """{{Multiple issues|{{one tag}}}} -> {{one tag}}."""
        from awb_l.core import tools

        res = m.value
        new_value = tools.remove_template_parameter(
            tools.remove_excess_template_pipes(m.value), "section"
        )
        if (
            tools.get_template_argument_count(new_value) == 1
            and len(W.NestedTemplates.matches(tools.get_template_argument(new_value, 1))) == 1
        ):
            res = tools.get_template_argument(new_value, 1)
            # the template may have a 1= parameter
            if res.startswith("1"):
                res = _OneEquals.replace(res, "")
        return res

    def _multiple_issues_de_dupe(self, m: DotNetMatch) -> str:
        from awb_l.core import tools
        from awb_l.core.parsers import parsers as _parsers

        new_value = m.value
        tags = tools.get_template_argument(new_value, 1)
        tag_values = _parsers.deduplicate_maintenance_tags(
            [n.value for n in W.NestedTemplates.matches(tags)]
        )
        new_tags = "\r\n".join(tag_values)
        # only if some duplicate templates were removed
        if new_tags.count("{{") < tags.count("{{"):
            new_value = new_value.replace(tags, new_tags)
        return new_value

    def _multiple_issues_zero_tag(self, m: DotNetMatch) -> str:
        from awb_l.core import tools

        new_value = tools.remove_template_parameter(
            tools.remove_excess_template_pipes(m.value), "section"
        )
        if tools.get_template_argument_count(new_value) == 0:
            return ""
        # excess newlines
        return _Newlines.replace(m.value, "\r\n")
