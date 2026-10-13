# PyAutoWikiBrowser: cross-platform AutoWikiBrowser
# Copyright (C) 2026 PyAutoWikiBrowser contributors
#
# Ported from WikiEditor's modules/jquery.wikiEditor.toolbar.config.js and the tool entries of
# modules/jquery.wikiEditor.dialogs.config.js (GPL-2.0-or-later, (C) WikiEditor contributors).
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""The WikiEditor toolbar as data: sections, groups, tools, special characters and help pages.

`build_toolbar` follows jquery.wikiEditor.toolbar.config.js section by section, so the two can be
read side by side. Labels come from Messages in the interface language; the signature comes from
the wiki's content language, the file namespace and magic words from the wiki (ToolbarSite).
The Qt widget (pyawb.ui.editor_toolbar) only lays this out and runs the actions.
"""

from __future__ import annotations

import html
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from typing import Any

import regex

from pyawb.editor.messages import Messages
from pyawb.editor.textselection import EncapsulateOptions, RegexReplace, TextAction

_DATA = files("pyawb.editor") / "data" / "wikieditor"


@dataclass(frozen=True, slots=True)
class DialogAction:
    """Opens a WikiEditor dialog: insert-link, insert-file, insert-table or search-and-replace."""

    module: str


Action = TextAction | DialogAction


@dataclass(frozen=True, slots=True)
class SelectOption:
    id: str
    label: str
    action: Action


@dataclass(frozen=True, slots=True)
class Tool:
    id: str
    label: str
    type: str  # "button" | "select"
    icon: str | None = None  # Codex icon name (cdxIconBold -> "bold")
    action: Action | None = None
    hotkey: str | None = None  # used with Ctrl (Cmd on macOS)
    options: tuple[SelectOption, ...] = ()


@dataclass(frozen=True, slots=True)
class Group:
    id: str
    tools: tuple[Tool, ...]
    label: str | None = None


@dataclass(frozen=True, slots=True)
class ToolbarSection:
    """A row of tool groups. 'main' and 'secondary' are always shown; others open from a tab."""

    id: str
    groups: tuple[Group, ...]
    label: str | None = None


@dataclass(frozen=True, slots=True)
class Character:
    label: str
    action: TextAction
    title: str | None = None
    # how the character is written in the config (and in the recently-used list)
    config: Any = None


@dataclass(frozen=True, slots=True)
class CharacterPage:
    id: str
    label: str
    characters: tuple[Character, ...]
    language: str | None = None
    direction: str = "ltr"  # WikiEditor makes every page explicitly ltr unless it says rtl


@dataclass(frozen=True, slots=True)
class HelpRow:
    description: str  # HTML
    syntax: str  # HTML
    result: str  # HTML


@dataclass(frozen=True, slots=True)
class HelpPage:
    id: str
    label: str
    headings: tuple[str, str, str]
    rows: tuple[HelpRow, ...]


@dataclass(frozen=True, slots=True)
class BookletSection:
    """A tab with an index of pages: special characters or help."""

    id: str
    label: str
    pages: tuple[CharacterPage, ...] | tuple[HelpPage, ...]


@dataclass(frozen=True, slots=True)
class Toolbar:
    main: ToolbarSection
    secondary: ToolbarSection
    advanced: ToolbarSection
    characters: BookletSection
    help: BookletSection

    @property
    def tabs(self) -> tuple[ToolbarSection | BookletSection, ...]:
        return (self.advanced, self.characters, self.help)

    def tools(self) -> list[Tool]:
        return [
            t for s in (self.main, self.secondary, self.advanced) for g in s.groups for t in g.tools
        ]


# English defaults of the magic words WikiEditor uses (Hooks::getMagicWords)
MAGIC_WORDS: dict[str, tuple[str, ...]] = {
    "redirect": ("#REDIRECT",),
    "img_alt": ("alt=$1",),
    "img_right": ("right",),
    "img_left": ("left",),
    "img_none": ("none",),
    "img_center": ("center", "centre"),
    "img_thumbnail": ("thumb", "thumbnail"),
    "img_framed": ("frame", "framed", "enframed"),
    "img_frameless": ("frameless",),
}

# MediaWiki's default $wgUrlProtocols
URL_PROTOCOLS: tuple[str, ...] = (
    "bitcoin:", "ftp://", "ftps://", "geo:", "git://", "gopher://", "http://", "https://",
    "irc://", "ircs://", "magnet:", "mailto:", "matrix:", "mms://", "news:", "nntp://",
    "redis://", "sftp://", "sip:", "sips:", "sms:", "ssh://", "svn://", "tel:", "telnet://",
    "urn:", "worldwind://", "xmpp:", "//",
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class ToolbarSite:
    """What the toolbar and its dialogs need from the wiki.

    WikiEditor's data.json (magic words, signature) plus wgFormattedNamespaces, wgUrlProtocols,
    wgServer and wgArticlePath.
    """

    content_language: str = "en"
    sitename: str = "Wikipedia"
    file_namespace: str = "File"
    user_namespace: str = "User"
    user_talk_namespace: str = "User talk"
    # every name of the File namespace (local, canonical, aliases), for reading [[File:...]]
    file_namespace_names: tuple[str, ...] = ("File", "Image")
    # WikiEditor's magicWords: redirect, img_alt, img_right ... (first alias is the preferred one)
    magic_words: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: dict(MAGIC_WORDS))
    url_protocols: tuple[str, ...] = URL_PROTOCOLS
    server: str = "//en.wikipedia.org"
    article_path: str = "/wiki/$1"
    capitalize_first_letter: bool = True
    extra_signature_namespaces: frozenset[int] = field(default_factory=frozenset[int])

    @property
    def redirect(self) -> str:
        return self.magic_word("redirect")

    @property
    def img_thumbnail(self) -> str:
        return self.magic_word("img_thumbnail")

    def magic_word(self, name: str) -> str:
        aliases = self.magic_words.get(name) or MAGIC_WORDS[name]
        return aliases[0]

    @classmethod
    def from_siteinfo(cls, query: Mapping[str, Any]) -> ToolbarSite:
        """From a siteinfo query (general, namespaces, namespacealiases, magicwords, protocols)."""
        general = query.get("general", {})
        namespaces = query.get("namespaces", {})
        words = {w["name"]: tuple(w.get("aliases", [])) for w in query.get("magicwords", [])}

        def ns(n: int, default: str) -> str:
            return str(namespaces.get(str(n), {}).get("name") or default)

        file_ns = namespaces.get("6", {})
        file_names = [file_ns.get("name"), file_ns.get("canonical")]
        file_names += [
            a.get("alias") for a in query.get("namespacealiases", []) if a.get("id") == 6
        ]
        protocols = tuple(str(p) for p in query.get("protocols", [])) or URL_PROTOCOLS
        return cls(
            content_language=str(general.get("lang", "en")),
            sitename=str(general.get("sitename", "")),
            file_namespace=ns(6, "File"),
            user_namespace=ns(2, "User"),
            user_talk_namespace=ns(3, "User talk"),
            file_namespace_names=tuple(dict.fromkeys(str(n) for n in file_names if n)),
            magic_words={k: words.get(k) or v for k, v in MAGIC_WORDS.items()},
            url_protocols=protocols,
            server=str(general.get("server", "")),
            article_path=str(general.get("articlepath", "/wiki/$1")),
            capitalize_first_letter=general.get("case", "first-letter") == "first-letter",
        )

    def wants_signature(self, namespace: int) -> bool:
        """mw.Title.wantSignaturesNamespace: talk namespaces and $wgExtraSignatureNamespaces."""
        return (
            namespace > 0 and namespace % 2 == 1
        ) or namespace in self.extra_signature_namespaces


def _encapsulate(
    pre: str = "",
    peri: str = "",
    post: str = "",
    *,
    ownline: bool = False,
    splitlines: bool = False,
    rx: RegexReplace | None = None,
) -> TextAction:
    return TextAction(
        "encapsulate",
        EncapsulateOptions(pre=pre, peri=peri, post=post, ownline=ownline, splitlines=splitlines),
        rx,
    )


# /^(\s*)(={1,6})(.*?)\2(\s*)$/ and '$1==$3==$4' etc.
_HEADING_RX = r"^(\s*)(={1,6})(.*?)\2(\s*)\Z"
# /^([*#:;]*)\s*(.*)$/gm
_LIST_RX = r"(?m)^([*#:;]*)\s*(.*)$"


@cache
def _special_characters() -> dict[str, list[Any]]:
    return json.loads((_DATA / "specialcharacters.json").read_text(encoding="utf-8"))


def _text_action(spec: Mapping[str, Any]) -> TextAction:
    """An action as written in the JSON data: {type, options: {pre, peri, post, selectPeri...}}."""
    o = spec.get("options", {})
    return TextAction(
        str(spec["type"]),
        EncapsulateOptions(
            pre=o.get("pre", ""),
            peri=o.get("peri", ""),
            post=o.get("post", ""),
            ownline=bool(o.get("ownline", False)),
            select_peri=bool(o.get("selectPeri", True)),
            splitlines=bool(o.get("splitlines", False)),
        ),
    )


def character(spec: Any, msg: Messages | None = None) -> Character | None:
    """toolbar.js buildCharacter: a string, a [label, insert] pair or {label, action, titleMsg}."""
    if isinstance(spec, str):
        return Character(
            spec,
            TextAction("replace", EncapsulateOptions(peri=spec, select_peri=False)),
            config=spec,
        )
    if isinstance(spec, list) and len(spec) >= 2:
        label, insert = str(spec[0]), str(spec[1])
        action = TextAction("replace", EncapsulateOptions(peri=insert, select_peri=False))
        return Character(label, action, config=spec)
    if isinstance(spec, dict) and "action" in spec and "label" in spec:
        title = spec.get("title")
        if "titleMsg" in spec and msg is not None:
            title = msg.text(spec["titleMsg"])
        return Character(str(spec["label"]), _text_action(spec["action"]), title, config=spec)
    return None


# WikiEditor's character pages, in order: (id, language, direction)
CHARACTER_PAGES: tuple[tuple[str, str | None, str], ...] = (
    ("latin", None, "ltr"),
    ("latinextended", None, "ltr"),
    ("ipa", None, "ltr"),
    ("symbols", None, "ltr"),
    ("greek", "el", "ltr"),
    ("greekextended", None, "ltr"),
    ("cyrillic", None, "ltr"),
    # The core 28-letter alphabet, special letters for the Arabic language, vowels, punctuation,
    # digits.
    ("arabic", "ar", "rtl"),
    # Characters for languages other than Arabic.
    ("arabicextended", "ar", "rtl"),
    ("hebrew", None, "rtl"),
    ("bangla", "bn", "ltr"),
    ("tamil", "ta", "ltr"),
    ("telugu", "te", "ltr"),
    ("sinhala", "si", "ltr"),
    ("devanagari", None, "ltr"),
    ("gujarati", "gu", "ltr"),
    ("thai", "th", "ltr"),
    ("lao", "lo", "ltr"),
    ("khmer", "km", "ltr"),
    ("canadianaboriginal", "cr", "ltr"),
    ("runes", None, "ltr"),
)

RECENT_MAX = 32


def character_pages(msg: Messages, recent: Sequence[Any] = ()) -> tuple[CharacterPage, ...]:
    data = _special_characters()
    recent_chars = tuple(c for c in (character(x, msg) for x in recent) if c is not None)
    pages = [CharacterPage("recent", msg.text("special-characters-recently-used"), recent_chars)]
    for page_id, language, direction in CHARACTER_PAGES:
        chars = tuple(
            c for c in (character(x, msg) for x in data.get(page_id, [])) if c is not None
        )
        label = msg.text(f"special-characters-group-{page_id}")
        pages.append(CharacterPage(page_id, label, chars, language, direction))
    return tuple(pages)


def remember_character(recent: Sequence[Any], char: Character) -> list[Any]:
    """toolbar.js updateRecentAction: move the character to the front, keep RECENT_MAX."""
    store = char.config if char.config is not None else char.label
    key = json.dumps(store, ensure_ascii=False, sort_keys=True)
    rest = [x for x in recent if json.dumps(x, ensure_ascii=False, sort_keys=True) != key]
    return [store, *rest][:RECENT_MAX]


# --- help pages -------------------------------------------------------------------------------

_INLINE = regex.compile(
    r"<nowiki>(?P<nowiki>.*?)</nowiki>"
    r"|\[\[(?P<target>[^\[\]|]*)(?:\|(?P<label>[^\[\]]*))?\]\]"
    r"|\[(?P<url>(?:https?:)?//[^\s\[\]]+)(?:\s+(?P<text>(?:[^\[\]]|\[[^\[\]]*\])*))?\]"
    r"|(?P<bare>https?://[^\s\[\]<>]+)",
    regex.S,
)


def wikitext_inline_html(text: str) -> str:
    """Just enough of the parser for WikiEditor's help examples: links, external links, nowiki.

    Links point nowhere, as WikiEditor's delink() makes them; line breaks are kept (pre-wrap).
    """
    out: list[str] = []
    pos = 0
    numbered = 0
    for m in _INLINE.finditer(text):
        out.append(html.escape(text[pos : m.start()]))
        pos = m.end()
        if m.group("nowiki") is not None:
            out.append(html.escape(m.group("nowiki")))
        elif m.group("target") is not None:
            label = m.group("label") if m.group("label") is not None else m.group("target")
            out.append(f'<a href="#">{html.escape(label)}</a>')
        elif m.group("url") is not None:
            label = m.group("text")
            if not label:
                numbered += 1
                label = f"[{numbered}]"
            # link text is not parsed for links again, only for nowiki
            label = regex.sub(r"<nowiki>(.*?)</nowiki>", r"\1", label, flags=regex.S)
            out.append(f'<a href="#">{html.escape(label)}</a>')
        else:
            out.append(f'<a href="#">{html.escape(m.group("bare"))}</a>')
    out.append(html.escape(text[pos:]))
    return "".join(out).replace("\n", "<br>")


def help_pages(
    msg: Messages, site: ToolbarSite, username: str | None = None
) -> tuple[HelpPage, ...]:
    def parse(key: str, *params: str) -> str:
        return wikitext_inline_html(msg.text(key, *params))

    def escaped(key: str, *params: str) -> str:
        return html.escape(msg.text(key, *params))

    headings = (
        msg.text("wikieditor-toolbar-help-heading-description"),
        msg.text("wikieditor-toolbar-help-heading-syntax"),
        msg.text("wikieditor-toolbar-help-heading-result"),
    )
    p = "wikieditor-toolbar-help-content-"

    def page(page_id: str, rows: list[HelpRow]) -> HelpPage:
        return HelpPage(
            page_id, msg.text(f"wikieditor-toolbar-help-page-{page_id}"), headings, tuple(rows)
        )

    url = msg.text(p + "xlink-example-url")
    url_label = msg.text(p + "xlink-example-label")
    user = username or msg.text(p + "signature-username")
    sig_params = (site.user_namespace, site.user_talk_namespace, user)

    return (
        page(
            "format",
            [
                HelpRow(
                    parse(p + "italic-description"),
                    "''" + escaped(p + "italic-example") + "''",
                    "<em>" + parse(p + "italic-example") + "</em>",
                ),
                HelpRow(
                    parse(p + "bold-description"),
                    "'''" + escaped(p + "bold-example") + "'''",
                    "<strong>" + parse(p + "bold-example") + "</strong>",
                ),
                HelpRow(
                    parse(p + "bolditalic-description"),
                    "'''''" + escaped(p + "bolditalic-example") + "'''''",
                    "<strong><em>" + parse(p + "bolditalic-example") + "</em></strong>",
                ),
            ],
        ),
        page(
            "link",
            [
                HelpRow(
                    parse(p + "ilink-description"),
                    escaped(p + "ilink-example").replace("\n", "<br>"),
                    parse(p + "ilink-example"),
                ),
                HelpRow(
                    parse(p + "xlink-description"),
                    escaped(p + "xlink-example1", url, url_label).replace("\n", "<br>"),
                    parse(p + "xlink-example2", url, url_label, "1"),
                ),
            ],
        ),
        page(
            "heading",
            [
                HelpRow(
                    parse(p + f"heading{n}-description"),
                    f"{'=' * n} " + escaped(p + f"heading{n}-example") + f" {'=' * n}",
                    f"<h{n}>" + parse(p + f"heading{n}-example") + f"</h{n}>",
                )
                for n in (2, 3, 4, 5)
            ],
        ),
        page(
            "list",
            [
                HelpRow(
                    parse(p + f"{kind}list-description"),
                    f"{mark} " + escaped(p + f"{kind}list-example") + "<br>"
                    f"{mark} " + escaped(p + f"{kind}list-example"),
                    f"<{kind}l><li>"
                    + parse(p + f"{kind}list-example")
                    + "</li><li>"
                    + parse(p + f"{kind}list-example")
                    + f"</li></{kind}l>",
                )
                for kind, mark in (("u", "*"), ("o", "#"))
            ],
        ),
        page(
            "file",
            [
                HelpRow(
                    parse(p + "file-description"),
                    escaped(
                        p + "file-syntax",
                        site.file_namespace,
                        site.img_thumbnail,
                        msg.text(p + "file-caption"),
                    ),
                    # WikiEditor shows example-image.png here; a framed caption is enough
                    '<table border="1" cellpadding="4"><tr><td>'
                    + escaped(p + "file-caption")
                    + "</td></tr></table>",
                ),
            ],
        ),
        page(
            "discussion",
            [
                HelpRow(
                    parse(p + "signaturetimestamp-description"),
                    escaped(p + "signaturetimestamp-syntax"),
                    parse(p + "signaturetimestamp-example", *sig_params),
                ),
                HelpRow(
                    parse(p + "signature-description"),
                    escaped(p + "signature-syntax"),
                    parse(p + "signature-example", *sig_params),
                ),
                HelpRow(
                    parse(p + "indent-description"),
                    escaped(p + "indent1")
                    + "<br>:"
                    + escaped(p + "indent2")
                    + "<br>::"
                    + escaped(p + "indent3"),
                    parse(p + "indent1")
                    + "<dl><dd>"
                    + parse(p + "indent2")
                    + "<dl><dd>"
                    + parse(p + "indent3")
                    + "</dd></dl></dd></dl>",
                ),
            ],
        ),
    )


# --- the toolbar ------------------------------------------------------------------------------


def build_toolbar(
    msg: Messages,
    site: ToolbarSite | None = None,
    content_msg: Messages | None = None,
    recent_characters: Sequence[Any] = (),
    username: str | None = None,
) -> Toolbar:
    """The toolbar of jquery.wikiEditor.toolbar.config.js plus the dialogs' tools.

    msg is the interface language; content_msg the wiki's content language (for the signature),
    msg when not given.
    """
    site = site or ToolbarSite()
    content_msg = content_msg or msg
    t: Callable[..., str] = msg.text

    def heading(level: int) -> SelectOption:
        marks = "=" * level
        return SelectOption(
            f"heading-{level}",
            t(f"wikieditor-toolbar-tool-heading-{level}"),
            _encapsulate(
                marks + " ",
                t("wikieditor-toolbar-tool-heading-example"),
                " " + marks,
                ownline=True,
                rx=RegexReplace(_HEADING_RX, rf"\g<1>{marks}\g<3>{marks}\g<4>"),
            ),
        )

    def tag(name: str, example: str) -> TextAction:
        return _encapsulate(f"<{name}>", t(example), f"</{name}>")

    main = ToolbarSection(
        "main",
        (
            Group(
                "format",
                (
                    Tool(
                        "bold",
                        t("wikieditor-toolbar-tool-bold"),
                        "button",
                        "bold",
                        _encapsulate("'''", t("wikieditor-toolbar-tool-bold-example"), "'''"),
                        "b",
                    ),
                    Tool(
                        "italic",
                        t("wikieditor-toolbar-tool-italic"),
                        "button",
                        "italic",
                        _encapsulate("''", t("wikieditor-toolbar-tool-italic-example"), "''"),
                        "i",
                    ),
                ),
            ),
            Group(
                "insert",
                (
                    Tool(
                        "signature",
                        t("wikieditor-toolbar-tool-signature"),
                        "button",
                        "signature",
                        _encapsulate(content_msg.text("sig-text", "~~~~")),
                    ),
                    # added after the signature by jquery.wikiEditor.dialogs.config.js
                    Tool(
                        "link",
                        t("wikieditor-toolbar-tool-link"),
                        "button",
                        "link",
                        DialogAction("insert-link"),
                        "k",
                    ),
                    Tool(
                        "file",
                        t("wikieditor-toolbar-tool-file"),
                        "button",
                        "image",
                        DialogAction("insert-file"),
                    ),
                ),
            ),
        ),
    )

    # Secondary section of the top toolbar (at right side when LTR).
    secondary = ToolbarSection(
        "secondary",
        (
            Group(
                "default",
                (
                    Tool(
                        "replace",
                        t("wikieditor-toolbar-tool-replace"),
                        "button",
                        "articleSearch",
                        DialogAction("search-and-replace"),
                    ),
                ),
            ),
        ),
    )

    def list_tool(tool_id: str, icon: str, mark: str) -> Tool:
        return Tool(
            tool_id,
            t(f"wikieditor-toolbar-tool-{tool_id}"),
            "button",
            icon,
            _encapsulate(
                mark + " ",
                t(f"wikieditor-toolbar-tool-{tool_id}-example"),
                "",
                ownline=True,
                splitlines=True,
                rx=RegexReplace(_LIST_RX, rf"\g<1>{mark} \g<2>", count=0),
            ),
        )

    advanced = ToolbarSection(
        "advanced",
        (
            Group(
                "heading",
                (
                    Tool(
                        "heading",
                        t("wikieditor-toolbar-tool-heading"),
                        "select",
                        options=tuple(heading(n) for n in (2, 3, 4, 5)),
                    ),
                ),
            ),
            Group(
                "format",
                (
                    list_tool("ulist", "listBullet", "*"),
                    list_tool("olist", "listNumbered", "#"),
                    Tool(
                        "code",
                        t("wikieditor-toolbar-tool-code"),
                        "button",
                        "code",
                        tag("code", "wikieditor-toolbar-tool-code-example"),
                    ),
                    Tool(
                        "nowiki",
                        t("wikieditor-toolbar-tool-nowiki"),
                        "button",
                        "noWikitext",
                        tag("nowiki", "wikieditor-toolbar-tool-nowiki-example"),
                        "\\",
                    ),
                    Tool(
                        "newline",
                        t("wikieditor-toolbar-tool-newline"),
                        "button",
                        "newline",
                        _encapsulate("<br>\n"),
                    ),
                ),
                t("wikieditor-toolbar-group-format"),
            ),
            Group(
                "size",
                (
                    Tool(
                        "big",
                        t("wikieditor-toolbar-tool-big"),
                        "button",
                        "bigger",
                        tag("big", "wikieditor-toolbar-tool-big-example"),
                    ),
                    Tool(
                        "small",
                        t("wikieditor-toolbar-tool-small"),
                        "button",
                        "smaller",
                        tag("small", "wikieditor-toolbar-tool-small-example"),
                    ),
                    Tool(
                        "superscript",
                        t("wikieditor-toolbar-tool-superscript"),
                        "button",
                        "superscript",
                        tag("sup", "wikieditor-toolbar-tool-superscript-example"),
                        ".",
                    ),
                    Tool(
                        "subscript",
                        t("wikieditor-toolbar-tool-subscript"),
                        "button",
                        "subscript",
                        tag("sub", "wikieditor-toolbar-tool-subscript-example"),
                        ",",
                    ),
                ),
            ),
            Group(
                "insert",
                (
                    Tool(
                        "gallery",
                        t("wikieditor-toolbar-tool-gallery"),
                        "button",
                        "imageGallery",
                        _encapsulate(
                            "<gallery>\n",
                            t("wikieditor-toolbar-tool-gallery-example", site.file_namespace),
                            "\n</gallery>",
                            ownline=True,
                        ),
                    ),
                    Tool(
                        "redirect",
                        t("wikieditor-toolbar-tool-redirect"),
                        "button",
                        "articleRedirect",
                        _encapsulate(
                            site.redirect + " [[",
                            t("wikieditor-toolbar-tool-redirect-example"),
                            "]]",
                            ownline=True,
                        ),
                    ),
                    # from jquery.wikiEditor.dialogs.config.js
                    Tool(
                        "table",
                        t("wikieditor-toolbar-tool-table"),
                        "button",
                        "table",
                        DialogAction("insert-table"),
                    ),
                ),
                t("wikieditor-toolbar-group-insert"),
            ),
        ),
        t("wikieditor-toolbar-section-advanced"),
    )

    characters = BookletSection(
        "characters",
        t("wikieditor-toolbar-section-characters"),
        character_pages(msg, recent_characters),
    )
    help_ = BookletSection(
        "help", t("wikieditor-toolbar-section-help"), help_pages(msg, site, username)
    )
    return Toolbar(main, secondary, advanced, characters, help_)


def shortcut_label(msg: Messages, label: str, key: str | None, mac: bool = False) -> str:
    """toolbar.js buildShortcutLabel: 'Bold [ctrl+b]' (the tooltip)."""
    if key is None:
        return label
    sep = msg.text("word-separator")
    modifier = "⌘" if mac else "ctrl+"
    return label + sep + msg.text("brackets", modifier + key)
