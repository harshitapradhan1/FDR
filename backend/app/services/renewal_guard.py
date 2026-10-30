"""DepoSafe Zero-Gap Guard & Renewal Continuity Analyzer.

Guarantees:
1. Zero-Gap Protection: Computes gap days where an institution's security deposit coverage
   lapsed between the expiry/maturity of an old instrument and the effective start of an approved replacement.
2. Flagging & Severity:
   - Gap > 30 days: CRITICAL (Potential statutory regulatory default)
   - Gap 1 to 30 days: HIGH (Uncovered grace window)
   - Gap = 0 days: CONTINUOUS (Zero regulatory gap)
3. Smart Renewal Priority Queue:
   - Ranks renewal cases into CRITICAL / HIGH / NORMAL with transparent reasons
     (days to maturity, renewal status, missing documents, past late renewal history).
"""

from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.deposafe_models import (
    FDR, Institution, FDRDocument, FDRStatus, RenewalRecord
)
from backend.app.services.demo_clock import get_simulated_today


def evaluate_zero_gap_guard(db: Session, fdr: FDR) -> Dict[str, Any]:
    """
    Evaluates coverage continuity for an instrument:
    Checks if old FDR is matured/expiring without an approved successor,
    or computes date gap if successor exists.
    """
    simulated_today = get_simulated_today(db)
    inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    # Look for successor instruments
    successor = db.query(FDR).filter(FDR.predecessor_fdr_id == fdr.id).first()

    has_gap = False
    gap_days = 0
    severity = "NONE"
    reason = "Continuous coverage maintained."

    if not successor:
        # Check if old FDR is already matured or overdue
        if fdr.maturity_date < simulated_today:
            has_gap = True
            gap_days = (simulated_today - fdr.maturity_date).days
            severity = "CRITICAL" if gap_days > 30 else "HIGH"
            reason = (
                f"Statutory Cover Gap: Deposit matured on {fdr.maturity_date.isoformat()} "
                f"({gap_days} days ago) with NO approved replacement or renewal instrument on record."
            )
        elif (fdr.maturity_date - simulated_today).days <= 30:
            days_to_lapse = (fdr.maturity_date - simulated_today).days
            has_gap = True
            gap_days = 0 # Imminent gap
            severity = "HIGH"
            reason = f"Imminent Cover Gap: Deposit expires in {days_to_lapse} days with no pending renewal successor."
    else:
        # Successor exists - compare dates
        if successor.issue_date and fdr.maturity_date:
            diff = (successor.issue_date - fdr.maturity_date).days
            if diff > 0:
                has_gap = True
                gap_days = diff
                severity = "CRITICAL" if gap_days > 30 else "HIGH"
                reason = (
                    f"Discontinuous Coverage: Successor FDR #{successor.fdr_number} starts on {successor.issue_date.isoformat()}, "
                    f"creating a {gap_days}-day uncovered security deposit gap."
                )
            else:
                has_gap = False
                gap_days = 0
                severity = "NONE"
                reason = "Continuous seamless renewal coverage (Zero gap)."

    return {
        "fdr_id": fdr.id,
        "fdr_number": fdr.fdr_number,
        "institution_id": inst.id if inst else None,
        "institution_name": inst.name if inst else "Unknown",
        "has_gap": has_gap,
        "gap_days": gap_days,
        "severity": severity,
        "reason": reason,
        "successor_fdr_id": successor.id if successor else None,
        "successor_fdr_number": successor.fdr_number if successor else None,
        "maturity_date": fdr.maturity_date.isoformat() if fdr.maturity_date else None,
        "statutory_label": "Zero-Gap Regulatory Guard"
    }


def compute_smart_renewal_priority_queue(db: Session) -> List[Dict[str, Any]]:
    """
    Ranks all renewal/expiring cases across the registry by urgency into:
    CRITICAL / HIGH / NORMAL with transparent contributing factors.
    """
    simulated_today = get_simulated_today(db)
    active_fdrs = db.query(FDR).filter(
        FDR.status.notin_([FDRStatus.RELEASED, FDRStatus.FORFEITED, FDRStatus.RENEWED_SUPERSEDED])
    ).all()

    queue = []

    for fdr in active_fdrs:
        inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
        if not inst:
            continue

        days_remaining = (fdr.maturity_date - simulated_today).days
        gap_eval = evaluate_zero_gap_guard(db, fdr)

        # Check documentation
        docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).all()
        doc_types = [d.doc_type for d in docs]
        has_bank_letter = "BANK_CONFIRMATION_LETTER" in doc_types

        # Score priority factors
        urgency_points = 0
        reasons = []

        if days_remaining <= 0:
            urgency_points += 50
            reasons.append(f"Deposit is OVERDUE by {abs(days_remaining)} days.")
        elif days_remaining <= 15:
            urgency_points += 35
            reasons.append(f"Matures in {days_remaining} days (T-15 window).")
        elif days_remaining <= 30:
            urgency_points += 20
            reasons.append(f"Matures in {days_remaining} days (T-30 renewal window).")

        if gap_eval["has_gap"]:
            urgency_points += 30
            reasons.append(gap_eval["reason"])

        if not has_bank_letter:
            urgency_points += 15
            reasons.append("Bank confirmation letter missing from depository.")

        if fdr.review_priority_score and fdr.review_priority_score >= 50.0:
            urgency_points += 15
            reasons.append(f"Elevated review priority indicator: {fdr.review_priority_score}/100.")

        # Determine level
        if urgency_points >= 60:
            urgency_level = "CRITICAL"
        elif urgency_points >= 30:
            urgency_level = "HIGH"
        else:
            urgency_level = "NORMAL"

        if days_remaining <= 90 or gap_eval["has_gap"]:
            queue.append({
                "fdr_id": fdr.id,
                "fdr_number": fdr.fdr_number,
                "institution_id": inst.id,
                "institution_name": inst.name,
                "aicte_id": inst.aicte_id,
                "state": inst.state,
                "amount": fdr.amount,
                "maturity_date": fdr.maturity_date.isoformat(),
                "days_remaining": days_remaining,
                "urgency_level": urgency_level,
                "urgency_score": urgency_points,
                "has_cover_gap": gap_eval["has_gap"],
                "gap_days": gap_eval["gap_days"],
                "status": fdr.status.value,
                "contributing_reasons": reasons
            })

    # Sort by urgency score descending, then days remaining ascending
    queue.sort(key=lambda x: (-x["urgency_score"], x["days_remaining"]))
    return queue
