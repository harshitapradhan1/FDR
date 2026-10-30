import os
import fitz # PyMuPDF
import cv2
import numpy as np
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.services.image_preprocessor import preprocess_document_image
from backend.app.services.doc_classifier import classify_document_type, detect_bank_layout
from backend.app.extractors.template_extractor import DeterministicTemplateExtractor
from backend.app.extractors.base import ExtractedDocumentFields
from backend.app.services.field_validator import validate_extracted_fields
from backend.app.services.document_ai import extract_pdf_forensics
from backend.app.models.deposafe_models import FDR, FDRDocument, ExtractedField, FieldProvenance, ProvenanceLevel

def run_document_ai_pipeline(
    file_path: str,
    declared_details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Complete AI Document Pipeline:
    1. Read native text or OpenCV preprocessed raster
    2. Classify document type (FDR, Bank Letter, Declaration, Electricity Bill)
    3. Detect layout (matched to YAML schema or generic fallback)
    4. Extract fields using deterministic schema regex + proximity
    5. Compute field confidence & assign bounding boxes
    6. Run Field Validation Engine (PASSED / FAILED / NOT_CONFIRMED)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = fitz.open(file_path)
    forensics = extract_pdf_forensics(doc, file_path)

    # 1. Text extraction (Native PDF text first)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"

    # If text is empty or sparse (<30 chars), run image preprocessing
    needs_vision_preprocessing = len(full_text.strip()) < 30
    preprocessing_meta = {}

    if needs_vision_preprocessing and len(doc) > 0:
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, 3))
        # OpenCV Deskew + Denoise + Binarize
        cv_result = preprocess_document_image(img_np)
        preprocessing_meta = {
            "skew_angle": cv_result["skew_angle_detected"],
            "preprocessing": cv_result["preprocessing_applied"]
        }
        # If PyMuPDF couldn't extract text, use OCR on preprocessed image if available
        # or use OCR text from fitz
        try:
            full_text = page.get_textpage_ocr().extractTEXT()
        except Exception:
            pass

    # 2. Document Classification
    doc_type, doc_type_conf = classify_document_type(full_text)

    # 3. Bank Layout Detection
    layout_id, layout_conf, layout_schema = detect_bank_layout(full_text)

    # 4. Field Extraction
    extractor = DeterministicTemplateExtractor()
    extracted_fields_obj: ExtractedDocumentFields = extractor.extract(full_text, layout_schema)

    # Convert to standard dictionary with bbox and needs_review
    fields_dict = {}
    low_confidence_fields = []

    for fname, fdata in extracted_fields_obj.model_dump().items():
        val = fdata.get("value")
        conf = fdata.get("confidence", 0.0)
        bbox = fdata.get("bbox") or [100, 100, 200, 30]

        # Flag low-confidence fields for human confirmation
        is_low_conf = (conf < 0.75) or (val is None and fname in ["fdr_number", "amount", "maturity_date", "issue_date", "bank_name"])
        if is_low_conf:
            low_confidence_fields.append(fname)

        fields_dict[fname] = {
            "value": val,
            "raw_text": fdata.get("raw_text"),
            "confidence": conf,
            "bbox": bbox,
            "needs_human_confirmation": is_low_conf,
            "source": fdata.get("source", "DETERMINISTIC_SCHEMA")
        }

    # 5. Field Validation Engine
    validation_result = validate_extracted_fields(extracted_fields_obj, declared_details)

    doc.close()

    return {
        "file_path": file_path,
        "forensics": forensics,
        "document_classification": {
            "doc_type": doc_type,
            "confidence": doc_type_conf,
            "is_valid_fdr_type": (doc_type == "FDR_CERTIFICATE")
        },
        "layout_classification": {
            "layout_id": layout_id,
            "confidence": layout_conf,
            "is_known_layout": (layout_id != "UNKNOWN_LAYOUT"),
            "status": "IDENTIFIED" if layout_id != "UNKNOWN_LAYOUT" else "NEEDS_REVIEW"
        },
        "preprocessing": preprocessing_meta,
        "extracted_fields": fields_dict,
        "low_confidence_fields": low_confidence_fields,
        "has_low_confidence_fields": len(low_confidence_fields) > 0,
        "field_validation": validation_result
    }


def persist_pipeline_results_to_db(
    db: Session,
    fdr_id: int,
    doc_id: int,
    pipeline_result: Dict[str, Any]
) -> None:
    """
    Saves extracted fields with bboxes and updates 4-level provenance table in database.
    """
    fdr = db.query(FDR).filter(FDR.id == fdr_id).first()
    if not fdr:
        return

    doc = db.query(FDRDocument).filter(FDRDocument.id == doc_id).first()
    if doc:
        doc.doc_type = pipeline_result["document_classification"]["doc_type"]
        doc.ocr_status = "COMPLETED"

    fields = pipeline_result["extracted_fields"]

    # Delete existing extracted fields for this document to avoid duplicates
    db.query(ExtractedField).filter(ExtractedField.document_id == doc_id).delete()

    for fname, fdata in fields.items():
        if fdata["value"] is not None:
            ef = ExtractedField(
                fdr_id=fdr.id,
                document_id=doc_id,
                field_name=fname,
                value=str(fdata["value"]),
                confidence=fdata["confidence"],
                provenance=ProvenanceLevel.AI_EXTRACTED,
                bbox=fdata["bbox"]
            )
            db.add(ef)

    # Synchronize provenance fields
    for prov in fdr.provenance_fields:
        if prov.field_name in fields and fields[prov.field_name]["value"] is not None:
            ext_val = str(fields[prov.field_name]["value"])
            prov.ai_extracted_value = ext_val
            prov.ai_confidence = fields[prov.field_name]["confidence"]
            prov.bounding_box = fields[prov.field_name]["bbox"]

            sub_val = (prov.submitted_value or "").strip().lower()
            norm_ext = ext_val.strip().lower()

            if prov.field_name == "amount":
                try:
                    has_mismatch = abs(float(sub_val) - float(norm_ext)) > 1.0
                except ValueError:
                    has_mismatch = (sub_val != norm_ext)
            else:
                has_mismatch = (sub_val != norm_ext)

            if has_mismatch:
                prov.status = ProvenanceLevel.MISMATCH
                prov.mismatch_reason = f"Discrepancy: Submitted '{prov.submitted_value}', Scanned '{ext_val}'."
            else:
                prov.status = ProvenanceLevel.AI_EXTRACTED

    db.commit()

