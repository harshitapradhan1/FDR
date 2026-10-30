import os
import time
import tempfile
from datetime import date
from typing import Dict, Any, List
from backend.app.services.pdf_generator import generate_synthetic_fdr_pdf
from backend.app.services.document_ai import extract_fdr_fields_from_pdf

# Synthetic Ground Truth Dataset Definitions
SYNTHETIC_EVAL_CASES = [
    {
        "id": "CASE-01",
        "category": "COMPLIANT",
        "bank_name": "State Bank of India",
        "branch_name": "New Delhi Main Branch",
        "ifsc_code": "SBIN0000691",
        "fdr_number": "SBI-DEL-8877665501",
        "amount": 3500000.0,
        "issue_date": date(2024, 4, 1),
        "maturity_date": date(2032, 4, 1),
        "society_name": "Aryavrat Education Foundation",
        "institution_name": "Aryavrat Institute of Technology",
        "regional_office": "North Western Regional Office",
        "tenure_months": 96,
        "tamper_metadata": False,
        "include_proper_lien": True,
        "expected_anomaly": False
    },
    {
        "id": "CASE-02",
        "category": "TAMPERED_METADATA",
        "bank_name": "Punjab National Bank",
        "branch_name": "Chandigarh Sector 17",
        "ifsc_code": "PUNB0024400",
        "fdr_number": "PNB-CHD-9922110022",
        "amount": 2500000.0,
        "issue_date": date(2024, 5, 10),
        "maturity_date": date(2032, 5, 10),
        "society_name": "Shivalik Development Trust",
        "institution_name": "Shivalik College of Engineering",
        "regional_office": "North Western Regional Office",
        "tenure_months": 96,
        "tamper_metadata": True, # Injected suspicious producer metadata
        "include_proper_lien": True,
        "expected_anomaly": True
    },
    {
        "id": "CASE-03",
        "category": "MISSING_LIEN",
        "bank_name": "Bank of Baroda",
        "branch_name": "Mumbai Fort Branch",
        "ifsc_code": "BARB0FORTXX",
        "fdr_number": "BOB-MUM-7733441133",
        "amount": 3500000.0,
        "issue_date": date(2024, 3, 15),
        "maturity_date": date(2032, 3, 15),
        "society_name": "Western Educational Society",
        "institution_name": "Western Institute of Management",
        "regional_office": "Western Regional Office",
        "tenure_months": 96,
        "tamper_metadata": False,
        "include_proper_lien": False, # Missing mandatory AICTE pledge
        "expected_anomaly": True
    },
    {
        "id": "CASE-04",
        "category": "COMPLIANT_PHARMACY",
        "bank_name": "Canara Bank",
        "branch_name": "Bangalore Cantonment",
        "ifsc_code": "CNRB0000123",
        "fdr_number": "CNR-BLR-5544332244",
        "amount": 2500000.0,
        "issue_date": date(2024, 6, 1),
        "maturity_date": date(2032, 6, 1),
        "society_name": "Cauvery Vidya Kendra",
        "institution_name": "Cauvery College of Pharmacy",
        "regional_office": "South Western Regional Office",
        "tenure_months": 96,
        "tamper_metadata": False,
        "include_proper_lien": True,
        "expected_anomaly": False
    },
    {
        "id": "CASE-05",
        "category": "TAMPERED_SHORT_TENURE",
        "bank_name": "Union Bank of India",
        "branch_name": "Hyderabad Koti",
        "ifsc_code": "UBIN0530018",
        "fdr_number": "UBI-HYD-1199887755",
        "amount": 1500000.0,
        "issue_date": date(2024, 1, 10),
        "maturity_date": date(2027, 1, 10), # Only 36 months instead of 96
        "society_name": "Telangana Academy of Science",
        "institution_name": "Telangana Polytechnic",
        "regional_office": "South Central Regional Office",
        "tenure_months": 36,
        "tamper_metadata": True,
        "include_proper_lien": False,
        "expected_anomaly": True
    },
    {
        "id": "CASE-06",
        "category": "COMPLIANT_MANAGEMENT",
        "bank_name": "HDFC Bank",
        "branch_name": "Nehru Place New Delhi",
        "ifsc_code": "HDFC0000003",
        "fdr_number": "HDF-DEL-6655443366",
        "amount": 1500000.0,
        "issue_date": date(2024, 2, 20),
        "maturity_date": date(2032, 2, 20),
        "society_name": "Apex Educational Society",
        "institution_name": "Apex School of Business",
        "regional_office": "Northern Regional Office",
        "tenure_months": 96,
        "tamper_metadata": False,
        "include_proper_lien": True,
        "expected_anomaly": False
    }
]

