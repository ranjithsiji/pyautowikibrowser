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
# Ported from AutoWikiBrowser WikiFunctions/Parse/MetaDataSorter.cs and InterWikiComparer
# (Parse/SiteMatrix.cs). Copyright (C) 2007 Martin Richards, Max Semenik et al.
# (GPL-2.0-or-later).
"""Page layout per [[MOS:ORDER]] (port of Parse/MetaDataSorter.cs): zeroth-section template order,
moving portals, sister links, external links and see also, and gathering DEFAULTSORT,
categories, stubs, persondata, disambiguation templates and interwikis at the end.

AWB loads the interwiki order lists from [[WP:AWB/IW]] into a cache; here they come from the
SiteConfig (filled in by awb_x.api; the defaults are AWB's unit-test values).
"""

# ruff: noqa: E501

from __future__ import annotations

import enum
from collections.abc import Iterable, Sequence

from awb_x.core import namespace, rx
from awb_x.core import wikiregexes as W
from awb_x.core.parsers import templates as _templates
from awb_x.core.rx import DotNetMatch, DotNetRegex
from awb_x.core.site import Namespace, current_site
from awb_x.core.textutil import nested_template_regex, turn_first_to_upper

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741


def _union(a: Iterable[str], b: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys([*a, *b]))


class InterWikiOrderEnum(enum.Enum):
    LOCAL_LANGUAGE_ALPHA = "LocalLanguageAlpha"
    LOCAL_LANGUAGE_FIRST_WORD = "LocalLanguageFirstWord"
    ALPHABETICAL = "Alphabetical"
    ALPHABETICAL_EN_FIRST = "AlphabeticalEnFirst"


class InterWikiComparer:
    """Sort position of an interwiki link by its language code, from an order list (port of
    AWB's InterWikiComparer: languages missing from the order keep their place among the
    others)."""

    def __init__(self, order: Sequence[str], languages: Iterable[str]) -> None:
        languages = list(languages)
        order = [o for o in order if o in languages]  # drop languages not in use
        unordered = [s for s in languages if s not in order]
        if not unordered:
            output = order
        else:
            output: list[str] = []
            for t in languages:
                if t in unordered:
                    output.append(t)
                    unordered.pop(0)  # as AWB: the first element, not t
                elif order:
                    output.append(order.pop(0))
        self.order: dict[str, int] = {}
        for s in output:
            self.order.setdefault("[[" + s, len(self.order))

    def key(self, iw: str) -> int:
        """Sort key: raises KeyError for an unknown language, as AWB wants to see such errors."""
        return self.order[iw[: iw.index(":")]]


# -- static regexes (generated from MetaDataSorter.cs by tools/porting/cs2py.py) ------------------

_CommentedOutEnInterwiki = _R(r"<!-- ?\[\[en:.*?\]\] ?-->")

_DablinksPlusHatnoteGroupList = _union(W.DablinksList, (r"hatnote group",))

_DablinksPlusHatnoteGroup = nested_template_regex(_DablinksPlusHatnoteGroupList)

_WikiTable = _R(r"^{\|", O.MULTILINE)

_TemplatesCannotHandle = nested_template_regex(
    (
        r"stack begin",
        r"stack end",
        r"stack",
        r"Collapsed infobox section begin",
        r"Collapsed infobox section end",
    )
)

_TemplatesToEndOfArticle = nested_template_regex(
    (r"coord", r"WikidataCoord", r"Sky", r"Authority control", r"coord missing")
)

_LifeTime = nested_template_regex(r"Lifetime")

_NF = nested_template_regex(r"NF")

_CatsForDeletion = _R(r"\[\[Category:(Pages|Categories|Articles) for deletion\]\]")

_UncategorizedImproveCats = nested_template_regex(
    (
        r"Improve categories",
        r"Ci",
        r"Cleanup-cat",
        r"Cleanup cat",
        r"Few categories",
        r"Few cats",
        r"Fewcategories",
        r"Fewcats",
        r"Improve-categories",
        r"Improve-cats",
        r"Improve cats",
        r"Improvecategories",
        r"Improvecats",
        r"More categories",
        r"More category",
        r"Morecat",
        r"Morecategories",
        r"Morecats",
        r"Cat-improve",
        r"Category-improve",
        r"Categories-improve",
        r"Category improve",
        r"Categories improve",
        r"Catimprove",
        r"More cats",
        r"Cat improve",
        r"Additional categories",
        r"Undercategorized",
        r"Undercategorised",
        r"CI",
        r"Undercat",
        r"Improve categorization",
        r"Improve cat",
        r"Uncategorized",
        r"CatNeeded",
        r"Catneeded",
        r"Uncategorised",
        r"Uncat",
        r"Categorize",
        r"Categories needed",
        r"Categoryneeded",
        r"Category needed",
        r"Categories requested",
        r"Nocats",
        r"Categorise",
        r"Nocat",
        r"Uncatstub",
        r"Uncategorisedstub",
        r"Needs cat",
        r"Needs cats",
        r"Cat needed",
        r"Uncategorized stub",
        r"Uncat-stub",
        r"Uncat stub",
        r"Cats needed",
        r"Uncategorizedstub",
        r"Uncategorised stub",
        r"Nocategory",
        r"No category",
        r"No categories",
        r"No cats",
        r"Category requested",
        r"+cat",
        r"Categorízame",
        r"Needs categories",
        r"Ncat",
        r"Noc",
        r"Categories missing",
        r"Missing categories",
    )
)

