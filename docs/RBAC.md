# DepoSafe - Role-Based Access Control (RBAC) Specification
## AICTE Regulation Bureau &bull; Security Deposit Governance

---

### 1. Role Hierarchy & Responsibilities

| Role Identifier | Role Title | Description & Statutory Mandate |
|---|---|---|
| `INSTITUTION_USER` | Institution User / Principal | Authorized representative of Society/Trust/College. Can submit deposits, upload certificates, initiate renewals, and request closure release for **their own institution only**. |
| `VERIFICATION_OFFICER` | Verification Officer | Technical verification officer in Regulation Bureau. Conducts Document AI scrutiny, field provenance verification, queries simulated bank CBS adapter, and records justified overrides. |
| `REGIONAL_OFFICER` | Regional Officer (RO) | Oversees regional jurisdiction (e.g. NWRO, WRO, SRO). Endorses compliance inspections, reviews regional workload forecasts, and recommends release requests. |
| `COMPETENT_AUTHORITY` | Senior Officer / Competent Authority | Executive authority (Member Secretary / Director, AICTE). **Sole authority empowered by regulation to approve deposit release, refund, or forfeiture.** |
| `SYSTEM_ADMIN` | System Administrator | Manages versioned APH regulation rules, user accounts, integration adapters, and the controllable Demo Clock. |
| `AUDITOR` | Regulatory / Vigilance Auditor | Independent oversight role. Read-only access to the append-only cryptographic hash chain, audit logs, and provenance history. Cannot modify records. |

---

### 2. Permissions Matrix

| Resource / Action | Endpoint | `INSTITUTION_USER` | `VERIFICATION_OFFICER` | `REGIONAL_OFFICER` | `COMPETENT_AUTHORITY` | `SYSTEM_ADMIN` | `AUDITOR` |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Register New FDR** | `POST /api/v1/fdrs` |  (Own Inst) |  |  |  |  | ❌ |
| **Upload Document Scan** | `POST /api/v1/fdrs/{id}/upload-document` |  (Own Inst) |  |  |  |  | ❌ |
| **View Own FDRs** | `GET /api/v1/fdrs` |  (Filtered) |  |  |  |  |  (Read) |
| **View All Institutional FDRs** | `GET /api/v1/fdrs` | ❌ |  |  |  |  |  (Read) |
| **Inspect 4-Level Provenance** | `GET /api/v1/fdrs/{id}` |  (Own Inst) |  |  |  |  |  |
| **Trigger Bank CBS Adapter** | `POST /api/v1/fdrs/{id}/verify-bank` | ❌ |  |  |  |  | ❌ |
| **Verify Provenance Field** | `POST /api/v1/fdrs/{id}/verify-field` | ❌ |  |  |  |  | ❌ |
| **Record Manual Evidence** | `POST /api/v1/fdrs/{id}/verify-manual` | ❌ |  |  |  |  | ❌ |
| **Officer Review Override** | `POST /api/v1/fdrs/{id}/override` | ❌ |  (Mandatory Justification) |  | ❌ |  | ❌ |
| **Initiate FDR Renewal** | `POST /api/v1/fdrs/{id}/renew` |  (Own Inst) |  |  |  |  | ❌ |
| **Request Deposit Release** | `POST /api/v1/fdrs/{id}/request-release` |  (Own Inst) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Recommend Release Request** | `POST /api/v1/fdrs/{id}/recommend-release` | ❌ |  |  | ❌ |  | ❌ |
| **Authorize Deposit Release** | `POST /api/v1/fdrs/{id}/authorize-release` | ❌ | ❌ | ❌ |  |  | ❌ |
| **Advance / Set Demo Clock** | `POST /api/v1/demo-clock/*` | ❌ |  |  | ❌ |  | ❌ |
| **Update Compliance Rules** | `POST /api/v1/compliance/rules/update` | ❌ | ❌ | ❌ | ❌ |  | ❌ |
| **View Audit Ledger** | `GET /api/v1/audit/ledger` | ❌ | ❌ | ❌ |  |  |  |
| **Verify Audit Chain** | `GET /api/v1/audit/verify` |  |  |  |  |  |  |
| **Run Evaluation Harness** | `POST /api/v1/evaluation/run` | ❌ | ❌ | ❌ | ❌ |  | ❌ |

---

### 3. Data Scoping & Multi-Tenancy Enforcement

1. **Institution Isolation**:
   - Institutional users are cryptographically bounded by `current_user.institution_id`.
   - Any attempt to query or register a deposit for a foreign `institution_id` results in `HTTP 403 Forbidden`.
2. **Four-Eyes Release Principle**:
   - The user who requested a release cannot approve it.
   - The verification officer who recommended a release cannot authorize the final order.
   - The Competent Authority requires independent inspection clearance and university NOC.
3. **Audit Immutability**:
   - Neither Administrator nor Competent Authority can edit or delete an audit log entry.
   - The ledger is append-only with $H_n = \text{SHA256}(H_{n-1} \parallel \text{event}_n)$.

