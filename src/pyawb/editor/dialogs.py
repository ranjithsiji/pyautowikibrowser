# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# Ported from WikiEditor's modules/jquery.wikiEditor.dialogs.config.js and modules/insertlink/
# (GPL-2.0-or-later, (C) WikiEditor contributors) and the suggestion ordering of MediaWiki core's
# mw.widgets.TitleWidget (GPL-2.0-or-later, (C) MediaWiki contributors).
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""The logic of WikiEditor's dialogs, without Qt: insert link, insert file, insert table, search and
replace. Each "Insert" returns the TextAction WikiEditor passes to doAction; the Qt dialogs in
pyawb.ui.editor_dialogs only collect the fields.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import regex

from pyawb.core import dotnet_regex, rx
from pyawb.editor.messages import Messages
from pyawb.editor.textselection import Edit, EncapsulateOptions, TextAction, encapsulate_selection
from pyawb.editor.toolbar import ToolbarSite


def _replace(pre: str = "", peri: str = "", post: str = "", ownline: bool = False) -> TextAction:
    return TextAction("replace", EncapsulateOptions(pre=pre, peri=peri, post=post, ownline=ownline))


# --- titles (the parts of mw.Title the dialogs use) ---------------------------------------------

# MediaWiki's $wgLegalTitleChars, as characters that are NOT legal
_ILLEGAL_TITLE = regex.compile(
    r"[^ %!\"$&'()*,\-./0-9:;=?@A-Z\\^_`a-z~\x80-\U0010FFFF+]|%[0-9A-Fa-f]{2}"
)


def is_valid_title(text: str) -> bool:
    """mw.Title.newFromText(text) !== null, for what the link dialog checks.

    The fragment (#...) is cut off; an empty title, illegal characters, %-escapes, ./ and ../
    paths, ~~~ and titles over 255 bytes are invalid. "#Section" alone is invalid, as in
    mw.Title.
    """
    title = text.split("#", 1)[0].replace("_", " ").strip()
    if not title or title == ":" or _ILLEGAL_TITLE.search(title):
        return False
    if title in (".", "..") or title.startswith(("./", "../")) or "/./" in title:
        return False
    if "/../" in title or title.endswith(("/.", "/..")) or "~~~" in title:
        return False
    return len(title.encode("utf-8")) <= 255


def _ucfirst(s: str) -> str:
    return s[:1].upper() + s[1:]


def split_file_title(name: str, site: ToolbarSite) -> tuple[bool, str]:
    """(is in the File namespace, main text) of a title; spaces normalised as mw.Title does."""
    name = regex.sub(r"[ _]+", " ", name).strip()
    prefix, sep, rest = name.partition(":")
    if sep:
        names = {n.replace("_", " ").casefold() for n in site.file_namespace_names}
        names.add(site.file_namespace.casefold())
        if prefix.strip().casefold() in names:
            rest = rest.strip()
            return True, _ucfirst(rest) if site.capitalize_first_letter else rest
    return False, _ucfirst(name) if site.capitalize_first_letter else name


# --- insert link ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LinkFields:
    """The link dialog's fields as pre-filled from the selection (open())."""

    target: str = ""
    text: str = ""
    is_external: bool | None = None  # None: not decided by the selection
    whitespace: tuple[str, str] = ("", "")
    # the text field was set from the selection: don't copy the target into it
    text_touched: bool = False


_SEL_INTERNAL = regex.compile(r"^(\s*)\[\[([^\]|]+)(\|([^\]|]*))?\]\](\s*)\Z")
_SEL_EXTERNAL = regex.compile(r"^(\s*)\[([^\] ]+)( ([^\]]+))?\](\s*)\Z")


def link_fields_from_selection(selection: str) -> LinkFields:
    if selection == "":
        return LinkFields()
    m = _SEL_INTERNAL.match(selection)
    if m:
        # [[foo|bar]] or [[foo]]
        return LinkFields(m[2], m[4] or m[2], False, (m[1], m[5]), True)
    m = _SEL_EXTERNAL.match(selection)
    if m:
        # [http://www.example.com foo] or [http://www.example.com]
        return LinkFields(m[2], m[4] or "", True, (m[1], m[5]), True)
    # Trim any leading and trailing whitespace from the selection, but preserve it when replacing
    target = selection.strip()
    whitespace = ("", "")
    if target and len(target) < len(selection):
        whitespace = (
            selection[: selection.index(target[0])],
            selection[selection.rindex(target[-1]) + 1 :],
        )
    return LinkFields(target, target, None, whitespace, True)


