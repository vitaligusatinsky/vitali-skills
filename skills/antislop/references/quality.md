# Dimensions B, C and D: dead weight, conventions, test integrity

Dimension A is the lie families in `patterns.md`, and it carries the most
weight in the report. The count lives in one place — the catalogue — so this
file does not repeat it; a number restated here is a number that drifts here. These three are the rest of the picture: they are what
a competent reviewer would say about the code even when nothing is lying.

Keep them in that order of authority. A repo with perfect conventions and a
watchdog that checks nothing is in worse shape than a scruffy repo whose signals
are honest, and the grade should say so.

## Contents

- B. Dead weight (including DRY)
- C. Conventions and best practices
- D. Test integrity
- How to survey a percentage honestly

---

## B. Dead weight

Code that exists and earns nothing. Related to family 3, but broader: family 3
is machinery nobody drives, this is everything nobody needs.

**B1. Unreferenced exports.** The most reliable DRY-adjacent signal, because it
is mechanical rather than a matter of taste.

```bash
# Exported symbols with no non-test, non-definition reference.
# Bounded on purpose: one rg per symbol, so cap the candidate list or this
# runs for minutes on a large repo. Raise the head count deliberately.
rg -o -r '$1' '^export (?:async )?(?:function|const|class) (\w+)' \
  -t ts -t js --glob '!*.test.*' --no-filename . | sort -u | head -150 \
  | while read -r sym; do
      n=$(rg -c --no-messages "\b$sym\b" -t ts -t js --glob '!*.test.*' . | wc -l)
      [ "$n" -le 1 ] && echo "no references: $sym"
    done
```

Read the head of that list, not all of it. A public library's API surface will
light up here and that is correct, not a finding: say so rather than reporting it.

**B2. Duplicated blocks.** Copy-paste is a maintenance liability because the
copies drift, and the drift is silent. Prefer a real detector over grep:
`jscpd` for JS/TS, `pmd cpd` for Java/C#, `ruff`/`pylint` similarity for Python.

```bash
# antislop:no-verify installs a package; run it deliberately
npx -y jscpd --min-lines 12 --reporters console --absolute . 2>/dev/null | tail -30
```

Report duplication as a percentage of surveyed lines, never as a raw block
count, and name the two or three worst clusters. "4.1% duplicated, mostly three
copies of the same retry wrapper" is actionable. "812 duplicate blocks" is not.

**B3. Dead configuration and dependencies.** Declared and never used, or used
and never declared. The second one is the dangerous direction.

```bash
rg -o -r '$1' "from ['\"]([@\w][\w@/.-]+)['\"]" -t ts -t js --no-filename . \
  | grep -v '^\.' | cut -d/ -f1-2 | sort -u | head -40
```
Diff that against the manifest by hand. An import present in code and absent
from the lockfile is a phantom dependency, which is a supply-chain concern, not
a tidiness one.

**B4. Commented-out code and stale TODOs.**

```bash
rg -n "TODO|FIXME|HACK|XXX" -t ts -t js -t py -t go --glob '!*.test.*' . \
  | head -40
```
Date them: `git log -1 --format=%as -S '<the TODO text>' -- <file>`. A TODO
older than a year is a decision nobody made, and it belongs in a tracker or in
the bin.

---

## C. Conventions and best practices

What the repo says about itself, versus what it does. Read the repo's own rules
first (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, lint config, ADRs). A
convention breach only counts if the repo actually claims the convention: do not
import your own house style and grade someone else against it.

**C1. Error handling that discards.**

```bash
# -U for multiline: an empty catch spans lines. Also catches `catch {}`.
rg -n -U "catch\s*(\([^)]*\))?\s*\{\s*\}" -t ts -t js --glob '!*.test.*' . \
  | head -30
# and the near-miss: a catch whose only statement is a log
rg -n -U -A2 "catch\s*(\([^)]*\))?\s*\{\s*(console|logger)\.\w+\([^)]*\);?\s*\}" \
  -t ts -t js --glob '!*.test.*' . | head -20
```
An empty catch is a decision to ignore a failure, taken silently.

**C2. Secrets and credentials in source.**

