# Resource Plan - {title}

Living document. This file holds what the State requires and the rules for staffing; it does not list the proposed people. The roster of proposed roles and people is `response/resources.csv` (one row per role, edited in place by stable ID P-nnn, never renumbered or reused). Hours, rates and labor categories live in the staffing workbook (`staffing_xlsx` in solution.toml, normally `09 Pricing/Staffing.xlsx`). Blocks between `<!-- derived:... -->` markers are recomputed by `/rfps:refresh-reports`; do not edit inside them. Do not put a `|` character inside a cell.

## How the pieces fit

| File | Holds | Edited by |
|------|-------|-----------|
| This file | State requirements for roles (Q-nnn), the deliverables that need an owner (D-nnn), stated figures, and the derived checks | The resource-planner skill or a person |
| `response/resources.csv` | One row per proposed role: status, scope, responsibilities, value added, deliverables led, headcount, level of effort, phases, person, resume status, and whether the role is written up in the response | The resource-planner skill or a person |
| `response/*.md` | The written narrative for each role flagged `in_response = yes`, as a bold lead-in with the role name | A person, seeded by the skill |
| `Staffing.xlsx` | Labor category, allocation %, rate, and hours by phase per role, with cost and FTE totals | The person pricing the work. `rfps-staffing` syncs it with the roster both ways |

Roster columns: `id, role, status, source, requirement_ref, in_response, scope, responsibilities, value_added, deliverables, headcount, loe_pct, phases, person, resume, notes`.

- **status:** KP (Key Personnel the State requires), Recommended (the solicitation names or implies the role), Ours (our addition; say why in notes), or Dropped (kept for history, ignored by every check and count).
- **in_response:** yes if the role gets its own written narrative in the response. Key Personnel are always yes. Other roles are named in one summary sentence.
- **headcount and loe_pct:** FTE = headcount x loe_pct / 100. Two people at 50 percent is one FTE.
- **phases:** the phases the role is active in, for example `1;2;3`.
- **deliverables:** the deliverable names the role leads, separated by `;`, matching the names in the table below.
- **person:** a name or TBD. A name means the person is approved and available. The tools never invent a person.
- **resume:** Needed, Received, Checked, or N/A.

**Two-way sync with the workbook.** Person, resume, responsibility (the roster's `scope`) and allocation % (headcount x loe_pct) can be edited in either file; `rfps-staffing` carries a change from one side to the other, comparing both against what they agreed on at the last sync (`.state/staffing-sync.json`). A field changed on both sides to different values is reported as a conflict and left alone; `--prefer csv` or `--prefer xlsx` resolves it. Role title, status, source, `in_response`, deliverables, headcount and the long text are roster-only; labor category, rate and hours are workbook-only, and the roster's `phases` follow the workbook's hours once hours are entered. A role typed into the workbook without an ID is added to the roster as the next P-nnn with status Ours. Nothing is ever deleted on either side, and the sync refuses to run while the workbook is open in Excel.

The response carries a one-sentence team size between `<!-- derived:team-size -->` markers; the refresh keeps it in step with the roster.

## Checks

<!-- derived:summary -->
<!-- /derived:summary -->

---

## Figures stated by the solicitation

Total amount, level-of-effort minimums, period, or any other number the State gives that bounds staffing. Cite the document and section.

| Item | Value | Source | Notes |
|------|-------|--------|-------|

---

## Role requirements

What the State requires of each role. Roster rows point here with `requirement_ref`. Minimum LOE is a number (percent of working hours) or blank.

| # | Role | Source | Required qualifications | Minimum LOE % | Notes |
|---|------|--------|-------------------------|---------------|-------|

---

## Deliverables that need an owner

Each deliverable the Work Order requires. The checks report any deliverable that no active role leads.

| # | Deliverable | Due | Source |
|---|-------------|-----|--------|

---

## Price view

What the staffing workbook adds up to, how far it moves if the hours move, and how it sits against any ceiling or budget the solicitation states (put those in "Figures stated by the solicitation" above, with the words ceiling, budget, not-to-exceed or total amount in the Item). Computed from the workbook; it recommends nothing. The price is the pricer's decision, and anything in "Value arguments" is an argument to be tested, not a fact.

<!-- derived:priceview -->
<!-- /derived:priceview -->

### Value arguments

| # | Argument, in the agency's terms | Evidence (register ID or source) | Where it is made in the response |
|---|---------------------------------|----------------------------------|----------------------------------|
