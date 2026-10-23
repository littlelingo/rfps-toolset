"""Plan changes to a shared WIP document without touching the document itself.

Pure functions over lists of block texts (one string per paragraph or table), so any backend can apply the plan:
the docx backend (sync_docx.py) today, a Google Docs backend later.

  snapshot  block texts at the last sync (what the tool last wrote or read)
  current   block texts in the shared document now (others may have edited it)
  new       block texts the response markdown renders to now

plan() diffs snapshot -> new, maps each affected block to its place in the current document, and returns the
operations that are safe to apply plus the conflicts to report (blocks someone edited in the document that the
response change also touches). Unaffected blocks, including ones others edited, are never touched.
"""
import difflib

def _ratio_free(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False)

def plan(snapshot, current, new):
    """-> (ops, conflicts, result, drift).

    ops        list of dicts: {"kind": "insert"|"delete"|"replace", "cur": [indexes into current to delete/replace],
               "after": index into current to insert after (None = start of section), "new": [indexes into new]}
    conflicts  list of strings describing changes that were skipped
    result     the snapshot after the applied ops (skipped changes stay as they were, so a later push retries them)
    drift      indexes into snapshot that no longer match the document (edited or removed by someone else)
    """
    match = {}
    for tag, i1, i2, j1, j2 in _ratio_free([key(t) for t in snapshot], [key(t) for t in current]).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1): match[i1 + k] = j1 + k
    drift = [i for i in range(len(snapshot)) if i not in match]
    ops, conflicts, result = [], [], []
    for tag, i1, i2, j1, j2 in _ratio_free([key(t) for t in snapshot], [key(t) for t in new]).get_opcodes():
        if tag == "equal":
            result += snapshot[i1:i2]; continue
        old, add = list(range(i1, i2)), list(range(j1, j2))
        label = f"{'; '.join(snapshot[i][:50] for i in old) or 'start of section'}"
        if tag == "insert":
            if i1 > 0 and (i1 - 1) not in match:
                conflicts.append(f"cannot place new text after a block edited in the document: {snapshot[i1 - 1][:60]}")
                continue
            ops.append({"kind": "insert", "cur": [], "after": match[i1 - 1] if i1 > 0 else None, "new": add})
            result += [new[j] for j in add]; continue
        gone = [i for i in old if i not in match]
        if gone:
            conflicts.append(f"edited in the document, so the response change was not applied: {label}")
            result += snapshot[i1:i2]; continue
        ops.append({"kind": "delete" if tag == "delete" else "replace", "cur": [match[i] for i in old],
                    "after": match[old[-1]], "new": add})
        result += [new[j] for j in add]
    return ops, conflicts, result, drift


# ---------- reading changes back (pull) ----------
import re

LIST_PREFIX = re.compile(r"^(-|\d+\.) ")

def key(text):
    """Comparison key: a leading bullet glyph does not count as a change (a Word list renders it, not the text)."""
    return text[2:] if text.startswith("• ") else text

def strip_md(tok):
    """What a markdown word renders as: no bold, italic or code marks."""
    t = tok.replace("**", "").replace("`", "")
    if len(t) > 2 and t.startswith("*") and t.endswith("*"): t = t[1:-1]
    return t

def merge_text(old_md, old_rendered, new_rendered):
    """New markdown for a paragraph someone edited: unchanged words keep their original markdown (bold, tags),
    changed words come from the document as plain text. Returns (markdown, formatting_simplified)."""
    m = LIST_PREFIX.match(old_md)
    prefix, body = (m.group(0), old_md[m.end():]) if m else ("", old_md)
    old_rend = key(old_rendered).split(); new_words = key(new_rendered).split()
    toks = [(t, strip_md(t)) for t in body.split()]
    toks = [(t, r) for t, r in toks if r]
    if [r for _, r in toks] != old_rend:   # markdown does not round-trip to what was rendered: fall back to plain text
        return prefix + " ".join(new_words), True
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_rend, new_words, autojunk=False).get_opcodes():
        if tag == "equal": out += [t for t, _ in toks[i1:i2]]
        elif tag in ("replace", "insert"): out += new_words[j1:j2]
    text = " ".join(out)
    if text.count("**") % 2: return prefix + " ".join(new_words), True
    return prefix + text, False

