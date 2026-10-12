"""Convert an AWB NUnit test file to pytest (one-off porting aid).

usage: nunit2py.py <file.cs> <scratch dir with csdecl.py> <python names json>
"""
import json, re, sys, textwrap
sys.path.insert(0, sys.argv[2])
from csdecl import tokens, strval
from cs2py import pylit  # noqa

NAMES = json.load(open(sys.argv[3]))  # {"static": [...], "site": [...]}
STATIC, SITE = set(NAMES["static"]), set(NAMES["site"])
_NS_CONSTANTS = ["MEDIA", "SPECIAL", "ARTICLE", "TALK", "USER", "USER_TALK", "PROJECT", "PROJECT_TALK",
    "FILE", "FILE_TALK", "MEDIAWIKI", "MEDIAWIKI_TALK", "TEMPLATE", "TEMPLATE_TALK", "HELP", "HELP_TALK",
    "CATEGORY", "CATEGORY_TALK", "PORTAL", "PORTAL_TALK", "DRAFT", "DRAFT_TALK", "MOS", "MOS_TALK",
    "TIMEDTEXT", "TIMEDTEXT_TALK", "MODULE", "MODULE_TALK", "EVENT", "EVENT_TALK"]
NS = {c.replace("_", "").lower(): c for c in _NS_CONSTANTS}
NS.update({"mainspace": "ARTICLE", "image": "FILE", "imagetalk": "FILE_TALK",
           "firstcustom": "PORTAL", "firstcustomtalk": "PORTAL_TALK"})
OPTS = {"IgnoreCase": "IGNORE_CASE", "Multiline": "MULTILINE", "Singleline": "SINGLELINE",
        "ExplicitCapture": "EXPLICIT_CAPTURE", "RightToLeft": "RIGHT_TO_LEFT", "None": "NONE"}

class Unsupported(Exception): pass

SNAKE_EXCEPTIONS = {"ExtractCOinS": "extract_coins", "COinS": "coins"}


def snake(name):
    """CamelCase -> snake_case, keeping acronyms together (HTMLListToWiki -> html_list_to_wiki)."""
    if name in SNAKE_EXCEPTIONS:
        return SNAKE_EXCEPTIONS[name]
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()

# AWB overloads with "out bool noChange" that AWB-L ports as foo_no_change() -> (text, no_change)
NO_CHANGE_OVERLOADS = {"fix_syntax", "fix_headings", "cite_template_dates", "remove_category", "add_category",
    "bullet_external_links", "conversions", "fix_people_categories", "interwiki_conversions", "living_people",
    "remove_image", "replace_image", "unicodify"}
TOOLS_FIELDS = {"Diacritics", "SortKeyChars"}
DATE_LOCALE = {"International": "INTERNATIONAL", "American": "AMERICAN", "ISO": "ISO", "Undetermined": "UNDETERMINED"}

