# Antislop pattern catalogue

Each family below has the same shape: **the lie**, a **detection recipe** you
can run, a **confirmation step** that proves it rather than suspecting it, and
**the fix that closes the class** rather than the instance.

Read this at the start of an audit. Working from memory produces plausible
findings; working from the recipes produces reproducible ones.

A note on confirmation: every recipe here ends in an action, not a judgement.
If you cannot state what you ran and what it printed, you have a suspicion.
Label it as one.

**Check that your own recipe ran.** A search that matches nothing and a codebase
with nothing to find print the same thing: silence. Before trusting a clean
result, run the pattern without its filters and confirm it matches *something*.
**How this file has failed before**, kept because the class recurs and the
specifics are cheap to forget:

- `grep --include='*.{ts,js}'` matches zero files. `--include` takes an fnmatch
  glob, fnmatch has no brace expansion, and the quotes stop the shell expanding
  it. Exits 0, prints nothing. Repeat the flag, or use `rg -t ts -t js`. Five
  recipes shipped with this.
- `rg -t rb` is not a valid type (`ruby` is). rg exits non-zero to stderr; a
  pipe swallows it; the reader sees a clean sweep. Shipped in the flagship
  family-1 recipe, one paragraph below a warning about exactly this class.
- An `rg` with no search path may read stdin instead of the directory,
  depending on the shell it is pasted into. Every recipe here now passes an
  explicit `.`.

None of those three are present now. `scripts/check-recipes.sh <repo>` runs
every block in this file and fails on any that matches nothing, matches too
much, or hangs. Run it after editing this file.


## Contents

1. False green
2. Empty is not absent
3. Orphaned machinery
4. Stale truth
5. Unactionable alert
6. Success-shaped failure
7. Partial is not whole
8. Proof by assertion
9. The record that outlived the fact
10. The stale reference
11. The double that models nothing
12. The threshold nobody measured
13. Unnarrowed value at a typed boundary
14. The idempotent no-op treated as fatal
15. Dry-run forever
16. Dedup that suppresses new information
17. Silent substitution: the fallback that became the answer
18. The fail-open gate

Plus a closing section on the two cross-cutting disciplines.

---

## 1. False green

**The lie:** it reports health it never verified.

**Detection**
```bash
# guards and checkers that read a path or config that may have moved
rg -n "exists|readFile|readdir|glob\(" -t ts -t js -t py -t go -t ruby \
  . | grep -iE "check|guard|verify|validate|watchdog|health"
```
For each, ask what it does when its input is missing. If the answer is
"finds nothing, so passes", it is a false green.

**Confirmation:** rename or empty its input, run it, watch it stay green.

**Fix:** a checker that cannot find its input must **throw**, not return zero
results. Zero results is a claim about the world.

**Seen in the wild (2026-08-18, since fixed).** A cron watchdog, the only
detector for a job that silently stops firing, read its schedule from a config
file that a build cleanup had deleted months earlier. The commit message said
"the platform never read it", true of the platform and false of the watchdog. It
returned an empty schedule, found nothing overdue, and answered
`{ checked: 0, overdue: 0, success: true }` every six hours. Thirty-seven jobs
were unwatched, including the ones meant to catch everything else. The loader
had no test because it was not exported.

Note the date. That system was repaired hours after this was written, so the
paragraph above describes a world that no longer exists. It is left here dated
rather than deleted, because an undated version of it would be family 4.

---

## 2. Empty is not absent

**The lie:** an outage and a genuine zero are the same observation.

**Detection**
```bash
rg -n -B3 --no-heading "return \[\]|return \{\}|return 0" -t ts -t js \
  . | rg -B3 "catch|except|rescue" | rg "return"
```

**Confirmation:** revoke the credential or block the network, call the code,
and see whether the caller can distinguish the result from a quiet day.

**Fix:** make *unavailable* a third state. In a UI a visible message, not a
blank. In an API a 503, not `[]`. Never render a confident zero you did not
measure. A dash is honest, a zero terminates the reader's curiosity.

---

## 3. Orphaned machinery

**The lie:** it exists, so someone assumes it runs.

**Detection:** for every writer, find its callers; for every table or store,
find its writers; for every scheduled route, find its schedule, and for every
schedule, find its route.
```bash
# a schedule pointing at nothing, or a job nobody schedules
rg -n '"?(schedule|cron)"?\s*[:=]' -t json -t yaml -t toml \
  --glob '!*lock*' --glob '!*/node_modules/*' .
```

