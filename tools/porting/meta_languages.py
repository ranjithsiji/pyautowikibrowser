"""Write the language and wiki snapshot the start screen uses before logging in.

Usage:
    python3 tools/porting/meta_languages.py src/pyawb/settings/data/meta-languages.json

Fetches meta.wikimedia.org's meta=languageinfo (autonym, English name, direction of every language
MediaWiki knows) and action=sitematrix (which projects have an open wiki in which language), and
writes them in settings.languages' format. Re-run to refresh; the app also fetches a fresh copy into
the user's data directory when it can.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pyawb.settings.languages import (  # noqa: E402
    LANGUAGEINFO_PARAMS,
    SITEMATRIX_PARAMS,
    LanguageData,
    parse_languageinfo,
    parse_open_wikis,
    to_json,
)

API = "https://meta.wikimedia.org/w/api.php"
USER_AGENT = "PyAutoWikiBrowser-tools/0.1 (https://en.wikipedia.org/wiki/Wikipedia:PyAutoWikiBrowser)"


def get(params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main(out: str) -> None:
    data = LanguageData(
        datetime.now(UTC).date().isoformat(),
        parse_languageinfo(get(dict(LANGUAGEINFO_PARAMS))),
        parse_open_wikis(get(dict(SITEMATRIX_PARAMS))),
    )
    Path(out).write_text(to_json(data) + "\n", encoding="utf-8")
    print(f"{len(data.languages)} languages, {len(data.wikis.get('wikipedia', ()))} Wikipedias")


if __name__ == "__main__":
    main(sys.argv[1])