class E:
    """Expression parser producing Python source."""
    def __init__(self, toks): self.t, self.i, self.out_args, self.ref_args = toks, 0, [], []

    def call_args(self):
        """Arguments, collecting C# "out x" arguments into self.out_args instead."""
        self.take("(")
        out = []
        while self.peek()[1] != ")":
            if self.peek()[1] == "out":
                self.take(); _, name = self.take(); self.out_args.append(name)
            elif self.peek()[1] == "ref":
                out.append(self.ref_arg())
            else:
                out.append(self.expr())
            if self.peek()[1] == ",": self.take(",")
        self.take(")")
        return out

    @staticmethod
    def with_outs(code, outs):
        """f(a, out x) -> value of f, also binding x: AWB-L returns (value, x, ...) for these."""
        binds = ", ".join(f"({o} := _t[{i + 1}])" for i, o in enumerate(outs))
        return f"((_t := {code}), {binds})[0][0]"
    def peek(self, o=0):
        j = self.i + o
        return self.t[j] if j < len(self.t) else ("eof", "")
    def take(self, text=None):
        k, t = self.t[self.i]
        if text is not None and t != text: raise Unsupported(f"expected {text} got {t} near {self.t[self.i-3:self.i+3]}")
        self.i += 1; return k, t
    def ref_arg(self):
        """ "ref x" argument: AWB-L returns (new x, value), see with_refs."""
        self.take("ref")
        e = self.expr()
        self.ref_args.append(e)
        return e

    @staticmethod
    def with_refs(code, refs):
        """f(ref x, ...) -> value of f, also rebinding x: AWB-L returns (new x, value)."""
        if len(refs) != 1 or not refs[0].isidentifier():
            raise Unsupported(f"ref arguments {refs}")
        return f"((_t := {code}), ({refs[0]} := _t[0]))[0][1]"

    def wrap_refs(self, code):
        if self.ref_args:
            refs, self.ref_args = self.ref_args, []
            code = self.with_refs(code, refs)
        return code

    def args(self):
        self.take("(")
        out = []
        while self.peek()[1] != ")":
            if self.peek()[1] == "out":
                self.take(); _, name = self.take(); self.out_args.append(name)
            else:
                out.append(self.ref_arg() if self.peek()[1] == "ref" else self.expr())
            if self.peek()[1] == ",": self.take(",")
        self.take(")")
        return out
    def expr(self):
        return self.orexpr()
    def orexpr(self):
        a = self.andexpr()
        while self.peek()[1] == "|" and self.peek(1)[1] == "|":
            self.take(); self.take(); a = f"{a} or {self.andexpr()}"
        return a
    def andexpr(self):
        a = self.eq()
        while self.peek()[1] == "&" and self.peek(1)[1] == "&":
            self.take(); self.take(); a = f"{a} and {self.eq()}"
        return a
    def eq(self):
        a = self.add()
        if self.peek()[1] in ("=", "!") and self.peek(1)[1] == "=":
            op = "==" if self.take()[1] == "=" else "!="; self.take()
            a = f"{a} {op} {self.add()}"
        elif self.peek()[1] in ("<", ">"):
            op = self.take()[1]
            if self.peek()[1] == "=": self.take(); op += "="
            a = f"{a} {op} {self.add()}"
        return a
    def add(self):
        a = self.unary()
        while self.peek()[1] in ("+", "|") and not (self.peek()[1] == "|" and self.peek(1)[1] == "|"):
            op = self.take()[1]
            a = f"{a} {op} {self.unary()}"
        return a
    def unary(self):
        if self.peek()[1] == "!":
            self.take(); return f"not {self.unary()}"
        return self.postfix(self.primary())
    def postfix(self, code):
        while True:
            k, t = self.peek()
            if t == "." or (k == "id" and t.startswith(".")):
                self.take("."); _, name = self.take()
                code = self.members(code, name.split("."))
            elif t == "[":
                self.take("["); idx = self.expr(); self.take("]")
                code = f"{code}[{idx}]"
            else:
                return code
    def members(self, code, parts):
        """a.B.C(...): only the last member can take the call's arguments."""
        parts = [p for p in parts if p]
        for i, part in enumerate(parts):
            code = self.member(code, part, can_call=(i == len(parts) - 1))
        return code

    def member(self, code, name, can_call=True):
        if name == "Groups":
            self.take("["); key = self.expr(); self.take("]")
            self.take("."); _, prop = self.take()
            prop, *rest = prop.split(".")  # Groups[2].Value.Equals(...)
            if prop == "Value": code = f"{code}.group({key})"
            elif prop == "Success": code = f"{code}.group_success({key})"
            elif prop == "Index": code = f"{code}.start({key})"
            elif prop == "Length": code = f"len({code}.group({key}))"
            else: raise Unsupported("Groups." + prop)
            code = self.members(code, rest) if rest else code
            return code
        if name == "TryGetValue":  # d.TryGetValue(k, out v) -> ((v := d.get(k)) is not None)
            self.take("("); key = self.expr(); self.take(","); self.take("out"); _, var = self.take(); self.take(")")
            return f"(({var} := {code}.get({key})) is not None)"
        if name == "Length": return f"cs_len({code})"
        simple = {"Value": "value", "Success": "success", "Index": "index"}
        if name in simple: return f"{code}.{simple[name]}"
        if name == "Count": return f"len({code})"
        if name == "Keys": return f"list({code}.keys())"
        if name == "Values": return f"list({code}.values())"
        meth = {"Add": None, "Equals": None, "Clear": None, "ContainsKey": None, "ContainsValue": None, "IsMatch": "is_match", "Match": "match", "Matches": "matches", "Replace": "replace",
                "Contains": None, "Trim": "strip", "ToString": None, "Split": "split", "StartsWith": "startswith",
                "EndsWith": "endswith", "Substring": None}
        if name not in meth:
            # generic fallback: AWB method -> snake_case Python method (verified by running tests)
            if can_call and self.peek()[1] == "(":
                a = self.args()
                code = self.wrap_refs(f"{code}.{snake(name)}({', '.join(a)})")
                if self.out_args:
                    outs, self.out_args = self.out_args, []
                    code = self.with_outs(code, outs)
                return code
            return f"{code}.{snake(name)}"
        a = self.args() if can_call and self.peek()[1] == "(" else []
        if name == "Contains": return f"({a[0]} in {code})"
        if name == "Add": return f"{code}.append({a[0]})" if len(a) == 1 else f"{code}[{a[0]}] = {a[1]}"
        if name == "Equals": return f"({code} == {a[0]})"
        if name == "ContainsKey": return f"({a[0]} in {code})"
        if name == "ContainsValue": return f"({a[0]} in {code}.values())"
        if name == "Clear": return f"{code}.clear()"
        if name == "ToString": return f"str({code})"
        if name == "Substring": return f"{code}[{a[0]}:]" if len(a) == 1 else f"{code}[{a[0]}:{a[0]} + {a[1]}]"
        return f"{code}.{meth[name]}({', '.join(a)})"
    def primary(self):
        k, t = self.peek()
        if k in ("str", "vstr"):
            self.take(); return pylit(strval(k, t))
        if k == "num": self.take(); return t
        if k == "chr": self.take(); return repr(strval("str", '"' + t[1:-1] + '"'))
        if t == "-" and self.peek(1)[0] == "num": self.take(); return "-" + self.take()[1]
        if t == "(":
            self.take("("); e = self.expr(); self.take(")"); return f"({e})"
        if t in ("null",): self.take(); return "None"
        if t in ("true", "false"): self.take(); return t.capitalize()
        if t == "new":
            self.take(); _, what = self.take()
            what = what.rsplit(".", 1)[-1]  # System.Collections.Generic.List -> List
            if what in ("[]", "[", "string"):
                if what == "[": self.take("]")
                if what == "string": self.take("["); self.take("]")
                self.take("{"); items = []
                while self.peek()[1] != "}":
                    items.append(self.expr())
                    if self.peek()[1] == ",": self.take(",")
                self.take("}")
                return "[" + ", ".join(items) + "]"
            if what == "Regex":
                a = self.args()
                return f"DotNetRegex({', '.join(a)})"
            if what == "Parsers":
                a = self.args(); return self.postfix(f"genfixes.Parsers({', '.join(a)})")
            if what in ("List", "Dictionary", "HashSet"):
                self.take("<")
                depth = 1
                while depth:
                    t2 = self.take()[1]
                    depth += {"<": 1, ">": -1}.get(t2, 0)
                if self.peek()[1] == "(":
                    a = self.args()
                    if self.peek()[1] != "{":
                        return f"list({a[0]})" if a else ("{}" if what == "Dictionary" else "[]")
                self.take("{")
                items = []
                while self.peek()[1] != "}":
                    if what == "Dictionary" and self.peek()[1] == "[":
                        self.take("["); k = self.expr(); self.take("]"); self.take("="); v = self.expr()
                        items.append(f"{k}: {v}")
                    elif what == "Dictionary" and self.peek()[1] == "{":
                        self.take("{"); k = self.expr(); self.take(","); v = self.expr(); self.take("}")
                        items.append(f"{k}: {v}")
                    else:
                        items.append(self.expr())
                    if self.peek()[1] == ",": self.take(",")
                self.take("}")
                if what == "Dictionary": return "{" + ", ".join(items) + "}"
                return "[" + ", ".join(items) + "]"
            if what[:1].isupper() and self.peek()[1] == "(":
                a = self.args()
                return self.postfix(f"{what}({', '.join(a)})")
            raise Unsupported("new " + what)
        if k == "id":
            self.take()
            head, _, rest = t.partition(".")
            if head == "WikiRegexes":
                name, _, more = rest.partition(".")
                if name == "GenerateNamespaceRegex":
                    a = self.args(); return f"S.site.generate_namespace_regex({', '.join(a)})"
                if name in SITE: code = f"S.{name}"
                elif name in STATIC: code = f"W.{name}"
                else: raise Unsupported("WikiRegexes." + name)
                code = self.members(code, more.split("."))
                return code
            if t == "Regex.Escape":
                a = self.args(); return f"rx.escape({a[0]})"
            if t == "System.DateTime.UtcNow.ToString":
                self.args(); return "utc_month_year()"  # only used with "MMMM yyyy", BritishEnglish
            if head == "InterWikiOrderEnum":
                return f"genfixes.InterWikiOrderEnum.{snake(rest).upper()}"
            if head == "ProjectEnum":
                return repr(rest)
            if head == "Namespace":
                if rest.lower() in NS: return f"Namespace.{NS[rest.lower()]}"
                a = self.args()
                return self.postfix(f"namespace.{snake(rest)}({', '.join(a)})")
            if head == "RegexOptions": return f"O.{OPTS[rest]}"
            if t == "Tools.NestedTemplateRegex":
                a = self.args(); return f"tools.nested_template_regex({', '.join(a)})"
            if head == "Tools":
                name, _, more = rest.partition(".")
                if name in TOOLS_FIELDS:
                    code = f"tools.{name}"
                else:
                    a = self.args()
                    code = f"tools.{snake(name)}({', '.join(a)})"
                code = self.members(code, more.split("."))
                return code
            if head == "Regex" and rest in ("IsMatch", "Match", "Matches", "Replace", "Split"):
                a = self.args()
                text, pat, extra = a[0], a[1], a[2:]
                opts = [x for x in extra if x.startswith("O.")]
                other = [x for x in extra if not x.startswith("O.")]
                regex = f"DotNetRegex({pat}{', ' + opts[0] if opts else ''})"
                meth = {"IsMatch": "is_match", "Match": "match", "Matches": "matches", "Replace": "replace", "Split": "split"}[rest]
                return self.postfix(f"{regex}.{meth}({', '.join([text, *other])})")
            if head in ("Parsers", "MetaDataSorter", "parser", "parser2", "Parser", "p") and rest and not t.startswith("Parsers.DateLocale."):
                name, _, more = rest.partition(".")
                obj = "genfixes" if head in ("Parsers", "MetaDataSorter") else head
                if more:  # parser.Sorter.RemoveCats(...): the call is on the last member
                    code = f"{obj}.{snake(name)}"
                elif self.peek()[1] == "(" and snake(name) == "tagger":
                    # Tagger(..., [out noChange,] ref summary): AWB-L returns (text, [no_change,] summary)
                    a = self.call_args()
                    refs, self.ref_args = self.ref_args, []
                    outs, self.out_args = self.out_args, []
                    a = [x for x in a if x not in refs]
                    fn = "tagger_no_change" if outs else "tagger"
                    code = self.with_outs(f"{obj}.{fn}({', '.join(a)})", outs + refs)
                elif self.peek()[1] == "(":
                    a = self.call_args()
                    code = self.wrap_refs(f"{obj}.{snake(name)}({', '.join(a)})")
                    if self.out_args:
                        outs, self.out_args = self.out_args, []
                        if snake(name) in NO_CHANGE_OVERLOADS:  # separate function in AWB-L
                            code = code.replace(f".{snake(name)}(", f".{snake(name)}_no_change(", 1)
                        code = self.with_outs(code, outs)
                else:
                    code = f"{obj}.{snake(name)}"
                code = self.members(code, more.split("."))
                return self.postfix(code)
            if t.startswith("Parsers.DateLocale."):
                return "DateLocale." + DATE_LOCALE[t.rsplit(".", 1)[1]]
            if t == "Namespace.Determine":
                a = self.args(); return f"namespace.determine({', '.join(a)})"
            if t == "Environment.NewLine": return '"\\r\\n"'
            if t == "string.Empty" or t == "String.Empty": return '""'
            if "." in t:
                # local.member chains
                base, *members = t.split(".")
                code = base
                code = self.members(code, members)
                return code
            if self.peek()[1] == "(" and t[:1].isupper():
                a = self.args()
                return f"{snake(t)}({', '.join(a)})"
            return t
        raise Unsupported(f"primary {t!r}")

