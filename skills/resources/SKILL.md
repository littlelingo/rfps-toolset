---
name: resources
description: Build or update the roster of roles and people, the State's role requirements, and the staffing workbook for the active solution
argument-hint: [role name, or what to add, change or drop]
disable-model-invocation: true
allowed-tools: Bash(rfps-collab:*), Bash(rfps-refresh-reports:*), Bash(rfps-staffing:*), Bash(rfps-flow-status:*), Read, Edit, Write
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Follow the resource-planner skill for the active solution. If `$ARGUMENTS` names a role or a change, work on that; if empty and `response/resources.csv` is missing or has no roles, start by extracting the roles, minimums, deliverables and any stated total from the solicitation and propose the first roster (Key Personnel with in-depth descriptions, plus suggested cover-down roles); if it has roles, run `rfps-refresh-reports --solution`, show the Checks and ask which open item to work on first. Show proposed rows before writing them. After roster or workbook changes, run `rfps-staffing` to sync the two (use `--check` to preview) and `rfps-refresh-reports --solution` to refresh the checks.
