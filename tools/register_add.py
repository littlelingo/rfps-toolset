# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Add rows to the evidence register safely: next free ID, never reused, and never `cleared` on its own.

A row is `hold` unless another clearance is given; `cleared` needs --confirm-cleared, which is for the user's own say-so
(the client or owner agreed to use the fact in the State-facing response). The ID counter counts superseded rows too.

Usage: rfps-register-add --claim "..." --client X --engagement Y --date 2024 --numbers "..." --source "file, section"
                         [--clearance hold|needs-permission|do-not-use|cleared --confirm-cleared] [--basis "..."] [--notes "..."] [--ban "a;b"]
       rfps-register-add --json rows.json     a list of objects with the same fields (confirm_cleared: true per row for cleared)
"""
import argparse, csv, datetime, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br

COLUMNS = ["id", "claim", "client", "engagement", "date", "numbers", "source", "clearance", "verified", "basis", "superseded_by", "notes", "ban_phrases"]
CLEARANCES = ["hold", "needs-permission", "do-not-use", "cleared"]

def add_rows(path, rows):
    path = pathlib.Path(path); existing = []
    if path.is_file():
        with open(path, newline="") as fh: existing = list(csv.DictReader(fh))
    top = max([int(m.group(1)) for r in existing if (m := re.match(r"E-(\d+)$", (r.get("id") or "").strip()))] or [0])
    made = []
    for r in rows:
        clearance = (r.get("clearance") or "hold").strip()
        if clearance not in CLEARANCES: raise SystemExit(f"unknown clearance '{clearance}' (use {', '.join(CLEARANCES)})")
        if clearance == "cleared" and not r.get("confirm_cleared"):
            raise SystemExit("clearance 'cleared' needs --confirm-cleared (only after the client or owner agreed to use it in the State-facing response); the row was not added")
        if not (r.get("claim") or "").strip(): raise SystemExit("every row needs a claim")
        top += 1; rid = f"E-{top:03d}"
        row = {c: (r.get(c) or "") for c in COLUMNS}; row.update(id=rid, clearance=clearance, verified=r.get("verified") or datetime.date.today().isoformat())
        existing.append(row); made.append(rid)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n"); w.writeheader(); w.writerows({c: r.get(c, "") for c in COLUMNS} for r in existing)
    return made

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("claim", "client", "engagement", "date", "numbers", "source", "clearance", "basis", "notes"): ap.add_argument("--" + k)
    ap.add_argument("--ban"); ap.add_argument("--confirm-cleared", action="store_true"); ap.add_argument("--json"); ap.add_argument("--solution", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); e = br.load_engagement(str(sol))
    if not e.get("register"): sys.exit("this solution has no register path in solution.toml")
    if a.json: rows = json.loads(pathlib.Path(a.json).read_text())
    else: rows = [{**{k: getattr(a, k) for k in ("claim", "client", "engagement", "date", "numbers", "source", "clearance", "basis", "notes")}, "ban_phrases": a.ban, "confirm_cleared": a.confirm_cleared}]
    ids = add_rows(e["register"], rows)
    print(f"Added {len(ids)} row(s) to {e['register']}: {', '.join(ids)}")
