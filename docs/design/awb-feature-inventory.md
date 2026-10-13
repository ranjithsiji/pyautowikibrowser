# AWB features: inventory and status in PyAutoWikiBrowser

Source: [Wikipedia:AutoWikiBrowser/User manual](https://en.wikipedia.org/wiki/Wikipedia:AutoWikiBrowser/User_manual)
(read 2026-10-13) checked against AWB's source (`../autowikibrowser-code-r13044/AWB`, mainly `AWB/Main.cs`,
`AWB/Main.Designer.cs`, `WikiFunctions/Controls/Lists/ListMaker.cs`, `WikiFunctions/Lists/Providers/*`).

Status: **done** · **partial** (what is missing in brackets) · **missing** · **n/a** (why).
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
| Show toolbar | done (always shown) | A: make it a toggle |
| Show control panel (F11) | missing | A |
| Enlarge edit box (F10) | missing | A |
| Show edit box toolbar | missing (always shown) | A |
| Display false positives button; False positives.txt | missing | A |
| (PyAWB) Show the diff pane | done | |

### List
| Item | Status | Phase / notes |
|---|---|---|
| Keep alphabetized | missing | A |
| Remove duplicates | done | as a command; A: AWB's "while lists are loaded" toggle |
| Remove non-mainspace | partial (model only) | A |
| Convert to / from talk pages | partial (`tools.convert_to_talk`) | A |
| Filter… (namespaces, title contains/not, set operations with another list, sort, remove duplicates) | missing | B |
| Save list… (text with wiki markup, plain, CSV, CSV with wiki markup) | missing | A |
| Clear current list | done | |

### Plugins
| Item | Status | Phase / notes |
|---|---|---|
| Load… / Manager… | missing | E (Python entry points, roadmap step 6) |

### Options
| Item | Status | Phase / notes |
|---|---|---|
| Preferences… (Ctrl+P) | partial | see Preferences below |
| Summaries… / Default Edit Summaries… | missing | B |
| Auto save settings file every 10 edits | missing | D |
| Use pre-parse mode | missing | A (auto-skip run; pages kept in the list marked "pre-parsed") |
| Follow redirects | done (Options tab) | A: also in the menu |
| Apply changes automatically (off = only on Re-parse) | missing | A |
| Auto focus end of the edit box | missing | A |
| Do not use section edit summaries | done (Options tab) | A: menu |
| Restrict {{DEFAULTSORT}} change/addition | partial (engine option, always on) | A |
| Restrict orphan tag addition to linkless pages | partial (engine option, always on) | A |
| Do not apply WP:MOS fixes | partial (engine option, always off) | A |
| Highlight syntax in edit box | done (always) | A: toggle |
| Highlight Find matches | missing | A |
| Highlight errors (clickable alerts, Ctrl+B) | missing | A |
| Mark all as minor | partial (Minor edit on the Start tab) | A |
| Watchlist behaviour | done (Start tab) | |
| Sort interwiki links | missing (engine always sorts) | A |
| Replace reference tags | partial (engine option, always on) | A |

### Preferences (dialog)
| Item | Status | Phase / notes |
|---|---|---|
| General: minimize to tray | missing | A (QSystemTrayIcon) |
| General: warn on exit | done | |
| General: save page list with settings | missing | D |
| General: low thread priority | missing | A |
| General: on load (show changes / preview) | done (diff / edit box) | A: preview |
| General: preview the diff in bot mode | missing | C (bots) |
| General: enable logging | missing (always on) | A |
| Site: project, language | done (profiles) | |
| Site: suppress "using AWB" | missing | A |
| Site: ignore {{bots}}/{{nobots}} | done (Options tab) | |
| Site: empty page list on project change | missing | A |
| Editing and saving: auto save edit box every x s to a file | missing | A |
| Editing and saving: moving average timer | missing | A |
| Editing and saving: "using AWB" on delete/protect | missing | C |
| Editing and saving: flash / beep when ready to save | missing | A |
| Editing and saving: edit box font | done (fonts per script) | |
| Tools: add list to comparer / splitter, DB scanner results to list (ask/always/never) | missing | E |
| Privacy: include user name in statistics | n/a | PyAWB sends no usage statistics |
| Alerts: which alerts to show | missing | B |
| (PyAWB) theme, interface language, fonts per script | done | |

