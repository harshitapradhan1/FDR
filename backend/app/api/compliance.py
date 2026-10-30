"""DepoSafe Deterministic Compliance API Routes.

Features:
1. Versioned Rule Lifecycle: List active and historical versions, fetch rule details with diff.
2. Rule Editor: Admin draft rule creation and validation.
3. Dry-Run Impact Simulator: Simulates a candidate rule version across all active deposits and produces an Impact Report.
4. Safe Publishing Flow: Publishes new version, records audit trail, runs re-evaluation while preserving historical decisions.
5. Compliance Scoring: Per-instrument and per-institution compliance scores and breakdown.
6. Statutory Disclaimers: Clear UI labeling in EN + HI on all rule data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Dict, Any, List, Optional
import yaml
import os

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_role
from backend.app.models.deposafe_models import User, UserRole, ComplianceRule, ComplianceResult, FDR, Institution, FDRStatus
from backend.app.services.compliance_service import (
    get_active_rule, evaluate_fdr_compliance_versioned, run_dry_run_impact_report,
    compute_institution_compliance_score, load_rule_from_yaml, RULES_CONFIG_DIR,
    DEFAULT_DISCLAIMER_EN, DEFAULT_DISCLAIMER_HI
)
from backend.app.schemas.compliance_schemas import (
    ComplianceRuleCreateRequest, ComplianceRulePublishRequest,
    DryRunImpactRequest, InstrumentComplianceEvaluation, InstitutionComplianceScore
)
from backend.app.services.audit_service import record_audit_event

router = APIRouter(prefix="/compliance", tags=["Compliance & Regulations"])


# --------------------------------------------------------------------------
# 1. Active & Historical Rule Versions
# --------------------------------------------------------------------------
@router.get("/rules/active")
def get_active_compliance_rules(db: Session = Depends(get_db)):
    """Returns currently active compliance rules with full bilingual explanations and disclaimers."""
    rule = get_active_rule(db)
    return {
        "version_tag": rule.version_tag,
        "effective_from": rule.effective_from.isoformat(),
        "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
        "is_active": rule.is_active,
        "description": rule.description,
        "disclaimer": DEFAULT_DISCLAIMER_EN,
        "disclaimer_hi": DEFAULT_DISCLAIMER_HI,
        "rules_definition": rule.rules_json
    }


@router.get("/rules/history")
def get_compliance_rules_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns list of all registered rule versions with author and active status."""
    rules = db.query(ComplianceRule).order_by(ComplianceRule.id.desc()).all()
    return {
        "total_versions": len(rules),
        "versions": [
            {
                "id": r.id,
                "version_tag": r.version_tag,
                "effective_from": r.effective_from.isoformat(),
                "effective_to": r.effective_to.isoformat() if r.effective_to else None,
                "is_active": r.is_active,
                "description": r.description,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "created_by": r.created_by
            }
            for r in rules
        ],
        "statutory_label": DEFAULT_DISCLAIMER_EN
    }


