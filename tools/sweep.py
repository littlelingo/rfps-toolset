# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl", "pypdf", "python-pptx"]
# ///
"""Sweep the solicitation for obligation sentences (shall, must, is required, no later than, should ...) and list any that no requirement row covers.

A deterministic backstop for the requirements mapper and the compliance validator: they read the solicitation with judgment, this counts.
Every obligation sentence is matched against the requirement text in coverage-matrix.md (R- rows) and compliance-report.md (check rows).
A sentence with no close row is "unmapped": either add a row for it, or decide it is not a requirement. Nothing is changed.

Usage: rfps-sweep [--solution [folder]] [--text-dir <folder of extracted .txt>] [--json] [--check]
  --check  exit 1 when a mandatory obligation is unmapped (for scripts and gates)
Text comes from the solicitation folder (solicitation_dir in solution.toml): the copy /rfps:extract made if there is one, else read in place.
"""
import argparse, json, pathlib, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import refresh_reports as rr
import solicit_text as st

def row_texts(sol):
    rows = {}
    f = sol / "coverage-matrix.md"
    if f.is_file(): rows.update({k: c[1] for k, c in rr.rows_of(f.read_text(), r"R-\d{3}", 9, []).items()})
    f = sol / "compliance-report.md"
    if f.is_file():
        t = f.read_text()
        for pre, n in ((r"[FCSP]-\d{3}", 7), (r"N-\d{3}", 7)): rows.update({k: c[1] for k, c in rr.rows_of(t, pre, n, []).items()})
    return rows

def run(sol, cfg, text_dir=None):
    docs, note = st.load_text(sol, cfg, text_dir)
    docs = st.scope_docs(docs, cfg)
    return note, docs, st.sweep(docs, row_texts(sol), st.scope(cfg))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default="")
    ap.add_argument("--text-dir", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    note, docs, res = run(sol, cfg, a.text_dir)
    if not docs: sys.exit(f"nothing to sweep: {note}")
    un = [r for r in res if not r["mapped"]]
    bad = [r for r in un if r["cls"] == "mandatory"]
    if a.json:
        print(json.dumps(dict(source=note, total=len(res), unmapped=un), indent=1))
    else:
        print(f"Solicitation sweep ({note}): {len(res)} obligation sentence(s) in {len(docs)} file(s); {len(res) - len(un)} covered by a requirement row, {len(un)} unmapped ({len(bad)} mandatory).")
        if un:
            print("\n| Class | Where | File | Sentence | Closest row (score) |\n|---|---|---|---|---|")
            for r in sorted(un, key=lambda r: r["cls"] != "mandatory"):
                print(f"| {r['cls']} | {r['where'] or '-'} | {r['file']} | {r['text'].replace('|', '/')[:200]} | {r['row'] or '-'} ({r['score']}) |")
            print("\nFor each: add a requirement row (stable next ID), or decide it is not a requirement and say why in the row notes. Then run rfps-refresh-reports.")
    if a.check and bad: sys.exit(1)

if __name__ == "__main__":
    main()
