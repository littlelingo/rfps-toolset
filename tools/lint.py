# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl", "pypdf", "python-pptx"]
# ///
"""Mechanical writing checks on response/*.md: the patterns that make a proposal read like it was written for anyone.

The empathy reviewer judges tone; this counts what can be counted, so it runs every time the reports refresh and no reviewer has to:
  superlatives     best-in-class, world-class, cutting-edge, robust, seamless, leverage, synergy ... (empty words an evaluator skips)
  passive          "will be <done>" with no "by <who>": nobody is accountable
  we-ratio         how often "we/our" outnumber the client's own name or terms in a section
  acronyms         capitalised abbreviations never defined and not used by the solicitation itself
  duplicates       near-identical paragraphs in different sections (boilerplate that evaluators notice)
  vocabulary       the client's key terms from brief.md that the response never uses
It lists candidates for a person to read. Hedge words (approximately, various, as needed, strive to) are counted for information.

Optional in solution.toml:
  [lint]
  mute = ["acronyms"]                       # rule ids to switch off
  client_terms = ["Riverbend County", "the County", "DPW"]   # names that stand for the client (enables we-ratio)
  we_ratio = 3                              # flag a section where we/our outnumber client terms by more than this
  acronyms_ok = ["WCAG", "SOC"]             # abbreviations that need no definition
Usage: rfps-lint [--solution [folder]] [--text-dir <folder of extracted .txt>]
"""
import argparse, collections, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import solicit_text as st

SUPER = re.compile(r"best[- ]in[- ]class|world[- ]class|industry[- ]leading|unparalleled|unmatched|second to none|cutting[- ]edge|state[- ]of[- ]the[- ]art|leading provider|\brobust\b|\bseamless(?:ly)?\b|\bsynerg(?:y|ies)\b|\bleverag(?:e|es|ed|ing)\b|\bturnkey\b|game[- ]chang\w*|\binnovative\b|proven (?:methodology|track record|approach)", re.I)
PASSIVE = re.compile(r"\b(?:will|shall|can|should|must) be (?!by\b)(\w+(?:ed|en))\b(?!\s+by\b)", re.I)
HEDGE = re.compile(r"\b(?:approximately|various|etc\.?|and so on|as needed|as appropriate|best efforts|strive to|try to|we believe|we feel)\b", re.I)
ACRO = re.compile(r"\b[A-Z]{2,6}s?\b")
COMMON_ACRONYMS = set("US USA PDF IT ID FAQ AM PM URL API CEO CFO CIO CTO FTE LOE SLA QA UAT HR PO".split())
WE = re.compile(r"\b(?:we|our|us|ours)\b", re.I)

def clean(text):
    t = br.TAG_RE.sub("", text)
    return re.sub(r"[*`]+", "", re.sub(r"<!--.*?-->", "", t, flags=re.S))

def body_lines(text):
    return [l for l in clean(text).split("\n") if l.strip() and not l.lstrip().startswith("#")]

def key_terms(sol):
    f = sol / "brief.md"
    if not f.is_file(): return []
    m = re.search(r"Client's Key Terms:?\*{0,2}(.*?)(?=\n\*\*|\n## )", f.read_text(), re.S)
    out = []
    for line in (m.group(1) if m else "").split("\n"):
        mm = re.match(r"^\s*[-*]\s*\**\[?([^:\]\n]{2,60})\]?\**\s*:", line)
        if mm and "[" not in mm.group(1): out.append(mm.group(1).strip().strip("*"))
    return out

