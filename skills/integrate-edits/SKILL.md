---
name: integrate-edits
description: When the user adds or edits text in the response files (or says "add this to <section>", "work this in", "clean this up", "integrate my edits"), review it as an expert proposal writer and weave it into its section so it reads as one cohesive, professional voice. Shows a before and after for approval and records the section as integrated.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

# Integrate user-added or edited text

The user's text is the source of the facts. Your job is to make the section read as if one expert wrote it, without changing what the user said.

## Find what changed
- Run `rfps-flow-status --changed` to list sections whose text differs from the last integrated version, with diffs. A section with no earlier version is entirely new.
- If the user pasted text and named a section, locate the heading (headings in `response/*.md` mirror the template docx; never rename, add, or remove one) and treat the pasted text as the new material.

## For each section, one at a time
1. Read the whole section, not just the change. Read the register rows for every `[GROUNDED: E-nnn]` it cites, the requirement rows that this section answers (coverage matrix) and the solicitation wording for them, the vocabulary and tone notes in `brief.md`, and the page budget.
2. Act as an expert proposal writer:
   - Keep every fact, number, name, and claim the user wrote exactly. Do not invent facts, outcomes, clients, or metrics.
   - Put the new content where it belongs logically, reorder if that makes the argument stronger, merge duplication, fix transitions, and match the section's voice and the client's vocabulary.
   - Open with the client's need, give specific evidence before the claim, use active voice with a named actor, and cut superlatives and filler. Do not grow the section unless the addition needs the space.
   - Keep `[GROUNDED]`, `[ASSERTION]`, `[DECISION]`, and `[EVIDENCE NEEDED]` notes attached to the claims they belong to, and never reword wording listed in a register `ban_phrases`.
   - Use hyphens, not em-dashes.
3. Check the result against what the section must answer. If the new text introduces a claim with no evidence, do not hide it: ask whether to add a register row, tag it `[ASSERTION: ...]`, or mark `[EVIDENCE NEEDED: ...]`.
4. Show the user a before and after of the changed paragraphs (not the whole section), three short bullets on what you changed and why, and any questions. Ask with the question tool: apply, apply with changes, or skip. After the first section offer "apply to the remaining sections the same way" if the edits are routine.

## Apply
- On approval, write only that heading's block in the response file, then run `rfps-flow-status --baseline "<heading>"` to record it as integrated, and offer `/rfps:build-wip`.
- If the written block carries any `[ASSERTION]`, `[DECISION]`, `[OPEN]` or `[EVIDENCE NEEDED]` marker, run `rfps-open-items --mark` so each gets its colored icon and `open-items.md` stays current. Write markers in bracket form only; keep an existing icon with its marker when you reword around it.
- Link the changed files for the user, using paths relative to the session working directory when possible.

## Rules
- Never integrate silently, and never change headings.
- Stay inside the selected sources. Do not search the web or read unlisted locations to enrich the text without asking first and logging the addition in `external-sources.md`.
- This skill works on its own: `/rfps:integrate` and natural requests like "work this in" both reach it, with or without the guided flow.
