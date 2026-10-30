import os
import shutil
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import (
    User, UserRole, FDR, FDRDocument, FieldProvenance,
    BankVerificationRecord, Institution, FDRStatus,
    ProvenanceLevel, BankVerificationStatus, AuditLog,
    CorrectionRecord, ProvenanceLedgerEntry, VerificationQueueItem
)
from backend.app.schemas.deposafe_schemas import (
    FDRCreate, FDROut, FDRDetailOut, FDRRenewRequest,
    FDRReleaseRequest, FDRReleaseApproval, OfficerOverrideRequest,
    BankVerifyRequest, ManualVerificationRequest, ProvenanceVerifyRequest,
    IntegrityCheckOut, IntegrityCheckDocumentResult, SignedDownloadUrlOut,
    FieldCorrectionRequest, FieldCorrectionOut, PROVENANCE_BADGE_MAP
)
from backend.app.services.document_ai import extract_fdr_fields_from_pdf
from backend.app.services.document_pipeline import run_document_ai_pipeline, persist_pipeline_results_to_db
from backend.app.services.risk_engine import compute_review_priority
from backend.app.services.audit_service import record_audit_event
from backend.app.rules.compliance_engine import get_active_rule, evaluate_fdr_compliance
from backend.app.adapters.bank_adapter import SimulatedBankVerificationAdapter, ManualVerificationAdapter
from backend.app.services.verification_orchestrator import VerificationOrchestrator, bank_circuit_breaker
from backend.app.services.reconciliation_service import CrossDocumentReconciler
from backend.app.services.document_service import (
    validate_and_scan_file, compute_file_sha256, generate_document_identifier,
    create_signed_download_token, verify_signed_download_token
)
from backend.app.services.lifecycle_service import build_fdr_lifecycle_passport

router = APIRouter(tags=["FDR Operations"])


# --------------------------------------------------------------------------
# Helper: Verify Stored Document Integrity
# --------------------------------------------------------------------------
def verify_document_integrity(db: Session, doc: FDRDocument) -> IntegrityCheckDocumentResult:
    if not os.path.exists(doc.file_path):
        return IntegrityCheckDocumentResult(
            document_id=doc.id,
            version=doc.version,
            file_name=doc.file_name,
            status="FILE_MISSING",
            is_tampered=True,
            recorded_hash=doc.file_hash_sha256,
            current_hash=None,
            chain_of_custody_verified=False,
            message=f"CRITICAL: Physical file missing at path '{doc.file_path}'"
        )

    with open(doc.file_path, "rb") as f:
        file_bytes = f.read()

    current_hash = hashlib.sha256(file_bytes).hexdigest()

    if current_hash != doc.file_hash_sha256:
        return IntegrityCheckDocumentResult(
            document_id=doc.id,
            version=doc.version,
            file_name=doc.file_name,
            status="TAMPERED",
            is_tampered=True,
            recorded_hash=doc.file_hash_sha256,
            current_hash=current_hash,
            chain_of_custody_verified=False,
            message="CRITICAL: Stored file byte content has been altered! Hash mismatch detected."
        )

    # Check if audit log chain contains this document
    audit_entry = db.query(AuditLog).filter(
        AuditLog.entity_type == "FDR_DOCUMENT",
        AuditLog.entity_id == str(doc.id)
    ).first()
    chain_verified = (audit_entry is not None)

    return IntegrityCheckDocumentResult(
        document_id=doc.id,
        version=doc.version,
        file_name=doc.file_name,
        status="INTACT",
        is_tampered=False,
        recorded_hash=doc.file_hash_sha256,
        current_hash=current_hash,
        chain_of_custody_verified=chain_verified,
        message="Document is intact and verified against immutable SHA-256 chain of custody."
    )


