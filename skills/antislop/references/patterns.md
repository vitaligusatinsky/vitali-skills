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

Do not take the above as a list of things now fixed — a paragraph claiming a
class is absent is family 4 waiting to happen, and this one was already false:
family 21 shipped with three path-less `rg` calls one screen below it. The
guarantee lives in `scripts/check-recipes.sh <repo>` instead, which runs every
bash-tagged block in this file and fails on any that matches nothing, matches
too much, hangs, or omits its search path. Run it after editing this file.

**Every family carries a runnable recipe or says out loud that it has none.**
Five here are judgement-led rather than grep-led, and each is marked
`no-recipe:` under its Detection heading. That marker is what the harness
counts, so a family whose recipe silently stops being seen — an opening fence
typed without its `bash` tag, which is exactly how family 21 went unchecked for
a day — fails the run instead of passing quietly.


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
19. The checker that read a different page
20. Valid is not correct
21. The marker a human has to remember
22. Published where nobody reads

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

**Inert is not free — rank orphans by what they cost while idle.** The usual
framing treats orphaned machinery as harmless clutter to tidy up eventually.
Some orphans run a meter. A dependency nothing imports still gets installed, and
if the install feeds a size-capped cache it can evict the cache on every build.
Ask of each orphan: does anything *pay* for it per unit time — install seconds,
storage, a cached artifact's size budget, a paid API's idle quota, a warm
instance? An orphan with a meter outranks a dozen dead exports.

**Seen in the wild (2026-08-22, since fixed).** A prompt-eval devDependency ran
in no CI workflow and executed on no deploy — textbook orphan, and by the usual
severity ranking, cosmetic. Its 122-package provider tree was 2.1 GB of the
4.0 GB `node_modules`, which pushed the platform's build cache 0.34 GB over a
1.5 GB cap. The cache was therefore discarded and rebuilt on *every* deploy for
roughly five months. Removing the orphan took production builds from 4.7 min to
2 min. Nothing "ran"; it still cost more than anything that did.

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

`no-recipe: the search term is the product's own alert strings, which differ per repo. Grep for the alert text you find, then for the command that clears it.`
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

`no-recipe: the tell is a status/payload disagreement, not a token. Read the response shapes your telemetry records as successes.`
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

**The filter that quietly became the denominator.** Pagination is the loud
version. The quiet version is a `where` clause: you aggregate over
`state == 'READY'`, `status == 'active'`, `deleted_at IS NULL` — each defensible
on its own — and then report the total as if it covered everything. Nothing
truncates, no cue fires, and the number is confidently low. Whenever a total is
computed from a filtered read, state the filter **in the same sentence as the
number**, or compute the unfiltered total alongside it and show both.

**Seen in the wild (2026-08-22).** A build-cost estimate summed the durations of
deployments in state `READY` — the successful ones — and reported it as monthly
build spend. Cancelled and errored builds consume build minutes too. The real
figure was 17% higher. The filter was never wrong; presenting its output as the
whole was.

---

## 8. Proof by assertion

**The lie:** a system records a result that the caller *typed* rather than one
it *derived from execution*.

This is the purest form of the species. A proof harness that accepts
`--check typecheck=pass` has recorded a string, not a measurement. Everything
downstream treats it as evidence.

**Detection:** for every check id, status field or "verified" flag, find the

`no-recipe: you are looking for a setter whose input is an argument rather than an exit code. That is a call-graph question, not a pattern.`
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

`no-recipe: the finding is two fields of different shapes meeting in one coalescing expression. Which fields those are is repo-specific; start from the typed queries and read backwards.`
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

`no-recipe: read the fingerprint functions your alerting actually uses. There is no token that distinguishes a lossy key from a sound one.`
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

**Enumerate every exit, including the one that only prints.** A guard placed on
the automated path and not the advisory path has not closed anything — it has
moved the unsafe act from the program to the person reading its output, who has
strictly *less* context about why it was refused. If a tool declines to do
something, it must not then print the command that does it. Treat printed
suggestions, copy-paste blocks, generated runbooks and error-message "try this"
hints as exits subject to the same precondition as the code.

**Seen in the wild (2026-08-22, three rounds).** A hygiene tool deleted remote
branches only when an API confirmed no open PR existed. When that API failed, an
empty PR list read as "no branch has a PR" — fail-open, round one. Round two
gated the destructive call on the API having actually answered. Round three
found the dry-run still printing a ready-to-paste
`git push origin --delete <names>` for exactly those branches, unguarded. Same
defect, three exits: the filter, the action, and the advice. Fixing two of three
felt like fixing it.

---