_ExternalLinksSection = _R(
    r"(^== *[Ee]xternal +[Ll]inks? *==.*?)(?=^==+[^=][^\r\n]*?[^=]==+(\r\n?|\n)$)",
    O.MULTILINE | O.SINGLELINE,
)

_ExternalLinksToEnd = _R(r"(==+) *[Ee]xternal +[Ll]inks? *\1.*", O.SINGLELINE)

_SeeAlsoSection = _R(
    r"(^== *[Ss]ee also *==.*?)(?=^==[^=][^\r\n]*?[^=]==(\r\n?|\n)$)", O.MULTILINE | O.SINGLELINE
)

_SeeAlsoToEnd = _R(r"(\s*(==+)\s*see\s+also\s*\2 *).*", O.IGNORE_CASE | O.SINGLELINE)

_ReferencesSectionRegex = _R(r"^== *[Rr]eferences *==\s*", O.MULTILINE)

_NotesSectionRegex = _R(r"^== *[Nn]otes(?: and references)? *==\s*", O.MULTILINE)

_FootnotesSectionRegex = _R(r"^== *(?:[Ff]ootnotes|Sources) *==\s*", O.MULTILINE)

_ReferencesSection = _R(
    r"(^== *([Rr]eferences|Notes) *==.*?)(?=^==[^=][^\r\n]*?[^=]==(\r\n?|\n)$)",
    O.MULTILINE | O.SINGLELINE,
)

_ReferencesToEnd = _R(
    r"^== *([Rr]eferences|Notes) *==\s*"
    + W.ReferencesTemplates
    + r"\s*(?={{DEFAULTSORT\:|\[\[Category\:)",
    O.MULTILINE,
)

_InterLangRegex = _R(
    r"<!--\s*(other languages?|language links?|inter ?(language|wiki)? ?links|inter ?wiki ?language ?links|(?:inter|Other) ?wikis?|The below are interlanguage links\.?|interwiki links to this article in other languages, below)\s*-->",
    O.IGNORE_CASE,
)
_CatCommentRegex = _R("<!--+ ?cat(egories)? ?--+>", O.IGNORE_CASE)
_TabsBeforeNewline = _R("\t+\r\n")
_Newlines = _R("(\r\n)+")
_CategorySortKey = _R(r"(\|\s*)(.+)(\s*\]\]$)")


def _template_exists(templates_found: Iterable[str], r: DotNetRegex) -> bool:
    # MetaDataSorter's own version: "{{name}}", not "{{name|}}"
    return any(r.is_match("{{" + s + "}}") for s in templates_found)


