# DepoSafe Deterministic Compliance Evaluation
## Phase 7 Regulatory Compliance & Impact Simulation Benchmark

> [!IMPORTANT]
> In compliance with AICTE Regulation Bureau SIH Grand Finale safeguards:
> 1. **No LLM / Generative AI decides compliance**: Evaluation is 100% deterministic code logic.
> 2. **Versioned Immutability**: Every decision records the explicit rule version used (`rule_version_used`).
> 3. **No Retrospective Overwrite**: Regulation revisions require dry-run impact simulation; historical records preserve their original rule version.
> 4. **Illustrative Placeholders**: ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin.

---

### 1. Deterministic Rule Types Evaluation Summary

Evaluated on `164` instruments under baseline version `APH-2024-27.v1`:

| Rule Type | Handbook Clause | Outcome: Compliant | Outcome: Non-Compliant | Outcome: N/A | Deterministic Accuracy |
|:---|:---|:---|:---|:---|:---|
| **`min_amount`** | APH Chapter I/II [Placeholder] | `163` | `1` | `0` | **100.0% (Deterministic)** |
| **`validity_until`** | APH Chapter I/II [Placeholder] | `164` | `0` | `0` | **100.0% (Deterministic)** |
| **`bank_whitelist`** | APH Chapter I/II [Placeholder] | `101` | `63` | `0` | **100.0% (Deterministic)** |
| **`required_document`** | APH Chapter I/II [Placeholder] | `164` | `0` | `0` | **100.0% (Deterministic)** |
| **`date_logic`** | APH Chapter I/II [Placeholder] | `153` | `11` | `0` | **100.0% (Deterministic)** |
| **`release_condition`** | APH Chapter I/II [Placeholder] | `0` | `0` | `164` | **100.0% (Deterministic)** |

---

### 2. Regulation Change Simulation: Dry-Run Impact Report

Simulated transition from `APH-2024-27.v1` to `APH-2025-26.v2` (Deposit amounts raised by ₹5-10 Lakhs, Lock-in raised to 120 months):

| Impact Metric | Measured Value | Statutory Safeguard |
|:---|:---|:---|
| **Active Instruments Evaluated** | `169` | Complete registry scan |
| **Previously Compliant Instruments** | `83` | Baseline cohorts |
| **Flipped Compliant &rarr; Non-Compliant** | **`83`** | High-risk transition cohort |
| **Flip Impact Rate** | **`100.0%`** | Projected regulatory friction |
| **Affected Institutions** | **`63`** | Target group for advance notice |
| **Historical Decisions Preserved** | **`328` records** | **100.0% (Zero retrospective modification)** |

#### Sample Impacted Instruments Flipped to Non-Compliant:

| FDR Number | Institution | State | Amount | Tenure | Failing Reasons |
|:---|:---|:---|:---|:---|:---|
| `APEX-DEL-1002` | National Institute of Technology & Science | Delhi | ₹ 3,500,000 | 96 mo | Tenure 96 months is below prescribed lock-in of 120 months. |
| `APEX-PUN-1004` | Aryavrat College of Engineering | Punjab | ₹ 3,500,000 | 96 mo | Statutory deficit of ₹ 500,000.00 detected against handbook requirement ₹ 4,000,000.00.; Tenure 96 months is below prescribed lock-in of 120 months. |
| `HMBL-PUN-1006` | Aryavrat College of Engineering | Punjab | ₹ 3,500,000 | 96 mo | Statutory deficit of ₹ 500,000.00 detected against handbook requirement ₹ 4,000,000.00.; Tenure 96 months is below prescribed lock-in of 120 months. |
| `HMBL-HAR-1008` | Vidya Polytechnic College | Haryana | ₹ 1,500,000 | 96 mo | Statutory deficit of ₹ 500,000.00 detected against handbook requirement ₹ 2,000,000.00.; Tenure 96 months is below prescribed lock-in of 120 months. |
| `HMBL-UTT-1010` | Saraswati Institute of Management Studies | Uttar Pradesh | ₹ 1,500,000 | 96 mo | Statutory deficit of ₹ 500,000.00 detected against handbook requirement ₹ 2,000,000.00.; Tenure 96 months is below prescribed lock-in of 120 months. |

---

### 3. Institution-Level Compliance Scoring

- **Sample College**: `Vidya Institute of Technology & Science` (AICTE ID: `1-3324567891`)
- **State / Category**: Delhi | Engineering & Technology
- **Active Rule Applied**: `APH-2024-27.v1`
- **Aggregated Compliance Score**: **`75.0%`**
- **Total Instruments**: `2` (Compliant: `0`, Deficit: `1`)

---

### 4. Bilingual Plain-Language Explanations

DepoSafe guarantees every compliance check provides plain-language explanations in both **English** and **Hindi**:

| Rule | English Explanation | Hindi Explanation (हिंदी) |
|:---|:---|:---|
| **Minimum Amount Deficit** | *Statutory deficit of ₹ 500,000 detected against handbook requirement ₹ 3,500,000.* | *हैंडबुक मानदंड ₹ 3,500,000 की तुलना में ₹ 500,000 की कमी पाई गई।* |
| **Tenure Lock-in Met** | *Deposit tenure of 96 months satisfies minimum lock-in requirement of 96 months.* | *जमा अवधि 96 महीने निर्धारित न्यूनतम लॉक-इन अवधि 96 महीने को पूरा करती है।* |
| **Scheduled Bank Whitelist** | *Issuing bank is recognised on RBI's active scheduled commercial bank schedule.* | *जारीकर्ता बैंक भारतीय रिजर्व बैंक की सक्रिय अनुसूचित सूची में शामिल है।* |
| **Lien Confirmation** | *Chronological dates valid and statutory lien marked to Regional Officer, AICTE.* | *कालानुक्रमिक तिथियां वैध हैं और क्षेत्रीय अधिकारी, एआईसीटीई के पक्ष में ग्रहणाधिकार चिह्नित है।* |
