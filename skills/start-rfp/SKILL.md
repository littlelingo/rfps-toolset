---
name: start-rfp
description: /rfps:start with the type fixed to RFP - for a request for proposals (a bid); joins the solution if one exists, otherwise starts a new one
argument-hint: [source folder] [--word]
disable-model-invocation: true
allowed-tools: Bash(rfps-new-engagement:*), Bash(rfps-collab:*), Bash(rfps-set-config:*), Bash(rfps-decode-b64:*), Bash(rfps-add-source:*), Bash(rfps-scan-sources:*), Bash(rfps-extract-docs:*), Bash(rfps-register-add:*), Bash(rfps-refresh-reports:*), Bash(rfps-open-items:*), Bash(rfps-flow-status:*), Bash(rfps-worklist:*), Bash(rfps-staffing:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Bash(rfps-build-response:*), Bash(rfps-sweep:*), Bash(rfps-lint:*), Bash(rfps-crossref:*), Bash(rfps-consistency:*), Bash(ls:*), Read, Write, Edit, Skill, AskUserQuestion
---

This is `/rfps:start` with the solicitation type already decided: **rfp**. Read `${CLAUDE_PLUGIN_ROOT}/skills/start/SKILL.md` and follow it exactly, with `--type rfp` as if the user had typed it. Do not run `rfps-detect-type` and do not ask the type question; the user named it. Everything else, including the entry check that joins an existing solution, is unchanged.

If the entry check finds a solution whose `solicitation_type` differs from rfp, say so in one line and ask whether to switch it (`rfps-set-config solicitation_type rfp`) before going on; never switch silently.
