import pytest
from fastapi.testclient import TestClient
from datetime import datetime, date
import os
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.models.deposafe_models import (
    FDR, User, UserRole, FieldProvenance, ProvenanceLevel,
    BankVerificationStatus, BankVerificationRecord, Institution, FDRDocument,
    FDRStatus
)
from backend.app.services.simulated_bank_service import (
    SimulatedBankService,
    compute_bank_signature,
    verify_bank_signature,
    BankTimeoutException,
    BankRateLimitException,
    BankDowntimeException
)
from backend.app.services.verification_orchestrator import VerificationOrchestrator, bank_circuit_breaker
from backend.app.services.reconciliation_service import CrossDocumentReconciler
from backend.app.schemas.deposafe_schemas import PROVENANCE_BADGE_MAP

client = TestClient(app)

def get_auth_token(email: str = "officer@deposafe.aicte.gov.in") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_dual_truth_badge_map_completeness():
    """Verifies that all 6 provenance levels have distinct UI badge colors and styling."""
    required_levels = ["SUBMITTED", "AI_EXTRACTED", "BANK_CONFIRMED", "OFFICER_VERIFIED", "MISMATCH", "SOURCE_UNAVAILABLE"]
    for lvl in required_levels:
        assert lvl in PROVENANCE_BADGE_MAP
        badge = PROVENANCE_BADGE_MAP[lvl]
        assert badge.bg_class.startswith("bg-")
        assert badge.text_class.startswith("text-")
        assert badge.hex_color.startswith("#")

def test_simulated_bank_service_behaviors_and_signature():
    """Tests all controllable bank behaviors and HMAC signature verification."""
    # 1. SUCCESS with HMAC signature
    res_success = SimulatedBankService.query_core_banking(
        bank="Bharat National Bank",
        branch_ifsc="BNBN0004918",
        fdr_number="BNB-DEL-1001",
        amount=1000000.0,
        issue_date="2024-11-15",
        maturity_date="2032-11-15",
        scenario="SUCCESS"
    )
    assert res_success["status"] == "AVAILABLE_CHECKS_PASSED"
    assert res_success["wording"] == "available checks passed"
    assert "SIMULATED" in res_success["watermark"]
    assert res_success["signature"] is not None
    assert verify_bank_signature(
        {
            "ref_id": res_success["api_reference_id"],
            "returned_fields": res_success["returned_fields"],
            "timestamp": res_success["timestamp"],
            "simulated": True
        },
        res_success["signature"]
    ) is True

    # 2. MISMATCH
    res_mismatch = SimulatedBankService.query_core_banking(
        bank="Bharat National Bank",
        branch_ifsc="BNBN0004918",
        fdr_number="BNB-DEL-HERO-1000",
        amount=1000000.0,
        issue_date="2024-11-15",
        maturity_date="2032-11-15",
        scenario="MISMATCH"
    )
    assert res_mismatch["status"] == "MISMATCH"
    assert "maturity_date" in res_mismatch["diffs"]

    # 3. NOT FOUND
    res_nf = SimulatedBankService.query_core_banking(
        bank="Bharat National Bank",
        branch_ifsc="BNBN0004918",
        fdr_number="BNB-DEL-9999",
        amount=500000.0,
        issue_date="2024-01-01",
        maturity_date="2032-01-01",
        scenario="NOT_FOUND"
    )
    assert res_nf["status"] == "NOT_CONFIRMED"
    assert res_nf["wording"] == "not confirmed"

    # 4. Custom Exceptions
    with pytest.raises(BankTimeoutException):
        SimulatedBankService.query_core_banking("Bank", "IFSC", "FDR", 100.0, "", "", scenario="TIMEOUT")

    with pytest.raises(BankRateLimitException):
        SimulatedBankService.query_core_banking("Bank", "IFSC", "FDR", 100.0, "", "", scenario="RATE_LIMIT")

    with pytest.raises(BankDowntimeException):
        SimulatedBankService.query_core_banking("Bank", "IFSC", "FDR", 100.0, "", "", scenario="DOWNTIME")

def test_circuit_breaker_tripping_and_recovery():
    """Tests CircuitBreaker transitions: CLOSED -> OPEN after 3 failures -> recovery."""
    bank_circuit_breaker.reset()
    assert bank_circuit_breaker.state == "CLOSED"
    assert bank_circuit_breaker.can_execute() is True

    # Record 3 failures to trigger trip
    bank_circuit_breaker.record_failure()
    bank_circuit_breaker.record_failure()
    assert bank_circuit_breaker.state == "CLOSED"
    bank_circuit_breaker.record_failure()
    assert bank_circuit_breaker.state == "OPEN"
    assert bank_circuit_breaker.can_execute() is False

    # Reset
    bank_circuit_breaker.reset()
    assert bank_circuit_breaker.state == "CLOSED"

