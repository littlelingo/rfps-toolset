---
description: A request to check the exported PDF before submitting should reach the final-gate skill.
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
runs: 3
---

I exported the response to PDF. Is it ready to submit? Check the page count, that no internal notes leaked into it, and that my name is not in the file properties.
