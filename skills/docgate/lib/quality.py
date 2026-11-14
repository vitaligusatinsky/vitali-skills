"""quality.py: measured layout-quality metrics for any PDF page.

docgate's DOM rules catch defects in documents we build. This module measures the
relational qualities a designer judges ("cramped", "card in card", "no ratio between
sizes and gaps", "poor visibility of boundaries") from the PDF alone: text-line geometry
from `pdftotext -bbox-layout` and frame geometry from the raster. Because it needs no
DOM, the same numbers can be computed for best-in-class reference PDFs and for our own
renders, and every threshold is banded from those references (see calibrate.py).

All lengths are expressed in relative units so pages at any size compare:
  h  = the body text's font-box height on the page (proxy for body type size)
  P  = the body line pitch (baseline to baseline)
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DPI = 144
NS = "{http://www.w3.org/1999/xhtml}"


@dataclass
class Line:
    x0: float
    y0: float
    x1: float
    y1: float          # pdftotext font box, in px at DPI
    text: str
    block: int
    iy0: float = 0.0   # ink top / bottom, measured on the raster
    iy1: float = 0.0

    @property
    def h(self):
        return self.y1 - self.y0

    @property
    def caps(self):
        letters = re.sub(r"[^A-Za-zÅÄÖåäöÜü]", "", self.text)
        return len(letters) >= 3 and letters.isupper()


@dataclass
class Frame:
    x0: int
    y0: int
    x1: int
    y1: int
    color: tuple
    area: float
    parent: int = -1          # index of the enclosing frame, -1 = page
    depth: int = 1
    contrast: float = 0.0     # OKLab lightness difference to the enclosing ground
    lines: list = field(default_factory=list)
    inset_top: float | None = None
    inset_left: float | None = None
    text_h: float = 0.0


@dataclass
class PageReport:
    page: int
    w: int
    h: int
    body_h: float
    pitch: float
    lines: list
    frames: list
    metrics: dict
    findings: list


def _oklab_L(rgb):
    c = np.asarray(rgb, dtype=float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    return 0.2104542553 * np.cbrt(l) + 0.7936177850 * np.cbrt(m) - 0.0040720468 * np.cbrt(s)


def raster(pdf: Path, page: int, dpi: int = DPI) -> np.ndarray:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "p"
        subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page), "-l", str(page),
                        "-png", "-singlefile", str(pdf), str(out)], check=True,
                       capture_output=True)
        return np.asarray(Image.open(str(out) + ".png").convert("RGB"))


def text_lines(pdf: Path, page: int, dpi: int = DPI) -> list[Line]:
    out = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-bbox-layout",
                          str(pdf), "-"], check=True, capture_output=True).stdout
    out = re.sub(rb"<!DOCTYPE[^>]*>", b"", out)
    root = ET.fromstring(out)
    k = dpi / 72.0
    lines, b = [], 0
    for blk in root.iter(NS + "block"):
        b += 1
        for ln in blk.iter(NS + "line"):
            words = [w.text or "" for w in ln.iter(NS + "word")]
            t = " ".join(words).strip()
            if not t:
                continue
            g = {a: float(ln.get(a)) * k for a in ("xMin", "yMin", "xMax", "yMax")}
            lines.append(Line(g["xMin"], g["yMin"], g["xMax"], g["yMax"], t, b))
    return lines


def _ink_extent(lum, ln: Line, ground):
    """Rows of real ink inside a line's box: the run of dark rows nearest the box centre."""
    H, W = lum.shape
    x0, x1 = max(0, int(ln.x0)), min(W, int(ln.x1) + 1)
    y0, y1 = max(0, int(ln.y0) - 2), min(H, int(ln.y1) + 2)
    if x1 <= x0 or y1 <= y0:
        return ln.y0, ln.y1
    band = lum[y0:y1, x0:x1]
    ink = (band < ground - 0.18).sum(axis=1) > max(1, 0.002 * (x1 - x0))
    rows = np.flatnonzero(ink)
    if rows.size == 0:
        return ln.y0, ln.y1
    # split into runs and keep the run nearest the box centre (the box overlaps neighbours)
    runs = np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1)
    c = (ln.y0 + ln.y1) / 2 - y0
    best = min(runs, key=lambda r: 0 if r[0] <= c <= r[-1] else min(abs(r[0] - c), abs(r[-1] - c)))
    return y0 + best[0], y0 + best[-1] + 1


