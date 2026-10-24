---
name: step
description: Mark a flow step done, skipped / not applicable, or back to detected
argument-hint: <step id> done|skip|reset
disable-model-invocation: true
allowed-tools: Bash(rfps-flow-status:*)
---

Run `rfps-flow-status --set $ARGUMENTS`, then `rfps-flow-status` and report the one-line progress and the changed step. The user's mark is stored in progress.md (`[x]` done, `[-]` skipped / not applicable, `[ ]` detected) and wins over detection. If the step id is unknown, list the valid ids.
