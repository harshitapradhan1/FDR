import os
import io
import time
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.services.seed_service import seed_database_if_empty
from backend.app.models.deposafe_models import User, FDR, FDRDocument, Institution, UserRole
from backend.app.services.pdf_generator import generate_synthetic_fdr_pdf

client = TestClient(app)

def make_fdr_pdf(filename: str, fdr_number: str = "SBI-DEL-9876543210", amount: float = 3500000.0) -> bytes:
    tmp_path = f"/tmp/{filename}"
    generate_synthetic_fdr_pdf(
        output_path=tmp_path,
        bank_name="State Bank of India",
        branch_name="Main Branch",
        ifsc_code="SBIN0000691",
        fdr_number=fdr_number,
        amount=amount,
        issue_date=date(2024, 4, 1),
        maturity_date=date(2029, 4, 1),
        society_name="Shree Vidya Educational Trust",
        institution_name="Vidya Institute of Technology & Science",
        regional_office="North Western Regional Office"
    )
    with open(tmp_path, "rb") as f:
        data = f.read()
    return data

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
# Test 1: Institution Scoped Access Control (Cannot Read / Upload Another's FDR)
# --------------------------------------------------------------------------
def test_institution_scoped_access_forbidden():
    """
    Non-negotiable rule: Institution-scoped access enforced server-side.
    Institution 1 user cannot read or access FDRs belonging to Institution 2.
    """
    db = SessionLocal()
    # Find two distinct institutions and their users
    inst1 = db.query(Institution).filter(Institution.id == 1).first()
    inst2 = db.query(Institution).filter(Institution.id == 2).first()
    
    # Institution 1 user
    user1 = db.query(User).filter(User.institution_id == 1).first()
    # Institution 2 user
    user2 = db.query(User).filter(User.institution_id == 2).first()
    
    # FDR belonging to Institution 2
    fdr2 = db.query(FDR).filter(FDR.institution_id == 2).first()
    db.close()

    assert user1 is not None and user2 is not None and fdr2 is not None

    token1 = get_auth_token(user1.email)
    headers1 = {"Authorization": f"Bearer {token1}"}

    # 1. Institution 1 user attempts to read Institution 2's FDR -> MUST be 403 Forbidden
    res = client.get(f"/fdr/{fdr2.id}", headers=headers1)
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

    # 2. Institution 1 user attempts to access Institution 2's passport -> MUST be 403 Forbidden
    res_passport = client.get(f"/fdr/{fdr2.id}/passport", headers=headers1)
    assert res_passport.status_code == 403

    # 3. Institution 1 user querying list with institution_id=2 -> MUST be 403 Forbidden
    res_list = client.get("/fdr?institution_id=2", headers=headers1)
    assert res_list.status_code == 403

    # 4. Institution 1 user listing FDRs without query param receives ONLY institution 1 FDRs
    res_own = client.get("/fdr", headers=headers1)
    assert res_own.status_code == 200
    for item in res_own.json():
        assert item["institution_id"] == 1


# --------------------------------------------------------------------------
# Test 2: Secure Upload, Malware Scan Stub & File Validation
# --------------------------------------------------------------------------
def test_secure_upload_validation_and_malware_stub():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Reject invalid file extension (.exe)
    bad_file = ("exploit.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")
    res = client.post("/fdr/upload", data={"fdr_id": 1}, files={"file": bad_file}, headers=headers)
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]

    # 2. Reject Malware/EICAR payload
    eicar_bytes = b"%PDF-1.4\nX5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*\n%%EOF"
    malware_file = ("fdr_eicar.pdf", eicar_bytes, "application/pdf")
    res_malware = client.post("/fdr/upload", data={"fdr_id": 1}, files={"file": malware_file}, headers=headers)
    assert res_malware.status_code == 400
    assert "Malware/EICAR signature detected" in res_malware.json()["detail"]


