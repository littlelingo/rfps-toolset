---
name: build-final
description: Finalize and publish the response docx as a new copy (scaffold lines and grounded/assertion markers stripped; copied to 11 Final Submission; refuses while decisions, placeholders, or uncleared evidence remain)
argument-hint: [active-solution folder or its source folder] [--force]
allowed-tools: Bash(rfps-build-response:*), Bash(rfps-use-solution:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Finalize the response document for the active solution, or for the folder given in `$ARGUMENTS` (an optional `--force` is passed through).

1. Run `rfps-build-response --solution <folder if given> --mode final` (use `--solution` alone for the active solution), adding `--force` only if the user included it.
2. If it succeeds, report the path of the new `_FINAL.docx` in `active-solution/build/` and the copy placed in the source folder's `11 Final Submission`, the markers stripped, any omitted headings removed, and the word count and page estimate. Remind the user that the file has not been opened in Word, so layout and graphics still need a visual check.
3. If it refuses, do not retry with `--force` on your own. Summarize the blocking items from the build report: unresolved `[DECISION]`, `[EVIDENCE NEEDED]`, `[OPEN]`, or bracketed placeholders; headings with no content; and evidence problems (IDs not `cleared`, superseded, unknown, or banned phrases). Group them by response heading or register ID and say where to resolve them (`response/*.md` or `evidence/register.csv`). Offer `--force` only as a way to produce a review copy that must not be submitted (a forced copy is also written to `11 Final Submission`, so say so).

Do not edit the template docx or any `response/*.md` or `evidence/register.csv` file as part of this command.
