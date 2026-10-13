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
# Ported from AutoWikiBrowser AWB/Main.cs (the edit box menu, mnuTextBox) and
# WikiFunctions/Background/Background.cs (BypassRedirectsFunc).
# Copyright (C) the AutoWikiBrowser contributors (GPL-2.0-or-later).
"""The edit box's context menu commands, as functions over (text, selection) returning an Edit
(text[start:end] replaced, then a selection). Qt only passes the selection in and out.

AWB wrote "\\r\\n" (Windows Forms text boxes); the Qt editor holds "\\n".
"""

from __future__ import annotations

import difflib
from collections.abc import Mapping

from pyawb.core import tools, wikiregexes
from pyawb.core.parsers import categorydefaultsort
from pyawb.core.parsers.hidetext import HideText
from pyawb.core.parsers.parsers import Parsers, remove_all_white_space
from pyawb.core.rx import DotNetMatch, DotNetRegex
from pyawb.core.site import current_site
from pyawb.editor.textselection import Edit, EncapsulateOptions, encapsulate_selection

# AWB's "Insert tag" texts. The month/year substs date the tag when saved.
DATED = "date={{subst:CURRENTMONTHNAME}} {{subst:CURRENTYEAR}}"
WIKIFY = "{{Wikify|" + DATED + "}}"
CLEANUP = "{{cleanup|" + DATED + "}}"
UNCATEGORISED = "{{Uncategorized|" + DATED + "}}"
CLEAR = "{{subst:clear}}"
DISAMBIGUATION = "{{Disambiguation}}"
DEFAULT_STUB = "{{stub}}"


def replace_selection(text: str, start: int, end: int, insert: str) -> Edit:
    """txtEdit.SelectedText = insert: the selection replaced, the cursor after it."""
    start, end = min(start, end), max(start, end)
    return Edit(start, end, insert, start + len(insert), start + len(insert))


def whole_text(text: str, new: str, cursor: int = 0) -> Edit:
    """txtEdit.Text = new."""
    cursor = min(cursor, len(new))
    return Edit(0, len(text), new, cursor, cursor)


def prepend_tag(text: str, tag: str) -> Edit:
    """Wikify / Cleanup / Speedy delete: the tag and a blank line before the page."""
    return whole_text(text, tag + "\n\n" + text)


def speedy_delete_tag(reason: str) -> str:
    return "{{db|" + reason.strip() + "}}"


def comment_selected(text: str, start: int, end: int) -> Edit:
    """Comment selected (Ctrl+K), AWB's imgComment: <!-- selection -->, or a sample comment."""
    return encapsulate_selection(
        text, start, end, EncapsulateOptions(pre="<!-- ", peri="Comment", post=" -->")
    )


def convert_list(text: str, start: int, end: int, bullet: str) -> Edit:
    """Convert list to ▸ * / #: Tools.HTMLListToWiki on the selection."""
    selected = text[min(start, end) : max(start, end)].replace("\n", "\r\n")
    converted = tools.html_list_to_wiki(selected, bullet).replace("\r\n", "\n")
    return replace_selection(text, start, end, converted)


def unicodify_selected(text: str, start: int, end: int, parsers: Parsers) -> Edit:
    return replace_selection(
        text, start, end, parsers.unicodify(text[min(start, end) : max(start, end)])
    )


def fix_all_excess_whitespace(text: str) -> Edit:
    """Parsers.RemoveAllWhiteSpace outside comments, nowiki, math… (AWB's RemoveText)."""
    hider = HideText(False, True, True)
    new = hider.add_back(remove_all_white_space(hider.hide(text.replace("\n", "\r\n"))))
    return whole_text(text, new.replace("\r\n", "\n"))


def human_name_defaultsort(text: str, start: int, end: int, title: str) -> Edit:
    """Insert tag ▸ Human name DEFAULTSORT."""
    key = tools.make_human_cat_key(title, text)
    return replace_selection(text, start, end, "{{DEFAULTSORT:" + key + "}}")


def human_name_disambig(text: str, start: int, end: int, title: str) -> Edit:
    """Insert tag ▸ Human name disambig tag."""
    key = tools.make_human_cat_key(title, text)
    return replace_selection(text, start, end, "{{Hndis|name=" + key + "}}")


_Years = DotNetRegex("[12][0-9]{3}")


