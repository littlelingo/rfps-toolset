# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Pour the markdown response text into the response .docx.

Two modes:
  wip    (default) Keep the Work Order and evaluation scaffold lines under each heading and replace
         only the [text] placeholders. Internal markers are shown highlighted.
  final  Write a NEW finished copy: scaffold lines removed, omitted headings removed, grounded and
         assertion markers stripped. Refuses if unresolved markers or placeholders remain (use
         --force to write anyway).

Evidence checks (optional, with --register): every [GROUNDED: E-nnn] tag must cite an ID in the
register; WIP warns, FINAL refuses if a cited ID is unknown, superseded, or not marked "cleared", or if the
tag cites no ID. Banned phrases (retired figures, non-public details, wrong names) come from the register's ban_phrases column and are checked the same way.

The template .docx is never modified. WIP output goes to the build dir; FINAL is also copied to final_copy_dir if configured.
"""
import argparse, csv, re, sys, pathlib, tomllib
import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

TAGS = r"GROUNDED|ASSERTION|EVIDENCE NEEDED|DECISION|OPEN|SOLUTIONING"
ICONS = "\U0001F7E1\U0001F534\U0001F7E0\U0001F7E3\U0001F7E2"   # optional scan icon before a marker; see rfps-open-items
TAG_RE = re.compile(r"(?:[%s]\uFE0F?[ \t]*)?\[(?:%s)[^\]]*\]" % (ICONS, TAGS), re.S)
STRIP_TAGS = ("GROUNDED", "ASSERTION")
STRICT = {"ref": False}   # set by load_engagement from solution.toml require_approval_ref: a cleared row must also record where the approval is
COLORS = {"GROUNDED": WD_COLOR_INDEX.BRIGHT_GREEN, "ASSERTION": WD_COLOR_INDEX.YELLOW}
INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)")


def load_register(path):
    rows = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows[r["id"].strip()] = r
    return rows

def deny_from_register(reg):
    """Banned phrases come from the register's ban_phrases column (separated by ';'); they apply to every row."""
    out = []
    for i, r in reg.items():
        for ph in (r.get("ban_phrases") or "").split(";"):
            if ph.strip(): out.append((ph.strip(), f"{i}: {(r.get('claim') or '')[:70]}"))
    return out

def check_evidence(resp, register, deny):
    """-> dict with warnings/errors lists and stats. resp maps heading -> [level, text, omit]."""
    res = {"issues": [], "cited": {}, "uncited": [], "deny": [], "unused": []}
    for h, (lvl, text, omit) in resp.items():
        if omit: continue
        for m in re.finditer(r"\[GROUNDED:([^\]]*)\]", text):
            ids = re.findall(r"E-\d+", m.group(1))
            if not ids:
                res["uncited"].append((h, m.group(0)[:70])); continue
            for i in ids:
                res["cited"].setdefault(i, set()).add(h)
        if deny:
            low = text.lower()
            for phrase, reason in deny:
                if phrase.lower() in low:
                    res["deny"].append((h, phrase, reason))
    if register is not None:
        for i, hs in sorted(res["cited"].items()):
            r = register.get(i)
            where = "; ".join(sorted(hs))[:90]
            if r is None: res["issues"].append(f"{i}: cited but not in the register ({where})"); continue
            c = (r.get("clearance") or "").strip()
            if r.get("superseded_by", "").strip(): res["issues"].append(f"{i}: superseded by {r['superseded_by'].strip()} ({where})")
            if c != "cleared": res["issues"].append(f"{i}: clearance is '{c}' ({where}); {r.get('notes','').strip()[:100]}")
            elif STRICT["ref"] and not (r.get("approval_ref") or "").strip(): res["issues"].append(f"{i}: cleared, but approval_ref records no proof of the client's or owner's approval ({where})")
        res["unused"] = [i for i, r in register.items() if i not in res["cited"] and not (r.get("ban_phrases") or "").strip() and (r.get("clearance") or "").strip() in ("cleared", "needs-permission")]
    return res

def parse_response(folder):
    """-> {heading: (level, text, omit)} from every .md in folder, in file order."""
    out, order = {}, []
    for p in sorted(pathlib.Path(folder).glob("*.md")):
        cur = None
        for line in p.read_text().split("\n"):
            m = re.match(r"^(#{1,3}) (.+?)\s*$", line)
            if m:
                cur = m.group(2).strip()
                if cur in out:
                    sys.exit(f"duplicate heading in response files: {cur}")
                out[cur] = [len(m.group(1)), [], False]; order.append(cur)
            elif cur is not None:
                out[cur][1].append(line)
    for h, v in out.items():
        raw = "\n".join(v[1])
        v[2] = bool(re.search(r"<!--\s*omit", raw))
        raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
        v[1] = raw.strip("\n")
    return out, order

