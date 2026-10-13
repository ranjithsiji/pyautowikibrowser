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
# Ported from AutoWikiBrowser WikiFunctions/Parse/Templates.cs
# Copyright (C) 2007 Martin Richards and the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Template helpers of Parsers (port of Parse/Templates.cs).

AWB keeps template redirects, dated templates and renamed template parameters (loaded from wiki
pages) in global fields. Here the loaders return immutable values that callers pass back in.
"""

# ruff: noqa: E501

from __future__ import annotations

import functools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from awb_x.core import rx
from awb_x.core import wikiregexes as W
from awb_x.core.rx import DotNetMatch, DotNetRegex
from awb_x.core.site import Namespace, SiteConfig, current_site, use_site
from awb_x.core.textutil import (
    first_letter_case_insensitive,
    nested_template_regex,
    turn_first_to_lower,
    turn_first_to_upper,
    turn_first_to_upper_no_project_check,
)

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

_TlOrTlx = nested_template_regex(["tl", "tlx"])
_TemplateRedirectsR = _R(r"({{ *[Tt]lx? *\|.*}}) *→[ ']*({{ *[Tt]lx? *\| *(.*?) *}})")


def _tl_name(m: DotNetMatch) -> str:
    return m.group(3).strip("|").rstrip("}").strip()


# -- template redirects ([[WP:AWB/TR]]) -----------------------------------------------------------


@dataclass(frozen=True)
class TemplateRedirectRules:
    """Template redirects: each regex matches calls of redirects to the template named."""

    rules: tuple[tuple[DotNetRegex, str], ...] = ()
    all_redirects: frozenset[str] = frozenset()  # AWB's WikiRegexes.AllTemplateRedirectsHS
    all_redirects_regex: DotNetRegex | None = None  # WikiRegexes.AllTemplateRedirects


def load_template_redirects(text: str) -> TemplateRedirectRules:
    """Parse "{{tl|A}}, {{tl|B}} → {{tl|Target}}" lines (the [[WP:AWB/TR]] page)."""
    text = W.UnformattedText.replace(text, "")
    rules: list[tuple[DotNetRegex, str]] = []
    all_redirects: list[str] = []
    for m in _TemplateRedirectsR.matches(text):
        redirects, template_name = m.group(1), m.group(2)
        template_name = _tl_name(_TlOrTlx.match(template_name))
        names = [
            turn_first_to_upper_no_project_check(_tl_name(r)) for r in _TlOrTlx.matches(redirects)
        ]
        rules.append((nested_template_regex(names), template_name))
        all_redirects.extend(names)
    return TemplateRedirectRules(
        tuple(rules),
        frozenset(all_redirects),
        nested_template_regex(all_redirects) if all_redirects else None,
    )


def load_dated_templates(text: str) -> list[str]:
    """Template names (first letter upper) listed with {{tl}} on [[WP:AWB/Dated templates]]."""
    text = W.UnformattedText.replace(text, "")
    return [turn_first_to_upper(_tl_name(m)) for m in _TlOrTlx.matches(text)]


_AcronymCamelCaseTemplate = _R(r"^([A-Z]{3}|[A-Z][a-z]+[A-Z])")


def _template_redirects_me(m: DotNetMatch, new_template_name: str) -> str:
    original = m.group(2)
    if not _AcronymCamelCaseTemplate.is_match(new_template_name):
        if turn_first_to_upper(original) == original:
            new_template_name = turn_first_to_upper(new_template_name)
        else:
            new_template_name = turn_first_to_lower(new_template_name)
    return m.group(1) + new_template_name + m.group(3)


def template_redirects(article_text: str, redirects: TemplateRedirectRules) -> str:
    """Replace calls of template redirects with the target template's name."""
    if redirects.all_redirects_regex is None:
        return article_text
    new_text = _template_redirects_hash_set(article_text, redirects)
    if new_text != article_text:
        from awb_x.core import tools

        return tools.template_to_magic_word(new_text)
    return article_text


