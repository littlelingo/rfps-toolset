# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Add a past-performance source location to past-performance/sources.toml (read in place, never copied).

A location inside the capture (source) folder is stored relative to `active-solution/`, the same base solution.toml
uses, so the entry survives moving or syncing the folder. A location elsewhere is stored as an absolute path.
An entry for the same location is not added twice.

Usage: rfps-add-source <folder or file> [<more> ...] [--label NAME] [--type local|drive] [--solution <folder>]
       (several locations in one call each get their own label from the folder name; --label is for a single location;
        for --type drive the location is the Drive folder id)
       rfps-add-source --normalize [--solution <folder>]   rewrite absolute local entries under the capture folder as relative,
                                                           and report entries whose location no longer exists
"""
import argparse, os, pathlib, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import solution_dir as sd
import build_response as br

def stored_path(target, sol):
    """Path as stored in sources.toml: relative to the solution folder when under the capture folder, else absolute."""
    capture = sd.source_of(sol)
    try:
        target.relative_to(capture)
    except ValueError:
        return str(target)
    return os.path.relpath(target, sol)

def resolve(entry_path, sol):
    """Absolute path of a stored entry (relative entries are relative to the solution folder)."""
    p = pathlib.Path(entry_path)
    return (p if p.is_absolute() else sol / p).resolve()

def normalize(sol):
    """Rewrite absolute local paths that sit under the capture folder as paths relative to the solution folder."""
    f = sol / "past-performance" / "sources.toml"
    if not f.is_file(): print("no sources.toml"); return
    text = f.read_text(); changed = missing = 0
    for s in tomllib.loads(text).get("source", []) if text.strip() else []:
        if s.get("type", "local") != "local" or not s.get("path"): continue
        target = resolve(s["path"], sol)
        if not target.exists(): missing += 1; print(f"missing: {s['path']} (label {s.get('label', '')})")
        if pathlib.Path(s["path"]).is_absolute() and stored_path(target, sol) != str(target):
            new = stored_path(target, sol)
            old_line, new_line = f'path = "{s["path"]}"', f'path = "{new}"'
            if old_line in text: text = text.replace(old_line, new_line, 1); changed += 1; print(f"relative: {s['path']} -> {new}")
    if changed: f.write_text(text)
    print(f"{changed} entr{'y' if changed == 1 else 'ies'} made relative, {missing} missing")

def add_one(sol, location, label, typ):
    target = pathlib.Path(location).expanduser().resolve()
    if typ == "local" and not target.exists(): return f"not found: {target}"
    f = sol / "past-performance" / "sources.toml"
    f.parent.mkdir(parents=True, exist_ok=True)
    text = f.read_text() if f.is_file() else ""
    have = tomllib.loads(text).get("source", []) if text.strip() else []
    if typ == "local" and any(resolve(s.get("path", ""), sol) == target for s in have if s.get("type", "local") == "local") \
            or typ == "drive" and any(s.get("path") == location for s in have if s.get("type") == "drive"):
        return f"already listed: {location if typ == 'drive' else target}"
    path = stored_path(target, sol) if typ == "local" else location
    label = label or (target.name if typ == "local" else location[:12])
    if any(s.get("label") == label for s in have): label = f"{label}-{len(have) + 1}"
    entry = f'\n[[source]]\ntype = "{typ}"\npath = "{path}"\nlabel = "{label}"\n'
    f.write_text(text.rstrip("\n") + "\n" + entry if text.strip() else entry.lstrip("\n"))
    return f"added {typ} source: {path} (label {label})"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("locations", nargs="*"); ap.add_argument("--normalize", action="store_true"); ap.add_argument("--label")
    ap.add_argument("--type", choices=["local", "drive"], default="local"); ap.add_argument("--solution", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    if a.normalize: normalize(sol); sys.exit(0)
    if not a.locations: sys.exit("give a folder or file to add, or use --normalize")
    if a.label and len(a.locations) > 1: sys.exit("--label is for a single location; several locations are labelled by folder name")
    bad = False
    for loc in a.locations:
        msg = add_one(sol, loc, a.label, a.type); print(msg); bad |= msg.startswith("not found")
    sys.exit(1 if bad else 0)
