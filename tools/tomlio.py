# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Helper module (not run on its own): set one top-level key in solution.toml without breaking its tables.

solution.toml holds plain keys first and tables ([past_performance], [final_gate], [lint], [docx]) after them. A key appended at the end of the
file lands inside the last table once a person has uncommented one, so the setting is silently ignored. set_key replaces the key where it is,
or inserts it above the first table.
"""
import pathlib, re

def set_key(path, key, value, comment=None):
    """Set key = "value" at the top level of a TOML file. A comment line goes above a newly added key."""
    path = pathlib.Path(path); lines = path.read_text().split("\n"); line = f'{key} = "{value}"'
    table = next((i for i, l in enumerate(lines) if re.match(r"^\s*\[", l)), len(lines))   # real table headers only; a commented one starts with #
    for i in range(table):
        if re.match(rf"^{re.escape(key)}\s*=", lines[i]): lines[i] = line; path.write_text("\n".join(lines)); return
    new = ([f"# {comment}"] if comment else []) + [line]
    if table == len(lines):
        path.write_text("\n".join(lines).rstrip("\n") + "\n" + "\n".join(new) + "\n"); return
    at = table
    while at > 0 and not lines[at - 1].strip(): at -= 1
    lines[at:at] = new + [""] if at == table else new
    path.write_text("\n".join(lines))