def table_md(text):
    """Markdown table lines from a block's accepted text (rows joined by \\x1e, cells by \\x1f)."""
    rows = [r.split("\x1f") for r in text.split("\x1e")]
    n = max(len(r) for r in rows)
    lines = ["| " + " | ".join(c.replace("|", "/") for c in r + [""] * (n - len(r))) + " |" for r in rows]
    return [lines[0], "|" + "|".join(["---"] * n) + "|"] + lines[1:]

def block_md(kind, text):
    """Markdown lines for a block read from the document (kind: 'p', 'li' or 'tbl')."""
    if kind == "tbl": return table_md(text)
    if kind == "li": return ["- " + key(text)]
    return [text]

def md_blocks(lines):
    """Block spans of a section body: [{'kind', 'text', 'start', 'end'}] with line indexes (end inclusive).
    Splits exactly as build_response.blocks() does; lines inside HTML comments are ignored."""
    res, para, table = [], [], []
    def flush():
        nonlocal para, table
        if para:
            res.append({"kind": "p", "text": " ".join(x.strip() for _, x in para), "start": para[0][0], "end": para[-1][0]}); para = []
        if table:
            res.append({"kind": "table", "text": [x for _, x in table], "start": table[0][0], "end": table[-1][0]}); table = []
    in_comment = False
    for n, line in enumerate(lines):
        if in_comment or line.lstrip().startswith("<!--"):
            in_comment = "-->" not in line
            flush(); continue
        if not line.strip(): flush(); continue
        if line.lstrip().startswith("|"):
            if para: flush()
            table.append((n, line.strip())); continue
        if table: flush()
        if re.match(r"^\s*(-|\d+\.) ", line):
            flush(); res.append({"kind": "li", "text": line.strip(), "start": n, "end": n}); continue
        if res and res[-1]["kind"] == "li" and line.startswith("  ") and res[-1]["end"] == n - 1:
            res[-1]["text"] += " " + line.strip(); res[-1]["end"] = n; continue
        para.append((n, line))
    flush()
    return res

def plan_pull(snap, cur, mdnew):
    """Changes made in the document since the last sync, mapped onto the response markdown.

    snap / cur / mdnew: block texts at the last sync / in the document now / rendered from the markdown now.
    -> (changes, conflicts, result). Each change: {'kind': insert|delete|replace, 'snap': (i1, i2), 'cur': (j1, j2),
    'md': [markdown block indexes to replace], 'after_md': markdown block index to insert after (None = start)}.
    A change is a conflict when the markdown also changed those blocks since the last sync.
    result is the snapshot after the applied changes."""
    sk, ck, mk = [key(t) for t in snap], [key(t) for t in cur], [key(t) for t in mdnew]
    md_of = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sk, mk, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1): md_of[i1 + k] = j1 + k
    changes, conflicts, result = [], [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sk, ck, autojunk=False).get_opcodes():
        if tag == "equal":
            result += snap[i1:i2]; continue
        old = list(range(i1, i2))
        label = "; ".join(snap[i][:50] for i in old) or "new text"
        if any(i not in md_of for i in old):
            conflicts.append(f"changed in both the document and the response, not brought in: {label}")
            result += snap[i1:i2]; continue
        if tag == "insert":
            if i1 > 0 and (i1 - 1) not in md_of:
                conflicts.append(f"new text in the document follows a block the response also changed, not brought in: {cur[j1][:60]}")
                continue
            changes.append({"kind": "insert", "snap": (i1, i2), "cur": (j1, j2), "md": [], "after_md": md_of[i1 - 1] if i1 > 0 else None})
        else:
            changes.append({"kind": "delete" if tag == "delete" else "replace", "snap": (i1, i2), "cur": (j1, j2),
                            "md": [md_of[i] for i in old], "after_md": md_of[old[-1]]})
        result += cur[j1:j2]
    return changes, conflicts, result


TAG_RE = re.compile(r"(?:[\U0001F7E1\U0001F534\U0001F7E0\U0001F7E3]\uFE0F?[ \t]*)?\[(?:GROUNDED|ASSERTION|EVIDENCE NEEDED|DECISION|OPEN|SOLUTIONING)[^\]]*\]", re.S)

