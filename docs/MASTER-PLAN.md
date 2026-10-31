# Master Plan: Making Responses Win and Compliance Verifiable

Status: proposal, not started. Drafted 2026-10-30 from four reviews of the toolset: a gap review, a sanity check of that review against the repo, a high-win-rate proposal writer's view, and an evaluator's view. Items marked (verified) were confirmed in the repo; items marked (inferred) come from reading skill text and should be confirmed against a real bid.

## 1. Where the toolset stands

Strong: stable IDs and living reports, a derived-block refresh tool, an evidence register with clearance and a deny list, a no-invented-facts rule, a guided flow, Google and Word sync, and a team lease.

Weak, in one sentence each:
- It assembles an honest, compliant, client-aware draft but has no strategy layer that makes a draft *win* (no win themes, discriminators, bid gate or price view) (verified: no hits in skills or tools).
- It reports pass/fail but never scores the way an agency will, so "meets" versus "exceeds" is invisible.
- Requirement capture and format compliance rely on model judgment with no deterministic backstop (verified: no shall/must sweep, no quote check, no render).
- Its own quality is barely measured: 12 eval cases, most about routing; none measures mapper recall or validator catches (verified).

## 2. Principles for the changes

1. **Measure before improving.** Golden evals come first so every later change shows up as a number.
2. **Deterministic backstops for anything disqualifying.** Models draft and judge; scripts count, quote-check and diff.
3. **Score like the evaluator, write like the winner.** Strategy flows forward into drafting; independent scoring flows back.
4. **Never weaken the honesty rules.** Nothing here may invent bidder facts; new artifacts follow `conventions.md`.
5. **Fit the existing grain.** New steps go in `tools/flow.toml`, new reports use stable IDs and derived blocks, new tools are `bin/rfps-*` wrappers over `tools/*.py` run with uv, and the user keeps clearance decisions.

## 3. Workstreams

| Code | Workstream | Lens that drives it |
|---|---|---|
| A | Trust and measurement (evals, hygiene) | Testing, all |
| B | Requirement integrity | Reviewer, compliance |
| C | Strategy and capture | Winning writer |
| D | Scoring and review | Reviewer |
| E | Submission safety | Reviewer, compliance |
| F | Evidence and pricing | Both |
| G | Section craft | Winning writer |
| H | Learning loop | Winning writer |

## 4. Work items

Size: S under a day, M a few days, L about a week or more. Each item states its acceptance check.

### Phase 0: Quick wins (week 1)

| ID | Item | Size | Done when |
|---|---|---|---|
| 0.1 | Fix drafter marker examples to `[GROUNDED: E-nnn]` in `skills/section-drafter/SKILL.md`, `references/drafting-patterns.md` and all five section templates (verified mismatch with `flow_status.py:64,136`) | S | A draft following the examples is not flagged "uncited" |
| 0.2 | Remove dangling references: "see CLAUDE.md" (`section-drafter`, `next`), and "Proposal Assembler" in `collateral-analyzer`, `requirements-mapper`, `compliance-validator`, `conventions.md`; resolve the BACKLOG item to retire it, pointing at `/rfps:build-final` | S | `rg "CLAUDE.md|Proposal Assembler" skills` returns nothing |
| 0.3 | Record this plan's decisions in BACKLOG.md and link it | S | BACKLOG references this file |

### Phase 1: Foundations (weeks 2 to 3)

| ID | Item | Size | Done when |
|---|---|---|---|
| 1.1 | **Golden eval set on the fixture.** Add an answer key to the fixture RFP (seeded shall items, a page limit, an amendment that overrides the RFP, a mandatory section). New cases: mapper recall, validator catches a planted overage and a missing mandatory section, empathy reviewer flags planted superlatives and vendor-centric openings, drafter leaves no unmarked claims. Track recall and precision | M | `claude plugin eval` reports a baseline per case |
| 1.2 | **Requirement sweep tool** `rfps-sweep`: regex over extracted solicitation text for shall, must, will (obligation), required, "no later than"; compare against `R-` and compliance rows; list obligation sentences with no matching row | M | Fixture's seeded items all appear or are listed as unmapped |
| 1.3 | **Quote verification** inside `rfps-refresh-reports`: every quoted RFP phrase in the matrix and compliance report must appear verbatim in extracted text; otherwise a derived "unverified quote" warning | S | A planted paraphrase is flagged |
| 1.4 | Wire 1.2 and 1.3 into `refresh-reports` autochecks and the flow's `requirements` step so "requirements recorded" is not green while unmapped obligations remain | S | `flow_status` shows the attention state |

