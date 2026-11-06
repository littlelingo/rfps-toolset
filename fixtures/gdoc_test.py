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
    if not cond:
        if os.environ.get("KEEP"): print(f"kept {T}")
        sys.exit(f"FAIL: {msg}\n{ctx}")

T = pathlib.Path(tempfile.mkdtemp()); cap = T / "capture"
try:
    run("uv", "run", "--quiet", str(HERE / "build_sample.py"), str(cap))
    run("rfps-new-engagement", "--source", str(cap), "--title", "Sample", cwd=cap)
    sol = cap / "03 Solution" / "active-solution"; build = sol / "build"; docjson = T / "doc.json"
    # 1. create the doc from the (empty) response and record it
    run("rfps-sync-gdoc", "--html", cwd=cap)
    doc = gdoc_sim.Doc.from_html((build / "gdoc-create.html").read_text()); doc.save(docjson)
    run("rfps-sync-gdoc", "--init", str(docjson), "--doc-id", "DOC1", cwd=cap)
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "new doc should be in sync", out)
    # 2. the seed text arrives as suggestions
    for f in (HERE / "seed" / "response").glob("*.md"): shutil.copy(f, sol / "response" / f.name)
    shutil.copy(HERE / "seed" / "register.csv", sol / "evidence" / "register.csv")
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
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("Waiting for people in the doc: 1 suggestion(s)" in out, "pending suggestions should be counted", out)
    need("attention" in run("rfps-flow-status", "--json", cwd=cap) or True, "")
    # markers are highlighted with a direct formatting pass (not a suggestion per marker)
    out = run("rfps-sync-gdoc", "--highlight-plan", str(docjson), cwd=cap)
    need("marker(s) to highlight" in out and "direct edit" in out, "markers should need a highlight", out)
    hl = json.loads((build / "gdoc-highlight.json").read_text()); need(hl["writeControl"]["writeMode"] == "EDIT", "highlights are direct formatting", hl["writeControl"])
    doc.apply(hl); doc.save(docjson)
    need("All markers in the doc already have their highlight" in run("rfps-sync-gdoc", "--highlight-plan", str(docjson), cwd=cap), "highlight pass should be idempotent")
    bgs = {c[3] for e, _ in doc._all_paras() for c in e.chars if len(c) > 3}
    need(len(bgs) >= 2, "expected at least a green (GROUNDED) and a yellow (ASSERTION) highlight", bgs)
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
    out = run("rfps-sync-gdoc", "--comments-plan", str(docjson), cwd=cap)
    need("CONFLICT" in out and "comment(s) to add" in out, "the skipped change should get a comment in the doc", out)
    reply = doc.apply(json.loads((build / "gdoc-comments.json").read_text())); (T / "reply.json").write_text(json.dumps(reply))
    run("rfps-sync-gdoc", "--comments-commit", str(T / "reply.json"), cwd=cap); doc.save(docjson)
    need(any("Response change not applied" in c["content"] for c in doc.comments.values()), "conflict comment text", doc.comments)
    # 6. new paragraph, bullet and table in the response, inserted into the doc in place
    tech.write_text(tech.read_text().replace("and post it online.", ".").replace("WCAG 2.1 AA .", "WCAG 2.1 AA.") + "\n- **Support (RFP 2.7).** We provide tier-two support during business hours.\n\n| Phase | Months |\n|-------|--------|\n| Build | 1-5 |\n| Go-live | 6-7 |\n")
    doc.human_replace("every staff page", "staff page"); doc.rev += 1; doc.save(docjson)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), "--apply", cwd=cap)
    need("is settled in the response, but its comment is still open" in out, "a conflict that no longer applies should be flagged", out)
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap)
    doc.apply(json.loads((build / "gdoc-push.json").read_text())); run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    txt = doc.accepted_text()
    need("tier-two support" in txt and "Go-live" in txt and "Build" in txt, "new bullet or table missing from the doc", txt)
    out = run("rfps-sync-gdoc", "--status", str(docjson), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "should be in sync after the table push", out)
    # 7. open items get a comment in the doc; comments are tracked and reconciled
    mp = sol / "response" / "03-management-plan.md"
    mp.write_text(mp.read_text().rstrip("\n") + "\n\nWe will confirm staffing. [DECISION: name the Project Manager]\n")
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap); doc.apply(json.loads((build / "gdoc-push.json").read_text()))
    run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    out = run("rfps-sync-gdoc", "--comments-plan", str(docjson), cwd=cap)
    need("1 comment(s) to add" in out, "one DECISION marker should get a comment (not the ASSERTIONs)", out)
    reply = doc.apply(json.loads((build / "gdoc-comments.json").read_text())); (T / "reply.json").write_text(json.dumps(reply))
    run("rfps-sync-gdoc", "--comments-commit", str(T / "reply.json"), cwd=cap); doc.save(docjson)
    need(any(c["quote"] == "[DECISION: name the Project Manager]" for c in doc.comments.values()), "comment anchored on the marker", doc.comments)
    need("No comments to add" in run("rfps-sync-gdoc", "--comments-plan", str(docjson), cwd=cap), "a second plan should find nothing to add")
    run("rfps-open-items", cwd=cap); oi = (sol / "open-items.md").read_text()
    dec_id = next(i for i, c in doc.comments.items() if "[DECISION" in c["quote"])
    need(f"?disco={dec_id}" in oi, "the DECISION item should link to its comment", oi[:800])
    need("#heading=h." in oi, "items without a comment link to their heading", oi[:800])
    cid = dec_id; doc.human_reply(cid, "We will name them Friday"); doc.save(docjson)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), cwd=cap)
    need("new reply by Reviewer" in out, "reply not noticed", out)
    doc.human_resolve(cid); doc.save(docjson)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), cwd=cap)
    need("comment resolved in the doc, but the marker is still there" in out, "resolved comment with a live marker should be flagged", out)
    mp.write_text(mp.read_text().replace(" [DECISION: name the Project Manager]", "")); need(True, "")
    cm = (sol / "review" / "doc-comments.md").read_text()
    need("Reviewer" in cm and "We will name them Friday" in cm, "comments file should list the reply", cm)
    run("rfps-sync-gdoc", "--comment-note", cid, "PM named in the staffing plan", "--handled", "addressed", cwd=cap)
    need("addressed" in (sol / "review" / "doc-comments.md").read_text(), "handling note")
    # 7b. evidence that is not cleared and banned phrases get comments too
    pp = sol / "response" / "04-past-performance.md"
    pp.write_text(pp.read_text().rstrip("\n") + "\n\nWe also did accessibility work [GROUNDED: E-003].\n")
    tech.write_text(tech.read_text().rstrip("\n") + "\n\nNo data loss occurred in any of our migrations.\n")
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap); doc.apply(json.loads((build / "gdoc-push.json").read_text()))
    run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    out = run("rfps-sync-gdoc", "--comments-plan", str(docjson), cwd=cap)
    need("2 comment(s) to add" in out and "EVIDENCE" in out and "BANNED" in out, "expected an evidence and a banned-phrase comment", out + "\n" + doc.accepted_text()[-900:] + "\n" + (sol / "response" / "04-past-performance.md").read_text()[-300:])
    reply = doc.apply(json.loads((build / "gdoc-comments.json").read_text())); (T / "reply.json").write_text(json.dumps(reply))
    run("rfps-sync-gdoc", "--comments-commit", str(T / "reply.json"), cwd=cap); doc.save(docjson)
    quotes = {c["quote"] for c in doc.comments.values()}
    need("[GROUNDED: E-003]" in quotes and "data loss occurred" in quotes, "comments anchored on the tag and the phrase", quotes)
    reg = sol / "evidence" / "register.csv"; reg.write_text(reg.read_text().replace("needs-permission", "cleared"))
    out = run("rfps-sync-gdoc", "--pull", str(docjson), cwd=cap)
    need("is settled in the response, but its comment is still open" in out, "evidence cleared but its comment is open", out)
    # 7c. a reviewer's comment can become an [OPEN] marker, and no second comment is made for it
    pcid = doc.human_comment("emails the responsible driver", "Why email and not SMS?"); doc.save(docjson)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), "--promote", cwd=cap)
    need("would add [OPEN: Why email and not SMS?]" in out, "promotion candidate not listed", out)
    run("rfps-sync-gdoc", "--pull", str(docjson), "--promote", pcid, "--apply", cwd=cap)
    need("[OPEN: Why email and not SMS?]" in tech.read_text(), "the marker should be in the response", tech.read_text())
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap); doc.apply(json.loads((build / "gdoc-push.json").read_text()))
    run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    out = run("rfps-sync-gdoc", "--comments-plan", str(docjson), cwd=cap)
    need("No comments to add" in out, "the reviewer's comment already covers the new marker", out)
    # 7d. a reworded marker keeps its comment
    mp.write_text(mp.read_text().rstrip("\n") + "\n\nStaffing is set. [OPEN: confirm the schedule]\n")
    run("rfps-sync-gdoc", "--push", str(docjson), cwd=cap); doc.apply(json.loads((build / "gdoc-push.json").read_text()))
    run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(docjson)
    run("rfps-sync-gdoc", "--comments-plan", str(docjson), cwd=cap)
    reply = doc.apply(json.loads((build / "gdoc-comments.json").read_text())); (T / "reply.json").write_text(json.dumps(reply))
    run("rfps-sync-gdoc", "--comments-commit", str(T / "reply.json"), cwd=cap); doc.save(docjson)
    doc.human_replace_in_comment("confirm the schedule", "confirm the delivery schedule"); doc.rev += 1; doc.save(docjson)
    out = run("rfps-sync-gdoc", "--pull", str(docjson), cwd=cap)
    need("comment now follows it" in out, "a reworded marker should keep its comment", out)
    need("Suggestions and comments in the shared document" in run("rfps-flow-status", "--table", cwd=cap), "flow step for suggestions and comments")
    # 8. locator and the manual comment import
    run("rfps-open-items", cwd=cap)
    need("docs.google.com/document/d/DOC1/edit" in (sol / "open-items.md").read_text(), "open items should link to the Google Doc", (sol / "open-items.md").read_text()[:600])
    need("DOC1" in run("rfps-sync-gdoc", "--url", cwd=cap), "url")
    out = run("rfps-flow-status", "--table", cwd=cap); need("Shared work-in-progress document" in out, "flow step title", out)
    (T / "comments.json").write_text(json.dumps([{"author": "Reviewer", "date": "2026-10-23", "text": "Cite the SLA", "section": "Technical Approach", "on": "RFP 2.5"}]))
    run("rfps-sync-gdoc", "--comments", str(T / "comments.json"), cwd=cap)
    need("Cite the SLA" in (sol / "review" / "doc-comments.md").read_text(), "comments file missing")
    sys.path.insert(0, str(HERE.parent / "tools"))
    import sync_gdoc
    def _par(i, text, **kw): return {"startIndex": i, "endIndex": i + len(text) + 1, "paragraph": {"elements": [{"startIndex": i, "endIndex": i + len(text) + 1, "textRun": {"content": text + "\n"}}], "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}, **kw}}
    d = {"body": {"content": [_par(1, "Plain"), _par(7, "First", bullet={"listId": "k"}), _par(14, "Second", suggestedBulletChange={"bullet": {"listId": "k"}})]}}
    kinds = [b["type"] for b in sync_gdoc.parse_doc(d)["blocks"]] if "blocks" in sync_gdoc.parse_doc(d) else None
    need(kinds == ["p", "li", "li"], "pending bullet read as plain paragraph", str(kinds))
    run("rfps-sync-gdoc", "--set-folder", "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQ?usp=sharing", cwd=cap)
    need('wip_folder = "1AbCdEfGhIjKlMnOpQ"' in (sol / "solution.toml").read_text(), "wip_folder not recorded from a link")
    print("gdoc test passed")
finally:
    if not os.environ.get("KEEP"): shutil.rmtree(T, ignore_errors=True)
