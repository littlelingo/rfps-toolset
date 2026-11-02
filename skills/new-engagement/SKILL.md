---
name: new-engagement
description: Start a new solicitation: create active-solution/ inside a source folder (config, response skeleton mirroring the template docx, evidence register, past-performance manifest)
argument-hint: <source folder> [template.docx] [title] [--type rfp|rfi]
disable-model-invocation: true
allowed-tools: Bash(rfps-new-engagement:*), Bash(rfps-decode-b64:*), Bash(ls:*), Read
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Start a new solicitation from `$ARGUMENTS`: the first item is the source folder (the capture folder holding `01 Solicitation Docs`, `05 Draft Response`, and so on). An optional second item is the response template .docx; the rest is an optional title. If no source folder is given, ask for it.

1. Run `rfps-new-engagement --source "<source folder>" [--template "<docx>"] [--title "<title>"] [--type rfi]`. Use `--type rfi` when the solicitation is a request for information (non-binding, no award); the default is `rfp`. An existing solution can be switched with `rfps-set-config solicitation_type rfi`. If the tool cannot find exactly one template in the source folder's `05 ... Draft ...` folder, show its message and ask which docx to use; if there is none, offer `/rfps:generate-template` to make one from the solicitation's response instructions.
2. Report what was created: `active-solution/` beside the numbered folders, `solution.toml` (paths relative, template stays in place, FINAL copies go to `11 Final Submission`), the `response/` files mirroring the template headings, `evidence/` and `past-performance/`, whether git was initialized (local disk) or skipped (Google Drive), and that it is now the active solution.
3. State the next steps: run the analysis skills on `01 Solicitation Docs`, add past-performance sources, write text under each heading in `response/*.md`, add facts to `evidence/register.csv`, then `/rfps:build-wip`.

**Template or solicitation files that live in Google Drive.** The tools read files from disk. Never retype the base64 that Drive `download_file_content` returns in chat: one wrong character corrupts a Word file and the template's styles and headings must be exact. If the app saved the download result to a file, decode it with `rfps-decode-b64 <saved result> "<folder>/<name>.docx"`. If the base64 only appeared in the chat, ask the user to download the file from Drive into the folder (give the exact folder path), then continue.

Do not modify the template docx, and do not overwrite an existing active-solution.
