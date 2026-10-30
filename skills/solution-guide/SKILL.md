---
name: solution-guide
description: Guides a proposal response from start to finish and answers "where are we", "what's next", "what's left", "what does section X need", "show the checklist", "mark X done". Reports color-coded status, suggests the next step as a question, and makes the individual tools easy to use on their own. Use for status, next-step, or checklist requests in natural language.
---

# Solution guide

The flow is a path, not a requirement. Every step is also a skill or command a user can run alone. The guide only keeps track, makes the state visible, and asks what to do next.

## What to do
- Status or "where are we": run `rfps-flow-status --table` (add `--sections` for every heading, `--detail <step id or heading text>` for one item). Show the progress line, the next three items, then the groups, with 🟢 done, 🟠 needs attention, 🔴 blocking, ⚪ not started, 🔵 skipped / not applicable. Use `--table` for the default view (progress line, a Next up table, an All steps table by group); it needs no widget. Draw the inline visual from `--json` only when the user asks and the visual tools are available.
- "What's next": follow `/rfps:next`: explain the top item briefly, ask its question, and act only after the answer.
- "Where do I begin" for a new solicitation with no `active-solution/`, or "what is left to fix" once a WIP exists: point to `/rfps:start` (typed-only; it runs the whole path from the documents to a first WIP) or `/rfps:walk` (typed-only; works the ranked worklist one item at a time). Tell the user to type the command.
- "Someone else already started this" / "how do I jump in": point to `/rfps:start` (typed-only). It checks the folder first: with an existing solution it joins it (setting up this machine, showing who is doing what, claiming work), otherwise it starts a new one.
- "Mark X done / skip X": `rfps-flow-status --set <id> done|skip|reset` (the checkbox lives in progress.md).
- "What does <section> need": `--detail "<section text>"` and explain what is missing and who can supply it.
- User edits to the response: use the integrate-edits skill.
- "What's left to resolve" or the `markers` step: point to `open-items.md` in the solution folder (every `[DECISION]`, `[OPEN]`, `[EVIDENCE NEEDED]` and `[ASSERTION]` in one table with a link to each line, decisions first). If response files were edited by hand and the icons are missing, run `rfps-open-items --mark`.

## How to talk to the user
- Keep the response short and procedural. Lead with the one thing to do; show detail only when asked. Ask questions, offer a recommended option, and always allow "skip for now".
- After creating or changing a file, link it so the user can click it, using a path relative to the session working directory when possible. Link progress.md whenever you show status.

## Sources and outside content
- Work from the sources the user selected: the solicitation folder, the listed past-performance locations, and the files in the solution. Do not search the web, open unlisted folders or drives, or pull material from other places unless the user says yes to that specific request. When it would help, ask: say what you would look for and why, and offer to proceed. Record anything approved and added in `external-sources.md` (date, what, why, approved by).

## Individual use
Say which command or skill each recommendation uses (for example /rfps:collateral-analyzer, /rfps:requirements-mapper, /rfps:refresh-reports, /rfps:build-wip). A user who knows the tools can skip the guide entirely.
