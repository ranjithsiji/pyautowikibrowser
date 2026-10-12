# AWB-L: cross-platform AutoWikiBrowser

A rewrite of AutoWikiBrowser (AWB), the semi-automated MediaWiki editor, for Linux, macOS and
Windows, usable on all ~360 Wikipedia languages including RTL (Arabic, Hebrew, Persian), Indic
(Malayalam, Hindi) and CJK scripts. The original is .NET Framework 4.8.1 + Windows Forms.

## Stack decision: Python + PySide6 + `regex` (decided 2026-10-12, do not change without discussion)

Chosen after measuring Python, Rust, PCRE2 (Qt C++) and JavaScript against AWB's real rules.
.NET was excluded by the project owner. Raw results are summarised here; the scripts were throwaway.

| Engine | AWB core regexes compile (/632) | enwiki typo rules compile (/4274) | Unicode cases correct (/36) | Typo pass, 391 KB page |
|---|---|---|---|---|
| Python `regex` | 602 | 4274 | 36 | 3.2 s |
| Rust `fancy-regex` | 617, but balancing groups silently wrong | 4243; 58 abort on backtrack limit | 35 | 53-60 s |
| PCRE2 (Qt / Rust `pcre2`) | 553 raw, 598 translated | 3947 raw, 4273 with capped lookbehind | 29 | 1.6 s |
| JavaScript V8 (wAwB, Tauri) | 493 | 4250 | ~19 (`\w`/`\d` are ASCII-only) | 1.0 s |
| .NET (AWB today, reference only) | 632 | 4274 | 26 | 0.6 s |

Why Python wins:
- Only engine that runs every community typo rule unchanged, including unbounded lookbehind.
- Most correct Unicode: `\w`/`\b` keep Malayalam and Hindi words whole (vowel signs, virama,
  chillu with ZWJ), keep Persian ZWNJ words whole, treat astral CJK/emoji as one character,
  match Arabic-Indic / Malayalam / fullwidth digits. .NET and PCRE2 split Malayalam words.
- Speed is acceptable: cost scales with page size, and typical articles are a small fraction of
  391 KB. Python's slow cases are concentrated in a few patterns meant for short strings.
- pywikibot (MIT) already provides login (bot password, OAuth), throttling, `maxlag`, and
  49 page generators. Qt gives mature bidi, complex-script shaping and IME on all three OSes.

## Reference code (read-only)

| Path | What | Use it for |
|---|---|---|
| `/home/alphad13/Projects/autowikibrowser-code-r13044/` | Whole AWB SVN checkout (r13044, v6.5.0.1) | See breakdown below |
| `.../AWB/` (trunk) | `AWB/` app, `WikiFunctions/` engine, `UnitTests/`, `Plugins/`, `Extras/` | Behaviour, rules, tests: the main reference |
| `.../AWB/Plugins/` | CFD, IFD, Delinker, Kingbotk, TypoScan, ... | Plugin API needs and later ports |
| `.../AWB/Extras/` | DBScanner, Regex Tester, CheckPage Converter, packager | Later tools |
| `.../TypoScan/`, `.../UsageStats/`, `.../Web/` | PHP server side, project website | Server protocols only; not ported |
| `.../tags/`, `.../branches/` | Old releases | Ignore |
| `/home/alphad13/Projects/huggle3-qt-lx` | Huggle 3 (Qt C++, GPL-3.0) | Qt desktop patterns, packaging for 3 OSes |
| wAwB gadget (`en.wikipedia.org/wiki/User:Ponor/wAwB`, JS, GPL) | In-browser AWB-like tool | Server-side diff/preview, protected regions, timed rule runs |

Key AWB sources: `WikiFunctions/Parse/*` (general fixes, ~15k lines), `WikiFunctions/WikiRegexes.cs`,
`WikiFunctions/Tools.cs`, `WikiFunctions/API/*`, `WikiFunctions/Lists/Providers/*`, `UnitTests/*` (~27k lines).

