# /// script
# requires-python = ">=3.11"
# dependencies = ["python-docx"]
# ///
"""Write the fictional sample capture folder used to try or test the whole rfps flow.

Everything here is made up: the county, the solicitation, the bidder and its past performance. Nothing refers to a real
agency, contract or firm. Usage: uv run fixtures/build_sample.py [output folder]   (default: fixtures/sample-capture)
"""
import pathlib, sys
import docx

OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent / "sample-capture"

def solicitation():
    d = docx.Document()
    d.add_heading("Request for Proposals DPW-2026-017", 0)
    d.add_paragraph("Fleet Maintenance Scheduling Portal. Issued by the Riverbend County Department of Public Works (fictional). Contracting Officer: J. Example, procurement@riverbend.example.")
    d.add_heading("1. Purpose", 1)
    d.add_paragraph("Riverbend County DPW (the County) seeks a contractor to design, build and operate a web portal that schedules preventive maintenance for the County's 420 fleet vehicles.")
    d.add_heading("2. Scope of Work", 1)
    for t in [
        "2.1 The Contractor shall provide a web portal that lets garage supervisors schedule, reschedule and cancel maintenance appointments.",
        "2.2 The Contractor shall migrate the County's existing maintenance history from the legacy spreadsheet system into the portal before go-live.",
        "2.3 The Contractor shall send an email reminder to the responsible driver at least 3 days before each appointment.",
        "2.4 The Contractor shall meet WCAG 2.1 AA accessibility for every public and staff page.",
        "2.5 The Contractor should provide a monthly utilization report to the Fleet Manager.",
        "2.6 The Contractor shall designate a Project Manager as Key Personnel, with at least 5 years of experience managing software delivery for public agencies.",
    ]: d.add_paragraph(t)
    d.add_heading("3. Period of Performance", 1)
    d.add_paragraph("Twelve months from the Notice to Proceed, with two optional one-year extensions. Go-live is required within 6 months of the Notice to Proceed.")
    d.add_heading("4. Evaluation Criteria", 1)
    d.add_paragraph("Proposals are evaluated on: Technical Approach (40 percent), Management Plan (30 percent), Past Performance (20 percent) and Executive Summary clarity (10 percent). Price is evaluated separately.")
    d.add_heading("5. Submission", 1)
    d.add_paragraph("Proposals are due 2026-12-01 at 2:00 PM Eastern by email to procurement@riverbend.example. The narrative response shall not exceed 10 pages. Questions are due 2026-11-10.")
    return d

def amendment():
    d = docx.Document()
    d.add_heading("Amendment 1 to RFP DPW-2026-017", 0)
    d.add_paragraph("Question 1: Is SMS reminder required? Answer: No. Email reminders in 2.3 are sufficient; SMS is optional.")
    d.add_paragraph("Change: Section 3 go-live is extended from 6 months to 7 months of the Notice to Proceed. This amendment supersedes the base RFP where they differ.")
    return d

def template():
    d = docx.Document()
    d.add_heading("Executive Summary", 1)
    d.add_paragraph("Evaluation: clarity of the overall approach (10 percent).", style="Subtitle")
    d.add_paragraph("[text]")
    d.add_heading("Technical Approach", 1)
    d.add_paragraph("Evaluation: soundness of the approach to RFP 2.1 through 2.5 (40 percent).", style="Subtitle")
    d.add_paragraph("[text]")
    d.add_heading("Management Plan", 1)
    d.add_paragraph("Evaluation: staffing, schedule and risk management (30 percent).", style="Subtitle")
    d.add_paragraph("[text]")
    d.add_heading("Past Performance", 1)
    d.add_paragraph("Evaluation: relevance and quality of comparable work (20 percent).", style="Subtitle")
    d.add_paragraph("[text]")
    return d

def bidder_notes():
    d = docx.Document()
    d.add_heading("Example Bidder LLC - past performance notes (fictional)", 0)
    d.add_paragraph("Example Bidder LLC is a fictional software firm used only for this sample.")
    d.add_heading("Hillview Transit Authority scheduling portal", 1)
    d.add_paragraph("2023-2024. Built a shift and vehicle scheduling portal for 310 buses. Delivered on schedule in 8 months. Client has approved use of this reference.")
    d.add_heading("Lakeshore Parks legacy data migration", 1)
    d.add_paragraph("2022. Migrated 11 years of maintenance records from spreadsheets into a web system with no data loss. Client has approved use of this reference.")
    d.add_heading("Northgate Water accessibility remediation", 1)
    d.add_paragraph("2024. Brought 60 public and staff pages to WCAG 2.1 AA. Client permission to name them is still pending.")
    return d

files = {
    "01 Solicitation Docs/RFP DPW-2026-017.docx": solicitation(),
    "01 Solicitation Docs/Amendment 1.docx": amendment(),
    "05 Draft Response/Response Template.docx": template(),
    "past-performance/Example Bidder past performance notes.docx": bidder_notes(),
}
for rel, doc in files.items():
    p = OUT / rel; p.parent.mkdir(parents=True, exist_ok=True); doc.save(p)
(OUT / "11 Final Submission").mkdir(exist_ok=True); (OUT / "11 Final Submission" / ".gitkeep").write_text("")
print(f"Wrote {OUT}")
