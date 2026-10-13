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
# Port of src/token.ts and src/data.ts of @bhsd/codemirror-mediawiki 4.7.1
# (GPL-2.0-or-later; authors pastakhov, MusikAnimal, Bhsd and others;
# https://gerrit.wikimedia.org/g/mediawiki/extensions/CodeMirror).
"""The wikitext stream tokenizer of CodeMirror's MediaWiki mode, ported line for line.

MediaWiki.mediawiki() gives a StreamParser: start_state(), copy_state(), token(stream, state).
token() returns a space-separated list of class names ("mw-template-ground mw-template-name
mw-pagename") for the text from stream.start to stream.pos. tokenize_text() runs it over a
document the way CodeMirror's StreamLanguage does.

A tokenizer is a Tok: a callable with the name and arguments of the method that made it, because
the original compares tokenizer names (getEqual, pipeTokenizers) and identities (checkpoints).
A style is a str ("local": used as is) or a one-element list (bold/italic are added when the
line is replayed). JavaScript identifiers are kept in Tok names and token keys so both can be
read side by side.

Not ported: the LilyPond mode for <score>; its content is styled as plain extension-tag text
("mw-exttag"). TeX and JSON content use pyawb.editor.submodes.
"""

from __future__ import annotations

import html
import math
from collections.abc import Callable, Iterator, Mapping, Sequence
from functools import lru_cache
from typing import Any, Protocol

import regex

from pyawb.editor.mwconfig import HTML_TAGS, SELF_CLOSING_TAGS, TOKENS, VOID_HTML_TAGS, MwConfig
from pyawb.editor.stream import StringStream, js_regex
from pyawb.editor.submodes import JsonParser, MathParser

T = TOKENS
INF = math.inf

type Style = str | list[str]


def _r(source: str, i: bool = False) -> regex.Pattern[str]:
    return js_regex(source, i)


# -- tokenizers and state --------------------------------------------------------------------------


class Tok:
    """A tokenizer: fn(stream, state) -> Style, named after the method that made it."""

    __slots__ = ("args", "fn", "name")

    def __init__(self, name: str, args: tuple[Any, ...], fn: Callable[[StringStream, State], Any]):
        self.name = name
        self.args = args
        self.fn = fn

    def __call__(self, stream: StringStream, state: State) -> Any:
        return self.fn(stream, state)

    def __repr__(self) -> str:
        return f"Tok({self.name}{self.args})"


def tokenizer(name: str) -> Callable[[Callable[..., Any]], Callable[..., Tok]]:
    """getTokenizer: the method's result (a closure, or another method's Tok) gets this name and
    the call's arguments."""

    def decorate(method: Callable[..., Any]) -> Callable[..., Tok]:
        def wrapper(self: MediaWiki, *args: Any) -> Tok:
            fn = method(self, *args)
            if isinstance(fn, Tok):
                fn.name, fn.args = name, args
                return fn
            return Tok(name, args, fn)

        wrapper.__name__ = method.__name__
        wrapper.__doc__ = method.__doc__
        return wrapper

    return decorate


NEST_KEYS = ("n_template", "n_ext", "n_var", "n_link", "n_ext_link")


class Dt:
    """state.dt: definition-list (;) tracking. Nesting fields are copied in by copy_nesting."""

    __slots__ = ("ext_name", "html", "n", "n_ext", "n_ext_link", "n_link", "n_template", "n_var")

    def __init__(self) -> None:
        self.n = 0
        self.html = 0
        self.n_template: int | None = None
        self.n_ext: int | None = None
        self.n_var: int | None = None
        self.n_link: int | None = None
        self.n_ext_link: int | None = None
        self.ext_name: str | bool | None = None

    def copy(self) -> Dt:
        d = Dt()
        for k in Dt.__slots__:
            setattr(d, k, getattr(self, k))
        return d


class ReadyToken:
    __slots__ = ("char", "pos", "state", "string", "style")

    def __init__(self, pos: int, char: str | None, string: str, state: State, style: Style) -> None:
        self.pos = pos
        self.char = char
        self.string = string
        self.state = state
        self.style = style


class MediaWikiData:
    """data.ts: per-parser scratch data shared (not copied) between states."""

    def __init__(self, tags: Sequence[str], url_protocols: str) -> None:
        self.tags: list[str] = (
            [t for t in tags if t != "tvar"] if "translate" in tags else list(tags)
        )
        self.url_protocols = _r(
            "^(" + ("<tvar name=[^>]+>" if "tvar" in self.tags else "") + ")?" + url_protocols,
            True,
        )
        self.ready_tokens: list[ReadyToken] = []
        self.old_token: ReadyToken | None = None
        self.mark: int | None = None
        self.first_single_letter_word: int | None = None
        self.first_multi_letter_word: int | None = None
        self.first_space: int | None = None


class State:
    __slots__ = (
        "bold",
        "data",
        "dt",
        "ext_mode",
        "ext_name",
        "ext_state",
        "img_link",
        "in_html_tag",
        "italic",
        "lbrack",
        "n_ext",
        "n_ext_link",
        "n_link",
        "n_template",
        "n_var",
        "redirect",
        "section",
        "sof",
        "stack",
        "tokenize",
    )

    def __init__(self, tokenize: Tok, data: MediaWikiData, sof: bool = False) -> None:
        self.tokenize = tokenize
        self.stack: list[Tok] = []
        self.in_html_tag: list[str] = []
        self.ext_name: str | bool = False
        self.ext_mode: StreamParser | bool = False
        self.ext_state: Any = False
        self.n_template = 0
        self.n_ext = 0
        self.n_var = 0
        self.n_link = 0
        self.n_ext_link = 0
        self.lbrack: bool | None = False
        self.bold = False
        self.italic = False
        self.dt = Dt()
        self.sof = sof
        self.redirect: dict[str, bool] | bool = False
        self.img_link = False
        self.section = 0
        self.data = data


class StreamParser(Protocol):
    def start_state(self) -> Any: ...

    def token(self, stream: StringStream, state: Any) -> str: ...


def copy_state(state: Any) -> Any:
    """copyState: lists, dt and redirect are copied; the extension state with its mode's own
    copy_state; data and the extension mode are shared."""
    if isinstance(state, dict):
        return dict(state)  # pyright: ignore[reportUnknownArgumentType]
    if not isinstance(state, State):
        return state
    result = State.__new__(State)
    for key in State.__slots__:
        setattr(result, key, getattr(state, key))
    result.stack = list(state.stack)
    result.in_html_tag = list(state.in_html_tag)
    result.dt = state.dt.copy()
    if isinstance(state.redirect, dict):
        result.redirect = dict(state.redirect)
    mode = state.ext_mode
    f = getattr(mode, "copy_state", None) if state.ext_name and not isinstance(mode, bool) else None
    result.ext_state = (f or copy_state)(state.ext_state)
    return result


def cmp_nesting(a: Dt | State, b: State, shallow: bool = False) -> bool:
    """cmpNesting: same template/extension/link nesting (and nested wikitext state)."""
    if any(getattr(a, k) != getattr(b, k) for k in NEST_KEYS) or a.ext_name != b.ext_name:
        return False
    if shallow or a.ext_name != "mediawiki":
        return True
    return cmp_nesting(a.ext_state, b.ext_state)  # type: ignore[union-attr]


def copy_nesting(a: Dt, b: State) -> None:
    for k in NEST_KEYS:
        setattr(a, k, getattr(b, k))
    a.ext_name = b.ext_name


def simple_token(stream: StringStream, state: State) -> str:
    style = state.tokenize(stream, state)
    return style[0] if isinstance(style, list) else style


def chain(state: State, *tokenizers: Tok) -> None:
    state.stack[0:0] = [*tokenizers[1:], state.tokenize]
    state.tokenize = tokenizers[0]


def pop(state: State) -> None:
    state.tokenize = state.stack.pop(0)


def is_sol_syntax(stream: StringStream, table: bool = False, file: bool = False) -> bool:
    """isSolSyntax: block syntax at the start of the line."""
    return stream.sol() and bool(
        (table and stream.match(_r(r"^\s*(?::+\s*)?\{\|"), False))
        or stream.match(_r(r"^(?:-{4}|=)"), False)
        or (not file and (stream.peek() or "") != "" and (stream.peek() or "") in "*#;:")
    )


def lookahead(chars: str, comment: bool | State = False) -> str:
    """Negative-lookahead alternatives for characters that start syntax when doubled."""
    table = {
        "'": "'(?!')",
        "{": r"\{(?!\{)",
        "}": r"\}(?!\})",
        "<": "<(?!!--)" if comment else "<(?!!--|/?[a-z])",
        "~": "~~?(?!~)",
        "_": "_(?!_)",
        "＿": "＿(?!＿)",
        "[": r"\[(?!\[)",
        "]": r"\](?!\])",
        "/": "/(?!>)",
        "-": r"-(?!\{(?!\{))",
    }
    if isinstance(comment, State):
        tags = comment.data.tags
        table["<"] = (
            "<(?!!--"
            + ("|onlyinclude>" if "onlyinclude" in tags else "")
            + "|(?:"
            + "|".join(t for t in tags if t != "onlyinclude")
            + r")(?:[\s/>]|$))"
        )
    return "|".join(table.get(ch, "undefined") for ch in chars)


def need_colon(state: State) -> bool:
    dt = state.dt
    return (
        bool(dt.n)
        and dt.html == 0
        and not state.bold
        and not state.italic
        and cmp_nesting(dt, state, True)
    )


def get_url_regex(punctuations: str = "") -> str:
    chars = "~{'"
    return "[^&" + chars + r'\p{Zs}[\]<>"' + punctuations + "]|&(?![lg]t;)|" + lookahead(chars)


def get_punctuations(lpar: bool = False) -> str:
    return ".,;:!?\\\\" + ("" if lpar else ")")


_WS = regex.compile(r"\s{2,}")


def make_full_style(style: Style, state: State) -> str:
    if isinstance(style, str):
        s = style
    else:
        strong = T["strong"] if state.bold or (state.dt.n if state.dt else 0) else ""
        s = f"{style[0]} {strong} {T['em'] if state.italic else ''}"
    return _WS.sub(" ", s.strip()) or " "