### Tools
| Item | Status | Phase / notes |
|---|---|---|
| Make module (Ctrl+M; C#/VB) | missing | E: Python modules `(text, title, vars) -> text`, roadmap step 6 |
| External processing (Ctrl+E) | missing | E |
| Regex tester (Ctrl+Shift+T) | missing | E |
| Database scanner (Ctrl+Shift+D) | missing | E |
| List comparer | missing (model: `lists.listmaker.compare_lists`) | E |
| List splitter | missing | E |
| Reset saved/skipped counts | missing | A |
| Submit stats | n/a | no usage statistics |
| Profile typos | missing | E |
| Invalidate cache | missing | A (`api.cache`) |

### Help
| Item | Status | Phase / notes |
|---|---|---|
| Help (F1): the manual in a browser | missing | A (opens the manual / the tool page) |
| Usage statistics | n/a | |
| Check for updates | missing | F |
| About | done | |

## Make list

| Item | Status | Phase / notes |
|---|---|---|
| Categories on page (all / no hidden / only hidden) | done | |
| Category, recurse 1 level, recursive | done | |
| Category (recurse user-defined level) | partial (engine has depth) | A |
| Checkwiki error (URL), Checkwiki error (number) | missing | A |
| Database dump | missing | E |
| Files on page, Image file links, Links on page (all / blue / red), Transclusions on page | done | |
| Google search | n/a for now | Google's page scraping is blocked; needs an API key |
| HTML scraper, HTML scraper (advanced regex) | missing | A |
| My watchlist, New pages, Pages with a page property, Random pages | done | |
| Special page (dialog: source + namespace) | done differently | each special page is its own source with a namespace box |
| Text file (UTF-8 / Windows-1252) | done | |
| User contribs; (user defined number) | partial (number) | A |
| What links here (all variants), What redirects here, What transcludes page | done | |
| Wiki search (text / title, all NS) | done | |
| (PyAWB) Manual list, Wikidata query (SPARQL), pywikibot page generators | done | |
| Multiple values with `\|` | done | |
| Make list appends; stop button while making | partial (no stop) | A |
| Add (text box + "+"), Remove, Filter | partial (Add via Manual list; no Filter) | A/B |

## Tabs

| Tab / item | Status | Phase / notes |
|---|---|---|
| Options: auto tag, general fixes, unicodify | done | |
| Options: Auto changes skip options ("Skip if no…" dialog) | missing (engine `SkipOptions` exists) | B |
| Options: find and replace normal settings | done | B: Search box in the dialog |
| Options: advanced settings (Replace Special: rule tree, in-template rules, If tab, apply n times, Test) | missing (engine `rules.replacespecial` exists) | B |
| Options: template substitution | missing (engine `rules.substtemplates` exists) | B |
| Options: skip if no / only minor replacement | done | |
| Options: RegexTypoFix, skip if no typo fixed | done | |
| More: append/prepend (+ sort metadata), files, categories, `%%key%%` | done | |
| Disambig tab + disambiguation dialog (unlink, {{dn}}, variants, unpipe, flip, reset, undo) | missing | C |
| Skip: contains / doesn't contain, regex, case, check after | done | |
| Skip: in use, no links, no change (+ whitespace, casing, genfixes, minor genfixes), redirect | done | |
| Skip: edit blocked by spam filter | missing | A |
| Skip: only cosmetic changes (same HTML) | missing | A (`action=parse` of both) |
| Skip: no alerts | missing | A |
| Skip: page exists / doesn't exist / don't care (radio) | partial (two check boxes) | A |
| Bots tab: auto save + delay, max edits, suppress "using AWB", nudge timer, auto shutdown | missing | C |
| Start: summary, lock, minor, statistics, alerts, multiple wiki-links | done | |
| Start: Delink selection (multiple wiki-links) | missing | A |
| Start: Start, Stop, Preview, Diff, Skip, Save, Find | done | |
| Start: Watch/Unwatch, Move, Protect, Delete (admins) | missing | C |
| Start: False (false positives) | missing | A |
| Start: shortcuts Ctrl+G start, Esc stop | missing | A |
| Edit box | done | |
| History tab (+ diffs, context menu: open in browser, refresh) | missing | C |
| What links here tab | missing | C |
| Edit summary tab | done (the page's summary above the editor) | |
| Logs (saved/skipped, save, clear, add all to list) | done | A: tooltips, context menu, filter by reason |
| Page logs (move/protect/delete) | missing | C |
| Typos tab (on this page / overall statistics) | missing (engine `get_statistics`) | C |

## Context menus

| Menu / item | Status | Phase / notes |
|---|---|---|
| List: open page / history in browser (Ctrl+Alt+P / H) | missing | A |
| List: cut, copy, paste (newlines or commas) | missing | A |
| List: select all / none / inverse | missing | A |
| List: remove selected / all / duplicates / non-main | partial (buttons) | A |
| List: add selected from list ▸ (links, categories, transclusions… of the selected pages) | missing | A |
| List: move to top / bottom; convert to/from talk; filter; save; sort (reverse) alphabetically | missing | A |
| Edit box: word wrap, undo, cut, copy, paste, select all | partial (Qt's own menu) | A |
| Edit box: paste more, save text to file, go to line | missing | A |
| Edit box: insert ▸ (birth/death categories, category Ctrl+T), insert tag ▸ (DEFAULTSORT, disambig, wikify, cleanup, expand, speedy delete, clear, uncategorised, stub) | missing | A |
| Edit box: convert list to `*` / `#`, unicodify selected, bypass all redirects (admins), fix all excess whitespace | missing | A |
| Edit box: re-parse (F5), comment selected (Ctrl+K) | missing | A |
| Edit box: open page / talk page / history / selection in browser | missing | A |
| Edit box: replace text with last edit, undo all changes | missing | A |
| History: open in browser, refresh | missing | C |
| Logs: add selected to list, cut, copy, remove, select all/none, open page/diff/history in browser, clear, reset; skipped: filter (exclude) by reason | missing | A |

## Order of work

A (this and the next steps), then B, C, D, E. Each batch is ported from AWB's code with its tests where AWB
has them, and checked in the running app.

## Manual chapters

### Find and replace (Wikipedia:AutoWikiBrowser/Find_and_replace)
| Item | Status | Phase / notes |
|---|---|---|
| Normal settings: ignore links/images/nowiki/math/comments (Hide), ignore templates/refs/link targets/headings/quotes (HideMore), add replacements to summary | done | |
| Normal settings: **Search** box + Go (searches Find and Replace with) | missing | B |
| Normal settings: Clear, OK, Cancel; rows: find, replace with, case sensitive, regex, multiline, singleline, minor, after fixes, enabled, comment | done | |
| `$1`, `$2`… in replacements; `\n` for newlines (plain and regex) | done | engine (`rules.findreplace`) |
| Keywords `%%key%%`, `%%title%%`, `%%fullpagename%%`, `%%pagename%%`, `%%subpagename%%`, `%%basepagename%%`, `%%namespace%%`, `%%server%%`, `%%servername%%`, `%%scriptpath%%` | done | `tools.apply_key_words`, values checked against the manual's table |
| Minor rules not applied on Re-parse (F5) | missing | A (with Re-parse) |
| Advanced settings (Replace Special): rule tree with New ▸ Rule / In template call / Template parameter and subrules; Name, Enabled (disabled in red), Type (entire text / inside template calls, nested), Find/Replace, regex, case, multiline, singleline, Apply # times, If: contains / not contains (+ options), Templates list (in template call), Rule menu (undo, redo, cut, copy, paste, delete, refresh colours), Test… | missing UI (engine `rules.replacespecial` done) | B |
| Template substitution: templates to substitute (one per line; braces and namespace optional), ignore links…, expand recursively, include comment with template name, Clear, Reset, OK, Cancel | missing UI (engine `rules.substtemplates` done; expansion through `api` `expandtemplates`) | B |
| Order: normal F&R → advanced → template substitution → general fixes and typos → F&R after fixes | done | `core.process.process_page` |
| Saved with the settings file | missing | D |

### Regular expression (Wikipedia:AutoWikiBrowser/Regular_expression)
| Item | Status | Phase / notes |
|---|---|---|
| .NET syntax: anchors, classes, `\p{…}`, groups, named groups, quantifiers (lazy, possessive-free), back references `\1` `\k<name>`, look-around, comments `(?#…)`, `$1` `${name}` in replacements | done | `core.dotnet_regex` translator; Python `regex` with better Unicode |
| Options IgnoreCase, SingleLine, MultiLine, ExplicitCapture (check boxes and inline `(?imsnx-imsnx)` / `(?i:…)`) | done | |
| Timeout per rule | done | rule 2 |
| User-made shortcut editing macros (advanced rules applied by Re-parse) | missing (needs Re-parse) | A |
| Regex tester | missing | E |

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
