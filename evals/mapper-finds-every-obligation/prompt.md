---
description: Golden case. The requirements mapper must find every obligation in the sample RFP, apply the amendment, and not treat a should as mandatory (answer key in fixtures/answer-key.toml).
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
runs: 3
---

Use the requirements mapper approach on the solicitation text below. The full text is here; do not look for files. List every requirement as a numbered list with its source clause, whether it is mandatory, and anything an amendment changes. Quote each requirement.

RFP DPW-2026-017 (Riverbend County Department of Public Works), Fleet Maintenance Scheduling Portal

2.1 The Contractor shall provide a web portal that lets garage supervisors schedule, reschedule and cancel maintenance appointments.
2.2 The Contractor shall migrate the County's existing maintenance history from the legacy spreadsheet system into the portal before go-live.
2.3 The Contractor shall send an email reminder to the responsible driver at least 3 days before each appointment.
2.4 The Contractor shall meet WCAG 2.1 AA accessibility for every public and staff page.
2.5 The Contractor should provide a monthly utilization report to the Fleet Manager.
2.6 The Contractor shall designate a Project Manager as Key Personnel, with at least 5 years of experience managing software delivery for public agencies.
3. Twelve months from the Notice to Proceed, with two optional one-year extensions. Go-live is required within 6 months of the Notice to Proceed.
4. Proposals are evaluated on: Technical Approach (40 percent), Management Plan (30 percent), Past Performance (20 percent) and Executive Summary clarity (10 percent). Price is evaluated separately.
5. Proposals are due 2026-12-01 at 2:00 PM Eastern by email to procurement@riverbend.example. The narrative response shall not exceed 10 pages. Questions are due 2026-11-10.

Amendment 1: Question 1: Is SMS reminder required? Answer: No. Email reminders in 2.3 are sufficient; SMS is optional. Change: Section 3 go-live is extended from 6 months to 7 months of the Notice to Proceed. This amendment supersedes the base RFP where they differ.
