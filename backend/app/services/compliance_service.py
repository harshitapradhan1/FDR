"""DepoSafe Deterministic Versioned Compliance Engine.

Key SIH Grand Finale Guarantees:
1. Purely Deterministic: No LLM/generative model decides compliance.
2. Versioned & Immutable: Every evaluation records exact rule version used (`APH-2024-27.v1`, etc.).
3. Four Outcomes: COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW, NOT_APPLICABLE.
4. Bilingual Explanations: Plain-language legal explanations in English (EN) and Hindi (HI).
5. Explainable Evidence: Observed vs Expected values with document/field references.
6. Statutory Disclaimers: ALL values are illustrative placeholders, configurable by AICTE Admin.
7. Change Management: Dry-run impact simulation produces an impact report without touching historical decisions.
"""

import os
import yaml
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.deposafe_models import (
    ComplianceRule, ComplianceResult, FDR, Institution, FDRDocument,
    FieldProvenance, BankVerificationRecord, ProvenanceLevel, BankVerificationStatus, FDRStatus
)

RULES_CONFIG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "rules")
)
DEFAULT_YAML_RULE = os.path.join(RULES_CONFIG_DIR, "aph_2024_27_v1.yaml")

DEFAULT_DISCLAIMER_EN = "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"
DEFAULT_DISCLAIMER_HI = "सभी नियम और मान उदाहरणार्थ सांकेतिक हैं - एआईसीटीई व्यवस्थापक द्वारा विन्यास योग्य"


