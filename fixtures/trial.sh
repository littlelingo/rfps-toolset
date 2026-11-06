#!/bin/sh
# Runs the analysis and drafting skills (extract, collateral-analyzer, requirements-mapper, section-drafter) with Claude
# on a throwaway copy of the fictional sample, to see how they perform. Uses the installed rfps plugin, makes model
# calls (takes a few minutes and costs tokens), and leaves the results in the folder it prints.
# Usage: fixtures/trial.sh [work folder]   (default: a new temp folder)
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
W=${1:-$(mktemp -d)}
export PATH="$HERE/../bin:$PATH"
mkdir -p "$W"; rm -rf "$W/capture"; cp -R "$HERE/sample-capture" "$W/capture"
cd "$W/capture"
rfps-new-engagement --source "$PWD" --title "Sample" >/dev/null
git -C "03 Solution/active-solution" add -A && git -C "03 Solution/active-solution" -c user.name=trial -c user.email=trial@example.com commit -qm baseline
run() {
  n=$1; shift; echo "== $n"
  # The Skill tool must be allowed, or a skill call errors and Claude follows SKILL.md by hand instead.
  claude -p "$*" --permission-mode acceptEdits --allowedTools "Skill,Bash,Read,Write,Edit,Glob,Grep" > "$W/$n.log" 2>&1
}
run 1-extract "Use the rfps:extract skill on '01 Solicitation Docs'. Do not ask me questions. Report the files written and where."
run 2-collateral "Use the rfps:collateral-analyzer skill on this solicitation folder. Do not ask me questions; record anything missing as a gap. Write brief.md and gap-report.md."
run 3-past-performance "Use the rfps:add-past-performance skill on the folder 'past-performance'. Do not ask me questions: show the proposed evidence rows, then write them, with clearance cleared only where the notes say the client approved use."
run 4-requirements "Use the rfps:requirements-mapper skill to build the coverage matrix for the active solution. Do not ask me questions. Then run rfps-refresh-reports --solution."
run 5-drafter "Use the rfps:section-drafter skill to draft all response sections for the active solution into response/*.md, grounded in the coverage matrix and the evidence register. Do not ask me questions. Then run rfps-build-response --solution --mode wip."
echo "Trial finished. Logs and results: $W (solution: $W/capture/03 Solution/active-solution)"
rfps-flow-status --table | head -12
