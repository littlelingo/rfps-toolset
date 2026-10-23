# Changelog

## 0.1.1 (2026-10-23)

- Added `fixtures/`: a fictional sample solicitation, a seed response and register, `smoke.sh` (tools end to end, no model calls) and `trial.sh` (runs the analysis and drafting skills with Claude on a throwaway copy).
- Added `/rfps:add-past-performance` and the `rfps-add-source` tool. Past-performance sources inside the capture folder are stored relative to `active-solution/`; `rfps-add-source --normalize` migrates older absolute entries.
- Collateral analyzer now extracts Word, Excel, PowerPoint and PDF files with `rfps-extract-docs` first, logs amendments and Q&A in `amendments/log.md`, and offers to record past-performance sources. The requirements mapper fills in the affected requirement IDs.
- `/rfps:extract` defaults its output to `<solution>/.state/text/` (git-ignored).
- The page estimate reads "about 3 pages" when the low and high estimates are the same number.
- Removed machine-specific `uv` paths from the status pane.

## 0.1.0

- Initial plugin packaging of the RFP toolset: skills (commands converted, `/rfps:` namespace), `rfps-*` tools on PATH, status pane mod, MIT license.