def blocks(text):
    """Split markdown text into ('p'|'li'|'table', payload) blocks."""
    res, para, table = [], [], []
    def flush():
        nonlocal para, table
        if para: res.append(("p", " ".join(x.strip() for x in para))); para = []
        if table: res.append(("table", table)); table = []
    for line in text.split("\n"):
        if not line.strip(): flush(); continue
        if line.lstrip().startswith("|"):
            if para: flush()
            table.append(line.strip()); continue
        if table: flush()
        if re.match(r"^\s*(-|\d+\.) ", line):
            flush(); res.append(("li", line.strip())); continue
        if res and res[-1][0] == "li" and line.startswith("  "):
            res[-1] = ("li", res[-1][1] + " " + line.strip()); continue
        para.append(line)
    flush()
    return res

def add_runs(par, text, mode, found):
    """Add inline-formatted runs; handle internal markers per mode."""
    # protect markers from inline parsing
    parts = TAG_RE.split(text); tags = TAG_RE.findall(text)
    seq = []
    for i, part in enumerate(parts):
        seq.append(("t", part))
        if i < len(tags): seq.append(("tag", tags[i]))
    for kind, val in seq:
        if kind == "tag":
            name = re.search(r"\[([A-Z ]+)", val).group(1).strip()
            if mode == "final" and name in STRIP_TAGS:
                found["stripped"] += 1
                # remove one preceding space already emitted
                if par.runs and par.runs[-1].text.endswith(" "):
                    par.runs[-1].text = par.runs[-1].text[:-1]
                continue
            if mode == "final": found["unresolved"].append(val[:80])
            r = par.add_run(val)
            r.font.highlight_color = COLORS.get(name, WD_COLOR_INDEX.PINK)
            continue
        for tok in INLINE.split(val):
            if not tok: continue
            if tok.startswith("**") and tok.endswith("**"): r = par.add_run(tok[2:-2]); r.bold = True
            elif tok.startswith("`") and tok.endswith("`"): r = par.add_run(tok[1:-1])
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2: r = par.add_run(tok[1:-1]); r.italic = True
            else: r = par.add_run(tok)
    if mode == "final":
        for m in re.finditer(r"\[[^\]\n]{2,}\]", par.text):
            found["unresolved"].append(m.group(0)[:80])

def make_table(doc, rows, mode, found):
    rows = [r for r in rows if not re.match(r"^\|\s*:?-{2,}", r)]
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    ncol = max(len(r) for r in cells)
    t = doc.add_table(rows=len(cells), cols=ncol)
    tblPr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "808080"); borders.append(e)
    tblPr.append(borders)
    for i, row in enumerate(cells):
        for j in range(ncol):
            c = t.cell(i, j); p = c.paragraphs[0]
            txt = row[j] if j < len(row) else ""
            add_runs(p, txt, mode, found)
            for r in p.runs:
                r.font.size = Pt(9)
                if i == 0: r.bold = True
    return t._tbl

def make_elements(doc, text, mode, found):
    els = []
    for kind, payload in blocks(text):
        if kind == "table":
            els.append(make_table(doc, payload, mode, found))
            continue
        p = doc.add_paragraph()
        if kind == "li":
            m = re.match(r"^(-|\d+\.) (.*)$", payload)
            lead = "• " if m.group(1) == "-" else m.group(1) + " "
            p.paragraph_format.left_indent = Inches(0.3); p.paragraph_format.first_line_indent = Inches(-0.2)
            p.add_run(lead)
            add_runs(p, m.group(2), mode, found)
        else:
            add_runs(p, payload, mode, found)
        els.append(p._p)
    return els

HP = ["Heading"]; SCAF = {"Subtitle"}; PH = set()

def load_defaults():
    return tomllib.loads((pathlib.Path(__file__).resolve().parent / "defaults.toml").read_text())

def is_heading(p): return p.style.name.startswith(HP[0])
def hlevel(p): return int(p.style.name.split()[-1])

def pages_text(words):
    """'about 3 pages' when the low and high estimates round to the same number, else 'about 3 to 4 pages'."""
    lo, hi = round(words / 550), round(words / 450)
    return f"about {lo} pages" if lo == hi else f"about {lo} to {hi} pages"

