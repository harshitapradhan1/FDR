#!/usr/bin/env python3
"""
DepoSafe Synthetic Dataset Generator (Phase 2)
Generates 80 Institutions, ~150 FDR Documents across 5 distinct bank layouts,
injected with ground-truth labelled forensic and compliance anomalies.
Seed is deterministic (SEED=42) for 100% reproducible benchmarks.
"""

import os
import random
import json
import hashlib
import numpy as np
from datetime import date, timedelta, datetime
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import fitz # PyMuPDF
import cv2
import imagehash

from reportlab.lib.pagesizes import letter, landscape, portrait
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

DEMO_CLOCK_BASE = date(2026, 11, 29)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic")
DOCS_DIR = os.path.join(SYNTHETIC_DIR, "documents")
INSTITUTIONS_DIR = os.path.join(SYNTHETIC_DIR, "institutions")
GROUND_TRUTH_PATH = os.path.join(SYNTHETIC_DIR, "ground_truth.json")
CONTACT_SHEET_PATH = os.path.join(BASE_DIR, "docs", "assets", "contact_sheet.png")

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(INSTITUTIONS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONTACT_SHEET_PATH), exist_ok=True)

# --- Catalogs of Real Fictional Data ---

INDIAN_STATES_REGIONS = [
    ("Delhi", "North Western Regional Office"),
    ("Punjab", "North Western Regional Office"),
    ("Haryana", "North Western Regional Office"),
    ("Uttar Pradesh", "Northern Regional Office"),
    ("Maharashtra", "Western Regional Office"),
    ("Gujarat", "Central Regional Office"),
    ("Karnataka", "South Western Regional Office"),
    ("Tamil Nadu", "Southern Regional Office"),
    ("Telangana", "South Central Regional Office"),
    ("Andhra Pradesh", "South Central Regional Office"),
    ("West Bengal", "Eastern Regional Office"),
    ("Rajasthan", "North Western Regional Office"),
    ("Kerala", "South Western Regional Office"),
    ("Madhya Pradesh", "Central Regional Office"),
]

COLLEGE_PREFIXES = [
    "National", "Aryavrat", "Vidya", "Saraswati", "Vivekananda", "Tagore",
    "APJ Abdul Kalam", "Shivalik", "Kaveri", "Himalayan", "Krishna", "Godavari",
    "Apex", "Zenith", "Sunrise", "Horizon", "Galaxy", "Imperial", "Vanguard",
    "Pioneer", "Global", "Universal", "Metropolitan", "Silicon", "Indus"
]

COLLEGE_TYPES = [
    ("Institute of Technology & Science", "Engineering & Technology", "UG", 3500000.0),
    ("College of Engineering", "Engineering & Technology", "UG", 3500000.0),
    ("Polytechnic College", "Engineering & Technology", "Diploma", 1500000.0),
    ("Institute of Management Studies", "Management", "PG", 1500000.0),
    ("Graduate School of Business", "Management", "PG", 1500000.0),
    ("College of Pharmacy", "Pharmacy", "UG", 2500000.0),
    ("Institute of Pharmaceutical Sciences", "Pharmacy", "Diploma", 1500000.0),
    ("School of Architecture & Planning", "Architecture & Town Planning", "UG", 2000000.0),
]

SOCIETY_SUFFIXES = [
    "Educational Society", "Charitable Trust", "Education Foundation",
    "Vidya Peeth Trust", "Memorial Welfare Society", "Kalyan Samiti", "Educational Academy"
]

PERSON_NAMES = [
    "Dr. Ramesh Sharma", "Prof. Ananya Verma", "Dr. Suresh Patil", "Dr. Sunita Deshmukh",
    "Prof. Rajeshwari Iyer", "Dr. Vikramaditya Rao", "Dr. Arvind Swaminathan", "Prof. Meenakshi Joshi",
    "Dr. Harish Chandra", "Prof. Deepa Nair", "Dr. Alok Srivastava", "Dr. Gurpreet Singh",
    "Prof. Amitava Mukherjee", "Dr. Kavita Reddy", "Prof. Manoj Tiwary", "Dr. Sanjay Kulkarni"
]

BANK_LAYOUTS = [
    "BHARAT_NATIONAL_BANK",
    "APEX_COMMERCIAL_BANK",
    "GRAMIN_VIKAS_BANK",
    "HINDUSTAN_MERCANTILE_BANK",
    "PRAGATI_COOPERATIVE_BANK"
]

