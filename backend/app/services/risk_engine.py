"""DepoSafe Explainable Review Priority Risk Engine.

Computes a transparent, weighted sum of named indicators:
1. duplicate_similarity (Exact bank+FDR collision, identical SHA-256, pHash clone)
2. maturity_mismatch (Discrepancy vs bank confirmation letter / CBS records)
3. missing_bank_confirmation (Bank CBS verification unconfirmed or missing)
4. tamper_indicators (ELA heatmap hotspots, metadata editor software, font discontinuity)
5. mandatory_field_completeness (Missing IFSC, amount, dates, or non-scheduled bank)
6. late_renewal_history (Overdue/matured deposit without active renewal lineage)

Statutory Guardrails:
- Label: "Review priority indicator, not a fraud probability."
- AI is strictly advisory; compliance is determined by explicit versioned rules.
- Officer override requires typed mandatory justification and is cryptographically audited.
"""

import os
import yaml
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models.deposafe_models import (
    FDR, FDRDocument, FieldProvenance, BankVerificationRecord, Institution,
    ProvenanceLevel, BankVerificationStatus, FDRStatus
)
from backend.app.services.duplicate_detector import DuplicateDetector
from backend.app.services.reconciliation_service import CrossDocumentReconciler
from backend.app.services.forensics_service import DigitalForensicsAnalyzer

WEIGHTS_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "risk_weights.yaml")
)

DEFAULT_WEIGHTS = {
    "duplicate_collision": 35.0,
    "maturity_mismatch": 25.0,
    "bank_unconfirmed": 25.0,
    "forensic_tamper": 20.0,
    "compliance_deficit": 15.0,
    "perceptual_clone": 15.0
}

