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
# Ported from AutoWikiBrowser WikiFunctions/Parse/CategoryDefaultSort.cs
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""Categories, DEFAULTSORT and people categories (port of Parse/CategoryDefaultSort.cs)."""

# ruff: noqa: E501

from __future__ import annotations

import datetime

from pyawb.core import namespace, rx
from pyawb.core import wikiregexes as W
from pyawb.core.parsers import templates as _templates
from pyawb.core.parsers import wikilinks as _wikilinks
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import Namespace, current_site
from pyawb.core.textutil import (
    first_letter_case_insensitive,
    nested_template_regex,
    turn_first_to_upper,
)

_R = DotNetRegex
O = rx.DotNetOptions  # noqa: E741

# -- static regexes (generated from CategoryDefaultSort.cs by tools/porting/cs2py.py) -------------

_PersonYearOfBirth = _R(
    r"(?<='''.{0,100}?)\( *[Bb]orn[^\)\.;]{1,150}?(?<!.*(?:[Dd]ied|&[nm]dash;|—).*)([12]?\d{3}(?: BC)?)\b[^\)]{0,200}"
)

_PersonYearOfDeath = _R(r"(?<='''.{0,100}?)\([^\(\)]*?[Dd]ied[^\)\.;]+?([12]?\d{3}(?: BC)?)\b")

_PersonYearOfBirthAndDeath = _R(
    r"^.{0,100}?'''\s*\([^\)\r\n]*?(?<![Dd]ied)\b([12]?\d{3})\b[^\)\r\n]*?(-|–|—|&[nm]dash;)[^\)\r\n]*?([12]?\d{3})\b[^\)]{0,200}",
    O.SINGLELINE,
)

_LongWikilink = _R(r"\[\[[^\[\]\|]{11,}(?:\|[^\[\]]+)?\]\]")

_YearPossiblyWithBC = _R(r"\d{3,4}(?![\ds])(?: BC)?")

_ThreeOrFourDigitNumber = _R(r"[0-9]{3,4}")

_DiedOrBaptised = _R(r"(^.*?)((?:&[nm]dash;|—|–|;|[Dd](?:ied|\.)|baptised|transitioned).*)")

_NotCircaTemplate = _R(r"{{(?!(?:[Cc]irca|[Ff]l\.?))[^{]*?}}")

_AsOfText = _R(r"\bas of\b")

_FloruitTemplate = nested_template_regex((r"fl", r"fl.", r"floruit"))

_BirthDateBasedOnAgeAtDeath = nested_template_regex(
    (r"Birth date based on age at death", r"Birth based on age at death")
)

_FootnoteTemplates = nested_template_regex(
    (
        r"Efn",
        r"Efn-ua",
        r"Efn-lr",
        r"Sfn",
        r"Shortened footnote",
        r"Shortened footnote template",
        r"Sfnb",
        r"Sfnp",
        r"Sfnm",
        r"SfnRef",
    )
)

_Cat4YearBirths = _R(r"\[\[Category *: *\d{1,4} (BC )?births\s*(?:\||\]\])")

_CatYearDeaths = _R(r"\[\[Category *: *[0-9]{1,4} (BC )?(deaths|suicides)\s*(?:\||\]\])")

YearOfBirthMissingLivingPeople = "Year of birth missing (living people)"
YearOfBirthMissing = "Year of birth missing"
YearOfBirthUncertain = "Year of birth uncertain"
YearofDeathMissing = "Year of death missing"
_CategoryLivingPeople = "[[Category:Living people"
_YearOnly = _R(r"^[12]\d{3}$")  # CiteTemplates.YearOnly in AWB
_Digits34 = _R(r"\d{3,4}")
_YearRangeInBirth = _R(r"[12]\d\d\d.[12]\d\d\d")
_DiedOrDot = _R(r"(?:[Dd](?:ied|\.)|baptised)")
_BornOrDot = _R(r"[Bb](?:orn|\.)")
_DiedOrDotOnly = _R(r"[Dd](?:ied|\.)")
_WordComma = _R(r"\w,\w")
_FullDob = _R(r"(\|\s*[0-9]+\s*){3}")
_PageName = nested_template_regex("PAGENAME")
_WordWhitespaceEndofline = _R(r"(\w+)\s+$")


def _cat_ns() -> str:
    return current_site().namespaces[Namespace.CATEGORY]


def _cat_ns_ci() -> str:
    return current_site().namespaces_case_insensitive[Namespace.CATEGORY]


# -- adding, replacing, removing categories -------------------------------------------------------


def re_categoriser(
    old_category: str, new_category: str, article_text: str, remove_sort_key: bool = False
) -> tuple[str, bool]:
    """Replace one category with another (keeping the sort key unless remove_sort_key).
    Returns (text, no_change)."""
    cat_prefix = _R("^" + _cat_ns_ci(), O.IGNORE_CASE)
    old_category = cat_prefix.replace(old_category, "")
    new_category = cat_prefix.replace(new_category, "")
    article_text = fix_categories(article_text)
    test_text = article_text

    if _R(
        r"\[\["
        + _cat_ns_ci()
        + first_letter_case_insensitive(rx.escape(new_category))
        + r"\s*(\||\]\])"
    ).is_match(article_text):
        article_text, _ = remove_category_no_change(old_category, article_text)
    else:
        old = (
            _cat_ns()
            + first_letter_case_insensitive(rx.escape(old_category))
            + r"\s*(\|[^\|\[\]]+\]\]|\]\])"
        )
        # keep pipes: [[WP:AWB/FR/Archive_5#Replacing_categoring_and_keeping_pipes]]
        # (AWB passes the category name into the .NET replacement string unescaped; kept as is)
        new = _cat_ns() + new_category + ("]]" if remove_sort_key else "$1")
        article_text = _R(old).replace(article_text, new)
    return article_text, test_text == article_text


def remove_category_no_change(old_cat: str, article_text: str) -> tuple[str, bool]:
    """Remove a category after fixing category syntax; returns (text, no_change)."""
    article_text = fix_categories(article_text)
    test_text = article_text
    article_text = remove_category(old_cat, article_text)
    return article_text, test_text == article_text


def remove_category(old_cat: str, article_text: str) -> str:
    """Remove a category (with its line break, unless the text has <includeonly>)."""
    old_cat = first_letter_case_insensitive(rx.escape(old_cat))
    cat = r"\[\[" + _cat_ns_ci() + " ?" + old_cat + r"( ?\]\]| ?\|[^\|]*?\]\])"
    if "<includeonly>" not in article_text:
        article_text = _R(cat + "\r\n").replace(article_text, "")
    return _R(cat).replace(article_text, "")


def category_match(article_text: str, category_name: str) -> bool:
    """Whether the text is in the category (name as written, case-insensitive)."""
    # performance: only search from the first category
    cq = W.for_site(current_site()).CategoryQuick.match(article_text)
    if cq:
        any_category = _R(
            r"\[\[\s*"
            + _cat_ns_ci()
            + r"\s*"
            + rx.escape(category_name)
            + r"\s*(?:|\|([^\|\]]*))\s*\]\]",
            O.IGNORE_CASE,
        )
        return any_category.is_match(article_text[cq.index :])
    return False


def get_cats(article_text: str) -> str:
    """All category links, concatenated."""
    s = W.for_site(current_site())
    return "".join(
        lnk
        for lnk in dict.fromkeys(_wikilinks.get_all_wiki_links(article_text))
        if ":" in lnk and s.Category.is_match(lnk)
    )


# -- DEFAULTSORT ----------------------------------------------------------------------------------


def missing_default_sort(article_text: str, article_title: str) -> bool:
    """Whether AWB would add a DEFAULTSORT."""
    s = W.for_site(current_site())
    if not s.Defaultsort.is_match(article_text):
        article_text, skip = change_to_default_sort(article_text, article_title)
        return not skip and s.Defaultsort.is_match(article_text)
    return False


def get_category_sort(article_text: str) -> str:
    """The sort key all categories share (no DEFAULTSORT), or ""."""
    if len(W.for_site(current_site()).Defaultsort.matches(article_text)) == 1:
        return ""
    dummy = "@@@@"
    sort, _ = get_category_sort_count(article_text, dummy)
    return "" if sort == dummy else sort


def get_category_sort_count(article_text: str, article_title: str) -> tuple[str, int]:
    """(the sort key all categories share, or "", number of categories); keys default to the
    title. AWB's GetCategorySort overload with an out int."""
    sort = ""
    all_same = True
    matches = 0
    article_text = article_text.replace("{{PAGENAME}}", article_title).replace(
        "{{subst:PAGENAME}}", article_title
    )
    for m in W.for_site(current_site()).Category.matches(article_text):
        explicit_key = m.group(2) or article_title
        if not sort:
            sort = explicit_key
        if sort != explicit_key and explicit_key:
            all_same = False
            break
        matches += 1
    if all_same and matches > 0:
        return sort, matches
    return "", matches


