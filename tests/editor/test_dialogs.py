"""WikiEditor's dialogs without Qt (pyawb.editor.dialogs)."""

from __future__ import annotations

import pytest

from pyawb.editor import dialogs as dl
from pyawb.editor.messages import Messages
from pyawb.editor.textselection import TextAction, do_action
from pyawb.editor.toolbar import ToolbarSite

SITE = ToolbarSite()
ML = ToolbarSite(
    file_namespace="പ്രമാണം",
    file_namespace_names=("പ്രമാണം", "File", "ചിത്രം", "Image"),
    magic_words={**ToolbarSite().magic_words, "img_thumbnail": ("ലഘുചിത്രം", "thumb")},
    server="//ml.wikipedia.org",
)


def run(action: TextAction, text: str = "", start: int = 0, end: int | None = None) -> str:
    end = start if end is None else end
    return do_action(text, start, end, action).apply(text)


def pre(result: TextAction | dl.LooksInternal) -> str:
    assert isinstance(result, TextAction)
    return result.options.pre


# --- link -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("selection", "target", "text", "external", "ws"),
    [
        ("", "", "", None, ("", "")),
        (" [[Foo|bar]] ", "Foo", "bar", False, (" ", " ")),
        ("[[Foo]]", "Foo", "Foo", False, ("", "")),
        ("[https://x.org label]", "https://x.org", "label", True, ("", "")),
        ("[https://x.org]", "https://x.org", "", True, ("", "")),
        ("  plain text ", "plain text", "plain text", None, ("  ", " ")),
    ],
)
def test_link_fields_from_selection(
    selection: str, target: str, text: str, external: bool | None, ws: tuple[str, str]
) -> None:
    f = dl.link_fields_from_selection(selection)
    assert (f.target, f.text, f.is_external, f.whitespace) == (target, text, external, ws)


def test_internal_links() -> None:
    assert pre(dl.insert_link("Foo", "Foo", True, SITE)) == "[[Foo]]"
    assert pre(dl.insert_link("Foo", "", True, SITE)) == "[[Foo]]"
    assert pre(dl.insert_link("Foo", " ", True, SITE)) == "[[Foo]]"
    assert pre(dl.insert_link("Foo", "a]]b", True, SITE)) == "[[Foo|a<nowiki>]]</nowiki>b]]"
    assert pre(dl.insert_link("Foo", "x", True, SITE, (" ", "\n"))) == " [[Foo|x]]\n"


def test_external_links() -> None:
    assert pre(dl.insert_link("example.org", "", False, SITE)) == "[http://example.org]"
    assert pre(dl.insert_link("https://x.org/a b", "x]", False, SITE)) == (
        "[https://x.org/a%20b x<nowiki>]</nowiki>]"
    )
    assert pre(dl.insert_link("https://x.org", "https://x.org", False, SITE)) == "https://x.org"
    assert pre(dl.insert_link("//x.org", "//x.org", False, SITE)) == "[//x.org //x.org]"


def test_external_link_to_this_wiki_looks_internal() -> None:
    url = "https://ml.wikipedia.org/wiki/%E0%B4%AE%E0%B4%B2%E0%B4%AF%E0%B4%BE%E0%B4%B3%E0%B4%82"
    assert dl.insert_link(url, "", False, ML) == dl.LooksInternal("മലയാളം")
    assert pre(dl.insert_link(url, "", False, ML, ignore_looks_internal=True)) == f"[{url}]"


def test_replacing_a_selected_link() -> None:
    text = "see [[Old]] now"
    action = dl.insert_link("New", "", True, SITE)
    assert isinstance(action, TextAction)
    assert run(action, text, 4, 11) == "see [[New]] now"


