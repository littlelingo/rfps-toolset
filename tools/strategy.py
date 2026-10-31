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

DONE_WORDS = {"yes", "y", "done", "complete", "completed", "applied", "n/a", "na", "none"}

def status_word(s):
    """The first word of a status cell, lower case: 'Done 2026-05-02' -> 'done', 'Yes - section 3.2' -> 'yes', 'N/A' -> 'n/a'."""
    m = re.match(r"\s*([a-z/]+)", (s or "").lower())
    return m.group(1) if m else ""

def is_done(s):
    """True for a status that means finished or not needed, however it is worded after the first word."""
    t = (s or "").strip().lower()
    return status_word(t) in DONE_WORDS or t.startswith(("not applicable", "no change", "not needed"))

def norm(s): return re.sub(r"\s+", " ", re.sub(r"[*_`\"]+", "", s or "")).strip().lower()

_TABLES = {"coverage-matrix.md": [(r"R-\d{3}", 9)], "compliance-report.md": [(r"[FCSPN]-\d{3}", 7)], "win-strategy.md": [(r"W-\d{2}", 5), (r"T-\d{2}", 6), (r"X-\d{2}", 6)],
           "submission.md": [(r"M-\d{2}", 7)], "questions.md": [(r"Q-\d{2}", 7)], "evaluation-sim.md": [(r"V-\d{3}", 9)]}

def malformed(sol):
    """Table rows in the living documents whose first cell is an ID but whose cell count is wrong (usually a stray '|'). The parsers skip such rows, so they are listed here."""
    out = []
    for fn, specs in _TABLES.items():
        f = pathlib.Path(sol) / fn
        if not f.is_file(): continue
        for line in _strip_derived(f.read_text()).split("\n"):
            for idre, n in specs:
                m = re.match(r"^\| (%s) \|" % idre, line)
                if m and len(_cells(line)) != n: out.append(f"{fn} {m.group(1)} has {len(_cells(line))} cells, expected {n}")
    return out

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

def submission(sol):
    """-> [dict(id, item, source, owner, due, status, notes)] from submission.md (the mandatory forms and steps tracker); [] when the file is missing."""
    f = pathlib.Path(sol) / "submission.md"
    if not f.is_file(): return []
    return [dict(id=k, item=c[1], source=c[2], owner=c[3], due=c[4], status=c[5], notes=c[6]) for k, c in rows(f.read_text(), r"M-\d{2}", 7).items()]

def amendments(sol):
    """-> [dict(id, type, date, file, change, affected, response_updated, analysis_rerun)] from amendments/log.md; rows with a number in the first cell."""
    f = pathlib.Path(sol) / "amendments" / "log.md"
    if not f.is_file(): return []
    out = []
    for line in f.read_text().split("\n"):
        c = _cells(line) if line.startswith("|") else []
        if len(c) == 8 and re.match(r"^\d+$", c[0]): out.append(dict(id=c[0], type=c[1], date=c[2], file=c[3], change=c[4], affected=c[5], response_updated=c[6], analysis_rerun=c[7]))
    return out

def questions(sol):
    """-> [dict(id, question, why, due, status, answer, logged)] from questions.md; [] when the file is missing."""
    f = pathlib.Path(sol) / "questions.md"
    if not f.is_file(): return []
    return [dict(id=k, question=c[1], why=c[2], due=c[3], status=c[4], answer=c[5], logged=c[6]) for k, c in rows(f.read_text(), r"Q-\d{2}", 7).items()]

def exhibits(sol):
    """-> [dict(id, section, exhibit, proves, caption, status)] from the exhibit plan in win-strategy.md."""
    f = pathlib.Path(sol) / "win-strategy.md"
    if not f.is_file(): return []
    return [dict(id=k, section=c[1], exhibit=c[2], proves=c[3], caption=c[4], status=c[5]) for k, c in rows(f.read_text(), r"X-\d{2}", 6).items()]

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