def shingles(s, n=5):
    w = re.findall(r"[a-z0-9']+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}

def run(sol, cfg, groups, solicitation_text=""):
    """groups = {top-level heading: text}. -> {rule id: [finding strings]} (hedges under 'hedges', information only)."""
    c = cfg.get("lint", {}); mute = set(c.get("mute", [])); out = collections.defaultdict(list)
    known = set(ACRO.findall(solicitation_text)) | COMMON_ACRONYMS | set(c.get("acronyms_ok", []))
    if "superlatives" not in mute:
        for h, t in groups.items():
            hits = [m.group(0) for m in SUPER.finditer(clean(t))]
            if hits: out["superlatives"].append(f"{h}: {', '.join(sorted(set(x.lower() for x in hits)))} ({len(hits)})")
    if "passive" not in mute:
        for h, t in groups.items():
            for m in PASSIVE.finditer(clean(t)): out["passive"].append(f"{h}: \"{clean(t)[max(0, m.start() - 25):m.end() + 15].strip()}\"".replace("\n", " "))
    terms = c.get("client_terms", [])
    if "ratio" not in mute and terms:
        for h, t in groups.items():
            tt = clean(t); we = len(WE.findall(tt)); cl = sum(len(re.findall(re.escape(x), tt, re.I)) for x in terms)
            if we >= 5 and we > float(c.get("we_ratio", 3)) * max(cl, 1): out["ratio"].append(f"{h}: we/our {we} times, the client {cl} time(s)")
    if "acronyms" not in mute:
        alltext = "\n".join(clean(t) for t in groups.values()); seen = {}
        defined = set(re.findall(r"\(([A-Z]{2,6})\)", alltext)) | set(re.findall(r"\b([A-Z]{2,6}) \(", alltext))
        for h, t in groups.items():
            for l in body_lines(t):
                for a in ACRO.findall(l):
                    a = a.rstrip("s") if a.endswith("s") and a[:-1].isupper() and len(a) > 2 else a
                    if a not in known and a not in defined and a not in seen: seen[a] = h
        out["acronyms"] = [f"{a} (first used in {h})" for a, h in seen.items()]
    if "duplicates" not in mute:
        paras = [(h, p.strip()) for h, t in groups.items() for p in re.split(r"\n\s*\n", clean(t)) if len(p.split()) >= 15 and not p.lstrip().startswith(("#", "|"))]
        sh = [shingles(p) for _, p in paras]
        for i in range(len(paras)):
            for j in range(i + 1, len(paras)):
                if paras[i][0] != paras[j][0] and sh[i] and sh[j] and len(sh[i] & sh[j]) / min(len(sh[i]), len(sh[j])) >= 0.6:
                    out["duplicates"].append(f"{paras[i][0]} and {paras[j][0]}: \"{paras[i][1][:70]}...\"")
    if "vocabulary" not in mute:
        kt = key_terms(cfg["_sol"]) if "_sol" in cfg else []
        low = "\n".join(clean(t) for t in groups.values()).lower()
        out["vocabulary"] = [x for x in kt if x.lower() not in low]
        out["_terms"] = kt
    out["hedges"] = [f"{h}: {len(HEDGE.findall(clean(t)))}" for h, t in groups.items() if HEDGE.search(clean(t))]
    return out

def checks(sol, cfg, groups, docs=None):
    """Table rows for the compliance report's automated checks."""
    c = cfg.get("lint", {}); mute = set(c.get("mute", [])); docs = docs if docs is not None else st.load_text(sol, cfg)[0]
    f = run(sol, {**cfg, "_sol": sol}, groups, "\n".join(t for _, t in docs))
    show = lambda xs, n=4: "; ".join(xs[:n]) + (" ..." if len(xs) > n else "")
    rows = []
    def row(rule, name, status, detail): rows.append(f"| Writing: {name} | {'Info' if rule in mute else status} | {'muted in solution.toml' if rule in mute else detail} |")
    row("superlatives", "no empty superlatives or buzzwords", "Pass" if not f["superlatives"] else "Open", f"{len(f['superlatives'])} section(s): {show(f['superlatives'])}" if f["superlatives"] else "none found")
    row("passive", "commitments name who does them", "Pass" if len(f["passive"]) <= 3 else "Open", f"{len(f['passive'])} 'will be <done>' with no actor: {show(f['passive'], 3)}" if f["passive"] else "none found")
    if c.get("client_terms") or "ratio" in mute: row("ratio", "the client is mentioned more than we are", "Pass" if not f["ratio"] else "Open", show(f["ratio"]) if f["ratio"] else "no section is mostly about us")
    else: rows.append("| Writing: the client is mentioned more than we are | Info | set client_terms under [lint] in solution.toml to check this |")
    row("acronyms", "acronyms defined on first use", "Pass" if not f["acronyms"] else "Open", f"{len(f['acronyms'])} undefined: {show(f['acronyms'], 6)}" if f["acronyms"] else "none found")
    row("duplicates", "no near-duplicate paragraphs across sections", "Pass" if not f["duplicates"] else "Open", show(f["duplicates"], 2) if f["duplicates"] else "none found")
    if f.get("_terms"): row("vocabulary", "the client's key terms are used", "Pass" if not f["vocabulary"] else "Open", f"never used: {', '.join(f['vocabulary'][:8])}" if f["vocabulary"] else f"all {len(f['_terms'])} terms from brief.md appear")
    else: rows.append("| Writing: the client's key terms are used | Info | no key terms found in brief.md |")
    rows.append(f"| Writing: hedge words | Info | {show(f['hedges'], 6) or 'none'} (approximately, various, as needed, strive to ...) |")
    return rows

def groups_of(sol, cfg):
    resp, order = br.parse_response(sol / cfg.get("response_dir", "response")); groups, cur = collections.OrderedDict(), None
    for h in order:
        lvl, body, omit = resp[h]
        if lvl <= 2: cur = h; groups.setdefault(cur, "")
        if cur is not None and not omit: groups[cur] += "\n" + body
    return groups

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default=""); ap.add_argument("--text-dir", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); cfg = tomllib.loads((sol / "solution.toml").read_text())
    docs, _ = st.load_text(sol, cfg, a.text_dir)
    f = run(sol, {**cfg, "_sol": sol}, groups_of(sol, cfg), "\n".join(t for _, t in docs))
    for rule in ("superlatives", "passive", "ratio", "acronyms", "duplicates", "vocabulary", "hedges"):
        xs = f.get(rule, [])
        print(f"\n{rule}: {len(xs)}" + ("" if not xs else "\n" + "\n".join("  - " + x for x in xs[:25])))

if __name__ == "__main__":
    main()
