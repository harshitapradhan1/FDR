"""DepoSafe Simulated Core Banking Service (CBS / SFMS).

Simulates banking integration responses with controllable behaviors:
1. SUCCESS / AVAILABLE_CHECKS_PASSED (matching parameters)
2. MISMATCH (discrepancy on maturity date / amount with diffs)
3. NOT_FOUND / NOT_CONFIRMED (instrument not found in CBS records)
4. TIMEOUT (network timeout simulation)
5. RATE_LIMIT (HTTP 429 quota exhaustion simulation)
6. DOWNTIME (HTTP 503 bank gateway outage simulation)
7. SIGNED_RESPONSE (HMAC-SHA256 authenticated verification payload)

All outputs strictly carry:
- watermark: "SIMULATED, not a real bank verification"
- simulated: True
- statutory wording: "available checks passed" vs "not confirmed" (never "genuine")
"""

import hmac
import hashlib
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

BANK_SIGNING_SECRET = "deposafe-simulated-sfms-secret-key-2026"

class BankTimeoutException(Exception):
    """Raised when simulated CBS Gateway times out (>3000ms)."""
    pass

class BankRateLimitException(Exception):
    """Raised when simulated CBS API rate quota is exceeded (HTTP 429)."""
    pass

class BankDowntimeException(Exception):
    """Raised when simulated CBS Core Service is down (HTTP 503)."""
    pass

def compute_bank_signature(payload: Dict[str, Any], secret: str = BANK_SIGNING_SECRET) -> str:
    """Computes deterministic HMAC-SHA256 signature over sorted JSON payload."""
    canonical_bytes = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()

def verify_bank_signature(payload: Dict[str, Any], signature: str, secret: str = BANK_SIGNING_SECRET) -> bool:
    """Verifies HMAC-SHA256 signature against payload."""
    expected_sig = compute_bank_signature(payload, secret)
    return hmac.compare_digest(expected_sig, signature)

