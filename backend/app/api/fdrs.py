import os
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import (
    User, UserRole, FDR, FDRDocument, FieldProvenance,
    BankVerificationRecord, Institution, FDRStatus,
    ProvenanceLevel, BankVerificationStatus
)
from backend.app.schemas.deposafe_schemas import (
    FDRCreate, FDROut, FDRDetailOut, FDRRenewRequest,
    FDRReleaseRequest, FDRReleaseApproval, OfficerOverrideRequest,
    BankVerifyRequest, ManualVerificationRequest, ProvenanceVerifyRequest
)
from backend.app.services.document_ai import extract_fdr_fields_from_pdf
from backend.app.services.risk_engine import compute_review_priority
from backend.app.services.audit_service import record_audit_event
from backend.app.rules.compliance_engine import get_active_rule, evaluate_fdr_compliance
from backend.app.adapters.bank_adapter import SimulatedBankVerificationAdapter, ManualVerificationAdapter

router = APIRouter(prefix="/fdrs", tags=["FDR Operations"])

@router.post("", response_model=FDROut)
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
        raise HTTPException(status_code=403, detail="Cannot register deposit for another institution")

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

@router.get("", response_model=List[FDROut])
def list_fdrs(
    status_filter: Optional[FDRStatus] = None,
    risk_level: Optional[str] = None,
    institution_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(FDR)
    
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id:
        query = query.filter(FDR.institution_id == current_user.institution_id)
    elif institution_id:
        query = query.filter(FDR.institution_id == institution_id)
        
    if status_filter:
        query = query.filter(FDR.status == status_filter)
    if risk_level:
        query = query.filter(FDR.review_priority_level == risk_level)

    return query.order_by(FDR.id.desc()).all()

@router.get("/{fdr_id}", response_model=FDRDetailOut)
def get_fdr_detail(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")
        
    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(fdr, institution, active_rule)

    docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).all()
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

@router.post("/{fdr_id}/upload-document")
async def upload_fdr_document(
    fdr_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")

    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    # Determine document version
    existing_docs_count = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).count()
    version = existing_docs_count + 1

    file_dir = os.path.join(settings.STORAGE_DIR, f"fdr_{fdr_id}")
    os.makedirs(file_dir, exist_ok=True)
    saved_filename = f"v{version}_{file.filename}"
    file_path = os.path.join(file_dir, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run Document AI
    ai_results = extract_fdr_fields_from_pdf(file_path)
    forensics = ai_results["forensics"]
    fields = ai_results["fields"]

    doc_record = FDRDocument(
        fdr_id=fdr.id,
        version=version,
        file_name=file.filename,
        file_path=file_path,
        file_hash_sha256=forensics["file_sha256"],
        perceptual_hash=forensics["perceptual_hash"],
        mime_type=file.content_type or "application/pdf",
        forensic_metadata=forensics,
        uploaded_by=current_user.id
    )
    db.add(doc_record)
    db.commit()

    # Update 4-level Provenance with AI_EXTRACTED values and mismatch detection
    for prov in fdr.provenance_fields:
        if prov.field_name in fields and fields[prov.field_name]["value"] is not None:
            extracted_val = str(fields[prov.field_name]["value"])
            prov.ai_extracted_value = extracted_val
            prov.ai_confidence = fields[prov.field_name]["confidence"]
            prov.bounding_box = fields[prov.field_name]["bbox"]
            
            # Check for mismatch against submitted
            sub_norm = (prov.submitted_value or "").strip().lower()
            ext_norm = extracted_val.strip().lower()

            if prov.field_name == "amount":
                try:
                    sub_num = float(sub_norm)
                    ext_num = float(ext_norm)
                    has_mismatch = abs(sub_num - ext_num) > 1.0
                except ValueError:
                    has_mismatch = (sub_norm != ext_norm)
            elif prov.field_name == "lien_marked":
                sub_bool = (sub_norm in ["yes", "true", "1"])
                ext_bool = (ext_norm in ["yes", "true", "1"])
                has_mismatch = (sub_bool != ext_bool)
            else:
                has_mismatch = (sub_norm != ext_norm)

            if has_mismatch:
                prov.status = ProvenanceLevel.MISMATCH
                prov.mismatch_reason = f"Discrepancy: Institution submitted '{prov.submitted_value}', AI document scan extracted '{extracted_val}'."
            else:
                prov.status = ProvenanceLevel.AI_EXTRACTED
    db.commit()

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

    record_audit_event(
        db=db,
        event_type="DOCUMENT_UPLOADED_AND_AI_PARSED",
        entity_type="FDR_DOCUMENT",
        entity_id=str(doc_record.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "fdr_id": fdr.id,
            "version": version,
            "sha256": forensics["file_sha256"],
            "producer_flagged": forensics["producer_flagged"],
            "review_priority_score": fdr.review_priority_score
        }
    )

    return {
        "message": "Document uploaded and intelligence analysis completed.",
        "version": version,
        "forensics": forensics,
        "extracted_fields": fields,
        "review_priority": risk_info
    }

@router.post("/{fdr_id}/verify-bank")
def verify_bank_details(
    fdr_id: int,
    req: BankVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")
        
    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    # Bank Verification Adapter pattern
    adapter = SimulatedBankVerificationAdapter()
    result = adapter.verify_instrument(
        bank_name=fdr.bank_name,
        fdr_number=fdr.fdr_number,
        ifsc_code=fdr.ifsc_code,
        expected_amount=fdr.amount,
        expected_holder=institution.society_or_trust_name
    )

    bank_status = BankVerificationStatus.AVAILABLE_CHECKS_PASSED if result["status"] == "AVAILABLE_CHECKS_PASSED" else BankVerificationStatus.NOT_CONFIRMED

    rec = BankVerificationRecord(
        fdr_id=fdr.id,
        adapter_used=result["adapter"],
        verification_status=bank_status,
        api_reference_id=result["api_reference_id"],
        watermark_notice=result["watermark"],
        verified_by=current_user.id,
        remarks=result["message"]
    )
    db.add(rec)

    # Update provenance BANK_CONFIRMED
    for prov in fdr.provenance_fields:
        if bank_status == BankVerificationStatus.AVAILABLE_CHECKS_PASSED:
            if prov.field_name == "amount" and result.get("bank_confirmed_amount") is not None:
                prov.bank_confirmed_value = str(result["bank_confirmed_amount"])
                prov.status = ProvenanceLevel.BANK_CONFIRMED
            elif prov.field_name == "fdr_number":
                prov.bank_confirmed_value = result.get("bank_fdr_number", fdr.fdr_number)
                prov.status = ProvenanceLevel.BANK_CONFIRMED
        else:
            if prov.field_name in ["amount", "fdr_number"]:
                prov.status = ProvenanceLevel.MISMATCH
                prov.mismatch_reason = "Bank core banking records did not confirm instrument validity."

    db.commit()

    # Re-evaluate risk
    active_rule = get_active_rule(db)
    comp_eval = evaluate_fdr_compliance(fdr, institution, active_rule)
    risk_info = compute_review_priority(db, fdr, institution, comp_eval)

    fdr.review_priority_score = risk_info["review_priority_score"]
    fdr.review_priority_level = risk_info["review_priority_level"]
    fdr.review_flags = risk_info["flags"]
    if comp_eval["overall_passed"] and bank_status == BankVerificationStatus.AVAILABLE_CHECKS_PASSED:
        fdr.status = FDRStatus.COMPLIANT
    else:
        fdr.status = FDRStatus.NON_COMPLIANT
    db.commit()

    record_audit_event(
        db=db,
        event_type="BANK_VERIFICATION_PERFORMED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "adapter": result["adapter"],
            "verification_status": bank_status.value,
            "watermark": result["watermark"],
            "api_ref": result["api_reference_id"]
        }
    )

    return {
        "verification_result": result,
        "watermark_notice": result["watermark"],
        "wording": result["wording"],
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
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found")
        
    institution = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    adapter = ManualVerificationAdapter(
        evidence_type=req.evidence_type,
        evidence_details=req.evidence_details,
        officer_name=current_user.full_name
    )
    result = adapter.verify_instrument(
        bank_name=fdr.bank_name,
        fdr_number=fdr.fdr_number,
        ifsc_code=fdr.ifsc_code,
        expected_amount=fdr.amount,
        expected_holder=institution.society_or_trust_name
    )

    rec = BankVerificationRecord(
        fdr_id=fdr.id,
        adapter_used=result["adapter"],
        verification_status=BankVerificationStatus.AVAILABLE_CHECKS_PASSED,
        api_reference_id=result["api_reference_id"],
        watermark_notice=result["watermark"],
        manual_evidence_type=req.evidence_type,
        manual_evidence_details=req.evidence_details,
        verified_by=current_user.id,
        remarks=req.remarks
    )
    db.add(rec)

    for prov in fdr.provenance_fields:
        if prov.field_name in ["amount", "fdr_number"]:
            prov.bank_confirmed_value = f"Manually verified via {req.evidence_type}"
            prov.status = ProvenanceLevel.BANK_CONFIRMED

    fdr.status = FDRStatus.COMPLIANT
    db.commit()

    record_audit_event(
        db=db,
        event_type="MANUAL_VERIFICATION_RECORDED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "evidence_type": req.evidence_type,
            "evidence_details": req.evidence_details,
            "remarks": req.remarks
        }
    )

    return {"message": "Manual verification evidence recorded successfully.", "result": result}

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
