import os
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import random

def format_inr(amount: float) -> str:
    return f"Rs. {amount:,.2f}"

def generate_synthetic_fdr_pdf(
    output_path: str,
    bank_name: str,
    branch_name: str,
    ifsc_code: str,
    fdr_number: str,
    amount: float,
    issue_date: date,
    maturity_date: date,
    society_name: str,
    institution_name: str,
    regional_office: str,
    tenure_months: int = 96,
    interest_rate: float = 7.25,
    tamper_metadata: bool = False,
    include_proper_lien: bool = True
) -> str:
    """
    Generates an authentic synthetic Fixed Deposit Receipt PDF for AICTE security deposit demonstration.
    Labels clearly: SYNTHETIC DEMONSTRATION DOCUMENT.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1,
        textColor=colors.HexColor('#1B365D')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#4A5568')
    )

    cell_bold = ParagraphStyle('CB', fontName='Helvetica-Bold', fontSize=9, leading=12)
    cell_norm = ParagraphStyle('CN', fontName='Helvetica', fontSize=9, leading=12)
    notice_style = ParagraphStyle(
        'Notice',
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor('#DC2626')
    )

    elements = []

    # Watermark / Notice
    elements.append(Paragraph("<b>[ SYNTHETIC DEMONSTRATION INSTRUMENT - FOR AICTE DEPOSAFE EVALUATION ONLY ]</b>", notice_style))
    elements.append(Spacer(1, 8))

    # Bank Header
    elements.append(Paragraph(f"<b>{bank_name.upper()}</b>", title_style))
    elements.append(Paragraph(f"Branch: {branch_name} &nbsp;|&nbsp; IFSC Code: {ifsc_code} &nbsp;|&nbsp; Core Banking System", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1B365D'), spaceBefore=2, spaceAfter=10))

    elements.append(Paragraph("<b>SPECIAL TERM DEPOSIT RECEIPT / SECURITY DEPOSIT CERTIFICATE</b>", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.HexColor('#0F172A'))))
    elements.append(Spacer(1, 10))

    if include_proper_lien:
        lien_clause = f"Pledged under Lien jointly in the name of <b>Regional Officer, AICTE ({regional_office})</b> and President / Secretary, <b>{society_name}</b> (for {institution_name}). Cannot be encashed or released without prior written NOC from the Competent Authority, AICTE."
    else:
        lien_clause = f"Fixed Deposit held singly in the name of {society_name}. No specific government lien marked on face of deposit."

    table_data = [
        [
            Paragraph("<b>FDR Account Number:</b>", cell_bold), Paragraph(f"<b>{fdr_number}</b>", cell_bold),
            Paragraph("<b>Deposit Amount:</b>", cell_bold), Paragraph(f"<b>{format_inr(amount)}</b>", cell_bold)
        ],
        [
            Paragraph("<b>Date of Issue:</b>", cell_bold), Paragraph(issue_date.strftime("%d-%b-%Y"), cell_norm),
            Paragraph("<b>Date of Maturity:</b>", cell_bold), Paragraph(maturity_date.strftime("%d-%b-%Y"), cell_norm)
        ],
        [
            Paragraph("<b>Tenure (Months):</b>", cell_bold), Paragraph(f"{tenure_months} Months", cell_norm),
            Paragraph("<b>Interest Rate (% p.a.):</b>", cell_bold), Paragraph(f"{interest_rate:.2f}%", cell_norm)
        ],
        [
            Paragraph("<b>Account Holder(s):</b>", cell_bold), Paragraph(society_name, cell_norm),
            Paragraph("<b>Beneficiary / Institution:</b>", cell_bold), Paragraph(institution_name, cell_norm)
        ],
        [
            Paragraph("<b>Lien / Joint Holding Clause:</b>", cell_bold),
            Paragraph(lien_clause, cell_norm),
            Paragraph("<b>Auto-Renewal Terms:</b>", cell_bold),
            Paragraph("Yes - Automatically renewed upon maturity until release order.", cell_norm)
        ]
    ]

    t = Table(table_data, colWidths=[130, 230, 130, 230])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('SPAN', (1, 4), (1, 4)),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 25))

    # Signatures & Verification Stamp Section
    sig_data = [
        [
            Paragraph("<b>Core Banking Generated Ref:</b><br/>TXN-FDR-" + fdr_number[-8:] + "<br/>CBS Server: HOST-DELHI-04", cell_norm),
            Paragraph("<b>Verified By Branch Accountant:</b><br/>[Official Digital Signature]<br/>Emp ID: BK-77492", cell_norm),
            Paragraph("<b>Authorized Signatory / Branch Manager:</b><br/>For " + bank_name + "<br/>[Official Seal & Signature]", cell_bold)
        ]
    ]
    st = Table(sig_data, colWidths=[240, 240, 240])
    st.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(st)

    def on_first_page(canv, _):
        if tamper_metadata:
            canv.setCreator("Canva PDF Designer v2.4 (tampered-producer-flag)")
            canv.setAuthor("Adobe Photoshop CC 2024 - Layered Output")
        else:
            canv.setCreator("CoreBankingSystem CBS-PDF Engine v4.1")
            canv.setAuthor("Authorized Bank Server")
        canv.setTitle(f"Security Deposit FDR - {fdr_number}")

    doc.build(elements, onFirstPage=on_first_page)
    return output_path
