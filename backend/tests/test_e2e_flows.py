"""
Playwright & End-to-End Test Suite for DepoSafe 3 Critical User Flows:
1. Document Intelligence & 4-Level Field Provenance Verification
2. Advisory Risk Flags Explainability & Officer Justified Override
3. Demo Clock Advance, Linked Renewal Chain (Superseding Predecessor) & Competent Authority Release
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.services.seed_service import seed_database_if_empty
from backend.app.models.deposafe_models import FDR, FDRStatus, ProvenanceLevel, BankVerificationStatus

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_database_if_empty(db)
    db.close()
    yield

def login(email: str, password: str = "Password@123") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}"
    return res.json()["access_token"]

# CRITICAL FLOW 1: Document Intelligence & 4-Level Field Provenance Verification
def test_critical_flow_1_provenance_and_bank_adapter():
    officer_token = login("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # 1. Fetch FDR Detail
    res = client.get("/api/v1/fdrs/1", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["fdr_number"] == "SBI-DEL-9876543210"

    # 2. Inspect 4-level provenance fields
    provs = {p["field_name"]: p for p in detail["provenance_fields"]}
    assert "amount" in provs
    assert "fdr_number" in provs
    assert provs["amount"]["submitted_value"] == "3500000.0"

    # 3. Trigger Bank Verification Adapter
    bank_res = client.post("/api/v1/fdrs/1/verify-bank", json={"fdr_id": 1}, headers=headers)
    assert bank_res.status_code == 200
    bank_data = bank_res.json()
    assert "SIMULATED" in bank_data["watermark_notice"]
    assert bank_data["wording"] == "available checks passed"

    # 4. Human-in-the-loop Officer Field Verification
    field_res = client.post(
        "/api/v1/fdrs/1/verify-field",
        json={"field_name": "lien_marked", "verified_value": "YES", "officer_notes": "Lien clause verified on certificate"},
        headers=headers
    )
    assert field_res.status_code == 200
    assert "OFFICER_VERIFIED" in field_res.json()["message"]

# CRITICAL FLOW 2: Advisory Risk Flags Explainability & Officer Justified Override
def test_critical_flow_2_risk_explainability_and_officer_override():
    officer_token = login("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {officer_token}"}

    # 1. Inspect FDR 2 (Tampered / Deficit)
    res = client.get("/api/v1/fdrs/2", headers=headers)
    assert res.status_code == 200
    fdr2 = res.json()
    assert fdr2["review_priority_level"] in ["HIGH", "CRITICAL"]
    assert len(fdr2["review_flags"]) >= 2

    # Check explainability fields: reason, evidence, rule_reference
    for flag in fdr2["review_flags"]:
        assert "reason" in flag
        assert "evidence" in flag
        assert "rule_reference" in flag

    # 2. Officer records override with mandatory justification
    override_payload = {
        "justification": "Council Executive Committee special dispensation under APH Clause 4.8 granted.",
        "adjusted_score": 12.0,
        "new_status": "COMPLIANT"
    }
    over_res = client.post("/api/v1/fdrs/2/override", json=override_payload, headers=headers)
    assert over_res.status_code == 200
    assert over_res.json()["officer_override"] is True
    assert over_res.json()["review_priority_score"] == 12.0

    # 3. Verify status updated and recorded
    updated_res = client.get("/api/v1/fdrs/2", headers=headers)
    assert updated_res.json()["status"] == "COMPLIANT"

# CRITICAL FLOW 3: Demo Clock Advance, Linked Renewal Chain & Competent Authority Release
def test_critical_flow_3_demo_clock_renewal_and_release():
    admin_token = login("admin@deposafe.aicte.gov.in")
    inst_token = login("institution1@vidya.edu.in")
    ca_token = login("director.approval@aicte-india.org")

    # 1. Advance Demo Clock by +30 days live
    clock_res = client.post("/api/v1/demo-clock/advance", json={"days": 30}, headers={"Authorization": f"Bearer {admin_token}"})
    assert clock_res.status_code == 200
    assert "new_simulated_date" in clock_res.json()

    # 2. Institution renews FDR 1 (Creates linked successor instrument)
    renewal_payload = {
        "new_fdr_number": "SBI-DEL-9876543210-RN2",
        "bank_name": "State Bank of India",
        "branch_name": "New Delhi Main Branch",
        "ifsc_code": "SBIN0000691",
        "amount": 3500000.0,
        "issue_date": date.today().isoformat(),
        "maturity_date": (date.today() + timedelta(days=96 * 30)).isoformat(),
        "tenure_months": 96,
        "interest_rate": 7.30,
        "auto_renewal": True
    }
    renew_res = client.post("/api/v1/fdrs/1/renew", json=renewal_payload, headers={"Authorization": f"Bearer {inst_token}"})
    assert renew_res.status_code == 200
    new_fdr_id = renew_res.json()["new_fdr_id"]
    assert new_fdr_id is not None

    # Verify old instrument is now SUPERSEDED
    old_fdr_res = client.get("/api/v1/fdrs/1", headers={"Authorization": f"Bearer {admin_token}"})
    assert old_fdr_res.json()["status"] == "RENEWED_SUPERSEDED"

    # 3. Institution requests release for FDR 4
    rel_req = client.post(
        "/api/v1/fdrs/4/request-release",
        json={"justification": "Full closure completed", "noc_reference": "NOC-DELHI-2024-001"},
        headers={"Authorization": f"Bearer {inst_token}"}
    )
    assert rel_req.status_code == 200

    # 4. Competent Authority authorizes release
    auth_res = client.post(
        "/api/v1/fdrs/4/authorize-release",
        json={"approved": True, "release_order_ref": "AICTE/REL/DEL/2024/099", "remarks": "Approved with zero dues."},
        headers={"Authorization": f"Bearer {ca_token}"}
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["status"] == "RELEASED"

    # 5. Verify cryptographic hash chain integrity after all actions
    audit_verify_res = client.get("/api/v1/audit/verify")
    assert audit_verify_res.status_code == 200
    assert audit_verify_res.json()["verified"] is True

