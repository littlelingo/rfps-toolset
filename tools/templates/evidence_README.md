# Evidence register

`register.csv` is the single home for facts about the firm's past performance and practices. The response cites facts by ID, for example `[GROUNDED: E-003]`; the claim, numbers, source, and clearance status live here, not in the prose.

## Add past performance
1. Put the source file in the engagement's source folder (run `rfps-extract-docs` if you need its text).
2. Add a row: next free `E-nnn` (never reuse or renumber IDs), one approved sentence for `claim`, client, engagement, date, numbers, the exact source file and location, `clearance`, `verified` (date), `basis` (what you actually read), and `notes` (scrubs, redactions, caveats).
3. Cite the ID in `response/*.md`.
4. Run `/rfps:build-wip`. The report lists register rows that nothing cites, which is how you find new evidence you have not used yet.

## Columns
`id, claim, client, engagement, date, numbers, source, clearance, verified, basis, superseded_by, notes, ban_phrases`

## Clearance values
- `cleared`: approved for the State-facing response.
- `needs-permission`: usable in WIP; FINAL refuses until the client or owner agrees and the row is changed to `cleared`.
- `hold`: not verified (unsourced, unnamed, or only in a draft); FINAL refuses.
- `do-not-use`: known wrong or non-public; FINAL refuses.

## Replace or correct a fact
Add the corrected fact as a new row and put its ID in `superseded_by` on the old row. The build then warns (WIP) or refuses (FINAL) wherever the old ID is still cited, so old data cannot sneak back in.

## Banned phrases
`ban_phrases` holds phrases, separated by `;`, that must never appear in the response: a retired figure, a non-public detail, a wrong name. Bans apply to every row regardless of clearance, so a corrected fact can still ban the old wording. The build warns (WIP) or refuses (FINAL) if one appears.