## Target stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+, fully type-annotated, `pyright` strict on `core/` |
| Env and deps | `uv` (`pyproject.toml`, `uv.lock`) |
| UI | PySide6 (Qt 6 Widgets, LGPL). Not QML |
| Look and feel | Fusion style forced on every OS + one QSS stylesheet with light/dark colour tokens (`awb_l.ui.theme`, `ui/styles/app.qss`). No per-widget inline styles; QSS rules stay direction-neutral for RTL. Fonts stay OS-provided for script coverage |
| Regex | `regex` module only, through `awb_l.core.rx`. Never import `re` for rule matching |
| Wiki API | pywikibot behind a thin `awb_l.api` wrapper, configured in code (no `user-config.py`) |
| Diff and preview | MediaWiki `action=compare` (`totext-main`) and `action=parse`, shown in `QWebEngineView` (the wAwB approach). Local `difflib` fallback when offline |
| Wikitext editor | `QPlainTextEdit` + `QSyntaxHighlighter`. Avoid QScintilla: its bidi support is weak |
| Custom modules | Python functions `(text, title, vars) -> text`, run in a worker with a timeout |
| Plugins | Python entry points (`awb_l.plugins` group) with a typed hook API |
| Settings | TOML/JSON project files; importer for old AWB settings XML |
| Credentials | `keyring` (OS keychain) |
| Tests | `pytest`, `pytest-qt`; ported AWB tests are the parity suite |
| Lint/format | `ruff` |
| Packaging | PyInstaller per OS in CI; Flatpak for Linux later |
| Licence | GPL-3.0-or-later (AWB is GPL-2.0-or-later, Huggle GPL-3.0) |

## Layout

```
pyproject.toml
src/awb_l/
  core/
    rx.py            # compile/cache/run regexes; timeouts; .NET->regex translation
    dotnet_regex.py  # translator for user rules and typo lists
    protect.py       # hide/restore comments, nowiki, templates, refs (AWB HideText, wAwB protection)
    parsers/         # port of WikiFunctions/Parse/*
    site.py          # SiteConfig: per-wiki namespaces, magic words, months (regex half of Variables.cs)
    wikiregexes.py   # port of WikiRegexes.cs: static names at module level, per-wiki on SiteRegexes
    tools.py         # port of Tools.cs (grows as callers are ported)
    article.py       # one page's processing pipeline
  api/               # pywikibot wrapper: session, CheckPage, scheduler, edit/save
  lists/             # list providers (wrap pywikibot pagegenerators)
  rules/             # find & replace, typo lists, skip conditions
  scripting/         # custom Python modules, sandbox-ish runner with timeout
  plugins/           # plugin API and loader
  ui/                # PySide6 windows, views, models (no business logic)
tests/
  core/  api/  ui/  parity/
```

`core/` must never import PySide6 or pywikibot. `ui/` must never contain regex or wikitext logic.

## Rules that matter

1. **Regex parity via translation, not rewrites.** Copy AWB patterns byte-for-byte into `wikiregexes.py`,
   then let `dotnet_regex.py` translate: `\k<name>` -> `(?P=name)`; `\p{IsBlock}` -> `\p{Block=...}`;
   `RegexOptions.ExplicitCapture` -> make unnamed groups non-capturing; `RightToLeft` -> `regex.REVERSE`;
   `\uXXXX` handled natively. Use `regex` VERSION0 semantics. Balancing groups: all 39 uses in AWB are one
   idiom, `(?>OTHER|OPEN(?<D>)|CLOSE(?<-D>))*(?(D)(?!))`, which the translator turns into an equivalent
   recursive group (tested per variant in `tests/core/test_dotnet_regex.py`). Any other balancing-group
   use is rejected and must be rewritten by hand, with a test. (Changed 2026-10-12 from "rewrite all by hand".)
   .NET group numbering (unnamed first, then named) is preserved via `TranslatedPattern.group_map`.
