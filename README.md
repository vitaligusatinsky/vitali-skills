# vitali-skills

Agent skills by [@vitaligusatinsky](https://github.com/vitaligusatinsky) for Claude Code, Codex, and other agents — installable via [skills.sh](https://skills.sh) / the `skills` CLI.

This is the canonical home for my general-purpose skills. (Brand-scoped sets live elsewhere, e.g. [`designanswers-skills`](https://github.com/vitaligusatinsky/designanswers-skills).)

## Install

```bash
# all skills in this repo
npx skills add vitaligusatinsky/vitali-skills

# a specific skill
npx skills add vitaligusatinsky/vitali-skills/skills/condense
```

Or drop a skill folder into `~/.claude/skills/` for Claude Code.

## Skills

### `condense`
Validated text shortening to a hard character/byte/word budget. Cuts text to fit a
limit (e.g. a 4000-char field) **without losing meaning** — preserves intent,
structure, and every concrete detail (file paths, names, commands, constraints),
then **proves the result fits** by writing to a temp file and counting (`wc -m`),
looping until it's under budget. Refuses to drop a required detail to hit a number;
if a faithful fit is impossible it says so and shows the smallest faithful version.
Triggers on `/condense`, "shorten this to under N chars", "fit this in N characters".

### `macwhisper`
Pull transcripts from the local MacWhisper SQLite database — find a recording by a
quoted phrase, list recent sessions, fetch a full transcript with timestamps, or
export to markdown. Triggers on `/macwhisper`, "find the recording where I said X",
"pull from macwhisper", "which recording was this from".

## License

MIT