def change_to_default_sort(
    article_text: str, article_title: str, restrict_defaultsort_changes: bool = False
) -> tuple[str, bool]:
    """Add or tidy {{DEFAULTSORT}}: merge identical duplicates, use a common category sort key,
    add one for titles with diacritics or people, drop category keys equal to it.
    Returns (text, no_change)."""
    from pyawb.core import tools
    from pyawb.core.parsers import fixsyntax as _fixsyntax
    from pyawb.core.parsers import parsers as _parsers

    site = current_site()
    s = W.for_site(site)
    original = article_text

    ds = s.Defaultsort.matches(article_text)
    if len(ds) > 1 or (len(ds) == 1 and "DEFAULTSORT" not in ds[0].value.upper()):
        # [[WP:AWB/FR/Archive_5#Detect_multiple_DEFAULTSORT]]: if all the same, keep one
        last_value = ""
        all_same = False
        for m in ds:
            if not last_value:
                last_value = m.value
                all_same = True
            else:
                all_same = m.value == last_value
        if all_same:
            article_text = s.Defaultsort.replace(article_text, "", len(ds) - 1)
        else:
            return article_text, True

    # performance: only replace and refresh if the DEFAULTSORT would change
    if ds and site.lang_code == "en" and _fixsyntax.defaultsort_me(ds[0]) != ds[0].value:
        article_text = s.Defaultsort.replace(article_text, _fixsyntax.defaultsort_me)
        ds = s.Defaultsort.matches(article_text)  # again, after normalisation

    # [[WP:AWB/B/Archive_9#AWB_didn't_fix_special_characters_in_a_pipe]]
    article_text = fix_categories(article_text)

    if not restrict_defaultsort_changes:
        # [[WP:AWB/B/Archive_12#defaultsort_adding_namespace]]
        article_title = tools.remove_namespace_string(article_title)

        if not ds:
            sort, matches = get_category_sort_count(article_text, article_title)
            # not for sort keys like "*" or " "; MediaWiki treats leading spaces differently for
            # DEFAULTSORT; only if all categories share a suitable key (not just the title)
            if len(sort) > 4 and matches > 1 and not sort.startswith(" "):
                # remove the keys from the categories
                article_text = s.Category.replace(article_text, "[[" + _cat_ns() + "$1]]")
                # use the shared key as DEFAULTSORT unless it is the title (case-insensitively)
                if (
                    sort != article_title
                    and tools.fixup_default_sort(sort).lower() != article_title.lower()
                ) or (
                    not site.unicode_category_collation
                    and tools.remove_diacritics(sort) != sort
                    and not _parsers.is_article_about_a_person(article_text, article_title, False)
                ):
                    article_text += (
                        tools.newline("{{DEFAULTSORT:") + tools.fixup_default_sort(sort) + "}}"
                    )
            # [[WP:AWB/FR#Add_defaultsort_to_pages_with_special_letters_and_no_defaultsort]],
            # [[WP:AWB/B/Archive_11#Human_DEFAULTSORT]]
            article_text = _defaultsort_titles_with_diacritics(
                article_text,
                article_title,
                matches,
                _parsers.is_article_about_a_person(article_text, article_title, True),
            )
        elif len(ds) == 1:  # already has a DEFAULTSORT
            key = ds[0].group(1).lstrip("|")
            fixed = tools.fixup_default_sort(
                key,
                _human_default_sort_cleanup_required(ds[0])
                and _parsers.is_article_about_a_person(article_text, article_title, True),
            ).strip()
            # not just for casing
            if fixed.lower() != ds[0].group(1).lower() and fixed:
                article_text = article_text.replace(ds[0].value, "{{DEFAULTSORT:" + fixed + "}}")
            # the key again, in case the replace changed it
            ds = s.Defaultsort.matches(article_text)
            # remove category keys case-insensitively equal to the DEFAULTSORT
            article_text = _explicit_category_sortkeys(article_text, ds[0].group("key"))

    no_change = original == article_text
    # performance: the slow check only if needed
    if not no_change and _parsers.no_include_include_only_programming_element(original):
        return original, True
    return article_text, no_change