BANK_DETAILS = {
    "BHARAT_NATIONAL_BANK": {
        "name": "Bharat National Bank",
        "type": "SCHEDULED_COMMERCIAL",
        "ifsc_prefix": "BNBN",
        "primary_color": "#1B365D",
        "accent_color": "#E67E22",
        "header_hi": "भारत नेशनल बैंक (सार्वजनिक क्षेत्र का उपक्रम)"
    },
    "APEX_COMMERCIAL_BANK": {
        "name": "Apex Commercial Bank",
        "type": "SCHEDULED_COMMERCIAL",
        "ifsc_prefix": "APEX",
        "primary_color": "#781428",
        "accent_color": "#D4AF37",
        "header_hi": "एपेक्स कमर्शियल बैंक लि."
    },
    "GRAMIN_VIKAS_BANK": {
        "name": "Gramin Vikas Bank",
        "type": "SCHEDULED_COMMERCIAL",
        "ifsc_prefix": "GVBK",
        "primary_color": "#138808",
        "accent_color": "#C29B38",
        "header_hi": "ग्रामीण विकास बैंक (प्रायोजित अनुसूचित बैंक)"
    },
    "HINDUSTAN_MERCANTILE_BANK": {
        "name": "Hindustan Mercantile Bank",
        "type": "SCHEDULED_COMMERCIAL",
        "ifsc_prefix": "HMBL",
        "primary_color": "#1E293B",
        "accent_color": "#0284C7",
        "header_hi": "हिंदुस्तान मर्केंटाइल बैंक"
    },
    "PRAGATI_COOPERATIVE_BANK": {
        "name": "Pragati Urban Cooperative Bank",
        "type": "NON_SCHEDULED",
        "ifsc_prefix": "PUCB",
        "primary_color": "#EA580C",
        "accent_color": "#4338CA",
        "header_hi": "प्रगति अर्बन को-ऑपरेटिव बैंक (गैर-अनुसूचित)"
    }
}

INJECTED_ISSUE_TYPES = [
    "missing_mandatory_field",
    "maturity_before_issue_date",
    "amount_edited",
    "maturity_mismatch_with_bank_letter",
    "wrong_bank_name",
    "duplicate_fdr_number_cross_institution",
    "same_bank_and_number_different_file",
    "same_file_reused",
    "perceptual_hash_near_collision",
    "metadata_anomaly",
    "wrong_document_type_uploaded",
    "expired_fdr",
    "renewal_missing",
    "release_request_unmet_conditions"
]

def format_inr(val):
    return f"Rs. {val:,.2f}"

def compute_file_sha256(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def apply_scan_imperfections(input_pdf_path, output_img_path, rotate_deg=0.0, blur=False, noise=False):
    """Converts the first page of PDF to an image and applies realistic scan noise/rotation."""
    doc = fitz.open(input_pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()

    if abs(rotate_deg) > 0.01:
        img = img.rotate(rotate_deg, resample=Image.BICUBIC, expand=True, fillcolor="white")

    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.7))

    if noise:
        np_img = np.array(img).astype(np.float32)
        gauss = np.random.normal(0, 8.0, np_img.shape)
        np_img = np.clip(np_img + gauss, 0, 255).astype(np.uint8)
        img = Image.fromarray(np_img)

    img.save(output_img_path, "JPEG", quality=88)
    return output_img_path

# --- Document Renderers across 5 Fictional Bank Layouts ---