# --------------------------------------------------------------------------
# 1. Create FDR
# --------------------------------------------------------------------------
@router.post("", response_model=FDROut)
@router.post("/", response_model=FDROut, include_in_schema=False)
def create_fdr(
    fdr_data: FDRCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    institution = db.query(Institution).filter(Institution.id == fdr_data.institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # If institution user, can only create for their own institution
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr_data.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden: Cannot register deposit for another institution")

    new_fdr = FDR(
        institution_id=fdr_data.institution_id,
        bank_name=fdr_data.bank_name,
        branch_name=fdr_data.branch_name,
        ifsc_code=fdr_data.ifsc_code,
        fdr_number=fdr_data.fdr_number,
        amount=fdr_data.amount,
        issue_date=fdr_data.issue_date,
        maturity_date=fdr_data.maturity_date,
        tenure_months=fdr_data.tenure_months,
        interest_rate=fdr_data.interest_rate,
        auto_renewal=fdr_data.auto_renewal,
        joint_holder_name=fdr_data.joint_holder_name or f"Regional Officer AICTE & {institution.society_or_trust_name}",
        lien_marked_to_aicte=fdr_data.lien_marked_to_aicte,
        lien_clause_text=fdr_data.lien_clause_text,
        status=FDRStatus.PENDING_REVIEW
    )
    db.add(new_fdr)
    db.commit()
    db.refresh(new_fdr)

    # Initialize 4-level Field Provenance records with SUBMITTED values
    provenance_mappings = {
        "fdr_number": str(new_fdr.fdr_number),
        "amount": str(new_fdr.amount),
        "bank_name": str(new_fdr.bank_name),
        "ifsc_code": str(new_fdr.ifsc_code),
        "maturity_date": new_fdr.maturity_date.isoformat(),
        "lien_marked": "YES" if new_fdr.lien_marked_to_aicte else "NO",
        "tenure_months": str(new_fdr.tenure_months)
    }

    for fname, fval in provenance_mappings.items():
        prov = FieldProvenance(
            fdr_id=new_fdr.id,
            field_name=fname,
            submitted_value=fval,
            status=ProvenanceLevel.SUBMITTED,
            ai_confidence=1.0
        )
        db.add(prov)
    db.commit()

    # Initial compliance check
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(new_fdr, institution, active_rule)
    risk_info = compute_review_priority(db, new_fdr, institution, comp_eval)

    new_fdr.review_priority_score = risk_info["review_priority_score"]
    new_fdr.review_priority_level = risk_info["review_priority_level"]
    new_fdr.review_flags = risk_info["flags"]
    db.commit()
    db.refresh(new_fdr)

    record_audit_event(
        db=db,
        event_type="FDR_REGISTERED",
        entity_type="FDR",
        entity_id=str(new_fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "fdr_number": new_fdr.fdr_number,
            "bank_name": new_fdr.bank_name,
            "amount": new_fdr.amount,
            "institution_id": new_fdr.institution_id
        }
    )

    return new_fdr


# --------------------------------------------------------------------------
# 2. Search and Filter FDRs with Pagination
# --------------------------------------------------------------------------
@router.get("", response_model=List[FDROut])
@router.get("/", response_model=List[FDROut], include_in_schema=False)
def list_fdrs(
    search: Optional[str] = Query(None, description="Search by FDR number, bank name, branch"),
    institution_id: Optional[int] = Query(None, description="Filter by institution ID"),
    bank: Optional[str] = Query(None, description="Filter by bank name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by FDR status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    maturity_from: Optional[date] = Query(None, description="Maturity date from"),
    maturity_to: Optional[date] = Query(None, description="Maturity date to"),
    amount_min: Optional[float] = Query(None, description="Minimum amount"),
    amount_max: Optional[float] = Query(None, description="Maximum amount"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(FDR)

    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER:
        if institution_id is not None and institution_id != current_user.institution_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot access FDRs belonging to another institution"
            )
        query = query.filter(FDR.institution_id == current_user.institution_id)
    elif institution_id:
        query = query.filter(FDR.institution_id == institution_id)

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                FDR.fdr_number.ilike(search_pattern),
                FDR.bank_name.ilike(search_pattern),
                FDR.branch_name.ilike(search_pattern)
            )
        )

    # Specific filters
    if bank:
        query = query.filter(FDR.bank_name.ilike(f"%{bank}%"))
    if status_filter:
        query = query.filter(FDR.status == status_filter)
    if risk_level:
        query = query.filter(FDR.review_priority_level == risk_level)
    if maturity_from:
        query = query.filter(FDR.maturity_date >= maturity_from)
    if maturity_to:
        query = query.filter(FDR.maturity_date <= maturity_to)
    if amount_min is not None:
        query = query.filter(FDR.amount >= amount_min)
    if amount_max is not None:
        query = query.filter(FDR.amount <= amount_max)

    offset = (page - 1) * page_size
    return query.order_by(FDR.id.desc()).offset(offset).limit(page_size).all()


# --------------------------------------------------------------------------
# 3. Secure Document Upload (PDF/JPG/PNG, Malware scan, SHA-256, Versioning)
# --------------------------------------------------------------------------
@router.post("/upload")
@router.post("/{fdr_id}/upload-document")
async def upload_fdr_document(
    fdr_id: Optional[int] = None,
    file: UploadFile = File(...),
    doc_type: str = Form("FDR_CERTIFICATE"),
    fdr_id_form: Optional[int] = Form(None, alias="fdr_id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    target_fdr_id = fdr_id or fdr_id_form
    if not target_fdr_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameter: fdr_id"
        )

    fdr = db.query(FDR).filter(FDR.id == target_fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot upload documents for another institution"
        )

    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    # Read and validate file bytes (malware scan, size, magic bytes)
    file_bytes = await file.read()
    cleaned_filename, verified_mime = validate_and_scan_file(file, file_bytes)

    # Compute SHA-256 byte hash
    file_sha256 = compute_file_sha256(file_bytes)

    # Determine document version (replacement creates a new version; previous retained)
    existing_docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).all()
    version = len(existing_docs) + 1

    # Immutable storage directory
    file_dir = os.path.join(settings.STORAGE_DIR, f"fdr_{fdr.id}")
    os.makedirs(file_dir, exist_ok=True)
    saved_filename = f"v{version}_{cleaned_filename}"
    file_path = os.path.join(file_dir, saved_filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    # Run full AI Document Pipeline
    declared_details = {
        "fdr_number": fdr.fdr_number,
        "amount": fdr.amount,
        "bank_name": fdr.bank_name
    }
    pipeline_result = run_document_ai_pipeline(file_path, declared_details=declared_details)
    forensics = pipeline_result["forensics"]
    fields = pipeline_result["extracted_fields"]
    doc_type_detected = pipeline_result["document_classification"]["doc_type"]

    doc_record = FDRDocument(
        fdr_id=fdr.id,
        version=version,
        file_name=cleaned_filename,
        file_path=file_path,
        storage_path=f"storage/fdr_{fdr.id}/{saved_filename}",
        file_hash_sha256=file_sha256,
        file_hash=file_sha256,
        perceptual_hash=forensics.get("perceptual_hash", ""),
        mime_type=verified_mime,
        doc_type=doc_type_detected,
        file_size_bytes=len(file_bytes),
        forensic_metadata=forensics,
        uploaded_by=current_user.id
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    persist_pipeline_results_to_db(db, fdr.id, doc_record.id, pipeline_result)

    doc_unique_id = generate_document_identifier(doc_record.id, doc_record.created_at.year)

    # Re-evaluate compliance and review priority
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(fdr, institution, active_rule)
    risk_info = compute_review_priority(db, fdr, institution, comp_eval)

    fdr.review_priority_score = risk_info["review_priority_score"]
    fdr.review_priority_level = risk_info["review_priority_level"]
    fdr.review_flags = risk_info["flags"]
    if fdr.status == FDRStatus.PENDING_REVIEW:
        fdr.status = FDRStatus.UNDER_VERIFICATION
    db.commit()

    # Record tamper-evident hash-chained audit entry
    record_audit_event(
        db=db,
        event_type="DOCUMENT_STORED_IN_CUSTODY",
        entity_type="FDR_DOCUMENT",
        entity_id=str(doc_record.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "fdr_id": fdr.id,
            "document_id": doc_record.id,
            "document_identifier": doc_unique_id,
            "version": version,
            "sha256": file_sha256,
            "mime_type": verified_mime,
            "file_name": cleaned_filename,
            "producer_flagged": forensics.get("producer_flagged", False),
            "validation_status": pipeline_result["field_validation"]["overall_status"],
            "ui_wording": pipeline_result["field_validation"]["ui_wording"]
        }
    )

    return {
        "message": "Document securely uploaded and AI intelligence pipeline completed.",
        "document_id": doc_record.id,
        "document_identifier": doc_unique_id,
        "fdr_id": fdr.id,
        "version": version,
        "sha256": file_sha256,
        "mime_type": verified_mime,
        "forensics": forensics,
        "document_classification": pipeline_result["document_classification"],
        "layout_classification": pipeline_result["layout_classification"],
        "extracted_fields": fields,
        "low_confidence_fields": pipeline_result["low_confidence_fields"],
        "field_validation": pipeline_result["field_validation"],
        "review_priority": risk_info
    }


# --------------------------------------------------------------------------
# 3b. Field Correction & Safe Self-Improving Extraction Sample Logging
# --------------------------------------------------------------------------
@router.post("/{fdr_id}/correct-field", response_model=FieldCorrectionOut)
def record_field_correction(
    fdr_id: int,
    req: FieldCorrectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot correct fields for another institution"
        )

    prov = db.query(FieldProvenance).filter(
        FieldProvenance.fdr_id == fdr.id,
        FieldProvenance.field_name == req.field_name
    ).first()

    extracted_val = prov.ai_extracted_value if prov else None
    
    if prov:
        prov.officer_verified_value = req.corrected_value
        prov.status = ProvenanceLevel.OFFICER_VERIFIED
        prov.mismatch_reason = f"Correction by {current_user.full_name}: {req.correction_reason}"

    if hasattr(fdr, req.field_name):
        try:
            if req.field_name == "amount":
                setattr(fdr, req.field_name, float(req.corrected_value))
            elif req.field_name in ["issue_date", "maturity_date"]:
                setattr(fdr, req.field_name, date.fromisoformat(req.corrected_value))
            else:
                setattr(fdr, req.field_name, req.corrected_value)
        except Exception:
            pass

    latest_doc = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.desc()).first()
    doc_id = latest_doc.id if latest_doc else None

    correction = CorrectionRecord(
        fdr_id=fdr.id,
        document_id=doc_id,
        field_name=req.field_name,
        extracted_value=extracted_val,
        corrected_value=req.corrected_value,
        correction_reason=req.correction_reason,
        corrected_by=current_user.id
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)

    # Safe Self-Improving Extraction: append labelled training sample to disk
    corrections_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/corrections"))
    os.makedirs(corrections_dir, exist_ok=True)
    sample_file = os.path.join(corrections_dir, "correction_samples.jsonl")
    sample_data = {
        "correction_id": correction.id,
        "fdr_id": fdr.id,
        "document_id": doc_id,
        "field_name": req.field_name,
        "extracted_value": extracted_val,
        "ground_truth_corrected_value": req.corrected_value,
        "reason": req.correction_reason,
        "corrected_by_user_id": current_user.id,
        "timestamp": datetime.utcnow().isoformat()
    }
    import json
    with open(sample_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(sample_data) + "\n")

    record_audit_event(
        db=db,
        event_type="FIELD_CORRECTION_RECORD_CREATED",
        entity_type="FIELD_PROVENANCE",
        entity_id=str(prov.id if prov else correction.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "fdr_id": fdr.id,
            "field_name": req.field_name,
            "extracted_value": extracted_val,
            "corrected_value": req.corrected_value,
            "reason": req.correction_reason
        }
    )

    return correction


# --------------------------------------------------------------------------
# 3c. Pipeline Inspection & Visual BBox Preview
# --------------------------------------------------------------------------
@router.get("/{fdr_id}/pipeline-results")
def get_fdr_pipeline_results(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    doc = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No document found for this FDR")

    pipeline_result = run_document_ai_pipeline(doc.file_path, {
        "fdr_number": fdr.fdr_number,
        "amount": fdr.amount,
        "bank_name": fdr.bank_name
    })
    return {
        "fdr_id": fdr.id,
        "document_id": doc.id,
        "file_name": doc.file_name,
        **pipeline_result
    }


# --------------------------------------------------------------------------
# 4. Get FDR Detail (Server-Side Scoped)
# --------------------------------------------------------------------------
@router.get("/{fdr_id}", response_model=FDRDetailOut)
def get_fdr_detail(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot access FDRs belonging to another institution"
        )

    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(fdr, institution, active_rule)

    docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.asc()).all()
    bank_recs = db.query(BankVerificationRecord).filter(BankVerificationRecord.fdr_id == fdr.id).all()

    return {
        **fdr.__dict__,
        "institution": institution,
        "review_flags": fdr.review_flags or [],
        "provenance_fields": fdr.provenance_fields,
        "compliance_evaluation": comp_eval,
        "documents": [
            {
                "id": d.id,
                "document_identifier": generate_document_identifier(d.id, d.created_at.year),
                "version": d.version,
                "file_name": d.file_name,
                "file_hash_sha256": d.file_hash_sha256,
                "perceptual_hash": d.perceptual_hash,
                "forensic_metadata": d.forensic_metadata,
                "created_at": d.created_at.isoformat()
            } for d in docs
        ],
        "bank_verifications": [
            {
                "id": b.id,
                "adapter_used": b.adapter_used,
                "verification_status": b.verification_status.value,
                "watermark_notice": b.watermark_notice,
                "api_reference_id": b.api_reference_id,
                "manual_evidence_type": b.manual_evidence_type,
                "remarks": b.remarks,
                "verified_at": b.verified_at.isoformat()
            } for b in bank_recs
        ]
    }


# --------------------------------------------------------------------------
# 5. FDR Lifecycle Passport
# --------------------------------------------------------------------------
@router.get("/{fdr_id}/passport")
def get_fdr_passport(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    # Server-side institution scoping
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot access the lifecycle passport for another institution's FDR"
        )

    passport = build_fdr_lifecycle_passport(db, fdr_id)
    return passport


@router.get("/lineage/{lineage_id}/passport")
def get_lineage_passport(
    lineage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.lineage_id == lineage_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="Lineage not found")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot access the lifecycle passport for another institution's lineage"
        )

    return build_fdr_lifecycle_passport(db, fdr.id)


# --------------------------------------------------------------------------
# 6. Secure Expiring Download URLs & Signed Download
# --------------------------------------------------------------------------
@router.get("/{fdr_id}/documents/{document_id}/download-url", response_model=SignedDownloadUrlOut)
def get_document_download_url(
    fdr_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot generate download URL for another institution's document"
        )

    doc = db.query(FDRDocument).filter(FDRDocument.id == document_id, FDRDocument.fdr_id == fdr.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    token_data = create_signed_download_token(doc.id, expires_in_seconds=900)
    download_url = f"/api/v1/fdrs/documents/download?token={token_data['token']}"

    return {
        "document_id": doc.id,
        "file_name": doc.file_name,
        "download_url": download_url,
        "expires_at": token_data["expires_at"],
        "expires_in_seconds": token_data["expires_in_seconds"],
        "disclaimer": "Temporary expiring link (valid 15m). Do not share."
    }


@router.get("/documents/download")
def download_document_with_token(
    token: str = Query(..., description="HMAC-signed expiring download token"),
    db: Session = Depends(get_db)
):
    document_id = verify_signed_download_token(token)
    doc = db.query(FDRDocument).filter(FDRDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in storage registry")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Physical file not found in storage")

    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type=doc.mime_type
    )


# --------------------------------------------------------------------------
# 7. Tamper-Evident Chain of Custody & File Integrity Check
# --------------------------------------------------------------------------
@router.get("/{fdr_id}/integrity-check", response_model=IntegrityCheckOut)
def check_fdr_integrity(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot run integrity check on another institution's FDR"
        )

    docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.asc()).all()
    results = [verify_document_integrity(db, d) for d in docs]
    has_tampering = any(r.is_tampered for r in results)

    record_audit_event(
        db=db,
        event_type="INTEGRITY_CHECK_EXECUTED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "documents_checked": len(results),
            "has_tampering": has_tampering,
            "overall_status": "TAMPERED" if has_tampering else "INTACT"
        }
    )

    return {
        "fdr_id": fdr.id,
        "overall_status": "TAMPERED" if has_tampering else "INTACT",
        "has_tampering": has_tampering,
        "documents_checked": len(results),
        "results": results,
        "disclaimer": "Cryptographic integrity verified against immutable SHA-256 chain of custody."
    }


