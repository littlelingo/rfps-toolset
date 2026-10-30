# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Turn a base64 download from the Drive connector into a real file, without anyone retyping it.

The Drive connector's download_file_content returns a file as base64 text. When the app saves that result to a file, this tool
decodes it exactly. When the base64 only appeared in the chat, do NOT copy it by hand (a single wrong character corrupts a Word
file): ask the user to download the file from Drive into the folder instead.

The input is the saved result file: raw base64, or JSON holding the base64 in some string field (the longest string is used).
The output must not exist yet, and its type is checked (.docx, .xlsx, .pptx are zip files; .pdf starts with %PDF).

Usage: rfps-decode-b64 SAVED_RESULT OUT_FILE
"""
import base64, json, pathlib, re, sys

def longest_string(o):
    if isinstance(o, str): return o
    best = ""
    for v in (o.values() if isinstance(o, dict) else o if isinstance(o, list) else []):
        s = longest_string(v)
        if len(s) > len(best): best = s
    return best

def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    src, out = pathlib.Path(sys.argv[1]).expanduser(), pathlib.Path(sys.argv[2]).expanduser()
    if not src.is_file(): sys.exit(f"not found: {src}")
    if out.exists(): sys.exit(f"{out} already exists; refusing to overwrite")
    text = src.read_text(errors="replace").strip()
    try: text = longest_string(json.loads(text))
    except ValueError: pass
    text = re.sub(r"\s+", "", text.split(",", 1)[1] if text.startswith("data:") else text)
    try: data = base64.b64decode(text + "=" * (-len(text) % 4), validate=True)
    except Exception as e: sys.exit(f"not valid base64 ({e}). If the result was not saved to a file, ask the user to download the file from Drive.")
    ext = out.suffix.lower()
    if ext in (".docx", ".xlsx", ".pptx") and data[:2] != b"PK": sys.exit(f"decoded {len(data):,} bytes but they are not a {ext} (zip) file; not written")
    if ext == ".pdf" and data[:4] != b"%PDF": sys.exit(f"decoded {len(data):,} bytes but they are not a PDF; not written")
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(data)
    print(f"Wrote {out} ({len(data):,} bytes)")

if __name__ == "__main__":
    main()
