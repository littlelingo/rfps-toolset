---
name: pull-docx
description: Bring edits and comments that other people made in the shared WIP docx (Word or Google Docs) back into response/*.md, shown for approval first
argument-hint: [section heading]
allowed-tools: Bash(rfps-sync-docx:*), Bash(rfps-open-items:*), Bash(rfps-flow-status:*), Read, Edit
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

People resolve open items and edit text directly in the shared WIP docx, so `response/*.md` (which the status, evidence, compliance and FINAL checks read) goes stale until their edits are brought back. This skill does that, with approval.

1. Run `rfps-sync-docx --pull` (it changes nothing in `response/`). It lists, per section, each change in the document that the response lacks: `replace`, `insert` or `delete`, with the old and new text, markers removed or added in the document, and any paragraph whose bold or italic formatting was simplified. It also writes their comments to `review/doc-comments.md`.
2. Show the user a short summary: sections with changes, conflicts (text changed in both the document and the response is not brought in, so the user must choose which version wins), and the new comments with their sections. Highlight every `[DECISION]`, `[OPEN]`, `[EVIDENCE NEEDED]` or `[ASSERTION]` marker that was removed in the document and ask whether it was resolved or just deleted.
3. Check what the edits claim. A fact someone added in the document with no evidence tag is not grounded: ask whether to add a register row, tag it `[ASSERTION: ...]` or mark it `[EVIDENCE NEEDED: ...]` (see the `integrate-edits` skill). Never hide an unsupported claim.
4. Ask for approval with the question tool: bring in all, bring in some sections (pass them with `--sections "A;B"`), or none. Then run `rfps-sync-docx --pull --apply` (with `--sections` if limited).
5. After applying: run `rfps-open-items --mark` if any marker changed, then `rfps-sync-docx --status` (it should show the document and the response in step), and offer `/rfps:integrate` for the changed sections to weave the new text into one voice, then `/rfps:build-wip` to push anything the response has that the document lacks. Link the changed files and `review/doc-comments.md`.

Comments are never written into the response. Report them; the user decides what each one needs. Replies and resolved state are not read. Edits to tables come in as plain tables; richer formatting added in Word stays in the document only.
