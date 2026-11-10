# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Scaffold a new solicitation: create <source folder>/03 Solution/active-solution/ beside the other numbered capture folders.

Creates in 03 Solution/active-solution/:
  solution.toml            config; paths relative to `active-solution/` (template stays in 05 Draft Response)
  response/NN-*.md         one file per Heading 1 of the template docx, every heading in order, empty bodies
  response/resources.csv   roster of proposed roles and people (header only; filled by the resource planner)
  evidence/                register.csv (header only) and README.md
  past-performance/        sources.toml (locations of past-performance material, read in place, never copied)
  amendments/              README.md and log.md for State amendments and Q&A answers
  capture.md (bid decision), questions.md (questions to the agency), win-strategy.md (factors and themes), evaluation-sim.md (second-reader ratings)   living documents
  coverage-matrix.md, compliance-report.md, resource-plan.md   living report skeletons (rows added by the analysis skills; derived blocks by /rfps:refresh-reports)
  .gitignore               build/ and .state/text/
and runs `git init` there when the folder is on a local disk (skipped on a Google Drive mount, where Drive's
own version history applies). 
Also writes the pointer 03 Solution/.claude/active-solution (beside active-solution/, not in the source folder's root, and outside the solution's git repo)
so the build commands default to this solution when Claude Code is opened in 03 Solution.

The template docx is only read. An existing solution is never overwritten.

Which template: --template FILE uses that docx; --template standard copies your standard for the type (rfps-standard-template) into
05 Draft Response; with no --template the one docx in 05 Draft Response is used, else your standard when that folder has none.
--list-templates [--json] only lists the choices (docx files in 05 Draft Response, likely response forms in 01 Solicitation Docs,
your standard, generating one from the notice) with their headings and a recommendation, and changes nothing.

Usage: rfps-new-engagement --source "<source folder>" [--template "<docx>"|standard] [--title "..."] [--slug x]
                                      [--name "Output name"] [--no-git] [--no-pointer]
       rfps-new-engagement --source "<source folder>" --list-templates [--json] [--type rfi|rfp]
