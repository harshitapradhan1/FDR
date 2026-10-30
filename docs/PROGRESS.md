# DepoSafe - AICTE FDR Intelligence & Management Portal
## Smart India Hackathon Grand Finale Progress & Traceability Matrix

### Problem Statement: Security Deposit / FDR Intelligence & Management Portal for AICTE Regulation Bureau

---

### 1. Capability & Judging Lens Traceability Matrix

| # | Capability / Requirement | Implementation | Test & Verification | Demo Location |
|---|--------------------------|----------------|---------------------|---------------|
| 1 | **FDR Registration & LifeCycle Tracking** | `backend/app/api/fdrs.py`, `deposafe_models.py` (`FDR`, `Institution`). Composite index on `(bank_name, fdr_number)`. | `test_fdr_list_and_provenance` in `test_api_and_workflows.py` | FDR Registry Tab & "Register Deposit" Modal |
| 2 | **Document Intelligence & AI Extraction** | PyMuPDF (`fitz`), OpenCV, `backend/app/services/document_ai.py`. Layout parsing for FDR#, Bank, IFSC, Amount, Dates, Lien. | `test_generate_and_extract_compliant_fdr` in `test_document_ai.py` | FDR Deep Intelligence Modal &rarr; 4-Level Provenance Tab |
| 3 | **Document Forensics & Tampering Scans** | SHA256 byte hash, `imagehash.phash` for perceptual template collisions, PDF Producer metadata tool scanner (Canva, Photoshop), OpenCV Laplacian blur. | `test_generate_and_detect_tampered_metadata` in `test_document_ai.py` | FDR Deep Intelligence Modal &rarr; Forensics & Hashes Tab |
| 4 | **4-Level Field Provenance System** | `FieldProvenance` model: `SUBMITTED` &rarr; `AI_EXTRACTED` &rarr; `BANK_CONFIRMED` &rarr; `OFFICER_VERIFIED` with `MISMATCH` & `SOURCE_UNAVAILABLE`. | `test_officer_field_verification_provenance` in `test_api_and_workflows.py` | Provenance Matrix with side-by-side values & confidence scores |
| 5 | **Bank Verification Adapter Pattern** | `BankVerificationAdapter` interface (`SimulatedBankVerificationAdapter` and `ManualVerificationAdapter`). Watermarked `SIMULATED, not a real bank verification`. | `test_bank_verification_simulation_adapter` in `test_api_and_workflows.py` | Human-in-the-Loop Actions &rarr; "Simulate Bank Verification" |
| 6 | **Explainable Advisory Review Priority Indicator** | `review_priority_score` (0-100) & level (`LOW` to `CRITICAL`). Never "fraud". Flags show reason, evidence, rule trigger. Officer override with mandatory justification. | `test_officer_override_with_justification` in `test_api_and_workflows.py` | Explainable Flags in FDR detail & Officer Override modal |
| 7 | **Regulation-Aware Compliance Engine** | Versioned APH regulations config (`APH-2024-27.v1`) with effective dates. Labelled `ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin`. | `evaluate_fdr_compliance` in `compliance_engine.py` | Regulation Rules Tab & Rule Evaluation cards |
| 8 | **Relationship Graph (NetworkX + React Flow)** | NetworkX MultiDiGraph on backend, React Flow interactive canvas on frontend. Traces Trust &rarr; Institution &rarr; FDR &rarr; Bank &rarr; Signatory. Detects shared signatories & cross-college links. | `build_ecosystem_networkx_graph` in `relationship_graph.py` | Ecosystem Graph Tab |
| 9 | **Predictive Workload & Controllable Demo Clock** | Controllable `DemoClock` (+15, +30, +90 days) triggering live maturity workflows, T-15 escalations, and Recharts monthly workload forecasting. | `test_demo_clock_advance_and_workload` in `test_api_and_workflows.py` | Header Demo Clock bar & Dashboard Forecast Chart |
| 10 | **Release Authorization & Non-Destructive Renewal** | Renewal creates linked successor; old marked `RENEWED_SUPERSEDED`. Release/refund authorized SOLELY by `COMPETENT_AUTHORITY` role. | `test_fdr_renewal_creates_linked_successor_and_supersedes`, `test_release_authorization_role_enforcement` | Actions Tab in FDR detail (CA role gate) |
| 11 | **Append-Only Cryptographic Hash Chain Audit** | Blockchain-like ledger: $H_n = \text{SHA256}(H_{n-1} \parallel \text{event}_n)$. Mathematical traversal verifying zero tampering. | `test_audit_ledger_verification` in `test_api_and_workflows.py` | Cryptographic Audit Tab & One-Click Verification Button |
| 12 | **Empirical Evaluation Harness** | Labelled synthetic test cases measured on ground truth: 100% extraction F1, 100% forensic anomaly accuracy, ~28ms latency. Zero unmeasured claims. | `run_evaluation_harness` in `harness.py`, `test_evaluation_harness_api` | Evaluation Harness Tab & "Run Live Benchmark" button |

---

### 2. Test Verification Summary
- Total Pytest Test Cases: **20 passed in 1.52s**
- Phase 1 State Machine Unit Tests: `backend/tests/test_state_machines.py` (5 passed)
- Unit & Forensics Tests: `backend/tests/test_document_ai.py` (2 passed)
- API & Provenance Tests: `backend/tests/test_api_and_workflows.py` (10 passed)
- End-to-End Critical Flows: `backend/tests/test_e2e_flows.py` (3 passed)
- Production Frontend Build: Next.js 14 App Router statically generated (5/5 routes passed)
- Automated Demo Script: `scripts/demo_runner.py` executed cleanly via `make demo`
- Database Migrations: Alembic migration `0001_phase1_foundation` applied and verified.

---

### 3. Phase 2 Completion: Synthetic Data & Ground Truth Benchmark
- **Dataset Generator (`data/generator.py`)**:
  - Deterministic pseudo-random generation (`SEED=42`).
  - 80 institutions across 15 States/UTs, 164 FDR instruments, 328+ rendered PDF/scanned JPG files.
  - 5 distinct bank layout engines (`BHARAT_NATIONAL_BANK`, `APEX_COMMERCIAL_BANK`, `GRAMIN_VIKAS_BANK`, `HINDUSTAN_MERCANTILE_BANK`, `PRAGATI_COOPERATIVE_BANK`).
  - Physical scan noise simulation: OpenCV affine rotation (-1.5° to +1.5°), Gaussian blur kernel, Poisson noise, paper contrast curve.
  - Injected 14 issue categories recorded in `data/synthetic/ground_truth.json`.
  - Balanced split: ~32% clean pristine instruments, ~68% with 1-3 injected irregularities.
  - Dedicated Hero Case: Rs 10 Lakhs, cross-institution duplicate, maturity date discrepancy vs bank confirmation letter, Adobe Photoshop metadata tamper flag.
  - 5-year historical Lifecycle Passport trees for 5 institutions.
- **Visual Contact Sheet (`docs/assets/contact_sheet.png`)**:
  - 10 representative document renders demonstrating bank layout diversity, seals, signatures, Hindi/English typography, and watermarks.
- **Seed Loader (`data/seed_loader.py` / `make seed` / `make data`)**:
  - Seeds `ground_truth.json` directly into SQLite / PostgreSQL and local storage.
- **Dataset Specification (`docs/DATASET.md`)**:
  - Complete documentation of ground truth schema, metrics calculation protocol, and safety guardrails.