2. **Every rule runs with a timeout** (`regex` supports `timeout=`). A timed-out rule is skipped and
   reported, never allowed to hang the UI. Run processing off the UI thread.
3. **Unicode is a feature.** Do not "fix" Python's Unicode behaviour back to .NET's. Where an AWB test
   encodes .NET's split-Indic-word or UTF-16 surrogate behaviour, change the expectation and say why in the test.
   Keep a multilingual test set: Arabic (harakat, tatweel, RLM), Persian ZWNJ, Malayalam (Mc signs,
   atomic and ZWJ chillu), Hindi, Chinese (astral Ext-B), Japanese (kana, `ー`, fullwidth), Turkish `İ`, Greek `ς`.
4. **RTL everywhere.** Take direction from siteinfo (`rtl`) per wiki; set the editor and preview direction
   from it. Never assume LTR. Test UI with Arabic and Hebrew wikis.
5. **Behaviour parity first.** Port a C# class together with its NUnit tests; get tests green before refactoring.
6. **Keep the CheckPage gate.** Read `Project:AutoWikiBrowser/CheckPageJSON`; refuse to save for unapproved
   users; keep version checks. Do not copy wAwB's "allow if >500 edits when no CheckPage" fallback without discussion.
7. **Be a polite API client.** Descriptive `User-Agent`, `maxlag`, `assert=user`, `baserevid` on save,
   respect throttles. All calls go through `awb_l.api`.
8. **Protected regions.** Hide comments/nowiki/math/pre/etc. before rules run and restore after, using
   Private Use Area placeholders (as AWB and wAwB do). Verify placeholders never survive into saved text.
9. Keep GPL headers and credit original authors in ported files.

## Porting conventions

- Ported code uses `rx.DotNetRegex`, a .NET-like API: `is_match`, `match`, `matches`, `replace` (with a .NET
  replacement string or an evaluator taking `DotNetMatch`), `split`. `match()` never returns None: a failed
  match is falsy with `value == ""` and empty groups, as in .NET. `m.group(n)` uses .NET group numbers.
  `regex + "text"` concatenates the pattern, as C# does.
- Keep AWB's names (`WikiRegexes.SimpleWikiLink` -> `wikiregexes.SimpleWikiLink`) so C# and Python can be
  read side by side. Static AWB fields are module-level; anything AWB rebuilds per wiki
  (`MakeLangSpecificRegexes` etc.) lives on `SiteRegexes`, obtained with `wikiregexes.for_site(site)`.
- No global mutable state: AWB's `Variables` becomes an immutable `SiteConfig` passed explicitly.
- Mechanical conversion helpers live in `tools/porting/` (C# declarations -> Python, NUnit -> pytest). Their
  output is committed and then edited by hand. AWB sources are CRLF; multi-line test strings keep `\r\n`.
- Ported test files keep every AWB assertion. Where an expectation changes on purpose (rule 3), add a comment.

## Commands

```
uv sync
uv run pytest                       # all tests
uv run pytest tests/core -k parsers # one area
uv run ruff check . && uv run ruff format .
uv run pyright
uv run awb-l                        # launch the app
```

Run tests and pyright before calling any task done.

## Roadmap

1. Done: skeleton, package layout, CI on ubuntu/macos/windows.
2. Done: `core/rx.py` + `dotnet_regex.py` + multilingual Unicode tests; all enwiki typo rules compile.
3. Port `WikiRegexes` (done: `RegexTests.cs` passes unchanged), `Tools` (started), then `Parse/*` with their tests.
4. `api/`: login, CheckPage, siteinfo, fetch/save, scheduler; `lists/` via pagegenerators.
5. UI MVP: list maker, editor, server diff/preview, skip/save loop, find & replace, typo fixing, general fixes.
6. Settings import, custom Python modules, plugins.
7. Packaging, auto-update, translatewiki.net integration.
