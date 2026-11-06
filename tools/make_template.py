# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Write a response template .docx from an outline of the sections the solicitation asks for.

For solicitations that come with no response form. The outline is made by reading the solicitation (see /rfps:generate-template)
and approved by the user; this tool only lays it out in the conventions the build expects: Heading 1-3 for sections, a Subtitle
line holding what the solicitation says that section must show, and a [text] placeholder where the response goes.
It never overwrites an existing file.

Outline (JSON): {"title": "Response to ...", "sections": [{"level": 1, "title": "Technical Approach",
                 "instruction": "Describe the approach to scope items 2.1 to 2.5", "source": "RFP 4.2", "optional": false}, ...]}

Usage: rfps-make-template --outline FILE.json [--source <capture folder>] [--out <docx>] [--force]
"""
import argparse, json, pathlib, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import solution_dir as sd
import docx
import build_response as br
import new_engagement as ne

DEFAULTS = tomllib.loads((pathlib.Path(__file__).resolve().parent / "defaults.toml").read_text())

def make(outline, out, include_optional=False):
    d = docx.Document()
    t = outline.get("title") or "Response"
    d.add_paragraph(t, style="Title")
    d.add_paragraph("Generated from the solicitation's response instructions. Replace it with the issuing office's form if one is provided.").runs[0].italic = True
    cfg = DEFAULTS["docx"]; scaffold = cfg["scaffold_styles"][0]; hp = cfg["heading_prefix"]; ph = next(x for x in cfg["placeholders"] if x.startswith("["))
    for s in outline["sections"]:
        if s.get("optional") and not include_optional: continue   # sections the notice may or may not invite
        lvl = int(s.get("level", 1))
        if lvl not in (1, 2, 3): raise SystemExit(f"section level must be 1, 2 or 3: {s.get('title')}")
        if not (s.get("title") or "").strip(): raise SystemExit("every section needs a title")
        d.add_heading(s["title"].strip(), lvl).style = d.styles[f"{hp} {lvl}"]
        line = " ".join(x for x in ((s.get("instruction") or "").strip(), f"({s['source']})" if s.get("source") else "") if x)
        if line: d.add_paragraph(line, style=scaffold)
        d.add_paragraph(ph)
    out.parent.mkdir(parents=True, exist_ok=True); d.save(str(out))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outline", required=True); ap.add_argument("--source"); ap.add_argument("--out"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    outline = json.loads(pathlib.Path(a.outline).read_text())
    if not outline.get("sections"): sys.exit("the outline has no sections")
    if a.out: out = pathlib.Path(a.out).expanduser().resolve()
    else:
        src = pathlib.Path(a.source).expanduser().resolve() if a.source else None
        if src is None:
            try: src = sd.source_of(br.resolve_solution(None))
            except SystemExit: sys.exit("give --source (the capture folder) or --out")
        folder = ne.find_folder(src, DEFAULTS["folders"]["draft_response"]) or (src / "05 Draft Response")
        out = folder / "Response Template.docx"
    if out.exists() and not a.force: sys.exit(f"{out} already exists; refusing to overwrite (use --force, or --out for another name)")
    make(outline, out)
    print(f"Wrote {out} ({len(outline['sections'])} sections). Next: /rfps:new-engagement")
