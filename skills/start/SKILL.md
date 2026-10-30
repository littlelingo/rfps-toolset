---
name: start
description: Front-loaded start for a new solicitation - ask once for the solicitation folder, template and past-performance locations, then run set-up, analysis, evidence, staffing, drafting, review and the first WIP build, and hand over a ranked worklist of gaps
argument-hint: [source folder] [--word]
disable-model-invocation: true
allowed-tools: Bash(rfps-new-engagement:*), Bash(rfps-decode-b64:*), Bash(rfps-add-source:*), Bash(rfps-scan-sources:*), Bash(rfps-extract-docs:*), Bash(rfps-register-add:*), Bash(rfps-refresh-reports:*), Bash(rfps-open-items:*), Bash(rfps-flow-status:*), Bash(rfps-worklist:*), Bash(rfps-staffing:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Bash(rfps-build-response:*), Bash(ls:*), Read, Write, Edit, Skill, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to every stage below.

Take a new solicitation from the documents to a first work-in-progress (WIP) response in one run, asking only at the start and for what cannot be decided, then hand over a ranked list of what is left. Each stage is an existing skill or tool that also works on its own; this skill only orders them. Where a stage names a typed-only skill (`build-wip`), read its `SKILL.md` under `${CLAUDE_PLUGIN_ROOT}/skills/` and follow it.

## 1. Intake (the only planned questions)

Collect these in one round (use the question tool; skip what `$ARGUMENTS` or the folder already answers):

1. **Source (capture) folder** holding the solicitation: the SOW or Work Order, RFP, amendments, Q&A, attachments. If `active-solution/` already exists there, tell the user and offer `/rfps:next` or `/rfps:walk` instead; never overwrite it.
2. **Response template** .docx (it must be a file on disk; if it is in Drive, follow the Drive paragraph of `new-engagement` - decode a saved download with `rfps-decode-b64`, never retype it, or ask the user to download it): use the one in the draft-response folder, or, if there is none, plan to run `generate-template` in stage 1 (its section outline still needs the user's approval).
3. **Past-performance locations**: local folders and/or a Google Drive folder, one or several, or "none yet". Material is read in place; nothing is copied or downloaded without the confirmation `add-past-performance` asks for.
4. **Where the team works on the WIP**: Google Docs (default) or Word (`--word`), and the Drive folder (or local folder) it should be created and kept in.

Then say in two lines what will happen and that you will only stop for a fact you cannot get from the documents, a clearance, or a choice that is the user's.

## 2. Run (no stops between stages)

The path is the flow defined in `${CLAUDE_PLUGIN_ROOT}/tools/flow.toml`, not a second copy of it. Run `rfps-flow-status --json` and work through its steps in order, up to and including `wip`. For each step that is not done, run its `command` (a skill, or the tool the step names); run the skills named below with the intake answers as their inputs. After each step give one line with links to what was written, then re-run `rfps-flow-status` and carry on. Steps already done are left alone, so `/rfps:start` can be run again to resume.

Do not run these steps; they depend on people and become worklist items instead: `amendments` (unless the analyzer found some to log), `cleared`, `markers`, `integrated`, `attachments`, `docreview`, `final`.

Rules that differ from running the skills one by one:

- `solution`/`template`: if there is no template, run `generate-template` first. Register each past-performance location with `rfps-add-source`, then `rfps-scan-sources` (Drive files need the confirmation step in `add-past-performance`).
- `register`: follow `add-past-performance` to propose rows and add them with `rfps-register-add` as `hold`; never mark a row `cleared` (that is the user's call and the client's permission). Unusable material goes to the user as a note, not into the register.
- `resources`: leave names the documents do not give as placeholders.
- `draft`: every claim is `[GROUNDED: E-nnn]`, `[ASSERTION]`, or a `[DECISION]`, `[OPEN]` or `[EVIDENCE NEEDED]` marker; invent nothing about the bidder. Run `rfps-open-items --mark` afterwards.
- `compliance`: finish with `rfps-refresh-reports`.
- `wip`: follow `build-wip` (Google Doc by default, Word for `--word`). Never run `build-final`.

If a step fails, stop there, say what failed and how to resume, and do not hide the failure behind later steps.

## 3. Hand over

1. Run `rfps-worklist`; report the counts by kind and how many are blockers.
2. Give a short honest summary: what exists now (WIP link, brief, matrix, register rows by clearance), what is thin or unsupported, and what the tools could not decide.
3. Ask one question: walk the worklist now with `/rfps:walk`, or stop here.