class MetaDataSorter:
    """Puts the parts of a page in [[MOS:ORDER]]."""

    def __init__(self) -> None:
        self.sort_interwikis = True
        self.add_cat_key = False
        self.possible_interwikis: list[str] = []
        self._comparer: InterWikiComparer | None = None
        self._order = InterWikiOrderEnum.LOCAL_LANGUAGE_ALPHA
        self.inter_wiki_order = InterWikiOrderEnum.LOCAL_LANGUAGE_ALPHA

    @property
    def inter_wiki_order(self) -> InterWikiOrderEnum:
        return self._order

    @inter_wiki_order.setter
    def inter_wiki_order(self, value: InterWikiOrderEnum) -> None:
        # orders from https://meta.wikimedia.org/wiki/Interwiki_sorting_order
        site = current_site()
        self._order = value
        seq = {
            InterWikiOrderEnum.ALPHABETICAL: site.interwiki_alpha,
            InterWikiOrderEnum.ALPHABETICAL_EN_FIRST: site.interwiki_alpha_en_first,
            InterWikiOrderEnum.LOCAL_LANGUAGE_ALPHA: site.interwiki_local_alpha,
            InterWikiOrderEnum.LOCAL_LANGUAGE_FIRST_WORD: site.interwiki_local_first,
        }[value]
        self.possible_interwikis = sorted(site.interwiki_languages)
        self._comparer = InterWikiComparer(list(seq), self.possible_interwikis)

    # -- whole page -------------------------------------------------------------------------

    def sort(
        self, article_text: str, article_title: str, fix_optional_whitespace: bool = True
    ) -> str:
        from awb_x.core import tools
        from awb_x.core.parsers import parsers as _parsers

        site = current_site()
        s = W.for_site(site)
        ns = namespace.determine(article_title)
        if ns in (Namespace.TEMPLATE, Namespace.MODULE):  # don't sort templates/modules
            return article_text

        # stray tabs
        article_text = _TabsBeforeNewline.replace(article_text, "\r\n")

        # performance: templates first, so the "move template" functions only run when needed
        all_templates = _templates.get_all_templates(article_text)
        is_article = namespace.is_main_space(article_title)

        # zeroth section
        if is_article and not tools.is_redirect(article_text):
            if _template_exists(all_templates, _TemplatesToEndOfArticle):
                article_text = self.move_template_to_end_of_article(article_text)
            zeroth = tools.get_zeroth_section(article_text)
            rest = article_text[len(zeroth) :]
            # not with noinclude/{{{1}}}/{{#ifexist/wikitables/behaviour switches in it
            if (
                not _parsers.no_include_include_only_programming_element(zeroth)
                and not _WikiTable.is_match(zeroth)
                and not W.MagicWordBehaviourSwitches.is_match(zeroth)
            ):
                article_text = self.sort_zeroth_section(zeroth) + rest

        # [[WP:AWB/FR/Archive_5#Substituted_templates]]: sorting may mess substituted templates up
        if is_article and _parsers.no_include_include_only_programming_element(article_text):
            return article_text

        # en: keep {{Short pages monitor}} at the very end, see [[Template:Long comment/doc]]
        short_pages_monitor = ""
        if site.lang_code == "en" and "Short pages monitor" in all_templates:
            spm = W.ShortPagesMonitor.match(article_text)
            if spm:
                article_text = W.ShortPagesMonitor.replace(article_text, "").rstrip()
                short_pages_monitor = spm.value.rstrip()

        article_text = _CommentedOutEnInterwiki.replace(article_text, "")

        person_data = ""
        if _template_exists(all_templates, s.Persondata):
            article_text, removed = remove_person_data(article_text)
            person_data = tools.newline(removed)

        disambig = ""
        if _template_exists(all_templates, s.Disambigs):
            article_text, removed = remove_disambig(article_text)
            disambig = tools.newline(removed)

        article_text, cats = self.remove_cats(article_text, article_title)
        categories = tools.newline(cats)

        article_text, iws = self.interwikis(
            article_text, _template_exists(all_templates, s.LinkFGAs)
        )
        interwikis = tools.newline(iws)

        if is_article and not tools.is_redirect(article_text) and site.lang_code == "en":
            if _template_exists(all_templates, W.PortalTemplate):
                article_text = move_portal_templates(article_text)
            if _template_exists(all_templates, W.SisterLinks):
                article_text = move_sisterlinks(article_text)
            if "Ibid" in all_templates:
                article_text = move_template_to_references_section(article_text, W.Ibid)
            article_text = move_external_links(article_text)
            article_text = move_see_also(article_text)

        # stubs: one blank line before them on en (T382578) and on ru, sl, ar, arz; two elsewhere.
        # Category pages may use {{Verylargestub}}/{{popstub}}, which are not stub templates.
        str_stub = ""
        if ns != Namespace.CATEGORY and _template_exists(all_templates, _R(site.stub)):
            article_text, stubs = remove_stubs(article_text)
            one = site.lang_code in ("ru", "sl", "ar", "arz") or site.is_wikipedia_en
            str_stub = tools.newline(stubs, 1 if one else 2)

        # excess whitespace and a trailing "----" (trim here: faster than in remove_white_space)
        if is_article:
            article_text = article_text.rstrip()
        article_text = _parsers.remove_white_space(article_text, fix_optional_whitespace) + "\r\n"

        article_text += disambig
        if _template_exists(all_templates, W.MultipleIssues):
            article_text = W.MultipleIssues.replace(
                article_text, lambda m: _Newlines.replace(m.value, "\r\n")
            )

        lang = site.lang_code
        if lang in ("de", "sl"):
            article_text += str_stub + categories + person_data
            # de: a blank line between persondata and interwikis
            if lang == "de" and person_data and interwikis:
                article_text += "\r\n"
        elif lang in ("ar", "arz", "cs", "el", "dk", "pl", "ru", "uk"):
            article_text += person_data + str_stub + categories
        elif lang == "it":
            if site.project == "wikiquote":
                article_text += person_data + str_stub + categories
            else:
                article_text += person_data + categories + str_stub
        else:
            article_text += person_data + categories + str_stub
        article_text += interwikis

        # only trim the start on Category pages; restore any short pages monitor text
        return (
            article_text.strip() if ns == Namespace.CATEGORY else article_text.rstrip()
        ) + short_pages_monitor

    def sort_zeroth_section(self, zeroth: str) -> str:
        """Order the templates at the top of an article per [[MOS:ORDER]]."""
        from awb_x.core.parsers import unbalancedbrackets as _ub

        move_display_title = _display_lower_case_italic_title_needs_moving(zeroth)
        all_templates = _templates.get_all_templates(zeroth)

        # templates that cannot be handled
        if _template_exists(all_templates, _TemplatesCannotHandle):
            return zeroth
        if _ub.unbalanced_brackets(zeroth)[0] > 0:
            return zeroth

        deletion_tags_comments = any(
            W.Comments.is_match(m.value) for m in W.DeletionProtectionTags.matches(zeroth)
        )

        # (rest of section) {{DISPLAYTITLE}}, {{Lowercase title}}, {{Italic title}} not directly after an infobox
        if move_display_title == 4:
            zeroth = move_template(zeroth, W.DisplayLowerCaseItalicTitle)
        # (L9) language maintenance templates after infoboxes
        if _template_exists(all_templates, W.LanguageMaintenanceTemplates):
            zeroth = move_template(zeroth, W.LanguageMaintenanceTemplates)
        # (L8-after) DISPLAYTITLE etc. directly after an infobox
        if move_display_title == 3:
            zeroth = move_template(zeroth, W.DisplayLowerCaseItalicTitle)
        # L8 infoboxes after English variety and date format templates
        if _template_exists(all_templates, W.InfoBox):
            zeroth = move_template(zeroth, W.InfoBox)
        # (L8-pre) DISPLAYTITLE etc. directly before an infobox
        if move_display_title == 2:
            zeroth = move_template(zeroth, W.DisplayLowerCaseItalicTitle)
        # L7 English variety and date format templates after maintenance templates
        if _template_exists(all_templates, W.UseDatesEnglishTemplates):
            zeroth = move_template(zeroth, W.UseDatesEnglishTemplates)
        # L6 maintenance templates (including {{in use}}, {{bots}})
        if _template_exists(all_templates, W.MosLevel6MaintenanceCleanupDispute):
            zeroth = move_template(zeroth, W.MosLevel6MaintenanceCleanupDispute)
        # L5 deletion/protection templates above maintenance tags, below dablinks; comments on the
        # lines after the template only when there are such comments, else unrelated comments
        # later in the section could be taken
        if _template_exists(all_templates, W.DeletionProtectionTags):
            zeroth = move_template(
                zeroth,
                W.DeletionProtectionTags
                if deletion_tags_comments
                else nested_template_regex(W.DeletionProtectionTagsList),
            )
        # L4 featured/good article templates above deletion/protection templates
        if _template_exists(all_templates, W.GoodFeaturedArticleTemplates):
            zeroth = move_template(zeroth, W.GoodFeaturedArticleTemplates)
        # L3 hatnotes/dablinks above maintenance tags; with {{hatnote group}} move that plus any
        # standalone dablinks
        if _template_exists(all_templates, _DablinksPlusHatnoteGroup):
            zeroth = move_template(zeroth, _DablinksPlusHatnoteGroup)
        # L2 DISPLAYTITLE etc. above hatnotes, if not kept next to an infobox
        if move_display_title == 1:
            zeroth = move_template(zeroth, W.DisplayLowerCaseItalicTitle)
        # L1 {{short description}} above dablinks
        if _template_exists(all_templates, W.ShortDescriptionTemplate):
            zeroth = move_template(zeroth, W.ShortDescriptionTemplate)
        return zeroth

    def move_template_to_end_of_article(self, article_text: str) -> str:
        """{{coord}}, {{Authority control}} etc. from the zeroth section to the end."""
        from awb_x.core import tools

        original = article_text
        zeroth = tools.get_zeroth_section(article_text)
        details = [
            t
            for t in _templates.get_all_template_detail(zeroth)
            if _TemplatesToEndOfArticle.is_match(t)
        ]
        if not details:
            return article_text

        # the last section
        hc = W.Headings.matches(article_text)
        if not hc:
            return article_text
        h = hc[-1].index
        last_section = article_text[h:]
        rest = article_text[:h]

        # nothing to do if the template is already in the last section
        if not _TemplatesToEndOfArticle.is_match(rest) or any(t in last_section for t in details):
            return article_text

        found = ""
        for m in W.NestedTemplates.matches(article_text):
            if (
                not _TemplatesToEndOfArticle.is_match(m.value)
                or _TemplatesToEndOfArticle.match(m.value).index > 0
            ):
                continue
            # only from the zeroth section
            if m.index > len(zeroth):
                continue
            template = m.value
            if _R("^" + rx.escape(template), O.MULTILINE).is_match(article_text):
                article_text = _R("^" + rx.escape(template) + r" *(?:\r\n)?", O.MULTILINE).replace(
                    article_text, ""
                )
                found += "\r\n" + template
        article_text += found
        if not tools.unformatted_text_not_changed(original, article_text):
            return original
        return article_text

    def remove_cats(self, article_text: str, article_title: str) -> tuple[str, str]:
        """Take DEFAULTSORT, categories (with their comments) and {{uncategorized}}/{{improve
        categories}} out of the text. Returns (text, the removed parts in [[MOS:ORDER]] order)."""
        from awb_x.core import tools

        site = current_site()
        s = W.for_site(site)

        # not from redirects to a category, e.g. #REDIRECT[[Category:Hello]]
        rt = tools.redirect_target(article_text)
        if rt and s.Category.is_match("[[" + rt + "]]"):
            return article_text, ""

        category_list: list[str] = []
        no_comments = tools.replace_with_spaces(article_text, W.Comments.matches(article_text))

        # not with (incorrectly) multiple DEFAULTSORTs, ignoring commented out ones
        # ([[WP:AWB/B/Archive_12#Moving_DEFAULTSORT_in_HTML_comments]]); exact duplicates are fine
        mc = s.Defaultsort.matches(no_comments)
        if len(mc) > 1:
            first = mc[0]
            article_text = s.Defaultsort.replace(
                article_text,
                lambda d: "" if d.index > first.index and first.value == d.value else d.value,
            )
            # count again after de-duplication
            no_comments = tools.replace_with_spaces(article_text, W.Comments.matches(article_text))
            if len(s.Defaultsort.matches(no_comments)) > 1:
                return article_text, ""

        default_sort = ""
        default_sort_removed = False

        # keep comments between categories in place; only take a comment after the last
        # category on the same line. Whitespace: remove all after, but leave a blank line before
        # a heading (rare case of categories not in the last section).
        # performance: only on the part of the text with category links
        cq = s.CategoryQuick.match(no_comments)
        if cq:
            # T387084 not with behaviour switches, as these can be anywhere
            if W.MagicWordBehaviourSwitches.is_match(article_text[cq.index :]):
                return article_text, ""

            all_unformatted = [m.value for m in W.UnformattedText.matches(article_text)]
            cutoff = max(0, cq.index - 500)
            cut = article_text[cutoff:]

            # unformatted text matched by the categories regex is a commented out category, or a
            # category comment containing a category: handle these as normal
            cats_found = [m.value for m in s.RemoveCatsAllCats.matches(cut)]
            all_unformatted = [u for u in all_unformatted if not any(u in c for c in cats_found)]

            def take(m: DotNetMatch) -> str:
                trimmed = m.value.strip()
                # not from comments/unformatted text
                if any(
                    trimmed in u and u != trimmed and u not in category_list
                    for u in all_unformatted
                ):
                    return m.value
                if not _CatsForDeletion.is_match(m.value):
                    category_list.append(trimmed)
                # category not at the start of a line: leave a newline, else the next line moves up
                if m.index > 2 and cut[m.index - 2 : m.index].strip() != "":
                    return "\r\n"
                return ""

            cut = s.RemoveCatsAllCats.replace(cut, take)

            if self.add_cat_key:
                category_list = _cat_keyer(category_list, article_title)

            # DEFAULTSORT again, with any comment after it on the same line
            if mc:
                mc = _R(str(s.Defaultsort) + r"(?: *<!--[^<>]*-->)?").matches(article_text)
            # remove the DEFAULTSORT from cut if possible (faster than from the whole text)
            if mc and mc[0].value in cut:
                cut = cut.replace(mc[0].value, "")
                default_sort_removed = True

            article_text = article_text[:cutoff] + cut

            if _CatCommentRegex.is_match(cut):

                def cat_comment(m: DotNetMatch) -> str:
                    category_list.insert(0, m.value)
                    return ""

                article_text = _CatCommentRegex.replace(article_text, cat_comment, 1)

        if site.lang_code == "sl" and _LifeTime.is_match(article_text):
            default_sort = _LifeTime.match(article_text).value
        if site.lang_code == "es" and _NF.is_match(article_text):
            default_sort = _NF.match(article_text).value
        elif mc:
            default_sort = mc[0].value

        if default_sort:
            # DEFAULTSORT not in the cut area before the categories: remove it now
            if not default_sort_removed:
                article_text = article_text.replace(default_sort, "")
            if "DEFAULTSORT" in default_sort.upper():
                default_sort = _format_default_sort(default_sort)
            default_sort += "\r\n"

        # {{uncategorized}}/{{improve categories}}, only from the last section (from the final
        # heading; the whole text if there are no headings)
        hc = W.Headings.matches(article_text)
        last_section_no_comments = no_comments
        rest = ""
        if hc:
            h = hc[-1].index
            last_section = article_text[h:]
            last_section_no_comments = tools.replace_with_spaces(
                last_section, W.Comments.matches(last_section)
            )
            rest = article_text[:h]

        uncat = ""
        if _UncategorizedImproveCats.is_match(
            last_section_no_comments
        ) and not _UncategorizedImproveCats.is_match(rest):
            found: list[str] = []

            def take_uncat(m: DotNetMatch) -> str:
                if m.value not in "".join(found):  # exact duplicates
                    found.append(m.value + "\r\n")
                return ""

            article_text = _UncategorizedImproveCats.replace(article_text, take_uncat)
            uncat = "".join(found)
            # {{improve categories}} may have been in {{multiple issues}}: tidy it
            from awb_x.core.parsers.parsers import Parsers

            article_text = Parsers().multiple_issues(article_text)

        # [[MOS:ORDER]]: {{Improve categories}}/{{Uncategorized}} after the categories (en)
        if site.is_wikipedia_en:
            return article_text, default_sort + _list_to_string(category_list) + uncat
        return article_text, uncat + default_sort + _list_to_string(category_list)

    def interwikis(self, article_text: str, link_fgas_in_text: bool = True) -> tuple[str, str]:
        """Take {{link FA}}-style templates, any interlanguage comment and the interwiki links out
        of the text. Returns (text, the removed parts)."""
        comment = ""
        if "<!--" in article_text:
            found: list[str] = []

            def take(m: DotNetMatch) -> str:
                found.append(m.value)
                return ""

            article_text = _InterLangRegex.replace(article_text, take, 1)
            comment = found[0] if found else ""

        iws = ""
        # only look for {{link FA}} etc. if necessary
        if link_fgas_in_text:
            article_text, link_fgas = _remove_link_fgas(article_text)
            iws = _list_to_string(link_fgas)
        if comment:
            iws += comment + "\r\n"
        article_text, removed = self._remove_inter_wikis(article_text)
        return article_text, iws + _list_to_string(removed)

    def _remove_inter_wikis(self, article_text: str) -> tuple[str, list[str]]:
        from awb_x.core import tools

        site = current_site()
        possible = self.possible_interwikis
        inter_wiki_list: list[str] = []

        # performance: all wikilinks filtered to interwikis, rather than the regex on the whole text
        if not any(
            ":" in m.value and m.group(1)[: m.group(1).index(":")].strip().lower() in possible
            for m in W.WikiLink.matches(article_text)
        ):
            return article_text, inter_wiki_list

        # unformatted text, to avoid taking interwikis from comments etc.
        unformatted = "".join(u.value for u in W.UnformattedText.matches(article_text))
        good: list[DotNetMatch] = []
        links_only: list[str] = []
        all_templates = _templates.get_all_template_detail(article_text)

        for m in W.PossibleInterwikis.matches(article_text):
            lang = m.group(1).strip().lower()
            # ignore interwikis in template calls
            if lang not in possible or any(m.value in t for t in all_templates):
                continue
            if m.value in unformatted:
                unformatted = tools.replace_once(unformatted, m.value, "")[0]
                continue
            good.append(m)
            # jbo is the only Wikipedia whose titles are first-letter case sensitive
            target = (
                m.group(2).strip() if lang == "jbo" else turn_first_to_upper(m.group(2).strip())
            )
            iw = "[[" + lang + ":" + target + "]]"
            # drop interwikis to the wiki itself, except on Commons etc. (language en, links to Wikipedia)
            if (
                not (m.group(1) == site.lang_code and not site.is_wikimedia_monolingual_project)
                and iw not in links_only
            ):
                links_only.append(iw)
                inter_wiki_list.append(iw + m.group(3))

        article_text = tools.remove_matches(article_text, good)
        if self.sort_interwikis and self._comparer is not None:
            # stable sort: interwikis to the same language keep their order (AWB sorts twice with
            # an unstable sort for the same effect)
            inter_wiki_list.sort(key=self._comparer.key)
        return article_text, inter_wiki_list