def make_local_style(style: str, state: State, end_ground: str | None = None) -> str:
    ground = ""
    nt = state.n_template
    if nt == 1:
        ground += "-template"
    elif nt == 2:
        ground += "-template2"
    elif nt != 0:
        ground += "-template3"
    ne = state.n_ext
    if ne == 1:
        ground += "-ext"
    elif ne == 2:
        ground += "-ext2"
    elif ne != 0:
        ground += "-ext3"
    if state.n_link or state.n_ext_link:
        ground += "-link"
    if end_ground:
        setattr(state, end_ground, getattr(state, end_ground) - 1)
        dt = state.dt
        limit = getattr(dt, end_ground) if dt else None
        if dt and dt.n and limit is not None and getattr(state, end_ground) < limit:
            dt.n = 0
    return (
        (f"mw{ground}-ground " if ground else "")
        + style
        + (f" mw-section--{state.section}" if state.section else "")
    )


def make_local_tag_style(tag: str, state: State, end_ground: str | None = None) -> str:
    return make_local_style(T[tag], state, end_ground)


def make_style(style: str, state: State, end_ground: str | None = None) -> list[str]:
    return [make_local_style(style, state, end_ground)]


def make_tag_style(tag: str, state: State, end_ground: str | None = None) -> list[str]:
    return make_style(T[tag], state, end_ground)


def get_tag_style(tag: str) -> str:
    return T.get(tag, tag)


def prepare_italic_for_correction(stream: StringStream, state: State) -> None:
    """Remember a ''' that may have to become ' + '' (MediaWiki's Parser::doQuotes)."""
    end = stream.pos
    s = stream.string[: max(end - 3, 0)]
    x1 = s[-1:]
    x2 = s[-2:-1]
    data = state.data
    if x1 == " ":
        if data.first_multi_letter_word or data.first_space:
            return
        data.first_space = end
    elif x2 == " ":
        data.first_single_letter_word = end
    elif data.first_multi_letter_word:
        return
    else:
        data.first_multi_letter_word = end
    data.mark = end


def get_pipe(is_template: bool) -> str:
    return "(?:" + ("" if is_template else r"\||") + r"\{(?:\{\s*|\s*\()!\s*\}\})"


def get_quote(stream: StringStream) -> str:
    peek = stream.peek()
    return peek * 2 if peek in ("'", '"') else ""


def get_equal(t: Tok) -> str:
    return "=" if t.name == "inTemplateArgument" and t.args and t.args[0] else ""


def escape_char_class(chars: str) -> str:
    return chars.replace("]", r"\]").replace("-", r"\-")


def peek_space(stream: StringStream, sol: bool = False) -> bool:
    if sol and stream.sol():
        return True
    peek = stream.peek()
    return bool(peek and not peek.strip())


SYNTAX_HIGHLIGHT = {"syntaxhighlight", "source", "pre", "score"}
PAGE_FUNCTIONS = {
    "raw",
    "msg",
    "filepath",
    "localurl",
    "localurle",
    "fullurl",
    "fullurle",
    "canonicalurl",
    "canonicalurle",
    "int",
    "msgnw",
}
SUBSTS = {"subst", "safesubst"}
OTHER_PARSER_FUNCTIONS = {"msg", "raw", "subst", "safesubst"}
EXT_LINK_CHARS = "[{'<-"
TABLE_DEFINITION_CHARS = "{<"
TABLE_CELL_CHARS = "'<~_＿{-"
HTML_ATTR_CHARS = "{/"
TABLE_DEFINITION_LOOKAHEAD = lookahead(TABLE_DEFINITION_CHARS)
HTML_ATTR_LOOKAHEAD = lookahead(HTML_ATTR_CHARS)
TABLE_CELL_LOOKAHEAD = lookahead(TABLE_CELL_CHARS)
ARGUMENT_LOOKAHEAD = lookahead("}{<~'_＿-")
HEADER_REGEX = _r(r"^(?:[^&[<{~'\-]|" + lookahead("<{~'-") + ")+", True)
TEMPLATE_REGEX = _r("^(?:[^|{}<]|" + lookahead("{}<", True) + ")+")
ARGUMENT_REGEX = _r(r"^(?:[^|[&:}{<~'_＿\-]|" + ARGUMENT_LOOKAHEAD + ")+", True)
STYLE_REGEX = _r(r"^(?:[^|[&}{<~'_＿\-]|" + ARGUMENT_LOOKAHEAD + ")+", True)
WIKI_REGEX = _r(r"^(?:[^&:'{[<~_＿\-]|" + lookahead("'{[<~_＿-") + ")+", True)
TABLE_DEFINITION_REGEX = _r("^(?:[^&={<]|" + TABLE_DEFINITION_LOOKAHEAD + ")+", True)
TABLE_CELL_REGEX = _r(r"^\s*(?:[|!]|\{\{\s*![!)\-+]?\s*\}\})")


def _free_regex(lpar: bool) -> regex.Pattern[str]:
    punctuations = get_punctuations(lpar)
    source = get_url_regex(punctuations)
    return _r("^(?:" + source + "|[" + punctuations + "]+(?=" + source + "))*")


FREE_REGEX = (_free_regex(False), _free_regex(True))
INDENTED_TABLE_REGEX = tuple(_r(r"^:*\s*(?=\{" + get_pipe(t) + ")") for t in (False, True))
TABLE_REGEX = tuple(_r("^" + get_pipe(t) + r"\s*") for t in (False, True))
SPACED_TABLE_REGEX = tuple(_r(r"^\s*(:+\s*)?(?=\{" + get_pipe(t) + ")") for t in (False, True))


def _link_text_regex(file: bool) -> regex.Pattern[str]:
    chars = "]'{<" + ("~" if file else "[") + "-"
    return _r(
        "^(?:[^&"
        + ("[|" if file else "")
        + escape_char_class(chars)
        + "]|"
        + lookahead(chars)
        + ")+",
        True,
    )


LINK_TEXT_REGEX = (_link_text_regex(False), _link_text_regex(True))
LINK_ERROR_REGEX = (
    _r("^(?:[<>{}]|%(?:3[ce]|[57][bd])|" + lookahead("[]") + ")+", True),
    _r(r"^(?:\}|" + lookahead("[]{") + ")+"),
    _r("^(?:[>}]|%(?:3[ce]|[57][bd])|" + lookahead("[]{<") + ")+", True),
)
TABLE_DEFINITION_VALUE_REGEX = tuple(
    _r(
        r"^(?:[^\s&" + TABLE_DEFINITION_CHARS + equal + "]|" + TABLE_DEFINITION_LOOKAHEAD + ")+",
        True,
    )
    for equal in ("", "=")
)
VARIABLE_REGEX = tuple(
    _r(
        "^(?:[^|{}<"
        + (r"[&~'_＿:\-" if is_default else "")
        + r"]|\}(?!\}\})|"
        + (TABLE_CELL_LOOKAHEAD if is_default else lookahead(TABLE_DEFINITION_CHARS, True))
        + ")+",
        True,
    )
    for is_default in (False, True)
)


def _parser_function_regex(prefix: str) -> Callable[[str], regex.Pattern[str]]:
    @lru_cache(maxsize=64)
    def build(chars: str) -> regex.Pattern[str]:
        return _r(
            "^(?:[^|" + prefix + escape_char_class(chars) + "]|" + lookahead(chars) + ")+", True
        )

    return build


PARSER_FUNCTION_REGEX = tuple(_parser_function_regex(s) for s in ("", "[&", "[&:"))
# Upstream uses [\p{L}\p{N}]: combining marks (Malayalam and Hindi vowel signs, virama) are
# added so localised words such as __ഉള്ളടക്കംവേണ്ട__ (Malayalam __NOTOC__) stay whole.
DOUBLE_UNDERSCORE_REGEX = {
    "_": _r(r"^[\p{L}\p{M}\p{N}_]+?__"),
    "＿": _r(r"^[\p{L}\p{M}\p{N}_＿]+?＿{2}"),
}
PIPE_TOKENIZERS = {"inTemplateArgument", "inParserFunctionArgument", "inVariable"}


@lru_cache(maxsize=64)
def get_ext_link_text_regex(pipe: str) -> regex.Pattern[str]:
    return _r(
        r"^(?:[^\]&"
        + pipe
        + escape_char_class(EXT_LINK_CHARS)
        + "]|"
        + lookahead(EXT_LINK_CHARS)
        + ")+",
        True,
    )


@lru_cache(maxsize=64)
def get_ext_link_regex(pipe: str) -> regex.Pattern[str]:
    return _r("^(?:" + get_url_regex(pipe) + ")+")


@lru_cache(maxsize=64)
def get_table_definition_regex(s: str) -> regex.Pattern[str]:
    return _r(
        "^(?:[^&" + TABLE_DEFINITION_CHARS + s + "]|" + TABLE_DEFINITION_LOOKAHEAD + ")+", True
    )


@lru_cache(maxsize=64)
def get_table_cell_regex(s: str) -> regex.Pattern[str]:
    return _r(
        "^(?:[^[&" + s + escape_char_class(TABLE_CELL_CHARS) + "]|" + TABLE_CELL_LOOKAHEAD + ")+",
        True,
    )


@lru_cache(maxsize=64)
def get_html_attr_regex(s: str) -> regex.Pattern[str]:
    return _r("^(?:[^<>&" + HTML_ATTR_CHARS + s + "]|" + HTML_ATTR_LOOKAHEAD + ")+")


@lru_cache(maxsize=64)
def get_html_attr_key_regex(pipe: str) -> regex.Pattern[str]:
    return _r("^(?:[^<>&={/" + pipe + "]|" + HTML_ATTR_LOOKAHEAD + ")+")


@lru_cache(maxsize=64)
def get_ext_attr_regex(s: str) -> regex.Pattern[str]:
    return _r("^(?:[^>/" + s + "]|" + lookahead("/") + ")+")


@lru_cache(maxsize=256)
def get_ext_tag_close_regex(name: str) -> regex.Pattern[str]:
    if name == "onlyinclude":
        return _r("</onlyinclude(?:>|$)")
    return _r("</" + regex.escape(name) + r"\s*(?:>|$)", True)


@lru_cache(maxsize=64)
def get_nested_regex(tag: str) -> regex.Pattern[str]:
    return _r("^(?:[^<]|<(?!" + tag + r"(?:[\s/>]|$)))+", True)


CHECK_ENTITIES = True
"""Whether "&name;" must be a real HTML entity. codemirror-mediawiki's own tests run without a
browser, where every well-formed reference counts; the parity tests switch this off."""


def is_html_entity(s: str) -> bool:
    if not CHECK_ENTITIES or s.startswith("#"):
        return True
    return len(html.unescape("&" + s)) == 1


