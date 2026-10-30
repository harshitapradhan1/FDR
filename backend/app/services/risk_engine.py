from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import FDR, FDRDocument, FieldProvenance, BankVerificationRecord, Institution, ProvenanceLevel, BankVerificationStatus

def compute_review_priority(
    db: Session,
    fdr: FDR,
    institution: Institution,
    compliance_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes explainable 'Review Priority Indicator' (0.0 to 100.0).
    AI is strictly advisory; compliance is determined by versioned rules.
    Wording: 'review priority indicator', never 'fraud probability'.
    """
    score = 0.0
    flags: List[Dict[str, Any]] = []

    # 1. Duplicate FDR Number Check across other institutions
    duplicate_fdr = db.query(FDR).filter(
        FDR.fdr_number == fdr.fdr_number,
        FDR.bank_name == fdr.bank_name,
        FDR.institution_id != fdr.institution_id,
        FDR.id != fdr.id
    ).first()
    if duplicate_fdr:
        other_inst = db.query(Institution).filter(Institution.id == duplicate_fdr.institution_id).first()
        score += 40.0
        flags.append({
            "code": "FLAG-CROSS-INST-FDR-DUP",
            "severity": "CRITICAL",
            "title": "Cross-Institution Instrument Number Collision",
            "reason": f"FDR number '{fdr.fdr_number}' at '{fdr.bank_name}' is already recorded by another institution.",
            "evidence": f"Pledged to institution: '{other_inst.name if other_inst else 'ID ' + str(duplicate_fdr.institution_id)}' (AICTE ID: {other_inst.aicte_id if other_inst else 'N/A'}).",
            "rule_reference": "APH-2024-DUPLICATE-PREVENTION"
        })

    # 2. Perceptual Image Hash & SHA256 Collision Check
    latest_doc = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.desc()).first()
    if latest_doc:
        # Check identical SHA256 in different FDR
        sha_dup = db.query(FDRDocument).filter(
            FDRDocument.file_hash_sha256 == latest_doc.file_hash_sha256,
            FDRDocument.fdr_id != fdr.id
        ).first()
        if sha_dup:
            score += 35.0
            flags.append({
                "code": "FLAG-DOC-SHA256-COLLISION",
                "severity": "HIGH",
                "title": "Exact Document Byte-Hash Collision",
                "reason": "The exact same document file was uploaded for a different deposit record.",
                "evidence": f"Matched previous document ID #{sha_dup.id} (SHA256: {latest_doc.file_hash_sha256[:16]}...).",
                "rule_reference": "DOC-INTEGRITY-01"
            })
            
        # Check perceptual hash collision
        if latest_doc.perceptual_hash:
            phash_dups = db.query(FDRDocument).filter(
                FDRDocument.perceptual_hash == latest_doc.perceptual_hash,
                FDRDocument.fdr_id != fdr.id
            ).all()
            if phash_dups and not sha_dup:
                score += 25.0
                flags.append({
                    "code": "FLAG-DOC-PHASH-TEMPLATE-REUSE",
                    "severity": "MEDIUM",
                    "title": "Visual Template Structure Collision",
                    "reason": "Perceptual image hash matches another document, indicating visual clone or reused certificate template.",
                    "evidence": f"Perceptual hash {latest_doc.perceptual_hash} matches {len(phash_dups)} other document(s).",
                    "rule_reference": "DOC-INTEGRITY-PHASH"
                })

        # Check metadata tampering flags
        metadata = latest_doc.forensic_metadata or {}
        if metadata.get("producer_flagged"):
            score += 30.0
            flags.append({
                "code": "FLAG-METADATA-EDIT-TOOL",
                "severity": "HIGH",
                "title": "Document Editing Software Signature",
                "reason": "PDF metadata indicates generation or modification using graphic/photo editing software.",
                "evidence": f"Detected: {metadata.get('pdf_producer') or metadata.get('pdf_creator')}",
                "rule_reference": "FORENSIC-META-02"
            })

    # 3. Compliance Rule Deficits
    for check in compliance_result.get("checks", []):
        if not check.get("passed"):
            if check["rule_id"] == "APH-RULE-AMT-02":
                score += 25.0
                flags.append({
                    "code": "FLAG-DEPOSIT-DEFICIT",
                    "severity": "HIGH",
                    "title": "Deposit Norm Deficit",
                    "reason": check["explanation"],
                    "evidence": f"Required: {check['required']}, Submitted: {check['observed']}",
                    "rule_reference": check["rule_id"]
                })
            elif check["rule_id"] == "APH-RULE-LIEN-04":
                score += 20.0
                flags.append({
                    "code": "FLAG-LIEN-CLAUSE-MISSING",
                    "severity": "HIGH",
                    "title": "AICTE Lien Clause Non-Compliance",
                    "reason": check["explanation"],
                    "evidence": check["observed"],
                    "rule_reference": check["rule_id"]
                })
            elif check["rule_id"] == "APH-RULE-BANK-01":
                score += 25.0
                flags.append({
                    "code": "FLAG-NON-SCHEDULED-BANK",
                    "severity": "HIGH",
                    "title": "Non-Scheduled Financial Institution",
                    "reason": check["explanation"],
                    "evidence": check["observed"],
                    "rule_reference": check["rule_id"]
                })
            elif check["rule_id"] == "APH-RULE-TENURE-03":
                score += 15.0
                flags.append({
                    "code": "FLAG-INSUFFICIENT-TENURE",
                    "severity": "MEDIUM",
                    "title": "Tenure Shorter Than Regulation Norm",
                    "reason": check["explanation"],
                    "evidence": check["observed"],
                    "rule_reference": check["rule_id"]
                })

    # 4. Field Provenance Mismatches
    mismatches = db.query(FieldProvenance).filter(
        FieldProvenance.fdr_id == fdr.id,
        FieldProvenance.status == ProvenanceLevel.MISMATCH
    ).all()
    for mm in mismatches:
        score += 15.0
        flags.append({
            "code": f"FLAG-MISMATCH-{mm.field_name.upper()}",
            "severity": "MEDIUM",
            "title": f"Field Mismatch on '{mm.field_name}'",
            "reason": mm.mismatch_reason or f"Discrepancy detected across provenance stages for {mm.field_name}.",
            "evidence": f"Submitted: '{mm.submitted_value}', AI: '{mm.ai_extracted_value}', Bank: '{mm.bank_confirmed_value}'",
            "rule_reference": "PROVENANCE-EVAL-01"
        })

    # 5. Bank Verification Status Check
    bank_rec = db.query(BankVerificationRecord).filter(BankVerificationRecord.fdr_id == fdr.id).first()
    if bank_rec and bank_rec.verification_status == BankVerificationStatus.NOT_CONFIRMED:
        score += 35.0
        flags.append({
            "code": "FLAG-BANK-NOT-CONFIRMED",
            "severity": "CRITICAL",
            "title": "Bank Verification Returned 'Not Confirmed'",
            "reason": "Bank record verification did not confirm the active deposit status.",
            "evidence": bank_rec.remarks or "CBS record missing or failed match.",
            "rule_reference": "BANK-VERIF-CBS"
        })

    # Clamp score to 100
    final_score = min(round(score, 1), 100.0)

    if final_score >= 80.0:
        level = "CRITICAL"
    elif final_score >= 50.0:
        level = "HIGH"
    elif final_score >= 25.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "review_priority_score": final_score,
        "review_priority_level": level,
        "flags": flags,
        "advisory_notice": "AI is advisory. Compliance is decided by explicit versioned rules. Officer verification required.",
        "rule_version_applied": compliance_result.get("rule_version", "APH-2024-27.v1")
    }

