"""DepoSafe Lifecycle Automation, Maturity Radar & Predictive Intelligence API.

Endpoints:
1. POST /radar/scan: Trigger manual or scheduled Maturity Radar scan across all instruments.
2. GET /radar/notifications: List generated radar notifications and email deliveries with filters.
3. POST /radar/notifications/{id}/acknowledge: Acknowledge receipt of statutory reminder.
4. GET /renewal/priority-queue: Smart Renewal Priority Queue ranked by urgency (Critical / High / Normal).
5. GET /renewal/{fdr_id}/zero-gap: Zero-Gap Guard evaluation and gap days calculation.
6. POST /renewal/{fdr_id}/compare: Automatic comparison between old and renewal instrument.
7. POST /renewal/{fdr_id}/decision: Officer approval/rejection of renewal instrument (supersedes old instrument).
8. GET /predictive/workload-forecast: scikit-learn based 30/60/90 days forecast of officer scrutiny.
9. GET /predictive/fdr/{fdr_id}/propensity: Late renewal risk probability and feature attribution.
10. GET /calendar/maturities: Expiry & maturity calendar API with date range and institution filters.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import (
    User, UserRole, FDR, Institution, Notification, FDRStatus, RenewalRecord
)
from backend.app.services.maturity_radar import run_maturity_radar_scan
from backend.app.services.renewal_guard import evaluate_zero_gap_guard, compute_smart_renewal_priority_queue
from backend.app.services.predictive_intelligence import PredictiveComplianceForecaster
from backend.app.services.demo_clock import get_simulated_today
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/lifecycle", tags=["Proactive Lifecycle Automation"])


class RenewalComparisonRequest(BaseModel):
    new_fdr_number: str
    new_bank_name: str
    new_amount: float
    new_issue_date: date
    new_maturity_date: date
    new_tenure_months: int


class RenewalDecisionRequest(BaseModel):
    decision: str # "APPROVE", "REJECT", "REQUEST_CLARIFICATION"
    remarks: str
    officer_justification: Optional[str] = "Statutory deposit continuity verified by verification officer."


# --------------------------------------------------------------------------
# 1. Maturity Radar & Notification Center
# --------------------------------------------------------------------------
@router.post("/radar/scan")
def trigger_maturity_radar_scan(
    target_fdr_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN, UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER]))
):
    """Triggers Maturity Radar sweep against active demo clock."""
    result = run_maturity_radar_scan(db, target_fdr_id=target_fdr_id)
    return result


@router.get("/radar/notifications")
def get_radar_notifications(
    recipient_email: Optional[str] = Query(None),
    fdr_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists generated radar notifications with delivery and acknowledgement timestamps."""
    query = db.query(Notification)
    if current_user.role == UserRole.INSTITUTION_USER:
        query = query.filter(Notification.recipient == current_user.email)
    elif recipient_email:
        query = query.filter(Notification.recipient == recipient_email)

    if fdr_id:
        query = query.filter(Notification.fdr_id == fdr_id)

    notifs = query.order_by(Notification.id.desc()).limit(100).all()
    return [
        {
            "id": n.id,
            "recipient": n.recipient,
            "recipient_role": n.recipient_role,
            "fdr_id": n.fdr_id,
            "notification_type": n.notification_type,
            "due_date": n.due_date.isoformat() if n.due_date else None,
            "delivery_status": n.delivery_status,
            "acknowledged_at": n.acknowledged_at.isoformat() if n.acknowledged_at else None,
            "payload": n.payload,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifs
    ]


@router.post("/radar/notifications/{notification_id}/acknowledge")
def acknowledge_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledges receipt of a statutory reminder notification."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if current_user.role == UserRole.INSTITUTION_USER and notif.recipient != current_user.email:
        raise HTTPException(status_code=403, detail="Cannot acknowledge notification sent to another recipient.")

    notif.acknowledged_at = datetime.utcnow()
    db.commit()

    record_audit_event(
        db=db,
        event_type="NOTIFICATION_ACKNOWLEDGED",
        entity_type="NOTIFICATION",
        entity_id=str(notif.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={"fdr_id": notif.fdr_id, "notification_type": notif.notification_type}
    )

    return {
        "message": f"Notification #{notif.id} successfully acknowledged.",
        "acknowledged_at": notif.acknowledged_at.isoformat()
    }


# --------------------------------------------------------------------------
# 2. Smart Renewal Priority Queue & Zero-Gap Guard
# --------------------------------------------------------------------------
@router.get("/renewal/priority-queue")
def get_renewal_priority_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]))
):
    """Returns smart renewal priority queue ranked by urgency (Critical / High / Normal) with reasons."""
    return compute_smart_renewal_priority_queue(db)