def convert_call(name, args, msg_ix=None):
    pass

ASSERTS = {
    "ClassicAssert.IsTrue": lambda a: f"assert {a[0]}" + (f", {a[1]}" if len(a) > 1 else ""),
    "ClassicAssert.IsFalse": lambda a: f"assert not ({a[0]})" + (f", {a[1]}" if len(a) > 1 else ""),
    "Assert.IsTrue": lambda a: f"assert {a[0]}" + (f", {a[1]}" if len(a) > 1 else ""),
    "Assert.IsFalse": lambda a: f"assert not ({a[0]})" + (f", {a[1]}" if len(a) > 1 else ""),
    "Assert.AreEqual": lambda a: f"assert {a[1]} == {a[0]}" + (f", {a[2]}" if len(a) > 2 else ""),
    "ClassicAssert.AreEqual": lambda a: f"assert {a[1]} == {a[0]}" + (f", {a[2]}" if len(a) > 2 else ""),
    "ClassicAssert.GreaterOrEqual": lambda a: f"assert {a[0]} >= {a[1]}" + (f", {a[2]}" if len(a) > 2 else ""),
    "ClassicAssert.IsNull": lambda a: f"assert {a[0]} is None" + (f", {a[1]}" if len(a) > 1 else ""),
    "ClassicAssert.IsNotNull": lambda a: f"assert {a[0]} is not None" + (f", {a[1]}" if len(a) > 1 else ""),
    "ClassicAssert.IsEmpty": lambda a: f"assert len({a[0]}) == 0" + (f", {a[1]}" if len(a) > 1 else ""),
    "ClassicAssert.AreNotEqual": lambda a: f"assert {a[1]} != {a[0]}" + (f", {a[2]}" if len(a) > 2 else ""),
    "RegexAssert.Matches": lambda a: f"regex_assert.matches({', '.join(a)})",
    "RegexAssert.NoMatch": lambda a: f"regex_assert.no_match({', '.join(a)})",
    "RegexAssert.IsMatch": lambda a: f"regex_assert.is_match({', '.join(a)})",
    "RegexAssert.NotMatches": lambda a: f"regex_assert.not_matches({', '.join(a)})",
    "TestMatch": lambda a: f"check_match({', '.join(a)})",
    "TestMatches": lambda a: f"check_matches({', '.join(a)})",
}

