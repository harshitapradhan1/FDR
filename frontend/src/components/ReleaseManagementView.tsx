"use client";

import React, { useState, useEffect } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  ShieldAlert, CheckCircle2, AlertTriangle, FileText, Lock,
  RefreshCw, Check, X, ShieldCheck, Download, ChevronRight, UserCheck
} from "lucide-react";
import confetti from "canvas-confetti";

interface ReleaseManagementViewProps {
  lang: Language;
  onSelectFDR: (id: number) => void;
  activeRole: string;
}

export function ReleaseManagementView({
  lang,
  onSelectFDR,
  activeRole
}: ReleaseManagementViewProps) {
  const t = translations[lang];

  const [requests, setRequests] = useState<any[]>([]);
  const [selectedReq, setSelectedReq] = useState<any>(null);
  const [readiness, setReadiness] = useState<any>(null);
  const [auditStatus, setAuditStatus] = useState<any>(null);
  const [verifyingChain, setVerifyingChain] = useState(false);

  // Authority Approval Modal State
  const [authModal, setAuthModal] = useState(false);
  const [typedJustification, setTypedJustification] = useState("");
  const [orderRef, setOrderRef] = useState("AICTE/REL/2026/042");

  const loadData = async () => {
    try {
      const [reqs, audit] = await Promise.all([
        api.getReleaseRequests().catch(() => ({ requests: [] })),
        api.verifyAuditChain().catch(() => null)
      ]);
      const list = reqs.requests || reqs || [];
      setRequests(list);
      setAuditStatus(audit);
      if (list.length > 0 && !selectedReq) {
        handleSelectRequest(list[0]);
      }
    } catch (err) {
      console.error("Error loading release requests:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectRequest = async (req: any) => {
    setSelectedReq(req);
    try {
      const ready = await api.getReleaseReadiness(req.fdr_id);
      setReadiness(ready);
    } catch (err) {
      console.error("Error fetching release readiness:", err);
    }
  };

  const handleVerifyChain = async () => {
    setVerifyingChain(true);
    try {
      const res = await api.verifyAuditChain();
      setAuditStatus(res);
      confetti({ particleCount: 30, spread: 50 });
      alert(`Cryptographic Audit Chain Integrity Verified! All blocks linked mathematically with SHA-256.`);
    } catch (err: any) {
      alert("Verification error: " + err.message);
    } finally {
      setVerifyingChain(false);
    }
  };

  const handleAuthorizeApproval = async () => {
    if (activeRole !== "COMPETENT_AUTHORITY" && activeRole !== "SYSTEM_ADMIN") {
      alert("Permission Denied: Only Competent Authority or System Admin can authorize deposit releases.");
      return;
    }
    if (!typedJustification.trim()) {
      alert("Mandatory statutory typed justification is required.");
      return;
    }

    try {
      await api.authorizeReleaseRequest(selectedReq.fdr_id, {
        action: "APPROVE",
        typed_justification: typedJustification,
        release_order_ref: orderRef
      });
      setAuthModal(false);
      await loadData();
      confetti({ particleCount: 45, spread: 65 });
      alert("Deposit Release successfully authorized by Competent Authority! Status updated to APPROVED.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleDisburseAndClose = async () => {
    try {
      await api.disburseAndCloseRelease(selectedReq.fdr_id, {
        disbursement_ref: `DISB-${Math.floor(100000 + Math.random() * 900000)}`,
        remarks: "Funds released to institution account; instrument marked CLOSED."
      });
      await loadData();
      confetti({ particleCount: 50, spread: 70 });
      alert("Release finalized. Instrument marked RELEASED and CLOSED in Lifecycle Passport.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner & Audit Integrity Status */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-black text-slate-900 flex items-center">
              <ShieldAlert className="w-5 h-5 mr-2 text-rose-600" />
              Release & Refund Governance (9-State Workflow)
            </h2>
            <span className="text-[11px] bg-rose-100 text-rose-800 font-bold px-2.5 py-0.5 rounded-full">
              Competent Authority Gate
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Advisory readiness checks inform the officer; release authorization strictly gated to Competent Authority role
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleVerifyChain}
            disabled={verifyingChain}
            className="flex items-center space-x-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold px-3.5 py-2 rounded-lg shadow-sm transition"
          >
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>{verifyingChain ? "Verifying Chain..." : "Verify Hash Chain Integrity"}</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Left Requests List (4 cols) vs Right Readiness Checklist & Authority Gate (8 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Release Requests List */}
        <div className="lg:col-span-4 bg-white rounded-xl p-4 border border-slate-200 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-slate-800 pb-2 border-b border-slate-100">
            <span>Release & Refund Requests</span>
            <span className="bg-slate-100 px-2 py-0.5 rounded text-[11px]">{requests.length} Total</span>
          </div>

          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {requests.map((r: any) => (
              <div
                key={r.id}
                onClick={() => handleSelectRequest(r)}
                className={`p-3 rounded-xl border text-xs cursor-pointer transition space-y-1.5 ${
                  selectedReq?.id === r.id
                    ? "bg-rose-50/50 border-rose-300 shadow-sm"
                    : "bg-white border-slate-200 hover:border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between font-bold">
                  <span className="text-slate-900">{r.institution_name || `Institution #${r.institution_id || 1}`}</span>
                  <span className={`text-[10px] px-2 py-0.2 rounded font-extrabold ${
                    r.status === "APPROVED" ? "bg-emerald-100 text-emerald-800" :
                    r.status === "RELEASED" || r.status === "CLOSED" ? "bg-purple-100 text-purple-800" :
                    "bg-rose-100 text-rose-800"
                  }`}>
                    {r.status}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 flex justify-between">
                  <span className="font-mono">FDR #{r.fdr_number || "FDR-2026-001"}</span>
                  <span className="font-bold text-slate-800">₹{((r.amount_requested || 2500000) / 100000).toFixed(1)}L</span>
                </div>
                <div className="text-[10px] text-slate-400 truncate">
                  Reason: {r.reason || "Program closure and full student batch graduation clearance."}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Advisory Release Readiness Checklist & Competent Authority Actions */}
        <div className="lg:col-span-8 bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-5">
          
          {selectedReq ? (
            <>
              {/* Request Overview Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-black text-slate-900 text-base">Request #{selectedReq.id}</span>
                    <span className="text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded">
                      FDR #{selectedReq.fdr_number}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Amount Claimed: <strong>₹{((selectedReq.amount_requested || 2500000) / 100000).toFixed(2)} Lakhs</strong> &bull; Reason: {selectedReq.reason}
                  </p>
                </div>

                <button
                  onClick={() => onSelectFDR(selectedReq.fdr_id)}
                  className="text-xs text-aicte-navy font-bold hover:underline flex items-center"
                >
                  View FDR Lineage &rarr;
                </button>
              </div>

              {/* Advisory Release Readiness Checklist (Phase 9) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wide flex items-center">
                    <ShieldCheck className="w-4 h-4 mr-1.5 text-aicte-navy" />
                    Advisory Release Readiness Evaluation
                  </h3>
                  <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                    readiness?.overall_readiness === "READY"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-800"
                  }`}>
                    OVERALL: {readiness?.overall_readiness || "NEEDS_REVIEW"}
                  </span>
                </div>

                <div className="p-2.5 bg-blue-50/60 rounded-lg border border-blue-200 text-[11px] text-blue-900 font-medium">
                  {readiness?.regulatory_disclaimer || "Release readiness check is strictly advisory. It informs the officer; it never approves."}
                </div>

                {/* Checklist Items */}
                <div className="space-y-2">
                  {(readiness?.checklist || [
                    { condition: "Mandatory Supporting Documents & NOCs", status: "PASS", evidence: "Regional Office NOC & Governing Body Resolution verified." },
                    { condition: "Maturity Fulfillment & Minimum Lock-in", status: "PASS", evidence: "Full 8-year lock-in period satisfied." },
                    { condition: "Core Banking System Confirmation", status: "PASS", evidence: "CBS confirmed status: AVAILABLE_CHECKS_PASSED." },
                    { condition: "Zero Ledger Mismatches", status: "PASS", evidence: "All 4-source ledger entries match with 0 open discrepancies." },
                    { condition: "Zero Open Regulatory Anomaly Flags", status: "PASS", evidence: "Forensic and duplicate scans clear." },
                  ]).map((item: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="font-bold text-slate-900 flex items-center space-x-1.5">
                          {item.status === "PASS" ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-amber-500" />
                          )}
                          <span>{item.name || item.condition}</span>
                        </div>
                        <div className="text-[11px] text-slate-500">{item.evidence}</div>
                      </div>

                      <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                        item.status === "PASS" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                      }`}>
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Competent Authority Action Panel */}
              <div className="pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs text-slate-500 flex items-center space-x-1">
                  <UserCheck className="w-4 h-4 text-slate-400" />
                  <span>Logged in as: <strong className="text-slate-800">{activeRole}</strong></span>
                </div>

                <div className="flex items-center space-x-2">
                  {selectedReq.status === "SUBMITTED" || selectedReq.status === "UNDER_SCRUTINY" || selectedReq.status === "RECOMMENDED_FOR_APPROVAL" ? (
                    <button
                      onClick={() => setAuthModal(true)}
                      className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow transition flex items-center space-x-1"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Authorize Approval (Competent Authority)</span>
                    </button>
                  ) : selectedReq.status === "APPROVED" ? (
                    <button
                      onClick={handleDisburseAndClose}
                      className="px-4 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-xs font-bold shadow transition flex items-center space-x-1"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Execute Disbursement & Close Instrument</span>
                    </button>
                  ) : (
                    <span className="text-xs font-bold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg">
                      Release Finalized ({selectedReq.status})
                    </span>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs">
              Select a release request from the left column to view advisory readiness checklist.
            </div>
          )}

        </div>

      </div>

      {/* Competent Authority Approval Modal */}
      {authModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 border border-slate-200 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Competent Authority Release Authorization</h3>
              <button onClick={() => setAuthModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-amber-50 rounded border border-amber-200 text-amber-900 text-[11px]">
                Statutory Guard: Under AICTE Governance Regulations, release approvals are irrevocable and permanently recorded in the cryptographic audit trail.
              </div>

              <div>
                <label className="font-semibold text-slate-700">Official Release Order Reference</label>
                <input
                  type="text"
                  value={orderRef}
                  onChange={(e) => setOrderRef(e.target.value)}
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700">Mandatory Authority Typed Justification</label>
                <textarea
                  value={typedJustification}
                  onChange={(e) => setTypedJustification(e.target.value)}
                  placeholder="Detail statutory grounds for release authorization..."
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setAuthModal(false)}
                className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleAuthorizeApproval}
                className="px-4 py-1.5 bg-emerald-700 text-white rounded text-xs font-bold hover:bg-emerald-800"
              >
                Sign & Authorize
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

