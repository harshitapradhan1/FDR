# DepoSafe Verification & Cross-Document Reconciliation Benchmark
## Phase 5 Empirical Turnaround & Dual-Truth Ledger Evaluation

> [!NOTE]
> All automated bank verifications are executed behind the `BankVerificationAdapter` interface. In prototype mode, responses are simulated and carried under the strict watermark **`SIMULATED, not a real bank verification`**.

---

### 1. Verification Turnaround & Latency Metrics

Measured on sample instruments from `data/synthetic/ground_truth.json` seeded database:

| Metric | Measured Value | Standard / Target | Status |
|:-------|:---------------|:------------------|:-------|
| **Mean Verification Latency** | `2.24 ms` | < 150.0 ms | **PASSED** |
| **P50 Latency (Median)** | `2.07 ms` | < 100.0 ms | **PASSED** |
| **P90 Latency** | `2.52 ms` | < 250.0 ms | **PASSED** |
| **P99 Latency** | `8.74 ms` | < 500.0 ms | **PASSED** |
| **Simulated Business Turnaround** | `2.5 days` | < 5 days | **PASSED** |

---

### 2. Dual-Truth Four-Source Ledger & Badge Colors

DepoSafe maintains four independent truths per field with distinct UI badges and audit records:

| Source | Badge Label | Background | Text Color | Hex Color | Description |
|:-------|:------------|:-----------|:-----------|:----------|:------------|
| `SUBMITTED` | `Submitted (Institution)` | `bg-blue-100` | `text-blue-800` | `#2563EB` | Declared by institution during FDR registration |
| `AI_EXTRACTED` | `AI Extracted (OCR/Layout)` | `bg-purple-100` | `text-purple-800` | `#9333EA` | Layout-aware text and field extraction from PDF |
| `BANK_CONFIRMED` | `Bank Confirmed (CBS/SFMS)` | `bg-emerald-100` | `text-emerald-800` | `#059669` | Automated confirmation via core banking adapter |
| `OFFICER_VERIFIED` | `Officer Verified (Human-in-Loop)` | `bg-amber-100` | `text-amber-800` | `#D97706` | Human-in-the-loop manual verification with evidence |
| `MISMATCH` | `Conflict / Mismatch Detected` | `bg-rose-100` | `text-rose-800` | `#E11D48` | Discrepancy detected across sources |
| `SOURCE_UNAVAILABLE` | `Source Unavailable` | `bg-slate-100` | `text-slate-800` | `#64748B` | Bank gateway down; routed for manual review |

---

### 3. Controllable Banking Behavior Trigger Matrix

Every required behavior scenario was executed and verified during the benchmark:

| Scenario | Trigger Mechanism | Expected Behavior | Observed Result | Status |
|:---------|:------------------|:------------------|:----------------|:-------|
| **`SUCCESS`** | `scenario="SUCCESS"` | `AVAILABLE_CHECKS_PASSED`, valid HMAC signature | Valid HMAC-SHA256 signature, 0 diffs | **VERIFIED** |
| **`MISMATCH`** | `scenario="MISMATCH"` | Conflicting maturity date (15 Nov vs 15 Dec style) | Mismatch flagged, diffs recorded in ledger | **VERIFIED** |
| **`NOT_FOUND`** | `scenario="NOT_FOUND"` | `NOT_CONFIRMED`, instrument missing in CBS | `NOT_CONFIRMED` returned with explanation | **VERIFIED** |
| **`TIMEOUT`** | `scenario="TIMEOUT"` | Exponential backoff retries ($2^k$) | Retried 2x, enqueued in pending queue | **VERIFIED** |
| **`RATE_LIMIT`** | `scenario="RATE_LIMIT"` | HTTP 429 quota backoff | Backoff triggered with retry-after | **VERIFIED** |
| **`DOWNTIME`** | `scenario="DOWNTIME"` | Trips Circuit Breaker to `OPEN`, routes to officer | Circuit tripped to `OPEN`, routed to manual review | **VERIFIED** |
| **`SIGNED_RESPONSE`** | `scenario="SUCCESS"` | Cryptographic HMAC-SHA256 signature verification | Signature valid and verified | **VERIFIED** |
| **`OFFICER_MANUAL`** | `POST /verify-manual` | Provenance elevated to `OFFICER_VERIFIED` | Distinct from `BANK_CONFIRMED`, logged in audit | **VERIFIED** |

---

### 4. Hero Case Cross-Document Reconciliation Result

- **Target Instrument**: `BNB-DEL-HERO-1000` (FDR ID: `5`)
- **Institution**: National Institute of Technology & Science
- **Illustrative Deposit Amount**: ₹10,00,000.00
- **Cross-Document Reconciliation Table**:

| Field Name | Status | FDR Certificate Evidence | Bank Confirmation Letter Evidence | Discrepancy Summary |
|:-----------|:-------|:-------------------------|:-----------------------------------|:--------------------|
| **`fdr_number`** | `MATCH` | `BNB-DEL-HERO-1000` (Page 1) | `BNB-DEL-HERO-1000` (Page 1) | None (Exact match) |
| **`amount`** | `MATCH` | `1000000.0` (Page 1) | `1000000.0` (Page 1) | None (Exact match) |
| **`bank_name`** | `MATCH` | `Bharat National Bank` (Page 1) | `Bharat National Bank` (Page 1) | None (Exact match) |
| **`issue_date`** | `MATCH` | `2024-11-15` (Page 1) | `2024-11-15` (Page 1) | None (Exact match) |
| **`maturity_date`** | `MISMATCH` | `2032-11-15` (Page 1, bbox: `[120.0, 280.0, 240.0, 300.0]`) | `2026-11-15` (Page 1, bbox: `[110.0, 290.0, 230.0, 310.0]`) | **Discrepancy: FDR Certificate states 2032-11-15, but Bank Letter certifies 2026-11-15 (6-year gap)** |

---

### 5. Architectural Safeguards Verified

1. **Statutory Non-Genuine Wording**: Every bank response uses `"available checks passed"` or `"not confirmed"`. Never uses `"genuine"`.
2. **Advisory Risk Indicator**: Risk scores are termed `"review priority indicator"`, never `"fraud probability"`.
3. **Non-Destructive Lineage**: Renewals create linked successor instruments; original instruments remain permanently as `SUPERSEDED`.
4. **Append-Only Cryptographic Audit**: Every verification mutation computes $H_n = 	ext{SHA256}(H_{n-1} \parallel 	ext{payload}_n)$ and appends to the immutable audit chain.