# --------------------------------------------------------------------------
# Test 3: Document Replacement Keeps History (v1 and v2 Retained)
# --------------------------------------------------------------------------
def test_document_versioning_keeps_history():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    fdr = db.query(FDR).filter(FDR.id == 1).first()
    db.close()

    # Generate PDF 1
    pdf1_bytes = make_fdr_pdf("v1_fdr.pdf", "SBI-DEL-9876543210", 3500000.0)

    # Upload Version 1
    res1 = client.post(
        "/fdr/upload",
        data={"fdr_id": fdr.id, "doc_type": "FDR_CERTIFICATE"},
        files={"file": ("certificate_v1.pdf", pdf1_bytes, "application/pdf")},
        headers=headers
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["version"] >= 1
    v1_id = data1["document_id"]

    # Upload Version 2 (Replacement / Revision)
    pdf2_bytes = make_fdr_pdf("v2_fdr.pdf", "SBI-DEL-9876543210", 4000000.0)

    res2 = client.post(
        "/fdr/upload",
        data={"fdr_id": fdr.id, "doc_type": "FDR_CERTIFICATE"},
        files={"file": ("certificate_v2.pdf", pdf2_bytes, "application/pdf")},
        headers=headers
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["version"] == data1["version"] + 1
    v2_id = data2["document_id"]
    assert v2_id != v1_id

    # Verify both versions exist in FDR detail
    detail_res = client.get(f"/fdr/{fdr.id}", headers=headers)
    assert detail_res.status_code == 200
    docs = detail_res.json()["documents"]
    doc_ids = [d["id"] for d in docs]
    assert v1_id in doc_ids
    assert v2_id in doc_ids


# --------------------------------------------------------------------------
# Test 4: Integrity Check Detects Manually Altered Stored File
# --------------------------------------------------------------------------
def test_integrity_check_detects_altered_stored_file():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Upload clean document to FDR 2
    pdf_bytes = make_fdr_pdf("integrity_test.pdf", "ACB-MUM-771122", 1500000.0)

    upload_res = client.post(
        "/fdr/upload",
        data={"fdr_id": 2},
        files={"file": ("integrity_sample.pdf", pdf_bytes, "application/pdf")},
        headers=headers
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]

    # 1. Check integrity BEFORE alteration: MUST be INTACT
    check1 = client.get(f"/fdr/2/integrity-check", headers=headers)
    assert check1.status_code == 200
    res1_data = check1.json()
    assert res1_data["overall_status"] == "INTACT"
    assert res1_data["has_tampering"] is False

    # 2. Simulate manual tampering on disk (attacker or corruption modifies file bytes)
    db = SessionLocal()
    doc_record = db.query(FDRDocument).filter(FDRDocument.id == doc_id).first()
    file_path = doc_record.file_path
    db.close()

    assert os.path.exists(file_path)
    with open(file_path, "ab") as f:
        f.write(b"\n% TAMPERED_PAYLOAD_INSERTED_BY_MALICIOUS_ACTOR %")

    # 3. Check integrity AFTER alteration: MUST DETECT TAMPERING
    check2 = client.get(f"/fdr/2/integrity-check", headers=headers)
    assert check2.status_code == 200
    res2_data = check2.json()
    assert res2_data["overall_status"] == "TAMPERED"
    assert res2_data["has_tampering"] is True
    
    # Specific document result flags tampering
    tampered_doc = next(r for r in res2_data["results"] if r["document_id"] == doc_id)
    assert tampered_doc["status"] == "TAMPERED"
    assert tampered_doc["is_tampered"] is True
    assert tampered_doc["current_hash"] != tampered_doc["recorded_hash"]


# --------------------------------------------------------------------------
# Test 5: FDR Lifecycle Passport Generation
# --------------------------------------------------------------------------
def test_fdr_lifecycle_passport():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Query Passport for FDR 1
    res = client.get("/fdr/1/passport", headers=headers)
    assert res.status_code == 200
    passport = res.json()

    # Validate essential Passport features
    assert "lineage_id" in passport
    assert "original_instrument" in passport
    assert "active_instrument" in passport
    assert "instruments" in passport
    assert "amount_evolution" in passport
    assert "verification_history" in passport
    assert "chronological_timeline" in passport
    assert "non_destructive_guarantee" in passport
    assert len(passport["chronological_timeline"]) > 0

    # Ensure timeline items are chronological
    timeline = passport["chronological_timeline"]
    timestamps = [t["timestamp"] for t in timeline]
    assert timestamps == sorted(timestamps)


# --------------------------------------------------------------------------
# Test 6: Secure Expiring Download URL Flow
# --------------------------------------------------------------------------
def test_secure_expiring_download_url():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Request signed download URL for Document 1
    db = SessionLocal()
    doc = db.query(FDRDocument).first()
    db.close()

    assert doc is not None

    url_res = client.get(f"/fdr/{doc.fdr_id}/documents/{doc.id}/download-url", headers=headers)
    assert url_res.status_code == 200
    url_data = url_res.json()
    assert "download_url" in url_data
    assert "expires_at" in url_data
    assert url_data["expires_in_seconds"] == 900

    # Execute download via signed expiring URL (public unauthenticated or officer)
    download_url = url_data["download_url"]
    dl_res = client.get(download_url)
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 0

    # Tampered token signature fails
    tampered_url = download_url + "tampered"
    tampered_res = client.get(tampered_url)
    assert tampered_res.status_code in [400, 403]


# --------------------------------------------------------------------------
# Test 7: Search and Filter Capabilities
# --------------------------------------------------------------------------
def test_fdr_search_and_filters():
    token = get_auth_token("officer@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Search by bank name
    res_bank = client.get("/fdr?bank=State%20Bank", headers=headers)
    assert res_bank.status_code == 200
    assert len(res_bank.json()) > 0

    # 2. Filter by amount range
    res_amount = client.get("/fdr?amount_min=2000000&amount_max=5000000", headers=headers)
    assert res_amount.status_code == 200
    for item in res_amount.json():
        assert 2000000.0 <= item["amount"] <= 5000000.0

    # 3. Filter by maturity date
    res_mat = client.get("/fdr?maturity_from=2025-01-01", headers=headers)
    assert res_mat.status_code == 200


# --------------------------------------------------------------------------
# Test 8: Institutions API Management
# --------------------------------------------------------------------------
def test_institutions_api():
    admin_token = get_auth_token("admin@deposafe.aicte.gov.in")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # List institutions
    res_list = client.get("/institutions", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 2

    # Get institution detail
    res_detail = client.get("/institutions/1", headers=headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == 1

    # Get institution FDRs
    res_fdrs = client.get("/institutions/1/fdrs", headers=headers)
    assert res_fdrs.status_code == 200
    assert len(res_fdrs.json()) >= 1
