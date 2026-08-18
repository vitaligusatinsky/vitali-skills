#!/usr/bin/env python3
"""Fail if any SKILL.md frontmatter does not parse.

A skill whose YAML is invalid is skipped by `npx skills add` with a warning
most people never read: the install says "Found 5 skills", succeeds, and drops
one. Silent partial success is the failure mode this repo's antislop skill is
about, so it should not ship in the repo that hosts it.

An unquoted description containing ": " is the usual cause. Use `>-` block
scalars for anything with punctuation.
"""
import glob, sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML not installed: pip install pyyaml")

bad = []
found = sorted(glob.glob("skills/*/SKILL.md"))
for path in found:
    text = open(path).read()
    if not text.startswith("---"):
        bad.append((path, "no frontmatter")); continue
    block = text.split("---")[1]
    try:
        data = yaml.safe_load(block)
    except Exception as exc:
        bad.append((path, str(exc).split("\n")[0])); continue
    for field in ("name", "description"):
        if not (data or {}).get(field):
            bad.append((path, f"missing {field}"))

print(f"checked {len(found)} skills")
for path, why in bad:
    print(f"  FAIL {path}: {why}")
sys.exit(1 if bad else 0)
