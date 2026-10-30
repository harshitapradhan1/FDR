from typing import Dict, Any, List, Optional
from datetime import date
from sqlalchemy.orm import Session
from backend.app.models.deposafe_models import ComplianceRule, FDR, Institution

DEFAULT_RULE_TAG = "APH-2024-27.v1"

DEFAULT_RULE_DEFINITION = {
    "disclaimer": "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin",
    "handbook_edition": "AICTE Approval Process Handbook (APH) 2024-2027",
    "effective_from": "2024-04-01",
    "rbi_scheduled_commercial_banks": [
        "State Bank of India",
        "Punjab National Bank",
        "Bank of Baroda",
        "Canara Bank",
        "Union Bank of India",
        "HDFC Bank",
        "ICICI Bank",
        "Axis Bank",
        "Kotak Mahindra Bank",
        "Bank of India",
        "Central Bank of India",
        "Indian Bank"
    ],
    "mandatory_minimum_tenure_months": 96, # 8 years (96 months) or 10 years (120 months)
    "deposit_norms_inr": {
        "Engineering & Technology": {
            "UG": 3500000,
            "PG": 2500000,
            "Diploma": 1500000
        },
        "Management": {
            "PG": 1500000,
            "UG": 1000000
        },
        "Pharmacy": {
            "UG": 2500000,
            "Diploma": 1500000
        },
        "Architecture & Town Planning": {
            "UG": 2000000
        },
        "Applied Arts & Crafts": {
            "UG": 1500000
        },
        "General Technical": {
            "Default": 2000000
        }
    },
    "category_concessions": {
        "Women": 0.20,       # 20% concession
        "Minority": 0.20,    # 20% concession
        "PwD": 0.20,         # 20% concession
        "North-East": 0.50,  # 50% concession
        "Normal": 0.00
    },
    "lien_clause_keywords": [
        "regional officer",
        "aicte",
        "all india council for technical education",
        "lien",
        "pledged"
    ],
    "auto_renewal_clause_recommended": True
}

def get_active_rule(db: Session) -> ComplianceRule:
    rule = db.query(ComplianceRule).filter(ComplianceRule.is_active == True).order_by(ComplianceRule.id.desc()).first()
    if not rule:
        rule = ComplianceRule(
            version_tag=DEFAULT_RULE_TAG,
            effective_from=date(2024, 4, 1),
            is_active=True,
            description="AICTE APH 2024-27 Security Deposit Baseline Rules",
            rules_json=DEFAULT_RULE_DEFINITION
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
    return rule

def calculate_required_fdr_amount(rules: Dict[str, Any], category: str, program_level: str, institution_type: str) -> float:
    norms = rules.get("deposit_norms_inr", {})
    cat_norms = norms.get(category, norms.get("General Technical", {}))
    base_amount = cat_norms.get(program_level, cat_norms.get("Default", 2000000))
    
    concessions = rules.get("category_concessions", {})
    concession_rate = concessions.get(institution_type, 0.0)
    
    final_required = base_amount * (1.0 - concession_rate)
    return float(final_required)

def evaluate_fdr_compliance(fdr: FDR, institution: Institution, rules_record: ComplianceRule) -> Dict[str, Any]:
    """
    Evaluates an FDR against the active versioned regulations.
    Safeguards:
    - Compliance is decided by explicit versioned rules.
    - AI is advisory.
    - Passing validation wording: 'available checks passed' vs 'not confirmed'.
    """
    rules = rules_record.rules_json
    checks: List[Dict[str, Any]] = []
    all_passed = True

    # 1. Scheduled Bank Check
    scheduled_banks = rules.get("rbi_scheduled_commercial_banks", [])
    bank_matched = any(sb.lower() in fdr.bank_name.lower() for sb in scheduled_banks)
    check_bank = {
        "rule_id": "APH-RULE-BANK-01",
        "name": "RBI Scheduled Commercial Bank Check",
        "required": "Must be an authorized RBI Scheduled Commercial Bank",
        "observed": fdr.bank_name,
        "passed": bank_matched,
        "explanation": "Bank is recognized on RBI's scheduled list." if bank_matched else f"Bank '{fdr.bank_name}' was not found in active RBI scheduled commercial list. Officer inquiry required."
    }
    checks.append(check_bank)
    if not bank_matched:
        all_passed = False

    # 2. Deposit Amount Check
    required_amount = calculate_required_fdr_amount(
        rules,
        institution.category,
        institution.program_level,
        institution.institution_type
    )
    amount_ok = fdr.amount >= required_amount
    check_amount = {
        "rule_id": "APH-RULE-AMT-02",
        "name": "Minimum Security Deposit Norm",
        "required": f"₹ {required_amount:,.2f} (Base norm for {institution.category} - {institution.program_level} with {institution.institution_type} norm)",
        "observed": f"₹ {fdr.amount:,.2f}",
        "passed": amount_ok,
        "explanation": "Deposit amount meets or exceeds regulatory requirement." if amount_ok else f"Deficit of ₹ {(required_amount - fdr.amount):,.2f} detected against prescribed handbook norm."
    }
    checks.append(check_amount)
    if not amount_ok:
        all_passed = False

    # 3. Tenure Check
    min_tenure = rules.get("mandatory_minimum_tenure_months", 96)
    tenure_ok = fdr.tenure_months >= min_tenure
    check_tenure = {
        "rule_id": "APH-RULE-TENURE-03",
        "name": "Mandatory Deposit Tenure Check",
        "required": f"Minimum {min_tenure} months ({min_tenure // 12} years)",
        "observed": f"{fdr.tenure_months} months",
        "passed": tenure_ok,
        "explanation": f"Tenure satisfies minimum lock-in requirement of {min_tenure} months." if tenure_ok else f"Tenure {fdr.tenure_months} months is below prescribed lock-in of {min_tenure} months."
    }
    checks.append(check_tenure)
    if not tenure_ok:
        all_passed = False

    # 4. Lien Clause Check
    lien_keywords = rules.get("lien_clause_keywords", [])
    lien_text = (fdr.lien_clause_text or "").lower()
    has_keywords = all(kw in lien_text for kw in ["aicte", "regional officer"]) or fdr.lien_marked_to_aicte
    check_lien = {
        "rule_id": "APH-RULE-LIEN-04",
        "name": "Mandatory Lien Marking to Regional Officer, AICTE",
        "required": "Instrument must state lien/pledge in favor of Regional Officer, AICTE",
        "observed": "Lien clause present and pledged" if has_keywords else "Missing explicit pledge to Regional Officer, AICTE",
        "passed": has_keywords,
        "explanation": "Lien confirmation text verified." if has_keywords else "Lien clause does not unambiguously reference Regional Officer, AICTE."
    }
    checks.append(check_lien)
    if not has_keywords:
        all_passed = False

    return {
        "rule_version": rules_record.version_tag,
        "disclaimer": rules.get("disclaimer", "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"),
        "evaluation_status": "AVAILABLE_CHECKS_PASSED" if all_passed else "NON_COMPLIANT",
        "overall_passed": all_passed,
        "checks": checks,
        "required_amount": required_amount,
        "observed_amount": fdr.amount
    }