@router.get("/documents/{document_id}/integrity-check", response_model=IntegrityCheckDocumentResult)
def check_single_document_integrity(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(FDRDocument).filter(FDRDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fdr = db.query(FDR).filter(FDR.id == doc.fdr_id).first()
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot run integrity check on another institution's document"
        )

    return verify_document_integrity(db, doc)


# --------------------------------------------------------------------------
# 8. Human-in-the-Loop Actions & Bank Verification
# --------------------------------------------------------------------------
@router.get("/circuit-breaker/status")
def get_circuit_breaker_status():
    """Returns live telemetry of the Core Banking Integration Circuit Breaker."""
    return {
        "circuit_breaker": bank_circuit_breaker.get_metrics(),
        "disclaimer": "SIMULATED, not a real bank verification"
    }

@router.post("/{fdr_id}/verify-bank")
def verify_bank_details(
    fdr_id: int,
    req: BankVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes resilient Bank Verification through VerificationOrchestrator:
    - Retries transient timeouts / rate-limits with exponential backoff.
    - Prevents cascade failures via Circuit Breaker pattern.
    - Updates Dual-Truth Four-Source Ledger and Field Provenance.
    - Routes to Officer Review with SOURCE_UNAVAILABLE if core gateway is down.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    # Scoped access validation
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to FDR record outside your institution")

    # Execute through VerificationOrchestrator
    orchestration_res = VerificationOrchestrator.execute_verification(
        fdr_id=fdr.id,
        db=db,
        scenario=req.scenario,
        actor_id=current_user.id
    )

    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(fdr, institution, active_rule)
    risk_info = compute_review_priority(db, fdr, institution, comp_eval)

    fdr.review_priority_score = risk_info["review_priority_score"]
    fdr.review_priority_level = risk_info["review_priority_level"]
    fdr.review_flags = risk_info["flags"]
    db.commit()

    return {
        "success": orchestration_res.get("success", False),
        "fdr_id": fdr.id,
        "fdr_number": fdr.fdr_number,
        "verification_status": orchestration_res.get("verification_status"),
        "wording": orchestration_res.get("wording"),
        "diffs": orchestration_res.get("diffs", {}),
        "api_reference_id": orchestration_res.get("api_reference_id"),
        "signature": orchestration_res.get("signature"),
        "watermark_notice": orchestration_res.get("watermark"),
        "simulated": True,
        "message": orchestration_res.get("message") or orchestration_res.get("reason"),
        "circuit_breaker": orchestration_res.get("circuit_breaker"),
        "review_priority": risk_info,
        "new_status": fdr.status.value
    }


@router.post("/{fdr_id}/verify-manual")
def record_manual_bank_verification(
    fdr_id: int,
    req: ManualVerificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]))
):
    """
    Officer manual verification recording when automated bank feeds are unavailable:
    - Elevates field provenance to OFFICER_VERIFIED (clearly distinct from BANK_CONFIRMED).
    - Preserves evidence type, reference number, and remarks in immutable audit trail.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    method = req.method or req.evidence_type or "OFFICIAL_PORTAL_VISIT"
    ref_id = req.reference_id or f"MAN-VERIF-{fdr.id}-{datetime.utcnow().strftime('%Y%m%d')}"
    remarks = req.remarks or f"Verified manually by officer {current_user.full_name} via {method}"
    now = datetime.utcnow()

    # Record BankVerificationRecord as OFFICER_MANUAL_VERIFICATION
    rec = BankVerificationRecord(
        fdr_id=fdr.id,
        adapter_used="OFFICER_MANUAL_VERIFICATION",
        verification_status=BankVerificationStatus.AVAILABLE_CHECKS_PASSED,
        api_reference_id=ref_id,
        watermark_notice="OFFICIAL OFFICER VERIFICATION RECORD - MANUAL PROVENANCE",
        manual_evidence_type=method,
        manual_evidence_details={
            "reference_id": ref_id,
            "remarks": remarks,
            "officer_name": current_user.full_name,
            "evidence_document_id": req.evidence_document_id,
            "verified_fields": req.verified_fields
        },
        verified_by=current_user.id,
        verified_at=now,
        remarks=remarks
    )
    db.add(rec)

    # Update Dual-Truth Provenance strictly as OFFICER_VERIFIED (distinct from BANK_CONFIRMED)
    prov_records = db.query(FieldProvenance).filter(FieldProvenance.fdr_id == fdr.id).all()
    prov_map = {p.field_name: p for p in prov_records}

    field_updates = req.verified_fields or {
        "fdr_number": fdr.fdr_number,
        "amount": str(fdr.amount),
        "bank_name": fdr.bank_name,
        "maturity_date": fdr.maturity_date.isoformat() if fdr.maturity_date else None,
        "issue_date": fdr.issue_date.isoformat() if fdr.issue_date else None
    }

    for f_name, f_val in field_updates.items():
        p = prov_map.get(f_name)
        if not p:
            p = FieldProvenance(fdr_id=fdr.id, field_name=f_name, submitted_value=str(f_val))
            db.add(p)
            prov_map[f_name] = p

        p.officer_verified_value = str(f_val)
        p.officer_verified_at = now
        p.officer_verified_by = f"Officer {current_user.full_name} ({current_user.designation or 'Verification Officer'})"
        p.status = ProvenanceLevel.OFFICER_VERIFIED
        p.mismatch_reason = f"Manual evidence validated via {method} (Ref: {ref_id})"
        p.conflicts = []

        # Append to Provenance Ledger
        ledger_entry = ProvenanceLedgerEntry(
            fdr_id=fdr.id,
            field_name=f_name,
            source=ProvenanceLevel.OFFICER_VERIFIED,
            value=str(f_val),
            actor_id=current_user.id,
            actor_name=current_user.full_name,
            actor_role=current_user.role.value,
            timestamp=now,
            confidence=1.0,
            evidence_ref=ref_id,
            remarks=remarks
        )
        db.add(ledger_entry)

    fdr.status = FDRStatus.ACTIVE
    db.commit()

    record_audit_event(
        db=db,
        event_type="OFFICER_MANUAL_VERIFICATION_RECORDED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "method": method,
            "reference_id": ref_id,
            "officer_name": current_user.full_name,
            "remarks": remarks,
            "evidence_document_id": req.evidence_document_id
        }
    )

    return {
        "success": True,
        "message": f"Officer manual verification successfully recorded. Provenance elevated to OFFICER_VERIFIED (Ref: {ref_id}).",
        "provenance_status": ProvenanceLevel.OFFICER_VERIFIED.value,
        "reference_id": ref_id,
        "method": method,
        "verified_by": current_user.full_name
    }


@router.get("/{fdr_id}/cross-document-reconciliation")
@router.get("/{fdr_id}/reconciliation")
def get_cross_document_reconciliation(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cross-document reconciliation: compares FDR, bank confirmation letter,
    institution declaration, and renewal instruments field by field.
    Produces a match/mismatch matrix with evidence references and bounding boxes.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    # Scoped access validation
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to FDR record outside your institution")

    reconciliation = CrossDocumentReconciler.reconcile_fdr_documents(fdr_id=fdr.id, db=db)
    return reconciliation


@router.get("/{fdr_id}/provenance-ledger")
def get_provenance_ledger(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the Dual-Truth Four-Source Ledger:
    - Side-by-side values from SUBMITTED, AI_EXTRACTED, BANK_CONFIRMED, OFFICER_VERIFIED.
    - Timestamps, actors, conflict explanations, and UI badge colors.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to FDR record outside your institution")

    prov_records = db.query(FieldProvenance).filter(FieldProvenance.fdr_id == fdr.id).all()
    ledger_history = db.query(ProvenanceLedgerEntry).filter(ProvenanceLedgerEntry.fdr_id == fdr.id).order_by(ProvenanceLedgerEntry.timestamp.desc()).all()

    provenance_fields = []
    for p in prov_records:
        style = PROVENANCE_BADGE_MAP.get(p.status.value)
        provenance_fields.append({
            "id": p.id,
            "field_name": p.field_name,
            "submitted_value": p.submitted_value,
            "ai_extracted_value": p.ai_extracted_value,
            "bank_confirmed_value": p.bank_confirmed_value,
            "officer_verified_value": p.officer_verified_value,
            "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
            "ai_extracted_at": p.ai_extracted_at.isoformat() if p.ai_extracted_at else None,
            "bank_confirmed_at": p.bank_confirmed_at.isoformat() if p.bank_confirmed_at else None,
            "officer_verified_at": p.officer_verified_at.isoformat() if p.officer_verified_at else None,
            "submitted_by": p.submitted_by,
            "ai_extracted_by": p.ai_extracted_by,
            "bank_confirmed_by": p.bank_confirmed_by,
            "officer_verified_by": p.officer_verified_by,
            "status": p.status.value,
            "ai_confidence": p.ai_confidence,
            "bounding_box": p.bounding_box,
            "mismatch_reason": p.mismatch_reason,
            "conflicts": p.conflicts or [],
            "badge_style": {
                "source": style.source,
                "label": style.label,
                "bg_class": style.bg_class,
                "text_class": style.text_class,
                "border_class": style.border_class,
                "hex_color": style.hex_color
            } if style else None
        })

    return {
        "fdr_id": fdr.id,
        "fdr_number": fdr.fdr_number,
        "institution_id": fdr.institution_id,
        "provenance_fields": provenance_fields,
        "mutation_history_count": len(ledger_history)
    }


@router.post("/{fdr_id}/verify-field")
def verify_field_provenance(
    fdr_id: int,
    req: ProvenanceVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]))
):
    prov = db.query(FieldProvenance).filter(
        FieldProvenance.fdr_id == fdr_id,
        FieldProvenance.field_name == req.field_name
    ).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Provenance field not found")

    old_status = prov.status
    prov.officer_verified_value = req.verified_value
    prov.status = ProvenanceLevel.OFFICER_VERIFIED
    prov.mismatch_reason = f"Verified by {current_user.full_name}: {req.officer_notes or 'Field verified in human-in-the-loop review'}"
    db.commit()

    record_audit_event(
        db=db,
        event_type="PROVENANCE_FIELD_OFFICER_VERIFIED",
        entity_type="FIELD_PROVENANCE",
        entity_id=str(prov.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "field_name": req.field_name,
            "verified_value": req.verified_value,
            "previous_status": old_status.value
        }
    )

    return {"message": f"Field '{req.field_name}' marked as OFFICER_VERIFIED", "field": prov}


@router.post("/{fdr_id}/override")
def officer_override(
    fdr_id: int,
    req: OfficerOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]))
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    fdr.officer_override = True
    fdr.officer_override_justification = req.justification
    fdr.officer_override_by = current_user.id
    fdr.officer_override_at = datetime.utcnow()

    if req.adjusted_score is not None:
        fdr.review_priority_score = req.adjusted_score
        if req.adjusted_score < 25.0:
            fdr.review_priority_level = "LOW"
        elif req.adjusted_score < 50.0:
            fdr.review_priority_level = "MEDIUM"
        elif req.adjusted_score < 80.0:
            fdr.review_priority_level = "HIGH"
        else:
            fdr.review_priority_level = "CRITICAL"

    if req.new_status:
        fdr.status = req.new_status

    db.commit()

    record_audit_event(
        db=db,
        event_type="OFFICER_REVIEW_OVERRIDE",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "justification": req.justification,
            "adjusted_score": req.adjusted_score,
            "new_status": req.new_status.value if req.new_status else None
        }
    )

    return {
        "message": "Officer override recorded with justification.",
        "fdr_id": fdr.id,
        "officer_override": fdr.officer_override,
        "review_priority_score": fdr.review_priority_score,
        "status": fdr.status.value,
        "justification": fdr.officer_override_justification
    }


@router.post("/{fdr_id}/renew")
def renew_fdr(
    fdr_id: int,
    req: FDRRenewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Non-negotiable rule: Never overwrite an FDR.
    Renewal creates a new linked instrument; old one becomes RENEWED_SUPERSEDED.
    """
    old_fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not old_fdr:
        raise HTTPException(status_code=404, detail="Existing FDR not found")

    new_fdr = FDR(
        institution_id=old_fdr.institution_id,
        lineage_id=old_fdr.lineage_id,
        bank_name=req.bank_name,
        branch_name=req.branch_name,
        ifsc_code=req.ifsc_code,
        fdr_number=req.new_fdr_number,
        amount=req.amount,
        issue_date=req.issue_date,
        maturity_date=req.maturity_date,
        tenure_months=req.tenure_months,
        interest_rate=req.interest_rate,
        auto_renewal=req.auto_renewal,
        joint_holder_name=old_fdr.joint_holder_name,
        lien_marked_to_aicte=True,
        lien_clause_text=req.lien_clause_text or old_fdr.lien_clause_text,
        status=FDRStatus.PENDING_REVIEW,
        predecessor_fdr_id=old_fdr.id
    )
    db.add(new_fdr)
    db.commit()
    db.refresh(new_fdr)

    # Mark old instrument as SUPERSEDED and link successor
    old_fdr.status = FDRStatus.RENEWED_SUPERSEDED
    old_fdr.successor_fdr_id = new_fdr.id
    old_fdr.superseded_by = new_fdr.id
    db.commit()

    record_audit_event(
        db=db,
        event_type="FDR_RENEWAL_CHAIN_CREATED",
        entity_type="FDR",
        entity_id=str(new_fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "predecessor_fdr_id": old_fdr.id,
            "predecessor_fdr_number": old_fdr.fdr_number,
            "new_fdr_id": new_fdr.id,
            "new_fdr_number": new_fdr.fdr_number
        }
    )

    return {
        "message": f"Renewal instrument created successfully. Previous FDR #{old_fdr.fdr_number} is now marked SUPERSEDED.",
        "new_fdr_id": new_fdr.id,
        "predecessor_fdr_id": old_fdr.id
    }


