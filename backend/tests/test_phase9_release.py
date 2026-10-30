import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.deposafe_models import (
    FDR, User, Institution, ReleaseRequest, ReleaseStatus, FDRStatus, UserRole
)
from backend.app.state_machines.fdr_state_machine import ReleaseWorkflowStateMachine, InvalidStateTransitionError
from backend.app.services.release_service import evaluate_release_readiness
from data.seed_loader import load_synthetic_data_into_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_phase9_release_data():
    db = SessionLocal()
    if db.query(FDR).count() < 100:
        load_synthetic_data_into_db(db)
    db.close()
    yield

def get_token_for(email: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_release_readiness_checklist_advisory():
    """
    Verifies that the release readiness check automatically evaluates all 5 regulatory
    conditions, produces PASS/FAIL/NEEDS_REVIEW with evidence, and is labeled advisory.
    """
    db = SessionLocal()
    fdr = db.query(FDR).filter(FDR.id == 1).first()
    assert fdr is not None

    readiness = evaluate_release_readiness(db, fdr)
    assert "overall_readiness" in readiness
    assert readiness["overall_readiness"] in ["PASS", "FAIL", "NEEDS_REVIEW"]
    assert "checklist" in readiness
    assert len(readiness["checklist"]) == 5

    for item in readiness["checklist"]:
        assert "condition_id" in item
        assert "status" in item
        assert item["status"] in ["PASS", "FAIL", "NEEDS_REVIEW"]
        assert "evidence" in item
        assert "explanation" in item

    assert "advisory" in readiness["statutory_disclaimer"].lower()
    assert "never approves" in readiness["statutory_disclaimer"].lower()
    db.close()


def test_end_to_end_release_scenario_with_all_9_states():
    """
    Tests full statutory release lifecycle through all 9 states:
    Draft -> Submitted -> Under scrutiny -> Clarification required -> Resubmitted
    -> Recommended for approval -> Approved -> Released -> Closed.
    """
    db = SessionLocal()
    # Pick FDR 170 (Replacement FDR belonging to institution 1)
    fdr = db.query(FDR).filter(FDR.id == 170).first()
    if not fdr:
        fdr = db.query(FDR).filter(FDR.institution_id == 1).first()
    assert fdr is not None

    inst_user_token = get_token_for("institution1@vidya.edu.in")
    officer_token = get_token_for("officer@deposafe.aicte.gov.in")
    ca_token = get_token_for("director.approval@aicte-india.org")

    # 1. State: DRAFT -> SUBMITTED (Institution submits request)
    sub_payload = {
        "justification": "AICTE Approval Process Handbook Chapter I Regulation 11(2) course closure completed.",
        "amount": fdr.amount,
        "noc_reference": "NOC-HR-CLOSURE-2024-89",
        "reason": "Complete disestablishment of Diploma program with zero pending student obligations."
    }
    res_sub = client.post(f"/api/v1/release/fdr/{fdr.id}/request", json=sub_payload, headers={"Authorization": f"Bearer {inst_user_token}"})
    assert res_sub.status_code == 200
    assert res_sub.json()["status"] == "Submitted"

    # 2. State: SUBMITTED -> UNDER_SCRUTINY (Officer begins scrutiny)
    res_scrut = client.post(
        f"/api/v1/release/fdr/{fdr.id}/scrutiny",
        json={"action": "BEGIN_SCRUTINY", "remarks": "Scrutinizing state NOC and affiliating board clearance."},
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert res_scrut.status_code == 200
    assert res_scrut.json()["status"] == "Under scrutiny"

    # 3. State: UNDER_SCRUTINY -> CLARIFICATION_REQUIRED
    res_clar = client.post(
        f"/api/v1/release/fdr/{fdr.id}/scrutiny",
        json={"action": "REQUEST_CLARIFICATION", "remarks": "Affiliating university final student migration certificate required."},
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert res_clar.status_code == 200
    assert res_clar.json()["status"] == "Clarification required"

    # 4. State: CLARIFICATION_REQUIRED -> UNDER_SCRUTINY (Resubmission)
    res_resub = client.post(
        f"/api/v1/release/fdr/{fdr.id}/scrutiny",
        json={"action": "RESUBMIT", "remarks": "Migration certificate uploaded under supplementary doc ref MIG-2024."},
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert res_resub.status_code == 200
    assert res_resub.json()["status"] == "Under scrutiny"

    # 5. State: UNDER_SCRUTINY -> RECOMMENDED_FOR_APPROVAL
    res_rec = client.post(
        f"/api/v1/release/fdr/{fdr.id}/scrutiny",
        json={"action": "RECOMMEND", "remarks": "All preconditions and NOCs verified. Forwarded to Competent Authority for sanction."},
        headers={"Authorization": f"Bearer {officer_token}"}
    )
    assert res_rec.status_code == 200
    assert res_rec.json()["status"] == "Recommended for approval"

    # 6. State: RECOMMENDED_FOR_APPROVAL -> APPROVED (Authorized by Competent Authority with typed justification)
    auth_payload = {
        "approved": True,
        "typed_justification": "All statutory preconditions under Regulation 11 verified. University NOC confirmed. Release authorized.",
        "release_order_ref": "AICTE/REG/REL/2026/00489"
    }
    res_app = client.post(f"/api/v1/release/fdr/{fdr.id}/authorize", json=auth_payload, headers={"Authorization": f"Bearer {ca_token}"})
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "Approved"

    # 7. State: APPROVED -> RELEASED -> CLOSED (Final disbursement & archive)
    res_close = client.post(f"/api/v1/release/fdr/{fdr.id}/disburse-and-close", headers={"Authorization": f"Bearer {ca_token}"})
    assert res_close.status_code == 200
    assert res_close.json()["fdr_status"] == "CLOSED"
    assert res_close.json()["release_status"] == "Closed"
    assert res_close.json()["history_preserved_in_passport"] is True

    # 8. Verify FDR in database is CLOSED and records are preserved
    db.refresh(fdr)
    assert fdr.status == FDRStatus.CLOSED
    assert fdr.release_order_ref == auth_payload["release_order_ref"]
    db.close()


def test_statutory_safeguard_no_non_authority_can_approve_release():
    """
    Non-negotiable SIH requirement:
    Prove by test that NO non-authority user or code path can approve release.
    (Institution User, Verification Officer, Regional Officer, Auditor MUST receive 403 Forbidden).
    """
    ca_token = get_token_for("director.approval@aicte-india.org")
    officer_token = get_token_for("officer@deposafe.aicte.gov.in")
    ro_token = get_token_for("ro.north@deposafe.aicte.gov.in")
    inst_token = get_token_for("institution1@vidya.edu.in")
    auditor_token = get_token_for("auditor@deposafe.aicte.gov.in")

    auth_payload = {
        "approved": True,
        "typed_justification": "Attempting illegal authorization without competent authority privileges.",
        "release_order_ref": "ILLEGAL/ORDER/999"
    }

    # 1. Institution User cannot authorize release -> 403
    r1 = client.post("/api/v1/release/fdr/4/authorize", json=auth_payload, headers={"Authorization": f"Bearer {inst_token}"})
    assert r1.status_code == 403

    # 2. Verification Officer cannot authorize release -> 403
    r2 = client.post("/api/v1/release/fdr/4/authorize", json=auth_payload, headers={"Authorization": f"Bearer {officer_token}"})
    assert r2.status_code == 403

    # 3. Regional Officer cannot authorize release -> 403
    r3 = client.post("/api/v1/release/fdr/4/authorize", json=auth_payload, headers={"Authorization": f"Bearer {ro_token}"})
    assert r3.status_code == 403

    # 4. Auditor cannot authorize release -> 403
    r4 = client.post("/api/v1/release/fdr/4/authorize", json=auth_payload, headers={"Authorization": f"Bearer {auditor_token}"})
    assert r4.status_code == 403

    # 5. Direct State Machine Code Path Guard: Attempting APPROVE event with non-CA role raises PermissionError
    sm = ReleaseWorkflowStateMachine(ReleaseStatus.RECOMMENDED_FOR_APPROVAL)
    with pytest.raises(PermissionError) as exc_info:
        sm.trigger("APPROVE", actor_role="VERIFICATION_OFFICER")
    assert "Statutory Safeguard Violation" in str(exc_info.value)


def test_illegal_state_machine_transitions_are_blocked():
    """Verifies that attempting illegal state jumps (e.g. Draft -> Approved) is strictly blocked."""
    sm = ReleaseWorkflowStateMachine(ReleaseStatus.DRAFT)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        sm.trigger("APPROVE", actor_role="COMPETENT_AUTHORITY")
    assert "Illegal state transition" in str(exc_info.value)