@router.get("/rules/version/{version_tag}")
def get_rule_by_version(
    version_tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches exact definition of a specific version tag."""
    rule = db.query(ComplianceRule).filter(ComplianceRule.version_tag == version_tag).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule version '{version_tag}' not found.")
    return {
        "id": rule.id,
        "version_tag": rule.version_tag,
        "effective_from": rule.effective_from.isoformat(),
        "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
        "is_active": rule.is_active,
        "description": rule.description,
        "rules_json": rule.rules_json,
        "disclaimer": DEFAULT_DISCLAIMER_EN
    }


@router.get("/rules/diff")
def diff_rule_versions(
    v1: str = Query(..., description="Base rule version tag (e.g. APH-2024-27.v1)"),
    v2: str = Query(..., description="Target rule version tag (e.g. APH-2025-26.v2)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compares two rule versions field-by-field and returns structural differences."""
    r1 = db.query(ComplianceRule).filter(ComplianceRule.version_tag == v1).first()
    r2 = db.query(ComplianceRule).filter(ComplianceRule.version_tag == v2).first()

    # Fallback to local files if not in database
    json1 = r1.rules_json if r1 else None
    json2 = r2.rules_json if r2 else None

    if not json1:
        yaml1_path = os.path.join(RULES_CONFIG_DIR, f"{v1.lower().replace('.', '_').replace('-', '_')}.yaml")
        if os.path.exists(yaml1_path):
            json1 = load_rule_from_yaml(yaml1_path)
    if not json2:
        yaml2_path = os.path.join(RULES_CONFIG_DIR, f"{v2.lower().replace('.', '_').replace('-', '_')}.yaml")
        if os.path.exists(yaml2_path):
            json2 = load_rule_from_yaml(yaml2_path)

    if not json1 or not json2:
        raise HTTPException(status_code=404, detail="One or both rule versions not found for diff comparison.")

    r1_rules = {r["rule_id"]: r for r in json1.get("rules", [])}
    r2_rules = {r["rule_id"]: r for r in json2.get("rules", [])}

    all_rule_ids = sorted(list(set(r1_rules.keys()).union(r2_rules.keys())))
    differences = []

    for rid in all_rule_ids:
        in_v1 = rid in r1_rules
        in_v2 = rid in r2_rules

        if in_v1 and not in_v2:
            differences.append({
                "rule_id": rid,
                "change_type": "REMOVED",
                "v1_definition": r1_rules[rid],
                "v2_definition": None
            })
        elif in_v2 and not in_v1:
            differences.append({
                "rule_id": rid,
                "change_type": "ADDED",
                "v1_definition": None,
                "v2_definition": r2_rules[rid]
            })
        else:
            p1 = r1_rules[rid].get("parameters", {})
            p2 = r2_rules[rid].get("parameters", {})
            if p1 != p2:
                differences.append({
                    "rule_id": rid,
                    "change_type": "MODIFIED_PARAMETERS",
                    "v1_parameters": p1,
                    "v2_parameters": p2,
                    "description": r2_rules[rid].get("description")
                })

    return {
        "base_version": v1,
        "target_version": v2,
        "total_differences": len(differences),
        "differences": differences,
        "disclaimer": DEFAULT_DISCLAIMER_EN
    }


# --------------------------------------------------------------------------
# 2. Regulation Change Flow: Dry-Run Impact Simulator
# --------------------------------------------------------------------------
@router.post("/rules/dry-run-impact")
def dry_run_rule_impact(
    req: DryRunImpactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN, UserRole.COMPETENT_AUTHORITY]))
):
    """
    Dry-runs a proposed rule version across all active deposits in the registry:
    - Identifies affected institutions and instruments.
    - Produces IMPACT REPORT: who flips COMPLIANT -> NON_COMPLIANT with failing reasons.
    - Non-negotiable safeguard: Zero retrospective mutation to historical decisions.
    """
    candidate_data = None
    candidate_tag = req.new_rule_version_tag or "APH-PROPOSED-SIMULATION"

    if req.target_rule_file:
        file_p = os.path.join(RULES_CONFIG_DIR, req.target_rule_file)
        if os.path.exists(file_p):
            candidate_data = load_rule_from_yaml(file_p)
            candidate_tag = candidate_data.get("version_tag", candidate_tag)

    if not candidate_data and req.candidate_rules:
        candidate_data = {
            "version_tag": candidate_tag,
            "description": "Proposed Candidate Rules",
            "effective_from": date.today().isoformat(),
            "rules": [r.dict() for r in req.candidate_rules]
        }

    if not candidate_data:
        # Default to APH-2025-26.v2 from config/rules
        v2_path = os.path.join(RULES_CONFIG_DIR, "aph_2025_26_v2.yaml")
        if os.path.exists(v2_path):
            candidate_data = load_rule_from_yaml(v2_path)
            candidate_tag = candidate_data.get("version_tag", "APH-2025-26.v2")
        else:
            raise HTTPException(status_code=400, detail="No candidate rule definition provided for dry run.")

    impact_report = run_dry_run_impact_report(db, candidate_data, candidate_tag)
    return impact_report


