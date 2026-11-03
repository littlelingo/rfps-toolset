---
name: start
description: The one entry point - joins the solution if one already exists in the folder, otherwise starts a new solicitation: ask once for the solicitation folder, template and past-performance locations, then run set-up, analysis, evidence, staffing, drafting, review and the first WIP build, and hand over a ranked worklist of gaps
argument-hint: [source folder] [--type rfp|rfi] [--word]
disable-model-invocation: true
allowed-tools: Bash(rfps-new-engagement:*), Bash(rfps-collab:*), Bash(rfps-detect-type:*), Bash(rfps-set-config:*), Bash(rfps-decode-b64:*), Bash(rfps-add-source:*), Bash(rfps-scan-sources:*), Bash(rfps-extract-docs:*), Bash(rfps-register-add:*), Bash(rfps-refresh-reports:*), Bash(rfps-open-items:*), Bash(rfps-flow-status:*), Bash(rfps-worklist:*), Bash(rfps-staffing:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Bash(rfps-build-response:*), Bash(rfps-sweep:*), Bash(rfps-lint:*), Bash(rfps-crossref:*), Bash(rfps-consistency:*), Bash(ls:*), Read, Write, Edit, Skill, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to every stage below.

Take a new solicitation from the documents to a first work-in-progress (WIP) response in one run, asking only at the start and for what cannot be decided, then hand over a ranked list of what is left. Each stage is an existing skill or tool that also works on its own; this skill only orders them. Where a stage names a typed-only skill (`build-wip`), read its `SKILL.md` under `${CLAUDE_PLUGIN_ROOT}/skills/` and follow it.

## 0. Entry check (new solution or an existing one)

First follow `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/entry.md` with `$ARGUMENTS`' folder. If a solution already exists there, that file's join path replaces everything below: stop after it. Only when it reports `none` continue with the intake.

## 1. Intake (the only planned questions)

Collect these in one round (use the question tool; skip what `$ARGUMENTS` or the folder already answers):

1. **Source (capture) folder** holding the solicitation: the SOW or Work Order, RFP, amendments, Q&A, attachments. The entry check above has already confirmed no solution exists there.
2. **Response template** .docx. Order of preference: the form the agency issued (a docx in the draft-response folder), else the user's standard template for the type (`rfps-standard-template --type <rfi|rfp> --show`; `rfps-new-engagement` copies it into the draft-response folder by itself when that folder has none), else `generate-template`. Say which one applies in one line and ask only if the user wants a different one. (The file must be on disk; if it is in Drive, follow the Drive paragraph of `new-engagement` - decode a saved download with `rfps-decode-b64`, never retype it, or ask the user to download it): use the one in the draft-response folder, or, if there is none, plan to run `generate-template` in stage 1 (its section outline still needs the user's approval).
3. **Past-performance locations**: local folders and/or a Google Drive folder, one or several, or "none yet". Material is read in place; nothing is copied or downloaded without the confirmation `add-past-performance` asks for.
4. **Type of solicitation**: RFP (a bid) or RFI (a request for information: non-binding, no award). Decide it in this order, and ask only at step c:
   a. **Named.** `--type` in `$ARGUMENTS`, or the user typed `/rfps:start-rfi` or `/rfps:start-rfp`: use it, no detection, no question.
   b. **Read from the notice.** Run `rfps-detect-type "<source folder>"`. `rfi` or `rfp` means the title and disclaimer of the solicitation say so (a draft PWS full of "shall" does not make an RFI a bid). Tell the user in one line, with the phrase that decided it, for example "This reads as an RFI (sources sought; no proposals are being requested). Proceeding as RFI - say so if that is wrong."
   c. **Unclear** (or no documents yet): ask once with the question tool, RFP first as the default.
   For an RFI pass `--type rfi` to `rfps-new-engagement`; the staffing and attachment steps then become optional and hidden, and `resources` is not run in stage 2 unless the RFI asks for staffing or pricing. An existing solution keeps its recorded type; the join path never asks.
