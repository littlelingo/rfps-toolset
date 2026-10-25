# Status pane

A live pane beside the chat in Claude Desktop (and the VS Code extension) for the RFP toolset.

- Open it with `/rfps-pane` or `/rfps-status-pane`. It never opens by itself: starting a session only makes the two commands available, so nothing appears and nothing runs in a session that does not want the pane.
- It reads the live status by running `rfps-status-page --json` against the active solution (found from the current directory), reads the status when you open it and then refreshes every minute while the session lasts, and shows steps, response sections, open items, blocking compliance checks, the evidence register and the team roster.
- Buttons put the next action in the prompt box (never send it), copy a command, or ask Claude to open a file at a line in the file pane.
- Check it: `claude plugin validate .` and `claude plugin test .` from the plugin folder.

It needs no setup. If a mod prompt asks to turn on mods, answer yes once. The pane draws only from the app's fixed elements, so it approximates the layout of `build/status.html` (`/rfps-status-page`) and cannot embed it.