**Confirmation:** check the store's newest row, or the job's last run. If the
newest row predates the feature's launch, only the migration ever wrote to it.

**Fix:** delete it, or wire it. A third state, "kept just in case", is how a
store decays silently from the day it ships.

**Seen in the wild (2026-08-18, since fixed).** A customer registry shipped
`upsertCustomer` and `upsertCustomerWorkspace`, exported, idempotent, tested,
and called by nothing. Every row in both tables had been hand-written as an
INSERT inside a migration. The ticket that shipped it listed "onboarding a
customer is a single registry write" as its acceptance criterion. That criterion
was never met and never noticed, because a registry nobody writes to looks
exactly like a registry nobody has needed to write to yet. Both functions have
callers now.

---

## 4. Stale truth

**The lie:** hand-kept data the world has moved past, presented undated.

**Detection:** any hardcoded list of real-world things: customers, staff,
accounts, regions, model names, price tiers.
```bash
# antislop:no-verify template, point it at a real file
git log -1 --format=%as -- path/to/list.json   # date every list you find
```

**Confirmation:** compare the list against the system of record and count the
disagreements.

**Fix:** the honest repair is often not to update it but to **make its age
visible at the point of use**. Undated stale data misleads; dated stale data
is history a reader can discount. One change, whole family.

**Seen in the wild.** A customer-onboarding JSON last touched six months earlier
described a signed customer as being in "prep", with a deadline long past and
seven pending checklist items. Both a retrieval index and an assistant's context
window read it, so the assistant reported all of it in the present tense, with
no hedging, because nothing in the pipeline carried the file's age. Five sibling
files were the same age. Stamping every one of them with "hand-maintained, as of
<date>, N months old, do not state as current" fixed the whole family in a single
change, and was the only available fix for the files with no live equivalent.

---

## 5. Unactionable alert

**The lie:** it nags without a resolution path, so it trains people to ignore
the channel it arrives in.

**Detection:** for each alert string, search for the command that resolves it.
If the remediation is a function with no entry point, there is no path.

**Confirmation:** try to clear it using only what the alert tells you.

**Fix:** every alert carries the runnable command that resolves it. If that
command does not exist, building it *is* the fix. Emit it **without** the
destructive flag, so pasting it prints a plan instead of performing a write.

**Seen in the wild.** A weekly alert told operators to "map the workspace with
`upsertCustomerWorkspace`", a function with no CLI, no route and no caller. The
alert was correct every week for weeks, and impossible to act on every time. The
fix was not to tune the alert; it was to build the entry point it had been
naming all along, then put the exact pre-filled command in the message.

---

## 6. Success-shaped failure

**The lie:** failure encoded as a normal result.

**Detection:** responses carrying both a success status and an error payload:
`200` with a populated `errors` array, an exit code of 0 with a stderr dump, a
"partial success" that telemetry counts as a run.

**Confirmation:** force the failure and read what the telemetry recorded.

**Fix:** derive the recorded outcome from the payload, not the envelope.

---

## 7. Partial is not whole

**The lie:** a read returned a **page** and the caller treats it as **the set**.

This one is nastier than it sounds, because the truncation is usually silent by
design. Server-side row caps return a partial result with a success status. The
caller then filters, counts, or de-duplicates over the partial set and produces
a **confident wrong answer with no missing-row cue**. Aggregations are the worst
case: a list that is short looks short, but a total that is wrong looks fine.

**Detection**
```bash
# list reads with no explicit bound
# Line-scoped, so a fluent chain with .limit() on the NEXT line reads as
# unbounded. Expect false positives; confirm each by reading the full chain.
rg -n "\.select\(\*?\)|SELECT \*" -t ts -t js -t py --glob '!*.test.*' .
# in-memory aggregation over a fetched set
rg -n "(data|rows|results|items|records)\.(length|reduce\()" -t ts -t js .
```

**Confirmation:** ask the server for the true count and compare it against what
the code received.
```bash
# antislop:no-verify needs a live API and credentials; add your auth header
curl -sI "$API/table?select=id" -H "Prefer: count=exact" -H "Range: 0-0" \
  | grep -i content-range        # -> 0-0/1525 while the code got 1000
```

**Watch for the fake fix.** A client-side `limit: 10000` may not beat a
server-side cap. Verify by requesting more than the cap and counting what comes
back. Code that *looks* bounded correctly is the harder version of this bug.

**Fix:** page until a short page returns, and give the pager a **hard ceiling
that throws** rather than truncating, otherwise the fix reintroduces the bug at
a larger number. Paging requires a **total order**: a non-unique sort key lets
rows repeat or vanish across page boundaries, so add a unique tiebreaker.