def _human_default_sort_cleanup_required(ds: DotNetMatch) -> bool:
    return "'" in ds.group(1) or _WordComma.is_match(ds.group(1))


def _explicit_category_sortkeys(article_text: str, defaultsort_key: str) -> str:
    """Remove category sort keys that the DEFAULTSORT makes redundant."""
    from pyawb.core import tools

    for m in W.for_site(current_site()).Category.matches(article_text):
        explicit_key = m.group(2)
        if not explicit_key:
            continue
        if (
            tools.case_insensitive_string_compare(explicit_key, defaultsort_key)
            or defaultsort_key.startswith(explicit_key)
            or _PageName.is_match(explicit_key)
        ):
            article_text = article_text.replace(m.value, "[[" + _cat_ns() + m.group(1) + "]]")
    return article_text


def _defaultsort_titles_with_diacritics(
    article_text: str, article_title: str, categories: int, article_about_a_person: bool
) -> str:
    """Add a DEFAULTSORT for titles with diacritics, or a "Surname, Forenames" one for people."""
    from pyawb.core import tools

    # need categories, no DEFAULTSORT, and a sort key differing from the title
    if categories > 0 and not W.for_site(current_site()).Defaultsort.is_match(article_text):
        # [[WP:AWB/B/Archive_11#Human_DEFAULTSORT]]
        sortkey = (
            tools.make_human_cat_key(article_title, article_text)
            if article_about_a_person
            else tools.fixup_default_sort(article_title)
        )
        # sort keys are not case sensitive now
        if sortkey.lower() != article_title.lower() or (
            not current_site().unicode_category_collation
            and tools.remove_diacritics(article_title) != article_title
        ):
            article_text += tools.newline("{{DEFAULTSORT:") + sortkey + "}}"
            return _explicit_category_sortkeys(article_text, sortkey)
    return article_text