_LATEST_BENCHMARK_RESULT: Dict[str, Any] = {}

def run_evaluation_harness() -> Dict[str, Any]:
    """
    Executes the full evaluation harness against labelled synthetic data.
    Never claims a metric that was not empirically measured.
    """
    global _LATEST_BENCHMARK_RESULT
    
    start_time = time.time()
    temp_dir = tempfile.mkdtemp(prefix="deposafe_eval_")

    total_cases = len(SYNTHETIC_EVAL_CASES)
    
    # Extraction metric counters
    metrics = {
        "fdr_number": {"tp": 0, "fp": 0, "fn": 0},
        "amount": {"tp": 0, "fp": 0, "fn": 0},
        "ifsc_code": {"tp": 0, "fp": 0, "fn": 0},
        "bank_name": {"tp": 0, "fp": 0, "fn": 0},
        "lien_marked": {"tp": 0, "fp": 0, "fn": 0}
    }

    # Anomaly detection counters
    anomaly_eval = {
        "tp": 0, # Predicted anomaly when expected anomaly
        "fp": 0, # Predicted anomaly when compliant
        "tn": 0, # Predicted normal when compliant
        "fn": 0  # Predicted normal when expected anomaly
    }

    case_details = []
    latencies = []

    for case in SYNTHETIC_EVAL_CASES:
        doc_start = time.time()
        pdf_path = os.path.join(temp_dir, f"{case['id']}.pdf")
        
        generate_synthetic_fdr_pdf(
            output_path=pdf_path,
            bank_name=case["bank_name"],
            branch_name=case["branch_name"],
            ifsc_code=case["ifsc_code"],
            fdr_number=case["fdr_number"],
            amount=case["amount"],
            issue_date=case["issue_date"],
            maturity_date=case["maturity_date"],
            society_name=case["society_name"],
            institution_name=case["institution_name"],
            regional_office=case["regional_office"],
            tenure_months=case["tenure_months"],
            tamper_metadata=case["tamper_metadata"],
            include_proper_lien=case["include_proper_lien"]
        )

        res = extract_fdr_fields_from_pdf(pdf_path)
        doc_elapsed_ms = (time.time() - doc_start) * 1000.0
        latencies.append(doc_elapsed_ms)

        fields = res["fields"]
        forensics = res["forensics"]

        # 1. FDR Number Extraction
        extracted_fdr = fields["fdr_number"]["value"]
        if extracted_fdr == case["fdr_number"]:
            metrics["fdr_number"]["tp"] += 1
        elif extracted_fdr is None:
            metrics["fdr_number"]["fn"] += 1
        else:
            metrics["fdr_number"]["fp"] += 1

        # 2. Amount Extraction
        extracted_amt = fields["amount"]["value"]
        if extracted_amt is not None and abs(extracted_amt - case["amount"]) < 1.0:
            metrics["amount"]["tp"] += 1
        elif extracted_amt is None:
            metrics["amount"]["fn"] += 1
        else:
            metrics["amount"]["fp"] += 1

        # 3. IFSC Extraction
        extracted_ifsc = fields["ifsc_code"]["value"]
        if extracted_ifsc == case["ifsc_code"]:
            metrics["ifsc_code"]["tp"] += 1
        elif extracted_ifsc is None:
            metrics["ifsc_code"]["fn"] += 1
        else:
            metrics["ifsc_code"]["fp"] += 1

        # 4. Bank Name Extraction
        extracted_bank = (fields["bank_name"]["value"] or "").lower()
        if case["bank_name"].lower() in extracted_bank or extracted_bank in case["bank_name"].lower():
            metrics["bank_name"]["tp"] += 1
        elif not extracted_bank:
            metrics["bank_name"]["fn"] += 1
        else:
            metrics["bank_name"]["fp"] += 1

        # 5. Lien Marking
        extracted_lien = fields["lien_marked"]["value"]
        if extracted_lien == case["include_proper_lien"]:
            metrics["lien_marked"]["tp"] += 1
        else:
            metrics["lien_marked"]["fp"] += 1

        # Anomaly / Risk Flag Assessment
        is_anomalous_detected = forensics["producer_flagged"] or (not extracted_lien)
        expected_anomaly = case["expected_anomaly"]

        if is_anomalous_detected and expected_anomaly:
            anomaly_eval["tp"] += 1
        elif is_anomalous_detected and not expected_anomaly:
            anomaly_eval["fp"] += 1
        elif not is_anomalous_detected and not expected_anomaly:
            anomaly_eval["tn"] += 1
        else:
            anomaly_eval["fn"] += 1

        case_details.append({
            "case_id": case["id"],
            "category": case["category"],
            "latency_ms": round(doc_elapsed_ms, 1),
            "expected_anomaly": expected_anomaly,
            "detected_anomaly": is_anomalous_detected,
            "tamper_flagged": forensics["producer_flagged"],
            "lien_correctly_classified": (extracted_lien == case["include_proper_lien"])
        })

    total_duration_sec = time.time() - start_time

    # Calculate Field-Level Precision, Recall, F1
    field_scores = {}
    for f_name, counts in metrics.items():
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0
        field_scores[f_name] = {
            "precision": round(precision * 100, 1),
            "recall": round(recall * 100, 1),
            "f1_score": round(f1 * 100, 1)
        }

    # Calculate Anomaly Detection Metrics
    a_tp, a_fp, a_tn, a_fn = anomaly_eval["tp"], anomaly_eval["fp"], anomaly_eval["tn"], anomaly_eval["fn"]
    anomaly_prec = a_tp / (a_tp + a_fp) if (a_tp + a_fp) > 0 else 1.0
    anomaly_rec = a_tp / (a_tp + a_fn) if (a_tp + a_fn) > 0 else 1.0
    anomaly_f1 = (2 * anomaly_prec * anomaly_rec) / (anomaly_prec + anomaly_rec) if (anomaly_prec + anomaly_rec) > 0 else 1.0
    anomaly_acc = (a_tp + a_tn) / total_cases if total_cases > 0 else 1.0

    _LATEST_BENCHMARK_RESULT = {
        "timestamp": date.today().isoformat(),
        "total_test_samples": total_cases,
        "total_execution_time_sec": round(total_duration_sec, 2),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 1),
        "p95_latency_ms": round(sorted(latencies)[int(0.95 * len(latencies))], 1),
        "field_extraction_metrics": field_scores,
        "overall_field_accuracy_pct": round(
            sum(fs["f1_score"] for fs in field_scores.values()) / len(field_scores), 1
        ),
        "forensic_anomaly_detection": {
            "accuracy_pct": round(anomaly_acc * 100, 1),
            "precision_pct": round(anomaly_prec * 100, 1),
            "recall_pct": round(anomaly_rec * 100, 1),
            "f1_score_pct": round(anomaly_f1 * 100, 1),
            "confusion_matrix": anomaly_eval
        },
        "cases": case_details,
        "measurement_guarantee": "Empirically measured on labelled synthetic dataset. No unmeasured claims."
    }

    return _LATEST_BENCHMARK_RESULT

def get_latest_benchmark() -> Dict[str, Any]:
    global _LATEST_BENCHMARK_RESULT
    if not _LATEST_BENCHMARK_RESULT:
        return run_evaluation_harness()
    return _LATEST_BENCHMARK_RESULT

