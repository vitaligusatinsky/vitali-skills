---
name: macwhisper
description: Pull transcripts from the local MacWhisper SQLite database — find a recording by a quoted phrase, list recent sessions, fetch a full transcript with timestamps, or export to markdown. Triggers on /macwhisper, "find the recording where I said X", "pull from macwhisper", "macwhisper transcript", "which recording was this from", or when the user pastes a transcript-style quote and asks where it came from.
argument-hint: "[search <phrase> | recent [Nd] | get <id|partial-title> | export <id>]"
---

# MacWhisper Transcript Lookup

Read the local MacWhisper SQLite DB directly. No exports, no UI automation.

## DB location and shape

- Path: `~/Library/Application Support/MacWhisper/Database/main.sqlite`
- Mode: WAL — safe to read while MacWhisper is open. ALWAYS use `sqlite3 -readonly`.
- Key tables:
  - `session` — one row per recording. Columns: `id` (BLOB), `dateCreated`, `playbackDuration` (s), `userChosenTitle`, `aiTitle`, `originalFilename`, `fullText`, `aiSummary`, `aiSummaryShort`, `textPreview`, `detectedLanguage`, `transcriptionDidSucceed`, `hasBeenDiarized`, `sourceAppBundleID`, `dateDeleted`
  - `sessionFTS` — FTS5 virtual table over `(id, fullText, aiSummary, userChosenTitle)`. MacWhisper maintains this via triggers; it is ALWAYS fresh.
  - `transcriptline` — line-level rows with `sessionId`, `text`, `start`, `end` (milliseconds), `speakerID`, `wordsJson`
  - `speaker`, `session_speaker` — diarization (only if `hasBeenDiarized = 1`)
  - `tag`, `session_tag` — user tags
- IDs are BLOBs — always wrap reads/writes in `hex(id)` and `x'…'` literals.

## Operating rules

1. NEVER open the DB in write mode. Always `sqlite3 -readonly`.
2. NEVER use `LIKE '%phrase%'` on `fullText` — use `sessionFTS MATCH` instead (orders of magnitude faster, already indexed).
3. Filter out trashed recordings: `WHERE dateDeleted IS NULL`.
4. When the user pastes a quote, treat it as an FTS lookup. Don't ask which recording — just find it.
5. Title fallback chain: `userChosenTitle → aiTitle → originalFilename → 'Untitled'`.

## Modes

Detect from the user's message. If ambiguous, default to **search**.

### Mode: search (most common)

Triggered by: a quoted phrase, "find the recording where…", "which session was this", a pasted snippet.

```bash
DB="$HOME/Library/Application Support/MacWhisper/Database/main.sqlite"
PHRASE="left border thing"   # 3–6 distinctive words from the user's quote

sqlite3 -readonly "$DB" <<SQL
.mode column
.headers on
SELECT
  hex(s.id)                                                      AS id,
  datetime(s.dateCreated)                                        AS at,
  COALESCE(s.userChosenTitle, s.aiTitle, s.originalFilename)     AS title,
  printf('%dm', CAST(s.playbackDuration/60 AS INT))              AS dur,
  s.detectedLanguage                                             AS lang,
  snippet(sessionFTS, 1, '«', '»', '…', 12)                      AS hit
FROM sessionFTS f
JOIN session s ON s.rowid = f.rowid
WHERE sessionFTS MATCH '"$PHRASE"'
  AND s.dateDeleted IS NULL
ORDER BY bm25(sessionFTS), s.dateCreated DESC
LIMIT 5;
SQL
```

FTS query syntax notes:
- Quote multi-word phrases for exact match: `MATCH '"left border thing"'`
- Drop quotes for AND-of-tokens: `MATCH 'border solid colors'`
- Boolean ops supported: `MATCH 'border AND (solid OR fancy)'`
- If you get zero hits, retry with fewer tokens or unquoted before giving up.

### Mode: recent

Triggered by: "what did I record today / this week / last N days", "recent transcripts", `/macwhisper recent 7d`.