@router.get("/renewal/{fdr_id}/zero-gap")
def get_fdr_zero_gap_guard(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Evaluates coverage continuity and computes gap days for an instrument."""
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden: Access to another institution's FDR is denied.")

    return evaluate_zero_gap_guard(db, fdr)


# --------------------------------------------------------------------------
# 3. Automatic Instrument Comparison & Renewal Decision Flow
# --------------------------------------------------------------------------
@router.post("/renewal/{fdr_id}/compare")
def compare_renewal_with_predecessor(
    fdr_id: int,
    req: RenewalComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automatically compares replacement / renewal instrument details against previous FDR:
    - Amount change (delta and percentage)
    - Bank change
    - Validity & lock-in comparison
    - Gap days between predecessor maturity and successor issue
    """
    old_fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not old_fdr:
        raise HTTPException(status_code=404, detail="Predecessor FDR not found.")

    amount_delta = req.new_amount - old_fdr.amount
    amount_change_pct = round((amount_delta / old_fdr.amount) * 100, 2) if old_fdr.amount else 0.0

    bank_changed = (req.new_bank_name.lower().strip() != old_fdr.bank_name.lower().strip())
    tenure_changed = (req.new_tenure_months != old_fdr.tenure_months)

    gap_days = (req.new_issue_date - old_fdr.maturity_date).days if (req.new_issue_date and old_fdr.maturity_date) else 0

    return {
        "predecessor_fdr_id": old_fdr.id,
        "predecessor_fdr_number": old_fdr.fdr_number,
        "comparison": {
            "amount": {
                "old_amount": old_fdr.amount,
                "new_amount": req.new_amount,
                "delta": amount_delta,
                "change_percentage": amount_change_pct,
                "status": "INCREASED" if amount_delta > 0 else "DECREASED" if amount_delta < 0 else "UNCHANGED"
            },
            "bank": {
                "old_bank": old_fdr.bank_name,
                "new_bank": req.new_bank_name,
                "changed": bank_changed
            },
            "tenure": {
                "old_tenure_months": old_fdr.tenure_months,
                "new_tenure_months": req.new_tenure_months,
                "changed": tenure_changed
            },
            "continuity": {
                "old_maturity": old_fdr.maturity_date.isoformat(),
                "new_issue": req.new_issue_date.isoformat(),
                "gap_days": gap_days,
                "is_zero_gap": (gap_days <= 0)
            }
        },
        "statutory_notice": "Instrument comparison generated for officer scrutiny."
    }


@router.post("/renewal/{fdr_id}/decision")
def officer_renewal_decision(
    fdr_id: int,
    req: RenewalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN]))
):
    """
    Officer approval/rejection flow for renewal instruments:
    - If APPROVED: Predecessor FDR is marked SUPERSEDED; replacement FDR becomes ACTIVE.
    - If REJECTED: Predecessor remains active/expiring; renewal record marked REJECTED.
    - Full lineage history and cryptographic audit entry recorded.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    if req.decision == "APPROVE":
        fdr.status = FDRStatus.ACTIVE
        fdr.verification_status = "VERIFIED"
        
        # If this fdr has a predecessor, mark predecessor SUPERSEDED
        if fdr.predecessor_fdr_id:
            pred = db.query(FDR).filter(FDR.id == fdr.predecessor_fdr_id).first()
            if pred:
                pred.status = FDRStatus.RENEWED_SUPERSEDED
                pred.superseded_by = fdr.id

        event_name = "RENEWAL_FDR_APPROVED"
        msg = f"Renewal instrument #{fdr.fdr_number} approved and marked ACTIVE. Predecessor marked SUPERSEDED."
    elif req.decision == "REJECT":
        fdr.status = FDRStatus.REJECTED
        event_name = "RENEWAL_FDR_REJECTED"
        msg = f"Renewal instrument #{fdr.fdr_number} rejected by officer."
    else:
        fdr.status = FDRStatus.UNDER_SCRUTINY
        event_name = "RENEWAL_CLARIFICATION_REQUESTED"
        msg = f"Clarification requested for renewal instrument #{fdr.fdr_number}."

    db.commit()

    record_audit_event(
        db=db,
        event_type=event_name,
        entity_type="FDR",
        entity_id=str(fdr.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "decision": req.decision,
            "remarks": req.remarks,
            "officer_justification": req.officer_justification,
            "fdr_number": fdr.fdr_number,
            "predecessor_fdr_id": fdr.predecessor_fdr_id
        }
    )

    return {
        "message": msg,
        "fdr_id": fdr.id,
        "status": fdr.status.value,
        "predecessor_fdr_id": fdr.predecessor_fdr_id
    }


# --------------------------------------------------------------------------
# 4. Predictive Compliance Intelligence (scikit-learn)
# --------------------------------------------------------------------------
@router.get("/predictive/workload-forecast")
def get_workload_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.VERIFICATION_OFFICER, UserRole.REGIONAL_OFFICER, UserRole.SYSTEM_ADMIN, UserRole.COMPETENT_AUTHORITY]))
):
    """scikit-learn based forecast of upcoming officer workload across next 30/60/90 days."""
    return PredictiveComplianceForecaster.forecast_officer_workload(db)


@router.get("/predictive/fdr/{fdr_id}/propensity")
def get_fdr_late_renewal_propensity(
    fdr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Predicts probability of late renewal / default for an instrument with top feature contributions."""
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=403, detail="Forbidden: Access to another institution's FDR is denied.")

    return PredictiveComplianceForecaster.predict_late_renewal_propensity(db, fdr)


