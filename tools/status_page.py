# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Write a local, self-contained HTML status page for the active solution: build/status.html.

Shows the flow steps by group with filters, what to do next with copyable commands, every response heading as a
color-coded grid, every open marker (decision, open, evidence needed, assertion) with a link to its line, the
blocking compliance checks, the evidence register, and the staffing roster. Nothing is uploaded; the page is one
file with no outside resources. It is regenerated each time, so refresh it with /rfps:status-page.

Usage: rfps-status-page [--solution [folder]] [--json]
"""
import argparse, csv, datetime, html, json, pathlib, re, subprocess, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import open_items as oi

ROOT = pathlib.Path(__file__).resolve().parent

def flow_json(sol):
    r = subprocess.run(["uv", "run", str(ROOT / "flow_status.py"), "--json", "--solution", str(sol)], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    return json.loads(r.stdout)

def blockers(sol):
    p = sol / "compliance-report.md"
    if not p.is_file(): return []
    t = p.read_text(); m = re.search(r"### Blocking Issues\s*\n(.*?)<!-- /derived:preflight -->", t, re.S)
    out = []
    for l in (m.group(1) if m else "").splitlines():
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 5 and re.match(r"[A-Z]-\d+", c[0]): out.append(dict(id=c[0], req=c[1], ref=c[2], why=c[3], action=c[4]))
    return out

def csv_rows(p, cols):
    if not p.is_file(): return []
    with open(p, newline="") as f: return [{k: (r.get(k) or "") for k in cols} for r in csv.DictReader(f)]

def build(sol):
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    fj = flow_json(sol)
    items = oi.scan(sol / cfg.get("response_dir", "response"))
    for x in items: x["path"] = (sol / cfg.get("response_dir", "response") / x["file"]).as_uri()
    reg = csv_rows(sol / cfg.get("register", "evidence/register.csv"), ["id", "client", "engagement", "claim", "clearance", "ban_phrases"])
    for r in reg: r["claim"] = r["claim"][:140]
    ros = csv_rows(sol / cfg.get("roster", "response/resources.csv"), ["id", "role", "status", "person", "headcount", "loe_pct", "phases", "resume"])
    files = [(n, (sol / n).as_uri()) for n in ("progress.md", "open-items.md", "brief.md", "gap-report.md", "coverage-matrix.md", "compliance-report.md", "resource-plan.md", "review-notes.md", "amendments/questions-to-state.md") if (sol / n).is_file()]
    builds = sorted((sol / cfg.get("build_dir", "build")).glob("*.docx"), key=lambda p: p.stat().st_mtime)
    if builds: files.append((builds[-1].name, builds[-1].as_uri()))
    return dict(title=cfg.get("title", sol.parent.name), generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                steps=fj["steps"], sections=fj["sections"], items=items, blockers=blockers(sol), register=reg, roster=ros, files=files)

TEMPLATE = open(pathlib.Path(__file__).with_name("templates") / "status_page.html").read()
LABEL = {"done": "Done", "attention": "Needs attention", "blocking": "Blocking", "todo": "Not started", "skipped": "Skipped"}
E = lambda x: html.escape(str(x), quote=True)

def dot(s): return f'<span class="dot s-{s}"></span>'

def render(d):
    st = d["steps"]; cnt = {k: sum(1 for x in st if x["state"] == k) for k in LABEL}
    total = len(st) - cnt["skipped"]; pct = round(100 * cnt["done"] / total) if total else 0
    counts = "".join(f'<span class="chip">{dot(k)}{cnt[k]} {LABEL[k].lower()}</span>' for k in LABEL if cnt[k])
    rank = {"blocking": 0, "attention": 1, "todo": 2}
    nxt = sorted([x for x in st if x["state"] in rank], key=lambda x: rank[x["state"]])[:3]
    cards = []
    for x in nxt:
        cmd = (f'<div class="row" style="margin-top:8px"><code>{E(x["command"])}</code><button class="copy" data-cmd="{E(x["command"])}">Copy command</button></div>') if x.get("command") else ""
        ask = f'<div class="sub" style="margin-top:6px">Ask: {E(x["ask"])}</div>' if x.get("ask") else ""
        cards.append(f'<div class="card next {x["state"]}"><h3>{dot(x["state"])} {E(x["title"])}</h3><div class="sub">{E(x["detail"])}</div>{cmd}{ask}</div>')
    nexthtml = "".join(cards) or '<div class="empty">Nothing open.</div>'
    stepchips = '<span class="chip on" data-f="all">All</span>' + "".join(f'<span class="chip" data-f="{k}">{dot(k)}{LABEL[k]}</span>' for k in ("blocking", "attention", "todo", "done"))
    groups = {}
    for x in st: groups.setdefault(x["group"], []).append(x)
    steps = "".join('<div class="card grp"><h3>%s</h3>%s</div>' % (E(g), "".join(
        f'<div class="step" data-state="{x["state"]}"><span class="dot s-{x["state"]}" style="margin-top:6px"></span><div><div class="t">{E(x["title"])}</div><div class="d">{E(x["detail"])}</div></div></div>' for x in xs)) for g, xs in groups.items())
    secs, grid, cur = [], [], None
    def close():
        if cur is not None: secs.append(f'<div class="card" style="margin-bottom:10px"><h3>{E(cur)}</h3><div class="grid">{"".join(grid)}</div></div>')
    for x in d["sections"]:
        if x["level"] == 1:
            close(); cur, grid = x["heading"], []; continue
        note = (" - " + ", ".join(x["notes"])) if x["notes"] else ""
        grid.append(f'<div class="tile {x["state"]}" title="{E(x["heading"])}{E(note)}">{E(x["heading"])}<small>{x["words"]} words{E(note)}</small></div>')
    close()
    kinds = [("all", "All", len(d["items"])), ("DECISION", "Decision", 0), ("OPEN", "Open", 0), ("EVIDENCE NEEDED", "Evidence", 0), ("ASSERTION", "Assertion", 0)]
    kc = {k: sum(1 for x in d["items"] if x["kind"] == k) for k, _, _ in kinds}
    itemchips = "".join(f'<span class="chip{" on" if k == "all" else ""}" data-k="{E(k)}">{lab} ({len(d["items"]) if k == "all" else kc.get(k, 0)})</span>' for k, lab, _ in kinds)
    rows = "".join(f'<tr class="item" data-kind="{E(x["kind"])}"><td><span class="k k-{"EVIDENCE" if x["kind"] == "EVIDENCE NEEDED" else x["kind"]}">{E(x["kind"])}</span></td><td><a class="lnk" href="{E(x["path"])}">{E(x["file"])}:{x["line"]}</a></td><td>{E(x["section"])}</td><td>{E(x["text"])}</td></tr>' for x in d["items"]) or '<tr><td colspan="4" class="empty">No open items.</td></tr>'
    blk = "".join(f'<tr class="blk"><td>{E(x["id"])}</td><td>{E(x["req"])}</td><td>{E(x["ref"])}</td><td>{E(x["why"])}</td><td>{E(x["action"])}</td></tr>' for x in d["blockers"]) or '<tr><td colspan="5" class="empty">None.</td></tr>'
    reg = "".join(f'<tr><td>{E(x["id"])}</td><td>{E(x["client"])}</td><td>{E(x["claim"])}</td><td class="cl-{E(x["clearance"])}">{E(x["clearance"])}</td></tr>' for x in d["register"]) or '<tr><td colspan="4" class="empty">None.</td></tr>'
    team = "".join(f'<tr><td>{E(x["id"])}</td><td>{E(x["role"])}</td><td>{E(x["status"])}</td><td{(" style=" + chr(34) + "color:var(--blk);font-weight:600" + chr(34)) if (x["person"] or "TBD") == "TBD" and x["status"] == "KP" else ""}>{E(x["person"] or "TBD")}</td><td>{E(x["headcount"] or "1")}</td><td>{E(x["loe_pct"])}</td><td>{E(x["phases"])}</td></tr>' for x in d["roster"]) or '<tr><td colspan="7" class="empty">None.</td></tr>'
    files = "".join(f'<a class="chip" style="text-decoration:none" href="{E(u)}">{E(n)}</a>' for n, u in d["files"])
    return {"TITLE": E(d["title"]), "GEN": E(f"Generated {d['generated']} - local file, refresh with /rfps:status-page"), "PCT": str(pct),
            "PTXT": f"{cnt['done']} of {total} steps done ({pct}%)", "COUNTS": counts, "NEXT": nexthtml, "STEPCHIPS": stepchips, "STEPS": steps,
            "SECTIONS": "".join(secs), "ITEMCHIPS": itemchips, "ITEMROWS": rows, "BLOCKROWS": blk, "REGROWS": reg, "TEAMROWS": team, "FILES": files}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default="")
    ap.add_argument("--json", action="store_true", help="print the page data as JSON and write nothing (used by the Claude pane)")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    if a.json:
        print(json.dumps(build(sol))); return
    page = TEMPLATE
    for k, v in render(build(sol)).items(): page = page.replace(f"__{k}__", v)
    out = sol / cfg.get("build_dir", "build") / "status.html"
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(page)
    print(f"Wrote {out}\n{out.as_uri()}")

if __name__ == "__main__":
    main()
