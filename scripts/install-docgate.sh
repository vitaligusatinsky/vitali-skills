#!/bin/bash
# Install the docgate skill into Claude Code: the skill folder to ~/.claude/skills/docgate,
# the command to ~/.claude/bin/docgate, the doc-critic agent to ~/.claude/agents/.
# Re-run after every change; it replaces the installed copy (rsync --delete).
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
src="$here/skills/docgate"
dest="$HOME/.claude/skills/docgate"
mkdir -p "$dest" "$HOME/.claude/bin" "$HOME/.claude/agents"
rsync -a --delete --exclude '__pycache__' "$src/" "$dest/"
ln -sf "$dest/bin/docgate" "$HOME/.claude/bin/docgate"
if [ -f "$src/agents/doc-critic.md" ]; then cp "$src/agents/doc-critic.md" "$HOME/.claude/agents/doc-critic.md"; fi
python3 -c "import importlib.metadata as m; v=m.version('playwright'); print('playwright', v)" || {
  echo "python playwright missing: pip install playwright==1.58.0 && playwright install chromium"; exit 1; }
echo "installed docgate $("$HOME/.claude/bin/docgate" version)"
