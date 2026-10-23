"""Roster of proposed roles and people for a solution (response/resources.csv), plus the figures the
other tools need from it: people count, FTE, and checks.

The roster is the single place to add, change or drop a role. resource-plan.md holds the State's
requirements and the rules; the response text holds the written narrative; Staffing.xlsx (in the pricing
folder) holds hours and rates. This module has no dependency beyond the standard library.

Status: KP, Recommended, Ours, or Dropped (a dropped row stays for history and is ignored everywhere).
FTE = headcount x loe_pct / 100, summed. Phase FTE counts only the roles active in that phase.
"""
import csv, pathlib, re

COLUMNS = ["id", "role", "status", "source", "requirement_ref", "in_response", "scope", "responsibilities",
           "value_added", "deliverables", "headcount", "loe_pct", "phases", "person", "resume", "notes"]
STATUSES = ("KP", "Recommended", "Ours", "Dropped")
RESUMES = ("Needed", "Received", "Checked", "N/A")
PHASES = (1, 2, 3)


def roster_path(sol, cfg):
    return pathlib.Path(sol) / cfg.get("roster", "response/resources.csv")


def load(path):
    p = pathlib.Path(path)
    if not p.is_file(): return None
    with open(p, newline="") as fh:
        rows = [{k: (v or "").strip() for k, v in r.items() if k} for r in csv.DictReader(fh)]
    return [r for r in rows if r.get("id") or r.get("role")]


def write(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in COLUMNS})


def active(rows):
    return [r for r in rows if r.get("status") != "Dropped"]


def num(s, default=0.0):
    try: return float(str(s).strip().rstrip("%"))
    except ValueError: return default


def phases_of(r):
    ps = {int(x) for x in re.findall(r"[123]", r.get("phases", ""))}
    return ps or set(PHASES)


def headcount(r): return max(0.0, num(r.get("headcount"), 1.0) if r.get("headcount", "").strip() else 1.0)


def fte_of(r): return headcount(r) * num(r.get("loe_pct")) / 100.0


def stats(rows):
    act = active(rows)
    kp = [r for r in act if r["status"] == "KP"]
    people = sum(headcount(r) for r in act)
    by_phase = {p: sum(fte_of(r) for r in act if p in phases_of(r)) for p in PHASES}
    return {"roles": len(act), "people": people, "kp_people": sum(headcount(r) for r in kp),
            "other_people": people - sum(headcount(r) for r in kp), "fte": sum(fte_of(r) for r in act), "by_phase": by_phase}


def fmt_fte(x):
    s = f"{x:.2f}"
    return s[:-1] if s.endswith("0") else s


def fmt_people(x): return str(int(x)) if abs(x - round(x)) < 1e-9 else f"{x:.1f}"


def team_size_sentence(s):
    bp = s["by_phase"]
    return (f"Our team for this Work Order is {fmt_people(s['people'])} people: {fmt_people(s['kp_people'])} Key Personnel and "
            f"{fmt_people(s['other_people'])} specialists, equal to {fmt_fte(s['fte'])} FTE in total "
            f"(Phase 1: {fmt_fte(bp[1])}, Phase 2: {fmt_fte(bp[2])}, Phase 3: {fmt_fte(bp[3])}).")


def _cells(line): return [c.strip() for c in line.strip().strip("|").split("|")]


def plan_rows(text, idre, ncols):
    text = re.sub(r"<!-- derived:(\w+) -->.*?<!-- /derived:\1 -->", "", text, flags=re.S)
    out = {}
    for line in text.split("\n"):
        m = re.match(r"^\| (%s) \|" % idre, line)
        if m:
            c = _cells(line)
            if len(c) == ncols: out[m.group(1)] = c
    return out


def requirements(text):
    """Q-nnn rows: id, role, source, qualifications, minimum loe %, notes."""
    return plan_rows(text, r"Q-\d{3}", 6)


def deliverables(text):
    """D-nnn rows: id, deliverable, due, source."""
    return plan_rows(text, r"D-\d{3}", 4)
