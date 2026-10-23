# Changelog

## Unreleased

- **Google Docs is now the default shared WIP document** (`wip_format = "gdoc"`; `--word` or `wip_format = "docx"` keeps the Word route). `rfps-sync-gdoc` plans everything and Claude reads and writes the doc through the Google connectors: `--html` builds the first version for Drive `create_file`, `--init` records it, `--push` writes the `update_doc` requests as *suggestions* (only the changed words, bullets and tables inserted in place, highest index first, guarded by the revision), `--commit` records the sync, `--pull` lists edits others made (and `--comments` writes their comments to `review/doc-comments.md`). Open items link to the Google Docs heading. Tested against a simulated Docs API (`fixtures/gdoc_sim.py`, `fixtures/gdoc_test.py`) and once against live Google (2026-10-23): Drive converted the generated HTML cleanly; `update_doc` accepted `writeMode: SUGGEST` and the word edits, new bullet and new paragraph came back as real suggestions that parse back as in sync; a direct edit was pulled into the response. Not yet live-tested: comments (the connector has no way to create one and none were present), tables inserted as suggestions, the optional Subtitle styling. Google's `read_doc` returned no `headingId` for the converted headings, so open items link to the doc with the text to search for, not to the heading.
- `/rfps:pull-docx` is now `/rfps:pull-wip` and handles both routes.
- Shared WIP docx: `/rfps:build-wip` now creates one WIP docx in `05 Draft Response` and updates it in place with `rfps-sync-docx`. Approved response changes go in as tracked changes (author "rfps"), only for paragraphs whose text changed, so other people's comments and edits are kept; a response change that touches text someone edited in the document is reported and left pending. `--status` shows drift, `--dry-run` previews, `--rebuild` regenerates (with a backup). `rfps-build-response --mode wip` remains the stateless regeneration into `build/`.
- `/rfps:pull-wip` (`rfps-sync-docx --pull`): lists edits others made in the shared WIP docx that the response lacks (changed words, new and deleted paragraphs, tables, removed markers) and writes their comments to `review/doc-comments.md`; after approval `--pull --apply` writes them into `response/*.md`, keeping bold and tags on unchanged words. Changes both sides touched are reported as conflicts. The flow's WIP step now shows whether the document or the response is ahead.
- Locators: open items (`open-items.md`, the status page and the pane) link to the shared WIP docx section and show the marker text to search for, once the document exists (`open_in = "docx"|"md"` in `solution.toml` overrides). `rfps-sync-docx` adds an invisible bookmark to every heading, including in existing documents. `rfps-open-doc` opens the document and copies the search text; Word cannot be driven to an exact spot from outside, so use its Navigation Pane for the heading.
- `tools/sync_core.py` plans changes from block texts, separate from the docx backend, so a Google Docs backend can be added later.
- `/rfps:build-final` checks for edits made in the shared document before building.

## 0.1.1 (2026-10-23)

- Added `fixtures/`: a fictional sample solicitation, a seed response and register, `smoke.sh` (tools end to end, no model calls) and `trial.sh` (runs the analysis and drafting skills with Claude on a throwaway copy).
- Added `/rfps:add-past-performance` and the `rfps-add-source` tool. Past-performance sources inside the capture folder are stored relative to `active-solution/`; `rfps-add-source --normalize` migrates older absolute entries.
- Collateral analyzer now extracts Word, Excel, PowerPoint and PDF files with `rfps-extract-docs` first, logs amendments and Q&A in `amendments/log.md`, and offers to record past-performance sources. The requirements mapper fills in the affected requirement IDs.
- `/rfps:extract` defaults its output to `<solution>/.state/text/` (git-ignored).
- The page estimate reads "about 3 pages" when the low and high estimates are the same number.
- Removed machine-specific `uv` paths from the status pane.

## 0.1.0

- Initial plugin packaging of the RFP toolset: skills (commands converted, `/rfps:` namespace), `rfps-*` tools on PATH, status pane mod, MIT license.
