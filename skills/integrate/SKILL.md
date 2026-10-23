---
name: integrate
description: Weave text the user added or edited into its section as an expert proposal writer would, shown for approval
argument-hint: [part of a heading] or paste "add this to <section>: ..."
allowed-tools: Bash(rfps-flow-status:*), Bash(rfps-open-items:*), Read, Edit
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Follow the integrate-edits skill. If `$ARGUMENTS` names a section, work on that one; if it contains text to add, find the section it belongs in and use that text as the new material; if it is empty, run `rfps-flow-status --changed` and work through the changed sections one at a time. Show a before and after for each section and wait for approval before writing it.