def test_titles_and_urls() -> None:
    assert dl.is_valid_title("Foo bar") and dl.is_valid_title("Foo#Section")
    assert dl.is_valid_title("മലയാളം") and dl.is_valid_title("𠀀")
    for bad in ("", "#Section", "a[b", "a|b", "a{b", "%41", "./x", "a/../b", "~~~"):
        assert not dl.is_valid_title(bad), bad
    assert dl.looks_like_external_link("www.x.org", SITE)
    assert dl.looks_like_external_link("HTTPS://x.org", SITE)
    assert not dl.looks_like_external_link("Wikipedia:About", SITE)
    assert dl.decode_uri("a%20b%2Fc%E0%B4%AE") == "a b%2Fcമ"
    assert dl.decode_uri("%E0%B4") == "%E0%B4"


def test_suggestions_follow_title_widget_order() -> None:
    result = {
        "redirects": [{"index": 2, "from": "Hg", "to": "Mercury (element)"}],
        "pages": [
            {"title": "Mercury", "index": 1, "pageprops": {"disambiguation": ""}},
            {"title": "Mercury (element)", "description": "Element 80"},
            {"title": "Mercury (planet)", "index": 3},
            {"title": "Mercury Records", "index": 4, "missing": True},
        ],
    }
    options = dl.title_options(result, "mercury", SITE, "redirect to $1")
    assert [o.title for o in options] == [
        "Mercury (element)",
        "Hg",
        "Mercury (planet)",
        "Mercury Records",
        "mercury",  # the typed text, as Mercury exists; a disambiguation page, so last
        "Mercury",
    ]
    hg = options[1]
    assert hg.redirect and hg.description == "redirect to Mercury (element)"
    assert options[3].missing
    match = dl.first_match(options, "mercury")
    assert match is not None and match.title == "mercury"
    assert dl.link_status(match, False, False) == (
        "articleDisambiguation",
        "wikieditor-toolbar-tool-link-int-target-status-disambig",
    )
    assert dl.link_status(options[3], False, False)[1].endswith("notexists")  # type: ignore[index]
    assert dl.link_status(options[3], True, True)[1].endswith("external")  # type: ignore[index]


# --- file -------------------------------------------------------------------------------------


def test_parse_file_syntax() -> None:
    f = dl.parse_file_syntax(
        " [[Image:foo_bar.jpg|thumb|left|200px|alt=Alt|A [[link|x]] caption]]\n", SITE
    )
    assert f == dl.FileFields(
        "Foo bar.jpg", "A [[link|x]] caption", "Alt", "200", "left", "thumb", (" ", "\n")
    )
    assert dl.parse_file_syntax("[[Foo]]", SITE) is None
    assert dl.parse_file_syntax("[[File:A.png|unknown|caption]]", SITE) is None
    assert dl.parse_file_syntax("[[File:A.png]]", SITE) == dl.FileFields("A.png", format="default")


def test_parse_file_syntax_in_the_wikis_language() -> None:
    f = dl.parse_file_syntax("[[ചിത്രം:ആന.jpg|ലഘുചിത്രം|അടിക്കുറിപ്പ്]]", ML)
    assert f is not None
    assert (f.file_name, f.format, f.caption) == ("ആന.jpg", "ലഘുചിത്രം", "അടിക്കുറിപ്പ്")


def test_insert_file() -> None:
    fields = dl.FileFields("foo.jpg", "Cap", "Alt", "120", "right", "thumb")
    assert run(dl.insert_file(fields, SITE), "a", 1) == (
        "a\n[[File:Foo.jpg|120px|thumb|right|alt=Alt|Cap]]\n"
    )
    plain = dl.FileFields("File:x.png", format="default")
    assert run(dl.insert_file(plain, SITE)) == "[[File:X.png]]\n"
    assert run(dl.insert_file(dl.FileFields("ആന.jpg", format="ലഘുചിത്രം"), ML)) == (
        "[[പ്രമാണം:ആന.jpg|ലഘുചിത്രം]]\n"
    )


def test_file_fields_default_to_thumbnail() -> None:
    assert dl.file_fields_from_selection("", ML).format == "ലഘുചിത്രം"
    assert dl.file_fields_from_selection("not a file", SITE) == dl.default_file_fields(SITE)


