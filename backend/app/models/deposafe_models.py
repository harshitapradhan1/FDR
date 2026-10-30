import enum
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    Text, ForeignKey, Enum as SQLEnum, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class UserRole(str, enum.Enum):
    INSTITUTION_USER = "INSTITUTION_USER"
    VERIFICATION_OFFICER = "VERIFICATION_OFFICER"
    REGIONAL_OFFICER = "REGIONAL_OFFICER"
    COMPETENT_AUTHORITY = "COMPETENT_AUTHORITY"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

class FDRStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    RENEWAL_DUE = "RENEWAL_DUE"
    RENEWED_SUPERSEDED = "RENEWED_SUPERSEDED"
    RELEASE_REQUESTED = "RELEASE_REQUESTED"
    RELEASED = "RELEASED"
    FORFEITED = "FORFEITED"

class ProvenanceLevel(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    AI_EXTRACTED = "AI_EXTRACTED"
    BANK_CONFIRMED = "BANK_CONFIRMED"
    OFFICER_VERIFIED = "OFFICER_VERIFIED"
    MISMATCH = "MISMATCH"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"

class BankVerificationStatus(str, enum.Enum):
    AVAILABLE_CHECKS_PASSED = "AVAILABLE_CHECKS_PASSED"
    NOT_CONFIRMED = "NOT_CONFIRMED"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.INSTITUTION_USER)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    regional_office = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="users")

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    aicte_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    society_or_trust_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False) # e.g. Technical, Management, Pharmacy
    program_level = Column(String(50), nullable=False) # UG, PG, Diploma
    institution_type = Column(String(50), nullable=False, default="Normal") # Normal, Minority, Women, PwD
    state = Column(String(100), nullable=False)
    regional_office = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50), nullable=False)
    authorized_signatory_name = Column(String(255), nullable=False)
    signatory_pan_or_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="institution")
    fdrs = relationship("FDR", back_populates="institution")

class FDR(Base):
    __tablename__ = "fdrs"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    
    # Financial & Instrument Details
    bank_name = Column(String(255), nullable=False, index=True)
    branch_name = Column(String(255), nullable=False)
    ifsc_code = Column(String(20), nullable=False, index=True)
    fdr_number = Column(String(100), nullable=False, index=True) # Indexed, but NOT globally unique
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    tenure_months = Column(Integer, nullable=False)
    interest_rate = Column(Float, nullable=True)
    auto_renewal = Column(Boolean, default=False)
    
    # Lien & Joint Clause
    joint_holder_name = Column(String(255), nullable=True)
    lien_marked_to_aicte = Column(Boolean, default=False)
    lien_clause_text = Column(Text, nullable=True)
    
    # Status & LifeCycle
    status = Column(SQLEnum(FDRStatus), default=FDRStatus.PENDING_REVIEW, nullable=False, index=True)
    predecessor_fdr_id = Column(Integer, ForeignKey("fdrs.id"), nullable=True)
    successor_fdr_id = Column(Integer, ForeignKey("fdrs.id"), nullable=True)
    
    # Risk & Review Priority Indicator (Advisory Only)
    review_priority_score = Column(Float, default=0.0) # 0.0 to 100.0 review priority indicator
    review_priority_level = Column(String(20), default="LOW") # LOW, MEDIUM, HIGH, CRITICAL
    review_flags = Column(JSON, default=list) # List of explainable flags
    
    # Human-In-The-Loop Officer Override
    officer_override = Column(Boolean, default=False)
    officer_override_justification = Column(Text, nullable=True)
    officer_override_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    officer_override_at = Column(DateTime, nullable=True)

    # Release / Refund Authorization (Only Competent Authority)
    release_requested_at = Column(DateTime, nullable=True)
    release_justification = Column(Text, nullable=True)
    release_authorized_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    release_authorized_at = Column(DateTime, nullable=True)
    release_order_ref = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution = relationship("Institution", back_populates="fdrs")
    documents = relationship("FDRDocument", back_populates="fdr", cascade="all, delete-orphan")
    provenance_fields = relationship("FieldProvenance", back_populates="fdr", cascade="all, delete-orphan")
    bank_verifications = relationship("BankVerificationRecord", back_populates="fdr", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_bank_fdr_composite", "bank_name", "fdr_number"),
    )

class FDRDocument(Base):
    __tablename__ = "fdr_documents"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdrs.id"), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    perceptual_hash = Column(String(64), nullable=True, index=True)
    mime_type = Column(String(100), default="application/pdf")
    file_size_bytes = Column(Integer, nullable=True)
    forensic_metadata = Column(JSON, default=dict)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    fdr = relationship("FDR", back_populates="documents")

class FieldProvenance(Base):
    __tablename__ = "field_provenance"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdrs.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    submitted_value = Column(String(500), nullable=True)
    ai_extracted_value = Column(String(500), nullable=True)
    bank_confirmed_value = Column(String(500), nullable=True)
    officer_verified_value = Column(String(500), nullable=True)
    status = Column(SQLEnum(ProvenanceLevel), default=ProvenanceLevel.SUBMITTED, nullable=False)
    ai_confidence = Column(Float, default=1.0)
    bounding_box = Column(JSON, nullable=True) # [x, y, w, h] or page coordinates
    mismatch_reason = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fdr = relationship("FDR", back_populates="provenance_fields")

class BankVerificationRecord(Base):
    __tablename__ = "bank_verification_records"

    id = Column(Integer, primary_key=True, index=True)
    fdr_id = Column(Integer, ForeignKey("fdrs.id"), nullable=False)
    adapter_used = Column(String(50), nullable=False) # SIMULATED or MANUAL
    verification_status = Column(SQLEnum(BankVerificationStatus), nullable=False)
    api_reference_id = Column(String(100), nullable=True)
    watermark_notice = Column(String(255), default="SIMULATED, not a real bank verification")
    manual_evidence_type = Column(String(100), nullable=True) # BRANCH_VISIT_REPORT, OFFICIAL_LETTER, EMAIL_CONFIRMATION
    manual_evidence_details = Column(JSON, default=dict)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, default=datetime.utcnow)
    remarks = Column(Text, nullable=True)

    fdr = relationship("FDR", back_populates="bank_verifications")

class AuditLog(Base):
    """
    Append-only cryptographic hash chain:
    H_n = SHA256(H_{n-1} || event_n)
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    sequence_num = Column(Integer, unique=True, nullable=False, index=True)
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    actor_id = Column(Integer, nullable=True)
    actor_role = Column(String(50), nullable=True)
    ip_address = Column(String(50), nullable=True, default="127.0.0.1")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    timestamp_iso = Column(String(50), nullable=False)
    payload = Column(JSON, default=dict)

class ComplianceRule(Base):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    version_tag = Column(String(50), unique=True, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    description = Column(String(255), nullable=False)
    rules_json = Column(JSON, nullable=False)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DemoClock(Base):
    __tablename__ = "demo_clock"

    id = Column(Integer, primary_key=True, default=1)
    current_simulated_date = Column(Date, nullable=False)
    offset_days = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, nullable=True)