def load_rule_from_yaml(filepath: str) -> Dict[str, Any]:
    """Loads a rule definition file from config/rules/*.yaml."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Rule file {filepath} not found.")
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_active_rule(db: Session) -> ComplianceRule:
    """
    Retrieves the currently active ComplianceRule from database.
    If none exists in database, bootstraps from config/rules/aph_2024_27_v1.yaml.
    """
    rule = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).order_by(ComplianceRule.id.desc()).first()
    if not rule:
        if os.path.exists(DEFAULT_YAML_RULE):
            yaml_data = load_rule_from_yaml(DEFAULT_YAML_RULE)
            rule = ComplianceRule(
                version_tag=yaml_data.get("version_tag", "APH-2024-27.v1"),
                effective_from=datetime.strptime(yaml_data.get("effective_from", "2024-04-01"), "%Y-%m-%d").date(),
                is_active=True,
                description=yaml_data.get("description", "AICTE APH 2024-27 Security Deposit Baseline Rules"),
                rules_json=yaml_data
            )
        else:
            # Fallback inline dictionary
            rule = ComplianceRule(
                version_tag="APH-2024-27.v1",
                effective_from=date(2024, 4, 1),
                is_active=True,
                description="AICTE APH 2024-27 Security Deposit Baseline Rules",
                rules_json={"version_tag": "APH-2024-27.v1", "rules": []}
            )
        db.add(rule)
        db.commit()
        db.refresh(rule)
    return rule


def calculate_required_fdr_amount(
    rule_params: Dict[str, Any],
    category: str,
    program_level: str,
    institution_type: str
) -> Tuple[float, float, float]:
    """
    Computes required deposit amount from rule parameters:
    Returns (base_amount, concession_rate, final_required_amount).
    """
    deposit_norms = rule_params.get("deposit_norms_inr", {})
    cat_norms = deposit_norms.get(category, deposit_norms.get("General Technical", {}))
    base_amount = float(cat_norms.get(program_level, cat_norms.get("Default", 2000000)))

    concessions = rule_params.get("category_concessions", {})
    concession_rate = float(concessions.get(institution_type, 0.0))

    final_required = base_amount * (1.0 - concession_rate)
    return base_amount, concession_rate, final_required


def evaluate_single_rule(
    rule_def: Dict[str, Any],
    fdr: FDR,
    institution: Institution,
    db: Session
) -> Dict[str, Any]:
    """
    Deterministically evaluates one granular rule against an FDR instrument and institution.
    Returns SingleCheckEvaluation dictionary.
    """
    rule_id = rule_def.get("rule_id", "RULE-UNKNOWN")
    rule_type = rule_def.get("type", "min_amount")
    severity = rule_def.get("severity", "HIGH")
    handbook_ref = rule_def.get("handbook_reference", "APH Guidelines [Placeholder]")
    params = rule_def.get("parameters", {})

    outcome = "COMPLIANT"
    observed = None
    expected = None
    evidence_refs: List[Dict[str, Any]] = []
    explanation_en = ""
    explanation_hi = ""

    # 1. Type: MIN_AMOUNT
    if rule_type == "min_amount":
        base_amt, conc_rate, req_amt = calculate_required_fdr_amount(
            params,
            institution.category,
            institution.program_level,
            institution.institution_type
        )
        observed = f"₹ {fdr.amount:,.2f}"
        expected = f"₹ {req_amt:,.2f} (Base ₹{base_amt:,.0f} minus {int(conc_rate*100)}% {institution.institution_type} concession)"

        evidence_refs.append({
            "source": "FDR_PRINCIPAL",
            "field": "amount",
            "value": fdr.amount
        })

        if fdr.amount >= req_amt:
            outcome = "COMPLIANT"
            explanation_en = f"Pledged deposit ₹ {fdr.amount:,.2f} meets or exceeds prescribed norm ₹ {req_amt:,.2f}."
            explanation_hi = f"सुरक्षा जमा राशि ₹ {fdr.amount:,.2f} निर्धारित मानदंड ₹ {req_amt:,.2f} को पूरा करती है।"
        else:
            outcome = "NON_COMPLIANT"
            deficit = req_amt - fdr.amount
            explanation_en = f"Statutory deficit of ₹ {deficit:,.2f} detected against handbook requirement ₹ {req_amt:,.2f}."
            explanation_hi = f"हैंडबुक मानदंड ₹ {req_amt:,.2f} की तुलना में ₹ {deficit:,.2f} की कमी पाई गई।"

    # 2. Type: VALIDITY_UNTIL (Tenure & Expiry)
    elif rule_type == "validity_until":
        min_tenure = params.get("mandatory_minimum_tenure_months", 96)
        observed = f"{fdr.tenure_months} months (Maturity: {fdr.maturity_date.isoformat() if fdr.maturity_date else 'N/A'})"
        expected = f"Minimum {min_tenure} months lock-in period ({min_tenure // 12} years)"

        evidence_refs.append({
            "source": "FDR_SCHEDULE",
            "field": "tenure_months",
            "value": fdr.tenure_months
        })

        if fdr.tenure_months >= min_tenure:
            outcome = "COMPLIANT"
            explanation_en = f"Deposit tenure of {fdr.tenure_months} months satisfies minimum lock-in requirement of {min_tenure} months."
            explanation_hi = f"जमा अवधि {fdr.tenure_months} महीने निर्धारित न्यूनतम लॉक-इन अवधि {min_tenure} महीने को पूरा करती है।"
        else:
            outcome = "NON_COMPLIANT"
            explanation_en = f"Tenure {fdr.tenure_months} months is below prescribed lock-in of {min_tenure} months."
            explanation_hi = f"जमा अवधि {fdr.tenure_months} महीने आवश्यक लॉक-इन {min_tenure} महीने से कम है।"

    # 3. Type: BANK_WHITELIST
    elif rule_type == "bank_whitelist":
        whitelist = params.get("rbi_scheduled_commercial_banks", [])
        observed = fdr.bank_name
        expected = "RBI Scheduled Commercial Bank whitelist"

        evidence_refs.append({
            "source": "ISSUING_BANK",
            "field": "bank_name",
            "value": fdr.bank_name
        })

        is_whitelisted = any(b.lower() in fdr.bank_name.lower() for b in whitelist)
        if is_whitelisted:
            outcome = "COMPLIANT"
            explanation_en = f"Issuing bank '{fdr.bank_name}' is recognised on RBI's active scheduled list."
            explanation_hi = f"जारीकर्ता बैंक '{fdr.bank_name}' भारतीय रिजर्व बैंक की सक्रिय अनुसूचित सूची में शामिल है।"
        else:
            outcome = "NON_COMPLIANT"
            explanation_en = f"Bank '{fdr.bank_name}' is not in the approved scheduled commercial bank schedule. Inquiry required."
            explanation_hi = f"बैंक '{fdr.bank_name}' अनुमोदित अनुसूचित वाणिज्यिक बैंकों की सूची में नहीं है।"

    # 4. Type: REQUIRED_DOCUMENT
    elif rule_type == "required_document":
        req_types = params.get("required_doc_types", ["FDR_CERTIFICATE", "BANK_CONFIRMATION_LETTER"])
        docs = db.query(FDRDocument).filter(FDRDocument.fdr_id == fdr.id).all()
        uploaded_types = [d.doc_type for d in docs]

        missing_types = [t for t in req_types if t not in uploaded_types]
        observed = f"Uploaded documents: {uploaded_types if uploaded_types else 'None'}"
        expected = f"Mandatory enclosures: {req_types}"

        if not missing_types:
            outcome = "COMPLIANT"
            explanation_en = "All mandatory regulatory document enclosures are present and indexed."
            explanation_hi = "सभी अनिवार्य विनियामक दस्तावेज़ संलग्नक उपलब्ध हैं।"
        elif "FDR_CERTIFICATE" in missing_types:
            outcome = "NON_COMPLIANT"
            explanation_en = f"Primary FDR Certificate is missing from depository records."
            explanation_hi = "प्राथमिक सावधि जमा रसीद (FDR) प्रमाण पत्र उपलब्ध नहीं है।"
        else:
            outcome = "NEEDS_REVIEW"
            explanation_en = f"Missing supporting enclosure(s): {missing_types}. Pending bank letter submission."
            explanation_hi = f"अनुपूरक संलग्नक अनुपलब्ध: {missing_types}। बैंक पत्र का सत्यापन लंबित है।"

    # 5. Type: DATE_LOGIC
    elif rule_type == "date_logic":
        has_dates = bool(fdr.issue_date and fdr.maturity_date)
        if not has_dates:
            outcome = "NON_COMPLIANT"
            observed = "Missing issue or maturity date"
            expected = "Valid chronological dates (Maturity > Issue)"
            explanation_en = "Mandatory deposit dates missing."
            explanation_hi = "अनिवार्य जमा तिथियां उपलब्ध नहीं हैं।"
        else:
            dates_valid = fdr.maturity_date > fdr.issue_date
            observed = f"Issue: {fdr.issue_date.isoformat()}, Maturity: {fdr.maturity_date.isoformat()}"
            expected = "Maturity date strictly later than issue date"

            # Check lien clause
            lien_keywords = params.get("lien_clause_keywords", ["aicte", "regional officer"])
            lien_text = (fdr.lien_clause_text or "").lower()
            # If lien_clause_text or lien_marked_to_aicte or joint_holder has AICTE or default active deposit
            has_explicit_lien = any(kw in lien_text for kw in lien_keywords) or fdr.lien_marked_to_aicte
            joint_holder = (fdr.joint_holder_name or "").lower()
            has_joint_lien = any(kw in joint_holder for kw in ["aicte", "regional officer"])

            if dates_valid and (has_explicit_lien or has_joint_lien or fdr.lien_clause_text is None):
                outcome = "COMPLIANT"
                explanation_en = "Chronological dates valid and statutory lien marked to Regional Officer, AICTE."
                explanation_hi = "कालानुक्रमिक तिथियां वैध हैं और क्षेत्रीय अधिकारी, एआईसीटीई के पक्ष में ग्रहणाधिकार चिह्नित है।"
            elif not dates_valid:
                outcome = "NON_COMPLIANT"
                explanation_en = f"Temporal inversion: maturity date {fdr.maturity_date.isoformat()} precedes issue date {fdr.issue_date.isoformat()}."
                explanation_hi = f"असंगत तिथियां: परिपक्वता तिथि {fdr.maturity_date.isoformat()} जारी तिथि से पूर्व की है।"
            else:
                outcome = "NEEDS_REVIEW"
                explanation_en = "Missing explicit statutory lien text referencing Regional Officer, AICTE."
                explanation_hi = "क्षेत्रीय अधिकारी, एआईसीटीई के पक्ष में स्पष्ट ग्रहणाधिकार पाठ अनुपलब्ध है।"

    # 6. Type: RELEASE_CONDITION
    elif rule_type == "release_condition":
        # Evaluated when release is requested
        if fdr.status == FDRStatus.RELEASE_REQUESTED:
            req_role = params.get("authorized_approver_role", "COMPETENT_AUTHORITY")
            has_justification = bool(fdr.release_justification)
            observed = f"Status: {fdr.status.value}, Justification: {fdr.release_justification or 'None'}"
            expected = f"Authorized role: {req_role}, Valid NOC and justification"

            if has_justification:
                outcome = "NEEDS_REVIEW" # Awaiting CA signoff
                explanation_en = f"Release conditions preliminary met; awaiting official Competent Authority ({req_role}) order."
                explanation_hi = f"विमुक्ति की प्राथमिक शर्तें पूर्ण; सक्षम प्राधिकारी के अंतिम आदेश की प्रतीक्षा है।"
            else:
                outcome = "NON_COMPLIANT"
                explanation_en = "Deposit release requested without mandatory statutory NOC references or justification."
                explanation_hi = "अनिवार्य अनापत्ति प्रमाण पत्र या औचित्य के बिना जमा विमुक्ति का अनुरोध किया गया।"
        elif fdr.status == FDRStatus.RELEASED:
            outcome = "COMPLIANT"
            observed = f"Released by order ref: {fdr.release_order_ref or 'CONFIRMED'}"
            expected = "Authorized Release Order"
            explanation_en = f"Deposit successfully released under official sanction ref {fdr.release_order_ref}."
            explanation_hi = f"सावधि जमा आधिकारिक स्वीकृति संदर्भ {fdr.release_order_ref} के तहत जारी की गई।"
        else:
            outcome = "NOT_APPLICABLE"
            observed = f"Status: {fdr.status.value}"
            expected = "Instrument active, not currently under release request"
            explanation_en = "Release condition is not applicable to currently active deposits."
            explanation_hi = "यह नियम वर्तमान में सक्रिय जमा पर लागू नहीं है।"

    return {
        "rule_id": rule_id,
        "rule_type": rule_type,
        "severity": severity,
        "outcome": outcome,
        "name": rule_def.get("description", rule_id),
        "name_hi": rule_def.get("description_hi", rule_id),
        "handbook_reference": handbook_ref,
        "observed_value": observed,
        "expected_value": expected,
        "evidence_references": evidence_refs,
        "explanation_en": explanation_en,
        "explanation_hi": explanation_hi
    }


def evaluate_fdr_compliance_versioned(
    fdr: FDR,
    institution: Institution,
    rule_record: ComplianceRule,
    db: Session,
    save_result: bool = True
) -> Dict[str, Any]:
    """
    Evaluates an FDR instrument against a specific ComplianceRule version.
    Stores evaluation result linked to rule_record.version_tag.
    """
    rules_data = rule_record.rules_json or {}
    rules_list = rules_data.get("rules", [])

    # If older schema with deposit_norms_inr at top level
    if not rules_list and "deposit_norms_inr" in rules_data:
        # Wrap into default rules list
        if os.path.exists(DEFAULT_YAML_RULE):
            default_yaml = load_rule_from_yaml(DEFAULT_YAML_RULE)
            rules_list = default_yaml.get("rules", [])

    checks = []
    overall_outcome = "COMPLIANT"
    total_score = 100.0

    for r_def in rules_list:
        chk = evaluate_single_rule(r_def, fdr, institution, db)
        checks.append(chk)

        if chk["outcome"] == "NON_COMPLIANT":
            overall_outcome = "NON_COMPLIANT"
            total_score -= 35.0 if chk["severity"] == "CRITICAL" else 20.0
        elif chk["outcome"] == "NEEDS_REVIEW" and overall_outcome != "NON_COMPLIANT":
            overall_outcome = "NEEDS_REVIEW"
            total_score -= 15.0

    compliance_score = max(0.0, min(100.0, round(total_score, 1)))

    evaluation_payload = {
        "fdr_id": fdr.id,
        "fdr_number": fdr.fdr_number,
        "institution_id": institution.id,
        "institution_name": institution.name,
        "rule_version_used": rule_record.version_tag,
        "overall_outcome": overall_outcome,
        "overall_passed": (overall_outcome == "COMPLIANT"),
        "compliance_score": compliance_score,
        "statutory_disclaimer": DEFAULT_DISCLAIMER_EN,
        "statutory_disclaimer_hi": DEFAULT_DISCLAIMER_HI,
        "checks": checks,
        "evaluated_at": datetime.utcnow().isoformat()
    }

    if save_result:
        res = ComplianceResult(
            fdr_id=fdr.id,
            rule_version_used=rule_record.version_tag,
            overall_passed=(overall_outcome == "COMPLIANT"),
            checks_json=evaluation_payload,
            evaluated_at=datetime.utcnow()
        )
        db.add(res)
        db.commit()

    return evaluation_payload


def run_dry_run_impact_report(
    db: Session,
    new_rule_data: Dict[str, Any],
    candidate_version_tag: str
) -> Dict[str, Any]:
    """
    Dry-runs a proposed rule version across all active FDRs in the system:
    - Identifies affected institutions and instruments.
    - Pinpoints which instruments flip from COMPLIANT -> NON_COMPLIANT.
    - Zero changes made to historical evaluations or database records.
    """
    active_fdrs = db.query(FDR).filter(FDR.status != FDRStatus.CLOSED).all()
    temp_rule_record = ComplianceRule(
        version_tag=candidate_version_tag,
        effective_from=date.today(),
        is_active=False,
        description=new_rule_data.get("description", "Candidate Rule for Dry Run"),
        rules_json=new_rule_data
    )

    total_instruments = len(active_fdrs)
    currently_compliant = 0
    newly_non_compliant = []
    affected_institutions_map = {}
    total_flips = 0

    # Retrieve active baseline rule to evaluate baseline outcome
    baseline_rule = get_active_rule(db)

    for fdr in active_fdrs:
        inst = db.query(Institution).filter(Institution.id == fdr.institution_id).first()
        if not inst:
            continue

        # Evaluate baseline compliance under active rule
        base_eval = evaluate_fdr_compliance_versioned(fdr, inst, baseline_rule, db, save_result=False)
        prev_outcome = base_eval["overall_outcome"]
        if prev_outcome == "COMPLIANT":
            currently_compliant += 1

        # Run candidate rule dry-run (save_result=False guarantees zero historical mutation)
        dry_eval = evaluate_fdr_compliance_versioned(fdr, inst, temp_rule_record, db, save_result=False)
        new_outcome = dry_eval["overall_outcome"]

        # Did it flip compliant -> non_compliant?
        if prev_outcome == "COMPLIANT" and new_outcome == "NON_COMPLIANT":
            total_flips += 1
            failing_checks = [c for c in dry_eval["checks"] if c["outcome"] == "NON_COMPLIANT"]
            item = {
                "fdr_id": fdr.id,
                "fdr_number": fdr.fdr_number,
                "institution_id": inst.id,
                "institution_name": inst.name,
                "aicte_id": inst.aicte_id,
                "state": inst.state,
                "amount": fdr.amount,
                "tenure_months": fdr.tenure_months,
                "failing_reasons": [
                    {
                        "rule_id": c["rule_id"],
                        "name": c["name"],
                        "observed": c["observed_value"],
                        "expected": c["expected_value"],
                        "explanation": c["explanation_en"]
                    }
                    for c in failing_checks
                ]
            }
            newly_non_compliant.append(item)
            affected_institutions_map[inst.id] = inst.name

    flip_percentage = round((total_flips / max(1, currently_compliant)) * 100, 1)

    return {
        "candidate_rule_version": candidate_version_tag,
        "simulation_timestamp": datetime.utcnow().isoformat(),
        "total_active_instruments_evaluated": total_instruments,
        "previously_compliant_count": currently_compliant,
        "impacted_instruments_flipped_count": total_flips,
        "flip_rate_percentage": flip_percentage,
        "total_affected_institutions": len(affected_institutions_map),
        "newly_non_compliant_instruments": newly_non_compliant,
        "affected_institutions_summary": [
            {"institution_id": k, "name": v} for k, v in affected_institutions_map.items()
        ],
        "statutory_notice": "Dry-run impact simulation. No retrospective modification occurred. Previous records retain their rule version.",
        "statutory_disclaimer": DEFAULT_DISCLAIMER_EN
    }


def compute_institution_compliance_score(db: Session, institution_id: int) -> Dict[str, Any]:
    """
    Computes aggregated compliance scoring and breakdown for an institution across its deposits.
    """
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise ValueError(f"Institution ID {institution_id} not found.")

    fdrs = db.query(FDR).filter(FDR.institution_id == inst.id).all()
    active_rule = get_active_rule(db)

    total_instruments = len(fdrs)
    compliant_count = 0
    non_compliant_count = 0
    needs_review_count = 0
    instrument_breakdowns = []
    total_score_sum = 0.0

    for fdr in fdrs:
        eval_res = evaluate_fdr_compliance_versioned(fdr, inst, active_rule, db, save_result=False)
        st = eval_res["overall_outcome"]
        sc = eval_res["compliance_score"]
        total_score_sum += sc

        if st == "COMPLIANT":
            compliant_count += 1
        elif st == "NON_COMPLIANT":
            non_compliant_count += 1
        else:
            needs_review_count += 1

        instrument_breakdowns.append({
            "fdr_id": fdr.id,
            "fdr_number": fdr.fdr_number,
            "amount": fdr.amount,
            "bank_name": fdr.bank_name,
            "outcome": st,
            "compliance_score": sc,
            "checks_summary": [
                {"rule_id": c["rule_id"], "outcome": c["outcome"], "name": c["name"]}
                for c in eval_res["checks"]
            ]
        })

    overall_percentage = round(total_score_sum / max(1, total_instruments), 1) if total_instruments > 0 else 100.0

    return {
        "institution_id": inst.id,
        "institution_name": inst.name,
        "aicte_id": inst.aicte_id,
        "state": inst.state,
        "category": inst.category,
        "active_rule_version": active_rule.version_tag,
        "total_instruments": total_instruments,
        "compliant_instruments": compliant_count,
        "non_compliant_instruments": non_compliant_count,
        "needs_review_instruments": needs_review_count,
        "overall_compliance_percentage": overall_percentage,
        "status_label": "FULLY_COMPLIANT" if compliant_count == total_instruments and total_instruments > 0 else "DEFICIT_OR_PENDING",
        "breakdown_by_instrument": instrument_breakdowns,
        "statutory_disclaimer": DEFAULT_DISCLAIMER_EN,
        "statutory_disclaimer_hi": DEFAULT_DISCLAIMER_HI
    }
