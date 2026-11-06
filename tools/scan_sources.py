# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "pypdf", "openpyxl", "python-pptx"]
# ///
"""Scan the past-performance sources for new or changed files, extract their text, and write a digest.

Reads past-performance/sources.toml. Local sources are scanned here; files are read in place and never copied, only their
extracted text is kept under .state/text/past-performance/<label>/. A Google Drive source (type = "drive", path = the folder id)
is listed by Claude through the Drive connector and compared here; nothing is downloaded until the user confirms.
Writes past-performance/digest.md: per file its status, size, the years, amounts and permission wording it mentions, and a
snippet, so evidence rows can be proposed from it. The digest proposes nothing itself.

Usage: rfps-scan-sources                                   scan local sources, extract new and changed files, rebuild the digest
       rfps-scan-sources --drive LABEL --listing FILE      compare a Drive folder listing (JSON list of {id, title, mimeType, modifiedTime, size}
                                                           saved from the connector, one entry per file AND per subfolder, with "path" = its folder path and "listed": true on a
                                                           folder once its contents are in the list) with the last scan; writes the pending list;
                                                           reports subfolders not yet listed and shortcuts to resolve
       rfps-scan-sources --drive LABEL --ingest            after Claude saved each pending file's text as
                                                           .state/text/past-performance/LABEL/<id>.txt, record them as scanned
       rfps-scan-sources --text-dir [LABEL]                print the folder where extracted text is kept (cache_dir in solution.toml, else .state/)
       rfps-scan-sources --digest                          rebuild the digest only
"""
import argparse, collections, datetime, hashlib, json, os, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import solution_dir as sd
import build_response as br
import add_source as asrc
import extract_docs as ex

SUFFIXES = set(ex.H)
NATIVE = {".gdoc", ".gsheet", ".gslides"}   # Google Drive for Desktop shows Google-format files as small pointers that only the connector can read
MOUNT = re.compile(r"CloudStorage/GoogleDrive|/Google Drive/")

def state_file(sol): return sol / ".state" / "pp-scan.json"
def load_state(sol): return json.loads(state_file(sol).read_text()) if state_file(sol).is_file() else {}
def save_state(sol, st): state_file(sol).parent.mkdir(parents=True, exist_ok=True); state_file(sol).write_text(json.dumps(st, indent=1) + "\n")
def cache_root(sol):
    """Where extracted text is kept: cache_dir/<slug> on this machine when solution.toml sets cache_dir (so it never syncs to Drive), else .state/."""
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    return (pathlib.Path(cfg["cache_dir"]) / cfg.get("slug", sd.source_of(sol).name)) if cfg.get("cache_dir") else sol / ".state"
def text_dir(sol, label): return cache_root(sol) / "text" / "past-performance" / label
def sources(sol):
    f = sol / "past-performance" / "sources.toml"
    return tomllib.loads(f.read_text()).get("source", []) if f.is_file() and f.read_text().strip() else []

def sha1(p):
    h = hashlib.sha1()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def walk(root):
    """Every file under root at any depth (symbolic links followed, loops avoided). -> files, folder count, deepest level."""
    files, folders, deepest, seen = [], 0, 0, set()
    for d, dirs, names in os.walk(root, followlinks=True):
        real = os.path.realpath(d)
        if real in seen: dirs[:] = []; continue
        seen.add(real); folders += 1; deepest = max(deepest, len(pathlib.Path(d).relative_to(root).parts))
        dirs.sort(); files += [pathlib.Path(d) / n for n in sorted(names)]
    return files, folders, deepest

