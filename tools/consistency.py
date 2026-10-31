# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl", "pypdf", "python-pptx"]
# ///
"""Find numbers that disagree: between the solicitation and the response, between sections of the response, and between the roster and the text.

A reader who finds one wrong figure doubts the rest, so this looks for the mismatches a person misses:
  - the solicitation says "within 7 months" and the response says 6 or 9; "at least 3 days" and the response says 2
  - the response still uses a figure an amendment replaced ("extended from 6 months to 7 months")
  - one section says 3 days and another says 5 days about the same thing
  - a person on the roster is not named anywhere in the response
Numbers are compared only when they have the same unit (months, days, weeks, years, hours, pages, percent, dollars) and the two sentences share
wording, so it reports candidates for a person to look at, not verdicts. It reads only; nothing is changed.

Usage: rfps-consistency [--solution [folder]] [--text-dir <folder of extracted .txt>]
"""
import argparse, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import solicit_text as st
import resources as rs

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
UNITS = r"(business days|calendar days|working days|months?|days?|weeks?|years?|hours?|pages?|percent|%)"
NUM = r"(\d[\d,]*(?:\.\d+)?|" + "|".join(WORDS) + r")"
QTY = re.compile(r"(?<![\w$.-])" + NUM + r"[\s-]*" + UNITS + r"\b", re.I)
MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(million|thousand|[KMB])?\b", re.I)
FROM_TO = re.compile(r"from\s+" + NUM + r"\s*" + UNITS + r"?\s+to\s+" + NUM + r"\s*" + UNITS + r"?", re.I)
MIN_W = re.compile(r"at least|minimum|no fewer|not less|or more|no less", re.I)
MAX_W = re.compile(r"within|no later|not exceed|no more|maximum|up to|at most|not more|less than|or fewer|or less", re.I)
GENERIC = set("contractor offeror vendor county state agency proposal response shall must will required within least after before each every per project work system portal provide ensure deliver deliverable".split())

def unit_of(u): u = u.lower(); return "percent" if u in ("%", "percent") else re.sub(r"s$", "", u.replace("business ", "").replace("calendar ", "").replace("working ", ""))

def val(n): n = n.lower().replace(",", ""); return float(WORDS[n]) if n in WORDS else float(n)

def quantities(s):
    out = [(val(m.group(1)), unit_of(m.group(2))) for m in QTY.finditer(s)]
    for m in MONEY.finditer(s):
        v = float(m.group(1).replace(",", "")) * {"m": 1e6, "k": 1e3, "t": 1e3, "b": 1e9}.get((m.group(2) or "")[:1].lower(), 1); out.append((v, "usd"))
    return out

def ctx(s):
    toks = {t for t in re.findall(r"[a-z][a-z-]{2,}", st.norm(s)) if t not in st.STOP and t not in GENERIC and not re.fullmatch(r"months?|days?|weeks?|years?|hours?|pages?|percent", t)}
    return toks

def sentences(docs):
    out = []
    for fname, text in docs:
        head = ""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#"): head = line.lstrip("# ").strip(); continue
            for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z0-9(\[])", re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", line)):
                if len(s.split()) >= 4: out.append(dict(file=fname, where=head, text=s.strip()))
    return out

def response_sentences(sol, cfg):
    resp, order = br.parse_response(sol / cfg.get("response_dir", "response")); out = []
    for h in order:
        lvl, body, omit = resp[h]
        if omit: continue
        clean = br.TAG_RE.sub("", body)
        for s in sentences([(h, re.sub(r"[|*`]", " ", clean))]): out.append(dict(s, where=h))
    return out

def rules(docs):
    """The figures the solicitation sets: [{value, unit, dir ('min','max','exact'), ctx, text, where, old}] with amendment changes applied (old = the replaced figure)."""
    sents = sentences(docs); changes = []; base = []
    for s in sents:
        m = FROM_TO.search(s["text"])
        if m:
            u = unit_of(m.group(2) or m.group(4) or "")
            if u: changes.append(dict(old=val(m.group(1)), new=val(m.group(3)), unit=u, ctx=ctx(s["text"]), s=s))
        elif st.MANDATORY.search(s["text"]) or st.ACTOR_WILL.search(s["text"]): base.append(s)
    out, used = [], set()
    for s in base:
        d = "min" if MIN_W.search(s["text"]) else ("max" if MAX_W.search(s["text"]) else "exact")
        for v, u in quantities(s["text"]):
            r = dict(value=v, unit=u, dir=d, ctx=ctx(s["text"]), text=s["text"], where=s["where"] or s["file"], old=None)
            for i, c in enumerate(changes):
                if c["unit"] == u and c["old"] == v and len(c["ctx"] & r["ctx"]) >= 2: r.update(value=c["new"], old=v); used.add(i)
            out.append(r)
    for i, c in enumerate(changes):   # a change that shares no wording with its base sentence still applies when exactly one base figure has the old value and unit
        if i in used: continue
        same = [r for r in out if r["unit"] == c["unit"] and r["value"] == c["old"] and r["old"] is None]
        if len(same) == 1: same[0].update(value=c["new"], old=c["old"]); used.add(i)
    for i, c in enumerate(changes):
        if i not in used: out.append(dict(value=c["new"], unit=c["unit"], dir="exact", ctx=c["ctx"], text=c["s"]["text"], where=c["s"]["where"] or c["s"]["file"], old=c["old"]))
    return out

