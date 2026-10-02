from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from reportlab.graphics.barcode import code128
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import AnesthesiaCase

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "generated"
TOKEN_DIR = DATA_DIR / "tokens"
FORM_DIR = DATA_DIR / "forms"
TOKEN_DIR.mkdir(parents=True, exist_ok=True)
FORM_DIR.mkdir(parents=True, exist_ok=True)


def _patient(case: AnesthesiaCase):
    return case.patient


def create_token_pdf(case: AnesthesiaCase, settings: dict) -> Path:
    width = int(settings.get("token_paper_width_mm", 80)) * mm
    height = int(settings.get("token_paper_height_mm", 110)) * mm
    path = TOKEN_DIR / f"{case.token_date.isoformat()}-{case.token_number}.pdf"
    styles = getSampleStyleSheet()
    center = ParagraphStyle("center", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, leading=12)
    big = ParagraphStyle("big", parent=center, fontSize=28, leading=32, fontName="Helvetica-Bold")
    doc = SimpleDocTemplate(
        str(path), pagesize=(width, height), leftMargin=5 * mm, rightMargin=5 * mm, topMargin=5 * mm, bottomMargin=4 * mm
    )
    patient = _patient(case)
    barcode = code128.Code128(case.token_number, barHeight=13 * mm, barWidth=0.32 * mm, humanReadable=False)
    story = [
        Paragraph("<b>CMH DHAKA</b>", center),
        Paragraph("Department of Anaesthesiology", center),
        Spacer(1, 3 * mm),
        Paragraph("TOKEN", center),
        Paragraph(case.token_number, big),
        Spacer(1, 2 * mm),
        barcode,
        Spacer(1, 2 * mm),
        Paragraph(f"<b>{patient.rank.label} {patient.name}</b>", center),
        Paragraph(f"No: {patient.service_number} &nbsp;|&nbsp; Unit: {patient.unit}", center),
        Paragraph(case.token_date.strftime("%d %b %Y"), center),
        Spacer(1, 2 * mm),
        Paragraph("Please keep this token with you.<br/>No audio announcement will be made; watch the display.", center),
    ]
    doc.build(story)
    return path


def _line(canvas: Canvas, label: str, x: float, y: float, width: float, value: str = "") -> None:
    canvas.setFont("Helvetica", 7.4)
    canvas.drawString(x, y, label)
    start = x + canvas.stringWidth(label, "Helvetica", 7.4) + 2 * mm
    canvas.line(start, y - 1, x + width, y - 1)
    if value:
        canvas.setFont("Helvetica-Bold", 8.2)
        canvas.drawString(start + 1.5 * mm, y, value)


