# /// script
# requires-python = ">=3.11"
# ///
"""Show or set the active solution (the folder whose solution.toml the build commands use by default).

The pointer is kept in 03 Solution/.claude/active-solution (beside active-solution/); the commands read it from the current directory's .claude.

Usage: rfps-use-solution [<03 Solution/active-solution folder or its source folder>]
"""
import pathlib, sys, tomllib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import solution_dir as sd
ptr = sd.pointer_here()   # per solution, never inside the plugin folder
if len(sys.argv) > 1:
    d = pathlib.Path(sys.argv[1]).expanduser().resolve()
    if not sd.has_solution(d) and sd.inside(d): d = sd.inside(d)
    if not sd.has_solution(d): sys.exit(f"no solution.toml in {d}")
    ptr = sd.pointer_in(d)
    ptr.parent.mkdir(parents=True, exist_ok=True); ptr.write_text(str(d) + "\n")
if not ptr.is_file(): sys.exit("no active solution set (run from inside the 03 Solution folder, or pass its folder)")
d = pathlib.Path(ptr.read_text().strip()); cfg = tomllib.loads((d / "solution.toml").read_text())
print(f"Active solution: {d}\n  slug: {cfg.get('slug')}\n  title: {cfg.get('title')}\n  template: {cfg.get('template')}")