# -- the tokenizer ---------------------------------------------------------------------------------

_MAGIC_LINK = _r(
    r"^(?:(?:RFC|PMID)[\p{Zs}\t]+\d+|ISBN[\p{Zs}\t]+(?:97[89][\p{Zs}\t-]?)?(?:\d[\p{Zs}\t-]?){9}"
    r"[\dxX])\b"
)
# with \p{M} for whole Indic words (see DOUBLE_UNDERSCORE_REGEX)
_LETTER_OR_DIGIT = _r(r"[\p{L}\p{M}\p{N}]")
_NOT_FREE_LINK_START = _r(r"[^\p{L}\p{M}\p{N}_＿&'{[<\-~:]")
_SKIP_FORMATTING_EXEMPT = _r(r"^ \s*(?=<!--)(?:\s|<!--(?:(?!-->).)*-->)+$")


class MediaWiki:
    """Adapted from the original CodeMirror 5 stream parser by Pavel Astakhov."""

    def __init__(self, config: MwConfig) -> None:
        self.config = config
        url_protocols = config.url_protocols
        self.permitted_html_tags = {*HTML_TAGS, *config.permitted_html_tags}
        self.void_html_tags = {*VOID_HTML_TAGS, *config.implicitly_closed_html_tags}
        self.url_protocols_source = "^(?:" + url_protocols + r')(?=[^\p{Zs}[\]<>"])'
        self.url_protocols = _r(self.url_protocols_source, True)
        self.link_regex = _r(r"^\[(?!" + url_protocols + r")\s*", True)
        self.file_regex = _r(
            "^(?:" + "|".join(ns for ns, i in config.nsid.items() if i == 6) + r")\s*:", True
        )
        self.redirect_regex = _r(
            r"^\s*(?:" + "|".join(config.redirection) + r")(\s*:)?\s*(?=\[\[|$)", True
        )
        keywords = config.image_keywords
        self.img = [w for w in keywords if not regex.search(r"\$1.", w)]
        sp_img_keys = [w for w in keywords if w.startswith("$1")]
        self.img_regex = _r(
            "^(?:"
            + "|".join(w[:-2] for w in self.img if w.endswith("$1"))
            + "|(?:"
            + "|".join(w for w in self.img if not w.endswith("$1"))
            + r"|(?:(?:\d+x?|\d*x\d+)\s*(?:px)?(?:"
            + "|".join(w[2:] for w in sp_img_keys if keywords[w] == "width")
            + r"))|\d+\s*(?:"
            + "|".join(w[2:] for w in sp_img_keys if keywords[w] != "width")
            + r"))\s*(?=\||\]\]|$))"
        )
        self.tags = [*config.tags, "includeonly", "noinclude", "onlyinclude"]
        self.convert_regex = _r(
            r"^(?:[^}|;&='{[<~_＿\-]|\}(?!-)|=(?!>)|\[(?!\[|"
            + url_protocols
            + ")|"
            + TABLE_CELL_LOOKAHEAD
            + ")+",
            True,
        )
        variants = config.variants
        self.convert_semicolon = (
            None
            if variants is None
            else _r(r"^;\s*(?=(?:[^;]*?=>\s*)?(?:" + "|".join(variants) + r")\s*:|(?:$|\}-))")
        )
        self.convert_lang = (
            None if variants is None else _r(r"^(?:=>\s*)?(?:" + "|".join(variants) + r")\s*:")
        )
        self.has_variants = bool(variants)
        self.pre_regex = tuple(
            _r(
                r"^(?:[^<&\-]|-"
                + (r"(?!\{)" if self.has_variants else "")
                + "|<(?!"
                + ("/" if begin else "")
                + "nowiki>))+",
                True,
            )
            for begin in (False, True)
        )
        insensitive = config.function_synonyms[0]
        self.subst_regex = _r(
            r"^\s*(?:("
            + "|".join(
                k + ("" if k.endswith("：") else ":") for k, v in insensitive.items() if v in SUBSTS
            )
            + r")\s*)?",
            True,
        )
        self._modes: Mapping[str, Callable[[list[str] | None], StreamParser]] = {
            "mediawiki": self.mediawiki,
            "text/mediawiki": self.mediawiki,
            "text/nowiki": lambda _tags: _NowikiParser(self),
            "text/pre": lambda _tags: _SimpleParser(self, lambda: self.in_pre(), []),
            "text/references": lambda tags: _SimpleParser(
                self, lambda: self.in_nested("ref"), tags or []
            ),
            "text/choose": lambda tags: _SimpleParser(
                self, lambda: self.in_nested("option"), tags or []
            ),
            "text/combobox": lambda tags: _SimpleParser(
                self, lambda: self.in_nested("combooption"), tags or []
            ),
            "text/inputbox": lambda _tags: _SimpleParser(self, lambda: self.in_inputbox, []),
            "text/gallery": lambda tags: _GalleryParser(self, tags or []),
            "text/math": lambda _tags: MathParser(),
            "json": lambda _tags: JsonParser(),
            "jsonc": lambda _tags: JsonParser(jsonc=True),
        }

    def has_mode(self, mode: str) -> bool:
        return mode in self._modes

    def get_mode(self, mode: str, tags: list[str] | None = None) -> StreamParser:
        return self._modes[mode](tags)

    def start_state(self, tokenize: Tok, tags: Sequence[str], sof: bool = False) -> State:
        # data.urlProtocols: `(${this.urlProtocols.source.slice(4)}`
        return State(tokenize, MediaWikiData(tags, "(" + self.url_protocols_source[4:]), sof)

    # -- small tokenizers --

    @tokenizer("inChars")
    def in_chars(self, chars: str, tag: str) -> Callable[[StringStream, State], str]:
        length = len(chars)

        def tok(stream: StringStream, state: State) -> str:
            stream.pos += length
            pop(state)
            return make_local_tag_style(tag, state)

        return tok

    @tokenizer("inStr")
    def in_str(
        self, s: str, tag: str | bool, error_tag: str = "error"
    ) -> Callable[[StringStream, State], str]:
        tag = get_tag_style(tag) if isinstance(tag, str) and tag else False
        error_style = get_tag_style(error_tag)

        def tok(stream: StringStream, state: State) -> str:
            if stream.match_str(s, bool(tag)):
                pop(state)
                return make_local_style(tag, state) if isinstance(tag, str) else ""
            if not stream.skip_to(s):
                stream.skip_to_end()
            return make_local_style(error_style, state)

        return tok

    # -- wikitext --

    @tokenizer("eatWikiText")
    def eat_wiki_text(self, style: str) -> Callable[[StringStream, State], Style]:
        style = get_tag_style(style)

        def tok(stream: StringStream, state: State) -> Style:
            ch: str
            if stream.eol():
                return ""
            if stream.sol():
                sof, redirect, tokenize = state.sof, state.redirect, state.tokenize
                if sof:
                    if stream.match(_r(r"^\s+$")):
                        return ""
                    state.sof = False
                    mt = stream.match(self.redirect_regex)
                    if mt:
                        state.redirect = {"colon": not mt[1]}
                        return T["redirect"]
                elif redirect:
                    if stream.match(_r(r"^\s+(?=$|\[\[)")):
                        return ""
                    if (
                        isinstance(redirect, dict)
                        and redirect["colon"]
                        and stream.match(_r(r"^\s*:\s*(?=$|\[\[)"))
                    ):
                        redirect["colon"] = False
                        return T["redirect"]
                    state.redirect = False
                ch = stream.next() or ""
                is_template = tokenize.name in PIPE_TOKENIZERS
                if ch in ("#", ";", "*"):
                    stream.back_up(1)
                    return self.eat_list(stream, state)
                if ch == ":":
                    # Highlight indented tables :{|, bug T108454
                    if stream.match(INDENTED_TABLE_REGEX[1 if is_template else 0]):
                        chain(state, self.eat_start_table)
                        return make_local_tag_style("list", state)
                    return self.eat_list(stream, state)
                if ch == "=":
                    tmp = stream.match(_r(r"^(={0,5})(.+?(=\1\s*)(?:<!--(?!.*-->\s*\S).*)?)$"))
                    if tmp:  # title
                        stream.back_up(len(tmp[2]))
                        state.section = len(tmp[1]) + 1
                        chain(state, self.in_section_header(tmp[3]))
                        return make_local_style(T["sectionHeader"], state)
                elif ch == "{":
                    if stream.match(TABLE_REGEX[1 if is_template else 0]):
                        chain(state, self.in_table_definition())
                        return make_local_tag_style("tableBracket", state)
                elif ch == "-":
                    if stream.match(_r(r"^-{3,}")):
                        return T["hr"]
                elif not ch.strip():
                    # Leading spaces is valid syntax for tables, bug T108454
                    mt = stream.match(SPACED_TABLE_REGEX[1 if is_template else 0])
                    if mt:
                        chain(state, self.eat_start_table)
                        return make_local_style(T["list"] if mt[1] else "", state)
                    if ch == " " and not _SKIP_FORMATTING_EXEMPT.search(stream.string):
                        return T["skipFormatting"]
            else:
                ch = stream.next() or ""

            if ch == "~":
                if stream.match(_r("^~{2,4}")):
                    return T["signature"]
            elif ch == "<":
                if stream.match_str("!--"):  # comment
                    chain(state, self.in_comment)
                    return make_local_tag_style("comment", state)
                is_close_tag = bool(stream.eat("/"))
                mt = stream.match(_r(r"^([a-z][^\s/>]*)>?", True), False)
                if mt:
                    tagname = mt[1].lower()
                    if (tagname != "onlyinclude" or mt[0] == "onlyinclude>") and (
                        tagname in state.data.tags
                    ):
                        return self.eat_ext_tag(tagname, is_close_tag, state)  # extension tag
                    if tagname in self.permitted_html_tags:
                        return self.eat_html_tag(tagname, is_close_tag, state)  # html tag
            elif ch == "{":
                # Can't be a variable when it starts with more than 3 brackets (T108450) or a
                # single { followed by a template. E.g. {{{!}} starts a table (T292967).
                if stream.match(_r(r"^\{\{(?!\{|[^{}]*\}\}(?!\}))\s*")):
                    state.n_var += 1
                    chain(state, self.in_variable())
                    return make_local_tag_style("templateVariableBracket", state)
                if stream.match(_r(r"^\{(?!\{(?!\{))")):
                    result = self.eat_transclusion(stream, state)
                    return make_style(style, state) if result is None else result
            elif ch in ("_", "＿"):
                pos = stream.pos
                stream.eat_while(ch)
                eaten = stream.pos - pos
                if eaten == 1:
                    return self.eat_double_underscore(style, ch, stream, state)
                if eaten > 1:
                    if not stream.eol():
                        stream.back_up(2)
                    return make_style(style, state)
            elif ch == "[":
                # Link Example: [[ Foo | Bar ]]
                if stream.match(self.link_regex):
                    redirect = state.redirect
                    if redirect or _r(r"[^[\]|]").search(stream.peek() or ""):
                        state.n_link += 1
                        state.lbrack = None
                        chain(
                            state,
                            self.in_link(
                                not redirect and bool(stream.match(self.file_regex, False))
                            ),
                        )
                        return make_local_tag_style("linkBracket", state)
                    if stream.match_str("]]"):
                        return make_style(style, state)
                else:
                    mt = stream.match(state.data.url_protocols, False)
                    if mt:
                        state.n_ext_link += 1
                        if mt[1]:
                            chain(
                                state,
                                self.in_chars("<", "extTagBracket"),
                                self.eat_tag_name("tvar"),
                                self.in_external_link(True),
                            )
                        else:
                            chain(state, self.eat_external_link_protocol(mt[2], False))
                        return make_local_tag_style("extLinkBracket", state)
            elif ch == "'":
                result = self.eat_apostrophes(state)(stream, state)
                if result:
                    return result
            elif ch == ":":
                if need_colon(state):
                    state.dt.n -= 1
                    return make_local_tag_style("list", state)
            elif ch == "&":
                return make_style(self.eat_entity(stream, style), state)
            elif ch == "-":  # noqa: SIM102 (mirrors the original switch)
                if self.config.variants and stream.match(_r(r"^\{(?!\{)\s*")):
                    chain(state, self.in_convert(style, True))
                    return make_local_tag_style("convertBracket", state)

            if not state.stack:
                if ch not in ("_", "＿"):
                    # highlight free external links, bug T108448
                    if _LETTER_OR_DIGIT.search(ch):
                        stream.back_up(1)
                    else:
                        stream.eat_while(_NOT_FREE_LINK_START)
                    mt = stream.match(self.url_protocols, False)
                    if mt:
                        chain(state, self.eat_external_link_protocol(mt[0]))
                        return make_style(style, state)
                    mt_magic = stream.match(_MAGIC_LINK, False)
                    if mt_magic:
                        chain(state, self.in_chars(mt_magic[0], "magicLink"))
                        return make_style(style, state)
                stream.eat_while(_LETTER_OR_DIGIT)
            return make_style(style, state)

        return tok

    @tokenizer("eatApostrophes")
    def eat_apostrophes(self, obj: Any) -> Callable[[StringStream, State], str | bool]:
        """obj: the state, or a link's own {bold, italic}."""

        def toggle(key: str) -> None:
            if isinstance(obj, dict):
                obj[key] = not obj[key]
            else:
                setattr(obj, key, not getattr(obj, key))

        def tok(stream: StringStream, state: State) -> str | bool:
            # skip the irrelevant apostrophes ( >5 or =4 )
            if stream.match(_r("^'*(?='{5})")) or stream.match(_r("^'''(?!')"), False):
                return False
            if stream.match_str("''''"):  # bold italic
                toggle("bold")
                toggle("italic")
                return make_local_tag_style("apostrophes", state)
            if stream.match_str("''"):  # bold
                if obj is state and state.data.first_single_letter_word is None:
                    prepare_italic_for_correction(stream, state)
                toggle("bold")
                return make_local_tag_style("apostrophes", state)
            if stream.eat("'"):  # italic
                toggle("italic")
                return make_local_tag_style("apostrophes", state)
            return False

        return tok

    @tokenizer("eatExternalLinkProtocol")
    def eat_external_link_protocol(
        self, protocol: str, free: bool = True
    ) -> Callable[[StringStream, State], Style]:
        length = len(protocol)

        def tok(stream: StringStream, state: State) -> Style:
            stream.pos += length
            state.tokenize = self.eat_free_external_link if free else self.in_external_link()
            if free:
                return make_tag_style("freeExtLinkProtocol", state)
            return make_local_tag_style("extLinkProtocol", state)

        return tok

    @tokenizer("inExternalLink")
    def in_external_link(self, text: bool = False) -> Callable[[StringStream, State], Style]:
        def tok(stream: StringStream, state: State) -> Style:
            t = state.stack[0]
            equal = get_equal(t)
            is_nested = t.name == "inTableCell" or t.name in PIPE_TOKENIZERS
            pipe = ("|" if is_nested else "") + equal
            peek = stream.peek()
            if (
                stream.sol()
                or stream.match(_r(r"^\p{Zs}*\]"))
                or (is_nested and peek == "|")
                or (equal and peek == "=")
            ):
                pop(state)
                return make_local_tag_style("extLinkBracket", state, "n_ext_link")
            if text:
                if stream.match(get_ext_link_text_regex(pipe)):
                    return make_tag_style("extLinkText", state)
                return self.eat_wiki_text("extLinkText")(stream, state)
            if stream.match(get_ext_link_regex(pipe)):
                return make_local_tag_style("extLink", state)
            state.tokenize = self.in_external_link(True)
            return ""

        return tok

    def _eat_free_external_link(self, stream: StringStream, state: State) -> Style:
        mt = stream.match(FREE_REGEX[0])
        assert mt is not None
        if not stream.eol() and "(" in mt[0] and (stream.peek() or "") in get_punctuations():
            stream.match(FREE_REGEX[1])
        pop(state)
        return make_tag_style("freeExtLink", state)

    @property
    def eat_free_external_link(self) -> Tok:
        tok = self.__dict__.get("_free_tok")
        if tok is None:
            tok = self.__dict__["_free_tok"] = Tok(
                "eatFreeExternalLink", (), self._eat_free_external_link
            )
        return tok

    @tokenizer("inLink")
    def in_link(self, file: bool, section: bool = False) -> Callable[[StringStream, State], Style]:
        if section:
            style = T["error" if file else "linkToSection"]
            re = _r(r"^(?:[^|<[\]{}]|<(?!!--|\/?[a-z]))+", True)
        else:
            style = f"{T['linkPageName']} {T['pageName']}"
            re = _r(r"^(?:&#(?:\d+|x[a-f\d]+);|[^#|<>[\]{}%]|%(?!3[ce]|[57][bd]))+", True)
        lt: list[int | None] = [None]

        def tok(stream: StringStream, state: State) -> Style:
            if (
                stream.sol()
                or (lt[0] is not None and lt[0] and stream.pos > lt[0])
                or stream.match(_r(r"^\s*\]\]"))
                or stream.match(_r(r"^\[\["), False)
            ):
                state.redirect = False
                state.lbrack = False
                pop(state)
                return make_local_tag_style("linkBracket", state, "n_link")
            lt[0] = None
            space = stream.eat_space()
            redirect = state.redirect
            if not section and stream.match(_r(r"^#\s*")):
                state.tokenize = self.in_link(file, True)
                return make_tag_style("error" if file else "linkToSection", state)
            if stream.match(_r(r"^\|\s*")):
                state.tokenize = self.in_link_text(file)
                s = "error" if redirect else "linkDelimiter"
                if file:
                    s = "fileDelimiter"
                    self.to_eat_image_parameter(stream, state)
                return make_local_tag_style(s, state)
            if redirect:
                rgx = LINK_ERROR_REGEX[0]
            elif section:
                rgx = LINK_ERROR_REGEX[1]
            else:
                rgx = LINK_ERROR_REGEX[2]
            if stream.match(rgx):
                return make_tag_style("error", state)
            if redirect:
                stream.match(_r(r"^(?:[^|<>[\]{}%]|%(?!3[ce]|[57][bd]))+", True))
                return make_style(style, state)
            if stream.match(re) or space:
                return make_style(style, state)
            if stream.match(
                _r(r"^<(?!(?:includeonly|noinclude)(?:\/?>|\s|$)|tvar(?:\s|$))[/a-z]", True), False
            ) and not stream.match(_r("^<onlyinclude>"), False):
                lt[0] = stream.pos + 1
            return self.eat_wiki_text(style if section else "error")(stream, state)

        return tok

    @tokenizer("inLinkText")
    def in_link_text(
        self, file: bool, gallery: bool = False
    ) -> Callable[[StringStream, State], Style]:
        link_state = {"bold": False, "italic": False}
        rgx = LINK_TEXT_REGEX[1 if file else 0]

        def tok(stream: StringStream, state: State) -> Style:
            img_link, stack = state.img_link, state.stack
            tmpstyle = (
                f"{T['fileText' if file else 'linkText']} "
                f"{T['strong'] if link_state['bold'] else ''} "
                f"{T['em'] if link_state['italic'] else ''} "
                f"{T['pageName'] if file and img_link else ''}"
            )
            redirect, lbrack = state.redirect, state.lbrack
            closing = stream.match_str("]]")
            if (
                closing
                or (not file and stream.match_str("[[", False))
                or (
                    not gallery
                    and stack
                    and stack[0].name == "inTableCell"
                    and stream.sol()
                    and stream.match(TABLE_CELL_REGEX, False)
                )
            ):
                if gallery:
                    return make_style(tmpstyle, state)
                if closing and not redirect and lbrack and stream.peek() == "]":
                    stream.back_up(1)
                    state.lbrack = False
                    return make_style(tmpstyle, state)
                state.redirect = False
                state.lbrack = False
                pop(state)
                return make_local_tag_style("linkBracket", state, "n_link")
            if redirect:
                if not stream.skip_to("]]"):
                    stream.skip_to_end()
                return make_local_tag_style("error", state)
            if file and stream.match(_r(r"^\|\s*")):
                self.to_eat_image_parameter(stream, state)
                return make_local_tag_style("fileDelimiter", state)
            if stream.match(_r("^'(?=')")):
                return self.eat_apostrophes(link_state)(stream, state) or make_style(
                    tmpstyle, state
                )
            if (file and is_sol_syntax(stream, True, True)) or (
                stream.sol() and stream.match_str("{|", False)
            ):
                return self.eat_wiki_text(tmpstyle)(stream, state)
            mt = stream.match(rgx)
            if lbrack is None and mt and "[" in mt[0]:
                state.lbrack = True
            return (
                make_style(tmpstyle, state) if mt else self.eat_wiki_text(tmpstyle)(stream, state)
            )

        return tok

    def to_eat_image_parameter(self, stream: StringStream, state: State) -> None:
        state.img_link = False
        mt = stream.match(self.img_regex, False)
        if mt:
            if self.config.image_keywords.get(mt[0] + "$1") == "link":
                state.img_link = True
            chain(state, self.in_chars(mt[0], "imageParameter"))

    def eat_list(self, stream: StringStream, state: State) -> str:
        mt = stream.match(_r("^[*#;:]*"))
        assert mt is not None
        dt = state.dt
        if ";" in mt[0]:
            dt.n = mt[0].count(";")
            copy_nesting(dt, state)
        return make_local_tag_style("list", state)

    def eat_double_underscore(
        self, style: str, ch: str, stream: StringStream, state: State
    ) -> Style:
        du = self.config.double_underscore
        underscore = ch * 2
        name = stream.match(DOUBLE_UNDERSCORE_REGEX[ch])
        if name:
            if (underscore + name[0].lower()) in du[0] or (underscore + name[0]) in du[1]:
                return T["doubleUnderscore"]
            if not stream.eol():
                # Two underscore symbols at the end can be the beginning of another double
                # underscored magic word
                stream.back_up(2)
        return make_style(style, state)

    # -- tables --

    @property
    def eat_start_table(self) -> Tok:
        def tok(stream: StringStream, state: State) -> str:
            stream.match(_r(r"^(?:\{\||\{\{(?:\{\s*|\s*\()!\s*\}\})\s*"))
            state.tokenize = self.in_table_definition()
            return make_local_tag_style("tableBracket", state)

        return Tok("eatStartTable", (), tok)

    @tokenizer("inTableDefinition")
    def in_table_definition(
        self, tr: bool = False, quote: str | None = None, css: bool = False
    ) -> Callable[[StringStream, State], Style]:
        if quote is None:
            style = f"{T['tableDefinition']} mw-html-{'tr' if tr else 'table'}"
        else:
            style = T["tableDefinitionValue"] + (" mw-css" if css else "")

        def tok(stream: StringStream, state: State) -> Style:
            if stream.sol():
                state.tokenize = self.in_table
                return ""
            equal = get_equal(state.stack[0])
            if equal and stream.peek() == "=":
                pop(state)
                return ""
            if stream.match(_r(r"^(?:&|\{\{|<(?:!--|\/?[a-z]))", True), False):
                return self.eat_wiki_text(style)(stream, state)
            if quote:  # quoted attribute value
                if stream.eat(quote[0]):
                    state.tokenize = self.in_table_definition(tr, quote[1:2] or None, css)
                else:
                    stream.match(get_table_definition_regex(equal + quote[0]))
                return make_local_style(style, state)
            if quote == "":  # unquoted attribute value
                if peek_space(stream):
                    state.tokenize = self.in_table_definition(tr)
                    return ""
                stream.match(TABLE_DEFINITION_VALUE_REGEX[1 if equal else 0])
                return make_local_style(style, state)
            if stream.match(_r(r"^=\s*")):
                state.tokenize = self.in_table_definition(tr, get_quote(stream), css)
                return make_local_style(style, state)
            mt = stream.match(TABLE_DEFINITION_REGEX)
            if mt and stream.peek() == "=":
                state.tokenize = self.in_table_definition(
                    tr, None, bool(_r(r"(?:^|\s)style\s*$", True).search(mt[0]))
                )
            return make_local_style(style, state)

        return tok

    @property
    def in_table(self) -> Tok:
        def tok(stream: StringStream, state: State) -> Style:
            if stream.sol():
                stream.eat_space()
                mt = stream.match(_r(r"^(?:\||\{\{\s*!([!)\-+])?\s*\}\})"))
                if mt:
                    m1 = mt[1]
                    if m1 == "-" or (not m1 and stream.eat("-")):
                        stream.match(_r(r"^-*\s*"))
                        state.tokenize = self.in_table_definition(True)
                        return make_local_tag_style("tableDelimiter", state)
                    if m1 == "+" or (not m1 and stream.match(_r(r"^\+\s*"))):
                        state.tokenize = self.in_table_cell(T["tableCaption"])
                        return make_local_tag_style("tableDelimiter", state)
                    if m1 == ")" or (not m1 and stream.eat("}")):
                        pop(state)
                        return make_local_tag_style("tableBracket", state)
                    stream.eat_space()
                    state.tokenize = self.in_table_cell(T["tableTd"], m1 != "!")
                    return make_local_tag_style("tableDelimiter", state)
                if stream.match(_r(r"^!\s*")):
                    state.tokenize = self.in_table_cell(T["tableTh"])
                    return make_local_tag_style("tableDelimiter", state)
                if is_sol_syntax(stream, True):
                    return self.eat_wiki_text("error")(stream, state)
            if stream.match(WIKI_REGEX):
                return make_tag_style("error", state)
            return self.eat_wiki_text("error")(stream, state)

        return Tok("inTable", (), tok)

    @tokenizer("inTableCell")
    def in_table_cell(
        self, style: str, need_attr: bool = True, first_line: bool = True
    ) -> Callable[[StringStream, State], Style]:
        def tok(stream: StringStream, state: State) -> Style:
            if stream.sol():
                if stream.match(TABLE_CELL_REGEX, False):
                    state.tokenize = self.in_table
                    return ""
                if first_line:
                    state.tokenize = self.in_table_cell(style, False, False)
                    return ""
                if is_sol_syntax(stream, True):
                    return self.eat_wiki_text(style)(stream, state)
            if first_line:
                if stream.match(_r(r"^(?:(?:\||\{\{\s*!\s*\}\}){2}|\{\{\s*!!\s*\}\})\s*")) or (
                    style == T["tableTh"] and stream.match(_r(r"^!!\s*"))
                ):
                    state.bold = False
                    state.italic = False
                    if not need_attr:
                        state.tokenize = self.in_table_cell(style)
                    return make_local_tag_style("tableDelimiter", state)
                if need_attr and stream.match(_r(r"^(?:\||\{\{\s*!\s*\}\})\s*")):
                    state.bold = False
                    state.italic = False
                    state.tokenize = self.in_table_cell(style, False)
                    return make_local_tag_style("tableDelimiter2", state)
                if need_attr and stream.match_str("[[", False):
                    state.tokenize = self.in_table_cell(style, False)
            equal = get_equal(state.stack[0])
            if equal and stream.peek() == "=":
                pop(state)
                return ""
            if stream.match(get_table_cell_regex(("|!" if first_line else ":") + equal)):
                return make_style(style, state)
            return self.eat_wiki_text(style)(stream, state)

        return tok

    @tokenizer("inSectionHeader")
    def in_section_header(self, s: str) -> Callable[[StringStream, State], Style]:
        def tok(stream: StringStream, state: State) -> Style:
            if stream.sol():
                pop(state)
                return ""
            if stream.match(HEADER_REGEX):
                if stream.eol():
                    stream.back_up(len(s))
                    state.tokenize = self.in_str(s, T["sectionHeader"])
                elif stream.match(_r(r"^<!--(?!.*?-->.*?=)"), False):
                    # T171074: handle trailing comments
                    stream.back_up(len(s))
                    state.tokenize = self.in_str("<!--", False, T["sectionHeader"])
                return make_local_style(T["section"], state)
            return self.eat_wiki_text(T["section"])(stream, state)

        return tok

    @property
    def in_comment(self) -> Tok:
        tok = self.in_str("-->", "comment", "comment")
        tok.name, tok.args = "inComment", ()
        return tok

    # -- tags --

    def eat_ext_tag(self, tagname: str, is_close_tag: bool, state: State) -> str:
        if is_close_tag:
            chain(state, self.in_str(">", "error"))
            return make_local_tag_style("error", state)
        chain(state, self.eat_tag_name(tagname))
        return make_local_tag_style("extTagBracket", state)

    def eat_html_tag(self, tagname: str, is_close_tag: bool, state: State) -> str:
        if is_close_tag:
            dt, in_html_tag = state.dt, state.in_html_tag
            if dt.n and dt.html:
                dt.html -= 1
            if in_html_tag and tagname == in_html_tag[-1]:
                in_html_tag.pop()
            else:
                chain(state, self.in_str(">", "error"))
                for i in range(len(in_html_tag) - 1, -1, -1):
                    if in_html_tag[i] == tagname:
                        del in_html_tag[i]
                        break
                return make_local_tag_style("error", state)
        chain(state, self.eat_tag_name(tagname, is_close_tag, True))
        return make_local_tag_style("htmlTagBracket", state)

    @tokenizer("eatTagName")
    def eat_tag_name(
        self, name: str, is_close_tag: bool = False, is_html_tag: bool = False
    ) -> Callable[[StringStream, State], str]:
        def tok(stream: StringStream, state: State) -> str:
            stream.match_str(name, True, True)
            stream.eat_space()
            if is_html_tag:
                state.tokenize = (
                    self.in_str(">", "htmlTagBracket")
                    if is_close_tag
                    else self.in_html_tag_attribute(name)
                )
                return make_local_tag_style("htmlTagName", state)
            # it is the extension tag
            state.tokenize = (
                self.in_str(">", "extTagBracket")
                if is_close_tag
                else self.in_ext_tag_attribute(name)
            )
            return make_local_tag_style("extTagName", state)

        return tok

    @tokenizer("inHtmlTagAttribute")
    def in_html_tag_attribute(
        self, name: str, quote: str | None = None, css: bool = False
    ) -> Callable[[StringStream, State], Style]:
        if quote is None:
            style = f"{T['htmlTagAttribute']} mw-html-{name}"
        else:
            style = T["htmlTagAttributeValue"] + (" mw-css" if css else "")

        def tok(stream: StringStream, state: State) -> Style:
            if stream.match(_r("^" + lookahead("<", state), True), False):
                pop(state)
                return ""
            mt = stream.match(_r("^/?>"))
            if mt:
                if name not in self.void_html_tags and (
                    mt[0] == ">" or name not in SELF_CLOSING_TAGS
                ):
                    state.in_html_tag.append(name)
                    state.dt.html += 1
                pop(state)
                return make_local_tag_style("htmlTagBracket", state)
            t = state.stack[0]
            pipe = ("|" if t.name in PIPE_TOKENIZERS else "") + get_equal(t)
            if (stream.peek() or "") in pipe:
                pop(state)
                return ""
            if stream.match(_r(r"^(?:[&<]|\{\{)"), False):
                return self.eat_wiki_text(style)(stream, state)
            if quote:  # quoted attribute value
                if stream.eat(quote[0]):
                    state.tokenize = self.in_html_tag_attribute(name, quote[1:2] or None, css)
                else:
                    stream.match(get_html_attr_regex(pipe + quote[0]))
                return make_local_style(style, state)
            if quote == "":  # unquoted attribute value
                if peek_space(stream, True):
                    state.tokenize = self.in_html_tag_attribute(name)
                    return ""
                stream.match(get_html_attr_regex(r"\s" + pipe))
                return make_local_style(style, state)
            if stream.match(_r(r"^=\s*")):
                state.tokenize = self.in_html_tag_attribute(name, get_quote(stream), css)
                return make_local_style(style, state)
            mt = stream.match(get_html_attr_key_regex(pipe))
            if mt and stream.peek() == "=":
                state.tokenize = self.in_html_tag_attribute(
                    name, None, bool(_r(r"(?:^|\s)style\s*$", True).search(mt[0]))
                )
            return make_local_style(style, state)

        return tok

    @tokenizer("inExtTagAttribute")
    def in_ext_tag_attribute(
        self,
        name: str,
        quote: str | None = None,
        is_lang: str | bool = False,
        is_page: bool = False,
        css: bool = False,
    ) -> Callable[[StringStream, State], str]:
        style = f"{T['extTagAttribute']} mw-ext-{name}"
        css_style = " mw-css" if css else ""

        def advance(stream: StringStream, state: State, re: regex.Pattern[str]) -> str:
            mt = stream.match(re)
            value = mt[0] if mt else ""
            if is_lang:
                if name != "score":
                    lang = value.strip().lower()
                    if lang == "wikitext" or (lang == "wiki" and is_lang == "lang"):
                        lang = "mediawiki"
                    elif is_lang == "format":
                        lang = ""
                    if lang in self.config.tag_modes.values() and self.has_mode(lang):
                        state.ext_mode = self.get_mode(lang)
                elif value.strip() == "ABC":
                    state.ext_mode = True
            return make_local_style(
                T["extTagAttributeValue"] + (f" {T['pageName']}" if is_page else "") + css_style,
                state,
            )

        def tok(stream: StringStream, state: State) -> str:
            if stream.match_str("/>"):
                if name == "tvar":
                    stream.back_up(1)
                    return make_local_tag_style("error", state)
                state.ext_mode = False
                pop(state)
                return make_local_tag_style("extTagBracket", state)
            if stream.eat(">"):
                tag_modes = self.config.tag_modes
                state.ext_name = name
                if not state.ext_mode:
                    mode = tag_modes.get(name)
                    if mode is not None and self.has_mode(mode):
                        state.ext_mode = self.get_mode(
                            mode,
                            [
                                *(t for t in state.data.tags if t != name),
                                *(["tvar"] if name == "translate" else []),
                            ],
                        )
                    else:
                        state.ext_mode = False
                if not isinstance(state.ext_mode, bool):
                    state.ext_state = state.ext_mode.start_state()
                state.tokenize = self.eat_ext_tag_area(name)
                return make_local_tag_style("extTagBracket", state)
            if quote:  # quoted attribute value
                if stream.eat(quote[0]):
                    remains = quote[1:2]
                    state.tokenize = self.in_ext_tag_attribute(
                        name,
                        remains or None,
                        bool(remains) and is_lang,
                        is_page and bool(remains),
                        css,
                    )
                    return make_local_style(T["extTagAttributeValue"] + css_style, state)
                return advance(stream, state, get_ext_attr_regex(quote[0]))
            if quote == "":  # unquoted attribute value
                if peek_space(stream, True):
                    state.tokenize = self.in_ext_tag_attribute(name)
                    return ""
                return advance(stream, state, _r(r"^(?:[^>/\s]|\/(?!>))+"))
            if stream.match(_r(r"^=\s*")):
                state.tokenize = self.in_ext_tag_attribute(
                    name, get_quote(stream), is_lang, is_page, css
                )
                return make_local_style(style, state)
            mt = stream.match(_r(r"^(?:[^>/=]|\/(?!>))+"))
            if stream.peek() == "=":
                attr = mt[0] if mt else ""
                lang: str | bool = False
                if name == "pre" and _r(r"(?:^|\s)format\s*$", True).search(attr):
                    lang = "format"
                elif name in SYNTAX_HIGHLIGHT and _r(r"(?:^|\s)lang\s*$", True).search(attr):
                    lang = "lang"
                state.tokenize = self.in_ext_tag_attribute(
                    name,
                    None,
                    lang,
                    name == "templatestyles" and bool(_r(r"(?:^|\s)src\s*$", True).search(attr)),
                    bool(_r(r"(?:^|\s)style\s*$", True).search(attr)),
                )
            return make_local_style(style, state)

        return tok

    @tokenizer("eatExtTagArea")
    def eat_ext_tag_area(self, name: str) -> Callable[[StringStream, State], str]:
        def tok(stream: StringStream, state: State) -> str:
            pos = stream.pos
            m = get_ext_tag_close_regex(name).search(stream.string[pos:])
            i = m.start() if m else -1
            if i == 0:
                stream.match_str("</")
                state.tokenize = self.eat_tag_name(name, True)
                state.ext_name = False
                state.ext_mode = False
                state.ext_state = False
                return make_local_tag_style("extTagBracket", state)
            orig_string = ""
            if i != -1:
                orig_string = stream.string
                stream.string = orig_string[: pos + i]
            chain(state, self.in_ext_tokens(orig_string))
            return ""

        return tok

    @tokenizer("inExtTokens")
    def in_ext_tokens(self, orig_string: str) -> Callable[[StringStream, State], str]:
        def tok(stream: StringStream, state: State) -> str:
            ext_mode, ext_name, section = state.ext_mode, state.ext_name, state.section
            ret = f"mw-tag-{ext_name} {f'mw-section--{section}' if section else ''}"
            if isinstance(ext_mode, bool):
                ret += f" {T['extTag']}"
                stream.skip_to_end()
            else:
                ret += f" {ext_mode.token(stream, state.ext_state) or ''}"
            if stream.eol():
                if orig_string:
                    stream.string = orig_string
                pop(state)
            return ret

        return tok

    # -- templates, parser functions, variables --

    @tokenizer("inVariable")
    def in_variable(self, pos: int = 0) -> Callable[[StringStream, State], Style]:
        tag = "templateVariableName" if pos == 0 else "templateVariable" if pos == 1 else "comment"
        re = VARIABLE_REGEX[1 if pos == 1 else 0]

        def tok(stream: StringStream, state: State) -> Style:
            sol = stream.sol()
            stream.eat_space()
            if stream.eol():
                return make_local_style("", state)
            if stream.eat("|"):
                if pos < 2:
                    state.tokenize = self.in_variable(pos + 1)
                return make_local_tag_style("templateVariableDelimiter", state)
            if stream.match(_r(r"^\}{2,3}")):
                pop(state)
                return make_local_tag_style("templateVariableBracket", state, "n_var")
            if stream.match_str("<!--"):
                chain(state, self.in_comment)
                return make_local_tag_style("comment", state)
            if pos == 0 and sol:
                state.n_var -= 1
                pop(state)
                stream.pos = 0
                return ""
            if (pos == 1 and is_sol_syntax(stream)) or not stream.match(re):
                return self.eat_wiki_text(tag)(stream, state)
            return (make_tag_style if pos == 1 else make_local_tag_style)(tag, state)

        return tok

    def eat_transclusion(self, stream: StringStream, state: State) -> str | None:
        m = stream.match(self.subst_regex)
        assert m is not None
        length, subst = len(m[0]), m[1]
        tokenizers = [self.in_subst(subst)] if subst else []
        # Parser function
        if stream.peek() == "#":
            stream.back_up(length)
            state.n_ext += 1
            chain(state, *tokenizers, self.in_parser_function_name())
            return make_local_tag_style("parserFunctionBracket", state)
        # Check for parser function without '#'
        name = stream.match(_r(r"^([^}<{|:：]+)(.?)"), False)
        if name:
            f, delimiter = name[1], name[2]
            full_width = delimiter == "："
            ff = f
            if full_width:
                ff += "："
            elif delimiter != ":":
                ff = f.strip()
            ff_lower = ff.lower()
            cfg = self.config
            insensitive, sensitive = cfg.function_synonyms
            canonical = sensitive.get(ff) or insensitive.get(ff_lower)
            if (
                canonical
                and (not delimiter or full_width or delimiter in (":", "}"))
                and canonical not in SUBSTS
                and (
                    full_width
                    or delimiter == ":"
                    or cfg.variable_ids is None
                    or canonical in cfg.variable_ids
                )
                and (
                    cfg.function_hooks is None
                    or (not full_width and delimiter != ":")
                    or canonical in cfg.function_hooks
                    or canonical in OTHER_PARSER_FUNCTIONS
                )
            ):
                stream.back_up(length)
                state.n_ext += 1
                chain(state, *tokenizers, self.in_parser_function_name())
                return make_local_tag_style("parserFunctionBracket", state)
        if stream.match_str("}}"):
            return None
        # Template
        stream.back_up(length)
        state.n_template += 1
        chain(state, *tokenizers, self.in_template_page_name())
        return make_local_tag_style("templateBracket", state)

    @tokenizer("inSubst")
    def in_subst(self, subst: str | None = None) -> Callable[[StringStream, State], str]:
        def tok(stream: StringStream, state: State) -> str:
            if subst:
                stream.eat_space()
                stream.match_str(subst)
                stream.back_up(1)
                state.tokenize = self.in_subst()
                return make_local_tag_style("parserFunctionName", state)
            stream.next()
            pop(state)
            return make_local_tag_style("parserFunctionDelimiter", state)

        return tok

    @tokenizer("inParserFunctionName")
    def in_parser_function_name(
        self, invoke: float | None = None, n: float | None = None, ns: int | None = None
    ) -> Callable[[StringStream, State], str]:
        def tok(stream: StringStream, state: State) -> str:
            sol = stream.sol()
            space = stream.eat_space()
            if stream.eol():
                return make_local_style("", state)
            if stream.eat("}"):
                pop(state)
                closed = stream.eat("}")
                return make_local_tag_style(
                    "parserFunctionBracket" if closed else "error", state, "n_ext"
                )
            if stream.match_str("<!--"):
                chain(state, self.in_comment)
                return make_local_tag_style("comment", state)
            if sol:
                state.n_ext -= 1
                pop(state)
                stream.pos = 0
                return ""
            ch = stream.eat(_r("[:：|]"))
            if ch:
                state.tokenize = self.in_parser_function_argument(invoke, n, ns)
                return make_local_tag_style(
                    "error" if space or ch == "|" else "parserFunctionDelimiter", state
                )
            mt = stream.match(_r(r"^(?:[^:：}{|<>[\]\s]|\s(?![:：]))+"))
            if mt:
                name = mt[0].strip().lower() + ("：" if stream.peek() == "：" else "")
                insensitive = self.config.function_synonyms[0]
                if name.startswith("#"):
                    canonical = insensitive.get(name)
                    if canonical is None:
                        canonical = insensitive.get(name[1:])
                    if canonical == "invoke":
                        state.tokenize = self.in_parser_function_name(2)
                    elif canonical == "widget":
                        state.tokenize = self.in_parser_function_name(1)
                    elif canonical == "switch":
                        state.tokenize = self.in_parser_function_name(None, 1)
                    elif canonical == "tag":
                        state.tokenize = self.in_parser_function_name(None, 2)
                    elif canonical in ("ifexist", "lst", "lstx", "lsth"):
                        state.tokenize = self.in_parser_function_name(INF)
                else:
                    canonical = insensitive.get(name)
                    if canonical in PAGE_FUNCTIONS:
                        namespace = 0
                        if canonical == "filepath":
                            namespace = 6
                        elif canonical == "int":
                            namespace = 8
                        elif canonical in ("raw", "msg", "msgnw"):
                            namespace = 10
                        state.tokenize = self.in_parser_function_name(INF, INF, namespace)
                return make_local_tag_style("parserFunctionName", state)
            pop(state)
            return make_local_style("", state, "n_ext")

        return tok

    @tokenizer("inTemplatePageName")
    def in_template_page_name(
        self, have_eaten: bool = False, anchor: bool = False
    ) -> Callable[[StringStream, State], Style]:
        style = T["error"] if anchor else f"{T['templateName']} {T['pageName']}"
        chars = "{}<"
        re = (
            TEMPLATE_REGEX
            if anchor
            else _r(r"^(?:&#(?:\d+|x[a-f\d]+);|[^|{}<>[\]#%]|%(?![\da-f]{2}))+", True)
        )

        def tok(stream: StringStream, state: State) -> Style:
            sol = stream.sol()
            space = stream.eat_space()
            if stream.eol():
                return make_local_style("", state)
            if stream.match_str("}}"):
                pop(state)
                return make_local_tag_style("templateBracket", state, "n_template")
            if stream.match_str("<!--"):
                chain(state, self.in_comment)
                return make_local_tag_style("comment", state)
            if (
                stream.match(_r("^</?onlyinclude>"))
                or stream.match(
                    _r(
                        r"^<(?:(?:includeonly|noinclude)(?:\s[^>]*)?\/?>|\/(?:includeonly|noinclude)\s*>)",
                        True,
                    )
                )
                or (
                    "tvar" in state.data.tags
                    and stream.match(_r(r"^<(?:tvar\s[^>]*>|\/tvar\s*>)", True))
                )
            ):
                return make_local_tag_style("comment", state)
            if stream.eat("|"):
                state.tokenize = self.in_template_argument(True)
                return make_local_tag_style("templateDelimiter", state)
            if have_eaten and sol:
                state.n_template -= 1
                pop(state)
                stream.pos = 0
                return ""
            if not anchor and stream.eat("#"):
                state.tokenize = self.in_template_page_name(True, True)
                return make_local_tag_style("error", state)
            if not anchor and stream.match(
                _r(r"^(?:[>[\]]|%[\da-f]{2}|" + lookahead(chars, state) + ")+", True)
            ):
                return make_local_tag_style("error", state)
            if not anchor and stream.peek() == "<":
                pop(state)
                return make_local_style("", state, "n_template")
            if space and not have_eaten:
                return make_local_style("", state)
            if stream.match(re):
                if not have_eaten:
                    state.tokenize = self.in_template_page_name(True, anchor)
                return make_local_style(style, state)
            return (
                make_local_style(style, state)
                if space
                else self.eat_wiki_text(style)(stream, state)
            )

        return tok

    @tokenizer("inParserFunctionArgument")
    def in_parser_function_argument(
        self, module: float | None = None, n: float | None = None, ns: int | None = None
    ) -> Tok | Callable[[StringStream, State], Style]:
        if n is None:
            n = module if module is not None else INF
        if ns is None:
            ns = 0
        if n == 0:
            return self.in_template_argument(True, True)
        chars = "}{<" if n == 2 else "}{<~'_＿-"  # `#invoke`/`#tag`
        style = f"{T['parserFunction']} {T['pageName'] if module else ''}"
        if module == 1:
            style += " mw-function-274"
        elif module == 2:
            style += " mw-function-828"
        elif module == INF:
            style += f" mw-function-{ns}"
        n_ = n

        def tok(stream: StringStream, state: State) -> Style:
            if stream.eat("|"):
                if module:
                    state.tokenize = self.in_parser_function_argument(None, module - 1)
                elif n_ != INF:
                    state.tokenize = self.in_parser_function_argument(None, n_ - 1)
                return make_local_tag_style("parserFunctionDelimiter", state)
            if stream.match_str("}}"):
                pop(state)
                return make_local_tag_style("parserFunctionBracket", state, "n_ext")
            index = 0 if module else int(need_colon(state)) + 1
            if not is_sol_syntax(stream) and stream.match(PARSER_FUNCTION_REGEX[index](chars)):
                return make_local_style(style, state)
            return self.eat_wiki_text("parserFunction")(stream, state)

        return tok

    @tokenizer("inTemplateArgument")
    def in_template_argument(
        self, expect_name: bool = False, parser_function: bool = False
    ) -> Callable[[StringStream, State], Style]:
        tag = "parserFunction" if parser_function else "template"

        def tok(stream: StringStream, state: State) -> Style:
            space = stream.eat_space()
            if stream.eol():
                return make_local_tag_style(tag, state)
            if stream.eat("|"):
                if not expect_name:
                    state.tokenize = self.in_template_argument(True, parser_function)
                return make_local_tag_style(
                    "parserFunctionDelimiter" if parser_function else "templateDelimiter", state
                )
            if stream.match_str("}}", False):
                if space:
                    return make_local_tag_style(tag, state)
                stream.pos += 2
                pop(state)
                return make_local_tag_style(
                    "parserFunctionBracket" if parser_function else "templateBracket",
                    state,
                    "n_ext" if parser_function else "n_template",
                )
            if stream.sol() and stream.peek() == "=":
                style = self.eat_wiki_text(tag)(stream, state)
                if isinstance(style, str) and T["sectionHeader"] in style:
                    return style
                stream.pos = 0
            if expect_name and stream.match(
                _r("^(?:[^=|}{[<]|" + lookahead("}{[<", state) + ")*=", True)
            ):
                state.tokenize = self.in_template_argument(False, parser_function)
                return make_local_tag_style(
                    "parserFunctionArgumentName" if parser_function else "templateArgumentName",
                    state,
                )
            if is_sol_syntax(stream) and stream.peek() != "=":
                return self.eat_wiki_text(tag)(stream, state)
            if stream.match(ARGUMENT_REGEX if need_colon(state) else STYLE_REGEX) or space:
                return make_local_tag_style(tag, state)
            return self.eat_wiki_text(tag)(stream, state)

        return tok

    @tokenizer("inConvert")
    def in_convert(
        self, style: str, need_flag: bool = False, need_lang: bool = True, plain: bool = False
    ) -> Callable[[StringStream, State], Style]:
        def tok(stream: StringStream, state: State) -> Style:
            space = stream.eat_space()
            if stream.match_str("}-"):
                pop(state)
                return make_local_tag_style("convertBracket", state)
            if need_flag and stream.match(_r(r"^[;\sa-z-]*(?=\|)", True)):
                state.tokenize = self.in_convert(style, False, True, plain)
                chain(state, self.in_str("|", "convertDelimiter"))
                return make_local_tag_style("convertFlag", state)
            if self.convert_semicolon is not None and stream.match(self.convert_semicolon):
                if need_flag or not need_lang:
                    state.tokenize = self.in_convert(style, False, True, plain)
                return make_local_tag_style("convertDelimiter", state)
            if need_lang and self.convert_lang is not None and stream.match(self.convert_lang):
                state.tokenize = self.in_convert(style, False, False, plain)
                return make_local_tag_style("convertLang", state)
            if plain:
                if stream.match_str("-{", False):
                    return self.eat_wiki_text(style)(stream, state)
                stream.match(_r(r"^(?:(?:[^}\-;=]|\}(?!-)|=(?!>)|-(?!\{))+|;|=>)"))
                return make_style(style, state)
            if (not is_sol_syntax(stream, True) and stream.match(self.convert_regex)) or space:
                return make_style(style, state)
            return self.eat_wiki_text(style)(stream, state)

        return tok

    def eat_entity(self, stream: StringStream, style: str) -> str:
        entity = stream.match(_r(r"^(?:#x[a-f\d]+|#\d+|[a-z][a-z\d]*);", True))
        return T["htmlEntity"] if entity and is_html_entity(entity[0]) else style

    # -- nested modes --

    @tokenizer("inPre")
    def in_pre(self, begin: bool = False) -> Callable[[StringStream, State], str]:
        def tok(stream: StringStream, state: State) -> str:
            if stream.match(_r("^</nowiki>" if begin else "^<nowiki>", True)):
                state.tokenize = self.in_pre(not begin)
                return T["ignored"]
            if self.has_variants and stream.match_str("-{"):
                chain(state, self.in_convert("", True, True, True))
                return T["convertBracket"]
            if stream.eat("&"):
                return self.eat_entity(stream, "")
            stream.match(self.pre_regex[1 if begin else 0])
            return ""

        return tok

    @tokenizer("inNested")
    def in_nested(self, tag: str) -> Callable[[StringStream, State], Style]:
        re = (
            _r(r"^(?:\{|(?:[^<{]|\{(?!\{)|<(?!!--|ref(?:[\s/>]|$)))+)", True)
            if tag == "ref"
            else get_nested_regex(tag)
        )

        def tok(stream: StringStream, state: State) -> Style:
            if tag == "ref":
                if stream.match_str("<!--"):
                    chain(state, self.in_comment)
                    return make_local_tag_style("comment", state)
                if stream.match(_r(r"^\{{3}(?!\{|[^{}]*\}\}(?!\}))\s*")):
                    chain(state, self.in_variable())
                    return T["templateVariableBracket"]
                if stream.match(_r(r"^\{\{(?!\{(?!\{))")):
                    result = self.eat_transclusion(stream, state)
                    return T["ignored"] if result is None else result
            if stream.match(re):
                return T["ignored"]
            stream.eat("<")
            chain(state, self.eat_tag_name(tag))
            return T["extTagBracket"]

        return tok

    @property
    def in_inputbox(self) -> Tok:
        def tok(stream: StringStream, state: State) -> str:
            if stream.match_str("<!--"):
                chain(state, self.in_comment)
                return T["comment"]
            if stream.match(_r(r"^\{\{(?!\{)")):
                result = self.eat_transclusion(stream, state)
                return "" if result is None else result
            stream.match(_r(r"^(?:[^<{]|<(?!!--)|\{(?!\{(?!\{)))+"))
            return ""

        return Tok("inInputbox", (), tok)

    @tokenizer("inGallery")
    def in_gallery(self, section: bool = False) -> Callable[[StringStream, State], Style]:
        if section:
            style = T["error"]
            rgx = _r(r"^(?:[[}\]]|\{(?!\{))+")
            re = _r(r"^(?:[^|<[\]{}]|<(?!!--))+")
        else:
            style = f"{T['linkPageName']} {T['pageName']}"
            rgx = _r(r"^(?:[>[}\]]|\{(?!\{)|<(?!!--))+")
            re = _r(r"^(?:&#(?:\d+|x[a-f\d]+);|[^#|<>[\]{}])+")

        def tok(stream: StringStream, state: State) -> Style:
            space = stream.eat_space()
            if not section and stream.match(_r(r"^#\s*")):
                state.tokenize = self.in_gallery(True)
                return make_tag_style("error", state)
            if stream.match(_r(r"^\|\s*")):
                state.tokenize = self.in_link_text(True, True)
                self.to_eat_image_parameter(stream, state)
                return make_local_tag_style("fileDelimiter", state)
            if stream.match(rgx):
                return make_tag_style("error", state)
            if stream.match(re) or space:
                return make_style(style, state)
            return self.eat_wiki_text(style if section else "error")(stream, state)

        return tok

    def mediawiki(self, tags: list[str] | None = None) -> _MediaWikiParser:
        """The main entry: a StreamParser for wikitext (tags: those of the enclosing page when
        nested in an extension tag)."""
        return _MediaWikiParser(self, tags)


