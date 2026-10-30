# DepoSafe - AICTE FDR Intelligence & Management Portal
### AI-Assisted, Human-in-the-Loop Security Deposit / Fixed Deposit Receipt Intelligence Portal
**Developed for the AICTE Regulation Bureau &bull; Smart India Hackathon Grand Finale**

[![Tests](https://img.shields.io/badge/pytest-15%20passed-brightgreen.svg)]()
[![Frontend](https://img.shields.io/badge/Next.js-14%20App%20Router-blue.svg)]()
[![Backend](https://img.shields.io/badge/FastAPI-Python%203.11-teal.svg)]()
[![Audit](https://img.shields.io/badge/SHA256-Hash%20Chained-indigo.svg)]()
[![Empirical Benchmark](https://img.shields.io/badge/Field%20F1-100.0%25-success.svg)]()

---

## 1. Executive Summary & Judging Lens

Under the AICTE Approval Process Handbook (APH), technical institutions must pledge fixed deposits as security deposits (jointly in favor of the Regional Officer, AICTE and Society/Trust) to obtain approval, establish new institutions, or introduce new programs.

**DepoSafe** replaces manual verification with an end-to-end, AI-assisted, human-in-the-loop regulatory platform:
- **Zero Black-Box Transparency**: 4-Level field provenance traces every value across `SUBMITTED` &rarr; `AI_EXTRACTED` &rarr; `BANK_CONFIRMED` &rarr; `OFFICER_VERIFIED`.
- **Document Forensics**: Detects Canva/Photoshop/GIMP editing signatures in PDF metadata, computes perceptual image hashes (`imagehash.phash`) for template reuse across institutions, and checks scan blur.
- **Bank Verification Adapter Pattern**: Sits behind a clean `BankVerificationAdapter` interface with official watermarks (`SIMULATED, not a real bank verification`) and statutory wording (`available checks passed` vs `not confirmed`, never "genuine").
- **Explainable Advisory Risk Engine**: Computes a "Review Priority Indicator" (0 to 100, never "fraud probability"). Every flag shows explicit reason, evidence, and rule trigger. Officers can override with mandatory recorded justification.
- **Versioned Compliance Regulations**: Uses versioned configuration (`APH-2024-27.v1`) with effective dates. Deposit amounts, tenure, and concessions are editable illustrative placeholders.
- **Ecosystem Relationship Graph**: NetworkX backend + React Flow interactive canvas mapping Trust &rarr; Institution &rarr; FDR &rarr; Bank &rarr; Signatory. Detects cross-college trusts and shared signatories.
- **Controllable Demo Clock**: Advances simulated "today" (+15, +30, +90 days) during live demos to trigger T-15 escalations and predictive monthly workload forecasts.
- **Cryptographic Hash Chain Audit**: Blockchain-grade append-only ledger: $H_n = \text{SHA256}(H_{n-1} \parallel \text{event}_n)$ with one-click mathematical integrity verification.
- **Empirical Evaluation Harness**: Pre-packaged benchmark runner on ground-truth labelled synthetic data measuring extraction precision, recall, F1, anomaly accuracy, and processing latency.

---

## 2. Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Celery + Redis (beat scheduler)
- **Database & Storage**: PostgreSQL (primary), SQLite (zero-config local dev), MinIO/Local S3-compatible storage
- **Document AI & Forensics**: PyMuPDF (`fitz`), OpenCV, `imagehash` (pHash/dHash), `reportlab`, `scikit-learn`
- **Graph Intelligence**: NetworkX (backend analytics) + React Flow (frontend canvas)
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS + Lucide Icons + Recharts + `canvas-confetti`
- **Auth & Security**: JWT (access/refresh) + RBAC (5 roles) + Argon2 password hashing
- **Testing**: pytest (15 unit/forensics/workflow/E2E tests), Playwright-compatible flow harnesses

---

## 3. Quick Start (Run Everything)

### Option A: Complete Docker Compose
```bash
# 1. Start all services (PostgreSQL, Redis, FastAPI Backend, Celery Worker, Celery Beat, Next.js Frontend)
make up

# 2. Open Portal in Browser
# Frontend: http://localhost:3000
# Backend API Docs: http://localhost:8000/docs
```

### Option B: Local Direct Execution (Zero External Daemons)
```bash
# 1. Run Backend Server (FastAPI on port 8000)
make run-backend

# 2. Run Frontend App (Next.js on port 3000 in a separate terminal)
make run-frontend

# 3. Seed Database with Realistic Synthetic FDRs & Genesis Ledger
make seed

# 4. Run Complete Test Suite (15 tests)
make test

# 5. Run Automated 90-Second Demo Sequence
make demo
```

---

## 4. Default Demo Accounts & Roles

Switch between roles with 1 click in the portal header:

| Role | Email | Password | Permissions & Responsibility |
|------|-------|----------|------------------------------|
| **System Admin** | `admin@deposafe.aicte.gov.in` | `Password@123` | Full access, APH rule version updates, demo clock control, audit ledger verification |
| **Verification Officer** | `officer@deposafe.aicte.gov.in` | `Password@123` | Document AI review, 4-level provenance verification, mock CBS verification, officer override |
| **Regional Officer** | `ro.north@deposafe.aicte.gov.in` | `Password@123` | Regional workload forecasting, inspection oversight, renewal endorsement |
| **Competent Authority** | `director.approval@aicte-india.org` | `Password@123` | **Sole role authorized to approve deposit release / refund orders** |
| **Institution User** | `institution1@vidya.edu.in` | `Password@123` | Deposit registration, document upload, renewal request, closure release request |

---

## 5. 90-Second Grand Finale Demo Script

1. **Header & Controllable Demo Clock**: Notice the live simulated date. Click **+30 Days** to advance the clock live and watch maturity escalation queues update instantly.
2. **Dashboard & Workload Forecast**: View the Recharts monthly maturity bar chart and review priority alerts. Click the **90-Second Demo Tour** button for a guided walkthrough.
3. **FDR Registry & Review Priority**: Click into **FDR #2** (Punjab National Bank). Notice the high review priority indicator (75/100).
4. **4-Level Field Provenance**:
   - Inspect the provenance matrix comparing Submitted (₹ 25L) vs AI Extracted (₹ 15L deficit).
   - Click **Verify** on any field to test human-in-the-loop officer confirmation.
5. **Document Forensics**: Switch to the **Document Forensics** tab. View the computed SHA256 byte hash, perceptual hash (`b4a8e3d2...`), and Canva/Photoshop tool tampering alert.
6. **Simulated Bank Verification**: Switch to **Human-in-the-Loop Actions**. Click **Simulate Bank Verification**. Note the official disclaimer: *"SIMULATED, not a real bank verification"*.
7. **Officer Override**: Click **Officer Override**, enter a justification (*"Special Council dispensation under APH 4.8"*), and observe the score adjust to 12.0 (Low).
8. **Linked Renewal Chain**: Click **Renew Deposit**. Enter a new FDR number. Notice that the old instrument is **NEVER overwritten**; it transitions to `RENEWED_SUPERSEDED` and links to the new successor.
9. **Competent Authority Release**: Switch role to **Competent Authority**. Open **FDR #4** (Release Requested). Click **Authorize Official Release** and issue release order `AICTE/REL/2024/099`. Regular officers cannot approve this.
10. **Ecosystem Graph**: Open the **Ecosystem Graph** tab to visualize the React Flow canvas linking Shree Vidya Educational Trust to both Vidya Tech and Vidya Polytechnic with shared signatory Dr. Ramesh Sharma.
11. **Cryptographic Audit Chain**: Open the **Cryptographic Audit** tab. Click **Verify Hash Chain Integrity**. The server traverses all blocks from Genesis ($H_0$) and mathematically validates $H_n = \text{SHA256}(H_{n-1} \parallel \text{event}_n)$.
12. **Empirical Evaluation Harness**: Open the **Evaluation Harness** tab. Click **Run Live Empirical Benchmark**. View 100% extraction F1, 100% anomaly accuracy, and ~28ms processing latency measured on ground truth.

---

## 6. Non-Negotiable Statutory Safeguards Checklist

- [x] **Advisory AI Only**: AI never makes legal determinations. Passing checks strictly state *"available checks passed"* vs *"not confirmed"*, never *"genuine"*.
- [x] **Review Priority Indicator**: Score strictly worded *"review priority indicator"*, never *"fraud probability"*. Officers can override with recorded justification.
- [x] **Non-Destructive Renewal**: Renewing a deposit creates a linked successor instrument; old instrument becomes `RENEWED_SUPERSEDED`. Existing instruments are never overwritten.
- [x] **Composite Key Indexing**: Bank FDR number is indexed with `(bank_name, fdr_number)`, not assumed globally unique.
- [x] **Competent Authority Gating**: Sole role authorized to authorize deposit release or forfeiture.
- [x] **Append-Only Cryptographic Hash Chain**: $H_n = \text{SHA256}(H_{n-1} \parallel \text{event}_n)$ verified through formal mathematical traversal.
- [x] **Bilingual Gov-Tech UI**: English and हिन्दी toggleable in header.