class SimulatedBankService:
    WATERMARK = "SIMULATED, not a real bank verification"
    DEFAULT_SOURCE = "SIMULATED_CBS_SFMS"

    @classmethod
    def query_core_banking(
        cls,
        bank: str,
        branch_ifsc: str,
        fdr_number: str,
        amount: float,
        issue_date: str,
        maturity_date: str,
        scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes simulated CBS query based on explicit scenario or input triggers.
        Scenarios: SUCCESS, MISMATCH, NOT_FOUND, TIMEOUT, RATE_LIMIT, DOWNTIME, SIGNED_RESPONSE
        """
        effective_scenario = (scenario or "").upper().strip()

        # Automatic detection hooks if scenario not explicitly specified
        if not effective_scenario:
            if "HERO" in fdr_number.upper() or fdr_number == "BNB-DEL-HERO-1000":
                effective_scenario = "MISMATCH"
            elif "TIMEOUT" in fdr_number.upper() or "TIMEOUT" in bank.upper():
                effective_scenario = "TIMEOUT"
            elif "RATELIMIT" in fdr_number.upper() or "429" in fdr_number:
                effective_scenario = "RATE_LIMIT"
            elif "DOWNTIME" in fdr_number.upper() or "503" in fdr_number:
                effective_scenario = "DOWNTIME"
            elif fdr_number.endswith("9999") or "FAIL" in fdr_number.upper():
                effective_scenario = "NOT_FOUND"
            else:
                effective_scenario = "SUCCESS"

        ref_id = f"SFMS-SIM-{uuid.uuid4().hex[:12].upper()}"
        ts = datetime.utcnow().isoformat()

        # 1. TIMEOUT Simulation
        if effective_scenario == "TIMEOUT":
            raise BankTimeoutException(
                f"Simulated Bank Core Gateway Timeout for {bank} [{branch_ifsc}]: CBS response delayed > 3000ms."
            )

        # 2. RATE LIMIT Simulation (HTTP 429)
        if effective_scenario in ["RATE_LIMIT", "RATE_LIMITED", "429"]:
            raise BankRateLimitException(
                f"Simulated Bank API Rate Limit Exceeded for {bank} [{branch_ifsc}]: 100 queries/min limit exhausted. Retry after 30s."
            )

        # 3. DOWNTIME Simulation (HTTP 503)
        if effective_scenario in ["DOWNTIME", "OUTAGE", "503"]:
            raise BankDowntimeException(
                f"Simulated Core Banking Service Unavailable (HTTP 503): {bank} SFMS gateway undergoing scheduled CBS maintenance."
            )

        # 4. NOT FOUND / NOT CONFIRMED
        if effective_scenario in ["NOT_FOUND", "NOT_CONFIRMED"]:
            return {
                "status": "NOT_CONFIRMED",
                "wording": "not confirmed",
                "message": "Bank CBS response: Instrument number not found or closed in core banking records.",
                "returned_fields": None,
                "diffs": {},
                "source": cls.DEFAULT_SOURCE,
                "timestamp": ts,
                "simulated": True,
                "watermark": cls.WATERMARK,
                "api_reference_id": ref_id,
                "signature": None
            }

        # 5. MISMATCH Simulation (Hero Case & Discrepancies)
        if effective_scenario == "MISMATCH":
            # For hero case or mismatch, simulate conflicting maturity date or amount
            # E.g., if certificate is 2032-11-15, bank CBS record shows 2026-11-15 (or +1 month 2032-12-15)
            bank_maturity = "2026-11-15" if "2032" in str(maturity_date) else "2024-12-15"
            if maturity_date and maturity_date.endswith("-15"):
                # 15 Nov vs 15 Dec style
                prefix = maturity_date[:-2]
                bank_maturity = f"{prefix}15" if prefix.endswith("-12-") else maturity_date.replace("-11-15", "-12-15")
                if bank_maturity == maturity_date:
                    bank_maturity = "2026-11-15"

            returned_fields = {
                "bank_name": bank,
                "branch_ifsc": branch_ifsc,
                "fdr_number": fdr_number,
                "amount": amount,
                "issue_date": issue_date,
                "maturity_date": bank_maturity,
                "lien_marked_to": "Member Secretary, AICTE",
                "cbs_status": "ACTIVE_LIEN_CONFIRMED",
                "holder_name": "AICTE Registered Institution"
            }

            diffs = {
                "maturity_date": {
                    "expected": maturity_date,
                    "bank_record": bank_maturity,
                    "discrepancy": f"Maturity mismatch: Institute claimed {maturity_date}, CBS record certifies {bank_maturity}"
                }
            }

            payload_to_sign = {
                "ref_id": ref_id,
                "returned_fields": returned_fields,
                "timestamp": ts,
                "simulated": True
            }
            sig = compute_bank_signature(payload_to_sign)

            return {
                "status": "MISMATCH",
                "wording": "not confirmed",
                "message": f"Bank CBS verification returned field mismatches: maturity date differs ({maturity_date} vs {bank_maturity}).",
                "returned_fields": returned_fields,
                "diffs": diffs,
                "source": cls.DEFAULT_SOURCE,
                "timestamp": ts,
                "simulated": True,
                "watermark": cls.WATERMARK,
                "api_reference_id": ref_id,
                "signature": sig
            }

        # 6. SUCCESS / SIGNED_RESPONSE / AVAILABLE_CHECKS_PASSED
        returned_fields = {
            "bank_name": bank,
            "branch_ifsc": branch_ifsc,
            "fdr_number": fdr_number,
            "amount": float(amount) if amount else 0.0,
            "issue_date": str(issue_date),
            "maturity_date": str(maturity_date),
            "lien_marked_to": "Member Secretary, AICTE",
            "cbs_status": "ACTIVE_LIEN_CONFIRMED",
            "holder_name": "AICTE Registered Institution"
        }

        payload_to_sign = {
            "ref_id": ref_id,
            "returned_fields": returned_fields,
            "timestamp": ts,
            "simulated": True
        }
        sig = compute_bank_signature(payload_to_sign)

        return {
            "status": "AVAILABLE_CHECKS_PASSED",
            "wording": "available checks passed",
            "message": "Simulated bank CBS confirmation received via mock SFMS adapter. All declared fields verified.",
            "returned_fields": returned_fields,
            "diffs": {},
            "source": cls.DEFAULT_SOURCE,
            "timestamp": ts,
            "simulated": True,
            "watermark": cls.WATERMARK,
            "api_reference_id": ref_id,
            "signature": sig
        }
