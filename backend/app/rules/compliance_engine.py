"""DepoSafe Deterministic Compliance Engine Adapter.
Preserves backwards compatibility with existing codebase callers while bridging
to the full Phase 7 versioned deterministic engine.
"""

from typing import Dict, Any, List, Optional
from datetime import date
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import ComplianceRule, FDR, Institution
from backend.app.services.compliance_service import (
    get_active_rule as get_active_rule_service,
    evaluate_fdr_compliance_versioned,
    calculate_required_fdr_amount,
    DEFAULT_DISCLAIMER_EN,
    DEFAULT_DISCLAIMER_HI
)

DEFAULT_RULE_TAG = "APH-2024-27.v1"

def get_active_rule(db: Session) -> ComplianceRule:
    return get_active_rule_service(db)

def evaluate_fdr_compliance(fdr: FDR, institution: Institution, rules_record: ComplianceRule) -> Dict[str, Any]:
    """
    Evaluates an FDR against the versioned rules record.
    Returns legacy-compatible and Phase 7 enriched dictionary.
    """
    from backend.app.core.database import SessionLocal
    # Create or use session if possible
    db = SessionLocal()
    try:
        eval_result = evaluate_fdr_compliance_versioned(
            fdr=fdr,
            institution=institution,
            rule_record=rules_record,
            db=db,
            save_result=False
        )
    finally:
        db.close()

    legacy_checks = []
    for c in eval_result["checks"]:
        legacy_checks.append({
            "rule_id": c["rule_id"],
            "name": c["name"],
            "required": str(c["expected_value"]),
            "observed": str(c["observed_value"]),
            "passed": (c["outcome"] == "COMPLIANT"),
            "explanation": c["explanation_en"]
        })

    return {
        "rule_version": eval_result["rule_version_used"],
        "disclaimer": DEFAULT_DISCLAIMER_EN,
        "statutory_disclaimer_hi": DEFAULT_DISCLAIMER_HI,
        "evaluation_status": "AVAILABLE_CHECKS_PASSED" if eval_result["overall_passed"] else "NON_COMPLIANT",
        "overall_passed": eval_result["overall_passed"],
        "overall_outcome": eval_result["overall_outcome"],
        "compliance_score": eval_result["compliance_score"],
        "checks": legacy_checks,
        "checks_versioned": eval_result["checks"],
        "required_amount": eval_result["checks"][0]["expected_value"] if eval_result["checks"] else 2000000.0,
        "observed_amount": fdr.amount
    }
