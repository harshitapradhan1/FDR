import os
import glob
import yaml
from typing import Tuple, Dict, Any

DOC_SCHEMAS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../config/doc_schemas"))

def load_all_bank_schemas() -> Dict[str, Dict[str, Any]]:
    schemas = {}
    if not os.path.exists(DOC_SCHEMAS_DIR):
        return schemas
    
    yaml_files = glob.glob(os.path.join(DOC_SCHEMAS_DIR, "*.yaml"))
    for yf in yaml_files:
        try:
            with open(yf, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "layout_id" in data:
                    schemas[data["layout_id"]] = data
        except Exception:
            continue
    return schemas


def classify_document_type(text: str) -> Tuple[str, float]:
    """
    Classifies uploaded document type into standard AICTE doc taxonomy:
    - FDR_CERTIFICATE
    - BANK_CONFIRMATION_LETTER
    - INSTITUTION_DECLARATION
    - ELECTRICITY_BILL / UNRECOGNIZED_DOC
    """
    lower = text.lower()

    if "electricity" in lower or "consumer no" in lower or "power distribution" in lower or "kwh" in lower:
        return "ELECTRICITY_BILL", 0.95

    if "confirmation letter" in lower or "to whomsoever it may concern" in lower or "we hereby confirm that fixed deposit" in lower:
        return "BANK_CONFIRMATION_LETTER", 0.95

    if "declaration" in lower and ("board of governors" in lower or "trust" in lower or "authorized signatory" in lower):
        return "INSTITUTION_DECLARATION", 0.90

    fdr_keywords = [
        "term deposit", "fixed deposit", "fdr", "deposit receipt",
        "date of maturity", "maturity date", "principal sum", "जमा रसीद",
        "fdr account", "deposit amount", "interest rate", "pledged deposit"
    ]
    match_count = sum(1 for kw in fdr_keywords if kw in lower)
    if match_count >= 1:
        return "FDR_CERTIFICATE", min(0.99, 0.75 + 0.08 * match_count)

    return "UNRECOGNIZED_DOC", 0.30


def detect_bank_layout(text: str) -> Tuple[str, float, Dict[str, Any]]:
    """
    Identifies the layout template based on `/config/doc_schemas/*.yaml`.
    Returns (layout_id, confidence, schema_data).
    """
    schemas = load_all_bank_schemas()
    lower = text.lower()

    best_match = None
    best_score = 0.0

    for layout_id, schema in schemas.items():
        if layout_id == "GENERIC_FDR":
            continue
        
        score = 0.0
        # Check bank name and aliases
        aliases = schema.get("aliases", []) + [schema.get("bank_name", "")]
        for alias in aliases:
            if alias.lower() in lower:
                score += 0.50
                break

        # Check header keywords
        keywords = schema.get("header_keywords", [])
        for kw in keywords:
            if kw.lower() in lower:
                score += 0.25

        if score > best_score:
            best_score = score
            best_match = (layout_id, min(0.98, score), schema)

    if best_match and best_match[1] >= 0.50:
        return best_match

    # Fallback to Generic FDR layout
    generic_schema = schemas.get("GENERIC_FDR", {})
    if any(k.lower() in lower for k in ["fixed deposit", "term deposit", "deposit receipt"]):
        return "GENERIC_FDR", 0.70, generic_schema

    return "UNKNOWN_LAYOUT", 0.25, {}
