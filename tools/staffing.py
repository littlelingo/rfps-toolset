# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl", "python-docx"]
# ///
"""Create and keep in step the staffing and pricing workbook (Staffing.xlsx) for a solution.

The workbook is built from one definitive template (tools/templates/staffing-template.xlsx) so every
solution's staffing plan has the same layout. The roster (response/resources.csv) supplies the role,
person, resume status and responsibility, and seeds a new row's allocation % and hours by phase. Labor
category, allocation %, rate and hours belong to the person pricing the work: after a row exists this tool
never overwrites them, and it never deletes a row.

Usage:
  rfps-staffing --template            rebuild tools/templates/staffing-template.xlsx
  rfps-staffing [--solution [path]]   create or update the workbook named by staffing_xlsx in solution.toml
  rfps-staffing --seed-hours          also fill EMPTY allocation and hour cells on existing rows with suggested values
                                                 (allocation from the roster; hours = allocation x phase months x hours per FTE-month);
                                                 cells that already hold a value, including 0, are never changed
"""
import argparse, json, pathlib, shutil, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import resources as rs

TEMPLATE = pathlib.Path(__file__).resolve().parent / "templates" / "staffing-template.xlsx"
FIRST, LAST = 5, 200
HEAD = ["ID", "Role", "Person", "Resume obtained", "Responsibility", "Labor category", "Allocation %", "Rate ($/hr)",
        "Hours Phase 1", "Hours Phase 2", "Hours Phase 3", "Total hours", "Total cost", "Notes"]
WIDTHS = [8, 30, 22, 12, 48, 22, 12, 11, 11, 11, 11, 12, 14, 36]
YELLOW = "FGHIJK"   # labor category, allocation %, rate, hours by phase: owned by the person pricing the work


def build_template(path, title="{title}"):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Staffing"
    bold = Font(bold=True); fill_in = PatternFill("solid", fgColor="FFF2CC"); fill_head = PatternFill("solid", fgColor="D9E1F2")
    ws["A1"] = f"Staffing and pricing - {title}"; ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = ("Yellow cells are yours to fill in or change: labor category, allocation % (the role's total allocation, so two people at 50 percent "
                "is 100 percent), rate, and hours by phase. New rows arrive pre-filled with suggested allocation and hours from the roster. "
                "ID, role, person, resume and responsibility come from the roster (response/resources.csv) and are refreshed by rfps-staffing. Rows are never deleted.")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top"); ws.merge_cells("A2:N2"); ws.row_dimensions[2].height = 58
    for i, h in enumerate(HEAD, 1):
        c = ws.cell(row=4, column=i, value=h); c.font = bold; c.fill = fill_head; c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(WIDTHS, 1): ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for r in range(FIRST, LAST + 1): style_row(ws, r, fill_in)
    ws.freeze_panes = "C5"
    a = wb.create_sheet("Assumptions")
    a["A1"] = "Assumptions for suggested hours and FTE"; a["A1"].font = Font(bold=True, size=12)
    for r, (k, v) in enumerate([("Phase 1 months (estimated)", 2), ("Phase 2 months (estimated)", 3), ("Phase 3 months (estimated)", 6), ("Hours per FTE-month", 160)], 3):
        a.cell(row=r, column=1, value=k); c = a.cell(row=r, column=2, value=v); c.fill = fill_in
    a["A8"] = "Suggested hours = allocation x months in the phase x hours per FTE-month. Phase FTE on the Summary = hours / (months x hours per FTE-month)."
    a.column_dimensions["A"].width = 34
    s = wb.create_sheet("Summary")
    s["A1"] = "Summary"; s["A1"].font = Font(bold=True, size=12)
    for i, h in enumerate(["", "Phase 1", "Phase 2", "Phase 3", "Total"], 1): s.cell(row=3, column=i, value=h).font = bold
    rng = lambda col: f"Staffing!{col}{FIRST}:{col}{LAST}"
    s["A4"] = "Hours"; s["A5"] = "Cost ($)"; s["A6"] = "FTE"
    for col, hc, mrow in zip("BCD", "IJK", (3, 4, 5)):
        s[f"{col}4"] = f"=SUM({rng(hc)})"
        s[f"{col}5"] = f"=SUMPRODUCT({rng(hc)},{rng('H')})"
        s[f"{col}6"] = f"={col}4/(Assumptions!$B${mrow}*Assumptions!$B$6)"
    s["E4"] = "=SUM(B4:D4)"; s["E5"] = "=SUM(B5:D5)"; s["E6"] = f"=SUM({rng('G')})"
    s["A8"] = "People (rows)"; s["B8"] = f"=COUNTA({rng('A')})"
    s["A10"] = "Attachment C total (enter)"; s["B10"].fill = fill_in
    s["A11"] = "Difference from this workbook"; s["B11"] = "=IF(B10=\"\",\"\",E5-B10)"
    s.column_dimensions["A"].width = 32
    for col in "BCDE": s.column_dimensions[col].width = 16
    for r in (4, 5, 10, 11):
        for col in "BCDE": s[f"{col}{r}"].number_format = '#,##0.00' if r != 4 else '#,##0'
    for col in "BCDE": s[f"{col}6"].number_format = '0.00'
    wb.move_sheet("Summary", offset=-1)
    wb.active = wb.sheetnames.index("Staffing")
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def style_row(ws, r, fill_in):
    from openpyxl.styles import Alignment
    for col in YELLOW: ws[f"{col}{r}"].fill = fill_in
    ws[f"E{r}"].alignment = Alignment(wrap_text=True, vertical="top"); ws[f"N{r}"].alignment = Alignment(wrap_text=True, vertical="top")
    ws[f"G{r}"].number_format = '0%'; ws[f"H{r}"].number_format = '#,##0.00'; ws[f"M{r}"].number_format = '#,##0.00'
    for col in "IJKL": ws[f"{col}{r}"].number_format = '#,##0'


