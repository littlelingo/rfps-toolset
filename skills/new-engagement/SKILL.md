---
name: new-engagement
description: Start a new solicitation: create active-solution/ inside a source folder (config, response skeleton mirroring the template docx, evidence register, past-performance manifest)
argument-hint: <source folder> [template.docx] [title]
disable-model-invocation: true
allowed-tools: Bash(rfps-new-engagement:*), Bash(ls:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Start a new solicitation from `$ARGUMENTS`: the first item is the source folder (the capture folder holding `01 Solicitation Docs`, `05 Draft Response`, and so on). An optional second item is the response template .docx; the rest is an optional title. If no source folder is given, ask for it.

1. Run `rfps-new-engagement --source "<source folder>" [--template "<docx>"] [--title "<title>"]`. If the tool cannot find exactly one template in the source folder's `05 ... Draft ...` folder, show its message and ask which docx to use; if there is none, offer `/rfps:generate-template` to make one from the solicitation's response instructions.
2. Report what was created: `active-solution/` beside the numbered folders, `solution.toml` (paths relative, template stays in place, FINAL copies go to `11 Final Submission`), the `response/` files mirroring the template headings, `evidence/` and `past-performance/`, whether git was initialized (local disk) or skipped (Google Drive), and that it is now the active solution.
3. State the next steps: run the analysis skills on `01 Solicitation Docs`, add past-performance sources, write text under each heading in `response/*.md`, add facts to `evidence/register.csv`, then `/rfps:build-wip`.

Do not modify the template docx, and do not overwrite an existing active-solution.
