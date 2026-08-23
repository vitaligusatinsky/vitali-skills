# The report

One shape every run, so two audits are comparable — but only the parts that
stop an audit being lazy. Everything here earns its place by making a specific
failure visible. If a block is not doing that, it is filler, and filler is what
readers learn to skip.

Two things this format used to do and no longer does, because both were
ceremony:

- **A line per family, every run.** Twenty-two lines of "checked, nothing
  found" does not prove anyone checked. It buries the two lines that carry
  information — the gaps — under twenty that do not. Report the gaps.
- **`A-<family n>` labels.** A finding tagged `A-17` reads as a case number.
  Name the family: *the fallback that became the answer*. The reader learns
  something from the name and nothing from the number.

## Contents

1. The verdict
2. Grading rules
3. What coverage has to say
4. The template
5. How a finding should read

---

## 1. The verdict

One letter, `A` to `F`, and one sentence of plain English saying how much of
the system you actually looked at and what would have made it worse.

```
**D.** One confirmed fail-open gate, in the branch-deletion path. I checked 14
of the 22 families and 3 of the 4 dimensions — a partial read, so treat a
better letter as unearned rather than as a clean bill of health.
```

The letter is worth keeping for one reason: the caps below are mechanical, so
the same findings produce the same letter for any auditor, and a genuinely bad
finding cannot be written up as "mostly healthy". That is the whole job it does.

Two rules keep it honest:

- **A grade that cannot go down is decoration.** Say what would have lowered
  it. If nothing could have, you did not audit.
- **Never a number.** `87.3/100` implies a measurement nobody made. A letter
  carries exactly as much resolution as the evidence supports.

## 2. Grading rules

Start at `A` and apply every cap that fires. The lowest cap wins.

| Trigger | Cap |
|---|---|
| Any **confirmed** lie-family finding on an auth, payment, data-integrity or deletion path | **F** |
| Any **confirmed** check that cannot fail — *false green*, *success-shaped failure*, *proof by assertion* | **D** |
| Any **confirmed** *silent substitution* or *fail-open gate* | **D** |
| 3 or more **confirmed** lie-family findings of any kind | **D** |
| 1 to 2 **confirmed** lie-family findings | **C** |
| Only **suspected** findings, none confirmed | **B** |
| Dead weight over 15% of the surveyed surface | one step down |
| Convention breaches in a security, money or migration path | one step down |
| Test integrity failing: assertions that survive a mutation | one step down |
| Nothing confirmed, nothing suspected, full coverage | **A** |

**A partial audit cannot score above `B`**, whatever it found. An audit that
checked four things and found nothing must not read like a clean bill of health.

`confirmed` means you reproduced it and the report cites the command that did.
Everything else is `suspected`, and a suspected finding never caps below `B` —
unproven claims must not drive a grade any more than they drive a fix. Guessing
which one a finding is defeats the point of having two words.

## 3. What coverage has to say

Not a line per family. Two things, both short:

- **The denominator, once**, inside the verdict sentence: how many families and
  dimensions you actually got to.
- **The gaps, named.** Every family you could not check, with the reason.
  `stale truth — not checked, no hardcoded real-world lists in this repo` is a
  good answer. `dedup — not checked, this repo has no alerting` is a good
  answer. Inventing a sweep is not, and neither is silence.

Five families are judgement-led and ship no runnable recipe; they are marked
`no-recipe:` in the catalogue. Skipping one of those is a choice you made and
it belongs in the gaps list like any other.

## 4. The template

```markdown
# Antislop: <target>
`<commit sha>` · audit-only | audit-and-fix · <date>

**<letter>.** <what capped it, in one clause.> I checked <n> of the <N>
families and <m> of the 4 dimensions. <What would have made this worse.>

## What I ran
Every command, URL and page, with its one-line result. A finding is
`confirmed` only if it points at a line here. Say here if you sampled a
ranked subset rather than reading every hit, and how you ranked it.

## What I found
Worst first. Prose, not a form — see section 5.

## What I did not check
One line per gap, with the reason. Omit this section only if there are none.

## Where it stands
| | Result |
|---|---|
| Honest signals | n confirmed, n suspected |
| Dead weight | n% of <denominator> surveyed lines |
| Conventions | n breaches, n in critical paths |
| Test integrity | pass / fail / not run |

## What would move the letter
The smallest set of fixes that gets it up one.
```

## 5. How a finding should read

Like a person explaining a problem to someone who has to fix it. Lead with what
is untrue, not with a label.

```markdown
### The branch cleanup deletes on an API failure

`scripts/git-hygiene.ts:212` deletes a remote branch when the PR lookup returns
an empty list — but an empty list is also what a failed lookup returns, so an
outage at GitHub reads as "no branch has an open PR" and every branch qualifies.

I reproduced it: with the token unset, the dry run listed 6 branches for
deletion including two with open PRs (`What I ran`, line 4).

Nobody would notice until the branches were gone, which is the severity here.
The fix is to require the lookup to have answered before it can authorise a
delete — and separately, the dry run still prints a ready-to-paste
`git push origin --delete`, which is the same defect at a second exit.

*The fail-open gate · confirmed*
```

The parts that are not optional: **what is untrue**, **where**, **who notices
and when**, **confirmed or suspected**, and **the fix**. The order and the
prose are yours. What must not happen is a finding that reads like a form
someone filled in, because that is the register in which nobody checks whether
the claim is true — including the person who wrote it.

One trap worth naming, because it is this catalogue's own family turned on the
auditor: **a finding stated more confidently than it was checked is the thing
you came to find.** If you did not run it, write `suspected` and say what you
would have to run.
