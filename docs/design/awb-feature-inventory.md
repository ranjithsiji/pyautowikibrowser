# AWB features: inventory and status in PyAutoWikiBrowser

Source: [Wikipedia:AutoWikiBrowser/User manual](https://en.wikipedia.org/wiki/Wikipedia:AutoWikiBrowser/User_manual)
(read 2026-10-13) checked against AWB's source (`../autowikibrowser-code-r13044/AWB`, mainly `AWB/Main.cs`,
`AWB/Main.Designer.cs`, `WikiFunctions/Controls/Lists/ListMaker.cs`, `WikiFunctions/Lists/Providers/*`).

Status: **done** · **partial** (what is missing in brackets) · **missing** · **n/a** (why).
The [screenshots on Commons](#from-the-manuals-screenshots) add items the manual does not list; the
[target menu bar](#target-menu-bar) and the [order of work](#order-of-work) are at the end.

Phase: **A** menus, list and editor commands (next); **B** dialogs (advanced find & replace, template
substitution, skip options, list filter, alerts, summaries); **C** tabs (History, What links here, Page logs,
Typos, Disambig, Bots); **D** projects/settings files and start-up parameters; **E** tools (regex tester,
list comparer, list splitter, external processing, database scanner, modules, plugins); **F** packaging.

## Start-up and login

| AWB | Status | Phase / notes |
|---|---|---|
| Start-up parameters `/s "file.xml"` (settings file), `/u name\|number` (profile) | missing | D: `pyawb --project file --profile name` |
| Log in/Profiles (File menu), saved passwords | done | start screen, Settings → User profiles, keychain |
| Two-factor accounts (AWB: bot passwords only) | done | account password + TOTP, or the wiki's login page |
| HTTPS for custom wikis | done | script path decides |

## Menus

### File
| Item | Status | Phase / notes |
|---|---|---|
| Reset to default settings | missing | D |
| Open settings… / Recent settings ▸ | missing | D (project files; AWB XML import) |
| Save settings / Save settings as… / Save settings as default | missing | D |
| Log in/Profiles… (Ctrl+L) | done | |
| Log out | done | |
| Refresh status/typos (Ctrl+R) | partial (typos only; CheckPage, user talk templates, template redirects, dated templates not reloaded) | A |
| Exit (Ctrl+Q) | done | |

### View
| Item | Status | Phase / notes |
|---|---|---|
| Show toolbar | done | |
| Show control panel (F11) | done | |
| Enlarge edit box (F10) | done | |
| Show edit box toolbar | done | |
| Display false positives button; False positives.txt | done | the file is in PyAWB's data directory |
| (PyAWB) Show the diff pane | done | |

### List
| Item | Status | Phase / notes |
|---|---|---|
| Keep alphabetized (Ctrl+Shift+A) | done | |
| Remove duplicates (Ctrl+Shift+U, a toggle as in AWB) | done | |
| Remove non-mainspace (Ctrl+Shift+M; also skips redirects to other namespaces) | done | |
| Convert to / from talk pages | done | |
| Filter… (namespaces, title contains/not, set operations with another list, sort, remove duplicates) | done | `lists.listfilter`, `ui.list_dialogs`; set operations keep the list's order |
| Save list… (text with wiki markup, plain, CSV, CSV with wiki markup) | done | |
| Clear current list | done | |

### Plugins
| Item | Status | Phase / notes |
|---|---|---|
| Load… / Manager… | missing | E (Python entry points, roadmap step 6) |

### Options
| Item | Status | Phase / notes |
|---|---|---|
| Preferences… (Ctrl+P) | partial | see Preferences below |
| Summaries… / Default Edit Summaries… | done | AWB's English list on English-language wikis until edited |
| Auto save settings file every 10 edits | missing | D |
| Use pre-parse mode (Ctrl+Shift+E) | done | pages with changes stay, marked green; works in Read only mode too (processed as a dry run) |
| Follow redirects | done | the menu item and the Options tab box are one setting |
| Apply changes automatically (off = only on Re-parse) | done | |
| Auto focus end of the edit box | done | |
| Do not use section edit summaries | done | mirrors the Options tab box |
| Restrict {{DEFAULTSORT}} change/addition | done | off by default, as in AWB (the engine had it on) |
| Restrict orphan tag addition to linkless pages | done | |
| Do not apply WP:MOS fixes | done | |
| Highlight syntax in edit box | done | on by default (AWB: off) |
| Highlight Find matches | done | extra selections, so undo is untouched |
| Highlight errors (clickable alerts) | done | `process.page_errors`; a click on the alerts selects the next error |
| Mark all as minor | done | mirrors Minor edit on the Start tab |
| Watchlist behaviour | done | Start tab and Options ▸ Watchlist ▸ |
| Sort interwiki links | done | |
| Replace reference tags | done | |

### Preferences (dialog)
| Item | Status | Phase / notes |
|---|---|---|
| General: minimize to tray | done | where the desktop has a notification area |
| General: warn on exit | done | |
| General: save page list with settings | missing | D |
| General: low thread priority | done | the worker threads run at low priority |
| General: on load (show changes / preview / edit box) | done | preview opens in the browser |
| General: preview the diff in bot mode | missing | C (bots) |
| General: enable logging | missing (always on) | A |
| Site: project, language | done (profiles) | |
| Site: suppress "using AWB" | n/a | AWB enables it only on non-Wikimedia wikis, where no tag is added; bots: C4 |
| Site: ignore {{bots}}/{{nobots}} | done (Options tab) | |
| Site: empty page list on project change | done | |
| Editing and saving: auto save edit box every x s to a file | done | |
| Editing and saving: moving average timer | done | "Timer: n" in the status bar |
| Editing and saving: "using AWB" on delete/protect | missing | C |
| Editing and saving: flash / beep when ready to save | done | only when the window is in the background, as AWB |
| Editing and saving: edit box font | done (fonts per script) | |
| Tools: add list to comparer / splitter, DB scanner results to list (ask/always/never) | missing | E |
| Privacy: include user name in statistics | n/a | PyAWB sends no usage statistics |
| Alerts: which alerts to show | done | also limits Highlight errors and Skip ▸ No alerts |
| (PyAWB) theme, interface language, fonts per script | done | |

### Tools
| Item | Status | Phase / notes |
|---|---|---|
| Make module (Ctrl+M; C#/VB) | missing | E: Python modules `(text, title, vars) -> text`, roadmap step 6 |
| External processing (Ctrl+E) | missing | E |
| Regex tester (Ctrl+Shift+T) | done | `ui.regex_tester`, `rules.regextest` |
| Database scanner (Ctrl+Shift+D) | missing | E |
| List comparer | missing (model: `lists.listmaker.compare_lists`) | E |
| List splitter | missing | E |
| Reset saved/skipped counts | done | |
| Submit stats | n/a | no usage statistics |
| Profile typos | missing | E |
| Invalidate cache | done | |

### Help
| Item | Status | Phase / notes |
|---|---|---|
| Help (F1): the manual in a browser | done | AWB's user manual, until the tool page has one |
| Usage statistics | n/a | |
| Check for updates | missing | F |
| About | done | |

## Make list

| Item | Status | Phase / notes |
|---|---|---|
| Categories on page (all / no hidden / only hidden) | done | |
| Category, recurse 1 level, recursive | done | |
| Category (recurse user-defined level) | done | levels box next to the input instead of AWB's dialog |
| Checkwiki error (URL), Checkwiki error (number) | done | the number uses the wiki id (AWB: language + "wiki") |
| Database dump | missing | E |
| Files on page, Image file links, Links on page (all / blue / red), Transclusions on page | done | |
| Google search | n/a for now | Google's page scraping is blocked; needs an API key |
| HTML scraper, HTML scraper (advanced regex) | done | fetched through `api.web` (our User-Agent); AWB's inverted "Case sensitive" fixed |
| My watchlist, New pages, Pages with a page property, Random pages | done | |
| Special page (dialog: source + namespace) | done differently | each special page is its own source with a namespace box |
| Text file (UTF-8 / Windows-1252) | done | |
| User contribs; (user defined number) | done | |
| What links here (all variants), What redirects here, What transcludes page | done | |
| Wiki search (text / title, all NS) | done | |
| (PyAWB) Manual list, Wikidata query (SPARQL), pywikibot page generators | done | |
| Multiple values with `\|` | done | |
| Make list appends; stop button while making | done | |
| Add (text box + "+"), Remove, Filter | done | |

## Tabs

| Tab / item | Status | Phase / notes |
|---|---|---|
| Options: auto tag, general fixes, unicodify | done | |
| Options: Auto changes skip options ("Skip if no…" dialog) | done | |
| Options: find and replace normal settings | done | with the Search box |
| Options: advanced settings (Replace Special: rule tree, in-template rules, If tab, apply n times, Test) | done | `ui.replace_special_dialog` |
| Options: template substitution | done | `ui.subst_templates_dialog`; expansion through `api.tagger.WikiTemplateExpander` |
| Options: skip if no / only minor replacement | done | |
| Options: RegexTypoFix, skip if no typo fixed | done | |
| More: append/prepend (+ sort metadata), files, categories, `%%key%%` | done | |
| Disambig tab + disambiguation dialog (unlink, {{dn}}, variants, unpipe, flip, reset, undo) | done | `rules.disambiguation`, `ui.disambig_dialog`; the dialog opens after processing, on the UI thread |
| Skip: contains / doesn't contain, regex, case, check after | done | |
| Skip: in use, no links, no change (+ whitespace, casing, genfixes, minor genfixes), redirect | done | |
| Skip: edit blocked by spam filter | done | unchecked: asks "Try and edit again?" and reloads the page |
| Skip: only cosmetic changes (same HTML) | done | `WikiSession.rendering` + `process.same_rendering` |
| Skip: no alerts | done | |
| Skip: page exists / doesn't exist / don't care (radio) | done | AWB's layout: the kinds of "no change" under it |
| Bots tab: auto save + delay, max edits, suppress "using AWB", nudge timer, auto shutdown | missing | C |
| Start: summary, lock, minor, statistics, alerts, multiple wiki-links | done | |
| Start: Delink selection (multiple wiki-links); a click on a link finds it | done | the pipe trick gives what MediaWiki shows |
| Start: Start, Stop, Preview, Diff, Skip, Save, Find | done | |
| Start: Watch/Unwatch, Move, Protect, Delete (admins) | missing | C |
| Start: False (false positives) | done | |
| Start: shortcuts Ctrl+G start, Esc stop | done | |
| Edit box | done | |
| History tab (+ diffs, context menu: open in browser, refresh) | done | a table from the API (AWB: a web page); double click opens that edit's diff |
| What links here tab | done | links, redirects and transclusions; add to the page list |
| Edit summary tab | done (the page's summary above the editor) | |
| Logs (saved/skipped, save, clear, add all to list) | done | newest first, as AWB |
| Page logs (move/protect/delete) | done (the tab) | filled by the admin actions of C3 |
| Typos tab (on this page / overall statistics) | done | shown while a typo list is loaded, as AWB |

## Context menus

| Menu / item | Status | Phase / notes |
|---|---|---|
| List: open page / history in browser (Ctrl+Shift+P / H), double click opens the page | done | asks first for 10 or more pages |
| List: cut, copy, paste (newlines or \|) | done | |
| List: select all / none / inverse | done | no Ctrl+D for none: it is Diff |
| List: remove selected / all / duplicates / non-main | done | |
| List: add selected from list ▸ (links, categories, transclusions… of the selected pages) | done | |
| List: move to top / bottom; convert to/from talk; filter; save; sort (reverse) alphabetically | done | |
| Edit box: word wrap, undo, cut, copy, paste, select all | done | word wrap saved in config.toml |
| Edit box: paste more, save text to file, go to line | done | paste more texts in config.toml until projects (D1) |
| Edit box: insert ▸ (birth/death categories, category Ctrl+T), insert tag ▸ (DEFAULTSORT, disambig, wikify, cleanup, speedy delete, clear, disambiguation, uncategorised, stub) | done | `editor.editcommands` |
| Edit box: convert list to `*` / `#`, unicodify selected, bypass all redirects (admins), fix all excess whitespace | done | redirects resolved 50 per query (`api.pageinfo.redirect_targets`) |
| Edit box: re-parse (F5), comment selected | done | comment is Ctrl+Shift+K: Ctrl+K is WikiEditor's link dialog |
| Edit box: open page / talk page / history / selection in browser | done | |
| Edit box: replace text with last edit, undo all changes | done | |
| History: open in browser, refresh | done | |
| Logs: add selected to list, cut, copy, remove, select all/none, open page/diff/history in browser, clear, reset; skipped: filter (exclude) by reason | done | |

## From the manual's screenshots

Source: the 73 images in [Commons: Category:AutoWikiBrowser user manual project](https://commons.wikimedia.org/wiki/Category:AutoWikiBrowser_user_manual_project)
and its subcategories (read 2026-10-14), checked against the menu trees in `AWB/Main.Designer.cs`,
`WikiFunctions/Controls/Lists/ListMaker.Designer.cs` and `WikiFunctions/Logging/LogControl.Designer.cs`.
These items were missing from the tables above.

| Where | Item | Status | Phase / notes |
|---|---|---|---|
| Diff | Single click on a line focuses the edit box there; **double click undoes all changes on that line** | done | `editcommands.undo_line_changes` |
| Diff | Persian AWB mirrors the whole window and the diff in RTL | done | `diffhtml` mirrors, Qt layout direction |
| Toolbar | Show/hide control panel and show/hide parameters buttons; Delete (admins); False positive | partial (View menu items) | C (delete) |
| Status bar | Timer, bot timer, user notifications (new talk-page messages), user name chip red/green | done but the bot timer | C4 (bot timer); messages and notifications are read with every page opened, as AWB |
| View | Show toolbar, Show control panel, Enlarge edit box, Show edit box toolbar, Display false positives button | missing | A |
| List context | Format page titles per displaytitle | done | italics, bold, sub, sup (AWB: italics only); looked up with `api.pageinfo` |
| List context | Select ▸ All (Ctrl+A) / None / Inverse (Ctrl+Shift+I); Remove ▸ Selected / All / Duplicates / Non-main space | done | |
| List menu | Shortcuts: Keep alphabetized Ctrl+Shift+A, Remove duplicates Ctrl+Shift+U, Remove non-main Ctrl+Shift+M, Filter Ctrl+Shift+F | done | |
| List box | Text box + "+" button to add one title; page count; Remove; Filter | done | |
| Logs context | Open diff in browser (Ctrl+Shift+D); Filter: Show only / Exclude (selected reasons) | done | |
| Logging to file tab | Log to XHTML / wiki code, verbose, folder; upload logs to a wiki page (location `$USER/Logs`, category, job name, max lines, watch, open in browser); status | missing | D |
| Edit box menu | Paste more ▸ 10 slots (Ctrl+1…Ctrl+0) + Configure…; Go to line ▸ text box; Insert tag ▸ `{{-stub}}` box | done | |
| Edit box | Custom toolbar buttons added by plugins and modules (Persian screenshot) | missing | E |
| Options menu | Use pre-parse mode Ctrl+Shift+E | done | |
| Tools | C# Eval (run a snippet against the page) → Python console | missing | E |
| Tray | Minimize to tray menu: Show / Hide / Exit | done | |
| Profiles dialog | Table ID / user / password saved? / default settings file / notes; Login, Add, Edit, Delete; quick login with "save this account / password" | done differently | start screen + Settings → User profiles; per-profile default project: D |
| Disambig tab | Enable, link to disambiguate + Load links (variants from the disambiguation page), variants box, skip when none made, ± context characters | done | |
| Bots tab | Auto save, max edits, delay between edits, suppress "using AWB"; nudge timer (resave if stuck, total nudges, reset, skip if first nudge fails); auto shutdown (shutdown/standby/restart/hibernate) | missing | C |
| Find & Replace dialog | row indicator column, Search + Go; links to the regex help | done (Search) | |
| Replace Special | New / Rule menus, up/down arrows to reorder, New rule / New subrule / Delete, Find/If tabs | done | undo/redo, cut/copy/paste, disabled rules in red |
| Skip if no… | Check all/none + 10 boxes (title boldened, external link bulleted, bad links fixed, unicodification, auto tag changes, header error fixed, DEFAULTSORT added, user talk templates subst'd, citation dates fixed, human category changes) | done | |
| List filter | Namespaces (content + talk columns, all content / all talk), title remove/keep containing (+regex), sort, remove duplicates, set operations (difference, intersection) with another list (open file, paste, clear) | done | |
| Regex tester | Find, Replace, text, result; MultiLine/SingleLine/IgnoreCase/ExplicitCapture | done | |
| External processing | Enabled, skip if no change, program, arguments, I/O file, pass text as file or as parameter | missing | E |
| Module | Enabled + "No module loaded" state, language, Make module, built-at time, fixed width font, template text | missing | E (Python) |
| List comparer | Two list makers, Compare, unique 1 / common / unique 2 with counts, Save list / Use list each, Clear all | missing | E |
| List splitter | List maker, pages per file, save to text files / to settings (project) files | missing | E |
| DB scanner | Text tab page properties (not counted / at least / at most, ignore redirects); Restriction: unlock move permissions; thread priority | missing | E |
| Plugin manager | Plugin menu, count, list of loaded plugins | missing | E |
| Splash | Start-up splash | n/a | the start screen replaces it |

## Target menu bar

AWB's "settings files" are PyAWB **projects** (TOML, with an importer for AWB's XML), so the File menu says
"project". Settings (theme, language, fonts, profiles, preferences) stay in PyAWB's own Settings menu; AWB's
Options ▸ Preferences… opens the same dialog.

```
File     New project (reset to defaults) · Open project… · Recent projects ▸ · Import AWB settings… |
         Save project (Ctrl+S is Save page, so none) · Save project as… · Save as default |
         Log in/Profiles… Ctrl+L · Log out · Refresh status/typos Ctrl+R | Exit Ctrl+Q
View     Show toolbar · Show control panel F11 · Enlarge edit box F10 · Show edit box toolbar ·
         Show the diff pane | Display false positives button
List     Keep alphabetized Ctrl+Shift+A · Remove duplicates Ctrl+Shift+U · Remove non-main space Ctrl+Shift+M |
         Convert to talk pages · Convert from talk pages | Filter… Ctrl+Shift+F · Save list… · Clear current list
Plugins  Load… · Manager… | (one entry per loaded plugin)
Options  Preferences… Ctrl+P · Default edit summaries… · Auto save project every 10 pages ·
         Use pre-parse mode Ctrl+Shift+E | Follow redirects · Apply changes automatically |
         Auto focus end of the edit box · Do not use section edit summaries · Restrict DEFAULTSORT change/addition ·
         Restrict orphan tag addition to linkless pages · Do not apply WP:MOS fixes · Highlight syntax ·
         Highlight Find matches · Highlight errors | Mark all as minor · Watchlist ▸ | Sort interwiki links ·
         Replace reference tags
Tools    Make module Ctrl+M · External processing Ctrl+E | Python console | Regex tester Ctrl+Shift+T ·
         Database scanner Ctrl+Shift+D · List comparer · List splitter | Reset saved/skipped counts |
         Profile typos · Invalidate cache
Settings Theme… · Language… · Fonts… · User profiles… · Preferences…
Help     Help F1 · Check for updates · About
```

## Order of work

Each step reads the manual chapter(s) named in its row and the AWB source files behind it, and ports that code (with its NUnit tests where AWB has them), keeps logic out of `ui/`
(models in `lists/`, `editor/`, `core/`, `rules/`), adds pytest-qt tests for the UI, and is checked in the
running app with screenshots. One commit per step.

| Step | Contents | AWB sources | Manual chapters to meet |
|---|---|---|---|
| A1 ✔ | **List**: List menu with shortcuts; list context menu (open page/history, cut/copy/paste, Select ▸, Remove ▸, Add selected to list from ▸, move to top/bottom, convert to/from talk, displaytitle, filter, save list in 4 formats, sort/reverse sort); keep alphabetized; add-one-title box; stop while making a list; missing sources (category user depth, user contribs with number, HTML scraper plain/advanced regex, CheckWiki URL/number) | `ListMaker.cs`, `ListBox2.cs`, `Lists/Providers/*` | User manual: Make list, list menus |
| A2 ✔ | **Edit box**: context menu (word wrap, paste more + configure, save text to file, go to line, insert ▸ birth/death cats and category Ctrl+T, insert tag ▸, convert list to `*`/`#`, unicodify selected, bypass all redirects, fix all excess whitespace, re-parse F5, comment selected Ctrl+K, open page/talk/history/selection in browser, replace with last edit, undo all changes); diff double click undoes a line | `Main.cs` (mnuTextBox handlers), `ConfigurePasteMoreItems.cs`, `Tools.cs` | Find and replace: minor rules not applied on Re-parse; Regular expression: shortcut editing macros run by Re-parse |
| A3 ✔ | **Options menu** (all toggles wired to `ProcessOptions`/engine flags), pre-parse mode, apply changes automatically, highlight Find matches/errors, auto focus end; **View menu** (toolbar, control panel F11, enlarge edit box F10, edit box toolbar, false positives); Tools ▸ reset counts, invalidate cache; Help F1; Start tab Delink selection, false positive button, Ctrl+G/Esc | `Main.cs`, `Article.cs` alerts | General fixes: the Options menu switches (restrict DEFAULTSORT, orphan tagging, MOS fixes, sort interwikis, reference tags) |
| A4 ✔ | **Skip tab** extras (spam filter blocked, only cosmetic changes, no alerts, exists/doesn't/don't care radio); **Logs** context menu (add to list, cut/copy, remove, select, open page/diff/history, filter show only/exclude, clear, reset) | `LogControl.cs`, `Main.cs` skip checks | User manual: Skip tab, Logs |
| B1 ✔ | **List filter** dialog (namespaces, title, set operations, sort, duplicates) | `ListFilterForm.cs` | Database Scanner: results Filter uses the same dialog |
| B2 ✔ | **Replace Special** dialog over `rules.replacespecial`; **Template substitution** dialog over `rules.substtemplates`; F&R Search box | `ReplaceSpecial/*`, `SubstTemplates.cs`, `FindandReplace.cs` | Find and replace: advanced settings, template substitution, Search; Regular expression: options, `$1`/`${name}`, inline options in every rule box |
| B3 ✔ | **Skip if no…** dialog; **Default edit summaries**; **Alerts** preferences page; remaining Preferences items (suppress "using AWB", empty list on project change, auto save edit box, flash/beep, low priority) | `SkipOptions.cs`, `SummaryEditor.cs`, `Preferences.cs` | General fixes: "Skip if no…" per fix |
| C1 ✔ | **History**, **What links here**, **Page logs** and **Typos** tabs | `Main.cs` web controls, `RegExTypoFix` stats | User manual: tabs |
| C2 ✔ | **Disambig** tab and dialog | `Disambiguation/*` | User manual: Disambig |
| C3 | Admin actions **Watch/Unwatch, Move, Protect, Delete** (+ "using AWB" summaries) and bypass all redirects | `ArticleActionDialog.cs`, `Article.cs` | User manual: Start tab admin buttons |
| C4 | **Bots** tab: auto save with delay, max edits, nudge timer, auto shutdown (bot accounts per CheckPage only) | `Main.cs` bot mode, `NudgeTimer.cs`, `ShutdownNotification.cs` | User manual: Bots |
| D1 | **Projects**: save/open/recent/default/reset (TOML, page list optionally), auto save every 10 pages, start-up `--project`/`--profile`, AWB settings XML import | `UserSettings.cs`, `UserPrefs.cs` | Find and replace: rules saved with the settings file |
| D2 | **Logging to file** (XHTML/wikitext logs, optional upload to the wiki) | `Logging/*` | User manual: Logging to file |
| E1 | **Regex tester**, **List comparer**, **List splitter**, **External processing** | `Extras/*`, `ListComparer.cs`, `ListSplitter.cs`, `ExternalProgram.cs` | Regular expression: the tester |
| E2 | **Database scanner** (dump reader in worker processes, all tabs) and the "Database dump" source | `Extras/DBScanner/*` | Database Scanner: every tab, AWB-specific checks, Convert, performance (worker processes) |
| E3 | **Custom Python modules** (Make module), Python console, **plugins** (load, manager, toolbar buttons), Profile typos | `CustomModule.cs`, `CSharpEval.cs`, `PluginManager.cs` | User manual: Tools, Plugins |
| F | Packaging, check for updates | | |

Not ported: Submit stats / Usage statistics / Privacy (PyAWB sends no usage data), Google search (needs an
API key), splash screen (start screen instead).

## Manual chapters

### Find and replace (Wikipedia:AutoWikiBrowser/Find_and_replace)
| Item | Status | Phase / notes |
|---|---|---|
| Normal settings: ignore links/images/nowiki/math/comments (Hide), ignore templates/refs/link targets/headings/quotes (HideMore), add replacements to summary | done | |
| Normal settings: **Search** box + Go (searches Find and Replace with) | done | |
| Normal settings: Clear, OK, Cancel; rows: find, replace with, case sensitive, regex, multiline, singleline, minor, after fixes, enabled, comment | done | |
| `$1`, `$2`… in replacements; `\n` for newlines (plain and regex) | done | engine (`rules.findreplace`) |
| Keywords `%%key%%`, `%%title%%`, `%%fullpagename%%`, `%%pagename%%`, `%%subpagename%%`, `%%basepagename%%`, `%%namespace%%`, `%%server%%`, `%%servername%%`, `%%scriptpath%%` | done | `tools.apply_key_words`, values checked against the manual's table |
| Minor rules not applied on Re-parse (F5) | n/a | AWB's source applies them; only "skip if no / only minor replacement" is off on Re-parse, as here |
| Advanced settings (Replace Special): rule tree with New ▸ Rule / In template call / Template parameter and subrules; Name, Enabled (disabled in red), Type (entire text / inside template calls, nested), Find/Replace, regex, case, multiline, singleline, Apply # times, If: contains / not contains (+ options), Templates list (in template call), Rule menu (undo, redo, cut, copy, paste, delete, refresh colours), Test… | done | `ui.replace_special_dialog` |
| Template substitution: templates to substitute (one per line; braces and namespace optional), ignore links…, expand recursively, include comment with template name, Clear, Reset, OK, Cancel | done | |
| Order: normal F&R → advanced → template substitution → general fixes and typos → F&R after fixes | done | `core.process.process_page` |
| Saved with the settings file | missing | D |

### Regular expression (Wikipedia:AutoWikiBrowser/Regular_expression)
| Item | Status | Phase / notes |
|---|---|---|
| .NET syntax: anchors, classes, `\p{…}`, groups, named groups, quantifiers (lazy, possessive-free), back references `\1` `\k<name>`, look-around, comments `(?#…)`, `$1` `${name}` in replacements | done | `core.dotnet_regex` translator; Python `regex` with better Unicode |
| Options IgnoreCase, SingleLine, MultiLine, ExplicitCapture (check boxes and inline `(?imsnx-imsnx)` / `(?i:…)`) | done | |
| Timeout per rule | done | rule 2 |
| User-made shortcut editing macros (advanced rules applied by Re-parse) | done | Re-parse runs every rule |
| Regex tester | done | Tools ▸ Regex tester (Ctrl+Shift+T) and the Test… buttons |

### General fixes (Wikipedia:AutoWikiBrowser/General_fixes)
All 56 fixes the chapter names are ported with AWB's tests (`core/parsers/*`, `core/article.py`); the four the
names do not match are labels inside other methods (MergeSeeAlso in `merge_templates_by_section`, MoveDablinks
and MoveMaintenanceTags in `MetaDataSorter`'s sort, MoveSisterLinks = `move_sisterlinks`). Missing only their
switches in the Options menu (restrict DEFAULTSORT, restrict orphan tagging, no MOS fixes, sort interwikis,
replace reference tags) and the "Skip if no…" dialog: phases A and B above.

### Database Scanner (Wikipedia:AutoWikiBrowser/Database_Scanner)
| Item | Status | Phase / notes |
|---|---|---|
| Database: dump file (XML, also .bz2/.gz to read directly), header (site name, base, generator, case) | missing | E |
| Namespaces to search | missing | E |
| Title contains / not contains, regex, case sensitive | missing | E |
| Revision: last edited between dates | missing | E |
| Text contains / not contains (keywords `%%title%%`, `%%key%%`, `%%titlename%%`, `%%namespace%%`), regex, singleline, case, multiline, ignore comments | missing | E |
| Page text properties: characters / links / words (more/less than) | missing | E |
| AWB specific: title AWB will embolden, links AWB will simplify, bad links AWB will fix, HTML entities, section error, unbulleted links, typo, missing {{DEFAULTSORT}}, human birth/death cats, unbalanced brackets, references to reorder, citation dates AWB will fix | missing (the checks exist in the engine) | E |
| Start from page, limit results, start / pause / reset, progress, multi-core | missing | E (worker processes) |
| Restriction: edit / move protection levels | missing | E |
| Results: filter, save, clear; Convert: headings every x, alphabetised headings, `#` / `*` list, make, copy, save | missing | E |
| "Database dump" list source; add results to the list (ask/always/never) | missing | E |
