---
name: start
description: Front-loaded start for a new solicitation - ask once for the solicitation folder, template and past-performance locations, then run set-up, analysis, evidence, staffing, drafting, review and the first WIP build, and hand over a ranked worklist of gaps
argument-hint: [source folder] [--word]
disable-model-invocation: true
allowed-tools: Bash(rfps-new-engagement:*), Bash(rfps-add-source:*), Bash(rfps-scan-sources:*), Bash(rfps-extract-docs:*), Bash(rfps-register-add:*), Bash(rfps-refresh-reports:*), Bash(rfps-open-items:*), Bash(rfps-flow-status:*), Bash(rfps-worklist:*), Bash(rfps-staffing:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Bash(rfps-build-response:*), Bash(ls:*), Read, Write, Edit, Skill, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to every stage below.

Take a new solicitation from the documents to a first work-in-progress (WIP) response in one run, asking only at the start and for what cannot be decided, then hand over a ranked list of what is left. Each stage is an existing skill or tool that also works on its own; this skill only orders them. Where a stage names a typed-only skill (`build-wip`), read its `SKILL.md` under `${CLAUDE_PLUGIN_ROOT}/skills/` and follow it.

## 1. Intake (the only planned questions)

Collect these in one round (use the question tool; skip what `$ARGUMENTS` or the folder already answers):

1. **Source (capture) folder** holding the solicitation: the SOW or Work Order, RFP, amendments, Q&A, attachments. If `active-solution/` already exists there, tell the user and offer `/rfps:next` or `/rfps:walk` instead; never overwrite it.
2. **Response template** .docx: use the one in the draft-response folder, or, if there is none, plan to run `generate-template` in stage 1 (its section outline still needs the user's approval).
3. **Past-performance locations**: local folders and/or a Google Drive folder, one or several, or "none yet". Material is read in place; nothing is copied or downloaded without the confirmation `add-past-performance` asks for.
4. **Where the team works on the WIP**: Google Docs (default) or Word (`--word`).

Then say in two lines what will happen and that you will only stop for a fact you cannot get from the documents, a clearance, or a choice that is the user's.

## 2. Run (no stops between stages)

Work in this order. After each stage give one line with links to what was written, and carry on.

1. **Set up.** Follow `new-engagement` (`rfps-new-engagement`); run `generate-template` first if there is no template. Register each past-performance location with `rfps-add-source`, then `rfps-scan-sources` (extract text with `rfps-extract-docs`; Drive files need the confirmation step in `add-past-performance`).
2. **Understand.** Run `collateral-analyzer` (brief, gap report, amendment log), then `requirements-mapper` (coverage matrix).
3. **Evidence.** Follow `add-past-performance` to propose register rows from the scanned material. Add them with `rfps-register-add` as `hold`; never mark any row `cleared` (that is the user's call, and permissions are the client's). Rows that look unusable go to the worklist as notes, not into the register.
4. **People.** Run `resource-planner` for the roster, `resource-plan.md` and the staffing workbook. Leave names the documents do not give as placeholders.
5. **Draft.** Run `section-drafter` for every heading. Every claim is `[GROUNDED: E-nnn]`, `[ASSERTION]`, or a `[DECISION]`, `[OPEN]` or `[EVIDENCE NEEDED]` marker; invent nothing about the bidder. Then `rfps-open-items --mark`.
6. **Review.** Run `empathy-reviewer` and `compliance-validator`, then `rfps-refresh-reports`.
7. **WIP.** Follow `build-wip` (Google Doc by default, Word for `--word`); it makes the shared document and pushes the drafted text as suggestions or tracked changes. Do not run `build-final`.

If a stage fails, stop at that stage, say what failed and how to resume (`/rfps:status`), and do not hide the failure behind later stages.

## 3. Hand over

1. Run `rfps-worklist`; report the counts by kind, how many are blockers, and link `worklist.md`.
2. Give a short honest summary: what exists now (WIP link, brief, matrix, register rows by clearance), what is thin or unsupported, and what the tools could not decide.
3. Ask one question: walk the worklist now with `/rfps:walk`, or stop here.
