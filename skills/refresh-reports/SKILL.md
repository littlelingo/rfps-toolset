---
name: refresh-reports
description: Recompute the derived blocks in coverage-matrix.md, compliance-report.md and resource-plan.md (counts, pre-flight status, blocking list, page estimates, automated checks)
argument-hint: [active-solution folder or its source folder]
allowed-tools: Bash(rfps-collab:*), Bash(rfps-refresh-reports:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Run `rfps-refresh-reports --solution $ARGUMENTS` (use `--solution` alone for the active solution). Report the summary lines it prints (coverage, compliance, resources, and the open-items count), and the compliance status. The tool also regenerates `open-items.md` in the solution folder, the scannable list of every marker in `response/*.md`; link it.

The tool only rewrites the blocks between `<!-- derived:... -->` markers; the requirement and check rows are the source and are edited in place by the requirements-mapper and compliance-validator skills or by a person. If the tool reports a row with the wrong number of columns, show which row and say it probably contains a `|` character. Report-only: do not change any row, and do not edit inside the derived markers.
