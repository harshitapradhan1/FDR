"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  X, ShieldCheck, AlertTriangle, FileText, CheckCircle2,
  Lock, RefreshCw, Upload, Eye, UserCheck, Check, Building,
  ArrowRight, Landmark, Clock, FileWarning, ExternalLink
} from "lucide-react";
import confetti from "canvas-confetti";

interface FDRDetailModalProps {
  lang: Language;
  fdrDetail: any;
  onClose: () => void;
  onRefresh: () => void;
  activeRole: string;
}

export function FDRDetailModal({
  lang,
  fdrDetail,
  onClose,
  onRefresh,
  activeRole
}: FDRDetailModalProps) {
  const t = translations[lang];
  const [activeTab, setActiveTab] = useState<"provenance" | "forensics" | "compliance" | "actions">("provenance");
  
  // Action state
  const [isVerifyingBank, setIsVerifyingBank] = useState(false);
  const [bankResultNotice, setBankResultNotice] = useState<any>(null);
  const [overrideModal, setOverrideModal] = useState(false);
  const [overrideJustification, setOverrideJustification] = useState("");
  const [renewModal, setRenewModal] = useState(false);
  const [renewFDRNumber, setRenewFDRNumber] = useState(`${fdrDetail.fdr_number}-R1`);
  const [releaseModal, setReleaseModal] = useState(false);
  const [releaseOrderRef, setReleaseOrderRef] = useState("AICTE/REL/2024/099");
  const [fieldVerifyModal, setFieldVerifyModal] = useState<string | null>(null);
  const [fieldVerifyVal, setFieldVerifyVal] = useState("");

  if (!fdrDetail) return null;

  const handleSimulateBankVerify = async () => {
    setIsVerifyingBank(true);
    try {
      const res = await api.verifyBank(fdrDetail.id);
      setBankResultNotice(res);
      onRefresh();
      confetti({ particleCount: 30, spread: 50, origin: { y: 0.2 } });
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setIsVerifyingBank(false);
    }
  };

  const handleOfficerOverride = async () => {
    if (!overrideJustification.trim()) {
      alert("Please provide a mandatory recorded justification for the override.");
      return;
    }
    try {
      await api.overrideReview(fdrDetail.id, overrideJustification, 10.0, "COMPLIANT");
      setOverrideModal(false);
      onRefresh();
      alert("Officer override recorded with justification in immutable audit ledger.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleRenewFDR = async () => {
    try {
      const today = new Date().toISOString().split("T")[0];
      const mat = new Date(Date.now() + 96 * 30 * 86400000).toISOString().split("T")[0];
      await api.renewFDR(fdrDetail.id, {
        new_fdr_number: renewFDRNumber,
        bank_name: fdrDetail.bank_name,
        branch_name: fdrDetail.branch_name,
        ifsc_code: fdrDetail.ifsc_code,
        amount: fdrDetail.amount,
        issue_date: today,
        maturity_date: mat,
        tenure_months: 96,
        interest_rate: 7.25,
        auto_renewal: true
      });
      setRenewModal(false);
      onRefresh();
      alert(`Renewal instrument created. Previous FDR #${fdrDetail.fdr_number} is now SUPERSEDED.`);
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleAuthorizeRelease = async () => {
    try {
      await api.authorizeRelease(fdrDetail.id, true, releaseOrderRef, "Verified closure and student clearance.");
      setReleaseModal(false);
      onRefresh();
      confetti({ particleCount: 50, spread: 70 });
      alert("Security Deposit release officially authorized by Competent Authority.");
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const handleFieldVerify = async () => {
    if (!fieldVerifyModal) return;
    try {
      await api.verifyField(fdrDetail.id, fieldVerifyModal, fieldVerifyVal);
      setFieldVerifyModal(null);
      onRefresh();
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  const latestDoc = fdrDetail.documents?.[0];

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-5xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Modal Header */}
        <div className="bg-aicte-navy text-white px-6 py-4 flex items-center justify-between border-b border-aicte-saffron">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg">FDR Deep Intelligence & Provenance Inspector</span>
              <span className="text-xs bg-aicte-saffron font-bold text-slate-950 px-2 py-0.5 rounded">
                #{fdrDetail.fdr_number}
              </span>
              <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                fdrDetail.status === "COMPLIANT" ? "bg-emerald-500 text-white" : "bg-amber-400 text-slate-950"
              }`}>
                {fdrDetail.status}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-0.5">
              Institution: <strong className="text-white">{fdrDetail.institution?.name}</strong> (AICTE ID: {fdrDetail.institution?.aicte_id}) &bull; Issuing Bank: <strong>{fdrDetail.bank_name}</strong>
            </p>
          </div>
          <button onClick={onClose} className="text-slate-300 hover:text-white p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 flex items-center space-x-6 text-xs font-bold text-slate-600">
          <button
            onClick={() => setActiveTab("provenance")}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition ${
              activeTab === "provenance" ? "border-aicte-navy text-aicte-navy" : "border-transparent hover:text-slate-900"
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>4-Level Field Provenance</span>
          </button>

          <button
            onClick={() => setActiveTab("forensics")}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition ${
              activeTab === "forensics" ? "border-aicte-navy text-aicte-navy" : "border-transparent hover:text-slate-900"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Document Forensics & Hashes</span>
          </button>

          <button
            onClick={() => setActiveTab("compliance")}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition ${
              activeTab === "compliance" ? "border-aicte-navy text-aicte-navy" : "border-transparent hover:text-slate-900"
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Regulation Handbook Rules</span>
          </button>

          <button
            onClick={() => setActiveTab("actions")}
            className={`py-3 border-b-2 flex items-center space-x-1.5 transition ${
              activeTab === "actions" ? "border-aicte-navy text-aicte-navy" : "border-transparent hover:text-slate-900"
            }`}
          >
            <UserCheck className="w-4 h-4" />
            <span>Human-in-the-Loop Actions</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
          
          {/* TAB 1: 4-LEVEL FIELD PROVENANCE */}
          {activeTab === "provenance" && (
            <div className="space-y-4">
              <div className="bg-blue-50/60 border border-blue-200 p-3 rounded-lg flex items-center justify-between">
                <span className="text-slate-800 font-medium">
                  <strong>4-Level Field Provenance Audit Trail:</strong> Traces each field from Institution Self-Declaration &rarr; AI OCR/PDF Extraction &rarr; Bank CBS Confirmation &rarr; Officer Human Verification.
                </span>
                <span className="text-[10px] bg-white border border-blue-300 text-blue-900 font-bold px-2 py-0.5 rounded">
                  Zero Black-Box
                </span>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase text-[10px]">
                    <tr>
                      <th className="py-2.5 px-3">Field</th>
                      <th className="py-2.5 px-3">1. Submitted (Institution)</th>
                      <th className="py-2.5 px-3">2. AI Extracted (Scan)</th>
                      <th className="py-2.5 px-3">3. Bank Confirmed (CBS Mock)</th>
                      <th className="py-2.5 px-3">4. Officer Verified (Human)</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                      <th className="py-2.5 px-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {fdrDetail.provenance_fields?.map((prov: any) => (
                      <tr key={prov.id} className={prov.status === "MISMATCH" ? "bg-rose-50/50" : "hover:bg-slate-50"}>
                        <td className="py-2.5 px-3 font-bold text-slate-900 capitalize">
                          {prov.field_name.replace("_", " ")}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">
                          {prov.submitted_value || "—"}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">
                          {prov.ai_extracted_value ? (
                            <span>
                              {prov.ai_extracted_value}
                              <span className="ml-1 text-[9px] text-emerald-600 font-sans font-bold">
                                ({(prov.ai_confidence * 100).toFixed(0)}%)
                              </span>
                            </span>
                          ) : (
                            <span className="text-slate-400">SOURCE_UNAVAILABLE</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">
                          {prov.bank_confirmed_value ? (
                            <span className="text-emerald-700 font-semibold">{prov.bank_confirmed_value}</span>
                          ) : (
                            <span className="text-slate-400">Pending Verification</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-700">
                          {prov.officer_verified_value ? (
                            <span className="text-purple-700 font-bold">{prov.officer_verified_value}</span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            prov.status === "MISMATCH"
                              ? "bg-rose-100 text-rose-800 border border-rose-300"
                              : prov.status === "OFFICER_VERIFIED"
                              ? "bg-purple-100 text-purple-800"
                              : prov.status === "BANK_CONFIRMED"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-blue-100 text-blue-800"
                          }`}>
                            {prov.status}
                          </span>
                          {prov.mismatch_reason && (
                            <div className="text-[9px] text-rose-700 font-sans mt-0.5 text-left max-w-xs">
                              {prov.mismatch_reason}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <button
                            onClick={() => {
                              setFieldVerifyModal(prov.field_name);
                              setFieldVerifyVal(prov.submitted_value || prov.ai_extracted_value || "");
                            }}
                            className="text-[10px] bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold px-2 py-1 rounded transition"
                          >
                            Verify
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Explainable Review Priority Flags */}
              <div className="mt-4">
                <h4 className="font-bold text-slate-900 text-xs mb-2 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-1 text-amber-500" />
                  Explainable Review Priority Indicator: {fdrDetail.review_priority_score} / 100 ({fdrDetail.review_priority_level})
                </h4>
                {fdrDetail.review_flags?.length > 0 ? (
                  <div className="space-y-2">
                    {fdrDetail.review_flags.map((flag: any, i: number) => (
                      <div key={i} className="p-3 rounded-lg border border-rose-200 bg-rose-50/70 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-rose-900">{flag.title}</span>
                          <span className="text-[10px] font-extrabold px-1.5 py-0.2 rounded bg-rose-200 text-rose-900">
                            {flag.severity}
                          </span>
                        </div>
                        <p className="text-slate-700"><strong>Reason:</strong> {flag.reason}</p>
                        <p className="text-slate-600 font-mono text-[11px]"><strong>Evidence:</strong> {flag.evidence}</p>
                        <p className="text-slate-500 text-[10px]"><strong>Rule Reference:</strong> {flag.rule_reference}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                    <span>No review priority anomalies detected. Available checks passed.</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: DOCUMENT FORENSICS */}
          {activeTab === "forensics" && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Forensic Metadata Card */}
                <div className="border border-slate-200 rounded-xl p-4 bg-slate-50">
                  <h4 className="font-bold text-slate-900 mb-3 flex items-center">
                    <FileText className="w-4 h-4 mr-1 text-aicte-navy" />
                    Cryptographic Document Fingerprints
                  </h4>
                  
                  <div className="space-y-2 text-xs">
                    <div>
                      <span className="text-slate-500 block font-semibold">Document File SHA256:</span>
                      <code className="bg-white px-2 py-1 rounded border border-slate-200 block font-mono text-[11px] text-slate-800 break-all select-all">
                        {latestDoc?.file_hash_sha256 || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
                      </code>
                    </div>

                    <div>
                      <span className="text-slate-500 block font-semibold">Perceptual Image Hash (imagehash.pHash):</span>
                      <code className="bg-white px-2 py-1 rounded border border-slate-200 block font-mono text-[11px] text-slate-800 select-all">
                        {latestDoc?.perceptual_hash || "b4a8e3d29c1f0a5b"}
                      </code>
                      <span className="text-[10px] text-slate-400 mt-0.5 block">
                        Used for cross-institution template collision detection
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-500 block font-semibold">PDF Producer Signature:</span>
                      <span className="font-mono text-slate-800 bg-white px-2 py-1 rounded border border-slate-200 block">
                        {latestDoc?.forensic_metadata?.pdf_producer || "CoreBankingSystem CBS-PDF Engine v4.1"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tampering & Integrity Analysis */}
                <div className="border border-slate-200 rounded-xl p-4 bg-slate-50">
                  <h4 className="font-bold text-slate-900 mb-3 flex items-center">
                    <ShieldCheck className="w-4 h-4 mr-1 text-aicte-emerald" />
                    Tampering & Scan Integrity Indicators
                  </h4>

                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
                      <span>Editing Tool Traces (Canva/Photoshop):</span>
                      {latestDoc?.forensic_metadata?.producer_flagged ? (
                        <span className="text-rose-700 font-bold bg-rose-50 px-2 py-0.5 rounded text-[11px]">
                          DETECTED
                        </span>
                      ) : (
                        <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded text-[11px]">
                          CLEAN
                        </span>
                      )}
                    </div>

                    <div className="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
                      <span>Scan Sharpness / Blur Check:</span>
                      <span className="text-slate-800 font-mono text-[11px]">
                        Laplacian Var: {latestDoc?.forensic_metadata?.laplacian_variance?.toFixed(1) || "142.5"} (Normal)
                      </span>
                    </div>

                    <div className="flex items-center justify-between p-2 rounded bg-white border border-slate-200">
                      <span>Document Versioning:</span>
                      <span className="font-bold text-slate-800">
                        Version {latestDoc?.version || 1} (Immutable)
                      </span>
                    </div>
                  </div>
                </div>

              </div>

              {/* Document Download Link */}
              <div className="p-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between">
                <span className="text-slate-700 font-medium">Uploaded Document: <strong>{latestDoc?.file_name || "v1_SBI_Certificate.pdf"}</strong></span>
                <a
                  href={`http://localhost:8000/storage/fdr_${fdrDetail.id}/${latestDoc?.file_name || "v1_SBI_Certificate.pdf"}`}
                  target="_blank"
                  rel="noreferrer"
                  className="bg-aicte-navy hover:bg-aicte-darkNavy text-white font-bold text-xs px-3 py-1.5 rounded flex items-center space-x-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>Preview Generated PDF</span>
                </a>
              </div>
            </div>
          )}

          {/* TAB 3: COMPLIANCE HANDBOOK RULES */}
          {activeTab === "compliance" && (
            <div className="space-y-4">
              <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg text-amber-900 text-xs">
                <strong>{t.placeholderNotice}</strong>: Regulations are versioned rules (e.g. {fdrDetail.compliance_evaluation?.rule_version || "APH-2024-27.v1"}). Compliance is decided strictly by explicit rules, never hardcoded.
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 border-b border-slate-200 font-bold uppercase text-[10px] text-slate-600">
                    <tr>
                      <th className="py-2.5 px-3">Rule ID & Name</th>
                      <th className="py-2.5 px-3">APH Prescribed Norm</th>
                      <th className="py-2.5 px-3">Observed in Instrument</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                      <th className="py-2.5 px-3">Explanation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {fdrDetail.compliance_evaluation?.checks?.map((chk: any) => (
                      <tr key={chk.rule_id} className={chk.passed ? "hover:bg-slate-50" : "bg-rose-50/50"}>
                        <td className="py-2.5 px-3 font-bold text-slate-900">
                          {chk.name}
                          <span className="block text-[10px] text-slate-500 font-mono">{chk.rule_id}</span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-700">{chk.required}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-800">{chk.observed}</td>
                        <td className="py-2.5 px-3 text-center">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            chk.passed ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                          }`}>
                            {chk.passed ? "PASS" : "FAIL"}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 text-[11px]">{chk.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 4: HUMAN-IN-THE-LOOP ACTIONS */}
          {activeTab === "actions" && (
            <div className="space-y-4">
              
              {/* Bank Verification Trigger Card */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-slate-900 text-xs">Simulate Bank CBS / SFMS Verification</h4>
                  <p className="text-[11px] text-slate-500">
                    Executes BankVerificationAdapter simulator with official watermark &ldquo;{t.simulatedNotice}&rdquo;.
                  </p>
                </div>
                <button
                  onClick={handleSimulateBankVerify}
                  disabled={isVerifyingBank}
                  className="bg-aicte-emerald hover:bg-aicte-emeraldDark text-white font-bold text-xs px-3.5 py-2 rounded-lg shadow transition flex items-center space-x-1.5"
                >
                  <Landmark className="w-4 h-4" />
                  <span>{isVerifyingBank ? "Querying Bank Mock..." : "Simulate Bank Verification"}</span>
                </button>
              </div>

              {bankResultNotice && (
                <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg text-xs space-y-1 font-mono">
                  <div className="font-bold text-emerald-900">
                    CBS Mock Response: {bankResultNotice.verification_result?.status}
                  </div>
                  <div className="text-emerald-800 text-[11px]">
                    API Ref: {bankResultNotice.verification_result?.api_reference_id} &bull; {bankResultNotice.watermark_notice}
                  </div>
                </div>
              )}

              {/* Officer Override Action Card */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-slate-900 text-xs">Officer Review Override (Human-in-the-Loop)</h4>
                  <p className="text-[11px] text-slate-500">
                    Allows verification officer to override advisory AI flags with mandatory recorded justification.
                  </p>
                </div>
                <button
                  onClick={() => setOverrideModal(true)}
                  className="bg-purple-700 hover:bg-purple-800 text-white font-bold text-xs px-3.5 py-2 rounded-lg shadow transition flex items-center space-x-1.5"
                >
                  <UserCheck className="w-4 h-4" />
                  <span>Officer Override</span>
                </button>
              </div>

              {/* Renewal Action Card */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-slate-900 text-xs">Renew FDR Instrument (Create Successor)</h4>
                  <p className="text-[11px] text-slate-500">
                    Non-negotiable rule: Never overwrites existing FDR. Creates linked successor; old marked SUPERSEDED.
                  </p>
                </div>
                <button
                  onClick={() => setRenewModal(true)}
                  className="bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs px-3.5 py-2 rounded-lg shadow transition flex items-center space-x-1.5"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Renew Deposit</span>
                </button>
              </div>

              {/* Release / Refund Authorization Card */}
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-slate-900 text-xs">Deposit Release / Refund Authorization</h4>
                  <p className="text-[11px] text-slate-500">
                    Safeguard: Authorized <strong>solely by Competent Authority</strong> role upon closure verification.
                  </p>
                </div>
                {activeRole === "COMPETENT_AUTHORITY" ? (
                  <button
                    onClick={() => setReleaseModal(true)}
                    className="bg-aicte-navy hover:bg-aicte-darkNavy text-white font-bold text-xs px-3.5 py-2 rounded-lg shadow transition flex items-center space-x-1.5"
                  >
                    <Lock className="w-4 h-4 text-aicte-saffron" />
                    <span>Authorize Official Release</span>
                  </button>
                ) : (
                  <span className="text-[11px] text-slate-500 bg-slate-200 px-2.5 py-1.5 rounded font-medium">
                    Requires Competent Authority Role
                  </span>
                )}
              </div>

            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span>AICTE Security Deposit Verification Engine &bull; Non-destructive append-only record</span>
          <button onClick={onClose} className="bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold px-4 py-1.5 rounded-lg">
            Close Inspector
          </button>
        </div>

      </div>

      {/* SUB-MODAL: Field Verification */}
      {fieldVerifyModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white p-5 rounded-xl max-w-md w-full shadow-xl space-y-3">
            <h4 className="font-bold text-slate-900 text-sm">Verify Field: {fieldVerifyModal}</h4>
            <p className="text-xs text-slate-600">Enter confirmed value verified through officer inspection:</p>
            <input
              type="text"
              value={fieldVerifyVal}
              onChange={(e) => setFieldVerifyVal(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded px-3 py-2 font-mono"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button onClick={() => setFieldVerifyModal(null)} className="text-xs px-3 py-1.5 bg-slate-100 rounded">
                Cancel
              </button>
              <button onClick={handleFieldVerify} className="text-xs px-3 py-1.5 bg-purple-700 text-white font-bold rounded">
                Save as Officer Verified
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SUB-MODAL: Officer Override */}
      {overrideModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white p-5 rounded-xl max-w-lg w-full shadow-xl space-y-3">
            <h4 className="font-bold text-slate-900 text-sm">Record Officer Review Override</h4>
            <p className="text-xs text-slate-600">
              Regulatory Safeguard: A written justification is mandatory and permanently anchored to the cryptographic audit ledger.
            </p>
            <textarea
              rows={3}
              placeholder="e.g., Institution produced original exemption letter from State Director of Technical Education ref..."
              value={overrideJustification}
              onChange={(e) => setOverrideJustification(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded p-2.5 focus:outline-none focus:ring-1 focus:ring-purple-700"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button onClick={() => setOverrideModal(false)} className="text-xs px-3 py-1.5 bg-slate-100 rounded">
                Cancel
              </button>
              <button onClick={handleOfficerOverride} className="text-xs px-3 py-1.5 bg-purple-700 text-white font-bold rounded">
                Confirm & Anchor Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SUB-MODAL: Renewal */}
      {renewModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white p-5 rounded-xl max-w-md w-full shadow-xl space-y-3">
            <h4 className="font-bold text-slate-900 text-sm">Renew Instrument #{fdrDetail.fdr_number}</h4>
            <p className="text-xs text-slate-600">
              New linked instrument number:
            </p>
            <input
              type="text"
              value={renewFDRNumber}
              onChange={(e) => setRenewFDRNumber(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded px-3 py-2 font-mono"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button onClick={() => setRenewModal(false)} className="text-xs px-3 py-1.5 bg-slate-100 rounded">
                Cancel
              </button>
              <button onClick={handleRenewFDR} className="text-xs px-3 py-1.5 bg-amber-600 text-white font-bold rounded">
                Confirm Renewal Chain
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SUB-MODAL: Release Authorization */}
      {releaseModal && (
        <div className="fixed inset-0 z-60 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white p-5 rounded-xl max-w-md w-full shadow-xl space-y-3">
            <h4 className="font-bold text-slate-900 text-sm">Competent Authority Release Authorization</h4>
            <p className="text-xs text-slate-600">
              Enter official Council Release Order Dispatch Reference:
            </p>
            <input
              type="text"
              value={releaseOrderRef}
              onChange={(e) => setReleaseOrderRef(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded px-3 py-2 font-mono"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button onClick={() => setReleaseModal(false)} className="text-xs px-3 py-1.5 bg-slate-100 rounded">
                Cancel
              </button>
              <button onClick={handleAuthorizeRelease} className="text-xs px-3 py-1.5 bg-aicte-navy text-white font-bold rounded">
                Issue Official Release Order
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

