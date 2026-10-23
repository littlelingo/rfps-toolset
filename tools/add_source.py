# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Add a past-performance source location to past-performance/sources.toml (read in place, never copied).

A location inside the capture (source) folder is stored relative to active-solution/, the same base solution.toml
uses, so the entry survives moving or syncing the folder. A location elsewhere is stored as an absolute path.
An entry for the same location is not added twice.

Usage: rfps-add-source <folder or file> [--label NAME] [--type local|drive] [--solution <folder>]
"""
import argparse, os, pathlib, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br

def stored_path(target, sol):
    """Path as stored in sources.toml: relative to the solution folder when under the capture folder, else absolute."""
    capture = sol.parent
    try:
        target.relative_to(capture)
    except ValueError:
        return str(target)
    return os.path.relpath(target, sol)

def resolve(entry_path, sol):
    """Absolute path of a stored entry (relative entries are relative to the solution folder)."""
    p = pathlib.Path(entry_path)
    return p if p.is_absolute() else (sol / p).resolve()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("location"); ap.add_argument("--label"); ap.add_argument("--type", choices=["local", "drive"], default="local")
    ap.add_argument("--solution", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution)
    target = pathlib.Path(a.location).expanduser().resolve()
    if a.type == "local" and not target.exists(): sys.exit(f"not found: {target}")
    f = sol / "past-performance" / "sources.toml"
    f.parent.mkdir(parents=True, exist_ok=True)
    text = f.read_text() if f.is_file() else ""
    have = tomllib.loads(text).get("source", []) if text.strip() else []
    if any(resolve(s.get("path", ""), sol) == target for s in have if s.get("type", "local") == a.type):
        print(f"already listed: {target}"); sys.exit(0)
    path = stored_path(target, sol) if a.type == "local" else a.location
    label = a.label or target.name
    entry = f'\n[[source]]\ntype = "{a.type}"\npath = "{path}"\nlabel = "{label}"\n'
    f.write_text(text.rstrip("\n") + "\n" + entry if text.strip() else entry.lstrip("\n"))
    print(f"added {a.type} source: {path} (label {label})")
