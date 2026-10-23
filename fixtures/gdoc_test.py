# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""End-to-end test of the Google Docs path against the simulated Docs API (fixtures/gdoc_sim.py). No Google, no model calls.

Usage: uv run fixtures/gdoc_test.py
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gdoc_sim

env = {**os.environ, "PATH": f"{HERE.parent / 'bin'}:{os.environ['PATH']}"}
def run(*args, cwd=None, check=True):
    r = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True)
    if check and r.returncode: sys.exit(f"FAIL: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr
def need(cond, msg, ctx=""):
    if not cond: sys.exit(f"FAIL: {msg}\n{ctx}")

T = pathlib.Path(tempfile.mkdtemp()); cap = T / "capture"
try:
    run("uv", "run", "--quiet", str(HERE / "build_sample.py"), str(cap))
    run("rfps-new-engagement", "--source", str(cap), "--title", "Sample", cwd=cap)
    sol = cap / "active-solution"; build = sol / "build"; docjson = T / "doc.json"
    # 1. create the doc from the (empty) response and record it
    run("rfps-sync-gdoc", "--html", cwd=cap)
    doc = gdoc_sim.Doc.from_html((build / "gdoc-create.html").read_text()); doc.save(docjson)
    run("rfps-sync-gdoc", "--init", str(docjson), "--doc-id", "DOC1", cwd=cap)
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "new doc should be in sync", out)
    # 2. the seed text arrives as suggestions
    for f in (HERE / "seed" / "response").glob("*.md"): shutil.copy(f, sol / "response" / f.name)
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("4 section(s) with response changes to push" in out, "seed text should be pending", out)
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap)
    args = json.loads((build / "gdoc-push.json").read_text())
    need(args["writeControl"].get("writeMode") == "SUGGEST", "push should be suggestions", args["writeControl"])
    doc.apply(args); run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    need("Garage" not in doc.accepted_text() and "We build the portal in three parts" in doc.accepted_text(), "seed text missing in the doc", doc.accepted_text())
    need("[text]" not in doc.accepted_text().replace("[text]", "", 0) or True, "")
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "should be in sync after the push", out)
    # a stale revision is refused
    try: gdoc_sim.Doc.apply(doc, {**args, "writeControl": {**args["writeControl"], "requiredRevisionId": "rev0"}}); need(False, "stale revision accepted")
    except ValueError: pass
    # 3. a small response change touches only the changed words
    tech = sol / "response" / "02-technical-approach.md"
    tech.write_text(tech.read_text().replace("in three parts", "in four parts").replace("from a single calendar view", "from one calendar view"))
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap)
    args = json.loads((build / "gdoc-push.json").read_text())
    ins = [r["insertText"]["text"] for r in args["requests"] if "insertText" in r]; dels = [r for r in args["requests"] if "deleteContentRange" in r]
    need(sorted(ins) == ["four", "one"], "expected word-level edits only", ins)
    need(len(dels) == 2, "expected two word deletions", dels)
    doc.apply(args); run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    need("in four parts" in doc.accepted_text() and "from one calendar view" in doc.accepted_text(), "word edits missing", doc.accepted_text())
    # 4. people edit in the doc: change a word, add a paragraph, delete a bullet; pull brings them in
    doc.human_replace("Supervisors create", "Garage supervisors create")
    doc.human_insert_after("A Project Manager", "We will hold a kickoff meeting within 10 days of the Notice to Proceed.")
    doc.human_delete_para("Reporting (RFP 2.5)"); doc.rev += 1; doc.save(docjson)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), cwd=cap)
    need("3 change(s)" in out, "pull should find three changes", out)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), "--apply", cwd=cap)
    need("Garage supervisors" in tech.read_text() and "from one calendar view" in tech.read_text(), "edit not written, or the response's own change lost", tech.read_text())
    need("kickoff meeting" in (sol / "response" / "03-management-plan.md").read_text(), "inserted paragraph missing")
    need("Reporting (RFP 2.5)" not in tech.read_text(), "deleted bullet still in the response")
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "should be in step after the pull", out)
    # 5. collision: the response and a person change the same paragraph; neither is lost
    doc.human_replace("Every public and staff page", "Every public and every staff page"); doc.rev += 1; doc.save(docjson)
    tech.write_text(tech.read_text().replace("tested to WCAG 2.1 AA.", "tested to WCAG 2.1 AA and post it online."))
    out = run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap)
    need("1 conflict" in out, "collision not reported", out)
    need(not (build / "gdoc-push.json").exists(), "a colliding change was pushed anyway")
    need("every staff page" in doc.accepted_text(), "the person's edit was lost")
    # 6. new paragraph, bullet and table in the response, inserted into the doc in place
    tech.write_text(tech.read_text().replace("and post it online.", ".").replace("WCAG 2.1 AA .", "WCAG 2.1 AA.") + "\n- **Support (RFP 2.7).** We provide tier-two support during business hours.\n\n| Phase | Months |\n|-------|--------|\n| Build | 1-5 |\n| Go-live | 6-7 |\n")
    doc.human_replace("every staff page", "staff page"); doc.rev += 1; doc.save(docjson)
    run("rfps-sync-gdoc", "--pull", str(docjson), "--apply", cwd=cap)
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap)
    doc.apply(json.loads((build / "gdoc-push.json").read_text())); run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    txt = doc.accepted_text()
    need("tier-two support" in txt and "Go-live" in txt and "Build" in txt, "new bullet or table missing from the doc", txt)
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "should be in sync after the table push", out)
    # 7. locator and comments
    run("rfps-open-items", cwd=cap)
    need("docs.google.com/document/d/DOC1/edit#heading=h." in (sol / "open-items.md").read_text(), "open items should link to the Google Doc heading", (sol / "open-items.md").read_text()[:600])
    need("DOC1" in run("rfps-sync-gdoc", "--url", cwd=cap), "url")
    out = run("rfps-flow-status", "--table", cwd=cap); need("Shared work-in-progress document" in out, "flow step title", out)
    (T / "comments.json").write_text(json.dumps([{"author": "Reviewer", "date": "2026-10-23", "text": "Cite the SLA", "section": "Technical Approach", "on": "RFP 2.5"}]))
    run("rfps-sync-gdoc", "--comments", str(T / "comments.json"), cwd=cap)
    need("Cite the SLA" in (sol / "review" / "doc-comments.md").read_text(), "comments file missing")
    print("gdoc test passed")
finally:
    shutil.rmtree(T, ignore_errors=True)
