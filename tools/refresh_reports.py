# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "openpyxl"]
# ///
"""Refresh the derived parts of coverage-matrix.md, compliance-report.md and resource-plan.md.

The two reports are living markdown documents. Their requirement and check tables are the source: the
requirements-mapper and compliance-validator skills (or a person) edit the rows in place, by stable ID.
This tool recomputes only the blocks wrapped in <!-- derived:NAME --> ... <!-- /derived:NAME --> markers
(counts, pre-flight status, blocking list, page estimates, automated checks). Everything outside the
markers is left exactly as written. It is idempotent.

Usage: rfps-refresh-reports [--solution <active-solution folder>]
Optional in solution.toml: page_limit = 30 (pages allowed for the narrative response).
"""
import argparse, collections, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import resources as rs
import staffing as sf

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
    lo, hi = tw / 550, tw / 450
    if lim: pl = "Within limits" if hi <= lim * 0.9 else ("At risk" if hi <= lim else "Exceeds limits")
    else: pl = "No page limit configured (set page_limit in solution.toml)"
    summ = [f"**Total Requirements Checked:** {N} (plus {len(nrows)} narrative requirements below)",
            f"**Pass:** {st['Pass']} | **Fail:** {st['Fail']} | **Partial:** {st['Partial']} | **Ambiguous:** {st['Ambiguous']} | **N/A:** {st['N/A']}", "",
            f"**Mandatory Requirements:** {mpass} / {len(mand)} passing", f"**Page Limit Compliance:** {pl}", "",
            "**Internal markers still in the text:** " + ", ".join(f"{tags[k]} [{k}]" for k in TAGS[:5]) + f" (and about {brackets} other bracketed values). Grounded notes: {tags['GROUNDED']}."]
    t = replace_block(t, "summary", "\n".join(summ), f.name)
    pc = ["| Response section | Estimated Pages | RFP Limit | Status | Notes |", "|------------------|----------------|-----------|--------|-------|"]
    for name, w in pages: pc.append(f"| {name} | {w/550:.1f} to {w/450:.1f} ({w:,} words) | None per section | Within | |")
    pc.append(f"| **Total** | {lo:.1f} to {hi:.1f} ({tw:,} words) | {lim if lim else 'Not set'} | {pl} | Words after removing internal tags; 450 to 550 words per page; tables and graphics add pages and graphics inside the response count. |")
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
    else: auto.append("| Evidence register | Info | no register configured |")
    t = replace_block(t, "autochecks", "\n".join(auto), f.name)
    f.write_text(t)
    return f"compliance-report.md: {N} checks ({st['Pass']} pass, {st['Fail']} fail, {st['Partial']} partial, {st['Ambiguous']} ambiguous, {st['N/A']} n/a); {status}; {len(blocking)} blocking" + (("; WARN " + "; ".join(warn)) if warn else "")

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
    t = replace_block(t, "summary", "\n".join(out), f.name); f.write_text(t)
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
    print(refresh_coverage(sol)); print(refresh_compliance(sol, cfg)); print(refresh_resources(sol, cfg))
    import open_items; n, _ = open_items.write(sol, cfg); print(f"open-items.md: {n} markers listed")

if __name__ == "__main__":
    main()
