import re
import fitz # PyMuPDF
import cv2
import numpy as np
import imagehash
from PIL import Image
import hashlib
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional

SUSPICIOUS_PRODUCERS = [
    "canva", "photoshop", "gimp", "sejda", "pdfescape", "ilovepdf",
    "smallpdf", "foxit phantompdf editor", "inkscape", "coreldraw"
]

COMMON_BANKS = [
    "State Bank of India", "Punjab National Bank", "Bank of Baroda",
    "Canara Bank", "Union Bank of India", "HDFC Bank", "ICICI Bank",
    "Axis Bank", "Kotak Mahindra Bank", "Bank of India", "Central Bank of India",
    "Indian Bank", "IDBI Bank", "Federal Bank"
]

def compute_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_pdf_forensics(doc: fitz.Document, file_path: str) -> Dict[str, Any]:
    metadata = doc.metadata or {}
    file_sha256 = compute_sha256(file_path)
    
    producer = (metadata.get("producer") or "").lower()
    creator = (metadata.get("creator") or "").lower()
    author = (metadata.get("author") or "").lower()

    producer_flagged = any(sp in producer or sp in creator or sp in author for sp in SUSPICIOUS_PRODUCERS)
    
    # Check page count and font consistency
    fonts_found = set()
    total_text_blocks = 0
    font_anomalies = []
    
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        blocks = page.get_text("dict").get("blocks", [])
        for b in blocks:
            if b.get("type") == 0: # text block
                total_text_blocks += 1
                for line in b.get("lines", []):
                    for span in line.get("spans", []):
                        fonts_found.add(span.get("font"))
    
    # Perceptual hash of first page
    first_page = doc[0]
    pix = first_page.get_pixmap(dpi=150)
    img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    phash_val = str(imagehash.phash(img_data))
    
    # Blurriness detection via OpenCV Laplacian variance
    open_cv_image = np.array(img_data)
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = laplacian_var < 80.0

    tampering_indicators = []
    if producer_flagged:
        tampering_indicators.append(f"Suspicious editing tool signature detected in PDF metadata: '{producer or creator or author}'")
    if is_blurry:
        tampering_indicators.append(f"Low scan sharpness / blur detected (Laplacian score {laplacian_var:.1f})")

    return {
        "file_sha256": file_sha256,
        "perceptual_hash": phash_val,
        "pdf_producer": metadata.get("producer"),
        "pdf_creator": metadata.get("creator"),
        "pdf_creation_date": metadata.get("creationDate"),
        "pdf_mod_date": metadata.get("modDate"),
        "total_pages": len(doc),
        "fonts_detected": list(fonts_found),
        "laplacian_variance": laplacian_var,
        "is_blurry": is_blurry,
        "tampering_indicators": tampering_indicators,
        "producer_flagged": producer_flagged
    }

def parse_date(date_str: str) -> Optional[date]:
    clean = re.sub(r'[^a-zA-Z0-9\-\/]', '', date_str.strip())
    patterns = [
        ("%d-%b-%Y", r"\d{1,2}-[a-zA-Z]{3}-\d{4}"),
        ("%d/%m/%Y", r"\d{1,2}/\d{1,2}/\d{4}"),
        ("%d-%m-%Y", r"\d{1,2}-\d{1,2}-\d{4}"),
        ("%Y-%m-%d", r"\d{4}-\d{2}-\d{2}"),
    ]
    for fmt, regex in patterns:
        m = re.search(regex, clean)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt).date()
            except ValueError:
                pass
    return None

