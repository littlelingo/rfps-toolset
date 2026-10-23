---
name: build-wip
description: Create or update the shared work-in-progress response docx in 05 Draft Response; changes go in as tracked changes so other people's edits and comments are kept
argument-hint: [active-solution folder or its source folder]
allowed-tools: Bash(rfps-sync-docx:*), Bash(rfps-build-response:*), Bash(rfps-use-solution:*), Bash(rfps-open-items:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Create or update the shared WIP response document for the active solution, or for the folder given in `$ARGUMENTS`.

The WIP docx lives next to the template (`05 Draft Response`, or `wip_docx` in `solution.toml`). It is created once from the template and then never regenerated: other people may be commenting and editing in it. Each run applies only the paragraphs whose `response/*.md` text changed, as Word tracked changes (author "rfps") that reviewers accept or reject. Edits and comments others made are never overwritten.

1. If there is no active solution, tell the user to run `/rfps:new-engagement` or `/rfps:use-solution`.
2. Run `rfps-sync-docx --status` and show the per-section result: which sections have response changes to push, and which have edits made in the document. If any section was edited in the document, run the `/rfps:pull-docx` steps first so the response text is current before anything is written to the document. If nothing has changed, say so and stop.
3. Before pushing, tell the user what will change and ask for approval (use the question tool): push, push after review, or skip. "Approved" in a conversation about the text counts only if the user said to push it. Then run `rfps-sync-docx` (add `--dry-run` first if the user wants to see it). If Word's lock file shows the document is open, report that and do not use `--force` unless the user says to.
4. Report: the changes pushed, any conflicts (a response change that touches text someone edited in the document is skipped and left pending; show the conflicting paragraphs so the user can decide which version wins), the evidence warnings (uncleared, superseded, unknown or banned items), and the path of the WIP docx. When markers remain, link `open-items.md` in the solution folder (run `rfps-open-items` first to refresh it; do not use `--mark`, which edits response files).
5. If it stops with a heading mismatch, list the headings that differ. The headings in `active-solution/response/*.md` must match the template docx exactly.
6. `rfps-sync-docx --rebuild` regenerates the WIP from the template and discards everyone's edits and comments (a backup goes to the solution's `build/` folder). Run it only when the user explicitly asks. For a throwaway regeneration with the full build report, `rfps-build-response --solution --mode wip` writes to `build/` and never touches the shared document.

Do not edit the template docx or any `response/*.md` or `evidence/register.csv` file as part of this command.