def _protocols_pattern(site: ToolbarSite) -> str:
    return "|".join(regex.escape(p) for p in site.url_protocols)


def looks_like_external_link(value: str, site: ToolbarSite) -> bool:
    """TitleInputWidget.looksLikeExternalLink: starts with a URL protocol or www."""
    return regex.match(f"(?i)^(?:{_protocols_pattern(site)}|www\\.)", value) is not None


def article_path_regex(site: ToolbarSite) -> regex.Pattern[str]:
    """The link dialog's articlePathRegex: a URL of a page on this wiki."""
    server_name = regex.sub(r"^(https?:)?//", "", site.server)
    escaped = regex.escape(server_name + site.article_path).replace(r"\$1", "(.*)")
    return regex.compile(f"^https?://{escaped}\\Z")


_URI_RESERVED = set(";/?:@&=+$,#")


def decode_uri(s: str) -> str:
    """JavaScript's decodeURI: %-escapes decoded, except reserved characters; invalid -> s."""

    def one(m: regex.Match[str]) -> str:
        decoded = bytes.fromhex(m[0].replace("%", "")).decode("utf-8")
        return "".join(f"%{ord(ch):02X}" if ch in _URI_RESERVED else ch for ch in decoded)

    try:
        return regex.sub(r"(?:%[0-9A-Fa-f]{2})+", one, s)
    except UnicodeDecodeError:
        return s


def _escape_internal_text(s: str) -> str:
    return regex.sub(r"(\]{2,})", r"<nowiki>\1</nowiki>", s)


def _escape_external_target(s: str) -> str:
    return s.replace(" ", "%20").replace("[", "%5B").replace("]", "%5D")


def _escape_external_text(s: str) -> str:
    return regex.sub(r"(\]+)", r"<nowiki>\1</nowiki>", s)


@dataclass(frozen=True, slots=True)
class LooksInternal:
    """An external link that points to this wiki: ask whether to make it internal (the title)."""

    title: str


def insert_link(
    target: str,
    text: str,
    internal: bool,
    site: ToolbarSite,
    whitespace: tuple[str, str] = ("", ""),
    ignore_looks_internal: bool = False,
) -> TextAction | LooksInternal:
    """The link dialog's Insert button."""
    if text.strip() == "":
        # [[Foo| ]] creates an invisible link; instead, generate [[Foo|]]
        text = ""
    if internal:
        if target == text or not text:
            insert_text = f"[[{target}]]"
        else:
            insert_text = f"[[{target}|{_escape_internal_text(text)}]]"
    else:
        target = target.strip()
        # Prepend http:// if there is no protocol
        if not regex.match(f"^(?:{_protocols_pattern(site)}).", target):
            target = "http://" + target
        # Detect if this is really an internal link in disguise
        m = article_path_regex(site).match(target)
        if m and not ignore_looks_internal:
            return LooksInternal(decode_uri(m[1]))
        esc_target = _escape_external_target(target)
        esc_text = _escape_external_text(text)
        if esc_target == esc_text and not target.startswith("//"):
            insert_text = esc_target
        elif text == "":
            insert_text = f"[{esc_target}]"
        else:
            insert_text = f"[{esc_target} {esc_text}]"
    # Preserve whitespace in selection when replacing
    return _replace(pre=whitespace[0] + insert_text + whitespace[1])


# --- link target suggestions (mw.widgets.TitleWidget) -------------------------------------------


@dataclass(frozen=True, slots=True)
class TitleOption:
    title: str
    description: str | None = None
    missing: bool = False
    redirect: bool = False
    disambiguation: bool = False
    external: bool = False