def _tags(text): return [t.strip() for t in TAG_RE.findall(text)]

def pull_edits(title, text, snap, cur_texts, kinds, sec, lines, render_md, is_placeholder):
    """Edits made in a shared document, as proposals and edits to a section of the response markdown.
    snap/cur_texts/kinds: block texts at the last sync / in the document now / their kinds ('p', 'li', 'tbl').
    sec: {'body': (first line, end line)} of the section in the markdown file whose lines are `lines`.
    render_md(text) -> the block texts the markdown renders to. -> (proposals, edits, conflicts, result);
    edits are (start, end, new lines) on the markdown file."""
    b0, b1 = sec["body"]; mblocks = md_blocks(lines[b0:b1])
    for b in mblocks: b["start"] += b0; b["end"] += b0
    if not text.strip():                       # empty section: the document's real text fills it
        real = [k for k, t in enumerate(cur_texts) if not is_placeholder(t)]
        if not real or [t for t in snap if not is_placeholder(t)]: return [], [], [], snap
        blocks_md = [block_md(kinds[k], cur_texts[k]) for k in real]
        return ([dict(kind="insert", old="", new="\n".join("\n".join(b) for b in blocks_md), removed=[], added=[], simplified=False)],
                [(b0, b0, [""] + [x for k, b in enumerate(blocks_md) for x in (b + [""])])], [], cur_texts)
    mdnew = render_md(text)
    if len(mdnew) != len(mblocks): return [], [], [f"could not align the markdown blocks with the rendered text ({len(mblocks)} vs {len(mdnew)})"], snap
    changes, conflicts, result = plan_pull(snap, cur_texts, mdnew)
    proposals, edits = [], []
    for c in changes:
        olds = [mblocks[m] for m in c["md"]]
        if len(olds) > 1 and any(c["md"][k + 1] != c["md"][k] + 1 for k in range(len(olds) - 1)):
            conflicts.append("the response has other text between these blocks; not brought in: " + "; ".join(snap[i][:40] for i in range(*c["snap"])))
            continue
        js = list(range(*c["cur"])); old_txt = " ".join(o["text"] if isinstance(o["text"], str) else " ".join(o["text"]) for o in olds)
        simplified = False
        paired = c["kind"] == "replace" and len(olds) == len(js) and all(
            olds[k]["kind"] in ("p", "li") and kinds[j] in ("p", "li") or (olds[k]["kind"] == "table" and kinds[j] == "tbl") for k, j in enumerate(js))
        if paired:
            new_lines = []
            for k, j in enumerate(js):
                if kinds[j] == "tbl": nl = table_md(cur_texts[j])
                else:
                    merged, simp = merge_text(olds[k]["text"], snap[c["snap"][0] + k], cur_texts[j]); nl = [merged]; simplified |= simp
                edits.append((olds[k]["start"], olds[k]["end"] + 1, nl)); new_lines += nl
        else:
            blocks_md = [block_md(kinds[j], cur_texts[j]) for j in js]
            new_lines = [x for b in blocks_md for x in b]
            body = []
            for k, b in enumerate(blocks_md):
                if k and not (kinds[js[k]] == "li" == kinds[js[k - 1]]): body.append("")
                body += b
            if c["kind"] == "insert":
                if c["after_md"] is None:
                    pos = mblocks[0]["start"] if mblocks else b0
                    edits.append((pos, pos, body + [""]))
                else:
                    prev = mblocks[c["after_md"]]
                    glue = [] if (prev["kind"] == "li" and kinds[js[0]] == "li") else [""]
                    edits.append((prev["end"] + 1, prev["end"] + 1, glue + body))
            else:
                edits.append((olds[0]["start"], olds[-1]["end"] + 1, body))
        new_txt = " ".join(new_lines)
        old_t, new_t = _tags(old_txt), _tags(new_txt)
        proposals.append(dict(kind=c["kind"], old=old_txt, new=new_txt, removed=[t for t in old_t if t not in new_t],
                              added=[t for t in new_t if t not in old_t], simplified=simplified))
    return proposals, edits, conflicts, result