@router.post("/{fdr_id}/request-release")
def request_fdr_release(
    fdr_id: int,
    req: FDRReleaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    fdr.status = FDRStatus.RELEASE_REQUESTED
    fdr.release_requested_at = datetime.utcnow()
    fdr.release_justification = f"{req.justification} | NOC Ref: {req.noc_reference}"
    db.commit()

    record_audit_event(
        db=db,
        event_type="FDR_RELEASE_REQUESTED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "justification": req.justification,
            "noc_reference": req.noc_reference
        }
    )

    return {"message": "Deposit release requested. Pending Competent Authority authorization.", "fdr": fdr}


@router.post("/{fdr_id}/authorize-release")
def authorize_fdr_release(
    fdr_id: int,
    req: FDRReleaseApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.COMPETENT_AUTHORITY, UserRole.SYSTEM_ADMIN]))
):
    """
    Non-negotiable rule: Only the competent-authority role can approve release/refund.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    if req.approved:
        fdr.status = FDRStatus.RELEASED
        fdr.release_authorized_by = current_user.id
        fdr.release_authorized_at = datetime.utcnow()
        fdr.release_order_ref = req.release_order_ref
    else:
        fdr.status = FDRStatus.COMPLIANT

    db.commit()

    record_audit_event(
        db=db,
        event_type="FDR_RELEASE_AUTHORIZED" if req.approved else "FDR_RELEASE_REJECTED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "approved": req.approved,
            "release_order_ref": req.release_order_ref,
            "remarks": req.remarks,
            "authorized_by": current_user.full_name
        }
    )

    return {
        "message": "Deposit release officially authorized by Competent Authority." if req.approved else "Deposit release rejected.",
        "status": fdr.status.value,
        "release_order_ref": req.release_order_ref
    }
