#!/usr/bin/env python3
"""Component gallery: every report-base / report_kit component alone, in each of its states.

    python3 gallery.py out.html        # or: docgate gallery [--out DIR]

Each state gets its own page so docgate measures it in isolation; a caption line
("GALLERY <component> · <state>") lets `docgate gallery` map pages back to components.
A component may be used in a deliverable only while every one of its states passes
(fill and orphan are waived here: a component alone does not fill a page).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE))
import importlib.util  # noqa: E402

import report_kit as rk  # noqa: E402

_spec = importlib.util.spec_from_file_location("example", HERE / "build_report.example.py")
ex = importlib.util.module_from_spec(_spec)  # generic example content (no client data)
_spec.loader.exec_module(ex)

PARA = ("The order moves from the sales offer to planning, production, delivery and installation. "
        "Each step has an owner, a system it is recorded in, and a point where the information is handed on.")


def para(n, k=1):
    return "".join(f"<p>{PARA[: int(len(PARA) * k)]}</p>" for _ in range(n))


def findings(n):
    items = "".join(f"<li><b>Finding {i + 1} is stated as one claim.</b> {PARA[:120]}</li>" for i in range(n))
    return f'<div class="panel"><h2>Summary</h2><ul class="findings">{items}</ul></div>'


def feature(n, wide=True):
    items = "".join(f'<div><b>Idea {i + 1}</b><span>{PARA[:110]}</span></div>' for i in range(n))
    w = f'<div class="wide"><b>The one change that matters most, said in one line</b><span>{PARA[:140]}</span></div>' if wide else ""
    return (f'<div class="feature"><h2>The one thing</h2><p class="lead">We asked each person for the single most '
            f'important change.</p><div class="items">{w}{items}</div></div>')


def road(now):
    steps = [("Workshop", "the session, the board"), ("Interim report", "this document"),
             ("Answers and files", "open questions"), ("Final deliverables", "report, prototypes")]
    cls = ' class="now"'
    return '<div class="road">' + "".join(
        f'<div{cls if k == now else ""}><b>{a}</b><span>{b}</span></div>' for k, (a, b) in enumerate(steps)) + "</div>"


def table(rows):
    body = "".join(f"<tr><td>Step {i + 1}</td><td>Spreadsheet and email</td><td>{PARA[:90]}</td></tr>" for i in range(rows))
    return (f'<div class="tbl"><table><thead><tr><th style="width:18%">Step</th><th style="width:30%">System</th>'
            f"<th>What happens</th></tr></thead><tbody>{body}</tbody></table></div>")


def phase(long):
    k = 3 if long else 1
    return rk.phase_page(
        1, ex.STEPS, "Planning, including the site measurement",
        [("Lead", "Office, with the planners"), ("Roles", "Office, Workshop, Client"),
         ("Systems now", 'Spreadsheet<span class="to">Target: load and draft batches</span>')],
        ["Site visits are not recorded"] if long else [],
        "What would an early model cover before the measurements, and what would it avoid?",
        [PARA] * (2 * k), [PARA] * (2 * k), [PARA[:140]] * (k + 1),
        labels=("Step", "Where information breaks", "Question for you", "Now", "Target", "Where it snags"))


def swimlane():
    cur, tgt = rk.Swimlane(ex.CURRENT), rk.Swimlane(ex.TARGET)
    rows = rk.Swimlane.shared_rows(cur, tgt)
    return f'<div class="figure"><h2>Current flow</h2>{cur.svg("current", rows)}</div>'


def bars(n):
    return '<div class="panel">' + rk.bar_chart([(f"Option {i + 1}", (i % 4) + 1) for i in range(n)]) + "</div>"


STATES = [
    ("findings", "2 items", lambda: findings(2)), ("findings", "6 items", lambda: findings(6)),
    ("feature", "wide + 2", lambda: feature(2)), ("feature", "4, no wide", lambda: feature(4, False)),
    ("road", "now first", lambda: road(0)), ("road", "now last", lambda: road(3)),
    ("table", "3 rows", lambda: table(3)), ("table", "10 rows", lambda: table(10)),
    ("phase", "short, no break", lambda: phase(False)), ("phase", "long, with break", lambda: phase(True)),
    ("swimlane", "current", swimlane),
    ("bar-chart", "4 rows", lambda: bars(4)),
]


def build(out):
    secs = []
    for comp, state, fn in STATES:
        secs.append(f'<section class="gallery" style="break-before:page"><p class="label">GALLERY {comp} · {state}</p>'
                    f"<h1>{comp}</h1>{fn()}</section>")
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>report-base gallery</title>'
            '<meta name="docgate-waive" content="fill: a component gallery shows one component per page by design">'
            '<meta name="docgate-waive" content="orphan: a component gallery shows one component per page by design">'
            f"<style>{rk.css('report-base component gallery')}</style></head><body>{''.join(secs)}</body></html>")
    Path(out).write_text(html, encoding="utf-8")
    return [(c, s) for c, s, _ in STATES]


if __name__ == "__main__":
    build(sys.argv[1])
    print("wrote", sys.argv[1])
