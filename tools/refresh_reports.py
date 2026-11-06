# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl", "pypdf", "python-pptx"]
# ///
"""Refresh the derived parts of coverage-matrix.md, compliance-report.md and resource-plan.md.

The two reports are living markdown documents. Their requirement and check tables are the source: the
requirements-mapper and compliance-validator skills (or a person) edit the rows in place, by stable ID.
This tool recomputes only the blocks wrapped in <!-- derived:NAME --> ... <!-- /derived:NAME --> markers
(counts, pre-flight status, blocking list, page estimates, automated checks). Everything outside the
markers is left exactly as written. It is idempotent.

Usage: rfps-refresh-reports [--solution <03 Solution/active-solution folder>]
Optional in solution.toml: page_limit = 30 (pages allowed for the narrative response).
"""
import argparse, collections, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import resources as rs
import staffing as sf
import solicit_text as st
import strategy as sg
import validated as vd
import evidence_checks as ec
import consistency as cn
import pricing as pr
import lint as lt
import crossref as cr

TAGS = ["ASSERTION", "EVIDENCE NEEDED", "DECISION", "OPEN", "SOLUTIONING", "GROUNDED"]

def cells(line): return [c.strip() for c in line.strip().strip("|").split("|")]

def strip_derived(text): return re.sub(r"<!-- derived:(\w+) -->.*?<!-- /derived:\1 -->", "", text, flags=re.S)

def rows_of(text, idre, ncols, warn):
    out = {}
    text = strip_derived(text)
    for line in text.split("\n"):
        m = re.match(r"^\| (%s) \|" % idre, line)
        if not m: continue
        c = cells(line)
        if len(c) != ncols: warn.append(f"{m.group(1)}: expected {ncols} columns, found {len(c)} (a '|' inside a cell?)"); continue
        out[m.group(1)] = c
    return out

def replace_block(text, name, new, fname):
    pat = re.compile(r"(<!-- derived:%s -->\n).*?(<!-- /derived:%s -->)" % (name, name), re.S)
    if not pat.search(text): sys.exit(f"{fname}: missing <!-- derived:{name} --> block (add the markers or re-scaffold)")
    return pat.sub(lambda m: m.group(1) + new.rstrip("\n") + "\n" + m.group(2), text, count=1)

def rng(words):
    """Page range at 450 to 550 words per page; one number when both ends round to the same value."""
    lo, hi = words / 550, words / 450
    return f"{lo:.1f}" if f"{lo:.1f}" == f"{hi:.1f}" else f"{lo:.1f} to {hi:.1f}"

def response_facts(sol, cfg):
    resp, order = br.parse_response(sol / cfg.get("response_dir", "response"))
    groups, cur = collections.OrderedDict(), None
    for line_h in order:
        lvl, body, omit = resp[line_h]
        if lvl <= 2: cur = line_h; groups.setdefault(cur, "")
        if cur is not None and not omit: groups[cur] += "\n" + body
    tagre = re.compile(r"\[(?:%s)[^\]]*\]" % "|".join(TAGS[:5]), re.S)
    pages = []
    for name, t in groups.items():
        w = len(re.findall(r"\S+", re.sub(r"\[[^\]]*\]", "", tagre.sub("", t))))
        if w: pages.append((name, w))
    alltxt = "\n".join(v[1] for v in resp.values() if not v[2])
    tags = {k: len(re.findall(r"\[" + k, alltxt)) for k in TAGS}
    brackets = len(re.findall(r"\[[^\]\n]{2,}\]", tagre.sub("", re.sub(r"\[GROUNDED[^\]]*\]", "", alltxt))))
    return resp, order, pages, tags, brackets

