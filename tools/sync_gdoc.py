# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Keep a shared Google Doc in step with response/*.md: push approved changes as suggestions, bring edits back.

This tool never talks to Google. Claude does, through the Google connectors, and uses this tool to do the careful
parts: build the document, work out which words changed, compute the index positions Google needs, and plan which
edits are safe. The loop for every operation is: Claude reads the doc with the Docs connector (read_doc) and saves
the JSON to a file; this tool reads that file and prints or writes what to do next; Claude sends it; this tool
records the result.

Usage (DOC.json is a saved read_doc result):
  rfps-sync-gdoc --html                          HTML for the first version of the doc, for Drive create_file (text/html)
  rfps-sync-gdoc --init DOC.json --doc-id ID     record the new doc: snapshot, heading links; write style requests (build/gdoc-style.json)
  rfps-sync-gdoc --status DOC.json               per section: response changes to push, edits made in the doc
  rfps-sync-gdoc --push DOC.json [--direct]      write the update_doc arguments to build/gdoc-push.json (suggestions unless --direct)
  rfps-sync-gdoc --commit                        after Claude sent the push successfully: record it as synced
  rfps-sync-gdoc --pull DOC.json [--apply] [--sections "A;B"]   edits others made, for approval; --apply writes response/*.md
  rfps-sync-gdoc --comments FILE                 write review/doc-comments.md from [{author, date, text, section, on}]
  rfps-sync-gdoc --url                           print the doc link
The doc must keep the response headings exactly; every section's text lives under its heading.
"""
import argparse, datetime, html, json, os, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import docx
import build_response as br
import sync_core

PH_FALLBACK = {"[text]", "text", "[insert table or graphic]"}
SUGGEST = {"writeMode": "SUGGEST"}

def u16(s): return len(s.encode("utf-16-le")) // 2

# ---------- markdown -> plain block texts (what the doc should contain) ----------

def plain_inline(text):
    out = []
    parts = br.TAG_RE.split(text); tags = br.TAG_RE.findall(text)
    for i, part in enumerate(parts):
        for tok in br.INLINE.split(part):
            if not tok: continue
            if tok.startswith("**") and tok.endswith("**"): out.append(tok[2:-2])
            elif tok.startswith("`") and tok.endswith("`"): out.append(tok[1:-1])
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2: out.append(tok[1:-1])
            else: out.append(tok)
        if i < len(tags): out.append(tags[i])
    return " ".join("".join(out).split())

def render_md(text):
    """-> [(kind, plain text, ordered)] one per block; kind 'p', 'li' or 'tbl'. Tables are rows joined by \\x1e, cells by \\x1f."""
    out = []
    for kind, payload in br.blocks(text):
        if kind == "table":
            rows = [r for r in payload if not re.match(r"^\|\s*:?-{2,}", r)]
            cells = [[plain_inline(c.strip()) for c in r.strip().strip("|").split("|")] for r in rows]
            out.append(("tbl", "\x1e".join("\x1f".join(r) for r in cells), False))
        elif kind == "li":
            m = re.match(r"^(-|\d+\.) (.*)$", payload)
            out.append(("li", plain_inline(m.group(2)), m.group(1) != "-"))
        else:
            out.append(("p", plain_inline(payload), False))
    return out

# ---------- reading a saved read_doc result ----------

def _tab_body(doc, tab=None):
    if "tabs" not in doc: return doc["body"], None
    flat = []
    def walk(ts):
        for t in ts:
            flat.append(t); walk(t.get("childTabs", []))
    walk(doc["tabs"])
    t = next((x for x in flat if x["tabProperties"]["tabId"] == tab), flat[0]) if tab else flat[0]
    return t["documentTab"]["body"], t["tabProperties"]["tabId"]

def _words(par):
    """Accepted-view words of a paragraph: [(text, start, end)] in document index space (pending deletions skipped)."""
    words, cur = [], None
    for e in par.get("elements", []):
        tr = e.get("textRun")
        if not tr or tr.get("suggestedDeletionIds"): continue
        idx = e["startIndex"]
        for ch in tr["content"]:
            w = 2 if ord(ch) > 0xFFFF else 1
            if ch.isspace():
                cur = None
            else:
                if cur is None: cur = [ch, idx, idx + w]; words.append(cur)
                else: cur[0] += ch; cur[2] = idx + w
            idx += w
    return [tuple(w) for w in words]

def parse_doc(doc, scaffold_texts=(), tab=None):
    """-> dict(revision, tab, blocks, sections). blocks: every heading/paragraph/table in order with positions.
    sections: title -> {'heading': block, 'blocks': content blocks after it (scaffold and blank lines excluded)}."""
    body, tab_id = _tab_body(doc, tab)
    content = body["content"]; scaffold = {" ".join(t.split()) for t in scaffold_texts}
    last = max((n for n, el in enumerate(content) if "paragraph" in el or "table" in el), default=-1)
    blocks = []
    for n, el in enumerate(content):
        base = dict(start=el.get("startIndex", 0), end=el["endIndex"] if "endIndex" in el else 0, content_index=n,
                    prev_end=content[n - 1].get("endIndex") if n else None,
                    next_is_table=n + 1 < len(content) and "table" in content[n + 1], is_last=n == last)
        if "paragraph" in el:
            par = el["paragraph"]; ws = _words(par); text = " ".join(w[0] for w in ws)
            if not ws: continue
            style = par.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
            if style.startswith("HEADING_"):
                blocks.append(dict(base, type="heading", text=text, level=int(style[-1]), heading_id=par["paragraphStyle"].get("headingId", ""), words=ws))
            elif style == "SUBTITLE" or text in scaffold:
                blocks.append(dict(base, type="scaffold", text=text, words=ws))
            else:
                blocks.append(dict(base, type="li" if par.get("bullet") else "p", text=text, words=ws,
                                   ordered="glyphType" in str(par.get("bullet", {}))))
        elif "table" in el:
            rows = []
            for r in el["table"]["tableRows"]:
                if r.get("tableRowStyle", {}).get("suggestedDeletionIds") or r.get("suggestedDeletionIds"): continue
                cells = [" ".join(" ".join(w[0] for w in _words(c["paragraph"])) for c in cell["content"] if "paragraph" in c and _words(c["paragraph"])) for cell in r["tableCells"]]
                rows.append("\x1f".join(cells))
            if rows: blocks.append(dict(base, type="tbl", text="\x1e".join(rows)))
    sections, cur = {}, None
    for b in blocks:
        if b["type"] == "heading": cur = sections.setdefault(b["text"], dict(heading=b, blocks=[]))
        elif cur is not None and b["type"] != "scaffold": cur["blocks"].append(b)
    return dict(revision=doc.get("revisionId", ""), tab=tab_id, doc_id=doc.get("documentId", ""), blocks=blocks, sections=sections)

# ---------- creating the doc ----------

def _inline_html(text):
    out = []
    parts = br.TAG_RE.split(text); tags = br.TAG_RE.findall(text)
    for i, part in enumerate(parts):
        for tok in br.INLINE.split(part):
            if not tok: continue
            if tok.startswith("**") and tok.endswith("**"): out.append(f"<b>{html.escape(tok[2:-2])}</b>")
            elif tok.startswith("`") and tok.endswith("`"): out.append(html.escape(tok[1:-1]))
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2: out.append(f"<i>{html.escape(tok[1:-1])}</i>")
            else: out.append(html.escape(tok))
        if i < len(tags): out.append(html.escape(tags[i]))
    return "".join(out)

def md_html(text):
    out, items = [], []
    def flush():
        nonlocal items
        if items:
            tag = "ol" if items[0][1] else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_inline_html(t)}</li>" for t, _ in items) + f"</{tag}>"); items = []
    for kind, payload in br.blocks(text):
        if kind == "li":
            m = re.match(r"^(-|\d+\.) (.*)$", payload); items.append((m.group(2), m.group(1) != "-")); continue
        flush()
        if kind == "table":
            rows = [r for r in payload if not re.match(r"^\|\s*:?-{2,}", r)]
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            out.append("<table border=\"1\">" + "".join("<tr>" + "".join(f"<td>{'<b>' if i == 0 else ''}{_inline_html(c)}{'</b>' if i == 0 else ''}</td>" for c in r) + "</tr>" for i, r in enumerate(cells)) + "</table>")
        else:
            out.append(f"<p>{_inline_html(payload)}</p>")
    flush()
    return "\n".join(out)

def template_outline(e):
    """[(level, title, [scaffold lines])] in template order, plus the placeholder text used for empty sections."""
    tcfg = e["tcfg"]; prefix = tcfg.get("heading_prefix", "Heading"); scaf = set(tcfg.get("scaffold_styles", ["Subtitle"]))
    d = docx.Document(e["template"]); out = []
    for p in d.paragraphs:
        sn = p.style.name
        if sn.startswith(prefix):
            m = re.search(r"(\d+)$", sn); out.append([int(m.group(1)) if m else 1, p.text.strip(), []])
        elif sn in scaf and out and p.text.strip(): out[-1][2].append(p.text.strip())
    return [tuple(x) for x in out]

def build_html(e, resp):
    parts = ["<html><body>"]
    for level, title, scaffold in template_outline(e):
        parts.append(f"<h{min(level, 6)}>{html.escape(title)}</h{min(level, 6)}>")
        for s in scaffold: parts.append(f"<p><i>{html.escape(s)}</i></p>")
        text = resp.get(title, [1, "", False])[1]
        parts.append(md_html(text) if text.strip() else "<p>[text]</p>")
    parts.append("</body></html>")
    return "\n".join(parts)

# ---------- planning edits ----------

def _sect_new(text, snap_texts):
    """Rendered markdown for a section; empty text over a placeholder-only section changes nothing."""
    r = render_md(text) if text.strip() else []
    if not text.strip():
        return ([], list(snap_texts)) if all(t.lower() in PH_FALLBACK or t.lower() in br.PH for t in snap_texts) else ([], [])
    return r, [t for _, t, _ in r]

def _word_edit(block, new_text):
    """[(position, requests)] changing only the words that differ in one paragraph, last change first so earlier positions hold."""
    import difflib
    ws = block["words"]; ow = [w[0] for w in ws]; nw = new_text.split(); acts = []
    for tag, i1, i2, j1, j2 in reversed(difflib.SequenceMatcher(None, ow, nw, autojunk=False).get_opcodes()):
        if tag == "equal": continue
        ins = " ".join(nw[j1:j2]); reqs = []
        if tag == "delete":
            if i2 < len(ws): a, b = ws[i1][1], ws[i2][1]
            elif i1 > 0: a, b = ws[i1 - 1][2], ws[i2 - 1][2]
            else: a, b = ws[i1][1], ws[i2 - 1][2]
            reqs.append({"deleteContentRange": {"range": {"startIndex": a, "endIndex": b}}}); pos = a
        elif tag == "insert":
            if i1 < len(ws): pos, txt = ws[i1][1], ins + " "
            else: pos, txt = ws[-1][2], " " + ins
            reqs.append({"insertText": {"location": {"index": pos}, "text": txt}})
        else:   # replace: remove exactly the old words, put the new words where they started
            a, b = ws[i1][1], ws[i2 - 1][2]; pos = a
            reqs.append({"deleteContentRange": {"range": {"startIndex": a, "endIndex": b}}})
            reqs.append({"insertText": {"location": {"index": a}, "text": ins}})
        acts.append((pos, reqs))
    return acts

def _delete_block(b):
    if b["type"] == "tbl": return b["start"], [{"deleteContentRange": {"range": {"startIndex": b["start"], "endIndex": b["end"]}}}]
    a, z = b["start"], b["end"]
    if b["is_last"] and b["prev_end"] is not None: a, z = b["prev_end"] - 1, b["end"] - 1
    elif b["next_is_table"]: z = b["end"] - 1
    return a, [{"deleteContentRange": {"range": {"startIndex": a, "endIndex": z}}}]

def _insert_blocks(anchor, news, after_list):
    """(position, requests) inserting rendered blocks [(kind, text, ordered)] after a block (or a heading/scaffold paragraph).
    After a table, text goes in front of the paragraph that follows it; otherwise a new paragraph starts after the anchor's text."""
    before_next = anchor["type"] == "tbl"
    ptr = anchor["end"] if before_next else anchor["end"] - 1
    pos0 = ptr; fill_empty = False; reqs = []; prev_li = after_list
    for kind, text, ordered in news:
        if kind == "tbl":
            rows = [r.split("\x1f") for r in text.split("\x1e")]; R, C = len(rows), max(len(r) for r in rows)
            reqs.append({"insertTable": {"location": {"index": ptr}, "rows": R, "columns": C}})
            cells = []
            for r in range(R):
                for c in range(C):
                    t = rows[r][c] if c < len(rows[r]) else ""
                    if t: cells.append((ptr + 4 + r * (2 * C + 1) + 2 * c, t))
            for at, t in sorted(cells, reverse=True): reqs.append({"insertText": {"location": {"index": at}, "text": t}})
            ptr = ptr + 3 + R * (2 * C + 1) + sum(u16(t) for _, t in cells)
            fill_empty = True; prev_li = False; continue
        if before_next:
            start = ptr; reqs.append({"insertText": {"location": {"index": ptr}, "text": text + "\n"}})
        elif fill_empty:
            start = ptr; reqs.append({"insertText": {"location": {"index": ptr}, "text": text}})
        else:
            start = ptr + 1; reqs.append({"insertText": {"location": {"index": ptr}, "text": "\n" + text}})
        rng = {"startIndex": start, "endIndex": start + u16(text) + 1}
        if kind == "li":
            reqs.append({"createParagraphBullets": {"range": rng, "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN" if ordered else "BULLET_DISC_CIRCLE_SQUARE"}})
        else:
            reqs.append({"updateParagraphStyle": {"range": rng, "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"}, "fields": "namedStyleType"}})
            if prev_li or before_next: reqs.append({"deleteParagraphBullets": {"range": rng}})
        reqs.append({"updateTextStyle": {"range": {"startIndex": start, "endIndex": start + u16(text)}, "textStyle": {}, "fields": "bold,italic"}})
        ptr = start + u16(text) + (1 if before_next else 0); fill_empty = False; prev_li = kind == "li"
    return pos0, reqs

def plan_section(title, text, sec, snap):
    """-> (actions [(position, requests)], conflicts, result, drift) for one section of a parsed doc."""
    cur = sec["blocks"]; cur_texts = [b["text"] for b in cur]
    snap = snap if snap is not None else cur_texts
    news, new_texts = _sect_new(text, snap)
    ops, conflicts, result, drift = sync_core.plan(snap, cur_texts, new_texts)
    actions = []
    anchor_default = sec["heading"]
    for op in ops:
        olds = [cur[i] for i in op["cur"]]; new = [news[j] for j in op["new"]] if news else []
        if op["kind"] == "replace" and len(olds) == len(new) and all(o["type"] in ("p", "li") and n[0] in ("p", "li") and o["type"] == n[0] for o, n in zip(olds, new)):
            for o, n in zip(olds, new): actions += _word_edit(o, n[1])
            continue
        for o in olds: actions.append(_delete_block(o))
        if news and op["new"]:
            anchor = olds[-1] if olds else (cur[op["after"]] if op["after"] is not None else None)
            if anchor is None: anchor = sec.get("scaffold_last") or anchor_default
            actions.append(_insert_blocks(anchor, new, anchor["type"] == "li"))
    return actions, conflicts, result, drift

# ---------- state ----------

def state_file(sol): return sol / ".state" / "gdoc-sync.json"
def load_state(sol):
    f = state_file(sol); return json.loads(f.read_text()) if f.is_file() else {}
def save_state(sol, st):
    f = state_file(sol); f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n")
def doc_url(st, heading=None):
    u = f"https://docs.google.com/document/d/{st['doc_id']}/edit"
    hid = st.get("heading_ids", {}).get(heading) if heading else None
    return u + (f"#heading={hid}" if hid else "")

def summary(sol):
    """For the flow, from the last sync only (the doc itself can only be read by Claude through the connector):
    {'exists', 'md_ahead', 'synced', 'url'}."""
    st = load_state(sol)
    if not st.get("doc_id"): return dict(exists=False)
    e = br.load_engagement(str(sol)); resp, order = br.parse_response(e["response"]); ahead = 0
    for t in order:
        if resp[t][2] or t not in st.get("sections", {}): continue
        snap = st["sections"][t]; _, new = _sect_new(resp[t][1], snap)
        if [sync_core.key(x) for x in new] != [sync_core.key(x) for x in snap]: ahead += 1
    return dict(exists=True, md_ahead=ahead, synced=st.get("synced", ""), url=doc_url(st))

def scaffold_of(e): return [s for _, _, ss in template_outline(e) for s in ss]

def load_doc(path, e):
    return parse_doc(json.loads(pathlib.Path(path).read_text()), scaffold_of(e))

def sections_for(parsed, resp, order):
    probs = [f"response heading not in the doc: {h}" for h in order if h not in parsed["sections"]]
    return probs

# ---------- operations ----------

def op_init(sol, e, doc_path, doc_id):
    parsed = load_doc(doc_path, e); resp, order = br.parse_response(e["response"])
    st = dict(doc_id=doc_id or parsed["doc_id"], revision=parsed["revision"], sections={t: [b["text"] for b in s["blocks"]] for t, s in parsed["sections"].items() if t in resp},
              heading_ids={t: s["heading"].get("heading_id", "") for t, s in parsed["sections"].items()}, synced=datetime.datetime.now().isoformat(timespec="seconds"))
    save_state(sol, st)
    sty = [{"updateParagraphStyle": {"range": {"startIndex": b["start"], "endIndex": b["end"]}, "paragraphStyle": {"namedStyleType": "SUBTITLE"}, "fields": "namedStyleType"}}
           for b in parsed["blocks"] if b["type"] == "scaffold" and b["text"] in {" ".join(t.split()) for t in scaffold_of(e)}]
    out = pathlib.Path(e["out"]); out.mkdir(parents=True, exist_ok=True)
    (out / "gdoc-style.json").write_text(json.dumps({"documentId": st["doc_id"], "requests": sorted(sty, key=lambda r: -r["updateParagraphStyle"]["range"]["startIndex"]),
                                                  "writeControl": {"requiredRevisionId": parsed["revision"]}}, indent=1))
    print(f"Recorded {doc_url(st)} ({len(st['sections'])} sections). Optional: apply build/gdoc-style.json with update_doc to mark the template's evaluation lines as Subtitle ({len(sty)} paragraph(s)).")

def analyse(sol, e, doc_path, st):
    parsed = load_doc(doc_path, e); resp, order = br.parse_response(e["response"])
    probs = sections_for(parsed, resp, order); rows = []
    for title in order:
        if title not in parsed["sections"] or resp[title][2]: continue
        rows.append((title, parsed["sections"][title]))
    return parsed, resp, probs, rows

def op_status(sol, e, doc_path, st):
    parsed, resp, probs, rows = analyse(sol, e, doc_path, st)
    if probs: print("Heading mismatch:\n  " + "\n  ".join(probs))
    n_md = n_doc = 0; print(f"Google Doc: {doc_url(st)}")
    for title, sec in rows:
        acts, conflicts, _, drift = plan_section(title, resp[title][1], sec, st["sections"].get(title))
        notes = []
        if acts or conflicts: notes.append(f"response ahead: {len(acts)} edit(s) to push" + (f", {len(conflicts)} blocked" if conflicts else "")); n_md += 1
        if drift: notes.append(f"edited in the doc: {len(drift)} block(s) not in the response yet (rfps-sync-gdoc --pull)"); n_doc += 1
        print(f"  {'✓' if not notes else '•'} {title}" + (": " + "; ".join(notes) if notes else ": in sync"))
        for c in conflicts: print(f"      conflict: {c}")
    print(f"{n_md} section(s) with response changes to push, {n_doc} with edits made in the doc.")

def op_push(sol, e, doc_path, st, direct):
    parsed, resp, probs, rows = analyse(sol, e, doc_path, st)
    if probs: sys.exit("Heading mismatch (headings must match exactly):\n  " + "\n  ".join(probs))
    actions, pending, nconf, notes = [], dict(st["sections"]), 0, []
    for title, sec in rows:
        acts, conflicts, result, _ = plan_section(title, resp[title][1], sec, st["sections"].get(title))
        if acts: actions += acts; pending[title] = result; notes.append(f"  {title}: {len(acts)} edit(s)")
        elif not conflicts and st["sections"].get(title) is None: pending[title] = [b["text"] for b in sec["blocks"]]
        nconf += len(conflicts)
        for c in conflicts: notes.append(f"      conflict (left pending): {c}")
    reqs = [r for _, rs in sorted(actions, key=lambda a: -a[0]) for r in rs]
    out = pathlib.Path(e["out"]); out.mkdir(parents=True, exist_ok=True)
    wc = {"requiredRevisionId": parsed["revision"]}
    if not direct: wc = {**SUGGEST, **wc}
    f = out / "gdoc-push.json"
    if reqs:
        f.write_text(json.dumps({"documentId": st["doc_id"], "requests": reqs, "writeControl": wc}, indent=1))
        save_state(sol, {**st, "pending": dict(sections=pending, revision=parsed["revision"])})
    elif f.exists(): f.unlink()
    print(f"{len(reqs)} request(s) in {len(actions)} edit(s) for {sum(1 for t,_ in rows)} section(s) checked; {nconf} conflict(s) skipped." + (f" Mode: {'direct edits' if direct else 'suggestions'}." if reqs else ""))
    print("\n".join(notes) if notes else "  Nothing to push: the doc already matches the response text.")
    if reqs: print(f"Send {f} with update_doc, then run rfps-sync-gdoc --commit.")

def op_commit(sol, st, revision):
    pend = st.get("pending")
    if not pend: sys.exit("Nothing pending to commit (run --push first).")
    st = {k: v for k, v in st.items() if k != "pending"}; st["sections"] = pend["sections"]
    if revision: st["revision"] = revision
    st["synced"] = datetime.datetime.now().isoformat(timespec="seconds"); save_state(sol, st)
    print("Recorded the push as synced.")

def op_pull(sol, e, doc_path, st, apply, only):
    import difflib  # noqa: F401
    parsed, resp, probs, rows = analyse(sol, e, doc_path, st)
    if probs: sys.exit("Heading mismatch (headings must match exactly):\n  " + "\n  ".join(probs))
    import sync_docx as sd
    secs = sd.md_sections(e["response"]); files = {}; new_sections = dict(st["sections"])
    report, edits_by_file, nprops, nconf = [], {}, 0, 0
    for title, sec in rows:
        if only and title not in only: continue
        msec = secs.get(title)
        if not msec: continue
        lines = files.setdefault(msec["path"], msec["path"].read_text().split("\n"))
        cur_texts = [b["text"] for b in sec["blocks"]]; kinds = [b["type"] if b["type"] != "tbl" else "tbl" for b in sec["blocks"]]
        snap = st["sections"].get(title); snap = snap if snap is not None else cur_texts
        props, edits, conflicts, result = sync_core.pull_edits(title, resp[title][1], snap, cur_texts, kinds, msec, lines,
                                                              lambda t: _sect_new(t, snap)[1], lambda t: t.lower() in PH_FALLBACK or t.lower() in br.PH)
        if not props and not conflicts: continue
        report.append(f"## {title}")
        for pr in props:
            nprops += 1
            report.append(f"- {pr['kind']}:" + (f"\n    was: {pr['old'][:160]}" if pr["old"] else "") + (f"\n    now: {pr['new'][:160]}" if pr["new"] else "\n    now: (removed)"))
            if pr["removed"]: report.append(f"    markers removed in the doc: {'; '.join(t[:80] for t in pr['removed'])}")
            if pr["added"]: report.append(f"    markers added in the doc: {'; '.join(t[:80] for t in pr['added'])}")
            if pr["simplified"]: report.append("    note: some bold or italic formatting in this paragraph was simplified")
        for c in conflicts: report.append(f"- conflict: {c}"); nconf += 1
        if apply and edits: edits_by_file.setdefault(msec["path"], []).extend(edits); new_sections[title] = result
    print(f"Doc edits not yet in the response: {nprops} change(s) in {sum(1 for x in report if x.startswith('## '))} section(s); {nconf} conflict(s).")
    print("\n".join(report) if report else "Nothing to bring in: the response already has everything in the doc.")
    if not apply: return
    for f, edits in edits_by_file.items():
        lines = files[f]
        for a, b, new in sorted(edits, key=lambda x: (x[0], x[1]), reverse=True): lines[a:b] = new
        f.write_text("\n".join(lines))
    st = {**st, "sections": new_sections, "revision": parsed["revision"], "synced": datetime.datetime.now().isoformat(timespec="seconds")}
    save_state(sol, st)
    print(f"Applied {nprops} change(s) to {len(edits_by_file)} response file(s). Run rfps-open-items --mark if markers changed, then rfps-sync-gdoc --status.")

def op_comments(sol, path):
    comments = json.loads(pathlib.Path(path).read_text()); import sync_docx as sd
    st = load_state(sol); seen = set(st.get("comments_seen", []))
    for i, c in enumerate(comments): c.setdefault("id", str(i))
    f = sd.write_comments(sol, comments, seen)
    save_state(sol, {**st, "comments_seen": [str(c["id"]) for c in comments]})
    print(f"{len(comments)} comment(s) -> {f}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--html", action="store_true"); ap.add_argument("--init"); ap.add_argument("--doc-id")
    ap.add_argument("--status"); ap.add_argument("--push"); ap.add_argument("--direct", action="store_true")
    ap.add_argument("--commit", action="store_true"); ap.add_argument("--revision")
    ap.add_argument("--pull"); ap.add_argument("--apply", action="store_true"); ap.add_argument("--sections")
    ap.add_argument("--comments"); ap.add_argument("--url", action="store_true")
    ap.add_argument("--solution", nargs="?", const="", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); e = br.load_engagement(str(sol)); st = load_state(sol)
    br.HP[0] = e["tcfg"].get("heading_prefix", "Heading"); br.SCAF.clear(); br.SCAF.update(e["tcfg"].get("scaffold_styles", ["Subtitle"]))
    br.PH.clear(); br.PH.update(x.lower() for x in e["tcfg"].get("placeholders", []))
    if a.html:
        resp, _ = br.parse_response(e["response"]); h = build_html(e, resp)
        out = pathlib.Path(e["out"]); out.mkdir(parents=True, exist_ok=True); (out / "gdoc-create.html").write_text(h)
        print(f"Wrote {out / 'gdoc-create.html'} ({len(h):,} characters). Send it to Drive create_file with contentMimeType text/html, then read the new doc with read_doc and run --init.")
        sys.exit(0)
    if a.init: op_init(sol, e, a.init, a.doc_id); sys.exit(0)
    if a.comments: op_comments(sol, a.comments); sys.exit(0)
    if not st.get("doc_id"): sys.exit("No Google Doc recorded yet. Run --html, create the doc, then --init DOC.json --doc-id ID.")
    if a.url: print(doc_url(st)); sys.exit(0)
    if a.commit: op_commit(sol, st, a.revision); sys.exit(0)
    if a.status: op_status(sol, e, a.status, st)
    elif a.push: op_push(sol, e, a.push, st, a.direct)
    elif a.pull: op_pull(sol, e, a.pull, st, a.apply, set(x.strip() for x in a.sections.split(";")) if a.sections else None)
    else: ap.print_help()
