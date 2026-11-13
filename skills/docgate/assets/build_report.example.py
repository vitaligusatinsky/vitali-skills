#!/usr/bin/env python3
"""Example builder: copy this next to a new report, replace the content, keep the shape.

    python3 build_report.example.py out.html && docgate render out.html out.pdf

It fills report-template.html through report_kit with a small generic report (an order's
journey through a furniture workshop) that exercises every component: summary panel, road,
agenda table, a two-diagram swimlane pair on one row grid, step cards and the closing block.
`docgate test` builds it as the template control: it must pass with no warnings.
"""
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(KIT))
import report_kit as rk  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "report-template.html"
NOW = ' class="now"'

STEPS = ["Offer", "Planning", "Production", "Delivery", "Installation", "Invoicing"]
LANES = [("client", "Client and site"), ("sales", "Sales"), ("office", "Office"),
         ("workshop", "Workshop"), ("site", "Installers")]
CURRENT = {
    "steps": STEPS, "lanes": LANES, "systems_label": "Systems now", "systems_framed": False,
    "votes": {1: 3, 2: 1}, "vote_word": ("vote", "votes"),
    "systems": ["Email, spreadsheet", "Spreadsheet", "Paper lists", "Phone", "Chat groups", "Accounting"],
    "nodes": [("a1", 0, "client", "Request", "by email", None),
              ("a2", 0, "sales", "Offer", "price list in a spreadsheet", "Inputs lost in hand-off"),
              ("a3", 1, "office", "Rough plan", "weekly meeting", "Kept apart from sales"),
              ("a4", 2, "workshop", "Production", "cut, assemble", "Status found by walking"),
              ("a5", 3, "site", "Delivery", "one carrier", None),
              ("a6", 4, "site", "Installation", "one to three weeks", "Defects in chat"),
              ("a7", 5, "office", "Final invoice", "typed by hand", None)],
    "edges": [("a1", "a2"), ("a2", "a3"), ("a3", "a4"), ("a4", "a5"), ("a5", "a6"), ("a6", "a7")],
}
TARGET = dict(CURRENT, systems_label="One data model", systems_framed=True,
              systems=["Room list, price per room", "Load and draft batches", "Work queues",
                       "Picked and shipped", "Ready per room", "Invoice per room"],
              nodes=[("b1", 0, "client", "Request", "missing data via portal", None),
                     ("b2", 0, "sales", "Offer per room", "drafted, checked by a person", None),
                     ("b3", 1, "office", "Proposed plan", "three options", None),
                     ("b4", 2, "workshop", "Production", "screen at every station", None),
                     ("b5", 3, "site", "Delivery", "site sign-off", None),
                     ("b6", 4, "site", "Installation", "percent ready per room", None),
                     ("b7", 5, "office", "Invoice data", "released at 90 percent", None)],
              edges=[("b1", "b2"), ("b2", "b3"), ("b3", "b4"), ("b4", "b5"), ("b5", "b6"), ("b6", "b7")])


def card(title, owner, now, goal, snags, ask, votes=None):
    p = lambda xs: "".join(f"<p>{x}</p>" for x in xs)
    return ('<section class="card"><div class="card-head">'
            f'<h3>{title}</h3>' + (f'<span class="votes">{votes}</span>' if votes else "") +
            f'</div><div class="owner">{owner}</div>'
            f'<div class="nowgoal"><div><h4>Now</h4>{p(now)}</div><div><h4>Target</h4>{p(goal)}</div></div>'
            '<div class="snag"><h4>Where it snags</h4><ul>' + "".join(f"<li>{s}</li>" for s in snags) + '</ul></div>'
            f'<div class="ask"><b>Question for you</b>{ask}</div></section>')