def _display_lower_case_italic_title_needs_moving(article_text: str) -> int:
    """Where {{DISPLAYTITLE}}/{{Lowercase title}}/{{Italic title}} should go: 0 nowhere, 1 to
    second place (after a short description), 2 keep before the infobox, 3 keep after it, 4 rest
    of section."""
    from awb_x.core import tools

    templates = [m.value for m in W.NestedTemplates.matches(tools.get_zeroth_section(article_text))]
    display = next(
        (i for i, t in enumerate(templates) if W.DisplayLowerCaseItalicTitle.is_match(t)), -1
    )
    infobox = next((i for i, t in enumerate(templates) if W.InfoBox.is_match(t)), -1)
    if display > -1:
        # no infobox, or other templates between: 2nd position per MOS:ORDER; just before or
        # anywhere after the infobox is allowed too
        if infobox == -1 or infobox - display > 1:
            return 1
        if infobox - display == 1:
            return 2
        if display - infobox == 1:
            return 3
        if display > infobox:
            return 4
    return 0


def _format_default_sort(article_text: str) -> str:
    """TalkPageFixes.FormatDefaultSort: {{DEFAULTSORT:key}}."""
    return W.for_site(current_site()).Defaultsort.replace(article_text, "{{DEFAULTSORT:${key}}}")