def title_options(
    result: Mapping[str, Any], query: str, site: ToolbarSite, redirect_msg: str = "→ $1"
) -> list[TitleOption]:
    """TitleWidget.getOptionsFromData for a formatversion=2 `query` result: pages in prefix
    search order, each redirect just below its target, disambiguation pages last, and the typed
    text first when it names an existing page under another spelling (addQueryInput).

    redirect_msg is mw-widgets-titleinput-description-redirect ("redirect to $1").
    """
    redirects_to: dict[str, list[str]] = {}
    redirect_index: dict[str, float] = {}
    for r in result.get("redirects", []):
        redirects_to.setdefault(r["to"], []).append(r["from"])
        index = r.get("index", 0)
        redirect_index[r["to"]] = min(redirect_index.get(r["to"], index), index)

    data: dict[str, dict[str, Any]] = {}
    titles: list[str] = []
    for page in result.get("pages", []):
        title = page["title"]
        missing = bool(page.get("missing"))
        data[title] = {
            "known": bool(page.get("known")),
            "missing": missing,
            "redirect": bool(page.get("redirect")),
            "disambiguation": "disambiguation" in page.get("pageprops", {}),
            "description": page.get("description"),
            "index": page.get("index", redirect_index.get(title, 0)),
            # TitleInputWidget.getLookupCacheDataFromResponse
            "external": missing and looks_like_external_link(title, site),
        }
        titles.append(title)
        for source in redirects_to.get(title, []):
            data[source] = {
                "known": True,
                "missing": False,
                "redirect": True,
                "disambiguation": False,
                "description": redirect_msg.replace("$1", title),
                "index": data[title]["index"] + 0.5,
                "external": False,
            }
            titles.append(source)
    titles.sort(key=lambda t: data[t]["index"])

    def exists(t: str) -> bool:
        return t in data and (not data[t]["missing"] or data[t]["known"])

    normalised = (
        _ucfirst(query.replace("_", " ").strip()) if site.capitalize_first_letter else query
    )
    if exists(normalised) and not exists(query) and query:
        titles.insert(0, query)
        data[query] = data[normalised]

    items: list[TitleOption] = []
    disambigs: list[TitleOption] = []
    for t in titles:
        d = data[t]
        option = TitleOption(
            t,
            d["description"],
            d["missing"] and not d["known"],
            d["redirect"],
            d["disambiguation"],
            d["external"],
        )
        (disambigs if d["disambiguation"] else items).append(option)
    return items + disambigs


def first_match(options: Sequence[TitleOption], query: str) -> TitleOption | None:
    """TitleInputWidget.selectFirstMatch: the exact title, or with an upper-case first letter."""
    for option in options:
        if option.title in (query, _ucfirst(query)):
            return option
    return None


def link_status(
    option: TitleOption | None, external_mode: bool, mode_manual: bool
) -> tuple[str, str] | None:
    """TitleInputField.onSelect: (icon, message key) shown under the target field."""
    if option is None:
        return None
    if external_mode or (not mode_manual and option.external):
        return "linkExternal", "wikieditor-toolbar-tool-link-int-target-status-external"
    if option.disambiguation:
        return "articleDisambiguation", "wikieditor-toolbar-tool-link-int-target-status-disambig"
    if not option.missing and not option.external:
        return "article", "wikieditor-toolbar-tool-link-int-target-status-exists"
    return "articleNotFound", "wikieditor-toolbar-tool-link-int-target-status-notexists"


# --- insert file ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FileFields:
    file_name: str = ""
    caption: str = ""
    alt: str = ""
    size: str = ""  # without "px"
    float: str = "default"  # "default" or the first alias of img_none/center/left/right
    format: str | None = None  # first alias of img_thumbnail/framed/frameless, or "default"
    whitespace: tuple[str, str] = ("", "")


def default_file_fields(site: ToolbarSite) -> FileFields:
    return FileFields(format=site.magic_word("img_thumbnail"))


_ESCAPED_PIPE = "\u0001"


