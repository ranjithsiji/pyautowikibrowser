# Porting aids (not shipped)

Throwaway-quality scripts that convert AWB C# to Python. Their output is a starting point that is
then committed and edited by hand; re-running them over hand-edited files would lose those edits.

| Script | Converts |
|---|---|
| `csdecl.py` | Tokenises C# and yields static field declarations (shared by the others) |
| `cs2py.py` | `static readonly Regex/string/List` declarations to Python (used for `core/wikiregexes.py`) |
| `nunit2py.py` | NUnit test methods to pytest functions (used for `tests/parity/test_regex_tests.py`) |
| `wikieditor_data.py` | WikiEditor/core toolbar messages, language fallbacks, special characters (re-runnable) |
| `codex_data.py` | Codex icons and design tokens from the Codex source (no npm build) to `src/pyawb/icons/` and `src/pyawb/ui/styles/codex-tokens.json` (re-runnable) |

Both read the C# with `newline=""`: AWB's sources are CRLF, and multi-line verbatim strings in tests
must keep `\r\n`.

```
python3 -I tools/porting/cs2py.py <AWB>/WikiFunctions/WikiRegexes.cs tools/porting > out.py
uv run python -c '<dump names json>' > names.json   # see nunit2py.py docstring
python3 -I tools/porting/nunit2py.py <AWB>/UnitTests/RegexTests.cs tools/porting names.json > tests.py
```

`nunit2py.py` maps AWB's C# idioms onto PyAutoWikiBrowser's conventions: `out`/`ref` arguments become tuple
returns (`with_outs`, `with_refs`), overloads with `out bool noChange` become `foo_no_change()`
(`NO_CHANGE_OVERLOADS`), and changes to AWB's global `Variables`/`WikiRegexes` state become
`set_site`/`set_lang`/`set_project` calls. A test it cannot convert is emitted as a skipped stub with
the reason, so it can be ported by hand.

```
python3 -I tools/porting/wikieditor_data.py <WikiEditor> <mediawiki core> src/pyawb/editor/data/wikieditor
python3 -I tools/porting/codex_data.py <design-codex> src/pyawb
```
