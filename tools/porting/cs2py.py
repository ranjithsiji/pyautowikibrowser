"""Convert static field declarations of WikiRegexes.cs to Python (one-off porting aid)."""
import re, sys
sys.path.insert(0, sys.argv[2])
from csdecl import declarations, strval

OPTS = {"IgnoreCase": "IGNORE_CASE", "Multiline": "MULTILINE", "Singleline": "SINGLELINE",
        "ExplicitCapture": "EXPLICIT_CAPTURE", "RightToLeft": "RIGHT_TO_LEFT", "Compiled": "COMPILED",
        "IgnorePatternWhitespace": "IGNORE_PATTERN_WHITESPACE", "CultureInvariant": "CULTURE_INVARIANT"}

def pylit(s):
    if "\n" not in s and "\r" not in s and not s.endswith("\\") and "\0" not in s:
        if '"' not in s: return 'r"' + s + '"'
        if "'" not in s: return "r'" + s + "'"
    return repr(s)

class P:
    def __init__(self, toks, types, names):
        self.t, self.i, self.types, self.names = toks, 0, types, names
    def peek(self, o=0):
        j = self.i + o
        return self.t[j] if j < len(self.t) else ("eof", "")
    def take(self, text=None):
        k, t = self.t[self.i]
        if text is not None and t != text: raise SyntaxError(f"expected {text!r} got {t!r} at {self.t[self.i:self.i+5]}")
        self.i += 1
        return k, t
    # returns (python_text, type) ; type in str|regex|list|bool
    def expr(self):
        parts = [self.term()]
        while self.peek()[1] == "+":
            self.take("+"); parts.append(self.term())
        if len(parts) == 1: return parts[0]
        # merge adjacent string literals
        out = []
        for code, typ in parts:
            out.append(f"str({code})" if typ == "regex" else code)
        return " + ".join(out), "str"
    def postfix(self, code, typ):
        while self.peek()[1] == "." :
            self.take("."); _, meth = self.take()
            self.take("(")
            args = []
            while self.peek()[1] != ")":
                args.append(self.expr())
                if self.peek()[1] == ",": self.take(",")
            self.take(")")
            if meth == "ToList": continue
            if meth == "Union": code, typ = f"_union({code}, {args[0][0]})", "list"
            elif meth == "Replace": code = f"{code}.replace({args[0][0]}, {args[1][0]})"
            elif meth == "ToString": code, typ = f"str({code})", "str"
            else: raise SyntaxError("method " + meth)
        return code, typ
    def strlist(self):
        self.take("{"); items = []
        while self.peek()[1] != "}":
            items.append(self.expr()[0])
            if self.peek()[1] == ",": self.take(",")
        self.take("}")
        return "(" + ", ".join(items) + ("," if len(items) == 1 else "") + ")", "list"
    def term(self):
        k, t = self.peek()
        if k in ("str", "vstr"):
            self.take(); return pylit(strval(k, t)), "str"
        if t == "(":
            self.take("("); r = self.expr(); self.take(")"); return self.postfix(*r)
        if t == "{":
            return self.strlist()
        if t == "new":
            self.take()
            _, what = self.take()
            if what == "[]" or what == "[":
                if what == "[": self.take("]")
                return self.postfix(*self.strlist())
            if what == "string":
                self.take("["); self.take("]"); return self.postfix(*self.strlist())
            if what == "List":
                self.take("<"); self.take(); self.take(">"); self.take("(")
                if self.peek()[1] == ")": self.take(")"); return "()", "list"
                r = self.expr(); self.take(")"); return self.postfix(*r)
            if what == "Regex":
                self.take("(")
                pat = self.expr()
                opts = []
                if self.peek()[1] == ",":
                    self.take(",")
                    while True:
                        _, o = self.take(); opts.append("O." + OPTS[o.split(".")[1]])
                        if self.peek()[1] != "|": break
                        self.take("|")
                self.take(")")
                pc = f"str({pat[0]})" if pat[1] == "regex" else pat[0]
                return self.postfix(f"_R({pc}" + (", " + " | ".join(opts) if opts else "") + ")", "regex")
            if what == "Dictionary" or what == "HashSet":
                raise SyntaxError("dict")
            raise SyntaxError("new " + what)
        if t == "Tools.NestedTemplateRegex":
            self.take(); self.take("(")
            arg = self.expr()
            if self.peek()[1] == ",": self.take(","); self.take()
            self.take(")")
            return self.postfix(f"nested_template_regex({arg[0]})", "regex")
        if k == "id":
            self.take()
            if t in ("true", "false"): return t.capitalize(), "bool"
            head, _, meth = t.rpartition(".")
            if head and meth in ("Union", "ToList", "Replace", "ToString"):
                self.i -= 1
                self.t = self.t[:self.i] + [("id", head), ("p", "."), ("id", meth)] + self.t[self.i + 1:]
                self.take()
                t = head
            return self.postfix(self.names.get(t, t), self.types.get(t, "str"))
        raise SyntaxError(f"term {t!r}")

def summaries(src):
    """name -> summary text from the /// <summary> block right above its declaration."""
    out = {}
    lines = src.splitlines()
    for n, line in enumerate(lines):
        m = re.match(r"\s*(?:public|private|internal)\s+(?:static\s+|readonly\s+|const\s+)+[\w<>\[\], ]+?\s(\w+)\s*(?:=|;)", line)
        if not m: continue
        doc = []
        j = n - 1
        while j >= 0 and lines[j].strip().startswith("//"):
            doc.insert(0, lines[j].strip()); j -= 1
        text = " ".join(re.sub(r"^///?\s?", "", d) for d in doc)
        text = re.sub(r"</?summary>|<para>|</para>|<remarks>|</remarks>", " ", text)
        text = re.sub(r"<see cref=\"([^\"]+)\"\s*/>", r"\1", text)
        out[m.group(1)] = " ".join(text.split())
    return out

def main():
    src = open(sys.argv[1], encoding="utf-8-sig", newline="").read()
    docs = summaries(src)
    types = {}
    names = {}
    out, skipped = [], []
    RUNTIME = {"DatedTemplates", "RenamedTemplateParameters", "TemplateRedirects"}
    for mods, typ, name, rhs in declarations(src):
        if "static" not in mods and "const" not in mods: continue
        if not rhs or name in RUNTIME:
            skipped.append((name, typ, "no initializer / runtime data")); continue
        types[name] = "regex" if typ == "Regex" else "list" if ("List" in typ or "[]" in typ) else "str"
        try:
            p = P(rhs, types, names)
            code, _ = p.expr()
            if p.i != len(p.t): raise SyntaxError("trailing " + str(p.t[p.i:p.i+4]))
        except (SyntaxError, KeyError) as e:
            skipped.append((name, typ, str(e)[:80])); continue
        private = "private" in mods
        pyname = ("_" + name) if private else name
        names[name] = pyname
        doc = docs.get(name, "")
        block = ""
        if doc:
            import textwrap
            block = "\n".join("# " + l for l in textwrap.wrap(doc, 96)) + "\n"
        out.append(f"{block}{pyname} = {code}\n")
    sys.stdout.write("\n".join(out))
    for s in skipped: print("SKIPPED", *s, file=sys.stderr)

if __name__ == "__main__":
    main()