class _MediaWikiParser:
    def __init__(self, mw: MediaWiki, tags: list[str] | None) -> None:
        self.mw = mw
        self.tags = tags

    def start_state(self) -> State:
        mw = self.mw
        return mw.start_state(
            mw.eat_wiki_text(""), self.tags if self.tags is not None else mw.tags, self.tags is None
        )

    def copy_state(self, state: State) -> State:
        return copy_state(state)

    def token(self, stream: StringStream, state: State) -> str:
        data, tokenize = state.data, state.tokenize
        ready_tokens = data.ready_tokens
        old_token = data.old_token
        while old_token and (
            stream.pos > old_token.pos
            or (stream.pos == old_token.pos and tokenize is not old_token.state.tokenize)
        ):
            old_token = ready_tokens.pop(0) if ready_tokens else None
        if (
            old_token is not None
            and ready_tokens
            and stream.pos == old_token.pos
            and stream.string == old_token.string
            and cmp_nesting(state, old_token.state)
        ):
            first = ready_tokens[0]
            pos, string, other, style = first.pos, first.string, first.state, first.style
            for key in State.__slots__:
                if key not in ("bold", "italic"):
                    setattr(state, key, getattr(other, key))
            if (
                isinstance(style, str)
                and (not state.ext_name or isinstance(state.ext_mode, bool))
                and state.n_link == 0
                and T["apostrophes"] in style
            ):
                if data.mark == pos:
                    # rollback: add one apostrophe, next token will be italic (two apostrophes)
                    data.mark = None
                    stream.string = string[: pos - 2]
                    s = state.tokenize(stream, state)
                    stream.string = string
                    old_token.pos += 1
                    data.old_token = old_token
                    return make_full_style(s, state)
                length = pos - stream.pos
                if length != 3:
                    state.italic = not state.italic
                if length != 2:
                    state.bold = not state.bold
            elif isinstance(style, str) and T["tableDelimiter"] in style:
                state.bold = False
                state.italic = False
            # return first saved token
            data.old_token = ready_tokens.pop(0)
            stream.pos = pos
            stream.string = string
            return make_full_style(style, state)
        if stream.sol():
            # reset bold and italic status in every new line
            state.bold = False
            state.italic = False
            state.section = 0
            state.dt.n = 0
            state.dt.html = 0
            data.first_single_letter_word = None
            data.first_multi_letter_word = None
            data.first_space = None
            if state.tokenize.name == "inExtTokens":
                pop(state)  # dispose inExtTokens
                pop(state)  # dispose eatExtTagArea
                state.ext_name = False
                state.ext_mode = False
                state.ext_state = False
        ready_tokens.clear()
        data.mark = None
        data.old_token = ReadyToken(stream.pos, None, stream.string, copy_state(state), "")
        start = stream.start
        stuck = 0
        while True:
            # get token style
            stream.start = stream.pos
            char = stream.peek()
            style = state.tokenize(stream, state)
            if isinstance(style, str) and "-argument-name" in style:
                is_template = T["templateArgumentName"] in style
                argument = T["template" if is_template else "parserFunction"]
                argument_name = T[
                    "templateArgumentName" if is_template else "parserFunctionArgumentName"
                ]
                delimiter = T["templateDelimiter" if is_template else "parserFunctionDelimiter"]
                for token in reversed(ready_tokens):
                    if cmp_nesting(state, token.state, True):  # noqa: SIM102 (mirrors the original switch)
                        if isinstance(token.style, str):
                            types = token.style.split(" ")
                            if argument in types:
                                types[types.index(argument)] = argument_name
                                token.style = " ".join(types)
                            elif delimiter in types:
                                break
            elif isinstance(style, str) and T["tableDelimiter2"] in style:
                for token in reversed(ready_tokens):
                    if cmp_nesting(state, token.state, True):
                        s = token.style
                        if isinstance(s, list):
                            kind = next(
                                (t for t in s[0].split(" ") if t and not t.endswith("-ground")),
                                None,
                            )
                            if kind and kind.startswith("mw-table-"):
                                token.style = (
                                    s[0].replace("mw-table-", "mw-html-", 1)
                                    + " "
                                    + T["tableDefinition"]
                                )
                        elif T["tableDelimiter"] in s:
                            break
            elif char == "|" and isinstance(style, str) and T["convertDelimiter"] in style:
                count = 0
                for token in reversed(ready_tokens):
                    if cmp_nesting(state, token.state, True):
                        s = token.style
                        if isinstance(s, str) and T["convertBracket"] in s:
                            count += 1 if token.char == "-" else -1
                            if count == 1:
                                break
                        elif isinstance(s, list):
                            token.style = s[0] + (
                                "" if T["convertFlag"] in s[0] else f" {T['convertFlag']}"
                            )
            # save token
            ready_tokens.append(
                ReadyToken(stream.pos, char, stream.string, copy_state(state), style)
            )
            if stream.eol():
                break
            # guard against a tokenizer that never advances (the original would hang)
            stuck = stuck + 1 if stream.pos == stream.start else 0
            if stuck > 1000:
                raise RuntimeError(f"wikitext tokenizer stuck at {stream.pos}: {state.tokenize}")
        if not state.bold or not state.italic:
            data.mark = None  # no need to rollback
        stream.start = start
        old = data.old_token
        stream.pos = old.pos
        stream.string = old.string
        for key in State.__slots__:
            setattr(state, key, getattr(old.state, key))
        return ""