def build(template, response, out, mode, name, force, register=None, final_copy=None, tcfg=None):
    tcfg = tcfg or load_defaults()["docx"]
    HP[0] = tcfg.get("heading_prefix", "Heading"); SCAF.clear(); SCAF.update(tcfg.get("scaffold_styles", ["Subtitle"]))
    PH.clear(); PH.update(x.lower() for x in tcfg.get("placeholders", []))
    resp, order = parse_response(response)
    d = docx.Document(template)
    paras = [p for p in d.paragraphs]
    heads = [(i, p) for i, p in enumerate(paras) if is_heading(p)]
    doc_heads = [p.text.strip() for _, p in heads]
    problems = []
    for h in order:
        if h not in doc_heads: problems.append(f"response heading not in docx: {h}")
    for h in doc_heads:
        if h not in resp: problems.append(f"docx heading missing from response files: {h}")
    if problems:
        sys.exit("Heading mismatch (headings must match exactly):\n  " + "\n  ".join(problems))
    found = {"stripped": 0, "unresolved": []}
    regd = load_register(register) if register else None
    ev = check_evidence(resp, regd, deny_from_register(regd) if regd else None)
    poured, empty, removed = [], [], []
    # map paragraph element -> index ranges
    for n, (i, hp) in enumerate(heads):
        title = hp.text.strip(); level, text, omit = resp[title]
        end = heads[n + 1][0] if n + 1 < len(heads) else len(paras)
        rng = paras[i + 1:end]
        placeholders = [p for p in rng if p.style.name not in SCAF and p.text.strip().lower() in PH]
        scaffold = [p for p in rng if p.style.name in SCAF]
        has_children = n + 1 < len(heads) and hlevel(heads[n + 1][1]) > hlevel(hp)
        if omit:
            if mode == "final":
                for p in [hp] + rng: p._p.getparent().remove(p._p)
                removed.append(title); continue
            continue
        if text.strip():
            if placeholders: anchor = placeholders[0]._p.getprevious()
            elif scaffold: anchor = scaffold[-1]._p
            else: anchor = hp._p
            els = make_elements(d, text, mode, found)
            for el in els:
                anchor.addnext(el); anchor = el
            for p in placeholders: p._p.getparent().remove(p._p)
            poured.append(title)
        else:
            if mode == "final":
                for p in placeholders: p._p.getparent().remove(p._p)
                if not has_children: empty.append(title)
    if mode == "final":
        for p in list(d.paragraphs):
            if p.style.name in SCAF: p._p.getparent().remove(p._p)
    # word estimate for the response body: from first Heading 1 to end
    started, words = False, 0
    for p in d.paragraphs:
        if is_heading(p) and hlevel(p) == 1: started = True
        if started and p.style.name not in SCAF: words += len(p.text.split())
    for t in d.tables:
        words += sum(len(c.text.split()) for r in t.rows for c in r.cells)
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    suffix = "WIP" if mode == "wip" else "FINAL"
    path = out / f"{name}_{suffix}.docx"
    errors = []
    if mode == "final":
        if empty: errors.append("headings with no content: " + "; ".join(empty))
        if found["unresolved"]: errors.append(f"{len(found['unresolved'])} unresolved marker/placeholder(s): " + "; ".join(sorted(set(found['unresolved']))[:25]))
        errors += [f"evidence: {x}" for x in ev["issues"]]
        errors += [f"evidence: grounded tag cites no register ID in '{h}': {t}" for h, t in ev["uncited"]]
        errors += [f"deny list: '{ph}' in '{h}' ({why})" for h, ph, why in ev["deny"]]
    rep = [f"# Build report ({suffix})", "", f"- Template: `{template}`", f"- Response source: `{response}`",
           f"- Headings poured: {len(poured)} of {len(doc_heads)}", f"- Omitted headings removed: {len(removed)} ({', '.join(removed) or 'none'})",
           f"- Markers stripped: {found['stripped']}",
           f"- Response body words (cover and scaffold excluded): {words:,} ({pages_text(words)} at 450 to 550 words per page; tables and graphics add pages; the State counts graphics inside the response)"]
    if mode == "wip":
        left = [p.text for p in d.paragraphs if p.text.strip().lower() in PH]
        rep.append(f"- Placeholders still in the document: {len(left)}")
        rep.append(f"- Unresolved markers shown highlighted: {len(TAG_RE.findall(chr(10).join(p.text for p in d.paragraphs)))}")
    if register:
        reg = load_register(register); cnt = {}
        for i in ev["cited"]:
            c = (reg.get(i, {}).get("clearance") or "missing").strip(); cnt[c] = cnt.get(c, 0) + 1
        rep.append(""); rep.append("## Evidence")
        rep.append(f"- Register: `{register}` ({len(reg)} rows); distinct IDs cited in the response: {len(ev['cited'])} ({', '.join(f'{k}: {v}' for k, v in sorted(cnt.items())) or 'none'})")
        if mode == "wip":
            for x in ev["issues"]: rep.append(f"- Warning: {x}")
            for h, t in ev["uncited"]: rep.append(f"- Warning: grounded tag cites no register ID in '{h}': {t}")
            for h, ph, why in ev["deny"]: rep.append(f"- Warning: deny-listed phrase '{ph}' in '{h}' ({why})")
        if ev["unused"]: rep.append(f"- Register rows not cited anywhere (new or unused evidence): {', '.join(ev['unused'])}")
    if errors:
        rep.append(""); rep.append("## Blocking" if not force else "## Blocking (written anyway with --force)")
        rep += [f"- {e}" for e in errors]
    (out / f"{name}_{suffix}_report.md").write_text("\n".join(rep) + "\n")
    if errors and not force:
        print("\n".join(rep)); sys.exit(f"\nFINAL not written. Resolve the items above or use --force. Report: {out / (name + '_' + suffix + '_report.md')}")
    d.save(path)
    print("\n".join(rep)); print(f"\nWrote {path}")
    if mode == "final" and final_copy:
        import shutil
        dest = pathlib.Path(final_copy); dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest / path.name); print(f"Copied to {dest / path.name}")

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent

def pointer_path():
    """The active-solution pointer lives in the user's project (current directory), never in the plugin folder."""
    return pathlib.Path.cwd() / ".claude" / "active-solution"

def find_local_solution():
    """A solution folder at or above the current directory (solution.toml here, or active-solution/solution.toml)."""
    here = pathlib.Path.cwd().resolve()
    for p in (here, *here.parents):
        if (p / "solution.toml").is_file(): return p
        if (p / "active-solution" / "solution.toml").is_file(): return p / "active-solution"
    return None

def resolve_solution(arg):
    """Folder holding solution.toml: explicit arg, else a solution found at or above the current directory, else the active-solution pointer file."""
    ptr = pointer_path()
    if arg:
        d = pathlib.Path(arg).expanduser()
    elif find_local_solution():
        d = find_local_solution()
    elif ptr.is_file():
        d = pathlib.Path(ptr.read_text().strip())
    else:
        sys.exit("no solution given and no active solution set (use /rfps:new-engagement or /rfps:use-solution, or run from inside a solution folder)")
    d = d.resolve()
    if (d / "active-solution" / "solution.toml").is_file(): d = d / "active-solution"   # a source folder was given
    if not (d / "solution.toml").is_file(): sys.exit(f"no solution.toml in {d}")
    return d

def load_engagement(path):
    d = resolve_solution(path)
    cfg = tomllib.loads((d / "solution.toml").read_text())
    STRICT["ref"] = bool(cfg.get("require_approval_ref"))
    def rel(v): return str(pathlib.Path(v) if pathlib.Path(v).is_absolute() else (d / v).resolve())
    return dict(template=rel(cfg["template"]), response=rel(cfg.get("response_dir", "response")),
                out=rel(cfg.get("build_dir", "build")), name=cfg.get("output_name", d.name),
                register=rel(cfg["register"]) if cfg.get("register") else None,
                final_copy=rel(cfg["final_copy_dir"]) if cfg.get("final_copy_dir") else None, dir=str(d),
                tcfg={**load_defaults()["docx"], **cfg.get("docx", {})})

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--solution", "--engagement", dest="solution", nargs="?", const="", default=None, help="active-solution folder (or its source folder) containing solution.toml; omit the value to use the active-solution pointer")
    ap.add_argument("--template"); ap.add_argument("--response"); ap.add_argument("--out"); ap.add_argument("--name")
    ap.add_argument("--mode", choices=["wip", "final"], default="wip")
    ap.add_argument("--force", action="store_true", help="write FINAL even if unresolved items remain")
    ap.add_argument("--register", help="evidence register CSV")
    a = ap.parse_args()
    cfg = load_engagement(a.solution) if a.solution is not None else {}
    template = a.template or cfg.get("template"); response = a.response or cfg.get("response")
    out = a.out or cfg.get("out"); name = a.name or cfg.get("name"); register = a.register or cfg.get("register")
    if not (template and response and out and name): sys.exit("need --engagement or --template, --response, --out and --name")
    build(template, response, out, a.mode, name, a.force, register, cfg.get("final_copy"), cfg.get("tcfg"))
