#!/usr/bin/env python3
"""Write the synthetic docgate fixtures: one small document per rule, plus a control that
carries every shape a rule must NOT fire on (white table gaps, pale grid lines, soft
connectors, a box nested in a card, a footer line in the margin box).

Generic content and system fonts only: this repo is public, so client documents and the
licensed brand fonts never go here. Client history fixtures live in the client's private
repo and are read through `git show` by a manifest there.

    python3 fixtures/make_synthetic.py && docgate test
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent / "synthetic"

CSS = """
@page { size: A4 portrait; margin: 16mm 18mm;
  @bottom-left { content: "Synthetic fixture"; font-family: Helvetica, sans-serif; font-size: 7pt; color: #6D5A7D; } }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Helvetica, sans-serif; font-size: 8.8pt; line-height: 1.52; color: #1C171B; orphans: 3; widows: 3;
  -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1, h2, h3 { font-family: Georgia, serif; font-weight: 600; line-height: 1.15; break-after: avoid; }
h1 { font-size: 22pt; margin: 0 0 10px; }
h2 { font-size: 16pt; margin: 24px 0 10px; }
h3 { font-size: 12pt; margin: 0 0 8px; }
p { margin-bottom: 6px; max-width: 52ch; }
.label { font-size: 7pt; color: #6D5A7D; }
.panel { background: #F6F4F0; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; break-inside: avoid; }
.ask { background: #F1E6EC; border-radius: 6px; padding: 10px; margin-top: 10px; }
.tbl { background: #F6F4F0; border-radius: 10px; padding: 4px 16px; }
table { width: 100%; border-collapse: collapse; }
td { padding: 6px 10px 6px 0; border-top: 2px solid #fff; vertical-align: top; }
.page { break-before: page; }
"""

PARA = ("The order moves from the sales offer to planning, production, delivery and installation. "
        "Each step has an owner, a system it is recorded in, and a point where the information "
        "is handed to the next person. Where that hand-off happens by phone or on paper, the "
        "status has to be found by asking. ")


def para(n=1):
    return "".join(f"<p>{PARA}</p>" for _ in range(n))


def doc(body, extra_css="", head="", fonts="Helvetica, Georgia"):
    return (f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="docgate-fonts" content="{fonts}">\n{head}<title>fixture</title>\n'
            f"<style>{CSS}{extra_css}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n")


def full_pages(n):
    """n pages that each fill to the bottom: panels of prose until the page breaks."""
    return "".join(f"<h2>Section {i + 1}</h2>" + "".join(f'<div class="panel"><h3>Item {i + 1}.{k + 1}</h3>{para(2)}</div>' for k in range(5)) for i in range(n))


SOFT_DIAGRAM = """<svg viewBox="0 0 400 140" width="100%" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#6D5A7D"/></marker></defs>
<line x1="130" y1="0" x2="130" y2="140" stroke="#EEEBE6" stroke-width="1"/><line x1="260" y1="0" x2="260" y2="140" stroke="#EEEBE6" stroke-width="1"/>
<rect x="10" y="20" width="100" height="40" rx="3" fill="#fff" stroke="#3D3147" stroke-width="0.8"/>
<text x="16" y="44" font-family="Helvetica" font-size="9.4" font-weight="600">Offer</text>
<rect x="150" y="80" width="100" height="40" rx="3" fill="#fff" stroke="#3D3147" stroke-width="0.8"/>
<text x="156" y="104" font-family="Helvetica" font-size="9.4" font-weight="600">Planning</text>
<path d="M100,60 V70 H160 V78.5" fill="none" stroke="#6D5A7D" stroke-width="1.2" marker-end="url(#a)"/>
</svg>"""

CONTROL_BODY = (
    '<h1>Synthetic control report</h1><p class="label">A clean two-page document. Every rule must stay quiet.</p>'
    + '<div class="panel"><h3>Summary</h3>' + para(2) + '<div class="ask"><b>Question</b> Who owns the hand-off?</div></div>'
    + '<div class="tbl"><table><tr><td>Offer</td><td>Excel and email</td></tr><tr><td>Planning</td><td>Spreadsheet</td></tr><tr><td>Delivery</td><td>Phone</td></tr></table></div>'
    + "<h2>Flow</h2>" + SOFT_DIAGRAM + full_pages(1)
)

FIXTURES = {
    "ok-control": (doc(CONTROL_BODY), {"pass": True, "not": ["divider", "left-accent", "hard-lines", "inset", "gutter", "leading", "gap", "overflow", "text-collision", "line-through-text", "fonts", "page-size"]},
                   "clean control: white table gaps, pale grid lines, soft connectors and a nested box must not fire"),
    "leading": (doc("<h1>Heading</h1><h2 style='line-height:1.6'>A heading set with body leading that wraps onto two lines</h2>" + para(3)),
                {"pass": False, "fail": ["leading"]}, "heading line-height 1.6"),
    "gap": (doc("<h1>Heading</h1><h2 style='margin-bottom:0;line-height:1.25'>A heading sitting tight on its text</h2><p style='margin-top:0'>" + PARA + "</p>"),
            {"pass": False, "fail": ["gap"], "not": ["leading"]}, "gap under heading smaller than its leading"),
    "left-accent": (doc("<h1>Heading</h1><div style='border-left:3px solid #473855;padding-left:12px'>" + para(2) + "</div>"),
                    {"pass": False, "fail": ["left-accent"]}, "coloured left border on a callout"),
    "divider": (doc("<h1>Heading</h1>" + para(2) + "<hr>" + para(2)), {"pass": False, "fail": ["divider"]}, "a raw <hr> between sections"),
    "landscape": (doc("<h1>Heading</h1>" + para(2) + "<section class='wide'><h2>Wide table</h2>" + para(2) + "</section>",
                      extra_css="@page wide { size: A4 landscape; } .wide { page: wide; }"),
                  {"pass": False, "fail": ["page-size"]}, "a landscape page mixed into a portrait set"),
    "half-empty": (doc("<h1>Heading</h1>" + para(2) + "<section class='page'>" + full_pages(1) + "</section>"),
                   {"pass": False, "fail": ["fill"]}, "page 1 breaks a third of the way down"),
    "orphan": (doc("<h1>Heading</h1>" + full_pages(1) + "<p class='page'>One last line on its own page.</p>"),
               {"pass": False, "fail": ["orphan"]}, "a final page holding one line"),
    "hard-lines": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace('stroke="#6D5A7D" stroke-width="1.2"', 'stroke="#111111" stroke-width="1.2"') + para(1)),
                   {"pass": False, "fail": ["hard-lines"]}, "a connector drawn in near-black"),
    "svg-overflow": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace('<text x="156" y="104" font-family="Helvetica" font-size="9.4" font-weight="600">Planning<', '<text x="340" y="104" font-family="Helvetica" font-size="9.4" font-weight="600">Planning and production<') + para(1)),
                     {"pass": False, "fail": ["overflow"]}, "a diagram label running past the diagram's edge"),
    "text-collision": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace('<text x="156" y="104"', '<text x="16" y="47"') + para(1)),
                       {"pass": False, "fail": ["text-collision"]}, "two diagram labels on top of each other"),
    "line-through-text": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace('d="M100,60 V70 H160 V78.5"', 'd="M30,10 V75 H160 V78.5"') + para(1)),
                          {"warn": ["line-through-text"]}, "a connector drawn through a label (warning until calibrated)"),
    "arrow-stub": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace('d="M100,60 V70 H160 V78.5"', 'd="M100,60 V78 H160 V78.5"') + para(1)),
                   {"pass": False, "fail": ["arrow-stub"]}, "an arrow that turns on a 0.5-unit run: the head sits on the corner"),
    "arrow-gap": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace('d="M100,60 V70 H160 V78.5"', 'd="M100,60 V65 H160 V70"') + para(1)),
                  {"pass": False, "fail": ["arrow-gap"]}, "an arrow that stops 10 units short of its box"),
    "box-overflow": (doc("<h1>Heading</h1>" + SOFT_DIAGRAM.replace(">Offer<", ">Offer automatically<") + para(1)),
                     {"pass": False, "fail": ["box-overflow"]}, "a label wider than the box it sits in"),
    "measure": (doc("<h1>Heading</h1><p style='max-width:none'>" + PARA * 3 + "</p>"),
                {"pass": False, "fail": ["measure"]}, "running text across the full measure, over 80 characters a line"),
    "tiny-text": (doc("<h1>Heading</h1><svg viewBox='0 0 400 400' width='100%'>" + "".join(f"<text x='{(i % 6) * 64}' y='{12 + (i // 6) * 18}' font-family='Helvetica' font-size='3.6'>label {i}</text>" for i in range(66)) + "</svg>"),
                  {"pass": False, "fail": ["tiny-text"]}, "66 diagram labels at 4.5 pt"),
    "missing-font": (doc("<h1 style=\"font-family:'BrandMissing', Georgia\">Heading</h1>" + para(2),
                         extra_css="@font-face { font-family: 'BrandMissing'; src: url('fonts/does-not-exist.ttf'); }", fonts="BrandMissing"),
                     {"pass": False, "fail": ["fonts"]}, "a webfont that never loads: the fallback prints instead"),
    "interrupted": ((lambda h: h[:h.index("{steps}") + len("{steps}")])(doc("<h1>Heading</h1>" + para(2) + "<section>{steps}</section>")),
                    {"pass": False, "fail": ["truncated", "placeholder"]}, "a build that stopped half-way: no closing tags, a template hole"),
    "stranded-heading": (doc("<h1>Heading</h1>" + "".join(f'<div class="panel"><h3>Item {k}</h3>{para(2)}</div>' for k in range(4))
                             + "<div style='height:150px'></div><h2 style='break-after:auto'>A section that starts too late</h2><p>One line of lead.</p>"
                             + "<div class='panel'><h3>Tall block</h3>" + para(5) + "</div>" + full_pages(1)),
                         {"pass": False, "fail": ["stranded-heading"]}, "a heading and one line left at the foot of a page"),
    "waived": (doc("<h1>Heading</h1>" + full_pages(1) + "<p class='page'>A deliberate closing line on its own page.</p>",
                   head='<meta name="docgate-waive" content="orphan: the closing line is meant to stand alone on the back page">\n'),
               {"pass": True, "not": []}, "an orphan waived by a config line with a reason"),
}


def main():
    import json
    HERE.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, (html, expect, note) in FIXTURES.items():
        (HERE / f"{name}.html").write_text(html, encoding="utf-8")
        entries.append({"id": f"synthetic-{name}", "source": {"file": f"synthetic/{name}.html"}, "expect": expect, "note": note})
    entries.append({"id": "template-example", "source": {"build": ["python3", "../assets/build_report.example.py", "{out}"]},
                    "expect": {"pass": True, "not": ["type-scale", "text-size", "line-through-text", "measure", "arrow-stub", "arrow-gap", "stranded-heading"]},
                    "note": "the template, built by report_kit with the brand fonts: must pass with no warnings (needs REPORT_FONTS)"})
    manifest = {"description": "Synthetic per-rule fixtures (generated by make_synthetic.py). Client history fixtures live in each client's private repo.",
                "profile": "a4-report", "fixtures": entries}
    (HERE.parent / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(entries)} fixtures to {HERE}")


if __name__ == "__main__":
    main()
