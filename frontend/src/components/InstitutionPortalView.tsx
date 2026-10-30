"use client";

import React, { useState, useEffect } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  Building, Upload, FileText, CheckCircle2, AlertTriangle, Clock,
  ArrowRight, Download, RefreshCw, Eye, Check, X, Shield, Landmark
} from "lucide-react";
import confetti from "canvas-confetti";

interface InstitutionPortalViewProps {
  lang: Language;
  onSelectFDR: (id: number) => void;
  onNavigateTab: (tab: string) => void;
}

export function InstitutionPortalView({
  lang,
  onSelectFDR,
  onNavigateTab
}: InstitutionPortalViewProps) {
  const t = translations[lang];

  const [institution, setInstitution] = useState<any>(null);
  const [fdrs, setFdrs] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [ocrProgress, setOcrProgress] = useState<number>(0);
  const [ocrStage, setOcrStage] = useState<string>("");
  const [extractedPreview, setExtractedPreview] = useState<any>(null);
  const [discrepancyResponse, setDiscrepancyResponse] = useState<string>("");
  const [selectedDiscrepancyFdr, setSelectedDiscrepancyFdr] = useState<number | null>(null);

  useEffect(() => {
    // Default load institution #1 (Vidya Tech)
    api.getInstitution(1).then(res => setInstitution(res)).catch(() => {});
    api.getInstitutionFDRs(1).then(res => setFdrs(res || [])).catch(() => {});
  }, []);

  const handleSimulatedUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setOcrProgress(15);
    setOcrStage("Scanning document SHA-256 and validating MIME type...");

    setTimeout(() => {
      setOcrProgress(45);
      setOcrStage("PyMuPDF native text extraction & OpenCV deskew preprocessing...");
    }, 700);

    setTimeout(() => {
      setOcrProgress(75);
      setOcrStage("Layout template matching & regex normalization...");
    }, 1400);

    setTimeout(async () => {
      setOcrProgress(100);
      setOcrStage("Extraction completed with field-level confidence ratings!");
      setIsUploading(false);
      setExtractedPreview({
        bank_name: "Bharat National Bank",
        fdr_number: `BNB-2026-${Math.floor(1000 + Math.random() * 9000)}`,
        amount: 2500000.0,
        issue_date: "2026-04-10",
        maturity_date: "2034-04-10",
        confidence: 0.96,
        lien_clause: "Jointly pledged in favor of Member Secretary AICTE",
      });
      confetti({ particleCount: 35, spread: 60 });
    }, 2200);
  };

  const handleCommitUpload = async () => {
    if (!extractedPreview) return;
    try {
      const created = await api.createFDR({
        institution_id: 1,
        fdr_number: extractedPreview.fdr_number,
        bank_name: extractedPreview.bank_name,
        branch_name: "Connaught Place New Delhi",
        ifsc_code: "BHNT0001234",
        amount: extractedPreview.amount,
        issue_date: extractedPreview.issue_date,
        maturity_date: extractedPreview.maturity_date,
        tenure_months: 96,
        interest_rate: 7.15,
        joint_holder_name: "Member Secretary AICTE",
        lien_marked_to_aicte: true
      });
      alert(`FDR #${created.fdr_number} successfully registered in AICTE Portal!`);
      setExtractedPreview(null);
      api.getInstitutionFDRs(1).then(res => setFdrs(res || []));
    } catch (err: any) {
      alert("Error registering FDR: " + err.message);
    }
  };

  const handleRespondDiscrepancy = async (fdrId: number) => {
    if (!discrepancyResponse.trim()) {
      alert("Please provide clarification remarks.");
      return;
    }
    try {
      // In a real flow, calls clarification API or correction record
      alert(`Clarification submitted for FDR #${fdrId}: "${discrepancyResponse}". Case updated to UNDER_SCRUTINY.`);
      setDiscrepancyResponse("");
      setSelectedDiscrepancyFdr(null);
      api.getInstitutionFDRs(1).then(res => setFdrs(res || []));
    } catch (err: any) {
      alert("Error: " + err.message);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Institution Banner & Deposit Compliance Header */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start space-x-3.5">
          <div className="w-12 h-12 rounded-xl bg-aicte-navy/10 text-aicte-navy flex items-center justify-center font-bold text-lg border border-aicte-navy/20">
            <Building className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-black text-slate-900">{institution?.name || "Vidya Institute of Technology & Engineering"}</h2>
              <span className="text-[11px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">
                AICTE ID: {institution?.aicte_id || "1-1029384751"}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Region: <strong>{institution?.regional_office || "North (New Delhi)"}</strong> &bull; Category: <strong>{institution?.category || "Engineering & Technology"}</strong> &bull; State: <strong>{institution?.state || "Delhi"}</strong>
            </p>
          </div>
        </div>

        {/* Mandatory Requirement Checklist Card */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs flex items-center space-x-4">
          <div>
            <div className="text-[10px] text-slate-500 font-semibold uppercase">Statutory Deposit Requirement</div>
            <div className="text-base font-black text-slate-900">₹ 25.0 Lakhs</div>
          </div>
          <div className="h-8 w-px bg-slate-300" />
          <div>
            <div className="text-[10px] text-slate-500 font-semibold uppercase">Active Coverage</div>
            <div className="text-base font-black text-emerald-700">₹ 25.0 Lakhs (100%)</div>
          </div>
        </div>
      </div>

      {/* Main Grid: Upload Document Left, Active Instruments Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Drag & Drop Upload & OCR Progress (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-900 text-sm flex items-center mb-1">
              <Upload className="w-4 h-4 mr-1.5 text-aicte-navy" />
              Upload Security Deposit / FDR Instrument
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Supported formats: PDF, JPG, PNG (Max 15MB). Automatic OCR extraction & layout matching.
            </p>

            {/* Drag & Drop Area */}
            <label className="border-2 border-dashed border-slate-300 hover:border-aicte-navy rounded-xl p-6 flex flex-col items-center justify-center cursor-pointer bg-slate-50/50 hover:bg-blue-50/20 transition group">
              <Upload className="w-8 h-8 text-slate-400 group-hover:text-aicte-navy mb-2 transition" />
              <span className="text-xs font-bold text-slate-700 group-hover:text-aicte-navy">
                Click to browse or drag & drop FDR document
              </span>
              <span className="text-[11px] text-slate-400 mt-1">
                Scanned original or e-Deposit confirmation
              </span>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                onChange={handleSimulatedUpload}
                disabled={isUploading}
                className="hidden"
              />
            </label>

            {/* OCR Pipeline Progress */}
            {isUploading && (
              <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-blue-900 flex items-center">
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin text-blue-700" />
                    AI Document Processing...
                  </span>
                  <span className="font-mono font-bold text-blue-800">{ocrProgress}%</span>
                </div>
                <div className="w-full bg-blue-200 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-aicte-navy h-full transition-all duration-300"
                    style={{ width: `${ocrProgress}%` }}
                  />
                </div>
                <div className="text-[11px] text-blue-700 font-medium">
                  {ocrStage}
                </div>
              </div>
            )}

            {/* Extracted Fields Preview & Confidence Editor */}
            {extractedPreview && (
              <div className="mt-4 p-4 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-emerald-900 flex items-center">
                    <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald-600" />
                    AI Extracted Fields (Confidence: {Math.round(extractedPreview.confidence * 100)}%)
                  </span>
                  <span className="text-[10px] bg-emerald-200 text-emerald-800 px-2 py-0.5 rounded font-bold">
                    Layout Validated
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="text-[10px] text-slate-500 font-semibold">Bank Name</label>
                    <input
                      type="text"
                      value={extractedPreview.bank_name}
                      onChange={(e) => setExtractedPreview({ ...extractedPreview, bank_name: e.target.value })}
                      className="w-full bg-white border border-slate-300 rounded px-2 py-1 font-bold text-slate-800 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 font-semibold">FDR Number</label>
                    <input
                      type="text"
                      value={extractedPreview.fdr_number}
                      onChange={(e) => setExtractedPreview({ ...extractedPreview, fdr_number: e.target.value })}
                      className="w-full bg-white border border-slate-300 rounded px-2 py-1 font-mono font-bold text-slate-800 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 font-semibold">Amount (INR)</label>
                    <input
                      type="number"
                      value={extractedPreview.amount}
                      onChange={(e) => setExtractedPreview({ ...extractedPreview, amount: Number(e.target.value) })}
                      className="w-full bg-white border border-slate-300 rounded px-2 py-1 font-bold text-slate-800 text-xs"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-500 font-semibold">Maturity Date</label>
                    <input
                      type="date"
                      value={extractedPreview.maturity_date}
                      onChange={(e) => setExtractedPreview({ ...extractedPreview, maturity_date: e.target.value })}
                      className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-slate-800 text-xs"
                    />
                  </div>
                </div>

                <div className="pt-2 flex items-center space-x-2">
                  <button
                    onClick={handleCommitUpload}
                    className="flex-1 bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-xs py-2 rounded-lg shadow transition text-center"
                  >
                    Confirm & Submit to AICTE Registry
                  </button>
                  <button
                    onClick={() => setExtractedPreview(null)}
                    className="px-3 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold rounded-lg transition"
                  >
                    Discard
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Quick Guidance Box */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 text-xs text-slate-600 space-y-2">
            <div className="font-bold text-slate-800 flex items-center">
              <Shield className="w-4 h-4 mr-1.5 text-aicte-navy" />
              Regulation Compliance Guidelines (APH 2024-27)
            </div>
            <ul className="list-disc pl-4 space-y-1 text-[11px] text-slate-500">
              <li>Instruments must be pledged jointly to <strong>Member Secretary, AICTE</strong>.</li>
              <li>Bank must be on RBI Second Schedule (Nationalized or Scheduled Commercial).</li>
              <li>Tenure must fulfill minimum 8 years (96 months) with auto-renewal clause.</li>
            </ul>
          </div>

        </div>

        {/* Right Column: Pledged Instruments & Status Tracker (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center">
                  <Landmark className="w-4 h-4 mr-1.5 text-aicte-navy" />
                  Pledged Instruments & Status Tracker
                </h3>
                <p className="text-xs text-slate-500">
                  Real-time lifecycle tracking across verification, renewal, and release states
                </p>
              </div>
              <span className="text-xs font-bold text-slate-600 bg-slate-100 px-2 py-1 rounded">
                {fdrs.length} Recorded Instruments
              </span>
            </div>

            <div className="space-y-3">
              {fdrs.map((fdr) => (
                <div
                  key={fdr.id}
                  className="p-4 rounded-xl border border-slate-200 hover:border-aicte-navy/40 transition bg-white space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-sm text-slate-900">{fdr.bank_name}</span>
                      <span className="ml-2 font-mono text-xs text-slate-500">#{fdr.fdr_number}</span>
                    </div>
                    <span
                      className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full ${
                        fdr.status === "ACTIVE"
                          ? "bg-emerald-100 text-emerald-800"
                          : fdr.status === "UNDER_SCRUTINY"
                          ? "bg-blue-100 text-blue-800"
                          : fdr.status === "CLARIFICATION_REQUIRED"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-slate-100 text-slate-800"
                      }`}
                    >
                      {fdr.status}
                    </span>
                  </div>

                  {/* Lifecycle Stage Steps */}
                  <div className="grid grid-cols-4 gap-1 text-[10px] text-center font-semibold pt-1">
                    <div className="p-1 rounded bg-emerald-100 text-emerald-800">1. Submitted</div>
                    <div className="p-1 rounded bg-emerald-100 text-emerald-800">2. AI Extracted</div>
                    <div className={`p-1 rounded ${fdr.status !== "DRAFT" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-400"}`}>
                      3. Bank Verified
                    </div>
                    <div className={`p-1 rounded ${fdr.status === "ACTIVE" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-400"}`}>
                      4. Statutory Active
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
                    <span className="font-semibold text-slate-700">
                      Amount: <strong>₹{(fdr.amount / 100000).toFixed(2)} Lakhs</strong>
                    </span>
                    <span className="text-slate-500">
                      Maturity: <strong className="text-slate-700">{fdr.maturity_date}</strong>
                    </span>
                  </div>

                  {/* Discrepancy Alert & Action */}
                  {fdr.status === "CLARIFICATION_REQUIRED" && (
                    <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-xs space-y-2">
                      <div className="font-bold text-amber-900 flex items-center">
                        <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />
                        Officer Scrutiny Observation: Clarification Required
                      </div>
                      <p className="text-[11px] text-amber-800">
                        Please upload supporting renewal confirmation or clarify maturity date mismatch.
                      </p>
                      {selectedDiscrepancyFdr === fdr.id ? (
                        <div className="space-y-2 pt-1">
                          <textarea
                            value={discrepancyResponse}
                            onChange={(e) => setDiscrepancyResponse(e.target.value)}
                            placeholder="Enter institutional clarification remarks..."
                            className="w-full text-xs p-2 border border-amber-300 rounded bg-white"
                            rows={2}
                          />
                          <div className="flex items-center space-x-2">
                            <button
                              onClick={() => handleRespondDiscrepancy(fdr.id)}
                              className="px-3 py-1 bg-amber-700 text-white rounded text-xs font-bold hover:bg-amber-800"
                            >
                              Submit Clarification
                            </button>
                            <button
                              onClick={() => setSelectedDiscrepancyFdr(null)}
                              className="px-2 py-1 bg-slate-200 text-slate-700 rounded text-xs"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => setSelectedDiscrepancyFdr(fdr.id)}
                          className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-[11px] font-bold"
                        >
                          Respond to Discrepancy
                        </button>
                      )}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex items-center justify-end space-x-2 pt-1">
                    <button
                      onClick={() => onSelectFDR(fdr.id)}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center"
                    >
                      <Eye className="w-3.5 h-3.5 mr-1" />
                      View Dossier
                    </button>
                    <a
                      href={api.getEvidencePackUrl(fdr.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-1.5 bg-aicte-navy hover:bg-blue-900 text-white rounded-lg text-xs font-bold flex items-center shadow-sm"
                    >
                      <Download className="w-3.5 h-3.5 mr-1" />
                      Download Receipt
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

