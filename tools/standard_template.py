# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Your standard response template for a type of solicitation (rfi or rfp), kept on this machine and reused for every new solicitation of that type.

Which template a solicitation uses, in order: the form the agency issued (a docx in 05 Draft Response, or --template), else your standard for the
type (this tool), else a plain one made from the plugin's outline (/rfps:generate-template). The standard is only ever copied; a solicitation
never changes it. It lives in ~/.config/rfps/templates/<type>.docx (set RFPS_TEMPLATE_DIR to move it) and is never shared.

Usage: rfps-standard-template [--type rfi|rfp] --show
       rfps-standard-template [--type rfi|rfp] --set FILE.docx [--force]   keep FILE as your standard for the type
       rfps-standard-template [--type rfi] --make-plain [--with-optional] [--force]   write a plain standard from the plugin's outline
"""
import argparse, json, os, pathlib, shutil, sys

OUTLINES = pathlib.Path(__file__).resolve().parent / "templates" / "outlines"
TYPES = ("rfi", "rfp")

def template_dir():
    return pathlib.Path(os.environ.get("RFPS_TEMPLATE_DIR") or (pathlib.Path.home() / ".config" / "rfps" / "templates")).expanduser()

def path(kind): return template_dir() / f"{kind}.docx"

def outline(kind):
    f = OUTLINES / f"{kind}.json"
    return json.loads(f.read_text()) if f.is_file() else None

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--type", choices=TYPES, default="rfi")
    ap.add_argument("--show", action="store_true"); ap.add_argument("--set", metavar="FILE"); ap.add_argument("--make-plain", action="store_true")
    ap.add_argument("--with-optional", action="store_true"); ap.add_argument("--force", action="store_true")
    a = ap.parse_args(); dest = path(a.type)
    if a.set:
        src = pathlib.Path(a.set).expanduser().resolve()
        if src.suffix.lower() != ".docx" or not src.is_file(): sys.exit(f"{src} is not a .docx file")
        if dest.exists() and not a.force: sys.exit(f"{dest} already exists; use --force to replace your standard {a.type} template")
        dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dest); print(f"Your standard {a.type} template is now {dest} (copied from {src})."); return
    if a.make_plain:
        o = outline(a.type)
        if not o: sys.exit(f"the plugin has no standard {a.type} outline yet; use --set with your own docx")
        if dest.exists() and not a.force: sys.exit(f"{dest} already exists; use --force to replace it")
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import make_template as mt   # imported here: make_template imports new_engagement, which imports this module
        mt.make(o, dest, include_optional=a.with_optional); print(f"Wrote a plain standard {a.type} template: {dest}"); return
    print(f"standard {a.type} template: {dest if dest.is_file() else '(none set)'}")
    print(f"plugin outline for {a.type}: {'yes' if outline(a.type) else 'no'}")
    print("Set one with --set FILE.docx, or write a plain one with --make-plain.")

if __name__ == "__main__":
    main()