def birth_death_categories(text: str, title: str) -> str:
    """Insert ▸ Guess birth/death cats: the first two years in the text (not in file links or
    dated templates) as "[[Category:YYYY births|Key]]" and, if at least 20 years later,
    "[[Category:YYYY deaths|Key]]". Empty if the text has no year."""
    site_rx = wikiregexes.for_site(current_site())
    local = tools.replace_with_spaces(text, site_rx.FileNamespaceLink.matches(text))
    for rx in (wikiregexes.NestedTemplates, wikiregexes.TemplateMultiline):
        for m in rx.matches(local):
            if tools.get_template_parameter_value(m.value, "date"):
                local = local.replace(m.value, "")
    years = [m.value for m in _Years.matches(local)]
    if not years:
        return ""
    births = years[0]
    deaths = years[1] if len(years) > 1 else ""
    name = tools.make_human_cat_key(title, text)
    categories = "[[Category:" + births + " births|" + name + "]]"
    if deaths and int(deaths) >= int(births) + 20:
        categories += "\n[[Category:" + deaths + " deaths|" + name + "]]"
    return categories


def insert_birth_death_categories(
    text: str, start: int, end: int, title: str, parsers: Parsers, restrict_defaultsort: bool
) -> Edit | None:
    """The categories at the selection, then DEFAULTSORT tidied (and metadata sorted if it was
    added), as AWB does. None if no year was found."""
    categories = birth_death_categories(text, title)
    if not categories:
        return None
    new = replace_selection(text, start, end, categories).apply(text).replace("\n", "\r\n")
    changed, no_change = categorydefaultsort.change_to_default_sort(
        new, title, restrict_defaultsort
    )
    if not no_change:
        changed = parsers.sort_meta_data(changed, title)
    return whole_text(text, changed.replace("\r\n", "\n"), start + len(categories))


def add_category(text: str, category: str) -> Edit:
    """Insert ▸ Category (Ctrl+T): "[[Category:X]]" after a blank line at the end, and any
    {{Uncategorized}} tag removed. category: the full name with the namespace."""
    new = text + "\n\n[[" + category + "]]"
    new = wikiregexes.for_site(current_site()).Uncategorized.replace(new, "")
    return whole_text(text, new, len(new))


def bypass_redirects(text: str, targets: Mapping[str, str]) -> str:
    """Bypass all redirects: each link to a redirect points at its target, keeping the link's
    text ([[A]] -> [[B|A]], [[A|x]] -> [[B|x]]). targets: first-letter-upper title -> target,
    for the links that are redirects (api.pageinfo.redirect_targets)."""

    def fix(m: DotNetMatch) -> str:
        article = m.group(1).lstrip(":")
        link_text = m.group(2) or article
        dest = targets.get(tools.turn_first_to_upper(article))
        if dest is None:
            return m.value
        return "[[" + dest + "|" + link_text + "]]"

    return wikiregexes.WikiLinksOnlyPossiblePipe.replace(text, fix)


def link_targets(text: str) -> list[str]:
    """The pages the text links to, first letter upper, without repeats (for bypass_redirects)."""
    found: dict[str, None] = {}
    for m in wikiregexes.WikiLinksOnlyPossiblePipe.matches(text):
        found[tools.turn_first_to_upper(m.group(1).lstrip(":"))] = None
    return [t for t in found if t]


def line_start(text: str, line: int) -> int:
    """Go to line: the offset of line (1-based; past the end goes to the last line)."""
    pos = 0
    for _ in range(max(line, 1) - 1):
        nl = text.find("\n", pos)
        if nl < 0:
            break
        pos = nl + 1
    return pos


def is_url(selection: str) -> bool:
    """Open text selection in browser: a URL opens as one, anything else as a page title."""
    s = selection.strip()
    return wikiregexes.UrlValidator.is_match(s) or s.lower().startswith("http")


def undo_line_changes(original: str, current: str, line: int) -> str | None:
    """A double click on the diff (AWB: "double click on a line to undo all changes on that
    line"): line (1-based, in current) goes back to the original. Where lines were added or
    removed, the whole changed block does (a deleted line is at the line after it). None if
    that line is unchanged."""
    old = original.split("\n")
    new = current.split("\n")
    index = line - 1
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and i2 - i1 == j2 - j1 and j1 <= index < j2:
            # lines changed one for one: only the clicked line goes back
            return "\n".join([*new[:index], old[i1 + index - j1], *new[index + 1 :]])
        if j1 <= index < j2 or (j1 == j2 and index == j1):
            return "\n".join(new[:j1] + old[i1:i2] + new[j2:])
    return None
