import pytest
import regex

from pyawb.core import rx
from pyawb.core.dotnet_regex import DotNetOptions as O
from pyawb.core.dotnet_regex import UnsupportedPatternError, translate


def sub(find: str, replace: str, text: str, options: O = O.NONE) -> str:
    return rx.rule(find, replace, options).apply(text).text


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        (r"(?<y>\d{4})", r"(?P<y>\d{4})"),
        (r"(?'y'\d)", r"(?P<y>\d)"),
        (r"(?<y>a)\k<y>", r"(?P<y>a)(?P=y)"),
        (r"\p{IsGreek}", r"\p{Block=Greek}"),
        (r"[\p{IsCyrillic}a]", r"[\p{Block=Cyrillic}a]"),
        (r"\e\cA", r"\x1b\x01"),
        (r"x{,2}", r"x\{,2}"),
        (r"x{2,}y{1,3}", r"x{2,}y{1,3}"),
        (r"[a[b]", r"[a\[b]"),
        (r"a\z", r"a\Z"),
        (r"(?<=a)(?<!b)(?=c)(?!d)(?>e)(?:f)", r"(?<=a)(?<!b)(?=c)(?!d)(?>e)(?:f)"),
        (r"a(?#comment)b", "ab"),
    ],
)
def test_syntax(pattern: str, expected: str) -> None:
    assert translate(pattern).pattern == expected


def test_dotnet_numbers_unnamed_groups_before_named() -> None:
    # .NET: group 1 = (b), group 2 = a. Python would number them the other way round.
    assert sub(r"(?<a>x)(y)", "$1$2", "xy") == "yx"
    assert sub(r"(?<a>x)(y)\1", "[$0]", "xyy") == "[xyy]"


def test_replacement_syntax() -> None:
    assert sub("(b)", "$$1", "abc") == "a$1c"
    assert sub("(b)", "<$&>", "abc") == "a<b>c"
    assert sub("(?<n>b)", "${n}${n}", "abc") == "abbc"
    assert sub("(b)", "${1}0", "abc") == "ab0c"
    assert sub("(b)", "$10", "abc") == "ab0c"  # no group 10: group 1 then "0"
    assert sub("(b)", "$9", "abc") == "a$9c"  # undefined: literal
    assert sub("b", "[$`|$']", "abc") == "a[a|c]c"
    assert sub("(a)?b", "[$1]", "b") == "[]"
    assert sub("b", "$x", "abc") == "a$xc"
    assert sub("b", "\\1", "abc") == "a\\1c"  # backslashes are literal in .NET replacements


def test_explicit_capture() -> None:
    tp = translate(r"(a)(?<n>b)", O.EXPLICIT_CAPTURE)
    assert tp.pattern == r"(?:a)(?P<n>b)"
    assert translate(r"(?n:(a))(b)").pattern == r"(?:(?:a))(b)"
    assert translate(r"(?n)(a)").pattern == r"(?:a)"


def test_mid_pattern_inline_flags_apply_onward_only() -> None:
    p = rx.compile_dotnet(r"a(?i)b")
    assert p.fullmatch("aB") and not p.fullmatch("AB")
    # The flag scope must not swallow the alternation.
    p = rx.compile_dotnet(r"x(?i)y|z")
    assert p.fullmatch("Z") and p.fullmatch("xY") and not p.fullmatch("xZ")
    p = rx.compile_dotnet(r"(?i)a(?-i)b")
    assert p.fullmatch("Ab") and not p.fullmatch("AB")


def test_class_subtraction() -> None:
    p = rx.compile_dotnet(r"^[a-z-[aeiou]]+$")
    assert p.match("bcd") and not p.match("bad")


def test_capital_z_allows_final_newline() -> None:
    p = rx.compile_dotnet(r"a\Z")
    assert p.search("a\n") and p.search("a") and not p.search("a\n\n")


def test_options() -> None:
    assert sub("B", "x", "abc", O.IGNORE_CASE) == "axc"
    assert sub("^b", "x", "a\nb", O.MULTILINE) == "a\nx"
    assert sub("a.b", "x", "a\nb", O.SINGLELINE) == "x"
    assert sub("a b # comment", "x", "ab", O.IGNORE_PATTERN_WHITESPACE) == "x"
    assert rx.rule("b", "x", O.RIGHT_TO_LEFT).apply("abcb", count=1).text == "abcx"


def test_numeric_conditional() -> None:
    p = rx.compile_dotnet(r"^(<)?a(?(1)>|)$")
    assert p.match("<a>") and p.match("a") and not p.match("<a")


def test_backreference_digits() -> None:
    assert rx.compile_dotnet(r"(a)\10").fullmatch("aa0")


def test_balancing_groups_outside_the_idiom_are_rejected() -> None:
    with pytest.raises(UnsupportedPatternError):
        translate(r"(?<open>\[)(?<-open>\])")
    with pytest.raises(UnsupportedPatternError):
        translate(r"(?<inner-open>x)")
    # Right shape but no (?(D)(?!)) check at the end.
    with pytest.raises(UnsupportedPatternError):
        translate(r"(?>[^{}]+|\{(?<D>)|\}(?<-D>))*")