def parse_file_syntax(wikitext: str, site: ToolbarSite) -> FileFields | None:
    """The file dialog's parseFileSyntax: the fields of a selected [[File:...]], else None."""
    if _ESCAPED_PIPE in wikitext:
        return None
    m = regex.match(r"^(\s*)\[\[(.*)\]\](\s*)\Z", wikitext, flags=regex.S)
    if not m:
        return None
    # Escape pipes inside links and templates, then split the parameters at the remaining pipes.
    # ({{[^{}]}} only matches one-character templates; kept as in WikiEditor.)
    params = regex.sub(
        r"\[\[[^\[\]]*\]\]|\{\{[^{}]\}\}", lambda x: x[0].replace("|", _ESCAPED_PIPE), m[2]
    ).split("|")
    in_file_ns, main = split_file_title(params[0], site)
    if not in_file_ns or not main or not is_valid_title(params[0]):
        return None

    def words(name: str) -> list[str]:
        return [w.lower() for w in site.magic_words.get(name, ())]

    fields: dict[str, Any] = {"whitespace": (m[1], m[3]), "file_name": main}
    for i, orig in enumerate(params[1:], start=1):
        param = orig.lower()
        for name, key in (
            ("img_right", "float"),
            ("img_left", "float"),
            ("img_none", "float"),
            ("img_center", "float"),
            ("img_thumbnail", "format"),
            ("img_framed", "format"),
            ("img_frameless", "format"),
        ):
            if param in words(name):
                fields[key] = site.magic_word(name)
                break
        else:
            if param.split("=", 1)[0] + "=$1" in words("img_alt"):
                fields["alt"] = orig.split("=", 1)[1] if "=" in orig else ""
            elif regex.match(r".+px\Z", param):
                fields["size"] = regex.sub(r"px\Z", "", param)
            elif param == "":
                continue
            elif i == len(params) - 1:
                # Last param -> caption
                fields["caption"] = orig.replace(_ESCAPED_PIPE, "|")
            else:
                # Unknown param
                return None
    fields.setdefault("format", "default")
    return FileFields(**fields)


def file_fields_from_selection(selection: str, site: ToolbarSite) -> FileFields:
    defaults = default_file_fields(site)
    if selection == "":
        return defaults
    parsed = parse_file_syntax(selection, site)
    return parsed if parsed is not None else defaults


def insert_file(fields: FileFields, site: ToolbarSite) -> TextAction:
    """The file dialog's Insert button."""
    size = fields.size
    # Append px to end to size if not already contains it
    if size != "" and not regex.match(r".+px\Z", size):
        size += "px"
    file_name = fields.file_name
    if file_name != "" and is_valid_title(file_name):
        # Append file namespace prefix to filename if not already contains it
        _, main = split_file_title(file_name, site)
        file_name = f"{site.file_namespace}:{main}"
    options = [o for o in (size, fields.format or "", fields.float) if o and o != "default"]
    if fields.alt:
        options.append(site.magic_word("img_alt").replace("$1", fields.alt))
    if fields.caption:
        options.append(fields.caption)
    file_use = file_name if not options else file_name + "|" + "|".join(options)
    return _replace(
        pre=fields.whitespace[0] + "[[",
        peri=file_use,
        post="]]" + fields.whitespace[1],
        ownline=True,
    )


# --- insert table -----------------------------------------------------------------------------

TABLE_MAX_CELLS = 1000


@dataclass(frozen=True, slots=True)
class TableError:
    message: str  # message key
    params: tuple[str, ...] = ()


def _int_field(value: str) -> int | None:
    # String(parseInt(value, 10)) === value
    m = regex.match(r"^-?\d+", value.strip())
    if not m or str(int(m[0])) != value:
        return None
    return int(m[0])


def insert_table(
    rows_value: str,
    columns_value: str,
    header: bool,
    wikitable: bool,
    sortable: bool,
    msg: Messages,
) -> TextAction | TableError:
    """The table dialog's Insert button. rows/columns are the fields' text."""
    rows, cols = _int_field(rows_value), _int_field(columns_value)
    if rows is None or cols is None or rows < 0 or cols < 0:
        return TableError("wikieditor-toolbar-tool-table-invalidnumber")
    head = 1 if header else 0
    if rows + head == 0 or cols == 0:
        return TableError("wikieditor-toolbar-tool-table-zero")
    if rows * cols > TABLE_MAX_CELLS:
        return TableError("wikieditor-toolbar-tool-table-toomany", (str(TABLE_MAX_CELLS),))
    caption_text = msg.text("wikieditor-toolbar-tool-table-example-caption")
    header_text = msg.text("wikieditor-toolbar-tool-table-example-header")
    normal_text = msg.text("wikieditor-toolbar-tool-table-example")
    table = f"|+ {caption_text}\n"
    for r in range(rows + head):
        table += "|-\n"
        for c in range(cols):
            is_header = head and r == 0
            delim = "!" if is_header else "|"
            if c > 0:
                delim += delim
            table += f"{delim} {header_text if is_header else normal_text} "
        # Replace trailing space by newline
        table = table[:-1] + "\n"
    classes = [name for name, on in (("wikitable", wikitable), ("sortable", sortable)) if on]
    class_str = f' class="{" ".join(classes)}"' if classes else ""
    return _replace(pre="{|" + class_str + "\n", peri=table, post="|}", ownline=True)


