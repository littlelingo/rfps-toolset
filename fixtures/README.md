# Sample fixture

A fictional solicitation so the whole rfps flow can be tried or tested with no real or sensitive material. The county, the RFP, the amendment, the bidder (Example Bidder LLC) and its past performance are all made up.

## What is here

| Path | What it is |
|---|---|
| `sample-capture/` | A ready capture folder: `01 Solicitation Docs` (RFP DPW-2026-017 and Amendment 1), `05 Draft Response` (the response template), `11 Final Submission`, and `past-performance` (the bidder's notes) |
| `seed/` | A finished `response/*.md` and `evidence/register.csv` for the sample, to copy into `active-solution/` when you want to skip drafting |
| `answer-key.toml` | What a correct requirements pass must find in the sample (11 obligation sentences, the page limit, the amendment override). `smoke.sh` checks `rfps-sweep` against it; the golden evals in `evals/` are graded against the same facts |
| `seed/coverage-matrix.md` | One verbatim row per keyed obligation, so the sweep and the quote check can be tested with and without rows |
| `seed/capture.md`, `seed/win-strategy.md`, `seed/evaluation-sim.md` | A recorded Go decision, the sample's evaluation factors and three win themes, and hand-written second-reader ratings, to test the bid step, theme and page-budget checks, weights on the worklist and the evaluation summary |
| `build_sample.py` | Regenerates `sample-capture/` (`uv run fixtures/build_sample.py [folder]`) |
| `smoke.sh` | Runs the tools end to end in a temp folder and checks the results (no model calls) |
| `gdoc_master_test.py`, `fearless-formal-master.json` | The master Google Doc: checks a master (styles, page setup, header, footer, blank body) against a style profile, empties a copy of a finished response, writes the response template's skeleton into the blank copy, and refuses a WIP with no master registered. It also generates the master .docx from the profile alone. The JSON is a read_doc result with only the styles, header and footer of a doc that meets the formal profile (no response text), used to test the check |
| `gdoc_sim.py`, `gdoc_test.py` | A simulated Google Docs API and an end-to-end test of the Google Docs route against it (create, suggestions, word-level edits, pull, collisions, bullets, tables); `smoke.sh` runs it. No Google involved |
| `trial.sh` | Runs the extract, collateral, past-performance, requirements and drafting skills with Claude on a throwaway copy (model calls; a few minutes) |

## Try the flow by hand

Copy the capture folder somewhere, open Claude Code in the copy, then:

```
/rfps:new-engagement
/rfps:extract
/rfps:collateral-analyzer
/rfps:requirements-mapper
/rfps:section-drafter
```

The sample's evidence is in `past-performance/`. To skip analysis and drafting, copy `seed/response/*.md` into `active-solution/response/` and `seed/register.csv` into `active-solution/evidence/`, then run `/rfps:build-wip` and `/rfps:build-final`.

## What the smoke test checks

`fixtures/smoke.sh` creates the sample in a temp folder, scaffolds a solution, loads the seed, refreshes the reports, builds WIP and FINAL, and confirms the FINAL docx has no internal markers. It then cites evidence that is not cleared (`E-003` is `needs-permission`) and confirms FINAL refuses. Run it before committing changes to `tools/`.
