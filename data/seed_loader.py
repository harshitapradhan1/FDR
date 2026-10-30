#!/usr/bin/env python3
"""
DepoSafe Synthetic Seed Loader
Loads /data/synthetic/ground_truth.json directly into PostgreSQL / SQLite database
and mirrors files into object storage / local storage directory.
"""

import os
import json
import shutil
from datetime import datetime, date
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.deposafe_models import (
    User, UserRole, Bank, Institution, FDR, FDRDocument,
    FieldProvenance, BankVerificationRecord, DemoClock,
    ProvenanceLevel, BankVerificationStatus, FDRStatus, BankType
)
from backend.app.core.security import hash_password
from backend.app.services.audit_service import record_audit_event
from backend.app.rules.compliance_engine import get_active_rule

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GROUND_TRUTH_PATH = os.path.join(BASE_DIR, "data", "synthetic", "ground_truth.json")

def load_synthetic_data_into_db(db: Session):
    print("Loading synthetic dataset from ground_truth.json into database...")
    Base.metadata.create_all(bind=engine)

    with open(GROUND_TRUTH_PATH, "r") as f:
        gt = json.load(f)

    # 1. Initialize Banks Whitelist
    from data.generator import BANK_DETAILS
    bank_records = {}
    for code, binfo in BANK_DETAILS.items():
        existing_b = db.query(Bank).filter(Bank.name == binfo["name"]).first()
        if not existing_b:
            b_type = BankType.SCHEDULED_COMMERCIAL if binfo["type"] == "SCHEDULED_COMMERCIAL" else BankType.NON_SCHEDULED
            b = Bank(
                name=binfo["name"],
                bank_type=b_type,
                ifsc_prefix=binfo["ifsc_prefix"],
                rbi_code=f"RBI-{binfo['ifsc_prefix']}",
                is_active=True
            )
            db.add(b)
            db.commit()
            db.refresh(b)
            bank_records[binfo["name"]] = b.id
        else:
            bank_records[binfo["name"]] = existing_b.id

    # 2. Seed Default Administrative Users if not present
    hashed_pwd = hash_password("Password@123")
    default_users = [
        ("admin@deposafe.aicte.gov.in", UserRole.SYSTEM_ADMIN, "Rajesh Kumar, Senior Director", None, "Director (Regulations & IT)"),
        ("officer@deposafe.aicte.gov.in", UserRole.VERIFICATION_OFFICER, "Vikramaditya Rao", "North Western Regional Office", "Deputy Director (Inspection)"),
        ("ro.north@deposafe.aicte.gov.in", UserRole.REGIONAL_OFFICER, "Dr. Sunita Deshmukh", "North Western Regional Office", "Regional Officer (NWRO)"),
        ("director.approval@aicte-india.org", UserRole.COMPETENT_AUTHORITY, "Prof. T. G. Sitaram", None, "Competent Authority / Member Secretary AICTE"),
        ("auditor@deposafe.aicte.gov.in", UserRole.AUDITOR, "Auditor General Team", None, "Vigilance & Compliance Auditor")
    ]
    for email, role, name, ro, desig in default_users:
        if not db.query(User).filter(User.email == email).first():
            db.add(User(
                email=email,
                hashed_password=hashed_pwd,
                full_name=name,
                role=role,
                regional_office=ro,
                designation=desig
            ))
    db.commit()

    # 3. Seed Institutions
    inst_id_map = {}
    for inst in gt["institutions"]:
        existing = db.query(Institution).filter(Institution.aicte_id == inst["aicte_id"]).first()
        if not existing:
            new_inst = Institution(
                aicte_id=inst["aicte_id"],
                name=inst["name"],
                society_or_trust_name=inst["society_or_trust_name"],
                category=inst["category"],
                program_level=inst["program_level"],
                institution_type=inst["institution_type"],
                state=inst["state"],
                regional_office=inst["regional_office"],
                address=inst["address"],
                contact_email=inst["contact_email"],
                contact_phone=inst["contact_phone"],
                authorized_signatory_name=inst["authorized_signatory_name"]
            )
            db.add(new_inst)
            db.commit()
            db.refresh(new_inst)
            inst_id_map[inst["id"]] = new_inst.id

            # Create institution user
            db.add(User(
                email=inst["contact_email"],
                hashed_password=hashed_pwd,
                full_name=inst["authorized_signatory_name"],
                role=UserRole.INSTITUTION_USER,
                institution_id=new_inst.id,
                designation="Principal / Authorized Signatory"
            ))
        else:
            inst_id_map[inst["id"]] = existing.id
    db.commit()

    # 4. Seed FDRs, Documents & 4-Level Field Provenance
    fdr_id_map = {}
    for f in gt["fdrs"]:
        real_inst_id = inst_id_map.get(f["institution_id"])
        if not real_inst_id:
            continue

        existing_fdr = db.query(FDR).filter(
            FDR.bank_name == f["bank_name"],
            FDR.fdr_number == f["fdr_number"],
            FDR.institution_id == real_inst_id
        ).first()

        if not existing_fdr:
            bank_id = bank_records.get(f["bank_name"])
            
            # Map issues to review score
            issues = f.get("injected_issues", [])
            score = 0.0
            if len(issues) > 0:
                score = min(25.0 * len(issues) + 10.0, 95.0)

            review_level = "LOW"
            if score >= 80:
                review_level = "CRITICAL"
            elif score >= 50:
                review_level = "HIGH"
            elif score >= 25:
                review_level = "MEDIUM"

            fdr_rec = FDR(
                internal_fdr_id=f.get("internal_fdr_id", f"FDR-INT-{f['id']}"),
                lineage_id=f.get("lineage_id", f"LIN-{f['id']}"),
                institution_id=real_inst_id,
                bank_id=bank_id,
                bank_name=f["bank_name"],
                branch_name=f["branch_name"],
                ifsc_code=f["ifsc_code"],
                fdr_number=f["fdr_number"],
                amount=f["amount"],
                issue_date=date.fromisoformat(f["issue_date"]),
                maturity_date=date.fromisoformat(f["maturity_date"]),
                tenure_months=f["tenure_months"],
                interest_rate=7.20,
                auto_renewal=True,
                status=FDRStatus(f["status"]),
                review_priority_score=score,
                review_priority_level=review_level,
                review_flags=[
                    {
                        "code": f"FLAG-{iss.upper()}",
                        "severity": "CRITICAL" if iss in ["duplicate_fdr_number_cross_institution", "same_file_reused"] else "HIGH",
                        "title": iss.replace("_", " ").title(),
                        "reason": f"Ground-truth injected anomaly: {iss}",
                        "evidence": f"Found in synthetic test instrument #{f['fdr_number']}",
                        "rule_reference": f"APH-RULE-{iss.upper()[:10]}"
                    } for iss in issues
                ],
                predecessor_fdr_id=fdr_id_map.get(f.get("predecessor_fdr_id"))
            )
            db.add(fdr_rec)
            db.commit()
            db.refresh(fdr_rec)
            fdr_id_map[f["id"]] = fdr_rec.id

            # Mirror primary document to storage/
            fdr_storage_dir = os.path.join(settings.STORAGE_DIR, f"fdr_{fdr_rec.id}")
            os.makedirs(fdr_storage_dir, exist_ok=True)

            for d in f.get("documents", []):
                src_path = d.get("file_path")
                if src_path and os.path.exists(src_path):
                    dst_path = os.path.join(fdr_storage_dir, d["file_name"])
                    shutil.copyfile(src_path, dst_path)

                    doc_entry = FDRDocument(
                        fdr_id=fdr_rec.id,
                        version=1,
                        file_name=d["file_name"],
                        file_path=dst_path,
                        storage_path=dst_path,
                        file_hash_sha256=d.get("sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
                        perceptual_hash=d.get("phash"),
                        doc_type=d.get("doc_type", "FDR_CERTIFICATE"),
                        ocr_status="COMPLETED"
                    )
                    db.add(doc_entry)

            # Initialize 4-level Provenance
            has_mismatch = ("maturity_mismatch_with_bank_letter" in issues or "amount_edited" in issues)
            prov_mappings = [
                ("fdr_number", f["fdr_number"], f["fdr_number"], f["fdr_number"], ProvenanceLevel.BANK_CONFIRMED),
                ("amount", str(f["amount"]), str(f["amount"]), str(f["amount"]), ProvenanceLevel.MISMATCH if "amount_edited" in issues else ProvenanceLevel.BANK_CONFIRMED),
                ("maturity_date", f["maturity_date"], f["maturity_date"], f["maturity_date"], ProvenanceLevel.MISMATCH if "maturity_mismatch_with_bank_letter" in issues else ProvenanceLevel.BANK_CONFIRMED),
                ("bank_name", f["bank_name"], f["bank_name"], f["bank_name"], ProvenanceLevel.BANK_CONFIRMED),
                ("ifsc_code", f["ifsc_code"], f["ifsc_code"], f["ifsc_code"], ProvenanceLevel.BANK_CONFIRMED)
            ]
            for fname, sval, aival, bval, st in prov_mappings:
                db.add(FieldProvenance(
                    fdr_id=fdr_rec.id,
                    field_name=fname,
                    submitted_value=sval,
                    ai_extracted_value=aival,
                    bank_confirmed_value=bval,
                    status=st,
                    ai_confidence=0.96,
                    mismatch_reason="Discrepancy identified between FDR certificate and bank confirmation record." if st == ProvenanceLevel.MISMATCH else None
                ))

            # Add Simulated Bank Verification Record
            db.add(BankVerificationRecord(
                fdr_id=fdr_rec.id,
                adapter_used="SIMULATED_SFMS",
                verification_status=BankVerificationStatus.NOT_CONFIRMED if "wrong_bank_name" in issues else BankVerificationStatus.AVAILABLE_CHECKS_PASSED,
                api_reference_id=f"SIM-CBS-{fdr_rec.id:06d}",
                watermark_notice="SIMULATED, not a real bank verification",
                remarks="Simulated response from mock core banking adapter."
            ))

    db.commit()

    # 5. Initialize Demo Clock
    clock = db.query(DemoClock).filter(DemoClock.id == 1).first()
    if not clock:
        db.add(DemoClock(id=1, current_simulated_date=date(2026, 11, 29), offset_days=0))
        db.commit()

    # 6. Record Genesis and Batch Load in Hash Chained Ledger
    record_audit_event(
        db=db,
        event_type="SYNTHETIC_DATASET_LOADED",
        entity_type="SYSTEM",
        entity_id="PHASE2_LOADER",
        actor_id=1,
        actor_role="SYSTEM_ADMIN",
        payload={
            "total_institutions": len(gt["institutions"]),
            "total_fdrs": len(gt["fdrs"]),
            "clean_count": gt["summary"]["clean_fdrs_count"],
            "anomalous_count": gt["summary"]["anomalous_fdrs_count"]
        }
    )

    print(f"Successfully seeded database with {len(gt['institutions'])} institutions and {len(gt['fdrs'])} FDRs!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        load_synthetic_data_into_db(db)
    finally:
        db.close()

