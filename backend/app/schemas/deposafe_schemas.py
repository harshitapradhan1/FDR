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
class ProvenanceBadgeStyle(BaseModel):
    source: str
    label: str
    bg_class: str
    text_class: str
    border_class: str
    hex_color: str

PROVENANCE_BADGE_MAP = {
    "SUBMITTED": ProvenanceBadgeStyle(
        source="SUBMITTED",
        label="Submitted (Institution)",
        bg_class="bg-blue-100",
        text_class="text-blue-800",
        border_class="border-blue-300",
        hex_color="#2563EB"
    ),
    "AI_EXTRACTED": ProvenanceBadgeStyle(
        source="AI_EXTRACTED",
        label="AI Extracted (OCR/Layout)",
        bg_class="bg-purple-100",
        text_class="text-purple-800",
        border_class="border-purple-300",
        hex_color="#9333EA"
    ),
    "BANK_CONFIRMED": ProvenanceBadgeStyle(
        source="BANK_CONFIRMED",
        label="Bank Confirmed (CBS/SFMS)",
        bg_class="bg-emerald-100",
        text_class="text-emerald-800",
        border_class="border-emerald-300",
        hex_color="#059669"
    ),
    "OFFICER_VERIFIED": ProvenanceBadgeStyle(
        source="OFFICER_VERIFIED",
        label="Officer Verified (Human-in-Loop)",
        bg_class="bg-amber-100",
        text_class="text-amber-800",
        border_class="border-amber-300",
        hex_color="#D97706"
    ),
    "MISMATCH": ProvenanceBadgeStyle(
        source="MISMATCH",
        label="Conflict / Mismatch Detected",
        bg_class="bg-rose-100",
        text_class="text-rose-800",
        border_class="border-rose-300",
        hex_color="#E11D48"
    ),
    "SOURCE_UNAVAILABLE": ProvenanceBadgeStyle(
        source="SOURCE_UNAVAILABLE",
        label="Source Unavailable",
        bg_class="bg-slate-100",
        text_class="text-slate-800",
        border_class="border-slate-300",
        hex_color="#64748B"
    )
}

class FieldProvenanceOut(BaseModel):
    id: int
    field_name: str
    submitted_value: Optional[str] = None
    ai_extracted_value: Optional[str] = None
    bank_confirmed_value: Optional[str] = None
    officer_verified_value: Optional[str] = None

    submitted_at: Optional[datetime] = None
    ai_extracted_at: Optional[datetime] = None
    bank_confirmed_at: Optional[datetime] = None
    officer_verified_at: Optional[datetime] = None

    submitted_by: Optional[str] = None
    ai_extracted_by: Optional[str] = None
    bank_confirmed_by: Optional[str] = None
    officer_verified_by: Optional[str] = None

    status: ProvenanceLevel
    ai_confidence: float = 1.0
    bounding_box: Optional[Any] = None
    mismatch_reason: Optional[str] = None
    conflicts: List[Any] = []
    badge_style: Optional[ProvenanceBadgeStyle] = None

    class Config:
        from_attributes = True

class ProvenanceVerifyRequest(BaseModel):
    field_name: str
    verified_value: str
    officer_notes: Optional[str] = None

class ManualVerificationRequest(BaseModel):
    fdr_id: Optional[int] = None
    method: Optional[str] = "OFFICIAL_PORTAL_VISIT"  # OFFICIAL_PORTAL_VISIT, BRANCH_VISIT, REGISTERED_EMAIL_CONFIRMATION, PHONE_DISPATCH, WRITTEN_DISPATCH
    reference_id: Optional[str] = None
    remarks: Optional[str] = "Manual verification recorded"
    evidence_document_id: Optional[int] = None
    verified_fields: Optional[Dict[str, str]] = None
    evidence_type: Optional[str] = None  # Backward compatibility
    evidence_details: Optional[Dict[str, Any]] = None  # Backward compatibility

class BankVerifyRequest(BaseModel):
    fdr_id: Optional[int] = None
    force_adapter: Optional[str] = None
    scenario: Optional[str] = "SUCCESS"  # SUCCESS, MISMATCH, NOT_FOUND, TIMEOUT, RATE_LIMIT, DOWNTIME, SIGNED_RESPONSE

class ReconciliationEvidenceOut(BaseModel):
    doc_type: str
    document_id: Optional[int] = None
    file_name: str
    value: Optional[str] = None
    page: int = 1
    bbox: Optional[List[float]] = None

class FieldReconciliationOut(BaseModel):
    field_name: str
    status: str  # MATCH, MISMATCH, SINGLE_SOURCE, NOT_FOUND
    discrepancy_details: Optional[str] = None
    evidence: List[ReconciliationEvidenceOut] = []

class ReconciliationResponseOut(BaseModel):
    fdr_id: int
    fdr_number: str
    institution_id: int
    reconciliation_summary: Dict[str, Any]
    reconciliation_table: List[FieldReconciliationOut]

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

# Phase 4: Corrections & Validation Schemas
class FieldCorrectionRequest(BaseModel):
    field_name: str
    corrected_value: str
    correction_reason: Optional[str] = "Human verification adjustment"

class FieldCorrectionOut(BaseModel):
    id: int
    fdr_id: int
    document_id: Optional[int] = None
    field_name: str
    extracted_value: Optional[str] = None
    corrected_value: str
    correction_reason: Optional[str] = None
    corrected_by: int
    created_at: datetime

    class Config:
        from_attributes = True

