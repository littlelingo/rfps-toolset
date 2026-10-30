---
name: pull-wip
description: Bring edits and comments that other people made in the shared WIP document (Google Doc by default, or Word with --word) back into response/*.md, shown for approval first
argument-hint: [--word] [section heading]
allowed-tools: Bash(rfps-collab:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Bash(rfps-open-items:*), Bash(rfps-flow-status:*), Read, Write, Edit
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

People resolve open items and edit text directly in the shared WIP document, so `response/*.md` (which the status, evidence, compliance and FINAL checks read) goes stale until their edits are brought back. This skill does that, with approval.

Which route: Google Docs is the default; use Word when `$ARGUMENTS` contains `--word` or `solution.toml` has `wip_format = "docx"`.

1. **List the changes (changes nothing in `response/`).**
   - Google Docs: read the doc with `read_doc` and `commentsIncluded: true`, save the JSON to a file (a trimmed copy with the fields `/rfps:build-wip` lists is fine, and must keep `comments` and `commentAnchors`), and run `rfps-sync-gdoc --pull <file>`. It also reconciles every comment in the doc with `.state/gdoc-comments.json` and writes `review/doc-comments.md`. Before the first Google call, read the `google-workspace` skill if it is listed, and check the Docs tools are available; if not, tell the user to turn on the Google Docs connector or use `--word`.
   - Word: run `rfps-sync-docx --pull`; it also writes `review/doc-comments.md`.
   Either lists, per section, each change the response lacks: `replace`, `insert` or `delete`, with the old and new text, markers removed or added in the document, and any paragraph whose bold or italic formatting was simplified.
2. Show the user a short summary: sections with changes, conflicts (text changed in both the document and the response is not brought in, so the user must choose which version wins), the comment changes the tool printed (new comments, new replies, comments resolved or gone, a comment still open after its marker left the response, a comment resolved while its marker is still in the response), and the new comments with their sections. Highlight every `[DECISION]`, `[OPEN]`, `[EVIDENCE NEEDED]` or `[ASSERTION]` marker that was removed in the document and ask whether it was resolved or just deleted.
3. Check what the edits claim. A fact someone added with no evidence tag is not grounded: ask whether to add a register row, tag it `[ASSERTION: ...]` or mark it `[EVIDENCE NEEDED: ...]` (see the `integrate-edits` skill). Never hide an unsupported claim.
3b. **Reviewer comments.** The pull also lists open comments by people that are not tied to an item (`rfps-sync-gdoc --pull <file> --promote` shows what each would become). A reviewer's comment never blocks FINAL on its own, so ask whether to turn each real request into an `[OPEN: ...]` marker in the response at that spot; for the ones approved, run `rfps-sync-gdoc --pull <file> --promote <ids> --apply`. Then `/rfps:build-wip` puts the marker in the doc as a suggestion without adding a second comment. When a `[DECISION]` or `[OPEN]` thread has been answered in its replies, draft the replacement text from the reply for the user's approval and replace the marker; resolving the comment alone does not settle the item.
4. Ask for approval with the question tool: bring in all, bring in some sections (pass them with `--sections "A;B"`), or none. Then run the same command with `--apply` (Google: `rfps-sync-gdoc --pull <file> --apply`; Word: `rfps-sync-docx --pull --apply`).
5. After applying: run `rfps-open-items --mark` if any marker changed, then the status command for the route (it should show the document and the response in step), and offer `/rfps:integrate` for the changed sections to weave the new text into one voice, then `/rfps:build-wip` to push anything the response has that the document lacks. Link the changed files and `review/doc-comments.md`.

Comments are never written into the response. Report them; the user decides what each one needs. Record how one was handled with `rfps-sync-gdoc --comment-note <id> "<note>" --handled addressed|ignored`. The Google connector can add comments but cannot reply to or resolve them, so ask people to reply and resolve in the doc. Word comments are listed without replies or resolved state. Edits to tables come in as plain tables; richer formatting added in the document stays only there.
