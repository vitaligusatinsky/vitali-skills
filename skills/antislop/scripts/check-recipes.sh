#!/usr/bin/env bash
# Prove every detection recipe in this skill actually fires.
#
# The skill's own rule is that a check which cannot fail is worse than no check.
# Its recipes are checks. This runs each one against a corpus known to contain
# real code, and fails if any returns nothing, because a recipe that matches
# zero files is indistinguishable from a clean codebase.
#
# This exists because five recipes once shipped using --include='*.{ts,js}',
# which matches zero files (fnmatch has no brace expansion). They exited 0 and
# printed nothing, so every audit using them reported a clean repo.
#
#   usage: scripts/check-recipes.sh [corpus-dir]
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

pass=0; empty=0; error=0; skipped=0; noisy=0; slow=0
# No recipe should take longer than this against a normal repo.
RECIPE_TIMEOUT="${RECIPE_TIMEOUT:-45}"
# Bytes matter independently of lines: one matched minified line can be ~800KB.
BYTE_CEILING="${BYTE_CEILING:-250000}"
# Above this many hits a recipe is not a detector, it is a listing.
NOISE_CEILING="${NOISE_CEILING:-400}"
failures=()

# Extract fenced bash blocks, one per temp file, preserving line numbers.
block=""; in_block=0; start_line=0; lineno=0
run_block() {
  local body="$1" first_line="$2"
  [ -z "${body//[[:space:]]/}" ] && return

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
    printf '  EMPTY %-22s matched nothing (a recipe that cannot fire)\n' "$first_line"
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

echo "corpus: $CORPUS"
echo "catalogues: $CATALOGUES"
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
echo "pass=$pass noisy=$noisy slow=$slow empty=$empty error=$error skipped=$skipped"

if [ ${#failures[@]} -gt 0 ]; then
  echo
  echo "FAILED. A recipe that matches nothing reports a clean codebase whether or"
  echo "not the codebase is clean; a recipe that matches everything reports nothing"
  echo "usable and burns the audit. Both are broken. Fix these before shipping:"
  printf '  - %s\n' "${failures[@]}"
  exit 1
fi

echo "All runnable recipes fire against a real corpus."
