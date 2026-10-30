# DepoSafe Synthetic Dataset & Ground Truth Specification

> **AICTE Regulation Bureau - FDR Intelligence & Management Portal**  
> **Evaluation & Benchmark Dataset Documentation**

---

## 1. Overview & Non-Negotiable Safeguards

DepoSafe's evaluation harness is underpinned by a rigorously labelled synthetic dataset. Every document, bank response, institution identifier, and signature is strictly synthetic.

- **Mandatory Visual Watermarking**: Every generated document explicitly bears the watermark: `SYNTHETIC SAMPLE - FOR REGULATION BUREAU DEMONSTRATION ONLY`.
- **Simulation Disclaimer**: Every simulated bank API verification record is stamped `SIMULATED, not a real bank verification`.
- **Deterministic Generation**: Generated via `make data` (or `python data/generator.py`) using pseudo-random seeds (`SEED = 42`) for 100% reproducible benchmark evaluation.
- **Measurable Results**: Never claim an AI/forensic detection metric without comparing against explicit labels in `data/synthetic/ground_truth.json`.

---

## 2. Dataset Composition

| Parameter | Value | Details |
|---|---|---|
| **Total Institutions** | 80 | Fictional engineering, polytechnic, and management institutes across 15 Indian States/UTs |
| **AICTE-Style IDs** | 80 | Format: `1-AICTE-[STATE_CODE]-[RANDOM_SEQ]` (e.g. `1-AICTE-MH-829104`) |
| **Total Instruments (FDRs)** | 164 | 1 to 3 FDR instruments per institution |
| **Rendered Artifacts** | 328+ files | PDF master instruments + scanned JPG/PNG variants with simulated capture noise |
| **Bank Layout Styles** | 5 Distinct Layouts | Fictional banks with unique typography, geometry, bilingual text, borders, stamps |
| **Supporting Documents** | ~50 documents | Bank confirmation letters, institution declarations, electricity bills (negative tests) |
| **Clean vs Anomalous Split** | ~32% Clean / ~68% Anomalous | 52 pristine instruments; 112 instruments with 1 to 3 injected irregularities |

---

## 3. Visual Contact Sheet

Ten representative synthetic FDR documents showing distinct bank layouts, stamps, Hindi/English bilingual headers, scan distortions, and watermarks:

![DepoSafe Synthetic FDR Contact Sheet](/Users/harshitapradhan/Desktop/fdr/docs/assets/contact_sheet.png)

---

## 4. Bank Layout Taxonomy

To prevent document AI models from overfitting to a single template, the dataset synthesizes documents across five distinct banking institution profiles:

1. **Bharat National Bank (`BHARAT_NATIONAL_BANK`)**
   - *Design*: Formal public-sector layout, navy primary palette (`#0B2545`), bilingual English/Hindi header (`भारत नेशनल बैंक / BHARAT NATIONAL BANK`).
   - *Security features*: Circular seal watermark, 2pt outer frame, dual authorized signatory blocks.
2. **Apex Commercial Bank (`APEX_COMMERCIAL_BANK`)**
   - *Design*: Modern corporate layout, deep maroon accents (`#7A1C1C`), tabular term deposit receipt structure.
   - *Security features*: Embedded security guilloche motif, branch IFSC banner, computer-generated receipt caveat.
3. **Gramin Vikas Bank (`GRAMIN_VIKAS_BANK`)**
   - *Design*: Regional rural bank layout, forest green theme (`#1B4D3E`), prominent Devanagari script headers (`ग्रामीण विकास बैंक`).
   - *Security features*: Branch manager verification stamp, district advisory note.
4. **Hindustan Mercantile Bank (`HINDUSTAN_MERCANTILE_BANK`)**
   - *Design*: Heritage merchant bank styling, charcoal & slate framing (`#2B2D42`), structured certificate grid.
   - *Security features*: Barcode mock block, interest compounding disclosure.
5. **Pragati Cooperative Bank (`PRAGATI_COOPERATIVE_BANK`)**
   - *Design*: Urban cooperative credit society format, royal purple motif (`#4A154B`), compact bilingual receipt.
   - *Security features*: Society registration number, cashier countersignature box.

---

## 5. Injected Irregularity Catalog (`ground_truth.json`)

Each generated instrument has a structured entry in `data/synthetic/ground_truth.json`. The dataset evaluates 14 distinct forensic, compliance, and lifecycle edge cases:

