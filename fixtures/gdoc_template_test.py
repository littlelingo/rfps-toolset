# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""A template with a cover, boilerplate and two heading levels, as a Google Doc: the template's own text is kept and the response
text arrives after it as suggestions (simulated Docs API; no Google). Usage: uv run fixtures/gdoc_template_test.py
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gdoc_sim

env = {**os.environ, "PATH": f"{HERE.parent / 'bin'}:{os.environ['PATH']}"}
def run(*args, cwd=None):
    r = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode: sys.exit(f"FAIL: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr
def need(cond, msg, ctx=""):
    if not cond: sys.exit(f"FAIL: {msg}\n{ctx}")

T = pathlib.Path(tempfile.mkdtemp()); cap = T / "capture"
try:
    run("uv", "run", "--quiet", str(HERE / "build_sample.py"), str(cap))
    (cap / "05 Draft Response" / "Response Template.docx").unlink()
    run("uv", "run", "--quiet", str(HERE / "build_test_template.py"), str(cap / "05 Draft Response"))
    shutil.move(str(cap / "05 Draft Response" / "Test Response Template.docx"), str(cap / "05 Draft Response" / "Response Template.docx"))
    run("rfps-new-engagement", "--source", str(cap), "--title", "Rich", cwd=cap)
    sol = cap / "active-solution"; build = sol / "build"; dj = T / "doc.json"
    run("rfps-sync-gdoc", "--html", cwd=cap); html = (build / "gdoc-create.html").read_text()
    need("Instructions: limit this section to one page." in html and "Offeror" in html and "<h2>Data Migration</h2>" in html, "the HTML should carry the template's boilerplate, form table and second level", html[:600])
    doc = gdoc_sim.Doc.from_html(html); doc.save(dj)
    out = run("rfps-sync-gdoc", "--init", str(dj), "--doc-id", "DOC1", cwd=cap)
    need("template paragraph(s) under headings are left alone" in out, "template text should be recorded", out)
    out = run("rfps-sync-gdoc", "--status", str(dj), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "a fresh copy of the template is in sync", out)
    out = run("rfps-sync-gdoc", "--style-plan", str(dj), cwd=cap); sp = json.loads((build / "gdoc-style.json").read_text())
    need(sp["header"].startswith("Response to RFP DPW-2026-017") and "Confidential" in sp["footer"], "header and footer text from the Word template", sp["header"] + sp["footer"])
    dsr = next(r["updateDocumentStyle"] for r in sp["requests"] if "updateDocumentStyle" in r)["documentStyle"]
    need(abs(dsr["marginLeft"]["magnitude"] - 54) < 0.1 and abs(dsr["marginTop"]["magnitude"] - 57.6) < 0.1, "margins from the Word template", dsr)
    fams = {r["updateTextStyle"]["textStyle"].get("weightedFontFamily", {}).get("fontFamily") for r in sp["requests"] if "updateTextStyle" in r}
    need({"Arial", "Times New Roman"} <= fams, "heading and body fonts from the Word template", fams)
    md = {"01-executive-summary.md": "# Executive Summary\n\nWe give garage supervisors one portal.\n",
          "02-technical-approach.md": "# Technical Approach\n\nWe build the portal in three parts.\n\n## Scheduling Portal\n\nSupervisors schedule and cancel appointments.\n\n## Data Migration\n\nWe load the legacy history before go-live.\n",
          "03-management-plan.md": "# Management Plan\n\nA Project Manager leads the work.\n",
          "04-past-performance.md": "# Past Performance\n\nTwo relevant references follow.\n"}
    for name, text in md.items(): (sol / "response" / name).write_text(text)
    run("rfps-sync-gdoc", "--push", str(dj), cwd=cap); doc.apply(json.loads((build / "gdoc-push.json").read_text()))
    run("rfps-sync-gdoc", "--commit", cwd=cap); doc.save(dj)
    txt = doc.accepted_text()
    for must in ("Instructions: limit this section to one page.", "Instructions: address each scope item by number.", "Offeror | Example Bidder LLC", "Instructions: give at least two references.",
                 "We give garage supervisors one portal.", "Supervisors schedule and cancel appointments.", "We load the legacy history before go-live."):
        need(must in txt, f"missing from the doc: {must}", txt)
    need("[text]" not in txt, "placeholders should be replaced by the response text", txt)
    lines = txt.split("\n")
    need(lines.index("Instructions: limit this section to one page.") < lines.index("We give garage supervisors one portal."), "response text goes after the template's boilerplate", txt)
    out = run("rfps-sync-gdoc", "--status", str(dj), cwd=cap)
    need("0 section(s) with response changes to push, 0 with edits" in out, "in sync after the push", out)
    print("gdoc template test passed")
finally:
    if not os.environ.get("KEEP"): shutil.rmtree(T, ignore_errors=True)
