---
name: clip
description: Copy the deliverable from Claude's last response to clipboard. Strips AI commentary. Supports plain text mode and custom instructions.
argument-hint: "[clean] [what to copy]"
---

Copy content to clipboard using `pbcopy`.

Argument: `$ARGUMENTS` (optional)

## Source of truth

Your previous response is already in conversation context. Copy the requested slice **verbatim** from it straight to the clipboard:

```bash
pbcopy <<'EOF'
<exact content, character-for-character — no rewording, no summarizing>
EOF
```

One attempt, then confirm. Do not hunt for response or transcript files on disk (`/tmp/claude/response.md` etc.) — none exist.

## Modes

Parse `$ARGUMENTS`:

- **No argument** (`/clip`): copy the deliverable portion of the last response.
- **"clean" or "plain"** (`/clip clean`): same, but strip markdown to plain text.
- **Custom instruction** (`/clip the SQL query`, `/clip second paragraph`): extract the specified slice.

## What counts as the deliverable

The user wants the artifact, not the chatter: strip framing like "Here's the...", option labels, commentary before/after, and blockquote `>` markers. Keep the content's own markdown unless clean mode.

## Clean mode (strip markdown)

Write the heredoc as plain text: drop `**`/`*`/`` ` `` markers, heading `#`s, and turn `[text](url)` into `text (url)` — while keeping every word identical.

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
