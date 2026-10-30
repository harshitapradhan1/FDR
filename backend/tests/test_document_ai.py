import os
import pytest
from datetime import date
from backend.app.services.pdf_generator import generate_synthetic_fdr_pdf
from backend.app.services.document_ai import extract_fdr_fields_from_pdf

def test_generate_and_extract_compliant_fdr(tmp_path):
    pdf_path = str(tmp_path / "compliant_fdr.pdf")
    generate_synthetic_fdr_pdf(
        output_path=pdf_path,
        bank_name="State Bank of India",
        branch_name="New Delhi Main Branch",
        ifsc_code="SBIN0000691",
        fdr_number="SBI-DEL-9876543210",
        amount=3500000.0,
        issue_date=date(2024, 4, 15),
        maturity_date=date(2032, 4, 15),
        society_name="Shree Vidya Educational Trust",
        institution_name="Vidya Institute of Technology & Science",
        regional_office="North Western Regional Office",
        tenure_months=96,
        tamper_metadata=False,
        include_proper_lien=True
    )
    
    assert os.path.exists(pdf_path)
    res = extract_fdr_fields_from_pdf(pdf_path)
    
    assert res["forensics"]["file_sha256"] is not None
    assert res["forensics"]["perceptual_hash"] is not None
    assert not res["forensics"]["producer_flagged"]
    
    fields = res["fields"]
    assert fields["fdr_number"]["value"] == "SBI-DEL-9876543210"
    assert fields["amount"]["value"] == 3500000.0
    assert fields["ifsc_code"]["value"] == "SBIN0000691"
    assert fields["lien_marked"]["value"] is True
    assert fields["tenure_months"]["value"] == 96

def test_generate_and_detect_tampered_metadata(tmp_path):
    pdf_path = str(tmp_path / "tampered_fdr.pdf")
    generate_synthetic_fdr_pdf(
        output_path=pdf_path,
        bank_name="Punjab National Bank",
        branch_name="Connaught Place",
        ifsc_code="PUNB0012300",
        fdr_number="PNB-FD-4455667788",
        amount=1500000.0,
        issue_date=date(2024, 6, 1),
        maturity_date=date(2032, 6, 1),
        society_name="Sunrise Foundation",
        institution_name="Sunrise College of Pharmacy",
        regional_office="Northern Regional Office",
        tamper_metadata=True,
        include_proper_lien=False
    )
    
    res = extract_fdr_fields_from_pdf(pdf_path)
    assert res["forensics"]["producer_flagged"] is True
    assert len(res["forensics"]["tampering_indicators"]) > 0
    assert res["fields"]["lien_marked"]["value"] is False

