import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime
import os
import yaml

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.deposafe_models import (
    FDR, User, Institution, ComplianceRule, ComplianceResult, FDRStatus
)
from backend.app.services.compliance_service import (
    get_active_rule, evaluate_fdr_compliance_versioned, run_dry_run_impact_report,
    compute_institution_compliance_score, load_rule_from_yaml, RULES_CONFIG_DIR
)
from data.seed_loader import load_synthetic_data_into_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_phase7_compliance_data():
    db = SessionLocal()
    if db.query(FDR).count() < 100:
        load_synthetic_data_into_db(db)
    # Ensure baseline rule is active
    get_active_rule(db)
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


def test_rule_model_structure_and_yaml_loader():
    """Verifies all 6 rule types, parameters, handbook placeholders, and YAML loading."""
    v1_path = os.path.join(RULES_CONFIG_DIR, "aph_2024_27_v1.yaml")
    assert os.path.exists(v1_path)
    rule_data = load_rule_from_yaml(v1_path)

    assert rule_data["version_tag"] == "APH-2024-27.v1"
    assert "ILLUSTRATIVE PLACEHOLDERS" in rule_data["disclaimer"]
    rules = rule_data["rules"]
    assert len(rules) >= 6

    rule_types = {r["type"] for r in rules}
    expected_types = {"min_amount", "validity_until", "required_document", "date_logic", "bank_whitelist", "release_condition"}
    assert expected_types.issubset(rule_types)

    # Check that each rule has handbook placeholder and bilingual descriptions
    for r in rules:
        assert "rule_id" in r
        assert "handbook_reference" in r
        assert "description" in r
        assert "description_hi" in r
        assert "parameters" in r


def test_deterministic_evaluation_stores_version_and_bilingual_explanation():
    """Verifies evaluation records exact rule version used, outcome, observed vs expected, and bilingual text."""
    db = SessionLocal()
    active_rule = get_active_rule(db)
    fdr = db.query(FDR).filter(FDR.amount >= 3500000).first()
    assert fdr is not None
    inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    eval_result = evaluate_fdr_compliance_versioned(fdr, inst, active_rule, db, save_result=True)
    assert eval_result["rule_version_used"] == active_rule.version_tag
    assert eval_result["overall_outcome"] in ["COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW", "NOT_APPLICABLE"]
    assert "checks" in eval_result
    assert len(eval_result["checks"]) >= 6

    for c in eval_result["checks"]:
        assert "rule_id" in c
        assert "rule_type" in c
        assert "observed_value" in c
        assert "expected_value" in c
        assert "explanation_en" in c
        assert "explanation_hi" in c
        assert len(c["explanation_hi"]) > 0

    # Verify stored database record
    latest_db_res = db.query(ComplianceResult).filter(ComplianceResult.fdr_id == fdr.id).order_by(ComplianceResult.id.desc()).first()
    assert latest_db_res is not None
    assert latest_db_res.rule_version_used == active_rule.version_tag
    db.close()


def test_dry_run_impact_report_simulation():
    """Verifies dry-run regulation change produces impact report showing who flips without altering history."""
    db = SessionLocal()
    v2_path = os.path.join(RULES_CONFIG_DIR, "aph_2025_26_v2.yaml")
    v2_data = load_rule_from_yaml(v2_path)

    # Count historical evaluations before dry run
    count_before = db.query(ComplianceResult).count()

    impact = run_dry_run_impact_report(db, v2_data, "APH-2025-26.v2")
    assert impact["candidate_rule_version"] == "APH-2025-26.v2"
    assert impact["total_active_instruments_evaluated"] > 0
    assert "impacted_instruments_flipped_count" in impact
    assert "flip_rate_percentage" in impact
    assert "newly_non_compliant_instruments" in impact
    assert len(impact["newly_non_compliant_instruments"]) > 0

    # Non-negotiable safeguard: Zero mutations to database records during dry-run
    count_after = db.query(ComplianceResult).count()
    assert count_before == count_after
    db.close()


def test_regulation_change_via_config_no_code_change_and_historical_preservation():
    """
    Demonstrates SIH requirement:
    Changing a rule via config (no code change) flips compliance, produces impact report,
    and old decisions preserve their rule version without retrospective mutation.
    """
    admin_token = get_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Diff comparison API
    res_diff = client.get("/api/v1/compliance/rules/diff?v1=APH-2024-27.v1&v2=APH-2025-26.v2", headers=headers)
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert diff_data["total_differences"] >= 2 # min_amount and validity_until were modified

    # 2. Dry-run Impact API
    res_dry = client.post("/api/v1/compliance/rules/dry-run-impact", json={"new_rule_version_tag": "APH-2025-26.v2"}, headers=headers)
    assert res_dry.status_code == 200
    dry_data = res_dry.json()
    assert dry_data["impacted_instruments_flipped_count"] > 0

    # 3. Publish API
    res_pub = client.post(
        "/api/v1/compliance/rules/publish",
        json={
            "version_tag": "APH-2025-26.v2",
            "authorized_by_justification": "AICTE Gazetted Revision: Mandatory lock-in extended to 10 years."
        },
        headers=headers
    )
    assert res_pub.status_code == 200
    pub_data = res_pub.json()
    assert pub_data["active_version"] == "APH-2025-26.v2"
    assert pub_data["instruments_re_evaluated"] > 0

    # 4. Verify Historical Decisions Preserve Original Version Tag
    db = SessionLocal()
    v1_records = db.query(ComplianceResult).filter(ComplianceResult.rule_version_used == "APH-2024-27.v1").all()
    v2_records = db.query(ComplianceResult).filter(ComplianceResult.rule_version_used == "APH-2025-26.v2").all()

    assert len(v1_records) > 0 # Historical records completely intact!
    assert len(v2_records) > 0 # New records evaluated under v2

    # Revert active back to v1 for clean state
    v1 = db.query(ComplianceRule).filter(ComplianceRule.version_tag == "APH-2024-27.v1").first()
    v2 = db.query(ComplianceRule).filter(ComplianceRule.version_tag == "APH-2025-26.v2").first()
    if v1 and v2:
        v1.is_active = True
        v2.is_active = False
        db.commit()
    db.close()


def test_compliance_scoring_per_institution_and_per_instrument():
    """Verifies per-institution and per-instrument score endpoints with breakdown."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Per-Instrument Evaluation Endpoint
    res_fdr = client.get("/api/v1/compliance/instrument/5/evaluation", headers=headers)
    assert res_fdr.status_code == 200
    eval_fdr = res_fdr.json()
    assert "fdr_number" in eval_fdr
    assert "overall_outcome" in eval_fdr
    assert "compliance_score" in eval_fdr
    assert "checks" in eval_fdr
    assert len(eval_fdr["checks"]) >= 6

    # 2. Per-Institution Score Endpoint
    res_inst = client.get("/api/v1/compliance/institution/1/score", headers=headers)
    assert res_inst.status_code == 200
    inst_score = res_inst.json()
    assert inst_score["institution_id"] == 1
    assert "overall_compliance_percentage" in inst_score
    assert "breakdown_by_instrument" in inst_score
    assert len(inst_score["breakdown_by_instrument"]) > 0
    assert inst_score["statutory_disclaimer"] == "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"

    # 3. Institution Scoping Security Test: Institution cannot access another college's score
    inst_token = get_inst_token()
    res_forbidden = client.get("/api/v1/compliance/institution/99/score", headers={"Authorization": f"Bearer {inst_token}"})
    assert res_forbidden.status_code == 403