| Issue ID | Category | Description | Ground Truth Label in JSON | Expected System Action |
|---|---|---|---|---|
| **ISSUE-01** | Forensic / Data | Missing mandatory field (e.g. missing Maturity Date or Bank Name) | `MISSING_MANDATORY_FIELD` | Scrutiny flag; provenance `MISMATCH` |
| **ISSUE-02** | Rule / Logic | Chronological impossibility: maturity date occurs before issue date | `MATURITY_BEFORE_ISSUE` | Immediate compliance rejection |
| **ISSUE-03** | Forensic / Tamper | Pixel-level amount tamper (modified raster block, noise discontinuity) | `AMOUNT_TAMPER_SUSPECTED` | Ela/Noise analysis flag; review priority elevated |
| **ISSUE-04** | Document Reconciliation | Maturity date mismatch between FDR certificate and Bank Confirmation Letter | `MATURITY_MISMATCH_BANK_LETTER` | Discrepancy callout in cross-document comparator |
| **ISSUE-05** | Document Alignment | Bank name on certificate contradicts institution application metadata | `WRONG_BANK_NAME` | Validation failure on bank catalog match |
| **ISSUE-06** | Graph / Integrity | Cross-institution duplicate FDR number (collusion / certificate reuse) | `DUPLICATE_FDR_CROSS_INSTITUTION` | NetworkX bipartite graph flagged node |
| **ISSUE-07** | Provenance | Same bank + number re-submitted as different scanned file | `SAME_BANK_NUMBER_NEW_SCAN` | Lineage linkage detection |
| **ISSUE-08** | Digital Signature | Identical file re-uploaded across different institutions (SHA-256 collision) | `EXACT_FILE_DUPLICATE_HASH` | Hash registry collision block |
| **ISSUE-09** | Image Forensics | Visually similar re-render with slight crop/shift (Perceptual Hash hamming < 5) | `PERCEPTUAL_HASH_COLLISION` | pHash cluster warning |
| **ISSUE-10** | Metadata Forensics | EXIF/PDF metadata indicates image manipulation (Photoshop, GIMP, modified date post-issue) | `METADATA_ANOMALY` | PDF trailer & XMP metadata inspect alert |
| **ISSUE-11** | Doc Classifier | Wrong document uploaded (e.g. Electricity Bill instead of FDR receipt) | `WRONG_DOC_TYPE` | OCR text classification reject (`UNRECOGNIZED_DOC`) |
| **ISSUE-12** | Lifecycle | FDR expired relative to Demo Clock | `EXPIRED_FDR` | Status set to `MATURED` / `EXPIRING`; renewal alert |
| **ISSUE-13** | Renewal Lifecycle | Expired deposit with missing renewal successor instrument | `RENEWAL_MISSING` | Red escalation flag; automated reminder queued |
| **ISSUE-14** | Release / Safeguard | Release requested before lock-in expiration or unfulfilled compliance conditions | `RELEASE_UNMET_CONDITIONS` | Competent authority rejection barrier |

---

## 6. The Hero Demo Case (`INST-DEMO-HERO`)

For the Smart India Hackathon grand-finale 90-second live demonstration, a dedicated hero case showcases multi-layered intelligence in a single workflow:

- **Institution**: `Saraswati Institute of Technology & Management` (`1-AICTE-DL-772091`, Delhi)
- **Primary Instrument**: FDR Number `HERO-DL-2024-8841`, Amount **Rs. 10,00,000.00** (Illustrative placeholder)
- **Injected Multi-Threat Vector**:
  1. **Cross-Document Discrepancy**: FDR certificate states maturity date `2034-03-31` (10-year term), but the accompanying Bank Confirmation Letter states maturity `2027-03-31` (3-year term).
  2. **Cross-Institution Duplicate**: The exact FDR number `HERO-DL-2024-8841` was simultaneously submitted by `Apex Institute of Polytechnic` in Maharashtra.
  3. **Metadata Anomaly**: The PDF metadata exposes `Creator: Adobe Photoshop 2024 (Windows)` and `ModDate` 48 hours after claimed bank issue date.
  4. **Explainability**: Review Priority Indicator score is calculated at `0.88` with explicit itemized reasons (`REASON_CROSS_DOC_MISMATCH`, `REASON_CROSS_INSTITUTION_COLLUSION`, `REASON_METADATA_TAMPER`).

---

## 7. Lifecycle Passport (5-Year Historical Lineage)

Five institutions include full 5-year chronological lineage trees, enabling demonstration of DepoSafe's "Never Overwrite an FDR" safeguard:

```
[2019 Original FDR: Rs 5,00,000]
         │ (Status: SUPERSEDED)
         ▼
[2021 Renewal 1: Rs 7,50,000 (+2.5L Addition)]
         │ (Status: SUPERSEDED)
         ▼
[2023 Renewal 2: Rs 10,00,000 (+2.5L Final)]
         │ (Status: ACTIVE / Maturity 2028)
```

Each transition writes an append-only hash-chained audit log (`H_n = SHA256(H_{n-1} || event_n)`).

---

## 8. Demo Clock Alignment

The dataset includes synthetic maturities distributed relative to the baseline Demo Clock (`2024-10-30`):
- **Immediate Escalation (+3 Days)**: 12 FDRs expiring within 72 hours (triggers Celery Beat SMS/Email alerts).
- **Grace Period (+12 Days)**: 18 FDRs expiring within 15 days (triggers renewal submission window).
- **Notice Period (+60 Days)**: 25 FDRs expiring within 60 days (triggers institution portal advisory banners).
- **Overdue / Stale (-30 to -180 Days)**: 15 FDRs past maturity requiring enforcement action.

---

## 9. Benchmark & Measurement Protocol

The evaluation harness in `backend/tests/` uses `ground_truth.json` to verify:

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

- **Extraction Accuracy**: Evaluated against field-level ground truth values (FDR number, amount, maturity date, bank name, interest rate).
- **Forensic Sensitivity**: Evaluated against injected `tamper_flags` and `anomalies`.
- **Zero Hallucination Rule**: If a field is degraded or occluded, the system must output `confidence < 0.5` with provenance `SOURCE_UNAVAILABLE` or `MISMATCH`, never an ungrounded guess.
