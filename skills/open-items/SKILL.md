---
name: open-items
description: List every decision, open question, evidence gap and assertion left in the response, with links to each line
argument-hint: [mark]
allowed-tools: Bash(rfps-open-items:*), Read
---

Show what is still open in `response/*.md`.

1. Run `rfps-open-items`. If `$ARGUMENTS` is `mark`, run `rfps-open-items --mark` instead; that adds or refreshes the colored icons in the response files (🔴 DECISION, 🟠 OPEN, 🟣 EVIDENCE NEEDED, 🟡 ASSERTION, 🟢 GROUNDED) and is the only way this command changes response files. Without `mark`, change nothing in the response.
2. Report the counts by type and link `open-items.md` in the solution folder. Once the shared WIP docx exists, each item links to its section in that document and shows the text to search for; when the user wants to jump to one, run `rfps-open-doc --section "<section>" --find "<search text>"` (opens the file and copies the search text). Name the two or three items that would unblock the most (decisions first), quoting each marker's section and its first words.
3. If the response files lack the icons, say that `/rfps:open-items mark` adds them.
4. Offer to work through the decisions one at a time. The marker is removed by replacing it with the final text; `open-items.md` drops it the next time it is regenerated (this command, or `/rfps:refresh-reports`).
