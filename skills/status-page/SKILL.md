---
name: status-page
description: Write and open a local HTML status page for the active solution (steps, sections, open items, blockers, evidence, team)
argument-hint: [03 Solution/active-solution folder]
allowed-tools: Bash(rfps-status-page:*), Bash(rfps-flow-status:*), Read
---

Build the local status page.

1. Run `rfps-status-page $ARGUMENTS` (use no arguments for the active solution). It refreshes `progress.md` through the flow status, reads the response markers, the compliance blockers, the evidence register and the roster, and writes `build/status.html` in the solution folder. The page is one file with no outside resources; nothing is uploaded.
2. Give the user the path as a link. If the app can render an HTML file, send it with `SendUserFile` (display `render`); otherwise tell them to open the file in a browser. Page tools in the built-in browser cannot act on local files, so do not try to click through it.
3. In two or three lines, say what is on the page: progress and next-up cards with copyable commands, the steps by group with filters, a tile for every response heading, every open marker with a link to its line (filter by decision, open, evidence needed or assertion), the blocking compliance checks, the evidence register, and the roster (unnamed Key Personnel in red). The search box filters all of them.
4. Remind the user it is a snapshot: rerun `/rfps:status-page` after changes to refresh it. The file lives in `build/`, which is git-ignored and a standard location, so it needs no provenance entry.

Do not change any response, register or report file.