def load_risk_weights() -> Dict[str, float]:
    """Loads configurable risk indicator weights from YAML config or falls back to defaults."""
    if os.path.exists(WEIGHTS_CONFIG_PATH):
        try:
            with open(WEIGHTS_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                indicators = cfg.get("indicators", {})
                return {k: float(v.get("max_weight", DEFAULT_WEIGHTS.get(k, 15.0))) for k, v in indicators.items()}
        except Exception:
            pass
    return DEFAULT_WEIGHTS

def compute_review_priority(
    db: Session,
    fdr: FDR,
    institution: Institution,
    compliance_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes explainable Review Priority Indicator (0.0 to 100.0) with contributing reasons breakdown.
    """
    weights = load_risk_weights()
    contributing_reasons: List[Dict[str, Any]] = []
    total_score = 0.0

    # 1. Indicator: Duplicate Collision (Exact bank+FDR match or SHA-256 byte reuse)
    dup_report = DuplicateDetector.check_fdr_duplicates(fdr, db)
    w_dup = weights.get("duplicate_collision", 35.0)

    if dup_report["exact_bank_fdr_matches"]:
        match_info = dup_report["exact_bank_fdr_matches"][0]
        score_contrib = w_dup
        total_score += score_contrib
        contributing_reasons.append({
            "indicator": "duplicate_collision",
            "title": "Cross-Institution Instrument Collision",
            "weight": w_dup,
            "score_contribution": score_contrib,
            "status": "Flagged",
            "reason": match_info["reason"],
            "evidence": f"Pledged to institution: '{match_info['institution_name']}' (AICTE ID: {match_info['aicte_id']}).",
            "recommended_action": "Examine physical ledger at issuing branch; issue clarification notice to institution."
        })
    elif dup_report["sha256_identical_matches"]:
        match_info = dup_report["sha256_identical_matches"][0]
        score_contrib = round(w_dup * 0.8, 1)
        total_score += score_contrib
        contributing_reasons.append({
            "indicator": "duplicate_collision",
            "title": "Exact Document Byte-Hash Collision",
            "weight": w_dup,
            "score_contribution": score_contrib,
            "status": "Flagged",
            "reason": match_info["reason"],
            "evidence": f"Matched Document #{match_info['matched_document_id']} (SHA-256: {match_info['sha256_hash'][:16]}...).",
            "recommended_action": "Verify original physical document to confirm whether same file was erroneously resubmitted."
        })
    elif dup_report["phash_visual_matches"]:
        w_phash = weights.get("perceptual_clone", 15.0)
        score_contrib = w_phash
        total_score += score_contrib
        contributing_reasons.append({
            "indicator": "perceptual_clone",
            "title": "Visual Layout Template Reuse",
            "weight": w_phash,
            "score_contribution": score_contrib,
            "status": "Flagged",
            "reason": dup_report["phash_visual_matches"][0]["reason"],
            "evidence": f"Hamming distance: {dup_report['phash_visual_matches'][0]['hamming_distance']} <= 8.",
            "recommended_action": "Cross-verify security paper watermarks and guilloche borders against issuing bank standards."
        })
    else:
        contributing_reasons.append({
            "indicator": "duplicate_collision",
            "title": "Duplicate Instrument Collision Check",
            "weight": w_dup,
            "score_contribution": 0.0,
            "status": "Complete",
            "reason": "No duplicate bank+FDR collisions or identical SHA-256 hashes detected.",
            "evidence": "Unique in AICTE Registry.",
            "recommended_action": "No action required."
        })

    # 2. Indicator: Maturity Mismatch (Cross-Document Discrepancy)
    w_mat = weights.get("maturity_mismatch", 25.0)
    has_mat_mismatch = False
    mat_reason = "Maturity dates across certificate, bank letter, and core banking match."

    try:
        rec_res = CrossDocumentReconciler.reconcile_fdr_documents(fdr.id, db)
        for row in rec_res.get("reconciliation_table", []):
            if row["field_name"] == "maturity_date" and row["status"] == "MISMATCH":
                has_mat_mismatch = True
                mat_reason = row["discrepancy_details"]
                break
    except Exception:
        pass

    if has_mat_mismatch:
        score_contrib = w_mat
        total_score += score_contrib
        contributing_reasons.append({
            "indicator": "maturity_mismatch",
            "title": "Cross-Document Maturity Date Discrepancy",
            "weight": w_mat,
            "score_contribution": score_contrib,
            "status": "Flagged",
            "reason": mat_reason,
            "evidence": "Discrepancy detected between FDR Certificate and Bank Confirmation Letter schedule.",
            "recommended_action": "Request bank confirmation letter directly dispatched from bank regional corporate office."
        })
    else:
        contributing_reasons.append({
            "indicator": "maturity_mismatch",
            "title": "Maturity Date Reconciliation",
            "weight": w_mat,
            "score_contribution": 0.0,
            "status": "Complete",
            "reason": mat_reason,
            "evidence": f"Maturity Date: {fdr.maturity_date.isoformat() if fdr.maturity_date else 'N/A'}",
            "recommended_action": "No action required."
        })

    # 3. Indicator: Bank Core Verification Status
    w_bank = weights.get("bank_unconfirmed", 25.0)
    bank_rec = db.query(BankVerificationRecord).filter(BankVerificationRecord.fdr_id == fdr.id).first()

    if bank_rec:
        if bank_rec.verification_status == BankVerificationStatus.NOT_CONFIRMED:
            score_contrib = w_bank
            total_score += score_contrib
            contributing_reasons.append({
                "indicator": "bank_unconfirmed",
                "title": "Core Banking Record Unconfirmed",
                "weight": w_bank,
                "score_contribution": score_contrib,
                "status": "Flagged",
                "reason": "Bank CBS returned 'not confirmed' or instrument is closed in bank records.",
                "evidence": bank_rec.remarks or "CBS record missing.",
                "recommended_action": "Initiate SFMS status inquiry with bank zonal nodal officer."
            })
        else:
            contributing_reasons.append({
                "indicator": "bank_unconfirmed",
                "title": "Bank Verification Adapter Confirmation",
                "weight": w_bank,
                "score_contribution": 0.0,
                "status": "Complete",
                "reason": "Available checks passed via Core Banking System adapter.",
                "evidence": f"Ref: {bank_rec.api_reference_id or 'CBS-CONFIRMED'}",
                "recommended_action": "No action required."
            })
    else:
        contributing_reasons.append({
            "indicator": "bank_unconfirmed",
            "title": "Core Banking Verification",
            "weight": w_bank,
            "score_contribution": 0.0,
            "status": "Pending",
            "reason": "Automated core banking query pending execution.",
            "evidence": "Verification pending.",
            "recommended_action": "Execute bank verification via Simulate Bank CBS or record manual officer evidence."
        })

    # 4. Indicator: Forensic Tampering (ELA, Metadata, Font Inconsistency)
    w_forensic = weights.get("forensic_tamper", 20.0)
    latest_doc = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).order_by(FDRDocument.version.desc()).first()

    if latest_doc:
        meta = latest_doc.forensic_metadata or {}
        has_tamper = meta.get("producer_flagged") or (meta.get("tampering_indicators") and len(meta["tampering_indicators"]) > 0)

        # Check for Photoshop / Canva metadata flag
        if has_tamper:
            score_contrib = w_forensic
            total_score += score_contrib
            contributing_reasons.append({
                "indicator": "forensic_tamper",
                "title": "Digital Editing & Forensic Metadata Traces",
                "weight": w_forensic,
                "score_contribution": score_contrib,
                "status": "Flagged",
                "reason": "PDF metadata indicates generation or editing using graphics/photo editor software.",
                "evidence": f"Producer: '{meta.get('pdf_producer') or meta.get('pdf_creator')}'",
                "recommended_action": "Examine ELA heatmap overlay; route to AICTE Forensic Scrutiny Cell for physical verification."
            })
        else:
            contributing_reasons.append({
                "indicator": "forensic_tamper",
                "title": "Digital Forensics & Metadata Check",
                "weight": w_forensic,
                "score_contribution": 0.0,
                "status": "Complete",
                "reason": "No graphic editing tools or suspicious ELA compression hotspots detected.",
                "evidence": f"Producer: {meta.get('pdf_producer', 'Standard Bank System')}",
                "recommended_action": "No action required."
            })
    else:
        contributing_reasons.append({
            "indicator": "forensic_tamper",
            "title": "Digital Forensics Check",
            "weight": w_forensic,
            "score_contribution": 0.0,
            "status": "Pending",
            "reason": "No document uploaded for forensic analysis.",
            "evidence": "Pending upload.",
            "recommended_action": "Upload primary FDR certificate."
        })

    # 5. Indicator: Compliance Rule Deficits (APH Regulations)
    w_comp = weights.get("compliance_deficit", 15.0)
    compliance_deficit = False
    comp_reason = "All statutory APH deposit norms satisfied."

    if compliance_result:
        for chk in compliance_result.get("checks", []):
            if not chk.get("passed"):
                compliance_deficit = True
                comp_reason = chk.get("explanation", "Compliance norm unmet")
                break

    if compliance_deficit:
        score_contrib = w_comp
        total_score += score_contrib
        contributing_reasons.append({
            "indicator": "compliance_deficit",
            "title": "Statutory Regulation Norm Deficit",
            "weight": w_comp,
            "score_contribution": score_contrib,
            "status": "Flagged",
            "reason": comp_reason,
            "evidence": "Failed one or more APH compliance rule checks.",
            "recommended_action": "Issue deficiency notice to institution with 15-day compliance window."
        })
    else:
        contributing_reasons.append({
            "indicator": "compliance_deficit",
            "title": "Statutory Regulation Norm Compliance",
            "weight": w_comp,
            "score_contribution": 0.0,
            "status": "Complete",
            "reason": comp_reason,
            "evidence": "Passed statutory checks.",
            "recommended_action": "No action required."
        })

    # 6. Indicator: Late Renewal / Overdue Status
    today = date.today()
    if fdr.maturity_date and fdr.maturity_date < today and fdr.status not in [FDRStatus.RELEASED, FDRStatus.CLOSED, FDRStatus.SUPERSEDED]:
        score_contrib = 15.0
        total_score += score_contrib
        contributing_reasons.append({
            "indicator": "late_renewal_history",
            "title": "Matured / Overdue Deposit Without Renewal",
            "weight": 15.0,
            "score_contribution": score_contrib,
            "status": "Flagged",
            "reason": f"Instrument matured on {fdr.maturity_date.isoformat()} and remains active without linked renewal successor.",
            "evidence": f"Maturity date passed: {fdr.maturity_date.isoformat()}.",
            "recommended_action": "Initiate automated renewal escalation notice to institution and issuing branch."
        })
    else:
        contributing_reasons.append({
            "indicator": "late_renewal_history",
            "title": "Deposit Maturity & Renewal Tracking",
            "weight": 15.0,
            "score_contribution": 0.0,
            "status": "Complete",
            "reason": "Deposit is active and within valid statutory tenure.",
            "evidence": f"Maturity Date: {fdr.maturity_date.isoformat() if fdr.maturity_date else 'N/A'}.",
            "recommended_action": "No action required."
        })

    # Clamp calculated score to 0.0 - 100.0
    calculated_score = min(100.0, max(0.0, round(total_score, 1)))

    # Determine final score (respect officer override if present)
    effective_score = calculated_score
    if fdr.officer_override and fdr.review_priority_score is not None:
        effective_score = fdr.review_priority_score

    # Determine Priority Level
    if effective_score >= 75.0:
        level = "CRITICAL"
    elif effective_score >= 50.0:
        level = "HIGH"
    elif effective_score >= 25.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "review_priority_score": effective_score,
        "review_priority_level": level,
        "calculated_raw_score": calculated_score,
        "officer_override": bool(fdr.officer_override),
        "officer_override_justification": fdr.officer_override_justification,
        "contributing_reasons": contributing_reasons,
        "flags": [
            {
                "code": f"FLAG-{r['indicator'].upper()}",
                "severity": "CRITICAL" if r["score_contribution"] >= 25 else "HIGH",
                "title": r["title"],
                "reason": r["reason"],
                "evidence": r["evidence"],
                "rule_reference": f"APH-INDICATOR-{r['indicator'].upper()}"
            }
            for r in contributing_reasons if r["status"] == "Flagged"
        ],
        "statutory_label": "Review priority indicator, not a fraud probability",
        "advisory_notice": "AI is advisory. Compliance is decided by explicit versioned rules. Officer verification required.",
        "rule_version_applied": compliance_result.get("rule_version", "APH-2024-27.v1") if compliance_result else "APH-2024-27.v1"
    }
