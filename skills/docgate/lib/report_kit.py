"""report_kit: builder helpers for printed A4 client reports on report-base.css.

Promoted from the approved a client builder (the approved version):
measured-glyph text wrapping for SVG, the vertical swimlane generator, a bar chart,
Finnish typographic quotes, and page assembly. Render the result with `docgate render`.

    import sys, os; sys.path.insert(0, os.path.expanduser("~/.claude/skills/docgate/lib"))
    import report_kit as rk
    html = rk.page(body_html, footer="Report 13.11.2026", lang="fi")

Fonts: brand TTFs are local (licensed, never committed to a public repo). Set REPORT_FONTS
to the folder holding nohemi/Nohemi-VF.ttf and landour-full/Landour-VF.ttf; the default is
~/1git/vitali-consulting/public/fonts.

Every SVG text size here is a step of the type scale: diagrams use the 7 pt label step
(LABEL_PX), so diagram text is never smaller than the smallest HTML text.
"""
import os
import re
from html import escape
from pathlib import Path

KIT = Path(__file__).resolve().parent
BASE_CSS = KIT.parent / "assets" / "report-base.css"
FONTS = Path(os.environ.get("REPORT_FONTS", os.path.expanduser("~/1git/vitali-consulting/public/fonts")))
FONT_FILES = {"Nohemi": FONTS / "nohemi" / "Nohemi-VF.ttf", "Landour": FONTS / "landour-full" / "Landour-VF.ttf"}

PT = 96 / 72
LABEL_PX = 7 * PT          # 9.33 px: the label step
BODY_PX = 8.8 * PT         # 11.73 px: the body step

INK, INK2, MUTED, ACCENT, WARN, WARN_DOT = "#1C171B", "#3D3147", "#6D5A7D", "#473855", "#9A3412", "#C2410C"
LINE, BOX = "#6D5A7D", "#3D3147"  # connectors and box outlines: softer than ink
LANE_TINT, SYS_TINT = "#F0EAE3", "#F1E6EC"  # >= 0.06 OKLab L off white (faint-frame)


# ----------------------------------------------------------------------------- page assembly
def fonts_css():
    return "\n".join(
        f"@font-face {{ font-family:'{fam}'; src:url('{path.as_uri()}') format('truetype-variations'); font-weight:100 900; }}"
        for fam, path in FONT_FILES.items())


def page_css(footer, margins="16mm 18mm 16mm 18mm"):
    f = footer.replace('"', '\\"')
    return (f"@page {{ size:A4 portrait; margin:{margins};\n"
            f"  @bottom-left {{ content:\"{f}\"; font-family:'Nohemi', sans-serif; font-size:7pt; color:#6D5A7D; }}\n"
            f"  @bottom-right {{ content:counter(page) \" / \" counter(pages); font-family:'Nohemi', sans-serif; font-size:7pt; color:#6D5A7D; }} }}")


def css(footer, extra=""):
    """The full stylesheet: fonts, page, base, then any document-specific additions."""
    return "\n".join([fonts_css(), page_css(footer), BASE_CSS.read_text(encoding="utf-8"), extra])


def finnish_quotes(html):
    """Straight double quotes in text nodes -> Finnish typographic quotes (” both sides)."""
    parts = re.split(r"(<style.*?</style>|<script.*?</script>|<[^>]+>)", html, flags=re.S)
    return "".join(p if p.startswith("<") else p.replace('"', "”") for p in parts)


# ----------------------------------------------------------------------------- measured text
_FONT_CACHE = {}


def _font(family, weight, size):
    """The font at this weight and, for fonts with an optical-size axis, the optical size
    Chrome will use (font-optical-sizing: auto sets opsz to the CSS px size). Measuring at the
    default opsz under-measures small text: Landour at 9.3 px is about 3% wider than at opsz 72."""
    from PIL import ImageFont
    axes_key = None
    f = _FONT_CACHE.get(("base", family))
    if f is None:
        f = ImageFont.truetype(str(FONT_FILES[family]), 100)  # measure at 100 px, scale linearly
        _FONT_CACHE[("base", family)] = f
    try:
        axes = f.get_variation_axes()
    except Exception:
        return f
    vals = []
    for ax in axes:
        name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
        if name == "Weight":
            vals.append(weight)
        elif name == "Optical Size":
            vals.append(min(max(size, ax["minimum"]), ax["maximum"]))
        else:
            vals.append(ax["default"])
    axes_key = (family, tuple(vals))
    if axes_key not in _FONT_CACHE:
        g = ImageFont.truetype(str(FONT_FILES[family]), 100)
        g.set_variation_by_axes(vals)
        _FONT_CACHE[axes_key] = g
    return _FONT_CACHE[axes_key]


