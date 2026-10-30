from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from enum import Enum

class RuleType(str, Enum):
    MIN_AMOUNT = "min_amount"
    VALIDITY_UNTIL = "validity_until"
    REQUIRED_DOCUMENT = "required_document"
    DATE_LOGIC = "date_logic"
    BANK_WHITELIST = "bank_whitelist"
    RELEASE_CONDITION = "release_condition"

class RuleSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ComplianceOutcome(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class RuleDefinitionSchema(BaseModel):
    rule_id: str
    description: str
    description_hi: Optional[str] = None
    type: RuleType
    severity: RuleSeverity = RuleSeverity.HIGH
    handbook_reference: str = "APH 2024-27 [Placeholder]"
    effective_from: str
    effective_to: Optional[str] = None
    applies_to: Dict[str, Any] = Field(default_factory=lambda: {"institution_category": "ALL", "program_level": "ALL"})
    parameters: Dict[str, Any] = Field(default_factory=dict)

class ComplianceRuleCreateRequest(BaseModel):
    version_tag: str
    description: str
    effective_from: date
    effective_to: Optional[date] = None
    rules: List[RuleDefinitionSchema]
    handbook_edition: Optional[str] = "AICTE Approval Process Handbook (APH)"
    disclaimer: str = "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"

class ComplianceRulePublishRequest(BaseModel):
    version_tag: str
    authorized_by_justification: str = "Official administrative gazette update authorized by Competent Authority."

class DryRunImpactRequest(BaseModel):
    new_rule_version_tag: Optional[str] = None
    candidate_rules: Optional[List[RuleDefinitionSchema]] = None
    target_rule_file: Optional[str] = None

class SingleCheckEvaluation(BaseModel):
    rule_id: str
    rule_type: str
    severity: str
    outcome: ComplianceOutcome
    name: str
    handbook_reference: str
    observed_value: Any
    expected_value: Any
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    explanation_en: str
    explanation_hi: str

class InstrumentComplianceEvaluation(BaseModel):
    fdr_id: int
    fdr_number: str
    institution_id: int
    institution_name: str
    rule_version_used: str
    overall_outcome: ComplianceOutcome
    compliance_score: float # 0 to 100
    statutory_disclaimer: str = "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"
    statutory_disclaimer_hi: str = "सभी नियम और मान उदाहरणार्थ सांकेतिक हैं - एआईसीटीई व्यवस्थापक द्वारा विन्यास योग्य"
    checks: List[SingleCheckEvaluation]
    evaluated_at: str

class InstitutionComplianceScore(BaseModel):
    institution_id: int
    institution_name: str
    aicte_id: str
    state: str
    total_instruments: int
    compliant_instruments: int
    non_compliant_instruments: int
    needs_review_instruments: int
    overall_compliance_percentage: float
    breakdown_by_instrument: List[Dict[str, Any]]
