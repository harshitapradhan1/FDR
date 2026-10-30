import os
import json
import pytest
from datetime import date
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.services.seed_service import seed_database_if_empty
from backend.app.models.deposafe_models import User, FDR, FDRDocument, FieldProvenance, ProvenanceLevel, CorrectionRecord
from backend.app.services.pdf_generator import generate_synthetic_fdr_pdf
from backend.app.services.document_pipeline import run_document_ai_pipeline
from backend.app.extractors.llm_extractor import LLMLayoutLMExtractor
from backend.app.services.field_validator import validate_extracted_fields
from backend.app.extractors.base import ExtractedDocumentFields, ExtractedFieldData

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database_if_empty(db)
    db.close()
    yield

def get_auth_token(email: str, password: str = "Password@123") -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


# --------------------------------------------------------------------------
# Test 1: Full Document AI Pipeline Execution & Visual BBox Preview
# --------------------------------------------------------------------------
def test_full_document_ai_pipeline_execution(tmp_path):
    pdf_path = str(tmp_path / "sample_fdr_test.pdf")
    generate_synthetic_fdr_pdf(
        output_path=pdf_path,
        bank_name="State Bank of India",
        branch_name="Connaught Place",
        ifsc_code="SBIN0001234",
        fdr_number="SBI-DEL-2024-9988",
        amount=2500000.0,
        issue_date=date(2024, 5, 1),
        maturity_date=date(2032, 5, 1),
        society_name="Vidya Educational Society",
        institution_name="Vidya College of Technology",
        regional_office="North Western Regional Office"
    )

    res = run_document_ai_pipeline(pdf_path, declared_details={
        "fdr_number": "SBI-DEL-2024-9988",
        "amount": 2500000.0,
        "bank_name": "State Bank of India"
    })

    assert res["document_classification"]["doc_type"] == "FDR_CERTIFICATE"
    assert res["document_classification"]["is_valid_fdr_type"] is True

    fields = res["extracted_fields"]
    assert fields["fdr_number"]["value"] == "SBI-DEL-2024-9988"
    assert fields["amount"]["value"] == 2500000.0
    assert fields["issue_date"]["value"] == "2024-05-01"
    assert fields["maturity_date"]["value"] == "2032-05-01"
    assert fields["lien_marked"]["value"] is True

    # Visual BBox check for preview overlay
    for fname in ["fdr_number", "amount", "issue_date", "maturity_date", "bank_name"]:
        assert fields[fname]["bbox"] is not None
        assert len(fields[fname]["bbox"]) == 4

    # Validation Engine check
    val = res["field_validation"]
    assert val["overall_status"] == "PASSED"
    assert val["ui_wording"] == "available checks passed"
    assert "never 'genuine'" in val["disclaimer"].lower() or "available checks passed" in val["ui_wording"]


# --------------------------------------------------------------------------
# Test 2: Field Validation Engine Safeguards (Never 'Genuine')
# --------------------------------------------------------------------------
def test_field_validation_engine_safeguards():
    # 1. Valid fields
    valid_fields = ExtractedDocumentFields(
        fdr_number=ExtractedFieldData(value="PNB-MUM-884422", confidence=0.98),
        amount=ExtractedFieldData(value=1500000.0, confidence=0.98),
        bank_name=ExtractedFieldData(value="Punjab National Bank", confidence=0.95),
        issue_date=ExtractedFieldData(value="2024-01-01", confidence=0.95),
        maturity_date=ExtractedFieldData(value="2029-01-01", confidence=0.95)
    )
    res_valid = validate_extracted_fields(valid_fields)
    assert res_valid["overall_status"] == "PASSED"
    assert res_valid["ui_wording"] == "available checks passed"
    assert "genuine" not in res_valid["ui_wording"].lower()

    # 2. Chronological violation: maturity before issue
    invalid_dates = ExtractedDocumentFields(
        fdr_number=ExtractedFieldData(value="PNB-MUM-884422", confidence=0.98),
        amount=ExtractedFieldData(value=1500000.0, confidence=0.98),
        bank_name=ExtractedFieldData(value="Punjab National Bank", confidence=0.95),
        issue_date=ExtractedFieldData(value="2029-01-01", confidence=0.95),
        maturity_date=ExtractedFieldData(value="2024-01-01", confidence=0.95) # Earlier than issue!
    )
    res_inv = validate_extracted_fields(invalid_dates)
    assert res_inv["overall_status"] == "FAILED"
    assert any("chronological impossibility" in c["explanation"].lower() for c in res_inv["checks"])

    # 3. Negative / zero amount
    neg_amount = ExtractedDocumentFields(
        fdr_number=ExtractedFieldData(value="PNB-MUM-884422", confidence=0.98),
        amount=ExtractedFieldData(value=-5000.0, confidence=0.98),
        bank_name=ExtractedFieldData(value="Punjab National Bank", confidence=0.95),
        issue_date=ExtractedFieldData(value="2024-01-01", confidence=0.95),
        maturity_date=ExtractedFieldData(value="2029-01-01", confidence=0.95)
    )
    res_neg = validate_extracted_fields(neg_amount)
    assert res_neg["overall_status"] == "FAILED"
    assert any("not positive" in c["explanation"].lower() for c in res_neg["checks"])