def refresh_coverage(sol):
    f = sol / "coverage-matrix.md"; t = f.read_text(); warn = []
    rows = rows_of(t, r"R-\d{3}", 9, warn)
    n = len(rows)
    impl = sum(1 for c in rows.values() if "(implicit)" in c[1]); cls = collections.Counter(c[5] for c in rows.values())
    sev = collections.Counter(c[6] for c in rows.values() if c[5] == "Gap")
    pct = lambda k: f"{round(100 * cls[k] / n)}%" if n else "0%"
    summ = [f"**Total Requirements Identified:** {n}", f"**Explicit (shall/must/should as written):** {n - impl} | **Implicit (inferred):** {impl}", "",
            "**Coverage Breakdown:**"] + [f"- {k}: {cls[k]} ({pct(k)})" for k in ("Grounded", "Assertable", "Gap")] + \
           ["", "**Gap Severity (Gap rows only):**"] + [f"- {k}: {sev[k]}" for k in ("Disqualifying", "Manageable", "Addressable")]
    t = replace_block(t, "summary", "\n".join(summ), f.name)
    old = {}
    m = re.search(r"<!-- derived:disqualifying -->\n(.*?)<!-- /derived:disqualifying -->", t, re.S)
    for line in (m.group(1).split("\n") if m else []):
        mm = re.match(r"^\| (R-\d{3}) \|", line)
        if mm and len(cells(line)) == 4: old[mm.group(1)] = cells(line)
    dq = ["| # | Requirement | Why Disqualifying | Possible Resolution |", "|---|-------------|-------------------|---------------------|"]
    for rid, c in rows.items():
        if c[5] == "Gap" and c[6] == "Disqualifying":
            prev = old.get(rid)
            why = prev[2] if prev else "Mandatory and classified Gap; cannot credibly assert"
            res = prev[3] if prev else ""
            dq.append(f"| {rid} | {c[1][:110]} | {why} | {res} |")
    if len(dq) == 2: dq.append("| | None | | |")
    t = replace_block(t, "disqualifying", "\n".join(dq), f.name)
    f.write_text(t)
    return f"coverage-matrix.md: {n} requirements, {cls['Grounded']} Grounded / {cls['Assertable']} Assertable / {cls['Gap']} Gap ({sev['Disqualifying']} disqualifying)" + (("; WARN " + "; ".join(warn)) if warn else "")

