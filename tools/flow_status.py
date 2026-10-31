# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Where is this solution in the flow? Status, checklist, section detail, and change detection.

Usage (the active-solution pointer is used when --solution is omitted):
  rfps-flow-status                      status: progress bar, next steps, steps by group (refreshes progress.md)
  rfps-flow-status --sections           every response heading with a color-coded state
  rfps-flow-status --detail <id|text>   what a step or a section still needs (step id or part of a heading)
  rfps-flow-status --set <id> done|skip|reset   change your override for a step in progress.md
  rfps-flow-status --changed            sections whose text changed since the last integration (with diffs)
  rfps-flow-status --validated NAME     record the response text as just checked (compliance, empathy or evalsim); the step then names the sections edited since
  rfps-flow-status --baseline [text]    record current text as integrated (all sections, or headings matching text)
  rfps-flow-status --unbaseline [text]  forget the integrated version (all sections, or headings matching text) so /rfps:integrate reviews them
  rfps-flow-status --table              the same status as markdown tables (the default view for /rfps:status; needs no widget)
  rfps-flow-status --json               machine-readable status

States: done (green), needs attention (orange), blocking (red), not started (white), skipped / not applicable (blue).
progress.md checkbox: [ ] use the detected state, [x] you mark it done, [-] skip / not applicable. Your mark wins.
"""
import argparse, datetime, difflib, json, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import refresh_reports as rr
import solicit_text as sol_txt
import strategy as sg
import validated as vd
import docx

ICON = {"done": "🟢", "attention": "🟠", "blocking": "🔴", "todo": "⚪", "skipped": "🔵"}
LABEL = {"done": "done", "attention": "needs attention", "blocking": "blocking", "todo": "not started", "skipped": "skipped / not applicable"}
TAGS5 = ["EVIDENCE NEEDED", "DECISION", "OPEN", "SOLUTIONING"]
RANK = {"blocking": 4, "attention": 3, "todo": 2, "done": 1, "skipped": 0}

class Ctx:
    def __init__(self, sol):
        self.sol = sol
        self.cfg = tomllib.loads((sol / "solution.toml").read_text())
        self.eng = br.load_engagement(str(sol))
        self.resp, self.order = br.parse_response(self.eng["response"])
        self.reg = br.load_register(self.eng["register"]) if self.eng.get("register") and pathlib.Path(self.eng["register"]).is_file() else None
        self.ev = br.check_evidence(self.resp, self.reg, br.deny_from_register(self.reg) if self.reg else None) if self.reg is not None else None
        rdir = pathlib.Path(self.eng["response"])
        self.newest = max([p.stat().st_mtime for p in rdir.glob("*.md")] or [0])
        self.state_dir = sol / ".state"
        mf = self.state_dir / "integrated.json"
        self.baseline = json.loads(mf.read_text()) if mf.is_file() else {}
    def leaves(self):
        out = []
        for i, h in enumerate(self.order):
            lvl, text, omit = self.resp[h]
            has_child = i + 1 < len(self.order) and self.resp[self.order[i + 1]][0] > lvl
            if not has_child and not omit: out.append(h)
        return out
    def texted(self):
        """Every non-omitted heading that has its own text, including containers such as a Heading 1 with an intro."""
        return [h for h in self.order if self.resp[h][1].strip() and not self.resp[h][2]]
    def has_children(self, h):
        i = self.order.index(h); return i + 1 < len(self.order) and self.resp[self.order[i + 1]][0] > self.resp[h][0]

def marks(text):
    tags = {k: len(re.findall(r"\[" + k, text)) for k in TAGS5}
    t = re.sub(r"\[(?:GROUNDED|ASSERTION|EVIDENCE NEEDED|DECISION|OPEN|SOLUTIONING)[^\]]*\]", "", text, flags=re.S)
    br_ = len(re.findall(r"\[[^\]\n]{2,}\]", t))
    return tags, br_

def cited_ids(text): return set(re.findall(r"E-\d+", " ".join(re.findall(r"\[GROUNDED:([^\]]*)\]", text))))

def heading_states(c):
    st = {}
    deny = br.deny_from_register(c.reg) if c.reg else []
    for h in c.order:
        lvl, text, omit = c.resp[h]; own = text.strip()
        notes = []
        if omit: st[h] = ("skipped", ["omitted from the final copy"]); continue
        s = "todo" if not own else "done"
        if own:
            tags, brk = marks(own)
            if sum(tags.values()) + brk: s = "attention"; notes.append(", ".join(f"{v} {k}" for k, v in tags.items() if v) + (f"{', ' if sum(tags.values()) else ''}{brk} bracketed placeholder(s)" if brk else ""))
            bad = [i for i in cited_ids(own) if c.reg is not None and ((c.reg.get(i, {}).get("clearance") or "").strip() != "cleared" or c.reg.get(i, {}).get("superseded_by", "").strip())]
            if bad: s = "attention" if s != "blocking" else s; notes.append(f"evidence not cleared: {', '.join(sorted(bad))}")
            hits = [ph for ph, _ in deny if ph.lower() in own.lower()]
            if hits: s = "blocking"; notes.append(f"banned phrase: {', '.join(hits)}")
            if c.baseline.get(h, "").strip() != own: s = "attention" if s == "done" else s; notes.append("changed since last integration")
        st[h] = (s, notes)
    # roll up containers
    for h in reversed(c.order):
        if not c.has_children(h): continue
        i = c.order.index(h); kids = []
        for hh in c.order[i + 1:]:
            if c.resp[hh][0] <= c.resp[h][0]: break
            if c.resp[hh][0] == c.resp[h][0] + 1: kids.append(st[hh][0])
        own_s, notes = st[h]
        ks = [k for k in kids if k != "skipped"]
        if not ks: continue
        if any(k == "blocking" for k in ks): roll = "blocking"
        elif any(k == "attention" for k in ks): roll = "attention"
        elif all(k == "todo" for k in ks): roll = "todo" if own_s == "todo" else own_s
        elif any(k == "todo" for k in ks): roll = "attention"
        else: roll = "done"
        if RANK[own_s] > RANK[roll] and own_s != "todo": roll = own_s
        st[h] = (roll, notes)
    return st

def pending_integration(c):
    return [h for h in c.texted() if c.baseline.get(h, "").strip() != c.resp[h][1].strip()]

# ---- step detectors: return (state, detail)
def d_solution_exists(c): return "done", "solution.toml found"
def d_solicitation_found(c):
    d = c.cfg.get("solicitation_dir")
    if not d: return "attention", "solicitation_dir is not set in solution.toml"
    p = (c.sol / d).resolve()
    if not p.is_dir(): return "attention", f"folder not found: {d}"
    n = len([f for f in p.rglob("*") if f.is_file() and not f.name.startswith(".")])
    return ("done", f"{n} file(s) in {d}") if n else ("todo", f"{d} is empty")
def d_template_ok(c):
    hp = c.eng["tcfg"].get("heading_prefix", "Heading")
    try: heads = [p.text.strip() for p in docx.Document(c.eng["template"]).paragraphs if p.style.name.startswith(hp) and p.text.strip()]
    except Exception as e: return "attention", f"cannot read template: {e}"
    miss = [h for h in heads if h not in c.resp]; extra = [h for h in c.resp if h not in heads]
    return ("done", f"{len(heads)} headings match") if not (miss or extra) else ("attention", f"missing from response: {', '.join(miss[:4]) or 'none'}; not in template: {', '.join(extra[:4]) or 'none'}")
def d_brief_exists(c):
    f = c.sol / "brief.md"; return ("done", "brief.md present") if f.is_file() and f.stat().st_size > 300 else ("todo", "brief.md not written yet")
def d_requirements_recorded(c):
    f = c.sol / "coverage-matrix.md"
    rows = rr.rows_of(f.read_text(), r"R-\d{3}", 9, []) if f.is_file() else {}
    n = len(rows)
    if not n: return "todo", "coverage matrix has no rows"
    try:   # cheap deterministic backstop: obligation sentences in the extracted solicitation text that no row covers (see rfps-sweep)
        docs, _ = sol_txt.load_text(c.sol, c.cfg, live=False)
        un = [r for r in sol_txt.sweep(docs, {k: v[1] for k, v in rows.items()}) if not r["mapped"] and r["cls"] == "mandatory"] if docs else []
    except Exception: un = []
    if un: return "attention", f"{n} requirements recorded, but {len(un)} mandatory obligation sentence(s) in the solicitation have no row (run rfps-sweep)"
    return "done", f"{n} requirements recorded"
def d_bid_decision(c):
    cp = sg.capture(c.sol)
    if cp is None: return "todo", "no capture.md yet (run /rfps:capture)"
    if cp["decision"] == "undecided": return "todo", "bid decision not recorded in capture.md"
    if cp["decision"] == "no-go": return "attention", "recorded as No-go; confirm you mean to keep going or stop here"
    return "done", "Go" + (f", pWin {cp['pwin']:.0f}%" if cp["pwin"] is not None else ", pWin not stated") + (f", decided by {cp['decided_by']}" if cp["decided_by"] else "")
def d_strategy_recorded(c):
    s = sg.strategy(c.sol); th, fac = s["themes"], s["factors"]
    if not th and not fac: return "todo", "no win-strategy.md content yet"
    if not fac: return "attention", "evaluation factors and weights not listed"
    if not 3 <= len(th) <= 5: return "attention", f"{len(th)} win theme(s); aim for 3 to 5"
    prop = [t["id"] for t in th if "(proposed)" in t["theme"].lower()]
    if prop: return "attention", f"{len(prop)} proposed theme(s) waiting for your approval: {', '.join(prop)}"
    weak = [t["id"] for t in th if not (t["discriminator"] and t["proof"] and t["benefit"] and t["phrase"])]
    if weak: return "attention", f"theme(s) missing a discriminator, proof, benefit or key phrase: {', '.join(weak)}"
    return "done", f"{len(fac)} factor(s), {len(th)} theme(s)"
def d_evalsim_run(c):
    e = sg.evalsim(c.sol); f = c.sol / "evaluation-sim.md"
    if not e["rows"]: return "todo", "no second-reader ratings yet"
    ch = vd.stale(c.sol, c.cfg, "evalsim")
    if ch: return "attention", f"{len(ch)} section(s) changed since the last second-reader run: {', '.join(ch[:4])}"
    if ch is None and f.stat().st_mtime < c.newest: return "attention", "response changed since the last second-reader run"
    pts = [(r, sg.rating_points(r["rating"], e["scale"])) for r in e["rows"]]
    low = [r["factor"] for r, p in pts if p is not None and p <= 0.25]
    return ("attention", f"{len(low)} factor(s) rated in the bottom of the scale: {', '.join(low[:4])}") if low else ("done", f"{len(e['rows'])} factor(s) rated, none in the bottom of the scale")
def d_pp_sources(c):
    f = c.sol / "past-performance" / "sources.toml"
    n = len(tomllib.loads(f.read_text()).get("source", [])) if f.is_file() else 0
    return ("done", f"{n} source location(s)") if n else ("todo", "no source locations listed")
def d_register_rows(c):
    n = len(c.reg) if c.reg is not None else 0
    return ("done", f"{n} register row(s)") if n else ("todo", "evidence register is empty")
def d_evidence_cleared(c):
    if c.ev is None or not c.ev["cited"]: return "todo", "the response cites no evidence yet"
    bad = [i for i in c.ev["cited"] if (c.reg.get(i, {}).get("clearance") or "").strip() != "cleared" or c.reg.get(i, {}).get("superseded_by", "").strip() or i not in c.reg]
    if c.ev["deny"] or c.ev["uncited"]: return "blocking", f"{len(c.ev['deny'])} banned phrase hit(s), {len(c.ev['uncited'])} grounded note(s) without an ID"
    return ("done", f"all {len(c.ev['cited'])} cited items cleared") if not bad else ("attention", f"{len(bad)} of {len(c.ev['cited'])} cited items not cleared: {', '.join(sorted(bad)[:6])}{' ...' if len(bad) > 6 else ''}")
def d_resources_defined(c):
    import resources as rs
    rows = rs.load(rs.roster_path(c.sol, c.cfg)) if hasattr(c, "cfg") else rs.load(c.sol / "response" / "resources.csv")
    if rows is None: return "todo", "response/resources.csv not present"
    rows = rs.active(rows)
    if not rows: return "todo", "the roster has no roles"
    kp = [r for r in rows if r["status"] == "KP"]
    open_ = [r["id"] for r in kp if r["person"].upper() in ("", "TBD") or r["resume"] != "Checked"]
    s = rs.stats(rows)
    if not kp: return "attention", f"{len(rows)} role(s) but none marked KP"
    head = f"{rs.fmt_people(s['people'])} people, {rs.fmt_fte(s['fte'])} FTE"
    return ("attention", f"{head}; Key Personnel not yet named and checked: {', '.join(open_)}") if open_ else ("done", f"{head}; {len(kp)} KP role(s) named and checked")
def d_files_tracked(c):
    import file_audit as fa
    un, rec = fa.audit(c.sol)
    rv = [k for k, r in rec.items() if r[4] in ("Review", "Remove")]
    if un: return "attention", f"{len(un)} file(s) not recorded: {', '.join(u[0] for u in un[:4])}"
    if rv: return "attention", f"{len(rv)} recorded file(s) marked Review or Remove: {', '.join(rv[:4])}"
    return "done", f"every file is standard or recorded ({len(rec)} recorded)"
def d_draft_complete(c):
    lv = c.leaves(); have = [h for h in lv if c.resp[h][1].strip()]
    if not lv: return "todo", "no response headings"
    return ("done", f"all {len(lv)} sections have text") if len(have) == len(lv) else (("attention", f"{len(have)} of {len(lv)} sections have text") if have else ("todo", f"0 of {len(lv)} sections have text"))
def d_integrated(c):
    p = pending_integration(c)
    if not p and not c.texted(): return "todo", "no text to integrate yet"
    return ("done", "no unintegrated changes") if not p else ("attention", f"{len(p)} section(s) changed since last integration")
def d_markers_resolved(c):
    tot = collections_total(c)
    if not c.texted(): return "todo", "no text yet"
    if c.ev and c.ev["deny"]: return "blocking", f"banned phrase in text: {', '.join(sorted({p for _, p, _ in c.ev['deny']}))}"
    return ("done", "none left") if not tot[0] else ("attention", f"{tot[1]} note(s) and {tot[2]} placeholder(s) left in {tot[0]} section(s)")
def collections_total(c):
    secs = notes = brk = 0
    for h in c.texted():
        t, b = marks(c.resp[h][1])
        if sum(t.values()) + b: secs += 1; notes += sum(t.values()); brk += b
    return secs, notes, brk
def d_empathy_reviewed(c):
    f = c.sol / "review-notes.md"
    if not f.is_file(): return "todo", "no review yet"
    ch = vd.stale(c.sol, c.cfg, "empathy")
    if ch is not None: return ("done", "reviewed; no section has changed since") if not ch else ("attention", f"{len(ch)} section(s) changed since the tone review: {', '.join(ch[:4])}")
    return ("done", "reviewed after the latest changes") if f.stat().st_mtime >= c.newest else ("attention", "response changed since the review")
def d_compliance_ok(c):
    f = c.sol / "compliance-report.md"
    if not f.is_file(): return "todo", "no compliance report"
    t = f.read_text(); rows = rr.rows_of(t, r"[FCSP]-\d{3}", 7, [])
    if not rows: return "todo", "no check rows recorded"
    bl = [k for k, v in rows.items() if v[3] == "Yes" and v[4] == "Fail"]
    pa = [k for k, v in rows.items() if v[4] in ("Partial", "Ambiguous")]
    if bl: return "blocking", f"{len(bl)} blocking check(s): {', '.join(bl[:6])}{' ...' if len(bl) > 6 else ''}"
    ch = vd.stale(c.sol, c.cfg, "compliance")
    if ch: return "attention", f"{len(ch)} section(s) changed since the compliance check: {', '.join(ch[:4])}"
    return ("attention", f"{len(pa)} partial or ambiguous check(s)") if pa else ("done", f"{len(rows)} checks, none blocking")
def newest_build(c, suffix):
    ds = [pathlib.Path(c.eng["out"])] + ([pathlib.Path(c.eng["final_copy"])] if c.eng.get("final_copy") else [])
    fs = [f for d in ds if d.is_dir() for f in d.glob(f"*_{suffix}.docx")]
    return max(fs, key=lambda f: f.stat().st_mtime) if fs else None
def d_wip_current(c):
    try:
        import sync_gdoc as sg
        g = sg.summary(c.sol)
    except Exception: g = {"exists": False}
    if g.get("exists"):
        when = g["synced"][:16].replace("T", " ")
        if g["md_ahead"]: return "attention", f"{g['md_ahead']} section(s) have response changes not in the shared Google Doc yet (/rfps:build-wip); last synced {when}"
        return "done", f"shared Google Doc matches the response as of {when}; run /rfps:pull-wip to check for edits made in it"
    try:
        import sync_docx as sd
        s = sd.summary(c.sol)
    except Exception: s = {"exists": False}
    if s.get("exists"):
        if s["doc_edits"]: return "attention", f"{s['doc_edits']} section(s) edited in the shared WIP docx are not in the response yet (/rfps:pull-docx)"
        if s["md_ahead"]: return "attention", f"{s['md_ahead']} section(s) have response changes not in the shared WIP docx yet (/rfps:build-wip)"
        return "done", f"{s['path'].name} is in sync with the response"
    f = newest_build(c, "WIP")
    if not f: return "todo", "no work-in-progress build yet"
    return ("done", f"{f.name} is current") if f.stat().st_mtime >= c.newest else ("attention", "response changed since the last build")
def d_doc_review(c):
    try:
        import sync_gdoc as sg
        g = sg.summary(c.sol)
    except Exception: g = {"exists": False}
    if not g.get("exists"): return "done", "not using a Google Doc (comments and suggestions are checked in Word)"
    o = g.get("observed") or {}
    if not o: return "todo", "the shared Google Doc has not been read yet (/rfps:pull-wip)"
    n, m = o.get("suggestions", 0), o.get("open_comments")
    note = f"as of {o['at'][:16].replace('T', ' ')}"
    if n or m: return "attention", f"{n} suggestion(s) waiting to be accepted or rejected and {m if m is not None else 'unknown'} open comment(s), {note}"
    return "done", f"no pending suggestions or open comments, {note}" if m is not None else f"no pending suggestions, {note}; comments not read"
def d_final_current(c):
    f = newest_build(c, "FINAL")
    if not f: return "todo", "no final build yet"
    return ("done", f"{f.name} is current") if f.stat().st_mtime >= c.newest else ("attention", "response changed since the last final build")
def d_final_gate_ok(c):
    f = c.sol / "final-gate.md"
    if not f.is_file(): return "todo", "the exported PDF has not been checked (run /rfps:final-gate)"
    t = f.read_text(); m = re.search(r"\*\*Result: (PASS|FAIL[^*]*)\*\*( for (\S+))?", t)
    if not m: return "todo", "final-gate.md has no result"
    if m.group(1).startswith("FAIL"): return "blocking", f"{m.group(1).strip()} (see final-gate.md)"
    return ("done", f"{m.group(3) or 'the PDF'} passed") if f.stat().st_mtime >= c.newest else ("attention", "response changed since the final gate ran; export and check again")
DETECT = {n[2:]: fn for n, fn in globals().items() if n.startswith("d_")}

def load_flow(): return tomllib.loads((pathlib.Path(__file__).resolve().parent / "flow.toml").read_text())["step"]

def read_overrides(sol):
    f = sol / "progress.md"; ov = {}
    if f.is_file():
        for line in f.read_text().split("\n"):
            m = re.match(r"^- \[([ x\-])\] \S+ `([a-z0-9-]+)`", line)
            if m: ov[m.group(2)] = m.group(1)
    return ov

def compute(c):
    ov = read_overrides(c.sol); out = []
    for s in load_flow():
        det = s.get("check"); mark = ov.get(s["id"], " ")
        if mark == "x": state, detail = "done", "marked done by you"
        elif mark == "-": state, detail = "skipped", "skipped / not applicable (your choice)"
        elif s.get("kind") == "manual": state, detail = "todo", "manual step: check it off when done"
        else: state, detail = DETECT[det](c)
        out.append({**s, "state": state, "detail": detail, "mark": mark})
    return out

def bar(n, d): k = round(10 * n / d) if d else 0; return "█" * k + "░" * (10 - k)

def write_progress(c, steps):
    L = ["# Progress", "", f"Last updated {datetime.date.today()} by `rfps-flow-status`. You can edit only the checkbox on each line: `[ ]` use the detected state, `[x]` you mark it done, `[-]` skip / not applicable. The rest of each line is rewritten when the status refreshes.", "",
         "Legend: 🟢 done  🟠 needs attention  🔴 blocking  ⚪ not started  🔵 skipped / not applicable", ""]
    g = None
    for s in steps:
        if s["group"] != g: g = s["group"]; L += ["", f"## {g}", ""]
        L.append(f"- [{s['mark']}] {ICON[s['state']]} `{s['id']}` {s['title']} - {s['detail']}")
    (c.sol / "progress.md").write_text("\n".join(L) + "\n")

def summary(steps):
    cnt = {k: sum(1 for s in steps if s["state"] == k) for k in ICON}
    total = len(steps) - cnt["skipped"]; n = cnt["done"]
    return cnt, f"Progress  {bar(n, total)}  {n} of {total} steps done ({round(100*n/total) if total else 0}%)   " + "  ".join(f"{ICON[k]} {cnt[k]}" for k in ICON)

def next_up(steps):
    cand = [s for s in steps if s["state"] in ("blocking", "attention", "todo")]
    cand.sort(key=lambda s: (-RANK[s["state"]] if s["state"] == "blocking" else 0, steps.index(s)))
    return cand[:3]

def cmd_status(c, steps):
    cnt, line = summary(steps); out = [line, "", "Next up:"]
    for i, s in enumerate(next_up(steps), 1):
        out.append(f"  {i}. {ICON[s['state']]} {s['title']} - {s['detail']}\n     Do: {s.get('command', 'edit the files named in the help')}   Ask: {s.get('ask','')}")
    if len(out) == 3: out.append("  Nothing open. Everything detected is done or skipped.")
    g = None
    for s in steps:
        if s["group"] != g: g = s["group"]; out += ["", g]
        out.append(f"  {ICON[s['state']]} {s['id']:<14} {s['title']} - {s['detail']}")
    out += ["", "More: --sections (every heading) | --detail <step id or heading text> | --set <id> done|skip|reset | progress.md has the checklist"]
    return "\n".join(out)

def cmd_table(c, steps):
    cnt, line = summary(steps); total = len(steps) - cnt["skipped"]; n = cnt["done"]
    out = [f"### Progress: {n} of {total} steps done ({round(100*n/total) if total else 0}%)", "",
           f"`{bar(n, total)}` " + " · ".join(f"{ICON[k]} {cnt[k]} {LABEL[k]}" for k in ICON if cnt[k]), "", "### Next up", "",
           "| # | | Step | What is missing | Do this |", "|---|---|------|-----------------|---------|"]
    nxt = next_up(steps)
    for i, s in enumerate(nxt, 1):
        out.append(f"| {i} | {ICON[s['state']]} | {s['title']} | {s['detail']} | {('`' + s['command'] + '`') if s.get('command') else 'edit the files named in the help'} |")
    if not nxt: out.append("| | | Nothing open | Everything detected is done or skipped | |")
    out += ["", "### All steps", "", "| Group | Step | Status | Detail |", "|-------|------|:------:|--------|"]
    g = None
    for s in steps:
        grp = f"**{s['group']}**" if s["group"] != g else ""
        g = s["group"]
        out.append(f"| {grp} | {s['title']} | {ICON[s['state']]} | {s['detail']} |")
    return "\n".join(out)

def cmd_sections(c):
    st = heading_states(c); out = ["| State | Section | Words | What it needs |", "|---|---|---|---|"]
    for h in c.order:
        lvl, text, omit = c.resp[h]; w = len(text.split()); s, notes = st[h]
        out.append(f"| {ICON[s]} | {'&nbsp;&nbsp;' * (lvl - 1)}{h} | {w or ''} | {'; '.join(n for n in notes if n) or ('has sections below' if c.has_children(h) and not text.strip() else '')} |")
    cnt = {k: sum(1 for h in c.order if st[h][0] == k) for k in ICON}
    return "  ".join(f"{ICON[k]} {cnt[k]} {LABEL[k]}" for k in ICON) + "\n\n" + "\n".join(out)

def cmd_detail(c, steps, key):
    k = key.lower()
    for s in steps:
        if s["id"] == k:
            return "\n".join([f"{ICON[s['state']]} {s['title']}  [{LABEL[s['state']]}]", f"Detected: {s['detail']}", f"What is needed: {s['help']}", f"Run: {s.get('command','-')}", f"Question to answer: {s.get('ask','')}"])
    hs = [h for h in c.order if k in h.lower()]
    if not hs: return f"No step id or heading matches '{key}'."
    st = heading_states(c); out = []
    for h in hs[:4]:
        lvl, text, omit = c.resp[h]; s, notes = st[h]
        out.append(f"{ICON[s]} {h}  [{LABEL[s]}]  ({len(text.split())} words)")
        if not text.strip() and not c.has_children(h): out.append("  Needs: text. Write it in response/ or run the section drafter.")
        tags, brk = marks(text)
        for n in re.findall(r"\[(?:EVIDENCE NEEDED|DECISION|OPEN|SOLUTIONING)[^\]]*\]", text): out.append(f"  Open note: {n[:160]}")
        if brk: out.append(f"  {brk} bracketed placeholder(s) to fill")
        for i in sorted(cited_ids(text)):
            r = c.reg.get(i) if c.reg else None
            if r is None: out.append(f"  Evidence {i}: not in the register")
            elif (r.get("clearance") or "").strip() != "cleared": out.append(f"  Evidence {i}: {r['clearance']} - {r.get('notes','')[:100]}")
        if c.baseline.get(h, "").strip() != text.strip() and text.strip(): out.append("  Changed since the last integration: run /rfps:integrate")
        if len(out) and out[-1].startswith(f"{ICON[s]}"): out.append("  Nothing open here.")
        out.append("")
    return "\n".join(out).rstrip()

def cmd_set(c, sid, val):
    f = c.sol / "progress.md"
    if not f.is_file(): sys.exit("progress.md does not exist yet; run the status first")
    ids = [s["id"] for s in load_flow()]
    if sid not in ids: sys.exit(f"unknown step '{sid}'. Steps: {', '.join(ids)}")
    mark = {"done": "x", "skip": "-", "reset": " "}[val]; lines = f.read_text().split("\n"); hit = False
    for i, l in enumerate(lines):
        if re.match(r"^- \[[ x\-]\] \S+ `%s`" % sid, l): lines[i] = re.sub(r"^- \[[ x\-]\]", f"- [{mark}]", l, count=1); hit = True
    f.write_text("\n".join(lines)); return f"{sid}: {val}" if hit else f"{sid} not found in progress.md"

def cmd_changed(c):
    out = []
    for h in c.texted():
        new = c.resp[h][1].strip(); old = c.baseline.get(h, "").strip()
        if new and new != old:
            d = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "last integrated", "now", lineterm="", n=1))
            out.append(f"## {h}\n" + ("(new text, nothing integrated before)\n" if not old else "") + "\n".join(d[:80]) + ("\n..." if len(d) > 80 else ""))
    return "\n\n".join(out) or "No section has changed since the last integration."

def cmd_validated(c, name):
    if name not in vd.NAMES: sys.exit(f"--validated takes one of: {', '.join(vd.NAMES)}")
    return f"Recorded {vd.record(c.sol, c.cfg, name)} response file(s) as checked by {name}; it is stale only for sections that change after this."

def cmd_baseline(c, text):
    c.state_dir.mkdir(exist_ok=True); n = 0
    for h in c.order:
        if text and text.lower() not in h.lower(): continue
        c.baseline[h] = c.resp[h][1]; n += 1
    (c.state_dir / "integrated.json").write_text(json.dumps(c.baseline, indent=1))
    return f"Recorded {n} heading(s) as integrated."

def cmd_unbaseline(c, text):
    c.state_dir.mkdir(exist_ok=True); n = 0
    for h in list(c.baseline):
        if not text or text.lower() in h.lower(): del c.baseline[h]; n += 1
    (c.state_dir / "integrated.json").write_text(json.dumps(c.baseline, indent=1))
    return f"Reset {n} heading(s); /rfps:integrate will review them."

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default=None)
    ap.add_argument("--sections", action="store_true"); ap.add_argument("--detail"); ap.add_argument("--set", nargs=2, metavar=("ID", "VALUE"))
    ap.add_argument("--changed", action="store_true"); ap.add_argument("--baseline", nargs="?", const="", default=None); ap.add_argument("--unbaseline", nargs="?", const="", default=None)
    ap.add_argument("--validated", metavar="NAME", help="record the current response text as just checked by compliance, empathy or evalsim")
    ap.add_argument("--table", action="store_true"); ap.add_argument("--json", action="store_true"); ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    c = Ctx(br.resolve_solution(a.solution or None))
    if a.set: print(cmd_set(c, a.set[0], a.set[1])); return
    if a.validated: print(cmd_validated(c, a.validated)); return
    if a.baseline is not None: print(cmd_baseline(c, a.baseline)); return
    if a.unbaseline is not None: print(cmd_unbaseline(c, a.unbaseline)); return
    if a.changed: print(cmd_changed(c)); return
    steps = compute(c)
    if not a.no_write: write_progress(c, steps)
    if a.json:
        st = heading_states(c)
        print(json.dumps({"steps": [{k: s[k] for k in ("id", "group", "title", "state", "detail", "command", "help", "ask") if k in s} for s in steps],
                          "sections": [{"heading": h, "level": c.resp[h][0], "state": st[h][0], "notes": st[h][1], "words": len(c.resp[h][1].split())} for h in c.order]}, indent=1)); return
    if a.table: print(cmd_table(c, steps)); return
    if a.sections: print(cmd_sections(c)); return
    if a.detail: print(cmd_detail(c, steps, a.detail)); return
    print(cmd_status(c, steps))

main()