def _frames(full, lines, body_px, ground=None):
    """Flat light-coloured rectangles (tint panels, cards) and how they nest.

    Found at half resolution: a colour mask is closed with a kernel just larger than a
    text line, so the text inside a panel does not punch holes in it, and a component
    counts as a frame only if most of its pixels really are that flat colour.
    """
    img = full[::2, ::2]
    body_px = body_px / 2
    H, W = img.shape[:2]
    q = (img // 4).astype(np.int32)
    key = (q[..., 0] << 12) | (q[..., 1] << 6) | q[..., 2]
    lum = _oklab_L(img)
    light = lum > 0.62
    vals, counts = np.unique(key[light], return_counts=True)
    order = np.argsort(-counts)
    page_area = H * W
    k = max(5, int(body_px * 0.8)) | 1
    se = np.ones((k, k), bool)
    frames = []
    seen = np.zeros((H, W), bool)
    for i in order[:12]:
        if counts[i] < 0.004 * page_area:
            break
        v = vals[i]
        c = np.array([(v >> 12) & 63, (v >> 6) & 63, v & 63]) * 4 + 2
        raw = np.abs(img.astype(int) - c).max(axis=2) <= 5
        mask = ndimage.binary_closing(raw, structure=se, border_value=1)
        lab, n = ndimage.label(mask)
        if n == 0:
            continue
        objs = ndimage.find_objects(lab)
        for j, sl in enumerate(objs, start=1):
            ys, xs = sl
            bw, bh = xs.stop - xs.start, ys.stop - ys.start
            comp = lab[sl] == j
            area = comp.sum()
            filled = ndimage.binary_fill_holes(comp).sum()  # a card inside punches a hole: judge the outline
            touches = ys.start <= 1 or xs.start <= 1 or ys.stop >= H - 1 or xs.stop >= W - 1
            if area < 0.003 * page_area or min(bw, bh) < 2.5 * body_px:
                continue
            if filled / (bw * bh) < 0.82:
                continue
            if (raw[sl] & comp).sum() / area < 0.6:
                continue  # a text block, not a flat fill
            if touches and filled > 0.5 * page_area:
                continue  # the page ground itself
            region = seen[sl]
            if region.mean() > 0.9:
                continue
            frames.append(Frame(2 * xs.start, 2 * ys.start, 2 * xs.stop, 2 * ys.stop,
                                tuple(int(t) for t in c), float(area) * 4))
            seen[sl] |= (lab[sl] == j)
    # merge near-duplicates (same rect found from two close colours)
    frames.sort(key=lambda f: -f.area)
    uniq = []
    for f in frames:
        if any(abs(f.x0 - u.x0) < 4 and abs(f.y0 - u.y0) < 4 and abs(f.x1 - u.x1) < 4
               and abs(f.y1 - u.y1) < 4 for u in uniq):
            continue
        uniq.append(f)
    frames = uniq
    # nesting: the smallest frame that contains this one
    for i, f in enumerate(frames):
        best = -1
        for j, g in enumerate(frames):
            if j == i or g.area <= f.area:
                continue
            if g.x0 - 2 <= f.x0 and g.y0 - 2 <= f.y0 and f.x1 <= g.x1 + 2 and f.y1 <= g.y1 + 2:
                if best < 0 or g.area < frames[best].area:
                    best = j
        f.parent = best
    ground = ground if ground is not None else _page_ground(full)
    for f in frames:
        d, p = 1, f.parent
        while p >= 0:
            d, p = d + 1, frames[p].parent
        f.depth = d
        outer = frames[f.parent].color if f.parent >= 0 else ground
        f.contrast = float(abs(_oklab_L(np.array(f.color)) - _oklab_L(np.array(outer))))
    return frames


def _page_ground(img):
    # one packed integer per pixel: np.unique on rows sorts the same way but is ~10x slower
    q = (img[::4, ::4] // 4).reshape(-1, 3).astype(np.int32)
    vals, counts = np.unique((q[:, 0] << 16) | (q[:, 1] << 8) | q[:, 2], return_counts=True)
    v = int(vals[np.argmax(counts)])
    return tuple(int(t) * 4 + 2 for t in ((v >> 16) & 255, (v >> 8) & 255, v & 255))


def _weighted_median(vals, weights):
    o = np.argsort(vals)
    v, w = np.asarray(vals)[o], np.asarray(weights)[o]
    cw = np.cumsum(w)
    return float(v[np.searchsorted(cw, cw[-1] / 2)])


def analyze_page(pdf: Path, page: int) -> PageReport:
    img = raster(pdf, page)
    H, W = img.shape[:2]
    lum = _oklab_L(img)
    lines = text_lines(pdf, page)
    ground = _page_ground(img)
    gL = float(_oklab_L(np.array(ground)))
    for ln in lines:
        ln.iy0, ln.iy1 = _ink_extent(lum, ln, min(gL, float(np.median(
            lum[max(0, int(ln.y0)):int(ln.y1) + 1, max(0, int(ln.x0)):int(ln.x1) + 1]) + 0.05)))
    metrics, findings = {}, []
    if len(lines) < 3:
        return PageReport(page, W, H, 0, 0, lines, [], {"sparse": True}, [])
    body_h = _weighted_median([l.h for l in lines], [len(l.text) for l in lines])
    # body pitch: consecutive lines in a block with body-size boxes, overlapping in x
    pitches = []
    for a, b in zip(lines, lines[1:]):
        if a.block == b.block and abs(a.h - body_h) < 0.15 * body_h and abs(b.h - body_h) < 0.15 * body_h \
                and min(a.x1, b.x1) > max(a.x0, b.x0) and 0 < b.y0 - a.y0 < 2.2 * body_h:
            pitches.append(b.y0 - a.y0)
    pitch = float(np.median(pitches)) if pitches else body_h
    frames = _frames(img, lines, body_h, ground)
    for f in frames:
        inside = [l for l in lines if f.x0 - 1 <= l.x0 and l.x1 <= f.x1 + 1
                  and f.y0 - 1 <= l.iy0 and l.iy1 <= f.y1 + 1]
        # only lines not inside a child frame
        kids = [g for g in frames if frames.index(g) != frames.index(f) and g.parent == frames.index(f)]
        own = [l for l in inside if not any(g.x0 <= l.x0 and l.x1 <= g.x1 and g.y0 <= l.iy0
                                           and l.iy1 <= g.y1 for g in kids)]
        f.lines = own
        if own:
            f.text_h = max(l.h for l in own)
            f.inset_top = (min(l.iy0 for l in own) - f.y0) / pitch
            f.inset_left = (min(l.x0 for l in own) - f.x0) / pitch
    metrics.update(_relational(lines, frames, body_h, pitch, W, H))
    return PageReport(page, W, H, body_h, pitch, lines, frames, metrics, findings)


def _column_neighbours(lines, i):
    """The nearest line above and below line i that shares its column (x-overlap)."""
    a = lines[i]
    above = below = None
    for j, b in enumerate(lines):
        if j == i or min(a.x1, b.x1) - max(a.x0, b.x0) < 0.25 * min(a.x1 - a.x0, b.x1 - b.x0):
            continue
        if b.iy1 <= a.iy0 + 1 and (above is None or b.iy1 > above.iy1):
            above = b
        if b.iy0 >= a.iy1 - 1 and (below is None or b.iy0 < below.iy0):
            below = b
    return above, below


def _relational(lines, frames, body_h, pitch, W, H):
    m = {}
    # 1. heading/label proximity: space above a heading vs below it (ink to ink)
    ratios, cramped_above = [], []
    for i, ln in enumerate(lines):
        is_head = ln.h >= 1.25 * body_h or (ln.caps and len(ln.text) <= 40)
        if not is_head:
            continue
        above, below = _column_neighbours(lines, i)
        if above is None or below is None:
            continue
        if ln.h >= 1.25 * body_h and abs(above.h - ln.h) < 0.1 * ln.h:
            continue  # the second or later line of a wrapped heading
        if ln.h >= 1.25 * body_h and below.h >= 1.25 * body_h:
            continue  # a multi-line heading
        ga, gb = ln.iy0 - above.iy1, below.iy0 - ln.iy1
        if ga > 6 * pitch or gb > 3 * pitch or gb <= 0:
            continue
        ratios.append((ga / gb, ln.text[:40], ga / pitch, gb / pitch))
    m["heading_ratios"] = ratios
    m["heading_ratio_min"] = min((r[0] for r in ratios), default=None)
    m["heading_ratio_med"] = float(np.median([r[0] for r in ratios])) if ratios else None
    # 2. frames: nesting, contrast, inset relative to the frame's own type
    m["frames"] = len(frames)
    m["frame_depth_max"] = max((f.depth for f in frames), default=0)
    texty = [f for f in frames if f.lines]
    m["frame_inset_min"] = min((min(f.inset_top, f.inset_left) * pitch / f.text_h for f in texty),
                               default=None)
    m["frame_contrast_min"] = min((f.contrast for f in frames), default=None)
    # 3. mid-size text (a lede or callout, 1.3-2.2x body) wrapped as prose in a narrow
    # box (an open pull-quote column is fine; a big question crammed in a card is not): >= 4 lines, continuation lines starting lower-case, under 34 characters a line.
    # Display titles (>2.2x) and short item lists (addresses, labels) are excluded.
    blocks = {}
    for ln in lines:
        if 1.3 * body_h <= ln.h < 2.2 * body_h:
            blocks.setdefault(ln.block, []).append(ln)
    narrow = []
    for b, ls in blocks.items():
        if len(ls) < 4:
            continue
        cpl = float(np.mean([len(l.text) for l in ls]))
        cont = sum(1 for l in ls[1:] if l.text[:1].islower() and ' ' in l.text) / (len(ls) - 1)
        boxed = any(f.x0 <= ls[0].x0 and ls[0].x1 <= f.x1 and f.y0 <= ls[0].iy0 <= f.y1
                    for f in frames)
        if cpl < 34 and cont >= 0.5 and boxed:
            narrow.append((len(ls), round(cpl, 1), ls[0].text[:40]))
    m["large_blocks"] = narrow
    # 4. density: share of the content box covered by text ink boxes
    if lines:
        x0 = min(l.x0 for l in lines); x1 = max(l.x1 for l in lines)
        y0 = min(l.iy0 for l in lines); y1 = max(l.iy1 for l in lines)
        cover = np.zeros((H, W), bool)
        for l in lines:
            cover[int(l.iy0):int(l.iy1) + 1, int(l.x0):int(l.x1) + 1] = True
        m["ink_cover"] = float(cover[int(y0):int(y1) + 1, int(x0):int(x1) + 1].mean())
        m["margin_side"] = float(min(x0, W - x1) / W)
        m["margin_top"] = float(y0 / H)
    # 5. small text wrapped in narrow columns (squeezed labels and values)
    byb = {}
    for ln in lines:
        byb.setdefault(ln.block, []).append(ln)
    squeezed = 0
    for ls in byb.values():
        small = [l for l in ls if l.h <= 1.05 * body_h]
        if len(small) >= 2 and np.mean([len(l.text) for l in small]) < 16:
            squeezed += len(small)
    m["squeezed_lines"] = squeezed
    m["squeezed_share"] = squeezed / max(1, len(lines))
    # 6. display type wrapped: the longest run of consecutive display-size lines
    run = best = 0
    prev = None
    for ln in lines:
        if ln.h >= 1.8 * body_h and prev is not None and prev.block == ln.block and prev.h >= 1.8 * body_h:
            run += 1
        else:
            run = 1 if ln.h >= 1.8 * body_h else 0
        best = max(best, run)
        prev = ln
    m["display_lines"] = best
    # 7. alignment axes: distinct left edges that start at least two lines
    xs = sorted(l.x0 for l in lines)
    axes, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] <= 0.3 * pitch:
            cur.append(x)
        else:
            axes.append(cur); cur = [x]
    axes.append(cur)
    m["axes"] = sum(1 for a in axes if len(a) >= 2)
    m["axes_per_100_lines"] = 100 * m["axes"] / len(lines)
    # 7b. body text set narrow (critic, round 1: "30-35 characters a line ... garbled") and
    # widows: a paragraph whose last line is a single short word.
    narrow_body, widows = [], 0
    for ls in byb.values():
        body = [l for l in ls if abs(l.h - body_h) < 0.12 * body_h]
        if len(body) >= 4:
            cpl = float(np.mean([len(l.text) for l in body[:-1]]))
            if cpl < 40:
                narrow_body.append((len(body), round(cpl, 1), body[0].text[:30]))
        if len(body) >= 3 and " " not in body[-1].text.strip() and len(body[-1].text) <= 12:
            widows += 1
    m["narrow_body"] = narrow_body
    m["widows"] = widows
    # 8. vertical rhythm: every gap between stacked lines in a column, in body pitches.
    # A gap should read either as leading (ink gap < 0.7 P) or as a break (>= 1.15 P);
    # gaps in between neither join nor separate ("no ratio between gaps", "glued").
    vg, gap_pairs = [], []
    for i, ln in enumerate(lines):
        _, below = _column_neighbours(lines, i)
        if below is not None:
            g = (below.iy0 - ln.iy1) / pitch
            if 0 < g < 8:
                vg.append(g)
                gap_pairs.append((g, ln.text[:40], below.text[:40], round(ln.iy1 / DPI * 25.4, 1)))
    amb = [g for g in vg if 0.7 <= g < 1.15]
    m["gaps"] = len(vg)
    m["ambiguous_gaps"] = len(amb)
    m["ambiguous_share"] = len(amb) / max(1, len(vg))
    m["gap_list"] = [round(g, 2) for g in vg]
    m["gap_pairs"] = gap_pairs
    # gap levels: cluster the break-size gaps (>= 0.7 P); a designed page uses a few
    # levels with a clear ratio between them (e.g. 1, 2, 4 lines), not a smear.
    brk = sorted(g for g in vg if g >= 0.7)
    levels, cur = [], []
    for g in brk:
        if cur and g > np.mean(cur) * 1.18:
            levels.append(cur); cur = []
        cur.append(g)
    if cur:
        levels.append(cur)
    lv = [float(np.mean(c)) for c in levels if len(c) >= 2]
    m["gap_levels"] = [round(x, 2) for x in lv]
    m["gap_level_count"] = len(lv)
    m["gap_level_ratio_min"] = min((b / a for a, b in zip(lv, lv[1:])), default=None)
    # 9. type steps on the page
    hs = sorted({round(l.h / body_h, 1) for l in lines})
    m["type_steps"] = hs
    m["display_ratio"] = float(max(l.h for l in lines) / body_h)
    return m


# Thresholds are banded from best-in-class reference reports (Nesta, Design Council,
# Sitra, Demos Helsinki: 148 pages) so that no reference page fails, and checked against
# the owner-rejected versions of a client report (see the calibration log in SKILL.md).
PROFILE = {
    "faintFrameDL": 0.04,     # reference frames never sit below 0.05 OKLab L from their ground
    "maxGapLevels": 6,        # references use at most 5 distinct break sizes on a page
    "warnGapLevels": 5,
    "warnTextFrames": 3,      # references frame text on 15% of pages, rarely more than 2 frames
}


def evaluate(r: PageReport, prof: dict = PROFILE) -> list[dict]:
    """Findings for one page: {rule, severity, detail}."""
    out = []
    m = r.metrics
    tf = [f for f in r.frames if f.lines]
    nest = [f for f in tf if f.depth >= 2]
    if nest:
        out.append(dict(rule="nested-frame", severity="fail",
                        detail=f"{len(nest)} framed boxes with text sit inside another frame (card in card)"))
    faint = [f for f in tf if 0.005 <= f.contrast < prof["faintFrameDL"]]
    if faint:
        out.append(dict(rule="faint-frame", severity="fail",
                        detail=f"{len(faint)} text frames barely differ from their ground (OKLab dL "
                               f"{min(f.contrast for f in faint):.3f} < {prof['faintFrameDL']}): the boundary is not visible"))
    if m.get("large_blocks"):
        n, cpl, t = m["large_blocks"][0]
        out.append(dict(rule="large-narrow", severity="fail",
                        detail=f"lede/callout-size text wrapped in a narrow column: {n} lines at {cpl} characters "
                               f"[{t}]"))
    lv = m.get("gap_level_count", 0)
    if m.get("gaps", 0) >= 10 and lv >= prof["maxGapLevels"]:
        out.append(dict(rule="gap-levels", severity="fail",
                        detail=f"{lv} different break sizes on one page {m['gap_levels']} (pitches): no clear ratio between gaps"))
    elif m.get("gaps", 0) >= 10 and lv >= prof["warnGapLevels"]:
        out.append(dict(rule="gap-scale", severity="warn",
                        detail=f"{lv} break sizes on one page {m['gap_levels']} (pitches): references use at most 5"))
    if len(tf) >= prof["warnTextFrames"]:
        out.append(dict(rule="frame-heavy", severity="warn",
                        detail=f"{len(tf)} framed text boxes on one page: give weight with type and space, not boxes"))
    return out


def _analyze_one(args):
    pdf, p = args
    r = analyze_page(pdf, p)
    return r, (evaluate(r) if r.body_h else [])


def analyze(pdf: Path, pages=None, workers: int | None = None) -> list[tuple[PageReport, list]]:
    """Per-page reports and findings, in page order. Pages are independent, so they run in
    parallel processes; the numbers are the same as a serial run."""
    pages = list(pages or range(1, page_count(pdf) + 1))
    n = workers if workers is not None else min(8, os.cpu_count() or 1, len(pages))
    if n <= 1 or len(pages) <= 1:
        return [_analyze_one((pdf, p)) for p in pages]
    try:  # fork: spawn would re-import the caller's __main__ (and re-run an unguarded script)
        with ProcessPoolExecutor(max_workers=n, mp_context=multiprocessing.get_context("fork")) as ex:
            return list(ex.map(_analyze_one, [(pdf, p) for p in pages]))
    except (ValueError, BrokenProcessPool):  # no fork here, or a worker died: do it serially
        return [_analyze_one((pdf, p)) for p in pages]


def explain(r: PageReport, findings: list) -> list[str]:
    """For each finding, the actual lines, gaps or frames that cause it, so the fix needs no
    ad-hoc script. Positions are mm from the top of the page, to the foot of the upper line."""
    out = []
    mm = lambda px: px / DPI * 25.4
    for f in findings:
        rule, m = f["rule"], r.metrics
        out.append(f"  p{r.page:02d} {rule}: {f['detail']}")
        if rule in ("gap-levels", "gap-scale"):
            brk = sorted((p for p in m.get("gap_pairs", []) if p[0] >= 0.7), key=lambda p: p[0])
            levels, cur = [], []
            for p in brk:
                if cur and p[0] > np.mean([c[0] for c in cur]) * 1.18:
                    levels.append(cur)
                    cur = []
                cur.append(p)
            if cur:
                levels.append(cur)
            for lv in levels:
                tag = f"level {np.mean([c[0] for c in lv]):.2f} P x{len(lv)}" if len(lv) >= 2 else "single (not a level)"
                out.append(f"      {tag}")
                for g, a, b, y in lv:
                    out.append(f'        {g:5.2f} P  y={y:6.1f}mm  "{a}"  ->  "{b}"')
        elif rule in ("nested-frame", "faint-frame", "frame-heavy"):
            for fr in r.frames:
                if not fr.lines:
                    continue
                if rule == "nested-frame" and fr.depth < 2:
                    continue
                if rule == "faint-frame" and not 0.005 <= fr.contrast < PROFILE["faintFrameDL"]:
                    continue
                out.append(f'      frame depth {fr.depth} dL {fr.contrast:.3f}  x={mm(fr.x0):.0f}-{mm(fr.x1):.0f}mm '
                           f'y={mm(fr.y0):.0f}-{mm(fr.y1):.0f}mm  "{fr.lines[0].text[:40]}"')
        elif rule == "large-narrow":
            for n, cpl, t in m.get("large_blocks", []):
                out.append(f'      {n} lines, {cpl} characters a line: "{t}"')
    return out


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


if __name__ == "__main__":
    import json, sys
    pdf = Path(sys.argv[1])
    verbose = "-v" in sys.argv
    args = [a for a in sys.argv[2:] if a != "-v"]
    pages = [int(p) for p in args[0].split(",")] if args else None
    bad = 0
    for r, fs in analyze(pdf, pages):
        for f in fs:
            bad += f["severity"] == "fail"
            print(f"  p{r.page:02d} {f['severity'].upper():5s} {f['rule']:13s} {f['detail']}")
        if verbose:
            mm = {k: v for k, v in r.metrics.items() if k not in ("heading_ratios", "gap_list", "gap_pairs")}
            print(f"  p{r.page:02d} metrics", json.dumps(mm, ensure_ascii=False, default=str))
    sys.exit(1 if bad else 0)
