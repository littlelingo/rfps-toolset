# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Helper module (not run on its own): read capture.md, win-strategy.md and evaluation-sim.md.

Used by refresh_reports.py, flow_status.py and worklist.py. These files are living markdown documents whose tables are the source;
this module only reads them. Every function returns an empty result when the file is missing, so older solutions keep working.
"""
import pathlib, re

DEFAULT_SCALE = ["Outstanding", "Good", "Acceptable", "Marginal", "Unacceptable"]

def _cells(line): return [c.strip() for c in line.strip().strip("|").split("|")]

def _strip_derived(text): return re.sub(r"<!-- derived:(\w+) -->.*?<!-- /derived:\1 -->", "", text, flags=re.S)

def rows(text, idre, ncols):
    """{id: cells} for table rows whose first cell matches idre and that have exactly ncols cells; derived blocks are ignored."""
    out = {}
    for line in _strip_derived(text).split("\n"):
        m = re.match(r"^\| (%s) \|" % idre, line)
        if m and len(_cells(line)) == ncols: out[m.group(1)] = _cells(line)
    return out

def _num(s):
    m = re.search(r"\d+(?:\.\d+)?", s or "")
    return float(m.group(0)) if m else None

def norm(s): return re.sub(r"\s+", " ", re.sub(r"[*_`\"]+", "", s or "")).strip().lower()

def capture(sol):
    """-> dict(decision, pwin, decided_by, date) from capture.md; decision is 'go', 'no-go' or 'undecided'. None when the file is missing."""
    f = pathlib.Path(sol) / "capture.md"
    if not f.is_file(): return None
    t = _strip_derived(f.read_text())
    def field(name):
        m = re.search(r"^\|\s*%s\s*\|\s*(.*?)\s*\|\s*$" % name, t, re.M | re.I)
        return m.group(1).strip() if m else ""
    d = norm(field("Decision"))
    d = "go" if d == "go" else ("no-go" if d in ("no-go", "no go", "nogo") else "undecided")
    return dict(decision=d, pwin=_num(field(r"Probability of win[^|]*")), decided_by=field("Decided by"), date=field("Date"))

def strategy(sol):
    """-> dict(factors=[...], themes=[...]) from win-strategy.md. Factor: id, factor, weight, heading. Theme: id, theme, discriminator, proof, benefit, phrase."""
    f = pathlib.Path(sol) / "win-strategy.md"
    if not f.is_file(): return dict(factors=[], themes=[])
    t = f.read_text()
    fac = [dict(id=k, factor=c[1], weight=_num(c[2]), heading=c[3]) for k, c in rows(t, r"W-\d{2}", 5).items()]
    th = [dict(id=k, theme=c[1], discriminator=c[2], proof=c[3], benefit=c[4], phrase=c[5].strip('"').strip()) for k, c in rows(t, r"T-\d{2}", 6).items()]
    return dict(factors=fac, themes=th)

def weight_by_heading(sol):
    """{normalized response heading: weight percent} for the evaluation factors that have a weight and a heading."""
    return {norm(x["heading"]): x["weight"] for x in strategy(sol)["factors"] if x["weight"] is not None and x["heading"]}

def evalsim(sol):
    """-> dict(scale=[best..worst], rows=[...]) from evaluation-sim.md. Row: id, factor, weight, rating, previous, strengths, weaknesses, change, where."""
    f = pathlib.Path(sol) / "evaluation-sim.md"
    if not f.is_file(): return dict(scale=DEFAULT_SCALE, rows=[])
    t = f.read_text()
    m = re.search(r"\*\*Scale \(best to worst\):\*\*\s*(.+)", t)
    scale = [s.strip() for s in m.group(1).split(",") if s.strip()] if m else DEFAULT_SCALE
    rs = [dict(id=k, factor=c[1], weight=_num(c[2]), rating=c[3], previous=c[4], strengths=c[5], weaknesses=c[6], change=c[7], where=c[8]) for k, c in rows(t, r"V-\d{3}", 9).items()]
    return dict(scale=scale, rows=rs)

def rating_points(rating, scale):
    """0 (worst) to 1 (best) for a rating on the scale; None when the rating is not on the scale."""
    names = [norm(s) for s in scale]
    r = norm(rating)
    if r not in names or len(names) < 2: return None
    return 1 - names.index(r) / (len(names) - 1)