def test_officer_manual_verification_provenance():
    """Verifies that officer manual verification elevates provenance to OFFICER_VERIFIED (distinct from BANK_CONFIRMED)."""
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Manual verification request
    payload = {
        "method": "BRANCH_VISIT",
        "reference_id": "REF-BRANCH-TEST-001",
        "remarks": "Official branch visit conducted. Physical ledger confirmed.",
        "verified_fields": {
            "amount": "1000000.0",
            "fdr_number": "SBI-DEL-9876543210"
        }
    }
    res = client.post("/api/v1/fdrs/1/verify-manual", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["provenance_status"] == "OFFICER_VERIFIED"
    assert data["reference_id"] == "REF-BRANCH-TEST-001"

    # Verify Dual-Truth Ledger reflects OFFICER_VERIFIED (and not BANK_CONFIRMED)
    ledger_res = client.get("/api/v1/fdrs/1/provenance-ledger", headers=headers)
    assert ledger_res.status_code == 200
    ledger_data = ledger_res.json()
    amt_prov = next((p for p in ledger_data["provenance_fields"] if p["field_name"] == "amount"), None)
    assert amt_prov is not None
    assert amt_prov["status"] == "OFFICER_VERIFIED"
    assert amt_prov["officer_verified_value"] == "1000000.0"
    assert "Officer" in amt_prov["officer_verified_by"]
    assert amt_prov["badge_style"]["source"] == "OFFICER_VERIFIED"

def test_hero_case_cross_document_reconciliation():
    """Verifies CrossDocumentReconciler detects maturity mismatch (2032 vs 2026) on Hero Case with bboxes."""
    db = SessionLocal()
    hero_fdr = db.query(FDR).filter(FDR.fdr_number == "BNB-DEL-HERO-1000").first()
    if not hero_fdr:
        inst = db.query(Institution).first()
        hero_fdr = FDR(
            fdr_number="BNB-DEL-HERO-1000",
            bank_name="Bharat National Bank",
            branch_name="New Delhi Central Branch",
            ifsc_code="BNBN0004918",
            amount=1000000.0,
            issue_date=date(2024, 11, 15),
            maturity_date=date(2032, 11, 15),
            tenure_months=96,
            institution_id=inst.id if inst else 1,
            status=FDRStatus.ACTIVE
        )
        db.add(hero_fdr)
        db.commit()
        db.refresh(hero_fdr)

    # Ensure documents are attached
    docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == hero_fdr.id).all()
    if not docs:
        src_fdr = os.path.join(PROJECT_ROOT, "data", "synthetic", "documents", "FDR_1001_BHARAT_NATIONAL_BANK.pdf")
        src_conf = os.path.join(PROJECT_ROOT, "data", "synthetic", "documents", "CONF_LETTER_1001.pdf")
        
        doc1 = FDRDocument(
            fdr_id=hero_fdr.id,
            version=1,
            file_name="FDR_1001_BHARAT_NATIONAL_BANK.pdf",
            file_path=src_fdr if os.path.exists(src_fdr) else "",
            doc_type="FDR_CERTIFICATE",
            file_hash_sha256="da61a0e3d69e2601dbcc8aaa15694b1ff492900d26e1049d12dcad4a7bf9a9be"
        )
        doc2 = FDRDocument(
            fdr_id=hero_fdr.id,
            version=1,
            file_name="CONF_LETTER_1001.pdf",
            file_path=src_conf if os.path.exists(src_conf) else "",
            doc_type="BANK_CONFIRMATION_LETTER",
            file_hash_sha256="e1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2"
        )
        db.add(doc1)
        db.add(doc2)
        db.commit()

    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/fdrs/{hero_fdr.id}/cross-document-reconciliation", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["reconciliation_summary"]["overall_status"] == "MISMATCH_DETECTED"
    assert data["reconciliation_summary"]["discrepancy_count"] >= 1

    # Check maturity_date row
    mat_row = next((r for r in data["reconciliation_table"] if r["field_name"] == "maturity_date"), None)
    assert mat_row is not None
    assert mat_row["status"] == "MISMATCH"
    assert "2032-11-15" in mat_row["discrepancy_details"]
    assert "2026-11-15" in mat_row["discrepancy_details"]

    # Verify evidence references contain doc_type, file_name, and bboxes
    assert len(mat_row["evidence"]) == 2
    fdr_ev = next(e for e in mat_row["evidence"] if e["doc_type"] == "FDR_CERTIFICATE")
    conf_ev = next(e for e in mat_row["evidence"] if e["doc_type"] == "BANK_CONFIRMATION_LETTER")

    assert fdr_ev["value"] == "2032-11-15"
    assert len(fdr_ev["bbox"]) == 4
    assert conf_ev["value"] == "2026-11-15"
    assert len(conf_ev["bbox"]) == 4

    db.close()
