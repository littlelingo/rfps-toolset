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
uv run --quiet --with python-docx python3 - past-performance/*.docx <<'PY'
import sys, docx
d = docx.Document(sys.argv[1]); d.add_paragraph("Update 2026: added a new reference."); d.save(sys.argv[1])
PY
rfps-scan-sources | grep -q "1 new, 1 changed\|0 new, 1 changed" || { echo "FAIL: an edited file should be reported as changed" >&2; exit 1; }
rfps-add-source FOLDER123 --type drive --label drivefolder >/dev/null
printf '[{"id":"f1","title":"Case A.docx","mimeType":"x","modifiedTime":"2026-01-01T00:00:00Z","size":"10"},{"id":"f2","title":"Case B.pdf","mimeType":"x","modifiedTime":"2026-01-02T00:00:00Z","size":"20"}]' > "$T/listing.json"
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
rfps-refresh-reports --solution >/dev/null
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
test -f active-solution/worklist.md
WID=$(rfps-worklist --next | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")
rfps-worklist --set "$WID" mine --note "needs the director" >/dev/null
grep -q "1 yours" active-solution/worklist.md && grep -q "needs the director" active-solution/worklist.md || { echo "FAIL: worklist did not keep a choice" >&2; exit 1; }
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
echo "smoke test passed"