SHARED = ("person", "resume", "scope", "alloc")   # synced both ways; role, status and the long text are roster-only
RES_X = {"Received": "Yes", "Checked": "Yes", "Needed": "No", "N/A": "N/A"}
RES_C = {"Yes": "Received", "No": "Needed", "N/A": "N/A"}


def _num(v):
    try: return float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError): return None


def csv_view(row):
    return {"person": (row["person"] or "TBD").strip(), "resume": RES_X.get(row["resume"], "No"), "scope": row["scope"].strip(),
            "alloc": f"{rs.fte_of(row):.4f}"}


def xlsx_rows(ws):
    out = {}
    for r in range(FIRST, LAST + 1):
        rid = ws.cell(row=r, column=1).value; role = ws.cell(row=r, column=2).value
        if not rid and not role: continue
        hours = [_num(ws.cell(row=r, column=9 + i).value) for i in range(3)]
        alloc = _num(ws.cell(row=r, column=7).value)
        res = str(ws.cell(row=r, column=4).value or "No").strip()
        out[r] = {"id": str(rid).strip() if rid else "", "role": str(role or "").strip(), "row": r,
                  "person": str(ws.cell(row=r, column=3).value or "TBD").strip() or "TBD",
                  "resume": res if res in RES_C else "No", "scope": str(ws.cell(row=r, column=5).value or "").strip(),
                  "alloc": None if alloc is None else f"{alloc:.4f}", "hours": hours,
                  "phases": {i + 1 for i, h in enumerate(hours) if h and h > 0}}
    return out


def read_baseline(path):
    try: return json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError): return {}


