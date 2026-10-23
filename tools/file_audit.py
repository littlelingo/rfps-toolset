# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Track where the files in a solution came from.

Lists every file in the solution folder that is not part of the expected set (tools/known_files.toml)
and not recorded in the solution's provenance.md, with when it appeared. Record a file with --record so
the solution keeps a note of who or what made it, why, and whether it is needed.

Usage:
  rfps-file-audit [--solution [path]]            list unlisted files and recorded ones
  rfps-file-audit --record PATH --by WHO --why WHY [--verdict Needed|Review|Remove]
  rfps-file-audit --json                         machine-readable summary
"""
import argparse, fnmatch, json, pathlib, re, sys, tomllib, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br

HEAD = "# File provenance\n\nWhere each non-standard file in this solution came from. Added with `rfps-file-audit --record`. Verdict: Needed (keep), Review (decide), Remove.\n\n| Path | Created by | Date | Why | Verdict |\n|------|------------|------|-----|---------|\n"

def expected_globs(): return tomllib.loads((pathlib.Path(__file__).parent / "known_files.toml").read_text())["expected"]

def is_expected(rel, globs):
    return any(fnmatch.fnmatch(rel, g) or (g.endswith("/**") and rel.startswith(g[:-2])) for g in globs)

def recorded(sol):
    f = sol / "provenance.md"; out = {}
    if f.is_file():
        for line in f.read_text().split("\n"):
            m = re.match(r"^\| ([^|]+?) \|", line)
            if m and not m.group(1).startswith(("Path", "-")):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                if len(c) == 5: out[c[0].strip("`")] = c
    return out

def born(p):
    s = p.stat(); t = getattr(s, "st_birthtime", s.st_mtime)
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")

def first_line(p):
    try:
        for l in p.read_text(errors="ignore").split("\n"):
            if l.strip(): return l.strip().lstrip("# ")[:90]
    except Exception: pass
    return ""

def audit(sol):
    globs, rec = expected_globs(), recorded(sol)
    unlisted = []
    for p in sorted(sol.rglob("*")):
        if not p.is_file(): continue
        rel = p.relative_to(sol).as_posix()
        if is_expected(rel, globs) or rel in rec: continue
        unlisted.append((rel, born(p), first_line(p)))
    return unlisted, rec

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default="")
    ap.add_argument("--record"); ap.add_argument("--by", default=""); ap.add_argument("--why", default="")
    ap.add_argument("--verdict", default="Review", choices=["Needed", "Review", "Remove"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(); sol = br.resolve_solution(a.solution or None)
    if a.record:
        p = sol / a.record
        if not p.is_file(): sys.exit(f"not found: {a.record}")
        if not (a.by and a.why): sys.exit("--record needs --by and --why")
        f = sol / "provenance.md"
        if not f.is_file(): f.write_text(HEAD)
        t = f.read_text()
        if f"| {a.record} |" in t: sys.exit(f"{a.record} is already recorded; edit provenance.md")
        f.write_text(t.rstrip("\n") + f"\n| {a.record} | {a.by.replace('|','/')} | {born(p)} | {a.why.replace('|','/')} | {a.verdict} |\n")
        print(f"Recorded {a.record} ({a.verdict})"); return
    unlisted, rec = audit(sol)
    if a.json: print(json.dumps({"unlisted": [u[0] for u in unlisted], "recorded": rec}, indent=1)); return
    print(f"{len(unlisted)} unlisted file(s); {len(rec)} recorded in provenance.md")
    for rel, b, h in unlisted: print(f"  ? {rel}  (appeared {b}) {h}")
    for k, c in rec.items():
        if c[4] != "Needed": print(f"  {c[4]}: {k} - {c[1]}: {c[3]}")

if __name__ == "__main__":
    main()
