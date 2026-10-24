# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Write a richer, fictional response template for testing how a Word template becomes a Google Doc template.

It has what a real template often has and the plain sample lacks: a cover (title and form table), page margins, fonts, a header
and footer, boilerplate instructions under headings, a second heading level, evaluation lines and [text] placeholders.
Usage: uv run fixtures/build_test_template.py [output folder]   (default: fixtures/test-template)
"""
import pathlib, sys
import docx
from docx.shared import Inches, Pt, RGBColor

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent / "test-template"
d = docx.Document()
sec = d.sections[0]
sec.left_margin = sec.right_margin = Inches(0.75); sec.top_margin = sec.bottom_margin = Inches(0.8)
sec.header.paragraphs[0].text = "Response to RFP DPW-2026-017 - Example Bidder LLC"
sec.footer.paragraphs[0].text = "Confidential - for the County's evaluation only"
n = d.styles["Normal"]; n.font.name = "Times New Roman"; n.font.size = Pt(11)
for lvl, size in ((1, 14), (2, 12)):
    h = d.styles[f"Heading {lvl}"]; h.font.name = "Arial"; h.font.size = Pt(size); h.font.bold = True; h.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
d.add_paragraph("Response to RFP DPW-2026-017", style="Title")
d.add_paragraph("Fleet Maintenance Scheduling Portal - Riverbend County Department of Public Works")
t = d.add_table(rows=3, cols=2)
for i, (k, v) in enumerate((("Offeror", "Example Bidder LLC"), ("Contact", "bids@example-bidder.example"), ("Date submitted", ""))):
    t.cell(i, 0).text = k; t.cell(i, 1).text = v

def section(title, evaluation, boiler, level=1):
    d.add_heading(title, level)
    d.add_paragraph(evaluation, style="Subtitle")
    if boiler: d.add_paragraph(boiler)
    d.add_paragraph("[text]")

section("Executive Summary", "Evaluation: clarity of the overall approach (10 percent).", "Instructions: limit this section to one page.")
section("Technical Approach", "Evaluation: soundness of the approach to RFP 2.1 through 2.5 (40 percent).", "Instructions: address each scope item by number.")
section("Scheduling Portal", "Evaluation: RFP 2.1 and 2.3.", "", level=2)
section("Data Migration", "Evaluation: RFP 2.2.", "", level=2)
section("Management Plan", "Evaluation: staffing, schedule and risk management (30 percent).", "")
section("Past Performance", "Evaluation: relevance and quality of comparable work (20 percent).", "Instructions: give at least two references.")
OUT.mkdir(parents=True, exist_ok=True); d.save(OUT / "Test Response Template.docx")
print(f"Wrote {OUT / 'Test Response Template.docx'}")
