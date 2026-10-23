# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Keep one shared WIP response docx and push approved response changes into it as tracked changes.

The WIP docx lives next to the template (05 Draft Response by default; override with wip_docx in solution.toml). It is
created once from the template. After that it is never regenerated: other people can add comments and edits, and each
push changes only the paragraphs whose response/*.md text changed, as Word tracked changes (author "rfps") that
reviewers accept or reject. Text others edited in the same paragraph is not overwritten; the change is reported instead.

Usage: rfps-sync-docx [--status | --push | --rebuild] [--solution <folder>] [--force] [--dry-run]
  (no mode)   push: create the WIP docx if it does not exist, else apply markdown changes as tracked changes
  --status    show, per section, whether the markdown or the document has changes; write nothing
  --push      same as no mode
  --rebuild   regenerate the WIP from the template (a backup of the old one goes to the solution's build/ folder);
              this discards everyone's edits and comments in the old file
  --dry-run   with push: report what would change, write nothing
  --force     push even if Word's lock file shows the document is open
"""
import argparse, contextlib, copy, datetime, io, hashlib, json, os, pathlib, shutil, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import build_response as br
import sync_core

AUTHOR = "rfps"
PH_FALLBACK = {"[text]", "text", "[insert table or graphic]"}

# ---------- reading the document (accepted view: pending insertions count, pending deletions do not) ----------

def _under(el, tag):
    p = el.getparent()
    while p is not None:
        if p.tag == qn(tag): return True
        p = p.getparent()
    return False

def par_text(p):
    return " ".join("".join(t.text or "" for t in p.iter(qn("w:t")) if not _under(t, "w:del")).split())

def mark_deleted(p):
    rpr = p.find(qn("w:pPr") + "/" + qn("w:rPr"))
    return rpr is not None and rpr.find(qn("w:del")) is not None

def row_deleted(tr):
    trpr = tr.find(qn("w:trPr"))
    return trpr is not None and trpr.find(qn("w:del")) is not None

def block_text(el):
    """Accepted-view text of a body block, or None when the block is entirely a pending deletion."""
    if el.tag == qn("w:tbl"):
        rows = [r for r in el.iter(qn("w:tr")) if not row_deleted(r)]
        if not rows: return None
        return "\x1e".join("\x1f".join(par_text(c) for c in r.iter(qn("w:tc"))) for r in rows)
    t = par_text(el)
    return None if (mark_deleted(el) and not t) else t

def section_blocks(body, heading_el, is_head, scaffold):
    """Body blocks after a heading up to the next heading, scaffold lines excluded -> [(element, text)]."""
    out, el = [], heading_el.getnext()
    while el is not None and not (el.tag == qn("w:p") and is_head(el)):
        if el.tag in (qn("w:p"), qn("w:tbl")):
            if not (el.tag == qn("w:p") and scaffold(el)):
                t = block_text(el)
                if t is not None: out.append((el, t))
        el = el.getnext()
    return out

class Wip:
    def __init__(self, path, tcfg):
        self.path = pathlib.Path(path)
        self.doc = docx.Document(str(self.path))
        br.HP[0] = tcfg.get("heading_prefix", "Heading"); br.SCAF.clear(); br.SCAF.update(tcfg.get("scaffold_styles", ["Subtitle"]))
        br.PH.clear(); br.PH.update(x.lower() for x in tcfg.get("placeholders", []))
        self.body = self.doc.element.body
        self.style_of = {p._p: p.style.name for p in self.doc.paragraphs}
        self.sections = []   # (heading text, heading element)
        for p in self.doc.paragraphs:
            if br.is_heading(p): self.sections.append((p.text.strip(), p._p))
    def is_head(self, el): return self.style_of.get(el, "").startswith(br.HP[0])
    def scaffold(self, el): return self.style_of.get(el, "") in br.SCAF
    def blocks(self, heading_el): return section_blocks(self.body, heading_el, self.is_head, self.scaffold)

# ---------- tracked-change markup ----------

class Rev:
    def __init__(self, doc):
        ids = [int(e.get(qn("w:id"))) for e in doc.element.body.iter() if e.get(qn("w:id")) and e.get(qn("w:id")).isdigit()]
        self.n = max(ids, default=0) + 1
        self.date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    def el(self, tag):
        e = OxmlElement(f"w:{tag}")
        e.set(qn("w:id"), str(self.n)); self.n += 1
        e.set(qn("w:author"), AUTHOR); e.set(qn("w:date"), self.date)
        return e

def _mark_par(p, rev, kind):
    ppr = p.find(qn("w:pPr"))
    if ppr is None: ppr = OxmlElement("w:pPr"); p.insert(0, ppr)
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None: rpr = OxmlElement("w:rPr"); ppr.append(rpr)
    rpr.insert(0, rev.el(kind))

def _wrap_inserted(p, rev):
    for r in [c for c in p if c.tag == qn("w:r")]:
        ins = rev.el("ins"); r.addprevious(ins); ins.append(r)

def _delete_runs(p, rev):
    for r in [r for r in p.iter(qn("w:r")) if not _under(r, "w:del")]:
        for t in r.findall(qn("w:t")):
            t.tag = qn("w:delText"); t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        d = rev.el("del"); r.addprevious(d); d.append(r)

def _rows(tbl, rev, kind):
    for tr in tbl.iter(qn("w:tr")):
        trpr = tr.find(qn("w:trPr"))
        if trpr is None:
            trpr = OxmlElement("w:trPr"); idx = 1 if tr.find(qn("w:tblPrEx")) is not None else 0; tr.insert(idx, trpr)
        trpr.append(rev.el(kind))

def track_insert(el, rev):
    ps = list(el.iter(qn("w:p"))) if el.tag == qn("w:tbl") else [el]
    if el.tag == qn("w:tbl"): _rows(el, rev, "ins")
    for p in ps: _mark_par(p, rev, "ins"); _wrap_inserted(p, rev)

def track_delete(el, rev):
    ps = list(el.iter(qn("w:p"))) if el.tag == qn("w:tbl") else [el]
    if el.tag == qn("w:tbl"): _rows(el, rev, "del")
    for p in ps: _mark_par(p, rev, "del"); _delete_runs(p, rev)

def _ppr_sig(p):
    ppr = p.find(qn("w:pPr"))
    if ppr is None: return ""
    c = copy.deepcopy(ppr)
    for r in c.findall(qn("w:rPr")): c.remove(r)
    from lxml import etree
    return etree.tostring(c).decode()

def track_replace_inplace(old, new, rev):
    """Same-kind paragraphs: strike the old runs and add the new runs in the same paragraph."""
    _delete_runs(old, rev)
    for r in [c for c in new if c.tag == qn("w:r")]:
        ins = rev.el("ins"); ins.append(r); old.append(ins)

# ---------- helpers ----------

def wip_path(sol, cfg, template, name):
    if cfg.get("wip_docx"): return (sol / cfg["wip_docx"]).resolve()
    return pathlib.Path(template).parent / f"{name}_WIP.docx"

def state_file(sol): return sol / ".state" / "docx-sync.json"

def load_state(sol):
    f = state_file(sol)
    return json.loads(f.read_text()) if f.is_file() else {}

def save_state(sol, st):
    f = state_file(sol); f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")

def snapshot_of(wip):
    return {title: [t for _, t in wip.blocks(hel)] for title, hel in wip.sections}

def render_new(wip, text, snap_texts):
    """Elements and texts the response text renders to. Empty text over a placeholder-only section changes nothing."""
    if not text.strip():
        if all(t.lower() in br.PH or t.lower() in PH_FALLBACK for t in snap_texts): return [], list(snap_texts)
        return [], []
    found = {"stripped": 0, "unresolved": []}
    els = br.make_elements(wip.doc, text, "wip", found)
    texts = []
    for e in els:
        e.getparent().remove(e)
        texts.append(block_text(e))
    return els, texts

def lock_file(path): return path.parent / ("~$" + path.name[2:] if len(path.name) > 2 else "~$" + path.name)

def create_wip(sol, e, path, report):
    out = pathlib.Path(e["out"]); out.mkdir(parents=True, exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):   # the stateless build prints its own report; this tool reports below
        br.build(e["template"], e["response"], str(out), "wip", e["name"], False, e["register"], None, e["tcfg"])
    built = out / f"{e['name']}_WIP.docx"
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, path)
    wip = Wip(path, e["tcfg"])
    st = {"wip": os.path.relpath(path, sol), "sections": snapshot_of(wip), "synced": datetime.datetime.now().isoformat(timespec="seconds")}
    save_state(sol, st)
    report.append(f"Created {path} from the template and the current response text ({len(st['sections'])} sections).")
    return st

# ---------- status and push ----------

def analyse(sol, e, path, st):
    wip = Wip(path, e["tcfg"])
    resp, order = br.parse_response(e["response"])
    heads = {t for t, _ in wip.sections}
    problems = [f"response heading not in the WIP docx: {h}" for h in order if h not in heads] + \
               [f"WIP docx heading missing from response files: {h}" for h in heads if h not in resp]
    rows = []
    for title, hel in wip.sections:
        if title not in resp: continue
        _, _, omit = resp[title]
        snap = st.get("sections", {}).get(title)
        cur = wip.blocks(hel)
        rows.append(dict(title=title, hel=hel, omit=omit, snap=snap, cur=cur))
    return wip, resp, problems, rows

def plan_section(wip, resp, r):
    text = resp[r["title"]][1]
    snap = r["snap"] if r["snap"] is not None else [t for _, t in r["cur"]]
    els, new_texts = render_new(wip, text, snap)
    ops, conflicts, result, drift = sync_core.plan(snap, [t for _, t in r["cur"]], new_texts)
    return dict(snap=snap, els=els, new=new_texts, ops=ops, conflicts=conflicts, result=result, drift=drift)

def evidence_notes(e):
    """Evidence warnings for the response text (same checks the stateless WIP build reports)."""
    if not e.get("register"): return []
    resp, _ = br.parse_response(e["response"])
    reg = br.load_register(e["register"]); ev = br.check_evidence(resp, reg, br.deny_from_register(reg))
    out = [f"Evidence: {len(ev['cited'])} distinct ID(s) cited, {len(reg)} register row(s)."]
    out += [f"  Warning: {x}" for x in ev["issues"]]
    out += [f"  Warning: grounded tag cites no register ID in '{h}': {t}" for h, t in ev["uncited"]]
    out += [f"  Warning: banned phrase '{ph}' in '{h}' ({why})" for h, ph, why in ev["deny"]]
    if ev["unused"]: out.append(f"  Register rows not cited anywhere: {', '.join(ev['unused'])}")
    return out

def status(sol, e, path, st):
    wip, resp, problems, rows = analyse(sol, e, path, st)
    if problems: print("Heading mismatch:\n  " + "\n  ".join(problems))
    n_md = n_doc = 0
    print(f"WIP docx: {path}")
    for r in rows:
        if r["omit"]: print(f"  - {r['title']}: omitted in the response"); continue
        p = plan_section(wip, resp, r)
        notes = []
        if p["ops"] or p["conflicts"]: notes.append(f"response ahead: {len(p['ops'])} change(s) to push" + (f", {len(p['conflicts'])} blocked" if p["conflicts"] else "")); n_md += 1
        if p["drift"]: notes.append(f"document edited: {len(p['drift'])} block(s) differ from the last sync"); n_doc += 1
        print(f"  {'✓' if not notes else '•'} {r['title']}" + (": " + "; ".join(notes) if notes else ": in sync"))
        for c in p["conflicts"]: print(f"      conflict: {c}")
    print(f"{n_md} section(s) with response changes to push, {n_doc} with edits made in the document.")
    print("\n".join(evidence_notes(e)))

def push(sol, e, path, st, dry, force):
    lock = lock_file(path)
    if lock.exists() and not force and not dry:
        sys.exit(f"{path.name} looks open in Word ({lock.name} exists). Ask the person to close it, or use --force.")
    stat0 = (path.stat().st_size, path.stat().st_mtime_ns)
    wip, resp, problems, rows = analyse(sol, e, path, st)
    if problems: sys.exit("Heading mismatch (headings must match exactly):\n  " + "\n  ".join(problems))
    rev = Rev(wip.doc)
    new_state = dict(st); new_state["sections"] = dict(st.get("sections", {}))
    applied = skipped = 0; notes = []
    for r in rows:
        if r["omit"]: continue
        p = plan_section(wip, resp, r)
        if not p["ops"] and not p["conflicts"]:
            if r["snap"] is None: new_state["sections"][r["title"]] = [t for _, t in r["cur"]]
            continue
        cur_els = [el for el, _ in r["cur"]]
        if not dry:
            for op in p["ops"]:
                olds = [cur_els[i] for i in op["cur"]]; news = [p["els"][j] for j in op["new"]]
                anchor = cur_els[op["after"]] if op["after"] is not None else None
                if op["kind"] == "replace" and len(olds) == 1 and len(news) == 1 and olds[0].tag == news[0].tag == qn("w:p") \
                        and _ppr_sig(olds[0]) == _ppr_sig(news[0]):
                    track_replace_inplace(olds[0], news[0], rev); continue
                for o in olds: track_delete(o, rev)
                at = olds[-1] if olds else anchor
                if at is None:   # insert at the start of the section: after the heading and any scaffold lines
                    at = r["hel"]
                    nx = at.getnext()
                    while nx is not None and nx.tag == qn("w:p") and wip.scaffold(nx): at = nx; nx = at.getnext()
                for n in news:
                    track_insert(n, rev); at.addnext(n); at = n
            new_state["sections"][r["title"]] = p["result"]
        applied += len(p["ops"]); skipped += len(p["conflicts"])
        notes.append(f"  {r['title']}: {len(p['ops'])} change(s)" + (f", {len(p['conflicts'])} not applied" if p["conflicts"] else ""))
        for c in p["conflicts"]: notes.append(f"      conflict: {c}")
    print(f"{'Would push' if dry else 'Pushed'} {applied} change(s) as tracked changes (author {AUTHOR}); {skipped} skipped because the document was edited there.")
    print("\n".join(notes) if notes else "  Nothing to push: the WIP docx already matches the response text.")
    print("\n".join(evidence_notes(e)))
    if dry or not applied and not any(new_state["sections"].get(k) != st.get("sections", {}).get(k) for k in new_state["sections"]):
        if not dry: save_state(sol, new_state)
        return
    if (path.stat().st_size, path.stat().st_mtime_ns) != stat0:
        sys.exit("The WIP docx changed while syncing; nothing was written. Run again.")
    tmp = path.with_name(path.name + ".rfps-tmp")
    wip.doc.save(str(tmp)); os.replace(tmp, path)
    new_state["synced"] = datetime.datetime.now().isoformat(timespec="seconds")
    save_state(sol, new_state)
    print(f"Wrote {path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true"); ap.add_argument("--push", action="store_true")
    ap.add_argument("--rebuild", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--solution", nargs="?", const="", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    e = br.load_engagement(str(sol))
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    path = wip_path(sol, cfg, e["template"], e["name"])
    st = load_state(sol); report = []
    if a.rebuild and path.is_file():
        bak = pathlib.Path(e["out"]); bak.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, bak / f"{path.stem}.{stamp}.bak.docx")
        report.append(f"Backed up the old WIP to {bak / (path.stem + '.' + stamp + '.bak.docx')}")
        path.unlink(); st = {}
    if not path.is_file():
        if a.status: sys.exit(f"No shared WIP docx yet ({path}). Run rfps-sync-docx to create it.")
        if a.dry_run: sys.exit(f"Would create {path} from the template.")
        if (path.parent / ("~$" + path.name[2:])).exists() and not a.force: sys.exit("The WIP location has a Word lock file; use --force.")
        st = create_wip(sol, e, path, report)
        print("\n".join(report + evidence_notes(e))); sys.exit(0)
    if not st.get("sections"):
        wip = Wip(path, e["tcfg"])
        sys.exit(f"{path} exists but has no sync record ({state_file(sol)}). Use --rebuild to regenerate it from the template (backs up the old file), or restore .state/docx-sync.json.")
    if report: print("\n".join(report))
    if a.status: status(sol, e, path, st)
    else: push(sol, e, path, st, a.dry_run, a.force)
