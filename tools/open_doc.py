# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Open the shared WIP docx for the active solution and show where to look.

Word has no way for another program to jump to a spot inside a document, so this opens the file and puts the text to
search for on the clipboard. In Word, use the Navigation Pane (View > Navigation Pane) to jump to a heading, or search
(Ctrl/Cmd+F) and paste. Each heading also carries a bookmark (Ctrl+G > Bookmark) named as printed below.

Usage: rfps-open-doc [--section "Heading"] [--find "[DECISION: text"] [--print] [--solution <folder>]
  --print   only print the location; open nothing and copy nothing
"""
import argparse, pathlib, shutil, subprocess, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_response as br
import locator

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--section"); ap.add_argument("--find"); ap.add_argument("--print", action="store_true")
    ap.add_argument("--solution", nargs="?", const="", default=None)
    a = ap.parse_args()
    sol = br.resolve_solution(a.solution or None)
    cfg = tomllib.loads((sol / "solution.toml").read_text())
    path, exists = locator.wip_location(sol, cfg)
    if not exists: sys.exit(f"No shared WIP docx yet ({path}). Run /rfps:build-wip to create it.")
    print(f"Document: {path}")
    if a.section: print(f"Section: {a.section}  (bookmark {locator.bookmark_name(a.section)})")
    if a.find: print(f"Search for: {a.find}")
    if a.print: sys.exit(0)
    if a.find:
        for cmd in (["pbcopy"], ["xclip", "-selection", "clipboard"], ["clip"]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, input=a.find.encode(), check=False); print("The search text is on the clipboard."); break
    opener = shutil.which("open") or shutil.which("xdg-open")
    if opener: subprocess.run([opener, str(path)], check=False); print("Opened in your default app. In Word: Navigation Pane to jump to the heading, then paste to search.")
    else: print("Open the file yourself; no opener was found.")
