"""DepoSafe Verification Orchestrator.

Orchestrates bank verification with:
1. Exponential backoff retries for transient hiccups (timeouts, rate limits).
2. Circuit Breaker pattern preventing cascade failures on core banking outages.
3. VERIFICATION_PENDING queue with scheduled background re-check.
4. SOURCE_UNAVAILABLE routing to Officer Manual Review when bank feed fails.
5. Dual-Truth Four-Source Ledger updates.
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.deposafe_models import (
    FDR, FDRStatus, FieldProvenance, ProvenanceLevel,
    BankVerificationRecord, BankVerificationStatus,
    ProvenanceLedgerEntry, VerificationQueueItem
)
from backend.app.adapters.bank_adapter import SimulatedBankVerificationAdapter
from backend.app.services.simulated_bank_service import (
    BankTimeoutException,
    BankRateLimitException,
    BankDowntimeException
)
from backend.app.services.audit_service import record_audit_event

logger = logging.getLogger("deposafe.orchestrator")

class CircuitBreaker:
    """
    In-memory Circuit Breaker for banking integrations.
    States:
    - CLOSED: Normal operation, requests flow through.
    - OPEN: Tripped after failure threshold, immediately rejects calls.
    - HALF_OPEN: Probe state testing recovery after cooldown.
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout_sec: float = 10.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.trip_count = 0

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time and (now - self.last_failure_time) >= self.recovery_timeout_sec:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioned to HALF_OPEN (probing bank gateway recovery)")
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return True

    def record_success(self):
        if self.state in ["HALF_OPEN", "OPEN"]:
            logger.info("Bank gateway healthy: circuit breaker reset to CLOSED")
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                self.trip_count += 1
                logger.warning(
                    f"Circuit breaker TRIPPED to OPEN after {self.failure_count} consecutive failures. "
                    f"Fast-failing subsequent calls for {self.recovery_timeout_sec}s."
                )
            self.state = "OPEN"

    def reset(self):
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_sec": self.recovery_timeout_sec,
            "trip_count": self.trip_count,
            "last_failure_time": datetime.fromtimestamp(self.last_failure_time).isoformat() if self.last_failure_time else None
        }

# Global singleton circuit breaker instance
bank_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout_sec=5.0)

