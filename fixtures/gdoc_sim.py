"""A small stand-in for the Google Docs API, enough to test rfps-sync-gdoc without Google.

It keeps a document as paragraphs of characters (each with suggestion flags) and tables, applies the update_doc requests
the tool writes (insertText, deleteContentRange, insertTable, updateParagraphStyle, createParagraphBullets,
deleteParagraphBullets, updateTextStyle) with Docs' index rules, supports writeMode SUGGEST (suggested insertions and
deletions stay in the index space) and requiredRevisionId, and prints the same read_doc JSON shape the tool reads.
It is not Google: real documents have more structure. Live behavior still needs a run with the Docs connector.
"""
import html as _html, json, re, sys

class Para:
    def __init__(self, text="", style="NORMAL_TEXT", bullet=None, ins=False):
        self.chars = [[c, ins, False] for c in text] + [["\n", ins, False]]
        self.style, self.bullet = style, bullet
    def length(self): return sum(2 if ord(c[0]) > 0xFFFF else 1 for c in self.chars)

class Table:
    def __init__(self, rows, cols):
        self.cells = [[[Para()] for _ in range(cols)] for _ in range(rows)]
    def length(self):
        R, C = len(self.cells), len(self.cells[0])
        return 2 + R * (2 * C + 1) + sum(p.length() - 1 for row in self.cells for cell in row for p in cell)