# --- table ------------------------------------------------------------------------------------


def test_insert_table() -> None:
    action = dl.insert_table("2", "2", True, True, True, Messages("en"))
    assert isinstance(action, TextAction)
    assert run(action) == (
        '{| class="wikitable sortable"\n'
        "|+ Caption text\n"
        "|-\n! Header text !! Header text\n"
        "|-\n| Example || Example\n"
        "|-\n| Example || Example\n"
        "|}\n"
    )
    plain = dl.insert_table("1", "1", False, False, False, Messages("en"))
    assert isinstance(plain, TextAction)
    assert run(plain) == "{|\n|+ Caption text\n|-\n| Example\n|}\n"


@pytest.mark.parametrize(
    ("rows", "cols", "header", "error"),
    [
        ("x", "3", True, "wikieditor-toolbar-tool-table-invalidnumber"),
        ("03", "3", True, "wikieditor-toolbar-tool-table-invalidnumber"),
        ("-1", "3", True, "wikieditor-toolbar-tool-table-invalidnumber"),
        ("0", "3", False, "wikieditor-toolbar-tool-table-zero"),
        ("3", "0", True, "wikieditor-toolbar-tool-table-zero"),
        ("100", "11", True, "wikieditor-toolbar-tool-table-toomany"),
    ],
)
def test_table_errors(rows: str, cols: str, header: bool, error: str) -> None:
    result = dl.insert_table(rows, cols, header, True, False, Messages("en"))
    assert isinstance(result, dl.TableError) and result.message == error


# --- search and replace -----------------------------------------------------------------------


def test_find_next_wraps_around() -> None:
    sr = dl.SearchReplace()
    text = "foo Foo foo"
    assert sr.run("find", text, "foo", "").selection == (0, 3)
    assert sr.run("find", text, "foo", "").selection == (4, 7)  # case-insensitive by default
    assert sr.run("find", text, "foo", "", match_case=True).selection == (8, 11)
    assert sr.run("find", text, "foo", "", match_case=True).selection == (0, 3)


def test_replace_then_select_next() -> None:
    sr = dl.SearchReplace()
    text = "a cat, a cat"
    r = sr.run("replace", text, "cat", "dog")
    assert r.edit is not None
    text = r.edit.apply(text)
    assert text == "a dog, a cat" and r.selection == (9, 12)
    r = sr.run("replace", text, "cat", "dog")
    assert r.edit is not None and r.edit.apply(text) == "a dog, a dog"


def test_replace_all_counts_and_uses_dotnet_replacements() -> None:
    sr = dl.SearchReplace()
    r = sr.run("replaceAll", "2020-01 2021-02", r"(\d{4})-(\d\d)", "$2/$1", is_regex=True)
    assert r.edit is not None and r.edit.apply("2020-01 2021-02") == "01/2020 02/2021"
    assert (r.message, r.params) == ("wikieditor-toolbar-tool-replace-success", ("2",))
    # without "regular expression", search and replacement are literal
    r = sr.run("replaceAll", "a.b a.b", "a.b", "$1", is_regex=False)
    assert r.edit is not None and r.edit.apply("a.b a.b") == "$1 $1"


def test_whole_words_and_multilingual_text() -> None:
    sr = dl.SearchReplace()
    text = "മലയാളം മലയാളത്തിൽ"
    r = sr.run("replaceAll", text, "മലയാളം", "X", match_word=True)
    assert r.edit is not None and r.edit.apply(text) == "X മലയാളത്തിൽ"


def test_search_messages() -> None:
    sr = dl.SearchReplace()
    assert sr.run("find", "x", "", "").message == "wikieditor-toolbar-tool-replace-emptysearch"
    assert sr.run("find", "x", "y", "").message == "wikieditor-toolbar-tool-replace-nomatch"
    bad = sr.run("find", "x", "(", "", is_regex=True)
    assert bad.message == "wikieditor-toolbar-tool-replace-invalidregex" and bad.params