def refresh_compliance(sol, cfg):
    f = sol / "compliance-report.md"; t = f.read_text(); warn = []
    rows = rows_of(t, r"[FCSP]-\d{3}", 7, warn); nrows = rows_of(t, r"N-\d{3}", 7, warn)
    N = len(rows); st = collections.Counter(c[4] for c in rows.values())
    mand = {k: c for k, c in rows.items() if c[3] == "Yes"}
    blocking = {k: c for k, c in mand.items() if c[4] == "Fail"}
    warns = [k for k, c in rows.items() if c[4] in ("Partial", "Ambiguous")]
    mpass = sum(1 for c in mand.values() if c[4] == "Pass")
    status = "NOT STARTED (no checks recorded yet)" if N == 0 else ("BLOCKING ISSUES EXIST" if blocking else ("REVIEW REQUIRED" if warns else "READY FOR ASSEMBLY"))
    pre = [f"**Status: {status}**", "", f"**Blocking Issues:** {len(blocking)} (mandatory requirements not met)", f"**Warnings:** {len(warns)} (partial or ambiguous)", "",
           "### Blocking Issues", "", "| # | Requirement | RFP Reference | Why Blocking | Required Action |", "|---|-------------|---------------|--------------|-----------------|"]
    for k, c in blocking.items(): pre.append(f"| {k} | {c[1]} | {c[2]} | Mandatory and not met: {c[5]} | {c[6]} |")
    if not blocking: pre.append("| | None | | | |")
    t = replace_block(t, "preflight", "\n".join(pre), f.name)
    resp, order, pages, tags, brackets = response_facts(sol, cfg)
    tw = sum(w for _, w in pages); lim = cfg.get("page_limit")
    hi = tw / 450
    if lim: pl = "Within limits" if hi <= lim * 0.9 else ("At risk" if hi <= lim else "Exceeds limits")
    else: pl = "No page limit configured (set page_limit in solution.toml)"
    summ = [f"**Total Requirements Checked:** {N} (plus {len(nrows)} narrative requirements below)",
            f"**Pass:** {st['Pass']} | **Fail:** {st['Fail']} | **Partial:** {st['Partial']} | **Ambiguous:** {st['Ambiguous']} | **N/A:** {st['N/A']}", "",
            f"**Mandatory Requirements:** {mpass} / {len(mand)} passing", f"**Page Limit Compliance:** {pl}", "",
            "**Internal markers still in the text:** " + ", ".join(f"{tags[k]} [{k}]" for k in TAGS[:5]) + f" (and about {brackets} other bracketed values). Grounded notes: {tags['GROUNDED']}."]
    t = replace_block(t, "summary", "\n".join(summ), f.name)
    pc = ["| Response section | Estimated Pages | RFP Limit | Status | Notes |", "|------------------|----------------|-----------|--------|-------|"]
    for name, w in pages: pc.append(f"| {name} | {rng(w)} ({w:,} words) | None per section | Within | |")
    pc.append(f"| **Total** | {rng(tw)} ({tw:,} words) | {lim if lim else 'Not set'} | {pl} | Words after removing internal tags; 450 to 550 words per page; tables and graphics add pages and graphics inside the response count. |")
    t = replace_block(t, "pagecount", "\n".join(pc), f.name)
    # automated checks
    auto = []
    cfgd = br.load_engagement(str(sol)); tpl = cfgd["template"]
    import docx as _d
    hp = cfgd["tcfg"].get("heading_prefix", "Heading")
    tpl_heads = [p.text.strip() for p in _d.Document(tpl).paragraphs if p.style.name.startswith(hp) and p.text.strip()]
    miss = [h for h in tpl_heads if h not in resp]; extra = [h for h in resp if h not in tpl_heads]
    auto.append("| Check | Result | Detail |\n|-------|--------|--------|")
    auto.append(f"| Response headings match the template docx | {'Pass' if not (miss or extra) else 'Fail'} | {len(tpl_heads)} template headings; missing from response: {', '.join(miss) or 'none'}; not in template: {', '.join(extra) or 'none'} |")
    empty = [h for h, v in resp.items() if not v[1].strip() and not v[2] and not any(order[i + 1:i + 2] and resp[order[i + 1]][0] > v[0] for i in [order.index(h)])]
    auto.append(f"| Headings with no text (and no sub-headings) | {'Pass' if not empty else 'Open'} | {len(empty)}: {', '.join(empty[:12]) or 'none'}{' ...' if len(empty) > 12 else ''} |")
    auto.append(f"| Unresolved internal markers | {'Pass' if not sum(tags[k] for k in TAGS[:5]) else 'Open'} | " + ", ".join(f"{tags[k]} {k}" for k in TAGS[:5]) + f"; about {brackets} other bracketed values |")
    reg = br.load_register(cfgd["register"]) if cfgd.get("register") and pathlib.Path(cfgd["register"]).is_file() else None
    if reg is not None:
        ev = br.check_evidence(resp, reg, br.deny_from_register(reg))
        notc = [i for i in ev["cited"] if (reg.get(i, {}).get("clearance") or "").strip() != "cleared"]
        auto.append(f"| Evidence cited is cleared | {'Pass' if not (notc or ev['issues']) else 'Open'} | {len(ev['cited'])} IDs cited; not cleared or problem: {', '.join(sorted(notc)) or 'none'} |")
        auto.append(f"| Grounded notes cite a register ID | {'Pass' if not ev['uncited'] else 'Fail'} | uncited: {len(ev['uncited'])} |")
        auto.append(f"| Banned phrases absent | {'Pass' if not ev['deny'] else 'Fail'} | hits: {', '.join(sorted({ph for _, ph, _ in ev['deny']})) or 'none'} |")
        auto.append(f"| Register rows not cited anywhere | Info | {', '.join(ev['unused']) or 'none'} |")
        auto += ec.pp_checks(cfg, reg, set(ev["cited"]))
        if br.STRICT["ref"]:
            noref = sorted(i for i in ev["cited"] if (reg.get(i, {}).get("clearance") or "").strip() == "cleared" and not (reg.get(i, {}).get("approval_ref") or "").strip())
            auto.append(f"| Cleared evidence records its approval proof | {'Pass' if not noref else 'Fail'} | require_approval_ref is on; cited rows with no approval_ref: {', '.join(noref) or 'none'} |")
    else: auto.append("| Evidence register | Info | no register configured |")
    try: auto += solicitation_checks(sol, cfg, rows, nrows)
    except Exception as e: auto.append(f"| Solicitation sweep and quote check | Info | not run: {e} |")
    thin = tw < 150   # too little text for the writing, cross-reference, figure and theme checks to say anything useful
    if thin: auto.append(f"| Writing, cross-reference, figures and theme checks | Info | they start once the response has about 150 words (now {tw}) |")
    if not thin:
        try: auto += lt.checks(sol, cfg, group_texts(resp, order))
        except Exception as e: auto.append(f"| Writing lint | Info | not run: {e} |")
        try: auto += cr.checks(sol, cfg)
        except Exception as e: auto.append(f"| Requirement cross-reference | Info | not run: {e} |")
        try: auto += cn.checks(sol, cfg)
        except Exception as e: auto.append(f"| Numbers agree | Info | not run: {e} |")
    try: auto += currency_checks(sol, cfg)
    except Exception as e: auto.append(f"| Reviews current and submission steps | Info | not run: {e} |")
    try: auto += [] if thin else strategy_checks(sol, resp, order, pages, cfg.get("page_limit"))
    except Exception as e: auto.append(f"| Win themes and page budget | Info | not run: {e} |")
    hdr, body = auto[:1], auto[1:]   # worst first: failures, then open items, then passes and information
    cell = lambda r: ([x.strip() for x in r.strip().strip("|").split("|")] + ["", ""])[1]
    body.sort(key=lambda r: {"Fail": 0, "Open": 1, "Pass": 2}.get(cell(r), 3))
    cnt = collections.Counter(cell(r) for r in body)
    auto = [f"**{cnt['Fail']} fail, {cnt['Open']} open, {cnt['Pass']} pass, {cnt['Info']} for information.** The ones that need you are first.", ""] + hdr + body
    t = replace_block(t, "autochecks", "\n".join(auto), f.name)
    f.write_text(t)
    return f"compliance-report.md: {N} checks ({st['Pass']} pass, {st['Fail']} fail, {st['Partial']} partial, {st['Ambiguous']} ambiguous, {st['N/A']} n/a); {status}; {len(blocking)} blocking" + (("; WARN " + "; ".join(warn)) if warn else "")