def _template_redirects_hash_set(article_text: str, redirects: TemplateRedirectRules) -> str:
    # performance: only templates both used in the article and listed as redirects
    found = [t for t in get_all_templates(article_text) if t in redirects.all_redirects]
    if not found:
        return article_text

    # performance: only the rules that match templates used in the article
    all_found = " ".join("{{" + s + "}}" for s in found)
    rules = [(r, name) for r, name in redirects.rules if r.is_match(all_found)]

    def replace(m2: DotNetMatch) -> str:
        res = m2.value
        before = ""
        while res != before:  # loop to handle nested templates
            before = res
            for r, name in rules:
                res = r.replace(res, lambda m, name=name: _template_redirects_me(m, name))
                # if the name changed and there are no nested templates, done
                if res != m2.value and "{{" not in m2.group(3):
                    break
        return res

    return nested_template_regex(found).replace(article_text, replace)


# -- listing templates ----------------------------------------------------------------------------

_NestedTemplates = _R(r"{{\s*([^{}\|]*)((?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!)))}}")


@functools.lru_cache(maxsize=10)
def _all_templates(article_text: str, site: SiteConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(distinct template names, distinct template calls), at any level of nesting."""
    from awb_x.core import tools

    names: dict[str, None] = {}  # ordered sets, like .NET HashSet without removals
    details: dict[str, None] = {}
    text = article_text
    while True:
        matches = _NestedTemplates.matches(text)
        if not matches:
            break
        details.update(dict.fromkeys(m.value for m in matches))
        names.update(dict.fromkeys(m.group(1) for m in matches))
        # process the template contents again for any (further) nested templates
        text = ",".join(dict.fromkeys(m.group(2) for m in matches))

    exact = (tools.turn_first_to_upper(tools.get_template_name("{{" + s + "}}")) for s in names)
    return tuple(dict.fromkeys(exact)), tuple(details)


def get_all_templates(article_text: str) -> list[str]:
    """Distinct template names used (first letter upper), at any level of nesting."""
    return list(_all_templates(article_text, current_site())[0])


def get_all_template_detail(article_text: str) -> list[str]:
    """Distinct template calls, including nested calls separately."""
    return list(_all_templates(article_text, current_site())[1])


def template_exists(templates_found: Iterable[str], r: DotNetRegex) -> bool:
    """Whether r matches any of the (first letter upper) template names."""
    return any(r.is_match("{{" + s + "|}}") for s in templates_found)


def template_count(templates_found: Iterable[str], r: DotNetRegex) -> int:
    return sum(1 for s in templates_found if r.is_match("{{" + s + "|}}"))


# -- renamed template parameters ([[WP:AWB/Template parameters]]) ---------------------------------


@dataclass(frozen=True)
class TemplateParameters:
    """One rename: in template template_name (first letter lower), old_parameter -> new_parameter."""

    template_name: str
    old_parameter: str
    new_parameter: str


_AwbRenameTemplateParameter = nested_template_regex("AWB rename template parameter")


def load_renamed_template_parameters(text: str) -> list[TemplateParameters]:
    """Parse {{AWB rename template parameter|template|old|new}} calls."""
    from awb_x.core import tools

    text = W.UnformattedText.replace(text, "")
    return [
        TemplateParameters(
            turn_first_to_lower(tools.get_template_argument(m.value, 1)),
            tools.get_template_argument(m.value, 2),
            tools.get_template_argument(m.value, 3),
        )
        for m in _AwbRenameTemplateParameter.matches(text)
    ]


def rename_template_parameters(article_text: str, renamed: Sequence[TemplateParameters]) -> str:
    """Rename old parameter names to new ones in the templates listed, unless the new one is set."""

    if not renamed:
        return article_text

    # performance: only templates used on the page
    used = [turn_first_to_lower(t) for t in get_all_templates(article_text)]
    renamed = [t for t in renamed if t.template_name in used]
    old_params = list(dict.fromkeys(t.old_parameter for t in renamed))
    to_process = list(dict.fromkeys(t.template_name for t in renamed))
    if not to_process:
        return article_text

    r = nested_template_regex(to_process)
    # nested templates are listed separately by get_all_template_detail
    for s in get_all_template_detail(article_text):
        m = r.match(s)
        if m and m.index == 0:
            res = _rename_template_parameters_me(m, renamed, old_params)
            if m.value != res:
                article_text = article_text.replace(m.value, res)
    return article_text


def _rename_template_parameters_me(
    m: DotNetMatch, renamed: Sequence[TemplateParameters], old_params: Sequence[str]
) -> str:
    from awb_x.core import tools

    new_value = m.value
    # performance: intersect the parameters to rename with those used in the template
    pv = tools.get_template_parameter_values(m.value)
    old_used = [p for p in old_params if p in pv]
    if old_used:
        tname = turn_first_to_lower(tools.get_template_name("{{" + m.group(2) + "}}"))
        for p in renamed:
            if (
                p.old_parameter in old_used
                and p.template_name == tname
                and not pv.get(p.new_parameter)
            ):
                new_value = tools.rename_template_parameter(
                    new_value, p.old_parameter, p.new_parameter
                )
    return new_value


# -- extracting templates -------------------------------------------------------------------------


def _extract_template(article_text: str, m: DotNetMatch) -> str:
    the_template = _R(
        rx.escape(m.group(1)) + r"(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}}"
    )
    for n in the_template.matches(article_text):
        if n.index == m.index:
            # AWB returns the first match in the text here, not n
            return the_template.match(article_text).value
    return ""


def get_template(article_text: str, template: str) -> str:
    """The first call of the template (not commented out), or ""."""
    search = _R(
        r"(\{\{\s*" + first_letter_case_insensitive(template) + r"\s*)(?:\||\}|<)", O.SINGLELINE
    )
    # skip commented out templates etc.
    if search.is_match(W.UnformattedText.replace(article_text, "")):
        m = search.match(article_text)
        return _extract_template(article_text, m) if m else ""
    return ""


def get_templates(
    article_text: str, template: str | DotNetRegex | None = None
) -> list[DotNetMatch]:
    """Calls of the named template (or of any template), excluding commented out/nowiki ones."""
    from awb_x.core import tools

    if template is None:
        search = W.NestedTemplates
    elif isinstance(template, str):
        search = nested_template_regex(template)
    else:
        search = template
    # blank out commented out templates etc., so offsets stay those of the real text
    cleaned = tools.replace_with_spaces(article_text, W.UnformattedText)
    original = search.matches(article_text)
    result: list[DotNetMatch] = []
    for m in search.matches(cleaned):
        for m2 in original:
            if m2.index == m.index:
                result.append(m2)
                break
    return result


_Efn = nested_template_regex("efn")


def get_info_box_field_value(article_text: str, fields: str | Sequence[str]) -> str:
    """First non-empty value of the given infobox fields, or ""."""
    from awb_x.core import tools

    if isinstance(fields, str):
        fields = [fields]
    info_box = W.InfoBox.match(article_text).value
    # clean out references and comments
    info_box = W.Comments.replace(info_box, "")
    info_box = W.Refs.replace(info_box, "")
    info_box = _Efn.replace(info_box, "")
    for f in tools.get_template_parameters_values(info_box, fields, True):
        if f:
            return f
    return ""


def remove_template_namespace(article_text: str) -> str:
    """{{Template:Foo}} -> {{Foo}}."""
    from awb_x.core.parsers.parsers import canonicalize_title

    template_ns = current_site().namespaces_case_insensitive[Namespace.TEMPLATE]
    r = _R(r"(\{\{\s*)" + template_ns + r"([^\|]*?)(\s*(?:\}\}|\|))", O.SINGLELINE)
    return r.replace(
        article_text, lambda m: m.group(1) + canonicalize_title(m.group(2)) + m.group(3)
    )


@functools.lru_cache(maxsize=16)
def site_template_redirects(site: SiteConfig) -> TemplateRedirectRules:
    """The wiki's template redirect rules (from SiteConfig.template_redirects_text)."""
    with use_site(site):
        return load_template_redirects(site.template_redirects_text)


@functools.lru_cache(maxsize=16)
def site_renamed_template_parameters(site: SiteConfig) -> tuple[TemplateParameters, ...]:
    """The wiki's renamed template parameters (from SiteConfig.renamed_template_parameters_text)."""
    with use_site(site):
        return tuple(load_renamed_template_parameters(site.renamed_template_parameters_text))
