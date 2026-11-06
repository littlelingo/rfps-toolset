"""Where a solution lives: <source folder>/03 Solution/active-solution/.

The numbered 03 Solution/active-solution folder holds the solution folder (active-solution/, the generated files, its own git repo)
and the .claude folder with the active-solution pointer, so nothing is added to the source folder's root.
Older solutions kept active-solution/ directly in the source folder; they are still found.
"""
import pathlib, re, tomllib

DEFAULT_NAME = "03 Solution"
SOLUTION_NAME = "active-solution"     # the solution folder inside 03 Solution
WIP_PREFIX = "SOLUTION - "                # leads the name of every shared WIP (Google Doc title and Word file)
POINTER_NAME = "active-solution"          # the pointer file, inside <solution>/.claude/
_DEFAULTS = pathlib.Path(__file__).resolve().parent / "defaults.toml"

def folder_pattern():
    return tomllib.loads(_DEFAULTS.read_text())["folders"]["solution"]

def has_solution(p):
    return (pathlib.Path(p) / "solution.toml").is_file()

def inside(p):
    """The solution folder for p, a source folder or its 03 Solution/active-solution folder (a legacy active-solution/ in the source is found too), or None."""
    p = pathlib.Path(p)
    if not p.is_dir(): return None
    direct = p / SOLUTION_NAME
    if has_solution(direct): return direct
    pat = re.compile(folder_pattern(), re.I)
    for c in sorted(p.iterdir()):
        if c.is_dir() and pat.search(c.name) and has_solution(c / SOLUTION_NAME): return c / SOLUTION_NAME
    return None

def target_for(src):
    """Where a new solution for source folder src goes: <existing numbered 03 folder, else '03 Solution'>/active-solution."""
    src = pathlib.Path(src)
    pat = re.compile(folder_pattern(), re.I)
    for c in sorted(src.iterdir()):
        if c.is_dir() and pat.search(c.name): return c / SOLUTION_NAME
    return src / DEFAULT_NAME / SOLUTION_NAME

def source_of(sol):
    """The source (capture) folder a solution belongs to."""
    sol = pathlib.Path(sol).resolve()
    par = sol.parent
    return par.parent if re.search(folder_pattern(), par.name, re.I) else par

def pointer_in(sol):
    """The pointer file beside the solution folder: <03 Solution>/.claude/active-solution."""
    return pathlib.Path(sol).parent / ".claude" / POINTER_NAME

def pointer_here(cwd=None):
    """The pointer file in the current directory's .claude (the current directory is normally the 03 Solution folder)."""
    return (pathlib.Path(cwd) if cwd else pathlib.Path.cwd()) / ".claude" / POINTER_NAME

def wip_title(title):
    """Title of the shared Google Doc WIP: SOLUTION - <solution title> - Response WIP."""
    return f"{WIP_PREFIX}{title} - Response WIP"

def wip_name(name):
    """File name of the shared work-in-progress copy: SOLUTION - <name>_WIP.docx."""
    return f"{WIP_PREFIX}{name}_WIP.docx"
