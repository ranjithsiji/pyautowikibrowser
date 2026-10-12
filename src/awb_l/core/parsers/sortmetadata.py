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
# Ported from AutoWikiBrowser WikiFunctions/Parse/SortMetaData.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Metadata sorting entry point, and merging of portals, hatnotes and section templates (port
of Parse/SortMetaData.cs). en only, except sorting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from awb_l.core import namespace
from awb_l.core import wikiregexes as W
from awb_l.core.parsers import templates as _templates
from awb_l.core.rx import DotNetMatch, DotNetRegex
from awb_l.core.site import Namespace, current_site
from awb_l.core.textutil import nested_template_regex

if TYPE_CHECKING:
    from awb_l.core.parsers.metadatasorter import MetaDataSorter

_R = DotNetRegex

_StackTemplate = nested_template_regex("stack")
SectionMergedTemplates = ("see also", "see also2", "main")
SectionMergedTemplatesR = nested_template_regex(SectionMergedTemplates)
_About = nested_template_regex("about")
_For = nested_template_regex("for")
_Distinguish = nested_template_regex("distinguish")
_AboutPrefix = _R(r"^\|\s*[Aa]bout\s*")
_TrailingBraces = _R(r"}}$")


class SortMetaDataMixin:
    """Instance methods of Parsers from SortMetaData.cs."""

    @property
    def sorter(self) -> MetaDataSorter:  # provided by Parsers
        raise NotImplementedError

    def sort_meta_data(
        self, article_text: str, article_title: str, fix_optional_whitespace: bool = True
    ) -> str:
        """Put the page in [[MOS:ORDER]] (Wikimedia projects only)."""
        if not current_site().is_wikimedia_project:
            return article_text
        return self.sorter.sort(article_text, article_title, fix_optional_whitespace)


def merge_portals(article_text: str) -> str:
    """Merge {{Portal}} templates into one, in See also or where they were (en)."""
    from awb_l.core import summary, tools

    if current_site().lang_code != "en":
        return article_text
    # not if a {{portal}} is within {{stack}}
    stacks = [
        t for t in _templates.get_all_template_detail(article_text) if _StackTemplate.is_match(t)
    ]
    if any(W.PortalTemplate.is_match(s) for s in stacks):
        return article_text

    original = article_text
    portals: list[str] = []
    first_portal = W.PortalTemplate.match(article_text).index
    portal_calls = W.PortalTemplate.matches(article_text)
    for m in portal_calls:
        call = m.value
        # not portal templates with named arguments
        if not tools.get_template_parameter_values(call):
            for i in range(1, tools.get_template_argument_count(call) + 1):
                portals.append(tools.get_template_argument(call, i).strip())
            article_text = _R(_rx_escape(call) + r"\s*(?:\r\n)?").replace(article_text, "")

    # no portal parameters: return now, removing the empty portal template
    if not portals:
        return article_text
    # not enough to merge, or all in one template already
    if len(portals) < 2 or len(portal_calls) == 1:
        return original

    to_add = "".join("|" + p for p in dict.fromkeys(portals))
    s = W.for_site(current_site())
    # merge into the See also section first
    if len(s.SeeAlso.matches(article_text)) == 1:
        return s.SeeAlso.replace(article_text, "$0" + tools.newline("{{Portal" + to_add + "}}"))
    # else at the original place if all portals were in the same section
    if not W.Headings.is_match(original) or summary.modified_section(original, article_text):
        return (
            article_text[:first_portal]
            + "{{Portal"
            + to_add
            + "}}\r\n"
            + article_text[first_portal:]
        )
    return original


def _rx_escape(text: str) -> str:
    from awb_l.core import rx

    return rx.escape(text)


