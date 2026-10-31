#!/bin/sh
# End-to-end check of the rfps flow on the fictional sample: scaffold, seed, reports, WIP build, FINAL build,
# plus a negative case (FINAL must refuse evidence that is not cleared). Usage: fixtures/smoke.sh
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH="$HERE/../bin:$PATH"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
uv run --quiet "$HERE/build_sample.py" "$T/capture" >/dev/null
cd "$T/capture"
rfps-new-engagement --source "$T/capture" --title "Sample" >/dev/null
printf 'wip_format = "docx"\n' >> active-solution/solution.toml   # this script tests the Word route; gdoc_test.py tests Google
rfps-add-source "$T/capture/past-performance" --label notes >/dev/null
grep -q 'path = "../past-performance"' active-solution/past-performance/sources.toml || { echo "FAIL: source path is not relative" >&2; exit 1; }
# shared WIP docx: created from the (still empty) template, then the seed text arrives as tracked changes
rfps-sync-docx >/dev/null
test -f "05 Draft Response/Response Template_WIP.docx"
# past-performance sources: scan for new and changed files, digest, Drive listing comparison, safe register rows
out=$(rfps-scan-sources); echo "$out" | grep -q "1 new, 0 changed" || { echo "FAIL: first scan should find 1 new file: $out" >&2; exit 1; }
grep -q "Permission wording" active-solution/past-performance/digest.md && grep -qi "approved" active-solution/past-performance/digest.md || { echo "FAIL: digest lacks the permission wording" >&2; exit 1; }
rfps-scan-sources | grep -q "0 new, 0 changed" || { echo "FAIL: a second scan should find nothing" >&2; exit 1; }
mkdir -p past-performance/a/b/c/d && printf 'Deep note 2024 approved' > past-performance/a/b/c/d/deep.txt && printf 'x' > past-performance/a/old.doc
out=$(rfps-scan-sources); echo "$out" | grep -q "deep.txt" && echo "$out" | grep -q "level 4" && echo "$out" | grep -q "NOT READ.*\.doc" || { echo "FAIL: deep folder or unsupported type not reported: $out" >&2; exit 1; }
rm -rf past-performance/a
rfps-scan-sources >/dev/null
printf '{"doc_id":"1AbCdEfGhIjKlMn","email":"x"}' > "past-performance/Case Study.gdoc"
out=$(rfps-scan-sources); echo "$out" | grep -q "1 Google-format file" && echo "$out" | grep -q "1AbCdEfGhIjKlMn" || { echo "FAIL: Google pointer file not routed to the connector: $out" >&2; exit 1; }
out=$(rfps-scan-sources); echo "$out" | grep -c "1AbCdEfGhIjKlMn" | grep -q "^1$" || { echo "FAIL: pointer listed twice" >&2; exit 1; }
rm "past-performance/Case Study.gdoc"
uv run --quiet --with python-docx python3 - past-performance/*.docx <<'PY'
import sys, docx
d = docx.Document(sys.argv[1]); d.add_paragraph("Update 2026: added a new reference."); d.save(sys.argv[1])
PY
rfps-scan-sources | grep -q "1 new, 1 changed\|0 new, 1 changed" || { echo "FAIL: an edited file should be reported as changed" >&2; exit 1; }
rfps-add-source FOLDER123 --type drive --label drivefolder >/dev/null
printf '[{"id":"f1","title":"Case A.docx","mimeType":"x","modifiedTime":"2026-01-01T00:00:00Z","size":"10"},{"id":"f2","title":"Case B.pdf","mimeType":"x","modifiedTime":"2026-01-02T00:00:00Z","size":"20"}]' > "$T/listing.json"
printf '[{"id":"d1","title":"Sub","path":"Sub","mimeType":"application/vnd.google-apps.folder"},{"id":"f1","title":"Case A.docx","path":"Sub/Case A.docx","mimeType":"x","modifiedTime":"2026-01-01T00:00:00Z","size":"10"}]' > "$T/deep.json"
rfps-scan-sources --drive drivefolder --listing "$T/deep.json" | grep -q "NOT YET LISTED" || { echo "FAIL: an unlisted Drive subfolder was not flagged" >&2; exit 1; }
rfps-scan-sources --drive drivefolder --listing "$T/listing.json" | grep -q "2 new or changed" || { echo "FAIL: Drive listing should show 2 new" >&2; exit 1; }
mkdir -p active-solution/.state/text/past-performance/drivefolder
printf 'Case A text approved 2025 $1.2M' > active-solution/.state/text/past-performance/drivefolder/f1.txt
printf 'Case B text' > active-solution/.state/text/past-performance/drivefolder/f2.txt
rfps-scan-sources --drive drivefolder --ingest | grep -q "Recorded 2 of 2" || { echo "FAIL: ingest" >&2; exit 1; }
printf '[{"id":"f1","title":"Case A.docx","mimeType":"x","modifiedTime":"2026-01-01T00:00:00Z","size":"10"},{"id":"f2","title":"Case B.pdf","mimeType":"x","modifiedTime":"2026-02-02T00:00:00Z","size":"20"}]' > "$T/listing.json"
rfps-scan-sources --drive drivefolder --listing "$T/listing.json" | grep -q "1 new or changed file(s), 1 unchanged" || { echo "FAIL: only the modified Drive file should be pending" >&2; exit 1; }
if rfps-register-add --claim "x" --client c --clearance cleared >/dev/null 2>&1; then echo "FAIL: cleared without confirmation was accepted" >&2; exit 1; fi
rfps-register-add --claim "Test fact" --client c --source s | grep -q "E-001" || { echo "FAIL: first register row should be E-001" >&2; exit 1; }
grep -q ",hold," active-solution/evidence/register.csv || { echo "FAIL: default clearance should be hold" >&2; exit 1; }
rfps-register-add --claim "Second" --client c --clearance cleared --confirm-cleared | grep -q "E-002" || { echo "FAIL: confirmed cleared row" >&2; exit 1; }
: > active-solution/evidence/register.csv && cp "$HERE/seed/register.csv" active-solution/evidence/register.csv   # the seed register for the rest of this script
cp "$HERE"/seed/response/*.md active-solution/response/
cp "$HERE/seed/register.csv" active-solution/evidence/register.csv
# requirement sweep against the answer key: with no requirement rows every obligation is unmapped, and the sweep finds exactly the keyed ones
rfps-sweep --json > "$T/sweep.json"
uv run --quiet python3 - "$HERE/answer-key.toml" "$T/sweep.json" <<'PY'
import json, sys, tomllib
key = tomllib.load(open(sys.argv[1], "rb"))["obligation"]; got = json.load(open(sys.argv[2]))["unmapped"]
miss = [k["id"] for k in key if not any(k["quote"].lower() in g["text"].lower() and g["cls"] == k["class"] for g in got)]
extra = [g["text"][:60] for g in got if not any(k["quote"].lower() in g["text"].lower() for k in key)]
sys.exit(f"sweep missed {miss}; sweep found unkeyed {extra}" if miss or extra else 0)
PY
if rfps-sweep --check >/dev/null 2>&1; then echo "FAIL: sweep --check passed with no requirement rows" >&2; exit 1; fi
# the harder solicitation (buried obligations, a table, a footnote, an amendment that changes three values): same check, plus the hard eval embeds it verbatim
mkdir -p "$T/hard" && cp "$HERE/hard-rfp.txt" "$T/hard/hard-rfp.txt"
rfps-sweep --json --text-dir "$T/hard" > "$T/hard.json"
uv run --quiet python3 - "$HERE/hard-answer-key.toml" "$T/hard.json" "$HERE/hard-rfp.txt" "$HERE/../evals/mapper-finds-buried-obligations/prompt.md" <<'PY'
import json, sys, tomllib
key = tomllib.load(open(sys.argv[1], "rb"))["obligation"]; got = json.load(open(sys.argv[2]))["unmapped"]
miss = [k["id"] for k in key if not any(k["quote"].lower() in g["text"].lower() and g["cls"] == k["class"] for g in got)]
extra = [g["text"][:60] for g in got if not any(k["quote"].lower() in g["text"].lower() for k in key)]
if miss or extra: sys.exit(f"hard sweep missed {miss}; found unkeyed {extra}")
if not open(sys.argv[4]).read().endswith(open(sys.argv[3]).read()): sys.exit("evals/mapper-finds-buried-obligations/prompt.md no longer embeds fixtures/hard-rfp.txt verbatim")
PY
cp active-solution/coverage-matrix.md "$T/cm-empty.md"   # restored after the sweep checks so the worklist checks below start from an empty matrix
cp "$HERE/seed/coverage-matrix.md" active-solution/coverage-matrix.md
rfps-sweep | grep -q "11 obligation sentence(s) in 2 file(s); 11 covered by a requirement row, 0 unmapped" || { echo "FAIL: the seed matrix should cover every obligation" >&2; rfps-sweep >&2; exit 1; }
rfps-sweep --check >/dev/null
rfps-refresh-reports --solution >/dev/null
grep -q "Solicitation obligations all mapped | Pass" active-solution/compliance-report.md && grep -q "Quoted RFP language found in the solicitation | Pass" active-solution/compliance-report.md || { echo "FAIL: autochecks for the seed matrix should pass" >&2; grep -n "Solicitation obligations\|Quoted RFP" active-solution/compliance-report.md >&2; exit 1; }
# a dropped row, a paraphrased row and a misquoted row are each caught
grep -v '^| R-009 ' active-solution/coverage-matrix.md > "$T/cm.md" && cp active-solution/coverage-matrix.md "$T/cm-full.md" && cp "$T/cm.md" active-solution/coverage-matrix.md
if rfps-sweep --check >/dev/null 2>&1; then echo "FAIL: a missing row for the page limit was not caught" >&2; exit 1; fi
rfps-refresh-reports --solution >/dev/null
grep -q "Solicitation obligations all mapped | Open.*shall not exceed 10 pages" active-solution/compliance-report.md || { echo "FAIL: refresh did not report the unmapped page limit" >&2; exit 1; }
cp "$T/cm-full.md" active-solution/coverage-matrix.md
sed -i.bak 's/^| R-004 | The Contractor shall meet WCAG 2.1 AA accessibility for every public and staff page\./| R-004 | The Contractor shall meet WCAG 2.2 AAA accessibility for every public and staff page./' active-solution/coverage-matrix.md && rm active-solution/coverage-matrix.md.bak
rfps-refresh-reports --solution >/dev/null
grep -q "Quoted RFP language found in the solicitation | Open.*not found verbatim: R-004" active-solution/compliance-report.md || { echo "FAIL: a misquoted requirement was not caught" >&2; exit 1; }
cp "$T/cm-empty.md" active-solution/coverage-matrix.md
rfps-refresh-reports --solution >/dev/null
# bid decision, win strategy (themes, page budget, weights on the worklist) and the second reader's ratings; scaffolds are restored afterwards
for f in capture.md win-strategy.md evaluation-sim.md solution.toml; do cp "active-solution/$f" "$T/$f.bak"; done
rfps-flow-status --table | grep -q "bid decision not recorded" || { echo "FAIL: an Undecided capture.md should leave the bid step open" >&2; exit 1; }
cp "$HERE/seed/capture.md" active-solution/capture.md
rfps-flow-status --table | grep -q "Go, pWin 55%" || { echo "FAIL: a recorded Go decision was not read" >&2; exit 1; }
cp "$HERE/seed/win-strategy.md" active-solution/win-strategy.md
printf 'page_limit = 10\n' >> active-solution/solution.toml
rfps-flow-status --table | grep -q "4 factor(s), 3 theme(s)" || { echo "FAIL: the win strategy was not read" >&2; exit 1; }
sed 's/| Your maintenance history/| (proposed) Your maintenance history/' active-solution/win-strategy.md > "$T/ws-prop.md" && cp active-solution/win-strategy.md "$T/ws-keep.md" && cp "$T/ws-prop.md" active-solution/win-strategy.md
rfps-flow-status --table | grep -q "1 proposed theme(s) waiting for your approval: T-02" || { echo "FAIL: a proposed theme should wait for approval in the flow" >&2; exit 1; }
cp "$T/ws-keep.md" active-solution/win-strategy.md
rfps-refresh-reports --solution >/dev/null
grep -q "Win themes carried through the response | Pass" active-solution/compliance-report.md || { echo "FAIL: seed themes should be carried through the seed response" >&2; grep -n "Win themes" active-solution/compliance-report.md >&2; exit 1; }
grep -q "Page budget by evaluation factor | Open.*Technical Approach" active-solution/compliance-report.md || { echo "FAIL: the thin seed sections should be far under their page budget" >&2; exit 1; }
grep -q "T-01 We have built this exact portal before | scheduling portal | Executive Summary, Past Performance" active-solution/win-strategy.md || { echo "FAIL: theme table not filled in" >&2; exit 1; }
sed -i.bak 's/| scheduling portal |$/| zzz phrase |/' active-solution/win-strategy.md && rm active-solution/win-strategy.md.bak
rfps-refresh-reports --solution >/dev/null
grep -q "Win themes carried through the response | Open.*T-01 is not in the executive summary" active-solution/compliance-report.md || { echo "FAIL: a theme missing from the response was not caught" >&2; exit 1; }
cp "$HERE/seed/win-strategy.md" active-solution/win-strategy.md
rfps-worklist --json | grep -q '\[40% factor\]' || { echo "FAIL: markers in the 40 percent factor should be marked on the worklist" >&2; exit 1; }
cp "$HERE/seed/evaluation-sim.md" active-solution/evaluation-sim.md
rfps-refresh-reports --solution | grep -q "evaluation-sim.md: 4 factor" || { echo "FAIL: ratings not read" >&2; exit 1; }
grep -q "Weighted score" active-solution/evaluation-sim.md && grep -q "Technical Approach (Marginal)" active-solution/evaluation-sim.md || { echo "FAIL: evaluation summary not filled in" >&2; exit 1; }
rfps-worklist --table | grep -q "Weak factor (Marginal)" || { echo "FAIL: a Marginal factor should be on the worklist" >&2; exit 1; }
rfps-flow-status --table | grep -q "1 factor(s) rated in the bottom of the scale: Technical Approach" || { echo "FAIL: the second reader's weakest factor not shown in the flow" >&2; exit 1; }
for f in capture.md win-strategy.md evaluation-sim.md solution.toml; do cp "$T/$f.bak" "active-solution/$f"; done
rfps-refresh-reports --solution >/dev/null
# validation staleness, amendments, the submission checklist and the PDF final gate; restored afterwards
cp active-solution/solution.toml "$T/sol3.bak"; cp active-solution/amendments/log.md "$T/amlog.bak"; cp active-solution/submission.md "$T/sub3.bak"; cp active-solution/response/02-technical-approach.md "$T/resp02.bak"
printf 'tone review notes\n' > active-solution/review-notes.md
rfps-flow-status --validated empathy | grep -q "Recorded 4 response file" || { echo "FAIL: --validated did not record the response files" >&2; exit 1; }
rfps-flow-status --table | grep -q "reviewed; no section has changed since" || { echo "FAIL: an unchanged review should read as current" >&2; exit 1; }
printf '\nOne more sentence.\n' >> active-solution/response/02-technical-approach.md
rfps-flow-status --table | grep -q "1 section(s) changed since the tone review: 02-technical-approach.md" || { echo "FAIL: the edited section was not named as stale" >&2; exit 1; }
rfps-refresh-reports --solution >/dev/null
grep -q "Tone review matches the current text | Open.*02-technical-approach.md" active-solution/compliance-report.md || { echo "FAIL: stale review not in the automated checks" >&2; exit 1; }
cp "$T/resp02.bak" active-solution/response/02-technical-approach.md; rm active-solution/review-notes.md active-solution/.state/validated.json
printf '| 1 | Amendment | 2026-10-25 | Amendment 1.docx | Go-live extended to 7 months | R-007 | No | No |\n' >> active-solution/amendments/log.md
rfps-worklist --table | grep -q "Amendment not applied" || { echo "FAIL: an unapplied amendment should be on the worklist" >&2; exit 1; }
sed -i.bak 's/| R-007 | No | No |/| R-007 | Yes | Yes |/' active-solution/amendments/log.md && rm active-solution/amendments/log.md.bak
if rfps-worklist --table | grep -q "Amendment not applied"; then echo "FAIL: an applied amendment should leave the worklist" >&2; exit 1; fi
cp "$T/amlog.bak" active-solution/amendments/log.md
printf '| M-01 | Signed Attachment B (Certifications) | RFP 6 | Pat | 2020-01-01 | Open | |\n' >> active-solution/submission.md
rfps-worklist --table | grep -q "Overdue submission step" || { echo "FAIL: an overdue form should be on the worklist" >&2; exit 1; }
rfps-refresh-reports --solution >/dev/null
grep -q "Submission checklist | Open.*overdue: M-01" active-solution/compliance-report.md || { echo "FAIL: overdue form not in the automated checks" >&2; exit 1; }
printf 'page_limit = 10\n[final_gate]\nrequired_text = ["Attachment B"]\nmargin_inches = 1.0\n' >> active-solution/solution.toml
uv run --quiet "$HERE/make_pdf.py" clean "$T/clean.pdf"; uv run --quiet "$HERE/make_pdf.py" defects "$T/defects.pdf"
if rfps-final-gate --pdf "$T/clean.pdf" >/dev/null 2>&1; then echo "FAIL: the gate passed with an open mandatory form" >&2; exit 1; fi
grep -q "Mandatory forms and steps in submission.md are done | Fail.*M-01" active-solution/final-gate.md || { echo "FAIL: open form not reported by the gate" >&2; exit 1; }
sed -i.bak 's/| 2020-01-01 | Open |/| 2020-01-01 | Done |/' active-solution/submission.md && rm active-solution/submission.md.bak
rfps-final-gate --pdf "$T/clean.pdf" >/dev/null || { echo "FAIL: a clean PDF with every form done should pass" >&2; cat active-solution/final-gate.md >&2; exit 1; }
rfps-flow-status --table | grep -q "clean.pdf passed" || { echo "FAIL: the flow did not show the gate result" >&2; exit 1; }
if rfps-final-gate --pdf "$T/defects.pdf" --scrub >/dev/null 2>&1; then echo "FAIL: the gate passed a PDF with planted defects" >&2; exit 1; fi
for want in "Page count within page_limit | Fail" "No internal markers, register IDs or placeholders | Fail" "Required wording present: Attachment B | Fail" "No links to Google Docs, Drive or local addresses | Fail" "Metadata free of names and emails | Fail"; do
  grep -qF "$want" active-solution/final-gate.md || { echo "FAIL: the gate missed: $want" >&2; exit 1; }
done
test -f "$T/defects_scrubbed.pdf" || { echo "FAIL: --scrub wrote no cleaned copy" >&2; exit 1; }
rfps-final-gate --pdf "$T/defects_scrubbed.pdf" | grep -q "Metadata free of names and emails | Pass" || { echo "FAIL: the cleaned copy still has personal metadata" >&2; exit 1; }
cp "$T/sol3.bak" active-solution/solution.toml; cp "$T/sub3.bak" active-solution/submission.md; rm -f active-solution/final-gate.md
rfps-refresh-reports --solution >/dev/null
# structured evidence fields, recency and value rules, approval proof, figures that disagree, the price view and the rate sheet; restored afterwards
cp active-solution/solution.toml "$T/sol4.bak"; cp active-solution/evidence/register.csv "$T/reg4.bak"; cp active-solution/response/02-technical-approach.md "$T/r02.bak"; cp active-solution/response/03-management-plan.md "$T/r03.bak"
rfps-register-add --update E-002 --value-usd 450K >/dev/null && grep -q ",450K," active-solution/evidence/register.csv || { echo "FAIL: --update did not set a structured field" >&2; exit 1; }
if rfps-register-add --update E-002 --clearance cleared >/dev/null 2>&1; then echo "FAIL: --update accepted clearance without --confirm-cleared" >&2; exit 1; fi
printf '[past_performance]\nmax_age_years = 1\nmin_value_usd = 1000000\nmin_references = 2\nreference_max_age_days = 1\n' >> active-solution/solution.toml
rfps-refresh-reports --solution >/dev/null
for want in "ended within 1 years) | Open" "minimum value (\$1,000,000) | Open.*E-002" "Enough qualifying references (2 distinct clients) | Open.*none" "confirmed within 1 days | Open"; do
  grep -q "$want" active-solution/compliance-report.md || { echo "FAIL: past-performance rule not reported: $want" >&2; grep -n "Cited work\|qualifying\|Reference contacts" active-solution/compliance-report.md >&2; exit 1; }
done
cp "$T/sol4.bak" active-solution/solution.toml
printf '[past_performance]\nmax_age_years = 100\nmin_value_usd = 100000\nmin_references = 2\nreference_max_age_days = 100000\n' >> active-solution/solution.toml
rfps-refresh-reports --solution >/dev/null
for want in "recent enough (ended within 100 years) | Pass" "minimum value (\$100,000) | Pass" "Enough qualifying references (2 distinct clients) | Pass" "confirmed within 100000 days | Pass"; do
  grep -q "$want" active-solution/compliance-report.md || { echo "FAIL: past-performance rule should pass: $want" >&2; exit 1; }
done
cp "$T/sol4.bak" active-solution/solution.toml
printf 'require_approval_ref = true\n' > "$T/strict.toml"; cat "$T/sol4.bak" "$T/strict.toml" > active-solution/solution.toml
rfps-refresh-reports --solution >/dev/null
grep -q "Cleared evidence records its approval proof | Fail.*E-002" active-solution/compliance-report.md || { echo "FAIL: a cleared row with no approval_ref should fail when proof is required" >&2; exit 1; }
if rfps-build-response --solution --mode final >/dev/null 2>&1; then echo "FAIL: FINAL accepted a cleared row with no approval proof" >&2; exit 1; fi
rfps-register-add --update E-002 --approved-by "Lakeshore IT manager (fictional)" --approved-date 2026-10-20 --approval-ref "email of 2026-10-20 (fictional)" >/dev/null
rfps-build-response --solution --mode final >/dev/null || { echo "FAIL: FINAL should build once the approval proof is recorded" >&2; exit 1; }
rm -f "11 Final Submission"/*_FINAL.docx active-solution/build/*_FINAL.docx
cp "$T/sol4.bak" active-solution/solution.toml; cp "$T/reg4.bak" active-solution/evidence/register.csv
sed -i.bak 's/within 7 months of the Notice to Proceed (Amendment 1)/within 6 months of the Notice to Proceed (Amendment 1)/' active-solution/response/03-management-plan.md && rm active-solution/response/03-management-plan.md.bak
sed -i.bak 's/at least 3 days before each appointment/at least 2 days before each appointment/' active-solution/response/02-technical-approach.md && rm active-solution/response/02-technical-approach.md.bak
rfps-refresh-reports --solution >/dev/null
grep -q "Numbers match the solicitation | Open.*superseded\|Numbers match the solicitation | Open.*replaced" active-solution/compliance-report.md || { echo "FAIL: a figure an amendment replaced was not caught" >&2; grep -n "Numbers match" active-solution/compliance-report.md >&2; exit 1; }
rfps-consistency | grep -q "2 day" || { echo "FAIL: a figure below the solicitation minimum was not listed" >&2; exit 1; }
cp "$T/r02.bak" active-solution/response/02-technical-approach.md; cp "$T/r03.bak" active-solution/response/03-management-plan.md
rfps-refresh-reports --solution >/dev/null
grep -q "Numbers match the solicitation | Pass" active-solution/compliance-report.md || { echo "FAIL: the seed response should agree with the solicitation" >&2; grep -n "Numbers match" active-solution/compliance-report.md >&2; exit 1; }
# writing lint, the requirement cross-reference, the exhibit plan, questions to the agency and the new flow steps; restored afterwards
cp active-solution/coverage-matrix.md "$T/cm5.bak"; cp active-solution/win-strategy.md "$T/ws5.bak"; cp active-solution/questions.md "$T/q5.bak"; cp active-solution/solution.toml "$T/sol5.bak"
cp active-solution/response/02-technical-approach.md "$T/p502.bak"; cp active-solution/response/03-management-plan.md "$T/p503.bak"
rfps-flow-status --table | grep -q "Questions to the agency drafted" && rfps-flow-status --table | grep -q "Outcome, agency feedback and lessons captured" || { echo "FAIL: the questions and debrief steps are missing from the flow" >&2; exit 1; }
printf '\nOur robust, seamless platform from a world-class team will be deployed. The checks will be run. Reports will be written. Users will be trained. Training will be scheduled. We use the XYZ module and our team leverages synergies.\n\nThe portal gives each supervisor one calendar that refuses a double booking, so a preventive maintenance appointment either holds or is moved before the day it was due, and supervisors stop losing bay time to collisions.\n' >> active-solution/response/02-technical-approach.md
printf '\nThe portal gives each supervisor one calendar that refuses a double booking, so a preventive maintenance appointment either holds or is moved before the day it was due, and supervisors stop losing bay time to collisions.\n' >> active-solution/response/03-management-plan.md
rfps-refresh-reports --solution >/dev/null
for want in "Writing: no empty superlatives or buzzwords | Open.*Technical Approach" "commitments name who does them | Open" "acronyms defined on first use | Open.*XYZ" "no near-duplicate paragraphs across sections | Open"; do
  grep -q "$want" active-solution/compliance-report.md || { echo "FAIL: the lint missed: $want" >&2; grep -n "Writing:" active-solution/compliance-report.md >&2; exit 1; }
done
rfps-lint | grep -q "superlatives: 1" || { echo "FAIL: rfps-lint did not list the planted superlatives" >&2; exit 1; }
printf '\n[lint]\nmute = ["superlatives"]\n' >> active-solution/solution.toml
rfps-refresh-reports --solution >/dev/null
grep -q "Writing: no empty superlatives or buzzwords | Info | muted in solution.toml" active-solution/compliance-report.md || { echo "FAIL: a muted lint rule should be reported as muted" >&2; exit 1; }
cp "$T/sol5.bak" active-solution/solution.toml; cp "$T/p502.bak" active-solution/response/02-technical-approach.md; cp "$T/p503.bak" active-solution/response/03-management-plan.md
cp "$HERE/seed/coverage-matrix.md" active-solution/coverage-matrix.md; cp "$HERE/seed/win-strategy.md" active-solution/win-strategy.md
rfps-crossref | grep -q "0 mandatory with no answering section found" || { echo "FAIL: every seed requirement should be answered somewhere" >&2; rfps-crossref >&2; exit 1; }
grep -q "R-001.*Technical Approach (p. 1)" active-solution/cross-reference.md || { echo "FAIL: cross-reference.md does not name the answering section" >&2; exit 1; }
grep -q "R-008.*n/a: a submission step" active-solution/cross-reference.md || { echo "FAIL: a submission step should be marked, not reported missing" >&2; exit 1; }
grep -v 'Accessibility (RFP 2.4)' "$T/p502.bak" > active-solution/response/02-technical-approach.md
rfps-refresh-reports --solution >/dev/null
grep -q "Every mandatory requirement is answered in a named section | Open.*R-004" active-solution/compliance-report.md || { echo "FAIL: an unanswered mandatory requirement was not caught" >&2; grep -n "answered in a named" active-solution/compliance-report.md >&2; exit 1; }
cp "$T/p502.bak" active-solution/response/02-technical-approach.md
rfps-refresh-reports --solution >/dev/null
grep -q "Exhibits planned for the heavily weighted factors | Pass" active-solution/compliance-report.md || { echo "FAIL: the seed exhibit plan should cover the weighted factors" >&2; grep -n "Exhibits" active-solution/compliance-report.md >&2; exit 1; }
grep -v '^| X-01 ' "$HERE/seed/win-strategy.md" > active-solution/win-strategy.md
rfps-refresh-reports --solution >/dev/null
grep -q "Exhibits planned for the heavily weighted factors | Open.*Technical Approach" active-solution/compliance-report.md || { echo "FAIL: a weighted factor with no exhibit was not listed" >&2; exit 1; }
printf '| Q-01 | RFP 2.2: does the existing maintenance history include the archive from before 2019? | R-002 | 2020-01-01 | Draft | | |\n' >> active-solution/questions.md
rfps-worklist --table | grep -q "Question deadline passed" || { echo "FAIL: an unsent question past its deadline should be on the worklist" >&2; exit 1; }
rfps-flow-status --table | grep -q "1 question(s) still a draft" || { echo "FAIL: the flow did not show the unsent question" >&2; exit 1; }
sed -i.bak 's/| Draft | | |$/| Answered | Yes, from 2015. | - |/' active-solution/questions.md && rm active-solution/questions.md.bak
rfps-worklist --table | grep -q "Answer not logged" || { echo "FAIL: an answer not logged as Q&A should be on the worklist" >&2; exit 1; }
rfps-flow-status --table | grep -q "answer(s) not logged in amendments/log.md: Q-01" || { echo "FAIL: the flow did not show the unlogged answer" >&2; exit 1; }
rfps-refresh-reports --solution >/dev/null
grep -q "Questions to the agency | Open.*answered but not logged in amendments/log.md: Q-01" active-solution/compliance-report.md || { echo "FAIL: unlogged answer not in the automated checks" >&2; exit 1; }
sed -i.bak 's/| Answered | Yes, from 2015. | - |$/| Answered | Yes, from 2015. | 2 |/' active-solution/questions.md && rm active-solution/questions.md.bak
if rfps-worklist --table | grep -q "Answer not logged"; then echo "FAIL: a logged answer should leave the worklist" >&2; exit 1; fi
cp "$T/cm5.bak" active-solution/coverage-matrix.md; cp "$T/ws5.bak" active-solution/win-strategy.md; cp "$T/q5.bak" active-solution/questions.md; rm -f active-solution/cross-reference.md
rfps-refresh-reports --solution >/dev/null
uv run --quiet --with openpyxl python3 - "$HERE/../tools" "$T" <<'PY'
import csv, pathlib, sys, openpyxl
sys.path.insert(0, sys.argv[1]); import pricing
t = pathlib.Path(sys.argv[2]) / "price"; t.mkdir(); (t / "09").mkdir()
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Staffing"
rows = [("P-01", "Project Manager", "A", "", "", "Senior PM", "100", 100, 100, 100, 100), ("P-02", "Developer", "B", "", "", "Developer III", "100", 200, 50, 50, 50)]
for i, r in enumerate(rows, 5):
    for j, v in enumerate(r, 1): ws.cell(row=i, column=j, value=v)
wb.save(t / "09" / "Staffing.xlsx")
with open(t / "09" / "Rates.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["labor_category", "rate"]); w.writerow(["Senior PM", 100]); w.writerow(["Developer III", 150])
cfg = {"staffing_xlsx": "09/Staffing.xlsx", "rate_sheet": "09/Rates.csv"}
plan = "## Figures stated by the solicitation\n\n| Item | Value | Source | Notes |\n|---|---|---|---|\n| Not-to-exceed ceiling | $100,000 | RFP 4 | |\n\n## Role requirements\n"
view = "\n".join(pricing.price_view(t, cfg, plan))
assert "Total labor cost:** $60,000" in view or "$60,000" in view, view   # (300 x 100) + (150 x 200)
assert "-40%" in view, view                                             # 60,000 against a 100,000 ceiling
assert "$54,000 to $66,000" in view, view
bad = pricing.rate_checks(t, cfg)[0]
assert "Fail" in bad and "P-02" in bad and "$200 > $150" in bad, bad
cfg["rate_sheet"] = "09/Missing.csv"
assert "Open" in pricing.rate_checks(t, cfg)[0]
PY
rfps-sync-docx >/dev/null
WIP="05 Draft Response/Response Template_WIP.docx"
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, zipfile
x = zipfile.ZipFile(sys.argv[1]).read("word/document.xml").decode()
sys.exit("no tracked insertions after the push" if x.count("<w:ins ") < 10 else 0)
PY
rfps-sync-docx --status | grep -q "0 section(s) with response changes" || { echo "FAIL: WIP not in sync after push" >&2; exit 1; }
# locators: every heading has a bookmark, and open items link to the document section with text to search for
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, zipfile
x = zipfile.ZipFile(sys.argv[1]).read("word/document.xml").decode()
sys.exit("expected 4 heading bookmarks, found %d" % x.count("<w:bookmarkStart ") if x.count("<w:bookmarkStart ") != 4 else 0)
PY
rfps-open-items >/dev/null
grep -q "WIP.docx#rfps_Technical_Approach_" active-solution/open-items.md || { echo "FAIL: open items do not link to the document section" >&2; exit 1; }
grep -q 'Search: `\[ASSERTION' active-solution/open-items.md || { echo "FAIL: open items lack the search text" >&2; exit 1; }
# ranked worklist: markers and gaps in one list, choices kept between runs
rfps-worklist | grep -q "open of" || { echo "FAIL: worklist did not run" >&2; exit 1; }
test ! -f active-solution/worklist.md || { echo "FAIL: worklist wrote a report file" >&2; exit 1; }
WID=$(rfps-worklist --next | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
rfps-worklist --set "$WID" mine --note "needs the director" >/dev/null
rfps-worklist | grep -q "1 yours" && rfps-worklist --table | grep -q "needs the director" || { echo "FAIL: worklist did not keep a choice" >&2; exit 1; }
rfps-open-items >/dev/null; grep -q "(mine)" active-solution/open-items.md || { echo "FAIL: open-items does not show the worklist choice" >&2; exit 1; }
rfps-worklist --set solution addressed 2>&1 | tee /dev/stderr | grep -q "solution: done" || { echo "FAIL: worklist --set did not reach a flow step" >&2; exit 1; }
rfps-worklist --set solution open >/dev/null
[ "$(rfps-worklist --next | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")" != "$WID" ] || { echo "FAIL: a claimed item came back as next" >&2; exit 1; }
rfps-open-doc --section "Technical Approach" --find "[ASSERTION: x" --print | grep -q "bookmark rfps_Technical_Approach_" || { echo "FAIL: open-doc did not print the bookmark" >&2; exit 1; }
# reviewers edit, insert, delete and comment in the document; pull brings those into the response
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, copy, docx
from docx.oxml.ns import qn
d = docx.Document(sys.argv[1]); body = d.element.body
for t in body.iter(qn("w:t")):
    if t.text and "Supervisors create" in t.text: t.text = t.text.replace("Supervisors create", "Garage supervisors create")
for par in body.iter(qn("w:p")):
    if "A Project Manager" in "".join(t.text or "" for t in par.iter(qn("w:t"))):
        new = copy.deepcopy(par)
        for t in new.iter(qn("w:t")): t.text = ""
        next(new.iter(qn("w:t"))).text = "We will hold a kickoff meeting within 10 days of the Notice to Proceed."
        par.addnext(new); break
for par in list(body.iter(qn("w:p"))):
    if "Reporting (RFP 2.5)" in "".join(t.text or "" for t in par.iter(qn("w:t"))): par.getparent().remove(par); break
for par in d.paragraphs:
    if par.style.name == "Subtitle" and "approach to RFP" in par.text:
        d.add_comment(runs=par.runs, text="Cite the SLA", author="Reviewer", initials="R"); break
d.save(sys.argv[1])
PY
rfps-sync-docx --pull | grep -q "3 change(s)" || { echo "FAIL: pull did not find the document edits" >&2; exit 1; }
grep -q "Cite the SLA" active-solution/review/doc-comments.md || { echo "FAIL: comment not read" >&2; exit 1; }
rfps-sync-docx --pull --apply >/dev/null
grep -q "Garage supervisors" active-solution/response/02-technical-approach.md || { echo "FAIL: edit not written to the response" >&2; exit 1; }
grep -q "kickoff meeting" active-solution/response/03-management-plan.md || { echo "FAIL: inserted paragraph not written" >&2; exit 1; }
if grep -q "Reporting (RFP 2.5)" active-solution/response/02-technical-approach.md; then echo "FAIL: deleted bullet still in the response" >&2; exit 1; fi
rfps-sync-docx --status | grep -q "0 section(s) with response changes to push, 0 with edits" || { echo "FAIL: not in step after pull" >&2; exit 1; }
# a reviewer edits one paragraph in the document; the response then changes the same paragraph and another one
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, docx
from docx.oxml.ns import qn
d = docx.Document(sys.argv[1]); n = 0
for t in d.element.body.iter(qn("w:t")):
    if t.text and "Every public and staff page" in t.text: t.text = t.text.replace("Every public and staff page", "Every public and every staff page"); n += 1
assert n, "reviewer edit target not found"
d.save(sys.argv[1])
PY
sed -i.bak 's/tested to WCAG 2.1 AA\./tested to WCAG 2.1 AA and post it online./; s/in three parts/in four parts/' active-solution/response/02-technical-approach.md && rm active-solution/response/02-technical-approach.md.bak
OUT=$(rfps-sync-docx)
echo "$OUT" | grep -q "1 skipped" || { echo "FAIL: collision with a reviewer edit was not reported" >&2; echo "$OUT" >&2; exit 1; }
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, zipfile
x = zipfile.ZipFile(sys.argv[1]).read("word/document.xml").decode()
assert "every staff page" in x, "reviewer edit was lost"
assert "four parts" in x, "non-colliding change was not pushed"
assert "post it online" not in x, "colliding change overwrote the reviewer"
PY
rfps-flow-status --table >/dev/null
rfps-build-response --solution --mode wip >/dev/null
test -f active-solution/build/*_WIP.docx
rfps-build-response --solution --mode final >/dev/null
test -f "11 Final Submission"/*_FINAL.docx
# the final copy must not contain internal markers
uv run --quiet --with python-docx python3 -c "
import docx,glob,sys
t=chr(10).join(p.text for p in docx.Document(glob.glob('11 Final Submission/*_FINAL.docx')[0]).paragraphs)
bad=[m for m in ('GROUNDED','ASSERTION','DECISION','[text]') if m in t]
sys.exit('markers left in FINAL: %s' % bad if bad else 0)"
# negative: citing the uncleared row must make FINAL refuse
rm "11 Final Submission"/*_FINAL.docx active-solution/build/*_FINAL.docx
printf '\nAlso: accessibility work for Northgate Water [GROUNDED: E-003].\n' >> active-solution/response/04-past-performance.md
if rfps-build-response --solution --mode final >/dev/null 2>&1; then echo "FAIL: FINAL accepted uncleared evidence" >&2; exit 1; fi
uv run --quiet "$HERE/gdoc_test.py"
uv run --quiet "$HERE/gdoc_template_test.py"
# template generation and update: an outline becomes a template; a changed template is compared with response/
cat > "$T/outline.json" <<'JSON'
{"title": "Response to RFP X", "sections": [
 {"level": 1, "title": "Executive Summary", "instruction": "One page on the overall approach", "source": "RFP 4.1"},
 {"level": 1, "title": "Technical Approach", "instruction": "Describe the approach to scope items 2.1 to 2.5", "source": "RFP 4.2"},
 {"level": 2, "title": "Data Migration", "instruction": "How legacy data moves", "source": "RFP 2.2"},
 {"level": 1, "title": "Management Plan"}]}
JSON
mkdir -p "$T/gen/05 Draft Response" && rfps-make-template --outline "$T/outline.json" --source "$T/gen" | grep -q "4 sections" || { echo "FAIL: template not written" >&2; exit 1; }
if rfps-make-template --outline "$T/outline.json" --source "$T/gen" >/dev/null 2>&1; then echo "FAIL: existing template was overwritten" >&2; exit 1; fi
(cd "$T/gen" && rfps-new-engagement --source "$T/gen" --title Gen >/dev/null) && test -f "$T/gen/active-solution/response/02-technical-approach.md" || { echo "FAIL: engagement from a generated template" >&2; exit 1; }
uv run --quiet --with python-docx python3 - "$T/gen/05 Draft Response/Response Template.docx" <<'PY'
import sys, docx
d = docx.Document(sys.argv[1])
for p in d.paragraphs:
    if p.style.name == "Heading 1" and p.text == "Management Plan": p.text = "Management Approach"      # renamed
    if p.style.name == "Heading 1" and p.text == "Executive Summary": p.text = "Overview of the Response"  # renamed
n = d.add_paragraph("Risk Management"); n.style = d.styles["Heading 1"]                                    # new
d.save(sys.argv[1])
PY
(cd "$T/gen" && out=$(rfps-update-template) && echo "$out" | grep -q "renamed: 'Management Plan' -> 'Management Approach'" && echo "$out" | grep -q "new in the template: Risk Management" || { echo "FAIL: update-template report" >&2; exit 1; }
 echo "$out" | grep -q "possibly renamed (same place, different wording): 'Executive Summary' -> 'Overview of the Response'" || { echo "FAIL: positional rename not suggested" >&2; echo "$out" >&2; exit 1; }
 rfps-update-template --apply --rename-all >/dev/null && out=$(rfps-update-template) && echo "$out" | grep -q "Everything matches" || { echo "FAIL: update-template apply" >&2; echo "$out" >&2; exit 1; })
rfps-set-config cache_dir "$T/cache" | grep -q "build_dir" || { echo "FAIL: cache_dir not set" >&2; exit 1; }
rfps-scan-sources --text-dir notes | grep -q "$T/cache/" || { echo "FAIL: text dir not under the cache" >&2; exit 1; }
rfps-set-config wip_folder "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQ" | grep -q "1AbCdEfGhIjKlMnOpQ" || { echo "FAIL: wip_folder" >&2; exit 1; }
if rfps-set-config cache_dir "/Users/x/Library/CloudStorage/GoogleDrive-a/My Drive/c" >/dev/null 2>&1; then echo "FAIL: cache inside Drive accepted" >&2; exit 1; fi
# collaboration: entry check, names, lease, claims, duplicate IDs
export HOME="$T/home"; mkdir -p "$HOME"
rfps-collab --resolve "$T/capture" | grep -q '"state": "found"' || { echo "FAIL: existing solution not found by the entry check" >&2; exit 1; }
mkdir -p "$T/empty" && rfps-collab --resolve "$T/empty" | grep -q '"state": "none"' || { echo "FAIL: empty folder should resolve to none" >&2; exit 1; }
RFPS_USER=Ann rfps-collab --lease acquire --op build-wip >/dev/null
if RFPS_USER=Bob rfps-collab --lease acquire --op pull-wip >/dev/null 2>&1; then echo "FAIL: a second person took a live lease" >&2; exit 1; fi
RFPS_USER=Bob rfps-collab --lease acquire --force >/dev/null; RFPS_USER=Bob rfps-collab --lease release >/dev/null
rfps-collab --lease status | grep -q "no one" || { echo "FAIL: lease not released" >&2; exit 1; }
rfps-collab --whoami --set "Clint" >/dev/null; [ "$(rfps-collab --whoami)" = "Clint" ] || { echo "FAIL: name not kept" >&2; exit 1; }
NID=$(rfps-worklist --next | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
rfps-worklist --set "$NID" mine >/dev/null; rfps-worklist --table | grep -q "mine by Clint" || { echo "FAIL: claim lacks the name" >&2; exit 1; }
rfps-collab --briefing | grep -q "1 by Clint" || { echo "FAIL: briefing lacks claims" >&2; exit 1; }
printf 'E-001,dup,c,,,,,hold,,,,,\n' >> active-solution/evidence/register.csv
rfps-collab --briefing | grep -q "DUPLICATE IDS" || { echo "FAIL: duplicate ids not reported" >&2; exit 1; }
echo "smoke test passed"
