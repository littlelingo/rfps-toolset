---
description: Hard golden case. The empathy reviewer must flag subtle defects across a multi-paragraph section, leave the good paragraph alone, and rewrite without inventing facts.
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
runs: 3
---

Do an empathy and tone review of this draft section from our response to Riverbend County's fleet maintenance scheduling portal RFP. The client's own words: garage supervisors, preventive maintenance appointments, 420 fleet vehicles, the legacy spreadsheet system, the Fleet Manager. The full text is below; do not look for files. Mark each paragraph as needs changes or fine, with the issue and a suggested rewrite where it needs changes.

Paragraph 1: "Example Bidder LLC is a leading provider of robust, seamless scheduling solutions. Our proven methodology leverages synergies across the fleet lifecycle."

Paragraph 2: "The County's 420 vehicles are scheduled today on a legacy spreadsheet, and garage supervisors told the County they lose bay time when two appointments collide. Our portal gives each supervisor one calendar that refuses a double booking, so a preventive maintenance appointment either holds or is moved before the day it was due. [ASSERTION: the calendar rejects overlapping bookings for the same bay]"

Paragraph 3: "Our solution reduces maintenance costs by 40 percent and is the only portal that County fleets will ever need."

Paragraph 4: "Reminders will be sent and reports will be generated as needed. Issues will be escalated."
