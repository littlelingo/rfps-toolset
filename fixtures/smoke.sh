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
rfps-add-source "$T/capture/past-performance" --label notes >/dev/null
grep -q 'path = "../past-performance"' active-solution/past-performance/sources.toml || { echo "FAIL: source path is not relative" >&2; exit 1; }
# shared WIP docx: created from the (still empty) template, then the seed text arrives as tracked changes
rfps-sync-docx >/dev/null
test -f "05 Draft Response/Response Template_WIP.docx"
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
# a reviewer edits one paragraph in the document; the response then changes the same paragraph and another one
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, docx
from docx.oxml.ns import qn
d = docx.Document(sys.argv[1]); n = 0
for t in d.element.body.iter(qn("w:t")):
    if t.text and "monthly utilization report" in t.text: t.text = t.text.replace("monthly utilization report", "monthly fleet utilization report"); n += 1
assert n, "reviewer edit target not found"
d.save(sys.argv[1])
PY
sed -i.bak 's/to the Fleet Manager\./to the Fleet Manager and post it online./; s/in three parts/in four parts/' active-solution/response/02-technical-approach.md && rm active-solution/response/02-technical-approach.md.bak
OUT=$(rfps-sync-docx)
echo "$OUT" | grep -q "1 skipped" || { echo "FAIL: collision with a reviewer edit was not reported" >&2; echo "$OUT" >&2; exit 1; }
uv run --quiet --with python-docx python3 - "$WIP" <<'PY'
import sys, zipfile
x = zipfile.ZipFile(sys.argv[1]).read("word/document.xml").decode()
assert "fleet utilization" in x, "reviewer edit was lost"
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
echo "smoke test passed"
