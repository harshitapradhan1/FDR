"""FastAPI Router for Simulated Core Banking Service (CBS / SFMS).

Provides:
- POST /api/v1/mock-bank/verify: Simulates bank core responses with controllable behavior scenarios.
- GET /api/v1/mock-bank/health: Health check.
- POST /api/v1/mock-bank/verify-signature: Validates HMAC-SHA256 signature on bank response.
"""

from fastapi import APIRouter, HTTPException, Query, Header, Request, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from backend.app.services.simulated_bank_service import (
    SimulatedBankService,
    compute_bank_signature,
    verify_bank_signature,
    BankTimeoutException,
    BankRateLimitException,
    BankDowntimeException
)

router = APIRouter(prefix="/mock-bank", tags=["Simulated Bank Service"])

class BankVerifyPayload(BaseModel):
    bank: str = Field(..., example="Bharat National Bank")
    branch_ifsc: str = Field(..., example="BNBN0004918")
    fdr_number: str = Field(..., example="BNB-DEL-HERO-1000")
    amount: float = Field(..., example=1000000.0)
    issue_date: str = Field(..., example="2024-11-15")
    maturity_date: str = Field(..., example="2032-11-15")
    scenario: Optional[str] = Field(None, example="SUCCESS")

class SignatureVerifyPayload(BaseModel):
    payload: Dict[str, Any]
    signature: str

@router.get("/health")
def mock_bank_health():
    return {
        "status": "healthy",
        "service": "DepoSafe Simulated Core Banking Gateway",
        "disclaimer": "SIMULATED, not a real bank verification"
    }

@router.post("/verify")
def verify_bank_instrument(
    body: BankVerifyPayload,
    x_scenario: Optional[str] = Header(None, alias="X-Simulated-Scenario")
):
    """
    Simulates core banking verification with controllable behaviors:
    - SUCCESS: All available checks passed, returns signed payload.
    - MISMATCH: Returns conflicting maturity date or amount with diffs.
    - NOT_FOUND: Returns not confirmed in core banking.
    - TIMEOUT: Simulates HTTP 408 Gateway Timeout.
    - RATE_LIMIT: Simulates HTTP 429 Too Many Requests.
    - DOWNTIME: Simulates HTTP 503 Core Banking Downtime.
    - SIGNED_RESPONSE: Generates cryptographically signed payload.
    """
    scenario = body.scenario or x_scenario

    try:
        result = SimulatedBankService.query_core_banking(
            bank=body.bank,
            branch_ifsc=body.branch_ifsc,
            fdr_number=body.fdr_number,
            amount=body.amount,
            issue_date=body.issue_date,
            maturity_date=body.maturity_date,
            scenario=scenario
        )
        return result
    except BankTimeoutException as e:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail={"error": "BANK_GATEWAY_TIMEOUT", "message": str(e), "simulated": True}
        )
    except BankRateLimitException as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "BANK_RATE_LIMIT_EXCEEDED", "message": str(e), "retry_after_seconds": 30, "simulated": True}
        )
    except BankDowntimeException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "BANK_CORE_DOWNTIME", "message": str(e), "simulated": True}
        )

@router.post("/verify-signature")
def check_bank_signature(body: SignatureVerifyPayload):
    is_valid = verify_bank_signature(body.payload, body.signature)
    return {
        "valid": is_valid,
        "disclaimer": "SIMULATED, not a real bank verification"
    }