# --------------------------------------------------------------------------
# 5. FDR Expiry & Maturity Calendar API
# --------------------------------------------------------------------------
@router.get("/calendar/maturities")
def get_maturity_calendar(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    institution_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calendar API listing deposit maturities with filter by date range and institution."""
    simulated_today = get_simulated_today(db)
    s_date = start_date or (simulated_today - timedelta(days=30))
    e_date = end_date or (simulated_today + timedelta(days=365))

    query = db.query(FDR).filter(
        FDR.maturity_date >= s_date,
        FDR.maturity_date <= e_date,
        FDR.status.notin_([FDRStatus.RELEASED, FDRStatus.FORFEITED, FDRStatus.RENEWED_SUPERSEDED])
    )

    if current_user.role == UserRole.INSTITUTION_USER:
        query = query.filter(FDR.institution_id == current_user.institution_id)
    elif institution_id:
        query = query.filter(FDR.institution_id == institution_id)

    fdrs = query.order_by(FDR.maturity_date.asc()).all()

    calendar_events = []
    for f in fdrs:
        inst = db.query(Institution).filter(Institution.id == f.institution_id).first()
        days_remaining = (f.maturity_date - simulated_today).days
        calendar_events.append({
            "id": f.id,
            "fdr_number": f.fdr_number,
            "title": f"Maturity: {f.fdr_number} (₹{f.amount:,.0f})",
            "start": f.maturity_date.isoformat(),
            "end": f.maturity_date.isoformat(),
            "institution_id": f.institution_id,
            "institution_name": inst.name if inst else "Unknown",
            "bank_name": f.bank_name,
            "amount": f.amount,
            "days_remaining": days_remaining,
            "status": f.status.value,
            "color_category": "OVERDUE" if days_remaining < 0 else "CRITICAL" if days_remaining <= 15 else "WARNING" if days_remaining <= 30 else "NORMAL"
        })

    return {
        "start_date": s_date.isoformat(),
        "end_date": e_date.isoformat(),
        "simulated_today": simulated_today.isoformat(),
        "total_events": len(calendar_events),
        "events": calendar_events
    }
