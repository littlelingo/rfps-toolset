---
name: make-gdoc-template
description: Build a Google Doc version of the Word response template (its headings, boilerplate, tables, page setup, fonts, header and footer) to copy for each solution's shared work-in-progress document
argument-hint: [--update]
allowed-tools: Bash(rfps-sync-gdoc:*), Bash(rfps-flow-status:*), Read, Write
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules apply here.

The Word template stays the source for the FINAL submission. This makes a Google Doc that looks like it, so the shared work-in-progress document has the same page setup, fonts, headings, boilerplate and header and footer, and the page count reviewers see is close to the final. It is made once and copied (Drive `copy_file`) for each WIP; copying keeps everything, including headers and page setup, without sending a file through the call.

Before the first Google call read the `google-workspace` skill if it is listed, check that the Docs editor tools (`read_doc`, `update_doc`) and Drive tools are available, and confirm with the user which Google account the connector uses (the template is created there).

1. If `solution.toml` already has `gdoc_template` and `$ARGUMENTS` does not say `--update`, tell the user where it is and stop (`/rfps:build-wip` copies it). If the Word template changed, `--update` makes a new one.
2. Run `rfps-sync-gdoc --html`. It writes `build/gdoc-create.html`: the template's cover text, form tables, boilerplate under headings, evaluation lines and `[text]` placeholders, without any response text. Read it and call Drive `create_file` with `contentMimeType` `text/html`, the file's text as `textContent`, and the title "<template name> - Google template". Note the new file's ID.
3. Read the new doc with `read_doc` (if the result was saved to a file use that file as is; otherwise write a trimmed copy as `/rfps:build-wip` describes) and run `rfps-sync-gdoc --style-plan <file>`. It reads the Word template's page size and margins, body and heading fonts, sizes and colors, line spacing, header text and footer text, and writes `build/gdoc-style.json`.
4. Send `build/gdoc-style.json`'s `requests` with `update_doc` as a direct edit (`writeControl` in the file; this is formatting, not text). Then, if the file's `header` is not empty, call `update_doc` with `createHeader` (`type` `DEFAULT`, `sectionBreakLocation` `{index: 0}`), take the returned `headerId`, and add the text with `insertText` at `{segmentId: <headerId>, index: 0}`; do the same for `footer` with `createFooter` and its `footerId`. Page-number fields cannot be added through the connector: tell the user to add them in the doc (Insert > Page numbers) if the Word template has them.
5. Run `rfps-sync-gdoc --set-template <file id>`, which records `gdoc_template` in `solution.toml`. Tell the user the template's link, that it carries no response text, and that `/rfps:build-wip` now copies it. Do not use the template doc itself as the WIP: copy it.

What does not carry over from Word: the Word template's cover design beyond text and tables, tables of contents, content controls, images, and page-number fields. Check the result visually once.