## 19. The checker that read a different page

**The lie:** the check passed, and it was looking at something real — just not the
thing under test.

Distinct from *false green* (family 1), where the check verifies nothing. Here the
assertion genuinely evaluated a live response. A substitute surface was served in
place of the application, and it satisfied every condition the check knew to ask:
a login wall, an SSO interstitial, a CDN or WAF challenge, a captcha, a
maintenance page, a paywall, a consent gate, a "your deployment is building"
holding page. All of them return **200**, none of them contain the application's
error strings, and a check written as *"status is OK and no error text"* passes
against every single one.

It is worst in exactly the situations where the stakes are highest — verifying a
deployed preview, a staging environment, a production canary — because those are
the environments most likely to sit behind an access wall the local one does not
have.

**Detection**
```bash
# assertions that only prove a response arrived
rg -n "toBe\(200\)|status_code == 200|assertEqual\(.*200|res\.ok\b" \
  --glob '*{test,spec,e2e,smoke,canary}*' .
# negative-only assertions: "no error" is not "the right thing"
rg -n "not.*(error|Error)|assertNotIn|does_not_contain" \
  --glob '*{test,spec,e2e,smoke}*' .
```
Any hit that lacks a positive assertion about application-specific content is a
candidate.

**Confirmation:** point the check at a URL that is definitely not the app — the
provider's own login page, a 302 target, `example.com` — and watch it pass. If it
does, it was never testing the app.

**Fix:** assert something **only the real application can produce**: a landmark or
role the app's own layout renders, a data value the app alone would know, a
specific heading. Then add the substitute surfaces to an explicit deny-list so
they fail loudly rather than silently satisfying a weak condition. Put both in one
shared helper — every ad-hoc smoke check written later will otherwise reinvent the
weak version.

For anything behind access protection, remember the check needs the bypass
credential too; a check that cannot get in will otherwise report the wall as
health forever.

---

## 20. Valid is not correct

**The lie:** a check from a lower tier of rigour is read as proof from a higher
one — and often says so plainly, in a place nobody reads.

Every stack has tiers: *parses* < *type-checks* < *schema-valid* < *runs* <
*behaves correctly under the case you care about*. Each tier is cheap and useful.
The failure is not using them; it is letting a lower tier stand in for a higher
one, which happens by default because passing looks identical at every tier.

Concrete pairs, all real:
- `bash -n` accepts `${$((x/60))}`. It parses. It is a bad substitution that
  fails the moment it executes. A syntax check is not a run.
- A type-checker green-lights code against **generated** types. If those types
  were generated from a rebuild rather than from the live system, the compiler is
  certifying a description, not reality (family 9).
- A fixture-shape validator confirms that hand-written scenarios describing
  behaviour are well-formed. It never runs the code they describe.
- Schema validation on a payload proves the shape, not that the values mean what
  the consumer assumes.

**The aggravating factor is naming.** A validator called `replay` that lists 33
scenario names like `ambiguous-approval-fails-closed` reads as behavioural proof,
even when its source sets `productionCodeExercised: false` and its output opens
with the word `Structural`. The disclaimer was present and accurate. It sat in
the one position readers skip: the first token of a line whose remainder is a
list they came to read. An artifact named after what it aspires to prove will be
cited as proof of that thing, by everyone, forever.

**Detection**
```bash
# artifacts that declare their own limits in a field rather than a name
rg -n "structural|dry.?run|shape.?only|does not execute|productionCodeExercised|smoke.?only" \
  -t ts -t js -t py -t go -t yaml -t json --glob '!*/node_modules/*' .
# names that assert an outcome the implementation may not test
rg -n "fails.closed|is.not.zero|never|always|blocks|refuses|rejects" \
  --glob '*{fixture,scenario,spec,test}*' . | head -40
```
For each hit, open the implementation and ask what tier it actually reaches.

**Confirmation:** break the behaviour the name claims and run the check. If it
stays green, the name is a claim the implementation does not make.

**Fix:** two moves, both cheap and neither optional.
1. **Name the artifact after what it verifies**, not what it aspires to.
   `fixture-shape-check` cites correctly; `replay` does not.
2. **Put the limitation where it is read** — in the command name, and in every
   line of output, not in a field in the source. A caveat that has to be found is
   a caveat that will not be.
Then, where the higher tier is genuinely worth having, promote a small number of
cases to it rather than promoting the whole suite: three fixtures that actually
execute beat thirty-three that describe.

---

## 21. The marker a human has to remember

**The lie:** correctness depends on someone editing a constant, and the code
says so out loud — `// bump this when the shape changes`. The comment reads as
documentation. It is actually an admission that the mechanism does not work.

