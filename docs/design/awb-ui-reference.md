# AWB user interface: reference for PyAutoWikiBrowser

Sources studied (2026-10-13):
- The 219 screenshots in [Commons: Category:Screenshots of AutoWikiBrowser](https://commons.wikimedia.org/wiki/Category:Screenshots_of_AutoWikiBrowser)
  (AWB 3.9 to 6.5, 2006-2026; English, Arabic, Persian, Hebrew, Japanese, Korean, Hindi, Sanskrit, Kannada,
  Tamil, Bengali, Armenian, Vietnamese and other wikis). File names below are on Commons.
- JWB, Joeytje50's in-browser AWB (`User:Joeytje50/JWB.js`, v4.5.2, GPL-2.0-or-later), read from `../awb-l/jwb.js`.

## 1. AWB's main window

One window, the same in every version since about 2008 (`046 AWB illustrations for AWB manual.png`,
`025 AWB illustrations for AWB manual.png`, `Capture AWB presentation fr.png`):

```
+---------------------------------------------------------------------------------+
| AutoWikiBrowser – <settings file> – <current page>                              |
| File  View  List  Plugins  Options  Tools  Help                                 |
| [optional toolbar: Stop ◀ Start ■ | Preview | Diff | Save ➜Skip | 🗑 | Pages: N]  |
+---------------------------------------------------------------------------------+
|  DIFF / PREVIEW (full width, ~45% height)                                       |
|  "Double click on a line to undo all changes on that line, or single click to   |
|   focus the edit box to that line."                                             |
|        Current revision        |          Your text                             |
|  Line 12:                      |  Line 12:                                      |
|  - old line (yellow)           |  + new line (blue/green), changed words bold   |
+------------------+---------------------------+----------------------------------+
| Make list        | Options|More…|Disambig|   | Edit box|History|What links here| |
| Source: [combo]  | Skip|Bots|Start           | Edit Summary|Logs|Page Logs|Typos |
| <criteria>: [  ] |                           | [B I Ab 🌐 √n 🚫 — #R str x² x₂ ⛔] |
| N pages [Make list]                          | [per-page edit summary box     ] |
| [add title ][+]  |  (see section 2)          |                                  |
| +--------------+ |                           |   wikitext edit box              |
| | page list    | |                           |   (syntax highlighted)           |
| |              | |                           |                                  |
| +--------------+ |                           |                                  |
| [Remove][Filter] |                           |                                  |
+------------------+---------------------------+----------------------------------+
| [progress] status text | Pages/min Edits/min Edits Skipped New | wiki | User | 0 |
+---------------------------------------------------------------------------------+
```

- The **diff/preview pane is on top, full width**. It shows the diff, the preview (rendered page), or
  "**No changes** — Press the "Skip" button below to skip to the next page." (`AWB change fail snip 4.png`).
- The **bottom row has three columns**: list maker (narrow), the tabbed control panel (narrow), and the
  edit box with its own tabs (widest).
- **Status bar** (left to right): progress bar; status text ("Ready to save", "Processing page", "Getting
  list", "List complete!", "Stopped", "Restarting in 50", "3139 typos loaded", "Loading page to check if we
  are logged in.", "Logged in, user and software enabled. Bot = True, Admin = False", "Software
  disabled"); "Bot timer: N"; Timer, Pages/min, Edits/min, Edits, Skipped, New; the wiki
  (`en.wikipedia`); the user name, **red "User:" when logged out, green when logged in**; a counter.
- Window title: `AutoWikiBrowser – <settings file> – <current page>`.
- RTL: on Arabic/Persian/Hebrew interface languages the whole window is mirrored, menus included
  (`AWB-skip1.png`, `Persian AWB interface.jpg`); on a Persian wiki the diff columns are mirrored too
  (new text left, current revision right: `FaAWB-diff.jpg`).
- Fully translated UI (Japanese `AWBja.png`, Persian), so every label must be translatable.
- The edit box in AWB is a Windows RichTextBox: complex scripts break on old Windows
  (`AWBbn error.JPG`: Bengali shows as boxes), and pages with Private Use Area characters are refused
  (`AutoWikiBrowser can't edit a page with symbols…png`). Qt's text engine is the fix for both.

## 2. The control panel tabs

**Options** (`003`/`017 AWB illustrations…`):
- *Automatic changes*: Auto tag; Apply general fixes; Unicodify whole page; button "Auto changes skip
  options" → dialog "Skip if no…" (Check all/none; Title boldened, External link bulleted, Bad links
  fixed, Unicodification, Auto tag changes, Header error fixed, {{defaultsort}} added, User talk templates
  subst'd, Citation template dates fixed, Human category changes).
- *Find and replace*: Enabled; buttons Normal settings / Advanced settings / Template substitution;
  "Skip if [ ] no replacement [ ] only minor replacement made".
- *Regex typo fixing*: "Enable RegexTypoFix" (a link to the typo page); Skip if no typo fixed.

**More…**: Append/Prepend text (Enabled, Append/Prepend radio, text with `\r\n`, "Use N newlines",
Sort meta data after); Files ("Choose a task…" + two boxes, Skip page when no file changed); Categories
("Choose a task…" + two boxes, Skip if no cat changed, Remove sortkey).

**Disambig**: Enable disambiguation, Link to disambiguate + Load links, Variants, Skip page when no
disambiguations made, "Use ± 20 characters for context"; a per-occurrence dialog (`Dismabig1.png`).

**Skip**: *Text*: Contains / Doesn't contain, Regex, Case sensitive, Check after. *General skip
options*: Page is in use; Edit blocked by spam filter; Page contains no links; No changes are made, with
nested Only whitespace / Only casing / Only genfixes / Only minor genfixes / Only cosmetic changes; Page
is redirect; No alerts. *Page*: ( ) Exists ( ) Doesn't exist ( ) Don't care.

**Bots** (approved bots only; otherwise "Sorry, these options are available only for approved bots."):
Auto save, Max edits, Delay N seconds between edits, Suppress "using AWB"; Nudge timer (resave if stuck,
total nudges, reset, skip page if first nudge doesn't help); Auto shutdown.

**Start** — the working tab (`008 AWB illustrations…`, `AWB change fail snip 1.png`):
- Default Summary [combo], Lock, Minor edit.
- *Page statistics*: Words, Links, Images, Categories, Interwiki links, Dates O/I/A.
- *Alerts* list (e.g. "No category (may be one in a template)", "Unbalanced brackets found", "Starts with
  heading", "Header(s) with wikilinks") and *Multiple wiki-links* list ("Mazandaran Province (2)") with
  "Delink selection".
- Buttons: Start, Stop, Preview, Diff, Watch/Unwatch, Move, Protect, Delete, **Skip** (large), **Save**
  (large, green; tooltip "Save the changes and continue (Ctrl+S)").
- *Find*: box, Regex, Case sensitive, Find (highlights in the edit box).

## 3. The edit area tabs

- **Edit box**: editor toolbar (bold, italic, link, external link, math, nowiki, hr, #R redirect,
  strike, sup, sub, comment) on the same row as the **per-page edit summary** box; the edit box below.
  Context menu: Word wrap, Undo…, Paste more ▸, Save text to file, Go to line, Insert ▸, Insert tag ▸,
  Convert list to ▸, Unicodify selected, Bypass all redirects, Fix all excess whitespace, **Re-parse
  (F5)**, Comment selected (Ctrl+K), Open page / talk / history in browser, Replace text with last edit,
  Undo all changes.
- **History**, **What links here** (of the current page).
- **Edit Summary** (default summaries list).
- **Logs**: "Successfully saved" table (Page, Time) and "Skipped" table (Page, Time, Skipped By, Skip
  Reason; e.g. "AWB — No Find And Replace Changes", "User — Clicked ignore", "Kingbotk Plugin — …"),
  each with Save log / Add all to list / Clear.
- **Page Logs**: Move/Protect/Delete actions (Page, Action, Time, Remark).
- **Logging to file** (XHTML/wiki code logs, upload to a wiki page).
- **Typos**: "On this page" (Find, Replace, Total, No changes) and "Overall statistics" (Total, No change,
  Typos/save) with a context menu.

## 4. List maker

`Make list` → Source combo (all providers; "Special page" opens a dialog with source + namespace) →
criteria label/box (label from the provider: "Category:", "What links to:", "Wiki search:", "Links on:")
→ "N pages" + Make list (becomes a stop button while making) → add box + "+" → the list → Remove,
Filter. Context menu: Open in browser, Open history, Cut/Copy/Paste, Select ▸, Remove ▸, Add selected to
list from… ▸, Move to top/bottom, Convert to/from talk pages, Filter, Save list, Sort (reverse)
alphabetically. **List menu**: Keep alphabetized, Remove duplicates, Remove non-main space, Convert
to/from talk pages, Filter… (List Filter dialog: namespaces to keep, title contains/not contains, set
operations with another list, sort, remove duplicates), Save list…, Clear current list.

## 5. Menus and dialogs

- **File**: Reset to default settings, Open settings…, Recent settings ▸, Save settings, Save settings
  as…, Save settings as default, Log in/Profiles… (Ctrl+L), Log out, Refresh status/typos (Ctrl+R), Exit.
- **View**: toolbar, control panel (F11), enlarge edit box (F10), edit box toolbar.
- **Options**: Preferences… (Ctrl+P), Default Edit Summaries…, Auto save settings file every 10 pages,
  Use pre-parse mode, Follow redirects, Apply changes automatically, Auto focus end of the edit box, Do
  not use section edit summaries, Restrict {{DEFAULTSORT}} change/addition, Restrict orphan tag addition to
  linkless pages, Do not apply WP:MOS fixes, Highlight syntax in edit box, Highlight Find matches,
  Highlight errors, Mark all as minor, watchlist combo, Sort interwiki links, Replace reference tags.
- **Tools**: Make module (Ctrl+M), External processing (Ctrl+E), Regex tester (Ctrl+Shift+T), Database
  scanner (Ctrl+Shift+D), List comparer, List splitter, Reset saved/skipped counts, Submit stats, Profile
  typos, Invalidate cache. **Plugins**: Load…, Manager… (plugins add tabs to the control panel).
  **Help**: Help (F1), About, Usage statistics, Check for updates.
- **Profiles** dialog: table (ID, Username, Password saved?, Default settings, Notes), Login / Add… /
  Edit… / Delete, and *Quick login* (username, password, Save this account, Save password). A profile
  links an optional default settings file.
- **Preferences**: General (on load: show changes / preview / edit, preview diff in bot mode, warn on
  exit, save page list with settings…), Site (project, language, suppress "using AWB", ignore
  bots/nobots, empty page list on project change), Editing and saving (auto save edit box, flash/beep
  when ready to save, edit box font), Tools, Privacy, Alerts (which alerts to show).
- **Find & Replace**: options at the top (ignore links…, ignore templates…, add replacements to edit
  summary), a **Search** box with Go to find rules, then the grid (Find, Replace with, CaseSensitive,
  Regex, MultiLine, SingleLine, Minor, After fixes, Enabled, Comment); sortable columns; a new row is
  always at the bottom (`*`). **Replace Special** (advanced): a rule tree (Rule, In Template Rule,
  subrules), Name, Enabled, Type (Entire text…), Find / If tabs, Replace with, Regular expression,
  Case sensitive, Multiline, Singleline, Apply No. of times, Test…. **Substitute templates**.
- **Regex tester**, **Database scanner** (Database, Namespace, Title, Revision, Text, Searching,
  Restriction, Help tabs; results; Convert), **List comparer** (two list makers, Compare, unique 1 /
  common / unique 2, Save list / Use list), **List splitter**, **Custom module** (C# code editor).
- Message boxes seen in the field: user blocked, CheckPage failed to load, PUA characters, new messages,
  "Error connecting to wiki".

## 6. JWB (JavaScript Wiki Browser): ideas worth taking

- **Per-page variables**: a list entry `Title|value`; `$x` in find/replace is replaced by the value
  (also from SMW queries' first printout).
- **Settings as named presets** ("setups") stored as JSON on the wiki at `User:<name>/JWB-settings.json`,
  plus download/import as a file; a `_blank` and a `default` setup.
- **Skip if in category** (checked with `prop=categories&clcategories=` in the same request that loads
  the page); **skip if exists / doesn't exist / neither** as one radio group (as AWB).
- **Redirects as one choice**: follow / skip / edit the redirect itself.
- **Limits**: regex time limit per rule (ms) and a **maximum diff size** (refuse saves that change more
  than N characters).
- **Warns before an endless skip**: "skip if no change" with no rules and no typo fixing.
- **Pre-parse mode**: run through the list without showing pages, keeping only pages that would change
  (a `#PRE-PARSE-STOP` marker in the list), then edit those.
- **Find/replace extras**: `_` flag (space and underscore match each other), empty find = append, and
  per-rule "ignore unparsed content" (nowiki/comments).
- **Saving is pipelined**: the next page loads while the save request is in flight; a failed save asks
  "continue?".
- **Action log** with counters: pages, saved, null edits, skipped, other actions; each log line has a
  diff link.
- **Clicking a diff line moves the editor cursor to that line** (AWB does the same; AWB also undoes a line
  on double click).
- **Skip typo fixing for this page** button; typo list refresh button.
- Admin tab: move (suppress redirect, talk, subpages), delete (with talk), protect (edit/move/upload,
  expiry).
- CheckPage gate: JWB lets admins and wikis without a CheckPage through (PyAWB does not: CLAUDE.md rule 6).

## 7. PyAWB today against AWB (gap list)

| Area | AWB | PyAWB now | Plan |
|---|---|---|---|
| Layout | diff/preview on top; list, controls, editor in the bottom row | list dock left; Edit/Diff tabs; options below | Adopt AWB's layout (section 8) |
| Start tab | summary, Lock, Minor, statistics, alerts, multiple links, big Skip/Save, Find | summary row and buttons under the panel | Start tab |
| Status bar | pages/min, edits/min, edits, skipped, new, wiki, coloured user | status text, edits/skipped, wiki | AWB's status bar |
| Logs | saved/skipped tables, page logs, add all to list | status line only | Logs tab |
| Diff | own diff, click → edit box line, double click → undo line | server diff, read-only | click-to-line now; native diff and undo with the wikidiff2 port |
| Editor tabs | History, What links here, Typos stats | — | later |
| Alerts/statistics | `Article.cs` alerts already ported | not shown | Start tab |
| Find in edit box | Find box on Start tab | WikiEditor search & replace dialog | Find box |
| Profiles | table + quick login | combo-based dialog | keep (fits keychain), add a profiles list later |
| Bots tab, pre-parse, list filter/comparer, DB scanner, modules, plugins | yes | no | later steps |

## 8. Proposed PyAWB layout (to confirm)

Keep AWB's arrangement, which AWB users know, with Qt widgets styled after Codex:

- Top: a `QSplitter` with the **diff/preview pane** (Qt-native diff, "No changes" page, preview opens in the
  browser or the optional embedded view).
- Bottom row (a second splitter): **list maker** | **control tabs** (Options, More, Skip, Bots, Start) |
  **edit tabs** (Edit box with toolbar + per-page summary, Logs, later History / What links here / Typos).
- Status bar as AWB's, the user name green/red.
- Menus as AWB's where the feature exists (File with profiles and settings; List; Options; Tools; Help),
  with AWB's shortcuts (Ctrl+S save, Ctrl+I skip, Ctrl+L profiles, Ctrl+R refresh status/typos,
  F5 re-parse, Ctrl+K comment).
- Whole window mirrored for RTL interface languages (`QApplication.setLayoutDirection`), and the diff,
  editor and lists in the wiki's direction.

## 9. Startup wizard, projects and preferences (planned, 2026-10-13)

Requested for PyAWB (not in AWB, which starts straight into the main window with `Default.xml`).

**Startup wizard** — on first run, and from *File → New project…*:
1. *Interface language* (any MediaWiki language; RTL languages mirror the window).
2. *Wiki*: project and language (or a custom wiki); the **fonts for its script**: an editor font and a
   UI font chosen from the families that `QFontDatabase` reports for the wiki's writing system
   (Malayalam, Arabic, Devanagari, Han…), with a live sample in the script and a warning when no
   installed font covers it. Correct shaping needs a font that supports the script, so this step matters.
3. *Account*: an existing profile, or a new one (bot password, keychain), or "later".
4. *Pages*: the list maker (source, criteria, Make list), so the user lands in the main window with a list.
5. *Summary*: save as a project file (optional), then open the main window.

**Projects** (AWB's settings files): *File → New project / Open project… / Recent projects ▸ / Save
project / Save project as…*. A project file (TOML, one per task) holds the profile name, the page list
(optional), the processing options, find & replace rules, skip options, edit summaries, append/prepend,
categories/files and the editor options. Never credentials. AWB settings XML import comes later
(roadmap step 6). JWB's idea of named presets saved to a JSON user page on the wiki can come later too.

**Preferences** (`config.toml`, per user): default profile/project and what to open at start-up;
interface language; fonts per writing system (editor, UI, diff); theme (system/light/dark); syntax
highlighting theme; editor options (word wrap, line numbers later, font size); on load (show changes /
preview / edit); warn on exit; save page list with project; "Flash/Beep when ready to save"; alerts to
show; User-Agent contact.

**Syntax highlighting themes**: the highlighter's colours are data (`editor/highlight_style.py`), so a
theme is a named palette. Candidates: *CodeMirror light* (current default; codemirror-mediawiki
`theme.ts`), *Nord dark* (codemirror-mediawiki `nord.ts`, already used for dark mode), a *colour-blind
friendly* palette (proposed for Wikimedia's CodeMirror in
[T163533](https://phabricator.wikimedia.org/T163533): headings/magic words `#E4A400`, templates
`#9C3A00`, tags/refs/math `#56B4E9`, variables `#009E73`), and *AWB classic* (AWB's
`ArticleTextBox.HighlightSyntax`: grey background for templates, refs, lists and categories; dark blue
template names; blue bold links; light green background for files; bold headings; italics). No
reusable cross-editor wikitext theme format exists (searched 2026-10-13), so themes stay in our own
data format, keyed by codemirror-mediawiki's token classes.

## 10. Login at start-up, two-factor, and read-only use (planned, 2026-10-13)

A login screen opens at start-up (after the wizard on first run). Three ways in, one screen:

1. **Bot password** (`Name@Tool` from Special:BotPasswords; recommended, as now): `action=login`,
   remembered in the keychain. Bot passwords do not ask for a second factor.
2. **Account password with two-factor**: our own `action=clientlogin` exchange in `pyawb.api` (pywikibot's
   `ClientLoginManager` does the same but asks for the code on the console). Step 1 sends user name +
   password; if the wiki answers `UI` with an `OATHToken` field, step 2 shows a **TOTP code** screen
   (`logincontinue=1&OATHToken=…`); an e-mail code (`EmailAuth`) is handled the same way. The
   password is never stored for this kind of login.
3. **Sign in with the wiki's own page** (security keys/passkeys/WebAuthn, and any future method): as
   vcut-gui does (`../vcut-gui/src/vcut/gui/browser_login.py`, GPL-3.0), Special:UserLogin in an embedded
   QtWebEngine view with its own cookie profile; when the session cookies appear (`<wikiid>Session`,
   `centralauth_*`), they are copied into pywikibot's HTTP session and confirmed with `meta=userinfo`
   and a CSRF token. WebAuthn is bound to the wiki's origin, so it cannot be done in a native form. When
   clientlogin answers with a WebAuthn request, the screen offers this way.

OAuth 2.0 with PKCE in the system browser is the long-term option (needs a registered OAuth consumer
for PyAutoWikiBrowser on Meta); not now.

**Skip** ("Continue without logging in"): lists, page viewing, diff and preview, and all read-only
actions work; Save/Move/Delete stay disabled. The screen says so before skipping: "Without logging in
(and without approval on the wiki's CheckPage) you cannot save edits." The status bar keeps the red
"User:" box, and File → Log in is always there.

## 11. Toolbar, modes and stepping (built, 2026-10-13)

Toolbar, always visible: **[Read only | Dry run | Make changes] | Start, Stop | Previous, Pause, Next |
Save, Skip | Preview, Diff | x / N + progress bar**.

- Modes (`editloop.Mode`, `available_modes`): *Read only* opens pages as they are (no processing, editor
  read-only, no saving); *Dry run* processes and diffs but never saves; *Make changes* is AWB's loop.
  Not logged in: Read only only. Logged in without CheckPage approval: Read only and Dry run. The
  active mode is highlighted.
- *Start* starts (or goes on with) the loop; *Stop* puts the page shown aside.
- *Pause* switches to one page at a time: Previous and Next work only while paused (a running batch
  moves by itself); Next leaves the page unmarked; *Skip* always marks the page skipped and moves on;
  after *Save* a paused loop stays until Next. Unpausing goes on.
- Pages the loop is done with stay in the list, marked saved or skipped (List → Remove done pages).

## 12. Information bar; no anonymous access; the start screen (2026-10-13)

- An **information bar** above the toolbar shows the wiki (project logo, site name, host), the user
  (with bot/admin) or "Not logged in", the CheckPage result ("Approved for editing" / "Not approved:
  read only and dry run"), and the mode.
- **Connecting to a wiki needs a login**, so there is no anonymous read-only use: logged out, only
  offline lists (manual list, text file) can be made; Start stays disabled. (Supersedes the anonymous
  plan in section 10; the login screen's Skip leads to this offline state, with the warning.)
- **Start screen** before the main window, asking everything needed to proceed: interface language →
  wiki (project + language) → **fonts for the wiki's script** (editor, interface and diff fonts from the
  installed families that support the script, with a live sample; the most important step, since it
  shapes every display) → login (bot password / password + two-factor / the wiki's own login page, or
  Skip with the warning) → mode and the list. Shown on first run and from File → New project; later runs
  open the last project and only ask for the login.

## 13. Settings (built, 2026-10-13)

*Settings* menu: Theme…, Language…, Fonts…, User profiles…, Preferences… (Ctrl+P), one dialog
(`ui/settings_dialog.py`) with a tab each, saved to config.toml (`[preferences]`, `[fonts.<script>]`).
- Languages come from Meta-Wiki (`meta=languageinfo`: autonym, English name, direction; `action=sitematrix`
  for which wikis are open), bundled as `settings/data/meta-languages.json` (`tools/porting/meta_languages.py`)
  and refreshed into the data directory (`api/languages.py`).
- Fonts are chosen per script (the wiki language's script, `settings.preferences.script_for_language`) from
  the installed families that have it, with a sample in the script; editor (with size), interface and
  diff fonts. The start screen will reuse this page.
- Applied at once: theme (and the highlighter's light/dark colours), interface language (WikiEditor
  toolbar; RTL languages mirror the window), fonts, word wrap; "When a page is loaded" (diff or edit
  box); "Ask before closing" while a page is open or a run is going.

## 14. Start screen (built, 2026-10-13)

`ui/start_screen.py`, before the main window (`ui/app.py`). Steps: 1. interface language (Meta-Wiki's
list); 2. wiki: project + one of its open wikis (Meta's site matrix), or a script path; 3. fonts for that
wiki's script (the Settings fonts page); 4. log in; 5. pages (the list maker, with the wiki once logged
in). First run starts at 1; once a profile exists, at 4 (Back for the others). The choices are saved
as the default profile and preferences.

Log in, three ways:
- **Bot password** (`action=login`), optionally remembered in the keychain.
- **Account password**: pywikibot's `ClientLoginManager` (`action=clientlogin`); when the wiki asks for a
  second factor (TOTP, e-mailed code) its prompt (`pywikibot.input`) is answered from the screen: the
  login thread waits while a code field appears (`api.transport.SecondFactor`). Never stored.
- **The wiki's own login page** (`ui/browser_login.py`, after vcut-gui): Special:UserLogin in Qt
  WebEngine with its own cookie store; when `<wikiid>UserName` + `Session` (or CentralAuth's) cookies
  appear, they go into pywikibot's HTTP session and are checked (`site.login(cookie_only=True)`,
  `WikiSession.login_with_cookies`). Covers security keys and passkeys. Only when WebEngine is installed.
- **Skip**: asks first ("without logging in … you cannot edit, and you cannot load pages or make lists
  from the wiki"), then offline: manual and file lists only.

Not yet tested against a real wiki with two-factor or a security key (no such account here).
