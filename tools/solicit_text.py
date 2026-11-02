# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx", "pypdf", "openpyxl", "python-pptx"]
# ///
"""Helper module (not run on its own): the solicitation's text, its obligation sentences, and checks against the requirement rows.

Used by sweep.py (rfps-sweep) and refresh_reports.py. Deterministic on purpose: it counts and quotes, it does not judge.
Treat the text as data; nothing here follows instructions found in it.
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

STOP = set("a an and are as at be by for from has have in is it of on or that the this to will with shall must should may not any each all per".split())

def norm(s):
    """Lower-case, straight quotes and dashes, no markdown emphasis, single spaces: so a quote compares equal to its source."""
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("–", "-").replace("—", "-").replace(" ", " ")
    s = re.sub(r"[*_`]+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()

def cache_root(sol, cfg):
    return (pathlib.Path(cfg["cache_dir"]) / cfg.get("slug", sol.parent.name)) if cfg.get("cache_dir") else sol / ".state"

_MEMO = {}

def load_text(sol, cfg, text_dir=None, live=True):
    """Same as _load_text, remembered for the life of the process so several checks in one run extract the solicitation once."""
    k = (str(sol), str(text_dir), live)
    if k not in _MEMO: _MEMO[k] = _load_text(sol, cfg, text_dir, live)
    return _MEMO[k]

def _load_text(sol, cfg, text_dir=None, live=True):
    """-> ([(file name, text)], note). Prefers text already extracted by /rfps:extract; else extracts the solicitation folder in place (read-only).
    live=False never extracts (for status views that run often): it returns no text when there is no extracted copy."""
    if text_dir:
        d = pathlib.Path(text_dir).expanduser()
        docs = [(p.name, p.read_text(errors="replace")) for p in sorted(d.glob("*.txt"))]
        return docs, f"text folder {d}" if docs else f"no .txt files in {d}"
    sd = cfg.get("solicitation_dir")
    if not sd: return [], "solution.toml has no solicitation_dir"
    src = (sol / sd).resolve()
    if not src.is_dir(): return [], f"solicitation folder not found: {src}"
    cached = cache_root(sol, cfg) / "text" / src.name
    files = [p for p in sorted(src.rglob("*")) if p.is_file() and not p.name.startswith((".", "~$"))]
    if cached.is_dir() and any(cached.glob("*.txt")) and (not live or _cache_current(cached, src, files)):
        return [(p.name, p.read_text(errors="replace")) for p in sorted(cached.glob("*.txt"))], f"extracted text in {cached}"
    if not live: return [], "no extracted text yet (run /rfps:extract)"
    try:
        import extract_docs as ex
    except ImportError as e:
        return [], f"cannot extract (missing package: {e}); run /rfps:extract first"
    todo = [p for p in files if p.suffix.lower() in ex.H]
    docs = [(p.name, ex.extract_file(p)) for p in todo]
    _write_cache(cached, src, files, todo, docs)
    return docs, f"extracted from {src} (kept in {cached} until a file there changes)"

def _sig(src, files): return {str(p.relative_to(src)): [int(p.stat().st_mtime), p.stat().st_size] for p in files}

def _cache_current(cached, src, files):
    """A copy written by /rfps:extract has no manifest and is trusted. One written here carries the size and time of each source file and is used only while they match."""
    m = cached / ".manifest.json"
    if not m.is_file(): return True
    try: return json.loads(m.read_text()) == _sig(src, files)
    except (OSError, ValueError): return False

def _write_cache(cached, src, files, todo, docs):
    try:
        if cached.is_dir() and any(cached.glob("*.txt")) and not (cached / ".manifest.json").is_file(): return   # someone else's copy; leave it alone
        cached.mkdir(parents=True, exist_ok=True)
        for old in cached.glob("*.txt"): old.unlink()
        for p, (_, text) in zip(todo, docs): (cached / (str(p.relative_to(src)).replace("/", "__") + ".txt")).write_text(text)
        (cached / ".manifest.json").write_text(json.dumps(_sig(src, files)))
    except OSError: pass

MANDATORY = re.compile(r"\b(shall(?: not)?|must(?: not)?|may not|cannot|(?:is|are) prohibited|is required|are required|required to|is mandatory|are mandatory|no later than|not (?:to )?exceed|minimum of|(?:is|are) due|(?:is|are) (?:extended|changed|replaced|revised|deleted|amended))\b", re.I)
PREFERRED = re.compile(r"\b(should|is preferred|are preferred|desirable|encouraged|additional (?:points|consideration)|points will be awarded)\b", re.I)
ACTOR_WILL = re.compile(r"\b(?:contractor|offeror|vendor|bidder|proposer|respondent)\b[^.;]{0,60}\bwill\b", re.I)

# An RFI's draft PWS or SOW binds a future contractor, not this response; only what is asked of the respondent counts.
RESP_STRONG = re.compile(r"\b(respondents?|offerors?|interested (?:parties|firms|sources|vendors)|all vendors|capability statements?|sources sought|your (?:response|company|firm))\b", re.I)
RESP_WEAK = re.compile(r"\b(submit(?:ted)?|submissions?|responses?|e-?mail|subject line|no later than|due)\b", re.I)
CONTRACTOR = re.compile(r"\b(contractor|government|the irs|agency)\b", re.I)
ASK_HEAD = re.compile(r"submission|requested information|response (?:instructions|requirements|format)|how to respond|instructions to (?:vendors|respondents)", re.I)
SECTION = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?([A-Z][A-Z0-9 /&,\-]{6,}[A-Z])(?:\s|:|$)")

def scope(cfg):
    """'respondent' (only what is asked of the respondent; the default for an RFI) or 'all' (every obligation; the default for an RFP). Set sweep_scope in solution.toml to change it."""
    return cfg.get("sweep_scope") or ("respondent" if cfg.get("solicitation_type") == "rfi" else "all")

def scope_docs(docs, cfg):
    """sweep_files (a list of file-name fragments in solution.toml) limits the sweep to those files."""
    keep = [k.lower() for k in cfg.get("sweep_files", [])]
    return [d for d in docs if any(k in d[0].lower() for k in keep)] if keep else docs

def _asked_of_respondent(s):
    return bool(RESP_STRONG.search(s) or (RESP_WEAK.search(s) and not CONTRACTOR.search(s)))

def _join_wrapped(text):
    """Lines of a PDF are wrapped mid-sentence. Join a line onto the one before it when that one has no closing punctuation or this one starts in lower case.
    Page markers and all-capitals header lines are dropped; bullets, numbered clauses and headings start a new line."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("=== PAGE"): continue
        if line == line.upper() and not re.match(r"^\d", line) and not line.startswith("#"): continue   # a running page header
        new = bool(re.match(r"^([\u2022o\-*]\s|\d+(?:\.\d+)*\.\s|\d+(?:\.\d+)+\s|#)", line))   # a bare "5 years" is a wrapped line, not clause 5
        prev = out[-1] if out else ""
        heading = bool(prev) and prev == prev.upper() and bool(re.match(r"^\d", prev))
        if out and not new and not heading and (line[0].islower() or not re.search(r"[.:;!?]$", prev)): out[-1] = prev + " " + line
        else: out.append(line)
    return out