# -- people categories ----------------------------------------------------------------------------


def fix_people_categories(
    article_text: str, article_title: str, parse_talk_page: bool = False
) -> str:
    """Add "XXXX births"/"XXXX deaths" (or "year of birth uncertain") categories to articles
    about people, from birth/death templates, infoboxes and "(born ...)" text (en only)."""
    from pyawb.core import tools
    from pyawb.core.parsers import parsers as _parsers

    site = current_site()
    s = W.for_site(site)
    if site.lang_code != "en":
        return article_text

    # performance: births/deaths checks on the categories only
    cats = get_cats(article_text)
    dol_match = W.DeathsOrLivingCategory.is_match(cats)
    bi_match = W.BirthsCategory.is_match(cats)

    # nothing to do if there are already birth and death/living categories
    if dol_match and bi_match:
        return _year_of_birth_death_missing_category(article_text, cats)
    # over 20 references or long, and not categorised by birth/death at all: implausible
    if (len(article_text) > 15000 and not bi_match and not dol_match) or (
        not dol_match and len(W.Refs.matches(article_text)) > 20
    ):
        return _year_of_birth_death_missing_category(article_text, cats)

    before = article_text
    cat_count = len(s.Category.matches(article_text))

    # the zeroth section, without references and long wikilinks (ISO dates allowed) that may
    # give false birth/death dates
    zeroth = tools.get_zeroth_section(article_text)
    zeroth = W.Refs.replace(zeroth, " ")
    zeroth = _FootnoteTemplates.replace(zeroth, " ")
    while _LongWikilink.is_match(zeroth):
        zeroth = _LongWikilink.replace(zeroth, " ")
    # ignore years from dated maintenance tags etc.
    zeroth = W.NestedTemplates.replace(
        zeroth,
        lambda m2: (
            ""
            if _ThreeOrFourDigitNumber.is_match(
                tools.get_template_parameter_value(m2.value, "date")
            )
            else m2.value
        ),
    )
    zeroth = W.TemplateMultiline.replace(
        zeroth,
        lambda m2: (
            ""
            if _ThreeOrFourDigitNumber.is_match(
                tools.get_template_parameter_value(m2.value, "date")
            )
            else m2.value
        ),
    )

    start_category = tools.newline(
        "[[" + ("" if namespace.is_main_space(article_title) else ":") + "Category:"
    )
    sort = get_category_sort(article_text)
    already_uncertain = False
    this_year = datetime.date.today().year

    # birth year from any infobox, ignoring {{Birth date based on age at death}}
    year_from_infobox = ""
    from_infobox = _templates.get_info_box_field_value(
        _BirthDateBasedOnAgeAtDeath.replace(zeroth, ""), W.InfoBoxDOBFields
    )
    # ignore "as of" dates
    if _AsOfText.is_match(from_infobox):
        from_infobox = from_infobox[: _AsOfText.match(from_infobox).index]
    if (
        from_infobox
        and not _parsers.UncertainWordings.is_match(from_infobox)
        and not _FloruitTemplate.is_match(from_infobox)
    ):
        year_from_infobox = _YearPossiblyWithBC.match(from_infobox).value

    # [[:Category -> [[Category for checking outside mainspace
    check_text = (
        article_text
        if namespace.is_main_space(article_title)
        else article_text.replace("[[:", "[[")
    )

    # birth
    if not W.BirthsCategory.is_match(check_text) and (
        len(_PersonYearOfBirth.matches(zeroth)) == 1
        or W.DateBirthAndAge.is_match(zeroth)
        or W.DeathDateAndAge.is_match(zeroth)
        or _ThreeOrFourDigitNumber.is_match(year_from_infobox)
    ):
        # {{birth date...}} first, then {{death date and age}}, then the infobox
        year = W.DateBirthAndAge.match(article_text).group(1)
        if not year:
            year = W.DeathDateAndAge.match(article_text).group(2)
        if _ThreeOrFourDigitNumber.is_match(year_from_infobox):
            year = year_from_infobox
        # then "(born xxxx)"
        if not year:
            m = _PersonYearOfBirth.match(zeroth)
            # the part before any dash or "died"
            birth_part = _DiedOrBaptised.replace(m.value, "$1")
            if W.CircaTemplate.is_match(birth_part) or _FloruitTemplate.is_match(birth_part):
                already_uncertain = True
            birth_part = W.TemplateMultiline.replace(birth_part, " ")
            # born info before any untemplated died info
            if not (
                m.index > _PersonYearOfDeath.match(zeroth).index
            ) or not _PersonYearOfDeath.is_match(zeroth):
                # only an approximate birth year: the "uncertain" category instead
                if _parsers.UncertainWordings.is_match(birth_part) or already_uncertain:
                    if not category_match(
                        article_text, YearOfBirthMissingLivingPeople
                    ) and not category_match(article_text, YearOfBirthUncertain):
                        article_text += start_category + YearOfBirthUncertain + _cat_end(sort)
                # after removing dashes the birth part must still have a year, not a range
                elif (
                    "?" not in birth_part
                    and _Digits34.is_match(birth_part)
                    and not _YearRangeInBirth.is_match(m.value)
                ):
                    year = m.group(1)

        # not born > 121 years ago with [[:Category:Living people]]; a YYYY year not in the future
        if (
            len(year) > 2
            and (not _YearOnly.is_match(year) or int(year) <= this_year)
            and not (
                _CategoryLivingPeople in article_text
                and _YearOnly.is_match(year)
                and int(year) < this_year - 121
            )
        ):
            article_text += start_category + year + " births" + _cat_end(sort)

    # death year from any infobox
    year_from_infobox = ""
    from_infobox = _templates.get_info_box_field_value(
        W.DateBirthAndAge.replace(zeroth, ""), W.InfoBoxDODFields
    )
    if from_infobox and not _parsers.UncertainWordings.is_match(from_infobox):
        year_from_infobox = _YearPossiblyWithBC.match(from_infobox).value

    check_text = (
        article_text
        if namespace.is_main_space(article_title)
        else article_text.replace("[[:", "[[")
    )
    if not W.DeathsOrLivingCategory.is_match(remove_category(YearofDeathMissing, check_text)) and (
        _PersonYearOfDeath.is_match(zeroth)
        or W.DeathDate.is_match(zeroth)
        or _ThreeOrFourDigitNumber.is_match(year_from_infobox)
    ):
        # {{death date...}} first, then the infobox, then "(died xxxx)"
        year = W.DeathDate.match(article_text).group(1)
        if _ThreeOrFourDigitNumber.is_match(year_from_infobox):
            year = year_from_infobox
        if not year:
            m = _PersonYearOfDeath.match(zeroth)
            # died info after any untemplated born info
            born_first = m.index >= _PersonYearOfBirth.match(zeroth).index
            if (born_first or not _PersonYearOfBirth.is_match(zeroth)) and (
                not _parsers.UncertainWordings.is_match(m.value) and "?" not in m.value
            ):
                year = m.group(1)
        # a YYYY year not in the future
        if len(year) > 2 and (not _YearOnly.is_match(year) or int(year) <= this_year):
            article_text += start_category + year + " deaths" + _cat_end(sort)

    zeroth = _NotCircaTemplate.replace(zeroth, " ")
    # birth and death together, if not fully categorised
    if _PersonYearOfBirthAndDeath.is_match(zeroth) and (
        not W.BirthsCategory.is_match(article_text)
        or not W.DeathsOrLivingCategory.is_match(article_text)
    ):
        m = _PersonYearOfBirthAndDeath.match(zeroth)
        birth_year, death_year = m.group(1), m.group(3)
        birth_int, death_int = int(birth_year), int(death_year)
        # logical validation of the dates
        if birth_int <= death_int - 2 and death_int - birth_int <= 125:
            birth_part = zeroth[m.index : m.start(2)]
            death_part = zeroth[m.start(2) : m.index + m.length]
            uncertain = _parsers.UncertainWordings
            ruled = _parsers.ReignedRuledUnsure
            if not W.BirthsCategory.is_match(article_text):
                if (
                    not uncertain.is_match(birth_part)
                    and not ruled.is_match(m.value)
                    and not _DiedOrDot.is_match(birth_part)
                    and not _FloruitTemplate.is_match(birth_part)
                ):
                    article_text += start_category + birth_year + " births" + _cat_end(sort)
                elif (
                    uncertain.is_match(birth_part)
                    and not category_match(article_text, YearOfBirthMissingLivingPeople)
                    and not category_match(article_text, YearOfBirthUncertain)
                ):
                    article_text += start_category + YearOfBirthUncertain + _cat_end(sort)
            if (
                not uncertain.is_match(death_part)
                and not ruled.is_match(m.value)
                and not _BornOrDot.is_match(death_part)
                and not _DiedOrDotOnly.is_match(birth_part)
                and (
                    not W.DeathsOrLivingCategory.is_match(article_text)
                    or category_match(article_text, YearofDeathMissing)
                )
            ):
                article_text += start_category + death_year + " deaths" + _cat_end(sort)

    # last, as is_article_about_a_person can be slow
    if article_text != before and not _parsers.is_article_about_a_person(
        before, article_title, parse_talk_page
    ):
        return _year_of_birth_death_missing_category(before, cats)

    # {{uncat}} -> {{Improve categories}} if categories were added
    if (
        len(s.Category.matches(article_text)) > cat_count
        and s.Uncategorized.is_match(article_text)
        and not W.CatImprove.is_match(article_text)
    ):
        article_text = tools.rename_template(
            article_text,
            tools.get_template_name(s.Uncategorized.match(article_text).value),
            "Improve categories",
        )

    return _year_of_birth_death_missing_category(article_text, get_cats(article_text))