---

## 8. Proof by assertion

**The lie:** a system records a result that the caller *typed* rather than one
it *derived from execution*.

This is the purest form of the species. A proof harness that accepts
`--check typecheck=pass` has recorded a string, not a measurement. Everything
downstream treats it as evidence.

**Detection:** for every check id, status field or "verified" flag, find the
code that sets it. If the setter's input is an argument rather than an exit
code, an assertion or a parsed output, it is self-attested.

**Confirmation:** pass the claim without doing the work and watch it be accepted.

**Fix:** the recorder runs the command and derives pass/fail from the real exit
code. Where it genuinely cannot execute a check, it **says which ones it
could not run** instead of implying full coverage.

---

## 9. The record that outlived the fact

**The lie:** a machine-generated artifact or ledger describes a reality it was
never re-checked against, and it is trusted *because* it is machine-generated.

Migration ledgers, generated type definitions, lockfiles, cached schemas,
inventory manifests, infrastructure state files. All are written once from a
world that has since moved.

**Detection:** for each generated artifact, find what it was generated **from**,
and whether that source is the thing production actually runs. Generated types
built from a local rebuild describe the *migrations*, not the *database*.

**Confirmation:** introspect the live system and diff it against the artifact.
```bash
# does the column the types promise actually exist?
# antislop:no-verify needs a live API and credentials; run against your own
curl -s "$API/table?select=suspicious_column&limit=1" | grep -q "42703" \
  && echo "types promise a column production does not have"
```

**Fix:** a scheduled or pre-deploy job that diffs the artifact against the live
system. Until that exists, treat the artifact as a hypothesis. Note the trap:
a type checker passing over such an artifact is itself a false green. It
certifies code against a description, not against reality.

---

## 10. The stale reference

**The lie:** a conclusion drawn from a local copy that has moved on.

Universal to git checkouts, cached configs, memoised clients, replicas, and
forked environments. It is especially dangerous for automated agents, which
have no instinct that their working copy might be old.

**Detection:** any tool output used as evidence about *current* state. Ask what
it read, and when that was last refreshed.

**Confirmation:** refresh, re-run, and compare the two answers.
```bash
# antislop:no-verify differs on every feature branch by design; read it, do not gate on it
git fetch origin && git rev-parse HEAD origin/main   # are these the same world?
```

**Fix:** make freshness a **precondition of the report, not a habit of the
reader**. The tool that prints state fetches first and labels itself `STALE`
when it cannot. A human or agent should never have to remember to ask.

---

## 11. The double that models nothing

**The lie:** a test fake silently no-ops the very semantics it exists to model,
so the tests certify inverted logic.

A hand-written query-builder fake whose `order()` and `limit()` return the
builder unchanged will pass whether the code sorts ascending or descending, and
whether it takes one row or a thousand.

**Detection**
```bash
rg -n "order: \(\) =>|limit: \(\) =>|sort: \(\) =>|=> builder|=> this" \
  --glob '*.test.*' --glob '*.spec.*' .
```
Count how many *independent copies* of the fake exist. Copies drift; a shared
double at least drifts once.

**Confirmation:** invert the behaviour in the source (flip the sort direction,
change the limit) and re-run. If the suite stays green, the double models
nothing.

**Fix:** do not fake semantics you depend on. Run that logic against the real
engine (an in-process or containerised instance is usually cheap enough), and
add a rule rejecting new ad-hoc doubles. If a shared fake is unavoidable, hold
it to a conformance test that runs the same queries against the real engine and
asserts identical results.

---

## 12. The threshold nobody measured

**The lie:** it works, and nobody knows how close to the edge it is.

A defect that is inert below a limit and live above it. URL length caps,
request body limits, batch sizes, argument-list limits, timeouts, connection
pools, memory. The margin was never there. It simply had not been crossed.
These arrive as sudden total failures of something that "has always worked",
usually right after a data import or a new customer.

**Detection:** any collection whose size is proportional to a growing table and
which is passed somewhere whole: an `IN (...)` list, a query string, a request
body, a fan-out loop.

**Confirmation: binary-search the real limit against the real system.** Do not
guess it and do not trust the documented value.
```bash
# antislop:no-verify call_with_n_items is a placeholder for your own call
# Grow the input until it fails; the last success is your real ceiling. If every
# row says FAIL the harness is not wired up, NOT that the ceiling is below 100.
for n in 100 500 675 676 1000; do
  printf '%s ' "$n"; call_with_n_items "$n" >/dev/null 2>&1 && echo ok || echo FAIL
done
```
Then compare that ceiling against today's production size. The gap is your
remaining runway, and it is worth writing down.

