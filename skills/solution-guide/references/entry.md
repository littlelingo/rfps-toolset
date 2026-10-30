# Entry check: start a new solution or join the one that exists

Used by `/rfps:start` and `/rfps:join`. Both run this check first, so a person never has to know which applies. Never create a solution where one exists, never offer "start over" (a fresh solution is a deliberate rename or archive done by hand), and never overwrite.

1. **Resolve.** Run `rfps-collab --resolve [<folder the user named>]`. It looks at the folder, in `active-solution/` inside it, and above it. If the user named no folder and the result is `none`, ask for the source (capture) folder and resolve that one.
2. **`state: none`** - there is no solution. Say so. If `looks_empty` is true, or the folder has no solicitation documents, confirm it is the right folder before creating anything. Then follow the start path (`/rfps:start`, intake onward). If this was reached from `/rfps:join`, say that nobody has started one here and ask whether to start it now.
3. **`state: found`** - a solution exists at `solution`. Tell the user in one line (title, where it is) and follow the join path below. If this was reached from `/rfps:start`, say that you are joining instead of starting.
4. **`state: many`** - list them and ask which one; never guess.

## Join path

1. Set the active solution: `rfps-use-solution "<solution>"`.
2. **Who you are:** `rfps-collab --whoami`. If it prints `(not set)`, ask the user for the name that should appear on claims and the lease and save it with `rfps-collab --whoami --set "<name>"` (kept on this machine only).
3. **This machine:** if the solution is in a Google Drive folder and `cache_dir` is not set, ask for a folder on this machine (suggest `~/rfps-cache`) and run `rfps-set-config cache_dir <path>`, so text caches and scratch builds are never synced to Drive. Check that the Google connector account is the one the user works in.
4. **Brief them:** run `rfps-collab --briefing` and `rfps-flow-status --table`. Give the progress line, who is writing now, what others have claimed, what changed recently, and any duplicate-ID warning (fix those first and tell the user which rows). If the shared WIP exists, read it as `/rfps:build-wip` describes and report the "waiting for people" counts.
5. **Catch up:** if the document has edits or comments the response files do not, offer `/rfps:pull-wip`. Ask what the person wants to take on and offer the unclaimed worklist items (`rfps-worklist --next 5`); claim what they choose with `rfps-worklist --set <id> mine --note "<what>"` (it records their name).
6. Do not rerun analysis, drafting or the WIP build because someone joined; those steps are already done or in progress. Offer the next open step with `/rfps:next` instead.
