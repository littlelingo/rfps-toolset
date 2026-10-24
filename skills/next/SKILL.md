---
name: next
description: Guide the next step: pick the most useful open item, ask what is needed, then do it with the user's answers
argument-hint: [step id to focus on]
disable-model-invocation: true
allowed-tools: Bash(rfps-flow-status:*), Bash(rfps-open-items:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Help the user take the next step without having to decide what it is.

1. Run `rfps-flow-status` (or `--detail "$ARGUMENTS"` if a step or heading was given). Take the top item from "Next up" (blocking first).
2. Explain in two or three sentences what it is, why it matters, and what is missing, in plain language.
3. Ask the item's question (the `ask` field, adapted to the facts you now know). When the answer is a choice, use the question tool with two to four options and a recommended one first; when it needs free text, ask in prose. Offer "skip for now" and "mark not applicable" as options.
4. Only after the answer, do the work: run the step's command or skill, or make the edit, and report with links to what changed. If the answer is "skip", run `rfps-flow-status --set <id> skip`.
5. Finish by showing the one-line progress and the next item as a question, never a list.

When the top item is the `markers` step, open the solution's `open-items.md` (run `rfps-open-items` first) and work through its table from the top, one marker at a time; if the response files lack the colored icons, tell the user `rfps-open-items --mark` adds them.

Never look outside the selected sources (web, unlisted folders, other drives) without asking first; see CLAUDE.md. Each step stays usable on its own, outside this guided path.