def scan_local(sol, src, st):
    label, root = src.get("label", "source"), asrc.resolve(src["path"], sol)
    if not root.exists():
        hint = " - the Google Drive folder is not mounted or is offline; check Drive for Desktop (Stream files mode)" if MOUNT.search(str(root)) else ""
        return [f"{label}: location not found: {root}{hint}"], 0, 0
    prev = st.setdefault(label, {}); out, new, changed = [], 0, 0
    files, folders, deepest = ([root], 0, 0) if root.is_file() else walk(root)
    stubs = [p for p in files if p.suffix.lower() in NATIVE]
    skipped = collections.Counter(p.suffix.lower() or "(no extension)" for p in files if p.suffix.lower() not in SUFFIXES | NATIVE and not p.name.startswith(("~$", ".")))
    if stubs:
        pend = []
        for p in stubs:
            try: did = json.loads(p.read_text()).get("doc_id") or json.loads(p.read_text()).get("id")
            except (ValueError, OSError): did = None
            if not did: out.append(f"{label}: could not read the Drive pointer {p.name}"); continue
            rel = str(p.relative_to(root)); prev_rec = prev.get(did)
            if prev_rec and prev_rec.get("modified") == str(int(p.stat().st_mtime)): continue
            pend.append(dict(id=did, title=rel, mimeType="application/vnd.google-apps." + p.suffix[2:], modified=str(int(p.stat().st_mtime)), size="", status="changed" if prev_rec else "new"))
        if pend:
            pf = sol / ".state" / "pp-drive-pending.json"; allp = json.loads(pf.read_text()) if pf.is_file() else {}
            allp[label] = list({x["id"]: x for x in allp.get(label, []) + pend}.values()); pf.parent.mkdir(parents=True, exist_ok=True); pf.write_text(json.dumps(allp, indent=1) + "\n")
            out.append(f"{label}: {len(pend)} Google-format file(s) read only through the Drive connector (ask the user, then read each with read_file_content and save its text as {text_dir(sol, label)}/<id>.txt, then run rfps-scan-sources --drive {label} --ingest): " + "; ".join(f"{x['title']} ({x['id']})" for x in pend))
    out.append(f"{label}: looked at {len(files)} file(s) in {folders} folder(s), down to level {deepest}") if not root.is_file() else None
    if skipped: out.append(f"{label}: NOT READ (unsupported type): " + ", ".join(f"{n} x {e}" for e, n in skipped.most_common()) + " - convert or tell the user so nothing is missed")
    seen = set()
    for p in files:
        if p.suffix.lower() not in SUFFIXES or p.name.startswith(("~$", ".")): continue
        rel = p.name if root.is_file() else str(p.relative_to(root)); seen.add(rel); h = sha1(p)
        was = prev.get(rel)
        if was and was["sha1"] == h: continue
        td = text_dir(sol, label); td.mkdir(parents=True, exist_ok=True)
        txt = ex.extract_file(p); (td / (rel.replace("/", "__") + ".txt")).write_text(txt)
        if txt.startswith("EXTRACT ERROR") or len(txt.strip()) < 40: out.append(f"{label}: NO TEXT READ (error or scanned file): {rel}")
        prev[rel] = dict(sha1=h, size=p.stat().st_size, scanned=datetime.datetime.now().isoformat(timespec="seconds"), status="changed" if was else "new")
        if was: changed += 1
        else: new += 1
        out.append(f"{label}: {'changed' if was else 'new'}: {rel}")
    for rel in [r for r in prev if r not in seen and prev[r].get("status") != "removed"]:
        prev[rel]["status"] = "removed"; out.append(f"{label}: no longer there: {rel}")
    for rel, v in prev.items():
        if rel in seen and v.get("status") in ("new", "changed") and not any(rel in o for o in out): v["status"] = "unchanged"
    return out, new, changed

SIGNALS = [("years", re.compile(r"\b(?:19|20)\d{2}\b")), ("amounts", re.compile(r"\$\s?[\d,.]+\s?(?:[KMB]|million|billion)?\b", re.I))]
PERMISSION = re.compile(r".{0,60}\b(?:approved|approval|permission|authori[sz]ed|confidential|not (?:to )?be named|do not name|NDA|may not|cleared)\b.{0,60}", re.I)

def digest(sol):
    st = load_state(sol); lines = ["# Past-performance digest", "",
        "Generated by `rfps-scan-sources`; do not edit. Facts here are what the files say, not what is cleared for the response: "
        "propose evidence rows from it, and set clearance only with the client's or owner's agreement.", ""]
    for src in sources(sol):
        label = src.get("label", "source"); td = text_dir(sol, label)
        files = sorted(td.glob("*.txt")) if td.is_dir() else []
        lines += [f"## {label}", "", f"Source: `{src.get('path', '')}` ({src.get('type', 'local')})", ""]
        if not files: lines += ["No text extracted yet.", ""]; continue
        lines += ["| File | Status | Characters | Years | Amounts | Permission wording |", "|---|---|---|---|---|---|"]
        body = []
        for f in files:
            name = f.name[:-4].replace("__", "/"); t = f.read_text()
            rec = st.get(label, {}).get(name) or st.get(label, {}).get(f.name[:-4]) or {}
            status = rec.get("status", ""); name = rec.get("title", name)
            yrs = sorted(set(SIGNALS[0][1].findall(t)))[:6]; amt = list(dict.fromkeys(SIGNALS[1][1].findall(t)))[:4]
            perm = [" ".join(m.group(0).split()) for m in PERMISSION.finditer(t)][:2]
            esc = lambda x: x.replace("|", "/")
            lines.append(f"| {esc(name)} | {status or 'unchanged'} | {len(t):,} | {', '.join(yrs)} | {esc(', '.join(amt))} | {esc('; '.join(perm))} |")
            body += [f"### {name}", "", "> " + " ".join(t.split())[:500].replace("\n", " "), ""]
        lines += [""] + body
    f = sol / "past-performance" / "digest.md"; f.parent.mkdir(parents=True, exist_ok=True); f.write_text("\n".join(lines) + "\n")
    return f

