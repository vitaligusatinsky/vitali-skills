---
name: condense
description: Shorten text to a hard character/byte budget while preserving intent, structure, and every concrete detail (paths, names, commands, constraints) — then VALIDATE the result by writing to a temp file and counting, looping until it fits. Triggers on /condense, "condense this to N chars", "shorten to under N", "fit this in N characters", "tighten this prompt/message/description to a limit", or any request to cut text to a character/word/byte target without losing meaning.
argument-hint: "<limit> [chars|bytes|words]  — then paste/attach the text (or point at a file)"
---

# Condense — validated text shortening to a budget

Cut text to a hard size budget **without losing meaning**. The deliverable is the
shortened text plus a proven count. Never claim it fits — measure it.

## Inputs
- **Budget**: a number + unit. Default unit = **characters** (`wc -m`). Accept `bytes` (`wc -c`) or `words` (`wc -w`). Common case: a tool/field cap like "under 4000 chars".
- **Text**: pasted in the message, attached, or a file path. If a path is given, read it.
- **Safety margin**: aim for **~3–5% under** the budget (e.g. target ≤3850 for a 4000 cap) so the count has headroom and isn't a nail-biter. If the user says "as close as possible," drop the margin.

If no budget is given, ask once for the number + unit. Don't guess a limit.

## What to PRESERVE (the payload — never cut these)
- **Intent and the ask** — what the reader must do/understand stays fully intact.
- **Concrete specifics**: file paths, identifiers, names, commands, numbers, URLs, flags, token/var names. These are the signal; losing one breaks the text.
- **Structure that carries logic**: numbered steps, a "hard rules" list, ordered priorities. Keep the skeleton; compress the prose around it.
- **Voice**: imperative and direct. Don't soften into hedge-speak.

## What to CUT (the noise)
- Redundancy and re-stated context; say each thing once.
- Filler and hedging ("in order to" → "to", "it is important to note that", "basically", "really", "very").
- Throat-clearing preambles and summaries that repeat the body.
- Long connective prose → compact punctuation: **semicolons, em-dashes, slashes, parentheses**. Merge short sentences. Use lists for parallel items.
- Adjectives/adverbs that don't change the instruction.

## What NEVER to do
- Don't drop a constraint, path, or rule to hit the number — re-compress prose instead. If the text genuinely cannot fit without losing a required detail, say so and show the smallest faithful version + by how much it overshoots, rather than silently cutting payload.
- Don't change meaning, invert a requirement, or merge two distinct rules into one.
- Don't add new claims or scope.

## Procedure (always do this — measurement is the point)
1. Identify budget + unit + margin. Identify the payload (specifics/structure) vs. the noise.
2. Draft the condensed version: cut noise, compress prose, keep payload + skeleton.
3. **Validate** — write the candidate to a temp file and count:
   ```bash
   cat > /tmp/condense-out.txt <<'EOF'
   <candidate text>
   EOF
   wc -m < /tmp/condense-out.txt   # characters (use -c for bytes, -w for words)
   ```
   Use a quoted `'EOF'` heredoc so `$`, backticks, and `!` in the text aren't expanded.
4. **Loop**: if over budget, cut more noise (not payload) and re-measure. If far under (>~15% headroom) and quality suffered, you may restore some clarity. Repeat until it's `≤ budget` and ideally within the margin.
5. Output: the final text in a copy-ready block, then one line — `N chars (limit M, K under)`. Note anything you had to drop if a faithful fit was impossible.

## Output format
- The condensed text, verbatim and ready to paste (fenced or plain per context).
- A final count line: e.g. `3,495 chars — under the 4,000 limit (505 to spare).`
- If it's a known artifact type (a `/goal` prompt, a PR body, a tweet, a meta description), keep that type's required opening/format intact.

## Synthetic examples

### 1. Marketing meta description → 155 chars
**Target:** ≤155 chars. **Before (228):**
> Vandall is a comprehensive platform that helps independent musicians and labels manage their music releases, collaborate with their teams, handle metadata and rights, and share files securely with everyone involved in a project.

**After (148):** `Vandall helps indie musicians and labels manage releases, collaborate, handle metadata and rights, and share files securely — one platform.`
*Kept: who/what/value. Cut: "comprehensive", "with everyone involved", repetition.*

### 2. Commit subject → 50 chars
**Target:** ≤50. **Before (78):** `fix the bug where the audio player would crash when you clicked pause too fast`
**After (44):** `fix(player): crash on rapid pause clicks`
*Kept: scope + cause. Cut: narrative; used conventional-commit shorthand.*

### 3. Slack status → 30 chars
**Target:** ≤30. **Before:** `In a meeting, will reply to messages later this afternoon`
**After (24):** `In mtg — replies this PM`

### 4. Over-budget with payload that can't be cut (honest fail)
**Target:** ≤40 chars. **Text:** `Deploy commit a37c587 to prod-eu and prod-us, then run smoke tests`
**Result:** smallest faithful = `Deploy a37c587 to prod-eu+us, smoke-test` (40) ✓ — but if it were ≤25, report: *"Can't fit under 25 without dropping a region or the commit SHA (both required). Smallest faithful is 40 chars."* Never silently drop `prod-us`.

## Notes
- For very large inputs, condense section-by-section so structure survives, then measure the whole.
- Character counts vary by tool (some count code points, some UTF-16 units, some bytes). `wc -m` = characters in the locale; `wc -c` = bytes. When a platform's limit is unclear, validate against `wc -c` (bytes ≥ chars) to stay safe.
- This skill measures; it does not assume. A condensed text without a measured count is not done.