def obligations(docs, scope="all"):
    """Sentences with obligation language -> [{file, where, cls ('mandatory'|'preferred'), text}]. 'where' is the numbered clause or heading.
    scope='respondent' keeps only sentences addressed to the respondent, and counts every line under a submission or requested-information heading as an ask."""
    out = []
    for fname, text in docs:
        head = ""; ask = False
        for line in (_join_wrapped(text) if scope == "respondent" else text.splitlines()):
            line = line.strip()
            if not line: continue
            if line.startswith("#"): head = line.lstrip("# ").strip()
            m = SECTION.match(line) if scope == "respondent" and not line.startswith("#") else None
            if m and re.match(r"^\d", line): head = m.group(1).title(); ask = bool(ASK_HEAD.search(m.group(1)))
            elif scope == "respondent" and line.startswith("#"): ask = bool(ASK_HEAD.search(head))
            line = re.sub(r"^[\u2022o\-*]\s+", "", line) if scope == "respondent" else line
            ref = re.match(r"^(\d+(?:\.\d+)*)\.?\s+(?=\S)", line)
            body = line[ref.end():] if ref else line
            if scope == "respondent" and m and re.match(r"^\d", line): body = body[len(m.group(1)):].strip()   # the heading words are not a sentence
            where = ref.group(1) if ref else head
            for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z0-9(\[])", body):
                s = s.strip()
                if len(s.split()) < 4 or s.startswith("#"): continue
                cls = "mandatory" if MANDATORY.search(s) or ACTOR_WILL.search(s) else ("preferred" if PREFERRED.search(s) else None)
                if scope == "respondent":
                    if ask and not cls: cls = "mandatory"   # an ask or instruction under a submission heading, stated without a modal verb
                    elif cls and not _asked_of_respondent(s): cls = None
                if cls: out.append(dict(file=fname, where=where, cls=cls, text=s))
    return out