def solicitation_checks(sol, cfg, comp_rows, narr_rows):
    """Table rows for the compliance report's automated checks: every obligation sentence in the solicitation has a requirement row,
    and quoted RFP language is found verbatim in the solicitation text. Info when the solicitation text is not available."""
    docs, note = st.load_text(sol, cfg)
    if not docs: return [f"| Solicitation obligations all mapped | Info | not checked: {note} |", f"| Quoted RFP language found in the solicitation | Info | not checked: {note} |"]
    f = sol / "coverage-matrix.md"
    cov = {k: c[1] for k, c in rows_of(f.read_text(), r"R-\d{3}", 9, []).items()} if f.is_file() else {}
    chk = {k: c[1] for k, c in list(comp_rows.items()) + list(narr_rows.items())}
    docs_s = st.scope_docs(docs, cfg)
    res = st.sweep(docs_s, {**cov, **chk}, st.scope(cfg))
    un = [r for r in res if not r["mapped"]]; um = [r for r in un if r["cls"] == "mandatory"]
    show = "; ".join(f"{r['where'] or r['file']}: {r['text'][:70].replace('|', '/')}" for r in um[:5]) + (" ..." if len(um) > 5 else "")
    out = [f"| Solicitation obligations all mapped | {'Pass' if not un else ('Open' if um else 'Info')} | {len(res)} obligation sentence(s) in {len(docs_s)} file(s){' (respondent asks only)' if st.scope(cfg) == 'respondent' else ''}; {len(un)} with no requirement row ({len(um)} mandatory){': ' + show if um else ''}. Run rfps-sweep for the list. |"]
    badc = st.unverified_quotes(cov, docs); badk = st.unverified_quotes(chk, docs, quoted_only=True)
    out.append(f"| Quoted RFP language found in the solicitation | {'Pass' if not (badc or badk) else 'Open'} | {len(cov)} matrix row(s), {len(chk)} check row(s); not found verbatim: {', '.join(badc + badk) or 'none'}. Source: {note}. |")
    return out