def _cat_end(sort: str) -> str:
    return ("|" + sort if len(sort) > 3 else "") + "]]"


def _year_of_birth_death_missing_category(article_text: str, cats: str) -> str:
    """Remove "year of birth/death missing" categories made redundant by year categories."""
    # year of birth missing, but a year of birth: remove the "missing" category
    if _Cat4YearBirths.is_match(cats):
        if category_match(cats, YearOfBirthMissingLivingPeople):
            article_text = remove_category(YearOfBirthMissingLivingPeople, article_text)
        elif category_match(cats, YearOfBirthMissing):
            article_text = remove_category(YearOfBirthMissing, article_text)
    # missing and uncertain: remove missing
    if category_match(cats, YearOfBirthMissing) and category_match(cats, YearOfBirthUncertain):
        article_text = remove_category(YearOfBirthMissing, article_text)
    # a year of death and "year of death missing": remove the latter
    if _CatYearDeaths.is_match(cats) and category_match(cats, YearofDeathMissing):
        article_text = remove_category(YearofDeathMissing, article_text)
    # full date of birth in {{birth date and age}}: remove "Date of birth missing" categories
    if cats.lower().find("date of birth missing") > 0 and _FullDob.is_match(
        W.DateBirthAndAge.match(article_text).value
    ):
        article_text = remove_category("Date of birth missing", article_text)
        article_text = remove_category("Date of birth missing (living people)", article_text)
    return article_text