def remove_person_data(article_text: str) -> tuple[str, str]:
    """Take {{Persondata}} out of the text. Returns (text, persondata)."""
    from awb_x.core import tools

    original = article_text
    found: list[str] = []

    def take(m: DotNetMatch) -> str:
        found.append(m.value if not found else tools.newline(m.value))
        return ""

    article_text = W.for_site(current_site()).Persondata.replace(article_text, take)
    if not tools.unformatted_text_not_changed(original, article_text):
        return original, ""
    return article_text, "".join(found)


def remove_stubs(article_text: str) -> tuple[str, str]:
    """Take stub templates out of the text (not section stubs; en: drop {{stub}} when a more
    specific stub exists). Returns (text, stubs)."""
    from awb_x.core import tools

    site = current_site()
    # ru-wiki places stubs before navboxes
    if site.lang_code == "ru":
        return article_text, ""
    stub_list: list[str] = []
    original = article_text
    sect_stub = _R(site.sect_stub)  # AWB: Regex.IsMatch(m.Value, Variables.SectStub)

    def take(m: DotNetMatch) -> str:
        if not sect_stub.is_match(m.value):
            stub_list.append(m.value)
            return ""
        return m.value

    article_text = W.for_site(site).PossiblyCommentedStub.replace(article_text, take)
    # not from comments
    if not tools.unformatted_text_not_changed(original, article_text + _list_to_string(stub_list)):
        return original, ""
    # en-wp: remove {{stub}} if a more specific stub exists (not counting {{uncategorized stub}})
    if site.is_wikipedia_en:
        cp = [
            s for s in stub_list if not tools.get_template_name(s).lower().startswith("uncategori")
        ]
        if len(_templates.get_all_template_detail(_list_to_string(cp))) > 1:
            stub_list = [
                s for s in stub_list if tools.get_template_name(s).lstrip("-").lower() != "stub"
            ]
    return article_text, _list_to_string(stub_list) if stub_list else ""


