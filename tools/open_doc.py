# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Open the shared WIP document for the active solution and show where to look.

Google Docs (the default): opens the heading's link in your browser. Word (wip_format = "docx"): opens the file and puts
the text to search for on the clipboard; Word cannot be driven to a spot from outside, so use the Navigation Pane
(View > Navigation Pane) to jump to a heading, then paste to search.

Usage: rfps-open-doc [--section "Heading"] [--find "[DECISION: text"] [--print] [--solution <folder>]
  --print   only print the location; open nothing and copy nothing
"""
import argparse, pathlib, shutil, subprocess, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import locator

def copy(text):
    for cmd in (["pbcopy"], ["xclip", "-selection", "clipboard"], ["clip"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text.encode(), check=False); return True
    return False

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--section"); ap.add_argument("--find"); ap.add_argument("--print", action="store_true")
    ap.add_argument("--solution", nargs="?", const="", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    loc = locator.wip_location(sol, cfg)
    if not loc["exists"]: sys.exit("No shared WIP document yet. Run /rfps:build-wip to create it.")
    if loc["format"] == "gdoc":
        import sync_gdoc as sg
        target = sg.doc_url(loc["state"], a.section)
        print(f"Google Doc: {target}")
    else:
        target = str(loc["path"]); print(f"Document: {target}")
        if a.section: print(f"Section: {a.section}  (bookmark {locator.bookmark_name(a.section)})")
    if a.find: print(f"Search for: {a.find}")
    if a.print: sys.exit(0)
    if a.find and loc["format"] == "docx" and copy(a.find): print("The search text is on the clipboard.")
    opener = shutil.which("open") or shutil.which("xdg-open")
    if opener: subprocess.run([opener, target], check=False); print("Opened." + (" In Word: Navigation Pane to jump to the heading, then paste to search." if loc["format"] == "docx" else ""))
    else: print("Open it yourself; no opener was found.")
