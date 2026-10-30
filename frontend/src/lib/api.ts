const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("deposafe_token") : null;
  const headers = new Headers(options.headers || {});
  
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || "API request failed");
  }

  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string = "Password@123") =>
    fetchAPI("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  getMe: () => fetchAPI("/auth/me"),

  // FDRs
  getFDRs: (params: { status?: string; risk_level?: string } = {}) => {
    const searchParams = new URLSearchParams();
    if (params.status) searchParams.set("status_filter", params.status);
    if (params.risk_level) searchParams.set("risk_level", params.risk_level);
    const query = searchParams.toString() ? `?${searchParams.toString()}` : "";
    return fetchAPI(`/fdrs${query}`);
  },
  getFDRDetail: (id: number) => fetchAPI(`/fdrs/${id}`),
  createFDR: (data: any) => fetchAPI("/fdrs", { method: "POST", body: JSON.stringify(data) }),
  uploadDocument: (id: number, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetchAPI(`/fdrs/${id}/upload-document`, { method: "POST", body: formData });
  },
  verifyBank: (id: number) => fetchAPI(`/fdrs/${id}/verify-bank`, { method: "POST", body: JSON.stringify({ fdr_id: id }) }),
  verifyField: (id: number, field_name: string, verified_value: string, officer_notes?: string) =>
    fetchAPI(`/fdrs/${id}/verify-field`, {
      method: "POST",
      body: JSON.stringify({ field_name, verified_value, officer_notes })
    }),
  overrideReview: (id: number, justification: string, adjusted_score?: number, new_status?: string) =>
    fetchAPI(`/fdrs/${id}/override`, {
      method: "POST",
      body: JSON.stringify({ justification, adjusted_score, new_status })
    }),
  renewFDR: (id: number, data: any) =>
    fetchAPI(`/fdrs/${id}/renew`, { method: "POST", body: JSON.stringify(data) }),
  requestRelease: (id: number, justification: string, noc_reference: string) =>
    fetchAPI(`/fdrs/${id}/request-release`, {
      method: "POST",
      body: JSON.stringify({ justification, noc_reference })
    }),
  authorizeRelease: (id: number, approved: boolean, release_order_ref: string, remarks: string) =>
    fetchAPI(`/fdrs/${id}/authorize-release`, {
      method: "POST",
      body: JSON.stringify({ approved, release_order_ref, remarks })
    }),

  // Demo Clock
  getClock: () => fetchAPI("/demo-clock"),
  advanceClock: (days: number) =>
    fetchAPI("/demo-clock/advance", { method: "POST", body: JSON.stringify({ days }) }),
  setClock: (target_date: string) =>
    fetchAPI("/demo-clock/set", { method: "POST", body: JSON.stringify({ target_date }) }),

  // Workload & Forecasting
  getWorkload: () => fetchAPI("/workload"),

  // Graph
  getGraph: (highlight_fdr_id?: number) => {
    const query = highlight_fdr_id ? `?highlight_fdr_id=${highlight_fdr_id}` : "";
    return fetchAPI(`/graph/ecosystem${query}`);
  },

  // Audit
  getAuditLedger: (limit: number = 50) => fetchAPI(`/audit/ledger?limit=${limit}`),
  verifyAuditChain: () => fetchAPI("/audit/verify"),

  // Evidence Pack
  getEvidencePackUrl: (id: number) => `${API_BASE_URL}/fdrs/${id}/evidence-pack`,
  getPassport: (id: number) => fetchAPI(`/fdrs/${id}/passport`),
  getLineagePassport: (lineage_id: string) => fetchAPI(`/fdrs/lineage/${lineage_id}/passport`),
  getReconciliation: (id: number) => fetchAPI(`/fdrs/${id}/reconciliation`),
  verifyManual: (id: number, data: { method: string; reference_number: string; remarks: string; evidence_document_id?: number }) =>
    fetchAPI(`/fdrs/${id}/verify-manual`, { method: "POST", body: JSON.stringify(data) }),

  // Institutions
  getInstitutions: () => fetchAPI("/institutions"),
  getInstitution: (id: number) => fetchAPI(`/institutions/${id}`),
  getInstitutionFDRs: (id: number) => fetchAPI(`/institutions/${id}/fdrs`),
  getInstitutionComplianceScore: (id: number) => fetchAPI(`/compliance/institution/${id}/score`),

  // Lifecycle & Maturity Radar (Phase 8)
  getPriorityQueue: () => fetchAPI("/lifecycle/renewal/priority-queue"),
  getMaturityCalendar: (month?: number, year?: number) => {
    const params = new URLSearchParams();
    if (month) params.set("month", month.toString());
    if (year) params.set("year", year.toString());
    const query = params.toString() ? `?${params.toString()}` : "";
    return fetchAPI(`/lifecycle/calendar/maturities${query}`);
  },
  getNotifications: (acknowledged?: boolean) => {
    const query = acknowledged !== undefined ? `?acknowledged=${acknowledged}` : "";
    return fetchAPI(`/lifecycle/radar/notifications${query}`);
  },
  acknowledgeNotification: (id: number) =>
    fetchAPI(`/lifecycle/radar/notifications/${id}/acknowledge`, { method: "POST" }),
  runRadarScan: () => fetchAPI("/lifecycle/radar/scan", { method: "POST" }),
  getZeroGap: (fdr_id: number) => fetchAPI(`/lifecycle/renewal/${fdr_id}/zero-gap`),
  getWorkloadForecast: () => fetchAPI("/lifecycle/predictive/workload-forecast"),
  getRenewalPropensity: (fdr_id: number) => fetchAPI(`/lifecycle/predictive/fdr/${fdr_id}/propensity`),

  // Release & Refund Lifecycle (Phase 9)
  getReleaseRequests: () => fetchAPI("/release/requests"),
  getReleaseReadiness: (fdr_id: number) => fetchAPI(`/release/fdr/${fdr_id}/readiness`),
  submitReleaseRequest: (fdr_id: number, data: { reason: string; amount_requested: number; remarks?: string }) =>
    fetchAPI(`/release/fdr/${fdr_id}/request`, { method: "POST", body: JSON.stringify(data) }),
  scrutinizeReleaseRequest: (fdr_id: number, data: { action: string; officer_remarks?: string }) =>
    fetchAPI(`/release/fdr/${fdr_id}/scrutiny`, { method: "POST", body: JSON.stringify(data) }),
  authorizeReleaseRequest: (fdr_id: number, data: { action: string; typed_justification: string; release_order_ref: string }) =>
    fetchAPI(`/release/fdr/${fdr_id}/authorize`, { method: "POST", body: JSON.stringify(data) }),
  disburseAndCloseRelease: (fdr_id: number, data: { disbursement_ref: string; remarks?: string }) =>
    fetchAPI(`/release/fdr/${fdr_id}/disburse-and-close`, { method: "POST", body: JSON.stringify(data) }),

  // Compliance Engine (Phase 7)
  getActiveRules: () => fetchAPI("/compliance/rules/active"),
  getRuleHistory: () => fetchAPI("/compliance/rules/history"),
  getRuleDiff: (base_version: string, compare_version: string) =>
    fetchAPI(`/compliance/rules/diff?base_version=${base_version}&compare_version=${compare_version}`),
  runImpactReport: (new_rule_data: any) =>
    fetchAPI("/compliance/rules/dry-run-impact", { method: "POST", body: JSON.stringify(new_rule_data) }),
  publishRuleVersion: (data: { version_tag: string; effective_from: string; migration_strategy?: string }) =>
    fetchAPI("/compliance/rules/publish", { method: "POST", body: JSON.stringify(data) }),

  // Evaluation
  getEvaluationLatest: () => fetchAPI("/evaluation/latest"),
  runEvaluation: () => fetchAPI("/evaluation/run", { method: "POST" }),
};

