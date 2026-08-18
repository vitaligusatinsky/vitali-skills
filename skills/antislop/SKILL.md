---
name: antislop
description: >
  Find code that lies about its own state: guards that check nothing, checks
  that record a claim instead of running a command, reads that return one page
  and get treated as the whole set, generated artifacts describing a world
  nobody rechecked, test doubles that no-op the semantics they exist to model,
  and limits nobody has ever measured. Use when asked to run antislop, audit a
  repo for dead or false-green machinery, work out why an alert never clears,
  check whether automation is really running, find out why something broke that
  every check called healthy, or investigate a system that looks fine but
  nobody trusts. Not a linter and not a style pass.
---

# Antislop

## What this is for

Slop is not ugly code. Ugly code announces itself and linters catch it.

Slop is code that **lies about its own state**. It reports success it has not
earned, serves data it has not checked, or maintains a store that nothing
writes to. Every line is valid. The types check. The tests pass, because the
tests assert the same wrong thing the code does.

It survives because **broken looks exactly like healthy**. A cron that stopped
firing and a cron with nothing to do produce the same silence. An outage and a
quiet day both return an empty list. A dashboard nobody updated and a business
that did not change render the same numbers.

Your job is to find the places where those two states are indistinguishable,
and make them distinguishable.

## The one question

For every green signal in the system, ask:

> **What would this look like if it were broken?**

If the answer is "the same as it looks now", it is not a signal. It is
decoration. That single question finds most of what follows.

Two corollaries worth holding:

- **A passing check that cannot fail is worse than no check**, because it
  spends trust it has not earned.
- **Absence of a finding is not evidence of health** unless you know the
  detector could have found one.

## When to use this

Reach for it when:

- an alert keeps firing and nobody can clear it
- a job is "running" but nothing it should change ever changes
- a number on a dashboard has not moved in a suspiciously long time
- you inherit a repo and want to know which of its machinery is real
- something broke in production that every check said was fine

Do not reach for it for general code review, performance work, or style. It
does not score a codebase and it does not chase technical debt. If you want a
health score and a cleanup queue, that is a different tool. This one hunts a
specific species: **machinery that is not doing what it claims**.

## Workflow

Work through these in order. Do not skip step 5, which is where most of the
real findings come from.

### 1. Inventory what claims to be healthy

List everything in the repo that produces a green signal or an assurance:

- scheduled jobs (cron config, CI schedules, queue workers, launchd/systemd)
- health checks, watchdogs, guards, monitors, freshness checkers
- alerting paths and their dedup/suppression logic
- fallbacks, retries, and catch blocks
- data sources that other code treats as authoritative

Write the list down before analysing any of it. The gaps in the list are
findings too: a scheduler nobody remembered, a route with no schedule, a
schedule pointing at a route that no longer exists.

### 2. Invert each one

For each item, write one sentence: what its failure would look like from the
outside. Then check whether anything in the system would distinguish that from
normal operation. Anything where you cannot tell is a finding.

### 3. Follow the data backwards

For each store the system treats as truth, ask **who writes to it**. Then
verify that writer actually runs. A store with a documented write path that
nothing calls is a store that decays silently from the day it ships.

### 4. Read the reality-facing constants

Any hardcoded list of things that exist in the real world (customers, team
members, accounts, IDs, routes, environments) is a promise that a human will
remember to edit it. They do not. Date every such list you find, by asking git
when it last changed and comparing that against the reality it describes.

### 5. Open the thing a human actually sees

This is the step that separates a real audit from a plausible one. Run the
page. Call the endpoint. Trigger the job with its dry-run flag. Read the
output.

Static search reliably finds some of the instances and misses the rest. In the
audit this skill was built from, searching found three hardcoded lists; opening
the page in a browser found five, and two of the missed ones were rendering
side by side on the page that had just been "fixed".

### 6. Fix the class, not the instance

When you find one stale file feeding an LLM, you have almost certainly found a
family. Fixing that one file leaves the family. Prefer a change that makes the
whole category safe (see "How to fix" below).

### 7. Report with evidence, and mark your confidence

Every finding gets a file:line you actually opened, a concrete failure
scenario, and one of two labels: **confirmed** (you reproduced it) or
**suspected** (it looks wrong but you have not proven it). Never blur them.

## Verification discipline

The findings are the product, so the standard for them is high.

- **A delegated audit produces claims, not facts.** Verify each at the source
  before repeating it. Expect both directions of error: overstated findings
  that dissolve on inspection, and whole categories the sweep never saw.
- **Reproduce before reporting.** For a "this check cannot fail" claim, break
  it deliberately and watch it stay green. For a "this test does not catch it"
  claim, revert the fix and watch the test pass.
- **Check ordering can hide a defect.** Some errors only surface in a specific
  sequence (for example, generated types that only exist after a build, so
  typechecking before the build never sees them). If a tool has an "ignore
  errors" escape anywhere in its config, assume something is hiding behind it
  and run the steps in the other order.
