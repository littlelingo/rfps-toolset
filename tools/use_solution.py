# /// script
# requires-python = ">=3.11"
# ///
"""Show or set the active solution (the folder whose solution.toml the build commands use by default).

Usage: rfps-use-solution [<active-solution folder or its source folder>]
"""
import pathlib, sys, tomllib
ptr = pathlib.Path.cwd() / ".claude" / "active-solution"   # per project, never inside the plugin folder
if len(sys.argv) > 1:
    d = pathlib.Path(sys.argv[1]).expanduser().resolve()
    if (d / "active-solution" / "solution.toml").is_file(): d = d / "active-solution"
    if not (d / "solution.toml").is_file(): sys.exit(f"no solution.toml in {d}")
    ptr.parent.mkdir(parents=True, exist_ok=True); ptr.write_text(str(d) + "\n")
if not ptr.is_file(): sys.exit("no active solution set")
d = pathlib.Path(ptr.read_text().strip()); cfg = tomllib.loads((d / "solution.toml").read_text())
print(f"Active solution: {d}\n  slug: {cfg.get('slug')}\n  title: {cfg.get('title')}\n  template: {cfg.get('template')}")
