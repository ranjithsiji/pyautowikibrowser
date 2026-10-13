"""Convert Wikimedia Codex's sources (icons and design tokens) to the JSON PyAutoWikiBrowser reads.

Usage:
    python3 -I tools/porting/codex_data.py <design-codex checkout> src/pyawb

Reads the sources directly, so no npm build is needed:

packages/codex-icons/src/icons.ts + images/*.svg -> src/pyawb/icons/codex-icons.json
    {"cdxIconBold": <svg contents> | {ltr, rtl, shouldFlip, shouldFlipExceptions, langCodeMap,
    default}}, the same shape as the built package's icons; the SVG contents without the <svg>
    wrapper and <title>, as the package's svgo build makes them.

packages/codex-design-tokens/src/{themes/wikimedia-ui,application,components,modes/dark}.json
    -> src/pyawb/ui/styles/codex-tokens.json
    {"version", "light": {...}, "dark": {...}}: the application and component (decision) tokens
    with style-dictionary's names (path joined by "-": background-color-interactive--hover),
    references ({ color.gray100 }, also inside calc()) resolved and Codex's px/rem unit
    transforms applied as its build does; dark = the dark mode's overrides on top.

Also copies both packages' LICENSE and the icons' README (licence of the designs: CC BY 4.0).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# --- icons --------------------------------------------------------------------------------

IMPORT = re.compile(r"import\s+(\w+)\s+from\s+'\./images/([^']+\.svg)';")
EXPORT = re.compile(r"export const (cdxIcon\w+)(?:\s*:\s*\w+)?\s*=\s*(\w+|\{.*?\n\});", re.S)


def svg_contents(path: Path) -> str:
    svg = path.read_text(encoding="utf-8")
    svg = re.sub(r"<\?xml.*?\?>", "", svg)
    svg = re.sub(r"<title>.*?</title>", "", svg, flags=re.S)
    svg = re.sub(r"</?svg[^>]*>", "", svg)
    return re.sub(r">\s+<", "><", svg).strip()


def ts_object(text: str, svgs: dict[str, str]) -> Any:
    """A TypeScript object literal of icons.ts as JSON (svg variables -> their contents)."""
    text = re.sub(r"'([^']*)'", r'"\1"', text)
    text = re.sub(r"(?<=[{,\s])([A-Za-z_]\w*)\s*:", r'"\1":', text)
    text = re.sub(r"\b(svg\w+)\b", lambda m: json.dumps(svgs[m.group(1)]), text)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)


def icons(src: Path) -> dict[str, Any]:
    ts = (src / "icons.ts").read_text(encoding="utf-8")
    svgs = {var: svg_contents(src / "images" / file) for var, file in IMPORT.findall(ts)}
    out: dict[str, Any] = {}
    for name, value in EXPORT.findall(ts):
        if value in svgs:
            out[name] = svgs[value]
        elif value in out:  # an alias: cdxIconDraggable = cdxIconDraggableVertical
            out[name] = out[value]
        else:
            out[name] = ts_object(value, svgs)
    return out


# --- design tokens ------------------------------------------------------------------------

REF = re.compile(r"\{\s*([\w.-]+)\s*\}")


def merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


# .style-dictionary/matchers.js shouldUseRelativeSize / shouldUseAbsoluteSize
RELATIVE = ("font-size", "line-height", "size", "max-width", "max-height")
ABSOLUTE = ("spacing", "min-width", "min-height", "min-size", "border-radius")


def number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def unit(path: tuple[str, ...], value: str, node: dict[str, Any]) -> str:
    """transformers.js relativeSizeTransform / absoluteSizeTransform (transitive: after refs)."""
    n = number(value)
    if n is None:
        return value
    if n == 0 and any(p in path for p in RELATIVE + ABSOLUTE):
        return "0"
    text = f"{n:g}"
    if not node.get("unitless") and any(p in path for p in RELATIVE):
        return f"{round(n / 16, 7)!r}".removesuffix(".0") + "rem"
    if any(p in path for p in ABSOLUTE):
        return f"{text}px"
    return value


PX_SUM = re.compile(r"^\s*-?\d+(?:\.\d+)?px(?:\s*[-+]\s*\d+(?:\.\d+)?px)+\s*$")


def px_arithmetic(value: str) -> str:
    """'12px - 1px' -> '11px', as LESS computes it (only sums of px terms)."""
    if not PX_SUM.match(value):
        return value
    terms = re.findall(r"([-+]?)\s*(\d+(?:\.\d+)?)px", value)
    total = sum(float(n) * (-1 if sign == "-" else 1) for sign, n in terms)
    return f"{total:g}px"


def resolve(tree: dict[str, Any], path: tuple[str, ...], depth: int = 0) -> str:
    """A token's value with references resolved and the unit transforms applied."""
    if depth > 20:
        raise ValueError(path)
    node: Any = tree
    for part in path:
        node = node[part]
    value = REF.sub(
        lambda m: resolve(tree, tuple(m.group(1).split(".")), depth + 1), str(node["value"])
    )
    return px_arithmetic(unit(path, value, node))


def flatten(tree: dict[str, Any], path: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    if "value" in tree:
        return [path]
    out: list[tuple[str, ...]] = []
    for k, v in tree.items():
        if isinstance(v, dict):
            out.extend(flatten(v, (*path, k)))
    return out


def tokens(src: Path) -> dict[str, dict[str, str]]:
    def load(name: str) -> dict[str, Any]:
        return json.loads((src / name).read_text(encoding="utf-8"))

    theme = load("themes/wikimedia-ui.json")
    decisions = merge(load("application.json"), load("components.json"))
    dark_mode = load("modes/dark.json")
    result: dict[str, dict[str, str]] = {}
    for mode, overrides in (("light", {}), ("dark", dark_mode)):
        public = merge(decisions, overrides)
        tree = merge(theme, public)
        result[mode] = {"-".join(p): resolve(tree, p) for p in flatten(public)}
    return result


def main(codex: Path, pyawb: Path) -> None:
    packages = codex / "packages"
    version = json.loads((packages / "codex" / "package.json").read_text("utf-8"))["version"]

    icons_out = pyawb / "icons"
    icons_out.mkdir(parents=True, exist_ok=True)
    data = icons(packages / "codex-icons" / "src")
    (icons_out / "codex-icons.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=0) + "\n", encoding="utf-8"
    )
    for name in ("LICENSE", "README.md"):
        shutil.copy(packages / "codex-icons" / name, icons_out / name)

    styles = pyawb / "ui" / "styles"
    tok = tokens(packages / "codex-design-tokens" / "src")
    (styles / "codex-tokens.json").write_text(
        json.dumps({"version": version, **tok}, indent=1) + "\n", encoding="utf-8"
    )
    shutil.copy(packages / "codex-design-tokens" / "LICENSE", styles / "codex-tokens.LICENSE")
    print(f"Codex {version}: {len(data)} icons, {len(tok['light'])} tokens")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
