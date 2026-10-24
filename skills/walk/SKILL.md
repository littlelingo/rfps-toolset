---
name: walk
description: Walk the ranked worklist of gaps, decisions, evidence needs and weak spots one item at a time - the tools address it, the user addresses it, or it is skipped
argument-hint: [item id or kind]
disable-model-invocation: true
allowed-tools: Bash(rfps-worklist:*), Bash(rfps-open-items:*), Bash(rfps-refresh-reports:*), Bash(rfps-flow-status:*), Bash(rfps-register-add:*), Bash(rfps-sync-gdoc:*), Bash(rfps-sync-docx:*), Read, Write, Edit, Skill, AskUserQuestion
---

Read `${CLAUDE_PLUGIN_ROOT}/skills/solution-guide/references/conventions.md` first; its rules (sources of truth, no invented bidder facts, evidence register, outside sources) apply to this skill.

Work through what is left after the first WIP, one item at a time, so the user never faces the whole pile.

Before starting, bring in what others did in the shared document (follow `pull-wip`, with approval), so the list is current.

For each pass:

1. Run `rfps-worklist --next` (or `--next` after setting focus from `$ARGUMENTS`: an item id, or a kind such as "Decision"). If none are open, say so and point to `/rfps:status`.
2. Show the item in plain words: where it is (link to the line or row), why it matters, and what the tools can do about it. Mention how many are left.
3. Ask what to do, with the recommended choice first:
   - **Tool addresses it** - do the work (the section drafter for a missing section or weak requirement, `add-past-performance` for evidence, the checker named in the item's suggested move), show the before and after, and edit `response/*.md` or the register only after the user approves. Never invent bidder facts or mark evidence `cleared`; a decision that is the user's (a price, a person, a commitment, a clearance) is always asked, not guessed.
   - **I will address it** - `rfps-worklist --set <id> mine --note "<what and by when>"`.
   - **Skip for now** - `--set <id> skipped`.
   - **Not applicable** - `--set <id> skipped --note "not applicable: <why>"`.
4. After a tool-made change, run `rfps-open-items` and `rfps-refresh-reports`, record `--set <id> addressed`, and push the change to the shared document by following `build-wip` for just the touched sections. Items that came from a marker leave the list by themselves once the marker is gone. `rfps-worklist --set` also accepts a flow step id, so one command records every choice; `open-items.md` and the status page show your choice next to each marker.
5. Offer the next item as a question, never a list. Stop when the user says so; the list is recomputed from the files each time and only your choices are kept, in `.state/worklist.json`.

Related items (several `[EVIDENCE NEEDED]` markers for one source, or a gap and the compliance failure it causes) may be offered together, once, when one answer settles them.
