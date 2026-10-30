from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.app.extractors.base import ExtractedDocumentFields
from backend.app.services.normalizer import words_to_amount_approx

RECOGNIZED_BANKS = [
    "State Bank of India", "Punjab National Bank", "Bank of Baroda",
    "Canara Bank", "Union Bank of India", "HDFC Bank", "ICICI Bank",
    "Axis Bank", "Kotak Mahindra Bank", "Bank of India", "Central Bank of India",
    "Indian Bank", "IDBI Bank", "Federal Bank",
    # Synthetic Banks
    "Bharat National Bank", "Apex Commercial Bank", "Gramin Vikas Bank",
    "Hindustan Mercantile Bank", "Pragati Cooperative Bank"
]

def validate_extracted_fields(
    fields: ExtractedDocumentFields,
    declared_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Field Validation Engine:
    1. FDR number present & alphanumeric >= 6 chars
    2. Amount numeric and positive
    3. Words vs figures amount reconciliation
    4. Maturity date occurs strictly after issue date
    5. Mandatory fields complete (FDR#, Amount, Issue Date, Maturity Date, Bank Name)
    6. Bank name recognized in scheduled/commercial bank directory
    7. Cross-check against institution declared details
    
    Status: PASSED / FAILED / NOT_CONFIRMED
    Wording: 'available checks passed', never 'genuine'
    """
    checks = []
    overall_status = "PASSED"

    # Check 1: Mandatory Fields Completeness
    mandatory = ["fdr_number", "amount", "issue_date", "maturity_date", "bank_name"]
    missing_fields = []
    for mf in mandatory:
        val = getattr(fields, mf).value
        if val is None or str(val).strip() == "":
            missing_fields.append(mf)

    if missing_fields:
        checks.append({
            "check_id": "CHECK_MANDATORY_FIELDS",
            "passed": False,
            "severity": "HIGH",
            "field": "mandatory_fields",
            "explanation": f"Mandatory deposit fields missing: {', '.join(missing_fields)}."
        })
        overall_status = "FAILED"
    else:
        checks.append({
            "check_id": "CHECK_MANDATORY_FIELDS",
            "passed": True,
            "severity": "INFO",
            "field": "mandatory_fields",
            "explanation": "All mandatory instrument fields successfully detected."
        })

    # Check 2: FDR Number Validity
    fdr_no = fields.fdr_number.value
    if fdr_no:
        fdr_str = str(fdr_no).strip()
        has_min_len = len(fdr_str) >= 6
        has_digit = any(c.isdigit() for c in fdr_str)
        if has_min_len and has_digit:
            checks.append({
                "check_id": "CHECK_FDR_NUMBER_FORMAT",
                "passed": True,
                "severity": "INFO",
                "field": "fdr_number",
                "explanation": f"FDR number format verified: '{fdr_str}'."
            })
        else:
            checks.append({
                "check_id": "CHECK_FDR_NUMBER_FORMAT",
                "passed": False,
                "severity": "HIGH",
                "field": "fdr_number",
                "explanation": f"FDR number '{fdr_str}' fails minimum length/digit requirement."
            })
            overall_status = "FAILED"

    # Check 3: Amount Numeric & Positive
    amount_val = fields.amount.value
    if amount_val is not None:
        try:
            amt = float(amount_val)
            if amt > 0:
                checks.append({
                    "check_id": "CHECK_AMOUNT_POSITIVE",
                    "passed": True,
                    "severity": "INFO",
                    "field": "amount",
                    "explanation": f"Deposit principal amount ₹{amt:,.2f} is numeric and positive."
                })
            else:
                checks.append({
                    "check_id": "CHECK_AMOUNT_POSITIVE",
                    "passed": False,
                    "severity": "CRITICAL",
                    "field": "amount",
                    "explanation": f"Extracted deposit amount ({amt}) is not positive."
                })
                overall_status = "FAILED"
        except (ValueError, TypeError):
            checks.append({
                "check_id": "CHECK_AMOUNT_NUMERIC",
                "passed": False,
                "severity": "CRITICAL",
                "field": "amount",
                "explanation": "Extracted deposit amount could not be parsed as a valid numeric sum."
            })
            overall_status = "FAILED"

    # Check 4: Words vs Figures Amount Reconciliation
    if amount_val is not None and fields.amount_words.value:
        words_val = str(fields.amount_words.value)
        approx_words_amount = words_to_amount_approx(words_val)
        if approx_words_amount is not None:
            if abs(approx_words_amount - float(amount_val)) < 1.0:
                checks.append({
                    "check_id": "CHECK_WORDS_VS_FIGURES",
                    "passed": True,
                    "severity": "INFO",
                    "field": "amount",
                    "explanation": f"Figures (₹{float(amount_val):,.2f}) reconcile with words ('{words_val}')."
                })
            else:
                checks.append({
                    "check_id": "CHECK_WORDS_VS_FIGURES",
                    "passed": False,
                    "severity": "HIGH",
                    "field": "amount",
                    "explanation": f"Discrepancy: Figures show ₹{float(amount_val):,.2f} while words indicate ₹{approx_words_amount:,.2f}."
                })
                overall_status = "FAILED"

    # Check 5: Chronology: Maturity Date after Issue Date
    iss = fields.issue_date.value
    mat = fields.maturity_date.value
    if iss and mat:
        try:
            d_iss = datetime.fromisoformat(str(iss)).date()
            d_mat = datetime.fromisoformat(str(mat)).date()
            if d_mat > d_iss:
                checks.append({
                    "check_id": "CHECK_CHRONOLOGY_DATES",
                    "passed": True,
                    "severity": "INFO",
                    "field": "maturity_date",
                    "explanation": f"Maturity date ({d_mat}) is chronologically after issue date ({d_iss})."
                })
            else:
                checks.append({
                    "check_id": "CHECK_CHRONOLOGY_DATES",
                    "passed": False,
                    "severity": "CRITICAL",
                    "field": "maturity_date",
                    "explanation": f"Chronological impossibility: Maturity date ({d_mat}) occurs on or before issue date ({d_iss})."
                })
                overall_status = "FAILED"
        except Exception as e:
            checks.append({
                "check_id": "CHECK_CHRONOLOGY_DATES",
                "passed": False,
                "severity": "MEDIUM",
                "field": "maturity_date",
                "explanation": f"Unable to parse chronological dates: {e}."
            })
            overall_status = "NOT_CONFIRMED"

    # Check 6: Bank Name Recognized
    bank_name = fields.bank_name.value
    if bank_name:
        b_clean = str(bank_name).strip().lower()
        is_recognized = any(rb.lower() in b_clean or b_clean in rb.lower() for rb in RECOGNIZED_BANKS)
        if is_recognized:
            checks.append({
                "check_id": "CHECK_BANK_RECOGNITION",
                "passed": True,
                "severity": "INFO",
                "field": "bank_name",
                "explanation": f"Issuing bank '{bank_name}' confirmed in official banking registry."
            })
        else:
            checks.append({
                "check_id": "CHECK_BANK_RECOGNITION",
                "passed": False,
                "severity": "MEDIUM",
                "field": "bank_name",
                "explanation": f"Issuing bank '{bank_name}' not identified in standard banking registry."
            })
            if overall_status == "PASSED":
                overall_status = "NOT_CONFIRMED"

    # Check 7: Match with Declared Details (if available)
    if declared_details:
        dec_amt = declared_details.get("amount")
        dec_fdr = declared_details.get("fdr_number")

        if dec_amt is not None and amount_val is not None:
            if abs(float(dec_amt) - float(amount_val)) < 1.0:
                checks.append({
                    "check_id": "CHECK_DECLARED_AMOUNT_MATCH",
                    "passed": True,
                    "severity": "INFO",
                    "field": "amount",
                    "explanation": "Extracted instrument amount matches institution's declared sum."
                })
            else:
                checks.append({
                    "check_id": "CHECK_DECLARED_AMOUNT_MATCH",
                    "passed": False,
                    "severity": "HIGH",
                    "field": "amount",
                    "explanation": f"Amount mismatch: Scanned document has ₹{float(amount_val):,.2f}, institution declared ₹{float(dec_amt):,.2f}."
                })
                overall_status = "FAILED"

        if dec_fdr and fdr_no:
            if str(dec_fdr).strip().lower() == str(fdr_no).strip().lower():
                checks.append({
                    "check_id": "CHECK_DECLARED_FDR_MATCH",
                    "passed": True,
                    "severity": "INFO",
                    "field": "fdr_number",
                    "explanation": "Extracted FDR number exactly matches institution application."
                })
            else:
                checks.append({
                    "check_id": "CHECK_DECLARED_FDR_MATCH",
                    "passed": False,
                    "severity": "HIGH",
                    "field": "fdr_number",
                    "explanation": f"FDR number mismatch: Scanned '{fdr_no}', declared '{dec_fdr}'."
                })
                overall_status = "FAILED"

    # Strict statutory wording
    ui_wording = "available checks passed" if overall_status == "PASSED" else "not confirmed"

    return {
        "overall_status": overall_status,
        "ui_wording": ui_wording,
        "disclaimer": "Statutory notice: 'available checks passed' reflects automated heuristic validation, not a guarantee of instrument genuineness.",
        "checks_passed_count": sum(1 for c in checks if c["passed"]),
        "total_checks_count": len(checks),
        "checks": checks
    }
