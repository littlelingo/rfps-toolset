---
name: file-audit
description: Check that every file in the solution folder has a known origin, and record the ones that do not
argument-hint: [--record PATH --by WHO --why WHY]
allowed-tools: Bash(rfps-file-audit:*), Read
---

Run `rfps-file-audit $ARGUMENTS` (with no arguments it lists the unlisted and recorded files for the active solution).

- With no arguments: report how many files are unlisted and recorded. For each unlisted file give its path, when it appeared, and a guess at what made it. Ask whether each is Needed, Review or Remove; do not decide for the user and do not delete anything.
- With `--record PATH --by WHO --why WHY [--verdict Needed|Review|Remove]`: record the file in the solution's `provenance.md` and confirm.
- Standard files (listed in `tools/known_files.toml`) never appear. Report-only unless the user supplies the record details.
