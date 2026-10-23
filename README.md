# RFPS Toolset

v0.1.0 | MIT License

A Claude Code plugin that guides a solicitation (RFP, SOW, SOO and similar) to a proposal response. It is generic: nothing in it is specific to an agency, contract or bidder. Everything for one solicitation lives in that solicitation's own `active-solution/` folder.

## Quick Start

Requirements: Claude Code, [`uv`](https://docs.astral.sh/uv/) (each tool declares its own Python dependencies inline), and Python 3.11 or later.

Local, from a clone (not published yet):

```bash
claude plugin marketplace add /path/to/rfps-toolset
claude plugin install rfps@rfps-toolset
```

Or try it for one session without installing:

```bash
claude --plugin-dir /path/to/rfps-toolset
```

Then, in the solicitation's source folder (the one with `01 Solicitation Docs`, `05 Draft Response` and so on):

```
/rfps:new-engagement
/rfps:status
/rfps:next
```

## How It Works

1. `/rfps:new-engagement` creates `active-solution/` beside the numbered capture folders: config, a `response/` skeleton mirroring the template docx headings, an evidence register, an amendments log and living report skeletons.
2. Analysis skills read the solicitation: `collateral-analyzer`, `requirements-mapper`, `resource-planner`.
3. `section-drafter` writes `response/*.md`; `empathy-reviewer` and `compliance-validator` review it.
4. `/rfps:build-wip` pours the text into a copy of the template docx. `/rfps:build-final` writes the submission copy and refuses while decisions, placeholders or uncleared evidence remain.
5. `/rfps:status` and `/rfps:next` show where you are and what to do; the status pane keeps that beside the chat.

The solution is found from the current directory (a folder at or above it holding `solution.toml`), else from the `.claude/active-solution` pointer in the current project. `/rfps:use-solution <folder>` sets the pointer.

## Skills

| Skill | Purpose |
|---|---|
| `/rfps:new-engagement` | Start a solicitation: create `active-solution/` |
| `/rfps:use-solution` | Show or set the active solution |
| `/rfps:status`, `/rfps:next`, `/rfps:step` | Where you are, the next best action, mark a step done or skipped |
| `/rfps:extract` | Turn PDF, Word, Excel and PowerPoint files into searchable text |
| `/rfps:collateral-analyzer` | Brief and gap report from the provided collateral |
| `/rfps:requirements-mapper` | Coverage matrix of requirements to evidence |
| `/rfps:resources`, `/rfps:resource-planner` | Roster of roles and people, resource plan, staffing workbook |
| `/rfps:section-drafter` | Draft each response section from the coverage matrix |
| `/rfps:integrate`, `/rfps:integrate-edits` | Weave your edits into their section for approval |
| `/rfps:empathy-reviewer` | Tone and client-centricity pass |
| `/rfps:compliance-validator` | Pass/fail check against the explicit requirements |
| `/rfps:refresh-reports` | Recompute counts, pre-flight status and page estimates |
| `/rfps:open-items` | List every decision, open question and evidence gap |
| `/rfps:file-audit` | Check every file has a known origin |
| `/rfps:build-wip`, `/rfps:build-final` | Build the work-in-progress or final docx |
| `/rfps:status-page` | Write a local one-file HTML status page |
| `/rfps:solution-guide` | Natural-language status and guidance |
| `/rfps:help` | List the terminal tools and skills |

## Terminal Tools

The `rfps-*` commands in `bin/` are on the PATH while the plugin is enabled: `rfps-flow-status`, `rfps-build-response`, `rfps-new-engagement`, `rfps-refresh-reports`, `rfps-open-items`, `rfps-staffing`, `rfps-extract-docs`, `rfps-file-audit`, `rfps-status-page`, `rfps-use-solution` and `rfps-list-tools`. Run `/rfps:help` for what each is for.

## Status Pane

A live pane beside the chat in Claude Desktop (a plugin mod in `hooks/`). Open it with `/rfps-pane`. See [docs/STATUS-PANE.md](docs/STATUS-PANE.md).

## Project Structure

```
.claude-plugin/    plugin.json, marketplace.json
skills/            one folder per skill (commands and analysis skills)
bin/               rfps-* wrappers that run tools/*.py with uv
tools/             Python tools, templates, flow.toml, defaults.toml
hooks/, types/     status pane mod
docs/              status pane notes
```

Shared rules (sources of truth, no invented bidder facts, evidence register, outside sources) are in `skills/solution-guide/references/conventions.md`.

## Development

```bash
claude plugin validate .
claude plugin test .
claude --plugin-dir .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [BACKLOG.md](BACKLOG.md).

## License

MIT. See [LICENSE](LICENSE).
