---
description: When the user asks for the Word route, the pull-wip skill must choose the Word sync tool, not Google.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
runs: 3
---

We keep the shared WIP as a Word file this time. Pull the edits and tracked changes people made in it back into the response (use the Word route, --word) and list them for my approval.
