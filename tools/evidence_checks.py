# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Helper module (not run on its own): recency, value and reference checks on the past performance the response cites.

Thresholds come from the solicitation (the person recording them reads the instructions) and live in solution.toml:
  [past_performance]
  max_age_years = 5            # work must have ended within this many years (ongoing work counts as now)
  min_value_usd = 1000000      # each cited engagement must be at least this large
  min_references = 3           # how many distinct clients must qualify
  reference_max_age_days = 180 # a reference contact must have been confirmed this recently
Without the table the checks report that nothing is set. Rows whose date or value is blank are reported as unknown, never as passing.
"""
import datetime, re

def parse_when(s, end=False):
    """'2024', '2024-03', '2024-03-15', 'present' -> date; None when blank or unreadable. A bare year is its last day when end is true, else its first."""
    s = (s or "").strip().lower()
    if s in ("present", "ongoing", "current", "now"): return datetime.date.today()
    m = re.fullmatch(r"(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?", s)
    if not m: return None
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    try:
        if d: return datetime.date(y, int(mo), int(d))
        if mo:
            nxt = datetime.date(y + (int(mo) == 12), int(mo) % 12 + 1, 1)
            return nxt - datetime.timedelta(days=1) if end else datetime.date(y, int(mo), 1)
        return datetime.date(y, 12, 31) if end else datetime.date(y, 1, 1)
    except ValueError: return None

def parse_money(s):
    """'$1.2M', '450K', '1,200,000', '2.5 million' -> float; None when blank or unreadable."""
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(million|thousand|billion|[kmb])?\b", (s or "").lower().replace("$", ""))
    if not m: return None
    v = float(m.group(1).replace(",", "")); u = (m.group(2) or "")[:1]
    return v * {"k": 1e3, "t": 1e3, "m": 1e6, "b": 1e9}.get(u, 1)

def pp_checks(cfg, reg, cited, today=None):
    """Table rows (| Check | Result | Detail |) for the compliance report's automated checks."""
    t = cfg.get("past_performance")
    if not t: return ["| Past performance meets the solicitation's age, value and reference rules | Info | no [past_performance] thresholds in solution.toml; set max_age_years, min_value_usd, min_references from the solicitation |"]
    today = today or datetime.date.today(); rows = [reg[i] | {"id": i} for i in sorted(cited) if i in reg]
    out = []
    if not rows: return ["| Past performance meets the solicitation's age, value and reference rules | Info | the response cites no register rows yet |"]
    if t.get("max_age_years") is not None:
        old, unk = [], []
        for r in rows:
            d = parse_when(r.get("end") or r.get("date"), end=True)
            if d is None: unk.append(r["id"]); continue
            if (today - d).days / 365.25 > float(t["max_age_years"]): old.append(f"{r['id']} ({d.isoformat()})")
        parts = ([f"too old: {', '.join(old)}"] if old else []) + ([f"no readable end date: {', '.join(unk)}"] if unk else []) or ["all recent"]
        out.append(f"| Cited work is recent enough (ended within {t['max_age_years']} years) | {'Pass' if not (old or unk) else 'Open'} | {'; '.join(parts)} |")
    if t.get("min_value_usd") is not None:
        low, unk = [], []
        for r in rows:
            v = parse_money(r.get("value_usd"))
            if v is None: unk.append(r["id"])
            elif v < float(t["min_value_usd"]): low.append(f"{r['id']} (${v:,.0f})")
        parts = ([f"below: {', '.join(low)}"] if low else []) + ([f"no value recorded: {', '.join(unk)}"] if unk else []) or ["all meet it"]
        out.append(f"| Cited work meets the minimum value (${float(t['min_value_usd']):,.0f}) | {'Pass' if not (low or unk) else 'Open'} | {'; '.join(parts)} |")
    if t.get("min_references") is not None:
        ok = {}
        for r in rows:
            d = parse_when(r.get("end") or r.get("date"), end=True); v = parse_money(r.get("value_usd"))
            if (r.get("clearance") or "").strip() != "cleared": continue
            if t.get("max_age_years") is not None and (d is None or (today - d).days / 365.25 > float(t["max_age_years"])): continue
            if t.get("min_value_usd") is not None and (v is None or v < float(t["min_value_usd"])): continue
            ok.setdefault((r.get("client") or r["id"]).strip().lower(), r["id"])
        need = int(t["min_references"])
        out.append(f"| Enough qualifying references ({need} distinct clients) | {'Pass' if len(ok) >= need else 'Open'} | {len(ok)} qualifying (cleared, recent, large enough): {', '.join(sorted(ok.values())) or 'none'} |")
    if t.get("reference_max_age_days") is not None:
        stale, none = [], []
        for r in rows:
            if not (r.get("reference_contact") or "").strip(): none.append(r["id"]); continue
            c = parse_when(r.get("reference_confirmed"))
            if c is None or (today - c).days > int(t["reference_max_age_days"]): stale.append(r["id"])
        parts = ([f"not recently confirmed: {', '.join(stale)}"] if stale else []) + ([f"no contact recorded: {', '.join(none)}"] if none else []) or ["all confirmed"]
        out.append(f"| Reference contacts confirmed within {t['reference_max_age_days']} days | {'Pass' if not (stale or none) else 'Open'} | {'; '.join(parts)} |")
    return out