def main(out):
    cur, tgt = rk.Swimlane(CURRENT), rk.Swimlane(TARGET)
    rows = rk.Swimlane.shared_rows(cur, tgt)
    sections = (
        '<h2>What the day covered</h2>'
        '<div class="tbl"><table><thead><tr><th style="width:18%">Time</th><th style="width:30%">Topic</th><th>What came out of it</th></tr></thead><tbody>'
        '<tr><td>10.00–11.30</td><td>The order today</td><td>One order traced from request to invoice: who does what, in which tool, where it waits.</td></tr>'
        '<tr><td>12.30–14.00</td><td>The order as it should be</td><td>The same journey on one shared data model, step by step.</td></tr>'
        '<tr><td>14.00–14.30</td><td>Votes and the one thing</td><td>Where the problems weigh most, and the single most important change.</td></tr>'
        '</tbody></table></div>'
        '<div class="two mt"><div class="panel"><h2>Votes</h2><p class="lead">Where the problems weigh most, counted from the board.</p>'
        + rk.bar_chart([("Planning", 3), ("Production", 1)]) +
        '</div><div class="panel plum"><h2>Deliverables agreed</h2><ul class="points"><li><b>A clickable prototype</b> per role.</li>'
        '<li><b>A requirements report</b> on the critical interfaces.</li><li><b>An effort estimate</b> and a technical roadmap.</li></ul></div></div>'
        '<section class="figure"><h2>The order today, by role</h2>'
        '<p class="lead">Steps run top to bottom, the column says who does the work, and the orange note shows where information breaks.</p>'
        + cur.svg("current", rows) + '</section>'
        '<section class="figure"><h2>The order on one data model</h2>'
        '<p class="lead">The target as drawn on the board. The right-hand column shows what each step records.</p>'
        + tgt.svg("target", rows) + '</section>'
        '<section><h2>Step by step</h2>'
        '<p class="lead">For each step: how it works now, where it snags, what the target is, and what we would like you to confirm.</p>'
        + card("Offer", "Sales, with the owner", ["Requests arrive by email with drawings attached.", "Prices come from a spreadsheet and are typed into the offer."],
               ["The offer is drafted per room and checked by a person.", "Sales can see what delivery time is realistic before promising one."],
               ["Resources are not checked when the deal is closed.", "Each seller prices in their own way."], "Who prices an offer in practice?", "2 votes")
        + card("Planning", "Office", ["A rough plan is made in a spreadsheet at the weekly meeting."], ["Three proposed schedules, with load shown per week."],
               ["The plan runs behind the work it describes."], "Who approves a production batch?", "3 votes")
        + '</section>'
    )
    html = TEMPLATE.read_text(encoding="utf-8").format(
        lang="en", title="Example interim report", css=rk.css("Example report · draft for review"), logo="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 28 28%27%3E%3Ccircle cx=%2714%27 cy=%2714%27 r=%2714%27 fill=%27%231C171B%27/%3E%3C/svg%3E",
        author="Vitali Gusatinsky", byline="Service design · Example Oy", doc_type="Interim report",
        kicker="Workshop interim report · 12.11.2026", headline="An order's journey from offer to invoice",
        intro="We walked through one order from the offer to the final invoice, as it works today and as it should. This draft is for you to check before the final deliverables.",
        summary_heading="Summary",
        summary_items="\n".join(f"    <li><b>{a}</b> {b}</li>" for a, b in [
            ("There is no shared picture.", "Information sits in spreadsheets, paper lists and chat groups, and is found by asking."),
            ("The room is the unit.", "Planning, delivery and installation all happen per room."),
            ("Planning drew the most votes", "(3 of 4) when we asked where problems weigh most.")]),
        road_heading="Where we are",
        road="\n".join(f'  <div{NOW if now else ""}><b>{a}</b><span>{b}</span></div>' for a, b, now in [
            ("Workshop", "12.11., today and target", False), ("Interim report", "this document, for your comments", True),
            ("Answers and files", "open questions and spreadsheets", False), ("Final deliverables", "report, prototypes, roadmap", False)]),
        sections=sections, contact="vitaligusatinsky.com",
    )
    Path(out).write_text(html, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "example-report.html")
