"""Bank Verification Adapters for DepoSafe.

Provides:
- BankVerificationAdapter abstract base interface.
- SimulatedBankVerificationAdapter (mock SFMS / CBS adapter with controllable scenarios).
- ManualVerificationAdapter (officer human-in-the-loop manual verification recording).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from backend.app.services.simulated_bank_service import (
    SimulatedBankService,
    compute_bank_signature,
    verify_bank_signature,
    BankTimeoutException,
    BankRateLimitException,
    BankDowntimeException
)

class BankVerificationAdapter(ABC):
    """
    Abstract interface for bank verification.
    Real bank integrations (SFMS, e-BG / NeSL, CBS API) implement this interface.
    No real bank API is assumed in this prototype.
    """
    @abstractmethod
    def verify(
        self,
        bank: str,
        branch_ifsc: str,
        fdr_number: str,
        amount: float,
        issue_date: str,
        maturity_date: str,
        scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Queries bank core verification.
        Returns:
        {
            "status": "AVAILABLE_CHECKS_PASSED" | "NOT_CONFIRMED" | "MISMATCH",
            "returned_fields": {...},
            "diffs": {...},
            "source": "...",
            "timestamp": "...",
            "simulated": True,
            "signature": "...",
            "watermark": "..."
        }
        """
        pass

    def verify_instrument(
        self,
        bank_name: str,
        fdr_number: str,
        ifsc_code: str,
        expected_amount: float,
        expected_holder: str
    ) -> Dict[str, Any]:
        """Backward-compatibility wrapper for Phase 1 legacy interface."""
        res = self.verify(
            bank=bank_name,
            branch_ifsc=ifsc_code,
            fdr_number=fdr_number,
            amount=expected_amount,
            issue_date="",
            maturity_date=""
        )
        return {
            "adapter": res.get("source", "SIMULATED_SFMS"),
            "watermark": res.get("watermark"),
            "api_reference_id": res.get("api_reference_id"),
            "status": res.get("status"),
            "wording": res.get("wording"),
            "message": res.get("message"),
            "bank_confirmed_amount": expected_amount if res.get("status") == "AVAILABLE_CHECKS_PASSED" else None,
            "bank_fdr_number": fdr_number,
            "bank_holder_name": expected_holder,
            "lien_confirmed": (res.get("status") == "AVAILABLE_CHECKS_PASSED"),
            "timestamp": res.get("timestamp")
        }

class SimulatedBankVerificationAdapter(BankVerificationAdapter):
    """
    Simulated verification adapter for hackathon and sandbox demos.
    Clearly watermarked and labelled on every output.
    """
    WATERMARK = "SIMULATED, not a real bank verification"

    def verify(
        self,
        bank: str,
        branch_ifsc: str,
        fdr_number: str,
        amount: float,
        issue_date: str,
        maturity_date: str,
        scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        return SimulatedBankService.query_core_banking(
            bank=bank,
            branch_ifsc=branch_ifsc,
            fdr_number=fdr_number,
            amount=amount,
            issue_date=issue_date,
            maturity_date=maturity_date,
            scenario=scenario
        )

class ManualVerificationAdapter(BankVerificationAdapter):
    """
    Officer manual verification recording adapter when automated bank feeds are unavailable.
    Elevates provenance to OFFICER_VERIFIED, strictly distinct from BANK_CONFIRMED.
    """
    def __init__(
        self,
        evidence_type: str,
        reference_id: str,
        officer_name: str,
        officer_id: Optional[int] = None,
        remarks: Optional[str] = None,
        evidence_document_id: Optional[int] = None
    ):
        self.evidence_type = evidence_type
        self.reference_id = reference_id
        self.officer_name = officer_name
        self.officer_id = officer_id
        self.remarks = remarks or "Manual verification completed by officer"
        self.evidence_document_id = evidence_document_id

    def verify(
        self,
        bank: str,
        branch_ifsc: str,
        fdr_number: str,
        amount: float,
        issue_date: str,
        maturity_date: str,
        scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        ref_id = self.reference_id or f"MAN-VERIF-{uuid.uuid4().hex[:8].upper()}"
        ts = datetime.utcnow().isoformat()
        return {
            "status": "AVAILABLE_CHECKS_PASSED",
            "wording": "available checks passed",
            "message": f"Verified manually by officer {self.officer_name} via {self.evidence_type}. Reference: {ref_id}",
            "returned_fields": {
                "bank_name": bank,
                "branch_ifsc": branch_ifsc,
                "fdr_number": fdr_number,
                "amount": amount,
                "issue_date": issue_date,
                "maturity_date": maturity_date,
                "officer_name": self.officer_name,
                "evidence_type": self.evidence_type,
                "reference_id": ref_id,
                "remarks": self.remarks,
                "evidence_document_id": self.evidence_document_id
            },
            "diffs": {},
            "source": "OFFICER_MANUAL_VERIFICATION",
            "timestamp": ts,
            "simulated": False,
            "watermark": "OFFICIAL OFFICER VERIFICATION RECORD - MANUAL PROVENANCE",
            "api_reference_id": ref_id,
            "signature": None
        }
