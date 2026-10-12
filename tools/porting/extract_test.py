"""Print the C# source of named methods. usage: extract_test.py file.cs Name...

Brace matching skips string/char literals and comments, so "{{foo}" in a test string is fine.
"""
import sys

src = open(sys.argv[1], encoding="utf-8-sig", newline="").read()


def method_end(s: str, j: int) -> int:
    depth, k, n = 0, j, len(s)
    while k < n:
        c = s[k]
        if s.startswith('@"', k):
            k += 2
            while k < n and not (s[k] == '"' and s[k + 1 : k + 2] != '"'):
                k += 2 if s[k] == '"' else 1
        elif c == '"':
            k += 1
            while s[k] != '"':
                k += 2 if s[k] == "\\" else 1
        elif c == "'" :
            k += 1
            while s[k] != "'":
                k += 2 if s[k] == "\\" else 1
        elif s.startswith("//", k):
            k = s.index("\n", k)
        elif s.startswith("/*", k):
            k = s.index("*/", k) + 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return k
        k += 1
    raise ValueError("unbalanced")


for name in sys.argv[2:]:
    i = src.find(f" {name}(")
    if i < 0:
        print(f"// {name}: not found")
        continue
    start = src.rfind("\n", 0, i) + 1
    k = method_end(src, src.index("{", i))
    print(src[start : k + 1].replace("\r\n", "\n"))
    print()