def plan(roster, wb_rows, baseline, prefer=None):
    """Three-way compare of the roster and the workbook against what they agreed on at the last sync."""
    byid = {r["id"]: r for r in roster}
    xby = {x["id"]: x for x in wb_rows.values() if x["id"]}
    to_x, to_c, conflicts, new_x, new_c, newbase = [], [], [], [], [], {}
    for rid, row in byid.items():
        if row["status"] == "Dropped": continue
        if rid not in xby: new_x.append(rid); continue
        x = xby[rid]; c = csv_view(row); b = baseline.get(rid, {}); nb = {}
        for f in SHARED:
            cv, xv, bv = c[f], x[f], b.get(f)
            if xv is None: nb[f] = cv; to_x.append((rid, f, cv)); continue
            same = (abs(float(cv) - float(xv)) < 1e-6) if f == "alloc" else cv == xv
            if same: nb[f] = cv
            elif bv is not None and (abs(float(xv) - float(bv)) < 1e-6 if f == "alloc" else xv == bv): nb[f] = cv; to_x.append((rid, f, cv))
            elif bv is not None and (abs(float(cv) - float(bv)) < 1e-6 if f == "alloc" else cv == bv): nb[f] = xv; to_c.append((rid, f, xv))
            elif prefer == "csv": nb[f] = cv; to_x.append((rid, f, cv))
            elif prefer == "xlsx": nb[f] = xv; to_c.append((rid, f, xv))
            else: nb[f] = bv if bv is not None else cv; conflicts.append((rid, f, cv, xv))
        if x["phases"]:
            ph = ";".join(str(p) for p in sorted(x["phases"]))
            if ph != ";".join(str(p) for p in sorted(rs.phases_of(row))): to_c.append((rid, "phases", ph))
        newbase[rid] = nb
    # roles typed into the workbook without an ID
    for x in wb_rows.values():
        if not x["id"] and x["role"]: new_c.append(x["row"])
    return {"to_x": to_x, "to_c": to_c, "conflicts": conflicts, "new_x": new_x, "new_c": new_c, "baseline": newbase}


def consistency(ws, roster):
    """Active roles whose total hours differ from allocation x months x hours per FTE-month by more than 10 percent."""
    asm = ws.parent["Assumptions"]; hpm = float(asm["B6"].value); months = [float(asm.cell(row=3 + i, column=2).value) for i in range(3)]
    byid = {r["id"]: r for r in roster}; off = []
    for x in xlsx_rows(ws).values():
        row = byid.get(x["id"])
        if not row or row["status"] == "Dropped" or x["alloc"] is None: continue
        have = sum(h or 0 for h in x["hours"]); ph = x["phases"] or rs.phases_of(row)
        want = float(x["alloc"]) * sum(months[p - 1] for p in ph) * hpm
        if have and want and abs(have - want) / want > 0.10: off.append(f"{x['id']} ({have:.0f} h vs about {want:.0f} h)")
    return off


def status(sol, cfg, roster):
    """Read-only summary for the resource checks: (text, in_step)."""
    import openpyxl
    sx = cfg.get("staffing_xlsx")
    if not sx: return "staffing_xlsx not set in solution.toml", False
    path = (sol / sx).resolve()
    if not path.is_file(): return f"{sx} not created yet (run rfps-staffing)", False
    try: ws = openpyxl.load_workbook(path)["Staffing"]
    except Exception: return f"{sx} could not be read", False
    pl = plan([r for r in roster], xlsx_rows(ws), read_baseline(sol / ".state" / "staffing-sync.json"))
    n = len(pl["to_x"]) + len(pl["to_c"]) + len(pl["new_x"]) + len(pl["new_c"])
    cons = consistency(ws, roster)
    parts = []
    if pl["conflicts"]: parts.append(f"{len(pl['conflicts'])} conflict(s): " + ", ".join(f"{i} {f}" for i, f, _, _ in pl["conflicts"]))
    if n: parts.append(f"{n} pending change(s) to carry over (run rfps-staffing)")
    if cons: parts.append("hours differ from allocation: " + ", ".join(cons))
    return (f"{sx} in step" if not parts else f"{sx}: " + "; ".join(parts)), not parts


