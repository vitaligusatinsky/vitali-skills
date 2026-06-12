---
name: clip
description: Copy the deliverable from Claude's last response to clipboard. Strips AI commentary. Supports plain text mode and custom instructions.
argument-hint: "[clean] [what to copy]"
---

Copy content to clipboard using `pbcopy`.

Argument: `$ARGUMENTS` (optional)

## Source of truth

Claude Code auto-writes the last assistant response to `/tmp/claude/response.md` every turn. **Always read from that file via shell pipelines** — never re-emit content through `echo` or heredocs. You already have your previous response in conversation context, so you can reason about what to extract and build a bash extractor without reading the file through the Read tool.

Rule: the content should travel from `/tmp/claude/response.md` → `pbcopy` via shell only. No content should appear in your tool arguments or text output.

## Modes

Parse `$ARGUMENTS`:

- **No argument** (`/clip`): copy the deliverable portion of the last response.
- **"clean" or "plain"** (`/clip clean`): same, but strip markdown to plain text.
- **Custom instruction** (`/clip the SQL query`, `/clip second paragraph`): extract the specified slice.

## How to extract without re-emitting

Build a bash pipeline that reads `/tmp/claude/response.md` and pipes to `pbcopy`. Choose the narrowest tool:

- **Whole response**: `pbcopy < /tmp/claude/response.md`
- **Between `---` delimiters**: `awk '/^---$/{f=!f;next} f' /tmp/claude/response.md | pbcopy`
- **Line range** (you know from your own prior output which lines): `sed -n '12,28p' /tmp/claude/response.md | pbcopy`
- **Section under a heading**: `awk '/^## Heading/{f=1;next} /^## /{f=0} f' /tmp/claude/response.md | pbcopy`
- **Grep a single line** (URL, command, etc.): `grep -oE 'https?://\S+' /tmp/claude/response.md | head -1 | pbcopy`
- **First/last code block**: `awk '/^```/{f=!f;next} f' /tmp/claude/response.md | pbcopy`

If the extraction genuinely needs content you can't address by line/pattern, check line numbers first with `nl /tmp/claude/response.md` or `wc -l`, then use `sed -n`. Only fall back to a heredoc if no shell pipeline can express the slice.

## Clean mode (strip markdown)

Pipe through perl before `pbcopy`:

```bash
perl -pe 's/\*\*(.+?)\*\*/$1/g; s/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/$1/g; s/`([^`]+)`/$1/g; s/^#+\s+//; s/^\s*[-*]\s+//g; s/\[([^\]]+)\]\([^)]+\)/$1/g' /tmp/claude/response.md | pbcopy
```

Combine with extraction by inserting the extractor before the perl stage.

## Output

Confirm with one short line: "Copied.", "Copied (plain).", or "Copied: <brief description>." Do not include the content itself.

## Examples

```
# Whole last response (or its main deliverable)
/clip

# Plain text for email/Slack
/clip clean

# Specific slice
/clip the SQL query
/clip just the function name
/clip the second paragraph

# Slice + plain
/clip clean the bullet points about pricing
```
