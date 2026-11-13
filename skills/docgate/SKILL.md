---
name: docgate
description: >-
  Render an HTML document to a deliverable PDF and prove it is right: a pinned Chromium,
  DOM preflight, measured checks on the real PDF (page sizes, fonts, page fill, orphans,
  stranded headings, leading, dividers, accents, diagram text), 150 dpi tiles for review,
  and a hash-bound receipt a Stop hook checks. Ships report-base.css, a report template,
  a builder kit with measured-glyph SVG swimlanes, fixtures, and the doc-critic agent.
  Use for any client report, proposal or recap PDF, for "render this to PDF", "check this
  PDF", "docgate", or when a document was rejected and the defect class needs a rule.
---

# docgate

Printed documents fail in ways a thumbnail hides and a reviewer finds: a landscape page in a
portrait set, a heading stranded at the foot of a page, diagram text too small to read, an
arrow through a label, a fallback font. docgate measures those on the actual PDF and refuses
to call the document done until they pass. What cannot be measured goes to `doc-critic`.

## Commands

```bash
docgate render in.html out.pdf [--profile a4-report] [--tiles DIR]   # the only way to make a deliverable PDF
docgate check out.pdf                       # does the receipt match this exact PDF, and did it pass?
docgate pair golden.pdf out.pdf DIR         # matched page pairs side by side (golden compare, before/after)
docgate test [--manifest FILE ...]          # fixtures: rejected versions fail on their own classes, approved pass
docgate quality any.pdf [-v]                # harness v2 quality rules on any PDF (e.g. a reference report), no receipt
docgate gallery [--out DIR]                 # every component alone in each state, gated per state
docgate plan my.plan.json                   # gate a layout plan before building
```

`render` exits 0 on pass, 1 on blocking findings, 2 if it could not run. It writes
`out.pdf.docgate.json` (sha256, profile, tool versions, every finding, page metrics, waivers,
tile paths) and page images plus three bands per page at 150 dpi for self-review.

On macOS, Chromium cannot launch inside the Claude Code sandbox (Mach port denied): run
`render` and `test` outside it.

## Building a report

1. Fill in the content standard (vitali-os `docs/conventions/documents/client-report-standard.md`).
2. Copy `assets/build_report.example.py`, keep its shape, replace the content. It fills
   `assets/report-template.html` through `lib/report_kit.py`, which prepends the brand fonts
   (`REPORT_FONTS`, licensed, never in this repo), the page footer and `report-base.css`.
3. `docgate render`, fix what it blocks, read the tiles, compare with the golden reference.
4. Run `doc-critic` (installed to `~/.claude/agents/`), mark each finding fixed or waived.
5. Hand off with the receipt summary and the critic table.

Rules, the loop and the rejection protocol: `~/.claude/rules-library/document-design.md`.

## Rules (profile `a4-report`)

| id | level | what |
|---|---|---|
| `page-size` | fail | every page A4 portrait, one size, no rotation, boxes agree |
| `fonts` | fail | fonts embedded; the expected families are in the PDF (`<meta name="docgate-fonts">` or the profile) |
| `fill` | fail | a non-final page ends at least 55% of the way down |
| `orphan` | fail | no page holds under 15% (a fragment) |
| `stranded-heading` | fail | no heading in the bottom quarter of a page with fewer than 3 lines under it |
| `leading` | fail | heading line-height ≤ 1.25 |
| `gap` | fail | the gap under a heading ≥ its internal leading |
| `overflow` | fail | no box clips its content; no diagram label runs past its diagram |
| `bleed` | fail | nothing extends past the content box |
| `left-accent` | fail | no coloured left border, no vertical accent stripe in a diagram |
| `divider` | fail | no `<hr>` or lone rule line between sections |
| `hard-lines` | fail | diagram connectors softer than the text (luminance ≥ 0.02) |
| `tiny-text` | fail | at most 50 text runs under 6.5 pt at printed size |
| `text-collision` | fail | no overlapping diagram labels |
| `truncated`, `placeholder` | fail | the build finished: `</html>` present, no `{holes}` left |
| `line-through-text` | warn | connectors crossing text (warn until calibrated) |
| `type-scale` | warn | more than 5 HTML sizes, or text over 26 pt |
| `text-size` | warn | body under 8 pt, a few labels under 6.5 pt |
| `inset`, `gutter`, `radius` | warn | one inset, one gutter, few radii on top-level frames |

Waive a rule for one document with a reason: `<meta name="docgate-waive" content="fill: ...">`.

## Quality rules (harness v2, `lib/quality.py`)

The rules above catch defects. These catch what a designer means by "cramped", "card in card",
"poor visibility of boundaries" and "no ratio between sizes and gaps". They read only the PDF
(text lines from `pdftotext -bbox-layout`, frames from the raster), so the same numbers run on
our renders and on any reference PDF: `docgate quality any.pdf [-v]`. `render` runs them too.
All lengths are in body-line pitches, so pages at any size compare.

