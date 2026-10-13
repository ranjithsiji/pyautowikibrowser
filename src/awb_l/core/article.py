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
# Ported from AutoWikiBrowser WikiFunctions/Article/Article.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""One page's processing pipeline (port of WikiFunctions/Article/Article.cs).

An Article holds a page's text while AWB's processing steps run over it: find and replace, typo
fixing, tagging, categorisation and the general fixes. Each step logs why it changed the text and
may mark the page to be skipped.

Left out (they need the wiki or the UI, and belong in api/ or ui/): OnlyCosmeticChanged (parses
the page through the API), Disambiguate, Move, Delete, Protect. Plugins call
plugin_change_article_text and set plugin_edit_summary/plugin_skip directly.
"""

# ruff: noqa: E501

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol

from awb_l.core import namespace, tools
from awb_l.core import wikiregexes as W
from awb_l.core.parsers import citetemplates as _cite
from awb_l.core.parsers import fixheadings as _fixheadings
from awb_l.core.parsers import fixsyntax as _fixsyntax
from awb_l.core.parsers import parsers as _parsers
from awb_l.core.parsers import references as _refs
from awb_l.core.parsers import tagger as _tagger
from awb_l.core.parsers import templates as _templates
from awb_l.core.parsers import unbalancedbrackets as _ub
from awb_l.core.parsers import wikilinks as _wikilinks
from awb_l.core.parsers.categorydefaultsort import (
    change_to_default_sort,
    fix_categories,
    re_categoriser,
    remove_category_no_change,
)
from awb_l.core.parsers.hidetext import HideText
from awb_l.core.parsers.parsers import DateLocale, Parsers
from awb_l.core.rx import DotNetOptions, DotNetRegex
from awb_l.core.site import Namespace, current_site

# -- options and collaborators ---------------------------------------------------------------------


@dataclass
class SkipOptions:
    """Which "skip if no change" options are on (AWB's ISkipOptions)."""

    skip_no_unicode: bool = False
    skip_no_tag: bool = False
    skip_no_header_error: bool = False
    skip_no_bold_title: bool = False
    skip_no_bulleted_link: bool = False
    skip_no_bad_link: bool = False
    skip_no_default_sort_added: bool = False
    skip_no_user_talk_templates_substd: bool = False
    skip_no_cite_template_dates_fixed: bool = False
    skip_no_people_categories_fixed: bool = False


class ImageReplaceOptions(enum.Enum):
    NO_ACTION = 0
    REPLACE = 1
    REMOVE = 2
    COMMENT = 3


class CategorisationOptions(enum.Enum):
    """Values as in AWB (settings files store them as numbers)."""

    NO_ACTION = 0
    RE_CAT = 1
    ADD_CAT = 2
    REMOVE_CAT = 3


class TypoFixer(Protocol):
    """awb_l.rules.typos.RegExTypoFix."""

    def perform_typo_fixes(
        self, article_text: str, article_title: str
    ) -> tuple[str, bool, str]: ...


class FindAndReplacer(Protocol):
    """awb_l.rules.findreplace.FindAndReplace."""

    def has_processing_replacements(self, after: bool) -> bool: ...

    @property
    def has_after_processing_replacements(self) -> bool: ...

    def multiple_find_and_replace(
        self, article_text: str, title: str, before_or_after: bool, edit_summary: str = ""
    ) -> tuple[str, str, bool]: ...


class TextRules(Protocol):
    """Advanced find and replace (ReplaceSpecial) or template substitution (SubstTemplates)."""

    @property
    def has_rules(self) -> bool: ...

    def apply(self, article_text: str, article_title: str) -> str: ...


class CustomModule(Protocol):
    """A custom module (AWB's IModule): returns (text, edit summary, skip)."""

    def process_article(
        self, article_text: str, article_title: str, namespace: int
    ) -> tuple[str, str, bool]: ...


class _FaRChange(enum.Enum):
    NOT_RUN = 0
    NO_CHANGE = 1
    MINOR_CHANGE = 2
    MAJOR_CHANGE = 3


@dataclass
class ArticleLog:
    """What happened to a page (AWB's AWBLogListener): changes with their reasons, and skipping."""

    entries: list[tuple[str, str]] = field(
        default_factory=list[tuple[str, str]]
    )  # (changed by, reason)
    skipped: bool = False
    skip_reason: str = ""

    def write_line(self, reason: str, changed_by: str) -> None:
        self.entries.append((changed_by, reason))

    def awb_skipped(self, reason: str) -> None:
        self.skipped = True
        self.skip_reason = reason

    def skipped_article(self, skipped_by: str, reason: str) -> None:
        self.skipped = True
        self.skip_reason = f"{skipped_by}: {reason}"


_WikiProjectBannerShellKnowns = (
    "blp",
    "blpo",
    "activepol",
    "collapsed",
    "demo_page",
    "1",
    "living",
    "class",
    "listas",
    "vital",
)
_MultipleIssuesKnowns = ("section", "collapsed")
_LinksInHeadings = DotNetRegex(
    r"^((={1,4})[^\[\]\{\}\|=\r\n]*)\[\[(?:[^\[\]\{\}\|=\r\n]+\|)?([^\[\]\{\}\|\r\n]+)(?<!.*(?:File|Image):.*)\]\]([^\{\}=\r\n]*\2)",
    DotNetOptions.MULTILINE,
)


# -- Article ---------------------------------------------------------------------------------------


class Article:
    """A wiki page being processed."""

    def __init__(self, name: str, text: str = "", namespace_key: int | None = None) -> None:
        self.name = name[: name.index("#")] if "#" in name else name
        self.namespace_key = namespace.determine(name) if namespace_key is None else namespace_key
        self._article_text = text
        self._original_article_text = text
        self.display_title: str | None = None
        self.log = ArticleLog()
        self.plugin_edit_summary = ""
        self.plugin_skip = False
        self.pre_processed = False
        self._summary: list[str] = []
        self._before = _FaRChange.NOT_RUN
        self._after = _FaRChange.NOT_RUN
        self._categorisation_made_changes = False
        self._custom_module_made_changes = False
        self._general_fixes_caused_change = False
        self._text_already_changed = False
        self._general_fixes_significant_change = False
        self._universal_general_fixes_caused_change = False
        self._after_general_fixes_article_text = ""
        self._hider_hide_ext_links_images = HideText(True, True, True)

    def __repr__(self) -> str:
        return f"Article({self.name!r})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> bool:
        # AWB's Article.Equals: another Article, or a string, with the same name
        if isinstance(other, str):
            return self.name == other
        return isinstance(other, Article) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __lt__(self, other: Article) -> bool:
        return self.compare_to(other) < 0

    def compare_to(self, other: Article) -> int:
        """String.CompareOrdinal of the names (UTF-16 code units), MediaWiki's sort order."""
        a = self.name.encode("utf-16-le")
        b = other.name.encode("utf-16-le")
        for i in range(0, min(len(a), len(b)), 2):
            ca = int.from_bytes(a[i : i + 2], "little")
            cb = int.from_bytes(b[i : i + 2], "little")
            if ca != cb:
                return ca - cb
        return (len(a) - len(b)) // 2

    # -- text and summary --------------------------------------------------------------------------

    @property
    def article_text(self) -> str:
        """The current text (change it through the *_change_article_text methods)."""
        return self._article_text

    @property
    def original_article_text(self) -> str:
        return self._original_article_text

    @property
    def namespaceless_name(self) -> str:
        return tools.remove_namespace_string(self.name)

    @property
    def url_encoded_name(self) -> str:
        from awb_l.core.textutil import wiki_encode

        return wiki_encode(self.name)

    @property
    def edit_summary(self) -> str:
        return "".join(self._summary)

    def reset_edit_summary(self) -> None:
        self._summary.clear()

    def _append_to_summary(self, new_text: str) -> None:
        if not new_text.strip():
            return
        comma = "، " if current_site().lang_code in ("ar", "arz", "fa") else ", "
        self._summary.append(comma + new_text if self._summary else new_text)

    @property
    def skip_article(self) -> bool:
        return self.log.skipped

    def awb_skip(self, reason: str) -> None:
        self.log.awb_skipped(reason)

    def change_article_text(
        self, changed_by: str, reason: str, new_text: str, check_if_changed: bool
    ) -> None:
        """Change the text and log why; with check_if_changed, do nothing if it is the same."""
        if check_if_changed and new_text == self._article_text:
            return
        self._article_text = new_text
        self.log.write_line(reason, changed_by)

    def awb_change_article_text(
        self,
        reason: str,
        new_text: str,
        check_if_changed: bool,
        performs_significant_changes: bool = False,
    ) -> None:
        if performs_significant_changes and new_text != self._article_text:
            self._general_fixes_significant_change = True
        self.change_article_text("AWB", reason, new_text, check_if_changed)

    def plugin_change_article_text(self, new_text: str) -> None:
        self._article_text = new_text

    def append_plugin_edit_summary(self) -> None:
        if self.plugin_edit_summary:
            self._append_to_summary(self.plugin_edit_summary.strip())
            self.plugin_edit_summary = ""

    def hide_text(self, remove_text: HideText) -> None:
        self._article_text = remove_text.hide(self._article_text)

    def unhide_text(self, remove_text: HideText) -> None:
        self._article_text = remove_text.add_back(self._article_text)

    def hide_more_text(self, remove_text: HideText) -> None:
        self._article_text = remove_text.hide_more(self._article_text)

    def unhide_more_text(self, remove_text: HideText) -> None:
        self._article_text = remove_text.add_back_more(self._article_text)

    # -- page properties ---------------------------------------------------------------------------

    @property
    def is_stub(self) -> bool:
        return _parsers.is_stub(self._article_text)

    @property
    def has_diacritics_in_title(self) -> bool:
        return tools.remove_diacritics(self.name) != self.name

    @property
    def article_is_about_a_person(self) -> bool:
        site = current_site()
        return (
            site.project == "wikipedia"
            and site.lang_code in ("en", "simple")
            and _parsers.is_article_about_a_person(self._article_text, self.name, True)
        )

    @property
    def has_stub_template(self) -> bool:
        return _parsers.has_stub_template(self._article_text)

    @property
    def has_info_box(self) -> bool:
        return _parsers.has_infobox(self._article_text)

    @property
    def is_in_use(self) -> bool:
        return _parsers.is_in_use(self._article_text)

    @property
    def has_sic_tag(self) -> bool:
        return _parsers.has_sic_tag(self._article_text)

    @property
    def has_dead_links(self) -> bool:
        return _parsers.has_dead_links(self._article_text)

    @property
    def has_target_less_links(self) -> bool:
        return _parsers.has_target_less_links(self._article_text)

    @property
    def has_double_pipe_links(self) -> bool:
        return _parsers.has_double_pipe_links(self._article_text)

    @property
    def has_morefootnotes_and_many_references(self) -> bool:
        return _parsers.has_morefootnotes_and_many_references(self._article_text)

    @property
    def is_disambiguation_page(self) -> bool:
        """A disambiguation page (en only)."""
        site = current_site()
        if site.lang_code not in ("en", "simple") or self.namespace_key != Namespace.ARTICLE:
            return False
        s = W.for_site(site)
        return any(
            s.Disambigs.is_match("{{" + t + "|}}")
            for t in _templates.get_all_templates(self._article_text)
        ) and s.Disambigs.is_match("".join(_templates.get_all_template_detail(self._article_text)))

    @property
    def is_sia_page(self) -> bool:
        """A set index article (en only)."""
        site = current_site()
        return (
            site.lang_code in ("en", "simple")
            and self.namespace_key == Namespace.ARTICLE
            and W.for_site(site).SIAs.is_match(
                "".join(_templates.get_all_template_detail(self._article_text))
            )
        )

    @property
    def is_disambiguation_page_with_refs(self) -> bool:
        return self.is_disambiguation_page and W.Refs.is_match(self._article_text)

    @property
    def has_ref_after_reflist(self) -> bool:
        return _parsers.has_ref_after_reflist(self._article_text)

    @property
    def has_named_references(self) -> bool:
        return _refs.has_named_references(self._article_text)

    @property
    def has_bare_references(self) -> bool:
        return _parsers.has_bare_references(self._article_text)

    @property
    def has_ambiguous_cite_template_dates(self) -> bool:
        return _cite.ambiguous_cite_template_dates(self._article_text)

    @property
    def has_see_also_after_notes_references_or_external_links(self) -> bool:
        return (
            self.namespace_key == Namespace.ARTICLE
            and _parsers.has_see_also_after_notes_references_or_external_links(self._article_text)
        )

    @property
    def can_do_general_fixes(self) -> bool:
        """Articles, categories, sandboxes, template documentation, and some wikis' list namespaces."""
        lang = current_site().lang_code
        ns = self.namespace_key
        return (
            ns in (Namespace.ARTICLE, Namespace.CATEGORY)
            or "Sandbox" in self.name
            or "sandbox" in self.name
            or "/doc" in self.name
            or (lang == "es" and ns == 104)  # Anexo
            or (lang == "ar" and ns == 104)
            or (lang == "pt" and ns == 102)  # Anexo
        )

    @property
    def can_do_talk_general_fixes(self) -> bool:
        return self.namespace_key in (Namespace.TALK, Namespace.CATEGORY_TALK)

    @property
    def is_missing_references_display(self) -> bool:
        return _parsers.is_missing_references_display(self._article_text)

    @property
    def date_locale(self) -> DateLocale:
        return _parsers.determine_predominant_date_locale(self._article_text)

    @property
    def is_redirect(self) -> bool:
        return tools.is_redirect(self._article_text)

    # -- change classification ---------------------------------------------------------------------

    @property
    def only_white_space_changed(self) -> bool:
        return W.WhiteSpace.replace(self.original_article_text, "") == W.WhiteSpace.replace(
            self._article_text, ""
        )

    @property
    def only_casing_changed(self) -> bool:
        return tools.case_insensitive_string_compare(self.original_article_text, self._article_text)

    @property
    def only_white_space_and_casing_changed(self) -> bool:
        return tools.case_insensitive_string_compare(
            W.WhiteSpace.replace(self.original_article_text, ""),
            W.WhiteSpace.replace(self._article_text, ""),
        )

    @property
    def only_general_fixes_changed(self) -> bool:
        return (
            self._general_fixes_caused_change
            and not self.find_and_replace_made_changes
            and not self._custom_module_made_changes
            and not self._categorisation_made_changes
            and self._article_text == self._after_general_fixes_article_text
        )

    @property
    def find_and_replace_made_changes(self) -> bool:
        changed = (_FaRChange.MAJOR_CHANGE, _FaRChange.MINOR_CHANGE)
        return self._after in changed or self._before in changed

    @property
    def only_minor_general_fixes_changed(self) -> bool:
        return self.only_general_fixes_changed and not self._general_fixes_significant_change

    @property
    def no_article_text_changed(self) -> bool:
        return self.original_article_text == self._article_text

    # -- checks that report positions {index: length} ----------------------------------------------

    def unbalanced_brackets(self) -> dict[int, int]:
        """The first unbalanced bracket (of the zeroth section only, on talk pages)."""
        page_text = self._article_text
        if namespace.is_talk(self.name):
            page_text = W.ZerothSection.match(page_text).value
        index, length = _ub.unbalanced_brackets(page_text)
        return {index: length} if index > -1 else {}

    def bad_cite_parameters(self) -> dict[int, int]:
        return _cite.bad_cite_parameters(self._article_text)

    def targetless_links(self) -> dict[int, int]:
        return _parsers.target_less_links(self._article_text)

    def doublepipe_links(self) -> dict[int, int]:
        return _parsers.double_pipe_links(self._article_text)

    def user_signature(self) -> dict[int, int]:
        return _parsers.user_signature(self._article_text)

    def duplicate_wiki_project_banner_shell_parameters(self) -> dict[int, int]:
        if self.namespace_key == Namespace.TALK:
            return tools.duplicate_template_parameters(
                W.WikiProjectBannerShellTemplate.match(self._article_text).value
            )
        return {}

    def unknown_wiki_project_banner_shell_parameters(self) -> list[str]:
        if self.namespace_key == Namespace.TALK:
            return tools.unknown_template_parameters(
                W.WikiProjectBannerShellTemplate.match(self._article_text).value,
                _WikiProjectBannerShellKnowns,
            )
        return []

    def unknown_multiple_issues_parameters(self) -> list[str]:
        if self.namespace_key == Namespace.ARTICLE and W.MultipleIssues.is_match(
            "".join(_templates.get_all_template_detail(self._article_text))
        ):
            return tools.unknown_template_parameters(
                W.MultipleIssues.match(self._article_text).value, _MultipleIssuesKnowns
            )
        return []

    def wiki_linked_headers(self) -> dict[int, int]:
        """Headings containing wikilinks (mainspace only)."""
        if self.namespace_key != Namespace.ARTICLE:
            return {}
        return {m.index: m.length for m in _LinksInHeadings.matches(self._article_text)}

    def unclosed_tags(self) -> dict[int, int]:
        return _ub.unclosed_tags(self._article_text)

    def dead_links(self) -> dict[int, int]:
        return _parsers.dead_links(self._article_text)

    def ambiguous_cite_template_dates(self) -> dict[int, int]:
        return _cite.ambig_cite_template_dates(self._article_text)

    # -- processing steps --------------------------------------------------------------------------

    def unicodify(self, skip_if_no_change: bool, parsers: Parsers, remove_text: HideText) -> None:
        """Convert HTML entities to characters."""
        # performance: only run slow HideMore if unicodify of raw text results in changes
        _, no_change = parsers.unicodify_no_change(self._article_text)
        if not no_change:
            self.hide_more_text(remove_text)
            str_temp, no_change = parsers.unicodify_no_change(self._article_text)
            self.awb_change_article_text("Page Unicodified", str_temp, False)
            self.unhide_more_text(remove_text)
        elif skip_if_no_change:
            self.awb_skip("No Unicodification")

    def update_images(
        self,
        option: ImageReplaceOptions,
        image_replace_text: str,
        image_with_text: str,
        skip_if_no_change: bool,
    ) -> None:
        """Remove, replace or comment out a file."""
        image_replace_text = image_replace_text.strip()
        image_with_text = image_with_text.strip()
        if not image_replace_text or option == ImageReplaceOptions.NO_ACTION:
            return
        if option == ImageReplaceOptions.REPLACE:
            if not image_with_text:
                return
            str_temp, no_change = _parsers.replace_image_no_change(
                image_replace_text, image_with_text, self._article_text
            )
        else:
            comment_out = option == ImageReplaceOptions.COMMENT
            str_temp, no_change = _parsers.remove_image_no_change(
                image_replace_text, self._article_text, comment_out, image_with_text
            )

        if no_change and skip_if_no_change:
            self.awb_skip("No File Changed")
        elif not no_change:
            self.awb_change_article_text("File replacement applied", str_temp, False)

    def categorisation(
        self,
        option: CategorisationOptions,
        parsers: Parsers,
        skip_if_no_change: bool,
        category_text: str,
        category_text2: str,
        remove_sort_key: bool,
    ) -> None:
        """Add, remove or replace a category."""
        category_text = category_text.strip()
        category_text2 = category_text2.strip()
        if not category_text or option == CategorisationOptions.NO_ACTION:
            return
        action = ""
        if option == CategorisationOptions.ADD_CAT:
            str_temp, no_change = parsers.add_category_no_change(
                category_text, self._article_text, self.name
            )
            action = "Added " + category_text
        elif option == CategorisationOptions.RE_CAT:
            if not category_text2:
                return
            str_temp, no_change = re_categoriser(
                category_text, category_text2, self._article_text, remove_sort_key
            )
        else:
            str_temp, no_change = remove_category_no_change(category_text, self._article_text)
            action = "Removed " + category_text

        if no_change and skip_if_no_change:
            self.awb_skip("No Category Changed")
        elif not no_change:
            self.awb_change_article_text(action, str_temp, False)
            self._categorisation_made_changes = True

    def do_far_skips(self, find_and_replace: FindAndReplacer) -> None:
        """Skip checks for find and replace."""
        if _FaRChange.MAJOR_CHANGE in (self._before, self._after):
            return
        if _FaRChange.MINOR_CHANGE in (self._before, self._after):
            self.awb_skip("Only minor Find And Replace Changes")
        elif (
            (
                self._before == _FaRChange.NO_CHANGE
                and not find_and_replace.has_after_processing_replacements
            )
            or (self._before == _FaRChange.NOT_RUN and self._after == _FaRChange.NO_CHANGE)
            or (self._before == _FaRChange.NO_CHANGE and self._after == _FaRChange.NO_CHANGE)
        ):
            self.awb_skip("No Find And Replace Changes")

    def _set_far_change(self, after: bool, value: _FaRChange) -> None:
        if after:
            self._after = value
        else:
            self._before = value

    def perform_find_and_replace(
        self,
        find_and_replace: FindAndReplacer,
        subst_templates: TextRules | None,
        replace_special: TextRules | None,
        skip_if_no_change: bool,
        skip_if_only_minor_change: bool,
        only_apply_after: bool,
    ) -> None:
        """Run find and replace (and, before general fixes, advanced rules and template
        substitution)."""
        if (
            not find_and_replace.has_processing_replacements(only_apply_after)
            and not (replace_special is not None and replace_special.has_rules)
            and not (subst_templates is not None and subst_templates.has_rules)
        ):
            return

        changed_text = tools.convert_from_local_line_endings(self._article_text)
        original_text = changed_text
        changed_text, edit_summary, major_changes_made = find_and_replace.multiple_find_and_replace(
            changed_text, self.name, only_apply_after, ""
        )
        far_made_major_changes = major_changes_made and original_text != changed_text
        adv_far_made_changes = False

        changed_text_by_adv_far = changed_text
        if not only_apply_after:  # only run "before"
            if replace_special is not None:
                changed_text_by_adv_far = replace_special.apply(changed_text, self.name)
            if subst_templates is not None:
                changed_text_by_adv_far = subst_templates.apply(changed_text_by_adv_far, self.name)
            adv_far_made_changes = changed_text_by_adv_far != changed_text
            if not far_made_major_changes and adv_far_made_changes:
                # override minor changes if advanced replacements did something, so we don't skip
                self._set_far_change(False, _FaRChange.MAJOR_CHANGE)

        if original_text == changed_text_by_adv_far:
            if skip_if_no_change:
                self._set_far_change(only_apply_after, _FaRChange.NO_CHANGE)
            # no changes, so nothing to change in article text (but we're not skipping either)
            return
        if not far_made_major_changes and not adv_far_made_changes and skip_if_only_minor_change:
            self._set_far_change(only_apply_after, _FaRChange.MINOR_CHANGE)
        else:
            self._set_far_change(only_apply_after, _FaRChange.MAJOR_CHANGE)

        self.awb_change_article_text(
            "Find and replace applied" + edit_summary,
            tools.convert_to_local_line_endings(changed_text_by_adv_far),
            True,
        )
        self._append_to_summary(edit_summary)

    def perform_typo_fixes(self, regex_typos: TypoFixer, skip_if_no_change: bool) -> None:
        """Fix spelling mistakes."""
        str_temp, no_change, tmp_edit_summary = regex_typos.perform_typo_fixes(
            self._article_text, self.name
        )
        if no_change and skip_if_no_change:
            self.awb_skip("No typo fixes")
        elif not no_change:
            self.awb_change_article_text(tmp_edit_summary, str_temp, False)
            self._append_to_summary(tmp_edit_summary)

    def auto_tag(
        self, parsers: Parsers, skip_if_no_change: bool, restrict_orphan_tagging: bool
    ) -> None:
        """Add or remove cleanup tags (stub, uncategorised, orphan ...)."""
        str_temp, no_change, tmp_edit_summary = parsers.tagger_no_change(
            self._article_text, self.name, restrict_orphan_tagging
        )
        if skip_if_no_change and no_change:
            self.awb_skip("No Tag changed")
        elif not no_change:
            self.awb_change_article_text(
                "Auto tagger changes applied " + tmp_edit_summary, str_temp, False
            )
            self._append_to_summary(tmp_edit_summary)

    def _minor_fixes(self, lang_code: str, skip_if_no_change: bool) -> bool:
        text, _ = _parsers.interwiki_conversions_no_change(self._article_text)
        self.awb_change_article_text("Fixed interwikis", text, True)
        any_changes = False

        if lang_code in ("en", "simple"):
            str_temp = self._article_text
            ns = namespace.determine(self.name)
            # do not subst on Template documentation pages, Template sandbox pages or commons
            # category pages
            if not (
                ns == Namespace.TEMPLATE
                and (self.name.endswith("/doc") or self.name.endswith("/sandbox"))
            ) and not (current_site().project == "commons" and ns == Namespace.CATEGORY):
                str_temp = _parsers.conversions(self._article_text)

            str_temp = _fixsyntax.fix_syntax_mainspace(str_temp, self.name)
            str_temp = _parsers.fix_living_things_related_dates(str_temp)
            str_temp, no_change = _fixheadings.fix_headings_no_change(str_temp, self.name)

            any_changes = self._article_text != str_temp

            if skip_if_no_change and self._article_text == str_temp:
                self.awb_skip("No header errors")
            elif not no_change:
                self.awb_change_article_text("Fixed header errors", str_temp, True)
            else:
                self.awb_change_article_text("Fixed minor formatting issues", str_temp, True)
                if skip_if_no_change:
                    self.awb_skip("No header errors")
        return any_changes

    def set_default_sort(
        self, lang_code: str, skip_if_no_change: bool, restrict_defaultsort_addition: bool = True
    ) -> None:
        """Add {{DEFAULTSORT}} if needed, clean diacritics in sort keys (en)."""
        site = current_site()
        if (
            lang_code in ("en", "simple")
            and site.is_wikimedia_project
            and not site.is_wikimedia_monolingual_project
        ):
            str_temp, no_change = change_to_default_sort(
                self._article_text, self.name, restrict_defaultsort_addition
            )
            if skip_if_no_change and no_change:
                self.awb_skip("No DefaultSort Added")
            elif not no_change:
                self.awb_change_article_text("DefaultSort Added/Diacritics cleaned", str_temp, True)

    def cite_template_dates(self, parsers: Parsers, skip_if_no_change: bool) -> None:
        str_temp, no_change = _cite.cite_template_dates_no_change(self._article_text)
        if skip_if_no_change and no_change:
            self.awb_skip("No Citation template dates fixed")
        elif not no_change:
            self.awb_change_article_text("Citation template dates fixed", str_temp, True)

    def fix_people_categories(self, parsers: Parsers, skip_if_no_change: bool) -> None:
        """Birth/death/living people categories (en)."""
        str_temp, no_change = parsers.fix_people_categories_no_change(
            self._article_text, self.name, True
        )
        str_temp, no_change2 = _parsers.living_people_no_change(str_temp, self.name)

        # call conversions if FixPeopleCategories made changes as may now require
        # {{multiple issues}} template updates etc.
        if not no_change:
            str_temp = _parsers.conversions(str_temp)
        if not no_change2:
            no_change = False

        if skip_if_no_change and no_change:
            self.awb_skip("No human category changes")
        elif not no_change:
            self.awb_change_article_text("Human category changes", str_temp, True)

    def fix_links(self, skip_if_no_change: bool) -> None:
        str_temp, no_change = _wikilinks.fix_links(self._article_text, self.name)
        if no_change and skip_if_no_change:
            self.awb_skip("No bad links")
        elif not no_change:
            self.awb_change_article_text("Fixed links", str_temp, False)

    def bullet_external_links(self, skip_if_no_change: bool) -> None:
        str_temp, no_change = _parsers.bullet_external_links_no_change(self._article_text)
        if skip_if_no_change and no_change:
            self.awb_skip("No missing bulleted links")
        elif not no_change:
            self.awb_change_article_text("Bulleted external links", str_temp, False)

    def embolden_titles(self, parsers: Parsers, skip_if_no_change: bool) -> None:
        str_temp, no_change = parsers.bold_title(self._article_text, self.name)
        if skip_if_no_change and no_change:
            self.awb_skip("No Titles to embolden")
        elif not no_change:
            self.awb_change_article_text("Emboldened titles", str_temp, False)

    def send_page_to_custom_module(self, module: CustomModule) -> None:
        str_temp, str_edit_summary, skip_article = module.process_article(
            self._article_text, self.name, self.namespace_key
        )
        self._custom_module_made_changes = str_temp != self._article_text
        # take updated article text even if skip true, so that in re-parse mode updates are taken
        self.awb_change_article_text("Custom module", str_temp, True)
        if not skip_article:
            if str_edit_summary:
                self.plugin_edit_summary = str_edit_summary.strip()
            self.plugin_skip = False
            self.append_plugin_edit_summary()
        else:
            self.awb_skip("Skipped by custom module (" + str_edit_summary + ")")

    # -- general fixes -----------------------------------------------------------------------------

    def perform_general_fixes(
        self,
        parsers: Parsers,
        remove_text: HideText,
        skip: SkipOptions,
        replace_reference_tags: bool,
        restrict_defaultsort_addition: bool,
        no_mos_compliance_fixes: bool,
    ) -> None:
        """The general fixes, in AWB's order."""
        site = current_site()
        self._before_general_fixes_text_changed()

        # two flags for FixDates functionality
        zeroth = W.ZerothSection.match(self._article_text).value
        circa_link = W.CircaLinkTemplate.is_match(self._article_text)
        floruit = "[[floruit|fl.]]" not in zeroth and W.UnlinkedFloruit.is_match(zeroth)

        self.hide_more_text(self._hider_hide_ext_links_images)

        self.awb_change_article_text(
            "Fix temperatures", _parsers.fix_temperatures(self._article_text), True
        )

        if not no_mos_compliance_fixes:
            self.awb_change_article_text(
                "Fix non-breaking spaces", parsers.fix_non_breaking_spaces(self._article_text), True
            )
            self.awb_change_article_text(
                "Mdashes", parsers.mdashes(self._article_text, self.name), True
            )
            self.awb_change_article_text(
                "Fix Date Ordinals/Of",
                parsers.fix_date_ordinals_and_of(self._article_text, self.name),
                True,
                True,
            )

        self.awb_change_article_text(
            "FixBrParagraphs", parsers.fix_br_paragraphs(self._article_text).strip(), True
        )

        if not tools.is_redirect(self._article_text):
            self.awb_change_article_text(
                "Fix dates 1",
                parsers.fix_dates_b(self._article_text, circa_link, floruit).strip(),
                True,
            )

        self.unhide_more_text(self._hider_hide_ext_links_images)

        self.hide_text(remove_text)

        if tools.is_redirect(self._article_text):
            self.awb_change_article_text(
                "Redirect tagger", _tagger.redirect_tagger(self._article_text, self.name), True
            )
            self.awb_change_article_text(
                "Fix syntax redirects", _fixsyntax.fix_syntax_redirects(self._article_text), True
            )
            self.awb_change_article_text(
                "Simplify links", _wikilinks.simplify_links(self._article_text), True
            )
        else:
            self.awb_change_article_text(
                "Fix whitespace in links",
                _wikilinks.fix_link_whitespace(self._article_text, self.name),
                True,
            )
            self.bullet_external_links(skip.skip_no_bulleted_link)

            # does significant fixes, call before MinorFixes
            self.awb_change_article_text(
                "Fix syntax", _fixsyntax.fix_syntax(self._article_text), True, True
            )

            self.awb_change_article_text(
                "Template redirects",
                _templates.template_redirects(
                    self._article_text, _templates.site_template_redirects(site)
                ),
                True,
            )
            self.awb_change_article_text(
                "Rename Template Parameters",
                _templates.rename_template_parameters(
                    self._article_text, _templates.site_renamed_template_parameters(site)
                ),
                True,
            )

            # call this before MinorFixes so that Parsers.Conversions cleans up from MultipleIssues
            if site.is_wikipedia_en:
                self.awb_change_article_text(
                    "Fixes for {{Multiple issues}}",
                    parsers.multiple_issues(self._article_text),
                    True,
                )

            # must call EmboldenTitles before calling FixLinks
            if self.namespace_key != Namespace.CATEGORY:
                self.embolden_titles(parsers, skip.skip_no_bold_title)

            changes_by_mf = self._minor_fixes(site.lang_code, skip.skip_no_header_error)

            if changes_by_mf:  # call EmboldenTitles again: zeroth section may have changed now
                self.embolden_titles(parsers, False)
                self.bullet_external_links(skip.skip_no_bulleted_link)

            self.fix_people_categories(parsers, skip.skip_no_people_categories_fixed)

            self.awb_change_article_text("Fix categories", fix_categories(self._article_text), True)
            self.awb_change_article_text(
                "Fix images", _parsers.fix_images(self._article_text), True
            )

            self.cite_template_dates(parsers, skip.skip_no_cite_template_dates_fixed)

            self.fix_links(skip.skip_no_bad_link)

            self.awb_change_article_text(
                "Simplify links", _wikilinks.simplify_links(self._article_text), True
            )
            self.awb_change_article_text(
                "Fix citation templates",
                _cite.fix_citation_templates(self._article_text),
                True,
                True,
            )
            self.awb_change_article_text(
                "Fix main article", _parsers.fix_main_article(self._article_text), True
            )

            if replace_reference_tags and site.lang_code != "de":
                self.awb_change_article_text(
                    "Fix reference tags", _refs.fix_reference_list_tags(self._article_text), True
                )

            self.awb_change_article_text(
                "Fix empty links and templates",
                _parsers.fix_empty_links_and_templates(self._article_text),
                True,
            )
            self.awb_change_article_text(
                "Fix empty references", _refs.simplify_reference_tags(self._article_text), True
            )
            self.awb_change_article_text(
                "FixReferenceTags", _refs.fix_reference_tags(self._article_text), True
            )
            self.awb_change_article_text(
                "DuplicateNamedReferences",
                _refs.duplicate_named_references(self._article_text),
                True,
            )
            self.awb_change_article_text(
                "DuplicateUnnamedReferences",
                _refs.duplicate_unnamed_references(self._article_text),
                True,
            )
            self.awb_change_article_text(
                "SameRefDifferentName", _refs.same_ref_different_name(self._article_text), True
            )
            self.awb_change_article_text(
                "Refs after punctuation", _refs.refs_after_punctuation(self._article_text), True
            )

            # ReorderReferences not for en-wp, uk-wiki or ru-wiki genfixes, T154089, T387784, T418701
            if not site.is_wikipedia_en and site.lang_code not in ("uk", "ru"):
                self.awb_change_article_text(
                    "ReorderReferences", _refs.reorder_references(self._article_text), True
                )

            # does significant fixes
            self.awb_change_article_text(
                "Add missing {{reflist}}", _refs.add_missing_reflist(self._article_text), True, True
            )

        self.unhide_text(remove_text)

        if not tools.is_redirect(self._article_text):
            # FixDates does its own hiding
            self.awb_change_article_text(
                "Fix dates 2", parsers.fix_dates_a(self._article_text).strip(), True
            )

        # run whether redirect or not, must be after FixPeopleCategories
        self.set_default_sort(
            site.lang_code, skip.skip_no_default_sort_added, restrict_defaultsort_addition
        )

        # specific fix that requires unhidden text
        self.awb_change_article_text(
            "FixImageSelfLinks", parsers.fix_image_self_links(self._article_text), True
        )

        # pass unhidden text to MetaDataSorter so that it can allow for comments around categories etc.
        self.awb_change_article_text(
            "Sort meta data", parsers.sort_meta_data(self._article_text, self.name), True
        )

        self._after_general_fixes_text_changed()

    def perform_universal_general_fixes(self) -> None:
        """General fixes for all pages: trim whitespace."""
        if self._article_text.strip() != self._article_text:
            self._universal_general_fixes_caused_change = True
            self._article_text = self._article_text.strip()

    def perform_meta_data_sort(self, parsers: Parsers) -> None:
        """Sort metadata on mainspace pages."""
        if self.namespace_key == Namespace.ARTICLE:
            self._article_text = parsers.sort_meta_data(self._article_text, self.name)

    def _before_general_fixes_text_changed(self) -> None:
        self._text_already_changed = self._article_text != self.original_article_text

    def _after_general_fixes_text_changed(self) -> None:
        if not self._text_already_changed:
            self._general_fixes_caused_change = self._article_text != self.original_article_text
        if self._universal_general_fixes_caused_change:
            self._general_fixes_caused_change = True
        if self._general_fixes_caused_change:
            self._after_general_fixes_article_text = self._article_text

    def perform_user_talk_general_fixes(
        self,
        remove_text: HideText,
        user_talk_templates_regex: DotNetRegex | None,
        skip_if_no_change: bool,
        expand_template: _tagger.ExpandTemplate | None = None,
    ) -> None:
        """Substitute user talk warning templates (expanding needs the wiki: see
        tagger.subst_user_templates)."""
        original_text = self._article_text
        self.hide_text(remove_text)
        self.awb_change_article_text(
            "Subst user talk warnings",
            _tagger.subst_user_templates(
                self._article_text, self.name, user_talk_templates_regex, expand_template
            ),
            True,
        )
        self.unhide_text(remove_text)
        if skip_if_no_change and original_text == self._article_text:
            self.awb_skip("No user talk templates subst'd")

    def perform_talk_general_fixes(self, remove_text: HideText) -> None:
        """General fixes for article talk pages."""
        from awb_l.core import talkpagefixes

        self._before_general_fixes_text_changed()
        self.hide_text(remove_text)
        article_text, _ = talkpagefixes.process_talk_page(
            self._article_text, talkpagefixes.DefaultSortChange.NO_CHANGE
        )
        if article_text != self._article_text:
            self.awb_change_article_text("Talk Page general fixes", article_text, False)
        self.unhide_text(remove_text)
        self._after_general_fixes_text_changed()
