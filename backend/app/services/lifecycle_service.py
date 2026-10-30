from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import (
    FDR, FDRDocument, FieldProvenance, BankVerificationRecord,
    Institution, User, AuditLog, ReleaseRequest, RenewalRecord, FDRStatus
)

def build_fdr_lifecycle_passport(db: Session, fdr_id: int) -> Dict[str, Any]:
    """
    Builds the comprehensive FDR Lifecycle Passport for an instrument lineage.
    Shows original FDR, verification records, renewals, amount changes,
    bank confirmations, officer observations, maturity history, release history,
    and a unified chronological timeline linked to audit events and documents.
    """
    target_fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not target_fdr:
        return {}

    # Query all instruments in the same lineage
    lineage_fdrs = db.query(FDR).filter(
        FDR.lineage_id == target_fdr.lineage_id
    ).order_by(FDR.created_at.asc(), FDR.issue_date.asc()).all()

    if not lineage_fdrs:
        lineage_fdrs = [target_fdr]

    institution = db.query(Institution).filter(Institution.id == target_fdr.institution_id).first()
    fdr_ids = [f.id for f in lineage_fdrs]

    # Gather documents across lineage
    docs = db.query(FDRDocument).filter(FDRDocument.fdr_id.in_(fdr_ids)).order_by(FDRDocument.created_at.asc()).all()
    
    # Gather verifications across lineage
    verifications = db.query(BankVerificationRecord).filter(
        BankVerificationRecord.fdr_id.in_(fdr_ids)
    ).order_by(BankVerificationRecord.verified_at.asc()).all()

    # Gather release requests
    releases = db.query(ReleaseRequest).filter(
        ReleaseRequest.fdr_id.in_(fdr_ids)
    ).order_by(ReleaseRequest.created_at.asc()).all()

    # Gather audit logs for this lineage
    audit_logs = db.query(AuditLog).filter(
        AuditLog.entity_id.in_([str(fid) for fid in fdr_ids] + [str(d.id) for d in docs])
    ).order_by(AuditLog.sequence_num.asc()).all()

    audit_map_by_entity = {}
    for log in audit_logs:
        audit_map_by_entity.setdefault(log.entity_id, []).append(log)

    # 1. Instruments in Lineage
    instruments_summary = []
    amount_history = []
    prev_amount = None

    for f in lineage_fdrs:
        f_docs = [d for d in docs if d.fdr_id == f.id]
        is_current = (f.id == target_fdr.id)
        is_active = (f.status not in [FDRStatus.SUPERSEDED, FDRStatus.RENEWED_SUPERSEDED, FDRStatus.RELEASED, FDRStatus.CLOSED, FDRStatus.REJECTED])

        instruments_summary.append({
            "fdr_id": f.id,
            "internal_fdr_id": f.internal_fdr_id,
            "fdr_number": f.fdr_number,
            "bank_name": f.bank_name,
            "branch_name": f.branch_name,
            "amount": f.amount,
            "currency": f.currency,
            "status": f.status.value,
            "issue_date": f.issue_date.isoformat(),
            "maturity_date": f.maturity_date.isoformat(),
            "tenure_months": f.tenure_months,
            "interest_rate": f.interest_rate,
            "lien_marked_to_aicte": f.lien_marked_to_aicte,
            "is_current_viewed": is_current,
            "is_active_instrument": is_active,
            "predecessor_fdr_id": f.predecessor_fdr_id,
            "successor_fdr_id": f.successor_fdr_id,
            "document_count": len(f_docs)
        })

        delta = (f.amount - prev_amount) if prev_amount is not None else 0.0
        amount_history.append({
            "fdr_id": f.id,
            "fdr_number": f.fdr_number,
            "amount": f.amount,
            "delta_from_previous": delta,
            "effective_date": f.issue_date.isoformat(),
            "reason": "Original Deposit" if prev_amount is None else ("Amount Augmented" if delta > 0 else "Unchanged on Renewal")
        })
        prev_amount = f.amount

    original_instrument = instruments_summary[0]
    active_instrument = next((i for i in reversed(instruments_summary) if i["is_active_instrument"]), instruments_summary[-1])

    # 2. Renewals Chain
    renewals_chain = []
    for f in lineage_fdrs:
        if f.successor_fdr_id:
            successor = next((s for s in lineage_fdrs if s.id == f.successor_fdr_id), None)
            renewals_chain.append({
                "predecessor_fdr_id": f.id,
                "predecessor_fdr_number": f.fdr_number,
                "successor_fdr_id": f.successor_fdr_id,
                "successor_fdr_number": successor.fdr_number if successor else "PENDING",
                "transition_type": "NON_DESTRUCTIVE_LINKAGE",
                "predecessor_status": f.status.value,
                "note": "Existing instrument was NOT overwritten; permanently preserved as SUPERSEDED."
            })

    # 3. Verification Records
    verifications_summary = []
    for v in verifications:
        verifications_summary.append({
            "id": v.id,
            "fdr_id": v.fdr_id,
            "adapter_used": v.adapter_used,
            "verification_status": v.verification_status.value,
            "watermark_notice": v.watermark_notice,
            "api_reference_id": v.api_reference_id,
            "manual_evidence_type": v.manual_evidence_type,
            "remarks": v.remarks,
            "verified_at": v.verified_at.isoformat()
        })

    # 4. Officer Observations & Overrides
    officer_observations = []
    for f in lineage_fdrs:
        if f.officer_override:
            officer_user = db.query(User).filter(User.id == f.officer_override_by).first() if f.officer_override_by else None
            officer_observations.append({
                "fdr_id": f.id,
                "fdr_number": f.fdr_number,
                "type": "OFFICER_OVERRIDE",
                "officer_name": officer_user.full_name if officer_user else "Authorized Verification Officer",
                "justification": f.officer_override_justification,
                "adjusted_score": f.review_priority_score,
                "recorded_at": f.officer_override_at.isoformat() if f.officer_override_at else f.updated_at.isoformat()
            })

    # 5. Maturity History
    maturity_history = [
        {
            "fdr_id": f.id,
            "fdr_number": f.fdr_number,
            "issue_date": f.issue_date.isoformat(),
            "maturity_date": f.maturity_date.isoformat(),
            "tenure_months": f.tenure_months,
            "auto_renewal": f.auto_renewal,
            "status": f.status.value
        }
        for f in lineage_fdrs
    ]

    # 6. Release & Refund History
    release_history = [
        {
            "id": r.id,
            "fdr_id": r.fdr_id,
            "status": r.status.value,
            "justification": r.justification,
            "noc_reference": r.noc_reference,
            "release_order_ref": r.release_order_ref,
            "requested_at": r.created_at.isoformat(),
            "approved_at": r.approved_at.isoformat() if r.approved_at else None
        }
        for r in releases
    ]

    # 7. Unified Chronological Timeline
    timeline = []

    # Add FDR creations
    for f in lineage_fdrs:
        timeline.append({
            "timestamp": f.created_at.isoformat(),
            "event_category": "INSTRUMENT_LIFECYCLE",
            "event_title": f"FDR #{f.fdr_number} Registered",
            "description": f"Security deposit registered for {institution.name if institution else 'Institution'}. Amount: ₹{f.amount:,.2f}, Bank: {f.bank_name}",
            "fdr_id": f.id,
            "actor_role": "INSTITUTION_USER",
            "metadata": {
                "fdr_number": f.fdr_number,
                "amount": f.amount,
                "maturity_date": f.maturity_date.isoformat()
            }
        })

    # Add Documents
    for d in docs:
        timeline.append({
            "timestamp": d.created_at.isoformat(),
            "event_category": "DOCUMENT_VERSION",
            "event_title": f"Document Version {d.version} Uploaded ({d.doc_type})",
            "description": f"File '{d.file_name}' stored immutably. SHA256: {d.file_hash_sha256[:16]}...",
            "fdr_id": d.fdr_id,
            "document_id": d.id,
            "actor_role": "INSTITUTION_USER / OFFICER",
            "metadata": {
                "version": d.version,
                "sha256": d.file_hash_sha256,
                "perceptual_hash": d.perceptual_hash,
                "document_identifier": f"FDR-{d.created_at.year}-{d.id:05d}"
            }
        })

    # Add Bank Verifications
    for v in verifications:
        timeline.append({
            "timestamp": v.verified_at.isoformat(),
            "event_category": "BANK_VERIFICATION",
            "event_title": f"Bank Verification ({v.adapter_used})",
            "description": f"Status: {v.verification_status.value}. {v.watermark_notice}. Remarks: {v.remarks or 'N/A'}",
            "fdr_id": v.fdr_id,
            "actor_role": "VERIFICATION_OFFICER",
            "metadata": {
                "status": v.verification_status.value,
                "api_reference": v.api_reference_id
            }
        })

    # Add Overrides
    for f in lineage_fdrs:
        if f.officer_override and f.officer_override_at:
            timeline.append({
                "timestamp": f.officer_override_at.isoformat(),
                "event_category": "OFFICER_ACTION",
                "event_title": f"Officer Review Override on #{f.fdr_number}",
                "description": f"Review priority adjusted to {f.review_priority_score} ({f.review_priority_level}). Justification: {f.officer_override_justification}",
                "fdr_id": f.id,
                "actor_role": "VERIFICATION_OFFICER",
                "metadata": {
                    "adjusted_score": f.review_priority_score
                }
            })

    # Add Renewals
    for f in lineage_fdrs:
        if f.successor_fdr_id:
            timeline.append({
                "timestamp": f.updated_at.isoformat(),
                "event_category": "RENEWAL_CHAIN",
                "event_title": f"FDR #{f.fdr_number} Superseded via Renewal",
                "description": f"Existing instrument marked SUPERSEDED. Linked successor created (FDR #{f.successor_fdr_id}). Original remains immutable.",
                "fdr_id": f.id,
                "actor_role": "SYSTEM",
                "metadata": {
                    "successor_fdr_id": f.successor_fdr_id
                }
            })

    # Add Releases
    for r in releases:
        timeline.append({
            "timestamp": r.created_at.isoformat(),
            "event_category": "RELEASE_LIFECYCLE",
            "event_title": "Security Deposit Release Requested",
            "description": f"Release requested. NOC: {r.noc_reference}. Justification: {r.justification}",
            "fdr_id": r.fdr_id,
            "actor_role": "INSTITUTION_USER",
            "metadata": {
                "status": r.status.value
            }
        })
        if r.approved_at:
            timeline.append({
                "timestamp": r.approved_at.isoformat(),
                "event_category": "RELEASE_LIFECYCLE",
                "event_title": f"Security Deposit Release Authorized ({r.status.value})",
                "description": f"Authorized by Competent Authority. Release Order Ref: {r.release_order_ref}",
                "fdr_id": r.fdr_id,
                "actor_role": "COMPETENT_AUTHORITY",
                "metadata": {
                    "status": r.status.value,
                    "release_order_ref": r.release_order_ref
                }
            })

    # Sort timeline chronologically
    timeline.sort(key=lambda x: x["timestamp"])

    return {
        "passport_schema_version": "1.0",
        "lineage_id": target_fdr.lineage_id,
        "viewed_fdr_id": target_fdr.id,
        "institution": {
            "id": institution.id if institution else None,
            "name": institution.name if institution else None,
            "aicte_id": institution.aicte_id if institution else None,
            "state": institution.state if institution else None,
            "regional_office": institution.regional_office if institution else None
        },
        "non_destructive_guarantee": "MANDATORY POLICY: Renewals NEVER overwrite existing instruments. Historical instruments and files are immutably preserved in the audit chain.",
        "original_instrument": original_instrument,
        "active_instrument": active_instrument,
        "instruments": instruments_summary,
        "amount_evolution": amount_history,
        "renewals_chain": renewals_chain,
        "verification_history": verifications_summary,
        "officer_observations": officer_observations,
        "maturity_history": maturity_history,
        "release_history": release_history,
        "chronological_timeline": timeline,
        "total_documents_count": len(docs),
        "total_timeline_events": len(timeline)
    }
