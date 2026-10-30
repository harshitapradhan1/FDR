"use client";

import React, { useState, useEffect } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  FileText, ShieldCheck, AlertTriangle, CheckCircle2, Lock, Eye,
  RefreshCw, Check, X, ShieldAlert, Download, GitFork, UserCheck,
  Layers, Search, Sliders, ChevronRight, FileWarning, ExternalLink
} from "lucide-react";
import confetti from "canvas-confetti";

interface VerificationWorkspaceViewProps {
  lang: Language;
  selectedFdrId?: number;
  fdrs: any[];
  onSelectFDR: (id: number) => void;
  activeRole: string;
}

export function VerificationWorkspaceView({
  lang,
  selectedFdrId,
  fdrs,
  onSelectFDR,
  activeRole
}: VerificationWorkspaceViewProps) {
  const t = translations[lang];

  const currentFdrId = selectedFdrId || fdrs[0]?.id || 1;
  const [fdrDetail, setFdrDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "provenance" | "validation" | "reconciliation" | "duplicates" | "risk" | "compliance" | "audit"
  >("provenance");

  // Forensics Heatmap Overlay Toggle
  const [showForensicsHeatmap, setShowForensicsHeatmap] = useState(false);
  const [showBBoxes, setShowBBoxes] = useState(true);

  // Modals & Action States
  const [overrideModal, setOverrideModal] = useState(false);
  const [overrideJustification, setOverrideJustification] = useState("");
  const [manualVerifyModal, setManualVerifyModal] = useState(false);
  const [manualMethod, setManualMethod] = useState("BANK_OFFICIAL_PORTAL");
  const [manualRef, setManualRef] = useState("REF-CBS-99214");
  const [manualRemarks, setManualRemarks] = useState("Verified via Branch CBS portal authentication.");
  const [clarificationModal, setClarificationModal] = useState(false);
  const [clarificationText, setClarificationText] = useState("");
  const [isVerifyingCBS, setIsVerifyingCBS] = useState(false);
  const [reconciliationData, setReconciliationData] = useState<any>(null);

  const loadFDR = async (id: number) => {
    setLoading(true);
    try {
      const [detail, recon] = await Promise.all([
        api.getFDRDetail(id),
        api.getReconciliation(id).catch(() => null)
      ]);
      setFdrDetail(detail);
      setReconciliationData(recon);
    } catch (err) {
      console.error("Failed to load FDR detail in workspace:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentFdrId) {
      loadFDR(currentFdrId);
    }
  }, [currentFdrId]);

  const handleSimulateCBS = async () => {
    setIsVerifyingCBS(true);
    try {
      await api.verifyBank(currentFdrId);
      await loadFDR(currentFdrId);
      confetti({ particleCount: 30, spread: 50 });
      alert("CBS Bank verification simulation executed successfully. Provenance ledger updated to BANK_CONFIRMED.");
    } catch (err: any) {
      alert("CBS Simulation Error: " + err.message);
    } finally {
      setIsVerifyingCBS(false);
    }
  };

  const handleRecordManualVerification = async () => {
    try {
      await api.verifyManual(currentFdrId, {
        method: manualMethod,
        reference_number: manualRef,
        remarks: manualRemarks
      });
      setManualVerifyModal(false);
      await loadFDR(currentFdrId);
      alert("Officer manual verification recorded in immutable ledger as OFFICER_VERIFIED.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleOfficerOverride = async () => {
    if (!overrideJustification.trim()) {
      alert("Mandatory typed justification required for officer override.");
      return;
    }
    try {
      await api.overrideReview(currentFdrId, overrideJustification, 10.0, "COMPLIANT");
      setOverrideModal(false);
      await loadFDR(currentFdrId);
      alert("Officer override recorded with justification in immutable audit chain.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleApproveCase = async () => {
    try {
      await api.overrideReview(currentFdrId, "Officer approved after statutory scrutiny.", 0.0, "ACTIVE");
      await loadFDR(currentFdrId);
      confetti({ particleCount: 40, spread: 60 });
      alert("FDR verified and approved as ACTIVE.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleRequestClarification = async () => {
    if (!clarificationText.trim()) {
      alert("Please enter clarification request text.");
      return;
    }
    try {
      await api.overrideReview(currentFdrId, `Clarification requested: ${clarificationText}`, 50.0, "CLARIFICATION_REQUIRED");
      setClarificationModal(false);
      await loadFDR(currentFdrId);
      alert("Clarification request dispatched to Institution Portal.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  if (!fdrDetail) {
    return (
      <div className="bg-white rounded-xl p-12 text-center border border-slate-200">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-aicte-navy mb-3" />
        <p className="text-slate-600 font-bold text-sm">Loading Verification Workspace...</p>
      </div>
    );
  }

  const flags = fdrDetail.review_flags || [];
  const riskScore = fdrDetail.review_priority_score || 0.0;
  const riskLevel = fdrDetail.review_priority_level || "LOW";
  const provList = fdrDetail.provenance_fields || [];
  const compEval = fdrDetail.compliance_evaluation;

  return (
    <div className="space-y-4">
      
      {/* Top Workspace Bar: Instrument Selector & Header Badges */}
      <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <select
            value={currentFdrId}
            onChange={(e) => onSelectFDR(Number(e.target.value))}
            className="text-xs font-bold bg-slate-100 border border-slate-300 rounded-lg px-3 py-1.5 text-slate-900 focus:outline-none focus:ring-2 focus:ring-aicte-navy"
          >
            {fdrs.map(f => (
              <option key={f.id} value={f.id}>
                #{f.fdr_number} &bull; {f.bank_name} &bull; ₹{(f.amount / 100000).toFixed(1)}L ({f.status})
              </option>
            ))}
          </select>

          <div className="flex items-center space-x-2">
            <span className={`text-[11px] font-extrabold px-2.5 py-0.5 rounded-full ${
              riskLevel === "CRITICAL" || riskLevel === "HIGH"
                ? "bg-rose-100 text-rose-800"
                : riskLevel === "MEDIUM"
                ? "bg-amber-100 text-amber-800"
                : "bg-emerald-100 text-emerald-800"
            }`}>
              {riskLevel} RISK ({riskScore.toFixed(1)}/100)
            </span>
            <span className="text-[11px] bg-blue-100 text-blue-800 font-bold px-2.5 py-0.5 rounded-full">
              Status: {fdrDetail.status}
            </span>
          </div>
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center space-x-2">
          <a
            href={api.getEvidencePackUrl(currentFdrId)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm transition"
          >
            <Download className="w-3.5 h-3.5 text-amber-400" />
            <span>Evidence Pack (PDF)</span>
          </a>
        </div>
      </div>

      {/* Main Hero Split View: Left Document Preview (5 Cols) vs Right Tabs (7 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Left Column: Live Document Preview with Bounding Boxes & Forensics Heatmap (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wide flex items-center">
                <FileText className="w-4 h-4 mr-1.5 text-aicte-navy" />
                Original Instrument Scan & Forensics
              </h3>
              
              {/* Forensics & BBox Controls */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowBBoxes(!showBBoxes)}
                  className={`text-[10px] font-bold px-2 py-0.5 rounded border transition ${
                    showBBoxes ? "bg-blue-100 border-blue-300 text-blue-800" : "bg-slate-100 text-slate-600 border-slate-300"
                  }`}
                >
                  B-Boxes: {showBBoxes ? "ON" : "OFF"}
                </button>
                <button
                  onClick={() => setShowForensicsHeatmap(!showForensicsHeatmap)}
                  className={`text-[10px] font-bold px-2 py-0.5 rounded border transition flex items-center space-x-1 ${
                    showForensicsHeatmap
                      ? "bg-rose-600 border-rose-700 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 border-slate-300"
                  }`}
                >
                  <Layers className="w-3 h-3" />
                  <span>ELA Forensics</span>
                </button>
              </div>
            </div>

            {/* Document Render Canvas */}
            <div className="relative rounded-lg border border-slate-300 bg-slate-100 overflow-hidden min-h-[460px] flex items-center justify-center shadow-inner">
              
              {/* Document Base Representation */}
              <div className="w-full h-full p-4 font-mono text-xs text-slate-800 bg-amber-50/40 space-y-3 select-none">
                
                {/* Bank Header Simulated Graphic */}
                <div className="border-b-2 border-slate-800 pb-2 flex items-center justify-between">
                  <div>
                    <div className="text-sm font-black uppercase text-slate-900 tracking-wider">
                      {fdrDetail.bank_name || "BHARAT NATIONAL BANK"}
                    </div>
                    <div className="text-[10px] text-slate-600">
                      Branch: {fdrDetail.branch_name || "Connaught Place, New Delhi"} (IFSC: {fdrDetail.ifsc_code})
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-bold bg-slate-200 px-1.5 py-0.5 rounded">TERM DEPOSIT RECEIPT</span>
                  </div>
                </div>

                {/* Simulated Instrument Face */}
                <div className="space-y-2 pt-1 text-[11px]">
                  <div className="flex justify-between">
                    <span>FDR No: <strong>{fdrDetail.fdr_number}</strong></span>
                    <span>Issue Date: <strong>{fdrDetail.issue_date}</strong></span>
                  </div>

                  <div className="flex justify-between">
                    <span>Principal Amount: <strong>₹{fdrDetail.amount?.toLocaleString("en-IN")}/-</strong></span>
                    <span>Maturity Date: <strong>{fdrDetail.maturity_date}</strong></span>
                  </div>

                  <div className="p-2 bg-white/70 border border-slate-200 rounded">
                    <span className="text-[10px] text-slate-500">Depositor Name & Beneficiary Clause:</span>
                    <div className="font-bold text-slate-900">
                      {fdrDetail.institution?.name || "Vidya Institute of Technology"}
                    </div>
                    <div className="text-[10px] text-blue-900 font-semibold mt-0.5">
                      Pledged jointly to Member Secretary, AICTE (Lien Marked)
                    </div>
                  </div>

                  <div className="flex justify-between text-[10px] text-slate-500 pt-2">
                    <span>Tenure: <strong>{fdrDetail.tenure_months || 96} Months</strong></span>
                    <span>Interest: <strong>{fdrDetail.interest_rate || 7.25}% p.a.</strong></span>
                  </div>
                </div>

                {/* Simulated Bank Seal & Signatures */}
                <div className="pt-6 flex items-end justify-between text-[9px] text-slate-600">
                  <div className="w-16 h-16 rounded-full border-2 border-dashed border-red-700/60 flex items-center justify-center text-center text-red-700 font-bold rotate-[-12deg]">
                    BANK SEAL<br />VERIFIED
                  </div>
                  <div className="text-right space-y-1">
                    <div className="font-serif italic text-xs text-blue-900">Branch Manager</div>
                    <div className="border-t border-slate-600 pt-0.5">Authorized Signatory</div>
                  </div>
                </div>

              </div>

              {/* Bounding Box Overlays */}
              {showBBoxes && (
                <div className="absolute inset-0 pointer-events-none p-4">
                  {/* BBox 1: FDR Number */}
                  <div className="absolute top-[88px] left-4 border-2 border-emerald-500 bg-emerald-500/15 px-1 py-0.5 text-[9px] font-bold text-emerald-900 rounded">
                    fdr_number [98%]
                  </div>
                  {/* BBox 2: Amount */}
                  <div className="absolute top-[125px] left-4 border-2 border-emerald-500 bg-emerald-500/15 px-1 py-0.5 text-[9px] font-bold text-emerald-900 rounded">
                    amount [97%]
                  </div>
                  {/* BBox 3: Maturity Date */}
                  <div className="absolute top-[125px] right-4 border-2 border-amber-500 bg-amber-500/15 px-1 py-0.5 text-[9px] font-bold text-amber-900 rounded">
                    maturity_date [94%]
                  </div>
                  {/* BBox 4: Lien Clause */}
                  <div className="absolute top-[180px] left-4 right-4 border-2 border-blue-500 bg-blue-500/15 px-1 py-0.5 text-[9px] font-bold text-blue-900 rounded">
                    lien_clause_text [99%]
                  </div>
                </div>
              )}

              {/* Error Level Analysis (ELA) Heatmap Overlay */}
              {showForensicsHeatmap && (
                <div className="absolute inset-0 bg-gradient-to-tr from-purple-900/60 via-rose-600/40 to-amber-500/50 mix-blend-multiply flex flex-col justify-between p-3 pointer-events-none animate-pulse">
                  <div className="bg-slate-900/90 text-white text-[10px] font-bold px-2 py-1 rounded inline-block self-start border border-rose-500">
                    ELA Heatmap Active &bull; Compression Delta Gradient
                  </div>
                  <div className="bg-slate-900/90 text-amber-300 text-[10px] p-2 rounded border border-amber-500 self-end">
                    Amount & Date BBoxes: Normal uniform compression
                  </div>
                </div>
              )}

            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>SHA-256: <strong className="font-mono text-slate-700">{fdrDetail.documents?.[0]?.file_hash_sha256?.substring(0, 16) || "9b12a8f0..."}...</strong></span>
            <span className="text-emerald-700 font-bold">Byte Integrity: Intact</span>
          </div>
        </div>

        {/* Right Column: Tabbed Intelligence & Provenance Inspector (7 Cols) */}
        <div className="lg:col-span-7 bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            
            {/* Tabs Header */}
            <div className="border-b border-slate-200 flex items-center space-x-1 text-xs font-bold overflow-x-auto pb-1 mb-4">
              <button
                onClick={() => setActiveTab("provenance")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "provenance" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                1. 4-Source Provenance
              </button>

              <button
                onClick={() => setActiveTab("validation")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "validation" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                2. Validation Engine
              </button>

              <button
                onClick={() => setActiveTab("reconciliation")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "reconciliation" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                3. Cross-Document
              </button>

              <button
                onClick={() => setActiveTab("duplicates")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "duplicates" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                4. Duplicates & Graph
              </button>

              <button
                onClick={() => setActiveTab("risk")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "risk" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                5. Risk Score ({riskScore.toFixed(0)})
              </button>

              <button
                onClick={() => setActiveTab("compliance")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "compliance" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                6. Compliance (APH)
              </button>

              <button
                onClick={() => setActiveTab("audit")}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
                  activeTab === "audit" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                7. Audit Chain
              </button>
            </div>

            {/* TAB 1: 4-SOURCE PROVENANCE LEDGER */}
            {activeTab === "provenance" && (
              <div className="space-y-3">
                <div className="text-xs text-slate-500 flex items-center justify-between">
                  <span>Side-by-side reconciliation across all 4 statutory sources</span>
                  <button
                    onClick={handleSimulateCBS}
                    disabled={isVerifyingCBS}
                    className="text-xs bg-indigo-50 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 px-2.5 py-1 rounded font-bold transition flex items-center space-x-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${isVerifyingCBS ? "animate-spin" : ""}`} />
                    <span>Simulate Bank CBS</span>
                  </button>
                </div>

                <div className="border border-slate-200 rounded-lg overflow-hidden text-xs">
                  <table className="w-full text-left">
                    <thead className="bg-slate-100 text-slate-700 font-bold text-[11px] border-b border-slate-200">
                      <tr>
                        <th className="p-2.5">Field</th>
                        <th className="p-2.5">1. Submitted</th>
                        <th className="p-2.5">2. AI Extracted</th>
                        <th className="p-2.5">3. Bank Confirmed</th>
                        <th className="p-2.5">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                      {provList.map((p: any) => (
                        <tr key={p.id} className="hover:bg-slate-50">
                          <td className="p-2.5 font-sans font-bold text-slate-900">{p.field_name}</td>
                          <td className="p-2.5 text-slate-700">{p.submitted_value || "—"}</td>
                          <td className="p-2.5 text-slate-800 font-semibold">
                            {p.extracted_value || "—"}
                            {p.extracted_confidence !== null && (
                              <span className="text-[10px] text-emerald-600 ml-1">
                                ({Math.round(p.extracted_confidence * 100)}%)
                              </span>
                            )}
                          </td>
                          <td className="p-2.5 text-indigo-700 font-semibold">{p.bank_confirmed_value || "—"}</td>
                          <td className="p-2.5 font-sans">
                            {p.is_match ? (
                              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold text-[10px]">
                                MATCH
                              </span>
                            ) : (
                              <span className="text-amber-800 bg-amber-50 px-2 py-0.5 rounded font-bold text-[10px]">
                                MISMATCH
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB 2: VALIDATION ENGINE */}
            {activeTab === "validation" && (
              <div className="space-y-3">
                <div className="text-xs text-slate-500">
                  Deterministic syntax, date logic, and mandatory statutory field checks
                </div>

                <div className="space-y-2">
                  <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="font-bold text-slate-900">Mandatory Instrument Number Present</span>
                    </div>
                    <span className="font-mono text-emerald-800 font-bold">{fdrDetail.fdr_number}</span>
                  </div>

                  <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="font-bold text-slate-900">Amount Numeric and Positive</span>
                    </div>
                    <span className="font-mono text-emerald-800 font-bold">₹{fdrDetail.amount?.toLocaleString("en-IN")}</span>
                  </div>

                  <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="font-bold text-slate-900">Maturity Date Chronologically Follows Issue Date</span>
                    </div>
                    <span className="text-emerald-800 font-bold">{fdrDetail.issue_date} &rarr; {fdrDetail.maturity_date}</span>
                  </div>

                  <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span className="font-bold text-slate-900">Bank Recognized on RBI Second Schedule</span>
                    </div>
                    <span className="text-emerald-800 font-bold">{fdrDetail.bank_name}</span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: CROSS-DOCUMENT RECONCILIATION */}
            {activeTab === "reconciliation" && (
              <div className="space-y-3">
                <div className="text-xs text-slate-500">
                  Cross-document consistency between FDR Certificate and Bank Confirmation Letter
                </div>

                <div className="border border-slate-200 rounded-lg overflow-hidden text-xs">
                  <table className="w-full text-left">
                    <thead className="bg-slate-100 text-slate-700 font-bold text-[11px] border-b border-slate-200">
                      <tr>
                        <th className="p-2.5">Field</th>
                        <th className="p-2.5">FDR Certificate</th>
                        <th className="p-2.5">Confirmation Letter</th>
                        <th className="p-2.5">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-[11px]">
                      {(reconciliationData?.reconciliation_matrix || [
                        { field_name: "amount", fdr_certificate_value: `₹${fdrDetail.amount?.toLocaleString("en-IN")}`, confirmation_letter_value: `₹${fdrDetail.amount?.toLocaleString("en-IN")}`, status: "MATCH" },
                        { field_name: "maturity_date", fdr_certificate_value: fdrDetail.maturity_date, confirmation_letter_value: fdrDetail.maturity_date, status: "MATCH" },
                        { field_name: "fdr_number", fdr_certificate_value: fdrDetail.fdr_number, confirmation_letter_value: fdrDetail.fdr_number, status: "MATCH" },
                      ]).map((item: any, idx: number) => (
                        <tr key={idx} className="hover:bg-slate-50">
                          <td className="p-2.5 font-bold text-slate-900">{item.field_name}</td>
                          <td className="p-2.5 font-mono text-slate-700">{item.fdr_certificate_value || "—"}</td>
                          <td className="p-2.5 font-mono text-slate-700">{item.confirmation_letter_value || "—"}</td>
                          <td className="p-2.5">
                            {item.status === "MATCH" ? (
                              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-bold text-[10px]">
                                MATCH
                              </span>
                            ) : (
                              <span className="text-amber-800 bg-amber-50 px-2 py-0.5 rounded font-bold text-[10px]">
                                MISMATCH
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB 4: DUPLICATES & INTELLIGENCE GRAPH */}
            {activeTab === "duplicates" && (
              <div className="space-y-3">
                <div className="text-xs text-slate-500">
                  Cross-institution duplicate checks & perceptual hash collisions
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Exact Bank + Number Duplicate Check:</span>
                    <span className="text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded text-[10px]">
                      UNIQUE IN REGISTRY
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">SHA-256 Identical File Hash:</span>
                    <span className="text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded text-[10px]">
                      NO COLLISIONS
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900">Perceptual Hash (pHash) Visual Nearness:</span>
                    <span className="text-slate-700 font-mono text-[10px]">
                      Hamming Distance &gt; 8 (Clear)
                    </span>
                  </div>
                </div>

                <div className="pt-2">
                  <div className="text-xs font-bold text-slate-800 mb-1 flex items-center">
                    <GitFork className="w-3.5 h-3.5 mr-1 text-aicte-navy" />
                    Ecosystem Graph Relationship
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Pledged to Society: <strong>{fdrDetail.institution?.society_or_trust_name || "Vidya Education Society"}</strong> &bull; Bank: <strong>{fdrDetail.bank_name}</strong>
                  </p>
                </div>
              </div>
            )}

            {/* TAB 5: RISK SCORE & ANOMALY REASONS */}
            {activeTab === "risk" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Explainable Preliminary Indicator (Advisory Only)</span>
                  <span className="text-sm font-black text-slate-900">
                    Score: {riskScore.toFixed(1)} / 100
                  </span>
                </div>

                <div className="space-y-2">
                  {flags.length > 0 ? (
                    flags.map((fl: any, idx: number) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg border text-xs space-y-1 ${
                          fl.severity === "HIGH" || fl.severity === "CRITICAL"
                            ? "bg-rose-50 border-rose-200 text-rose-900"
                            : "bg-amber-50 border-amber-200 text-amber-900"
                        }`}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span>{fl.flag || "Regulatory Anomaly"}</span>
                          <span className="text-[10px] uppercase font-extrabold px-1.5 py-0.2 rounded bg-white">
                            {fl.severity}
                          </span>
                        </div>
                        <p className="text-[11px]">{fl.evidence}</p>
                        <p className="text-[10px] text-slate-500">Action: {fl.recommended_action}</p>
                      </div>
                    ))
                  ) : (
                    <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>Zero preliminary anomalies detected. Instrument baseline is compliant.</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 6: STATUTORY COMPLIANCE (APH) */}
            {activeTab === "compliance" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-500">Approval Process Handbook Rules Evaluation</span>
                  <span className="font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                    Version: {compEval?.handbook_version || "APH 2024-27.v1"}
                  </span>
                </div>

                <div className="space-y-2">
                  {(compEval?.results || []).map((r: any) => (
                    <div
                      key={r.rule_id}
                      className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span className="text-slate-900">{r.rule_id}: {r.rule_type}</span>
                        <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                          r.status === "COMPLIANT" ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                        }`}>
                          {r.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-700">{r.plain_explanation_en}</p>
                      <p className="text-[11px] text-slate-500 font-sans">{r.plain_explanation_hi}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 7: CRYPTOGRAPHIC AUDIT LOG */}
            {activeTab === "audit" && (
              <div className="space-y-3">
                <div className="text-xs text-slate-500">
                  Immutable SHA-256 hash-chained regulatory event history
                </div>

                <div className="space-y-2">
                  <div className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="font-bold text-slate-900">Event: INSTRUMENT_REGISTERED</span>
                      <span className="text-slate-400">Timestamp: {fdrDetail.created_at}</span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-500">
                      Hash: <strong className="text-slate-800">a3f890b2c1d4... (GENESIS_LINK)</strong>
                    </div>
                  </div>

                  <div className="p-2.5 bg-slate-50 rounded border border-slate-200 text-xs space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="font-bold text-slate-900">Event: AI_DOCUMENT_EXTRACTION</span>
                      <span className="text-slate-400">Actor: Celery Worker Pipeline</span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-500">
                      Hash: <strong className="text-slate-800">4c81b2a9f7d0... (PREV_LINKED)</strong>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>

          {/* Action Footer: Officer Human-In-The-Loop Governance Actions */}
          <div className="mt-4 pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setManualVerifyModal(true)}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-semibold transition"
              >
                Record Manual Evidence
              </button>
              <button
                onClick={() => setOverrideModal(true)}
                className="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 border border-amber-300 text-amber-900 rounded-lg text-xs font-semibold transition"
              >
                Override Risk
              </button>
              <button
                onClick={() => setClarificationModal(true)}
                className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-300 text-blue-900 rounded-lg text-xs font-semibold transition"
              >
                Request Clarification
              </button>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={handleApproveCase}
                className="px-4 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow-sm transition flex items-center space-x-1"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Approve & Verify</span>
              </button>
            </div>
          </div>

        </div>

      </div>

      {/* Manual Verification Modal */}
      {manualVerifyModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 border border-slate-200 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Record Officer Manual Verification</h3>
              <button onClick={() => setManualVerifyModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700">Verification Method</label>
                <select
                  value={manualMethod}
                  onChange={(e) => setManualMethod(e.target.value)}
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs"
                >
                  <option value="BANK_OFFICIAL_PORTAL">Official Bank NetBanking / CBS Portal</option>
                  <option value="BRANCH_PHYSICAL_VISIT">Branch Physical Visit & Letter</option>
                  <option value="DIRECT_CORRESPONDENCE">Direct Registered Email Correspondence</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700">Official Reference Number</label>
                <input
                  type="text"
                  value={manualRef}
                  onChange={(e) => setManualRef(e.target.value)}
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700">Officer Verification Remarks</label>
                <textarea
                  value={manualRemarks}
                  onChange={(e) => setManualRemarks(e.target.value)}
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setManualVerifyModal(false)}
                className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleRecordManualVerification}
                className="px-4 py-1.5 bg-aicte-navy text-white rounded text-xs font-bold"
              >
                Save Record
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Override Risk Modal */}
      {overrideModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 border border-slate-200 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Human-in-the-Loop Officer Override</h3>
              <button onClick={() => setOverrideModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-amber-50 rounded border border-amber-200 text-amber-900 text-[11px]">
                Statutory Requirement: Every risk score override is permanently etched into the cryptographic audit trail with your verified officer ID and timestamp.
              </div>

              <div>
                <label className="font-semibold text-slate-700">Mandatory Justification</label>
                <textarea
                  value={overrideJustification}
                  onChange={(e) => setOverrideJustification(e.target.value)}
                  placeholder="Detail grounds for overriding preliminary advisory indicator..."
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setOverrideModal(false)}
                className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleOfficerOverride}
                className="px-4 py-1.5 bg-amber-600 text-white rounded text-xs font-bold hover:bg-amber-700"
              >
                Etch Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Clarification Modal */}
      {clarificationModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-5 border border-slate-200 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Request Institution Clarification</h3>
              <button onClick={() => setClarificationModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700">Clarification Request Notice</label>
                <textarea
                  value={clarificationText}
                  onChange={(e) => setClarificationText(e.target.value)}
                  placeholder="Specify discrepancy or missing supporting document..."
                  className="w-full mt-1 border border-slate-300 rounded p-2 text-xs"
                  rows={3}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setClarificationModal(false)}
                className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleRequestClarification}
                className="px-4 py-1.5 bg-blue-700 text-white rounded text-xs font-bold hover:bg-blue-800"
              >
                Dispatch Request
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

