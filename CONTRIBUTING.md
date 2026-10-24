# Contributing

Contributor notes for the rfps plugin. A plugin cannot ship a CLAUDE.md that loads into a user's context (the validator warns), so behavior rules live in `skills/solution-guide/references/conventions.md` and each skill.

- This repo is the generic tool. No solicitation, agency or bidder data belongs here; it lives in each solicitation's `active-solution/` folder.
- Skills are in `skills/<name>/SKILL.md`; the plugin namespace is `rfps` (`/rfps:<name>`). Do not prefix skill names with `rfps-`.
- Tools are `tools/*.py` (inline `uv` dependencies) with a matching `bin/rfps-<name>` wrapper. A new tool needs a wrapper (`chmod +x`) and a `HINTS` row in `tools/list_tools.py`.
- Tools resolve read-only assets from their own location and write only into the user's solution folder or project. Never write state inside the plugin folder: the plugin cache is replaced on update.
- The docx heading text is the contract between the template and `response/*.md`.
- Check before committing: `claude plugin validate .`, `claude plugin test .`, and `fixtures/smoke.sh` (end-to-end run on the fictional sample; see `fixtures/README.md`).
- In prose and docs, use hyphens instead of em-dashes.
- Behavior tests: `evals/` holds `claude plugin eval` cases (plain wording must reach the right skill, unrelated requests must not, drafting must not invent facts, clearance is never granted by the tool). Run `claude plugin eval . --trust-plugin --no-publish` after changing a skill description or a rule in `conventions.md`; it makes model calls and costs a few dollars. Results go to `evals/results/` (git-ignored).
- Skills with outward effects (files, Drive documents, submission copies) set `disable-model-invocation: true` so they only run when typed; keep that for any new skill of that kind.

## Releasing

1. Bump `version` in `.claude-plugin/plugin.json` and the version line in `README.md`; move the `Unreleased` changelog entries under the new version.
2. Run `claude plugin validate . --strict`, `ruff check .`, `fixtures/smoke.sh`, and (after skill or convention changes) `claude plugin eval . --trust-plugin --no-publish`.
3. Commit, then tag with `claude plugin tag --push`. It writes the standard `rfps--vX.Y.Z` tag and checks that `plugin.json` and the marketplace entry agree. (Releases up to 0.3.0 also carry an older `vX.Y.Z` tag; both point at the same commit.)
4. `claude plugin update rfps@rfps-toolset` picks the release up. Users only receive a change when `version` changes.

Settings that differ per solicitation (`wip_format`, `open_in`, `gdoc_template`, the page limit) live in each solution's `solution.toml`, not in the plugin's `userConfig`, because they belong to a project, not to a user.
