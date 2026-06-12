---
name: supercharge
description: Audit and upgrade a repo's Claude Code configuration into an integrated, token-efficient development system — context diet, parallel-session safety, stop-gate verification, worktrees, model tiering, footgun hooks. Use when the user says /supercharge, "tune this repo's Claude config", "apply the config playbook here", or "look for workflow improvements".
---

# Supercharge — Claude Code config audit & upgrade

Apply a proven Claude Code config playbook to the current repo — the patterns
below come from a real restructure of a busy monorepo (many parallel sessions,
heavy subagent orchestration); adapt them to this repo's stack.

**Operating rules:** detect-before-create (every step is idempotent — skip what
already exists), never commit/branch unilaterally, verify every change (jq for
JSON, smoke-run every hook), and note the current branch up front (parallel
sessions may own the working tree).

## Phase 1 — Inventory (parallel subagents, read-only)

Dispatch 1-2 Explore agents to map, then synthesize:

1. **Always-loaded context weight:** `wc -l` on root + nested CLAUDE.md, AGENTS.md,
   and every `.claude/rules/*.md` (these AUTO-LOAD every session). Note anything
   loading that most sessions don't need.
2. **Existing plumbing:** `.claude/settings.json` + `settings.local.json` (hooks by
   event, permission count), `.claude/hooks/`, `.claude/agents/` (and whether agents
   have `model:` frontmatter), `.claude/skills/`, `.mcp.json`, `.worktreeinclude`.
3. **Stack facts needed later:** package manager (bun/pnpm/npm/yarn — check lockfile),
   monorepo layout (workspaces? apps/ packages/?), per-package `typecheck`/`lint`/
   `test` scripts, CI gates.
4. **Repo-specific footguns:** scan CLAUDE.md, `docs/learnings/`, `docs/solutions/`
   for documented recurring incidents (candidates for enforcement hooks).
5. **Global config overlap:** check `~/.claude/settings.json` for the SessionStart
   git-state hook and other global hooks — don't duplicate them at project level.

## Phase 2 — Gap analysis against the playbook

Score each pattern: ✅ present / ⚠️ partial / ❌ missing / N/A.

| Pattern | Test | Fix |
|---|---|---|
| **Context diet** | auto-loaded CLAUDE.md + rules > ~250 lines total | Split: `.claude/rules/critical-guardrails.md` digest (one line per rule + pointer) stays auto-loaded; full docs move to `.claude/rules-library/` (NOT auto-loaded). `git mv`, then grep + update ALL references (`grep -rn '\.claude/rules/' --include='*.md' --include='*.sh' --include='*.py'`, skip historical docs/) |
| **SessionStart git-state** | global hook exists? | If global `~/.claude/hooks/session-start-git-state.sh` is registered, nothing to do. Only add per-project if global is absent |
| **Stop-gate verification** | Stop hook running typecheck/lint on edited packages | Two hooks: PostToolUse(Edit\|Write) appends edited source files to `/tmp/cc-<repo>-edits-<session_id>`; Stop hook maps files→packages, runs the package's check command, emits `{decision:"block", reason:...}` on failure. MUST include the `stop_hook_active` loop guard. Adapt: file extensions, package-path regex, and check command to this repo's stack |
| **Worktree readiness** | `.worktreeinclude` at root | Add it listing every gitignored runtime file a fresh worktree needs (`.env.local`, `.env.development.local`, `**/.env*.local`, local certs, etc. — derive from .gitignore + what dev scripts read) |
| **Model tiering** | `.claude/agents/*` missing `model:` | Read-only/search agents → `haiku`; synthesis/diagnosis → `sonnet`; review/spec keep inherit or `opus`. If the repo has an agent registry/codegen (e.g. an `agents:build` script), regenerate after editing |
| **Footgun hooks** | documented incidents with no enforcement | For each recurring incident found in Phase 1.4, propose a PreToolUse guard (block) or PostToolUse reminder (inject context). Propose only — these need user judgment |
| **Insights-derived rules** | CLAUDE.md missing them | Assets-verbatim, docs-first debugging, confirm-target-component-before-UI-work, branch re-check before push. Usually global already — add per-repo only if repo-specific variants exist |
| **Permission hygiene** | settings.local.json allowlist > ~50 overlapping entries | Report consolidation candidates only — never edit allowlists without explicit approval |

## Phase 3 — Align with the user

One AskUserQuestion round, only for genuinely open choices (typically: diet
aggressiveness, stop-gate vs per-edit verification, which footgun hooks to
enforce vs just document). Recommend the playbook default unless
this repo's facts differ. Skip the question for anything Phase 2 marked ✅ or N/A.

## Phase 4 — Apply & verify

1. Make the approved changes. Reuse the global hooks where possible; write
   project hooks into `.claude/hooks/` and register in `.claude/settings.json`.
2. **Verification gate (all must pass before reporting done):**
   - `jq empty` on every touched JSON file
   - `chmod +x` + smoke-run every new hook with a synthetic stdin payload
     (e.g. `echo '{"session_id":"smoke"}' | hook.sh` → expect clean exit)
   - Stop-gate dry run with no marker file → exit 0
   - Grep proves zero stale references to moved rule files (outside docs/ history
     and `.claude/worktrees/`)
   - Repo's own CI-style gates if config files are code-adjacent (registry checks,
     codegen sync)
3. Report: per-pattern before→after, estimated tokens saved per session, the
   exact uncommitted change set (`git status --porcelain`), and the current
   branch with a recommendation for how to commit. Do not commit.

## Portability notes

- **Check command resolution:** prefer the package's own `typecheck` script; fall
  back to `tsc --noEmit`, `cargo check`, `ruff check`/`mypy`, `go vet` by stack.
  If a check takes >2 min for the repo, warn the user before wiring it to Stop.
- **Single-package repos:** the marker→package mapping collapses to "any source
  edit → run the check once".
- **Non-TS repos:** adapt marker extensions (.rs, .py, .go…) and skip patterns
  that don't apply (e.g. agents/MCP if absent) — report them as N/A, don't force.
