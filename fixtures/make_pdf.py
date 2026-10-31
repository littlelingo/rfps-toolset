# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Write small test PDFs by hand (no PDF library needed) for the final-gate checks in smoke.sh.

Usage: uv run fixtures/make_pdf.py clean|defects OUT.pdf
  clean    3 Letter pages of plain text, left margin 72 points, only a Title in the metadata
  defects  14 pages, internal markers, a link to a Google Doc, an Author with an email address, no signature wording
"""
import sys

def esc(s): return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def make_pdf(path, pages, info=None, links=None, size=(612, 792)):
    """pages: [[(x, y, text), ...], ...]; links: {page index: url}; info: {"Title": ..., "Author": ...}."""
    objs = []   # object n is objs[n - 1]
    n_pages = len(pages)
    first_page = 5   # 1 catalog, 2 pages, 3 font, 4 info, then page/content pairs (plus an annotation after a linked page)
    ids, nxt = [], first_page
    annot = {}
    for i in range(n_pages):
        ids.append((nxt, nxt + 1)); nxt += 2
        if links and i in links: annot[i] = nxt; nxt += 1
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(("<< /Type /Pages /Kids [" + " ".join(f"{p} 0 R" for p, _ in ids) + f"] /Count {n_pages} >>").encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objs.append(("<< " + " ".join(f"/{k} ({esc(v)})" for k, v in (info or {}).items()) + " >>").encode())
    for i, lines in enumerate(pages):
        p, c = ids[i]
        a = f" /Annots [{annot[i]} 0 R]" if i in annot else ""
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {size[0]} {size[1]}] /Contents {c} 0 R /Resources << /Font << /F1 3 0 R >> >>{a} >>".encode())
        stream = "\n".join(f"BT /F1 11 Tf {x} {y} Td ({esc(t)}) Tj ET" for x, y, t in lines).encode()
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        if i in annot:
            objs.append(f"<< /Type /Annot /Subtype /Link /Rect [72 700 200 712] /Border [0 0 0] /A << /S /URI /URI ({esc(links[i])}) >> >>".encode())
    out = b"%PDF-1.4\n"; offs = []
    for n, body in enumerate(objs, 1):
        offs.append(len(out)); out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info 4 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    open(path, "wb").write(out)

def body(page_no, extra=()):
    lines = [(72, 720, f"Sample narrative response, page {page_no}")]
    for k in range(18): lines.append((72, 690 - k * 16, "Riverbend County garage supervisors schedule preventive maintenance in one calendar."))
    return lines + list(extra)

if __name__ == "__main__":
    kind, out = sys.argv[1], sys.argv[2]
    if kind == "clean":
        pages = [body(1), body(2), body(3, [(72, 300, "Attachment B signed by the authorized representative.")])]
        make_pdf(out, pages, info={"Title": "Sample response"})
    elif kind == "defects":
        pages = [body(i + 1) for i in range(14)]
        pages[1] = body(2, [(72, 300, "The portal prevents double booking. [ASSERTION: the calendar rejects overlaps] [GROUNDED: E-002]")])
        make_pdf(out, pages, info={"Title": "Sample response", "Author": "pat@example.com"}, links={0: "https://docs.google.com/document/d/abc/edit"})
    else:
        sys.exit("clean or defects")
