# Backlog

Deferred or agreed-but-not-built items, so they are not lost. Newest decisions first. Status: **deferred** (parked on purpose), **next** (agreed, not built), **open** (needs a decision).

## Deferred

- **Sample fixture** (built 2026-10-23, see `fixtures/`). Still to do: run it in CI (validate, then `fixtures/smoke.sh`), and extend it with a second amendment, a multi-level template and a staffing workbook.
- **Client permission records** (deferred 2026-10-21). The evidence register's `clearance` column says whether a fact is cleared for State-facing use, but nothing records the proof: who approved, when, how (for example an email), and any conditions such as "redact staff names". If this is picked up later, the likely shape is a few extra register columns (approved by, date, reference) or a small folder of saved approvals, and the FINAL build could require a reference before a row can be `cleared`.
- **Section 9 signature page and the emails** (deferred 2026-10-21): tooling to produce and track the Section 9 signature page, and to draft the submission email (subject with company name and work order number, attachment list), the intent-to-respond acknowledgement, and the questions email. These remain real obligations on any solicitation that requires them (a signature page is typically mandatory; acknowledgements and questions have deadlines) and stay tracked as blocking items in the compliance report; only the tooling is parked.
- **Artifact redaction** (deferred 2026-10-21): tracking redaction per artifact (needs redaction, redacted copy, approved), producing or storing redacted copies, and checking that scrub items (recording passcodes, share links, source-code paths, staff first names, internal navigation trees) are gone before an artifact goes into a packet. For now the scrub notes stay in the evidence register's `notes` column, and redaction is manual. Redacted copies would not be stored in `active-solution`; revisit where they would live if this is picked up.
- **Shared Google Drive edit conflicts** (noted 2026-10-21, not solved). Two people editing `response/` or the register in a shared Drive folder can conflict; Drive keeps versions but does not merge. Noted in `CLAUDE.md`.

- Rate sheet / labor-category rates (2026-10-21): no rate sheet exists yet. Once one does, the staffing plan and Attachment C should reference it. Log only for now; staffing and resources design is being brainstormed.

## Guided experience (user feedback 2026-10-21)

Goal: make building a response feel guided and less overwhelming, not a pile of separate tools.

Built (first pass, 2026-10-21): `tools/flow.toml` and `tools/flow_status.py`; `/rfps-status`, `/rfps-next`, `/rfps-step`, `/rfps-integrate`; the `solution-guide` and `integrate-edits` skills; `progress.md`; change tracking in `.state/integrated.json`; the outside-sources rule and `external-sources.md`. Still to do: a persistent inline checklist view, real-world tuning of the step list and questions, and a requirement-to-heading view if wanted.


- Procedural flow: an explicit ordered list of steps, each backed by a slash command and also reachable in natural language.
- Checklist: an interactive step list the user can check on and off, plus automatic completion where it can be detected from files.
- Status at any time: what is complete versus what needs attention, color coded; drill into a section to see what it still needs.
- Suggestions as questions: after each step the tool asks targeted questions instead of dumping output.
- Expert integration: when the user adds or edits text in `response/`, an expert-proposal-writer pass weaves it into the section cleanly (flow, voice, evidence, requirement coverage), shown for approval.
- Outside content: work from the selected sources by default; ask before looking anywhere else (web or unlisted locations), and log what was added.
- Clickable paths: every file the tools create or change is reported as a link the user can click to open.

## Next (agreed, not built)

- **`/add-past-performance`, remaining parts** (a first version exists, 2026-10-23: local folders, sources.toml, extraction, proposed rows). Still to do: several locations in one call, scanning for new or changed files, a written digest, and the Google Drive connector with a confirmation before any download.
- **Template generation and `/update-template`:** generate a response template docx from the Work Order's response instructions when none exists; `/update-template` compares a new or changed template's headings with `response/`, adds new headings, flags renamed or removed ones, and never deletes text.
- **Google Drive adapter (connector-based):** pull inputs to a local working copy, build locally, push outputs back. Open points: native Google Docs versus `.docx`, the register as a Sheet versus CSV, per-download confirmations.

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
- Retire the `proposal-assembler` skill (superseded by `/rfps-build-final`)?
- Baseline commits: `active-solution` has no commit yet; this repo has uncommitted tool and command changes.
- Regenerate the solicitation summary that was removed with the old ingest skill? (Not needed unless wanted.)