def assert_that(e):
    e.take("(")
    actual = e.expr(); e.take(",")
    _, isx = e.take()
    if isx == "Is.EqualTo":
        e.take("("); exp = e.expr(); e.take(")")
        cond = f"{actual} == {exp}"
        if e.peek()[1] == "." and e.peek(1)[1] == "IgnoreCase":
            e.take(); e.take()
            cond = f"({actual}).lower() == ({exp}).lower()"
    elif isx in ("Does.Contain", "Does.Not.Contain", "Does.StartWith", "Does.EndWith", "Is.Not.EqualTo"):
        e.take("("); exp = e.expr(); e.take(")")
        cond = {"Does.Contain": f"{exp} in {actual}", "Does.Not.Contain": f"{exp} not in {actual}",
                "Does.StartWith": f"{actual}.startswith({exp})", "Does.EndWith": f"{actual}.endswith({exp})",
                "Is.Not.EqualTo": f"{actual} != {exp}"}[isx]
    elif isx in ("Is.Not.SameAs", "Is.SameAs"):
        e.take("("); exp = e.expr(); e.take(")")
        cond = f"{actual} {'is not' if 'Not' in isx else 'is'} {exp}"
    elif isx == "Is.Not.Null": cond = f"{actual} is not None"
    elif isx == "Is.Not.Empty": cond = f"len({actual}) > 0"
    elif isx == "Is.Empty": cond = f"len({actual}) == 0"
    elif isx == "Is.True": cond = f"{actual}"
    elif isx == "Is.False": cond = f"not ({actual})"
    elif isx == "Is.Null": cond = f"{actual} is None"
    else: raise Unsupported(isx)
    # .AsCollection etc
    while e.peek()[1] == ".": e.take(); e.take()
    msg = None
    if e.peek()[1] == ",": e.take(); msg = e.expr()
    e.take(")")
    return f"assert {cond}" + (f", {msg}" if msg else "")

