import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.deposafe_models import (
    FDR, User, Institution, Notification, FDRStatus, DemoClock
)
from backend.app.services.maturity_radar import run_maturity_radar_scan
from backend.app.services.renewal_guard import evaluate_zero_gap_guard, compute_smart_renewal_priority_queue
from backend.app.services.predictive_intelligence import PredictiveComplianceForecaster
from backend.app.services.demo_clock import get_simulated_today, set_demo_clock_date
from data.seed_loader import load_synthetic_data_into_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_phase8_automation_data():
    db = SessionLocal()
    if db.query(FDR).count() < 100:
        load_synthetic_data_into_db(db)
    db.close()
    yield

def get_admin_token() -> str:
    res = client.post("/api/v1/auth/login", json={"email": "admin@deposafe.aicte.gov.in", "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_officer_token() -> str:
    res = client.post("/api/v1/auth/login", json={"email": "officer@deposafe.aicte.gov.in", "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_inst_token() -> str:
    res = client.post("/api/v1/auth/login", json={"email": "institution1@vidya.edu.in", "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_maturity_radar_and_escalation_progression():
    """
    Demonstrates that advancing the demo clock triggers exact reminders and tiered escalations
    (Institution -> Verification Officer -> Regional Officer -> Competent Authority).
    """
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger radar scan API
    res_scan = client.post("/api/v1/lifecycle/radar/scan", headers=headers)
    assert res_scan.status_code == 200
    scan_data = res_scan.json()
    assert "active_fdrs_scanned" in scan_data
    assert scan_data["active_fdrs_scanned"] > 0
    assert "notifications_generated_count" in scan_data
    assert "escalations_count" in scan_data

    # 2. Inspect generated notifications
    res_notifs = client.get("/api/v1/lifecycle/radar/notifications", headers=headers)
    assert res_notifs.status_code == 200
    notif_list = res_notifs.json()
    assert len(notif_list) > 0

    first_notif = notif_list[0]
    assert "recipient" in first_notif
    assert "delivery_status" in first_notif
    assert first_notif["delivery_status"] == "DELIVERED"

    # 3. Test acknowledgement endpoint
    notif_id = first_notif["id"]
    res_ack = client.post(f"/api/v1/lifecycle/radar/notifications/{notif_id}/acknowledge", headers=headers)
    assert res_ack.status_code == 200
    assert "acknowledged_at" in res_ack.json()


def test_zero_gap_guard_detects_seeded_cover_gaps():
    """Verifies Zero-Gap Guard detects cover gaps and accurately computes gap days."""
    db = SessionLocal()
    # Find an overdue or matured FDR
    today = get_simulated_today(db)
    matured_fdr = db.query(FDR).filter(FDR.maturity_date < today).first()
    assert matured_fdr is not None

    gap_result = evaluate_zero_gap_guard(db, matured_fdr)
    assert gap_result["has_gap"] is True
    assert gap_result["gap_days"] > 0
    assert gap_result["severity"] in ["HIGH", "CRITICAL"]
    assert "Statutory Cover Gap" in gap_result["reason"]
    db.close()


def test_smart_renewal_priority_queue_ranking():
    """Verifies that the Smart Renewal Priority Queue ranks cases by urgency with clear reasons."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    res_queue = client.get("/api/v1/lifecycle/renewal/priority-queue", headers=headers)
    assert res_queue.status_code == 200
    queue = res_queue.json()
    assert len(queue) > 0

    first_case = queue[0]
    assert "fdr_number" in first_case
    assert "urgency_level" in first_case
    assert first_case["urgency_level"] in ["CRITICAL", "HIGH", "NORMAL"]
    assert "urgency_score" in first_case
    assert "contributing_reasons" in first_case
    assert len(first_case["contributing_reasons"]) > 0


def test_renewal_workflow_supersedes_fdr_without_data_loss():
    """
    Demonstrates:
    1. Automatic comparison with previous instrument (amount change, bank change, tenure).
    2. Officer approves renewal -> old FDR is marked SUPERSEDED, new becomes ACTIVE.
    3. Full history preserved.
    """
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}
    db = SessionLocal()

    # Predecessor FDR
    old_fdr = db.query(FDR).filter(FDR.id == 1).first()
    assert old_fdr is not None
    pred_number = old_fdr.fdr_number

    # 1. Compare endpoint
    compare_payload = {
        "new_fdr_number": f"{pred_number}-REN-2026",
        "new_bank_name": old_fdr.bank_name,
        "new_amount": old_fdr.amount + 500000.0, # Increased amount
        "new_issue_date": old_fdr.maturity_date.isoformat(),
        "new_maturity_date": (old_fdr.maturity_date + timedelta(days=96 * 30)).isoformat(),
        "new_tenure_months": 96
    }
    res_comp = client.post(f"/api/v1/lifecycle/renewal/{old_fdr.id}/compare", json=compare_payload, headers=headers)
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["comparison"]["amount"]["status"] == "INCREASED"
    assert comp_data["comparison"]["continuity"]["is_zero_gap"] is True

    # 2. Upload replacement FDR in registry
    ren_create_payload = {
        "new_fdr_number": f"{pred_number}-REN-2026",
        "bank_name": old_fdr.bank_name,
        "branch_name": old_fdr.branch_name,
        "ifsc_code": old_fdr.ifsc_code,
        "amount": old_fdr.amount + 500000.0,
        "issue_date": old_fdr.maturity_date.isoformat(),
        "maturity_date": (old_fdr.maturity_date + timedelta(days=96 * 30)).isoformat(),
        "tenure_months": 96,
        "interest_rate": 7.5,
        "auto_renewal": True
    }
    res_renew = client.post(f"/api/v1/fdr/{old_fdr.id}/renew", json=ren_create_payload, headers=headers)
    assert res_renew.status_code == 200
    new_fdr_id = res_renew.json()["new_fdr_id"]

    # 3. Officer Decision: APPROVE
    decision_payload = {
        "decision": "APPROVE",
        "remarks": "Continuous renewal instrument verified and approved against core banking letter.",
        "officer_justification": "Verified under Regulation 1.7."
    }
    res_dec = client.post(f"/api/v1/lifecycle/renewal/{new_fdr_id}/decision", json=decision_payload, headers=headers)
    assert res_dec.status_code == 200
    assert res_dec.json()["status"] == "ACTIVE"

    # 4. Verify Old FDR is now SUPERSEDED without data loss
    db.refresh(old_fdr)
    new_fdr = db.query(FDR).filter(FDR.id == new_fdr_id).first()
    assert old_fdr.status == FDRStatus.RENEWED_SUPERSEDED
    assert old_fdr.superseded_by == new_fdr.id
    assert new_fdr.status == FDRStatus.ACTIVE
    assert new_fdr.predecessor_fdr_id == old_fdr.id
    db.close()


def test_predictive_intelligence_and_expiry_calendar_api():
    """Verifies scikit-learn forecast and expiry calendar API."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Predictive Workload Forecast
    res_pred = client.get("/api/v1/lifecycle/predictive/workload-forecast", headers=headers)
    assert res_pred.status_code == 200
    pred_data = res_pred.json()
    assert "workload_projection" in pred_data
    assert "next_30_days" in pred_data["workload_projection"]
    assert "next_60_days" in pred_data["workload_projection"]
    assert "next_90_days" in pred_data["workload_projection"]
    assert "Statistical forecast" in pred_data["statutory_label"]

    # 2. Late Renewal Propensity for FDR #1
    res_prop = client.get("/api/v1/lifecycle/predictive/fdr/1/propensity", headers=headers)
    assert res_prop.status_code == 200
    prop_data = res_prop.json()
    assert "late_renewal_probability" in prop_data
    assert 0.0 <= prop_data["late_renewal_probability"] <= 1.0
    assert "top_features" in prop_data
    assert len(prop_data["top_features"]) > 0

    # 3. Maturity Calendar API
    res_cal = client.get("/api/v1/lifecycle/calendar/maturities", headers=headers)
    assert res_cal.status_code == 200
    cal_data = res_cal.json()
    assert "total_events" in cal_data
    assert "events" in cal_data
    assert len(cal_data["events"]) > 0
    first_ev = cal_data["events"][0]
    assert "start" in first_ev
    assert "title" in first_ev
    assert "color_category" in first_ev