def remove_disambig(article_text: str) -> tuple[str, str]:
    """Take one disambiguation template out of the text (en). Returns (text, template)."""
    if current_site().lang_code != "en":
        return article_text, ""
    s = W.for_site(current_site())
    found: list[str] = []
    # at most one (there should not be several), not from comments
    if s.Disambigs.is_match(W.Comments.replace(article_text, "")):

        def take(m: DotNetMatch) -> str:
            found.append(m.value)
            return ""

        article_text = s.Disambigs.replace(article_text, take, 1)
    return article_text, "".join(found)


_LeadingComments = r"(?:^<!--\s*[^<>\r\n]+\s*-->\s*){0,5}"
_TrailingComments = r"(?: *<!--[^<>]+--> ?)*"


def move_template(article_text: str, template_regex: DotNetRegex) -> str:
    """Move the matching templates to the top of the article (en), keeping comments that belong
    to them (on the lines above, or after them on the same line)."""
    from awb_x.core import tools
    from awb_x.core.parsers import parsers as _parsers

    original = article_text
    zeroth = tools.get_zeroth_section(article_text)

    t1 = [
        t for t in _templates.get_all_templates(zeroth) if template_regex.is_match("{{" + t + "}}")
    ]
    t2 = [
        t
        for t in _templates.get_all_templates(W.Comments.replace(zeroth, ""))
        if template_regex.is_match("{{" + t + "}}")
    ]
    # not commented out / partly commented out templates
    if current_site().lang_code != "en" or any(t not in t2 for t in t1):
        return article_text

    with_comments = _R(_LeadingComments + str(template_regex) + _TrailingComments, O.MULTILINE)
    rest = article_text[len(zeroth) :]

    # the templates, not section ones
    the_templates = [
        m.value
        for m in with_comments.matches(zeroth)
        if tools.get_template_argument(m.value, 1) != "section"
    ]
    deduplicated = _parsers.deduplicate_maintenance_tags(the_templates)
    # several templates folded together, e.g. an infobox weather event with sub-templates
    folded = len(the_templates) > 2 and "".join(the_templates) in zeroth

    for t in the_templates:
        # with any colon before and whitespace after
        zeroth = _R(":?" + rx.escape(t) + r" *(?:\r\n)?").replace(zeroth, "")
    templates_text = "".join(t + ("" if folded else "\r\n") for t in deduplicated)
    if folded:
        templates_text += "\r\n"

    article_text = templates_text + zeroth + rest
    # not commented out templates, round 2
    if tools.unformatted_text_not_changed(original, article_text):
        return article_text
    return original


