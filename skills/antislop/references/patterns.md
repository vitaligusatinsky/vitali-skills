# Antislop pattern catalogue

Each family below has the same shape: **the lie**, a **detection recipe** you
can run, a **confirmation step** that proves it rather than suspecting it, and
**the fix that closes the class** rather than the instance.

Read this at the start of an audit. Working from memory produces plausible
findings; working from the recipes produces reproducible ones.

A note on confirmation: every recipe here ends in an action, not a judgement.
If you cannot state what you ran and what it printed, you have a suspicion.
Label it as one.

---

## 1. False green

**The lie:** it reports health it never verified.

**Detection**
```bash
# guards and checkers that read a path or config that may have moved
grep -rn "exists\|readFile\|readdir\|glob(" --include='*.{ts,js,py,go,rb}' . \
  | grep -iE "check|guard|verify|validate|watchdog|health"
```
For each, ask what it does when its input is missing. If the answer is
"finds nothing, so passes", it is a false green.

**Confirmation:** rename or empty its input, run it, watch it stay green.

**Fix:** a checker that cannot find its input must **throw**, not return zero
results. Zero results is a claim about the world.

---

## 2. Empty is not absent

**The lie:** an outage and a genuine zero are the same observation.

**Detection**
```bash
grep -rn -B3 "return \[\]\|return {}\|return 0\|?? \[\]" --include='*.{ts,js}' . \
  | grep -iE "catch|error"
```

**Confirmation:** revoke the credential or block the network, call the code,
and see whether the caller can distinguish the result from a quiet day.

**Fix:** make *unavailable* a third state. In a UI a visible message, not a
blank. In an API a 503, not `[]`. Never render a confident zero you did not
measure — a dash is honest, a zero terminates the reader's curiosity.

---

## 3. Orphaned machinery

**The lie:** it exists, so someone assumes it runs.

**Detection:** for every writer, find its callers; for every table or store,
find its writers; for every scheduled route, find its schedule, and for every
schedule, find its route.
```bash
# a schedule pointing at nothing, or a job nobody schedules
grep -rn "cron\|schedule" --include='*.{json,yml,yaml,toml}' .
```

**Confirmation:** check the store's newest row, or the job's last run. If the
newest row predates the feature's launch, only the migration ever wrote to it.

**Fix:** delete it, or wire it. A third state — "kept just in case" — is how a
store decays silently from the day it ships.

---

## 4. Stale truth

**The lie:** hand-kept data the world has moved past, presented undated.

**Detection:** any hardcoded list of real-world things — customers, staff,
accounts, regions, model names, price tiers.
```bash
git log -1 --format=%ad -- path/to/list.json   # date every one you find
```

**Confirmation:** compare the list against the system of record and count the
disagreements.

**Fix:** the honest repair is often not to update it but to **make its age
visible at the point of use**. Undated stale data misleads; dated stale data
is history a reader can discount. One change, whole family.

---

## 5. Unactionable alert

**The lie:** it nags without a resolution path, so it trains people to ignore
the channel it arrives in.

**Detection:** for each alert string, search for the command that resolves it.
If the remediation is a function with no entry point, there is no path.

**Confirmation:** try to clear it using only what the alert tells you.

**Fix:** every alert carries the runnable command that resolves it. If that
command does not exist, building it *is* the fix.

---

## 6. Success-shaped failure

**The lie:** failure encoded as a normal result.

**Detection:** responses carrying both a success status and an error payload —
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
grep -rn "\.select(\|SELECT " --include='*.{ts,js,py}' . \
  | grep -v "limit\|range\|LIMIT\|first(\|single("
# in-memory aggregation over a fetched set
grep -rn "\.length\|reduce(\|filter(.*)\.length" --include='*.{ts,js}' .
```

**Confirmation:** ask the server for the true count and compare it against what
the code received.
```bash
curl -sI "$API/table?select=id" -H "Prefer: count=exact" -H "Range: 0-0" \
  | grep -i content-range        # -> 0-0/1525 while the code got 1000
```

**Watch for the fake fix.** A client-side `limit: 10000` may not beat a
server-side cap. Verify by requesting more than the cap and counting what comes
back — code that *looks* bounded correctly is the harder version of this bug.

**Fix:** page until a short page returns, and give the pager a **hard ceiling
that throws** rather than truncating — otherwise the fix reintroduces the bug at
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
code — and, where it genuinely cannot execute a check, it **says which ones it
could not run** instead of implying full coverage.

---

## 9. The record that outlived the fact

**The lie:** a machine-generated artifact or ledger describes a reality it was
never re-checked against — and it is trusted *because* it is machine-generated.

Migration ledgers, generated type definitions, lockfiles, cached schemas,
inventory manifests, infrastructure state files. All are written once from a
world that has since moved.

**Detection:** for each generated artifact, find what it was generated **from**,
and whether that source is the thing production actually runs. Generated types
built from a local rebuild describe the *migrations*, not the *database*.

**Confirmation:** introspect the live system and diff it against the artifact.
```bash
# does the column the types promise actually exist?
curl -s "$API/table?select=suspicious_column&limit=1" | grep -q "42703" \
  && echo "types promise a column production does not have"
```

**Fix:** a scheduled or pre-deploy job that diffs the artifact against the live
system. Until that exists, treat the artifact as a hypothesis. Note the trap:
a type checker passing over such an artifact is itself a false green — it
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
grep -rn "order: () =>\|limit: () =>\|sort: () =>\|=> builder\|=> this" \
  --include='*.test.*' --include='*.spec.*' .
```
Count how many *independent copies* of the fake exist. Copies drift; a shared
double at least drifts once.

**Confirmation:** invert the behaviour in the source — flip the sort direction,
change the limit — and re-run. If the suite stays green, the double models
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
pools, memory. The margin was never there — it simply had not been crossed.
These arrive as sudden total failures of something that "has always worked",
usually right after a data import or a new customer.

**Detection:** any collection whose size is proportional to a growing table and
which is passed somewhere whole — an `IN (...)` list, a query string, a request
body, a fan-out loop.

**Confirmation: binary-search the real limit against the real system.** Do not
guess it and do not trust the documented value.
```bash
# grow the input until it fails; the last success is your real ceiling
for n in 100 500 675 676 1000; do
  printf '%s ' "$n"; call_with_n_items "$n" >/dev/null 2>&1 && echo ok || echo FAIL
done
```
Then compare that ceiling against today's production size. The gap is your
remaining runway, and it is worth writing down.

**Fix:** chunk at the boundary inside a shared helper so callers never have to
know the limit exists — and assert the runway in a test using the real
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

**Fix:** narrow before querying — filter the list to values of the right shape
rather than trusting the string. Anchor the check: a value that *contains* a
well-formed identifier is not one, and a loose match still fails at the parser.

---

## Cross-cutting: the two disciplines

**Falsify every gate you add.** A new check ships with a case proving it fires
on the real defect and a case proving it does not fire on correct code. Prove
it by breaking the code and watching the check go red, then restoring it. A
regression test that passes against the bug is decoration.

**Verify what a delegate reports.** A sub-agent or a colleague produces claims,
not facts. Expect error in both directions: confident findings that dissolve on
inspection, and whole categories the sweep never saw. Re-derive anything
load-bearing at the source before repeating it — and prefer the remote or live
reference over the local copy (see family 10, which catches auditors as often
as it catches code).