def _section(canvas: Canvas, title: str, x: float, y: float, width: float) -> None:
    canvas.setFillColor(colors.HexColor("#E9F2EE"))
    canvas.rect(x, y - 3 * mm, width, 6 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#173D32"))
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawString(x + 2 * mm, y - 0.5 * mm, title)


def create_anesthesia_form_pdf(case: AnesthesiaCase) -> Path:
    path = FORM_DIR / f"{case.token_date.isoformat()}-{case.token_number}-form.pdf"
    c = Canvas(str(path), pagesize=A4)
    patient = _patient(case)
    page_w, page_h = A4
    margin = 13 * mm
    content_w = page_w - 2 * margin

    c.setTitle(f"CMH Anaesthesia Form - {case.token_number}")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_w / 2, page_h - 16 * mm, "CMH DHAKA")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(page_w / 2, page_h - 22 * mm, "DEPARTMENT OF ANAESTHESIOLOGY")
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_w / 2, page_h - 27 * mm, "PRE-ANAESTHETIC CHECK-UP FORM • CONFIDENTIAL")
    y = page_h - 38 * mm
    _line(c, "No:", margin, y, 43 * mm, patient.service_number)
    _line(c, "Rank:", margin + 46 * mm, y, 39 * mm, patient.rank.label)
    _line(c, "Name:", margin + 89 * mm, y, 70 * mm, patient.name)
    _line(c, "Unit:", margin + 163 * mm, y, 21 * mm, patient.unit)
    y -= 8 * mm
    _line(c, "Age:", margin, y, 30 * mm, str(patient.age))
    _line(c, "Sex:", margin + 35 * mm, y, 30 * mm, patient.sex.title())
    _line(c, "Disease:", margin + 70 * mm, y, 114 * mm)
    y -= 9 * mm
    _line(c, "Proposed surgery:", margin, y, content_w, case.proposed_surgery)
    y -= 9 * mm
    _line(c, "Proposed anaesthetic:", margin, y, content_w, case.proposed_anesthetic)
    y -= 10 * mm
    _section(c, "KEY POINTS & INVESTIGATIONS", margin, y, 57 * mm)
    _section(c, "COMORBIDITY / DATE / MEDICATION", margin + 61 * mm, y, 123 * mm)
    left_items = ["Weight", "Blood group", "HBsAg / HBC", "Drug allergy", "Denture", "Hb / Hct", "WBC", "FBS / RBS", "Electrolytes", "Urea / Creatinine", "LFT", "ECG", "Echo", "CXR", "Coag profile", "USG", "CT / MRI", "Others / Urine"]
    right_items = ["HTN", "DM / DAN", "COPD / BA / ILD / OSA / Others", "MI / Angina / CABG / VHD / PTCA / Pacemaker", "Stroke / CVD / PD / AD / Others", "Jaundice / Obstructive / Infective / HELLP", "Thyroid status", "Renal disease / Dialysis", "Anticoagulants / Smoking / Others"]
    row_y = y - 10 * mm
    for index, label in enumerate(left_items):
        _line(c, f"{label}:", margin, row_y - index * 7 * mm, 57 * mm)
    for index, label in enumerate(right_items):
        _line(c, f"{label}:", margin + 61 * mm, row_y - index * 8 * mm, 123 * mm)
    box_y = row_y - 82 * mm
    c.rect(margin + 61 * mm, box_y - 52 * mm, 123 * mm, 51 * mm)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(margin + 64 * mm, box_y - 5 * mm, "PHYSICAL EXAMINATION")
    physical = ["Consciousness / GCS", "Anaemia", "Dehydration", "Oedema", "Dyspnoea", "Abdomen", "Disability", "Mouth opening", "Pulse", "BP", "Temperature", "Respiration", "Heart", "Lungs", "Neck movement", "Others"]
    for i, label in enumerate(physical):
        col = i // 8
        row = i % 8
        _line(c, f"{label}:", margin + (64 + col * 60) * mm, box_y - (11 + row * 5) * mm, 56 * mm)
    bottom_y = 39 * mm
    c.roundRect(margin, bottom_y, content_w, 28 * mm, 3 * mm)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 3 * mm, bottom_y + 21 * mm, "GRADING:  ASA I / II / III / IV / V / E     NYHA 1 / 2 / 3 / 4     Mallampati 1 / 2 / 3 / 4")
    c.drawString(margin + 3 * mm, bottom_y + 14 * mm, "CASE:  [ ] ACCEPTED   [ ] GA   [ ] TIVA   [ ] RA   [ ] BPB   [ ] NERVE BLOCK   [ ] LA   [ ] DEFERRED")
    c.drawString(margin + 3 * mm, bottom_y + 7 * mm, "SPECIAL NOTE / PRE-ANAESTHETIC ADVICE:")
    c.setFont("Helvetica", 7)
    c.drawRightString(page_w - margin, 18 * mm, "Anaesthesiologist (Rank & Name / Signature)")
    c.showPage()

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(page_w / 2, page_h - 16 * mm, "ANAESTHETIC NOTE")
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_w / 2, page_h - 22 * mm, "CONFIDENTIAL")
    y = page_h - 34 * mm
    sections = [
        ("OPERATION PERFORMED", 14),
        ("OPERATION DATE / START / END / DURATION", 13),
        ("LINES / AIRWAY / VENTILATION", 17),
        ("GA / TIVA / SAB / EPIDURAL / BPB / PERIPHERAL NERVE BLOCKS", 31),
        ("DELIVERY NOTE (LUCS)", 14),
    ]
    for title, height in sections:
        _section(c, title, margin, y, content_w)
        c.rect(margin, y - height * mm, content_w, (height - 3) * mm)
        y -= (height + 3) * mm
    _section(c, "PER-OP MONITORING", margin, y, content_w)
    y -= 8 * mm
    monitor_style = ParagraphStyle(
        "monitor-header",
        fontName="Helvetica-Bold",
        fontSize=5.4,
        leading=6,
        alignment=TA_CENTER,
    )
    columns = [
        Paragraph(label, monitor_style)
        for label in ("TIME", "PULSE", "BP", "SpO2", "URINE OUTPUT", "BLOOD LOSS", "FLUID / BLOOD INTAKE", "DRUGS / INFUSIONS")
    ]
    widths = [13, 13, 18, 16, 22, 20, 32, 50]
    table = Table(
        [columns] + [[""] * len(columns) for _ in range(6)],
        colWidths=[width * mm for width in widths],
        rowHeights=[7 * mm] + [7 * mm] * 6,
    )
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#526D64")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9F2EE")), ("ALIGN", (0, 0), (-1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    table.wrapOn(c, content_w, 80 * mm)
    table.drawOn(c, margin, y - 49 * mm)
    y -= 56 * mm
    for title, height in [("BLOOD TRANSFUSION", 10), ("OTHER MANAGEMENT NOTES", 18), ("POST-ANAESTHETIC ADVICE / ANALGESIA / INSTRUCTIONS", 28)]:
        _section(c, title, margin, y, content_w)
        c.rect(margin, y - height * mm, content_w, (height - 3) * mm)
        y -= (height + 3) * mm
    c.setFont("Helvetica", 7)
    c.drawString(margin, 10 * mm, "Anaesthesia Assistant (Rank & Name / Signature)")
    c.drawRightString(page_w - margin, 10 * mm, "Anaesthesiologist (Rank & Name / Signature)")
    c.save()
    return path


def queue_token_print(path: Path, settings: dict) -> tuple[bool, str]:
    return _queue_pdf(
        path,
        str(settings.get("token_printer_name", "")).strip(),
        bool(settings.get("token_auto_print", False)),
        "Token",
    )


def queue_form_print(path: Path, settings: dict) -> tuple[bool, str]:
    return _queue_pdf(
        path,
        str(settings.get("form_printer_name", "")).strip(),
        bool(settings.get("form_auto_print", False)),
        "Form",
    )


def _queue_pdf(path: Path, printer: str, enabled: bool, document_name: str) -> tuple[bool, str]:
    if not enabled:
        return False, f"{document_name} PDF generated; automatic printing is disabled"
    if not printer:
        return False, f"{document_name} PDF generated; no printer queue is configured"
    try:
        if platform.system() == "Windows":
            sumatra = os.getenv("CMH_ANESTHESIA_SUMATRA_PATH", r"C:\Program Files\SumatraPDF\SumatraPDF.exe")
            subprocess.run([sumatra, "-print-to", printer, "-silent", str(path)], check=True, timeout=45)
        else:
            subprocess.run(["lp", "-d", printer, str(path)], check=True, timeout=45, capture_output=True)
        return True, f"Queued on {printer}"
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        return False, f"{document_name} PDF generated, but printer queue failed: {type(exc).__name__}"
