#!/usr/bin/env bash
# Prove this skill's recipes fire, and that its claims about itself are true.
#
# The skill's own first rule is that a check which cannot fail is worse than no
# check. Its recipes are checks and its numbers are claims, so both are in
# scope here. Two halves:
#
#   1. Self-consistency. The catalogue's Contents list against its headings;
#      every family carrying either a runnable recipe or an explicit
#      `no-recipe:` marker; every family-count stated in prose against the
#      catalogue; and a canary proving the extractor that reads those claims
#      still matches anything at all.
#   2. Every bash-tagged block in the catalogues, run against a real corpus.
#      A recipe that matches nothing reads as a clean codebase. One that
#      matches most of the corpus reads as noise and burns the audit. One with
#      no search path reads stdin. All three fail here.
#
# Each check exists because the defect shipped:
#   - five recipes used --include='*.{ts,js}', which matches zero files
#     (fnmatch has no brace expansion). Exited 0, printed nothing, every audit
#     using them reported a clean repo.
#   - the coverage block was graded out of 18 against a 21-family catalogue for
#     four days, so a "complete" run silently skipped three families.
#   - quality.md called them "the eighteen lie families" while the catalogue
#     had 22. The extractor that was supposed to catch that only read digits.
#   - family 21 shipped with its recipes in an untagged fence, invisible to
#     this harness, which then reported that all recipes fire. Its three `rg`
#     calls also had no search path, one screen below a paragraph claiming no
#     recipe in the file had that defect.
#
#   usage: scripts/check-recipes.sh [corpus-dir]
#
# Point it at a broad application repository. Against a narrow one (a library,
# a design system) sound recipes go EMPTY simply because the corpus contains no
# cron config or no untyped boundaries — the harness cannot tell that from a
# broken pattern, which is family 2 turned on the tool that hunts family 2.
#
# Noise ceilings scale with corpus size, so the defaults hold from a few
# hundred files to tens of thousands. Override with NOISE_CEILING / BYTE_CEILING.
#
# A recipe that genuinely cannot run here (needs a live API, a placeholder
# function, a path that does not exist) must carry a marker on its first line:
#
#   # antislop:no-verify <reason>
#
# Unmarked and empty is a failure. Marked recipes are reported, never silently
# skipped, so the count of unverifiable recipes stays visible.

set -uo pipefail

CORPUS="${1:-.}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CATALOGUES="$SKILL_DIR/references/patterns.md $SKILL_DIR/references/quality.md"

for c in $CATALOGUES; do
  if [ ! -f "$c" ]; then
    echo "FATAL: catalogue not found at $c" >&2
    exit 2
  fi
done
if [ ! -d "$CORPUS" ]; then
  echo "FATAL: corpus directory not found: $CORPUS" >&2
  exit 2
fi

# Refuse to pass on an empty corpus. Otherwise this harness becomes the very
# thing it is checking for: a green result that proves nothing.
corpus_files=$(find "$CORPUS" -type f \( -name '*.ts' -o -name '*.js' -o -name '*.py' -o -name '*.go' -o -name '*.rb' \) 2>/dev/null | head -50 | wc -l | tr -d ' ')
if [ "$corpus_files" -lt 10 ]; then
  echo "FATAL: corpus has $corpus_files source files, too few to prove anything." >&2
  echo "Point this at a real repository: scripts/check-recipes.sh ~/some/repo" >&2
  exit 2
fi

pass=0; empty=0; error=0; skipped=0; noisy=0; slow=0; nopath=0
# No recipe should take longer than this against a normal repo.
RECIPE_TIMEOUT="${RECIPE_TIMEOUT:-45}"
failures=()