def currency_checks(sol, cfg):
    """Automated checks: each review still matches the response text it looked at, and the submission checklist has nothing overdue or due within three days."""
    out = []
    for name, label in (("compliance", "Compliance check"), ("empathy", "Tone review"), ("evalsim", "Second-reader run")):
        ch = vd.stale(sol, cfg, name)
        out.append(f"| {label} matches the current text | {'Info' if ch is None else ('Pass' if not ch else 'Open')} | " + ("never recorded (run rfps-flow-status --validated " + name + " after it)" if ch is None else ("no section changed since" if not ch else f"changed since: {', '.join(ch)}")) + " |")
    bad = sg.malformed(sol)
    out.append(f"| Living tables are well formed | {'Pass' if not bad else 'Open'} | " + ("no row has a missing cell or a stray '|'" if not bad else f"{len(bad)} row(s) the tools skip until fixed: " + "; ".join(bad[:4]) + (" ..." if len(bad) > 4 else "")) + " |")
    qs = sg.questions(sol)
    if qs:
        import datetime
        today = datetime.date.today(); unsent, unlogged = [], []
        for q in qs:
            s = sg.status_word(q["status"])
            if s == "draft": unsent.append(q["id"])
            if s == "answered" and q["logged"].strip() in ("", "-"): unlogged.append(q["id"])
        late = []
        for q in qs:
            if sg.status_word(q["status"]) == "draft":
                try:
                    if (datetime.date.fromisoformat(q["due"][:10]) - today).days <= 3: late.append(q["id"])
                except ValueError: pass
        out.append(f"| Questions to the agency | {'Open' if late or unlogged else ('Info' if unsent else 'Pass')} | {len(qs)} question(s); {len(unsent)} still a draft" + (f"; due within 3 days or overdue and not sent: {', '.join(late)}" if late else "") + (f"; answered but not logged in amendments/log.md: {', '.join(unlogged)}" if unlogged else "") + " |")
    sub_rows = sg.submission(sol)
    if sub_rows:
        import datetime
        today = datetime.date.today(); late, soon, open_ = [], [], 0
        for r in sub_rows:
            if sg.is_done(r["status"]): continue
            open_ += 1
            try: d = datetime.date.fromisoformat(r["due"][:10])
            except ValueError: continue
            (late if d < today else soon if (d - today).days <= 3 else []).append(f"{r['id']} {r['item'][:40]} ({r['due'][:10]})")
        out.append(f"| Submission checklist | {'Open' if late or soon else ('Info' if open_ else 'Pass')} | {len(sub_rows)} item(s), {open_} not done" + (f"; overdue: {'; '.join(late)}" if late else "") + (f"; due within 3 days: {'; '.join(soon)}" if soon else "") + " |")
    return out

def group_texts(resp, order):
    """{top-level heading (level 1 or 2): its text including sub-headings, omitted sections left out}."""
    groups, cur = collections.OrderedDict(), None
    for h in order:
        lvl, body, omit = resp[h]
        if lvl <= 2: cur = h; groups.setdefault(cur, "")
        if cur is not None and not omit: groups[cur] += "\n" + body
    return groups