def move_sisterlinks(article_text: str) -> str:
    """Move sister project link templates to the External links section."""
    from awb_x.core import tools

    original = article_text
    s = W.for_site(current_site())
    for m in W.SisterLinks.matches(article_text):
        found = m.value
        el_section = _ExternalLinksSection.match(article_text).value
        # no match: External links must be the last section
        if not el_section:
            el_section = _ExternalLinksToEnd.match(article_text).value
        # need an External links section, and the sister link not already in it
        if el_section and found.strip() not in el_section:
            article_text = _R(rx.escape(found) + r"\s*(?:\r\n)?").replace(article_text, "")
            # AWB passes the template into the .NET replacement string unescaped; kept as is
            article_text = s.ExternalLinksHeader.replace(article_text, "$0\r\n" + found)
    if tools.unformatted_text_not_changed(original, article_text):
        return article_text
    return original


def move_multiple_issues(article_text: str) -> str:
    """Move {{Multiple issues}} above an infobox."""
    from awb_x.core import tools

    original = article_text
    mi_index = infobox_index = -1
    for m in W.NestedTemplates.matches(article_text):
        if "infobox" in tools.get_template_name(m.value).lower():
            infobox_index = m.index
        elif W.MultipleIssues.is_match(m.value):
            mi_index = m.index
    if mi_index > infobox_index > -1:
        mi = W.MultipleIssues.match(article_text).value
        article_text = mi + "\r\n" + article_text.replace(mi, "")
        if not tools.unformatted_text_not_changed(original, article_text):
            return original
    return article_text


def move_template_to_see_also_section(article_text: str, template_to_move: DotNetRegex) -> str:
    """Move the template to the top of the See also section."""
    from awb_x.core import tools

    mc = template_to_move.matches(article_text)
    if not mc:
        return article_text
    original = article_text
    moved = False
    s = W.for_site(current_site())
    for m in mc:
        found = m.value
        sa = _SeeAlsoSection.match(article_text)
        section, index = sa.value, sa.index
        # no match: See also must be the last section
        if not section:
            sae = _SeeAlsoToEnd.match(article_text)
            section, index = sae.value, sae.index
        if not section:  # no See also section to move templates to
            break
        # only templates not already in See also
        if m.index < index or m.index > index + len(section):
            # remove the template, and its newline if it is on its own line
            article_text = _R("^" + rx.escape(found) + r" *(?:\r\n)?", O.MULTILINE).replace(
                article_text, ""
            )
            article_text = article_text.replace(found, "")
            # top of the See also section (template passed into the replacement string as AWB does)
            article_text = s.SeeAlso.replace(article_text, "$0" + tools.newline(found))
            moved = True
    if moved and tools.unformatted_text_not_changed(original, article_text):
        return article_text
    return original


def move_portal_templates(article_text: str) -> str:
    """[[WP:AWB/FR#Placement_of_portal_template]]: portals to the See also section."""
    return move_template_to_see_also_section(article_text, W.PortalTemplate)


