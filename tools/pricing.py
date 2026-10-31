# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl"]
# ///
"""Helper module (not run on its own): a price view from the staffing workbook, and the rate sheet check.

The price is the pricer's decision. This only adds up what the workbook holds (hours x rate, by phase and labor category), shows how much it moves
if the hours move, sets it beside any ceiling or budget figure the solicitation states, and, when a rate sheet is named in solution.toml
(rate_sheet = "09 Pricing/Rate Sheet.csv", columns labor_category,rate), checks every labor category and rate against it. Nothing here recommends a price.
"""
import csv, pathlib, re
import evidence_checks as ec

FIRST, LAST = 5, 200

def _num(v):
    try: return float(str(v).strip().replace("$", "").replace(",", ""))
    except (TypeError, ValueError): return None

def workbook_rows(sol, cfg):
    """[{id, role, category, rate, hours[3]}] from the Staffing sheet, or None when there is no readable workbook."""
    sx = cfg.get("staffing_xlsx")
    if not sx: return None
    path = (pathlib.Path(sol) / sx).resolve()
    if not path.is_file(): return None
    import openpyxl
    try: ws = openpyxl.load_workbook(path, data_only=True)["Staffing"]
    except Exception: return None
    out = []
    for r in range(FIRST, LAST + 1):
        rid, role = ws.cell(row=r, column=1).value, ws.cell(row=r, column=2).value
        if not rid and not role: continue
        out.append(dict(id=str(rid or "").strip(), role=str(role or "").strip(), category=str(ws.cell(row=r, column=6).value or "").strip(),
                        rate=_num(ws.cell(row=r, column=8).value), hours=[_num(ws.cell(row=r, column=9 + i).value) or 0.0 for i in range(3)]))
    return out

def rate_sheet(sol, cfg):
    """{lower-case labor category: rate} from the csv named by rate_sheet; None when none is set or the file is missing."""
    rp = cfg.get("rate_sheet")
    if not rp: return None
    p = (pathlib.Path(sol) / rp).resolve()
    if not p.is_file(): return None
    with open(p, newline="") as fh:
        return {(r.get("labor_category") or "").strip().lower(): _num(r.get("rate")) for r in csv.DictReader(fh) if (r.get("labor_category") or "").strip()}

def stated_figures(plan_text):
    """[(item, dollars)] from the 'Figures stated by the solicitation' table in resource-plan.md for rows that read as a ceiling or budget."""
    m = re.search(r"## Figures stated by the solicitation(.*?)(?=\n## )", plan_text, re.S)
    out = []
    for line in (m.group(1) if m else "").split("\n"):
        c = [x.strip() for x in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(c) >= 2 and re.search(r"ceiling|budget|not.to.exceed|nte|maximum|total amount|funding|estimated value", c[0], re.I):
            v = ec.parse_money(c[1])
            if v: out.append((c[0], v))
    return out

def price_view(sol, cfg, plan_text):
    """Lines for the derived priceview block, or None when the workbook has nothing priced yet."""
    rows = workbook_rows(sol, cfg)
    if rows is None: return ["The staffing workbook is not set or not created yet (staffing_xlsx in solution.toml, rfps-staffing)."]
    priced = [r for r in rows if r["rate"] and sum(r["hours"])]
    if not priced: return [f"{len(rows)} role(s) in the workbook, none with both a rate and hours yet, so there is nothing to total."]
    hrs = [sum(r["hours"][i] for r in priced) for i in range(3)]; cost = [sum(r["hours"][i] * r["rate"] for r in priced) for i in range(3)]
    total_h, total = sum(hrs), sum(cost)
    out = [f"**Priced from the workbook:** {len(priced)} of {len(rows)} role(s). **Total hours:** {total_h:,.0f} (Phase 1 {hrs[0]:,.0f}, Phase 2 {hrs[1]:,.0f}, Phase 3 {hrs[2]:,.0f}). **Total labor cost:** ${total:,.0f} (Phase 1 ${cost[0]:,.0f}, Phase 2 ${cost[1]:,.0f}, Phase 3 ${cost[2]:,.0f}). **Average rate:** ${total / total_h:,.2f} per hour.",
           f"**If the hours move 10 percent:** ${total * 0.9:,.0f} to ${total * 1.1:,.0f}; each 100 hours moves the price by about ${100 * total / total_h:,.0f}.", ""]
    by = {}
    for r in priced: by[r["category"] or "(no labor category)"] = by.get(r["category"] or "(no labor category)", 0) + sum(h * r["rate"] for h in r["hours"])
    out.append("**Largest cost shares:** " + "; ".join(f"{k} {v / total * 100:.0f}%" for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:5]))
    figs = stated_figures(plan_text)
    if figs:
        out += ["", "| Stated by the solicitation | Figure | Our labor total | Difference |", "|---|---|---|---|"]
        out += [f"| {i.replace('|', '/')} | ${v:,.0f} | ${total:,.0f} | {(total - v) / v * 100:+.0f}% |" for i, v in figs]
        out.append("Labor only: other direct costs, fee and any fixed-price structure are not in the workbook.")
    return out

def rate_checks(sol, cfg):
    """Table rows for the resource checks: labor categories on the rate sheet, rates within it."""
    sheet = rate_sheet(sol, cfg)
    if not cfg.get("rate_sheet"): return ["| Labor categories and rates match the rate sheet | Info | no rate_sheet in solution.toml |"]
    if sheet is None: return [f"| Labor categories and rates match the rate sheet | Open | {cfg['rate_sheet']} not found |"]
    rows = [r for r in (workbook_rows(sol, cfg) or []) if r["rate"] or r["category"]]
    off = [f"{r['id'] or r['role']} ({r['category'] or 'no category'})" for r in rows if r["category"].lower() not in sheet]
    over = [f"{r['id'] or r['role']} ${r['rate']:g} > ${sheet[r['category'].lower()]:g}" for r in rows if r["category"].lower() in sheet and r["rate"] and sheet[r["category"].lower()] and r["rate"] > sheet[r["category"].lower()] + 1e-9]
    if not rows: status, detail = "Open", "no priced roles yet"
    elif off or over: status, detail = "Fail", "; ".join(x for x in ((f"not on the sheet: {', '.join(off)}" if off else ""), (f"rate above the sheet: {', '.join(over)}" if over else "")) if x)
    else: status, detail = "Pass", f"{len(rows)} priced role(s) checked"
    return [f"| Labor categories and rates match the rate sheet | {status} | {detail} |"]
