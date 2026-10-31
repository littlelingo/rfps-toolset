# Evidence register

`register.csv` is the single home for facts about the firm's past performance and practices. The response cites facts by ID, for example `[GROUNDED: E-003]`; the claim, numbers, source, and clearance status live here, not in the prose.

## Add past performance
1. Put the source file in the engagement's source folder (run `rfps-extract-docs` if you need its text).
2. Add a row: next free `E-nnn` (never reuse or renumber IDs), one approved sentence for `claim`, client, engagement, date, numbers, the exact source file and location, `clearance`, `verified` (date), `basis` (what you actually read), and `notes` (scrubs, redactions, caveats).
3. Cite the ID in `response/*.md`.
4. Run `/rfps:build-wip`. The report lists register rows that nothing cites, which is how you find new evidence you have not used yet.

## Columns
`id, claim, client, engagement, date, numbers, source, clearance, verified, basis, superseded_by, notes, ban_phrases`, then the structured fields `start, end, value_usd, scope_tags, reference_contact, reference_confirmed, approved_by, approved_date, approval_ref`.

The structured fields are what the automated checks read. `start` and `end` (2024, 2024-03 or 2024-03-15; `end` may be `present`) feed the recency check, `value_usd` (digits, or 1.2M / 450K) the minimum-value check, `reference_contact` and `reference_confirmed` the reference check, and `approved_by`, `approved_date` and `approval_ref` record who agreed to use the fact and where the proof is (an email, a file path). Set the thresholds in `solution.toml` under `[past_performance]`; set `require_approval_ref = true` and FINAL refuses a `cleared` row with no `approval_ref`. Fill the fields on an existing row with `rfps-register-add --update E-003 --end 2024-06 --value-usd 1.2M`. Blank fields are reported as unknown, never as passing.

## Clearance values
- `cleared`: approved for the State-facing response.
- `needs-permission`: usable in WIP; FINAL refuses until the client or owner agrees and the row is changed to `cleared`.
- `hold`: not verified (unsourced, unnamed, or only in a draft); FINAL refuses.
- `do-not-use`: known wrong or non-public; FINAL refuses.

## Replace or correct a fact
Add the corrected fact as a new row and put its ID in `superseded_by` on the old row. The build then warns (WIP) or refuses (FINAL) wherever the old ID is still cited, so old data cannot sneak back in.

## Banned phrases
`ban_phrases` holds phrases, separated by `;`, that must never appear in the response: a retired figure, a non-public detail, a wrong name. Bans apply to every row regardless of clearance, so a corrected fact can still ban the old wording. The build warns (WIP) or refuses (FINAL) if one appears.