def strategy_checks(sol, resp, order, pages, limit):
    """Automated checks from win-strategy.md: each win theme's key phrase is in the executive summary and at least one other section,
    and each weighted evaluation factor's section is near its share of the page limit. Also fills the theme table in win-strategy.md."""
    s = sg.strategy(sol); th = s["themes"]; groups = group_texts(resp, order); out = []
    if not th:
        out.append("| Win themes carried through the response | Info | no themes recorded in win-strategy.md |")
    else:
        bad, table = [], ["| Theme | Key phrase | Found in |", "|-------|------------|----------|"]
        for t in th:
            ph = sg.norm(t["phrase"]); hits = [h for h, txt in groups.items() if ph and ph in sg.norm(txt)]
            table.append(f"| {t['id']} {t['theme'].replace('|', '/')} | {t['phrase'].replace('|', '/') or '(none)'} | {', '.join(hits) or 'nowhere yet'} |")
            if not ph: bad.append(f"{t['id']} has no key phrase")
            elif not any("summary" in h.lower() for h in hits): bad.append(f"{t['id']} is not in the executive summary")
            elif len(hits) < 2: bad.append(f"{t['id']} appears only in the executive summary")
        out.append(f"| Win themes carried through the response | {'Pass' if not bad else 'Open'} | {len(th)} theme(s); {'; '.join(bad) or 'each is in the executive summary and at least one other section'} |")
        f = sol / "win-strategy.md"
        if f.is_file() and "<!-- derived:themecheck -->" in f.read_text():
            f.write_text(replace_block(f.read_text(), "themecheck", "\n".join(table), f.name))
    fac = [x for x in s["factors"] if x["weight"] is not None and x["heading"]]
    if fac and limit:
        tot = sum(x["weight"] for x in fac); words = dict(pages); parts, flags = [], []
        for x in fac:
            key = next((n for n in words if sg.norm(n) == sg.norm(x["heading"])), None)
            bud = limit * x["weight"] / tot
            if key is None: parts.append(f"{x['heading']}: no text (budget {bud:.1f})"); flags.append(x["heading"]); continue
            est = words[key] / 500; parts.append(f"{x['heading']}: {est:.1f} of {bud:.1f}")
            if est > bud * 1.25 or est < bud * 0.5: flags.append(x["heading"])
        out.append(f"| Page budget by evaluation factor | {'Pass' if not flags else 'Open'} | pages written of budget (weights share the {limit} page limit; 500 words a page): " + "; ".join(parts) + (f". Far from budget: {', '.join(flags)}" if flags else "") + " |")
    elif fac: out.append("| Page budget by evaluation factor | Info | set page_limit in solution.toml to see the budget |")
    if fac:
        ex = sg.exhibits(sol); have = {sg.norm(x["section"]) for x in ex}
        none = [x["heading"] for x in fac if sg.norm(x["heading"]) not in have and x["weight"] >= 15]
        undone = [x["id"] for x in ex if x["status"].lower() not in ("done", "n/a")]
        out.append(f"| Exhibits planned for the heavily weighted factors | {'Pass' if not none else 'Open'} | {len(ex)} exhibit(s) planned, {len(undone)} not done" + (f"; no exhibit planned for: {', '.join(none)}" if none else "") + " |")
    return out

