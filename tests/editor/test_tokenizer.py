"""The wikitext tokenizer on real wiki configurations and scripts beyond the upstream tests."""

import json
from pathlib import Path

from pyawb.editor import tokenizer as tk
from pyawb.editor.mwconfig import from_siteinfo

DATA = Path(__file__).parent / "data"
ML = from_siteinfo(json.loads((DATA / "mlwiki_siteinfo.json").read_text(encoding="utf-8"))["query"])
ML_MW = tk.MediaWiki(ML)


def tokens(text: str, mw: tk.MediaWiki = ML_MW) -> list[list[tuple[str, str]]]:
    lines = text.split("\n")
    return [
        [(line[a:b], style) for a, b, style in toks]
        for line, toks in zip(lines, tk.tokenize_text(mw.mediawiki(), text), strict=True)
    ]


def classes(text: str, piece: str, mw: tk.MediaWiki = ML_MW) -> str:
    """The classes of the first token whose text is piece."""
    for line in tokens(text, mw):
        for t, style in line:
            if t == piece:
                return style
    raise AssertionError(f"no token {piece!r} in {tokens(text, mw)}")


def test_config_from_malayalam_siteinfo() -> None:
    assert "ref" in ML.tags and "references" in ML.tags
    assert ML.function_synonyms[0]["എങ്കിൽ"] == "if"
    assert ML.function_synonyms[0]["#എങ്കിൽ"] == "if"
    assert ML.function_synonyms[1]["ഈവർഷം"] == "currentyear"
    assert ML.function_synonyms[0]["ബദൽ"] == "subst"
    assert "__ഉള്ളടക്കംവേണ്ട__" in ML.double_underscore[0]
    assert ML.nsid["ചിത്രം"] == 6 and ML.nsid["file"] == 6 and ML.nsid["image"] == 6
    assert ML.image_keywords["ലഘു"] == "thumbnail" and ML.image_keywords["$1ബിന്ദു"] == "width"
    assert "#തിരിച്ചുവിടുക" in ML.redirection
    assert r"https://" in ML.url_protocols


def test_malayalam_magic_words() -> None:
    text = "{{#എങ്കിൽ:{{{1|}}}|ഉണ്ട്|ഇല്ല}} __ഉള്ളടക്കംവേണ്ട__ {{ഈവർഷം}}"
    assert classes(text, "#എങ്കിൽ") == "mw-ext-ground mw-parserfunction-name"
    assert classes(text, "ഉണ്ട്") == "mw-ext-ground mw-parserfunction"
    # whole word, vowel signs included (upstream's [\p{L}\p{N}] would split it)
    assert classes(text, "__ഉള്ളടക്കംവേണ്ട__") == "mw-double-underscore"
    assert classes(text, "ഈവർഷം") == "mw-ext-ground mw-parserfunction-name"


def test_malayalam_redirect_file_and_subst() -> None:
    assert classes("#തിരിച്ചുവിടുക [[കേരളം]]", "#തിരിച്ചുവിടുക ") == "mw-redirect"
    text = "[[ചിത്രം:Kerala.jpg|ലഘു|200ബിന്ദു|കേരളം]] {{ബദൽ:ഫലകം}}"
    assert classes(text, "ലഘു") == "mw-link-ground mw-image-parameter"
    assert classes(text, "200ബിന്ദു") == "mw-link-ground mw-image-parameter"
    assert classes(text, "കേരളം") == "mw-link-ground mw-file-text"
    assert classes(text, "ബദൽ") == "mw-template-ground mw-parserfunction-name"
    assert classes(text, "ഫലകം") == "mw-template-ground mw-template-name mw-pagename"


def test_bold_italic_across_scripts() -> None:
    line = tokens("'''ബോൾഡ്''' ''مائل'' '''''粗斜'''''")[0]
    styles = dict(line)
    assert styles["ബോൾഡ്"] == "mw-strong"
    assert styles["مائل"] == "mw-em"
    assert styles["粗斜"] == "mw-strong mw-em"


def test_arabic_link_and_template() -> None:
    text = "[[مصر|نص الرابط]] {{قالب|اسم=قيمة}}"
    assert classes(text, "مصر") == "mw-link-ground mw-link-pagename mw-pagename"
    assert classes(text, "نص الرابط") == "mw-link-ground mw-link-text"
    assert classes(text, "اسم=") == "mw-template-ground mw-template-argument-name"
    assert classes(text, "قيمة") == "mw-template-ground mw-template"


def test_astral_characters_are_one_position() -> None:
    # 𠀋 (CJK Ext-B) is one str index; the Qt layer converts to UTF-16 offsets
    line = tokens("[[𠀋|𠀋]] http://example.org/𠀋")[0]
    assert ("𠀋", "mw-link-ground mw-link-pagename mw-pagename") in line
    assert ("example.org/𠀋", "mw-free-extlink") in line


def test_state_carries_across_lines() -> None:
    lines = tokens("{{infobox\n| name = കേരളം\n}}")
    assert (" name =", "mw-template-ground mw-template-argument-name") in lines[1]
    assert ("}}", "mw-template-ground mw-template-bracket") in lines[2]


def test_entities_checked_outside_tests() -> None:
    assert classes("a &amp; b", "&amp;") == "mw-entity"
    assert classes("a &notanentity; b", "&notanentity;") == " "
