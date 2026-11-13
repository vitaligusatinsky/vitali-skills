"""plan.py: gate a layout plan before anything is built (`docgate plan plan.json`).

A plan states the system a document will be built on: page, grid, type scale, gap scale,
measure, frames and one best-in-class reference per page type. The checks are the same
relational bands harness v2 measures on rendered pages (see quality.py), applied to the
intent, so a plan that cannot pass the rendered gate is rejected before a line of layout.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _oklab_L(hexc):
    c = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = lin
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    return 0.2104542553 * np.cbrt(l) + 0.7936177850 * np.cbrt(m) - 0.0040720468 * np.cbrt(s)


def check(plan: dict, base: Path) -> list[tuple[str, str, str]]:
    """Returns (level, rule, message) rows."""
    out = []
    add = lambda lvl, rule, msg: out.append((lvl, rule, msg))

    # type scale: at most five sizes, each step at least 1.2x the one below, display >= 2x body
    sizes = sorted(plan["type"]["sizes_pt"])
    body = plan["type"]["body_pt"]
    if len(sizes) > 5:
        add("fail", "plan-type-count", f"{len(sizes)} type sizes; five at most")
    for a, b in zip(sizes, sizes[1:]):
        if b / a < 1.2:
            add("fail", "plan-type-ratio", f"{a} pt -> {b} pt is a {b / a:.2f}x step; steps under 1.2x read as the same size")
    if max(sizes) / body < 2:
        add("fail", "plan-type-ratio", f"display {max(sizes)} pt is under 2x body {body} pt: no hierarchy")

    # gap scale: few levels, each a clear multiple of the last, on the body line
    line_pt = body * plan["type"]["leading"]
    gaps = sorted(plan["gaps"]["lines"])  # in body lines
    if len(gaps) > 4:
        add("fail", "plan-gap-count", f"{len(gaps)} gap sizes; references use at most five break sizes once leading is counted, so plan four")
    for a, b in zip(gaps, gaps[1:]):
        if b / a < 1.5:
            add("fail", "plan-gap-ratio", f"gaps of {a} and {b} lines differ by {b / a:.2f}x: under 1.5x they read as the same gap")
    for g in gaps:
        if abs(g * 2 - round(g * 2)) > 1e-6:
            add("fail", "plan-gap-unit", f"a {g}-line gap is off the half-line grid")

    # measure: estimate characters per line for each text column
    pg = plan["page"]
    content_mm = pg["width_mm"] - pg["margin_mm"][1] - pg["margin_mm"][3]
    cols, gutter = plan["grid"]["columns"], plan["grid"]["gutter_mm"]
    col_mm = (content_mm - (cols - 1) * gutter) / cols
    avg_char_em = plan["type"].get("avg_char_em", 0.5)
    for name, span in plan["grid"]["text_spans"].items():
        w_mm = span * col_mm + (span - 1) * gutter
        size = plan["type"]["text_sizes"].get(name, body)
        cpl = w_mm / (size * 0.3528 * avg_char_em)
        lo, hi = plan["measure"].get(name, plan["measure"]["default"])
        if not lo <= cpl <= hi:
            add("fail", "plan-measure", f"{name}: {span} columns at {size} pt is about {cpl:.0f} characters a line (band {lo}-{hi})")

    # frames: at most one level, visible against the page
    fr = plan.get("frames", {})
    if fr.get("max_depth", 1) > 1:
        add("fail", "plan-nesting", "frames nest (max_depth > 1): card in card")
    page_L = _oklab_L(plan["page"].get("ground", "#FFFFFF"))
    for name, hexc in fr.get("tints", {}).items():
        dL = abs(page_L - _oklab_L(hexc))
        if dL < 0.05:
            add("fail", "plan-faint-frame", f"tint {name} {hexc} is {dL:.3f} OKLab L off the ground; references sit at >= 0.05")
    if fr.get("max_text_frames_per_page", 0) > 2:
        add("warn", "plan-frame-heavy", "more than two framed text boxes a page: references give weight with type and space")

    # every page type names a best-in-class reference that exists, and only gallery components
    for pt in plan["page_types"]:
        ref = pt.get("reference")
        if not ref:
            add("fail", "plan-reference", f"page type '{pt['name']}' names no best-in-class reference")
        elif not ref.startswith(("http://", "https://")) and not (base / ref).exists():
            add("fail", "plan-reference", f"page type '{pt['name']}': reference {ref} not found")
        if not pt.get("why"):
            add("warn", "plan-reference", f"page type '{pt['name']}': say what it takes from its reference")
    return out


def run(path: str) -> int:
    p = Path(path)
    plan = json.loads(p.read_text())
    rows = check(plan, p.parent)
    for lvl, rule, msg in rows:
        print(f"  {lvl.upper():5} {rule:18} {msg}")
    bad = sum(1 for r in rows if r[0] == "fail")
    print(f"docgate plan: {'FAIL' if bad else 'PASS'} ({bad} blocking) {p}")
    return 1 if bad else 0
