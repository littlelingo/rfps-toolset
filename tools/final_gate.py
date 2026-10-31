# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl", "pypdf", "python-pptx"]
# ///
"""Check the PDF that will be submitted, before it goes out. Reads only; --scrub writes a cleaned copy beside it.

Checks (Pass, Fail or Info), each from the file itself or from the solution's own records:
  file name and size; page count against page_limit; page size; text can be extracted; no internal marker text, register IDs
  or placeholders; required wording present; no links to Google Docs or Drive; approximate margins and the fonts used;
  metadata (author, creator, subject, keywords); blocking items in the compliance report; unresolved response markers;
  evidence cited that is not cleared; open rows in submission.md.
Margins are measured from where text sits on the page: the left margin is exact for left-aligned text, top and bottom are
approximate (a header, footer or page number counts), the right margin is not measured, and only the left margin can fail.

Optional in solution.toml:
  [final_gate]
  exclude_pages = 1            # pages not counted against page_limit (cover, table of contents)
  max_mb = 10                  # largest file the State accepts
  name_pattern = "^[A-Za-z0-9_ -]+\\.pdf$"
  required_text = ["Attachment B", "authorized representative"]   # wording that must appear
  margin_inches = 1.0
  page_size = "letter"         # or "a4"

Usage: rfps-final-gate [--solution [folder]] [--pdf FILE] [--scrub] [--json]
  Without --pdf the newest .pdf in final_copy_dir (else the build folder) is checked.
  Writes final-gate.md in the solution folder. Exit status 1 when anything fails.
"""
import argparse, datetime, json, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import refresh_reports as rr
import strategy as sg
import open_items
from pypdf import PdfReader, PdfWriter

PAGE_SIZES = {"letter": (612, 792), "a4": (595, 842)}
LEAK = re.compile(r"\[(?:GROUNDED|ASSERTION|DECISION|OPEN|EVIDENCE NEEDED|SOLUTIONING|REVIEW)[^\]]*\]|\[text\]|\[insert[^\]]*\]|\bE-\d{3}\b|\bTBD\b", re.I)
BAD_LINK = re.compile(r"docs\.google\.com|drive\.google\.com|localhost|127\.0\.0\.1", re.I)

def find_pdf(sol, eng, given):
    if given: return pathlib.Path(given).expanduser()
    dirs = [pathlib.Path(d) for d in (eng.get("final_copy"), eng.get("out")) if d]
    pdfs = [p for d in dirs if d.is_dir() for p in d.glob("*.pdf") if not p.stem.endswith("_scrubbed")]
    return max(pdfs, key=lambda p: p.stat().st_mtime) if pdfs else None

def text_margins(reader):
    """-> (left, right, top, bottom) smallest margins in points over all pages, from where text sits; right, top and bottom are approximate."""
    L = R = T = B = None
    for page in reader.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height); seen = []
        def visit(text, cm, tm, font_dict, font_size):
            if not text or not text.strip(): return
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]; y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]; fs = abs(font_size) or 10
            seen.append((x, y, fs, len(text)))
        try: page.extract_text(visitor_text=visit)
        except Exception: continue
        if not seen: continue
        l = min(s[0] for s in seen); r = w - max(s[0] + s[3] * s[2] * 0.5 for s in seen); t = h - max(s[1] + s[2] for s in seen); b = min(s[1] for s in seen)
        L = l if L is None else min(L, l); R = r if R is None else min(R, r); T = t if T is None else min(T, t); B = b if B is None else min(B, b)
    return L, R, T, B

def fonts_of(reader):
    names = set()
    for page in reader.pages:
        try:
            for f in (page["/Resources"].get("/Font") or {}).values():
                names.add(str(f.get_object().get("/BaseFont", "?")).lstrip("/").split("+")[-1])
        except Exception: pass
    return sorted(names)

