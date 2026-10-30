# Backlog

Deferred or agreed-but-not-built items, so they are not lost. Newest decisions first. Status: **deferred** (parked on purpose), **next** (agreed, not built), **open** (needs a decision).

## Deferred

- **Sample fixture** (built 2026-10-23, CI added 2026-10-24, see `fixtures/` and `.github/workflows/ci.yml`). Still to do: extend it with a second amendment, a multi-level template and a staffing workbook.
- **Client permission records** (deferred 2026-10-21). The evidence register's `clearance` column says whether a fact is cleared for State-facing use, but nothing records the proof: who approved, when, how (for example an email), and any conditions such as "redact staff names". If this is picked up later, the likely shape is a few extra register columns (approved by, date, reference) or a small folder of saved approvals, and the FINAL build could require a reference before a row can be `cleared`.
- **Section 9 signature page and the emails** (deferred 2026-10-21): tooling to produce and track the Section 9 signature page, and to draft the submission email (subject with company name and work order number, attachment list), the intent-to-respond acknowledgement, and the questions email. These remain real obligations on any solicitation that requires them (a signature page is typically mandatory; acknowledgements and questions have deadlines) and stay tracked as blocking items in the compliance report; only the tooling is parked.
- **Artifact redaction** (deferred 2026-10-21): tracking redaction per artifact (needs redaction, redacted copy, approved), producing or storing redacted copies, and checking that scrub items (recording passcodes, share links, source-code paths, staff first names, internal navigation trees) are gone before an artifact goes into a packet. For now the scrub notes stay in the evidence register's `notes` column, and redaction is manual. Redacted copies would not be stored in `active-solution`; revisit where they would live if this is picked up.
- **Shared Google Drive edit conflicts** (noted 2026-10-21, not solved). Two people editing `response/` or the register in a shared Drive folder can conflict; Drive keeps versions but does not merge. Noted in `skills/solution-guide/references/conventions.md`.

- Rate sheet / labor-category rates (2026-10-21): no rate sheet exists yet. Once one does, the staffing plan and Attachment C should reference it. Log only for now; staffing and resources design is being brainstormed.

## Guided experience (user feedback 2026-10-21)

Goal: make building a response feel guided and less overwhelming, not a pile of separate tools.

Built (first pass, 2026-10-21): `tools/flow.toml` and `tools/flow_status.py`; `/rfps:status`, `/rfps:next`, `/rfps:step`, `/rfps:integrate`; the `solution-guide` and `integrate-edits` skills; `progress.md`; change tracking in `.state/integrated.json`; the outside-sources rule and `external-sources.md`. Still to do: a persistent inline checklist view, real-world tuning of the step list and questions, and a requirement-to-heading view if wanted.


- Procedural flow: an explicit ordered list of steps, each backed by a slash command and also reachable in natural language.
- Checklist: an interactive step list the user can check on and off, plus automatic completion where it can be detected from files.
- Status at any time: what is complete versus what needs attention, color coded; drill into a section to see what it still needs.
- Suggestions as questions: after each step the tool asks targeted questions instead of dumping output.
- Expert integration: when the user adds or edits text in `response/`, an expert-proposal-writer pass weaves it into the section cleanly (flow, voice, evidence, requirement coverage), shown for approval.
- Outside content: work from the selected sources by default; ask before looking anywhere else (web or unlisted locations), and log what was added.
- Clickable paths: every file the tools create or change is reported as a link the user can click to open.

## Next (agreed, not built)