| id | level | what | banded from |
|---|---|---|---|
| `nested-frame` | fail | a framed box with text inside another frame (card in card) | 0 of 292 reference pages |
| `faint-frame` | fail | a text frame under 0.04 OKLab L from its ground: the boundary does not read | every reference frame sits at ≥ 0.05 |
| `large-narrow` | fail | 1.3–2.2× body text wrapped ≥ 4 lines under 34 characters, inside a box | 0 reference pages (open pull-quote columns are fine) |
| `gap-levels` | fail | 6+ distinct break sizes on a page | references use at most 5 |
| `gap-scale` | warn | 5 break sizes | reference max |
| `frame-heavy` | warn | 3+ framed text boxes on a page | references frame text on 15% of pages |

Measured and not used, because references do the same: overall ink density, gap above vs below
headings, distinct left edges, narrow body columns under 40 characters (103 of 269 reference
pages), widows. A rule may block only if no reference page trips it.

## Three levels: plan, component, document

The same bands gate a document at every level. Each level fails before the next is built.

1. **Plan:** `docgate plan my.plan.json`.
   - Before any layout, state the system:
     - page and grid
     - type sizes and leading
     - gap scale in body lines
     - measure band per text span
     - frame tints and nesting depth
     - one best-in-class reference per page type, with what it takes from it
   - It fails on:
     - more than 5 sizes or steps under 1.2×
     - more than 4 gap sizes or gaps under 1.5× apart
     - spans outside their measure band
     - nesting, or tints under 0.05 OKLab L
     - a page type with no reference
   - Examples are in `assets/plans/`. `report-base-v1.plan.json` is the rejected system, with 9 blocking
     findings. `phase-spread.plan.json` passes.
2. **Component:** `docgate gallery [--out DIR]`.
   - It renders every component (`assets/gallery.py`) alone, in each of its states, one per page, and
     gates each state. Components: findings, feature, road, table, phase, swimlane, bar chart.
   - A component may be used in a deliverable only while all its states pass.
   - Add a state for every new component or variant.
3. **Document:** `docgate render`, which applies all the rules above. Then `doc-critic`, as an
   advisor that is not the gate.

## Calibration, harness v2 (14.11.2026)

- **Controls:** 166 pages from four best-in-class reports (Nesta strategy, Design Council
  Design for Innovation, Sitra 2025, Demos Helsinki 2018) set the bands. 126 held-out pages
  (Nesta annual report 2023-24, Design Council Systemic Design) were checked after: 0 fail.
  The held-out set caught one overreach first (large pull quotes in open columns), which is why
  `large-narrow` only applies inside a box.
- **Negatives:** the owner-rejected client versions fail on every rejected page. The refined
  rebuild (rejected 13.11 evening) fails 18 of 18 pages; the version before it 10 of 13.
- **Jitter fixtures:** the control with one injected defect each (`synthetic-nested-frame`,
  `-faint-frame`, `-large-narrow`, `-gap-levels`) must fail on exactly that rule.
- **Not a gate: LLM judges.** Benchmarked 14.11 on 11 owner-rejected pages and 17 reference
  pages (Claude Opus 5.5, Sonnet 5.5, Gemini 3.8 Flash; 318 calls, USD 6): every model rejected
  all 11 rejected pages, and also 73-98% of the references; pairwise accuracy was near chance
  (5-7 of 11). An LLM judge says "no" to everything, so it cannot be the gate. `doc-critic`
  stays an advisor whose located findings a builder fixes or waives; measurable findings it
  raises become rules here.
- `measure` now counts the widest real line (text boxes per line), not characters / lines: a
  short last line had hidden a 90-character measure in two-line list items.

## Calibration (13.11.2026)

Calibrated on a client interim report: six rejected versions and the approved
one (fixtures in that client's private repo, read through `git show`).

- The approved version passes; its lowest non-final page reaches 66% (threshold 55%). The
  rejected versions' half-empty pages reached 41–46%, and the orphan page 3%.
- The approved version has 36 runs under 6.5 pt (a bar chart); the rejected swimlane versions
  had 231–249 (threshold 50).
- Rebuilt on report-base, the approved report uses exactly 5 type sizes (it had 17) and passes
  with no warnings.
- Rules the reviews proved wrong as blocking stay as warnings: ink coverage, colour counts,
  radius and size caps, path-sampling collision.

## Fixtures

- `fixtures/make_synthetic.py` writes one fixture per rule plus a control that carries every
  shape a rule must not fire on; `fixtures/manifest.json` lists them, with the template
  example built by its own builder as a second control.
- A client's rejected versions go in a manifest in the client's own (private) repo. This
  repo is public: never commit client documents or brand fonts here.

## Install

`scripts/install-docgate.sh` copies the skill to `~/.claude/skills/docgate`, links
`~/.claude/bin/docgate`, and installs `agents/doc-critic.md`. It needs Python with
`playwright==1.58.0` (pinned: Chromium 145), Pillow, and poppler (`pdfinfo`, `pdffonts`,
`pdftoppm`, `pdftotext`).
