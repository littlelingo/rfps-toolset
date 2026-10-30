---
description: Golden case. The compliance validator must fail a response that exceeds the page limit and omits a required section, instead of passing it.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
runs: 3
---

Act as the compliance validator on this summary of a drafted response. Everything you need is here; do not look for files. Give a pass, fail, partial or ambiguous for each check and say whether the response is ready to assemble.

Solicitation facts (RFP DPW-2026-017): the narrative response shall not exceed 10 pages. It is evaluated on Technical Approach, Management Plan, Past Performance and Executive Summary clarity. Proposals are due 2026-12-01 at 2:00 PM Eastern by email. A named Project Manager is required as Key Personnel (RFP 2.6).

The drafted response, as measured:
- Executive Summary: 700 words
- Technical Approach: 3,400 words
- Management Plan: 2,100 words
- There is no Past Performance section yet.
- The Project Manager is shown as "TBD".
- Total about 6,200 words. At about 500 words per page that is roughly 12 pages.