def sync(sol, cfg, roster, workbook, seed_hours=False, prefer=None):
    import openpyxl
    from openpyxl.styles import PatternFill
    title = cfg.get("title", "")
    lock = workbook.parent / ("~$" + workbook.name)
    if lock.exists(): sys.exit(f"{workbook.name} appears to be open in Excel ({lock.name} exists). Close it and run again.")
    created = not workbook.is_file()
    if created:
        workbook.parent.mkdir(parents=True, exist_ok=True)
        if not TEMPLATE.is_file(): build_template(TEMPLATE)
        shutil.copyfile(TEMPLATE, workbook)
    wb = openpyxl.load_workbook(workbook); ws = wb["Staffing"]; asm = wb["Assumptions"]
    if ws["A1"].value and "{title}" in str(ws["A1"].value): ws["A1"] = f"Staffing and pricing - {title}"
    bpath = sol / ".state" / "staffing-sync.json"
    base = read_baseline(bpath)
    pl = plan(roster, xlsx_rows(ws), base, prefer)
    byid = {r["id"]: r for r in roster}
    rowof = {x["id"]: x["row"] for x in xlsx_rows(ws).values() if x["id"]}
    free = (r for r in range(FIRST, LAST + 1) if not ws.cell(row=r, column=1).value and not ws.cell(row=r, column=2).value)
    hpm = float(asm["B6"].value); blank = lambda c: c.value in (None, "")
    # roster to workbook
    for rid, f, v in pl["to_x"]:
        r = rowof[rid]
        if f == "person": ws[f"C{r}"] = v
        elif f == "resume": ws[f"D{r}"] = v
        elif f == "scope": ws[f"E{r}"] = v
        elif f == "alloc": ws[f"G{r}"] = round(float(v), 4)
    for rid in pl["new_x"]:
        r = next(free); rowof[rid] = r; row = byid[rid]; c = csv_view(row); alloc = rs.fte_of(row); ph = rs.phases_of(row)
        ws[f"A{r}"] = rid; ws[f"C{r}"] = c["person"]; ws[f"D{r}"] = c["resume"]; ws[f"E{r}"] = c["scope"]; ws[f"G{r}"] = round(alloc, 4)
        for i, p in enumerate(rs.PHASES): ws.cell(row=r, column=9 + i, value=round((alloc if p in ph else 0) * float(asm.cell(row=3 + i, column=2).value) * hpm))
        pl["baseline"][rid] = dict(c)
    if seed_hours:
        for rid, r in rowof.items():
            row = byid.get(rid)
            if not row or row["status"] == "Dropped": continue
            alloc = rs.fte_of(row); ph = rs.phases_of(row)
            if blank(ws[f"G{r}"]): ws[f"G{r}"] = round(alloc, 4)
            for i, p in enumerate(rs.PHASES):
                cell = ws.cell(row=r, column=9 + i)
                if blank(cell): cell.value = round((alloc if p in ph else 0) * float(asm.cell(row=3 + i, column=2).value) * hpm)
    for rid, r in rowof.items():           # roster-only fields and formulas
        row = byid.get(rid)
        if row: ws[f"B{r}"] = row["role"]
        ws[f"L{r}"] = f"=SUM(I{r}:K{r})"; ws[f"M{r}"] = f"=L{r}*H{r}"
    # workbook to roster
    for rid, f, v in pl["to_c"]:
        row = byid[rid]
        if f == "person": row["person"] = "" if v == "TBD" else v
        elif f == "resume": row["resume"] = RES_C[v]
        elif f == "scope": row["scope"] = v
        elif f == "alloc": row["loe_pct"] = f"{float(v) * 100 / rs.headcount(row):g}"
        elif f == "phases": row["phases"] = v
    added_c = []
    nextnum = max([int(r["id"][2:]) for r in roster if r["id"][:2] == "P-" and r["id"][2:].isdigit()] + [0])
    xr = xlsx_rows(ws)
    for r in pl["new_c"]:
        x = xr[r]; nextnum += 1; rid = f"P-{nextnum:03d}"
        row = {c: "" for c in rs.COLUMNS}
        alloc = float(x["alloc"] or 0)
        row.update(id=rid, role=x["role"], status="Ours", in_response="no", scope=x["scope"], headcount="1", loe_pct=f"{alloc * 100:g}",
                   phases=";".join(str(p) for p in sorted(x["phases"])) or "1;2;3", person="" if x["person"] == "TBD" else x["person"],
                   resume=RES_C[x["resume"]], notes="Added in Staffing.xlsx; add source, scope, responsibilities, value added, and deliverables.")
        roster.append(row); byid[rid] = row; ws[f"A{r}"] = rid; rowof[rid] = r; added_c.append(rid)
        pl["baseline"][rid] = csv_view(row)
    # flags
    flagged = []
    for x in xlsx_rows(ws).values():
        rid = x["id"]; r = x["row"]; note = str(ws[f"N{r}"].value or "")
        row = byid.get(rid)
        if row and row["status"] == "Dropped" and "Dropped in roster" not in note:
            ws[f"N{r}"] = (note + " Dropped in roster; review hours and rate.").strip(); flagged.append(rid)
        elif rid and not row and "Not in roster" not in note:
            ws[f"N{r}"] = (note + " Not in roster; review.").strip(); flagged.append(rid)
    fill_in = PatternFill("solid", fgColor="FFF2CC")
    for r in range(FIRST, LAST + 1):
        if ws.cell(row=r, column=1).value: style_row(ws, r, fill_in)
    wb.save(workbook)
    if pl["to_c"] or added_c: rs.write(rs.roster_path(sol, cfg), roster)
    merged = dict(base); merged.update(pl["baseline"])
    (sol / ".state").mkdir(exist_ok=True); bpath.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n")
    return {"created": created, "to_x": pl["to_x"], "to_c": pl["to_c"], "conflicts": pl["conflicts"], "new_x": pl["new_x"], "added_c": added_c, "flagged": flagged,
            "consistency": consistency(ws, roster)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", action="store_true"); ap.add_argument("--seed-hours", action="store_true")
    ap.add_argument("--prefer", choices=("csv", "xlsx")); ap.add_argument("--check", action="store_true")
    ap.add_argument("--solution", nargs="?", const="", default=None)
    a = ap.parse_args()
    if a.template:
        build_template(TEMPLATE); print(f"wrote {TEMPLATE}"); return
    import build_response as br
    sol = br.resolve_solution(a.solution or None)
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    sx = cfg.get("staffing_xlsx")
    if not sx: sys.exit("solution.toml has no staffing_xlsx (path to the workbook, relative to `active-solution/`, for example ../../09 Pricing/Staffing.xlsx)")
    roster = rs.load(rs.roster_path(sol, cfg))
    if roster is None: sys.exit("roster not found; create response/resources.csv first (/rfps:resources)")
    if a.check:
        text, ok = status(sol, cfg, roster); print(text); sys.exit(0 if ok else 1)
    res = sync(sol, cfg, roster, (sol / sx).resolve(), a.seed_hours, a.prefer)
    show = lambda items: ", ".join(f"{i} {f}" for i, f, *_ in items) or "none"
    print(f"{(sol / sx).resolve()}{' (created)' if res['created'] else ''}")
    print(f"  roster to workbook: {show(res['to_x'])}; new rows: {', '.join(res['new_x']) or 'none'}")
    print(f"  workbook to roster: {show(res['to_c'])}; roles added to the roster: {', '.join(res['added_c']) or 'none'}")
    if res["conflicts"]:
        print("  CONFLICTS (left unchanged; run with --prefer csv or --prefer xlsx to choose):")
        for rid, f, cv, xv in res["conflicts"]: print(f"    {rid} {f}: roster = {cv!r}, workbook = {xv!r}")
    if res["flagged"]: print(f"  flagged for review in the workbook: {', '.join(res['flagged'])}")
    if res["consistency"]: print(f"  hours differ from allocation by more than 10 percent: {', '.join(res['consistency'])}")


if __name__ == "__main__":
    main()