"""
import argparse, csv, json, os, pathlib, re, shutil, subprocess, sys, tomllib
import docx
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import standard_template as st_tpl
import solution_dir as sd

COLUMNS = ["id", "claim", "client", "engagement", "date", "numbers", "source", "clearance", "verified", "basis", "superseded_by", "notes", "ban_phrases",
           "start", "end", "value_usd", "scope_tags", "reference_contact", "reference_confirmed", "approved_by", "approved_date", "approval_ref"]
DRIVE = re.compile(r"Google ?Drive|GoogleDrive|My Drive|CloudStorage/GoogleDrive", re.I)
PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULTS = tomllib.loads((pathlib.Path(__file__).resolve().parent / "defaults.toml").read_text())

def slug_of(text): return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
def rel(target, base): return os.path.relpath(target, base)

def find_folder(src, pattern):
    return next((p for p in sorted(src.iterdir()) if p.is_dir() and re.search(pattern, p.name, re.I)), None)

def find_template(src, draft_pattern, exclude):
    cands = []
    for f in [p for p in sorted(src.iterdir()) if p.is_dir() and re.search(draft_pattern, p.name, re.I)]:
        cands += [p for p in f.glob("*.docx") if not p.name.startswith("~$") and not re.search(exclude, p.name, re.I)]
    return cands

# A docx in the solicitation folder is offered as a template only when its name reads like a response form.
FORM_NAME = re.compile(r"respon|template|\bform\b|attachment|questionnaire|volume", re.I)
NOT_FORM = re.compile(r"amendment|q ?& ?a|questions and answers|^~\$", re.I)

def headings(path):
    try: d = docx.Document(str(path))
    except Exception: return None
    hp = DEFAULTS["docx"]["heading_prefix"]
    return [q.text.strip() for q in d.paragraphs if q.style.name.startswith(hp) and q.text.strip()]

def template_candidates(src, a):
    """Every response template the user could pick, best first, one marked recommended. Reads only."""
    out = []
    def add(kind, path, note, excluded=False):
        h = headings(path) if path else None
        out.append({"kind": kind, "path": str(path) if path else None, "headings": len(h) if h is not None else None,
                    "first_headings": (h or [])[:4], "note": note, "excluded": excluded, "recommended": False})
    for f in [p for p in sorted(src.iterdir()) if p.is_dir() and re.search(a.draft_pattern, p.name, re.I)]:
        for p in sorted(f.glob("*.docx")):
            if p.name.startswith("~$"): continue
            ex = bool(re.search(a.template_exclude, p.name, re.I))
            add("draft", p, f"in {f.name}" + (" (name looks like a resume, evidence or old copy, so not picked by default)" if ex else ""), ex)
    sol_dir = find_folder(src, a.solicitation_pattern)
    if sol_dir:
        for p in sorted(sol_dir.rglob("*.docx")):
            if FORM_NAME.search(p.name) and not NOT_FORM.search(p.name):
                add("solicitation", p, f"in {sol_dir.name}: a form issued with the solicitation")
    std = st_tpl.path(a.type)
    if std.is_file(): add("standard", std, f"your standard {a.type} template (copied into the draft-response folder if picked)")
    out.append({"kind": "generate", "path": None, "headings": None, "first_headings": [], "excluded": False, "recommended": False,
                "note": "make one from the solicitation's response instructions (/rfps:generate-template; you approve the outline first)"})
    usable = [c for c in out if c["kind"] in ("draft", "solicitation") and not c["excluded"] and c["headings"]]
    pick = max(usable, key=lambda c: (c["kind"] == "draft", c["headings"])) if usable else next(c for c in out if c["kind"] in ("standard", "generate"))
    pick["recommended"] = True
    for c in out:
        if c["headings"] == 0: c["note"] += "; no Heading 1-3 paragraphs, so nothing to mirror"
    out.sort(key=lambda c: not c["recommended"])
    return out

def print_candidates(cands, as_json):
    if as_json: print(json.dumps(cands, indent=2)); return
    for i, c in enumerate(cands, 1):
        tag = " (recommended)" if c["recommended"] else ""
        what = c["path"] or "generate a template"
        hs = f"; {c['headings']} headings: " + " | ".join(c["first_headings"]) + (" ..." if (c["headings"] or 0) > 4 else "") if c["headings"] else ""
        print(f"{i}. [{c['kind']}]{tag} {what}\n   {c['note']}{hs}")

def copy_standard(src, a, why="Template"):
    std = st_tpl.path(a.type)
    if not std.is_file(): sys.exit(f"no standard {a.type} template of yours (rfps-standard-template --type {a.type} --set FILE.docx, or --make-plain)")
    folder = find_folder(src, a.draft_pattern) or (src / "05 Draft Response"); folder.mkdir(exist_ok=True)
    tpl = folder / f"{slug_of(src.name)}-{a.type}-response-template.docx"
    if tpl.exists(): sys.exit(f"{tpl} already exists; pass it with --template")
    shutil.copyfile(std, tpl); print(f"{why}: using your standard {a.type} template (copied to {tpl})."); return tpl

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True); ap.add_argument("--template")
    ap.add_argument("--title", default=""); ap.add_argument("--slug", default=""); ap.add_argument("--name", default="")
    ap.add_argument("--type", choices=["rfp", "rfi"], default="rfp", help="rfi: a request for information (non-binding); staffing and attachments become optional steps")
    ap.add_argument("--no-git", action="store_true"); ap.add_argument("--no-pointer", action="store_true")
    F = DEFAULTS["folders"]
    ap.add_argument("--draft-pattern", default=F["draft_response"], help="regex for the folder holding the response template")
    ap.add_argument("--solicitation-pattern", default=F["solicitation"], help="regex for the solicitation documents folder")
    ap.add_argument("--final-pattern", default=F["final_submission"], help="regex for the final submission folder")
    ap.add_argument("--pricing-pattern", default=F["pricing"], help="regex for the pricing folder (holds Staffing.xlsx)")
    ap.add_argument("--template-exclude", default=F["template_exclude"], help="regex of template file names to ignore when auto-detecting")
    ap.add_argument("--list-templates", action="store_true", help="list the templates to choose from, with a recommendation; changes nothing")
    ap.add_argument("--json", action="store_true", help="with --list-templates: print JSON")
    a = ap.parse_args()
    src = pathlib.Path(a.source).expanduser().resolve()
    if not src.is_dir(): sys.exit(f"source folder not found: {src}")
    if a.list_templates: print_candidates(template_candidates(src, a), a.json); return
    sol = sd.target_for(src)
    if sd.has_solution(sol) or sd.inside(src): sys.exit(f"{sd.inside(src) or sol} already holds a solution; refusing to overwrite")
    if sol.exists() and any(sol.iterdir()): sys.exit(f"{sol} is not empty; refusing to overwrite")
    if a.template == "standard": tpl = copy_standard(src, a)
    elif a.template: tpl = pathlib.Path(a.template).expanduser().resolve()
    else:
        c = find_template(src, a.draft_pattern, a.template_exclude)
        if len(c) == 1: tpl = c[0].resolve()
        elif not c:
            if not st_tpl.path(a.type).is_file(): sys.exit(f"no response template .docx found in a folder matching --draft-pattern, and no standard {a.type} template of yours (rfps-standard-template); pass --template, or make one with /rfps:generate-template. See the choices with --list-templates")
            tpl = copy_standard(src, a, "No template in the draft-response folder")
        else: sys.exit("several candidate templates; pass --template (see --list-templates for their headings):\n  " + "\n  ".join(str(p) for p in c))
    if not tpl.is_file(): sys.exit(f"template not found: {tpl}")
    d = docx.Document(str(tpl))
    hp = DEFAULTS["docx"]["heading_prefix"]
    heads = [(int(p.style.name.split()[-1]), p.text.strip()) for p in d.paragraphs if p.style.name.startswith(hp) and p.text.strip()]
    if not heads: sys.exit("template has no Heading 1-3 paragraphs; nothing to mirror")
    solicitation = find_folder(src, a.solicitation_pattern)
    final = find_folder(src, a.final_pattern)
    pricing = find_folder(src, a.pricing_pattern)
    slug = a.slug or slug_of(src.name); name = a.name or tpl.stem
    for sub in ("response", "evidence", "past-performance", "amendments"): (sol / sub).mkdir(parents=True, exist_ok=True)
    lines = ["# Solution configuration. Paths are relative to this folder (03 Solution/active-solution/) unless absolute,",
             "# so the folder works the same on a local disk or a synced Google Drive mount.",
             f'slug = "{slug}"', f'title = "{a.title or src.name}"',
             '# "rfp" (a bid) or "rfi" (a request for information: non-binding, no award; staffing and attachments become optional steps).', f'solicitation_type = "{a.type}"',
             "# The response .docx the text is poured into. It is never modified.",
             f'template = "{rel(tpl, sol)}"', f'output_name = "{name}"']
    if solicitation: lines.append(f'solicitation_dir = "{rel(solicitation, sol)}"')
    if final: lines += ["# FINAL builds are also copied here; WIP builds stay in build/.", f'final_copy_dir = "{rel(final, sol)}"']
    lines += ['response_dir = "response"', '# Work from the selected sources only; ask before looking anywhere else.', 'external_sources = "ask"', 'register = "evidence/register.csv"', 'build_dir = "build"',
              "# Pages allowed for the narrative response (excludes cover, table of contents, and supporting evidence). Set it, then run /rfps:refresh-reports.", "# page_limit = 30",
              "# Roster of proposed roles and people (see resource-plan.md for the State's requirements).", 'roster = "response/resources.csv"',
              "# Shared work-in-progress document: \"gdoc\" (Google Docs, the default) or \"docx\" (Word; the WIP skills also take --word).",
              "# wip_format = \"gdoc\"",
              "# Staffing and pricing workbook built from tools/templates/staffing-template.xlsx; create or refresh it with rfps-staffing."]
    lines.append(f'staffing_xlsx = "{rel(pricing / "Staffing.xlsx", sol)}"' if pricing else '# staffing_xlsx = "../../09 Pricing/Staffing.xlsx"')
    lines += ["# FINAL refuses a cleared evidence row that records no proof of the client's approval (approval_ref).", "# require_approval_ref = true",
              "# Price list (csv with labor_category,rate): the price view checks the staffing workbook against it.", '# rate_sheet = "../../09 Pricing/Rate Sheet.csv"',
              "# Rules from the solicitation, read by the automated checks. These are tables, so keep them last.",
              "# [past_performance]", "# max_age_years = 5", "# min_value_usd = 1000000", "# min_references = 3", "# reference_max_age_days = 180",
              "# [final_gate]", "# exclude_pages = 1", "# max_mb = 10", '# required_text = ["Attachment B"]', "# margin_inches = 1.0", '# page_size = "letter"']
    (sol / "solution.toml").write_text("\n".join(lines) + "\n")
    files, cur = [], None
    for lvl, h in heads:
        if lvl == 1: cur = {"name": f"{len(files)+1:02d}-{slug_of(h)}.md", "lines": []}; files.append(cur)
        if cur is None: cur = {"name": "01-front.md", "lines": []}; files.append(cur)
        cur["lines"].append("#" * lvl + " " + h + "\n")
    for f in files:
        (sol / "response" / f["name"]).write_text("<!-- Response source for the docx. Headings must match the docx exactly. Build with /rfps:build-wip. -->\n\n" + "\n".join(f["lines"]))
    with open(sol / "evidence" / "register.csv", "w", newline="") as fh: csv.writer(fh, lineterminator="\n").writerow(COLUMNS)
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import resources as rs
    rs.write(sol / "response" / "resources.csv", [])
    (sol / "evidence" / "README.md").write_text((pathlib.Path(__file__).parent / "templates" / "evidence_README.md").read_text())
    (sol / "past-performance" / "sources.toml").write_text('# Past-performance source locations (read in place, never copied). type = "local" | "drive".\n# [[source]]\n# type = "local"\n# path = "..."   (relative paths are relative to `active-solution/`; rfps-add-source writes them)\n# label = "..."\n')
    (sol / ".state").mkdir(); (sol / ".state" / "integrated.json").write_text("{}\n")
    (sol / "external-sources.md").write_text("# Outside sources added\n\nThe tools work from the selected sources. If you approve looking anywhere else (web, an unlisted folder or drive), record it here.\n\n| Date | What was added | Why | Approved by |\n|------|----------------|-----|-------------|\n")
    (sol / "amendments" / "README.md").write_text((pathlib.Path(__file__).parent / "templates" / "amendments_README.md").read_text())
    (sol / "amendments" / "log.md").write_text("# Amendment and Q&A log\n\n| # | Type | Date received | File (in 01 Solicitation Docs) | What changed | Requirement IDs affected | Response updated | Analysis re-run |\n|---|------|---------------|--------------------------------|--------------|--------------------------|------------------|-----------------|\n| | | | | | | | |\n")
    tdir = pathlib.Path(__file__).parent / "templates"
    for fn, srcf in (("coverage-matrix.md", tdir / "coverage-matrix.md"), ("compliance-report.md", tdir / "compliance-report.md"),
                     ("capture.md", tdir / "capture.md"), ("submission.md", tdir / "submission.md"), ("questions.md", tdir / "questions.md"), ("win-strategy.md", tdir / "win-strategy.md"), ("evaluation-sim.md", tdir / "evaluation-sim.md"),
                     ("resource-plan.md", PLUGIN_ROOT / "skills" / "resource-planner" / "assets" / "resource-plan-template.md")):
        (sol / fn).write_text(srcf.read_text().replace("{title}", a.title or src.name))
    (sol / ".gitignore").write_text("build/\n.state/text/\n.DS_Store\n")
    git = "skipped (--no-git)"
    if not a.no_git:
        if DRIVE.search(str(sol)): git = "skipped (Google Drive folder: Drive version history applies)"
        else:
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=sol, check=True); git = "initialized (no commit yet)"
    if not a.no_pointer:
        ptr = sd.pointer_in(sol); ptr.parent.mkdir(parents=True, exist_ok=True); ptr.write_text(str(sol) + "\n")
    print(f"Created {sol}")
    print(f"  template: {tpl} (stays in place)")
    print(f"  response/: {len(files)} file(s), {len(heads)} headings mirrored")
    print(f"  solicitation_dir: {solicitation or 'not found'}; final_copy_dir: {final or 'not found'}")
    print(f"  git: {git}; pointer: {'not set' if a.no_pointer else str(sd.pointer_in(sol))}")
    print("Next: open Claude Code in the 03 Solution folder, run the analysis skills on the solicitation, add past-performance sources, write text under each heading, then /rfps:build-wip.")

if __name__ == "__main__":
    main()