```bash
# antislop:empty-ok nothing found is the good result for a secrets sweep
# antislop:control: printf 'api_key = "abcdefghijklmnopqrstuvwx"\n' | rg -q "(api[_-]?key|secret|password|token)\s*[:=]\s*.?[A-Za-z0-9_-]{16,}"
rg -n "(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}" \
  -t ts -t js -t py -t go --glob '!*.test.*' --glob '!*.example*' . | head -20
```
Any hit here is a finding regardless of the rest of the audit, and it outranks
everything else in the report.

**C3. Logging discipline.** Does the repo mandate a logger and then use
`console.log`? This one is only a finding where the repo states the rule.

```bash
# antislop:empty-ok a repo that mandates a logger and obeys it returns nothing
# antislop:control: printf 'console.log(1)\n' | rg -q "console\.(log|error|warn)"
rg -n "console\.(log|error|warn)" -t ts -t js \
  --glob '!*.test.*' --glob '!scripts/**' . | head -20
```

**C4. Typed boundaries.** `any`, `# type: ignore`, `interface{}`, unchecked
casts. Each is a place the type system was told to stop looking.

```bash
rg -n ":\s*any\b|as any\b|@ts-ignore|@ts-nocheck" -t ts . --glob '!*.test.*' | head -30
```

**C5. The repo's own gates.** Run them. `lint`, `typecheck`, `test`, `build`,
whatever the manifest declares. A repo whose own scripts fail is a finding that
needs no interpretation, and running them is cheaper than reading about them.

---

## D. Test integrity

Coverage percentage is not integrity. The question is whether the tests would
have failed on the real defect.

**D1. Do the assertions constrain anything?** The mechanical answer is mutation
testing: Stryker for JS/TS, mutmut or cosmic-ray for Python, PIT for Java. A
surviving mutant is a line the suite does not actually hold.

```bash
# antislop:no-verify slow and installs a package; scope it to changed files
npx -y stryker run --mutate 'src/lib/**/*.ts' 2>/dev/null | tail -20
```

Too slow for a whole repo. Point it at what changed recently, or at the module
carrying the finding you care about.

**D2. Tests committed with their implementation, never failing first.** An
assertion derived from the code encodes the bug as the specification. This is
the dominant way agent-written tests lie.

Do this per suspicious file, not as a repo-wide scan. `--diff-filter=A` makes
git diff every commit it walks, which took over 45 seconds on a large repo and
answered a question nobody asked; the targeted form answers the real one in
milliseconds.

```bash
# antislop:no-verify template, needs a real file. With a path that does not
# exist git walks the entire history looking for it and never returns.
# Did this test and its subject land in the same commit, with no failing state?
f=src/lib/example.test.ts                      # the test you are suspicious of
sha=$(git log --diff-filter=A --format=%H -1 -- "$f")
echo "added in $sha"; git show --stat --format='%s' "$sha" | head -20
```

If the implementation appears in that same commit, the test never saw the code
fail. That does not prove the assertion is derived from the implementation, but
it is where to look first.

**D3. Doubles that model nothing.** Family 11 in `patterns.md`, and the cheapest
real check here: invert the behaviour in the source, run the suite, and see
whether anything notices.

**D4. Skipped and silenced tests.**

```bash
# antislop:empty-ok no skipped or focused tests is the good result
# antislop:control: printf 'it.only("x")\n' | rg -q "\.skip\(|\.only\(|xit\("
rg -n "\.skip\(|\.only\(|xit\(|xdescribe\(|@pytest.mark.skip|t.Skip\(" \
  -t ts -t js -t py -t go . | head -20
```
`.only` in a committed test is worse than `.skip`: it silently stops the rest of
the file from running.

---

## How to survey a percentage honestly

Dimension B asks for a percentage, which is a number, which means it can lie.

- **Name the denominator.** "12% of 4,200 surveyed source lines", not "12%".
- **Say what was excluded** and why: generated files, vendored code, lockfiles,
  test fixtures.
- **Never extrapolate from a sample without saying so.** If you surveyed one
  package of a monorepo, the percentage describes that package.

A percentage with no denominator is the same species this whole skill is about:
a number that looks measured and is not.