# -- category syntax ------------------------------------------------------------------------------


def fix_categories(article_text: str) -> str:
    """Tidy category links: extra brackets, spacing, underscores, first letter, sort keys."""
    site = current_site()
    s = W.for_site(site)
    category_start = "[[" + site.namespaces.get(Namespace.CATEGORY, "Category:")
    # performance: only the part of the text with categories
    cq = s.CategoryQuick.match(article_text)
    if not cq:
        return article_text
    # allow some characters before the category in case of excess opening brackets
    cutoff = max(0, cq.index - 2)
    cats = article_text[cutoff:]
    cats_original = cats
    esc_start = rx.escape(category_start)
    # extra brackets: three or more at the end, three or more at the start
    cats = _R("(" + esc_start + r"[^\r\n\[\]{}<>]+\]\])\]+").replace(cats, "$1")
    cats = _R(r"\[+(?=" + esc_start + r"[^\r\n\[\]{}<>]+\]\])").replace(cats, "")
    cats = s.LooseCategory.replace(cats, lambda m: _loose_category_me(m, category_start))
    if cats == cats_original:  # performance: no changes
        return article_text
    return article_text[:cutoff] + cats


def _loose_category_me(m: DotNetMatch, category_start: str) -> str:
    from pyawb.core import tools
    from pyawb.core.parsers import parsers as _parsers

    if not tools.is_valid_title(m.group(1)):
        return m.value
    sortkey = m.group(2)
    if sortkey:
        # diacritics removed from sort keys on en/simple wikis only
        if current_site().lang_code in ("en", "simple"):
            sortkey = tools.clean_sort_key(sortkey)
        sortkey = _WordWhitespaceEndofline.replace(sortkey, "$1")
    return (
        category_start
        + turn_first_to_upper(
            _parsers.canonicalize_title_raw(m.group(1), False).strip().lstrip(":")
        )
        + sortkey
        + "]]"
    )


