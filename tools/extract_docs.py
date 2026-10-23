# /// script
# requires-python = ">=3.10"
# dependencies = ["pypdf", "python-docx", "openpyxl", "python-pptx"]
# ///
"""Extract text from every .pdf, .docx, .xlsx and .pptx under a folder into one .txt per file.

Usage: rfps-extract-docs <input folder> <output folder>
Read-only on the input; the output folder receives <relative path with / replaced by __>.txt.
Use it to give the analysis skills searchable text for solicitation documents and past-performance sources.
"""
import sys, os, re, pathlib
root=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2])
import pypdf, docx, openpyxl, pptx
from docx.table import Table
from docx.text.paragraph import Paragraph
def do_pdf(p):
    r=pypdf.PdfReader(str(p)); return "\n".join(f"\n=== PAGE {i} ===\n"+(pg.extract_text() or "") for i,pg in enumerate(r.pages,1))
def do_docx(p):
    d=docx.Document(str(p)); o=[]
    for el in d.element.body.iterchildren():
        if el.tag.endswith('}p'):
            q=Paragraph(el,d)
            if q.text.strip(): o.append(("# " if q.style.name.startswith("Heading") else "")+q.text)
        elif el.tag.endswith('}tbl'):
            t=Table(el,d)
            for r in t.rows: o.append(" | ".join(c.text.strip().replace("\n"," / ") for c in r.cells))
    return "\n".join(o)
def do_xlsx(p):
    wb=openpyxl.load_workbook(str(p),data_only=True); o=[]
    for ws in wb:
        o.append(f"## {ws.title} {ws.dimensions}")
        for row in ws.iter_rows():
            v=[f"{c.coordinate}={str(c.value)[:400]}" for c in row if c.value is not None]
            if v: o.append(" | ".join(v))
    return "\n".join(o)
def do_pptx(p):
    pr=pptx.Presentation(str(p)); o=[]
    for i,s in enumerate(pr.slides,1):
        o.append(f"=== SLIDE {i} ===")
        for sh in s.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip(): o.append(sh.text_frame.text)
            if getattr(sh,"has_table",False) and sh.has_table:
                for r in sh.table.rows: o.append(" | ".join(c.text for c in r.cells))
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip(): o.append("NOTES: "+s.notes_slide.notes_text_frame.text)
    return "\n".join(o)
H={".pdf":do_pdf,".docx":do_docx,".xlsx":do_xlsx,".pptx":do_pptx}
for p in sorted(root.rglob("*")):
    if p.is_file() and p.suffix.lower() in H:
        rel=str(p.relative_to(root)).replace("/","__")
        try:
            t=H[p.suffix.lower()](p)
        except Exception as e:
            t=f"EXTRACT ERROR {e}"
        (out/(rel+".txt")).write_text(t)
        print(len(t), rel[:120])