```bash
DB="$HOME/Library/Application Support/MacWhisper/Database/main.sqlite"
DAYS=7

sqlite3 -readonly "$DB" <<SQL
.mode column
.headers on
SELECT
  hex(id)                                                        AS id,
  datetime(dateCreated)                                          AS at,
  COALESCE(userChosenTitle, aiTitle, originalFilename)           AS title,
  printf('%dm', CAST(playbackDuration/60 AS INT))                AS dur,
  detectedLanguage                                               AS lang,
  substr(COALESCE(aiSummaryShort, textPreview, ''), 1, 80)       AS preview
FROM session
WHERE dateCreated >= datetime('now', '-${DAYS} days')
  AND dateDeleted IS NULL
ORDER BY dateCreated DESC
LIMIT 30;
SQL
```

### Mode: get (full session detail)

Triggered by: a hex ID, or "show me that one", or "open …" / "expand …" after a search.

ID may be passed as full 32-char hex or a unique prefix (≥ 8 chars).

```bash
DB="$HOME/Library/Application Support/MacWhisper/Database/main.sqlite"
ID_PREFIX="EF65165B"   # accept 8+ chars; resolve below

# Resolve prefix → full id (refuse if ambiguous)
FULL=$(sqlite3 -readonly "$DB" "SELECT hex(id) FROM session WHERE hex(id) LIKE '${ID_PREFIX}%' LIMIT 2;")
# If two lines come back, ask the user to disambiguate.

sqlite3 -readonly "$DB" <<SQL
.mode list
SELECT
  '## ' || COALESCE(userChosenTitle, aiTitle, originalFilename, 'Untitled') || char(10) ||
  '- id: ' || hex(id) || char(10) ||
  '- recorded: ' || datetime(dateCreated) || char(10) ||
  '- duration: ' || printf('%d min', CAST(playbackDuration/60 AS INT)) || char(10) ||
  '- language: ' || COALESCE(detectedLanguage, 'unknown') || char(10) ||
  '- source app: ' || COALESCE(sourceAppBundleID, '—') || char(10) || char(10) ||
  CASE WHEN aiSummary IS NOT NULL
       THEN '### Summary' || char(10) || aiSummary || char(10) || char(10)
       ELSE '' END ||
  '### Transcript' || char(10) ||
  fullText
FROM session
WHERE hex(id) = '$FULL';
SQL
```

For line-level access with timestamps:

```bash
sqlite3 -readonly "$DB" <<SQL
.mode tabs
SELECT
  printf('%02d:%02d', start/60000, (start/1000) % 60) AS t,
  text
FROM transcriptline
WHERE hex(sessionId) = '$FULL'
ORDER BY start;
SQL
```

If the session was diarized (`hasBeenDiarized = 1`), join `speaker`:

```sql
SELECT
  printf('%02d:%02d', tl.start/60000, (tl.start/1000) % 60) AS t,
  COALESCE(sp.name, 'Speaker ' || substr(hex(tl.speakerID), 1, 4)) AS who,
  tl.text
FROM transcriptline tl
LEFT JOIN speaker sp ON sp.id = tl.speakerID
WHERE hex(tl.sessionId) = '$FULL'
ORDER BY tl.start;
```

### Mode: export

Triggered by: "export to markdown", "save the transcript", `/macwhisper export <id>`.

Write to `/tmp/macwhisper-<short-id>-<slug>.md` by default — never into the repo unless asked. After writing, show the path and offer to move it.

## Output format

For **search** and **recent**: 5–10 rows max, columnar. Bold the most likely hit. Include `hex(id)` so the user can ask for more.

For **get**: render as markdown. Header = title. Then metadata block. Then summary if present. Then transcript (truncate to ~3000 chars if it's a long meeting and ask before dumping the full thing).

For **export**: report the file path and word count.

## Anti-patterns

- ❌ Reading the DB with `bun:sqlite` from a one-off skill call. `sqlite3 -readonly` ships with macOS, no project deps needed.
- ❌ `LIKE '%phrase%'` scans on `fullText`. Use FTS5 `MATCH`.
- ❌ Writing to the DB. Ever. MacWhisper owns it.
- ❌ Asking the user "which recording?" when they pasted a distinctive quote — search first, then ask only if FTS returns multiple equally-good hits.
- ❌ Saving exported transcripts into the working directory. Default to `/tmp/`.
