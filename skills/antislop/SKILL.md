---
name: antislop
description: Audit a system for machinery that lies about its own state, meaning checks that verify nothing, jobs that run but change nothing, alerts that never clear, undated stale data, orphaned code nothing calls, paginated reads treated as whole sets, mocks that no-op the logic they model, and fallbacks that quietly became the answer. Use for "run antislop", "why is this cron or sync doing nothing", "is this job actually running", "this alert never clears", "the dashboard numbers have not moved", "it broke but every check was green", "our tests pass but prove nothing", "find dead or zombie or orphaned code", "is this empty because it is broken or genuinely zero", "are we silently truncating rows", "what in this inherited repo is real", or checking a subagent's audit claims. For a technical-debt score and a cleanup queue use desloppify instead. Not a linter, a style pass, or general code review.
argument-hint: "[path or subsystem to audit]"
---

# Antislop

Hunt machinery that lies about its own state: checks that cannot fail, catch
blocks that return `[]`, jobs that run and change nothing, generated files
describing a world nobody rechecked. The types check and the tests pass, because
the tests assert the same wrong thing the code does.

## Do this first

1. **Read `references/patterns.md` in full, before searching anything.** It has
   all 18 families, the grep for each, and the step that confirms rather than
   suspects. This page deliberately does not summarise them: a summary is a page
   treated as the whole set, which is family 7.
2. **Say the target and the mode in one line.** Which repo or subsystem, and
   `audit-only` (the default) or `audit-and-fix`. If the user did not say,
   assume audit-only and state that you did.
3. **Prove your tools work before trusting a clean result.** Run one recipe
   without its filters and confirm it matches something, or run
   `scripts/check-recipes.sh <repo>` to do that for every recipe at once. Not
   hypothetical: a shipped recipe here used `rg -t rb`, which is not a valid
   ripgrep type, so it printed nothing, exited 0, and read as a clean codebase.
   The correct flag returned 33 hits in the same repo.
4. **Do not break production to prove a point.** Several confirmation steps say
   to revoke a credential, empty an input, or grow a payload until it fails.
   Those belong on a local copy or staging. Against anything shared or live, ask
   first and name exactly what you intend to break.

## The one question

For every green signal, ask:

> **What would this look like if it were broken?**

If the answer is "the same as it looks now", it is not a signal.

Two rules that decide most calls:

- **A passing check that cannot fail is worse than no check**, because it spends
  trust it has not earned.
- **Absence of a finding is not evidence of health** unless you know the detector
  could have found one.

## Workflow

1. **List everything that emits a green signal**: scheduled jobs, guards, health
   checks, alert paths, catch blocks, and every store other code treats as
   authoritative. Emit this list in your response before analysing it. An
   unstated inventory has no visible gaps, which is why it finds none. The gaps
   are findings: a schedule pointing at a route that no longer exists, a job
   nobody schedules, a checker nobody runs.

2. **Invert each one.** Write one sentence on what its failure would look like
   from outside, then check whether anything distinguishes that from normal
   operation. Where you cannot tell, you have a finding.

3. **Follow the data backwards.** For every store treated as truth, find who
   writes to it, then verify that writer runs. A documented write path that
   nothing calls decays from the day it ships.

4. **Date the reality-facing constants.** Any hardcoded list of real-world things
   (customers, staff, accounts, IDs, routes) is a promise that a human will
   remember to edit it. Run `git log -1 --format=%as -- <path>` on each and
   compare that date against what the file claims.

5. **Open the thing a human sees.** Run the page, call the endpoint, trigger the
   job with its dry-run flag, read the output. Static search finds some instances
   and misses the rest: in the audit this skill came from, search found 3 of 8
   hardcoded customer lists, and opening the page found the other 5, two of them
   rendering side by side on the page that had just been "fixed".

6. **Fix the family, not the instance.** One stale file feeding an LLM means a
   family of them. The repair is almost never "make it work", it is **make broken
   look different from healthy**. Per-family fixes are in `references/patterns.md`.

7. **Report in the format below.** The format is the gate: it is what makes
   steps 1 and 5 visible instead of assumed.

## Confirmation discipline

- **A delegated audit produces claims, not facts.** Verify each by opening the
  file:line yourself, or by running the command the delegate says it ran. Expect
  error in both directions: confident findings that dissolve on inspection, and
  whole categories the sweep never saw. Both happened while building this skill.
- **Check ordering can hide a defect.** Generated artifacts exist only after a
  build, so a typecheck run before the build never sees errors in them. If a
  config carries an ignore-errors escape anywhere, run the steps in the other
  order at least once.
- **Do not trust a comment about behaviour.** A docblock saying "not yet enabled"
  beside an enabled thing is itself a finding.
- **Watch both directions of a bad detector.** A recipe matching zero files
  reports a clean codebase. A recipe matching most of the codebase reports
  nothing usable and burns the audit. Both are broken.
- **Count before you read.** Pipe every recipe through `| wc -l` and `| wc -c`
  first. On a 7,400-file monorepo one recipe here returned 537KB, which is
  roughly 134k tokens: reading it whole ends the audit. Under a few hundred
  hits, read it. Over that, do not just narrow the pattern, **collapse to files
  and rank**:

      <recipe> | awk -F: '{print $1}' | sort | uniq -c | sort -rn | head -20

  Open the top ten files, not the top five hundred lines, and say in the Scope
  block that you sampled and how.
- **Rank by blast radius, not hit count.** Anything under a scheduler, a
  security or auth path, a migration, or a script that writes, goes first. The
  same expression in a React component is usually cosmetic.

## Reporting format

Emit these four blocks, in order.

**1. Scope.** Target, mode, and what you did not cover and why. Silent
truncation reads as "covered everything".

**2. Executed.** Every command, URL and page you actually ran, with the one-line
result of each. A finding may be labelled `confirmed` only if it cites a line
here. With no Executed block, nothing is confirmed.

**3. Findings**, worst first:
- **Title**: the lie, stated plainly. "The watchdog checks zero jobs and reports
  success" beats "watchdog path issue".
- **Family**: which of the 18.
- **Evidence**: file:line you opened, and the mechanism.
- **Blast radius**: what breaks and who notices. If nobody notices, say so,
  because that is the severity.
- **Fix**: one sentence.
- **Confidence**: `confirmed` (reproduced, cites Executed) or `suspected`.

**4. Coverage.** One line per family, 18 of them:
`<n>. <name> - confirmed N | suspected N | checked, nothing found | not checked: <why>`

Fewer than 18 lines means `references/patterns.md` was never opened, and the
audit does not stand.

---
*Hand-maintained, as of 2026-08-18. The worked examples in
`references/patterns.md` are dated incidents, not current state: two of them
were already false within a day of being written, which is the point.*
