import hashlib
import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import AuditLog

GENESIS_HASH = "0" * 64

def compute_event_hash(prev_hash: str, event_data: dict) -> str:
    canonical_repr = json.dumps(event_data, sort_keys=True, default=str)
    message = f"{prev_hash}::{canonical_repr}".encode("utf-8")
    return hashlib.sha256(message).hexdigest()

def record_audit_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_id: int = None,
    actor_role: str = None,
    payload: dict = None,
    ip_address: str = "127.0.0.1"
) -> AuditLog:
    """
    Appends an immutable, hash-chained record to the audit ledger:
    H_n = SHA256(H_{n-1} || event_n)
    """
    last_record = db.query(AuditLog).order_by(AuditLog.sequence_num.desc()).first()
    
    if last_record is None:
        sequence_num = 1
        prev_hash = GENESIS_HASH
    else:
        sequence_num = last_record.sequence_num + 1
        prev_hash = last_record.current_hash

    payload_data = payload or {}
    now = datetime.utcnow()
    timestamp_str = now.isoformat()
    
    event_envelope = {
        "sequence_num": sequence_num,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "timestamp": timestamp_str,
        "payload": payload_data
    }
    
    current_hash = compute_event_hash(prev_hash, event_envelope)
    
    audit_entry = AuditLog(
        sequence_num=sequence_num,
        prev_hash=prev_hash,
        current_hash=current_hash,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor_id=actor_id,
        actor_role=actor_role,
        ip_address=ip_address,
        payload=payload_data,
        timestamp=now,
        timestamp_iso=timestamp_str
    )
    
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry

def verify_audit_chain(db: Session) -> dict:
    """
    Verifies that the entire cryptographic hash chain is uncompromised and intact.
    """
    records = db.query(AuditLog).order_by(AuditLog.sequence_num.asc()).all()
    if not records:
        return {
            "verified": True,
            "total_records": 0,
            "message": "Audit ledger is empty (genesis state)."
        }
    
    expected_prev_hash = GENESIS_HASH
    for i, rec in enumerate(records):
        if rec.prev_hash != expected_prev_hash:
            return {
                "verified": False,
                "broken_at_sequence": rec.sequence_num,
                "expected_prev_hash": expected_prev_hash,
                "found_prev_hash": rec.prev_hash,
                "message": f"Hash chain broken at sequence #{rec.sequence_num}: prev_hash mismatch!"
            }
        
        event_envelope = {
            "sequence_num": rec.sequence_num,
            "event_type": rec.event_type,
            "entity_type": rec.entity_type,
            "entity_id": str(rec.entity_id),
            "actor_id": rec.actor_id,
            "actor_role": rec.actor_role,
            "timestamp": rec.timestamp_iso or rec.timestamp.isoformat(),
            "payload": rec.payload
        }
        computed = compute_event_hash(expected_prev_hash, event_envelope)
        if computed != rec.current_hash:
            return {
                "verified": False,
                "broken_at_sequence": rec.sequence_num,
                "expected_hash": computed,
                "recorded_hash": rec.current_hash,
                "message": f"Hash chain corrupted at sequence #{rec.sequence_num}: data tampering detected!"
            }
        expected_prev_hash = rec.current_hash

    return {
        "verified": True,
        "total_records": len(records),
        "latest_sequence": records[-1].sequence_num,
        "latest_block_hash": records[-1].current_hash,
        "message": f"Audit ledger verified! All {len(records)} cryptographic blocks valid and untampered."
    }
