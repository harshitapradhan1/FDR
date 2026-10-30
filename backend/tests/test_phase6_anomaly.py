import pytest
from fastapi.testclient import TestClient
import os
import cv2
import numpy as np

from backend.app.main import app
from backend.app.core.database import SessionLocal
from backend.app.models.deposafe_models import FDR, User, Institution, FDRDocument
from backend.app.services.duplicate_detector import DuplicateDetector
from backend.app.services.forensics_service import DigitalForensicsAnalyzer
from backend.app.services.relationship_graph import build_ecosystem_networkx_graph
from backend.app.services.risk_engine import compute_review_priority
from data.seed_loader import load_synthetic_data_into_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_phase6_data():
    db = SessionLocal()
    heroes = db.query(FDR).filter(FDR.fdr_number == "BNB-DEL-HERO-1000").all()
    if len(heroes) < 2:
        load_synthetic_data_into_db(db)
    # Reset officer override state on hero
    h = db.query(FDR).filter(FDR.fdr_number == "BNB-DEL-HERO-1000").first()
    if h:
        h.officer_override = False
        h.officer_override_justification = None
        h.review_priority_score = None
        db.commit()
    db.close()
    yield

def get_officer_token() -> str:
    res = client.post("/api/v1/auth/login", json={"email": "officer@deposafe.aicte.gov.in", "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def get_inst_token() -> str:
    res = client.post("/api/v1/auth/login", json={"email": "institution1@vidya.edu.in", "password": "Password@123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_duplicate_detector_exact_bank_fdr_match():
    """Verifies cross-institution duplicate detection by composite key (bank_name + fdr_number)."""
    db = SessionLocal()
    hero = db.query(FDR).filter(FDR.fdr_number == "BNB-DEL-HERO-1000").first()
    assert hero is not None

    result = DuplicateDetector.check_fdr_duplicates(hero, db)
    assert result["has_collision"] is True
    assert len(result["exact_bank_fdr_matches"]) >= 1
    match = result["exact_bank_fdr_matches"][0]
    assert match["bank_name"] == "Bharat National Bank"
    assert match["matched_fdr_number"] == "BNB-DEL-HERO-1000"
    assert "Bharat National Bank" in match["reason"]
    db.close()


def test_digital_forensics_ela_heatmap_generation(tmp_path):
    """Verifies ELA heatmap generation and optical feature analysis."""
    # Create a synthetic image with an edited patch
    test_img = np.ones((300, 400, 3), dtype=np.uint8) * 240
    cv2.putText(test_img, "AICTE FDR TEST", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    test_file = str(tmp_path / "test_doc.jpg")
    cv2.imwrite(test_file, test_img)

    out_dir = str(tmp_path / "heatmaps")
    os.makedirs(out_dir, exist_ok=True)

    result = DigitalForensicsAnalyzer.analyze_document(test_file, doc_id=999, output_heatmap_dir=out_dir)
    assert "ela_score" in result
    assert 0.0 <= result["ela_score"] <= 100.0
    assert os.path.exists(result["ela_heatmap_path"])
    assert "font_inconsistencies" in result
    assert "metadata_anomalies" in result


def test_risk_engine_explainable_score():
    """Verifies that the risk score engine calculates transparent weighted indicators."""
    db = SessionLocal()
    # Reset officer override on hero FDR if previously set by override tests
    hero = db.query(FDR).filter(FDR.fdr_number == "BNB-DEL-HERO-1000").first()
    assert hero is not None
    hero.officer_override = False
    hero.officer_override_justification = None
    hero.review_priority_score = None
    db.commit()
    inst = db.query(Institution).filter(Institution.id == hero.institution_id).first()

    risk_profile = compute_review_priority(db, hero, inst)
    assert "review_priority_score" in risk_profile
    assert "review_priority_level" in risk_profile
    # Target hero case score is 60.0 to 80.0
    assert 60.0 <= risk_profile["review_priority_score"] <= 80.0
    assert risk_profile["review_priority_level"] in ["HIGH", "CRITICAL"]
    assert risk_profile["statutory_label"] == "Review priority indicator, not a fraud probability"

    # Verify each contributing reason has status and recommended action
    reasons = risk_profile["contributing_reasons"]
    assert len(reasons) >= 6
    for r in reasons:
        assert "indicator" in r
        assert "weight" in r
        assert "score_contribution" in r
        assert "status" in r
        assert r["status"] in ["Flagged", "Pending", "Complete"]
        assert "recommended_action" in r
    db.close()


def test_fdr_intelligence_graph_ecosystem_and_hero_detection():
    """Verifies NetworkX graph construction and cross-institution shared FDR pattern detection."""
    db = SessionLocal()
    graph_data = build_ecosystem_networkx_graph(db)
    assert "nodes" in graph_data
    assert "edges" in graph_data
    assert "anomalous_relationships" in graph_data
    assert len(graph_data["nodes"]) > 0
    assert len(graph_data["edges"]) > 0

    # Check for cross-institution shared FDR pattern
    patterns = graph_data["anomalous_relationships"]
    assert len(patterns) > 0
    hero_pattern = next((p for p in patterns if p["fdr_number"] == "BNB-DEL-HERO-1000"), None)
    assert hero_pattern is not None
    assert hero_pattern["pattern"] == "CROSS_INSTITUTION_SHARED_FDR"
    assert hero_pattern["severity"] == "CRITICAL"
    assert "Bharat National Bank" in hero_pattern["investigation_note"]
    db.close()


def test_api_endpoints_forensics_duplicates_and_risk_override():
    """Tests API endpoints for forensics, duplicate inspection, and audited risk override."""
    token = get_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Inspect Duplicates API
    res_dup = client.get("/api/v1/fdr/5/duplicates", headers=headers)
    assert res_dup.status_code == 200
    dup_data = res_dup.json()
    assert "has_collision" in dup_data
    assert dup_data["has_collision"] is True

    # 2. Digital Forensics API
    res_forensics = client.get("/api/v1/fdr/5/forensics", headers=headers)
    assert res_forensics.status_code == 200
    forensics_data = res_forensics.json()
    assert "forensics" in forensics_data
    assert "statutory_label" in forensics_data

    # 3. Ecosystem Graph API
    res_graph = client.get("/api/v1/graph/ecosystem", headers=headers)
    assert res_graph.status_code == 200
    assert "nodes" in res_graph.json()
    assert "edges" in res_graph.json()

    # 4. Audited Officer Risk Override
    override_payload = {
        "adjusted_score": 15.0,
        "justification": "Branch manager confirmed original physical instrument manually under official seal."
    }
    res_override = client.post("/api/v1/fdr/5/override-risk", json=override_payload, headers=headers)
    assert res_override.status_code == 200
    override_resp = res_override.json()
    assert override_resp["review_priority_score"] == 15.0
    assert override_resp["officer_override"] is True
    assert override_resp["justification"] == override_payload["justification"]

    # Verify unauthorized role cannot override risk
    inst_token = get_inst_token()
    res_unauth = client.post("/api/v1/fdr/5/override-risk", json=override_payload, headers={"Authorization": f"Bearer {inst_token}"})
    assert res_unauth.status_code == 403