def text_w(s, size, weight=400, family="Nohemi"):
    return _font(family, weight, size).getlength(s) * size / 100


def wrap_px(text, max_px, size, weight=400, family="Nohemi"):
    """Wrap on measured glyph widths. Words may break after '-' or at a soft hyphen (shown as '-')."""
    lines, cur = [], ""
    for word in text.split():
        parts = re.split("(?<=[-­])", word)
        prev_soft = False
        for k, part in enumerate(parts):
            vis = part.replace("­", "")
            trial = cur + (" " if (k == 0 and cur) else "") + vis
            if cur and text_w(trial, size, weight, family) > max_px:
                lines.append(cur + ("-" if (k > 0 and prev_soft) else ""))
                cur = vis
            else:
                cur = trial
            prev_soft = part.endswith("­")
    if cur:
        lines.append(cur)
    return lines


def t(x, y, s, size, weight=400, fill=INK, family="Nohemi", anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size:.2f}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


# ----------------------------------------------------------------------------- vertical swimlane
class Swimlane:
    """Steps run down, roles are columns, an optional systems column on the right.

    spec = {
      "steps": [names...], "lanes": [(key, name)...],
      "nodes": [(id, step_row, lane_key, title, detail, break_note_or_None)...],
      "edges": [(from_id, to_id)...],
      "systems": [text per step], "systems_label": "...", "systems_framed": bool,
      "votes": {step_row: n}, "vote_word": ("tarra", "tarraa"),
    }
    Build two diagrams on one row grid with rows=Swimlane.shared_rows(a, b) so they line up.
    """
    W, STEP_W, SYS_W, GAP, HEAD_H, PAD = 658, 74, 92, 4, 26, 5
    EXIT = 6                               # vertical connectors leave a box this far from its edge
    FT = FD = FB = LABEL_PX               # title, detail, break note: all the label step
    LT, LD, LB = 10.8, 10.3, 10.3          # line heights (1.16 x the label step, 1.1 for detail)

    def __init__(self, spec):
        self.s = spec
        self.lane_w = (self.W - self.STEP_W - self.SYS_W - self.GAP * 2) / len(spec["lanes"])
        self.box_w = self.lane_w - 6
        # which side a vertical connector leaves each box from, so its break note stays clear of it
        order = {key: i for i, (key, _) in enumerate(spec["lanes"])}
        where = {n[0]: (n[1], order[n[2]]) for n in spec["nodes"]}
        self.exit, self.below = {}, set()
        for a, b in spec["edges"]:
            (ra, la), (rb, lb) = where[a], where[b]
            if ra != rb:
                self.exit[a] = "left" if lb < la else "right"

    def note_x(self, nid, brk=None):
        """(start offset, max width) of a break note, clear of the lane its connector leaves
        through. A note whose longest word cannot fit beside that lane keeps the full width, and
        the connector starts below the note instead (self.below)."""
        side, lane = self.exit.get(nid), self.EXIT + 5
        if side and brk:
            room = self.box_w - (lane + 6 if side == "left" else 9 + lane)
            if max(text_w(w, self.FB, 500) for w in brk.split()) > room:
                self.below.add(nid)
                return 9, self.box_w - 9
        if side == "left":
            return lane + 6, self.box_w - lane - 6
        if side == "right":
            return 9, self.box_w - 9 - lane
        return 9, self.box_w - 9

    def _fit(self, lines, max_px, size, weight, what):
        for ln in lines:
            if text_w(ln, size, weight) > max_px + 0.5:
                raise ValueError(f"swimlane: '{ln}' in {what} is {text_w(ln, size, weight):.0f}px, the box allows {max_px:.0f}px. "
                                 f"Break the word with a soft hyphen (\\u00ad) or shorten it.")
        return lines

    def node_metrics(self, title, detail, brk, nid=None):
        inner = self.box_w - 2 * self.PAD
        tl = self._fit(wrap_px(title, inner, self.FT, 600), inner, self.FT, 600, f"the title of {nid}")
        dl = self._fit(wrap_px(detail, inner, self.FD), inner, self.FD, 400, f"the detail of {nid}") if detail else []
        bl = wrap_px(brk, self.note_x(nid, brk)[1], self.FB, 500) if brk else []
        box_h = 6 + len(tl) * self.LT + (2 if dl else 0) + len(dl) * self.LD + 5
        total = box_h + (6 + len(bl) * self.LB if bl else 0)
        return tl, dl, bl, box_h, total

    def row_heights(self):
        return self.keep_drops(self.base_rows())

    def base_rows(self):
        s = self.s
        rows = [28.0] * len(s["steps"])
        for nid, row, lane, title, detail, brk in s["nodes"]:
            total = self.node_metrics(title, detail, brk, nid)[4]  # measures the note, and so decides self.below
            # a box whose arrow leaves from under its note sits at the top of its row, with the run-in below it
            rows[row] = max(rows[row], total + (self.RUN_IN + 6 if nid in self.below else 2))
        for r, sys_text in enumerate(s.get("systems") or []):
            rows[r] = max(rows[r], len(wrap_px(sys_text, self.SYS_W - 20, self.FD)) * self.LD + 18)
        votes = s.get("votes") or {}
        for r, name in enumerate(s["steps"]):
            rows[r] = max(rows[r], len(wrap_px(name, self.STEP_W - 8, LABEL_PX, 600)) * 11 + (20 if r in votes else 8))
        return rows

    def keep_drops(self, rows):
        """Two boxes joined by a straight drop between neighbouring rows are centred in their rows, so the
        gap between them is the sum of the two slacks. Grow the lower row until that gap is at least
        MIN_DROP, so the arrow has a visible run-in. Takes the final (possibly shared) row heights."""
        rows = list(rows)
        where = {}
        for n in self.s["nodes"]:
            m = self.node_metrics(n[3], n[4], n[5], n[0])
            where[n[0]] = (n[1], n[2], m[4], m[3])  # row, lane, box plus note, box alone
        for a, b in self.s["edges"]:
            (ra, la, ta, ha), (rb, lb, tb, _) = where[a], where[b]
            if la == lb and rb == ra + 1 and a not in self.below and b not in self.below:
                gap = (rows[ra] - ta) / 2 + (ta - ha) + (rows[rb] - tb) / 2  # source box bottom to target box top
                if gap < self.MIN_DROP:
                    rows[rb] += 2 * (self.MIN_DROP - gap)
        return rows

    @staticmethod
    def shared_rows(*lanes):
        rows = [max(col) for col in zip(*(l.base_rows() for l in lanes))]
        for l in lanes:
            rows = [max(a, b) for a, b in zip(rows, l.keep_drops(rows))]
        return rows

    def svg(self, kind, rows=None):
        s, W, GAP, HEAD_H = self.s, self.W, self.GAP, self.HEAD_H
        rows = rows or self.row_heights()
        lane_x = {key: self.STEP_W + GAP + i * self.lane_w for i, (key, _) in enumerate(s["lanes"])}
        sys_x = self.STEP_W + GAP + len(s["lanes"]) * self.lane_w + GAP
        row_y = [HEAD_H]
        for h in rows[:-1]:
            row_y.append(row_y[-1] + h)
        H = row_y[-1] + rows[-1] + 2
        o = [f'<svg viewBox="0 0 {W} {H:.0f}" width="100%" xmlns="http://www.w3.org/2000/svg" role="img">',
             f'<defs><marker id="ah{kind}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" '
             f'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="{LINE}"/></marker></defs>']
        for key, name in s["lanes"]:
            x = lane_x[key]
            o.append(f'<rect x="{x + 1:.1f}" y="0" width="{self.lane_w - 2:.1f}" height="{H:.0f}" rx="6" fill="{LANE_TINT}"/>')
            for j, line in enumerate(wrap_px(name, self.lane_w - 12, LABEL_PX, 600, "Landour")):
                o.append(t(x + 6, 13 + j * 10.8, line, LABEL_PX, 600, family="Landour"))
        if s.get("systems"):
            o.append(f'<rect x="{sys_x:.1f}" y="0" width="{self.SYS_W:.1f}" height="{H:.0f}" rx="6" fill="{SYS_TINT}"/>')
            for j, line in enumerate(wrap_px(s["systems_label"], self.SYS_W - 14, LABEL_PX, 600, "Landour")):
                o.append(t(sys_x + 8, 13 + j * 10.8, line, LABEL_PX, 600, family="Landour"))
        votes = s.get("votes") or {}
        one, many = s.get("vote_word", ("vote", "votes"))
        for r, name in enumerate(s["steps"]):
            y = row_y[r]
            if r:
                o.append(f'<line x1="{self.STEP_W + GAP:.1f}" y1="{y:.1f}" x2="{W:.1f}" y2="{y:.1f}" stroke="#FFFFFF" stroke-width="2"/>')
            lines = wrap_px(name, self.STEP_W - 8, LABEL_PX, 600)
            for j, line in enumerate(lines):
                o.append(t(0, y + 14 + j * 11, line, LABEL_PX, 600))
            if kind == "current" and r in votes:
                n = votes[r]
                o.append(t(0, y + 14 + (len(lines) - 1) * 11 + 12.5, f"{n} {one if n == 1 else many}", LABEL_PX, 600, ACCENT))
            if s.get("systems"):
                sl = wrap_px(s["systems"][r], self.SYS_W - 20, self.FD)
                sh = len(sl) * self.LD + 8
                sy = y + (rows[r] - sh) / 2
                if s.get("systems_framed"):
                    o.append(f'<rect x="{sys_x + 6:.1f}" y="{sy:.1f}" width="{self.SYS_W - 12:.1f}" height="{sh:.1f}" rx="3" '
                             f'fill="#FFFFFF" stroke="{ACCENT}" stroke-width="0.8"/>')
                for j, line in enumerate(sl):
                    o.append(t(sys_x + 10, sy + 11 + j * self.LD, line, self.FD, 400, INK2))
        boxes, node_row, solid = {}, {}, {}
        for nid, row, lane, title, detail, brk in s["nodes"]:
            node_row[nid] = row
            tl, dl, bl, bh, total = self.node_metrics(title, detail, brk, nid)
            x = lane_x[lane] + 3
            y = row_y[row] + (3 if nid in self.below else (rows[row] - total) / 2)
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{self.box_w:.1f}" height="{bh:.1f}" rx="3" '
                     f'fill="#FFFFFF" stroke="{BOX}" stroke-width="0.8"/>')
            for j, line in enumerate(tl):
                o.append(t(x + self.PAD, y + 13 + j * self.LT, line, self.FT, 600))
            for j, line in enumerate(dl):
                o.append(t(x + self.PAD, y + 13 + (len(tl) - 1) * self.LT + 2 + self.LD + j * self.LD, line, self.FD, 400, MUTED))
            if bl:
                by = y + bh + 11
                nx = self.note_x(nid, brk)[0]
                o.append(f'<circle cx="{x + nx - 6:.1f}" cy="{by - 3:.1f}" r="2.4" fill="{WARN_DOT}"/>')
                for j, line in enumerate(bl):
                    o.append(t(x + nx, by + j * self.LB, line, self.FB, 500, WARN))
            # a connector leaving from under a full-width note starts below the note
            boxes[nid] = (x, y, self.box_w, (total + 2) if nid in self.below else bh)
            solid[nid] = (x - 2, y - 2, self.box_w + 4, total + 4)  # box plus its note: what a line must avoid
        for a, b in s["edges"]:
            others = [r for k, r in solid.items() if k not in (a, b)]
            o.append(self._edge(boxes[a], boxes[b], kind, others, self.EXIT))
        o.append("</svg>")
        return "\n".join(o)

    @staticmethod
    def _hits(seg, rects):
        x1, y1, x2, y2 = seg
        lo_x, hi_x, lo_y, hi_y = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
        return any(lo_x < rx + rw and hi_x > rx and lo_y < ry + rh and hi_y > ry for rx, ry, rw, rh in rects)

    MIN_DROP = 5.5  # least gap between two boxes joined by a straight drop: tip offset 1.5 plus a run above the 3.5-unit stub limit
    RUN_IN = 9  # the last straight run into a box: room for the arrowhead plus a visible line

    @classmethod
    def _edge(cls, A, B, kind, others, ex_off):
        """Route one connector. Every arrow ends with a straight run of at least RUN_IN
        into its target, its tip 1.5 units off the box edge."""
        ax, ay, aw, ah = A
        bx, by, bw, bh = B
        if by < ay + ah and by + bh > ay:  # rows overlap: horizontal at the shared middle
            my = (max(ay, by) + min(ay + ah, by + bh)) / 2
            p = (f"M{ax + aw:.1f},{my:.1f} H{bx - 1.5:.1f}" if bx > ax else f"M{ax:.1f},{my:.1f} H{bx + bw + 1.5:.1f}")
        elif abs(bx - ax) < 1:  # same lane: one straight drop
            sx = ax + aw - ex_off
            p = (f"M{sx:.1f},{ay + ah:.1f} V{by - 1.5:.1f}" if by > ay else f"M{sx:.1f},{ay:.1f} V{by + bh + 1.5:.1f}")
        else:
            right = bx > ax
            sx = ax + aw - ex_off if right else ax + ex_off
            sy = ay + ah if by > ay else ay
            # preferred: drop in the source lane, then enter the target from the side at its title
            my = by + 9.5
            tip = bx - 1.5 if right else bx + bw + 1.5
            if not cls._hits((sx, sy, sx, my), others) and not cls._hits((sx, my, tip, my), others):
                p = f"M{sx:.1f},{sy:.1f} V{my:.1f} H{tip:.1f}"
            else:  # fallback: enter from the top with a real run-in
                ex = bx + 10 if right else bx + bw - 10
                hy = by - cls.RUN_IN - 1.5 if by > ay else by + bh + cls.RUN_IN + 1.5
                end = by - 1.5 if by > ay else by + bh + 1.5
                p = f"M{sx:.1f},{sy:.1f} V{hy:.1f} H{ex:.1f} V{end:.1f}"
        return f'<path d="{p}" fill="none" stroke="{LINE}" stroke-width="1.2" stroke-linejoin="round" marker-end="url(#ah{kind})"/>'