# The balanced-nesting idiom, as AWB writes it (WikiRegexes.NestedTemplates etc.).
NESTED_TEMPLATES = r"{{(?>[^\{\}]+|\{(?<DEPTH>)|\}(?<-DEPTH>))*(?(DEPTH)(?!))}}"
SIMPLE_WIKILINK = r"\[\[((?>[^\[\]\n]+|\[\[(?<DEPTH>)|\]\](?<-DEPTH>))*(?(DEPTH)(?!)))\]\]"
NESTED_COMMENT = r"<!--(?>(?!<!--|-->).|<!--(?<Depth>)|-->(?<-Depth>))*(?(Depth)(?!))-->"
ALL_TAGS = (
    r"<\s*(pre|nowiki)[^<>]*>(?>(?!<\s*\1[^<>]*>|<\s*/\s*\1\b[^<>]*>).|<\s*\1[^<>]*>(?<Depth>)"
    r"|<\s*/\s*\1\b[^<>]*>(?<-Depth>))*(?(Depth)(?!))<\s*/\s*\1\b[^<>]*>"
)


def test_idiom_nested_templates() -> None:
    p = rx.compile_dotnet(NESTED_TEMPLATES)
    text = "a {{x|{{y|{{z}}}}|w}} b {{c}} {{open|{{inner}}"
    assert [m.group(0) for m in p.finditer(text)] == ["{{x|{{y|{{z}}}}|w}}", "{{c}}", "{{inner}}"]


def test_idiom_keeps_dotnet_group_numbers() -> None:
    text = "[[File:a.jpg|thumb|see [[b]] and [[c|d]]]] [[e]]"
    assert sub(SIMPLE_WIKILINK, "<$1>", text) == "<File:a.jpg|thumb|see [[b]] and [[c|d]]> <e>"
    # Newlines are excluded from the content, so this does not match as one link.
    assert rx.compile_dotnet(SIMPLE_WIKILINK).findall("[[a\nb]]") == []


def test_idiom_with_lookahead_other() -> None:
    p = rx.compile_dotnet(NESTED_COMMENT, O.SINGLELINE)
    m = p.search("x <!-- a <!-- b --> c --> d -->")
    assert m and m.group(0) == "<!-- a <!-- b --> c -->"


def test_idiom_with_backreference() -> None:
    p = rx.compile_dotnet(ALL_TAGS, O.SINGLELINE | O.IGNORE_CASE)
    m = p.search("x <pre>a<PRE>b</pre>c</pre> y</pre>")
    assert m and m.group(0) == "<pre>a<PRE>b</pre>c</pre>"
    assert m.group(1) == "pre"


def test_idiom_twice_in_one_pattern() -> None:
    p = rx.compile_dotnet(NESTED_TEMPLATES + " " + NESTED_TEMPLATES)
    m = p.search("{{a|{{b}}}} {{c}}")
    assert m and m.group(0) == "{{a|{{b}}}} {{c}}"


def test_timeout_is_reported_not_raised() -> None:
    r = rx.rule(r"(a|aa)+$", "x")
    res = r.apply("a" * 40 + "b", timeout=0.05)
    assert res.timed_out and res.text.endswith("b")


def test_rx_compile_uses_version0() -> None:
    assert rx.compile("a").flags & regex.VERSION0


def test_escape_matches_dotnet() -> None:
    assert rx.escape("a b.c*d#e\tf]g}h") == r"a\ b\.c\*d\#e\tf]g}h"


def test_failed_match_behaves_like_dotnet() -> None:
    m = rx.DotNetRegex(r"(a)(?<n>b)").match("xyz")
    assert not m and not m.success
    assert m.value == "" and m.group(1) == "" and m.group("n") == ""


def test_dotnet_match_groups() -> None:
    m = rx.DotNetRegex(r"(?<n>x)(y)(z)?").match("_xy")
    assert m.success and m.index == 1 and m.length == 2
    # .NET numbers the unnamed groups first: 1 = (y), 2 = (z)?, 3 = n
    assert (m.group(1), m.group(2), m.group(3)) == ("y", "", "x")
    assert m.group_success(1) and not m.group_success(2)
    assert m.group(99) == "" and not m.group_success(99)


def test_regex_concatenates_like_csharp() -> None:
    r = rx.DotNetRegex("a+")
    assert r + "b" == "a+b" and "b" + r == "ba+"


def test_split_like_dotnet() -> None:
    assert rx.DotNetRegex(",").split("a,b,,c") == ["a", "b", "", "c"]
    assert rx.DotNetRegex("(-)").split("a-b") == ["a", "-", "b"]
    # hidden recursion groups from balancing-group translation are not returned
    r = rx.DotNetRegex(
        r"\[(?>[^\[\]]+|\[(?<DEPTH>)|\](?<-DEPTH>))*(?(DEPTH)(?!))\]",
        rx.DotNetOptions.EXPLICIT_CAPTURE,
    )
    assert r.split("x [a [b]] y") == ["x ", " y"]
