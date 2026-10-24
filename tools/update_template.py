# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Compare the response template's headings with response/*.md after the template changed, and bring the response in line.

Reports headings that are new in the template, renamed (a close match to a heading that disappeared), removed, or moved to
another level. With --apply it adds the new headings to response/ (empty sections, in the template's order) and, with --rename,
renames the markdown headings that were renamed in the template (--rename-all also renames a heading that moved to a new wording in the
same place, which needs a person to confirm). It never deletes text: a removed heading is only reported,
because its text may belong in another section.

Usage: rfps-update-template [--template NEW.docx | --doc DOC.json] [--apply] [--rename] [--rename-all] [--adopt] [--solution <folder>]
  --template  compare this docx instead of the template named in solution.toml
  --doc       compare the headings of a Google Doc (a saved read_doc result) instead; use it when the shared WIP or the Google template changed
  --adopt     with --template: make it the solution's template (rewrites the template line in solution.toml)
"""
import argparse, difflib, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import docx
import build_response as br

def docx_headings(path, tcfg):
    hp = tcfg.get("heading_prefix", "Heading")
    out = []
    for p in docx.Document(str(path)).paragraphs:
        if p.style.name.startswith(hp) and p.text.strip():
            m = re.search(r"(\d+)$", p.style.name); out.append((int(m.group(1)) if m else 1, p.text.strip()))
    return out

def md_headings(rdir):
    out = []
    for f in sorted(pathlib.Path(rdir).glob("*.md")):
        for n, line in enumerate(f.read_text().split("\n")):
            m = re.match(r"^(#{1,3}) (.+?)\s*$", line)
            if m: out.append((len(m.group(1)), m.group(2).strip(), f, n))
    return out

def slug(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

def compare(dh, mh):
    dtitles = [t for _, t in dh]; mtitles = [t for _, t, _, _ in mh]
    new = [t for t in dtitles if t not in mtitles]; gone = [t for t in mtitles if t not in dtitles]
    renamed = []
    for g in list(gone):
        best = max(new, key=lambda n: difflib.SequenceMatcher(None, g.lower(), n.lower()).ratio(), default=None)
        if best and difflib.SequenceMatcher(None, g.lower(), best.lower()).ratio() >= 0.7:
            renamed.append((g, best)); new.remove(best); gone.remove(g)
    possible = []   # different wording but the same place: the neighbours before and after match, and the level is the same
    dl = {t: lv for lv, t in dh}
    for g in list(gone):
        mi = mtitles.index(g); before = next((t for t in reversed(mtitles[:mi]) if t in dtitles), None); after = next((t for t in mtitles[mi + 1:] if t in dtitles), None)
        lo = dtitles.index(before) + 1 if before else 0; hi = dtitles.index(after) if after else len(dtitles)
        cand = [t for t in dtitles[lo:hi] if t in new and dl[t] == next(lv for lv, tt, _, _ in mh if tt == g)]
        if len(cand) == 1: possible.append((g, cand[0])); new.remove(cand[0]); gone.remove(g)
    mlevel = {t: lv for lv, t, _, _ in mh}
    moved = [(t, mlevel[t], lv) for lv, t in dh if t in mlevel and mlevel[t] != lv]
    order_ok = [t for t in dtitles if t in mtitles] == [t for t in mtitles if t in dtitles]
    return new, gone, renamed, possible, moved, order_ok

def add_heading(rdir, dh, title):
    """Add an empty section for a new template heading, next to its neighbours, without renumbering any file."""
    rdir = pathlib.Path(rdir); i = [t for _, t in dh].index(title); lvl = dh[i][0]
    mh = md_headings(rdir); where = {t: (f, n) for _, t, f, n in mh}
    prev = next((t for _, t in reversed(dh[:i]) if t in where), None)
    if lvl == 1:
        base = "00"
        if prev:
            stem = where[prev][0].stem; base = stem.split("-")[0].rstrip("abcdefghijklmnopqrstuvwxyz")
        k = 0
        while True:
            name = f"{base}{'abcdefghijklmnopqrstuvwxyz'[k]}-{slug(title)}.md"
            if not (rdir / name).exists(): break
            k += 1
        (rdir / name).write_text(f"<!-- Response source for the docx. Headings must match the docx exactly. -->\n\n# {title}\n")
        return f"added {name}"
    f, n = where[prev] if prev else (sorted(rdir.glob("*.md"))[0], 0)
    lines = f.read_text().split("\n")
    nxt = next((k for k in range(n + 1, len(lines)) if re.match(r"^#{1,3} ", lines[k])), len(lines))
    lines[nxt:nxt] = [f"{'#' * lvl} {title}", ""]
    f.write_text("\n".join(lines))
    return f"added '{title}' to {f.name}"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template"); ap.add_argument("--doc"); ap.add_argument("--apply", action="store_true"); ap.add_argument("--rename", action="store_true"); ap.add_argument("--rename-all", action="store_true")
    ap.add_argument("--adopt", action="store_true"); ap.add_argument("--solution", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); e = br.load_engagement(str(sol))
    tpl = pathlib.Path(a.template).expanduser().resolve() if a.template else pathlib.Path(e["template"])
    if a.doc:
        import sync_gdoc as sg
        parsed = sg.parse_doc(sg.read_doc_file(a.doc), sg.scaffold_of(e)); tpl = pathlib.Path(a.doc)
        dh = [(b["level"], b["text"]) for b in parsed["blocks"] if b["type"] == "heading"]
    else: dh = docx_headings(tpl, e["tcfg"])
    mh = md_headings(e["response"])
    new, gone, renamed, possible, moved, order_ok = compare(dh, mh)
    print(f"{'Google Doc' if a.doc else 'Template'}: {tpl}\n{len(dh)} headings in the template, {len(mh)} in response/")
    if not (new or gone or renamed or possible or moved) and order_ok: print("Everything matches.")
    for t in new: print(f"  new in the template: {t}")
    for g, n in renamed: print(f"  renamed: '{g}' -> '{n}'" + ("" if a.rename else "  (--rename applies it)"))
    for g, n in possible: print(f"  possibly renamed (same place, different wording): '{g}' -> '{n}'" + ("" if a.rename_all else "  (check it is the same section, then --rename-all)"))
    for t in gone: print(f"  removed from the template (its text stays; move it to another section or drop the heading by hand): {t}")
    for t, o, n in moved: print(f"  level changed: {t} (response has {o}, template has {n}); fix the number of # by hand")
    if not order_ok: print("  the order of the headings differs from the template; response files are read in file-name order")
    if a.apply:
        for g, n in (renamed + (possible if a.rename_all else [])) if (a.rename or a.rename_all) else []:
            f, ln = next((f, k) for _, t, f, k in mh if t == g); lines = f.read_text().split("\n")
            lines[ln] = re.sub(r"^(#{1,3}) .*$", lambda m: f"{m.group(1)} {n}", lines[ln]); f.write_text("\n".join(lines)); print(f"  renamed in {f.name}")
        for t in new: print("  " + add_heading(e["response"], dh, t)); mh = md_headings(e["response"])
        if a.adopt and a.template:
            cfgp = sol / "solution.toml"; s = cfgp.read_text()
            import os
            s = re.sub(r'^template = ".*"$', f'template = "{os.path.relpath(tpl, sol)}"', s, flags=re.M); cfgp.write_text(s); print(f"  solution.toml now uses {tpl}")
        print("Done. A shared WIP document does not change by itself: add or rename those headings in it by hand, or rebuild it (Word: rfps-sync-docx --rebuild).")
    elif new or renamed or possible: print("Nothing was changed. Run again with --apply (and --rename) to bring response/ in line.")
