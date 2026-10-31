# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Working on one solution with other people: find out whether a solution exists, who you are, who is writing, who owns what.

  --resolve [FOLDER]          decide between starting and joining: looks in FOLDER (default: here) for a solution, at the folder, in
                              active-solution/ inside it, and above it; prints JSON {"state": "none"|"found"|"many", ...}
  --whoami [--set NAME]       the name used for claims and the lease, kept in ~/.config/rfps/user.toml on this machine (never shared)
  --lease status|acquire|release [--op NAME] [--force]
                              a small note in .state/lease.json saying who is running a command that writes shared files, so a second
                              person is warned. A lease older than 2 hours is treated as stale. Exit code 3 when someone else holds it.
  --briefing                  what a person joining needs: lease, claims by person, recent activity, duplicate IDs, cache_dir

Usage: rfps-collab --resolve [FOLDER] | --whoami [--set NAME] | --lease ACTION [--op NAME] | --briefing   (add --solution FOLDER to point at one)
"""
import argparse, collections, csv, datetime, json, os, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br

USER_FILE = pathlib.Path.home() / ".config" / "rfps" / "user.toml"
STALE = datetime.timedelta(hours=2)

def whoami():
    n = os.environ.get("RFPS_USER")
    if n: return n.strip()
    if USER_FILE.is_file(): return tomllib.loads(USER_FILE.read_text()).get("name", "").strip()
    return ""

def set_name(name):
    USER_FILE.parent.mkdir(parents=True, exist_ok=True); USER_FILE.write_text(f'name = "{name.strip()}"\n')

def resolve(folder=None):
    start = pathlib.Path(folder).expanduser().resolve() if folder else pathlib.Path.cwd().resolve()
    found = []
    for p in (start, *start.parents):
        for c in (p, p / "active-solution"):
            if (c / "solution.toml").is_file() and c not in found: found.append(c)
        if found: break
    sub = [c for c in start.glob("*/active-solution") if (c / "solution.toml").is_file()] if not found else []
    found += sub
    if not found:
        files = [x for x in start.rglob("*") if x.is_file() and not x.name.startswith(".")][:5] if start.is_dir() else []
        return dict(state="none", folder=str(start), looks_empty=not files, note="no solution.toml here, above, or in active-solution/")
    state = "found" if len(found) == 1 else "many"
    return dict(state=state, solution=str(found[0]), solutions=[str(f) for f in found], folder=str(start))

def lease_file(sol): return sol / ".state" / "lease.json"

def lease(sol, action, op="", force=False):
    f = lease_file(sol); me = whoami() or "someone"; now = datetime.datetime.now()
    cur = json.loads(f.read_text()) if f.is_file() else None
    age = (now - datetime.datetime.fromisoformat(cur["since"])) if cur else None
    live = bool(cur) and age < STALE
    if action == "status":
        return (0, f"{cur['holder']} is running {cur['op'] or 'a command'} (since {cur['since'][11:16]}, {int(age.total_seconds() // 60)} min ago)" + ("" if live else " - stale, treated as free")) if cur else (0, "no one is writing")
    if action == "acquire":
        if live and cur["holder"] != me and not force:
            return 3, f"{cur['holder']} is running {cur['op'] or 'a command'} that writes shared files (since {cur['since'][11:16]}). Wait, or ask them, before continuing; --force overrides."
        f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(dict(holder=me, op=op, since=now.isoformat(timespec="seconds"))) + "\n")
        return 0, f"lease taken by {me}" + (f" for {op}" if op else "")
    if action == "release":
        if cur and (cur["holder"] == me or force or not live): f.unlink()
        return 0, "lease released"
    return 2, "action must be status, acquire or release"

IDCOLS = [("evidence/register.csv", "E-"), ("response/resources.csv", "P-")]

def duplicate_ids(sol, cfg):
    dups = []
    for rel, pre in ((cfg.get("register", "evidence/register.csv"), "E-"), (cfg.get("roster", "response/resources.csv"), "P-")):
        p = sol / rel
        if not p.is_file(): continue
        with open(p, newline="") as fh: ids = [(r.get("id") or "").strip() for r in csv.DictReader(fh)]
        dups += [f"{rel}: {i} appears {n} times" for i, n in collections.Counter(ids).items() if i.startswith(pre) and n > 1]
    for rel in ("coverage-matrix.md", "compliance-report.md"):
        p = sol / rel
        if p.is_file():
            ids = re.findall(r"^\|\s*([A-Z]-\d+)\s*\|", p.read_text(), re.M)
            dups += [f"{rel}: {i} appears {n} times" for i, n in collections.Counter(ids).items() if n > 1]
    return dups

def briefing(sol):
    cfg = tomllib.loads((sol / "solution.toml").read_text()); out = [f"Solution: {cfg.get('title', sol.parent.name)} ({sol})"]
    out.append("Who you are on this machine: " + (whoami() or "not set (rfps-collab --whoami --set NAME)"))
    out.append("Writing now: " + lease(sol, "status")[1])
    wl = sol / ".state" / "worklist.json"
    if wl.is_file():
        by = collections.Counter(v.get("by", "someone") for v in json.loads(wl.read_text()).values() if v.get("status") == "mine")
        out.append("Worklist items claimed: " + (", ".join(f"{n} by {w}" for w, n in by.items()) or "none"))
    acts = []
    for rel in ("response", "evidence", "coverage-matrix.md", "compliance-report.md", "capture.md", "questions.md", "win-strategy.md", "evaluation-sim.md", "progress.md", "review-notes.md"):
        p = sol / rel
        files = [p] if p.is_file() else list(p.glob("*")) if p.is_dir() else []
        for q in files:
            if q.is_file(): acts.append((q.stat().st_mtime, str(q.relative_to(sol))))
    for t, n in sorted(acts, reverse=True)[:5]: out.append(f"  changed {datetime.datetime.fromtimestamp(t):%Y-%m-%d %H:%M}: {n}")
    d = duplicate_ids(sol, cfg)
    out += (["DUPLICATE IDS (two people added at once; renumber the newer row by hand and fix references):"] + ["  " + x for x in d]) if d else ["IDs: no duplicates"]
    if "cache_dir" not in cfg and re.search(r"CloudStorage/GoogleDrive|/Google Drive/", str(sol)):
        out.append("cache_dir is not set on this solution, and it is in Google Drive: text caches would sync to Drive. Set it with rfps-set-config cache_dir <folder on this machine>.")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resolve", nargs="?", const="", default=None); ap.add_argument("--whoami", action="store_true"); ap.add_argument("--set")
    ap.add_argument("--lease", choices=["status", "acquire", "release"]); ap.add_argument("--op", default=""); ap.add_argument("--force", action="store_true")
    ap.add_argument("--briefing", action="store_true"); ap.add_argument("--solution", default="")
    a = ap.parse_args()
    if a.resolve is not None: print(json.dumps(resolve(a.resolve or None), indent=1)); return
    if a.whoami:
        if a.set: set_name(a.set)
        print(whoami() or "(not set)"); return
    sol = br.resolve_solution(a.solution or None)
    if a.lease:
        code, msg = lease(sol, a.lease, a.op, a.force); print(msg); sys.exit(code)
    if a.briefing: print(briefing(sol)); return
    ap.print_help()

if __name__ == "__main__":
    main()