def statement(toks):
    if len(toks) == 2 and toks[0][0] == "id" and toks[1][0] == "id":
        return None  # bare declaration, e.g. "bool noChange;"
    if toks and toks[0][1] == "const":
        toks = toks[1:]
    e = E(toks)
    k, t = e.peek()
    if t == "Assert.That":
        e.take(); out = assert_that(e)
    elif t in ASSERTS:
        e.take(); out = ASSERTS[t](e.args())
    elif t == "Variables.SetProjectLangCode":
        e.take(); a = e.args(); out = f"S = set_lang({a[0]})"
    elif t == "WikiRegexes.MakeLangSpecificRegexes":
        return None
    elif t.rsplit(".", 1)[-1] in ("List", "Dictionary", "HashSet", "IDictionary") and e.peek(1)[1] == "<":
        e.take(); e.take("<"); depth = 1
        while depth:
            depth += {"<": 1, ">": -1}.get(e.take()[1], 0)
        _, name = e.take(); e.take("="); out = f"{name} = {e.expr()}"
    elif t == "string" and e.peek(1)[1] == "[]" and e.peek(3)[1] == "=":
        e.take(); e.take(); _, name = e.take(); e.take("="); out = f"{name} = {e.expr()}"
    elif e.peek(1)[0] == "id" and e.peek(2)[1] == "=" and e.peek(3)[1] != "=":
        e.take(); _, name = e.take(); e.take("="); out = f"{name} = {e.expr()}"
        while e.peek()[1] == ",":
            e.take(); _, name = e.take(); e.take("="); out += f"\n{name} = {e.expr()}"
    elif t == "Variables.AddUnderscoredTitles":
        e.take(); a = e.args()
        out = f"S = set_site(underscored_titles=current_site().underscored_titles | frozenset({a[0]}))"
    elif t in ("Variables.SetProjectSimple", "Variables.SetProject"):
        e.take(); a = e.args()
        out = f"S = set_project({a[0]}, {a[1]})"
    elif t == "foreach" and e.peek(1)[1] == "(":
        # foreach (T x in expr) statement;  (single-statement body without braces)
        e.take(); e.take("("); e.take()
        _, var = e.take(); e.take("in"); seq = e.expr(); e.take(")")
        body = statement(e.t[e.i:])
        e.i = len(e.t)
        out = f"for {var} in {seq}:\n" + "\n".join("    " + line for line in (body or "pass").split("\n"))
    elif t == "Variables.Namespaces.Remove":
        e.take(); a = e.args()
        out = f"S = set_site(namespaces={{k: v for k, v in current_site().namespaces.items() if k != {a[0]}}})"
    elif t == "Variables.Namespaces.Add":
        e.take(); a = e.args()
        name = a[1]
        if name.endswith('"') and not name.endswith(':"'):  # SiteConfig names end with ":", as AWB's do
            name = name[:-1] + ':"'
        out = f"S = set_site(namespaces={{**current_site().namespaces, {a[0]}: {name}}})"
    elif t == "WikiRegexes.DatedTemplates" and e.peek(1)[1] == "=":
        e.take(); e.take("=")
        out = f"S = set_site(dated_templates=tuple({e.expr()}))"
    elif t in ("Globals.UnitTestIntValue", "Globals.UnitTestBoolValue") and e.peek(1)[1] == "=":
        e.take(); e.take("=")
        out = f"unit_test.{'int_value' if t.endswith('IntValue') else 'bool_value'} = {e.expr()}"
    elif t in ("WikiRegexes.TemplateRedirects.Clear", "WikiRegexes.RenamedTemplateParameters.Clear"):
        e.take(); e.args()
        field = "template_redirects_text" if "Redirects" in t else "renamed_template_parameters_text"
        out = f'S = set_site({field}="")'
    elif t in ("WikiRegexes.TemplateRedirects", "WikiRegexes.RenamedTemplateParameters") and e.peek(1)[1] == "=":
        # AWB-L keeps the rule page text in SiteConfig and parses it on use
        e.take(); e.take("="); e.take(); a = e.args()
        field = "template_redirects_text" if "Redirects" in t else "renamed_template_parameters_text"
        out = f"S = set_site({field}={a[0]})"
    elif t == "WikiRegexes.DatedTemplates.Clear":
        e.take(); e.args(); out = "S = set_site(dated_templates=())"
    elif t == "WikiRegexes.DatedTemplates.Add":
        e.take(); a = e.args()
        out = f"S = set_site(dated_templates=(*current_site().dated_templates, {a[0]}))"
    elif t == "Variables.MagicWords.Add":
        e.take(); a = e.args()
        out = f"S = set_site(magic_words={{**current_site().magic_words, {a[0]}: tuple({a[1]})}})"
    elif t == "Variables.MagicWords.Remove":
        e.take(); a = e.args()
        out = f"S = set_site(magic_words={{k: v for k, v in current_site().magic_words.items() if k != {a[0]}}})"
    elif t == "Variables.NamespacesCaseInsensitive.Remove":
        e.take(); e.args()
        return None  # AWB-L derives NamespacesCaseInsensitive from the namespace names; see Add
    elif t == "Variables.NamespacesCaseInsensitive.Add":
        # AWB sets the case-insensitive regex directly; AWB-L derives it from the namespace name,
        # so set the name the pattern stands for ("[Kk]ategori:" -> "Kategori:")
        e.take(); a = e.args()
        pat = eval(a[1])
        name = re.sub(r"\[(.).\]", r"\1", pat)
        name = re.sub(r"\(\?i:([^)]*)\)\\s\*", r"\1", name)
        out = (f"S = set_site(namespaces={{**current_site().namespaces, {a[0]}: {name!r}}})"
               f"  # AWB: NamespacesCaseInsensitive[...] = {pat!r}")
    elif t in ("Variables.UnderscoredTitles.Add", "Variables.UnderscoredTitles.Remove"):
        e.take(); a = e.args()
        op = "|" if t.endswith("Add") else "-"
        out = f"S = set_site(underscored_titles=current_site().underscored_titles {op} {{{a[0]}}})"
    elif t.startswith("Variables.") and e.peek(1)[1] == "=":
        e.take(); e.take("=")
        out = f"S = set_site({snake(t.split('.', 1)[1])}={e.expr()})"
    elif t == "SiteMatrix.Languages" and e.peek(1)[1] == "=":
        e.take(); e.take("=")
        out = f"S = set_site(interwiki_languages=frozenset({e.expr()}))"
    elif k == "id" and e.peek(1)[1] == "=" and e.peek(2)[1] != "=":
        e.take(); e.take("=")
        base, *members = t.split(".")
        target = ".".join([base, *(snake(m) for m in members)])  # parser.Sorter.AddCatKey
        out = f"{target} = {e.expr()}"
    elif k == "id" and (e.peek(1)[1] == "(" or "." in t):
        out = e.expr()  # expression statement, e.g. a helper call
    else:
        raise Unsupported(f"statement {toks[:4]}")
    if e.i != len(e.t): raise Unsupported(f"trailing {e.t[e.i:e.i+4]}")
    # d.TryGetValue(k, out v) used as a statement: just the assignment
    m = re.fullmatch(r"\(\((\w+) := (.*)\) is not None\)", out or "")
    if m:
        out = f"{m.group(1)} = {m.group(2)}"
    return out