Status (2026-10-30): built. 1.2 is `rfps-sweep` (`tools/sweep.py`, helpers in `tools/solicit_text.py`, skill `/rfps:sweep`); 1.3 and the sweep both show as automated checks in `compliance-report.md`; 1.4 turns the `requirements` flow step orange when extracted solicitation text has a mandatory obligation with no row. 1.1 is `fixtures/answer-key.toml`, `fixtures/seed/coverage-matrix.md`, deterministic sweep checks in `smoke.sh`, and four model-graded cases (`mapper-finds-every-obligation`, `validator-catches-planted-failures`, `empathy-flags-planted-defects`, `drafter-marks-every-claim`). The four evals have not been run yet (model calls); run `claude plugin eval . --trust-plugin --no-publish` to record the baseline. Known limits: matching is token overlap (0.6), so a very short or heavily paraphrased row can miss or falsely match; amendments are caught only by change verbs (extended, changed, replaced, revised, deleted, amended).

Why first: 1.1 makes everything after it measurable, and 1.2 and 1.3 close the silent-miss risk that sits under both the mapper and the validator.

### Phase 2: Score like an evaluator, write like a winner (weeks 4 to 7)

| ID | Item | Size | Done when |
|---|---|---|---|
| 2.1 | **Evaluator simulator skill.** A fresh-context agent given only the evaluation criteria and `response/*.md` (not `brief.md` or strategy). Scores each factor on the agency's adjectival scale, lists strengths, weaknesses and deficiencies, and states the single change that most raises each score. Output `evaluation-sim.md` with stable IDs; findings feed the worklist | L | Run on the fixture produces scored factors and a ranked fix list; golden eval confirms it flags a planted weak section |
| 2.2 | **Bid gate and capture record** `capture.md`: pWin with reasons, incumbent, likely competitors, what must be true, go/no-go sign-off by the user. New flow step before analysis; the mapper's "escalate" gaps feed it | M | Flow blocks drafting until the gate is recorded or skipped on purpose |
| 2.3 | **Win strategy skill** `win-strategy.md`: 3 to 5 themes, discriminators with register proof IDs, competitor weak spots (labelled as assumptions), and a feature-benefit-proof line per evaluation factor. New flow step between `requirements` and `draft` | M | Themes cite register IDs or are marked assertions |
| 2.4 | **Drafter uses the strategy.** Each section states which theme and factor it serves; feature, benefit, proof structure becomes the default paragraph shape; the executive summary is drafted last from themes and mapped to criteria | M | Theme-coverage lint (in 5.1) passes on the fixture |
| 2.5 | **Page budget per factor.** Derive target pages from evaluation weights; show budget against actual in the page-count block | S | `refresh-reports` shows over/under per factor |
| 2.6 | **Assertion weighting.** Rank open assertions and evidence gaps by the weight of the factor they sit in, so the worklist leads with the ones that cost most | S | Worklist order changes with weights |

Status (2026-10-30): built. 2.1 `/rfps:evaluator-simulator` (fresh agent sees only the evaluation criteria and `response/*.md`; ratings in `evaluation-sim.md`, summary by `refresh-reports`, weak factors on the worklist); 2.2 `/rfps:capture` and `capture.md` with a `bid` flow step; 2.3 `/rfps:win-strategy` and `win-strategy.md` with a `strategy` flow step and a theme check in the compliance report's automated checks; 2.4 the drafter reads the strategy, names the factor and theme each section serves, writes feature-benefit-proof paragraphs and drafts the executive summary last; 2.5 page budget by factor (weights share `page_limit`; flagged outside 50 to 125 percent of budget); 2.6 markers in a 30 percent or heavier factor move up two places on the worklist, 15 percent one. Decisions taken by default, change if you disagree: the bid gate and strategy are flow steps you can skip, not blockers; the default scale is Outstanding, Good, Acceptable, Marginal, Unacceptable, replaced by the solicitation's own scale when it has one. Not covered by model-graded evals: the three new skills are user-invoked only, so routing evals do not apply; the simulator's independence is by instruction, not by a tool-enforced sandbox.

### Phase 3: Submission safety (weeks 8 to 10)

| ID | Item | Size | Done when |
|---|---|---|---|
| 3.1 | **Final gate command** `rfps-final-gate`: blocking items, signatures present, file names, file types, total size, deadline and submission method, then copy to `11 Final Submission` | M | Fails on each planted defect in the fixture |
| 3.2 | **Measured format check.** Render docx to PDF (LibreOffice, optional dependency with a clear message when missing) and check real page count, font, size and margins against `solution.toml` rules | M | Page count from render replaces the estimate when available |
| 3.3 | **Metadata and hidden-content scrub**: docx and PDF metadata, comments, tracked changes, hidden text | M | Scrub report lists what was removed and what remains |
| 3.4 | **Signature page and mandatory forms tracker**, plus draft text for the submission email, intent-to-respond acknowledgement and questions email (the parked Section 9 item). Dates tracked as blocking items | M | Each mandatory form has owner, due date, status |
| 3.5 | **Validation staleness.** Store a per-section content hash when compliance, empathy or simulation last ran; `refresh-reports` flags sections edited since | S | Editing a validated section shows "stale" |
| 3.6 | **Amendment impact.** When an amendment is logged, diff against requirements and checks; reopen affected rows as stale and add them to the worklist | M | Fixture amendment reopens the planted rows |

