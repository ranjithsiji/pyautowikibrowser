`enwiki.json` is English Wikipedia's parser configuration from wikiparser-node 1.48.0
(config/enwiki.json, GPL-3.0-or-later, (C) Bhsd). It lets the editor highlight wikitext before a
wiki is loaded; once a wiki's siteinfo is loaded, `mwconfig.from_siteinfo` replaces it.

`wikieditor/` is copied by `tools/porting/wikieditor_data.py`:
- `messages/<lang>.json`: WikiEditor's `wikieditor-toolbar*` messages (GPL-2.0-or-later, WikiEditor and
  translatewiki.net contributors) and the core messages the toolbar uses (`special-characters-*`, `sig-text`,
  `word-separator`, `brackets`; MediaWiki core 1.45.3, GPL-2.0-or-later);
- `fallbacks.json`: language fallback chains from core's `languages/messages/Messages*.php`;
- `specialcharacters.json`: core's `mediawiki.language.specialCharacters`, unchanged.