# Extract fenced bash blocks, one per temp file, preserving line numbers.
block=""; in_block=0; start_line=0; lineno=0
# An `rg` or `grep` with no search path reads stdin in some shells: it hangs, or
# it returns nothing and reads as a clean codebase. The catalogue used to claim
# in prose that no recipe did this. The claim was false — family 21 shipped
# three of them — so the guarantee is here instead, where it is executed.
# Only the FIRST command of a pipeline needs a path; anything downstream is
# meant to read stdin.
check_paths() {
  local body="$1" first_line="$2" bad
  # Join backslash continuations, then judge each logical command. Only a
  # pipeline's FIRST command needs a path; anything after a pipe is meant to
  # read stdin, so a line that does not START with rg/grep is not our business.
  # Splitting on "|" was the obvious approach and it is wrong: most of these
  # patterns contain alternation, so `rg "exists|readFile" .` looked like a
  # two-stage pipeline whose first stage had no path. Every recipe failed.
  bad=$(printf '%s\n' "$body" | sed -e ':a' -e '/\\$/{N;s/\\\n//;ba' -e '}' | awk '
    /^[[:space:]]*#/ { next }
    {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      if (line !~ /^(rg|grep)[[:space:]]/) next
      found = 0
      n = split(line, tok, /[[:space:]]+/)
      for (i = 2; i <= n; i++) {
        t = tok[i]
        # flags, and quoted arguments (patterns), are never the search path
        if (t ~ /^-/ || t ~ /^["'"'"']/) continue
        if (t == "." || t ~ /\//) { found = 1; break }
      }
      if (!found) print substr(line, 1, 58)
    }')
  if [ -n "$bad" ]; then
    while IFS= read -r b; do
      printf '  NOPATH %-21s no search path: %s\n' "$first_line" "$b"
      failures+=("$first_line reads stdin: no search path on \`$b\`")
    done <<< "$bad"
    return 1
  fi
  return 0
}

run_block() {
  local body="$1" first_line="$2"
  [ -z "${body//[[:space:]]/}" ] && return
  check_paths "$body" "$first_line" || nopath=$((nopath+1))

  if printf '%s' "$body" | grep -q 'antislop:empty-ok'; then
    # Absence is the good result here, but only if the detector can fire at all.
    # The positive control is the proof; without one this is an untested claim.
    local control
    control=$(printf '%s' "$body" | grep -m1 'antislop:control:' | sed 's/.*antislop:control: *//')
    if [ -z "$control" ]; then
      printf '  ERROR %-22s empty-ok with no antislop:control to prove it can fire\n' "$first_line"
      error=$((error+1)); failures+=("$first_line empty-ok without a positive control")
      rm -f "$tmp" 2>/dev/null; return
    fi
    if (cd "$CORPUS" && eval "$control" >/dev/null 2>&1 </dev/null); then
      printf '  OKEMPTY %-20s clean, and the detector fires on its control\n' "$first_line"
      pass=$((pass+1))
    else
      printf '  ERROR %-22s control failed: the detector cannot fire\n' "$first_line"
      error=$((error+1)); failures+=("$first_line positive control did not match")
    fi
    return
  fi

  if printf '%s' "$body" | grep -q 'antislop:no-verify'; then
    local reason
    reason=$(printf '%s' "$body" | grep -m1 'antislop:no-verify' | sed 's/.*antislop:no-verify *//')
    printf '  SKIP  %-22s %s\n' "$first_line" "${reason:-no reason given}"
    skipped=$((skipped+1))
    return
  fi

  # Bound every recipe. macOS ships no timeout/gtimeout, so this is a plain
  # watchdog: run in the background, kill it if it outlives RECIPE_TIMEOUT.
  # A harness that can hang forever is the thing this skill is about.
  local out rc tmp
  tmp=$(mktemp)
  ( cd "$CORPUS" && eval "$body" 2>/dev/null </dev/null | head -c 4000000 >"$tmp" ) &
  local job=$!
  ( sleep "$RECIPE_TIMEOUT"; kill -9 "$job" 2>/dev/null ) 2>/dev/null &
  local watchdog=$!
  wait "$job" 2>/dev/null; rc=$?
  kill -9 "$watchdog" 2>/dev/null; wait "$watchdog" 2>/dev/null

  if [ $rc -ge 128 ]; then
    printf '  SLOW  %-22s killed after %ss (a recipe nobody will wait for)\n' \
      "$first_line" "$RECIPE_TIMEOUT"
    slow=$((slow+1)); failures+=("$first_line timed out after ${RECIPE_TIMEOUT}s")
    rm -f "$tmp"; return
  fi

  # Never load recipe output into a shell variable. One minified JSON makes a
  # single matched "line" ~788KB, and ${var//[[:space:]]/} on that is quadratic
  # in bash: it spins in the PARENT, after the watchdog has already reaped the
  # child, so the harness hangs with no way to kill it. Count with wc instead,
  # and bound bytes as well as lines: a recipe can return few lines and still
  # be unreadable.
  local hits bytes
  hits=$(wc -l < "$tmp" | tr -d ' ')
  bytes=$(wc -c < "$tmp" | tr -d ' ')
  rm -f "$tmp"

  if [ "$bytes" -eq 0 ]; then
    printf '  EMPTY %-22s matched nothing — broken, or a corpus without this kind of code\n' "$first_line"
    empty=$((empty+1)); failures+=("$first_line matched nothing")
  elif [ "$hits" -ge "$NOISE_CEILING" ] || [ "$bytes" -gt "$BYTE_CEILING" ]; then
    printf '  NOISY %-22s %s hits / %sk bytes (~%sk tokens, too broad to read)\n' \
      "$first_line" "$hits" "$((bytes/1000))" "$((bytes/4000))"
    noisy=$((noisy+1)); failures+=("$first_line: $hits hits / $bytes bytes")
  else
    printf '  PASS  %-22s %s hits / %sk bytes\n' "$first_line" "$hits" "$((bytes/1000))"
    pass=$((pass+1))
  fi
}

CORPUS_FILES=$(find "$CORPUS" \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.py' -o -name '*.go' -o -name '*.sh' \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.next/*' 2>/dev/null | wc -l | tr -d ' ')

# "Too broad to read" is relative to the repo, not absolute. Fixed ceilings made
# three sound recipes fail on a 32k-file monorepo and pass on a 500-file one, so
# the harness demanded a magic env var that only someone who had already hit the
# failure would know. Scale with the corpus and keep a floor for small repos.
# A genuinely broad recipe matches a large fraction of the corpus and still
# trips this; the floor is what stops a tiny repo passing everything.
NOISE_CEILING="${NOISE_CEILING:-$(( CORPUS_FILES / 40 > 400 ? CORPUS_FILES / 40 : 400 ))}"
# Bytes matter independently of lines: one matched minified line can be ~800KB.
BYTE_CEILING="${BYTE_CEILING:-$(( CORPUS_FILES * 16 > 250000 ? CORPUS_FILES * 16 : 250000 ))}"

echo "corpus: $CORPUS"
echo "corpus files: $CORPUS_FILES -> ceilings ${NOISE_CEILING} hits / ${BYTE_CEILING} bytes (override with NOISE_CEILING / BYTE_CEILING)"
echo "catalogues: $CATALOGUES"
# --- Self-consistency: the skill's claims about itself ------------------------
# This skill audits systems that lie about their own state, so its own numbers
# and cross-references are fair game. Three real defects motivated each check
# below; every one shipped, and every one read as green.
PAT="$SKILL_DIR/references/patterns.md"
PROSE="$SKILL_DIR/SKILL.md $SKILL_DIR/references/grading.md $SKILL_DIR/references/quality.md $PAT"

# The distribution README is the one surface a stranger reads first, and it is
# outside the skill directory, so it drifted furthest: it advertised "Eighteen
# families with runnable detection recipes" against a 22-family catalogue, five
# of which carry no recipe at all. Scan any README that actually mentions this
# skill, so the shop window is held to the same standard as the catalogue.
for candidate in "$SKILL_DIR/README.md" "$SKILL_DIR/../../README.md"; do
  [ -f "$candidate" ] || continue
  grep -qi 'antislop' "$candidate" || continue
  PROSE="$PROSE $candidate"
done

FAMILIES=$(grep -cE '^## [0-9]+\. ' "$PAT")
if [ "$FAMILIES" -lt 1 ]; then
  echo "FATAL: could not count families in patterns.md" >&2
  exit 2
fi
# Judgement-led families declare themselves; see patterns.md. Counted only
# inside a family section, so the preamble that explains the marker is not one.
NORECIPE=$(awk '/^## [0-9]+\. /{fam=1} fam && /^`no-recipe:/{n++} END{print n+0}' "$PAT")

consistency_fail=0

# (1) Contents list vs the headings it indexes. A catalogue whose own table of
#     contents has drifted is family 7 with a straight face.
if ! diff -q \
  <(sed -n '/^## Contents/,/^---$/p' "$PAT" | sed -nE 's/^[0-9]+\. //p') \
  <(sed -nE 's/^## [0-9]+\. //p' "$PAT") >/dev/null; then
  echo "  - patterns.md: the Contents list and the family headings disagree"
  diff <(sed -n '/^## Contents/,/^---$/p' "$PAT" | sed -nE 's/^[0-9]+\. //p') \
       <(sed -nE 's/^## [0-9]+\. //p' "$PAT") | sed 's/^/      /'
  consistency_fail=1
fi

# (2) Every family carries a runnable recipe or declares it has none. Family 21
#     shipped with its recipes in an untagged fence: invisible to this harness,
#     which then reported "all recipes fire" while never running three of them.
missing_recipe=$(awk '
  /^## [0-9]+\. / { if (fam != "" && !seen) print "      family " fam " (" name ")"
                    fam=$2; sub(/\.$/,"",fam); name=substr($0, index($0,$3)); seen=0; next }
  fam != "" && /^```bash$/     { seen=1 }
  fam != "" && /^`no-recipe:/  { seen=1 }
  END { if (fam != "" && !seen) print "      family " fam " (" name ")" }
' "$PAT")
if [ -n "$missing_recipe" ]; then
  echo "  - patterns.md: families with neither a bash-tagged recipe nor a no-recipe marker:"
  echo "$missing_recipe"
  consistency_fail=1
fi

# (3) Family-count claims in prose must match the catalogue. Numbers spelled as
#     words count: quality.md read "the eighteen lie families" against a
#     22-family catalogue, and the digit-only extractor that preceded this could
#     not see it. Claims inside fenced blocks are worked examples, not claims.
claims=0
while IFS='|' read -r file phrase claimed expected; do
  [ -z "$file" ] && continue
  claims=$((claims+1))
  if [ "$claimed" != "$expected" ]; then
    echo "  - $file: \"$phrase\" says $claimed, the catalogue has $expected"
    consistency_fail=1
  fi
done < <(
  for f in $PROSE; do
    awk -v fname="$(basename "$f")" -v fam="$FAMILIES" -v nore="$NORECIPE" '
      BEGIN {
        split("zero one two three four five six seven eight nine ten eleven twelve " \
              "thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty " \
              "twenty-one twenty-two twenty-three twenty-four", w, " ")
        for (i in w) num[w[i]] = i-1
      }
      /^```/ { infence = !infence; next }
      infence { next }
      {
        line = $0
        # "<n> lie families" / "<n> families" / "<n>/<n> families"
        if (line !~ /judgement-led/ && match(line, /([A-Za-z-]+|[0-9]+)(\/[0-9]+)? (lie )?families/)) {
          m = substr(line, RSTART, RLENGTH)
          n = m; sub(/ (lie )?families$/, "", n); sub(/^.*\//, "", n)
          v = (n ~ /^[0-9]+$/) ? n : (tolower(n) in num ? num[tolower(n)] : "")
          if (v != "") print fname "|" m "|" v "|" fam
        }
        # "<n> families are judgement-led" / "<n> of them are judgement-led"
        if (match(line, /([A-Za-z-]+|[0-9]+) (families|of them) are judgement-led/)) {
          m = substr(line, RSTART, RLENGTH); split(m, a, " "); n = a[1]
          v = (n ~ /^[0-9]+$/) ? n : (tolower(n) in num ? num[tolower(n)] : "")
          if (v != "") print fname "|" m "|" v "|" nore
        }
      }' "$f"
  done
)

# (4) The extractor above is itself a check, so prove it can still fire. A
#     reword that stops it matching would otherwise turn every claim green by
#     making the harness blind — which is family 1, committed by the tool that
#     exists to find family 1. The canary is deliberately wrong: if the
#     extractor works it MUST be reported as a mismatch.
canary=$(printf 'the seven lie families\n' | awk -v fam="$FAMILIES" '
  BEGIN { split("zero one two three four five six seven eight nine ten", w, " ")
          for (i in w) num[w[i]] = i-1 }
  { if (match($0, /([A-Za-z-]+|[0-9]+)(\/[0-9]+)? (lie )?families/)) {
      m = substr($0, RSTART, RLENGTH); n = m; sub(/ (lie )?families$/, "", n)
      if (tolower(n) in num && num[tolower(n)] != fam) print "fired" } }')
if [ "$canary" != "fired" ]; then
  echo "  - the family-count extractor no longer matches its own canary."
  echo "    It cannot report drift, so every claim above is unverified."
  consistency_fail=1
fi
if [ "$claims" -lt 3 ]; then
  echo "  - only $claims family-count claims found across the prose (expected >=3);"
  echo "    the extractor probably stopped matching after a rewording."
  consistency_fail=1
fi

if [ "$consistency_fail" -eq 1 ]; then
  echo "SELF-CONSISTENCY FAILED. This skill grades others on whether their own"
  echo "numbers are true. Its own have to be."
else
  echo "Self-consistent: $FAMILIES families ($NORECIPE judgement-led), $claims prose claims agree."
fi

echo

for CATALOGUE in $CATALOGUES; do
CATNAME=$(basename "$CATALOGUE")
lineno=0
while IFS= read -r line; do
  lineno=$((lineno+1))
  if [ $in_block -eq 0 ] && [ "$line" = '```bash' ]; then
    in_block=1; block=""; start_line=$((lineno+1)); continue
  fi
  if [ $in_block -eq 1 ] && [ "$line" = '```' ]; then
    in_block=0; run_block "$block" "$CATNAME:$start_line"; continue
  fi
  [ $in_block -eq 1 ] && block+="$line"$'\n'
done < "$CATALOGUE"
done

echo
echo "pass=$pass noisy=$noisy slow=$slow empty=$empty error=$error nopath=$nopath skipped=$skipped"

if [ "$consistency_fail" -eq 1 ] && [ ${#failures[@]} -eq 0 ]; then
  echo
  echo "FAILED on self-consistency alone. Every recipe fires; the skill's"
  echo "claims about itself do not. Fix those, then re-run."
  exit 1
fi

if [ ${#failures[@]} -gt 0 ]; then
  echo
  echo "FAILED. A recipe that matches nothing reports a clean codebase whether or"
  echo "not the codebase is clean; a recipe that matches everything reports nothing"
  echo "usable and burns the audit. Both are broken. Fix these before shipping:"
  if [ "$empty" -gt 0 ]; then
    echo
    echo "  NOTE on EMPTY: this harness cannot tell a broken recipe from a corpus"
    echo "  with nothing of that kind in it — which is family 2, committed by the"
    echo "  tool that hunts family 2. A design-system repo has no cron config and"
    echo "  no untyped boundaries, and three recipes go EMPTY against it while"
    echo "  being perfectly sound. Before touching a pattern, run the same recipe"
    echo "  by hand against a corpus that definitely contains the thing. Point"
    echo "  this at a broad application repo, not a library."
    echo
  fi
  if [ "$noisy" -gt 0 ]; then
    echo
    echo "  NOTE on NOISY: ceilings are hits>=$NOISE_CEILING or bytes>$BYTE_CEILING,"
    echo "  against a corpus of $CORPUS_FILES files. A recipe that is genuinely too"
    echo "  broad and one that is fine on a corpus several times the tuning size"
    echo "  FAIL IDENTICALLY here, so check which you have before narrowing a"
    echo "  pattern — narrowing a working detector is how it goes blind."
    echo "  Rank instead of narrowing (this is SKILL.md's own guidance):"
    echo "    <recipe> | awk -F: '{print \$1}' | sort | uniq -c | sort -rn | head -20"
    echo "  Or re-run with a corpus-appropriate ceiling:"
    echo "    NOISE_CEILING=$((NOISE_CEILING*2)) BYTE_CEILING=$((BYTE_CEILING*2)) \\"
    echo "      scripts/check-recipes.sh $CORPUS"
    echo
  fi
  printf '  - %s\n' "${failures[@]}"
  [ "$consistency_fail" -eq 1 ] && echo "  - plus the self-consistency failures above."
  exit 1
fi

echo "All runnable recipes fire against a real corpus."
