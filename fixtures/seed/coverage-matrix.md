# Coverage Matrix - Sample

Living document. The tables of requirements below are the source: the requirements-mapper skill, or a person, adds and edits rows in place by stable ID (R-001, R-002, ...). Never renumber or reuse an ID. Mark an implied requirement by appending *(implicit)* to its text. Blocks between `<!-- derived:... -->` markers are recomputed by `/rfps:refresh-reports`; do not edit inside them.

Seed for the sample solicitation: one row per obligation sentence in RFP DPW-2026-017 and Amendment 1, quoted verbatim. `fixtures/answer-key.toml` lists the same obligations; `smoke.sh` checks the sweep against it.

## Summary

<!-- derived:summary -->
<!-- /derived:summary -->

---

## Requirements by Section

### RFP 2 Scope of Work

| # | Requirement | Source | Mandatory | Evidence Source | Classification | Gap Severity | Recommended Action | Notes |
|---|-------------|--------|-----------|----------------|----------------|--------------|-------------------|-------|
| R-001 | The Contractor shall provide a web portal that lets garage supervisors schedule, reschedule and cancel maintenance appointments. | RFP 2.1 | Yes | E-001 | Grounded | - | Cite and ground | |
| R-002 | The Contractor shall migrate the County's existing maintenance history from the legacy spreadsheet system into the portal before go-live. | RFP 2.2 | Yes | E-002 | Grounded | - | Cite and ground | |
| R-003 | The Contractor shall send an email reminder to the responsible driver at least 3 days before each appointment. | RFP 2.3 | Yes | | Assertable | - | Assert with caveat | SMS optional per Amendment 1 |
| R-004 | The Contractor shall meet WCAG 2.1 AA accessibility for every public and staff page. | RFP 2.4 | Yes | E-003 | Grounded | - | Cite and ground | E-003 is not cleared |
| R-005 | The Contractor should provide a monthly utilization report to the Fleet Manager. | RFP 2.5 | No | | Assertable | - | Assert with caveat | |
| R-006 | The Contractor shall designate a Project Manager as Key Personnel, with at least 5 years of experience managing software delivery for public agencies. | RFP 2.6 | Yes | | Gap | Manageable | Seek evidence | Name and resume needed |

### RFP 3 and 5 Period, Submission

| # | Requirement | Source | Mandatory | Evidence Source | Classification | Gap Severity | Recommended Action | Notes |
|---|-------------|--------|-----------|----------------|----------------|--------------|-------------------|-------|
| R-007 | Go-live is required within 6 months of the Notice to Proceed. | RFP 3 | Yes | | Assertable | - | Assert with caveat | Changed to 7 months by Amendment 1 |
| R-008 | Proposals are due 2026-12-01 at 2:00 PM Eastern by email to procurement@riverbend.example. | RFP 5 | Yes | | Assertable | - | Assert with caveat | |
| R-009 | The narrative response shall not exceed 10 pages. | RFP 5 | Yes | | Assertable | - | Assert with caveat | |
| R-010 | Questions are due 2026-11-10. | RFP 5 | Yes | | Assertable | - | Assert with caveat | |
| R-011 | Section 3 go-live is extended from 6 months to 7 months of the Notice to Proceed. | Amendment 1 | Yes | | Assertable | - | Assert with caveat | Supersedes R-007 |

---

## Disqualifying Gaps

Mandatory requirements classified Gap with severity Disqualifying. The list is derived; the "Why" and "Possible Resolution" text is kept when you edit it.

<!-- derived:disqualifying -->
<!-- /derived:disqualifying -->

---

## Evidence Inventory Cross-Reference

| Collateral File | Type | Requirements Supported |
|----------------|------|----------------------|

---

## Open Questions

- [ ] R-006: who is the Project Manager? - Current classification: Gap - Would change to Grounded if resolved