class Doc:
    def __init__(self, doc_id="DOC1"):
        self.id, self.rev, self.els, self.sug, self.hid = doc_id, 1, [], 0, 0
        self.comments, self.ncomment = {}, 0

    # ----- creation from the HTML the tool writes -----
    @classmethod
    def from_html(cls, text, doc_id="DOC1"):
        d = cls(doc_id)
        strip = lambda t: _html.unescape(re.sub(r"<[^>]+>", "", t))
        for m in re.finditer(r"<h(\d)>(.*?)</h\1>|<p>(.*?)</p>|<(ul|ol)>(.*?)</\4>|<table[^>]*>(.*?)</table>", text, re.S):
            if m.group(1): d.els.append(Para(strip(m.group(2)), f"HEADING_{m.group(1)}"))
            elif m.group(3) is not None: d.els.append(Para(strip(m.group(3))))
            elif m.group(4):
                for li in re.findall(r"<li>(.*?)</li>", m.group(5), re.S): d.els.append(Para(strip(li), bullet=m.group(4)))
            else:
                rows = [re.findall(r"<td>(.*?)</td>", r, re.S) for r in re.findall(r"<tr>(.*?)</tr>", m.group(6), re.S)]
                t = Table(len(rows), max(len(r) for r in rows))
                for i, r in enumerate(rows):
                    for j, c in enumerate(r): t.cells[i][j] = [Para(strip(c))]
                d.els.append(t)
        return d

    # ----- reading -----
    def _spans(self):
        pos, out = 1, []
        for e in self.els:
            n = e.length(); out.append((e, pos, pos + n)); pos += n
        return out
    def read(self):
        content = [{"endIndex": 1, "sectionBreak": {}}]
        for e, s, z in self._spans():
            if isinstance(e, Para): content.append(self._par_json(e, s))
            else:
                rows, p = [], s + 1
                for r in e.cells:
                    rs = p; cells = []; p += 1
                    for cell in r:
                        cs = p; p += 1; cont = []
                        for par in cell: cont.append(self._par_json(par, p)); p += par.length()
                        cells.append({"startIndex": cs, "endIndex": p, "content": cont})
                    rows.append({"startIndex": rs, "endIndex": p, "tableCells": cells})
                content.append({"startIndex": s, "endIndex": z, "table": {"rows": len(e.cells), "columns": len(e.cells[0]), "tableRows": rows}})
        tab = {"tabProperties": {"tabId": "t.0"}, "documentTab": {"body": {"content": content}}}
        out = {"documentId": self.id, "revisionId": f"rev{self.rev}", "tabs": [tab]}
        if self.comments:
            anchors, lst = {}, []
            for cid, c in self.comments.items():
                rng = self._find_quote(c["quote"])
                anchors[c["anchor"]] = {"anchorId": c["anchor"], "ranges": [rng] if rng else []}
                head = {"author": {"displayName": c["author"]}, "content": c["content"], "createTime": c["created"], "postId": cid}
                lst.append({"commentId": cid, "anchorId": c["anchor"], "headPost": head, "plainTextQuote": c["quote"], "status": c["status"],
                            "replies": [{"author": {"displayName": r[0]}, "content": r[1], "createTime": "2026-10-24T16:00:00Z"} for r in c["replies"]]})
            out["comments"] = lst; tab["documentTab"]["commentAnchors"] = anchors
        return out
    def _find_quote(self, quote):
        for e, s, z in self._spans():
            if isinstance(e, Para):
                t = "".join(c[0] for c in e.chars)
                if quote in t: a = t.index(quote); return {"startIndex": s + a, "endIndex": s + a + len(quote)}
        return None
    def _par_json(self, p, start):
        els, pos, run = [], start, None
        for ch, ins, dele in p.chars:
            w = 2 if ord(ch) > 0xFFFF else 1
            if run is None or (run["ins"], run["del"]) != (ins, dele): run = {"ins": ins, "del": dele, "text": "", "s": pos}; els.append(run)
            run["text"] += ch; run["e"] = pos + w; pos += w
        out = []
        for r in els:
            tr = {"content": r["text"]}
            if r["ins"]: tr["suggestedInsertionIds"] = ["s.1"]
            if r["del"]: tr["suggestedDeletionIds"] = ["s.1"]
            out.append({"startIndex": r["s"], "endIndex": r["e"], "textRun": tr})
        ps = {"namedStyleType": p.style}
        if p.style.startswith("HEADING_"): ps["headingId"] = "h." + re.sub(r"\W", "", "".join(c[0] for c in p.chars)[:12]).lower()
        j = {"startIndex": start, "endIndex": start + p.length(), "paragraph": {"elements": out, "paragraphStyle": ps}}
        if p.bullet: j["paragraph"]["bullet"] = {"listId": "kix.1", **({"glyphType": "DECIMAL"} if p.bullet == "ol" else {})}
        return j

    # ----- writing -----
    def _locate(self, idx):
        for e, s, z in self._spans():
            if isinstance(e, Para) and s <= idx < z: return e, idx - s, None
        raise ValueError(f"index {idx} is not inside a paragraph")
    def _offset(self, p, k):   # character position of UTF-16 offset k
        n = 0
        for i, c in enumerate(p.chars):
            if n >= k: return i
            n += 2 if ord(c[0]) > 0xFFFF else 1
        return len(p.chars)
    def insert_text(self, idx, text, suggest):
        p, k, _ = self._locate(idx); at = self._offset(p, k)
        new = [[c, suggest, False] for c in text]
        chars = p.chars[:at] + new + p.chars[at:]
        # split at newlines
        parts, cur = [], []
        for c in chars:
            cur.append(c)
            if c[0] == "\n": parts.append(cur); cur = []
        pos = self.els.index(p); first = True; made = []
        for part in parts:
            q = Para(); q.chars = part; q.style, q.bullet = p.style, p.bullet; made.append(q)
        self.els[pos:pos + 1] = made
    def delete_range(self, a, b, suggest):
        # tables: exact element range
        for e, s, z in self._spans():
            if not isinstance(e, Para) and a <= s and z <= b:
                if suggest: raise ValueError("suggested table deletion not simulated")
                self.els.remove(e); return
        pos = 1; i = 0; merge_next = False
        spans = self._spans()
        for idx, (e, s, z) in enumerate(spans):
            if not isinstance(e, Para): continue
            lo, hi = max(a, s), min(b, z)
            if lo >= hi: continue
            c0, c1 = self._offset(e, lo - s), self._offset(e, hi - s)
            if suggest:
                for c in e.chars[c0:c1]: c[2] = True
            else:
                had_nl = any(c[0] == "\n" for c in e.chars[c0:c1]); del e.chars[c0:c1]
                if had_nl:
                    nxt = next((x for x, _, _ in spans[idx + 1:] if isinstance(x, Para)), None)
                    if nxt is not None and self.els.index(nxt) == self.els.index(e) + 1:
                        nxt.chars = e.chars + nxt.chars; self.els.remove(e)
        self.els = [e for e in self.els if not (isinstance(e, Para) and not e.chars)]
    def paragraphs_in(self, a, b):
        return [e for e, s, z in self._spans() if isinstance(e, Para) and s < b and z > a]
    def insert_table(self, idx, rows, cols):
        p, k, _ = self._locate(idx); at = self._offset(p, k)
        head = Para(); head.chars = p.chars[:at] + [["\n", False, False]]; head.style, head.bullet = p.style, p.bullet
        tail = Para(); tail.chars = p.chars[at:]; tail.style, tail.bullet = "NORMAL_TEXT", None
        pos = self.els.index(p); self.els[pos:pos + 1] = [head, Table(rows, cols), tail]
    def apply(self, args):
        wc = args.get("writeControl", {})
        if wc.get("requiredRevisionId") and wc["requiredRevisionId"] != f"rev{self.rev}":
            raise ValueError(f"400: required revision ID {wc['requiredRevisionId']} does not match rev{self.rev}")
        suggest = wc.get("writeMode") == "SUGGEST"; api = []
        for r in args["requests"]:
            k, v = next(iter(r.items()))
            if k == "insertComment":
                self.ncomment += 1; cid = f"doco.SIM{self.ncomment}"; a, z = v["range"]["startIndex"], v["range"]["endIndex"]
                quote = next((("".join(c[0] for c in e.chars))[self._offset(e, a - s):self._offset(e, z - s)] for e, s, zz in self._spans() if isinstance(e, Para) and s <= a < zz), "")
                self.comments[cid] = dict(anchor=f"kix.sim{self.ncomment}", quote=quote, status="OPEN", author="Clint Little", content=v["content"], created="2026-10-24T15:00:00Z", replies=[])
                api.append({"insertComment": {"commentThread": {"anchorId": f"kix.sim{self.ncomment}", "commentId": cid, "plainTextQuote": quote, "status": "OPEN",
                           "headPost": {"author": {"displayName": "Clint Little"}, "content": v["content"], "createTime": "2026-10-24T15:00:00Z"}}}})
                continue
            api.append({})
            if k == "insertText":
                idx = v["location"]["index"]
                # cell paragraphs: find in tables too
                if not self._in_table_cell(idx, v["text"], suggest): self.insert_text(idx, v["text"], suggest)
            elif k == "deleteContentRange": self.delete_range(v["range"]["startIndex"], v["range"]["endIndex"], suggest)
            elif k == "insertTable": self.insert_table(v["location"]["index"], v["rows"], v["columns"])
            elif k == "updateParagraphStyle":
                for p in self.paragraphs_in(v["range"]["startIndex"], v["range"]["endIndex"]): p.style = v["paragraphStyle"]["namedStyleType"]
            elif k == "createParagraphBullets":
                for p in self.paragraphs_in(v["range"]["startIndex"], v["range"]["endIndex"]): p.bullet = "ol" if v["bulletPreset"].startswith("NUMBERED") else "ul"
            elif k == "deleteParagraphBullets":
                for p in self.paragraphs_in(v["range"]["startIndex"], v["range"]["endIndex"]): p.bullet = None
            elif k == "updateTextStyle": pass
            else: raise ValueError(f"request not simulated: {k}")
        self.rev += 1
        return {"replies": [{"api_replies": api, "errors": [], "warnings": []}]}
    def _in_table_cell(self, idx, text, suggest):
        for e, s, z in self._spans():
            if isinstance(e, Table) and s <= idx < z:
                p = s + 1
                for r in e.cells:
                    p += 1
                    for cell in r:
                        p += 1
                        for par in cell:
                            if p <= idx < p + par.length():
                                at = self._offset(par, idx - p); par.chars[at:at] = [[c, suggest, False] for c in text]; return True
                            p += par.length()
        return False

    # ----- helpers for tests: what a person does in the doc -----
    def human_replace(self, old, new):
        for e, _, _ in self._spans():
            if isinstance(e, Para):
                t = "".join(c[0] for c in e.chars)
                if old in t:
                    a = t.index(old); e.chars[a:a + len(old)] = [[c, False, False] for c in new]; return
        raise ValueError(old)
    def human_delete_para(self, contains):
        for e, _, _ in self._spans():
            if isinstance(e, Para) and contains in "".join(c[0] for c in e.chars): self.els.remove(e); return
        raise ValueError(contains)
    def human_insert_after(self, contains, text):
        for e, _, _ in self._spans():
            if isinstance(e, Para) and contains in "".join(c[0] for c in e.chars):
                self.els.insert(self.els.index(e) + 1, Para(text, e.style if e.style == "NORMAL_TEXT" else "NORMAL_TEXT", e.bullet)); return
        raise ValueError(contains)
    def human_comment(self, quote, text, author="Reviewer"):
        self.ncomment += 1; cid = f"doco.SIM{self.ncomment}"
        self.comments[cid] = dict(anchor=f"kix.sim{self.ncomment}", quote=quote, status="OPEN", author=author, content=text, created="2026-10-24T16:00:00Z", replies=[]); return cid
    def human_reply(self, cid, text, author="Reviewer"): self.comments[cid]["replies"].append((author, text))
    def human_resolve(self, cid): self.comments[cid]["status"] = "RESOLVED"
    def accepted_text(self):
        out = []
        for e, _, _ in self._spans():
            if isinstance(e, Para):
                t = "".join(c[0] for c in e.chars if not c[2]).strip()
                if t: out.append(t)
            else:
                for row in e.cells:
                    out.append(" | ".join("".join(c[0] for par in cell for c in par.chars if not c[2]).strip() for cell in row))
        return "\n".join(out)
    def save(self, path): open(path, "w").write(json.dumps(self.read()))

if __name__ == "__main__":
    # usage: gdoc_sim.py create HTML OUT.json | read STATE.json OUT.json | apply STATE.json ARGS.json
    cmd = sys.argv[1]
    import pickle
    if cmd == "create": d = Doc.from_html(open(sys.argv[2]).read()); d.save(sys.argv[3])
