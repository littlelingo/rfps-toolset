"""Plan changes to a shared WIP document without touching the document itself.

Pure functions over lists of block texts (one string per paragraph or table), so any backend can apply the plan:
the docx backend (sync_docx.py) today, a Google Docs backend later.

  snapshot  block texts at the last sync (what the tool last wrote or read)
  current   block texts in the shared document now (others may have edited it)
  new       block texts the response markdown renders to now

plan() diffs snapshot -> new, maps each affected block to its place in the current document, and returns the
operations that are safe to apply plus the conflicts to report (blocks someone edited in the document that the
response change also touches). Unaffected blocks, including ones others edited, are never touched.
"""
import difflib

def _ratio_free(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False)

def plan(snapshot, current, new):
    """-> (ops, conflicts, result, drift).

    ops        list of dicts: {"kind": "insert"|"delete"|"replace", "cur": [indexes into current to delete/replace],
               "after": index into current to insert after (None = start of section), "new": [indexes into new]}
    conflicts  list of strings describing changes that were skipped
    result     the snapshot after the applied ops (skipped changes stay as they were, so a later push retries them)
    drift      indexes into snapshot that no longer match the document (edited or removed by someone else)
    """
    match = {}
    for tag, i1, i2, j1, j2 in _ratio_free(snapshot, current).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1): match[i1 + k] = j1 + k
    drift = [i for i in range(len(snapshot)) if i not in match]
    ops, conflicts, result = [], [], []
    for tag, i1, i2, j1, j2 in _ratio_free(snapshot, new).get_opcodes():
        if tag == "equal":
            result += snapshot[i1:i2]; continue
        old, add = list(range(i1, i2)), list(range(j1, j2))
        label = f"{'; '.join(snapshot[i][:50] for i in old) or 'start of section'}"
        if tag == "insert":
            if i1 > 0 and (i1 - 1) not in match:
                conflicts.append(f"cannot place new text after a block edited in the document: {snapshot[i1 - 1][:60]}")
                continue
            ops.append({"kind": "insert", "cur": [], "after": match[i1 - 1] if i1 > 0 else None, "new": add})
            result += [new[j] for j in add]; continue
        gone = [i for i in old if i not in match]
        if gone:
            conflicts.append(f"edited in the document, so the response change was not applied: {label}")
            result += snapshot[i1:i2]; continue
        ops.append({"kind": "delete" if tag == "delete" else "replace", "cur": [match[i] for i in old],
                    "after": match[old[-1]], "new": add})
        result += [new[j] for j in add]
    return ops, conflicts, result, drift