def render_fdr_pdf(
    out_path,
    layout_code,
    bank_info,
    fdr_number,
    amount,
    issue_date,
    maturity_date,
    tenure_months,
    interest_rate,
    institution_name,
    society_name,
    regional_office,
    lien_clause_text=None,
    tamper_metadata=False,
    missing_field=None,
    pixel_tamper_amount=False
):
    doc = SimpleDocTemplate(
        out_path,
        pagesize=landscape(letter),
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()
    primary = colors.HexColor(bank_info["primary_color"])
    accent = colors.HexColor(bank_info["accent_color"])

    elements = []

    # Mandatory Synthetic Warning
    warn_style = ParagraphStyle('W', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=1, textColor=colors.HexColor('#DC2626'))
    elements.append(Paragraph("<b>[ SYNTHETIC SAMPLE - GENERATED FOR AICTE DEPOSAFE EVALUATION ONLY - NOT A REAL INSTRUMENT ]</b>", warn_style))
    elements.append(Spacer(1, 6))

    # Header section depending on layout
    if layout_code == "BHARAT_NATIONAL_BANK":
        # PSU Style Boxed Banner
        h_style = ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=18, leading=22, alignment=1, textColor=primary)
        sub_style = ParagraphStyle('Sub', fontName='Helvetica-Bold', fontSize=9, leading=12, alignment=1, textColor=accent)
        elements.append(Paragraph(f"<b>{bank_info['name'].upper()}</b>", h_style))
        elements.append(Paragraph(f"{bank_info['header_hi']} &bull; New Delhi Central Branch", sub_style))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=2, color=primary, spaceBefore=4, spaceAfter=8))
        elements.append(Paragraph("<b>TERM DEPOSIT RECEIPT (SPECIAL SECURITY DEPOSIT SCHEME)</b>", ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=12, alignment=1)))

    elif layout_code == "APEX_COMMERCIAL_BANK":
        # Private Corporate Two-Column Header
        elements.append(Table([
            [
                Paragraph(f"<font color='{bank_info['primary_color']}'><b>{bank_info['name']}</b></font><br/><font size=8 color='#64748B'>{bank_info['header_hi']}</font>", ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=16, leading=18)),
                Paragraph(f"<b>IFSC:</b> {bank_info['ifsc_prefix']}0001290<br/><b>CBS Ref:</b> TXN-{fdr_number[-8:]}", ParagraphStyle('R', fontName='Helvetica', fontSize=8, alignment=2))
            ]
        ], colWidths=[500, 240]))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#94A3B8'), spaceBefore=2, spaceAfter=8))
        elements.append(Paragraph("<b>CERTIFICATE OF FIXED DEPOSIT PLEDGED TO AICTE</b>", ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=11, alignment=0, textColor=primary)))

    elif layout_code == "GRAMIN_VIKAS_BANK":
        # Rural Green/Gold Theme with Devanagari Banner
        elements.append(Paragraph(f"<b>{bank_info['header_hi']}</b>", ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=13, alignment=1, textColor=primary)))
        elements.append(Paragraph(f"<b>{bank_info['name'].upper()}</b> &bull; Regd. Head Office", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=15, alignment=1, textColor=primary)))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=2, color=accent, spaceBefore=4, spaceAfter=8))
        elements.append(Paragraph("<b>सावधि जमा रसीद / FIXED DEPOSIT RECEIPT</b>", ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=11, alignment=1)))

    elif layout_code == "HINDUSTAN_MERCANTILE_BANK":
        # Vintage Formal Border Style
        elements.append(Paragraph(f"<b>{bank_info['name'].upper()}</b>", ParagraphStyle('H', fontName='Times-Bold', fontSize=19, alignment=1, textColor=primary)))
        elements.append(Paragraph("Established 1932 &bull; Scheduled Commercial Bank", ParagraphStyle('Sub', fontName='Times-Italic', fontSize=9, alignment=1, textColor=colors.HexColor('#475569'))))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=primary, spaceBefore=4, spaceAfter=8))
        elements.append(Paragraph("<b>OFFICIAL SECURITY DEPOSIT RECEIPT</b>", ParagraphStyle('T', fontName='Times-Bold', fontSize=11, alignment=1)))

    else: # PRAGATI_COOPERATIVE_BANK
        # Urban Co-op layout with Warning Header
        elements.append(Paragraph(f"<b>{bank_info['name'].upper()}</b>", ParagraphStyle('H', fontName='Helvetica-Bold', fontSize=17, alignment=1, textColor=primary)))
        elements.append(Paragraph(f"{bank_info['header_hi']} &bull; Non-Scheduled Urban Cooperative Banking Unit", ParagraphStyle('Sub', fontName='Helvetica', fontSize=8, alignment=1, textColor=colors.HexColor('#DC2626'))))
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=2, color=primary, spaceBefore=4, spaceAfter=8))
        elements.append(Paragraph("<b>MEMBER FIXED DEPOSIT ACKNOWLEDGEMENT</b>", ParagraphStyle('T', fontName='Helvetica-Bold', fontSize=11, alignment=1)))

    elements.append(Spacer(1, 8))

    # Field Data Table Construction
    cell_b = ParagraphStyle('CB', fontName='Helvetica-Bold', fontSize=8.5, leading=11)
    cell_n = ParagraphStyle('CN', fontName='Helvetica', fontSize=8.5, leading=11)

    disp_fdr = "" if missing_field == "fdr_number" else fdr_number
    disp_ifsc = "" if missing_field == "ifsc_code" else f"{bank_info['ifsc_prefix']}0004918"
    disp_amount = "[MISSING]" if missing_field == "amount" else format_inr(amount)
    
    if pixel_tamper_amount:
        disp_amount = f"<font color='#B91C1C'><b>{format_inr(amount)} [MODIFIED]</b></font>"

    disp_mat = "" if missing_field == "maturity_date" else maturity_date.strftime("%d-%b-%Y")

    if not lien_clause_text:
        lien_clause_text = f"Pledged under Lien jointly in the name of <b>Regional Officer, AICTE ({regional_office})</b> and President / Secretary, <b>{society_name}</b> (for {institution_name}). Cannot be encashed or released without prior written NOC from the Competent Authority, AICTE."

    table_data = [
        [
            Paragraph("<b>FDR Account Number:</b>", cell_b), Paragraph(f"<b>{disp_fdr}</b>", cell_b),
            Paragraph("<b>Pledged Deposit Amount:</b>", cell_b), Paragraph(f"<b>{disp_amount}</b>", cell_b)
        ],
        [
            Paragraph("<b>IFSC Code:</b>", cell_b), Paragraph(disp_ifsc, cell_n),
            Paragraph("<b>Interest Rate (% p.a.):</b>", cell_b), Paragraph(f"{interest_rate:.2f}% Compounded Quarterly", cell_n)
        ],
        [
            Paragraph("<b>Date of Issue:</b>", cell_b), Paragraph(issue_date.strftime("%d-%b-%Y"), cell_n),
            Paragraph("<b>Date of Maturity:</b>", cell_b), Paragraph(disp_mat, cell_b)
        ],
        [
            Paragraph("<b>Tenure (Months):</b>", cell_b), Paragraph(f"{tenure_months} Months", cell_n),
            Paragraph("<b>Auto-Renewal Mandate:</b>", cell_b), Paragraph("Yes (Automatic on maturity until release order)", cell_n)
        ],
        [
            Paragraph("<b>Account Holder(s):</b>", cell_b), Paragraph(society_name, cell_n),
            Paragraph("<b>Beneficiary College:</b>", cell_b), Paragraph(institution_name, cell_n)
        ],
        [
            Paragraph("<b>Lien / Joint Holding Clause:</b>", cell_b),
            Paragraph(lien_clause_text, cell_n),
            Paragraph("<b>Branch Code:</b>", cell_b),
            Paragraph("BR-4918 / Reg: DEL-02", cell_n)
        ]
    ]

    t = Table(table_data, colWidths=[120, 240, 120, 260])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('SPAN', (1, 5), (1, 5)),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 15))

    # Signatures Table
    sig_data = [
        [
            Paragraph("<b>Official CBS Audit Ref:</b><br/>TXN-CBS-" + fdr_number[-8:] + "<br/>Host: DEL-SRV-04", cell_n),
            Paragraph("<b>Checked & Verified:</b><br/>[Authorized Bank Seal]<br/>Accountant Emp #7821", cell_n),
            Paragraph(f"<b>For {bank_info['name']}</b><br/>[Authorized Digital Signature]<br/>Branch Manager", cell_b)
        ]
    ]
    st = Table(sig_data, colWidths=[240, 240, 260])
    st.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(st)

    def on_page(canv, _):
        if tamper_metadata:
            canv.setCreator("Canva PDF Designer v2.4 (tampered-producer-flag)")
            canv.setAuthor("Adobe Photoshop CC 2024 - Layered Export")
        else:
            canv.setCreator(f"{bank_info['name']} CBS Document Engine v5.1")
            canv.setAuthor("CoreBankingSystem Server")
        canv.setTitle(f"Security Deposit FDR - {fdr_number}")

    doc.build(elements, onFirstPage=on_page)
    return out_path