# --------------------------------------------------------------------------
# Test 3: Pluggable Extractor Interface & Strict LLM Schema Validation
# --------------------------------------------------------------------------
def test_pluggable_llm_extractor_schema_guardrails():
    # 1. Reject invalid / negative amount from untrusted LLM output
    bad_llm_payload = {
        "bank_name": "Canara Bank",
        "fdr_number": "CAN-DEL-1001",
        "amount": -500000.0, # Negative! Fails strict validator
        "issue_date": "2024-01-01",
        "maturity_date": "2029-01-01"
    }
    extractor = LLMLayoutLMExtractor(mock_response=bad_llm_payload)
    res_bad = extractor.extract("sample text", {})
    # Untrusted unvalidated output is completely rejected
    assert res_bad.amount.value is None

    # 2. Accept strictly validated schema
    valid_llm_payload = {
        "bank_name": "Canara Bank",
        "fdr_number": "CAN-DEL-1001",
        "amount": 500000.0,
        "issue_date": "2024-01-01",
        "maturity_date": "2029-01-01",
        "lien_marked_to_aicte": True
    }
    extractor_valid = LLMLayoutLMExtractor(mock_response=valid_llm_payload)
    res_valid = extractor_valid.extract("sample text", {})
    assert res_valid.amount.value == 500000.0
    assert res_valid.fdr_number.value == "CAN-DEL-1001"
    assert res_valid.lien_marked.value is True


# --------------------------------------------------------------------------
# Test 4: Visual Bounding Box Overlay API Endpoint
# --------------------------------------------------------------------------
def test_visual_bbox_pipeline_results_endpoint():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/fdr/1/pipeline-results", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "extracted_fields" in data
    assert "field_validation" in data
    assert "layout_classification" in data

    # Verify visual bboxes exist for frontend canvas overlay
    fields = data["extracted_fields"]
    assert "amount" in fields
    assert "bbox" in fields["amount"]
    assert len(fields["amount"]["bbox"]) == 4


# --------------------------------------------------------------------------
# Test 5: Field Correction & Safe Self-Improving Extraction Sample Logging
# --------------------------------------------------------------------------
def test_field_correction_and_sample_logging():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    fdr = db.query(FDR).filter(FDR.id == 1).first()
    db.close()

    # Officer corrects a field (e.g. adjusts amount)
    correction_payload = {
        "field_name": "amount",
        "corrected_value": "3600000.0",
        "correction_reason": "Audited passbook indicates additional interest compounding addition."
    }
    res = client.post(f"/fdr/{fdr.id}/correct-field", json=correction_payload, headers=headers)
    assert res.status_code == 200
    corr_data = res.json()
    assert corr_data["field_name"] == "amount"
    assert corr_data["corrected_value"] == "3600000.0"

    # Verify CorrectionRecord in database
    db = SessionLocal()
    rec = db.query(CorrectionRecord).filter(CorrectionRecord.fdr_id == fdr.id).order_by(CorrectionRecord.id.desc()).first()
    assert rec is not None
    assert rec.corrected_value == "3600000.0"
    db.close()

    # Verify training sample saved to disk for safe self-improving candidate evaluation
    sample_path = "data/corrections/correction_samples.jsonl"
    assert os.path.exists(sample_path)
    with open(sample_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) > 0
        last_sample = json.loads(lines[-1])
        assert last_sample["field_name"] == "amount"
        assert last_sample["ground_truth_corrected_value"] == "3600000.0"
