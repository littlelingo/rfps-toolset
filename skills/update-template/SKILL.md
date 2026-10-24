---
name: update-template
description: After the response template changed (new, renamed, removed or moved sections), compare its headings with response/*.md and bring the response in line - adds new sections, renames on request, never deletes text
argument-hint: [new template .docx]
allowed-tools: Bash(rfps-update-template:*), Bash(rfps-sync-docx:*), Bash(rfps-sync-gdoc:*), Bash(rfps-flow-status:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules apply here. The heading text is the contract between the template and `response/*.md`: the build fails when they differ.

1. Run `rfps-update-template` (add `--template "<new docx>"` when `$ARGUMENTS` names a replacement; without it the template named in `solution.toml` is compared). It changes nothing yet. Report what it found, in plain terms:
   - **new** headings: sections the template added;
   - **renamed**: a close match to a heading that disappeared;
   - **possibly renamed**: a different wording in the same place (same level, same neighbours); ask the user to confirm each, because it could also be a removed section plus a new one;
   - **removed**: headings only in `response/` (their text stays);
   - **level changed** and **order differs**.
2. Ask what to do (question tool): apply, apply with changes, or stop. Then run `rfps-update-template --apply` with `--rename` for the confirmed close renames and `--rename-all` for the confirmed same-place ones, and `--template "<new docx>" --adopt` when the new file should become the solution's template. New sections are added empty, in the template's order; nothing is deleted.
3. For a removed heading, show its text and ask where it belongs: move it by hand into another section and delete the heading, or keep it by restoring the heading in the template. Do not delete text yourself.
4. A shared WIP document does not follow the template by itself. For Word, run `rfps-sync-docx --status` (a heading mismatch is reported) and rebuild with `rfps-sync-docx --rebuild` only if the user accepts losing others' edits there; for a Google Doc, add or rename the heading in the doc by hand (the sync tool reports a heading mismatch). Then run `rfps-flow-status` and link the changed files.
