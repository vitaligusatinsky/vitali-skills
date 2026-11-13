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