def move_template_to_references_section(
    article_text: str, template_regex: DotNetRegex, only_from_zeroth_section: bool = False
) -> str:
    """Move the (single) template into the Notes, References or Footnotes section."""
    from awb_x.core import tools

    # at most one such template
    if len(template_regex.matches(article_text)) != 1 or (
        only_from_zeroth_section
        and len(template_regex.matches(W.ZerothSection.match(article_text).value)) != 1
    ):
        return article_text
    # already in one of those sections
    for sec in tools.split_to_sections(article_text):
        if template_regex.is_match(sec) and (
            _NotesSectionRegex.is_match(sec)
            or _ReferencesSectionRegex.is_match(sec)
            or _FootnotesSectionRegex.is_match(sec)
        ):
            return article_text

    position = template_regex.match(article_text).index
    notes = _NotesSectionRegex.match(article_text).index
    if notes > 0 and position < notes:
        return _move_template_to_section(article_text, template_regex, _NotesSectionRegex)
    references = _ReferencesSectionRegex.match(article_text).index
    if references > 0 and position < references:
        return _move_template_to_section(article_text, template_regex, _ReferencesSectionRegex)
    footnotes = _FootnotesSectionRegex.match(article_text).index
    if footnotes > 0 and position < footnotes:
        return _move_template_to_section(article_text, template_regex, _FootnotesSectionRegex)
    return article_text


def _move_template_to_section(
    article_text: str, template_regex: DotNetRegex, section: DotNetRegex
) -> str:
    extracted = template_regex.match(article_text).value
    article_text = template_regex.replace(article_text, "")
    # template passed into the replacement string as AWB does
    return section.replace(article_text, "$0" + extracted + "\r\n", 1)


def move_external_links(article_text: str) -> str:
    """Put External links after References/Notes ([[WP:AWB/FR#Place_"External_links"_section_after_"References"]]).
    Only works when another section follows References."""
    elm = _ExternalLinksSection.match(article_text)
    external_links = elm.group(1)
    # no <ref> in the External links section
    if not elm or _R(W.ReferenceEnd).is_match(external_links):
        return article_text
    references = _ReferencesSection.match(article_text).group(1)
    # References may be the last section
    if not references:
        references = _ReferencesToEnd.match(article_text).value
    if references and elm.index < article_text.find(references):
        article_text = article_text.replace(external_links, "")
        article_text = article_text.replace(references, references + external_links)
    return article_text


def move_see_also(article_text: str) -> str:
    """Put See also before References/Notes (newlines are fixed later)."""
    ref = _ReferencesSection.match(article_text)
    see = _SeeAlsoSection.match(article_text)
    references, see_also = ref.group(1), see.group(1)
    if see and see.index > ref.index and len(_ReferencesSection.matches(article_text)) == 1:
        article_text = article_text.replace(see_also, "")
        article_text = article_text.replace(references, see_also + "\r\n" + references)
    return article_text


def _remove_link_fgas(article_text: str) -> tuple[str, list[str]]:
    from awb_x.core import tools

    s = W.for_site(current_site())
    matches = s.LinkFGAs.matches(
        tools.replace_with_spaces(article_text, W.UnformattedText.matches(article_text))
    )
    return tools.remove_matches(article_text, matches), [m.value for m in matches]


def iw_match_eval(match: DotNetMatch) -> str:
    return "[[" + match.group("site").lower() + ":" + match.group("text") + "]]"


def _list_to_string(items: Sequence[str]) -> str:
    """The items, one per line, without duplicates: an item is a duplicate if an earlier one
    starts with it, or (categories) differs only by sort key or sort key first letter case, or
    (templates) by first letter case."""
    if not items:
        return ""
    s = W.for_site(current_site())
    unique: list[str] = []
    for item in items:
        add = True
        s2 = item
        is_category = s.Category.is_match(s2)
        # compare categories by their first-letter-upper sort key
        if "|" in s2 and is_category:
            s2 = _CategorySortKey.replace(
                s2, lambda m: m.group(1) + turn_first_to_upper(m.group(2)) + m.group(3)
            )
        for u in unique:
            if u.startswith(s2) or u.startswith(s2.rstrip("]") + "|") or u in (item, s2):
                add = False
                break
            if s2.startswith(u):  # [[Category:A]] added, now [[Category:A]] <!-- comment-->
                unique.remove(u)
                break
            # [[Category:A|Foo]] added, now [[Category:A|Foo bar]]
            if is_category and "|" in u and s2.rstrip("]").startswith(u.rstrip("]")):
                unique.remove(u)
                break
            if is_category and "|" in s2 and u.rstrip("]").startswith(s2.rstrip("]")):
                add = False
                break
            # templates: first letter case-insensitive (AWB's exact, slightly odd, comparison)
            if (
                W.NestedTemplates.is_match(s2)
                and W.NestedTemplates.is_match(u)
                and s2[1:4].upper() + s2[3:] == u[1:4].upper() + u[3:]
            ):
                add = False
                break
        if add:
            unique.append(item)
    return "".join(u + "\r\n" for u in unique)


def _cat_keyer(categories: Iterable[str], name: str) -> list[str]:
    """Add a human sort key to categories without one."""
    from awb_x.core import tools

    key = tools.make_human_cat_key(name, "")
    return [c if "|" in c else c.replace("]]", "|" + key + "]]") for c in categories]