def render_bank_confirmation_letter(out_path, bank_name, fdr_number, amount, confirmed_maturity, society_name, mismatch=False):
    """Generates official bank confirmation letter."""
    doc = SimpleDocTemplate(out_path, pagesize=portrait(letter), rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>[ SYNTHETIC SAMPLE - BANK CONFIRMATION LETTER ]</b>", ParagraphStyle('W', fontSize=8, textColor=colors.HexColor('#DC2626'), alignment=1)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>{bank_name.upper()} - CHIEF MANAGER OFFICE</b>", ParagraphStyle('H', fontSize=14, leading=16, textColor=colors.HexColor('#1B365D'), alignment=1)))
    elements.append(Paragraph("Regional Corporate Banking Branch &bull; New Delhi", ParagraphStyle('Sub', fontSize=9, alignment=1, textColor=colors.HexColor('#64748B'))))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1B365D'), spaceBefore=6, spaceAfter=14))

    body_style = ParagraphStyle('B', fontSize=9, leading=14, textColor=colors.HexColor('#0F172A'))
    elements.append(Paragraph(f"<b>Ref No:</b> BCL/CONF/{fdr_number[-6:]}/2024<br/><b>Date:</b> {date.today().strftime('%d-%b-%Y')}", body_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>To:<br/>The Regional Officer,<br/>All India Council for Technical Education (AICTE)</b>", body_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>Subject: Confirmation of Term Deposit Receipt & Lien Marking</b>", ParagraphStyle('SB', fontSize=10, fontName='Helvetica-Bold')))
    elements.append(Spacer(1, 8))

    mat_str = confirmed_maturity.strftime("%d-%b-%Y")
    status_msg = (
        f"We hereby confirm that Fixed Deposit Receipt No. <b>{fdr_number}</b> for an amount of <b>{format_inr(amount)}</b> "
        f"held in the name of <b>{society_name}</b> has been duly created in our core banking system. "
        f"The maturity date recorded in our core banking records is <b>{mat_str}</b>. "
        f"Lien in favor of Regional Officer, AICTE has been successfully registered."
    )
    if mismatch:
        status_msg += "<br/><br/><font color='#DC2626'><b>NOTE ON CBS VARIANCE:</b> Core Banking record maturity schedule reflects tenure lock-in concluding on " + mat_str + " (divergent from physical receipt schedule).</font>"

    elements.append(Paragraph(status_msg, body_style))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("<b>Yours Faithfully,<br/>Chief Manager (Advances & Term Deposits)<br/>" + bank_name + "</b>", body_style))

    doc.build(elements)
    return out_path

