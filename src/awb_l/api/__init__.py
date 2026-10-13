# AWB-L: cross-platform AutoWikiBrowser
# Copyright (C) 2026 AWB-L contributors
#
# This program is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
"""All wiki API calls go through here (a thin layer over pywikibot).

- transport: the Transport protocol and PywikibotTransport (pywikibot configured in code)
- session: WikiSession: site configuration, login, the CheckPage gate, open/save/preview/diff
- siteinfo, checkpage, models, errors: parsing API responses (pure, tested offline)
- wikidata: batched wbgetentities into core.wikidata items
- tagger: Tagger's wiki lookups and template expansion
- cache: ObjectCache; credentials: bot passwords in the OS keychain
"""