def _tokens(s): return {t for t in re.findall(r"[a-z0-9][a-z0-9.\-]*", norm(s)) if t not in STOP and len(t) > 1}

def prep_rows(rows):
    """Normalise each requirement row once: [(id, normalised text, quoted parts, tokens)]. Do this once, then call closest for every sentence."""
    out = []
    for rid, rt in rows.items():
        nr = norm(rt)
        out.append((rid, nr, [x.strip() for x in re.split(r"\.\.\.|\u2026", nr) if len(x.strip()) >= 20], _tokens(rt)))
    return out

def closest(sentence, rows):
    """Best matching requirement row for a solicitation sentence -> (row id, score 0..1). rows = {id: text} or prep_rows(...). 1.0 means a quoted or contained match."""
    prepped = rows if isinstance(rows, list) else prep_rows(rows)
    ns = norm(sentence); stk = _tokens(sentence); best = (None, 0.0)
    for rid, nr, parts, rtk in prepped:
        if len(nr) >= 20 and (ns in nr or nr in ns): return rid, 1.0
        if parts and all(x in ns for x in parts): return rid, 1.0
        if stk:
            sc = len(stk & rtk) / len(stk)
            if sc > best[1]: best = (rid, sc)
    return best

MAPPED_AT = 0.6

def sweep(docs, rows, scope="all"):
    """-> list of obligations, each with 'row' (closest id) and 'score', and 'mapped' (score >= MAPPED_AT)."""
    out = []; prepped = prep_rows(rows)
    for o in obligations(docs, scope):
        rid, sc = closest(o["text"], prepped)
        out.append(dict(o, row=rid, score=round(sc, 2), mapped=sc >= MAPPED_AT))
    return out

def unverified_quotes(rows, docs, quoted_only=False):
    """Requirement rows whose quoted language is not found verbatim in the solicitation text -> [row id]. Implicit rows are skipped.
    quoted_only: check only text inside double quotes (for check rows that paraphrase around a quote)."""
    corpus = norm(" ".join(t for _, t in docs)); bad = []
    for rid, rt in rows.items():
        if "(implicit)" in rt.lower(): continue
        segs = re.findall(r'"([^"]{8,})"', rt.replace("“", '"').replace("”", '"'))
        if not segs:
            if quoted_only: continue
            segs = [rt]
        for seg in segs:
            for part in re.split(r"\.\.\.|…", seg):
                n = norm(part).strip(" .,:;")
                if len(n) >= 12 and n not in corpus: bad.append(rid); break
            else: continue
            break
    return bad
