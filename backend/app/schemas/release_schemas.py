from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class ReleaseSubmissionRequest(BaseModel):
    justification: str
    amount: float
    noc_reference: str
    noc_issuing_authority: Optional[str] = "State Directorate of Technical Education & Affiliating University"
    reason: Optional[str] = "Course closure completed with zero pending student obligations under APH Chapter I Regulation 11."

class ReleaseScrutinyRequest(BaseModel):
    action: str # "BEGIN_SCRUTINY", "REQUEST_CLARIFICATION", "RECOMMEND", "REJECT", "RESUBMIT"
    remarks: str
    clarification_details: Optional[str] = None

class ReleaseAuthorizationRequest(BaseModel):
    approved: bool
    typed_justification: str = Field(..., min_length=10, description="Mandatory typed justification required by Competent Authority")
    release_order_ref: str = Field(..., description="Official AICTE Gazette / Sanction Order Reference")
    remarks: Optional[str] = None

