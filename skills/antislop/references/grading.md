# The report and the grade

One output shape, every run, so two audits of the same repo are comparable and
an audit of two repos is comparable. If you change the shape, the grade stops
meaning anything.

## Contents

1. The grade, and what it is allowed to be
2. Grading rules
3. Coverage gating
4. The report template
5. Worked example of a grade

---

## 1. The grade, and what it is allowed to be

A single letter, `A` to `F`, plus a coverage suffix.

```
GRADE: C (partial: 12/18 families, 3/4 dimensions)
```

Three rules keep the grade honest, and they matter more than the thresholds:

- **A grade that cannot go down is decoration.** State, every time, what would
  have lowered it. If nothing could have, you did not audit.
- **No false precision.** Never emit `87.3/100`. A letter carries exactly as
  much resolution as the evidence supports, and a decimal implies measurement
  nobody made.
- **Coverage travels with the grade, always.** An `A` from four families
  checked is worth less than a `C` from eighteen, and the reader cannot tell
  unless you print the denominator.

## 2. Grading rules

Start at `A` and apply every cap that fires. The lowest cap wins. Caps are
mechanical: the same findings must produce the same grade for any auditor.

| Trigger | Cap |
|---|---|
| Any **confirmed** lie-family finding on an auth, payment, data-integrity or deletion path | **F** |
| Any **confirmed** check that cannot fail (family 1, 6 or 8) anywhere | **D** |
| Any **confirmed** silent substitution or fail-open gate (family 17, 18) | **D** |
| 3 or more **confirmed** lie-family findings of any kind | **D** |
| 1 to 2 **confirmed** lie-family findings | **C** |
| Only **suspected** lie-family findings, none confirmed | **B** |
| Dead weight over 15% of the surveyed surface (dimension B) | one step down |
| Convention breaches in a security, money or migration path (dimension C) | one step down |
| Test integrity failing (dimension D): assertions that survive a mutation | one step down |
| Nothing confirmed, nothing suspected, full coverage | **A** |

`confirmed` means reproduced and cited in the Executed block. A `suspected`
finding never caps below `B`, because unproven claims must not drive a grade
any more than they drive a fix.

## 3. Coverage gating

The grade is suffixed `(partial: n/18 families, m/4 dimensions)` unless both are
complete, and **a partial audit cannot score above `B`**. This is the whole
anti-slop point of the grade: an audit that checked four things and found
nothing must not read like a clean bill of health.

If you could not check something, the coverage line says why. `not checked: no
runnable recipe for this language` is a good answer. Inventing a sweep is not.

## 4. The report template

Emit these six blocks, in order, every run.

```markdown
# Antislop report: <target>

**GRADE: <letter> (<coverage suffix>)**
<one sentence: what would have lowered this, and what did>

## 1. Scope
Target, commit SHA, mode (audit-only / audit-and-fix), date.
What was not covered, and why.

## 2. Executed
Every command, URL and page actually run, with its one-line result.
A finding may be `confirmed` only if it cites a line here.

## 3. Findings (worst first)
### <n>. <the lie, stated plainly>
- **Dimension / family**: A-<family n> | B dead weight | C conventions | D tests
- **Evidence**: file:line, and the mechanism
- **Blast radius**: what breaks, who notices. "Nobody notices" is the severity
- **Fix**: one sentence
- **Confidence**: confirmed | suspected

## 4. Dimension scores
| Dimension | Result | Evidence |
|---|---|---|
| A. Honest signals (18 families) | n confirmed, n suspected | |
| B. Dead weight | n% of surveyed surface | |
| C. Conventions | n breaches, n in critical paths | |
| D. Test integrity | pass / fail / not run | |

## 5. Coverage
18 lines, one per family:
`<n>. <name> - confirmed N | suspected N | checked, nothing found | not checked: <why>`
Then one line per dimension B, C, D.

## 6. What would change this grade
The specific, smallest set of fixes that moves it up a letter.
```

## 5. Worked example of a grade

From the audit that produced this skill, graded after the fact:

```
GRADE: D (full: 18/18 families, 4/4 dimensions)

Capped at D by two confirmed family-1 findings: a cron watchdog that checked
zero of 37 scheduled jobs and returned success, and a registry whose only
write path had no callers. Neither touched auth or payments, so it did not
reach F. It would have been C with one such finding, and B if both had been
suspected rather than reproduced.
```

That is the shape to copy. The grade is a claim, so it carries the reason it is
not a better one.
