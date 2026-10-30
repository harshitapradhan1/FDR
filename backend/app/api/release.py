"""DepoSafe Release and Refund Lifecycle API Router.

Implements all 9 state machine transitions and statutory safeguards:
1. POST /fdr/{fdr_id}/release/request: Institution submits release/refund request.
2. GET /fdr/{fdr_id}/release/readiness: Automatically evaluates release conditions checklist (advisory only).
3. POST /fdr/{fdr_id}/release/scrutiny: Officer moves request through Scrutiny / Clarification / Recommendation.
4. POST /fdr/{fdr_id}/release/authorize: Only COMPETENT_AUTHORITY can approve/reject; requires typed justification.
5. POST /fdr/{fdr_id}/release/disburse: Competent Authority marks RELEASED then CLOSED; preserves full history in Passport.
6. GET /release/requests: Lists all active and historical release requests with status filters.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import (
    User, UserRole, FDR, Institution, ReleaseRequest, ReleaseStatus, FDRStatus
)
from backend.app.state_machines.fdr_state_machine import ReleaseWorkflowStateMachine, FDRStateMachine, InvalidStateTransitionError
from backend.app.services.release_service import evaluate_release_readiness
from backend.app.schemas.release_schemas import (
    ReleaseSubmissionRequest, ReleaseScrutinyRequest, ReleaseAuthorizationRequest
)
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/release", tags=["Deposit Release & Refund"])


# --------------------------------------------------------------------------
# 1. Submission & Readiness Check
# --------------------------------------------------------------------------
@router.post("/fdr/{fdr_id}/request")
def submit_release_request(
    fdr_id: int,
    req: ReleaseSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Institution submits deposit release/refund request:
    Transitions state Draft -> Submitted.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot request release for another college's deposit.")

    existing_rel = db.query(ReleaseRequest).filter(
        ReleaseRequest.fdr_id == fdr.id,
        ReleaseRequest.status.notin_([ReleaseStatus.CLOSED, ReleaseStatus.REJECTED])
    ).first()

    if existing_rel and existing_rel.status != ReleaseStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Active release request #{existing_rel.id} already exists in status '{existing_rel.status.value}'.")

    if not existing_rel:
        existing_rel = ReleaseRequest(
            fdr_id=fdr.id,
            institution_id=fdr.institution_id,
            status=ReleaseStatus.DRAFT,
            justification=req.justification,
            noc_reference=req.noc_reference,
            requested_by=current_user.id
        )
        db.add(existing_rel)
        db.commit()
        db.refresh(existing_rel)

    # State Machine Transition: Draft -> Submitted
    sm = ReleaseWorkflowStateMachine(existing_rel.status)
    try:
        new_status = sm.trigger("SUBMIT", actor_role=current_user.role.value)
    except (InvalidStateTransitionError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    existing_rel.status = new_status
    existing_rel.justification = f"{req.justification} | Reason: {req.reason}"
    existing_rel.noc_reference = req.noc_reference

    fdr.status = FDRStatus.RELEASE_REQUESTED
    fdr.release_requested_at = datetime.utcnow()
    fdr.release_justification = existing_rel.justification
    db.commit()

    record_audit_event(
        db=db,
        event_type="RELEASE_REQUEST_SUBMITTED",
        entity_type="RELEASE_REQUEST",
        entity_id=str(existing_rel.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "fdr_id": fdr.id,
            "fdr_number": fdr.fdr_number,
            "noc_reference": req.noc_reference,
            "amount": req.amount,
            "status": existing_rel.status.value
        }
    )

    return {
        "message": "Release request submitted successfully. Awaiting officer scrutiny.",
        "release_request_id": existing_rel.id,
        "fdr_id": fdr.id,
        "status": existing_rel.status.value
    }


@router.get("/fdr/{fdr_id}/readiness")
def get_release_readiness_checklist(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RELEASE READINESS CHECK:
    Automatically evaluates release conditions (supporting docs, maturity, bank confirmation, discrepancy clearance, anomaly clearance).
    Advisory only - informs the officer, never approves.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden: Access denied to another college's deposit.")

    rel_req = db.query(ReleaseRequest).filter(ReleaseRequest.fdr_id == fdr.id).order_by(ReleaseRequest.id.desc()).first()
    readiness = evaluate_release_readiness(db, fdr, rel_req)
    return readiness


# --------------------------------------------------------------------------
# 2. Officer Scrutiny & Recommendation Flow
# --------------------------------------------------------------------------
@router.post("/fdr/{fdr_id}/scrutiny")
def process_release_scrutiny(
    fdr_id: int,
    req: ReleaseScrutinyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]))
):
    """
    Officer Scrutiny Flow:
    Actions:
    - BEGIN_SCRUTINY: Submitted -> Under scrutiny
    - REQUEST_CLARIFICATION: Under scrutiny -> Clarification required
    - RESUBMIT: Clarification required -> Under scrutiny
    - RECOMMEND: Under scrutiny -> Recommended for approval
    - REJECT: Under scrutiny -> Rejected
    """
    rel = db.query(ReleaseRequest).filter(
        ReleaseRequest.fdr_id == fdr_id,
        ReleaseRequest.status.notin_([ReleaseStatus.CLOSED, ReleaseStatus.REJECTED])
    ).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Active release request not found for this FDR.")

    sm = ReleaseWorkflowStateMachine(rel.status)
    try:
        new_status = sm.trigger(req.action, actor_role=current_user.role.value)
    except (InvalidStateTransitionError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    rel.status = new_status
    if req.action == "RECOMMEND":
        rel.recommended_by = current_user.id
    db.commit()

    record_audit_event(
        db=db,
        event_type=f"RELEASE_WORKFLOW_{req.action}",
        entity_type="RELEASE_REQUEST",
        entity_id=str(rel.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "action": req.action,
            "remarks": req.remarks,
            "new_status": rel.status.value,
            "clarification_details": req.clarification_details
        }
    )

    return {
        "message": f"Release request transitioned to '{rel.status.value}'.",
        "release_request_id": rel.id,
        "status": rel.status.value
    }


# --------------------------------------------------------------------------
# 3. Competent Authority Authorization Gate (Strictly Guarded)
# --------------------------------------------------------------------------
@router.post("/fdr/{fdr_id}/authorize")
def authorize_release_decision(
    fdr_id: int,
    req: ReleaseAuthorizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.COMPETENT_AUTHORITY, UserRole.SYSTEM_ADMIN]))
):
    """
    Non-negotiable SIH requirement:
    ONLY the competent-authority role can approve release.
    Requires typed justification; audit logged with actor, timestamp, reason.
    """
    rel = db.query(ReleaseRequest).filter(
        ReleaseRequest.fdr_id == fdr_id,
        ReleaseRequest.status == ReleaseStatus.RECOMMENDED_FOR_APPROVAL
    ).first()

    if not rel:
        raise HTTPException(
            status_code=400,
            detail="Release request must be in 'Recommended for approval' status prior to Competent Authority authorization."
        )

    sm = ReleaseWorkflowStateMachine(rel.status)
    event = "APPROVE" if req.approved else "REJECT"

    try:
        new_status = sm.trigger(event, actor_role=current_user.role.value)
    except (InvalidStateTransitionError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    rel.status = new_status
    rel.approved_by = current_user.id
    rel.approved_at = datetime.utcnow()
    rel.release_order_ref = req.release_order_ref

    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if fdr:
        if req.approved:
            fdr.status = FDRStatus.RELEASED
            fdr.release_authorized_by = current_user.id
            fdr.release_authorized_at = datetime.utcnow()
            fdr.release_order_ref = req.release_order_ref
        else:
            fdr.status = FDRStatus.ACTIVE # Reverts back to active on rejection

    db.commit()

    record_audit_event(
        db=db,
        event_type="RELEASE_OFFICIALLY_APPROVED" if req.approved else "RELEASE_REJECTED",
        entity_type="RELEASE_REQUEST",
        entity_id=str(rel.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "approved": req.approved,
            "typed_justification": req.typed_justification,
            "release_order_ref": req.release_order_ref,
            "authorized_by": current_user.full_name,
            "status": rel.status.value
        }
    )

    return {
        "message": f"Release request officially {rel.status.value} by Competent Authority.",
        "release_request_id": rel.id,
        "status": rel.status.value,
        "release_order_ref": req.release_order_ref,
        "authorized_by": current_user.full_name
    }


# --------------------------------------------------------------------------
# 4. Final Disbursement & Archival Closure
# --------------------------------------------------------------------------
@router.post("/fdr/{fdr_id}/disburse-and-close")
def disburse_and_close_fdr(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.COMPETENT_AUTHORITY, UserRole.SYSTEM_ADMIN]))
):
    """
    On Released:
    Records release authorization, moves FDR from RELEASED -> CLOSED.
    Preserves complete history in the Lifecycle Passport.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    rel = db.query(ReleaseRequest).filter(ReleaseRequest.fdr_id == fdr.id).order_by(ReleaseRequest.id.desc()).first()
    if not rel or rel.status not in [ReleaseStatus.APPROVED, ReleaseStatus.RELEASED]:
        raise HTTPException(status_code=400, detail="Deposit must be officially Approved prior to final disbursement and closure.")

    # Transition Release Request: Approved -> Released -> Closed
    sm = ReleaseWorkflowStateMachine(rel.status)
    if rel.status == ReleaseStatus.APPROVED:
        rel.status = sm.trigger("DISBURSE_RELEASE", actor_role=current_user.role.value)
    
    # Finalize closure
    sm_close = ReleaseWorkflowStateMachine(rel.status)
    rel.status = sm_close.trigger("FINALIZE_CLOSURE", actor_role=current_user.role.value)

    # Transition FDR Instrument to CLOSED
    fdr.status = FDRStatus.CLOSED
    db.commit()

    record_audit_event(
        db=db,
        event_type="DEPOSIT_OFFICIALLY_RELEASED_AND_CLOSED",
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "fdr_number": fdr.fdr_number,
            "final_status": fdr.status.value,
            "release_order_ref": rel.release_order_ref,
            "closed_at": datetime.utcnow().isoformat(),
            "history_preserved": True
        }
    )

    return {
        "message": f"Security deposit #{fdr.fdr_number} officially RELEASED and archived as CLOSED.",
        "fdr_id": fdr.id,
        "fdr_status": fdr.status.value,
        "release_status": rel.status.value,
        "history_preserved_in_passport": True
    }


@router.get("/requests")
def list_release_requests(
    status_filter: Optional[str] = Query(None),
    institution_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all release requests with role scoping."""
    query = db.query(ReleaseRequest)

    if current_user.role == UserRole.INSTITUTION_USER:
        query = query.filter(ReleaseRequest.institution_id == current_user.institution_id)
    elif institution_id:
        query = query.filter(ReleaseRequest.institution_id == institution_id)

    if status_filter:
        query = query.filter(ReleaseRequest.status == ReleaseStatus(status_filter))

    results = query.order_by(ReleaseRequest.id.desc()).all()
    return [
        {
            "id": r.id,
            "fdr_id": r.fdr_id,
            "fdr_number": r.fdr.fdr_number if r.fdr else "N/A",
            "institution_id": r.institution_id,
            "institution_name": r.institution.name if r.institution else "Unknown",
            "status": r.status.value,
            "justification": r.justification,
            "noc_reference": r.noc_reference,
            "release_order_ref": r.release_order_ref,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "approved_at": r.approved_at.isoformat() if r.approved_at else None
        }
        for r in results
    ]
