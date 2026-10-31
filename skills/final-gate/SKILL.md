---
name: final-gate
description: >
  Check the PDF that will be submitted before it goes out - page count and size, extractable text, no internal
  markers or links to the working document, required wording, margins, metadata, blocking compliance items and
  open forms - and write a cleaned copy with the personal metadata removed. Trigger when the user asks "is the
  PDF ready", "final check", "can we submit", "check the export", or "scrub the metadata".
argument-hint: "[path to the PDF, default the newest in the final folder] [--scrub]"
allowed-tools: Bash(rfps-final-gate:*), Bash(rfps-refresh-reports:*), Bash(rfps-worklist:*), Bash(ls:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules apply to this skill.

The submission file is a PDF exported from the final Google Doc. This is the last check on that file, and it reads only; it never edits the PDF in place.

1. Find the PDF: the one named in `$ARGUMENTS`, else the newest `.pdf` in `final_copy_dir` (default `11 Final Submission`). If there is none, tell the user to export the final Google Doc to PDF (File, Download, PDF) into that folder, or see `build-final` for the steps, and stop.
2. Run `rfps-refresh-reports` first so the compliance report and the blocking list are current, then `rfps-final-gate --pdf <file>` (add `--scrub` if the user asked, or if the metadata check failed and they agree). Show the failed checks first, then the rest, and link `final-gate.md`.
3. For each failure say where to fix it: a page count or margin problem is fixed in the Google Doc and re-exported; a marker or placeholder in the PDF means the final Doc was built from text that still had one (fix `response/*.md`, rebuild the final copy, export again); metadata is fixed with `--scrub` and the cleaned copy is checked again with `--pdf`; an open form is a row in `submission.md`.
4. Margins other than the left one are approximate (a page number counts as text), so a margin warning is for the user to look at, not a verdict. Say that the gate cannot judge layout, graphics, fonts the agency requires or whether tables broke badly; the user still opens the PDF and looks at it.

Do not submit, email or upload anything. The result is a report; the decision to submit is the user's.