def render_utility_bill(out_path, institution_name):
    """Generates a wrong document type (Electricity Utility Bill) for testing wrong_document_type_uploaded."""
    doc = SimpleDocTemplate(out_path, pagesize=portrait(letter), rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("<b>[ SYNTHETIC SAMPLE - UTILITY BILL / WRONG DOCUMENT TYPE ]</b>", ParagraphStyle('W', fontSize=8, textColor=colors.HexColor('#DC2626'), alignment=1)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>STATE ELECTRICITY DISTRIBUTION COMPANY LIMITED</b>", ParagraphStyle('H', fontSize=14, leading=16, alignment=1, textColor=colors.HexColor('#0F172A'))))
    elements.append(Paragraph("Monthly High Tension (HT) Commercial Power Bill", ParagraphStyle('Sub', fontSize=9, alignment=1)))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0F172A'), spaceBefore=6, spaceAfter=14))

    body_style = ParagraphStyle('B', fontSize=9, leading=13)
    elements.append(Paragraph(f"<b>Consumer Name:</b> {institution_name}<br/><b>CA Number:</b> 9948271038<br/><b>Bill Month:</b> OCT 2024<br/><b>Amount Due:</b> Rs. 48,920.00", body_style))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("Notice: This is a utility electricity tariff bill and NOT an approved financial security deposit certificate pledged to AICTE.", ParagraphStyle('N', fontSize=9, fontName='Helvetica-Oblique', textColor=colors.HexColor('#B91C1C'))))

    doc.build(elements)
    return out_path

# --- Main Dataset Generation Logic ---

def generate_phase2_synthetic_dataset():
    print(f"=== Starting Phase 2 Synthetic Dataset Generation (Seed: {SEED}) ===")
    
    institutions_data = []
    fdrs_data = []
    documents_data = []
    ground_truth_cases = []

    # Counters
    total_inst = 80
    fdr_counter = 1000

    # 1. Select 5 institutions for 5-Year Lifecycle Passport History (Renewals)
    passport_inst_indices = set(range(5))

    # Global pool of duplicate FDR numbers for testing collision
    duplicate_pool = [
        {"bank_name": "Bharat National Bank", "fdr_number": "BNB-DUP-99112233"},
        {"bank_name": "Apex Commercial Bank", "fdr_number": "APEX-COLLIDE-778899"},
        {"bank_name": "Gramin Vikas Bank", "fdr_number": "GVB-SHARED-445566"},
    ]

    # Pre-generated shared document byte hash for exact SHA-256 reuse
    shared_pdf_template_path = os.path.join(DOCS_DIR, "SHARED_REUSED_INSTRUMENT.pdf")
    render_fdr_pdf(
        shared_pdf_template_path,
        "BHARAT_NATIONAL_BANK",
        BANK_DETAILS["BHARAT_NATIONAL_BANK"],
        "BNB-SHARED-BYTE-777",
        3500000.0,
        date(2024, 1, 15),
        date(2032, 1, 15),
        96,
        7.25,
        "Shared Foundation College",
        "Apex Trust",
        "North Western Regional Office"
    )
    shared_sha256 = compute_file_sha256(shared_pdf_template_path)

    for i in range(total_inst):
        inst_id = i + 1
        aicte_id = f"1-{1000000000 + i * 137}"
        state_info = INDIAN_STATES_REGIONS[i % len(INDIAN_STATES_REGIONS)]
        state_name, regional_office = state_info
        
        prefix = COLLEGE_PREFIXES[i % len(COLLEGE_PREFIXES)]
        type_info = COLLEGE_TYPES[i % len(COLLEGE_TYPES)]
        c_suffix, category, level, base_amount = type_info

        inst_name = f"{prefix} {c_suffix}"
        soc_name = f"{prefix} {SOCIETY_SUFFIXES[i % len(SOCIETY_SUFFIXES)]}"
        signatory = PERSON_NAMES[i % len(PERSON_NAMES)]

        # Specific Concession logic
        inst_type = "Normal"
        if i % 7 == 0:
            inst_type = "Women"
        elif i % 11 == 0:
            inst_type = "Minority"

        inst_obj = {
            "id": inst_id,
            "aicte_id": aicte_id,
            "name": inst_name,
            "society_or_trust_name": soc_name,
            "category": category,
            "program_level": level,
            "institution_type": inst_type,
            "state": state_name,
            "regional_office": regional_office,
            "address": f"Campus Road, Sector {i%30 + 1}, {state_name}",
            "contact_email": f"principal@{prefix.lower().replace(' ', '')}{inst_id}.edu.in",
            "contact_phone": f"+91 11 {20000000 + i*99}",
            "authorized_signatory_name": signatory,
            "has_lifecycle_passport": (i in passport_inst_indices)
        }
        institutions_data.append(inst_obj)

        # Decide FDR Count: 1 to 3 FDRs (targeting ~150 total FDR documents)
        num_fdrs = 3 if (i in passport_inst_indices or i % 3 == 0) else (2 if i % 2 == 0 else 1)

        # Hero Demo Case at Institution index 0
        is_hero_inst = (i == 0)

        for f_idx in range(num_fdrs):
            fdr_counter += 1
            fdr_id = fdr_counter
            
            # Select bank layout
            layout_code = BANK_LAYOUTS[(i + f_idx) % len(BANK_LAYOUTS)]
            bank_info = BANK_DETAILS[layout_code]

            # Injected issue determination (30% clean, 70% with 1-3 issues)
            # Inst 0 is hero case
            injected_issues = []
            
            if is_hero_inst and f_idx == 0:
                # HERO CASE
                injected_issues = [
                    "duplicate_fdr_number_cross_institution",
                    "maturity_mismatch_with_bank_letter",
                    "metadata_anomaly"
                ]
                fdr_num = "BNB-DEL-HERO-1000"
                amount = 1000000.0 # Illustrative Rs 10 Lakhs
                issue_d = date(2024, 11, 15)
                mat_d = date(2032, 11, 15) # 8 years on certificate
                bank_letter_mat = date(2026, 11, 15) # Mismatch in bank letter
                tamper_meta = True
                pixel_tamper = False
                missing_field = None
                is_duplicate = True
            elif (i + f_idx) % 10 in [1, 2, 3]:
                # CLEAN CASE (~30%)
                fdr_num = f"{bank_info['ifsc_prefix']}-{state_name[:3].upper()}-{fdr_id}"
                amount = base_amount
                issue_d = DEMO_CLOCK_BASE - timedelta(days=random.randint(100, 600))
                # Maturity relative to demo clock
                if i % 5 == 0:
                    mat_d = DEMO_CLOCK_BASE + timedelta(days=60) # +60 days upcoming
                elif i % 7 == 0:
                    mat_d = DEMO_CLOCK_BASE + timedelta(days=12) # +12 days T-15 escalation
                elif i % 9 == 0:
                    mat_d = DEMO_CLOCK_BASE + timedelta(days=3)  # +3 days critical
                else:
                    mat_d = issue_d + timedelta(days=96 * 30) # standard 8 years
                
                bank_letter_mat = mat_d
                tamper_meta = False
                pixel_tamper = False
                missing_field = None
                is_duplicate = False
            else:
                # ANOMALOUS CASE (~70% with 1-3 issues)
                issue_choice = INJECTED_ISSUE_TYPES[(i + f_idx) % len(INJECTED_ISSUE_TYPES)]
                injected_issues.append(issue_choice)
                
                # Maybe second issue
                if (i + f_idx) % 4 == 0:
                    second_choice = INJECTED_ISSUE_TYPES[(i + f_idx + 3) % len(INJECTED_ISSUE_TYPES)]
                    if second_choice != issue_choice:
                        injected_issues.append(second_choice)

                fdr_num = f"{bank_info['ifsc_prefix']}-{state_name[:3].upper()}-{fdr_id}"
                amount = base_amount
                issue_d = DEMO_CLOCK_BASE - timedelta(days=random.randint(100, 500))
                mat_d = issue_d + timedelta(days=96 * 30)
                bank_letter_mat = mat_d
                tamper_meta = False
                pixel_tamper = False
                missing_field = None
                is_duplicate = False

                # Apply specific issue logic
                if "missing_mandatory_field" in injected_issues:
                    missing_field = "ifsc_code" if (i % 2 == 0) else "fdr_number"
                if "maturity_before_issue_date" in injected_issues:
                    mat_d = issue_d - timedelta(days=180) # Chronological inversion
                if "amount_edited" in injected_issues:
                    pixel_tamper = True
                if "maturity_mismatch_with_bank_letter" in injected_issues:
                    bank_letter_mat = mat_d - timedelta(days=730) # 2 year gap
                if "metadata_anomaly" in injected_issues:
                    tamper_meta = True
                if "wrong_bank_name" in injected_issues:
                    layout_code = "PRAGATI_COOPERATIVE_BANK"
                    bank_info = BANK_DETAILS[layout_code]
                if "duplicate_fdr_number_cross_institution" in injected_issues:
                    dup = duplicate_pool[i % len(duplicate_pool)]
                    bank_info = BANK_DETAILS["BHARAT_NATIONAL_BANK"]
                    fdr_num = dup["fdr_number"]
                    is_duplicate = True
                if "expired_fdr" in injected_issues:
                    mat_d = DEMO_CLOCK_BASE - timedelta(days=45) # Overdue

            # Lifecycle Passport Chain logic for first 5 institutions
            predecessor_id = None
            if i in passport_inst_indices and f_idx > 0:
                predecessor_id = fdr_id - 1
                issue_d = date(2019 + (f_idx * 3), 4, 15)
                mat_d = date(2022 + (f_idx * 3), 4, 15)

            # File Paths
            pdf_filename = f"FDR_{fdr_id}_{layout_code}.pdf"
            jpg_filename = f"FDR_{fdr_id}_{layout_code}.jpg"
            pdf_path = os.path.join(DOCS_DIR, pdf_filename)
            jpg_path = os.path.join(DOCS_DIR, jpg_filename)

            # Generate PDF
            if "wrong_document_type_uploaded" in injected_issues:
                render_utility_bill(pdf_path, inst_name)
            elif "same_file_reused" in injected_issues:
                # Copy identical byte-for-byte SHA256 file
                with open(shared_pdf_template_path, "rb") as f_in, open(pdf_path, "wb") as f_out:
                    f_out.write(f_in.read())
            else:
                render_fdr_pdf(
                    out_path=pdf_path,
                    layout_code=layout_code,
                    bank_info=bank_info,
                    fdr_number=fdr_num,
                    amount=amount,
                    issue_date=issue_d,
                    maturity_date=mat_d,
                    tenure_months=96,
                    interest_rate=7.20,
                    institution_name=inst_name,
                    society_name=soc_name,
                    regional_office=regional_office,
                    tamper_metadata=tamper_meta,
                    missing_field=missing_field,
                    pixel_tamper_amount=pixel_tamper
                )

            # Apply realistic scan imperfections (rotation, noise, blur) and convert to JPG
            rot = 0.0
            add_blur = False
            add_noise = False
            if (i + f_idx) % 4 == 1:
                rot = 1.1 # Mild rotation tilt
            elif (i + f_idx) % 4 == 2:
                add_noise = True
            elif (i + f_idx) % 4 == 3:
                add_blur = True

            apply_scan_imperfections(pdf_path, jpg_path, rotate_deg=rot, blur=add_blur, noise=add_noise)

            # Compute actual hashes
            sha256_hash = compute_file_sha256(pdf_path)
            pil_img = Image.open(jpg_path)
            phash_str = str(imagehash.phash(pil_img))
            pil_img.close()

            # Render bank confirmation letter for this FDR
            letter_pdf_filename = f"CONF_LETTER_{fdr_id}.pdf"
            letter_pdf_path = os.path.join(DOCS_DIR, letter_pdf_filename)
            has_letter_mismatch = "maturity_mismatch_with_bank_letter" in injected_issues
            render_bank_confirmation_letter(
                letter_pdf_path,
                bank_info["name"],
                fdr_num,
                amount,
                bank_letter_mat,
                soc_name,
                mismatch=has_letter_mismatch
            )

            # Build FDR Record Entry
            fdr_entry = {
                "id": fdr_id,
                "internal_fdr_id": f"FDR-INT-{fdr_id}",
                "lineage_id": f"LIN-{inst_id}-{f_idx}",
                "institution_id": inst_id,
                "bank_name": bank_info["name"],
                "branch_name": "New Delhi Central Branch",
                "ifsc_code": f"{bank_info['ifsc_prefix']}0004918",
                "fdr_number": fdr_num,
                "amount": amount,
                "issue_date": issue_d.isoformat(),
                "maturity_date": mat_d.isoformat(),
                "tenure_months": 96,
                "predecessor_fdr_id": predecessor_id,
                "status": "SUPERSEDED" if predecessor_id else ("EXPIRING" if (mat_d - DEMO_CLOCK_BASE).days <= 30 else "ACTIVE"),
                "documents": [
                    {
                        "file_name": pdf_filename,
                        "file_path": pdf_path,
                        "image_path": jpg_path,
                        "doc_type": "FDR_CERTIFICATE",
                        "sha256": sha256_hash,
                        "phash": phash_str
                    },
                    {
                        "file_name": letter_pdf_filename,
                        "file_path": letter_pdf_path,
                        "doc_type": "BANK_CONFIRMATION_LETTER"
                    }
                ],
                "injected_issues": injected_issues,
                "is_clean": len(injected_issues) == 0,
                "is_hero_case": (is_hero_inst and f_idx == 0)
            }
            fdrs_data.append(fdr_entry)

    # Save Ground Truth Catalog
    ground_truth = {
        "dataset_name": "DepoSafe AICTE Synthetic Evaluation Benchmark",
        "version": "2.0.0",
        "deterministic_seed": SEED,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_institutions": len(institutions_data),
            "total_fdrs": len(fdrs_data),
            "clean_fdrs_count": sum(1 for f in fdrs_data if f["is_clean"]),
            "anomalous_fdrs_count": sum(1 for f in fdrs_data if not f["is_clean"]),
            "clean_percentage": round(sum(1 for f in fdrs_data if f["is_clean"]) / len(fdrs_data) * 100, 1),
            "anomalous_percentage": round(sum(1 for f in fdrs_data if not f["is_clean"]) / len(fdrs_data) * 100, 1),
            "bank_layouts_represented": BANK_LAYOUTS,
            "injected_issue_types_catalog": INJECTED_ISSUE_TYPES
        },
        "hero_demo_case": {
            "fdr_number": "BNB-DEL-HERO-1000",
            "institution_name": institutions_data[0]["name"],
            "aicte_id": institutions_data[0]["aicte_id"],
            "amount": 1000000.0,
            "injected_issues": [
                "duplicate_fdr_number_cross_institution",
                "maturity_mismatch_with_bank_letter",
                "metadata_anomaly"
            ],
            "description": "Hero Demo Case: Rs 10 Lakhs illustrative FDR, cross-institution duplicate collision, maturity mismatch vs bank letter, Adobe Photoshop metadata signature."
        },
        "institutions": institutions_data,
        "fdrs": fdrs_data
    }

    with open(GROUND_TRUTH_PATH, "w") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated {len(institutions_data)} institutions and {len(fdrs_data)} FDR instruments.")
    print(f"Ground truth catalog saved to: {GROUND_TRUTH_PATH}")

    # Generate Contact Sheet Image
    generate_contact_sheet(fdrs_data)

    return ground_truth

