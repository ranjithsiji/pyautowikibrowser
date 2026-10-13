# AWB-X

A cross-platform rewrite of [AutoWikiBrowser](https://en.wikipedia.org/wiki/Wikipedia:AutoWikiBrowser),
the semi-automated MediaWiki editor, for Linux, macOS and Windows. Python + PySide6 + `regex`.

Status: early development (roadmap step 2). See `CLAUDE.md` for the design and roadmap.

```
uv sync
uv run pytest -m "not network"
uv run awb-x
```

Licensed GPL-3.0-or-later. Based on AutoWikiBrowser (GPL-2.0-or-later) by its many contributors.