# --- search and replace -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchResult:
    """What one Find next / Replace / Replace all did."""

    edit: Edit | None = None  # apply to the text first (one undo step)
    selection: tuple[int, int] | None = None  # then select this (in the new text)
    message: str | None = None  # message key to show
    params: tuple[str, ...] = ()


@dataclass
class SearchReplace:
    """The search-and-replace dialog's replaceCallback, with its offset/matchIndex state.

    Patterns use .NET syntax (as AWB's find and replace) through pyawb.core.rx, run with a
    timeout; the replacement uses .NET's $1 / ${name} / $$. WikiEditor uses JavaScript regexes,
    whose syntax is nearly the same for what people type here. Two deliberate differences: with
    "Treat search string as a regular expression" off, the replacement is literal (WikiEditor
    still expands $& and $1 in it), and Replace expands the match's own groups instead of
    matching the regex again on the matched text.
    """

    offset: int = 0
    match_index: int = 0
    timeout: float = rx.DEFAULT_TIMEOUT

    def reset(self) -> None:
        """open(): start from the top."""
        self.offset = self.match_index = 0

    def run(
        self,
        mode: str,  # "find" | "replace" | "replaceAll"
        text: str,
        search: str,
        replacement: str,
        match_case: bool = False,
        is_regex: bool = False,
        match_word: bool = False,
    ) -> SearchResult:
        # Search string cannot be empty
        if search == "":
            return SearchResult(message="wikieditor-toolbar-tool-replace-emptysearch")
        options = rx.DotNetOptions.MULTILINE
        if not match_case:
            options |= rx.DotNetOptions.IGNORE_CASE
        pattern = search if is_regex else dotnet_regex.escape(search)
        if match_word:
            pattern = f"\\b(?:{pattern})\\b"
        if not is_regex:
            replacement = replacement.replace("$", "$$")
        try:
            rgx = rx.DotNetRegex(pattern, options)
        except (dotnet_regex.UnsupportedPatternError, regex.error) as e:
            return SearchResult(
                message="wikieditor-toolbar-tool-replace-invalidregex", params=(str(e),)
            )
        try:
            return self._run(mode, text, rgx, replacement)
        except TimeoutError:
            return SearchResult(
                message="wikieditor-toolbar-tool-replace-invalidregex", params=("timeout",)
            )

    def _search(self, rgx: rx.DotNetRegex, text: str, offset: int) -> rx.DotNetMatch:
        # JavaScript matches on text.slice(offset), so ^ matches at the offset
        return rgx.match(text[offset:], timeout=self.timeout)

    def _run(self, mode: str, text: str, rgx: rx.DotNetRegex, replacement: str) -> SearchResult:
        offset = 0
        match: rx.DotNetMatch | None = None
        if mode != "replaceAll":
            offset = self.match_index if mode == "replace" else self.offset
            match = self._search(rgx, text, offset)
        if not match:
            # Search hit BOTTOM, continuing at TOP
            offset = 0
            match = self._search(rgx, text, 0)
        if not match:
            return SearchResult(message="wikieditor-toolbar-tool-replace-nomatch")

        if mode == "replaceAll":
            count = len(rgx.matches(text, timeout=self.timeout))
            new_text = rgx.replace(text, replacement, timeout=self.timeout)
            self.offset = 0
            return SearchResult(
                edit=Edit(0, len(text), new_text, len(new_text), len(new_text)),
                message="wikieditor-toolbar-tool-replace-success",
                params=(str(count),),
            )

        edit = None
        if mode == "replace":
            actual = rgx.result(match, replacement)
            start = offset + match.index
            edit = encapsulate_selection(
                text,
                start,
                start + match.length,
                EncapsulateOptions(peri=actual, replace=True, select_peri=True),
            )
            text = edit.apply(text)
            # Find the next instance
            offset = start + len(actual)
            match = self._search(rgx, text, offset)
            if not match:
                offset = 0
                match = self._search(rgx, text, 0)
        start = offset + (match.index if match else 0)
        end = start + (match.length if match else 0)
        self.match_index = start
        self.offset = end
        return SearchResult(edit=edit, selection=(start, end))
