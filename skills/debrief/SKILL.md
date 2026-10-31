---
name: debrief
description: >
  Capture what the bid taught after the decision or the agency's debriefing - outcome, the agency's feedback in
  its own words, how the scores compared with the second reader's, which themes worked, and what is reusable
  (evidence rows, themes, questions that worked, process fixes) proposed for approval - in debrief.md. Trigger
  when the user says "we won", "we lost", "debrief", "lessons learned", "what did the agency say", or "post-mortem".
argument-hint: "[outcome, or the debrief notes to record]"
allowed-tools: Bash(rfps-collab:*), Bash(rfps-register-add:*), Bash(rfps-flow-status:*), Bash(rfps-refresh-reports:*), Read, Edit, Write, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules apply to this skill.

Each bid should make the next one better. This writes down what happened while it is fresh, and turns it into things the next bid can reuse. It proposes; the user approves anything that goes into the register or a template.

1. Open `debrief.md` in the solution folder (create it if missing, titled "Debrief and Lessons"). Read `capture.md`, `win-strategy.md`, `evaluation-sim.md`, `questions.md` and the compliance report for context.
2. **Outcome and feedback.** Ask for the outcome (award, no award, withdrawn, pending) and any debriefing the agency gave: scores or ratings per factor, strengths, weaknesses, deficiencies, price position, who won. Record the agency's words quoted and dated, with the source (a letter, a call). Do not paraphrase a score into something kinder.
3. **Compare with the second reader.** Put the agency's ratings beside `evaluation-sim.md` for each factor. Where they differ by a full step or more, say what the simulator missed or over-rated; that is how the second reader gets better.
4. **What worked and what did not.** For each win theme: did the agency's feedback mention it? For each section: the strongest and the weakest, with the evidence. Which questions to the agency changed anything? Which checks (sweep, consistency, lint, final gate) caught something real, and which noise annoyed? Which step cost the most time?
5. **Reusable, as proposals only.** (a) Evidence: engagements, results or a new reference worth adding to the register, to be proposed through `/rfps:add-past-performance`, never added on your own. (b) Themes and discriminators that proved out or failed. (c) Text blocks that scored well, named by section, to start from next time. (d) Questions to ask the agency that worked. (e) Process and tool fixes, each as one line the owner of this toolset can act on. If the outcome is a win, add the delivery commitments that must be kept (they become the next bid's past performance).
6. Show the proposals and ask which to keep. Mark the flow step done only when the user says so (`rfps-flow-status --set debrief done`).

Link `debrief.md`. Quote, do not embellish; this file is a record.