def run(sol, cfg, eng, pdf_arg):
    g = cfg.get("final_gate", {}); rows = []
    def add(name, status, detail): rows.append((name, status, detail))
    pdf = find_pdf(sol, eng, pdf_arg)
    if not pdf or not pdf.is_file():
        add("PDF found", "Fail", "no PDF given and none in final_copy_dir or the build folder; export the final Google Doc to PDF and save it there"); return None, rows
    try: reader = PdfReader(str(pdf))
    except Exception as e:
        add("PDF opens", "Fail", f"{pdf.name}: {e}"); return pdf, rows
    add("PDF found", "Pass", f"{pdf.name} ({pdf.stat().st_size / 1e6:.2f} MB, {len(reader.pages)} pages)")
    if g.get("name_pattern"): add("File name matches the required pattern", "Pass" if re.search(g["name_pattern"], pdf.name) else "Fail", f"{pdf.name} against {g['name_pattern']}")
    if g.get("max_mb"): add("File size within the limit", "Pass" if pdf.stat().st_size / 1e6 <= float(g["max_mb"]) else "Fail", f"{pdf.stat().st_size / 1e6:.2f} MB of {g['max_mb']} MB")
    n = len(reader.pages); ex = int(g.get("exclude_pages", 0)); lim = cfg.get("page_limit")
    if lim: add("Page count within page_limit", "Pass" if n - ex <= lim else "Fail", f"{n} pages{f' minus {ex} excluded' if ex else ''} = {n - ex} against a limit of {lim}")
    else: add("Page count within page_limit", "Info", f"{n} pages; set page_limit in solution.toml to check it")
    sizes = {(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in reader.pages}
    want = PAGE_SIZES.get(str(g.get("page_size", "")).lower())
    desc = ", ".join(f"{w / 72:.1f} x {h / 72:.1f} in" for w, h in sorted(sizes))
    if want: add("Page size", "Pass" if sizes == {want} else "Fail", f"{desc}; wanted {g['page_size']}")
    else: add("Page size", "Info", desc)
    texts = []
    for p in reader.pages:
        try: texts.append(p.extract_text() or "")
        except Exception: texts.append("")
    thin = [i + 1 for i, t in enumerate(texts) if len(t.strip()) < 80]
    add("Text can be extracted", "Pass" if not thin else "Fail", "every page has text" if not thin else f"page(s) with little or no text (scanned images?): {', '.join(map(str, thin[:10]))}")
    leaks = [(i + 1, m.group(0)[:40]) for i, t in enumerate(texts) for m in LEAK.finditer(t)]
    add("No internal markers, register IDs or placeholders", "Pass" if not leaks else "Fail", "none found" if not leaks else "; ".join(f"page {p}: {s}" for p, s in leaks[:8]) + (" ..." if len(leaks) > 8 else ""))
    full = "\n".join(texts).lower()
    for phrase in g.get("required_text", []): add(f"Required wording present: {phrase}", "Pass" if phrase.lower() in full else "Fail", "found" if phrase.lower() in full else "not found in the extracted text")
    links = []
    for i, p in enumerate(reader.pages):
        for a in (p.get("/Annots") or []):
            try:
                uri = a.get_object().get("/A", {}).get("/URI")
                if uri and BAD_LINK.search(str(uri)): links.append(f"page {i + 1}: {uri}")
            except Exception: pass
    add("No links to Google Docs, Drive or local addresses", "Pass" if not links else "Fail", "none found" if not links else "; ".join(links[:5]))
    L, R, T, B = text_margins(reader)
    if L is not None:
        inch = lambda v: f"{v / 72:.2f}"
        note = f"left {inch(L)} in (exact for left-aligned text); top {inch(T)}, bottom {inch(B)} in (approximate; a header, footer or page number counts as text); right not measured"
        if g.get("margin_inches"): add("Left margin at least the required size", "Pass" if L / 72 >= float(g["margin_inches"]) - 0.05 else "Fail", f"{note}; required {g['margin_inches']} in")
        else: add("Margins", "Info", note)
    fl = fonts_of(reader)
    add("Fonts used", "Info", ", ".join(fl) or "none found")
    md = reader.metadata or {}
    meta = {k.lstrip("/"): str(v) for k, v in md.items() if v}
    risky = [k for k, v in meta.items() if (k in ("Author", "Subject", "Keywords") and v.strip()) or "@" in v]
    add("Metadata free of names and emails", "Pass" if not risky else "Fail", ("; ".join(f"{k}={v}" for k, v in meta.items()) or "no metadata") + (". Run with --scrub for a cleaned copy." if risky else ""))
    # the solution's own records
    cr = sol / "compliance-report.md"
    if cr.is_file():
        crow = rr.rows_of(cr.read_text(), r"[FCSP]-\d{3}", 7, [])
        bl = [k for k, c in crow.items() if c[3] == "Yes" and c[4] == "Fail"]
        add("No blocking compliance items", "Pass" if crow and not bl else ("Info" if not crow else "Fail"), "no check rows recorded yet" if not crow else (f"blocking: {', '.join(bl)}" if bl else f"{len(crow)} checks, none blocking"))
    mk = [x for x in open_items.scan(sol / cfg.get("response_dir", "response")) if x["kind"] in ("DECISION", "OPEN", "EVIDENCE NEEDED")]
    add("No unresolved decisions, open questions or evidence needs in the response", "Pass" if not mk else "Fail", "none" if not mk else f"{len(mk)} open: " + "; ".join(f"{x['kind']} in {x['file']}" for x in mk[:5]))
    try:
        reg = br.load_register(eng["register"]) if eng.get("register") and pathlib.Path(eng["register"]).is_file() else None
        if reg is not None:
            resp, _ = br.parse_response(eng["response"]); ev = br.check_evidence(resp, reg, br.deny_from_register(reg))
            bad = [i for i in ev["cited"] if (reg.get(i, {}).get("clearance") or "").strip() != "cleared" or i not in reg]
            add("Evidence cited is cleared", "Pass" if not (bad or ev["issues"]) else "Fail", f"{len(ev['cited'])} IDs cited" + (f"; not cleared: {', '.join(sorted(bad))}" if bad else ""))
    except Exception as e: add("Evidence cited is cleared", "Info", f"not checked: {e}")
    sub = sg.submission(sol)
    if sub:
        opn = [r for r in sub if r["status"].lower() not in ("done", "n/a", "na")]
        add("Mandatory forms and steps in submission.md are done", "Pass" if not opn else "Fail", f"{len(sub)} item(s)" + (f"; open: {', '.join(r['id'] + ' ' + r['item'][:40] for r in opn[:5])}" if opn else ", all done"))
    else: add("Mandatory forms and steps in submission.md are done", "Info", "submission.md has no rows; list the signature page, forms and acknowledgements with /rfps:submission")
    return pdf, rows

def scrub(pdf, title):
    r = PdfReader(str(pdf)); w = PdfWriter()
    for p in r.pages: w.add_page(p)
    w.add_metadata({"/Title": title or pdf.stem, "/Author": "", "/Creator": "", "/Producer": "", "/Subject": "", "/Keywords": ""})
    out = pdf.with_name(pdf.stem + "_scrubbed.pdf")
    with open(out, "wb") as fh: w.write(fh)
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default=""); ap.add_argument("--pdf"); ap.add_argument("--scrub", action="store_true"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); cfg = tomllib.loads((sol / "solution.toml").read_text()); eng = br.load_engagement(str(sol))
    pdf, rows = run(sol, cfg, eng, a.pdf)
    fails = [r for r in rows if r[1] == "Fail"]
    out = [f"# Final Gate - {cfg.get('title', sol.parent.name)}", "", f"Generated by `rfps-final-gate` on {datetime.datetime.now().isoformat(timespec='minutes')}. Do not edit.", "",
           f"**Result: {'FAIL - ' + str(len(fails)) + ' check(s) failed' if fails else 'PASS'}**" + (f" for {pdf.name}" if pdf else ""), "",
           "| Check | Result | Detail |", "|-------|--------|--------|"] + [f"| {n} | {s} | {d.replace('|', '/')} |" for n, s, d in rows]
    if a.scrub and pdf and pdf.is_file():
        try: cleaned = scrub(pdf, cfg.get("title", ""))
        except Exception as e: sys.exit(f"scrub failed: {e}")
        out += ["", f"Cleaned copy written: {cleaned} (author, creator, producer, subject and keywords cleared; the original is untouched). Check the cleaned copy again with --pdf before submitting it."]
    (sol / "final-gate.md").write_text("\n".join(out) + "\n")
    if a.json: print(json.dumps(dict(pdf=str(pdf) if pdf else None, failed=len(fails), checks=[dict(check=n, result=s, detail=d) for n, s, d in rows]), indent=1))
    else: print("\n".join(out))
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
