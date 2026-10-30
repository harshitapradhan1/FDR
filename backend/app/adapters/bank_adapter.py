from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class BankVerificationAdapter(ABC):
    """
    Abstract interface for bank verification.
    Real bank integrations (SFMS/API) can implement this interface.
    No real bank API is assumed in this prototype.
    """
    @abstractmethod
    def verify_instrument(
        self,
        bank_name: str,
        fdr_number: str,
        ifsc_code: str,
        expected_amount: float,
        expected_holder: str
    ) -> Dict[str, Any]:
        pass

class SimulatedBankVerificationAdapter(BankVerificationAdapter):
    """
    Simulated verification adapter for hackathon and sandbox demos.
    Clearly watermarked and labelled on every output.
    """
    WATERMARK = "SIMULATED, not a real bank verification"

    def verify_instrument(
        self,
        bank_name: str,
        fdr_number: str,
        ifsc_code: str,
        expected_amount: float,
        expected_holder: str
    ) -> Dict[str, Any]:
        ref_id = f"SIM-SFMS-{uuid.uuid4().hex[:10].upper()}"
        
        # Test hook: if fdr_number ends in "FAIL" or "9999", simulate unconfirmed/mismatch
        if fdr_number.endswith("9999") or "FAIL" in fdr_number.upper():
            return {
                "adapter": "SIMULATED_SFMS",
                "watermark": self.WATERMARK,
                "api_reference_id": ref_id,
                "status": "NOT_CONFIRMED",
                "wording": "not confirmed",
                "message": "Bank CBS response: Instrument number not found or closed in core banking records.",
                "bank_confirmed_amount": None,
                "lien_confirmed": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "adapter": "SIMULATED_SFMS",
            "watermark": self.WATERMARK,
            "api_reference_id": ref_id,
            "status": "AVAILABLE_CHECKS_PASSED",
            "wording": "available checks passed",
            "message": "Simulated bank CBS confirmation received via mock SFMS adapter.",
            "bank_confirmed_amount": expected_amount,
            "bank_fdr_number": fdr_number,
            "bank_holder_name": expected_holder,
            "lien_confirmed": True,
            "maturity_in_records": "Confirmed active",
            "timestamp": datetime.utcnow().isoformat()
        }

class ManualVerificationAdapter(BankVerificationAdapter):
    """
    Officer manual verification recording adapter when automated bank feeds are unavailable.
    """
    def __init__(self, evidence_type: str, evidence_details: Dict[str, Any], officer_name: str):
        self.evidence_type = evidence_type
        self.evidence_details = evidence_details
        self.officer_name = officer_name

    def verify_instrument(
        self,
        bank_name: str,
        fdr_number: str,
        ifsc_code: str,
        expected_amount: float,
        expected_holder: str
    ) -> Dict[str, Any]:
        ref_id = f"MAN-VERIF-{uuid.uuid4().hex[:8].upper()}"
        return {
            "adapter": "OFFICER_MANUAL_VERIFICATION",
            "watermark": "OFFICIAL OFFICER VERIFICATION RECORD",
            "api_reference_id": ref_id,
            "status": "AVAILABLE_CHECKS_PASSED",
            "wording": "available checks passed",
            "message": f"Verified manually by officer {self.officer_name} via {self.evidence_type}.",
            "evidence_type": self.evidence_type,
            "evidence_details": self.evidence_details,
            "bank_confirmed_amount": expected_amount,
            "bank_fdr_number": fdr_number,
            "timestamp": datetime.utcnow().isoformat()
        }