def ok(rule, v):
    return v >= rule["value"] if rule["dir"] == "min" else (v <= rule["value"] if rule["dir"] == "max" else v == rule["value"])

def against_solicitation(rs_, resp):
    found = []
    for r in resp:
        for v, u in quantities(r["text"]):
            for rule in rs_:
                if rule["unit"] != u or len(rule["ctx"] & ctx(r["text"])) < 2: continue
                if rule["old"] is not None and v == rule["old"] and v != rule["value"]:
                    found.append(dict(kind="superseded", section=r["where"], resp=r["text"], rfp=rule["text"], note=f"uses {v:g} {u}, the figure an amendment replaced with {rule['value']:g}"))
                elif not ok(rule, v):
                    found.append(dict(kind="differs", section=r["where"], resp=r["text"], rfp=rule["text"], note=f"says {v:g} {u}; the solicitation sets {rule['dir'] if rule['dir'] != 'exact' else 'exactly'} {rule['value']:g}"))
    seen, out = set(), []
    for f in found:
        k = (f["section"], f["resp"][:60], f["note"])
        if k not in seen: seen.add(k); out.append(f)
    return out

def across_sections(resp):
    found = []; qs = [(r, quantities(r["text"]), ctx(r["text"])) for r in resp]
    for i, (a, qa, ca) in enumerate(qs):
        for b, qb, cb in qs[i + 1:]:
            if a["where"] == b["where"] or len(ca & cb) < 3: continue
            for va, ua in qa:
                for vb, ub in qb:
                    if ua == ub and va != vb and not any(ua == u2 and va == v2 for v2, u2 in qb) and not any(ub == u2 and vb == v2 for v2, u2 in qa):
                        found.append(dict(kind="sections", section=f"{a['where']} / {b['where']}", resp=a["text"], rfp=b["text"], note=f"{va:g} {ua} here, {vb:g} {ub} there, about the same thing"))
    seen, out = set(), []
    for f in found:
        k = (f["resp"][:50], f["rfp"][:50])
        if k not in seen: seen.add(k); out.append(f)
    return out

def roster_missing(sol, cfg, resp):
    path = rs.roster_path(sol, cfg); rows = rs.load(path)
    if rows is None: return None
    text = st.norm(" ".join(r["text"] for r in resp)); miss = []
    for r in rs.active(rows):
        p = r.get("person", "").strip()
        if p and p.upper() != "TBD" and r.get("in_response", "").lower() == "yes" and st.norm(p) not in text: miss.append(f"{r['id']} {p}")
    return miss

def checks(sol, cfg, docs=None):
    """Table rows for the compliance report's automated checks."""
    resp = response_sentences(sol, cfg); out = []
    if docs is None: docs, _ = st.load_text(sol, cfg)
    if docs:
        f = against_solicitation(rules(docs), resp)
        out.append(f"| Numbers match the solicitation | {'Pass' if not f else 'Open'} | " + (f"{len(f)} to look at: " + "; ".join(f"{x['section']}: {x['note']}" for x in f[:4]) + (" ..." if len(f) > 4 else "") + ". Run rfps-consistency for the sentences." if f else "no figure in the response disagrees with a solicitation figure it shares wording with") + " |")
    else: out.append("| Numbers match the solicitation | Info | no solicitation text to compare with |")
    f = across_sections(resp)
    out.append(f"| Numbers agree across sections | {'Pass' if not f else 'Open'} | " + (f"{len(f)} to look at: " + "; ".join(f"{x['section']}: {x['note']}" for x in f[:3]) + (" ..." if len(f) > 3 else "") if f else "no two sections give different figures for the same thing") + " |")
    miss = roster_missing(sol, cfg, resp)
    if miss is None: out.append("| People on the roster are named in the response | Info | no roster |")
    else: out.append(f"| People on the roster are named in the response | {'Pass' if not miss else 'Open'} | " + (f"not found: {', '.join(miss)}" if miss else "every named person flagged in_response appears in the text") + " |")
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default=""); ap.add_argument("--text-dir", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); cfg = tomllib.loads((sol / "solution.toml").read_text())
    docs, note = st.load_text(sol, cfg, a.text_dir); resp = response_sentences(sol, cfg)
    found = (against_solicitation(rules(docs), resp) if docs else []) + across_sections(resp)
    print(f"Consistency ({note}): {len(found)} candidate(s) to look at.")
    for x in found:
        print(f"\n- [{x['kind']}] {x['section']}: {x['note']}\n    response: {x['resp'][:200]}\n    {'solicitation' if x['kind'] != 'sections' else 'other section'}: {x['rfp'][:200]}")
    miss = roster_missing(sol, cfg, resp)
    if miss: print("\nRoster people not named in the response: " + ", ".join(miss))

if __name__ == "__main__":
    main()
