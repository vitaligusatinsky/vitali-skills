# claude-skills

Agent skills by [@vitaligusatinsky](https://github.com/vitaligusatinsky), installable via [skills.sh](https://skills.sh) / the `skills` CLI.

## Install

```bash
# all skills in this repo
npx skills add vitaligusatinsky/claude-skills

# a specific skill
npx skills add vitaligusatinsky/claude-skills/skills/condense
```

Or drop a skill folder into `~/.claude/skills/` for Claude Code.

## Skills

### `condense`
Validated text shortening to a hard character/byte/word budget. Cuts text to fit a
limit (e.g. a 4000-char field) **without losing meaning** — it preserves intent,
structure, and every concrete detail (file paths, names, commands, constraints),
then **proves the result fits** by writing to a temp file and counting (`wc -m`),
looping until it's under budget. Refuses to drop a required detail to hit a number;
if a faithful fit is impossible it says so and shows the smallest faithful version.

Triggers on `/condense`, "shorten this to under N chars", "fit this in N characters",
"tighten this prompt to a limit", etc. Includes worked examples (meta description,
commit subject, status line, and an honest over-budget case).

## License

MIT
