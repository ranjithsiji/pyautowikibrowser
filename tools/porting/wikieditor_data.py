"""Copy the data the editor toolbar needs from WikiEditor and MediaWiki core.

Usage:
    python3 -I tools/porting/wikieditor_data.py <WikiEditor> <mediawiki core> \
        src/pyawb/editor/data/wikieditor

Writes:
    messages/<lang>.json   WikiEditor's toolbar messages + the core messages the toolbar uses
    fallbacks.json         language fallback chains from core's languages/messages/Messages*.php
    specialcharacters.json core's mediawiki.language.specialCharacters data, unchanged

The icons come from Codex (codex_data.py). The toolbar layout itself is hand-ported in pyawb/editor/toolbar.py.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

CORE_KEYS = (
    "sig-text",
    "word-separator",
    "brackets",
    "mw-widgets-titleinput-description-new-page",
    "mw-widgets-titleinput-description-redirect",
)
CORE_PREFIXES = ("special-characters-",)
WIKIEDITOR_PREFIXES = ("wikieditor-toolbar",)


def wanted(key: str, prefixes: tuple[str, ...], keys: tuple[str, ...] = ()) -> bool:
    return key in keys or key.startswith(prefixes)


def load_i18n(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("@metadata", None)
    return data


def lang_of(messages_php: Path) -> str:
    # MessagesEn_gb.php -> en-gb
    return messages_php.stem[len("Messages") :].lower().replace("_", "-")


def main(wikieditor: Path, core: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / "messages").mkdir(parents=True)

    langs: dict[str, dict[str, str]] = {}
    for f in sorted((wikieditor / "i18n").glob("*.json")):
        if f.stem == "qqq":
            continue
        msgs = {k: v for k, v in load_i18n(f).items() if wanted(k, WIKIEDITOR_PREFIXES)}
        langs.setdefault(f.stem, {}).update(msgs)
    i18n = core / "languages" / "i18n"
    for f in sorted([*i18n.glob("*.json"), *(i18n / "nontranslatable").glob("*.json")]):
        if f.stem == "qqq":
            continue
        msgs = {k: v for k, v in load_i18n(f).items() if wanted(k, CORE_PREFIXES, CORE_KEYS)}
        if msgs:
            langs.setdefault(f.stem, {}).update(msgs)
    for lang, msgs in langs.items():
        if msgs:
            (out / "messages" / f"{lang}.json").write_text(
                json.dumps(dict(sorted(msgs.items())), ensure_ascii=False, indent=0) + "\n",
                encoding="utf-8",
            )

    fallbacks: dict[str, list[str]] = {}
    pattern = re.compile(r"^\$fallback\s*=\s*'([^']*)'", re.M)
    for f in sorted((core / "languages" / "messages").glob("Messages*.php")):
        m = pattern.search(f.read_text(encoding="utf-8"))
        if m:
            fallbacks[lang_of(f)] = [x.strip() for x in m.group(1).split(",") if x.strip()]
    (out / "fallbacks.json").write_text(
        json.dumps(fallbacks, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8"
    )

    shutil.copy(
        core / "resources/src/mediawiki.language.specialCharacters/specialcharacters.json",
        out / "specialcharacters.json",
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