def generate_contact_sheet(fdrs_data):
    """
    Assembles a visual contact sheet of 10 diverse documents showcasing:
    - 5 different bank layouts
    - Scan noise, rotation tilt, blur
    - Tampered amount overlay and bank confirmation letters
    Saves to /docs/assets/contact_sheet.png.
    """
    print("Generating visual contact sheet in docs/assets/contact_sheet.png...")
    
    # Pick 10 representative FDR images
    sample_images = []
    
    # Hero case first
    hero = next(f for f in fdrs_data if f["is_hero_case"])
    sample_images.append((hero["documents"][0]["image_path"], "HERO: Bharat National Bank (Photoshop Metadata)"))

    # 1 from each remaining bank layout
    for b_layout in BANK_LAYOUTS[1:]:
        match = next(f for f in fdrs_data if b_layout in f["documents"][0]["file_name"])
        sample_images.append((match["documents"][0]["image_path"], f"Layout: {b_layout}"))

    # Add 4 additional cases with specific visual variants (rotation, blur, noise, letter)
    rotated = next(f for f in fdrs_data if "missing_mandatory_field" in f["injected_issues"])
    sample_images.append((rotated["documents"][0]["image_path"], "Scan Skew Tilt + Missing Field"))

    edited = next(f for f in fdrs_data if "amount_edited" in f["injected_issues"])
    sample_images.append((edited["documents"][0]["image_path"], "Pixel Tampered Amount Overlay"))

    pragati = next(f for f in fdrs_data if "wrong_bank_name" in f["injected_issues"])
    sample_images.append((pragati["documents"][0]["image_path"], "Non-Scheduled Co-op Layout"))

    clean_sample = next(f for f in fdrs_data if f["is_clean"])
    sample_images.append((clean_sample["documents"][0]["image_path"], "Clean Compliant Instrument"))

    # Grid: 2 columns x 5 rows
    thumb_w, thumb_h = 600, 420
    header_h = 30
    cols, rows = 2, 5
    canvas_w = cols * thumb_w + 30
    canvas_h = rows * (thumb_h + header_h) + 30

    sheet = Image.new("RGB", (canvas_w, canvas_h), color="#0F172A")
    draw = ImageDraw.Draw(sheet)

    for idx, (img_path, label) in enumerate(sample_images[:10]):
        c = idx % cols
        r = idx // cols
        x = 15 + c * (thumb_w + 10)
        y = 15 + r * (thumb_h + header_h + 10)

        # Label header
        draw.rectangle([x, y, x + thumb_w, y + header_h], fill="#1B365D")
        draw.text((x + 10, y + 8), f"#{idx+1}: {label}", fill="#FFFFFF")

        if os.path.exists(img_path):
            im = Image.open(img_path)
            im.thumbnail((thumb_w, thumb_h))
            sheet.paste(im, (x, y + header_h))
            im.close()

    sheet.save(CONTACT_SHEET_PATH, "PNG")
    print(f"Contact sheet saved successfully to: {CONTACT_SHEET_PATH}")

if __name__ == "__main__":
    generate_phase2_synthetic_dataset()