class VerificationOrchestrator:
    """Orchestrates resilient automated and fallback verification workflows."""

    @classmethod
    def execute_verification(
        cls,
        fdr_id: int,
        db: Session,
        scenario: Optional[str] = None,
        max_retries: int = 3,
        initial_backoff: float = 0.05,
        actor_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes orchestrated verification for an FDR with retry backoff and circuit breaker.
        Updates field provenance, dual-truth ledger, and audit log.
        """
        fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
        if not fdr:
            raise ValueError(f"FDR record with id {fdr_id} not found.")

        adapter = SimulatedBankVerificationAdapter()
        attempt = 0
        last_error_msg = None

        # Check circuit breaker before attempting
        if not bank_circuit_breaker.can_execute():
            # Circuit breaker is OPEN - fast-fail and route to manual review
            return cls._handle_source_unavailable(
                fdr=fdr,
                db=db,
                actor_id=actor_id,
                reason="Circuit Breaker OPEN: Bank Core Banking Gateway is undergoing scheduled maintenance or excessive downtime.",
                scenario=scenario,
                circuit_tripped=True
            )

        # Retry loop with exponential backoff
        while attempt < max_retries:
            attempt += 1
            try:
                res = adapter.verify(
                    bank=fdr.bank_name,
                    branch_ifsc=fdr.ifsc_code,
                    fdr_number=fdr.fdr_number,
                    amount=fdr.amount,
                    issue_date=fdr.issue_date.isoformat() if fdr.issue_date else "",
                    maturity_date=fdr.maturity_date.isoformat() if fdr.maturity_date else "",
                    scenario=scenario
                )

                # Successful API query (even if status is MISMATCH or NOT_CONFIRMED, bank service responded)
                bank_circuit_breaker.record_success()
                return cls._apply_bank_verification_result(
                    fdr=fdr,
                    db=db,
                    result=res,
                    actor_id=actor_id,
                    attempts_taken=attempt
                )

            except (BankTimeoutException, BankRateLimitException) as e:
                last_error_msg = str(e)
                logger.warning(f"Transient error on attempt {attempt}/{max_retries} for FDR {fdr.fdr_number}: {e}")
                if attempt < max_retries:
                    # Exponential backoff
                    sleep_time = initial_backoff * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                else:
                    bank_circuit_breaker.record_failure()

            except BankDowntimeException as e:
                last_error_msg = str(e)
                logger.error(f"Bank Core Downtime on attempt {attempt} for FDR {fdr.fdr_number}: {e}")
                bank_circuit_breaker.record_failure()
                # Do not waste retries if bank core gateway is down
                break

            except Exception as e:
                last_error_msg = str(e)
                bank_circuit_breaker.record_failure()
                break

        # Max retries exhausted or bank outage -> Route to manual review with SOURCE_UNAVAILABLE
        return cls._handle_source_unavailable(
            fdr=fdr,
            db=db,
            actor_id=actor_id,
            reason=f"Bank verification failed after {attempt} attempts: {last_error_msg}",
            scenario=scenario,
            circuit_tripped=False
        )

    @classmethod
    def _apply_bank_verification_result(
        cls,
        fdr: FDR,
        db: Session,
        result: Dict[str, Any],
        actor_id: Optional[int],
        attempts_taken: int
    ) -> Dict[str, Any]:
        """Applies bank verification result to FDR, Dual-Truth Provenance, and Audit Log."""
        status_str = result.get("status", "NOT_CONFIRMED")
        returned_fields = result.get("returned_fields") or {}
        diffs = result.get("diffs") or {}
        ref_id = result.get("api_reference_id")
        now = datetime.utcnow()

        v_status = BankVerificationStatus.AVAILABLE_CHECKS_PASSED if status_str == "AVAILABLE_CHECKS_PASSED" else BankVerificationStatus.NOT_CONFIRMED
        
        # 1. Record BankVerificationRecord
        verif = BankVerificationRecord(
            fdr_id=fdr.id,
            adapter_used=result.get("source", "SIMULATED_CBS_SFMS"),
            verification_status=v_status,
            api_reference_id=ref_id,
            watermark_notice=result.get("watermark", "SIMULATED, not a real bank verification"),
            evidence_data={
                "returned_fields": returned_fields,
                "diffs": diffs,
                "signature": result.get("signature"),
                "attempts_taken": attempts_taken,
                "simulated": True
            },
            verified_by=actor_id,
            verified_at=now,
            remarks=result.get("message")
        )
        db.add(verif)

        # 2. Update Dual-Truth Provenance for all fields
        provenance_records = db.query(FieldProvenance).filter(FieldProvenance.fdr_id == fdr.id).all()
        prov_map = {p.field_name: p for p in provenance_records}

        for field_key, bank_val in returned_fields.items():
            str_val = str(bank_val) if bank_val is not None else None
            p = prov_map.get(field_key)
            if not p:
                p = FieldProvenance(
                    fdr_id=fdr.id,
                    field_name=field_key,
                    submitted_value=str_val
                )
                db.add(p)
                prov_map[field_key] = p

            p.bank_confirmed_value = str_val
            p.bank_confirmed_at = now
            p.bank_confirmed_by = result.get("source", "SIMULATED_CBS_SFMS")

            # Check for conflict/mismatch
            if field_key in diffs:
                p.status = ProvenanceLevel.MISMATCH
                p.mismatch_reason = diffs[field_key].get("discrepancy", "Mismatch against Core Banking Record")
                p.conflicts = [{
                    "source1": "SUBMITTED",
                    "value1": p.submitted_value,
                    "source2": "BANK_CONFIRMED",
                    "value2": str_val,
                    "details": p.mismatch_reason
                }]
            elif status_str == "AVAILABLE_CHECKS_PASSED":
                p.status = ProvenanceLevel.BANK_CONFIRMED
                p.mismatch_reason = None
                p.conflicts = []

            # 3. Append to Provenance Ledger
            ledger_entry = ProvenanceLedgerEntry(
                fdr_id=fdr.id,
                field_name=field_key,
                source=ProvenanceLevel.BANK_CONFIRMED,
                value=str_val,
                actor_name="SIMULATED_CBS_SFMS",
                actor_role="SYSTEM_BANK_ADAPTER",
                timestamp=now,
                confidence=1.0,
                evidence_ref=ref_id,
                remarks=f"Verified via CBS API. Status: {status_str}"
            )
            db.add(ledger_entry)

        # 4. Update FDR Status & Risk Indicators
        if status_str == "AVAILABLE_CHECKS_PASSED":
            if fdr.status in [FDRStatus.SUBMITTED, FDRStatus.UNDER_VERIFICATION, FDRStatus.PENDING_REVIEW]:
                fdr.status = FDRStatus.ACTIVE
        elif status_str == "MISMATCH":
            fdr.status = FDRStatus.UNDER_SCRUTINY
            fdr.review_priority_score = min(100.0, (fdr.review_priority_score or 0.0) + 40.0)
            fdr.review_priority_level = "CRITICAL" if fdr.review_priority_score >= 70 else "HIGH"
            existing_flags = list(fdr.review_flags or [])
            existing_flags.append({
                "flag": "BANK_CBS_MISMATCH",
                "severity": "CRITICAL",
                "reason": result.get("message"),
                "timestamp": now.isoformat()
            })
            fdr.review_flags = existing_flags
        elif status_str == "NOT_CONFIRMED":
            fdr.status = FDRStatus.UNDER_SCRUTINY
            fdr.review_priority_score = min(100.0, (fdr.review_priority_score or 0.0) + 30.0)
            fdr.review_priority_level = "HIGH"

        # 5. Append to Cryptographic Audit Hash Chain
        record_audit_event(
            db=db,
            event_type="BANK_VERIFICATION_COMPLETED",
            entity_type="FDR",
            entity_id=str(fdr.id),
            actor_id=actor_id,
            actor_role="SYSTEM_BANK_ADAPTER",
            payload={
                "status": status_str,
                "api_reference_id": ref_id,
                "diffs": diffs,
                "attempts_taken": attempts_taken,
                "simulated": True
            }
        )

        db.commit()
        db.refresh(fdr)

        return {
            "success": True,
            "fdr_id": fdr.id,
            "fdr_number": fdr.fdr_number,
            "verification_status": status_str,
            "wording": result.get("wording", "not confirmed"),
            "diffs": diffs,
            "api_reference_id": ref_id,
            "signature": result.get("signature"),
            "watermark": result.get("watermark"),
            "simulated": True,
            "message": result.get("message"),
            "circuit_breaker": bank_circuit_breaker.get_metrics()
        }

    @classmethod
    def _handle_source_unavailable(
        cls,
        fdr: FDR,
        db: Session,
        actor_id: Optional[int],
        reason: str,
        scenario: Optional[str] = None,
        circuit_tripped: bool = False
    ) -> Dict[str, Any]:
        """Handles bank feed failure: enqueues into pending queue and routes to officer review."""
        now = datetime.utcnow()

        # Enqueue in verification_queue for scheduled background re-check
        q_item = VerificationQueueItem(
            fdr_id=fdr.id,
            status="QUEUED" if not circuit_tripped else "ROUTED_MANUAL",
            attempts=1,
            max_attempts=3,
            last_error=reason,
            scenario=scenario,
            next_retry_at=now + timedelta(minutes=5)
        )
        db.add(q_item)

        # Update field provenance to SOURCE_UNAVAILABLE
        provenance_records = db.query(FieldProvenance).filter(FieldProvenance.fdr_id == fdr.id).all()
        for p in provenance_records:
            if p.status != ProvenanceLevel.OFFICER_VERIFIED:
                p.status = ProvenanceLevel.SOURCE_UNAVAILABLE
                p.mismatch_reason = reason

        # Transition FDR status to UNDER_SCRUTINY for human verification officer routing
        fdr.status = FDRStatus.UNDER_SCRUTINY
        
        # Log to audit trail
        record_audit_event(
            db=db,
            event_type="BANK_VERIFICATION_FEED_UNAVAILABLE",
            entity_type="FDR",
            entity_id=str(fdr.id),
            actor_id=actor_id,
            actor_role="SYSTEM_ORCHESTRATOR",
            payload={
                "reason": reason,
                "circuit_tripped": circuit_tripped,
                "action": "ROUTED_TO_OFFICER_MANUAL_REVIEW",
                "queue_id": q_item.id
            }
        )

        db.commit()
        db.refresh(fdr)

        return {
            "success": False,
            "fdr_id": fdr.id,
            "fdr_number": fdr.fdr_number,
            "verification_status": "SOURCE_UNAVAILABLE",
            "wording": "not confirmed",
            "reason": reason,
            "action_taken": "ROUTED_TO_OFFICER_MANUAL_REVIEW",
            "circuit_breaker": bank_circuit_breaker.get_metrics(),
            "simulated": True,
            "watermark": "SIMULATED, not a real bank verification"
        }

    @classmethod
    def process_pending_queue(cls, db: Session, max_items: int = 10) -> Dict[str, Any]:
        """Worker task processing pending items in verification_queue."""
        now = datetime.utcnow()
        pending_items = db.query(VerificationQueueItem).filter(
            VerificationQueueItem.status.in_(["QUEUED", "RETRYING"]),
            VerificationQueueItem.next_retry_at <= now
        ).limit(max_items).all()

        processed = 0
        succeeded = 0

        for item in pending_items:
            processed += 1
            item.status = "RETRYING"
            item.attempts += 1
            db.commit()

            try:
                res = cls.execute_verification(
                    fdr_id=item.fdr_id,
                    db=db,
                    scenario=item.scenario,
                    max_retries=1
                )
                if res.get("verification_status") in ["AVAILABLE_CHECKS_PASSED", "MISMATCH", "NOT_CONFIRMED"]:
                    item.status = "COMPLETED"
                    succeeded += 1
                else:
                    item.status = "ROUTED_MANUAL"
            except Exception as e:
                item.last_error = str(e)
                if item.attempts >= item.max_attempts:
                    item.status = "ROUTED_MANUAL"
                else:
                    item.next_retry_at = now + timedelta(minutes=5 * item.attempts)
            db.commit()

        return {
            "items_checked": len(pending_items),
            "processed": processed,
            "succeeded": succeeded,
            "timestamp": now.isoformat()
        }
