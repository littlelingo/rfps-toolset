# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""The master Google Doc: a styled, blank copy of a finished Fearless response. Checks the master against the style profile, empties a copy of a finished
response, writes the response template's skeleton into the blank copy in the master's styles, and refuses a WIP without a registered master.
Simulated Docs API; no Google. Usage: uv run fixtures/gdoc_master_test.py
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gdoc_sim

env = {**os.environ, "PATH": f"{HERE.parent / 'bin'}:{os.environ['PATH']}"}
def run(*args, cwd=None, ok=True):
    r = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True)
    if ok and r.returncode: sys.exit(f"FAIL: {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    if not ok and not r.returncode: sys.exit(f"FAIL (should have stopped): {' '.join(args)}\n{r.stdout}")
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
    sol = cap / "active-solution"; build = sol / "build"

    # no master registered: the WIP must not silently fall back to Google's default look
    out = run("rfps-sync-gdoc", "--template-id", cwd=cap, ok=False)
    need("No master Google Doc is registered" in out, "a missing master should be explained", out)

    # the master matches the profile; a changed heading color or a missing page-number field does not
    master = HERE / "fearless-formal-master.json"
    for flags in ([], ["--named-styles"]):
        out = run("rfps-sync-gdoc", "--template-check", str(master), "--profile", "formal", *flags, cwd=cap)
        need("The master matches the profile." in out and "DEVIATES" not in out, f"a doc built to the standard should match the formal profile {flags}", out)
    bad = json.loads(master.read_text()); t = bad["tabs"][0]["documentTab"]
    for s in t["namedStyles"]["styles"]:
        if s["namedStyleType"] == "HEADING_1": s["textStyle"]["foregroundColor"]["color"]["rgbColor"] = {"red": 0, "green": 0, "blue": 1}
    for seg in t["footers"].values():
        for el in seg["content"]:
            for r in el["paragraph"]["elements"]:
                if "autoText" in r: del r["autoText"]
    (T / "bad.json").write_text(json.dumps(bad))
    out = run("rfps-sync-gdoc", "--template-check", str(T / "bad.json"), "--profile", "formal", "--named-styles", cwd=cap, ok=False)
    need("DEVIATES HEADING_1 color" in out and "DEVIATES footer page-number field" in out, "both deviations should be named", out)
    nb = json.loads(master.read_text()); nb["tabs"][0]["documentTab"]["body"]["content"].append(
        {"startIndex": 2, "endIndex": 20, "paragraph": {"elements": [{"startIndex": 2, "endIndex": 20, "textRun": {"content": "Solicitation text\n"}}], "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}}})
    (T / "notblank.json").write_text(json.dumps(nb))
    out = run("rfps-sync-gdoc", "--template-check", str(T / "notblank.json"), "--profile", "formal", cwd=cap, ok=False)
    need("DEVIATES blank body" in out, "a master that still holds text should be refused", out)
    run("rfps-sync-gdoc", "--template-check", str(T / "notblank.json"), "--profile", "formal", "--style-only", cwd=cap)


    # the master can be generated from the profile alone: a .docx whose styles, page setup, first-page rule, header and footer follow the standard
    run("rfps-sync-gdoc", "--master-docx", "--profile", "formal", cwd=cap)
    import docx as _docx
    from docx.shared import Pt
    md = _docx.Document(str(build / "formal-master.docx")); sec = md.sections[0]
    need(md.styles["Normal"].font.name == "Times New Roman" and md.styles["Normal"].font.size == Pt(11), "Normal text follows the profile")
    need(str(md.styles["Heading 1"].font.color.rgb) == "5C3977" and str(md.styles["Heading 2"].font.color.rgb) == "EE5340" and md.styles["Heading 1"].font.bold, "headings follow the profile")
    need(md.styles["Heading 1"].font.name == "Times New Roman", "headings take the Normal font, not the Word theme font")
    need(sec.page_width == Pt(612) and sec.left_margin == Pt(72) and sec.different_first_page_header_footer, "page setup and the first-page rule follow the profile")
    need([p.text for p in sec.header.paragraphs] == ["Company name", "Solicitation title", "Date", "Document type"], "the header carries the placeholder lines")
    need("restriction on the title page" in sec.footer.paragraphs[0].text and "PAGE" in sec.footer._element.xml, "the footer carries the notice and a page-number field")
    run("rfps-sync-gdoc", "--master-docx", "--profile", "nope", cwd=cap, ok=False)

    # the WIP itself is checked against the profile (direct formatting over named styles), so a doc can drift without anyone editing the master
    def para(text, style, **ts): return {"paragraph": {"elements": [{"textRun": {"content": text + "\n", "textStyle": ts}}], "paragraphStyle": {"namedStyleType": style}}}
    wip = json.loads(master.read_text()); wip["tabs"][0]["documentTab"]["body"]["content"] += [para("Technical approach", "HEADING_1"), para("Body text.", "NORMAL_TEXT")]
    (T / "wip-ok.json").write_text(json.dumps(wip)); out = run("rfps-sync-gdoc", "--wip-check", str(T / "wip-ok.json"), "--profile", "formal", cwd=cap)
    need("every checked run follows the profile" in out, "a conforming WIP passes", out)
    wip["tabs"][0]["documentTab"]["body"]["content"] += [para("Drifted heading", "HEADING_1", fontSize={"magnitude": 20, "unit": "PT"}, weightedFontFamily={"fontFamily": "Arial"})]
    (T / "wip-bad.json").write_text(json.dumps(wip)); out = run("rfps-sync-gdoc", "--wip-check", str(T / "wip-bad.json"), "--profile", "formal", cwd=cap, ok=False)
    need("DEVIATES HEADING_1 font" in out and "DEVIATES HEADING_1 size" in out and "Drifted heading" in out, "the drifted heading is named", out)

    # a native Google Doc is made to meet the profile in two sends (no Word file): page setup first, then header and footer text
    fresh = {"documentId": "NEWDOC", "revisionId": "r1", "tabs": [{"tabProperties": {"tabId": "t.0"}, "documentTab": {"documentStyle": {}, "body": {"content": [{"endIndex": 1, "sectionBreak": {}}, {"startIndex": 1, "endIndex": 2, "paragraph": {"elements": [{"startIndex": 1, "endIndex": 2, "textRun": {"content": "\n"}}]}}]}}}]}
    (T / "fresh.json").write_text(json.dumps(fresh))
    run("rfps-sync-gdoc", "--master-plan", str(T / "fresh.json"), "--profile", "formal", cwd=cap)
    m1 = json.loads((build / "gdoc-master-1.json").read_text()); kinds = [next(iter(r)) for r in m1["requests"]]
    ds1 = m1["requests"][0]["updateDocumentStyle"]["documentStyle"]
    need(kinds == ["updateDocumentStyle", "createHeader", "createFooter"] and ds1["useFirstPageHeaderFooter"] is True and ds1["marginLeft"]["magnitude"] == 72 and ds1["pageSize"]["width"]["magnitude"] == 612, "stage 1 sets the page and creates the header and footer", m1)
    need(m1["writeControl"]["writeMode"] == "EDIT", "formatting is a direct edit")
    out = run("rfps-sync-gdoc", "--master-plan", str(T / "fresh.json"), "--stage", "2", cwd=cap, ok=False); need("send stage 1 first" in out, "stage 2 needs the header id", out)
    fresh["tabs"][0]["documentTab"]["documentStyle"] = {"defaultHeaderId": "kix.h1", "defaultFooterId": "kix.f1", "useFirstPageHeaderFooter": True}; (T / "fresh.json").write_text(json.dumps(fresh))
    out = run("rfps-sync-gdoc", "--master-plan", str(T / "fresh.json"), "--stage", "2", cwd=cap); need("page-number field" in out and "named styles" in out, "what the connector cannot do is said", out)
    m2 = json.loads((build / "gdoc-master-2.json").read_text()); ins = [r["insertText"] for r in m2["requests"] if "insertText" in r]
    need(ins[0]["location"] == {"segmentId": "kix.h1", "index": 0} and ins[0]["text"].split("\n") == ["Company name", "Solicitation title", "Date", "Document type"], "header lines go into the header segment", ins)
    need(ins[1]["location"]["segmentId"] == "kix.f1" and "restriction on the title page" in ins[1]["text"] and ins[1]["text"].endswith("Page "), "footer notice and page label go into the footer segment", ins)
    need(any(r.get("updateParagraphStyle", {}).get("paragraphStyle", {}).get("alignment") == "END" for r in m2["requests"]), "the header is right aligned")

    # register the master from a link; the profile is recorded too
    run("rfps-sync-gdoc", "--set-template", "https://docs.google.com/document/d/1AbCdEfGhIjKlMnOpQrStUv/edit?tab=t.0", "--profile", "formal", cwd=cap)
    cfg = (sol / "solution.toml").read_text()
    need('gdoc_template = "1AbCdEfGhIjKlMnOpQrStUv"' in cfg and 'style_profile = "formal"' in cfg, "the master id and profile should be recorded", cfg)
    need(run("rfps-sync-gdoc", "--template-id", cwd=cap).strip() == "1AbCdEfGhIjKlMnOpQrStUv", "the registered master should print")
    run("rfps-sync-gdoc", "--set-template", "x", "--profile", "nope", cwd=cap, ok=False)

    # the shared default master lives in the profile file; a solution with no gdoc_template of its own uses it
    (sol / "solution.toml").write_text("\n".join(l for l in (sol / "solution.toml").read_text().split("\n") if not l.startswith(("gdoc_template", "style_profile"))))
    run("rfps-sync-gdoc", "--template-id", cwd=cap, ok=False)
    prof = HERE.parent / "tools" / "templates" / "styles" / "formal.toml"; before = prof.read_text()
    try:
        run("rfps-sync-gdoc", "--set-default-master", "https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHg/edit", "--profile", "formal", cwd=cap)
        need(run("rfps-sync-gdoc", "--template-id", cwd=cap).strip() == "1ZyXwVuTsRqPoNmLkJiHg", "the profile's shared master should be used")
        import tomllib; need(tomllib.loads(prof.read_text())["page"]["margin"] == 72, "the profile still parses with its tables")
        need("master_fingerprint" in tomllib.loads(prof.read_text()), "the fingerprint is recorded with the master")
        prof.write_text(prof.read_text().replace("margin = 72 ", "margin = 54 "))   # the standard changes; the master was made from the old one
        out = run("rfps-sync-gdoc", "--template-id", cwd=cap, ok=False); need("is stale" in out, "a master made from an older profile is flagged stale", out)
    finally: prof.write_text(before)

    # a copy of a finished response is emptied: the body goes, one Normal paragraph stays
    done = gdoc_sim.Doc.from_html("<h1>Old Section</h1><p>Old solicitation text.</p><table><tr><td>A</td><td>B</td></tr></table><h2>Another</h2><p>More.</p>")
    dj = T / "done.json"; done.save(dj)
    out = run("rfps-sync-gdoc", "--clean-plan", str(dj), cwd=cap); need("deletes the body text" in out and "tables" in out, "the clean plan should say what it removes", out)
    done.apply(json.loads((build / "gdoc-clean.json").read_text()))
    need(done.accepted_text().strip() == "", "the body should be empty after the clean plan", done.accepted_text())
    need(all(e.style == "NORMAL_TEXT" for e in done.els), "the left-over paragraph should be Normal text")

    # the response template's skeleton goes into the blank copy, in the master's styles
    blank = gdoc_sim.Doc("MASTERCOPY"); blank.els = [gdoc_sim.Para("")]; bj = T / "blank.json"; blank.save(bj)
    out = run("rfps-sync-gdoc", "--skeleton-plan", str(bj), cwd=cap); need("table(s) in the response template arrive as rows of text" in out, "tables should be reported", out)
    sk = json.loads((build / "gdoc-skeleton.json").read_text())
    h1 = [r["updateTextStyle"]["textStyle"] for r in sk["requests"] if "updateTextStyle" in r and r["updateTextStyle"]["textStyle"].get("bold") and r["updateTextStyle"]["textStyle"]["foregroundColor"]["color"]["rgbColor"]["red"] > 0.35 and r["updateTextStyle"]["textStyle"]["foregroundColor"]["color"]["rgbColor"]["red"] < 0.37]
    need(h1 and h1[0]["weightedFontFamily"]["fontFamily"] == "Times New Roman" and h1[0]["fontSize"]["magnitude"] == 11, "headings carry the profile's font, size, bold and purple as direct formatting", h1[:1])
    blank.apply(sk)
    styles = {e.chars and "".join(c[0] for c in e.chars).strip(): e.style for e in blank.els if isinstance(e, gdoc_sim.Para)}
    need(styles.get("Technical Approach") == "HEADING_1" and styles.get("Scheduling Portal") == "HEADING_2", "headings should take Heading styles", styles)
    need(styles.get("Evaluation: RFP 2.1 and 2.3.") == "SUBTITLE", "evaluation lines should take the Subtitle (scaffold) style", styles)
    blank.save(bj)
    out = run("rfps-sync-gdoc", "--init", str(bj), "--doc-id", "MASTERCOPY", cwd=cap)
    need("template paragraph(s) under headings are left alone" in out, "the skeleton should be accepted as a WIP start", out)
    out = run("rfps-sync-gdoc", "--skeleton-plan", str(bj), cwd=cap, ok=False)
    need("not blank" in out, "a skeleton must not be written over text", out)
    print("gdoc master test passed")
finally:
    if not os.environ.get("KEEP"): shutil.rmtree(T, ignore_errors=True)
