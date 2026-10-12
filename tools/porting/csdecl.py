"""Tokenise C# static field declarations from WikiRegexes.cs (one-off porting aid)."""
import re, sys

TOKEN = re.compile(r'''
  (?P<istr>\$@?"(?:[^"\\]|\\.|"")*")
 |(?P<vstr>@"(?:[^"]|"")*")
 |(?P<str>"(?:[^"\\]|\\.)*")
 |(?P<chr>'(?:[^'\\]|\\.)')
 |(?P<num>\d+)
 |(?P<id>@?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
 |(?P<ws>\s+|//[^\n]*|/\*.*?\*/)
 |(?P<p>\[\]|[^\sA-Za-z0-9_"@'])
''', re.X | re.S)

def tokens(s):
    i = 0
    out = []
    while i < len(s):
        m = TOKEN.match(s, i)
        if not m: raise SyntaxError(s[i:i+40])
        if m.lastgroup != "ws": out.append((m.lastgroup, m.group()))
        i = m.end()
    return out

def strval(kind, text):
    if kind == "vstr": return text[2:-1].replace('""', '"')
    body = text[1:-1]
    return re.sub(r'\\(u[0-9a-fA-F]{4}|.)', lambda m: {'n':'\n','r':'\r','t':'\t','\\':'\\','"':'"',"'":"'",'0':'\0'}.get(m.group(1)) or chr(int(m.group(1)[1:],16)), body)

def declarations(src):
    """Yield (modifiers+type, name, rhs tokens) for class-level field declarations."""
    toks = tokens(src)
    i = 0
    while i < len(toks):
        k, t = toks[i]
        if t in ("public", "private", "internal") and i + 1 < len(toks):
            j = i
            mods = []
            while toks[j][1] in ("public","private","internal","static","readonly","const"):
                mods.append(toks[j][1]); j += 1
            # type tokens until NAME followed by = or ;
            start = j
            depth = 0
            while j < len(toks) and not (toks[j][0]=="id" and depth==0 and toks[j+1][1] in ("=",";","(")):
                if toks[j][1] == "<": depth += 1
                if toks[j][1] == ">": depth -= 1
                j += 1
            typ = " ".join(t for _, t in toks[start:j])
            name = toks[j][1]
            if toks[j+1][1] == "(":   # method: skip
                i = j + 1; continue
            if toks[j+1][1] == ";":
                yield mods, typ, name, []
                i = j + 2; continue
            # rhs until ; at depth 0
            k2 = j + 2; depth = 0
            while not (toks[k2][1] == ";" and depth == 0):
                if toks[k2][1] in "({[": depth += 1
                if toks[k2][1] in ")}]": depth -= 1
                k2 += 1
            yield mods, typ, name, toks[j+2:k2]
            i = k2 + 1
        else:
            i += 1

if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8-sig", newline="").read()
    # only class body after the methods we port by hand: keep everything, filter later
    import collections
    shapes = collections.Counter()
    for mods, typ, name, rhs in declarations(src):
        if "static" not in mods and "const" not in mods: continue
        shape = " ".join(t if k in ("p","id") else k for k, t in rhs)
        shape = re.sub(r"(str|vstr)( \+ (str|vstr))*", "S", shape)
        shapes[(typ, shape[:120])] += 1
    for (typ, shape), n in shapes.most_common():
        print(n, typ, "=", shape)
