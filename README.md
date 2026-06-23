# vitali-skills

Agent skills by [@vitaligusatinsky](https://github.com/vitaligusatinsky) for Claude Code, Codex, and other agents — installable via [skills.sh](https://skills.sh) / the `skills` CLI.

This is the canonical home for my general-purpose skills. (Brand-scoped sets live elsewhere, e.g. [`designanswers-skills`](https://github.com/vitaligusatinsky/designanswers-skills).)

## Install

```bash
# all skills in this repo
npx skills add vitaligusatinsky/vitali-skills

# a specific skill
npx skills add vitaligusatinsky/vitali-skills/skills/condense
```

Or drop a skill folder into `~/.claude/skills/` for Claude Code.

## Skills

### `grounded-analysis`
Analysis you can trust — of meetings and mentoring sessions, ideas, plans,
performance, and decisions. Grounds every claim in the source before asserting it,
separates observation from judgment, labels confidence (`[confirmed]` / `[inferred]`
/ `[speculative]`), and runs each sharp or critical claim through an adversarial
self-check before it ships. Built to stop the most common analysis failure: an
insight-shaped claim, stated as fact, that the evidence doesn't actually support.
Keeps critiques sharp *and* cited. Adaptive (one-shot for clear asks, frame-first
when stakes are high); five domain adapters. Triggers on `/analyze`, "give me
analysis", "what's your read on this".

### `clip`
Copy the deliverable from the agent's last response straight to the clipboard —
strips AI commentary, never re-emits content through the model (shell pipelines
from the response file to `pbcopy` only). Supports plain-text mode (`/clip clean`)
and targeted slices (`/clip the SQL query`). Triggers on `/clip`.

### `condense`
Validated text shortening to a hard character/byte/word budget. Cuts text to fit a
limit (e.g. a 4000-char field) **without losing meaning** — preserves intent,
structure, and every concrete detail (file paths, names, commands, constraints),
then **proves the result fits** by writing to a temp file and counting (`wc -m`),
looping until it's under budget. Refuses to drop a required detail to hit a number;
if a faithful fit is impossible it says so and shows the smallest faithful version.
Triggers on `/condense`, "shorten this to under N chars", "fit this in N characters".

### `macwhisper`
Pull transcripts from the local MacWhisper SQLite database — find a recording by a
quoted phrase, list recent sessions, fetch a full transcript with timestamps, or
export to markdown. Triggers on `/macwhisper`, "find the recording where I said X",
"pull from macwhisper", "which recording was this from".

### `supercharge`
Audit and upgrade a repo's Claude Code configuration into an integrated,
token-efficient development system. Inventories always-loaded context weight,
scores the repo against a playbook (context diet via on-demand rules-library,
SessionStart git-state guard for parallel sessions, Stop-gate typecheck hooks,
`.worktreeinclude` worktree readiness, subagent model tiering, footgun-to-hook
conversion), asks one alignment round, then applies and verifies every change
(JSON validation, hook smoke-runs, stale-reference greps). Idempotent; adapts
to the repo's package manager and stack. Triggers on `/supercharge`,
"tune this repo's Claude config".

## License

MIT
