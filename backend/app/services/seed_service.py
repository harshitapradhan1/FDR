import os
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models.deposafe_models import (
    User, UserRole, Institution, FDR, FDRDocument, FieldProvenance,
    BankVerificationRecord, FDRStatus, ProvenanceLevel, BankVerificationStatus
)
from backend.app.rules.compliance_engine import get_active_rule, evaluate_fdr_compliance
from backend.app.services.demo_clock import get_simulated_today
from backend.app.services.risk_engine import compute_review_priority
from backend.app.services.audit_service import record_audit_event
from backend.app.services.pdf_generator import generate_synthetic_fdr_pdf

from backend.app.core.database import Base, engine

def seed_database_if_empty(db: Session):
    Base.metadata.create_all(bind=engine)
    existing_user = db.query(User).first()
    if existing_user:
        return # Already seeded

    simulated_today = get_simulated_today(db)
    active_rule = get_active_rule(db)

    # 1. Seed Institutions
    inst1 = Institution(
        aicte_id="1-3324567891",
        name="Vidya Institute of Technology & Science",
        society_or_trust_name="Shree Vidya Educational Trust",
        category="Engineering & Technology",
        program_level="UG",
        institution_type="Normal",
        state="Delhi",
        regional_office="North Western Regional Office",
        address="Sector 12, Dwarka, New Delhi 110078",
        contact_email="principal@vidyatech.edu.in",
        contact_phone="+91 11 2808 1234",
        authorized_signatory_name="Dr. Ramesh Sharma",
        signatory_pan_or_id="AAAPL1234K"
    )
    inst2 = Institution(
        aicte_id="1-4455667788",
        name="Sunrise College of Pharmacy",
        society_or_trust_name="Sunrise Foundation",
        category="Pharmacy",
        program_level="UG",
        institution_type="Normal",
        state="Punjab",
        regional_office="North Western Regional Office",
        address="GT Road, Mohali, Punjab 160055",
        contact_email="admin@sunrisepharm.edu.in",
        contact_phone="+91 172 2234 567",
        authorized_signatory_name="Dr. Ananya Verma",
        signatory_pan_or_id="BBBPV5678M"
    )
    inst3 = Institution(
        aicte_id="1-9988776655",
        name="Aryavrat Institute of Management",
        society_or_trust_name="Aryavrat Education Trust",
        category="Management",
        program_level="PG",
        institution_type="Normal",
        state="Maharashtra",
        regional_office="Western Regional Office",
        address="Nariman Point, Mumbai 400021",
        contact_email="director@aryavratmgmt.ac.in",
        contact_phone="+91 22 2282 9988",
        authorized_signatory_name="Prof. Suresh Patil",
        signatory_pan_or_id="CCCPP9012N"
    )
    inst4 = Institution(
        aicte_id="1-5544332211",
        name="Vidya Polytechnic College",
        society_or_trust_name="Shree Vidya Educational Trust", # Same Trust as Inst 1!
        category="Engineering & Technology",
        program_level="Diploma",
        institution_type="Normal",
        state="Haryana",
        regional_office="North Western Regional Office",
        address="NH-1, Sonipat, Haryana 131001",
        contact_email="polytechnic@vidyatech.edu.in",
        contact_phone="+91 130 2211 445",
        authorized_signatory_name="Dr. Ramesh Sharma", # Same Signatory as Inst 1!
        signatory_pan_or_id="AAAPL1234K"
    )
    db.add_all([inst1, inst2, inst3, inst4])
    db.commit()
    db.refresh(inst1)
    db.refresh(inst2)
    db.refresh(inst3)
    db.refresh(inst4)

    # 2. Seed Users
    hashed_pwd = hash_password("Password@123")
    users = [
        User(
            email="admin@deposafe.aicte.gov.in",
            hashed_password=hashed_pwd,
            full_name="Rajesh Kumar, Senior Director",
            role=UserRole.SYSTEM_ADMIN,
            designation="Director (Regulations & IT)"
        ),
        User(
            email="officer@deposafe.aicte.gov.in",
            hashed_password=hashed_pwd,
            full_name="Vikramaditya Rao",
            role=UserRole.VERIFICATION_OFFICER,
            regional_office="North Western Regional Office",
            designation="Deputy Director (Inspection & Verification)"
        ),
        User(
            email="ro.north@deposafe.aicte.gov.in",
            hashed_password=hashed_pwd,
            full_name="Dr. Sunita Deshmukh",
            role=UserRole.REGIONAL_OFFICER,
            regional_office="North Western Regional Office",
            designation="Regional Officer (NWRO)"
        ),
        User(
            email="director.approval@aicte-india.org",
            hashed_password=hashed_pwd,
            full_name="Prof. T. G. Sitaram",
            role=UserRole.COMPETENT_AUTHORITY,
            designation="Competent Authority / Member Secretary AICTE"
        ),
        User(
            email="institution1@vidya.edu.in",
            hashed_password=hashed_pwd,
            full_name="Dr. Ramesh Sharma",
            role=UserRole.INSTITUTION_USER,
            institution_id=inst1.id,
            designation="Principal & Authorized Signatory"
        ),
        User(
            email="institution2@sunrise.edu.in",
            hashed_password=hashed_pwd,
            full_name="Dr. Ananya Verma",
            role=UserRole.INSTITUTION_USER,
            institution_id=inst2.id,
            designation="Director"
        )
    ]
    db.add_all(users)
    db.commit()

    # 3. Seed FDR Instruments with PDF documents & 4-level Provenance
    
    # FDR 1: Fully Compliant SBI Deposit
    fdr1 = FDR(
        institution_id=inst1.id,
        bank_name="State Bank of India",
        branch_name="New Delhi Main Branch",
        ifsc_code="SBIN0000691",
        fdr_number="SBI-DEL-9876543210",
        amount=3500000.0,
        issue_date=date(2024, 4, 15),
        maturity_date=date(2032, 4, 15),
        tenure_months=96,
        interest_rate=7.25,
        auto_renewal=True,
        joint_holder_name=f"Regional Officer AICTE & {inst1.society_or_trust_name}",
        lien_marked_to_aicte=True,
        lien_clause_text="Pledged under Lien jointly in the name of Regional Officer, AICTE (North Western Regional Office) and President / Secretary, Shree Vidya Educational Trust.",
        status=FDRStatus.COMPLIANT
    )
    db.add(fdr1)
    db.commit()
    db.refresh(fdr1)

    # Generate PDF for FDR 1
    fdr1_pdf_path = os.path.join(settings.STORAGE_DIR, f"fdr_{fdr1.id}", "v1_SBI_Certificate.pdf")
    generate_synthetic_fdr_pdf(
        output_path=fdr1_pdf_path,
        bank_name=fdr1.bank_name,
        branch_name=fdr1.branch_name,
        ifsc_code=fdr1.ifsc_code,
        fdr_number=fdr1.fdr_number,
        amount=fdr1.amount,
        issue_date=fdr1.issue_date,
        maturity_date=fdr1.maturity_date,
        society_name=inst1.society_or_trust_name,
        institution_name=inst1.name,
        regional_office=inst1.regional_office,
        tenure_months=fdr1.tenure_months,
        tamper_metadata=False,
        include_proper_lien=True
    )

    doc1 = FDRDocument(
        fdr_id=fdr1.id,
        version=1,
        file_name="v1_SBI_Certificate.pdf",
        file_path=fdr1_pdf_path,
        file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        perceptual_hash="b4a8e3d29c1f0a5b",
        forensic_metadata={
            "pdf_producer": "CoreBankingSystem CBS-PDF Engine v4.1",
            "pdf_creator": "Authorized Bank Server",
            "producer_flagged": False,
            "tampering_indicators": []
        }
    )
    db.add(doc1)

    # FDR 1 Provenance
    prov1_data = [
        ("fdr_number", fdr1.fdr_number, fdr1.fdr_number, fdr1.fdr_number, fdr1.fdr_number, ProvenanceLevel.BANK_CONFIRMED),
        ("amount", "3500000.0", "3500000.0", "3500000.0", "3500000.0", ProvenanceLevel.BANK_CONFIRMED),
        ("bank_name", fdr1.bank_name, fdr1.bank_name, fdr1.bank_name, fdr1.bank_name, ProvenanceLevel.BANK_CONFIRMED),
        ("ifsc_code", fdr1.ifsc_code, fdr1.ifsc_code, fdr1.ifsc_code, fdr1.ifsc_code, ProvenanceLevel.BANK_CONFIRMED),
        ("maturity_date", "2032-04-15", "2032-04-15", "2032-04-15", "2032-04-15", ProvenanceLevel.BANK_CONFIRMED),
        ("lien_marked", "YES", "YES", "YES", "YES", ProvenanceLevel.BANK_CONFIRMED)
    ]
    for fn, sub, ai, bank, off, st in prov1_data:
        db.add(FieldProvenance(
            fdr_id=fdr1.id,
            field_name=fn,
            submitted_value=sub,
            ai_extracted_value=ai,
            bank_confirmed_value=bank,
            officer_verified_value=off,
            status=st,
            ai_confidence=0.98
        ))

    # Bank verification record for FDR 1
    db.add(BankVerificationRecord(
        fdr_id=fdr1.id,
        adapter_used="SIMULATED_SFMS",
        verification_status=BankVerificationStatus.AVAILABLE_CHECKS_PASSED,
        api_reference_id="SIM-SFMS-A99B88CC77",
        watermark_notice="SIMULATED, not a real bank verification",
        remarks="Simulated bank CBS confirmation received via mock SFMS adapter."
    ))

    # FDR 2: High Review Priority / Deficit & Metadata Tampering Anomaly
    fdr2 = FDR(
        institution_id=inst2.id,
        bank_name="Punjab National Bank",
        branch_name="Connaught Place",
        ifsc_code="PUNB0012300",
        fdr_number="PNB-DEL-4455667788",
        amount=1500000.0, # Deficit: Pharmacy UG requires 25 Lakhs!
        issue_date=date(2024, 6, 1),
        maturity_date=date(2032, 6, 1),
        tenure_months=96,
        interest_rate=6.85,
        auto_renewal=False,
        joint_holder_name=inst2.society_or_trust_name,
        lien_marked_to_aicte=False, # Missing lien!
        status=FDRStatus.UNDER_VERIFICATION,
        review_priority_score=75.0,
        review_priority_level="HIGH",
        review_flags=[
            {
                "code": "FLAG-DEPOSIT-DEFICIT",
                "severity": "HIGH",
                "title": "Deposit Norm Deficit",
                "reason": "Deficit of Rs. 1,000,000.00 detected against prescribed handbook norm.",
                "evidence": "Required: Rs. 2,500,000.00, Submitted: Rs. 1,500,000.00",
                "rule_reference": "APH-RULE-AMT-02"
            },
            {
                "code": "FLAG-LIEN-CLAUSE-MISSING",
                "severity": "HIGH",
                "title": "AICTE Lien Clause Non-Compliance",
                "reason": "Missing mandatory joint lien clause pledged to Regional Officer, AICTE.",
                "evidence": "Lien clause not marked on instrument face.",
                "rule_reference": "APH-RULE-LIEN-04"
            },
            {
                "code": "FLAG-METADATA-EDIT-TOOL",
                "severity": "HIGH",
                "title": "Document Editing Software Signature",
                "reason": "PDF metadata indicates generation using graphic editing software.",
                "evidence": "Detected: Canva PDF Designer v2.4 (tampered-producer-flag)",
                "rule_reference": "FORENSIC-META-02"
            }
        ]
    )
    db.add(fdr2)
    db.commit()
    db.refresh(fdr2)

    # Generate PDF for FDR 2 with tampered metadata
    fdr2_pdf_path = os.path.join(settings.STORAGE_DIR, f"fdr_{fdr2.id}", "v1_PNB_Tampered.pdf")
    generate_synthetic_fdr_pdf(
        output_path=fdr2_pdf_path,
        bank_name=fdr2.bank_name,
        branch_name=fdr2.branch_name,
        ifsc_code=fdr2.ifsc_code,
        fdr_number=fdr2.fdr_number,
        amount=fdr2.amount,
        issue_date=fdr2.issue_date,
        maturity_date=fdr2.maturity_date,
        society_name=inst2.society_or_trust_name,
        institution_name=inst2.name,
        regional_office=inst2.regional_office,
        tenure_months=fdr2.tenure_months,
        tamper_metadata=True,
        include_proper_lien=False
    )
    db.add(FDRDocument(
        fdr_id=fdr2.id,
        version=1,
        file_name="v1_PNB_Tampered.pdf",
        file_path=fdr2_pdf_path,
        file_hash_sha256="7c5a9d2e1b4f8a3c6e9d0b2a5c8e1f4a7b0d3e6f9a2c5b8e1d4f7a0b3c6e9d2f",
        perceptual_hash="d8c4a2b1e7f9035a",
        forensic_metadata={
            "pdf_producer": "Canva PDF Designer v2.4 (tampered-producer-flag)",
            "producer_flagged": True,
            "tampering_indicators": ["Suspicious editing tool signature detected in PDF metadata: 'Canva PDF Designer v2.4'"]
        }
    ))

    # Provenance with Mismatch for FDR 2
    prov2_data = [
        ("fdr_number", fdr2.fdr_number, fdr2.fdr_number, None, None, ProvenanceLevel.AI_EXTRACTED),
        ("amount", "2500000.0", "1500000.0", None, None, ProvenanceLevel.MISMATCH),
        ("bank_name", fdr2.bank_name, fdr2.bank_name, None, None, ProvenanceLevel.AI_EXTRACTED),
        ("ifsc_code", fdr2.ifsc_code, fdr2.ifsc_code, None, None, ProvenanceLevel.AI_EXTRACTED),
        ("maturity_date", "2032-06-01", "2032-06-01", None, None, ProvenanceLevel.AI_EXTRACTED),
        ("lien_marked", "YES", "NO", None, None, ProvenanceLevel.MISMATCH)
    ]
    for fn, sub, ai, bank, off, st in prov2_data:
        db.add(FieldProvenance(
            fdr_id=fdr2.id,
            field_name=fn,
            submitted_value=sub,
            ai_extracted_value=ai,
            bank_confirmed_value=bank,
            officer_verified_value=off,
            status=st,
            ai_confidence=0.95,
            mismatch_reason="Discrepancy detected between submitted declaration and scanned certificate." if st == ProvenanceLevel.MISMATCH else None
        ))

    # FDR 3: Renewal Due / Imminent Maturity (Matures in 18 days relative to simulated date)
    imminent_maturity = simulated_today + timedelta(days=18)
    fdr3 = FDR(
        institution_id=inst3.id,
        bank_name="Bank of Baroda",
        branch_name="Nariman Point",
        ifsc_code="BARB0NARIMA",
        fdr_number="BOB-BOM-1122334455",
        amount=1500000.0,
        issue_date=imminent_maturity - timedelta(days=96 * 30),
        maturity_date=imminent_maturity,
        tenure_months=96,
        interest_rate=7.10,
        auto_renewal=False,
        joint_holder_name=f"Regional Officer AICTE & {inst3.society_or_trust_name}",
        lien_marked_to_aicte=True,
        status=FDRStatus.RENEWAL_DUE,
        review_priority_score=15.0,
        review_priority_level="LOW"
    )
    db.add(fdr3)
    db.commit()
    db.refresh(fdr3)

    prov3_data = [
        ("fdr_number", fdr3.fdr_number, fdr3.fdr_number, fdr3.fdr_number, fdr3.fdr_number, ProvenanceLevel.BANK_CONFIRMED),
        ("amount", "1500000.0", "1500000.0", "1500000.0", "1500000.0", ProvenanceLevel.BANK_CONFIRMED),
        ("maturity_date", imminent_maturity.isoformat(), imminent_maturity.isoformat(), imminent_maturity.isoformat(), imminent_maturity.isoformat(), ProvenanceLevel.BANK_CONFIRMED)
    ]
    for fn, sub, ai, bank, off, st in prov3_data:
        db.add(FieldProvenance(
            fdr_id=fdr3.id,
            field_name=fn,
            submitted_value=sub,
            ai_extracted_value=ai,
            bank_confirmed_value=bank,
            officer_verified_value=off,
            status=st
        ))

    # FDR 4: Release Requested Deposit (Awaiting Competent Authority Authorization)
    past_date = simulated_today - timedelta(days=15)
    fdr4 = FDR(
        institution_id=inst4.id,
        bank_name="Canara Bank",
        branch_name="Sonipat City",
        ifsc_code="CNRB0001928",
        fdr_number="CNR-SON-8899001122",
        amount=1500000.0,
        issue_date=past_date - timedelta(days=96 * 30),
        maturity_date=past_date,
        tenure_months=96,
        interest_rate=7.50,
        auto_renewal=False,
        joint_holder_name=f"Regional Officer AICTE & {inst4.society_or_trust_name}",
        lien_marked_to_aicte=True,
        status=FDRStatus.RELEASE_REQUESTED,
        release_requested_at=datetime.utcnow() - timedelta(days=2),
        release_justification="Institution closure completed under Regulation 11(2). No pending student grievances. State Government & Affiliating University NOC uploaded. NOC Ref: NOC-HR-CLOSURE-2024-89."
    )
    db.add(fdr4)
    db.commit()
    db.refresh(fdr4)

    # 4. Initialize Cryptographic Hash-Chained Audit Ledger
    db.commit()
    record_audit_event(
        db=db,
        event_type="SYSTEM_GENESIS_INITIALIZED",
        entity_type="SYSTEM",
        entity_id="GENESIS",
        actor_id=1,
        actor_role="SYSTEM_ADMIN",
        payload={
            "app": "DepoSafe",
            "version": "1.0.0",
            "message": "AICTE Regulation Bureau Security Deposit Intelligence Ledger established."
        }
    )
    record_audit_event(
        db=db,
        event_type="SEED_DATA_LOADED",
        entity_type="SYSTEM",
        entity_id="SEED_LOADER",
        actor_id=1,
        actor_role="SYSTEM_ADMIN",
        payload={
            "institutions_seeded": 4,
            "fdrs_seeded": 4,
            "rules_version": active_rule.version_tag
        }
    )
