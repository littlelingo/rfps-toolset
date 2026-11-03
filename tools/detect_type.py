# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl", "pypdf", "python-pptx"]
# ///
"""Say whether a folder of solicitation documents is an RFI (request for information, sources sought) or an RFP, from what the notice itself says.

Reads the filename and the opening of each solicitation file (the title and disclaimer), not the whole text: a draft PWS inside an RFI is full of
"shall" language and must not make it look like a bid. Prints JSON: type (rfi, rfp or unclear), the two scores and the phrases that decided it.
Nothing is changed.

Usage: rfps-detect-type [FOLDER] [--json]
  FOLDER  the source (capture) folder, its solicitation folder, or one file (default: here)
"""
import argparse, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import extract_docs as ex

HEAD = 3000   # characters read from the start of each file
RFI = [(r"sources sought", 3), (r"request(?:s)? for information", 3), (r"\brfi\b", 2),
       (r"no (?:proposals?|quotations?|bids?) (?:are|is|will be) (?:being )?(?:requested|accepted)", 3), (r"not (?:a|an) (?:solicitation|request for (?:proposals?|quotations?))", 3),
       (r"for (?:preliminary )?planning purposes only", 2), (r"market research", 1), (r"capability statements?", 1)]
RFP = [(r"request(?:s)? for (?:proposals?|quotations?)", 3), (r"\brf[pq]\b", 2), (r"evaluation factors?|basis for award|best value|source selection", 2),
       (r"offerors? shall|proposals? (?:are|is) due|proposals? must", 2)]
# phrases that name a proposal request only to deny it; remove them before scoring the RFP side
DENIAL = re.compile(r"not (?:a|an) (?:solicitation|request for (?:proposals?|quotations?))|no (?:proposals?|quotations?) (?:are|is|will be) (?:being )?(?:requested|accepted)", re.I)

def candidates(p):
    if p.is_file(): return [p]
    sub = next((d for d in sorted(p.iterdir()) if d.is_dir() and re.search(r"^0?1\b.*solicit", d.name, re.I)), None) if p.is_dir() else None
    root = sub or p
    files = [f for f in sorted(root.rglob("*")) if f.is_file() and f.suffix.lower() in ex.H and not f.name.startswith((".", "~$"))]
    return files[:12]

def score(files):
    rfi = rfp = 0; sig = []
    for f in files:
        try: text = ex.extract_file(f)
        except Exception: continue
        blob = (f.name + "\n" + text[:HEAD]).lower()
        a = b = 0
        for pat, w in RFI:
            if m := re.search(pat, blob): a += w; sig.append(dict(file=f.name, side="rfi", phrase=m.group(0)))
        cleaned = DENIAL.sub(" ", blob)
        for pat, w in RFP:
            if m := re.search(pat, cleaned): b += w; sig.append(dict(file=f.name, side="rfp", phrase=m.group(0)))
        rfi += min(a, 8); rfp += min(b, 8)   # one file cannot decide by repeating itself
    return rfi, rfp, sig

def decide(rfi, rfp):
    if rfi >= 3 and rfi >= 2 * rfp: return "rfi"
    if rfp >= 3 and rfp >= 2 * rfi: return "rfp"
    return "unclear"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", default="."); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    p = pathlib.Path(a.folder).expanduser().resolve()
    if not p.exists(): sys.exit(f"not found: {p}")
    files = candidates(p); rfi, rfp, sig = score(files)
    out = dict(type=decide(rfi, rfp), rfi_score=rfi, rfp_score=rfp, files=[f.name for f in files], signals=sig)
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