class CategoryDefaultSortMixin:
    """Instance methods of Parsers from CategoryDefaultSort.cs."""

    def sort_meta_data(
        self, article_text: str, article_title: str, fix_optional_whitespace: bool = True
    ) -> str:  # provided by Parsers
        raise NotImplementedError

    def add_category_no_change(
        self, new_category: str, article_text: str, article_title: str
    ) -> tuple[str, bool]:
        """AWB's overload AddCategory(..., out noChange): returns (text, no_change)."""
        new_text = self.add_category(new_category, article_text, article_title)
        return new_text, new_text == article_text

    def add_category(self, new_category: str, article_text: str, article_title: str) -> str:
        """Add a category (inside <noinclude> on templates) and sort the metadata."""
        from pyawb.core import tools

        old_text = article_text
        article_text = fix_categories(article_text)
        if _R(r"\[\[" + _cat_ns_ci() + rx.escape(new_category) + r"[\|\]]").is_match(article_text):
            return old_text
        cat = tools.newline("[[" + _cat_ns() + new_category + "]]")
        cat = tools.apply_key_words(article_title, cat)
        if namespace.determine(article_title) == Namespace.TEMPLATE:
            article_text += "<noinclude>" + cat + tools.newline("</noinclude>")
        else:
            article_text += cat
        # sort the metadata so general fixes need not be enabled
        return self.sort_meta_data(article_text, article_title, False)

    def fix_people_categories(
        self, article_text: str, article_title: str, parse_talk_page: bool = False
    ) -> str:
        return fix_people_categories(article_text, article_title, parse_talk_page)

    def fix_people_categories_no_change(
        self, article_text: str, article_title: str, parse_talk_page: bool = False
    ) -> tuple[str, bool]:
        """AWB's overloads FixPeopleCategories(..., [parseTalkPage,] out noChange): returns
        (text, no_change)."""
        new_text = self.fix_people_categories(article_text, article_title, parse_talk_page)
        return new_text, new_text == article_text
