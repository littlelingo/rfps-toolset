# Contributing

Contributor notes for the rfps plugin. A plugin cannot ship a CLAUDE.md that loads into a user's context (the validator warns), so behavior rules live in `skills/solution-guide/references/conventions.md` and each skill.

- This repo is the generic tool. No solicitation, agency or bidder data belongs here; it lives in each solicitation's `active-solution/` folder.
- Skills are in `skills/<name>/SKILL.md`; the plugin namespace is `rfps` (`/rfps:<name>`). Do not prefix skill names with `rfps-`.
- Tools are `tools/*.py` (inline `uv` dependencies) with a matching `bin/rfps-<name>` wrapper. A new tool needs a wrapper (`chmod +x`) and a `HINTS` row in `tools/list_tools.py`.
- Tools resolve read-only assets from their own location and write only into the user's solution folder or project. Never write state inside the plugin folder: the plugin cache is replaced on update.
- The docx heading text is the contract between the template and `response/*.md`.
- Check before committing: `claude plugin validate .`, `claude plugin test .`, and a smoke run of `rfps-new-engagement` on a fixture folder.
- In prose and docs, use hyphens instead of em-dashes.
