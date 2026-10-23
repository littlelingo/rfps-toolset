---
name: status
description: Show where the solution is in the flow (color-coded steps and sections), or drill into one step or section
argument-hint: [sections | step id | part of a heading]
allowed-tools: Bash(rfps-flow-status:*), Read
---

Show the current state of the active solution.

1. Run `rfps-flow-status --table` for the overview (it also refreshes progress.md). If `$ARGUMENTS` is `sections`, run `--sections` instead; if it is anything else, run `--detail "$ARGUMENTS"` (a step id such as `markers`, or part of a heading such as `migration`).
2. Present the result as the tool prints it, without reformatting: the progress line and bar, the Next up table, then the All steps table. Keep the colors the tool uses: 🟢 done, 🟠 needs attention, 🔴 blocking, ⚪ not started, 🔵 skipped / not applicable. This table view is the default because it needs no widget and always renders. Draw the inline visual widget (from `--json`) only when the user asks for it and the visual tools are available; its items send `/rfps:status <step id>` when clicked.
3. Link the files: [progress.md](progress.md) is the checklist the user can tick; link any file you mention using a path relative to the session working directory when it is inside it.
4. End with one or two questions from the `ask` fields (what is open and what the user wants to do about it), not a list of everything. Every step also works on its own: name the command or skill for each item you recommend.

Do not change any response, register, or report file as part of this command. Refreshing progress.md is expected.
