import re
from typing import Dict, Any, Optional
from backend.app.extractors.base import BaseExtractor, ExtractedDocumentFields, ExtractedFieldData
from backend.app.services.normalizer import (
    normalize_amount, normalize_date, normalize_hindi_digits, words_to_amount_approx
)

class DeterministicTemplateExtractor(BaseExtractor):
    def extract(self, text: str, layout_schema: Dict[str, Any]) -> ExtractedDocumentFields:
        result = ExtractedDocumentFields()
        clean_text = normalize_hindi_digits(text)
        patterns = layout_schema.get("field_patterns", {})
        baseline_conf = layout_schema.get("confidence_baseline", 0.90)

        # 1. Bank Name
        bank_name = layout_schema.get("bank_name")
        if bank_name and bank_name != "Generic Bank Fallback" and (bank_name.lower() in clean_text.lower() or layout_id_match(layout_schema, clean_text)):
            result.bank_name = ExtractedFieldData(
                value=bank_name,
                raw_text=bank_name,
                confidence=baseline_conf,
                bbox=[50, 40, 250, 30],
                source="TEMPLATE_SCHEMA"
            )

        if not result.bank_name.value:
            from backend.app.services.field_validator import RECOGNIZED_BANKS
            for b in RECOGNIZED_BANKS:
                if b.lower() in clean_text.lower():
                    result.bank_name = ExtractedFieldData(
                        value=b,
                        raw_text=b,
                        confidence=0.96,
                        bbox=[50, 40, 250, 30],
                        source="BANK_DIRECTORY_MATCH"
                    )
                    break

        # 2. FDR Number
        # Standard bank alphanumeric pattern (e.g. BNB-DEL-HERO-1000, APEX-DEL-1002, SBI-DEL-9876543210, HMB-PUN-1006)
        m_code = re.search(r"\b([A-Z]{2,5}-[A-Z]{2,4}-[A-Z0-9\-]{4,20})\b", clean_text)
        if m_code:
            result.fdr_number = ExtractedFieldData(
                value=m_code.group(1).strip(),
                raw_text=m_code.group(0),
                confidence=0.98,
                bbox=[120, 100, 150, 25],
                source="STANDARDIZED_FDR_PATTERN"
            )

        if not result.fdr_number.value:
            fdr_rule = patterns.get("fdr_number", {})
            fdr_regex = fdr_rule.get("regex")
            if fdr_regex:
                m = re.search(fdr_regex, clean_text, re.IGNORECASE)
                if m:
                    val = m.group(1).strip()
                    if any(c.isdigit() for c in val):
                        result.fdr_number = ExtractedFieldData(
                            value=val,
                            raw_text=m.group(0),
                            confidence=0.96,
                            bbox=fdr_rule.get("expected_bbox", [120, 100, 150, 25]),
                            source="TEMPLATE_SCHEMA"
                        )

        # Fallback labeled search
        if not result.fdr_number.value:
            for m in re.finditer(r"(?:FDR|Deposit|Certificate|Receipt)\s*(?:Account|Advice)?\s*(?:Number|No\.?|Ref\.?|रसीद|संख्या|#)?[:\s\n]+([A-Z0-9\-\/]{6,35})", clean_text, re.IGNORECASE):
                val = m.group(1).strip().upper()
                if any(c.isdigit() for c in val) and val not in ["RECEIPT", "PLEDGED", "SPECIAL", "SCHEME", "AMOUNT", "ACCOUNT", "NUMBER"]:
                    result.fdr_number = ExtractedFieldData(
                        value=val,
                        raw_text=m.group(0),
                        confidence=0.92,
                        bbox=[120, 100, 150, 25],
                        source="PROXIMITY_FALLBACK"
                    )
                    break

        if not result.fdr_number.value:
            m_num = re.search(r"\b([0-9]{8,18})\b", clean_text)
            if m_num:
                result.fdr_number = ExtractedFieldData(
                    value=m_num.group(1),
                    raw_text=m_num.group(0),
                    confidence=0.85,
                    bbox=[120, 100, 150, 25],
                    source="NUMERIC_ACCOUNT_FALLBACK"
                )

        # 3. Amount (Figures)
        amt_rule = patterns.get("amount", {})
        amt_regex = amt_rule.get("regex")
        if amt_regex:
            m_amt = re.search(amt_regex, clean_text, re.IGNORECASE)
            if m_amt:
                norm_val = normalize_amount(m_amt.group(1))
                if norm_val:
                    result.amount = ExtractedFieldData(
                        value=norm_val,
                        raw_text=m_amt.group(0),
                        confidence=0.98,
                        bbox=amt_rule.get("expected_bbox", [350, 100, 120, 25]),
                        source="TEMPLATE_SCHEMA"
                    )

        if not result.amount.value:
            m_gen_amt = re.search(r"(?:Deposit\s*Amount|Pledged\s*Deposit\s*Amount|Face\s*Value|Principal|Sum|₹|Rs\.?|INR)[:\s\n]*[^\d\n]*([0-9,]+(?:\.\d{2})?)", clean_text, re.IGNORECASE)
            if m_gen_amt:
                norm_val = normalize_amount(m_gen_amt.group(1))
                if norm_val and norm_val > 1000:
                    result.amount = ExtractedFieldData(
                        value=norm_val,
                        raw_text=m_gen_amt.group(0),
                        confidence=0.90,
                        bbox=[350, 100, 120, 25],
                        source="PROXIMITY_FALLBACK"
                    )

        # 4. Amount Words (Words vs Figures reconciliation)
        words_rule = patterns.get("amount_words", {})
        words_regex = words_rule.get("regex")
        if words_regex:
            m_words = re.search(words_regex, clean_text, re.IGNORECASE)
            if m_words:
                w_text = m_words.group(1).strip()
                result.amount_words = ExtractedFieldData(
                    value=w_text,
                    raw_text=m_words.group(0),
                    confidence=0.92,
                    bbox=words_rule.get("expected_bbox", [120, 130, 400, 25]),
                    source="TEMPLATE_SCHEMA"
                )

        # 5. Issue Date
        issue_rule = patterns.get("issue_date", {})
        issue_regex = issue_rule.get("regex")
        if issue_regex:
            m_issue = re.search(issue_regex, clean_text, re.IGNORECASE)
            if m_issue:
                d = normalize_date(m_issue.group(1))
                if d:
                    result.issue_date = ExtractedFieldData(
                        value=d,
                        raw_text=m_issue.group(1),
                        confidence=0.95,
                        bbox=issue_rule.get("expected_bbox", [120, 130, 100, 25]),
                        source="TEMPLATE_SCHEMA"
                    )

        if not result.issue_date.value:
            m_gen_iss = re.search(r"(?:Date\s*of\s*Issue|Issue\s*Date|जारी\s*दिनांक)[:\s\n]*([0-9a-zA-Z\-\/]{8,15})", clean_text, re.IGNORECASE)
            if m_gen_iss:
                d = normalize_date(m_gen_iss.group(1))
                if d:
                    result.issue_date = ExtractedFieldData(
                        value=d,
                        raw_text=m_gen_iss.group(1),
                        confidence=0.90,
                        bbox=[120, 130, 100, 25],
                        source="FALLBACK_DATE"
                    )

        # 6. Maturity Date
        mat_rule = patterns.get("maturity_date", {})
        mat_regex = mat_rule.get("regex")
        if mat_regex:
            m_mat = re.search(mat_regex, clean_text, re.IGNORECASE)
            if m_mat:
                d = normalize_date(m_mat.group(1))
                if d:
                    result.maturity_date = ExtractedFieldData(
                        value=d,
                        raw_text=m_mat.group(1),
                        confidence=0.95,
                        bbox=mat_rule.get("expected_bbox", [350, 130, 100, 25]),
                        source="TEMPLATE_SCHEMA"
                    )

        if not result.maturity_date.value:
            m_gen_mat = re.search(r"(?:Date\s*of\s*Maturity|Maturity\s*Date|Due\s*Date|परिपक्वता\s*दिनांक)[:\s\n]*([0-9a-zA-Z\-\/]{8,15})", clean_text, re.IGNORECASE)
            if m_gen_mat:
                d = normalize_date(m_gen_mat.group(1))
                if d:
                    result.maturity_date = ExtractedFieldData(
                        value=d,
                        raw_text=m_gen_mat.group(1),
                        confidence=0.90,
                        bbox=[350, 130, 100, 25],
                        source="FALLBACK_DATE"
                    )

        # 7. Interest Rate
        roi_rule = patterns.get("interest_rate", {})
        roi_regex = roi_rule.get("regex")
        if roi_regex:
            m_roi = re.search(roi_regex, clean_text, re.IGNORECASE)
            if m_roi:
                try:
                    roi_val = float(m_roi.group(1))
                    result.interest_rate = ExtractedFieldData(
                        value=roi_val,
                        raw_text=m_roi.group(0),
                        confidence=0.94,
                        bbox=roi_rule.get("expected_bbox", [120, 160, 80, 25]),
                        source="TEMPLATE_SCHEMA"
                    )
                except ValueError:
                    pass

        # 8. Depositor Name
        dep_rule = patterns.get("depositor_name", {})
        dep_regex = dep_rule.get("regex")
        if dep_regex:
            m_dep = re.search(dep_regex, clean_text, re.IGNORECASE)
            if m_dep:
                result.depositor_name = ExtractedFieldData(
                    value=m_dep.group(1).strip(),
                    raw_text=m_dep.group(0),
                    confidence=0.90,
                    bbox=dep_rule.get("expected_bbox", [120, 190, 300, 25]),
                    source="TEMPLATE_SCHEMA"
                )

        # 9. Lien Clause & Lien Marked
        lien_rule = patterns.get("lien_clause", {})
        lien_regex = lien_rule.get("regex")
        if lien_regex:
            m_lien = re.search(lien_regex, clean_text, re.DOTALL | re.IGNORECASE)
            if m_lien:
                clause_text = m_lien.group(1).strip()
                result.lien_clause_text = ExtractedFieldData(
                    value=clause_text,
                    raw_text=clause_text,
                    confidence=0.95,
                    bbox=lien_rule.get("expected_bbox", [120, 220, 450, 40]),
                    source="TEMPLATE_SCHEMA"
                )
                result.lien_marked = ExtractedFieldData(
                    value=True,
                    confidence=0.95,
                    bbox=lien_rule.get("expected_bbox", [120, 220, 450, 40]),
                    source="TEMPLATE_SCHEMA"
                )

        if not result.lien_marked.value:
            # Fallback check
            lower_all = clean_text.lower()
            is_pledged = ("lien" in lower_all or "pledged" in lower_all) and ("aicte" in lower_all)
            result.lien_marked = ExtractedFieldData(
                value=is_pledged,
                confidence=0.90 if is_pledged else 0.40,
                bbox=[120, 220, 450, 40],
                source="KEYWORD_SEARCH"
            )

        # Flag fields with low confidence
        for field_name in result.model_fields.keys():
            item: ExtractedFieldData = getattr(result, field_name)
            if item.confidence < 0.75:
                item.needs_review = True

        return result


def layout_id_match(schema: Dict[str, Any], text: str) -> bool:
    aliases = schema.get("aliases", [])
    for a in aliases:
        if a.lower() in text.lower():
            return True
    return False
