# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Scaffold a new solicitation: create <source folder>/active-solution/ beside the numbered capture folders.

Creates in active-solution/:
  solution.toml            config; paths relative to active-solution/ (template stays in 05 Draft Response)
  response/NN-*.md         one file per Heading 1 of the template docx, every heading in order, empty bodies
  response/resources.csv   roster of proposed roles and people (header only; filled by the resource planner)
  evidence/                register.csv (header only) and README.md
  past-performance/        sources.toml (locations of past-performance material, read in place, never copied)
  amendments/              README.md and log.md for State amendments and Q&A answers
  coverage-matrix.md, compliance-report.md, resource-plan.md   living report skeletons (rows added by the analysis skills; derived blocks by /rfps:refresh-reports)
  .gitignore               build/ and .state/text/
and runs `git init` there when the folder is on a local disk (skipped on a Google Drive mount, where Drive's
own version history applies). Sets the active-solution pointer (<current directory>/.claude/active-solution) so the build commands default to it.

The template docx is only read. An existing active-solution/ is never overwritten.

Usage: rfps-new-engagement --source "<source folder>" [--template "<docx>"] [--title "..."] [--slug x]
                                      [--name "Output name"] [--no-git] [--no-pointer]
"""
import argparse, csv, os, pathlib, re, subprocess, sys, tomllib
import docx

COLUMNS = ["id", "claim", "client", "engagement", "date", "numbers", "source", "clearance", "verified", "basis", "superseded_by", "notes", "ban_phrases"]
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

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True); ap.add_argument("--template")
    ap.add_argument("--title", default=""); ap.add_argument("--slug", default=""); ap.add_argument("--name", default="")
    ap.add_argument("--no-git", action="store_true"); ap.add_argument("--no-pointer", action="store_true")
    F = DEFAULTS["folders"]
    ap.add_argument("--draft-pattern", default=F["draft_response"], help="regex for the folder holding the response template")
    ap.add_argument("--solicitation-pattern", default=F["solicitation"], help="regex for the solicitation documents folder")
    ap.add_argument("--final-pattern", default=F["final_submission"], help="regex for the final submission folder")
    ap.add_argument("--pricing-pattern", default=F["pricing"], help="regex for the pricing folder (holds Staffing.xlsx)")
    ap.add_argument("--template-exclude", default=F["template_exclude"], help="regex of template file names to ignore when auto-detecting")
    a = ap.parse_args()
    src = pathlib.Path(a.source).expanduser().resolve()
    if not src.is_dir(): sys.exit(f"source folder not found: {src}")
    sol = src / "active-solution"
    if sol.exists(): sys.exit(f"{sol} already exists; refusing to overwrite")
    if a.template: tpl = pathlib.Path(a.template).expanduser().resolve()
    else:
        c = find_template(src, a.draft_pattern, a.template_exclude)
        if len(c) == 1: tpl = c[0].resolve()
        elif not c: sys.exit("no response template .docx found in a folder matching --draft-pattern; pass --template, or generate one from the solicitation with /rfps:generate-template")
        else: sys.exit("several candidate templates; pass --template:\n  " + "\n  ".join(str(p) for p in c))
    if not tpl.is_file(): sys.exit(f"template not found: {tpl}")
    d = docx.Document(str(tpl))
    hp = DEFAULTS["docx"]["heading_prefix"]
    heads = [(int(p.style.name.split()[-1]), p.text.strip()) for p in d.paragraphs if p.style.name.startswith(hp) and p.text.strip()]
    if not heads: sys.exit("template has no Heading 1-3 paragraphs; nothing to mirror")
    solicitation = find_folder(src, a.solicitation_pattern)
    final = find_folder(src, a.final_pattern)
    pricing = find_folder(src, a.pricing_pattern)
    slug = a.slug or slug_of(src.name); name = a.name or tpl.stem
    for sub in ("response", "evidence", "past-performance", "amendments"): (sol / sub).mkdir(parents=True)
    lines = ["# Solution configuration. Paths are relative to this folder (active-solution/) unless absolute,",
             "# so the folder works the same on a local disk or a synced Google Drive mount.",
             f'slug = "{slug}"', f'title = "{a.title or src.name}"',
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
    lines.append(f'staffing_xlsx = "{rel(pricing / "Staffing.xlsx", sol)}"' if pricing else '# staffing_xlsx = "../09 Pricing/Staffing.xlsx"')
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
    (sol / "past-performance" / "sources.toml").write_text('# Past-performance source locations (read in place, never copied). type = "local" | "drive".\n# [[source]]\n# type = "local"\n# path = "..."   (relative paths are relative to active-solution/; rfps-add-source writes them)\n# label = "..."\n')
    (sol / ".state").mkdir(); (sol / ".state" / "integrated.json").write_text("{}\n")
    (sol / "external-sources.md").write_text("# Outside sources added\n\nThe tools work from the selected sources. If you approve looking anywhere else (web, an unlisted folder or drive), record it here.\n\n| Date | What was added | Why | Approved by |\n|------|----------------|-----|-------------|\n")
    (sol / "amendments" / "README.md").write_text((pathlib.Path(__file__).parent / "templates" / "amendments_README.md").read_text())
    (sol / "amendments" / "log.md").write_text("# Amendment and Q&A log\n\n| # | Type | Date received | File (in 01 Solicitation Docs) | What changed | Requirement IDs affected | Response updated | Analysis re-run |\n|---|------|---------------|--------------------------------|--------------|--------------------------|------------------|-----------------|\n| | | | | | | | |\n")
    tdir = pathlib.Path(__file__).parent / "templates"
    for fn, srcf in (("coverage-matrix.md", tdir / "coverage-matrix.md"), ("compliance-report.md", tdir / "compliance-report.md"),
                     ("resource-plan.md", PLUGIN_ROOT / "skills" / "resource-planner" / "assets" / "resource-plan-template.md")):
        (sol / fn).write_text(srcf.read_text().replace("{title}", a.title or src.name))
    (sol / ".gitignore").write_text("build/\n.state/text/\n.DS_Store\n")
    git = "skipped (--no-git)"
    if not a.no_git:
        if DRIVE.search(str(sol)): git = "skipped (Google Drive folder: Drive version history applies)"
        else:
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=sol, check=True); git = "initialized (no commit yet)"
    if not a.no_pointer:
        ptr = pathlib.Path.cwd() / ".claude" / "active-solution"; ptr.parent.mkdir(parents=True, exist_ok=True); ptr.write_text(str(sol) + "\n")
    print(f"Created {sol}")
    print(f"  template: {tpl} (stays in place)")
    print(f"  response/: {len(files)} file(s), {len(heads)} headings mirrored")
    print(f"  solicitation_dir: {solicitation or 'not found'}; final_copy_dir: {final or 'not found'}")
    print(f"  git: {git}; active-solution pointer: {'not set' if a.no_pointer else 'set'}")
    print("Next: run the analysis skills on the solicitation, add past-performance sources, write text under each heading, then /rfps:build-wip.")

if __name__ == "__main__":
    main()