def refresh_evalsim(sol, cfg):
    """Fill the derived summary of evaluation-sim.md: weighted score on the scale, the weakest factors, and whether the response changed since the run."""
    f = sol / "evaluation-sim.md"
    if not f.is_file(): return "evaluation-sim.md: not present"
    t = f.read_text()
    if "<!-- derived:evalsummary -->" not in t: return "evaluation-sim.md: no derived block (add the markers or re-scaffold)"
    e = sg.evalsim(sol); rated = [(r, sg.rating_points(r["rating"], e["scale"])) for r in e["rows"]]
    ok = [(r, p) for r, p in rated if p is not None]; off = [r["id"] for r, p in rated if p is None]
    if not rated: summ = ["No factors rated yet. Run /rfps:evaluator-simulator."]
    else:
        wt = sum((r["weight"] or 1) for r, _ in ok); score = sum((r["weight"] or 1) * p for r, p in ok) / wt if wt else 0
        worst = sorted(ok, key=lambda x: x[1])[:3]
        ch = vd.stale(sol, cfg, "evalsim")
        summ = [f"**Weighted score:** {score * 100:.0f} of 100 across {len(ok)} rated factor(s) (best rating = 100, worst = 0 on the scale above). A second reader's view, not the agency's.",
                "**Weakest factors:** " + (", ".join(f"{r['factor']} ({r['rating']})" for r, _ in worst) or "none"),
                f"**Ratings not on the scale:** {', '.join(off) or 'none'}",
                "**Response changed since this run:** " + ("unknown: record the run with rfps-flow-status --validated evalsim right after it" if ch is None else ("no" if not ch else f"yes, re-run the simulator ({', '.join(ch)})"))]
    f.write_text(replace_block(t, "evalsummary", "\n".join(summ), f.name))
    return f"evaluation-sim.md: {len(rated)} factor(s) rated"

