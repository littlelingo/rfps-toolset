# Sample fixture

A fictional solicitation so the whole rfps flow can be tried or tested with no real or sensitive material. The county, the RFP, the amendment, the bidder (Example Bidder LLC) and its past performance are all made up.

## What is here

| Path | What it is |
|---|---|
| `sample-capture/` | A ready capture folder: `01 Solicitation Docs` (RFP DPW-2026-017 and Amendment 1), `05 Draft Response` (the response template), `11 Final Submission`, and `past-performance` (the bidder's notes) |
| `seed/` | A finished `response/*.md` and `evidence/register.csv` for the sample, to copy into `active-solution/` when you want to skip drafting |
| `answer-key.toml` | What a correct requirements pass must find in the sample (11 obligation sentences, the page limit, the amendment override). `smoke.sh` checks `rfps-sweep` against it; the golden evals in `evals/` are graded against the same facts |
| `seed/coverage-matrix.md` | One verbatim row per keyed obligation, so the sweep and the quote check can be tested with and without rows |
| `build_sample.py` | Regenerates `sample-capture/` (`uv run fixtures/build_sample.py [folder]`) |
| `smoke.sh` | Runs the tools end to end in a temp folder and checks the results (no model calls) |
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
