import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.services.seed_service import seed_database_if_empty
from backend.app.models.deposafe_models import User, FDR, FDRStatus, ProvenanceLevel, BankVerificationStatus

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
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_auth_login_all_roles():
    admin_token = get_auth_token("admin@deposafe.aicte.gov.in")
    assert admin_token is not None

    officer_token = get_auth_token("officer@deposafe.aicte.gov.in")
    assert officer_token is not None

    ca_token = get_auth_token("director.approval@aicte-india.org")
    assert ca_token is not None

def test_fdr_list_and_provenance():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/fdrs", headers=headers)
    assert res.status_code == 200
    fdrs = res.json()
    assert len(fdrs) >= 4

    # Check detail of FDR 1
    detail_res = client.get(f"/api/v1/fdrs/{fdrs[0]['id']}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert "provenance_fields" in data
    assert "compliance_evaluation" in data
    assert "review_priority_score" in data
    assert "disclaimer" in data["compliance_evaluation"]

def test_bank_verification_simulation_adapter():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/fdrs/1/verify-bank", json={"fdr_id": 1}, headers=headers)
    assert res.status_code == 200
    result = res.json()
    assert result["watermark_notice"] == "SIMULATED, not a real bank verification"
    assert result["wording"] == "available checks passed"

def test_officer_field_verification_provenance():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/fdrs/2/verify-field",
        json={"field_name": "amount", "verified_value": "1500000.0", "officer_notes": "Certificate examined directly"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "OFFICER_VERIFIED" in data["message"]

def test_officer_override_with_justification():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/fdrs/2/override",
        json={
            "justification": "Institution produced special Council exemption letter dated 2024-05-10.",
            "adjusted_score": 15.0,
            "new_status": "COMPLIANT"
        },
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["officer_override"] is True
    assert data["review_priority_score"] == 15.0

def test_fdr_renewal_creates_linked_successor_and_supersedes():
    token = get_auth_token("institution1@vidya.edu.in")
    headers = {"Authorization": f"Bearer {token}"}

    renew_payload = {
        "new_fdr_number": "SBI-DEL-9876543210-R1",
        "bank_name": "State Bank of India",
        "branch_name": "New Delhi Main Branch",
        "ifsc_code": "SBIN0000691",
        "amount": 3500000.0,
        "issue_date": date.today().isoformat(),
        "maturity_date": (date.today() + timedelta(days=96 * 30)).isoformat(),
        "tenure_months": 96,
        "interest_rate": 7.40,
        "auto_renewal": True
    }
    res = client.post("/api/v1/fdrs/1/renew", json=renew_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["predecessor_fdr_id"] == 1
    new_fdr_id = data["new_fdr_id"]

    # Verify old FDR is SUPERSEDED
    old_res = client.get("/api/v1/fdrs/1", headers=headers)
    assert old_res.json()["status"] in ["SUPERSEDED", "RENEWED_SUPERSEDED"]

def test_release_authorization_role_enforcement():
    # Regular officer cannot authorize release
    officer_token = get_auth_token("officer@deposafe.aicte.gov.in")
    res = client.post(
        "/api/v1/fdrs/4/authorize-release",
        json={"approved": True, "release_order_ref": "AICTE/REL/2024/099", "remarks": "Approved"},
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert res.status_code == 403

    # Competent Authority CAN authorize release
    ca_token = get_auth_token("director.approval@aicte-india.org")
    ca_res = client.post(
        "/api/v1/fdrs/4/authorize-release",
        json={"approved": True, "release_order_ref": "AICTE/REL/2024/099", "remarks": "Verified closure and NOC."},
        headers={"Authorization": f"Bearer {ca_token}"}
    )
    assert ca_res.status_code == 200
    assert ca_res.json()["status"] == "RELEASED"

def test_demo_clock_advance_and_workload():
    admin_token = get_auth_token("admin@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.post("/api/v1/demo-clock/advance", json={"days": 30}, headers=headers)
    assert res.status_code == 200
    assert "new_simulated_date" in res.json()

    # Workload endpoint check
    wl_res = client.get("/api/v1/workload", headers=headers)
    assert wl_res.status_code == 200
    wl = wl_res.json()
    assert "summary" in wl
    assert "buckets" in wl

def test_audit_ledger_verification():
    res = client.get("/api/v1/audit/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is True
    assert data["total_records"] > 0

def test_evaluation_harness_api():
    res = client.get("/api/v1/evaluation/latest")
    assert res.status_code == 200
    data = res.json()
    assert "overall_field_accuracy_pct" in data
    assert "mean_latency_ms" in data
    assert "measurement_guarantee" in data
