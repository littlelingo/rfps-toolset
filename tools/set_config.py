# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Record where the shared outputs and the machine-local working files go, in solution.toml.

  wip_folder      Drive folder (id or link) where the shared Google WIP and the template copy are created
  wip_docx        path of the shared Word WIP (default: next to the template in 05 Draft Response)
  final_copy_dir  folder the FINAL docx is copied to (default: 11 Final Submission)
  cache_dir       a folder on THIS machine for text caches and scratch builds, so they are never synced to Drive;
                  also sets build_dir to <cache_dir>/<slug>/build
  solicitation_type  rfp (default) or rfi; an RFI makes the staffing and attachment steps optional

The skills ask for these locations and use the defaults only when none is given. Run with no VALUE to show the current setting.

Usage: rfps-set-config KEY [VALUE] [--solution [folder]]
       rfps-set-config --show
"""
import argparse, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import tomlio

KEYS = {"wip_folder", "wip_docx", "final_copy_dir", "cache_dir", "solicitation_type"}

def drive_id(text):
    m = re.search(r"/(?:folders|d)/([\w-]{10,})|[?&]id=([\w-]{10,})", text)
    return (m.group(1) or m.group(2)) if m else text.strip()

def put(cfgfile, key, value): tomlio.set_key(cfgfile, key, value)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("key", nargs="?"); ap.add_argument("value", nargs="?"); ap.add_argument("--show", action="store_true")
    ap.add_argument("--solution", default="")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); f = sol / "solution.toml"; cfg = tomllib.loads(f.read_text())
    if a.show or not a.key:
        for k in sorted(KEYS | {"build_dir"}): print(f"{k} = {cfg.get(k, '(default)')}")
        return
    if a.key not in KEYS: sys.exit(f"unknown setting {a.key}; choose one of {', '.join(sorted(KEYS))}")
    if a.value is None: print(f"{a.key} = {cfg.get(a.key, '(default)')}"); return
    v = a.value.strip()
    if a.key == "wip_folder": v = drive_id(v)
    if a.key == "solicitation_type" and v not in ("rfp", "rfi"): sys.exit("solicitation_type must be rfp or rfi")
    if a.key == "cache_dir":
        p = pathlib.Path(v).expanduser().resolve()
        if "CloudStorage/GoogleDrive" in str(p) or "/Google Drive/" in str(p): sys.exit(f"{p} is inside Google Drive; the cache must be a folder on this machine outside Drive")
        build = p / cfg.get("slug", sol.parent.name) / "build"; build.mkdir(parents=True, exist_ok=True)
        put(f, "cache_dir", str(p)); put(f, "build_dir", str(build))
        print(f"cache_dir = {p}\nbuild_dir = {build}"); return
    put(f, a.key, v); print(f"{a.key} = {v}")

if __name__ == "__main__":
    main()
