# Porting aids (not shipped)

Throwaway-quality scripts that convert AWB C# to Python. Their output is a starting point that is
then committed and edited by hand; re-running them over hand-edited files would lose those edits.

| Script | Converts |
|---|---|
| `csdecl.py` | Tokenises C# and yields static field declarations (shared by the others) |
| `cs2py.py` | `static readonly Regex/string/List` declarations to Python (used for `core/wikiregexes.py`) |
| `nunit2py.py` | NUnit test methods to pytest functions (used for `tests/parity/test_regex_tests.py`) |

Both read the C# with `newline=""`: AWB's sources are CRLF, and multi-line verbatim strings in tests
must keep `\r\n`.

```
python3 -I tools/porting/cs2py.py <AWB>/WikiFunctions/WikiRegexes.cs tools/porting > out.py
uv run python -c '<dump names json>' > names.json   # see nunit2py.py docstring
python3 -I tools/porting/nunit2py.py <AWB>/UnitTests/RegexTests.cs tools/porting names.json > tests.py
```