### Phase 4: Evidence, people and price (weeks 11 to 14)

| ID | Item | Size | Done when |
|---|---|---|---|
| 4.1 | **Structured register fields**: parsed start and end dates, contract value, scope tags, reference contact and currency; keep old columns readable | M | Existing registers still load |
| 4.2 | **Relevance and recency check** against the solicitation's thresholds (for example last five years, minimum value), shown per past-performance requirement | M | Fixture selection fails a planted threshold |
| 4.3 | **Clearance proof**: approver, date and reference columns; FINAL requires a reference before `cleared` counts (parked item) | S | Build refuses an unreferenced `cleared` row |
| 4.4 | **Consistency checker**: names, roles, LOE percentages, dates and dollar figures agree across the response, roster, `Staffing.xlsx` and pricing | M | A planted mismatch is reported with both locations |
| 4.5 | **Price-to-win view** beside the staffing workbook: stated budget signals, value arguments, sensitivity; clearly labelled as assumption-driven and decided by the user | M | Section exists in `resource-plan.md` with derived checks |
| 4.6 | **Rate sheet hook** when a rate sheet exists (parked item) | S | Staffing references the sheet |

### Phase 5: Craft and learning (weeks 15 to 18)

| ID | Item | Size | Done when |
|---|---|---|---|
| 5.1 | **`rfps-lint`** in autochecks: superlatives, passive voice without actor, we-to-client ratio, undefined acronyms, client-vocabulary hits from the brief, duplicate paragraphs across sections, theme coverage. Separate from the register deny list | M | Planted defects in the fixture are reported |
| 5.2 | **More section templates**: executive summary, management plan, transition, risk register, quality assurance, schedule | M | Drafter selects them by heading |
| 5.3 | **Exhibit plan** per section (visual, what it proves, action caption) and an auto-generated reviewer-facing requirement-to-section cross-reference table | M | Cross-reference matches the coverage matrix |
| 5.4 | **Questions to the agency log** with deadlines, linked to `amendments/`; answers become sources | S | Overdue question appears in the worklist |
| 5.5 | **Orals support** when the solicitation calls for them: likely questions from the evaluation sim, practice outline | M | Only offered when orals are required |
| 5.6 | **Debrief and lessons capture** after submission and after the decision; writes reusable themes and evidence candidates (for approval) | M | A completed bid leaves a reusable record |

## 5. Dependencies

```
0.x
 |
1.1 evals  ------------------------------------------------+
 |                                                          |
1.2 sweep -> 1.3 quote check -> 1.4 flow wiring             |
 |                                                          |
2.2 bid gate -> 2.3 win strategy -> 2.4 drafter uses it     |
 |                                      |                   |
2.1 evaluator sim  <------- needs 1.1 for its own eval      |
 |
3.5 staleness -> 3.6 amendment impact -> 3.1 final gate (3.2, 3.3, 3.4 feed it)
 |
4.1 register fields -> 4.2 recency, 4.3 clearance proof
4.4 consistency needs the roster and workbook already present
5.1 lint needs 2.3 for theme coverage
```

Items 2.1 and 3.1 can start in parallel with their neighbours; everything else follows the arrows.

## 6. Decisions needed from the owner

1. Is `pWin` and a bid gate wanted in this plugin, or is capture handled outside it? (2.2)
2. Is LibreOffice acceptable as an optional dependency? Otherwise 3.2 stays an estimate. (3.2)
3. Which adjectival scale does the evaluator simulator default to when a solicitation states none? (2.1)
4. Should the evaluator simulator and win strategy be flow steps that block, or optional ones? Recommendation: optional but shown as attention items. (2.1, 2.3)
5. Register change: add columns to the CSV (simple) or move to a structured file? Recommendation: add columns. (4.1)

## 7. Risks

- **Scope creep into capture management.** Keep 2.2 and 2.3 to a single page each; they feed the draft, they do not replace a capture tool.
- **Model-written competitor claims.** Competitor weak spots are assumptions; label them and never put them in response text.
- **False comfort from scores.** The simulator is a second reader, not the agency; reports must say so.
- **Lint noise.** Start with a small rule set, report counts and examples, and let users mute a rule per solution.
- **Unverified premises.** Q&A, orals and price-to-win gaps are inferred from skill text (see section 1); confirm against a real bid before building 5.4, 5.5 and 4.5.

## 8. Measures of success

- Golden eval recall for requirement capture at or above an agreed target on the fixture, and tracked per release.
- Zero unmapped obligation sentences at the final gate.
- Every disqualifying class (page limit, mandatory form, format, deadline) has a deterministic check.
- Simulator score for each factor rises across revisions on a real bid.
- Time from fixture start to first scored draft, tracked so added steps do not make the flow heavier than it needs to be.