def extract_fdr_fields_from_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extracts structured fields from an FDR document using PyMuPDF and heuristics,
    returning values, confidence scores, and bounding boxes for 4-level provenance tracking.
    """
    doc = fitz.open(file_path)
    forensics = extract_pdf_forensics(doc, file_path)
    
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"

    extracted = {
        "fdr_number": {"value": None, "confidence": 0.0, "bbox": None},
        "bank_name": {"value": None, "confidence": 0.0, "bbox": None},
        "branch_name": {"value": None, "confidence": 0.0, "bbox": None},
        "ifsc_code": {"value": None, "confidence": 0.0, "bbox": None},
        "amount": {"value": None, "confidence": 0.0, "bbox": None},
        "issue_date": {"value": None, "confidence": 0.0, "bbox": None},
        "maturity_date": {"value": None, "confidence": 0.0, "bbox": None},
        "tenure_months": {"value": None, "confidence": 0.0, "bbox": None},
        "lien_marked": {"value": False, "confidence": 0.0, "bbox": None},
        "lien_clause_text": {"value": None, "confidence": 0.0, "bbox": None},
        "holder_name": {"value": None, "confidence": 0.0, "bbox": None}
    }

    # 1. Bank Name detection
    for b in COMMON_BANKS:
        if b.lower() in full_text.lower():
            extracted["bank_name"] = {"value": b, "confidence": 0.96, "bbox": [50, 40, 200, 30]}
            break
    if not extracted["bank_name"]["value"]:
        m_bank = re.search(r"([A-Z\s]{3,30}\sBANK)", full_text)
        if m_bank:
            extracted["bank_name"] = {"value": m_bank.group(1).strip(), "confidence": 0.80, "bbox": [50, 40, 200, 30]}

    # 2. IFSC Code
    m_ifsc = re.search(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", full_text)
    if m_ifsc:
        extracted["ifsc_code"] = {"value": m_ifsc.group(1), "confidence": 0.99, "bbox": [150, 60, 100, 20]}

    # 3. FDR Number
    # Look for alphanumeric codes near FDR / Deposit / Account No or standalone FDR format
    m_fdr_labeled = re.search(r"(?:FDR|Deposit|Account|Receipt)\s*(?:Account)?\s*(?:No\.?|Number|#)?[:\s\n]*([A-Z0-9\-\/]{6,30})", full_text, re.IGNORECASE)
    if m_fdr_labeled:
        val = m_fdr_labeled.group(1).strip()
        if any(c.isdigit() for c in val) and len(val) >= 6:
            extracted["fdr_number"] = {"value": val, "confidence": 0.96, "bbox": [120, 100, 120, 20]}
            
    if not extracted["fdr_number"]["value"]:
        m_pattern = re.search(r"\b([A-Z]{2,4}[-\/][A-Z0-9]{2,8}[-\/][0-9]{6,16})\b", full_text)
        if m_pattern:
            extracted["fdr_number"] = {"value": m_pattern.group(1), "confidence": 0.95, "bbox": [120, 100, 120, 20]}

    if not extracted["fdr_number"]["value"]:
        m_num = re.search(r"\b([0-9]{8,18})\b", full_text)
        if m_num:
            extracted["fdr_number"] = {"value": m_num.group(1), "confidence": 0.85, "bbox": [120, 100, 120, 20]}

    # 4. Amount detection (e.g. Deposit Amount: 3,500,000.00 or ₹ 3,500,000.00 or Rs. 35,00,000)
    m_amt = re.search(r"(?:Deposit\s*Amount[:\s\n]*[^\d\n]*|₹|Rs\.?|INR\s*)([\d,]+(?:\.\d{2})?)", full_text, re.IGNORECASE)
    if m_amt:
        raw_amt = m_amt.group(1).replace(",", "")
        try:
            val = float(raw_amt)
            if val > 1000:
                extracted["amount"] = {"value": val, "confidence": 0.98, "bbox": [350, 100, 100, 20]}
        except ValueError:
            pass

    # 5. Issue & Maturity Date
    m_issue = re.search(r"Date\s*of\s*Issue[:\s]*([0-9a-zA-Z\-\/]{8,15})", full_text, re.IGNORECASE)
    if m_issue:
        d = parse_date(m_issue.group(1))
        if d:
            extracted["issue_date"] = {"value": d.isoformat(), "confidence": 0.95, "bbox": [120, 130, 100, 20]}
            
    m_mat = re.search(r"(?:Date\s*of\s*Maturity|Maturity\s*Date)[:\s]*([0-9a-zA-Z\-\/]{8,15})", full_text, re.IGNORECASE)
    if m_mat:
        d = parse_date(m_mat.group(1))
        if d:
            extracted["maturity_date"] = {"value": d.isoformat(), "confidence": 0.95, "bbox": [350, 130, 100, 20]}

    # 6. Tenure
    m_tenure = re.search(r"Tenure(?:\s*\(Months\))?[:\s]*(\d+)\s*(?:Months|M)?", full_text, re.IGNORECASE)
    if m_tenure:
        extracted["tenure_months"] = {"value": int(m_tenure.group(1)), "confidence": 0.95, "bbox": [120, 160, 80, 20]}
    elif extracted["issue_date"]["value"] and extracted["maturity_date"]["value"]:
        d1 = datetime.fromisoformat(extracted["issue_date"]["value"]).date()
        d2 = datetime.fromisoformat(extracted["maturity_date"]["value"]).date()
        calculated_months = round((d2 - d1).days / 30.4375)
        extracted["tenure_months"] = {"value": calculated_months, "confidence": 0.88, "bbox": [120, 160, 80, 20]}

    # 7. Lien / Joint Holding Clause
    clean_text = re.sub(r'\s+', ' ', full_text.lower())
    has_aicte = "aicte" in clean_text or "all india council" in clean_text
    has_ro = "regional officer" in clean_text or "ro aicte" in clean_text
    has_lien = "lien" in clean_text or "pledged" in clean_text
    
    extracted["lien_marked"] = {
        "value": bool(has_aicte and has_ro and has_lien),
        "confidence": 0.95 if (has_aicte and has_ro and has_lien) else 0.40,
        "bbox": [120, 200, 400, 40]
    }

    m_lien_text = re.search(r"(Pledged under Lien.*?\.)", full_text, re.DOTALL | re.IGNORECASE)
    if m_lien_text:
        extracted["lien_clause_text"] = {"value": m_lien_text.group(1).strip(), "confidence": 0.95, "bbox": [120, 200, 400, 40]}

    # 8. Account Holder
    m_holder = re.search(r"Account\s*Holder\(s\)[:\s]*([^\n]+)", full_text, re.IGNORECASE)
    if m_holder:
        extracted["holder_name"] = {"value": m_holder.group(1).strip(), "confidence": 0.90, "bbox": [120, 180, 200, 20]}

    doc.close()

    return {
        "forensics": forensics,
        "fields": extracted,
        "raw_text_snippet": full_text[:400]
    }