def main():
    src = open(sys.argv[1], encoding="utf-8-sig", newline="").read()
    # drop preprocessor lines (#if DEBUG blocks are kept: AWB's tests run in DEBUG)
    src = re.sub(r"^\s*#(if|endif|else|region|endregion)\b.*$", "", src, flags=re.M)
    src = re.sub(r"\bWikiFunctions\.(?:Parse\.)?", "", src)
    if len(sys.argv) > 4:
        # only the named test class
        start = src.index(f"class {sys.argv[4]}")
        nxt = src.find("[TestFixture]", start)
        src = src[start: nxt if nxt > 0 else len(src)]
    toks = tokens(src)
    out = []
    # class-level constants (e.g. "const string Caption1 = ..., Caption2 = ...;" between tests)
    depth = 0
    i = 0
    consts = []
    while i < len(toks):
        t = toks[i][1]
        if t == "{": depth += 1
        elif t == "}": depth -= 1
        elif t == "const" and depth in (1, 2):  # namespace or class body
            j = i + 1
            while toks[j][1] != ";": j += 1
            try:
                py = statement(toks[i:j])
                consts.append(py)
            except Unsupported as ex:
                print("FAILED const", ex, file=sys.stderr)
            i = j
        i += 1
    if consts:
        out.append("\n".join(consts) + "\n")
    failed = []
    used = set()
    i = 0
    cls = None
    while i < len(toks):
        if toks[i][1] == "class": cls = toks[i + 1][1]
        if toks[i][1] == "[" and toks[i + 1][1] == "Test" and toks[i + 2][1] == "]":
            j = i + 3
            while toks[j][1] != "void": j += 1
            name = toks[j + 1][1]
            j += 2
            while toks[j][1] != "{": j += 1
            depth, k = 0, j
            while True:
                if toks[k][1] == "{": depth += 1
                if toks[k][1] == "}":
                    depth -= 1
                    if depth == 0: break
                k += 1
            body = toks[j + 1:k]
            # split statements at ; (depth 0)
            stmts, cur, d = [], [], 0
            for tok in body:
                if tok[1] in "([{": d += 1
                if tok[1] in ")]}": d -= 1
                if tok[1] == ";" and d == 0:
                    stmts.append(cur); cur = []
                else: cur.append(tok)
            # two fixtures in one file can have tests of the same name: qualify the later ones
            pyname = snake(name) if snake(name) not in used else f"{snake(cls)}_{snake(name)}"
            used.add(pyname)
            lines = ["S = W.for_site(EN)"]
            try:
                for st in stmts:
                    if not st: continue
                    py = statement(st)
                    if py: lines.append(py)
                fn = f"def test_{pyname}() -> None:\n" + "\n".join("    " + l for line in lines for l in line.split("\n")) + "\n"
            except Exception as ex:  # anything unexpected: this test only is not converted
                failed.append((name, f"{type(ex).__name__}: {ex}"))
                ex = Unsupported(f"{type(ex).__name__}: {ex}")
                fn = (f"@pytest.mark.skip(reason={('not converted: ' + str(ex))[:90]!r})\n"
                      f"def test_{pyname}() -> None:\n    pass\n")
            out.append(fn)
            i = k
        i += 1
    sys.stdout.write("\n\n".join(out))
    for f in failed: print("FAILED", *f, file=sys.stderr)

main()