- **Measure limits, do not guess them.** When a failure smells like a cap
  (URL length, body size, batch count, timeout), binary-search the real ceiling
  against the real system, then compare it against today's production size. The
  gap is your remaining runway. A documented limit and the enforced one are
  often different numbers.
- **Prefer the remote or live reference over the local copy.** A stale checkout
  produces confident, wrong, acted-upon conclusions, and it catches auditors as
  readily as it catches code. Fetch before you reason.
- **Do not trust a comment about behaviour.** Comments describe the intent of
  whoever wrote them, often years and several refactors ago. A docblock saying
  "not yet enabled" next to an enabled thing is itself a finding.

## The patterns

Full catalogue with detection recipes, confirmation steps, and worked examples:
`references/patterns.md`. Read it when you start an audit rather than working
from memory, because the value is in the specific greps and the confirmation
step for each.

Summary of the families:

| Family | The lie | Classic instance |
|---|---|---|
| **False green** | Reports health it never verified | A guard whose input file moved; it finds nothing, checks nothing, returns success |
| **Empty is not absent** | Cannot tell outage from genuine zero | A `catch` that returns `[]`, so a revoked token and an empty inbox are the same observation |
| **Orphaned machinery** | Exists, nothing drives it | An exported writer with no callers; the table it maintains only ever got rows from migrations |
| **Stale truth** | Hand-kept data the world moved past | An undated JSON feeding an LLM's context, describing a customer state from six months ago |
| **Unactionable alert** | Nags without a resolution path | An alert naming a fix that has no runnable entry point, so it re-fires forever and gets ignored |
| **Success-shaped failure** | Failure encoded as a normal result | HTTP 200 with a populated `errors` array; telemetry records it as a healthy run |
| **Partial is not whole** | A page treated as the whole set | A server row cap returns 1,000 of 1,525 with a success status; a count computed over it is confidently wrong |
| **Proof by assertion** | Records a claim instead of a measurement | A proof harness accepting `--check typecheck=pass`, a string the caller typed, with nothing running the command |
| **Record outlived the fact** | A generated artifact describes a world it was never rechecked against | Types generated from a local rebuild promise a column production does not have, so the compiler certifies code that cannot run |
| **Stale reference** | A conclusion drawn from a local copy that moved on | An audit run in a checkout 13 commits behind reports drift that does not exist |
| **Double models nothing** | A test fake no-ops the semantics it exists to model | A query-builder fake whose `order()` and `limit()` do nothing, so inverting the sort leaves the suite green |
| **Threshold nobody measured** | Works, with no idea how close the edge is | A list of ids passed whole into a URL; fine at 100, a hard 400 at 676, and nobody knew the number |
| **Unnarrowed value** | Free text reaching a typed boundary | One provenance string in an id column; the parser rejects rather than ignores, and a whole page 500s |

## How to fix

The repair is usually not "make it work". It is **make broken look different
from healthy**. Principles, in rough priority order:

1. **Fail loudly instead of returning empty.** A checker that cannot find its
   input must throw, not return zero results. Zero results is a claim.

2. **Make "unavailable" a third state.** Anywhere code renders or returns a
   count, distinguish *loaded and empty* from *could not load*. In a UI that
   is a visible message, not a blank. In an API it is a 503, not `[]`.

3. **Never fabricate a number you did not measure.** If the count is unknown,
   render "unknown" or a dash. A confident zero is worse than an obvious gap,
   because it terminates the reader's curiosity.

4. **Date anything hand-maintained.** When a file has no owner and no refresh
   job, the honest fix is often not to update it but to make its age visible
   at the point of use. Undated stale data misleads. Dated stale data is just
   history, and a reader can discount it. This one change fixes a whole family
   at once.

5. **Every alert carries the command that resolves it.** If the remediation is
   a function with no entry point, build the entry point. An alert that cannot
   be acted on trains people to ignore the channel it arrives in.

6. **Distinguish idempotent no-ops from failures.** "Already exists", "already
   a member", "nothing to do" are successes. Treating them as fatal makes an
   operation work exactly once, which is a bug that only appears on the second
   run. Verify the end state rather than trusting the write's return value.

7. **Delete rather than preserve, when the data has no live source.** Removing
   wrong data is strictly better than serving it. If something reads it, point
   that reader at whatever store is actually maintained.

8. **Add the test that would have caught it, and prove the test works** by
   reverting the fix and watching it fail. A regression test that passes
   against the bug is decoration.

## Reporting format

Order findings by severity, worst first. For each:

- **Title**: the lie, stated plainly. "The watchdog checks zero jobs and
  reports success" beats "watchdog path issue".
- **Evidence**: file:line you opened, plus the specific mechanism.
- **What breaks in practice, and who notices.** If the answer is "nobody
  notices", say so, because that is the severity.
- **Fix**: one sentence.
- **Confidence**: confirmed or suspected.

Say plainly which categories you checked and found nothing in. A reader cannot
tell thorough coverage from a lucky sweep unless you tell them.

If the audit bounded its own coverage (sampled, capped, skipped a language),
say that too. Silent truncation reads as "covered everything".
