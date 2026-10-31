# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Helper module (not run on its own): remember which version of each response section a review looked at.

After the compliance check, the tone review or the second-reader run, `rfps-flow-status --validated NAME` records a hash of every
response/*.md file in .state/validated.json. A review is stale only for the sections whose text changed since, so touching a file
without changing it does not matter and a one-line edit names exactly the section to re-check.
"""
import datetime, hashlib, json, pathlib, re

NAMES = ("compliance", "empathy", "evalsim")

def _hash(text): return hashlib.sha1(re.sub(r"[ \t]+\n", "\n", text).strip().encode()).hexdigest()[:12]

def current(sol, cfg):
    return {p.name: _hash(p.read_text()) for p in sorted((pathlib.Path(sol) / cfg.get("response_dir", "response")).glob("*.md"))}

def _file(sol): return pathlib.Path(sol) / ".state" / "validated.json"

def load(sol):
    f = _file(sol)
    return json.loads(f.read_text()) if f.is_file() else {}

def record(sol, cfg, name):
    st = load(sol); st[name] = dict(at=datetime.datetime.now().isoformat(timespec="seconds"), files=current(sol, cfg))
    _file(sol).parent.mkdir(parents=True, exist_ok=True); _file(sol).write_text(json.dumps(st, indent=1) + "\n")
    return len(st[name]["files"])

def stale(sol, cfg, name):
    """Response files changed, added or removed since the review was recorded -> sorted list; None when it was never recorded."""
    rec = load(sol).get(name)
    if rec is None: return None
    now, then = current(sol, cfg), rec["files"]
    return sorted([f for f in now if then.get(f) != now[f]] + [f for f in then if f not in now])
