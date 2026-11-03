# RFPS Toolset

v0.7.0 | MIT License

A Claude Code plugin that guides a solicitation (RFP, RFI, SOW, SOO and similar) to a proposal response. It is generic: nothing in it is specific to an agency, contract or bidder. Everything for one solicitation lives in that solicitation's own `active-solution/` folder.

## Quick Start

Requirements: Claude Code, [`uv`](https://docs.astral.sh/uv/) (each tool declares its own Python dependencies inline), and Python 3.11 or later.

From GitHub (the repo is private for now; you need read access and git set up for GitHub, for example `gh auth login`):

```bash
claude plugin marketplace add littlelingo/rfps-toolset
claude plugin install rfps@rfps-toolset
```

Local, from a clone:

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
/rfps:start
/rfps:walk
```

`/rfps:start` asks once for the solicitation folder, the template and where past-performance material lives, then runs everything through to a first shared WIP document and hands over a ranked worklist. `/rfps:walk` then goes through that list one item at a time. The step-by-step commands (`/rfps:new-engagement`, `/rfps:status`, `/rfps:next`) still work on their own.

## How It Works

0. `/rfps:start` runs steps 1 to 4 below in one go (asking only at the start and for what it cannot decide); `/rfps:walk` works through what is left.
1. `/rfps:new-engagement` (`--type rfi` for a request for information, which makes staffing and attachments optional) creates `active-solution/` beside the numbered capture folders: config, a `response/` skeleton mirroring the template docx headings, an evidence register, an amendments log and living report skeletons.
2. Analysis skills read the solicitation: `collateral-analyzer`, `requirements-mapper`, `resource-planner`.
3. `capture` records the bid decision and `win-strategy` the evaluation factors and win themes; `section-drafter` writes `response/*.md` carrying those themes; `empathy-reviewer`, `compliance-validator` and `evaluator-simulator` review it. `/rfps:refresh-reports` checks that themes run through the response, compares pages written with each factor's page budget, and the worklist moves open work in heavily weighted factors up.
4. `/rfps:build-wip` creates one shared WIP document (a Google Doc by default; `--word` for a Word file in `05 Draft Response`) and then updates it in place as suggestions (Word: tracked changes), so reviewers' comments and edits are kept. `/rfps:pull-wip` brings their edits and comments back into the response. `/rfps:build-final` writes the submission docx from the template.
5. `/rfps:status` and `/rfps:next` show where you are and what to do; the status pane keeps that beside the chat.

The solution is found from the current directory (a folder at or above it holding `solution.toml`), else from the `.claude/active-solution` pointer in the current project. `/rfps:use-solution <folder>` sets the pointer.

## Response Templates

Which template a solicitation uses, in order: the form the agency issued (a docx in `05 Draft Response`), else your standard for the type, else one generated from the notice. Your standard RFI (or RFP) template is your branded docx (cover, proprietary legend, header and footer, styles) kept on your machine: `rfps-standard-template --type rfi --set my-template.docx` stores it in `~/.config/rfps/templates/` (never shared), and `rfps-new-engagement` copies it into each new capture folder. Without one, `rfps-standard-template --type rfi --make-plain` writes a plain one from the plugin's RFI outline (`tools/templates/outlines/rfi.json`). The RFP standard is not defined yet.

## Working With Google Drive

- **Files that are already in Drive** (the solicitation, past performance, the capture folder): install Google Drive for Desktop and keep it in **Stream files** mode (not Mirror). The capture folder then appears in Finder and files download only when the tools read them; nothing is copied by hand. Leave "Back up folders" (Desktop, Documents) off so nothing else on your machine goes to Drive.
- **Machine-local working files:** `rfps-set-config cache_dir ~/rfps-cache` keeps text caches and scratch builds on your machine, outside Drive. `/rfps:start` asks for it when the capture folder is on a Drive mount.
- **Where outputs go:** `/rfps:start`, `/rfps:build-wip` and `/rfps:build-final` ask where the shared WIP and the FINAL copy should go and use the defaults (the capture's `05 Draft Response` and `11 Final Submission`, never the Drive root) only when you give none. `rfps-set-config` records the answers.
- **Google-format files** (`.gdoc`, `.gsheet`, `.gslides`) on the mount are pointers only the Drive connector can read; the scan lists them and Claude reads them after you confirm.
- **Without Drive for Desktop,** Claude can list and read Drive folders through the connector (every subfolder, after one summary and confirmation), but Drive downloads of Word templates arrive as base64 in the chat; use `rfps-decode-b64` on a saved result, or download the file into the folder yourself.

## Working With a Team

- **Everyone works in the shared Google Doc** (comments, suggestions); it merges live and needs nothing installed.
- **A second person who runs the tools** shares the solution folder in Google Drive (Drive for Desktop, Stream mode) and runs `/rfps:start` in it. It begins with an entry check: no solution means start one, an existing one means join it (nothing is ever overwritten). Joining sets their name (kept on their machine), a local `cache_dir`, and shows who is writing, who has claimed which worklist items, what changed lately, and any duplicate IDs.
- **Commands that write shared files take a lease** (`.state/lease.json`) and warn if someone else holds it; a lease older than two hours counts as free. Drive does not merge two people editing the same Markdown or CSV file at the same moment, so the lease and the claims are the guard. The register re-reads itself before writing, so two people adding evidence at once do not get the same ID.

## Skills

| Skill | Purpose |
|---|---|
| `/rfps:start` | The one entry point. With an existing solution in the folder it joins it (your machine, who is doing what, claim work); otherwise front-loaded run: intake, then set-up, analysis, evidence, staffing, drafting, review and the first WIP, ending in a worklist |
| `/rfps:start-rfi`, `/rfps:start-rfp` | The same entry point with the type named. `/rfps:start` on its own reads the type from the notice (sources sought, request for information, or request for proposals) and asks only when it cannot tell |
| `/rfps:walk` | Walk the ranked worklist one item at a time: tools address it, you address it, or skip |
| `/rfps:new-engagement` | Start a solicitation: create `active-solution/` |
| `/rfps:use-solution` | Show or set the active solution |
| `/rfps:status`, `/rfps:next`, `/rfps:step` | Where you are, the next best action, mark a step done or skipped |
| `/rfps:add-past-performance` | List where past-performance material lives and draft evidence rows for approval |
| `/rfps:generate-template` | Make a response template .docx from the solicitation's instructions when no form was issued |
| `/rfps:update-template` | Bring `response/` in line after the template's headings changed (Word or a Google Doc) |
| `/rfps:make-gdoc-template` | Build a Google Doc version of the Word template to copy for each shared WIP document |
| `/rfps:extract` | Turn PDF, Word, Excel and PowerPoint files into searchable text |
| `/rfps:collateral-analyzer` | Brief and gap report from the provided collateral |
| `/rfps:questions` | Draft and track questions to the agency, with the reason, deadline and status of each, and log the answers |
| `/rfps:capture` | Record the bid decision: go or no-go, probability of winning and why, competitors, what must be true |
| `/rfps:requirements-mapper` | Coverage matrix of requirements to evidence |
| `/rfps:win-strategy` | Evaluation factors with weights and 3 to 5 win themes (discriminator, proof, benefit, key phrase) that every section carries |
| `/rfps:resources`, `/rfps:resource-planner` | Roster of roles and people, resource plan, staffing workbook |
| `/rfps:section-drafter` | Draft each response section from the coverage matrix |
| `/rfps:integrate`, `/rfps:integrate-edits` | Weave your edits into their section for approval |
| `/rfps:empathy-reviewer` | Tone and client-centricity pass |
| `/rfps:compliance-validator` | Pass/fail check against the explicit requirements |
| `/rfps:submission` | Keep the checklist of mandatory forms, signatures and deadlines; draft the submission or acknowledgement email for you to send |
| `/rfps:orals` | Prepare for an oral presentation or demonstration: outline by factor, likely questions, rehearsal checklist |
| `/rfps:debrief` | After the decision, record the outcome and the agency's feedback and list what is reusable |
| `/rfps:final-gate` | Check the exported PDF (pages, text, markers, links, margins, metadata, blocking items, open forms) and write a cleaned copy |
| `/rfps:evaluator-simulator` | An independent second reader rates each evaluation factor and names the change that most raises it |
| `/rfps:sweep` | List solicitation obligation sentences that no requirement row covers |
| `/rfps:refresh-reports` | Recompute counts, pre-flight status, page estimates and the solicitation checks |
| `/rfps:open-items` | List every decision, open question and evidence gap |
| `/rfps:file-audit` | Check every file has a known origin |
| `/rfps:pull-wip` | Bring edits and comments made in the shared WIP document back into the response, for approval |
| `/rfps:build-wip` | Create or update the shared WIP document (Google Doc by default, `--word` for Word) |
| `/rfps:build-final` | Build the final submission docx from the template |
| `/rfps:status-page` | Write a local one-file HTML status page |
| `/rfps:solution-guide` | Natural-language status and guidance |
| `/rfps:help` | List the terminal tools and skills |

## Terminal Tools

The `rfps-*` commands in `bin/` are on the PATH while the plugin is enabled: `rfps-flow-status`, `rfps-build-response`, `rfps-new-engagement`, `rfps-refresh-reports`, `rfps-sweep`, `rfps-consistency`, `rfps-lint`, `rfps-crossref`, `rfps-final-gate`, `rfps-open-items`, `rfps-worklist`, `rfps-collab`, `rfps-set-config`, `rfps-detect-type`, `rfps-decode-b64`, `rfps-staffing`, `rfps-sync-gdoc`, `rfps-sync-docx`, `rfps-open-doc`, `rfps-extract-docs`, `rfps-add-source`, `rfps-file-audit`, `rfps-status-page`, `rfps-use-solution` and `rfps-list-tools`. Run `/rfps:help` for what each is for.

## Status Pane

A live pane beside the chat in Claude Desktop (a plugin mod in `hooks/`). Open it with `/rfps-pane`. See [docs/STATUS-PANE.md](docs/STATUS-PANE.md).

## What This Plugin Runs (Security and Trust)

A plugin runs with your privileges, so here is exactly what this one does. Read the files before you install. The only network use is `uv` fetching the Python packages the tools declare (python-docx, openpyxl, pypdf, python-pptx) from PyPI on first run, and Claude talking to the Google connectors you turn on.

| Component | What it does | Where it runs |
|---|---|---|
| `skills/` | Instructions Claude follows. Solicitation text is treated as data, never as instructions. Several skills (`start`, `walk`, `build-wip`, `build-final`, `make-gdoc-template`, `new-engagement` and others) can only be run by typing them, because they create files, documents or submission copies. | In Claude's context |
| `bin/rfps-*` | Thin shell wrappers that run `tools/*.py` with `uv`. They are put on the Bash tool's PATH while the plugin is enabled. | Your shell, with your privileges |
| `tools/*.py` | Read the solicitation folders you point them at and write only to that solution's `active-solution/` folder (and `.state/`), plus `.claude/active-solution` in the current project. Nothing is written into the plugin folder. They never call Google; Claude does that through your connectors. | Your shell |
| `hooks/` (the status pane, a mod) | A pane in Claude Desktop, opened only when you ask for it (`/rfps-pane`). Once opened it runs `rfps-status-page --json` through `uv` every minute and shows the result; before that, and in any session where you never open it, it runs nothing. It runs outside the sandbox. | Inside Claude Code |
| Google connectors | When the Google route is used, Claude reads and edits the shared Google Doc through the Drive and Docs connectors you enabled, as suggestions and comments. Check which Google account each connector uses before real work. | Your Google account |

Review it with `claude plugin details rfps`, or `claude --plugin-dir <clone> plugin details rfps` before installing.

**Where it works.** Claude Code (terminal, desktop and IDE). It does not install on claude.ai or in Cowork, because a top-level `bin/` directory and the mod are Claude Code only. It needs `uv` and Python 3.11 or later.

## Project Structure

```
.claude-plugin/    plugin.json, marketplace.json
skills/            one folder per skill (commands and analysis skills)
bin/               rfps-* wrappers that run tools/*.py with uv
tools/             Python tools, templates, flow.toml, defaults.toml
hooks/, types/     status pane mod
docs/              status pane notes
fixtures/          fictional sample solicitation and an end-to-end smoke test
```

Shared rules (sources of truth, no invented bidder facts, evidence register, outside sources) are in `skills/solution-guide/references/conventions.md`.

## Try It With the Sample

`fixtures/` holds a fictional solicitation, template and bidder, so the whole flow can be tried with no real data. See [fixtures/README.md](fixtures/README.md).

## Development

```bash
claude plugin validate .
claude plugin test .
fixtures/smoke.sh
claude plugin eval . --trust-plugin --no-publish   # model calls; scores the skills with and without the plugin
claude --plugin-dir .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [BACKLOG.md](BACKLOG.md).

## License

MIT. See [LICENSE](LICENSE).