5. **Where the team works on the WIP**: Google Docs (default) or Word (`--word`).
6. **Where the outputs go**: the folder for the shared WIP (a Drive folder link, or a local folder for Word) and the folder for the FINAL copy. Ask; if the user gives none, the defaults are the capture's `05 Draft Response` (never the Drive root) and `11 Final Submission`. Record only an answer the user actually gave, with `rfps-set-config wip_folder|wip_docx|final_copy_dir <value>` (`wip_docx` is a full file path for the Word file, `wip_folder` a Drive folder). When the user takes the defaults, run nothing: the tools already use them, and a wrong value written here puts files in the wrong place.
7. **Machine-local working files**: if the capture folder is on a Google Drive mount, ask for a folder on this machine for text caches and scratch builds (suggest `~/rfps-cache`) and record it with `rfps-set-config cache_dir <path>` so they are never synced to Drive.

Then say in two lines what will happen and that you will only stop for a fact you cannot get from the documents, a clearance, or a choice that is the user's.

## 2. Run (no stops between stages)

The path is the flow defined in `${CLAUDE_PLUGIN_ROOT}/tools/flow.toml`, not a second copy of it. Run `rfps-flow-status --json` and work through its steps in order, up to and including `wip`. For each step that is not done, run its `command` (a skill, or the tool the step names); run the skills named below with the intake answers as their inputs. After each step give one line with links to what was written, then re-run `rfps-flow-status` and carry on. Steps already done are left alone, so `/rfps:start` can be run again to resume.

Optional steps (`bid`, `questions`, `strategy`, `evalsim`, `debrief`) are marked `optional` in the flow and are not counted in the progress bar. Run `bid`, `questions` and `strategy` in proposal mode as below; skip `debrief` and `evalsim`. Do not run these steps; they depend on people and become worklist items instead: `amendments` (unless the analyzer found some to log), `debrief`, `cleared`, `markers`, `integrated`, `attachments`, `docreview`, `final`.

Rules that differ from running the skills one by one:

- `solution`/`template`: if there is no template, run `generate-template` first. Register each past-performance location with `rfps-add-source`, then `rfps-scan-sources` (Drive files need the confirmation step in `add-past-performance`).
- `register`: follow `add-past-performance` to propose rows and add them with `rfps-register-add` as `hold`; never mark a row `cleared` (that is the user's call and the client's permission). Unusable material goes to the user as a note, not into the register.
- `resources`: for an RFI it is optional; skip it unless the RFI asks for staffing, roles or pricing. Otherwise leave names the documents do not give as placeholders.
- `draft`: every claim is `[GROUNDED: E-nnn]`, `[ASSERTION]`, or a `[DECISION]`, `[OPEN]` or `[EVIDENCE NEEDED]` marker; invent nothing about the bidder. Run `rfps-open-items --mark` afterwards.
- `questions`: follow `questions` in proposal mode. Draft questions from the gaps, ambiguities and conflicts the analysis found, as Draft rows; send nothing and ask nothing. The hand-over asks which to keep and send.
- `bid`: follow `capture` in proposal mode. Write a proposed bid view from the brief and the gaps and leave Decision as Undecided; the decision is the user's and is asked in the hand-over.
- `strategy`: follow `win-strategy` in proposal mode. Candidate themes come from the cleared register rows and the strongest requirements; they are written marked "(proposed)" and wait for the user's approval.
- `evalsim`: do not run it here. It costs a model run and reads best on a draft that people have worked on. Mention in the hand-over that a second-reader score is available (`/rfps:evaluator-simulator`, or just ask).
- `compliance`: finish with `rfps-refresh-reports`.
- `wip`: follow `build-wip` (Google Doc by default, Word for `--word`). Never run `build-final`.

If a step fails, stop there, say what failed and how to resume, and do not hide the failure behind later steps.

## 3. Hand over

Keep this to one short message. The user should be able to read it in under a minute and answer in one line.

1. Run `rfps-worklist`; give the counts by kind and how many are blockers, in one sentence.
2. In three or four lines say what exists now (WIP link, brief, matrix, register rows by clearance), what is thin or unsupported, and what the tools could not decide.
3. **Drafts to react to, in one block:** "I also drafted a bid view (it says <Go or No-go, in a few words> and leaves the decision to you), <N> draft questions for the agency (due <date>), and <N> candidate win themes (each marked proposed)." Link the three files. Then: "Say *accept* to keep all three as drafted, or name any you want changed." Do not walk through them unless asked. A second-reader score of the draft is available on request.
4. Ask one question: walk the worklist now with `/rfps:walk`, or stop here.
