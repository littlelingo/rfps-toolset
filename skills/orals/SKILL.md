---
name: orals
description: >
  Prepare for an oral presentation, demonstration or Q&A with the evaluators when the solicitation calls for one -
  likely questions drawn from the weak factors and gaps, an outline mapped to the evaluation factors with timings,
  and a rehearsal checklist - in orals-prep.md. Trigger when the user asks to "prepare for orals", "the
  presentation to the evaluators", "likely questions from the panel", "demo script", or "best and final".
argument-hint: "[length in minutes, or the format the agency set]"
allowed-tools: Bash(rfps-sweep:*), Bash(rfps-refresh-reports:*), Bash(rfps-collab:*), Read, Edit, Write, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules apply to this skill.

Only worth doing when the solicitation requires or invites oral presentations, a demonstration, or a question session. Check first: read the solicitation text (run `/rfps:extract` if there is none) for oral, presentation, demonstration, interview, or panel wording, and quote what it says about format, length, who may attend, and what may be shown. If it says nothing, tell the user and stop unless they want practice questions anyway.

1. Open `orals-prep.md` in the solution folder (create it if missing, titled "Orals Preparation"). Put the solicitation's own rules at the top, quoted, with the clause number: length, order, attendees, materials, whether Key Personnel must present, and what is scored.
2. **Outline.** Map the presentation to the evaluation factors in the agency's order and weight (from `win-strategy.md`; if missing, from the solicitation). For each: the one message (the win theme and its key phrase), the proof to show (register IDs; cleared evidence only), the exhibit, the speaker, and the minutes. The total must fit the time the agency set. Lead with the agency's problem, not the company.
3. **Likely questions.** Draw them from the second reader's weakest factors (`evaluation-sim.md`), the Gap and Assertable requirements, the open `[DECISION]` and `[OPEN]` markers, the risks, and any figure the agency's answers changed. For each: the question as an evaluator would ask it, the honest answer using only the response and the register, the proof to point to, and who answers. Where there is no honest answer yet, write "no answer yet" and add it to the worklist rather than inventing one.
4. **Rehearsal checklist.** Timed run-through, a run with someone playing a hostile evaluator, handling a question you cannot answer (say so and follow up in writing), technology and backup, Key Personnel present and prepared on their own sections, nothing in the slides that is not in the submitted response unless the agency invited it.
5. Everything must agree with the submitted response. If a rehearsal answer differs from the response, the response wins unless the user decides to change it.

Link `orals-prep.md`. Do not invent facts, clients or numbers; use markers where a fact is missing.
