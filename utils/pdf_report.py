"""
pdf_report.py — builds a monthly patient health report as a downloadable PDF.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

TEAL = colors.HexColor("#0F7173")
NAVY = colors.HexColor("#0B2545")
MINT = colors.HexColor("#EAF6F6")
CORAL = colors.HexColor("#E63950")


def build_monthly_report_pdf(patient, year, month, logs, diagnoses_by_log):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18 * mm, bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title=f"SymptTrack Report {year}-{month:02d}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleBrand", parent=styles["Title"], textColor=TEAL, fontSize=22, spaceAfter=2)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], textColor=NAVY, fontSize=11, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=TEAL, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13)
    center = ParagraphStyle("Center", parent=styles["Normal"], alignment=TA_CENTER, textColor=colors.grey, fontSize=8)

    elements = []
    elements.append(Paragraph("🩺 SymptTrack — Monthly Health Report", title_style))
    month_name = datetime(year, month, 1).strftime("%B %Y")
    elements.append(Paragraph(f"{month_name}", sub_style))
    elements.append(HRFlowable(width="100%", color=TEAL, thickness=1.2))
    elements.append(Spacer(1, 10))

    # Patient info block
    info_data = [
        ["Patient", patient.get("full_name", "-")],
        ["Email", patient.get("email", "-")],
        ["Gender", (patient.get("gender") or "-").replace("_", " ").title()],
        ["Blood Group", patient.get("blood_group") or "-"],
        ["Report Generated", datetime.now().strftime("%d %b %Y, %I:%M %p")],
    ]
    info_table = Table(info_data, colWidths=[110, 380])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), TEAL),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8))

    # Summary stats
    total_logs = len(logs)
    avg_severity = round(sum(l["severity"] for l in logs) / total_logs, 1) if total_logs else 0
    elements.append(Paragraph("📊 Month Summary", h2))
    summary_data = [["Days Logged", "Avg. Severity", "Total Diagnoses Suggested"],
                     [str(total_logs), f"{avg_severity} / 5", str(sum(len(v) for v in diagnoses_by_log.values()))]]
    summary_table = Table(summary_data, colWidths=[160, 160, 170])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 1), (-1, 1), MINT),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CFE8E8")),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 10))

    # Daily log table
    elements.append(Paragraph("📅 Daily Symptom Log", h2))
    table_data = [["Date", "Symptoms", "Severity", "Top Suggested Diagnosis"]]
    for log in sorted(logs, key=lambda x: x["log_date"]):
        diags = diagnoses_by_log.get(log["id"], [])
        top_diag = f"{diags[0]['label']} ({diags[0]['probability']*100:.0f}%)" if diags else "—"
        table_data.append([
            log["log_date"].strftime("%d %b") if hasattr(log["log_date"], "strftime") else str(log["log_date"]),
            Paragraph((log.get("symptoms_text") or "-")[:180], body),
            f"{log['severity']}/5",
            Paragraph(top_diag, body),
        ])

    if len(table_data) == 1:
        elements.append(Paragraph("No symptom entries were logged this month.", body))
    else:
        log_table = Table(table_data, colWidths=[55, 195, 55, 185], repeatRows=1)
        log_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MINT]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7E5E5")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(log_table)

    elements.append(Spacer(1, 18))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#D7E5E5"), thickness=0.8))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "⚠️ This report is generated from self-reported symptoms and an automated decision-support "
        "model. It is not a medical diagnosis. Always consult a licensed healthcare professional "
        "for medical advice.", center))
    elements.append(Paragraph("Generated by SymptTrack 🏥", center))

    doc.build(elements)
    buffer.seek(0)
    return buffer
