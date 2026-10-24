# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""List the terminal tools (the rfps-* commands on the PATH while the plugin is enabled) in this toolset and the skills, with what each is for.

Usage: rfps-list-tools [--json]
Each tool's one-line summary comes from the first line of its docstring, so a new tool shows up automatically;
the "use it when" hint and the related slash command come from the HINTS table below (add a row for a new tool).
"""
import ast, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent
SKIP = {"resources.py"}   # helper module imported by other tools, not run on its own
HINTS = {
    "new_engagement.py": ("Starting a new solicitation", "/rfps:new-engagement"),
    "use_solution.py": ("Switching between solicitations, or checking which one is active", "/rfps:use-solution"),
    "flow_status.py": ("Seeing where you are, what is next, and which sections changed since last integrated", "/rfps:status, /rfps:next, /rfps:step"),
    "extract_docs.py": ("Turning PDFs, Word, Excel and PowerPoint files into searchable text for the analysis skills", "/rfps:extract"),
    "refresh_reports.py": ("After editing the coverage matrix, compliance report, roster or response, to recompute counts, status and page estimates", "/rfps:refresh-reports"),
    "open_items.py": ("Finding every decision, open question, evidence gap and assertion in the response; add --mark to put the colored icons in the files", "/rfps:open-items"),
    "build_response.py": ("Pouring the response text into the Word template: a work-in-progress copy, or the final submission copy", "/rfps:build-wip, /rfps:build-final"),
    "staffing.py": ("Creating the staffing and pricing workbook and keeping it in step with the roster", "/rfps:resources"),
    "sync_gdoc.py": ("Planning pushes to, and reading edits back from, the shared Google Doc (Claude does the reading and writing through the Google connectors)", "/rfps:build-wip, /rfps:pull-wip"),
    "sync_docx.py": ("Pushing approved response changes into the shared WIP docx as tracked changes, and reading edits and comments others made there back into the response; never overwrites their work", "/rfps:build-wip, /rfps:pull-wip"),
    "open_doc.py": ("Opening the shared WIP docx and copying the text to search for, from an open item", "/rfps:open-items"),
    "scan_sources.py": ("Finding new or changed past-performance files, extracting their text and writing the digest the evidence rows are proposed from", "/rfps:add-past-performance"),
    "register_add.py": ("Adding evidence register rows with the next free ID, never cleared on their own", "/rfps:add-past-performance"),
    "make_template.py": ("Writing a response template .docx from an approved outline when the solicitation comes with no form", "/rfps:generate-template"),
    "update_template.py": ("Bringing response/ in line after the template's headings changed: new, renamed, removed or moved sections", "/rfps:update-template"),
    "add_source.py": ("Listing where past-performance material lives, so it is read in place and never copied", "/rfps:add-past-performance"),
    "file_audit.py": ("Checking that every file in the solution folder has a known origin, and recording the ones that do not", "/rfps:file-audit"),
    "status_page.py": ("Seeing the whole picture on one local web page: steps, sections, open items, blockers, evidence and team, with filters and search", "/rfps:status-page"),
    "list_tools.py": ("Seeing this list", "/rfps:help"),
}

def summary(path):
    try:
        d = ast.get_docstring(ast.parse(path.read_text())) or ""
    except SyntaxError:
        d = ""
    first = d.strip().splitlines()[0].strip() if d.strip() else "(no description)"
    usage = next((l.strip() for l in d.splitlines() if l.strip().startswith(("Usage", "uv run"))), "")
    return first, usage

def tools():
    out = []
    for p in sorted(ROOT.glob("*.py")):
        if p.name in SKIP: continue
        first, usage = summary(p)
        when, slash = HINTS.get(p.name, ("", ""))
        out.append(dict(name=p.name, command="rfps-" + p.stem.replace("_", "-"), summary=first, use_when=when, slash=slash, usage=usage))
    return out

NOTES = {}

def skills():
    out = []
    for p in sorted((ROOT.parent / "skills").glob("*/SKILL.md")):
        fm = re.match(r"---\n(.*?)\n---", p.read_text(), re.S)
        desc = ""
        if fm:
            lines = fm.group(1).splitlines()
            for i, l in enumerate(lines):
                if l.startswith("description:"):
                    v = l.split(":", 1)[1].strip()
                    if v in (">", "|", ">-", "|-"):
                        v = " ".join(x.strip() for x in lines[i + 1:] if x.startswith((" ", "\t")))
                    desc = v.strip("\"'")
                    break
        first = re.split(r"(?<=[.])\s", desc, maxsplit=1)[0] if desc else "(no description)"
        out.append(dict(name=p.parent.name, description=NOTES.get(p.parent.name, first)))
    return out

if __name__ == "__main__":
    data = dict(tools=tools(), skills=skills())
    if "--json" in sys.argv:
        print(json.dumps(data, indent=1)); sys.exit()
    print("# Terminal tools (rfps-* commands, run from a terminal or by Claude)\n")
    for t in data["tools"]:
        print(f"- `{t['command']}` - {t['summary']}" + (f"\n  Use it when: {t['use_when']}." if t["use_when"] else "") + (f"\n  Slash command: {t['slash']}" if t["slash"] else ""))
    print("\n# Skills (ask in plain language, or type the name as a slash command)\n")
    for s in data["skills"]:
        print(f"- {s['name']} - {s['description']}")
