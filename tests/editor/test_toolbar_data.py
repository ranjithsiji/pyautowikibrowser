"""Toolbar data: messages and fallbacks, Codex icon variants, special characters, help pages."""

from __future__ import annotations

from pyawb import icons
from pyawb.editor.messages import Messages, language_chain
from pyawb.editor.toolbar import (
    RECENT_MAX,
    CharacterPage,
    HelpPage,
    ToolbarSite,
    build_toolbar,
    character,
    remember_character,
    wikitext_inline_html,
)


def test_messages_in_language_with_fallback_to_english() -> None:
    assert Messages("ml").text("wikieditor-toolbar-tool-bold") == "കടുപ്പിക്കുക"
    assert Messages("ar").text("wikieditor-toolbar-tool-bold") == "غليظ"
    assert Messages("xx-unknown").text("wikieditor-toolbar-tool-bold") == "Bold"
    assert Messages("en").text("no-such-message") == "⧼no-such-message⧽"


def test_language_chain_uses_mediawiki_fallbacks() -> None:
    assert language_chain("be-tarask") == ["be-tarask", "be", "en"]
    assert language_chain("de-AT")[:2] == ["de-at", "de"]
    assert language_chain("en") == ["en"]


def test_plural_sitename_and_parameters() -> None:
    m = Messages("en", sitename="Wikipedia")
    assert m.text("wikieditor-toolbar-tool-replace-success", "1") == "1 replacement made."
    assert m.text("wikieditor-toolbar-tool-replace-success", "3") == "3 replacements made."
    assert m.text("wikieditor-toolbar-tool-link-int-target-status-exists").endswith("Wikipedia")
    assert m.text("word-separator") == " "


def test_icons_follow_language_and_direction() -> None:
    assert "bold" in icons.names() and len(icons.names()) > 200
    bold_en, _ = icons.resolve("bold", "en") or ("", False)
    bold_de, _ = icons.resolve("bold", "de") or ("", False)
    bold_de_at, _ = icons.resolve("bold", "de-at") or ("", False)
    assert bold_en != bold_de and bold_de == bold_de_at
    # separate rtl drawing
    assert icons.resolve("imageAdd", rtl=True) != icons.resolve("imageAdd", rtl=False)
    # mirrored for rtl, except where the language says not to
    assert icons.resolve("help", "ar", rtl=True) == (icons.resolve("help")[0], True)  # type: ignore[index]
    assert icons.resolve("help", "he", rtl=True) == (icons.resolve("help")[0], False)  # type: ignore[index]
    svg = icons.icon_svg("listBullet", rtl=True, color="#ffffff") or b""
    assert b'fill="#ffffff"' in svg and b"scale(-1,1)" in svg
    assert icons.resolve("no-such-icon") is None


def test_every_toolbar_icon_exists() -> None:
    toolbar = build_toolbar(Messages("en"))
    for tool in toolbar.tools():
        if tool.icon:
            assert icons.resolve(tool.icon) is not None, tool.icon


def test_toolbar_layout_matches_wikieditor() -> None:
    tb = build_toolbar(Messages("en"))
    assert [t.id for g in tb.main.groups for t in g.tools] == [
        "bold",
        "italic",
        "signature",
        "link",
        "file",
    ]
    assert [g.id for g in tb.advanced.groups] == ["heading", "format", "size", "insert"]
    assert [t.label for t in tb.tabs] == ["Advanced", "Special characters", "Help"]
    pages = tb.characters.pages
    assert pages[0].id == "recent" and len(pages) == 22
    arabic = next(p for p in pages if p.id == "arabic")
    assert isinstance(arabic, CharacterPage) and arabic.direction == "rtl"


def test_toolbar_uses_the_wikis_names() -> None:
    query = {
        "general": {"lang": "ml", "sitename": "വിക്കിപീഡിയ"},
        "namespaces": {
            "2": {"name": "ഉപയോക്താവ്"},
            "3": {"name": "ഉപയോക്താവിന്റെ സംവാദം"},
            "6": {"name": "പ്രമാണം"},
        },
        "magicwords": [{"name": "redirect", "aliases": ["#തിരിച്ചുവിടുക", "#REDIRECT"]}],
    }
    site = ToolbarSite.from_siteinfo(query)
    tb = build_toolbar(Messages("ml"), site)
    redirect = next(t for t in tb.tools() if t.id == "redirect")
    assert redirect.action.options.pre == "#തിരിച്ചുവിടുക [["  # type: ignore[union-attr]
    file_help = next(p for p in tb.help.pages if isinstance(p, HelpPage) and p.id == "file")
    assert "[[പ്രമാണം:Example.png|" in file_help.rows[0].syntax
    assert site.wants_signature(1) and site.wants_signature(3) and not site.wants_signature(0)


def test_character_specs_and_recent_list() -> None:
    plain = character("é")
    pair = character(["◌ְ", "ְ"])
    quotes = character(
        {"label": "„”", "action": {"type": "encapsulate", "options": {"pre": "„", "post": "”"}}}
    )
    assert plain and plain.action.options.peri == "é" and not plain.action.options.select_peri
    assert pair and pair.label == "◌ְ" and pair.action.options.peri == "ְ"
    assert quotes and quotes.action.type == "encapsulate" and quotes.action.options.pre == "„"
    recent = remember_character(["a", "é"], plain)
    assert recent == ["é", "a"]
    many = [str(i) for i in range(40)]
    assert len(remember_character(many, plain)) == RECENT_MAX


def test_help_examples_render_links() -> None:
    html = wikitext_inline_html(
        "[[Page title|Link label]] [https://x.org [1]] <nowiki>[[x]]</nowiki>"
    )
    assert html == '<a href="#">Link label</a> <a href="#">[1]</a> [[x]]'
    tb = build_toolbar(Messages("en"))
    assert len(tb.help.pages) == 6
