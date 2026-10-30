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

  // Compliance
  getActiveRules: () => fetchAPI("/compliance/rules/active"),

  // Evaluation
  getEvaluationLatest: () => fetchAPI("/evaluation/latest"),
  runEvaluation: () => fetchAPI("/evaluation/run", { method: "POST" }),
};