# ----------------------------------------------------------------------------- phase pages
def phase_page(i, steps, title, facts, breaks, ask, now, goal, snags,
               labels=("Vaihe", "Missä tieto katkeaa", "Kysymys teille", "Nyt", "Tavoite", "Missä takkuaa")):
    """One page per step of a flow, the same frame every time (report-base `.phase`):
    the flow strip with this step highlighted, step number and title, facts as (label, html)
    pairs, where information breaks, the question, then now | target and the snags.
    Pass `labels` in the report's language."""
    step, brk_l, ask_l, now_l, goal_l, snag_l = labels
    flow = "".join(f'<span class="{"here" if k == i else ("done" if k < i else "")}">{name}</span>' for k, name in enumerate(steps))
    paras = lambda xs: "".join(f"<p>{x}</p>" for x in xs)
    return (
        '<section class="phase">'
        f'<div class="flow" style="--steps:{len(steps)}">{flow}</div>'
        '<div class="phase-head"><div class="who">'
        f'<div class="label step-no">{step} {i + 1} / {len(steps)}</div><h2>{title}</h2>'
        '<dl class="facts">' + "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in facts) + '</dl></div>'
        '<div class="why">'
        + (f'<div class="breaks"><div class="label">{brk_l}</div><ul>' + "".join(f"<li>{b}</li>" for b in breaks) + '</ul></div>' if breaks else "")
        + f'<div class="ask"><b>{ask_l}</b><p>{ask}</p></div></div></div>'
        f'<div class="nowgoal"><div><h4>{now_l}</h4>{paras(now)}</div><div><h4>{goal_l}</h4>{paras(goal)}</div></div>'
        f'<div class="snag"><h4>{snag_l}</h4><ul>' + "".join(f"<li>{x}</li>" for x in snags) + '</ul></div>'
        '</section>')


# ----------------------------------------------------------------------------- bar chart
def bar_chart(rows, width=300, label_w=132, unit=36, row_h=19):
    """Horizontal bars, labels at the label step. rows = [(label, value)...]."""
    o = [f'<svg viewBox="0 0 {width} {len(rows) * row_h}" width="100%" xmlns="http://www.w3.org/2000/svg">']
    for i, (name, n) in enumerate(rows):
        y = i * row_h
        o.append(t(0, y + 12, name, LABEL_PX, 500))
        o.append(f'<rect x="{label_w}" y="{y + 4}" width="{n * unit}" height="10" rx="2" fill="{ACCENT}"/>')
        o.append(t(label_w + n * unit + 6, y + 12.5, str(n), LABEL_PX, 600))
    o.append("</svg>")
    return "\n".join(o)
