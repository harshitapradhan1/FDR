from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from backend.app.models.deposafe_models import UserRole, FDRStatus, ProvenanceLevel, BankVerificationStatus

# Auth
class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    institution_id: Optional[int] = None
    regional_office: Optional[str] = None
    designation: Optional[str] = None

    class Config:
        from_attributes = True

# Institution
class InstitutionCreate(BaseModel):
    aicte_id: str
    name: str
    society_or_trust_name: str
    category: str
    program_level: str
    institution_type: str = "Normal"
    state: str
    regional_office: str
    address: Optional[str] = None
    contact_email: str
    contact_phone: str
    authorized_signatory_name: str
    signatory_pan_or_id: Optional[str] = None

class InstitutionOut(InstitutionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Provenance
class FieldProvenanceOut(BaseModel):
    id: int
    field_name: str
    submitted_value: Optional[str]
    ai_extracted_value: Optional[str]
    bank_confirmed_value: Optional[str]
    officer_verified_value: Optional[str]
    status: ProvenanceLevel
    ai_confidence: float
    bounding_box: Optional[Any]
    mismatch_reason: Optional[str]

    class Config:
        from_attributes = True

class ProvenanceVerifyRequest(BaseModel):
    field_name: str
    verified_value: str
    officer_notes: Optional[str] = None

# FDR
class FDRCreate(BaseModel):
    institution_id: int
    bank_name: str
    branch_name: str
    ifsc_code: str
    fdr_number: str
    amount: float
    issue_date: date
    maturity_date: date
    tenure_months: int
    interest_rate: Optional[float] = None
    auto_renewal: bool = False
    joint_holder_name: Optional[str] = None
    lien_marked_to_aicte: bool = True
    lien_clause_text: Optional[str] = None

class FDROut(BaseModel):
    id: int
    institution_id: int
    bank_name: str
    branch_name: str
    ifsc_code: str
    fdr_number: str
    amount: float
    issue_date: date
    maturity_date: date
    tenure_months: int
    interest_rate: Optional[float]
    auto_renewal: bool
    status: FDRStatus
    review_priority_score: float
    review_priority_level: str
    officer_override: bool
    created_at: datetime

    class Config:
        from_attributes = True

class FDRDetailOut(FDROut):
    institution: Optional[InstitutionOut] = None
    review_flags: List[Dict[str, Any]] = []
    officer_override_justification: Optional[str] = None
    provenance_fields: List[FieldProvenanceOut] = []
    compliance_evaluation: Optional[Dict[str, Any]] = None
    documents: List[Dict[str, Any]] = []
    bank_verifications: List[Dict[str, Any]] = []

class FDRRenewRequest(BaseModel):
    new_fdr_number: str
    bank_name: str
    branch_name: str
    ifsc_code: str
    amount: float
    issue_date: date
    maturity_date: date
    tenure_months: int
    interest_rate: Optional[float] = None
    auto_renewal: bool = True
    lien_clause_text: Optional[str] = None

class FDRReleaseRequest(BaseModel):
    justification: str
    noc_reference: str

class FDRReleaseApproval(BaseModel):
    approved: bool
    release_order_ref: str
    remarks: str

class OfficerOverrideRequest(BaseModel):
    justification: str
    adjusted_score: Optional[float] = None
    new_status: Optional[FDRStatus] = None

# Bank Verification
class BankVerifyRequest(BaseModel):
    fdr_id: int
    force_adapter: Optional[str] = None # "SIMULATED" or "MANUAL"

class ManualVerificationRequest(BaseModel):
    fdr_id: int
    evidence_type: str # BRANCH_VISIT_REPORT, OFFICIAL_LETTER, EMAIL_CONFIRMATION
    evidence_details: Dict[str, Any]
    remarks: str

# Demo Clock
class DemoClockAdvance(BaseModel):
    days: int

class DemoClockSet(BaseModel):
    target_date: date

class DemoClockOut(BaseModel):
    current_simulated_date: date
    offset_days: int
    updated_at: datetime

# Phase 3: Integrity & Lifecycle Passport Schemas
class IntegrityCheckDocumentResult(BaseModel):
    document_id: int
    version: int
    file_name: str
    status: str # "INTACT", "TAMPERED", "FILE_MISSING"
    is_tampered: bool
    recorded_hash: str
    current_hash: Optional[str] = None
    chain_of_custody_verified: bool
    message: str

class IntegrityCheckOut(BaseModel):
    fdr_id: int
    overall_status: str
    has_tampering: bool
    documents_checked: int
    results: List[IntegrityCheckDocumentResult]
    disclaimer: str = "Cryptographic integrity verified against immutable SHA-256 chain of custody."

class SignedDownloadUrlOut(BaseModel):
    document_id: int
    file_name: str
    download_url: str
    expires_at: int
    expires_in_seconds: int
    disclaimer: str = "Temporary expiring link. Do not share credentials."

class PaginatedFDROut(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[FDROut]
