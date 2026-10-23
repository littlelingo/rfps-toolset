---
name: build-wip
description: Build the work-in-progress response docx (keeps Work Order and evaluation lines, fills the [text] placeholders)
argument-hint: [active-solution folder or its source folder]
allowed-tools: Bash(rfps-build-response:*), Bash(rfps-use-solution:*), Bash(rfps-open-items:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Build the WIP response document for the active solution, or for the folder given in `$ARGUMENTS`.

1. Run `rfps-build-response --solution $ARGUMENTS --mode wip`. With no arguments, use `--solution` alone; it reads the active-solution pointer. If there is no active solution, tell the user to run `/rfps:new-engagement` or `/rfps:use-solution`.
2. Report briefly from the printed build report: headings poured, placeholders still in the document, unresolved markers shown highlighted, the evidence warnings (uncleared, superseded, unknown, or banned items) grouped by register ID, register rows nothing cites yet, the response body word count and page estimate, and the path of the WIP docx. When markers remain, link `open-items.md` in the solution folder (run `rfps-open-items` first to refresh it; do not use `--mark`, which edits response files) so the user can work through them.
3. If the build stops with a heading mismatch, list the headings that differ. The headings in `active-solution/response/*.md` must match the template docx exactly.

Do not edit the template docx or any `response/*.md` or `evidence/register.csv` file as part of this command.
