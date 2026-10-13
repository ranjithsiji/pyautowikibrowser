"""Parity with @bhsd/codemirror-mediawiki: its 2717 tokenizer tests (test/parserTests.json,
MediaWiki parser-test inputs with the expected token classes), run with its test configuration
(wikiparser-node config/default.json). The output format is that of its test/src/test.ts."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from pyawb.editor import tokenizer as tk
from pyawb.editor.mwconfig import config_from_parser_data

DATA = Path(__file__).parent / "data"
CASES: list[dict[str, Any]] = [
    c
    for c in json.loads((DATA / "cm_parser_tests.json").read_text(encoding="utf-8"))
    if "wikitext" in c
]
MW = tk.MediaWiki(
    config_from_parser_data(
        json.loads((DATA / "wikiparser_default_config.json").read_text(encoding="utf-8"))
    )
)


@pytest.fixture(autouse=True)
def no_entity_check() -> Iterator[None]:
    # the upstream tests run without a browser, where every well-formed &...; is an entity
    tk.CHECK_ENTITIES = False
    yield
    tk.CHECK_ENTITIES = True


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt")


def render(text: str) -> str:
    out: list[list[str]] = []
    lines = tk._LINE_BREAK.split(text)  # pyright: ignore[reportPrivateUsage]
    for line, tokens in zip(lines, tk.tokenize_text(MW.mediawiki(), text), strict=True):
        for start, end, style in tokens:
            name = style.replace("mw-", "")
            if out and out[-1][0] == name:
                out[-1][1] += line[start:end]
            else:
                out.append([name, line[start:end]])
    return "".join(f"<{n}>{_escape(t)}</>" if n.strip() else _escape(t) for n, t in out)


@pytest.mark.parametrize("case", CASES, ids=[f"{i}:{c['desc'][:60]}" for i, c in enumerate(CASES)])
def test_codemirror_parser_tests(case: dict[str, Any]) -> None:
    assert render(case["wikitext"]) == case["parsed"]
