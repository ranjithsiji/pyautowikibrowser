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
"""Translate .NET regular expressions (as used by AWB rules and typo lists) to the `regex` module.

The translation is syntactic: Unicode semantics deliberately stay Python's (see CLAUDE.md, rule 3).

Handled:
- ``(?<name>..)`` / ``(?'name'..)`` -> ``(?P<name>..)``; ``\\k<name>`` -> ``(?P=name)``
- .NET group numbering (unnamed groups first, then named) mapped to Python numbering, in both
  pattern backreferences and replacement strings
- ``RegexOptions.ExplicitCapture`` and inline ``n``: unnamed groups become non-capturing
- inline flags in mid-pattern (``a(?i)b``) become scoped groups, as .NET applies them only onward
- ``\\p{IsBlock}`` -> ``\\p{Block=Block}``, ``\\e``, ``\\cX``, ``\\Z``/``\\z``
- character class subtraction ``[a-z-[aeiou]]``
- ``{`` that is not a .NET quantifier is literal
- ``RightToLeft`` -> ``regex.REVERSE``

Balancing groups: AWB uses them in exactly one idiom, a loop that matches balanced nesting,
``(?>OTHER|OPEN(?<D>)|CLOSE(?<-D>))*(?(D)(?!))``. That idiom is translated to an equivalent
recursive group (see :meth:`_Translator.balancing_idiom`). Any other use of balancing groups is
rejected with :class:`UnsupportedPatternError` and must be rewritten by hand.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass, field

import regex

__all__ = [
    "DotNetOptions",
    "Replacement",
    "TranslatedPattern",
    "UnsupportedPatternError",
    "escape",
    "translate",
    "translate_replacement",
]


class UnsupportedPatternError(ValueError):
    """The pattern uses a .NET construct with no automatic translation."""


class DotNetOptions(enum.IntFlag):
    """Values of System.Text.RegularExpressions.RegexOptions."""

    NONE = 0
    IGNORE_CASE = 1
    MULTILINE = 2
    EXPLICIT_CAPTURE = 4
    COMPILED = 8
    SINGLELINE = 16
    IGNORE_PATTERN_WHITESPACE = 32
    RIGHT_TO_LEFT = 64
    ECMA_SCRIPT = 256
    CULTURE_INVARIANT = 512


_DIGITS = frozenset("0123456789")
_IDIOM_TAIL = regex.compile(r"\*\(\?\((\w+)\)\(\?!\)\)")


def _scan_group(src: str, start: int) -> tuple[int, list[int]]:
    """For the group opening at src[start] == "(", return the index of its closing ")" and the
    positions of its top-level "|" separators."""
    depth = 0
    bars: list[int] = []
    j, n = start, len(src)
    while j < n:
        c = src[j]
        if c == "\\":
            j += 2
            continue
        if c == "[":
            j += 1
            if j < n and src[j] == "^":
                j += 1
            if j < n and src[j] == "]":
                j += 1
            while j < n and src[j] != "]":
                j += 2 if src[j] == "\\" else 1
            j += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j, bars
        elif c == "|" and depth == 1:
            bars.append(j)
        j += 1
    raise UnsupportedPatternError(f"unbalanced parenthesis in {src!r}")


@dataclass(frozen=True)
class _Backref:
    """Placeholder for a numeric backreference, resolved once all groups are known."""

    number: int
    trailing: str  # digits that turned out not to belong to the group number
    conditional: bool = False  # the N in (?(N)yes|no)


@dataclass
class _Frame:
    explicit_capture: bool
    ignore_whitespace: bool
    # Scopes opened for mid-group inline flags, e.g. "i" for (?i); closed at "|" and ")".
    auto_scopes: list[str] = field(default_factory=list[str])


@dataclass(frozen=True)
class TranslatedPattern:
    """A translated pattern plus what is needed to use it like the .NET original."""

    source: str
    pattern: str
    flags: int
    # .NET group number -> Python group number. Group 0 maps to 0.
    group_map: dict[int, int] = field(default_factory=dict[int, int])
    group_names: frozenset[str] = frozenset()


class _Translator:
    def __init__(self, source: str, options: DotNetOptions) -> None:
        self.src = source
        self.i = 0
        self.out: list[str | _Backref] = []
        self.stack: list[_Frame] = [
            _Frame(
                explicit_capture=bool(options & DotNetOptions.EXPLICIT_CAPTURE),
                ignore_whitespace=bool(options & DotNetOptions.IGNORE_PATTERN_WHITESPACE),
            )
        ]
        # Capturing groups in order of appearance: None for unnamed, else the name.
        self.groups: list[str | None] = []
        self.options = options
        self.balancing_count = 0

    # -- helpers ---------------------------------------------------------------------------------

    def error(self, msg: str) -> UnsupportedPatternError:
        return UnsupportedPatternError(f"{msg} at offset {self.i} in {self.src!r}")

    def peek(self, offset: int = 0) -> str:
        j = self.i + offset
        return self.src[j] if j < len(self.src) else ""

    def startswith(self, s: str) -> bool:
        return self.src.startswith(s, self.i)

    def read_until(self, terminator: str) -> str:
        end = self.src.find(terminator, self.i)
        if end < 0:
            raise self.error(f"missing {terminator!r}")
        text = self.src[self.i : end]
        self.i = end + len(terminator)
        return text

    # -- main loop -------------------------------------------------------------------------------

    def run(self) -> list[str | _Backref]:
        src = self.src
        while self.i < len(src):
            c = src[self.i]
            frame = self.stack[-1]
            if c == "\\":
                self.escape(in_class=False)
            elif c == "[":
                self.out.append(self.char_class())
            elif c == "(":
                self.open_group()
            elif c == ")":
                self.close_group()
            elif c == "{":
                self.brace()
            elif c == "|":
                scopes = frame.auto_scopes
                self.out.append(")" * len(scopes) + "|" + "".join(f"(?{s}:" for s in scopes))
                self.i += 1
            elif c == "#" and frame.ignore_whitespace:
                end = src.find("\n", self.i)
                self.i = len(src) if end < 0 else end + 1
            elif c in " \t\r\n\f\v" and frame.ignore_whitespace:
                self.i += 1
            else:
                self.out.append(c)
                self.i += 1
        if len(self.stack) != 1:
            raise self.error("unbalanced parenthesis")
        self.out.append(")" * len(self.stack[0].auto_scopes))
        return self.out

    def brace(self) -> None:
        m = regex.compile(r"\{\d+(?:,\d*)?\}").match(self.src, self.i)
        if m:
            self.out.append(m.group(0))
            self.i = m.end()
        else:
            self.out.append("\\{")
            self.i += 1

    # -- escapes ---------------------------------------------------------------------------------

    def escape(self, *, in_class: bool) -> None:
        """Translate the escape at self.i (which points at the backslash)."""
        nxt = self.peek(1)
        if nxt == "":
            raise self.error("trailing backslash")
        if nxt in "pP" and self.peek(2) == "{":
            self.i += 3
            name = self.read_until("}")
            if name.startswith("Is"):
                name = "Block=" + name[2:]
            self.out.append(f"\\{nxt}{{{name}}}")
            return
        if nxt == "e":
            self.out.append("\\x1b")
            self.i += 2
            return
        if nxt == "c":
            letter = self.peek(2)
            if not letter.isascii() or not letter.isalpha():
                raise self.error("bad \\c escape")
            self.out.append(f"\\x{ord(letter.upper()) - 64:02x}")
            self.i += 3
            return
        if in_class:
            self.out.append("\\" + nxt)
            self.i += 2
            return
        if nxt == "k" and self.peek(2) in "<'":
            close = ">" if self.peek(2) == "<" else "'"
            self.i += 3
            name = self.read_until(close)
            if name.isdigit():
                self.out.append(_Backref(int(name), ""))
            else:
                self.out.append(f"(?P={name})")
            return
        if nxt == "Z":
            self.out.append("(?=\\n?\\Z)")
            self.i += 2
            return
        if nxt == "z":
            self.out.append("\\Z")
            self.i += 2
            return
        if nxt in _DIGITS and nxt != "0":
            j = self.i + 1
            while j < len(self.src) and self.src[j] in _DIGITS:
                j += 1
            digits = self.src[self.i + 1 : j]
            self.out.append(_Backref(int(digits), digits))
            self.i = j
            return
        self.out.append("\\" + nxt)
        self.i += 2

    # -- character classes -----------------------------------------------------------------------

    def char_class(self) -> str:
        """Translate the class starting at self.i ('['); return its text and advance past it."""
        src = self.src
        start_out = len(self.out)
        self.i += 1
        parts = ["["]
        if self.peek() == "^":
            parts.append("^")
            self.i += 1
        first = True
        subtract: str | None = None
        while True:
            if self.i >= len(src):
                raise self.error("unterminated character class")
            c = src[self.i]
            if c == "]" and not first:
                self.i += 1
                break
            if c == "\\":
                self.escape(in_class=True)
                piece = self.out.pop()
                assert isinstance(piece, str)
                parts.append(piece)
            elif c == "-" and self.peek(1) == "[":
                self.i += 1
                subtract = self.char_class()
                if self.peek() != "]":
                    raise self.error("class subtraction must be last in the class")
                self.i += 1
                break
            elif c == "[":
                parts.append("\\[")
                self.i += 1
            else:
                parts.append(c)
                self.i += 1
            first = False
        del self.out[start_out:]
        parts.append("]")
        base = "".join(parts)
        if subtract is None:
            return base
        return f"(?:(?!{subtract}){base})"

    # -- groups ----------------------------------------------------------------------------------

    def push(self, opener: str, *, explicit_capture: bool, ignore_whitespace: bool) -> None:
        self.out.append(opener)
        self.stack.append(_Frame(explicit_capture, ignore_whitespace))

    def close_group(self) -> None:
        if len(self.stack) == 1:
            raise self.error("unbalanced ')'")
        frame = self.stack.pop()
        self.out.append(")" * len(frame.auto_scopes) + ")")
        self.i += 1

    def subpattern(self, text: str) -> list[str | _Backref]:
        """Translate a fragment in the current flag context. It may not define capture groups."""
        frame = self.stack[-1]
        sub = _Translator(text, self.options)
        sub.stack[0].explicit_capture = frame.explicit_capture
        sub.stack[0].ignore_whitespace = frame.ignore_whitespace
        sub.balancing_count = self.balancing_count
        pieces = sub.run()
        if sub.groups:
            raise self.error("capturing group inside a balancing-group idiom")
        return pieces

    def balancing_idiom(self) -> bool:
        """Translate ``(?>OTHER|OPEN(?<D>)|CLOSE(?<-D>))*(?(D)(?!))`` if it starts at self.i - 2.

        The .NET loop pushes D on OPEN, pops it on CLOSE (failing if empty) and finally requires D
        empty. The equivalent recursive group, with B a fresh group name, is::

            (?P<B>(?:(?>OTHER)|(?!OTHER)(?>OPEN)(?&B)(?!OTHER)(?!OPEN)(?>CLOSE))*)

        The lookaheads keep .NET's alternative order: inside the atomic group, OPEN is only tried
        where OTHER fails, and CLOSE only where both fail. Recursion stays non-atomic, so the loop
        can backtrack exactly as the .NET one can.
        """
        start = self.i - 2  # the "(" of "(?>"
        end, bars = _scan_group(self.src, start)
        tail = _IDIOM_TAIL.match(self.src, end + 1)
        if not tail:
            return False
        d = tail.group(1)
        starts = [start + 3, *(b + 1 for b in bars)]
        segs = [self.src[a:b] for a, b in zip(starts, [*bars, end], strict=True)]
        push, pop = f"(?<{d}>)", f"(?<-{d}>)"
        if len(segs) < 3 or not segs[-2].endswith(push) or not segs[-1].endswith(pop):
            return False
        other = self.subpattern("|".join(segs[:-2]))
        opener = self.subpattern(segs[-2][: -len(push)])
        closer = self.subpattern(segs[-1][: -len(pop)])

        self.balancing_count += 1
        name = f"_bal{self.balancing_count}_{d}"
        self.groups.append(name)
        self.out += [f"(?P<{name}>(?:(?>", *other, ")|(?!", *other, ")(?>", *opener]
        self.out += [f")(?&{name})(?!", *other, ")(?!", *opener, ")(?>", *closer, "))*)"]
        self.i = tail.end()
        return True

    def open_group(self) -> None:
        frame = self.stack[-1]
        ec, ws = frame.explicit_capture, frame.ignore_whitespace
        if self.peek(1) != "?":
            self.i += 1
            if ec:
                self.push("(?:", explicit_capture=ec, ignore_whitespace=ws)
            else:
                self.groups.append(None)
                self.push("(", explicit_capture=ec, ignore_whitespace=ws)
            return

        self.i += 2  # past "(?"
        c = self.peek()
        if c == "#":
            self.read_until(")")
            return
        if c == ">" and self.balancing_idiom():
            return
        if c in ":=!>":
            self.i += 1
            self.push("(?" + c, explicit_capture=ec, ignore_whitespace=ws)
            return
        if c == "<" and self.peek(1) in "=!":
            self.push("(?<" + self.peek(1), explicit_capture=ec, ignore_whitespace=ws)
            self.i += 2
            return
        if c in "<'" or (c == "P" and self.peek(1) == "<"):
            if c == "P":
                self.i += 1
                c = "<"
            self.i += 1
            name = self.read_until(">" if c == "<" else "'")
            if "-" in name:
                raise self.error("balancing group (rewrite by hand with recursion)")
            if not name or name.isdigit():
                raise self.error(f"numbered group name {name!r}")
            self.groups.append(name)
            self.push(f"(?P<{name}>", explicit_capture=ec, ignore_whitespace=ws)
            return
        if c == "(":
            # Conditional: (?(name)yes|no), (?(1)yes|no) or (?(?=expr)yes|no).
            if self.peek(1) == "?":
                self.push("(?", explicit_capture=ec, ignore_whitespace=ws)
                return
            self.i += 1
            cond = self.read_until(")")
            if cond.isdigit():
                self.out.append("(?(")
                self.out.append(_Backref(int(cond), "", conditional=True))
                self.push(")", explicit_capture=ec, ignore_whitespace=ws)
            else:
                self.push(f"(?({cond})", explicit_capture=ec, ignore_whitespace=ws)
            return

        # Inline options: (?imnsx-imnsx) or scoped (?imnsx-imnsx:...)
        m = regex.compile(r"([imnsx]*)(?:-([imnsx]*))?([:)])").match(self.src, self.i)
        if not m:
            raise self.error("unknown group construct")
        on, off, end = m.group(1), m.group(2) or "", m.group(3)
        self.i = m.end()
        if "n" in on:
            ec = True
        if "n" in off:
            ec = False
        if "x" in on:
            ws = True
        if "x" in off:
            ws = False
        on, off = on.replace("n", ""), off.replace("n", "")
        spec = on + ("-" + off if off else "")
        if end == ":":
            self.push(f"(?{spec}:", explicit_capture=ec, ignore_whitespace=ws)
            return
        # (?flags) applies from here to the end of the enclosing group.
        frame.explicit_capture, frame.ignore_whitespace = ec, ws
        if spec:
            self.out.append(f"(?{spec}:")
            frame.auto_scopes.append(spec)


def _python_numbering(groups: list[str | None]) -> tuple[dict[int, int], frozenset[str]]:
    """Map .NET group numbers to Python group numbers for the same list of groups."""
    py_index: list[int] = []
    py_named: dict[str, int] = {}
    n = 0
    for g in groups:
        if g is None:
            n += 1
            py_index.append(n)
        elif g in py_named:
            py_index.append(py_named[g])
        else:
            n += 1
            py_named[g] = n
            py_index.append(n)

    mapping: dict[int, int] = {0: 0}
    net = 0
    for g, py in zip(groups, py_index, strict=True):
        if g is None:
            net += 1
            mapping[net] = py
    seen: set[str] = set()
    for g, py in zip(groups, py_index, strict=True):
        if g is not None and g not in seen:
            seen.add(g)
            net += 1
            mapping[net] = py
    return mapping, frozenset(py_named)


def _resolve_backref(ref: _Backref, mapping: dict[int, int]) -> str:
    if not ref.trailing:
        if ref.number not in mapping:
            raise UnsupportedPatternError(f"reference to undefined group {ref.number}")
        if ref.conditional:
            return str(mapping[ref.number])
        return f"(?:\\{mapping[ref.number]})"
    # .NET reads as many digits as form an existing group; the rest are literal. With no such
    # group, a multi-digit escape is octal.
    digits = ref.trailing
    for k in range(len(digits), 0, -1):
        n = int(digits[:k])
        if n in mapping:
            return f"(?:\\{mapping[n]})" + digits[k:]
    if len(digits) == 1:
        raise UnsupportedPatternError(f"reference to undefined group {digits}")
    return "\\" + digits


_ESCAPES = {
    "\\": "\\\\",
    "*": "\\*",
    "+": "\\+",
    "?": "\\?",
    "|": "\\|",
    "{": "\\{",
    "[": "\\[",
    "(": "\\(",
    ")": "\\)",
    "^": "\\^",
    "$": "\\$",
    ".": "\\.",
    "#": "\\#",
    " ": "\\ ",
    "\t": "\\t",
    "\n": "\\n",
    "\r": "\\r",
    "\f": "\\f",
}


def escape(text: str) -> str:
    """System.Text.RegularExpressions.Regex.Escape: same characters, same output.

    AWB code relies on its exact output, e.g. replacing the escaped space "\\ " afterwards.
    """
    return "".join(_ESCAPES.get(c, c) for c in text)


def _flags_for(options: DotNetOptions) -> int:
    flags = regex.VERSION0
    if options & DotNetOptions.IGNORE_CASE:
        flags |= regex.IGNORECASE
    if options & DotNetOptions.MULTILINE:
        flags |= regex.MULTILINE
    if options & DotNetOptions.SINGLELINE:
        flags |= regex.DOTALL
    if options & DotNetOptions.RIGHT_TO_LEFT:
        flags |= regex.REVERSE
    if options & DotNetOptions.ECMA_SCRIPT:
        flags |= regex.ASCII
    return flags


def translate(pattern: str, options: DotNetOptions = DotNetOptions.NONE) -> TranslatedPattern:
    """Translate a .NET pattern. Raises UnsupportedPatternError for untranslatable constructs."""
    t = _Translator(pattern, options)
    pieces = t.run()
    mapping, names = _python_numbering(t.groups)
    text = "".join(p if isinstance(p, str) else _resolve_backref(p, mapping) for p in pieces)
    return TranslatedPattern(pattern, text, _flags_for(options), mapping, names)


# -- replacement strings -------------------------------------------------------------------------

type _Part = str | int | Callable[[regex.Match[str]], str]


@dataclass(frozen=True)
class Replacement:
    """A .NET replacement string, usable as the `repl` callable of regex.sub."""

    source: str
    parts: tuple[_Part, ...]

    def __call__(self, m: regex.Match[str]) -> str:
        out: list[str] = []
        for p in self.parts:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, int):
                out.append(m.group(p) or "")
            else:
                out.append(p(m))
        return "".join(out)

    @property
    def is_literal(self) -> bool:
        return all(isinstance(p, str) for p in self.parts)


def _last_group(m: regex.Match[str]) -> str:
    # .NET's $+ is the highest-numbered group (not the last one to match).
    groups = m.re.groups
    return (m.group(groups) or "") if groups else m.group(0)


def translate_replacement(replacement: str, tp: TranslatedPattern) -> Replacement:
    """Translate a .NET replacement string for use with a pattern from translate()."""
    parts: list[_Part] = []
    lit: list[str] = []

    def flush() -> None:
        if lit:
            parts.append("".join(lit))
            lit.clear()

    def add(p: _Part) -> None:
        flush()
        parts.append(p)

    s = replacement
    i = 0
    while i < len(s):
        c = s[i]
        if c != "$" or i + 1 >= len(s):
            lit.append(c)
            i += 1
            continue
        nxt = s[i + 1]
        if nxt == "$":
            lit.append("$")
            i += 2
        elif nxt == "&":
            add(0)
            i += 2
        elif nxt in _DIGITS:
            j = i + 1
            while j < len(s) and s[j] in _DIGITS:
                j += 1
            digits = s[i + 1 : j]
            for k in range(len(digits), 0, -1):
                n = int(digits[:k])
                if n in tp.group_map:
                    add(tp.group_map[n])
                    lit.append(digits[k:])
                    break
            else:
                lit.append("$" + digits)
            i = j
        elif nxt == "{":
            end = s.find("}", i + 2)
            name = s[i + 2 : end] if end > 0 else ""
            if name.isdigit() and int(name) in tp.group_map:
                add(tp.group_map[int(name)])
                i = end + 1
            elif name in tp.group_names:
                add(_named(name))
                i = end + 1
            else:
                lit.append("$")
                i += 1
        elif nxt == "`":
            add(lambda m: m.string[: m.start()])
            i += 2
        elif nxt == "'":
            add(lambda m: m.string[m.end() :])
            i += 2
        elif nxt == "_":
            add(lambda m: m.string)
            i += 2
        elif nxt == "+":
            add(_last_group)
            i += 2
        else:
            lit.append("$")
            i += 1
    flush()
    return Replacement(replacement, tuple(parts))


def _named(name: str) -> Callable[[regex.Match[str]], str]:
    def get(m: regex.Match[str]) -> str:
        return m.group(name) or ""

    return get
