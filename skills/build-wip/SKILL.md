---
name: build-wip
description: Create or update the shared work-in-progress response document (a Google Doc by default, or Word with --word); approved changes go in as suggestions or tracked changes so other people's edits and comments are kept
argument-hint: [--word] [active-solution folder or its source folder]
allowed-tools: Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Bash(rfps-build-response:*), Bash(rfps-use-solution:*), Bash(rfps-open-items:*), Read, Write
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Create or update the shared WIP document for the active solution. It is created once and then never regenerated: other people comment and edit in it. Each run applies only the response text that changed, as suggestions (Google Docs) or tracked changes (Word), so their edits and comments stay.

Which route: **Google Docs is the default.** Use Word when `$ARGUMENTS` contains `--word` or `solution.toml` has `wip_format = "docx"`; then follow "Word" below. 
If there is no active solution, tell the user to run `/rfps:new-engagement` or `/rfps:use-solution`.

## Google Docs (default)

`rfps-sync-gdoc` does the planning; Claude does the reading and writing through the Google connectors. Before the first Google call, read the `google-workspace` skill if it is listed, and check that the Google Docs editor tools (`read_doc`, `update_doc`) and Drive tools are available (search for and load them if they are deferred). If the Docs editor tools are missing, stop and tell the user to turn on the Google Docs connector in this chat, or use `--word`. Do not make a second document as a workaround.

**Everything added to the doc is a suggestion** (tracked changes that people accept or reject), including the first draft: the new doc holds only the template's headings, evaluation lines and `[text]` placeholders, and the response text arrives as suggestions on the first push. Never send an edit as a direct change.

**Saving `read_doc` output.** Always read with `commentsIncluded: true`. If the tool result was saved to a file, use that path. If it came back inline (about 25 KB for three pages), write a trimmed copy to a file: keep `documentId`, `revisionId`, the top-level `comments` array as returned, and per tab `documentTab.commentAnchors` as returned and `documentTab.body.content[]` reduced to each element's `startIndex`/`endIndex`, `paragraph.elements[]` (`startIndex`, `endIndex`, `textRun.content`, `textRun.suggestedInsertionIds`, `textRun.suggestedDeletionIds`), `paragraph.paragraphStyle.namedStyleType` and `headingId`, `paragraph.bullet`, and `table.tableRows[].tableCells[].content[]` the same way. Drop every other style field. Keep indexes and text exactly as returned.

**No document yet** (`rfps-sync-gdoc --url` says none is recorded):
1. Run `rfps-sync-gdoc --html` (a skeleton). Read `build/gdoc-create.html` in the solution folder.
2. Ask where to put it (a Drive folder, or My Drive) and confirm the connector's Google account is the one the user works in. Call Drive `create_file` with `contentMimeType` `text/html`, the file's text as `textContent`, and the title "<solution title> - Response WIP". Note the returned file ID.
3. Read it with `read_doc`, save the JSON as above, and run `rfps-sync-gdoc --init <that file> --doc-id <file ID>`.
4. Continue with "Document exists" step 1 so the response text goes in as suggestions. The template's page design (cover, headers, fonts) is not in this document; the FINAL submission still comes from the Word template through `/rfps:build-final`.

**Document exists:**
1. Read it (see above). Run `rfps-sync-gdoc --status <file>`. Show the per-section result.
2. If any section was edited in the doc, run the `/rfps:pull-wip` steps first so the response text is current. If nothing has changed, say so and stop.
3. Tell the user what will change and ask for approval (use the question tool): push, or skip. Then run `rfps-sync-gdoc --push <file>`. It writes `build/gdoc-push.json`.
4. Read `build/gdoc-push.json` and send it unchanged with `update_doc` (its `documentId`, `requests` and `writeControl`, which sets `writeMode: SUGGEST`). Never reorder the requests, never drop `requiredRevisionId`, never remove `writeMode`. On a 400 revision mismatch, read the doc again and redo steps 1 to 4. If the connector says "Unsupported WriteControl mode", stop: tell the user suggestions are unavailable and offer the list of changes; do not make direct edits.
5. Run `rfps-sync-gdoc --commit`. Read the doc again and run `rfps-sync-gdoc --status <file>`; it should show everything in sync. Say that the changes are suggestions waiting in the doc for someone to accept or reject, and link the doc.
6. **Comments for open items.** Run `rfps-sync-gdoc --comments-plan <file>`. It plans one comment for each `[DECISION]`, `[OPEN]` and `[EVIDENCE NEEDED]` marker in the doc that has none yet (`--kinds` changes which; assertions are left out). If it lists comments, tell the user and send `build/gdoc-comments.json` with `update_doc`, save the whole reply to a file, and run `rfps-sync-gdoc --comments-commit <reply file>`. Each comment is anchored on its marker, so the item's link in `open-items.md`, the status page and the pane opens the doc at that spot. The connector can add comments but cannot reply to or resolve them, so people do that in the doc.
7. Report conflicts (a response change that touches text someone edited in the doc is skipped and left pending; show the paragraphs so the user can decide which version wins) and the evidence warnings (`rfps-build-response --solution --mode wip` prints them in a scratch build). When markers remain, link `open-items.md` (run `rfps-open-items` first; do not use `--mark`, which edits response files).

Inserted text is plain, so bold from the markdown is not carried into a Google Doc.

## Word (`--word`)

1. Run `rfps-sync-docx --status` and show the per-section result. If any section was edited in the document, run the `/rfps:pull-wip --word` steps first. If nothing has changed, say so and stop.
2. Tell the user what will change and ask for approval. Then run `rfps-sync-docx` (add `--dry-run` first if the user wants to see it). The WIP docx lives next to the template (`05 Draft Response`, or `wip_docx` in `solution.toml`) and changes go in as tracked changes by author "rfps". If Word's lock file shows the document is open, report that and do not use `--force` unless the user says to.
3. Report the changes pushed, any conflicts, the evidence warnings, and the path of the docx. Heading mismatches must be fixed: the headings in `response/*.md` must match the template exactly.
4. `rfps-sync-docx --rebuild` regenerates the WIP and discards everyone's edits and comments (a backup goes to `build/`); run it only when the user explicitly asks.

For a throwaway regeneration with the full build report, `rfps-build-response --solution --mode wip` writes to `build/` and never touches the shared document.

Do not edit the template docx or any `response/*.md` or `evidence/register.csv` file as part of this command.