The tell is a literal whose only job is to be different from last time: a
`SCHEMA_VERSION`, a `CACHE_VERSION`, a `migrationLevel`, a hand-typed hash. It
is never wrong at the moment it is written, so review passes. It goes wrong on
the change *after* the one that introduced it, made by someone who did not know
the constant existed.

**Why it survives review: the failure is invisible to the person shipping it.**
This is the property that makes it worth its own family. A developer testing a
change starts from a clean state — a fresh browser profile, an empty cache, a
new container — and clean state always takes the new code path. The stale path
only exists for someone who was there *before*, so the author, the reviewer and
CI all see the fix working while every returning user sees the old behaviour.
Nobody is lying and nobody is careless; the test is structurally incapable of
reaching the broken case.

A worked example. A demo app cached a per-visitor snapshot and re-seeded it only
when a fingerprint changed. The fingerprint was `hash(serverPayload) + ":" +
SANDBOX_VERSION`, and `SANDBOX_VERSION` was `"stable-links-v3-catalog-groups"`,
hand-edited. A change then altered how the *same* payload was mapped — a
publisher's songwriter had been showing in the Artist column where the
performing act belonged. The payload did not change, so the hash did not change,
so the constant was the only thing that could have forced a re-seed, and it was
not bumped. New visitors got the fix. Everyone who had ever opened the demo
before — every prospect it existed for — kept the wrong names indefinitely. It
was found only because a user and a developer looked at the same URL and
described different screens.

**The general shape:** a cache key built from the inputs to a transform but not
from the transform itself. Change the code, keep the data, serve a stale result
forever. Same family: memoisation keyed on arguments while the memoised function
closes over changing config; a CDN key of the source asset but not the build
that compiled it; a "has this migration run" flag keyed on a name that gets
edited in place.

**Detection**

```bash
# hand-edited literals whose only job is to differ from last time
rg -n "SCHEMA_VERSION|CACHE_VERSION|STATE_VERSION|_VERSION\s*=\s*[\"']" \
  -t ts -t js -t py -t go -t sh .
# the comment that admits the mechanism does not work
rg -n -B2 "bump (this|the)|increment (this|when)|remember to (bump|update)" \
  -t ts -t js -t py -t go -t sh .
# version-shaped literals in config, where they rot unread
rg -n "version:\s*[0-9]+|v[0-9]+-[a-z-]+\"" -t ts -t js -t yaml -t json \
  --glob '!*lock*' .
```

Then, for each hit, find every place the cached artifact is *produced* and ask
whether a change there can move the key. Also read the tests: a test asserting
the literal (`expect(key()).toBe("published-revision:stable-links-v3")`) is part
of the defect, because it makes the correct fix look like a regression.

**Confirmation:** change the transform without changing its input, rebuild, and
load as an entity that has state from before — a browser profile you already
used, a warm cache, an existing row. If the old result survives, confirmed. A
fresh profile proves nothing here; that is the path that already worked.

**Fix:** derive the marker from something that moves on its own. In order of
preference:

1. **Key on the build** — commit SHA or build id injected at compile time. One
   line, no maintenance, and no change of any kind can escape it. The cost is a
   re-seed on unrelated deploys; when the cached thing is cheap to rebuild,
   that is the right trade.
2. **Key on the output** — hash the transform's *result*, not its input, so the
   key moves exactly when what the user sees moves. Strictly better when the
   output is deterministic; check for timestamps and randomness first, or the
   key changes on every run and the cache stops existing.
