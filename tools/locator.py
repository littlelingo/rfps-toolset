"""Where to find an open item: the response markdown (file and line) and, when a shared WIP document exists, its place in it.

The shared WIP document is a Google Doc by default (wip_format = "gdoc" in solution.toml) or a Word file ("docx"). People
resolve items there, so links go to the document once it exists (open_in = "gdoc" or "docx") and to response/*.md
otherwise or when solution.toml says open_in = "md". A Google Docs location is a heading link; a Word location is the
heading's bookmark (added by rfps-sync-docx) plus the marker text to search for.
"""
import hashlib, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

def wip_format(cfg):
    """'gdoc' (default) or 'docx'."""
    return "docx" if str(cfg.get("wip_format", "gdoc")).lower() in ("docx", "word") else "gdoc"

def bookmark_name(heading):
    """A Word bookmark name for a heading: starts with a letter, letters digits and underscores, at most 40 characters."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", heading).strip("_")[:28]
    return f"rfps_{slug}_{hashlib.sha1(heading.encode()).hexdigest()[:6]}"

def find_text(item):
    """Text to search for in the document: the start of the marker."""
    t = item["text"].strip()
    if len(t) > 45: t = t[:45].rsplit(" ", 1)[0]   # cut at a word boundary so the search matches the document text
    return f"[{item['kind']}" + (f": {t}" if t else "")

def wip_location(sol, cfg):
    """dict(format, exists, path, url): the shared WIP document for a solution (path for Word, url for Google Docs)."""
    import build_response as br
    fmt = wip_format(cfg)
    if fmt == "gdoc":
        import sync_gdoc as sg
        st = sg.load_state(sol)
        if st.get("doc_id"): return dict(format="gdoc", exists=True, path=None, url=sg.doc_url(st), state=st)
        if "wip_format" in cfg: return dict(format="gdoc", exists=False, path=None, url="", state={})   # chosen explicitly: no Word fallback
    import sync_docx as sd
    e = br.load_engagement(str(sol))
    path = sd.wip_path(sol, cfg, e["template"], e["name"])
    return dict(format="docx", exists=path.is_file() and bool(sd.load_state(sol).get("sections")), path=path, url="", state={})

def open_in(cfg, loc):
    mode = cfg.get("open_in") or (loc["format"] if loc["exists"] else "md")
    return "md" if mode in ("docx", "gdoc") and not loc["exists"] else mode

def decorate(sol, cfg, items):
    """Add to each item: find, bookmark, doc (link into the document, or ''), open_in. Returns the mode used."""
    loc = wip_location(sol, cfg)
    mode = open_in(cfg, loc)
    for x in items:
        x["find"] = find_text(x)
        x["bookmark"] = bookmark_name(x["section"])
        if mode == "gdoc":
            import sync_gdoc as sg
            x["doc"] = sg.doc_url(loc["state"], x["section"])
        elif mode == "docx": x["doc"] = f"{loc['path'].as_uri()}#{x['bookmark']}"
        else: x["doc"] = ""
        x["open_in"] = mode
    return mode
