# Backlog

What is agreed but not built, parked, or waiting on a decision, so it is not lost. Built work lives in [CHANGELOG.md](CHANGELOG.md); the phased plan and its status in [docs/MASTER-PLAN.md](docs/MASTER-PLAN.md) (phases 0 to 5 built except item 3.0). Reviewed against the repo on 2026-11-10 (v0.8.0).

Status: **next** (agreed, not built), **verify** (built, needs a live check), **deferred** (parked on purpose), **open** (needs a decision).

## Next (agreed, not built)

- **Google FINAL route** (master plan item 3.0). Fill a clean copy of the Google master with direct edits, remove the scaffold lines, export to PDF through the Drive connector, run `rfps-final-gate`. The PDF export and gate were verified live on 2026-10-30; filling the copy and removing scaffold lines were not. Until then `build-final` documents the manual route (open `_FINAL.docx` in Google Docs, download as PDF).
- **RFP standard template.** `rfps-standard-template` handles RFI only; define the RFP outline (`tools/templates/outlines/rfp.json`) and `--make-plain` for it.
- **RFI profile, second pass** (listed as not built in 0.8.0): RFI section templates, a commitment-language lint (binding words in a non-binding response), a proprietary legend check, a response-deadline countdown, and an RFI fixture for `smoke.sh`.
- **`whitepaper` style profile** beside `formal` and `proposal` in `tools/templates/styles/`.
- **Sample fixture, extended:** a second amendment, a multi-level template (Heading 2 and below) and a staffing workbook.

## Verify (built, needs a live run)

- **Interactive `/rfps:start` on a real bid,** end to end through the first WIP and hand-over.
- **Status pane** (`hooks/`) in Claude Desktop.
- **Google Docs connector paths** (needs the connector on the account that owns the docs): conflict, evidence and banned-phrase comments; reviewer-comment promotion; tables inserted as suggestions; heading links; the `?disco=` comment link format (`gdoc_comment_link` adjusts it); a second suggested bullet reading back as a plain paragraph (the parser now reads `suggestedBulletChange`, the likely cause).
- **Evals.** First full baseline 2026-11-10: 26 cases, mean delta +0.63, about $19. Six cases score the same with and without the plugin (`draft-does-not-invent-facts`, both mapper-recall cases, `start-intake-before-running`, `unrelated-request-stays-quiet`, `word-route-uses-docx-sync`), so they guard regressions but do not show the plugin's value; consider harder versions. `validator-catches-planted-failures` and `template-outline-cites-the-rfp` each had one judge-split failure on output that met the grader; watch for flakiness. Google and Word skill evals cover routing only, not connector calls (that needs `--mocks`).

## Known limits (accepted for now)

- The Google connector cannot add page-number fields, tables of contents, images or content controls, and has no reply or resolve request for comments.
- Word has no external deep link to a paragraph (`rfps-open-doc` opens the file and copies the search text); word-level tracked changes inside a modified paragraph are not produced.
- FINAL needs real .docx bytes; without Drive for Desktop the connector returns them as chat base64 (`rfps-decode-b64`).

## Deferred

- **Artifact redaction** (2026-10-21): tracking redaction per artifact (needs redaction, redacted copy, approved), storing redacted copies outside `03 Solution`, and checking scrub items (recording passcodes, share links, source-code paths, staff first names, internal navigation trees) are gone. For now scrub notes stay in the register's `notes` column and redaction is manual.
- **Signature page content.** `submission.md` and `/rfps:submission` track mandatory forms, signatures and deadlines and draft the emails; the signature page itself is not produced or checked.
- **Connector-only engine** (Drive-first option C, 2026-10-30): the engine reading and writing Drive files through the connector instead of local files. Decided instead: Drive for Desktop in Stream mode, a machine-local cache, locations asked for with defaults.

## Brainstormed, not scheduled: submission packet

Built since: the final gate on the PDF (with `--scrub`), the submission checklist, the rate sheet check and register approval columns. Still only ideas, to revisit after a packet is assembled by hand and the painful parts are known:

- A packet manifest listing every item with producer, status, owner, due date and checks.
- A people register (availability, work authorization, background check, degree, computed years, resume version) and a resume-to-requirement matrix with stale-resume flags.
- Filling the price form (Attachment C) from the staffing workbook without altering it, cross-checked against the response's milestones and totals.
- An evidence packet chosen by register ID with a one-line index per artifact, pulled into `11 Final Submission` at assembly time.
- Metadata, comment, tracked-change and hidden-text scrub on the .docx and .xlsx attachments (the PDF scrub exists).
- A dated freeze snapshot under `submissions/` with file hashes.

## Open (needs a decision)

- **Generic plugin, branded profiles.** The plugin is meant to hold nothing bidder-specific, yet `tools/templates/styles/formal.toml` and `proposal.toml` are Fearless-branded. Option: ship one neutral profile and keep branded profiles per user (as standard templates already are, in `~/.config/rfps`).
- **Team editing on Drive.** Built: the entry check, join path, lease, named claims and register recheck. Still open: something stronger than the lease and a warning for two people editing the same Markdown at once; recheck roster and requirement IDs before writing (today only duplicates are reported); a "what changed since I last looked" view that is more than file times.
- **Guided experience leftovers.** A persistent inline checklist in the chat (the status pane and `/rfps:status` cover most of it) and a requirement-to-heading view (`rfps-crossref` covers requirement to section).