def refresh_resources(sol, cfg):
    f = sol / "resource-plan.md"
    if not f.is_file(): return "resource-plan.md: not present (copy the resource-planner skill's assets/resource-plan-template.md to start one)"
    t = f.read_text(); warn = []
    rpath = rs.roster_path(sol, cfg)
    allrows = rs.load(rpath)
    if allrows is None: return f"resource-plan.md: roster {rpath.name} not found (run /rfps:resources to create it)"
    rows = rs.active(allrows)
    dropped = len(allrows) - len(rows)
    st = rs.stats(allrows)
    reqs = rs.requirements(t); dels = rs.deliverables(t)
    kp = [r for r in rows if r["status"] == "KP"]
    ls = lambda ids: ", ".join(ids) or "none"
    badstat = [r["id"] for r in allrows if r["status"] not in rs.STATUSES]
    nosrc = [r["id"] for r in rows if r["status"] in ("KP", "Recommended") and not r["source"]]
    noreason = [r["id"] for r in rows if r["status"] == "Ours" and not r["notes"]]
    noloe = [r["id"] for r in rows if not r["loe_pct"] or not r["phases"]]
    kp_flag = [r["id"] for r in kp if r["in_response"].lower() != "yes"]
    below = []
    for r in kp:
        q = reqs.get(r["requirement_ref"])
        if q and rs.num(q[4]) and rs.num(r["loe_pct"]) < rs.num(q[4]): below.append(f"{r['id']} ({r['loe_pct']} < {q[4]})")
    tbd = [r["id"] for r in kp if r["person"].upper() in ("", "TBD")]
    kp_resume = [r["id"] for r in kp if r["resume"] != "Checked"]
    resp, order, pages, tags, brackets = response_facts(sol, cfg)
    alltxt = "\n".join(v[1] for v in resp.values() if not v[2])
    low = alltxt.lower()
    flagged = [r for r in rows if r["in_response"].lower() == "yes"]
    nonarr = [r["id"] for r in flagged if not re.search(r"\*\*[^*\n]*" + re.escape(r["role"].lower()) + r"[^*\n]*\*\*", low)]
    others = [r["id"] for r in rows if r["in_response"].lower() != "yes" and r["role"].lower() not in low]
    owned = {d.strip().lower() for r in rows for d in r["deliverables"].split(";") if d.strip()}
    nodel = [k for k, c in dels.items() if c[1].strip().lower() not in owned]
    phase_fte = ", ".join(f"Phase {p}: {rs.fmt_fte(st['by_phase'][p])}" for p in rs.PHASES)
    wb, wb_ok = ("not set (solution.toml staffing_xlsx)", False) if not cfg.get("staffing_xlsx") else sf.status(sol, cfg, allrows)
    out = [f"**People:** {rs.fmt_people(st['people'])} ({rs.fmt_people(st['kp_people'])} KP, {rs.fmt_people(st['other_people'])} other) | **Total FTE:** {rs.fmt_fte(st['fte'])} ({phase_fte}) | **Roles:** {st['roles']} | **Dropped:** {dropped}", "",
           "| Check | Result | Detail |", "|-------|--------|--------|",
           f"| Roles defined | {'Pass' if rows else 'Open'} | {len(rows)} active role(s) |",
           f"| Status is KP, Recommended, Ours or Dropped | {'Pass' if not badstat else 'Fail'} | {ls(badstat)} |",
           f"| KP and Recommended roles cite a source | {'Pass' if not nosrc else 'Open'} | missing: {ls(nosrc)} |",
           f"| Roles we added say why | {'Pass' if not noreason else 'Open'} | missing: {ls(noreason)} |",
           f"| Level of effort and phases filled in | {'Pass' if not noloe else 'Open'} | missing: {ls(noloe)} |",
           f"| Key Personnel are written up in the response | {'Pass' if not kp_flag else 'Open'} | in_response not yes: {ls(kp_flag)} |",
           f"| Key Personnel effort meets the State minimum | {'Pass' if not below else 'Fail'} | below minimum: {ls(below)} |",
           f"| Key Personnel named | {'Pass' if kp and not tbd else 'Open'} | still TBD: {ls(tbd)} |",
           f"| Key Personnel resumes checked | {'Pass' if kp and not kp_resume else 'Open'} | not yet Checked: {ls(kp_resume)} |",
           f"| Selected roles have a narrative in the response | {'Pass' if not nonarr else 'Open'} | no bold lead-in with the role name: {ls(nonarr)} |",
           f"| Other roles are named in the response | {'Pass' if not others else 'Open'} | not found: {ls(others)} |",
           f"| Every deliverable has an owner role | {'Pass' if dels and not nodel else ('Open' if dels else 'Info')} | " + (f"no owner: {ls(nodel)}" if dels else "no deliverables listed in the plan") + " |",
           f"| Staffing workbook | {'Pass' if wb_ok else 'Open'} | {wb} |"]
    try: out += pr.rate_checks(sol, cfg)
    except Exception as e: out.append(f"| Rate sheet | Info | not checked: {e} |")
    t = replace_block(t, "summary", "\n".join(out), f.name)
    if "<!-- derived:priceview -->" in t:
        try: t = replace_block(t, "priceview", "\n".join(pr.price_view(sol, cfg, t)), f.name)
        except Exception as e: t = replace_block(t, "priceview", f"Price view not built: {e}", f.name)
    f.write_text(t)
    # keep the team-size sentence in the response in step with the roster
    note = ""
    for mdf in sorted((sol / cfg.get("response_dir", "response")).glob("*.md")):
        txt = mdf.read_text()
        if "<!-- derived:team-size -->" in txt:
            mdf.write_text(replace_block(txt, "team-size", rs.team_size_sentence(st), mdf.name)); note = f"; team-size sentence updated in {mdf.name}"
    return f"resource-plan.md: {st['roles']} roles, {rs.fmt_people(st['people'])} people, {rs.fmt_fte(st['fte'])} FTE ({len(kp)} KP rows); {len(tbd)} KP unnamed" + note + (("; WARN " + "; ".join(warn)) if warn else "")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default="")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    print(refresh_coverage(sol)); print(refresh_compliance(sol, cfg)); print(refresh_resources(sol, cfg)); print(refresh_evalsim(sol, cfg))
    try: n, m = cr.write(sol, cfg); print(f"cross-reference.md: {n} requirement(s), {m} mandatory with no answering section found")
    except Exception as e: print(f"cross-reference.md: not written ({e})")
    import open_items; n, _ = open_items.write(sol, cfg); print(f"open-items.md: {n} markers listed")

if __name__ == "__main__":
    main()
