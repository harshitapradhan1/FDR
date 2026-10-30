import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError, field_validator
from backend.app.extractors.base import BaseExtractor, ExtractedDocumentFields, ExtractedFieldData
from backend.app.services.normalizer import normalize_date, normalize_amount

class StrictLLMOutputSchema(BaseModel):
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    fdr_number: Optional[str] = None
    amount: Optional[float] = None
    issue_date: Optional[str] = None
    maturity_date: Optional[str] = None
    interest_rate: Optional[float] = None
    depositor_name: Optional[str] = None
    lien_marked_to_aicte: Optional[bool] = None
    lien_clause_text: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Extracted amount must be strictly positive")
        return v


class LLMLayoutLMExtractor(BaseExtractor):
    """
    Optional LLM / LayoutLM extractor fallback.
    Sits behind the BaseExtractor interface and strictly validates all outputs
    against StrictLLMOutputSchema before admitting fields into the pipeline.
    """
    def __init__(self, mock_response: Optional[Dict[str, Any]] = None):
        self.mock_response = mock_response

    def extract(self, text: str, layout_schema: Dict[str, Any]) -> ExtractedDocumentFields:
        result = ExtractedDocumentFields()

        # In production, this calls a hosted LayoutLM / Gemini multimodal endpoint.
        # Here we demonstrate the strict schema guardrail.
        raw_output = self.mock_response or {}

        try:
            # Enforce strict schema validation. If malformed, rejected immediately.
            validated: StrictLLMOutputSchema = StrictLLMOutputSchema.model_validate(raw_output)
        except ValidationError:
            # Never trust unvalidated model output
            return result

        if validated.bank_name:
            result.bank_name = ExtractedFieldData(
                value=validated.bank_name,
                confidence=0.88,
                bbox=[50, 40, 200, 30],
                source="LLM_FALLBACK_VALIDATED"
            )
        if validated.fdr_number:
            result.fdr_number = ExtractedFieldData(
                value=validated.fdr_number,
                confidence=0.89,
                bbox=[120, 100, 150, 25],
                source="LLM_FALLBACK_VALIDATED"
            )
        if validated.amount:
            result.amount = ExtractedFieldData(
                value=validated.amount,
                confidence=0.91,
                bbox=[350, 100, 120, 25],
                source="LLM_FALLBACK_VALIDATED"
            )
        if validated.issue_date:
            d = normalize_date(validated.issue_date)
            if d:
                result.issue_date = ExtractedFieldData(
                    value=d,
                    confidence=0.86,
                    bbox=[120, 130, 100, 25],
                    source="LLM_FALLBACK_VALIDATED"
                )
        if validated.maturity_date:
            d = normalize_date(validated.maturity_date)
            if d:
                result.maturity_date = ExtractedFieldData(
                    value=d,
                    confidence=0.86,
                    bbox=[350, 130, 100, 25],
                    source="LLM_FALLBACK_VALIDATED"
                )
        if validated.lien_marked_to_aicte is not None:
            result.lien_marked = ExtractedFieldData(
                value=validated.lien_marked_to_aicte,
                confidence=0.85,
                bbox=[120, 220, 450, 40],
                source="LLM_FALLBACK_VALIDATED"
            )

        return result