def drive_compare(sol, label, listing, st):
    prev = st.setdefault(label, {}); pend, same = [], 0
    FOLDER, SHORTCUT = "application/vnd.google-apps.folder", "application/vnd.google-apps.shortcut"
    folders = [it for it in listing if it.get("mimeType") == FOLDER]
    drive_compare.coverage = dict(folders=len(folders), unlisted=[f.get("path") or f.get("title") or f["id"] for f in folders if not f.get("listed")],
                                  shortcuts=[it.get("path") or it.get("title") or it["id"] for it in listing if it.get("mimeType") == SHORTCUT],
                                  deepest=max([len((it.get("path") or "").split("/")) - 1 for it in listing] or [0]))
    listing = [it for it in listing if it.get("mimeType") not in (FOLDER, SHORTCUT)]
    for it in listing:
        fid = it["id"]; was = prev.get(fid)
        if was and was.get("modified") == it.get("modifiedTime"): same += 1; continue
        pend.append(dict(id=fid, title=it.get("path") or it.get("title", fid), mimeType=it.get("mimeType", ""), modified=it.get("modifiedTime", ""), size=it.get("size", ""), status="changed" if was else "new"))
    gone = [v.get("title", k) for k, v in prev.items() if k not in {i["id"] for i in listing} and v.get("status") != "removed"]
    f = sol / ".state" / "pp-drive-pending.json"; f.parent.mkdir(parents=True, exist_ok=True); allp = json.loads(f.read_text()) if f.is_file() else {}; allp[label] = pend; f.write_text(json.dumps(allp, indent=1) + "\n")
    return pend, same, gone

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drive"); ap.add_argument("--listing"); ap.add_argument("--ingest", action="store_true")
    ap.add_argument("--digest", action="store_true"); ap.add_argument("--text-dir", nargs="?", const="", default=None, metavar="LABEL"); ap.add_argument("--solution", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None); st = load_state(sol)
    if a.digest: print(f"Wrote {digest(sol)}"); sys.exit(0)
    if a.text_dir is not None:
        d = text_dir(sol, a.text_dir) if a.text_dir else cache_root(sol) / "text"
        d.mkdir(parents=True, exist_ok=True); print(d); sys.exit(0)
    if a.drive and a.listing:
        pend, same, gone = drive_compare(sol, a.drive, json.loads(pathlib.Path(a.listing).read_text()), st)
        print(f"{a.drive}: {len(pend)} new or changed file(s), {same} unchanged" + (f", {len(gone)} no longer listed" if gone else ""))
        cv = drive_compare.coverage
        print(f"  coverage: {cv['folders']} subfolder(s), down to level {cv['deepest']}")
        if cv["unlisted"]: print("  NOT YET LISTED - list these folders too (search_files with parentId) and add their files to the listing: " + "; ".join(cv["unlisted"]))
        if cv["shortcuts"]: print("  SHORTCUTS - resolve each to its target (get_file_metadata) and list the target: " + "; ".join(cv["shortcuts"]))
        for p in pend: print(f"  {p['status']}: {p['title']} ({p['mimeType'].split('.')[-1]}, {p['size'] or '?'} bytes) id {p['id']}")
        if pend: print(f"Ask the user before reading these. Then save each file's text as {text_dir(sol, a.drive)}/<id>.txt and run rfps-scan-sources --drive {a.drive} --ingest.")
        sys.exit(0)
    if a.drive and a.ingest:
        pf = sol / ".state" / "pp-drive-pending.json"; pend = json.loads(pf.read_text()).get(a.drive, []) if pf.is_file() else []
        prev = st.setdefault(a.drive, {}); n = 0
        for p in pend:
            if (text_dir(sol, a.drive) / (p["id"] + ".txt")).is_file():
                prev[p["id"]] = dict(title=p["title"], modified=p["modified"], size=p["size"], scanned=datetime.datetime.now().isoformat(timespec="seconds"), status=p["status"]); n += 1
        save_state(sol, st); print(f"Recorded {n} of {len(pend)} pending file(s) as scanned. Wrote {digest(sol)}"); sys.exit(0)
    msgs, tn, tc = [], 0, 0
    for src in sources(sol):
        if src.get("type", "local") != "local": msgs.append(f"{src.get('label')}: Drive source; Claude lists it through the connector (see /rfps:add-past-performance)"); continue
        m, n, c = scan_local(sol, src, st); msgs += m; tn += n; tc += c
    save_state(sol, st)
    print("\n".join(msgs) if msgs else "No past-performance sources listed (rfps-add-source adds them).")
    print(f"{tn} new, {tc} changed. Wrote {digest(sol)}")