class _NowikiParser:
    def __init__(self, mw: MediaWiki) -> None:
        self.mw = mw

    def start_state(self) -> dict[str, Any]:
        return {}

    def token(self, stream: StringStream, state: Any) -> str:
        if stream.eat_while(_r("[^&]")):
            return ""
        stream.next()  # eat &
        return self.mw.eat_entity(stream, "")


class _SimpleParser:
    """A mode whose token is the current tokenizer's style (simpleToken)."""

    def __init__(self, mw: MediaWiki, first: Callable[[], Tok], tags: list[str]) -> None:
        self.mw = mw
        self.first = first
        self.tags = tags

    def start_state(self) -> State:
        return self.mw.start_state(self.first(), self.tags)

    def token(self, stream: StringStream, state: State) -> str:
        return simple_token(stream, state)


class _GalleryParser(_SimpleParser):
    def __init__(self, mw: MediaWiki, tags: list[str]) -> None:
        super().__init__(mw, lambda: mw.in_gallery(), tags)

    def token(self, stream: StringStream, state: State) -> str:
        if stream.sol():
            fresh = self.mw.start_state(self.mw.in_gallery(), state.data.tags)
            for key in State.__slots__:
                setattr(state, key, getattr(fresh, key))
        return simple_token(stream, state)