**Fix:** chunk at the boundary inside a shared helper so callers never have to
know the limit exists, and assert the runway in a test using the real
production number, so the test fails when the margin closes rather than when
the page does.

---

## 13. Unnarrowed value at a typed boundary

**The lie:** a free-text value is passed where a type is required, and one bad
row takes down a whole surface.

Strict parsers reject rather than ignore. A database will raise on a malformed
UUID instead of returning no rows; a date parser throws instead of skipping.
So a single unexpected value in a column that *usually* holds the right shape
becomes a total outage of every page that reads it.

The usual cause is a field used for two purposes: a provenance column holding
`docs/services.md` for some rows and an identifier for others, with a
`primary ?? fallback` expression feeding both into a typed query.

**Detection:** every `a ?? b` or `a || b` where `a` and `b` come from different
fields, and the result is passed to a typed query, parser or cast.

**Confirmation:** query the column and count values that do not match the
required shape. One is enough to break the surface.

**Fix:** narrow before querying. Filter the list to values of the right shape
rather than trusting the string. Anchor the check: a value that *contains* a
well-formed identifier is not one, and a loose match still fails at the parser.

---

## 14. The idempotent no-op treated as fatal

**The lie:** "already done" is reported as an error, so the operation succeeds
exactly once and fails forever afterwards.

External APIs routinely return an error status for a no-op: *already exists*,
*already a member*, *nothing to update*. A client that throws on any non-2xx
turns that into a hard failure. Tests never catch it because they start from a
clean state, so the bug only appears on the second run, in production, often
months later.

It is at its worst behind a fail-closed guard: the remote side has the change,
the local side refuses to record it, and every retry re-reports failure while
the two systems drift further apart.

**Detection**
```bash
rg -n -B2 -A4 "already exist|already in|AlreadyExists|duplicate key|409" \
  -t ts -t js -t py . | rg -i "throw|raise|reject|Error\("
```
Look for an unconditional throw on any non-2xx, with no branch for the
already-done case.

**Confirmation:** run the operation twice. The second run failing is the proof.

**Fix:** verify the **end state**, not the write's return value. Attempt the
write, remember what it said, then read back and let actual state decide, with
a short bounded retry if the API is eventually consistent. Keep the fail-closed
guarantee: the goal is that a correct end state reads as success, not that
failures get ignored.

**Seen in the wild.** An audience sync threw on a 400 meaning "contact already
in list". Because the sync was fail-closed, the customer row was never
persisted, while the contact *was* in the audience. It worked once per customer,
and no retry could ever succeed.

---

## 15. Dry-run forever

**The lie:** a job runs on schedule, does all the reading, computes exactly what
it would change, and changes nothing, because the flag that authorises writes
was never added to the schedule.

It looks perfect from every angle. The job is scheduled. It runs. It succeeds.
It logs work. Nothing downstream ever moves, and the absence of movement is
indistinguishable from having nothing to do.

**Detection:** diff each scheduler entry against the invocation its own docs
describe. Look for a flag present in the documentation and absent from the
schedule.
```bash
rg -n -t ts -t js -t py -t go -t sh \
  "dry[-_]?run|DRY_RUN|--apply|--live|--execute|(apply|live|execute)['\"]\)" .
```
Then read the schedule entry for each file the search returns.

**Confirmation:** the flag is absent and its default is false. The job's own
docblock often still says "not scheduled yet", which is a second finding.

**Fix:** add the flag or remove the schedule. Running on a timer to do nothing
is the only option with no upside. Before enabling, run it once by hand and read
the diff: the first live pass carries the entire backlog the job has been
ignoring, which can be a lot of change at once.

---

## 16. Dedup that suppresses new information

**The lie:** a suppression key is coarser than the thing it suppresses, so
genuinely new problems hash to an old fingerprint and are silently dropped.

Alert dedup is necessary and almost always slightly wrong. The failure is
invisible by construction: you cannot see the alerts you did not get.

Common causes: fingerprinting a list that was truncated to the first N items;
normalising digits away so `429` and `503` collapse into the same condition;
hashing a set of ids without its count, so an addition changes nothing.

**Detection:** read every fingerprint, hash, or dedup-key function used for
alert suppression, and ask what it discards. Look for `slice(`, `take(`,
truncation constants, and digit-stripping regexes.

**Confirmation:** construct two materially different inputs and show they
produce the same key.

