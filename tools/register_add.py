# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Add rows to the evidence register safely: next free ID, never reused, and never `cleared` on its own.

A row is `hold` unless another clearance is given; `cleared` needs --confirm-cleared, which is for the user's own say-so
(the client or owner agreed to use the fact in the State-facing response). The ID counter counts superseded rows too.

Structured fields (all optional, read by the recency, value and reference checks and by the clearance-proof rule):
  --start / --end        when the work began and ended: 2024, 2024-03 or 2024-03-15; end may be "present"
  --value-usd            contract value in dollars (digits, or 1.2M / 450K)
  --scope-tags           short tags separated by ";" (for example scheduling;migration)
  --reference-contact    who can confirm it, and how to reach them
  --reference-confirmed  the date that person last confirmed, YYYY-MM-DD
  --approved-by / --approved-date / --approval-ref   who agreed to use the fact in the response, when, and where the proof is (an email, a file)

Usage: rfps-register-add --claim "..." --client X --engagement Y --date 2024 --numbers "..." --source "file, section"
                         [--clearance hold|needs-permission|do-not-use|cleared --confirm-cleared] [--basis "..."] [--notes "..."] [--ban "a;b"]
                         [the structured fields above]
       rfps-register-add --json rows.json     a list of objects with the same fields (confirm_cleared: true per row for cleared)
       rfps-register-add --update E-003 [structured fields] [--clearance X --confirm-cleared]   change those fields on an existing row; nothing else changes
"""
import argparse, csv, datetime, json, os, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br

COLUMNS = ["id", "claim", "client", "engagement", "date", "numbers", "source", "clearance", "verified", "basis", "superseded_by", "notes", "ban_phrases",
           "start", "end", "value_usd", "scope_tags", "reference_contact", "reference_confirmed", "approved_by", "approved_date", "approval_ref"]
STRUCTURED = ["start", "end", "value_usd", "scope_tags", "reference_contact", "reference_confirmed", "approved_by", "approved_date", "approval_ref"]
CLEARANCES = ["hold", "needs-permission", "do-not-use", "cleared"]

def _read(path):
    if not path.is_file(): return [], list(COLUMNS)
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh); rows = list(rd); head = list(rd.fieldnames or [])
    return rows, COLUMNS + [c for c in head if c not in COLUMNS]   # keep any extra columns a person added

def _write(path, rows, fields, before):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n"); w.writeheader(); w.writerows({c: r.get(c, "") or "" for c in fields} for r in rows)
    if before != ((path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None): tmp.unlink(); return False
    os.replace(tmp, path); return True

def _retry(path, fn):
    """Run fn(before) until the file did not change under us (someone else adding rows); fn returns None to ask for another pass."""
    path = pathlib.Path(path)
    for _ in range(5):
        before = (path.stat().st_mtime_ns, path.stat().st_size) if path.is_file() else None
        out = fn(path, before)
        if out is not None: return out
    raise SystemExit("the register keeps changing under us (someone else is changing it); try again in a moment")

def add_rows(path, rows):
    """Add rows with fresh IDs. If the register changed on disk between reading and writing (another person added rows), start again from the new file."""
    return _retry(path, lambda p, before: _add_rows(p, rows, before))

def _add_rows(path, rows, before):
    existing, fields = _read(path)
    top = max([int(m.group(1)) for r in existing if (m := re.match(r"E-(\d+)$", (r.get("id") or "").strip()))] or [0])
    made = []
    for r in rows:
        clearance = (r.get("clearance") or "hold").strip()
        if clearance not in CLEARANCES: raise SystemExit(f"unknown clearance '{clearance}' (use {', '.join(CLEARANCES)})")
        if clearance == "cleared" and not r.get("confirm_cleared"):
            raise SystemExit("clearance 'cleared' needs --confirm-cleared (only after the client or owner agreed to use it in the State-facing response); the row was not added")
        if not (r.get("claim") or "").strip(): raise SystemExit("every row needs a claim")
        top += 1; rid = f"E-{top:03d}"
        row = {c: (r.get(c) or "") for c in fields}; row.update(id=rid, clearance=clearance, verified=r.get("verified") or datetime.date.today().isoformat())
        existing.append(row); made.append(rid)
    return made if _write(path, existing, fields, before) else None

def update_row(path, rid, changes, confirm_cleared=False):
    """Set structured fields (and optionally the clearance) on one existing row. Returns the fields changed."""
    bad = [k for k in changes if k not in STRUCTURED + ["clearance"]]
    if bad: raise SystemExit(f"cannot update {', '.join(bad)} here; only the structured fields and clearance")
    if changes.get("clearance") and changes["clearance"] not in CLEARANCES: raise SystemExit(f"unknown clearance '{changes['clearance']}' (use {', '.join(CLEARANCES)})")
    if changes.get("clearance") == "cleared" and not confirm_cleared: raise SystemExit("clearance 'cleared' needs --confirm-cleared (the client or owner agreed to use it in the State-facing response); nothing was changed")
    def go(p, before):
        rows, fields = _read(p)
        hit = next((r for r in rows if (r.get("id") or "").strip() == rid), None)
        if hit is None: raise SystemExit(f"no row {rid} in {p}")
        hit.update({k: v for k, v in changes.items() if v is not None})
        return list(changes) if _write(p, rows, fields, before) else None
    return _retry(path, go)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("claim", "client", "engagement", "date", "numbers", "source", "clearance", "basis", "notes"): ap.add_argument("--" + k)
    for k in STRUCTURED: ap.add_argument("--" + k.replace("_", "-"))
    ap.add_argument("--ban"); ap.add_argument("--confirm-cleared", action="store_true"); ap.add_argument("--json"); ap.add_argument("--solution", default=None); ap.add_argument("--update", metavar="ID")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); e = br.load_engagement(str(sol))
    if not e.get("register"): sys.exit("this solution has no register path in solution.toml")
    if a.update:
        ch = {k: getattr(a, k) for k in STRUCTURED + ["clearance"] if getattr(a, k) is not None}
        if not ch: sys.exit("nothing to change: give at least one structured field or --clearance")
        done = update_row(e["register"], a.update, ch, a.confirm_cleared)
        print(f"Updated {a.update}: {', '.join(done)}"); sys.exit(0)
    if a.json: rows = json.loads(pathlib.Path(a.json).read_text())
    else: rows = [{**{k: getattr(a, k) for k in ("claim", "client", "engagement", "date", "numbers", "source", "clearance", "basis", "notes") + tuple(STRUCTURED)}, "ban_phrases": a.ban, "confirm_cleared": a.confirm_cleared}]
    ids = add_rows(e["register"], rows)
    print(f"Added {len(ids)} row(s) to {e['register']}: {', '.join(ids)}")