# -- running it over a document (CodeMirror's StreamLanguage) ------------------------------------

MAX_LINE_LENGTH = 10000
"""StreamLanguage stops tokenizing a line after this many characters."""

_LINE_BREAK = regex.compile(r"\r\n?|\n")

type Token = tuple[int, int, str]
"""(start, end, classes) within a line; positions are str indices."""


def tokenize_line(parser: Any, line: str, state: Any) -> list[Token]:
    """Tokenize one line, advancing state (StreamLanguage's per-line loop and readToken)."""
    stream = StringStream(line)
    tokens: list[Token] = []
    while not stream.eol():
        stream.start = stream.pos
        for _ in range(10):
            style = parser.token(stream, state)
            if stream.pos > stream.start:
                break
        else:
            raise RuntimeError("Stream parser failed to advance stream.")
        if style:
            tokens.append((stream.start, stream.pos, style))
        if stream.start > MAX_LINE_LENGTH:
            break
    return tokens


def tokenize_text(parser: Any, text: str, state: Any = None) -> Iterator[list[Token]]:
    """Tokens of each line of text (lines split as CodeMirror does: \\r\\n, \\r or \\n)."""
    if state is None:
        state = parser.start_state()
    for line in _LINE_BREAK.split(text):
        yield tokenize_line(parser, line, state)