3. **Keep the literal only where neither is possible**, and then put the
   invariant in a test rather than a comment — assert the *property* ("differs
   across builds", "stable within a build"), never the literal value.

**Adjacent smell worth reporting together:** anything else whose correctness
rests on a human remembering — a hand-maintained allowlist beside a generated
one, a "keep this in sync with X" comment, a duplicated constant in two files, a
count in prose next to the list it counts. Each is the same bet, and the house
edge grows with every contributor who has not read the comment.

---

## 22. Published where nobody reads

**The lie:** the system *is* reporting the failure. It reports it after the
success line, in the last few lines of a log, in a place the reader has already
stopped reading. Nothing is hidden and nothing is silent — and nobody knows.

This is the inverse of family 1. False green is a signal that cannot go red.
Here the signal goes red every single time, correctly, in writing, and is still
worth nothing. The defect is in the *position* of the message, not its content,
which is why code search never finds it: grep the source and the log line is
right there, looking fine.

Two shapes dominate:

- **After the summary.** A pipeline prints `Build Completed`, then does
  post-work — cache upload, artifact publish, cleanup, notification — and that
  post-work fails. Readers stop at the summary; tooling that scrapes "the
  result" stops there too.
- **Below the fold.** The message is inside output long enough that everyone
  `head`s it, or it sits in a per-run log that only opens when someone is
  already suspicious.

**Detection**
```bash
# success announced before work that can still fail: a done/complete/success
# log line with more fallible statements after it in the same routine
rg -n -i "(console\.(log|info)|logger\.(info|log)|echo|print)\b.*\b(done|complete|completed|success|succeeded|finished)\b" \
  -t ts -t js -t sh -t py --glob '!*.test.*' .
```
```bash
# antislop:no-verify needs live CI/build systems and credentials.
# Read the TAIL of the most recent run of every scheduled job and build.
# The summary line is not the end of the log.
vercel inspect "$DEPLOYMENT_URL" --logs | tail -25
gh run view "$RUN_ID" --log | tail -25
journalctl -u "$UNIT" -n 25 --no-pager
```

**Confirmation:** take one recurring job and read the final 25 lines of its last
three runs, not the summary and not the exit code. Then ask what would have to
appear there for anyone to notice. If the answer is "someone would have to go
looking", the message is unread by design.

**Fix:** move the verdict to where the reader already is, and make the tail
loud. Re-emit any post-summary failure *as* the job's status rather than after
it — a cache that was rejected is a failed step, not a footnote. Where the
platform will not let you reorder its output, add a check that greps the tail
and raises on its own schedule, so the finding arrives without anyone opening a
log. **Exit code is not enough**: most of these failures are non-fatal by
design, which is exactly why they persist.

**Seen in the wild (2026-08-22, since fixed).** Every production build of a
Next.js app ended with `Build cache size 1.84 GB exceeds limit of 1.50 GB.
Invalidating cache. Next build will start with an empty cache.` — printed on
100% of builds, for months, on the line after `Deployment completed`. So every
build ran cold, each additionally spending ~76s writing a cache that was deleted
seconds later. The build script's own comment said it kept the cache "warm,
cheaper builds". The disproof was published, in full, in every log, and the
string `Restored build cache` had never once appeared in the project's history.
Nobody reads past `Deployment completed`.

---

## Cross-cutting: the disciplines

**Falsify every gate you add.** A new check ships with a case proving it fires
on the real defect and a case proving it does not fire on correct code. Prove
it by breaking the code and watching the check go red, then restoring it. A
regression test that passes against the bug is decoration.

**Verify from the state a real user is in, not from a clean one.** Fresh
containers, new browser profiles, empty caches and brand-new rows all take the
new code path by construction, so a check run that way can only ever confirm the
change. The bugs that survive to production are the ones that need prior state
to reproduce: a stale cache, a row written by the previous schema, a session
opened before the deploy, a config a returning user already has. Before
reporting a fix verified, name which starting state you used, and re-run from a
dirty one — reuse the profile, keep the cache, take an existing record. If you
cannot get into the returning state naturally, construct it: write the old value
back and reload. An incident behind family 21 ran for hours with a user and an
agent describing different screens at the same URL, because every agent check
started clean and every user visit did not.

**Verify what a delegate reports.** A sub-agent or a colleague produces claims,
not facts. Expect error in both directions: confident findings that dissolve on
inspection, and whole categories the sweep never saw. Re-derive anything
load-bearing at the source before repeating it, and prefer the remote or live
reference over the local copy (see family 10, which catches auditors as often
as it catches code).

**Verify your own claims, on the same terms.** This is the one most often
skipped, because the auditor is the only reader of their own output and a result
that matches expectation gets no second pass. An audit of this exact catalogue's
subject matter produced five wrong orchestrator claims in a day; four were
caught, one reached a human as stated fact. Every one was a green result that
confirmed what the auditor already believed. Two tells, both mechanical enough
to apply while typing:

- **A universal quantifier reached from a sample.** "All eight", "zero",
  "nothing does X" — after checking three things. Scope the claim to what you
  actually checked. "None of the 3 configs I read" is shorter than "zero
  enforcement" *and* true.
- **Behaviour inferred from a name.** A scenario, test, flag or function called
  `x-fails-closed` is a title, not an assertion. Open the implementation. This is
  family 20 turned on the auditor.

The counter-move for both is the same and costs less than the prose it replaces:
**report the command and its output instead of the synthesis.** A summary is
where the error enters; the raw evidence is usually shorter and is checkable by
the reader.

---
*Hand-maintained catalogue, as of 2026-08-23. Worked examples are dated
incidents, not current state.*
