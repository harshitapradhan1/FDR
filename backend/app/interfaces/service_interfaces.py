from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import date
from sqlalchemy.orm import Session

class OCRProvider(ABC):
    """Abstract interface for text extraction from PDF / scanned documents."""
    @abstractmethod
    def extract_text_and_layout(self, file_path: str) -> Dict[str, Any]:
        """Returns structured full_text, page blocks, and word coordinates."""
        pass

class FieldExtractor(ABC):
    """Abstract interface for extracting structured FDR instrument fields."""
    @abstractmethod
    def extract_fields(self, document_path: str, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns extracted fields with confidence scores and bounding boxes."""
        pass

class ValidationEngine(ABC):
    """Abstract interface for syntactic and formatting validations (IFSC, FDR#, checksums)."""
    @abstractmethod
    def validate_instrument_format(self, instrument_data: Dict[str, Any]) -> Dict[str, Any]:
        """Returns format check results (e.g. valid IFSC, valid dates)."""
        pass

class ComplianceEngine(ABC):
    """Abstract interface for versioned regulation handbook rule evaluation."""
    @abstractmethod
    def evaluate_compliance(self, fdr_data: Any, institution_data: Any, rule_version: str) -> Dict[str, Any]:
        """Evaluates minimum security deposit norms, mandatory tenure, and lien clauses."""
        pass

class AnomalyDetector(ABC):
    """Abstract interface for forensic tampering and anomaly detection."""
    @abstractmethod
    def detect_anomalies(self, document_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Detects PDF producer editing traces, pHash visual collisions, and image blur."""
        pass

class BankVerificationAdapter(ABC):
    """Abstract interface for Bank Core Banking System (CBS) / SFMS mock integration."""
    @abstractmethod
    def verify_instrument(
        self,
        bank_name: str,
        fdr_number: str,
        ifsc_code: str,
        expected_amount: float,
        expected_holder: str
    ) -> Dict[str, Any]:
        """Queries core banking confirmation and returns available checks status."""
        pass

class NotificationChannel(ABC):
    """Abstract interface for automated escalation and maturity alerts."""
    @abstractmethod
    def send_notification(self, recipient: str, role: str, template: str, context: Dict[str, Any]) -> bool:
        """Dispatches automated notifications (Email, SMS, Portal Inbox)."""
        pass

class AuditLogger(ABC):
    """Abstract interface for append-only cryptographic hash chain logging."""
    @abstractmethod
    def log_event(
        self,
        db: Session,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[int],
        actor_role: Optional[str],
        payload: Dict[str, Any]
    ) -> Any:
        """Calculates H_n = SHA256(H_{n-1} || event_n) and commits to ledger."""
        pass

    @abstractmethod
    def verify_chain(self, db: Session) -> Dict[str, Any]:
        """Traverses the full chain to mathematically verify immutability."""
        pass

class RiskScorer(ABC):
    """Abstract interface for computing advisory Review Priority Indicators (0-100)."""
    @abstractmethod
    def compute_review_priority(self, db: Session, fdr_id: int) -> Dict[str, Any]:
        """Computes advisory review priority score with explainable flags."""
        pass