# --------------------------------------------------------------------------
# 3. Rule Editor & Safe Publishing Flow
# --------------------------------------------------------------------------
@router.post("/rules/create-draft")
def create_rule_draft(
    req: ComplianceRuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN]))
):
    """
    Admin Rule Editor endpoint: creates a draft rule version (is_active=False).
    Can subsequently be simulated via dry-run and published.
    """
    existing = db.query(ComplianceRule).filter(ComplianceRule.version_tag == req.version_tag).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule version tag '{req.version_tag}' already exists.")

    rule_payload = {
        "version_tag": req.version_tag,
        "description": req.description,
        "handbook_edition": req.handbook_edition,
        "effective_from": req.effective_from.isoformat(),
        "effective_to": req.effective_to.isoformat() if req.effective_to else None,
        "disclaimer": req.disclaimer,
        "statutory_disclaimer_hi": DEFAULT_DISCLAIMER_HI,
        "rules": [r.dict() for r in req.rules]
    }

    new_rule = ComplianceRule(
        version_tag=req.version_tag,
        effective_from=req.effective_from,
        effective_to=req.effective_to,
        is_active=False, # Draft initially
        description=req.description,
        rules_json=rule_payload,
        created_by=current_user.id
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    record_audit_event(
        db=db,
        event_type="COMPLIANCE_RULE_DRAFT_CREATED",
        entity_type="COMPLIANCE_RULE",
        entity_id=str(new_rule.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "version_tag": req.version_tag,
            "rules_count": len(req.rules),
            "effective_from": req.effective_from.isoformat()
        }
    )

    return {
        "message": f"Draft compliance rule '{req.version_tag}' created successfully.",
        "rule_id": new_rule.id,
        "version_tag": new_rule.version_tag,
        "is_active": new_rule.is_active,
        "rules_count": len(req.rules)
    }


@router.post("/rules/publish")
def publish_compliance_rule(
    req: ComplianceRulePublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SYSTEM_ADMIN]))
):
    """
    Publishes a rule version as the official active regulation:
    - Sets previous active rules to inactive.
    - Sets new rule to active with effective date.
    - Runs re-evaluation for current active deposits, while PRESERVING old evaluations under their original version tag.
    - Cryptographically audit logs the gazette publication.
    """
    rule = db.query(ComplianceRule).filter(ComplianceRule.version_tag == req.version_tag).first()
    if not rule:
        # Check if exists as a yaml file in config/rules
        yaml_p = os.path.join(RULES_CONFIG_DIR, f"{req.version_tag.lower().replace('.', '_').replace('-', '_')}.yaml")
        if os.path.exists(yaml_p):
            y_data = load_rule_from_yaml(yaml_p)
            rule = ComplianceRule(
                version_tag=req.version_tag,
                effective_from=datetime.strptime(y_data.get("effective_from", "2025-06-01"), "%Y-%m-%d").date(),
                is_active=False,
                description=y_data.get("description", "Imported Rule Version"),
                rules_json=y_data,
                created_by=current_user.id
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
        else:
            raise HTTPException(status_code=404, detail=f"Rule version '{req.version_tag}' not found.")

    # Deactivate previous active rules
    prev_active = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).all()
    for pa in prev_active:
        pa.is_active = False
        if not pa.effective_to:
            pa.effective_to = date.today()

    # Activate new rule
    rule.is_active = True
    db.commit()

    # Re-evaluate all active deposits under the new rule (save_result=True writes NEW versioned result records)
    active_fdrs = db.query(FDR).filter(FDR.status != FDRStatus.CLOSED).all()
    re_evaluated_count = 0
    for f in active_fdrs:
        inst = db.query(Institution).filter(Institution.id == f.institution_id).first()
        if inst:
            evaluate_fdr_compliance_versioned(f, inst, rule, db, save_result=True)
            re_evaluated_count += 1

    record_audit_event(
        db=db,
        event_type="COMPLIANCE_RULE_PUBLISHED",
        entity_type="COMPLIANCE_RULE",
        entity_id=str(rule.id),
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        payload={
            "published_version_tag": rule.version_tag,
            "justification": req.authorized_by_justification,
            "instruments_re_evaluated": re_evaluated_count,
            "statutory_note": "Previous evaluations preserved under historic version tags."
        }
    )

    return {
        "message": f"Rule version '{rule.version_tag}' is now active.",
        "active_version": rule.version_tag,
        "effective_from": rule.effective_from.isoformat(),
        "instruments_re_evaluated": re_evaluated_count,
        "justification": req.authorized_by_justification,
        "disclaimer": DEFAULT_DISCLAIMER_EN
    }


# --------------------------------------------------------------------------
# 4. Compliance Scoring & Breakdown Endpoints
# --------------------------------------------------------------------------
@router.get("/instrument/{fdr_id}/evaluation")
def get_instrument_compliance_evaluation(
    fdr_id: int,
    version_tag: Optional[str] = Query(None, description="Optional historic rule version tag"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns granular deterministic compliance evaluation for an instrument:
    - Rule ID, rule version used, outcome (COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW / NOT_APPLICABLE).
    - Observed vs expected values, evidence references, bilingual plain explanations.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        raise HTTPException(status_code=404, detail="FDR record not found.")

    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != fdr.institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to FDR outside your institution.")

    inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()

    # Determine rule record to evaluate against
    if version_tag:
        rule = db.query(ComplianceRule).filter(ComplianceRule.version_tag == version_tag).first()
        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule version '{version_tag}' not found.")
    else:
        rule = get_active_rule(db)

    eval_result = evaluate_fdr_compliance_versioned(fdr, inst, rule, db, save_result=False)
    return eval_result


@router.get("/institution/{institution_id}/score")
def get_institution_compliance_score(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Computes aggregated compliance score (0 to 100%) and instrument breakdown for an institution.
    """
    if current_user.role == UserRole.INSTITUTION_USER and current_user.institution_id != institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to score of another institution.")

    try:
        score_data = compute_institution_compliance_score(db, institution_id)
        return score_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