def dablinks(article_text: str) -> str:
    """Tidy and merge hatnotes in the zeroth section: {{about}}s with the same reason, several
    {{for}}s into {{about}}, {{for}} into an existing {{about}}, non-article links escaped,
    several {{distinguish}}s into one (en)."""
    from awb_l.core import tools

    site = current_site()
    if site.lang_code != "en":
        return article_text
    zeroth = tools.get_zeroth_section(article_text)
    rest = article_text[len(zeroth) :]
    text = zeroth
    arg = tools.get_template_argument

    # {{otheruses4}} -> {{about}} (Wikipedia only)
    if site.is_wikipedia_en:
        text = tools.rename_template(text, "otheruses4", "about")

    # "{{about|about x..." -> "{{about|x..."
    for m in _About.matches(text):
        if m.group(3).lstrip("| ").lower().startswith("about"):
            text = text.replace(
                m.value, m.group(1) + m.group(2) + _AboutPrefix.replace(m.group(3), "|")
            )

    # several {{about}} with the same reason into one
    old = ""
    while old != text:
        old = text
        done = False
        for m in _About.matches(text):
            first_arg = arg(m.value, 1)
            for m2 in _About.matches(text):
                if m2.value == m.value:
                    continue
                if arg(m2.value, 1) == first_arg:  # same reason, not itself
                    if arg(m.value, 2) and arg(m2.value, 2):
                        extra = (
                            ("|" + arg(m2.value, 4) + "|" + arg(m2.value, 5))
                            if arg(m2.value, 4)
                            else ""
                        )
                        text = text.replace(
                            m.value,
                            m.value.rstrip("}")
                            + "|"
                            + arg(m2.value, 2)
                            + "|"
                            + arg(m2.value, 3)
                            + extra
                            + "}}",
                        )
                        done = True
                    if not arg(m.value, 2) and not arg(m2.value, 2):
                        text = text.replace(
                            m.value, m.value.rstrip("}") + "|and|" + arg(m2.value, 3) + "}}"
                        )
                        done = True
                elif not arg(m2.value, 1):  # one reason empty
                    if arg(m.value, 2) and arg(m2.value, 2):
                        text = text.replace(
                            m.value,
                            m.value.rstrip("}")
                            + "|"
                            + arg(m2.value, 2)
                            + "|"
                            + arg(m2.value, 3)
                            + "}}",
                        )
                        done = True
                if done:
                    text = text.replace(m2.value, "")
                    break
            if done:
                break

    # several {{for}} into {{about}}: a 2-argument {{for}} becomes {{about}} with no reason
    if len(_For.matches(text)) > 1 and not _About.matches(text):
        for m in _For.matches(text):
            if not arg(m.value, 3):
                text = text.replace(m.value, tools.rename_template(m.value, "about|"))
                break

    # {{for}} into an existing {{about}} with >= 2 arguments
    if len(_About.matches(text)) == 1 and arg(_About.match(text).value, 2):
        for m in _For.matches(text):
            about = _About.match(text).value
            # {{about}} supports up to 9 arguments
            if arg(about, 9):
                continue
            # an {{about}} with 2 arguments needs an extra pipe
            extra = (
                "|"
                if not arg(_About.match(text).value, 3) and not arg(_About.match(text).value, 4)
                else ""
            )
            if not arg(m.value, 3):
                text = text.replace(about, about.rstrip("}") + extra + m.group(3))
            elif not arg(m.value, 4):  # a 3-argument {{for}} needs an extra "and"
                g3 = m.group(3)
                cut = g3.rfind("|") + 1
                text = text.replace(about, about.rstrip("}") + extra + g3[:cut] + "and|" + g3[cut:])
            # 4 arguments: do nothing; otherwise remove the old {{for}}
            if not arg(m.value, 4):
                text = text.replace(m.value, "")

        # a {{for}} with an empty first argument copied over needs "other uses" as the argument
        def other_uses(m2: DotNetMatch) -> str:
            res = m2.value
            if arg(res, 7) and not arg(res, 6):
                i = tools.get_template_argument_index(res, 6)
                res = res[:i] + "other uses" + res[i:]
            return res

        text = _About.replace(text, other_uses)

    # non-mainspace links need escaping in {{about}}
    for m in _About.matches(text):
        call = m.value
        for a in range(1, tools.get_template_argument_count(m.value) + 1):
            value = arg(call, a)
            if value and namespace.determine(value) != Namespace.ARTICLE:
                call = call.replace(value, ":" + value)
        if m.value != call:
            text = text.replace(m.value, call)

    # several {{distinguish}} into one, not when using text=
    old = ""
    while old != text:
        old = text
        done = False
        for m in _Distinguish.matches(text):
            for m2 in _Distinguish.matches(text):
                if (
                    m2.value == m.value
                    or tools.get_template_parameter_value(m.value, "text")
                    or tools.get_template_parameter_value(m2.value, "text")
                ):
                    continue
                text = text.replace(m.value, m.value.rstrip("}") + m2.group(3))
                done = True
                text = text.replace(m2.value, "")
                break
            if done:
                break
    return text + rest


def merge_templates_by_section(article_text: str) -> str:
    """Merge consecutive {{see also}}/{{see also2}}/{{main}} at the start of each section."""
    from awb_l.core import tools

    out: list[str] = []
    for section in tools.split_to_sections(article_text):
        for t in SectionMergedTemplates:
            if len(SectionMergedTemplatesR.matches(section)) < 2:
                break
            section = _merge_templates(section, t)
        out.append(section)
    return "".join(out).rstrip()


def _merge_templates(section_text: str, template_name: str) -> str:
    from awb_l.core import tools

    if current_site().lang_code != "en":
        return section_text
    original = section_text
    template = nested_template_regex(template_name)
    merged_templates = ""

    # outside the zeroth section, drop the heading so the templates are at the start
    heading = ""
    h = W.Headings.match(section_text)
    if h and h.index == 0:
        heading = h.value.rstrip()
        section_text = section_text[h.length :].lstrip()

    merged = 0
    while template.is_match(section_text):
        m = template.match(section_text)
        # only templates at the very start of the section (after the heading)
        if m.index > 0:
            break
        if not merged_templates:
            merged_templates = m.value
        else:
            # named parameters in the second template can't be handled (e.g. l1 in {{main}})
            if tools.get_template_parameter_values(m.value):
                break
            # AWB passes group 3 into the .NET replacement string unescaped; kept as is
            merged_templates = _TrailingBraces.replace(merged_templates, m.group(3))
            merged += 1
        section_text = section_text[m.length :].lstrip()

    # recompose only if something was merged
    if merged > 0:
        return (heading + "\r\n" if heading else "") + merged_templates + "\r\n" + section_text
    return original
