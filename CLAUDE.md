# PyAutoWikiBrowser (PyAWB): cross-platform AutoWikiBrowser

A rewrite of AutoWikiBrowser (AWB), the semi-automated MediaWiki editor, for Linux, macOS and
Windows, usable on all ~360 Wikipedia languages including RTL (Arabic, Hebrew, Persian), Indic
(Malayalam, Hindi) and CJK scripts. The original is .NET Framework 4.8.1 + Windows Forms.
Named PyAutoWikiBrowser (PyAWB, package `pyawb`) since 2026-10-13, reviving the name of a 2009 Python AWB
(https://en.wikipedia.org/wiki/Wikipedia:PyAutoWikiBrowser, also the User-Agent contact). Earlier names: AWB-L
(`awb_l`), then briefly AWB-X (`awb_x`).

## Stack decision: Python + PySide6 + `regex` (decided 2026-10-12, do not change without discussion)

Editor decided the same day, after weighing a full HTML UI (pywebview, Qt WebEngine), Rust/Tauri again (Tauri
uses Chromium/WebView2 on Windows and cannot use Gecko; Gecko cannot be embedded at all) and CodeMirror 6:
Chromium has real display bugs with some complex scripts, so the editor and diff use Qt's own text engine.
Qt-native `QPlainTextEdit` editor with a toolbar built from WikiEditor's layout and translations; wikitext
highlighting by a Python tokenizer (CodeMirror's MediaWiki mode as reference for token rules); native diff.
Things that need a full browser engine (Parsoid preview, the wiki's VisualEditor) open in the user's default
browser (Firefox where installed). An embedded Qt WebEngine (Chromium) preview is an optional setting only.

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

Paths are relative to this repository: the reference checkouts sit next to it in the same parent folder.

| Path | What | Use it for |
|---|---|---|
| `../autowikibrowser-code-r13044/` | Whole AWB SVN checkout (r13044, v6.5.0.1) | See breakdown below |
| `.../AWB/` (trunk) | `AWB/` app, `WikiFunctions/` engine, `UnitTests/`, `Plugins/`, `Extras/` | Behaviour, rules, tests: the main reference |
| `.../AWB/Plugins/` | CFD, IFD, Delinker, Kingbotk, TypoScan, ... | Plugin API needs and later ports |
| `.../AWB/Extras/` | DBScanner, Regex Tester, CheckPage Converter, packager | Later tools |
| `.../TypoScan/`, `.../UsageStats/`, `.../Web/` | PHP server side, project website | Server protocols only; not ported |
| `.../tags/`, `.../branches/` | Old releases | Ignore |
| `../mediawiki-extensions-WikiEditor` | MediaWiki WikiEditor (JS, GPL-2.0-or-later, 2026-10) | Editor toolbar: layout and `encapsulate` actions (`modules/jquery.wikiEditor.toolbar.config.js`), dialogs, translations in 273 languages (`i18n/`) |
| `../codemirror-mediawiki` | `@bhsd/codemirror-mediawiki` 4.7.1 (TS, GPL-2.0-or-later, 2026-10) | Highlighter: port the line-by-line stream tokenizer `src/token.ts` to a `QSyntaxHighlighter` (per-block state); its tests in `test/src/`. `mw/textSelection.ts` for `encapsulateSelection`; `matchBrackets`/`matchTag`/`fold`/`bidi` for later editor features |
| `/var/www/html/mediawiki` | MediaWiki core 1.45.3 (local install, GPL-2.0-or-later) | `jquery.textSelection` and its QUnit tests, special characters, core i18n and language fallbacks |
| `../design-codex` | Wikimedia Codex 2.7.0 source (2026-09-30; tokens GPL-2.0+, icons MIT / designs CC BY 4.0) | Icons (`packages/codex-icons/src`) and design tokens (`packages/codex-design-tokens/src`), converted by `tools/porting/codex_data.py`; component styles (`packages/codex/src/components/*/*.vue` `<style>`) as the reference for `ui/styles/app.qss` |
| `../wikidiff2` | wikidiff2 (Tim Starling, C++, 2006; SWIG Python wrapper used by a 2009 Python AWB) | Native diff (step 5): MediaWiki's word-level diff with character-level diff for Han, Japanese and Thai; `DiffEngine.h` algorithm; `test/test-a*`, `test-b*` expected outputs |
| `../huggle3-qt-lx` | Huggle 3 (Qt C++, GPL-3.0) | Qt desktop patterns, packaging for 3 OSes |
| wAwB gadget (`en.wikipedia.org/wiki/User:Ponor/wAwB`, JS, GPL) | In-browser AWB-like tool | Server-side diff/preview, protected regions, timed rule runs |

Key AWB sources: `WikiFunctions/Parse/*` (general fixes, ~15k lines), `WikiFunctions/WikiRegexes.cs`,
`WikiFunctions/Tools.cs`, `WikiFunctions/API/*`, `WikiFunctions/Lists/Providers/*`, `UnitTests/*` (~27k lines).

## Target stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+, fully type-annotated, `pyright` strict on `core/` |
| Env and deps | `uv` (`pyproject.toml`, `uv.lock`) |
| UI | PySide6 (Qt 6 Widgets, LGPL) for lists, toolbars, menus, options, dialogs. Not QML |
| Look and feel | Wikimedia Codex look: Fusion style forced on every OS + one QSS stylesheet (`ui/styles/app.qss`) styled after Codex components and filled from Codex design tokens, light and dark (`ui/styles/codex-tokens.json`, `pyawb.ui.theme`; decided 2026-10-13). Rules stay direction-neutral for RTL. Fonts stay OS-provided for script coverage |
| Icons | Codex icons only (`pyawb.icons`, `@wikimedia/codex-icons`, the successor of OOUI's icons; `ui.icons.codex_icon`), never the OS icon theme: same look on every OS, per-language variants (bold B/F/ض...) and RTL mirroring |
| Wikitext editor | `QPlainTextEdit` + `QSyntaxHighlighter` fed by a Python wikitext tokenizer ported from codemirror-mediawiki's `src/token.ts` (pure, tested, outside `ui/`). Avoid QScintilla (weak bidi) and browser editors (Chromium complex-script bugs). Editor actions are Python functions over (text, selection) with unit tests; Qt only passes selection in and out |
| Editor toolbar | `editor/toolbar.py` hand-ports WikiEditor's toolbar config (sections, groups, tools, `encapsulate` actions, help pages); special characters from MediaWiki core; labels from WikiEditor's and core's i18n with MediaWiki language fallbacks (`editor/messages.py`); `encapsulate` ported from core's `jquery.textSelection` (`editor/textselection.py`); Qt widget `ui/editor_toolbar.py`. Data copied by `tools/porting/wikieditor_data.py` |
| Visual editing | "Visual" button opens the wiki's own VisualEditor (`?veaction=edit`) in the default browser. No embedded VisualEditor, no tiptap/ProseMirror (cannot round-trip wikitext) |
| Regex | `regex` module only, through `pyawb.core.rx`. Never import `re` for rule matching |
| Wiki API | pywikibot behind a thin `pyawb.api` wrapper, configured in code (no `user-config.py`) |
| Diff and preview | Diff in native Qt widgets (word-level, from `difflib` or `action=compare`). Parsoid/`action=parse` preview opens in the default browser; optional embedded `QWebEngineView` preview as a setting |
| Custom modules | Python functions `(text, title, vars) -> text`, run in a worker with a timeout |
| Plugins | Python entry points (`pyawb.plugins` group) with a typed hook API |
| Settings | User config `config.toml` in the OS config dir (`pyawb.paths`, `settings/appconfig.py`): login profiles (wiki, login name), User-Agent contact. Project/rule settings as TOML/JSON files later; importer for old AWB settings XML |
| Credentials | `keyring` (OS keychain, `api/credentials.py`); never written to `config.toml` (the parser rejects a `password` key) |
| Tests | `pytest`, `pytest-qt`; ported AWB tests are the parity suite |
| Lint/format | `ruff` |
| Packaging | PyInstaller per OS in CI; Flatpak for Linux later |
| Licence | GPL-3.0-or-later (AWB is GPL-2.0-or-later, Huggle GPL-3.0) |

## Layout

```
pyproject.toml
src/pyawb/
  core/
    rx.py            # compile/cache/run regexes; timeouts; .NET->regex translation
    dotnet_regex.py  # translator for user rules and typo lists
    protect.py       # hide/restore comments, nowiki, templates, refs (AWB HideText, wAwB protection)
    parsers/         # port of WikiFunctions/Parse/*
    site.py          # SiteConfig (regex half of Variables.cs) + current_site()/use_site()
    textutil.py      # low-level Tools.cs helpers (case, URL encoding, template regex builders)
    namespace.py     # port of Namespace.cs
    wikiregexes.py   # port of WikiRegexes.cs: static names at module level, per-wiki on SiteRegexes
    tools.py         # port of Tools.cs (minus HTTP/UI/file helpers)
    article.py       # one page's processing pipeline
  api/               # pywikibot wrapper: transport, session, CheckPage, siteinfo, Wikidata, cache
  lists/             # page list model, AWB list providers, pywikibot pagegenerators
  rules/             # find & replace, typo lists, skip conditions
  editor/            # editor logic without Qt: tokenizer.py (port of codemirror-mediawiki token.ts),
                     #   mwconfig.py (per-wiki config from siteinfo), highlight_style.py (theme as data),
                     #   textselection.py (encapsulate), toolbar.py (WikiEditor toolbar), messages.py (i18n),
                     #   dialogs.py (WikiEditor's link/file/table/search-and-replace dialogs)
  icons/             # Codex icon set (codex-icons.json) and variant lookup
  scripting/         # custom Python modules, sandbox-ish runner with timeout
  settings/          # config.toml profiles; later AWB settings import
  paths.py           # per-OS config and data directories (PYAWB_HOME overrides)
  plugins/           # plugin API and loader
  ui/                # PySide6 windows, views, models (no business logic)
tests/
  core/  api/  ui/  parity/  settings/  editor/
docs/wiki/           # pages to publish on Wikipedia (the User-Agent contact page)
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
   respect throttles. All calls go through `pyawb.api`.
8. **Protected regions.** Hide comments/nowiki/math/pre/etc. before rules run and restore after, with
   `core.parsers.hidetext.HideText`. Placeholders are AWB's exact `⌊⌊⌊⌊n⌋⌋⌋⌋` / `⌊⌊⌊⌊Mn⌋⌋⌋⌋` markers, because
   ported WikiRegexes patterns match them. Verify placeholders never survive into saved text.
9. Keep GPL headers and credit original authors in ported files.

## Porting conventions

- Ported code uses `rx.DotNetRegex`, a .NET-like API: `is_match`, `match`, `matches`, `replace` (with a .NET
  replacement string or an evaluator taking `DotNetMatch`), `split`. `match()` never returns None: a failed
  match is falsy with `value == ""` and empty groups, as in .NET. `m.group(n)` uses .NET group numbers.
  `regex + "text"` concatenates the pattern, as C# does.
- Keep AWB's names (`WikiRegexes.SimpleWikiLink` -> `wikiregexes.SimpleWikiLink`) so C# and Python can be
  read side by side. Static AWB fields are module-level; anything AWB rebuilds per wiki
  (`MakeLangSpecificRegexes` etc.) lives on `SiteRegexes`, obtained with `wikiregexes.for_site(site)`.
- AWB's global `Variables` becomes an immutable `SiteConfig`. Ported code reads the wiki from
  `site.current_site()` (a `ContextVar`, English Wikipedia by default); `with use_site(cfg):` sets it for a
  block, `set_current_site()` for a worker. Never mutate a `SiteConfig`; build a new one with `replace()`.
- C# overloads become optional parameters, or one function that dispatches on argument types where AWB's
  overloads differ in meaning (see `tools.rename_template`, `tools.remove_template_parameter`). `ref`/`out`
  parameters become return values. Document each such mapping in the docstring.
- Watch C#/Python semantic differences when porting by hand: `%` truncates in C# (`-1 % 2 == -1`),
  `char.ToUpper` is one char in/one out (`textutil.char_upper`), `char.IsLetterOrDigit` is not `str.isalnum`
  (`textutil.is_letter_or_digit`), `HttpUtility.UrlEncode` uses lower-case hex and `+` for spaces
  (`textutil.url_encode`). Regex.Replace replacement strings interpret `$`: escape literal values (`$$`).
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
uv run pyawb                        # launch the app
```

Run tests and pyright before calling any task done.

## Roadmap

1. Done: skeleton, package layout, CI on ubuntu/macos/windows.
2. Done: `core/rx.py` + `dotnet_regex.py` + multilingual Unicode tests; all enwiki typo rules compile.
3. Done: `WikiRegexes`, `Tools`, `Parse/*`, `Article.cs` (the general-fixes pipeline, `core/article.py`),
   `TalkPageFixes.cs`, typo fixing (`rules/typos.py`), find and replace (`rules/findreplace.py`), advanced
   find and replace (`rules/replacespecial.py`), template substitution (`rules/substtemplates.py`), skip
   comparers (`rules/skip.py`) and the page list model (`lists/listmaker.py`). Every AWB test file passes
   except `DiffTests.cs` (ported with the native diff in step 5) and `CacheTests.cs` (with `api/`); the 4
   skips are .NET/UI-only or need `api/`. Tagger's wiki lookups go through `parsers.tagger.TaggerLookups`,
   implemented in `api/` in step 4.
4. Mostly done: `api/` (everything written against a `Transport` protocol; `PywikibotTransport` is the real one,
   tests use a fake): siteinfo -> `SiteConfig` (namespaces, aliases, magic words, RTL, month names, summary tag,
   AWB config pages, interwiki order, site matrix), login with bot passwords (keychain via `api/credentials.py`),
   the CheckPage gate (`api/checkpage.py`, enforced in `WikiSession.save`), open/save with
   `baserevid`/`basetimestamp`/`starttimestamp`/`assert=user`, preview, `action=compare`, expandtemplates,
   Tagger lookups, ObjectCache (`CacheTests.cs` passes). `lists/providers.py` ports AWB's API list providers;
   `lists/pagegenerators.py` exposes pywikibot's generators. Wikidata: `api/wikidata.py` fetches (batched
   `wbgetentities`), `core/wikidata.py` holds items and the interwiki-vs-sitelinks check/removal.
   `api/connect.py` opens a session from a `config.toml` profile. The User-Agent contact is the tool page
   (`docs/wiki/PyAutoWikiBrowser.wikitext`, to be published at Wikipedia:PyAutoWikiBrowser). Open: whether PyAutoWikiBrowser requires its own entry in the global VersionJSON
   (`WikiSession(require_enabled_version=...)`, off for now) and may use the "AWB" change tag; OAuth; the edit
   scheduler (delay between saves) belongs with the save loop in step 5; Wikidata dates/description not yet
   used by the category and DEFAULTSORT fixes.
5. In progress. Done: wikitext highlighting. `editor/tokenizer.py` is a line-for-line port of codemirror-mediawiki's
   `token.ts` (+ TeX/JSON sub-modes; LilyPond not ported) passing all 2717 upstream tokenizer tests
   (`tests/editor/test_tokenizer_parity.py`); deliberate difference: `\p{M}` added to word classes so Indic words
   stay whole. `ui/highlighter.py` runs it per block with the state kept on each block. WikiEditor toolbar:
   main/secondary rows, Advanced (heading menu, lists, size, gallery, redirect), Special characters (with
   recently used), Help; `encapsulate` passes core's QUnit cases (`tests/editor/test_textselection.py`); Codex
   icons and Codex design tokens. WikiEditor's dialogs: insert link (target suggestions from
   `WikiSession.prefix_search`, ordered as `mw.widgets.TitleWidget`, fetched off the UI thread), insert file
   (reads and writes the wiki's localised image magic words), insert table, search and replace (.NET regex
   syntax via `core.rx`, with timeout); logic in `editor/dialogs.py`, Qt in `ui/editor_dialogs.py`.
   Next: the main window loop (profile and login, list maker, diff, save loop).
   UI MVP (Qt widgets, Qt-native editor implementing WikiEditor: toolbar sections/groups/tools, heading menu,
   special characters, link/table/search-replace dialogs, help panel, `encapsulate` behaviour, all from WikiEditor's
   config and i18n): list maker, editor, server diff/preview, skip/save loop, find & replace, typo fixing, general fixes.
6. Settings import, custom Python modules, plugins.
7. Packaging, auto-update, translatewiki.net integration.