**Fix:** fingerprint the whole set, or include a count so growth changes the
hash. Where a cap is genuinely needed, hash the full set and *display* the cap.

---

## 17. Silent substitution: the fallback that became the answer

**The lie:** the caller gets a well-formed value and cannot tell it is a
substitute. Cached, retried, defaulted, imputed or degraded, rather than the
thing it asked for.

This is the most dangerous family here, because the machinery producing the lie
exists specifically to hide failure, and it is doing its job perfectly. Error
rate stays flat. Latency stays flat or improves, because the fallback is faster
than the thing it replaced. The output is valid and plausible. So the temporary
degradation becomes the permanent steady state, with no moment at which anyone
could have noticed.

Family 2 (empty is not absent) is its mildest special case: a substitute that at
least looks empty. A substitute that looks like real data ends the reader's
curiosity completely.

Instances: a cache serving stale-if-error through a six-hour origin outage; a
retry loop that eventually succeeds against a warm replica; a circuit breaker
whose fallback path has carried 100% of traffic for a month; `?? 0` and
`getOrDefault` filling a hole with a number that flows into a sum; a permissive
parser routing malformed rows to a corrupt-record column nobody queries; a
feature store returning the imputed mean because the pipeline died; an API
quietly downgrading to a cheaper model under load.

**Detection**
```bash
rg -n -t ts -t js -t py -t go --glob '!*.test.*' . \
  -e 'stale[-_]?(if|while)[-_]?error' -e 'getOrDefault' -e 'CircuitBreaker' \
  -e 'fallback[A-Za-z]*\s*[:=(]' -e '\bwithRetry\b'
# and, separately, coalescing INSIDE a catch, which is where it hides:
rg -n -A3 -t ts -t js 'catch\s*\(' . | rg "\?\?|\|\|"
```
The operator is not the finding; the finding is that **the caller cannot tell**.
Rank hits inside a `catch`, inside a cache layer, or feeding an aggregate first.

**Confirmation:** make the primary path fail, then inspect what the caller
receives. If it is indistinguishable from a healthy response, confirmed.

**Fix:** provenance travels with the value.
`return { value, provenance: 'fresh' | 'cached' | 'default' | 'partial' }`, and
a counter at every substitution site. Then alert on the things that are not
errors: the **ratio of non-fresh responses**, and **time since the primary path
last succeeded**. Watching error rates cannot find this, by construction.

---

## 18. The fail-open gate

**The lie:** "this request was authorized", when the check errored, timed out,
or was never registered, and the failure path is allow.

The system looks *healthier* when the gate is broken, because the denials stop.
Authorized and unauthenticated traffic produce identical observations: 200s,
normal latency, no errors.

Instances: an admission webhook with `failurePolicy: Ignore` whose pod is down;
an unreachable policy sidecar; `rejectUnauthorized: false` left in from
debugging; JWT verification wrapped in a `try` whose `catch` returns the
decoded-but-unverified claims; middleware registered after the route it guards.

**Detection**
```bash
rg -n "failurePolicy|rejectUnauthorized|verify: false|InsecureSkipVerify|NODE_TLS_REJECT" \
  -t ts -t js -t py -t go -t yaml .
rg -n -A4 "catch" -t ts -t js --glob '!*.test.*' \
  . | rg -i "return.*(token|claims|session|user|true)"
```

**Confirmation:** present a bad, absent, or expired credential to a protected
route and assert you get 401 or 403. Do this on a local copy or staging, never
by disabling auth on a shared system.

**Fix:** two moves, both cheap. **Monitor the negative space**: every gate emits
a denial counter, and a gate whose denial count is exactly zero over a week is
either protecting nothing or protecting nothing. Alert on `denials == 0`, not on
`errors > 0`. Then keep a negative test per gate, proven by removing the
middleware and watching it go red.

---

## Cross-cutting: the two disciplines

**Falsify every gate you add.** A new check ships with a case proving it fires
on the real defect and a case proving it does not fire on correct code. Prove
it by breaking the code and watching the check go red, then restoring it. A
regression test that passes against the bug is decoration.

**Verify what a delegate reports.** A sub-agent or a colleague produces claims,
not facts. Expect error in both directions: confident findings that dissolve on
inspection, and whole categories the sweep never saw. Re-derive anything
load-bearing at the source before repeating it, and prefer the remote or live
reference over the local copy (see family 10, which catches auditors as often
as it catches code).

---
*Hand-maintained catalogue, as of 2026-08-18. Worked examples are dated
incidents, not current state.*
