# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""One ranked list of everything left to do once the work-in-progress response exists.

Collects, from the solution's own files:
  - markers in response/*.md: DECISION, OPEN, EVIDENCE NEEDED, ASSERTION
  - coverage-matrix.md rows classified Gap, and rows whose action is Assert with caveat, Seek evidence or Escalate
  - compliance-report.md rows whose status is Fail, Partial or Ambiguous
  - evaluation-sim.md factors the second reader rated in the lower half of the scale
  - amendments/log.md rows whose response or analysis is not marked done, and submission.md rows not Done (overdue ones rank first)
Markers in a section whose evaluation factor has a weight in win-strategy.md move up the list (30 percent or more by two places, 15 percent or more by one).
and ranks them (blockers first). Each item says who can act on it: the tools ("tool"), the user ("you"), or either.
What was done about each item (addressed, mine, skipped) is kept in .state/worklist.json, keyed by a stable id, so
re-running never loses a choice. It writes no report file: the list is computed from the files each time.

Usage:
  rfps-worklist [--solution [folder]]              print the counts
  rfps-worklist --table                             the whole list as a markdown table
  rfps-worklist --next [N]                          print the next N open items (default 1) as JSON
  rfps-worklist --set ID addressed|mine|skipped|open [--note TEXT]   ID may also be a flow step id (addressed = done, skipped = skip, open = reset), so there is one command for choices
  rfps-worklist --json                              the whole list as JSON
"""
import argparse, hashlib, json, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_response as br
import open_items
import strategy as sg

# (rank, label, who, suggested action) - lower rank is more urgent
MARKER = {"DECISION": (2, "Decision", "you", "Ask the user to choose; replace the marker with the final text"),
          "OPEN": (3, "Open question", "either", "Answer from the documents if possible, otherwise ask; resolve or state the assumption"),
          "EVIDENCE NEEDED": (4, "Evidence needed", "either", "Find a source (/rfps:add-past-performance), propose a register row, or remove the claim"),
          "ASSERTION": (7, "Assertion", "either", "Support it with a register row or accept it knowingly")}

def key(*parts): return hashlib.sha1("|".join(parts).encode()).hexdigest()[:8]

def tables(text):
    """Yield (heading, header cells, row cells) for each markdown table row."""
    head = ""; cols = None
    for line in text.splitlines():
        if line.startswith("#"): head = line.lstrip("# ").strip(); cols = None; continue
        if not line.startswith("|"): cols = None; continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols is None: cols = cells; continue
        if set("".join(cells)) <= set("-: "): continue
        yield head, cols, cells

def col(cols, cells, *names):
    for n in names:
        for i, c in enumerate(cols):
            if c.lower().startswith(n.lower()) and i < len(cells): return cells[i]
    return ""

def marker_id(x): return key("m", x["kind"], x["section"], x["text"][:60])

def choice_of(sol, x):
    """The user's recorded choice for a marker found by open_items.scan ('' when none); lets the other views show it."""
    c = load_state(sol).get(marker_id(x), {})
    if c.get("status", "open") == "open": return ""
    return c["status"] + (f" by {c['by']}" if c.get("by") else "")

def collect(sol, cfg):
    items = []
    rdir = sol / cfg.get("response_dir", "response"); wmap = sg.weight_by_heading(sol); h1w = {}
    def weight_of(fname):   # the evaluation weight of the factor whose response heading is this file's Heading 1 (win-strategy.md); None when unknown
        if fname not in h1w:
            m = re.search(r"^#\s+(.+)$", (rdir / fname).read_text(), re.M)
            h1w[fname] = wmap.get(sg.norm(m.group(1))) if m else None
        return h1w[fname]
    for x in open_items.scan(rdir):
        rank, label, who, act = MARKER[x["kind"]]
        w = weight_of(x["file"]); txt = x["text"]
        if w and x["kind"] != "DECISION":   # open work in a heavily weighted factor costs more points, so it moves up the list
            rank = max(2, rank - (2 if w >= 30 else 1 if w >= 15 else 0)); txt = f"[{w:g}% factor] " + txt
        items.append(dict(id=marker_id(x), rank=rank, kind=label, who=who, action=act,
                          where=f"{x['file']}:{x['line']}", section=x["section"], text=txt))
    cm = sol / "coverage-matrix.md"
    if cm.is_file():
        for head, cols, cells in tables(cm.read_text()):
            rid = col(cols, cells, "#")
            if not re.match(r"R-\d+", rid): continue
            cls, sev, act = col(cols, cells, "Classification"), col(cols, cells, "Gap Severity"), col(cols, cells, "Recommended Action")
            mand = col(cols, cells, "Mandatory").lower().startswith(("y", "m", "x"))
            req = col(cols, cells, "Requirement")
            if cls.lower().startswith("gap"):
                rank = 1 if sev.lower().startswith("disq") else (5 if sev.lower().startswith("man") else 6)
                items.append(dict(id=key("g", rid), rank=rank, kind=f"Requirement gap ({sev or 'unrated'})", who="either",
                                  action="Find evidence, change the approach, or escalate; update the matrix row", where=f"coverage-matrix.md {rid}", section=head, text=f"{rid} {req}"))
            elif act.lower().startswith(("assert", "seek", "escalate")):
                items.append(dict(id=key("a", rid), rank=6 if mand else 7, kind="Weakly supported requirement", who="either",
                                  action=act, where=f"coverage-matrix.md {rid}", section=head, text=f"{rid} {req}"))
    cr = sol / "compliance-report.md"
    if cr.is_file():
        for head, cols, cells in tables(cr.read_text()):
            rid, st = col(cols, cells, "#"), col(cols, cells, "Status")
            if not re.match(r"[A-Z]-\d+", rid) or not st.lower().startswith(("fail", "partial", "ambig")): continue
            mand = col(cols, cells, "Mandatory").lower().startswith(("y", "m", "x"))
            items.append(dict(id=key("c", rid), rank=1 if (mand and st.lower().startswith("fail")) else 5, kind=f"Compliance {st}", who="either",
                              action=col(cols, cells, "Remediation") or "Fix and re-run /rfps:compliance-validator", where=f"compliance-report.md {rid}",
                              section=head, text=f"{rid} {col(cols, cells, 'Requirement')}"))
    for a in sg.amendments(sol):   # an amendment supersedes the base solicitation where they differ, so one not yet applied outranks ordinary open work
        undone = [k for k, v in (("response", a["response_updated"]), ("analysis", a["analysis_rerun"])) if v.strip().lower() not in ("yes", "y", "done", "n/a", "na")]
        if undone: items.append(dict(id=key("am", a["id"]), rank=1, kind="Amendment not applied", who="either",
                                     action="Re-run the sweep and the analysis, update the affected requirement rows and response text, then mark this row in amendments/log.md", where=f"amendments/log.md #{a['id']}",
                                     section=a["type"] or "Amendment", text=f"Amendment {a['id']} ({a['file']}): {a['change']} - not yet applied to the {' and '.join(undone)}; affects {a['affected'] or 'unknown requirements'}"))
    import datetime as _dt
    for q in sg.questions(sol):   # questions to the agency: a draft near the deadline, and an answer not yet logged as a Q&A amendment
        s = q["status"].lower()
        try: days = (_dt.date.fromisoformat(q["due"][:10]) - _dt.date.today()).days
        except ValueError: days = None
        if s == "draft" and days is not None and days <= 3:
            items.append(dict(id=key("q", q["id"]), rank=1 if days < 0 else 3, kind="Question deadline passed" if days < 0 else "Question not sent", who="you",
                              action="Send it (or drop it) before the questions deadline; mark it Sent in questions.md", where=f"questions.md {q['id']}", section="Questions", text=f"{q['id']} {q['question']} (due {q['due']})"))
        if s == "answered" and q["logged"].strip() in ("", "-"):
            items.append(dict(id=key("ql", q["id"]), rank=2, kind="Answer not logged", who="either", action="Log the answer in amendments/log.md, re-run the sweep and apply it to the requirements and response",
                              where=f"questions.md {q['id']}", section="Questions", text=f"{q['id']} {q['question']} - answered: {q['answer']}"))
    for r in sg.submission(sol):   # mandatory forms and steps not yet done; overdue first
        if r["status"].lower() in ("done", "n/a", "na"): continue
        import datetime
        try: late = datetime.date.fromisoformat(r["due"][:10]) < datetime.date.today()
        except ValueError: late = False
        items.append(dict(id=key("sub", r["id"]), rank=1 if late else 4, kind="Overdue submission step" if late else "Submission step", who="you",
                          action="Get it done and mark it Done in submission.md", where=f"submission.md {r['id']}", section=r["owner"] or "Submission", text=f"{r['id']} {r['item']} (due {r['due'] or 'unset'})"))
    for r in sg.evalsim(sol)["rows"]:   # factors the independent second reader rated in the lower half of the scale
        p = sg.rating_points(r["rating"], sg.evalsim(sol)["scale"])
        if p is None or p > 0.5: continue
        items.append(dict(id=key("v", r["id"]), rank=3 if p <= 0.25 else 6, kind=f"Weak factor ({r['rating']})", who="either",
                          action=r["change"] or "Make the change that most raises the rating; re-run /rfps:evaluator-simulator", where=f"evaluation-sim.md {r['id']}",
                          section=r["factor"], text=f"{r['id']} {r['factor']}: {r['weaknesses']}"))
    return sorted(items, key=lambda i: (i["rank"], i["where"]))

def load_state(sol):
    f = sol / ".state" / "worklist.json"
    return json.loads(f.read_text()) if f.is_file() else {}

def save_state(sol, st):
    d = sol / ".state"; d.mkdir(exist_ok=True); (d / "worklist.json").write_text(json.dumps(st, indent=1))

def open_list(sol, cfg):
    st = load_state(sol); items = collect(sol, cfg)
    for i in items: i.update(status=st.get(i["id"], {}).get("status", "open"), note=st.get(i["id"], {}).get("note", ""), by=st.get(i["id"], {}).get("by", ""))
    return items

def table(items):
    out = ["| Rank | ID | Kind | Who | Where | What | Suggested next move | Status |", "|---|---|---|---|---|---|---|---|"]
    for i in items:
        t = i["text"].replace("|", "/"); t = t if len(t) <= 160 else t[:157] + "..."
        out.append(f"| {i['rank']} | {i['id']} | {i['kind']} | {i['who']} | {i['where']} | {t} | {i['action'].replace('|', '/')} | {i['status']}{(' by ' + i['by']) if i['by'] else ''}{(' - ' + i['note']) if i['note'] else ''} |")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", nargs="?", const="", default="")
    ap.add_argument("--next", nargs="?", const=1, type=int); ap.add_argument("--json", action="store_true"); ap.add_argument("--table", action="store_true")
    ap.add_argument("--set", nargs=2, metavar=("ID", "STATUS")); ap.add_argument("--note", default="")
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); cfg = tomllib.loads((sol / "solution.toml").read_text())
    if a.set:
        i, s = a.set
        if s not in ("addressed", "mine", "skipped", "open"): sys.exit("status must be addressed, mine, skipped or open")
        if i in {st["id"] for st in tomllib.loads((pathlib.Path(__file__).parent / "flow.toml").read_text())["step"]}:
            if s == "mine": sys.exit("a flow step is done, skipped or open; use addressed, skipped or open")
            import subprocess
            fs = str(pathlib.Path(__file__).parent.parent / "bin" / "rfps-flow-status")
            if not (sol / "progress.md").is_file(): subprocess.run([fs, "--solution", str(sol)], capture_output=True)   # writes progress.md
            r = subprocess.run([fs, "--solution", str(sol), "--set", i, {"addressed": "done", "skipped": "skip", "open": "reset"}[s]], capture_output=True, text=True)
            print((r.stdout + r.stderr).strip()); sys.exit(r.returncode)
        if i not in {x["id"] for x in collect(sol, cfg)}: sys.exit(f"no item {i} in the current list")
        import collab
        st = load_state(sol); st[i] = {"status": s, "note": a.note, **({"by": collab.whoami()} if collab.whoami() else {})}; save_state(sol, st)
    items = open_list(sol, cfg); todo = [i for i in items if i["status"] == "open"]
    if a.json: print(json.dumps(items, indent=1))
    elif a.table: print(table(items))
    elif a.next: print(json.dumps(todo[:a.next], indent=1))
    else:
        by = {}
        for i in todo: by[i["kind"]] = by.get(i["kind"], 0) + 1
        print(f"worklist: {len(todo)} open of {len(items)}, {sum(1 for i in items if i['status'] == 'mine')} yours, {sum(1 for i in items if i['status'] == 'skipped')} skipped (" + ", ".join(f"{n} {k}" for k, n in sorted(by.items(), key=lambda kv: -kv[1])) + ")")

if __name__ == "__main__":
    main()
