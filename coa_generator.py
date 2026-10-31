from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os

def generate_coa_pdf(sample_data, results_data, product_name, output_path):
    """
    Generate a Certificate of Analysis PDF for Nordec Lab.
    sample_data: dict with sample info
    results_data: list of dicts with test results + conformity + specs
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=12*mm,
        bottomMargin=12*mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'TitleCustom',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=2*mm,
        textColor=colors.HexColor("#1a365d"),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=1*mm,
        textColor=colors.HexColor("#2c5282")
    )
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#1a365d")
    )
    normal_style = ParagraphStyle(
        'NormalCustom',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=7,
        leading=9
    )
    center_style = ParagraphStyle(
        'Center',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER
    )

    story = []

    # Header
    story.append(Paragraph("NORDEC LABORATORY", title_style))
    story.append(Paragraph("Lubricating Oils Testing Laboratory", subtitle_style))
    story.append(Paragraph("ISO/IEC 17025 Compliant Testing Services", subtitle_style))
    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a365d")))
    story.append(Spacer(1, 3*mm))

    # Certificate title
    cert_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Heading2'],
        fontSize=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#c53030"),
        spaceAfter=4*mm,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("CERTIFICATE OF ANALYSIS (COA)", cert_style))

    # Sample Information Table
    sample_info = [
        [Paragraph("<b>Sample Code:</b>", normal_style), sample_data.get("sample_code", "-"),
         Paragraph("<b>Report Date:</b>", normal_style), datetime.now().strftime("%Y-%m-%d")],
        [Paragraph("<b>Client:</b>", normal_style), sample_data.get("client_name", "-"),
         Paragraph("<b>Client Ref:</b>", normal_style), sample_data.get("client_ref", "-")],
        [Paragraph("<b>Product / Grade:</b>", normal_style), product_name or "-",
         Paragraph("<b>Equipment ID:</b>", normal_style), sample_data.get("equipment_id", "-")],
        [Paragraph("<b>Collection Date:</b>", normal_style), sample_data.get("collection_date", "-"),
         Paragraph("<b>Received Date:</b>", normal_style), sample_data.get("registered_at", "-")[:10] if sample_data.get("registered_at") else "-"],
        [Paragraph("<b>Collector:</b>", normal_style), sample_data.get("collector_name", "-"),
         Paragraph("<b>Location:</b>", normal_style), sample_data.get("collection_location", "-")],
        [Paragraph("<b>Oil Hours:</b>", normal_style), str(sample_data.get("oil_hours") or "-"),
         Paragraph("<b>Total Hours:</b>", normal_style), str(sample_data.get("total_hours") or "-")],
    ]

    t = Table(sample_info, colWidths=[35*mm, 55*mm, 35*mm, 55*mm])
    t.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#edf2f7")),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor("#edf2f7")),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#a0aec0")),
    ]))
    story.append(t)
    story.append(Spacer(1, 4*mm))

    # Results Table Header
    story.append(Paragraph("<b>TEST RESULTS</b>", header_style))
    story.append(Spacer(1, 1.5*mm))

    # Results header
    header = [
        Paragraph("<b>Test Parameter</b>", small_style),
        Paragraph("<b>Method</b>", small_style),
        Paragraph("<b>Unit</b>", small_style),
        Paragraph("<b>Result</b>", small_style),
        Paragraph("<b>Specification</b>", small_style),
        Paragraph("<b>Conformity</b>", small_style),
    ]

    data = [header]

    overall_pass = True
    for r in results_data:
        result_val = r.get("value")
        if result_val is None and r.get("value_text"):
            result_str = r.get("value_text")
        elif result_val is not None:
            result_str = f"{result_val:.3f}" if isinstance(result_val, float) else str(result_val)
        else:
            result_str = "-"

        # Spec string
        mn = r.get("min_value")
        mx = r.get("max_value")
        if mn is not None and mx is not None:
            spec_str = f"{mn} – {mx}"
        elif mn is not None:
            spec_str = f"≥ {mn}"
        elif mx is not None:
            spec_str = f"≤ {mx}"
        else:
            spec_str = "-"

        conf = r.get("conformity") or "N/A"
        if conf == "Fail":
            overall_pass = False

        conf_color = {
            "Pass": colors.HexColor("#276749"),
            "Fail": colors.HexColor("#c53030"),
            "Conditional": colors.HexColor("#c05621"),
        }.get(conf, colors.black)

        row = [
            Paragraph(r.get("test_name", "-"), small_style),
            Paragraph(r.get("method", "-")[:25], small_style),
            Paragraph(r.get("unit") or "-", small_style),
            Paragraph(result_str, small_style),
            Paragraph(spec_str, small_style),
            Paragraph(f"<font color='{conf_color.hexval()}'><b>{conf}</b></font>", small_style),
        ]
        data.append(row)

    col_widths = [50*mm, 35*mm, 18*mm, 22*mm, 28*mm, 22*mm]
    results_table = Table(data, colWidths=col_widths, repeatRows=1)
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c5282")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#a0aec0")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
    ]))
    story.append(results_table)
    story.append(Spacer(1, 4*mm))

    # Overall Conformity
    overall_text = "PASS – Meets Specification" if overall_pass else "FAIL – Does Not Meet Specification"
    overall_color = colors.HexColor("#276749") if overall_pass else colors.HexColor("#c53030")
    overall_style = ParagraphStyle(
        'Overall',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        textColor=overall_color,
        fontName='Helvetica-Bold',
        spaceBefore=2*mm,
        spaceAfter=3*mm
    )
    story.append(Paragraph(f"OVERALL CONFORMITY: {overall_text}", overall_style))

    # Notes
    if sample_data.get("notes"):
        story.append(Paragraph(f"<b>Sample Notes:</b> {sample_data.get('notes')}", small_style))
        story.append(Spacer(1, 2*mm))

    # Footer statements (ISO 17025)
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#a0aec0")))
    story.append(Spacer(1, 2*mm))

    statements = [
        "1. The results relate only to the items tested / sampled.",
        "2. This certificate shall not be reproduced except in full, without written approval of Nordec Laboratory.",
        "3. Decision rule for conformity: Simple acceptance (measured value compared directly to specification limits) unless otherwise stated.",
        "4. Measurement uncertainty is available upon request.",
        "5. This laboratory operates in accordance with the principles of ISO/IEC 17025.",
    ]
    for s in statements:
        story.append(Paragraph(s, small_style))

    story.append(Spacer(1, 6*mm))

    # Signatures
    sig_data = [
        [Paragraph("<b>Analyzed by:</b><br/><br/>_________________<br/>Name / Signature", center_style),
         Paragraph("<b>Reviewed by:</b><br/><br/>_________________<br/>Name / Signature", center_style),
         Paragraph("<b>Authorized by:</b><br/><br/>_________________<br/>Lab Manager", center_style)],
    ]
    sig_table = Table(sig_data, colWidths=[60*mm, 60*mm, 60*mm])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(sig_table)

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        f"Generated electronically by Nordec LIMS on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Document controlled under ISO 17025",
        ParagraphStyle('Footer', parent=small_style, alignment=TA_CENTER, textColor=colors.gray)
    ))

    doc.build(story)
    return output_path
