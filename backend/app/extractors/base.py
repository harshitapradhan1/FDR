from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ExtractedFieldData(BaseModel):
    value: Any = None
    raw_text: Optional[str] = None
    confidence: float = 0.0
    bbox: Optional[list] = None # [ymin, xmin, ymax, xmax] or [x, y, w, h]
    needs_review: bool = False
    source: str = "DETERMINISTIC_LAYOUT"

class ExtractedDocumentFields(BaseModel):
    bank_name: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    branch_name: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    fdr_number: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    amount: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    amount_words: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    issue_date: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    maturity_date: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    tenure_months: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    interest_rate: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    depositor_name: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    lien_marked: ExtractedFieldData = Field(default_factory=ExtractedFieldData)
    lien_clause_text: ExtractedFieldData = Field(default_factory=ExtractedFieldData)

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, layout_schema: Dict[str, Any]) -> ExtractedDocumentFields:
        """Extract structured fields from text using layout schema."""
        pass

