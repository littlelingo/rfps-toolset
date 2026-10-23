---
name: help
description: List the terminal tools and skills in this toolset with what each one is for
argument-hint: [tool or skill name to explain]
allowed-tools: Bash(rfps-list-tools:*), Read
---

Run `rfps-list-tools --json`.

1. Present the terminal tools first, as one table with the columns Tool (the `rfps-<name>` command), What it does (one plain sentence), Use it when, and Slash command (blank when none). These are the commands that are not slash commands; each is run in the terminal from the toolset folder. Keep the sentences short and in plain language.
2. Then list the skills in a second, shorter table (Skill, What it does), and say they work by asking in plain language or by typing the name as a slash command.
3. End with one line: slash commands starting `/rfps:` are the guided path, and every tool and skill also works on its own.

If `$ARGUMENTS` names a tool or skill, explain just that one: read its docstring (tools) or its SKILL.md (skills), say what it reads and writes, show a typical command, and name any related slash command. Report only; do not run any tool other than `list_tools.py` and do not change any file.
