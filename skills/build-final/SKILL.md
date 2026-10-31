---
name: build-final
description: Finalize and publish the response docx as a new copy (scaffold lines and grounded/assertion markers stripped; copied to 11 Final Submission; refuses while decisions, placeholders, or uncleared evidence remain)
argument-hint: [active-solution folder or its source folder] [--force]
disable-model-invocation: true
allowed-tools: Bash(rfps-collab:*), Bash(rfps-build-response:*), Bash(rfps-set-config:*), Bash(rfps-use-solution:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Finalize the response document for the active solution, or for the folder given in `$ARGUMENTS` (an optional `--force` is passed through).

0. If a shared WIP document exists, check it first: Google Docs (the default) by reading the doc and running `rfps-sync-gdoc --status <file>` (see `/rfps:build-wip`), Word (`wip_format = "docx"`) by running `rfps-sync-docx --status`. If it reports edits made in the document that the response text does not have, FINAL is built from `response/*.md` and would not include those edits. Run the `/rfps:pull-wip` steps first (it shows the edits for approval), then continue. For Google Docs also read the "Waiting for people in the doc" line of `rfps-sync-gdoc --status` (read the doc with `commentsIncluded: true`): suggestions nobody has accepted and comments still open mean the reviewers have not signed off, so tell the user the counts before building. This does not stop the build; the flow step "Suggestions and comments in the shared document settled" tracks it.
1. **Where the copy goes.** The FINAL is built in the build folder and copied to `final_copy_dir` (default: the capture's `11 Final Submission`). If the user has not been asked yet, ask where the final copy should go and record it with `rfps-set-config final_copy_dir <folder>`; use the default only if they give none.
2. Run `rfps-build-response --solution <folder if given> --mode final` (use `--solution` alone for the active solution), adding `--force` only if the user included it.
3. If it succeeds, report the path of the new `_FINAL.docx` in `active-solution/build/` and the copy placed in the source folder's `11 Final Submission`, the markers stripped, any omitted headings removed, and the word count and page estimate. Remind the user that the file has not been opened in Word, so layout and graphics still need a visual check.
4. If it refuses, do not retry with `--force` on your own. Summarize the blocking items from the build report: unresolved `[DECISION]`, `[EVIDENCE NEEDED]`, `[OPEN]`, or bracketed placeholders; headings with no content; and evidence problems (IDs not `cleared`, superseded, unknown, or banned phrases). Group them by response heading or register ID and say where to resolve them (`response/*.md` or `evidence/register.csv`). Offer `--force` only as a way to produce a review copy that must not be submitted (a forced copy is also written to `11 Final Submission`, so say so).

## Submitting as a PDF (Google route)

When the submission file is a PDF exported from a Google Doc, `build-final` still produces the checked, clean `_FINAL.docx` (markers and scaffold lines stripped, evidence cleared), and that file is the source of the PDF:

1. Open the `_FINAL.docx` from `final_copy_dir` in Google Docs (in Drive, open it with Google Docs and choose File, Save as Google Docs). Look at the layout; the conversion can change tables and spacing.
2. File, Download, PDF document. Save it in `final_copy_dir` (default `11 Final Submission`).
3. Run `/rfps:final-gate`. It checks the PDF itself (pages, text, markers, links, margins, metadata, blocking items, open forms) and `--scrub` writes a copy without personal metadata.

Do not export the shared WIP document: it carries suggestions, comments, highlights and internal markers. An automated route that fills a clean copy of the Google template and exports it through the Drive connector is planned but not built; it needs a live test of the connector's PDF export first.

Do not edit the template docx or any `response/*.md` or `evidence/register.csv` file as part of this command.
