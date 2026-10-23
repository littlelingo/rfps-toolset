"""Where to find an open item: the response markdown (file and line) and, when a shared WIP docx exists, its place in that document.

People resolve items in Word or Google Docs, so links go to the document by default once it exists (open_in = "docx"),
and to response/*.md otherwise or when solution.toml says open_in = "md". A document location is the heading's
bookmark (added by rfps-sync-docx) plus the marker text to search for. Word's Navigation Pane also lists the headings.

A Google Docs location (a heading link, #heading=h.<id>) is a later backend; see BACKLOG.md.
"""
import hashlib, pathlib, re, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

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
    """(path, exists) of the shared WIP docx for a solution."""
    import build_response as br, sync_docx as sd
    e = br.load_engagement(str(sol))
    path = sd.wip_path(sol, cfg, e["template"], e["name"])
    return path, path.is_file() and bool(sd.load_state(sol).get("sections"))

def open_in(cfg, wip_exists):
    mode = cfg.get("open_in") or ("docx" if wip_exists else "md")
    return "md" if mode == "docx" and not wip_exists else mode

def decorate(sol, cfg, items):
    """Add to each item: find, bookmark, doc (file URL with the bookmark, or ''), open_in. Returns the mode used."""
    path, exists = wip_location(sol, cfg)
    mode = open_in(cfg, exists)
    for x in items:
        x["find"] = find_text(x)
        x["bookmark"] = bookmark_name(x["section"])
        x["doc"] = f"{path.as_uri()}#{x['bookmark']}" if mode == "docx" else ""
        x["open_in"] = mode
    return mode
