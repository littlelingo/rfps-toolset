---
description: Hard golden case. The compliance validator must fail the planted defects, pass the items that are compliant, and not call the response ready.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
runs: 3
---

Act as the compliance validator on this summary of a drafted response. Everything you need is here; do not look for files. Give a pass, fail, partial or ambiguous for each numbered check, with a one-line reason, and say whether the response is ready to assemble.

Solicitation facts (RFP DPW-2026-017 as amended): the narrative response shall not exceed 10 pages. It is evaluated on Technical Approach, Management Plan, Past Performance and Executive Summary clarity. Proposals are due 2026-12-01 at 2:00 PM Eastern by email to procurement@riverbend.example. A named Project Manager with at least 5 years of experience is required as Key Personnel (RFP 2.6). Go-live is required within 7 months of the Notice to Proceed (Amendment 1). Email reminders at least 3 days before each appointment are required (RFP 2.3); SMS is optional.

The drafted response, as measured:
- Executive Summary: 700 words. Technical Approach: 3,400 words. Management Plan: 2,100 words. There is no Past Performance section yet. Total about 6,200 words, roughly 12 pages at about 500 words per page.
- The Project Manager is shown as "TBD".
- The schedule section commits to go-live within 7 months of the Notice to Proceed and says reminders are emailed 3 days before each appointment. SMS is not offered.
- The submission plan is to email the package to procurement@riverbend.example on 2026-11-30.

Checks: 1 page limit; 2 evaluated sections present; 3 Key Personnel named; 4 go-live period; 5 reminder requirement; 6 submission method and date.
