---
name: join
description: Join a solicitation that someone else already started - find the existing solution, set up this machine, see who is doing what and what changed, then pick up work from the worklist
argument-hint: [source folder or active-solution folder]
disable-model-invocation: true
allowed-tools: Bash(rfps-collab:*), Bash(rfps-use-solution:*), Bash(rfps-set-config:*), Bash(rfps-flow-status:*), Bash(rfps-worklist:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Read, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules apply to this skill. Then follow `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/entry.md` with `$ARGUMENTS` as the folder: it decides whether a solution exists (join) or not (offer to start one), and holds the join steps.

This command changes nothing in the solution except what the person chooses in the last step (claims) and their own machine settings.
