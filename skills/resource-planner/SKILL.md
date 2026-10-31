---
name: resource-planner
description: Builds and maintains the roster of proposed roles and people (response/resources.csv), the State's role requirements (resource-plan.md), and the staffing and pricing workbook (Staffing.xlsx). Trigger when the user says "resource plan", "roles", "key personnel", "staffing plan", "who do we need", "level of effort", "how many people", "staffing workbook", or after the requirements mapper has recorded staffing requirements.
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

# Resource planner

## Inputs
- `coverage-matrix.md` and `brief.md` (staffing requirements, Key Personnel attachment, level-of-effort minimums, any total amount or budget figure)
- The solicitation documents named in `solution.toml` (read the staffing, Key Personnel, labor category and pricing sections directly; Key Personnel responsibilities are quoted from the attachment)
- `resource-plan.md` (the State's requirements, deliverables to cover, stated figures, derived checks; copy `assets/resource-plan-template.md` first if the solution does not have one)
- `response/resources.csv` (the roster; create it with the header from `tools/resources.py` if missing)
- User-supplied names, availability and resumes. Never invent a person, qualification or rate.

## Outputs
- `resource-plan.md`: rows in "Figures stated by the solicitation", "Role requirements" (Q-nnn) and "Deliverables that need an owner" (D-nnn).
- `response/resources.csv`: one row per proposed role.
- `Staffing.xlsx` in the pricing folder, created and kept in step by `rfps-staffing` (two-way with the roster).
- Draft narratives in the response for roles flagged `in_response = yes`, shown to the user before they are written.
- `/rfps:refresh-reports` afterward to recompute the Checks block and the team-size sentence.

## How the files divide the work
Requirements and rules live in `resource-plan.md`. Proposed roles and people live in the roster. The written story lives in the response. Hours and rates live in the workbook. Do not copy one into another by hand: the roster is the only place to add, change or drop a role. Read `resource-plan.md` ("How the pieces fit") for the column meanings and follow them exactly.

## Process
1. **Extract what the State says.** For every role the solicitation requires (Key Personnel), names or implies (deliverables that need a skill the Work Order lists), or bounds (minimum level of effort, period, total amount), record it with the document and section: required qualifications and minimum effort as Q-nnn rows, figures in the figures table, and every deliverable as a D-nnn row.
2. **Create the roster.** First pass:
   - One `KP` row for each Key Personnel role, with `in_response = yes`, `source` and `requirement_ref`, and an in-depth description: `scope` (one sentence), `responsibilities` (what the person does day to day, quoting the State's own description and adding what our approach requires), `value_added` (what the State gets from this role), `deliverables` (the deliverables the role leads), `loe_pct` at or above the State minimum, and `phases`.
   - Suggested `Recommended` or `Ours` rows that cover down the rest of the ask and the solution, each with the same description fields. A role we add that the State did not ask for is `Ours`, with the reason in `notes`.
   - Choose `in_response` for each non-Key-Personnel role: yes for roles that carry a lot of the work or answer an evaluation question, no for supporting roles (they are named in one summary sentence).
3. **Fill the rest.** `headcount` defaults to 1. `person` is TBD until the user names someone, and a named person is understood to be approved and available. `resume` is Needed for Key Personnel until it is received. Proposed `loe_pct` and `phases` are our assumptions until the user confirms them.
4. **Ask before assuming.** Ask the user which roles to add or drop, who could fill each, and whether anyone already has a resume. Outside sources (a rate sheet, an HR system, a drive) only with the user's yes; log them in `external-sources.md`.
5. **Drop, don't delete.** To remove a role, set `status` to Dropped and say why in `notes`. Never delete a row, renumber, or reuse an ID.
6. **Write the narratives.** For each `in_response = yes` role, draft a short narrative for the matching Management Approach subsection: a bold lead-in with the role name, what the person is responsible for, the value the role adds, and how it keeps sprint velocity, grounded in the roster fields and in the solicitation. Show the draft before writing it. After this first draft the response text is edited by hand; do not regenerate it over the user's edits. Add a `<!-- derived:team-size --> ... <!-- /derived:team-size -->` block where the team size should appear.
7. **Build and sync the workbook.** Run `rfps-staffing`. It builds the workbook from `tools/templates/staffing-template.xlsx` and then syncs it with the roster both ways (see "Two-way sync" in `resource-plan.md`): person, resume, responsibility and allocation % carry over from whichever side changed, roles added in the workbook become new roster rows, conflicts are reported and left alone, and nothing is deleted. New rows arrive with a suggested allocation % and hours by phase (allocation x phase months x hours per FTE-month) as ordinary numbers for the user to edit; `--seed-hours` fills only empty cells on existing rows; it never invents rates. Use `--check` to see pending changes without writing, and `--prefer csv|xlsx` to settle a conflict the user has decided.
8. **Check against the State's figures.** Compare the plan with any stated total amount or minimum effort and report mismatches. Do not compute cost without rates. Put any ceiling, budget or not-to-exceed figure in "Figures stated by the solicitation" with that word in the Item: the refresh then fills the Price view block (labor total by phase, the effect of a 10 percent move in hours, largest cost shares, the total against the stated figure). The price is the pricer's decision; report the view, never recommend a price. If the solicitation or the firm has a rate sheet (csv `labor_category,rate`), offer to record it as `rate_sheet` in `solution.toml`; the refresh then checks every labor category and rate in the workbook against it.
9. Run `rfps-refresh-reports --solution` and report the Checks block, with a link to [resource-plan.md](resource-plan.md) (relative path from the working directory).

## Rules
- The roster is the only place to add, edit or drop a role.
- Keep the solicitation's own role titles in the `role` column so the response and the plan match.
- Distinguish required (shall/must) from suggested (should/may) in `source` or `notes`.
- Pricing never goes in the roster or the response. Rates belong in the workbook.
- No `|` or line break inside a cell of resource-plan.md. CSV fields may use `;` to separate lists.

## Related
- Compliance rows for resumes and Key Personnel (the compliance validator) stay the source for pass/fail; this plan tracks who and what is needed to meet them.
