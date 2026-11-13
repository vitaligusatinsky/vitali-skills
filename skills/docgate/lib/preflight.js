// docgate preflight: DOM checks on the laid-out document, run by `docgate render` in
// Chromium with print media emulated and the viewport set to the profile's content width.
// It is a preflight: the printed layout is checked again on the real PDF afterwards.
//
// Returns { checks, findings: [{rule, level, msg, el}], metrics }.
// level: "fail" blocks, "warn" is reported. The profile can raise or lower a rule's level.
//
// Rules (ids are stable; document-design.md and the fixtures refer to them):
//   leading      heading line-height / font-size <= maxHeadingLeading            (fail)
//   gap          space under a heading >= its own internal leading                  (fail)
//   overflow     a box that clips its own content (scrollWidth > clientWidth)        (fail)
//   bleed        an element extends past the content box's right edge               (fail)
//   left-accent  a coloured left border with no other border, or a vertical accent
//                stripe inside a diagram (banned taste rule)                          (fail)
//   divider      a raw rule line between sections: <hr> or a lone top/bottom border  (fail)
//   text-collision  diagram labels overlapping each other                           (fail)
//   line-through-text  connectors drawn through diagram text                         (warn)
//   measure      running text over maxMeasure characters per line                  (fail)
//   arrow-stub   a turning connector whose last run is shorter than minRunIn       (fail)
//   arrow-gap    an arrow tip further than maxTipGap from any box                   (fail)
//   box-overflow a diagram label running past the edge of its own box                (fail)
//   inset        framed containers use more than one padding-left                   (warn)
//   gutter       grid/flex columns use more than one column gap                      (warn)
//   hard-lines   diagram connectors drawn in near-black (luminance < minLineLuminance)(fail)
//   tiny-text    more than maxTinyRuns text runs under minLabelPt (SVG included)     (fail)
//   text-size    body text under minBodyPt, a few labels under minLabelPt            (warn)
//   type-scale   more distinct HTML font sizes than the scale allows; huge headings  (warn)
//   radius       more distinct corner radii than the scale allows                    (warn)
(async (P) => {
  await document.fonts.ready;
  const out = [];
  const add = (rule, msg, el) => out.push({ rule, msg, el: el ? label(el) : "" });
  const px = (v) => parseFloat(v) || 0;
  const PT = 96 / 72;
  function label(el) {
    const t = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 48);
    const tag = el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).join(".") : "");
    return `${tag} "${t}"`;
  }
  const visible = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const opaque = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return false;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return p.length < 4 || p[3] > 0.05;
  };
  const nearWhite = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return false;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return p[0] > 245 && p[1] > 245 && p[2] > 245;
  };

  // ---- headings: leading and gap (the seed gate, generalised)
  const heads = [...document.querySelectorAll("h1, h2, h3, h4, h5, h6, [data-docgate-heading]")].filter(visible);
  for (const h of heads) {
    const cs = getComputedStyle(h);
    const fs = px(cs.fontSize), lh = cs.lineHeight === "normal" ? fs * 1.2 : px(cs.lineHeight);
    if (lh / fs > P.maxHeadingLeading + 0.005) add("leading", `heading line-height ${(lh / fs).toFixed(2)} > ${P.maxHeadingLeading}`, h);
    let next = h.nextElementSibling;
    while (next && !visible(next)) next = next.nextElementSibling;
    if (!next) continue;
    const hb = h.getBoundingClientRect(), nb = next.getBoundingClientRect();
    if (nb.top < hb.bottom - 1 || Math.abs(nb.left - hb.left) > 40) continue; // not stacked below
    const gap = nb.top - hb.bottom, leading = lh - fs;
    if (gap + 0.5 < leading) add("gap", `gap under heading ${gap.toFixed(1)}px < its leading ${leading.toFixed(1)}px`, h);
  }

  const all = [...document.body.querySelectorAll("*")].filter((el) => !el.closest("svg") && el.tagName !== "SCRIPT" && el.tagName !== "STYLE");
  const bodyBox = document.body.getBoundingClientRect();
  const contentRight = bodyBox.left + P.contentWidthPx;

  for (const el of all) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    // ---- overflow (clipping) and bleed
    if (el.scrollWidth > el.clientWidth + 1 && cs.overflow !== "visible" && cs.overflowX !== "visible") add("overflow", `clips its content ${el.scrollWidth}px > ${el.clientWidth}px`, el);
    if (r.right > contentRight + 2 && cs.position !== "fixed") add("bleed", `right edge ${Math.round(r.right - bodyBox.left)}px past the ${Math.round(P.contentWidthPx)}px content box`, el);
    // ---- left-accent: a coloured left border and no other border
    const bl = px(cs.borderLeftWidth), br = px(cs.borderRightWidth), bt = px(cs.borderTopWidth), bb = px(cs.borderBottomWidth);
    if (bl >= 1.5 && cs.borderLeftStyle !== "none" && opaque(cs.borderLeftColor) && !nearWhite(cs.borderLeftColor) && br < 0.5 && bt < 0.5 && bb < 0.5) add("left-accent", `${bl}px left border, no other border`, el);
    // ---- divider: hr, or a lone top/bottom border line across most of the measure
    const lone = (w, style, color, others) => w >= 0.5 && style !== "none" && opaque(color) && !nearWhite(color) && others.every((o) => o < 0.5);
    if (el.tagName === "HR") add("divider", "<hr> rule", el);
    else if (r.width >= P.contentWidthPx * 0.5 && !["TD", "TH", "TR", "THEAD", "TBODY"].includes(el.tagName)) {
      if (lone(bt, cs.borderTopStyle, cs.borderTopColor, [bl, br, bb]) || lone(bb, cs.borderBottomStyle, cs.borderBottomColor, [bl, br, bt])) add("divider", "lone top/bottom border line", el);
    }
  }

  // ---- inset and gutter
  const framed = all.filter((el) => {
    if (!visible(el)) return false;
    const cs = getComputedStyle(el);
    return opaque(cs.backgroundColor) && !nearWhite(cs.backgroundColor) && px(cs.borderTopLeftRadius) > 0 && el.getBoundingClientRect().width > 160 && cs.display !== "inline";
  });
  // nested frames (an ask box inside a card) and columns inside a frame have their own inset
  const topFramed = framed.filter((el) => !framed.some((o) => o !== el && o.contains(el)));
  const insets = new Map();
  for (const el of topFramed) {
    const v = getComputedStyle(el).paddingLeft;
    if (!insets.has(v)) insets.set(v, el);
  }
  if (insets.size > P.maxInsets) add("inset", `${insets.size} padding-left values on framed containers: ${[...insets.keys()].join(", ")}`, null);
  const gaps = new Set();
  for (const el of all) {
    const cs = getComputedStyle(el);
    if ((cs.display === "grid" || cs.display === "flex") && el.children.length > 1 && !framed.some((f) => f.contains(el)) && cs.columnGap !== "normal" && px(cs.columnGap) >= 6) {
      const kids = [...el.children].filter(visible);
      if (kids.length > 1 && Math.abs(kids[0].getBoundingClientRect().top - kids[1].getBoundingClientRect().top) < 2) gaps.add(cs.columnGap);
    }
  }
  if (gaps.size > P.maxGutters) add("gutter", `${gaps.size} column gaps: ${[...gaps].join(", ")}`, null);

  // ---- text sizes (HTML text nodes and SVG text, at printed size)
  const sizes = new Map(); // pt -> count of chars
  let smallBody = 0, smallLabel = 0, firstSmall = null, firstTiny = null, maxPt = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode, el = n.parentElement;
    const txt = n.textContent.trim();
    if (!txt || !el || !visible(el) || el.closest("script, style, #qa-result")) continue;
    let pt;
    if (el.closest("svg")) {
      const t = el.closest("text") || el;
      if (!t.getScreenCTM) continue;
      const m = t.getScreenCTM();
      pt = (px(getComputedStyle(t).fontSize) * Math.hypot(m.a, m.b)) / PT;
    } else {
      pt = px(getComputedStyle(el).fontSize) / PT;
      const k = Math.round(pt * 10) / 10;
      sizes.set(k, (sizes.get(k) || 0) + txt.length);
    }
    maxPt = Math.max(maxPt, pt);
    if (pt + 0.05 < P.minLabelPt) { smallLabel++; firstTiny = firstTiny || `${pt.toFixed(1)}pt ${label(el)}`; }
    else if (pt + 0.05 < P.minBodyPt && txt.length > P.bodyMinChars && !el.closest("svg, th, .tag, .kicker, .note, .owner, .legend, figcaption, small, .end, .label")) { smallBody++; firstSmall = firstSmall || `${pt.toFixed(1)}pt ${label(el)}`; }
  }
  if (smallLabel > P.maxTinyRuns) add("tiny-text", `${smallLabel} text runs under ${P.minLabelPt}pt, more than the ${P.maxTinyRuns} allowed (first: ${firstTiny}): diagram or label text too small to read`, null);
  else if (smallLabel) add("text-size", `${smallLabel} text runs under ${P.minLabelPt}pt (first: ${firstTiny})`, null);
  if (smallBody) add("text-size", `${smallBody} body paragraphs under ${P.minBodyPt}pt (first: ${firstSmall})`, null);
  const steps = [...sizes.entries()].filter(([, n]) => n >= 8).map(([k]) => k).sort((a, b) => a - b);
  if (steps.length > P.maxTypeSizes) add("type-scale", `${steps.length} font sizes in use (scale allows ${P.maxTypeSizes}): ${steps.join(", ")} pt`, null);
  if (maxPt > P.maxHeadingPt) add("type-scale", `largest text ${maxPt.toFixed(1)}pt > ${P.maxHeadingPt}pt`, null);

  // ---- SVG diagrams: accent stripes and connectors drawn in ink
  const lum = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return 1;
    const p = m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    if (p.length >= 4 && p[3] < 0.05) return 1;
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(p[0]) + 0.7152 * f(p[1]) + 0.0722 * f(p[2]);
  };
  let hard = 0, firstHard = null;
  for (const svg of document.querySelectorAll("svg")) {
    if (!visible(svg)) continue;
    const sb = svg.getBoundingClientRect();
    for (const ln of svg.querySelectorAll("line, path, polyline")) {
      const cs = getComputedStyle(ln);
      if (cs.stroke === "none" || px(cs.strokeWidth) <= 0) continue;
      const b = ln.getBoundingClientRect();
      const stripe = ln.tagName === "line" && !ln.getAttribute("marker-end") && b.width < 3 && b.height > Math.max(60, sb.height * 0.5) && lum(cs.stroke) < 0.4; // pale grid lines are not accents
      if (stripe) add("left-accent", `a ${Math.round(b.height)}px vertical stripe in a diagram (${cs.stroke})`, svg.parentElement);
      const connector = ln.getAttribute("marker-end") || ln.tagName !== "path" || cs.fill === "none";
      if (connector && !stripe && lum(cs.stroke) < P.minLineLuminance) { hard++; firstHard = firstHard || cs.stroke; }
    }
  }
  // ---- connectors drawn through text (M/H/V/L paths, lines); endpoints sit on boxes, not text
  let crossed = 0, firstCross = null;
  for (const svg of document.querySelectorAll("svg")) {
    if (!visible(svg)) continue;
    const texts = [...svg.querySelectorAll("text")].map((tx) => ({ b: tx.getBBox(), s: tx.textContent }));
    for (const ln of svg.querySelectorAll("path[marker-end], line, polyline")) {
      const cs = getComputedStyle(ln);
      if (cs.stroke === "none" || nearWhite(cs.stroke)) continue;
      const segs = [];
      if (ln.tagName === "line") segs.push([+ln.getAttribute("x1"), +ln.getAttribute("y1"), +ln.getAttribute("x2"), +ln.getAttribute("y2")]);
      else {
        let x = 0, y = 0;
        const toks = (ln.getAttribute("d") || ln.getAttribute("points") || "").match(/[MLHV]|-?[\d.]+/g) || [];
        let cmd = "M";
        for (let i = 0; i < toks.length;) {
          if (/[MLHV]/.test(toks[i])) { cmd = toks[i++]; continue; }
          let nx = x, ny = y;
          if (cmd === "H") nx = +toks[i++];
          else if (cmd === "V") ny = +toks[i++];
          else { nx = +toks[i++]; ny = +toks[i++]; }
          if (cmd !== "M") segs.push([x, y, nx, ny]);
          x = nx; y = ny; if (cmd === "M") cmd = "L";
        }
      }
      for (const [x1, y1, x2, y2] of segs) {
        for (const { b, s } of texts) {
          const l = b.x + 0.5, r = b.x + b.width - 0.5, tp = b.y + 0.5, bt = b.y + b.height - 0.5;
          const hit = (x1 === x2) ? (x1 > l && x1 < r && Math.max(y1, y2) > tp && Math.min(y1, y2) < bt)
            : (y1 === y2) ? (y1 > tp && y1 < bt && Math.max(x1, x2) > l && Math.min(x1, x2) < r) : false;
          if (hit) { crossed++; firstCross = firstCross || s; }
        }
      }
    }
  }
  // ---- diagram text that leaves its diagram, or lands on other text
  for (const svg of document.querySelectorAll("svg")) {
    if (!visible(svg)) continue;
    const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.width ? svg.viewBox.baseVal : null;
    const texts = [...svg.querySelectorAll("text")].map((tx) => ({ b: tx.getBBox(), s: tx.textContent }));
    if (vb) {
      for (const { b, s } of texts) {
        if (b.x < vb.x - 0.5 || b.x + b.width > vb.x + vb.width + 0.5) add("overflow", `diagram text "${s}" runs past the diagram's edge (${(b.x + b.width - vb.width).toFixed(1)} units)`, svg.parentElement);
      }
    }
    let hits = 0, first = null;
    for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
      const a = texts[i].b, c = texts[j].b;
      const w = Math.min(a.x + a.width, c.x + c.width) - Math.max(a.x, c.x);
      const h = Math.min(a.y + a.height, c.y + c.height) - Math.max(a.y, c.y);
      if (w > 1 && h > a.height * 0.35) { hits++; first = first || `"${texts[i].s}" / "${texts[j].s}"`; }
    }
    if (hits) add("text-collision", `${hits} pairs of diagram labels overlap (first: ${first})`, svg.parentElement);
  }

  // ---- arrowheads: a turning connector needs a straight run-in, and its tip must reach a box
  let stubs = 0, tipGaps = 0, firstStub = null, firstGap = null;
  for (const svg of document.querySelectorAll("svg")) {
    if (!visible(svg)) continue;
    const boxes = [...svg.querySelectorAll("rect")].map((r) => r.getBBox()).filter((b) => b.width < 200 && b.height < 200);
    for (const ln of svg.querySelectorAll("path[marker-end]")) {
      const toks = (ln.getAttribute("d") || "").match(/[MLHV]|-?[\d.]+/g) || [];
      const pts = []; let x = 0, y = 0, cmd = "M";
      for (let i = 0; i < toks.length;) {
        if (/[MLHV]/.test(toks[i])) { cmd = toks[i++]; continue; }
        if (cmd === "H") x = +toks[i++]; else if (cmd === "V") y = +toks[i++]; else { x = +toks[i++]; y = +toks[i++]; }
        pts.push([x, y]); if (cmd === "M") cmd = "L";
      }
      if (pts.length < 2) continue;
      const [x1, y1] = pts[pts.length - 2], [x2, y2] = pts[pts.length - 1];
      const last = Math.hypot(x2 - x1, y2 - y1);
      const minRun = pts.length > 2 ? P.minRunIn : P.minRunIn - 1.5;  // a straight arrow between adjacent boxes may be short, never a bare head
      if (last < minRun) { stubs++; firstStub = firstStub || ln.getAttribute("d"); }
      const dist = Math.min(...boxes.map((b) => {
        const dx = Math.max(b.x - x2, 0, x2 - (b.x + b.width)), dy = Math.max(b.y - y2, 0, y2 - (b.y + b.height));
        return Math.hypot(dx, dy);
      }));
      if (boxes.length && dist > P.maxTipGap) { tipGaps++; firstGap = firstGap || ln.getAttribute("d"); }
    }
  }
  if (stubs) add("arrow-stub", `${stubs} arrows turn on a final run shorter than ${P.minRunIn} units: the head sits on the corner (first: ${firstStub})`, null);
  if (tipGaps) add("arrow-gap", `${tipGaps} arrow tips stop more than ${P.maxTipGap} units from any box (first: ${firstGap})`, null);

  // ---- text spilling out of the box it starts in
  let spills = 0, firstSpill = null;
  for (const svg of document.querySelectorAll("svg")) {
    if (!visible(svg)) continue;
    const rects = [...svg.querySelectorAll("rect")].map((r) => r.getBBox()).filter((b) => b.width < 200 && b.height < 300);
    for (const tx of svg.querySelectorAll("text")) {
      const b = tx.getBBox();
      const home = rects.filter((r) => b.x >= r.x && b.x <= r.x + r.width && b.y + b.height / 2 >= r.y && b.y + b.height / 2 <= r.y + r.height)
        .sort((p, q) => p.width * p.height - q.width * q.height)[0];
      if (home && b.x + b.width > home.x + home.width + 0.5) { spills++; firstSpill = firstSpill || tx.textContent; }
    }
  }
  if (spills) add("box-overflow", `${spills} diagram labels run past the right edge of their box (first: "${firstSpill}")`, null);

  if (crossed) add("line-through-text", `${crossed} connector segments cross diagram text (first: "${firstCross}")`, null);

  if (hard) add("hard-lines", `${hard} diagram lines or arrows drawn in near-black ${firstHard}; connectors must be softer than the text`, null);

  // ---- measure: characters per line of running text (paragraphs, list items)
  let longLines = 0, worst = 0, worstEl = null;
  for (const el of document.querySelectorAll("p, li")) {
    if (!visible(el) || el.closest("svg, table, .end, .note, .legend")) continue;
    const txt = (el.textContent || "").replace(/\s+/g, " ").trim();
    const lh = parseFloat(getComputedStyle(el).lineHeight);
    if (!lh || txt.length < 40) continue;
    const lines = Math.max(1, Math.round(el.getBoundingClientRect().height / lh));
    if (lines < 2) continue;
    const cpl = txt.length / lines;
    if (cpl > P.maxMeasure) { longLines++; if (cpl > worst) { worst = cpl; worstEl = el; } }
  }
  if (longLines) add("measure", `${longLines} paragraphs run longer than ${P.maxMeasure} characters per line (worst ${Math.round(worst)})`, worstEl);

  // ---- radii
  const radii = new Set(framed.map((el) => getComputedStyle(el).borderTopLeftRadius));
  if (radii.size > P.maxRadii) add("radius", `${radii.size} corner radii on framed containers: ${[...radii].join(", ")}`, null);

  return { checks: heads.length + all.length, findings: out, metrics: { typeSizes: steps, maxPt: +maxPt.toFixed(1), insets: [...insets.keys()], gutters: [...gaps], radii: [...radii] } };
})