- **Shared WIP document (Google Docs default, Word alternate)** (agreed 2026-10-23). Built and released through 0.3.1: Word route (tracked changes, pull, bookmarks, `--word`), Google route (suggestions, comments ledger, highlights, conflict/evidence/banned-phrase comments, reviewer-comment promotion, locators, waiting-for-people counts), template tooling (`/rfps:generate-template`, `/rfps:update-template`, `/rfps:make-gdoc-template`), all simulator-tested; the create, suggest, word-level edit, paragraph, bullet, pull and insertComment paths were checked live. `tools/sync_core.py` holds the backend-independent planning.
  - Still to do (needs the Docs connector on the right account): live-test the conflict, evidence and banned comments, promotion, tables inserted as suggestions, heading links, and the `?disco=` comment link format (`gdoc_comment_link` adjusts it).
  - Known gaps: a second suggested bullet read back as a plain paragraph on the live doc (2026-10-24: the parser now also reads `suggestedBulletChange`, which is the likely cause; confirm on the next live run); page-number fields, tables of contents, images and content controls cannot be added through the connector; `--update` for the Google template (2026-10-24: re-styles the existing doc in place when only the look changed, new template when headings changed; `--style-plan` now reports page numbers, TOC, content controls and images it cannot carry over); word-level tracked changes inside a modified paragraph on the Word route; no reply or resolve request exists in the connector; eval cases for the Google and Word skills cover routing only (`pull-wip-fires`, `word-route-uses-docx-sync`), not connector calls (that needs `--mocks`); Word has no external deep link to a paragraph (opens the file and copies the search text).
- **`/add-past-performance`** (built 2026-10-23 and 2026-10-24: several locations, `--normalize`, `rfps-scan-sources`, Drive source type with confirmation before any download). Still to do: a written digest.
- **Template generation and `/update-template`** (built 2026-10-24: `/rfps:generate-template`, `/rfps:update-template`). Nothing outstanding.
- **Google Drive adapter (connector-based):** pull inputs to a local working copy, build locally, push outputs back. Open points: native Google Docs versus `.docx`, the register as a Sheet versus CSV, per-download confirmations.

- **Drive-first working model** (raised 2026-10-30 after a real-world run: "perform the work in Drive so all can drive from it"). Today the WIP document, its comments and the template copy live in Drive, while the engine's files (`response/*.md`, the register, reports, `.state/`) are local. Options: (A) Drive as the collaboration surface only, engine local (what exists); (B) a Drive folder mirroring the readable outputs (reports, open items, register as a Sheet) pushed by a sync step so everyone sees them; (C) the engine itself reading and writing Drive files through the connector (the adapter below). Also open: starting from a Google Doc template with no local .docx (headings from `read_doc`); FINAL still needs the real .docx bytes, which the connector only returns as chat base64 unless the app saves them.
  - Decided 2026-10-30: Google Drive for Desktop (Stream mode) for files already in Drive, machine-local cache kept out of Drive, locations asked for with defaults; connector-only engine (option C) not built.

## Brainstormed, not scheduled: submission packet

Everything the State receives, not just the narrative. Suggested order: manifest and readiness report; people register and resumes; Attachment C fill and checks; supporting evidence packet (index; redaction deferred, above); metadata scrub and final gate. (Section 9 and the emails are deferred, above.)

- Packet manifest listing each item with producer, status, owner, due date, checks.
- People register (role, availability, work authorization, background check, degree, computed years, resume version) and a resume-to-requirement matrix with stale-resume flags.
- Attachment C fill from the pricing workbook without altering the form; cross-check milestones, offsets, totals and planning assumptions against the response.
- Supporting evidence packet chosen by register ID, one-line index per artifact (redaction tracking deferred, above); pulled from sources into `11 Final Submission` at assembly time.
- Docx and PDF metadata, comment, tracked-change and hidden-text scrub.
- Dated freeze snapshot under `submissions/` with file hashes.
- Final gate command (page estimate, file names, signatures, Excel and PDF, total size, compliance report), then copy to `11 Final Submission`.

## Open

- Which submission attachments cause the most pain is not yet clear (2026-10-21), so the packet ideas stay unscheduled; revisit after the first packet is assembled by hand.
- Retire the `proposal-assembler` skill (superseded by `/rfps:build-final`)?
- Baseline commits: `active-solution` has no commit yet; this repo has uncommitted tool and command changes.
- Regenerate the solicitation summary that was removed with the old ingest skill? (Not needed unless wanted.)

- Team use on Drive (2026-10-30): built the entry check, join, lease, named claims and the register recheck. Still open: a stronger answer for two people editing the same Markdown at once than the lease and a warning; roster and requirement IDs are only checked for duplicates, not rechecked before writing; a "what changed since I last looked" view that is more than file times.
