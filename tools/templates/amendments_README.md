# Amendments and Q&A

State amendments and Q&A answers change requirements, so they are logged here and trigger a re-run of the requirements analysis.

## When a new amendment or Q&A answer arrives
1. Save the original file in the source folder's `01 Solicitation Docs` (never edit it).
2. Add a row to `log.md`: number, date received, file name, a plain summary of what changed, and the requirement IDs affected.
3. Re-run the requirements analysis (requirements mapper), then `rfps-regen` if this solution uses generators, and check the compliance report for new or changed mandatory items.
4. Update `response/*.md` where a requirement or deadline changed, and the register if a claim is affected.
5. Re-read the amended solicitation for changes the amendment did not call out: a response can keep text for scope that a later amendment already removed.

## Why
A response written to the original Work Order can silently conflict with an amendment. Logging each change, and the requirement IDs it touches, is how conflicts get found before submission.
