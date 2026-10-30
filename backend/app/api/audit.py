from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from backend.app.core.database import get_db
from backend.app.models.deposafe_models import AuditLog
from backend.app.services.audit_service import verify_audit_chain

router = APIRouter(prefix="/audit", tags=["Cryptographic Audit Ledger"])

@router.get("/ledger")
def get_audit_ledger(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """
    Returns the latest cryptographic blocks of the append-only ledger.
    """
    logs = db.query(AuditLog).order_by(AuditLog.sequence_num.desc()).limit(limit).all()
    return [
        {
            "sequence_num": l.sequence_num,
            "prev_hash": l.prev_hash,
            "current_hash": l.current_hash,
            "event_type": l.event_type,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "actor_id": l.actor_id,
            "actor_role": l.actor_role,
            "timestamp": l.timestamp.isoformat(),
            "payload": l.payload
        } for l in logs
    ]

@router.get("/verify")
def verify_ledger_integrity(db: Session = Depends(get_db)):
    """
    Cryptographically traverses all audit blocks from Genesis (H_0) to current (H_n)
    to mathematically verify that zero records have been altered, inserted, or removed.
    """
    return verify_audit_chain(db)

