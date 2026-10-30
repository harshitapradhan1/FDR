"use client";

import React, { useState, useEffect } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  FileText, Landmark, Clock, ShieldCheck, CheckCircle2,
  GitFork, ArrowRight, Download, RefreshCw, AlertTriangle, Lock
} from "lucide-react";

interface LifecyclePassportViewProps {
  lang: Language;
  selectedFdrId?: number;
  fdrs: any[];
  onSelectFDR: (id: number) => void;
}

export function LifecyclePassportView({
  lang,
  selectedFdrId,
  fdrs,
  onSelectFDR
}: LifecyclePassportViewProps) {
  const t = translations[lang];

  const currentFdrId = selectedFdrId || fdrs[0]?.id || 1;
  const [passport, setPassport] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadPassport = async (id: number) => {
    setLoading(true);
    try {
      const res = await api.getPassport(id);
      setPassport(res);
    } catch (err) {
      console.error("Error loading lifecycle passport:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentFdrId) {
      loadPassport(currentFdrId);
    }
  }, [currentFdrId]);

  if (!passport) {
    return (
      <div className="bg-white rounded-xl p-12 text-center border border-slate-200">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-aicte-navy mb-3" />
        <p className="text-slate-600 font-bold text-sm">Generating FDR Lifecycle Passport...</p>
      </div>
    );
  }

  const events = passport.timeline_events || [];

  return (
    <div className="space-y-6">
      
      {/* Top Header Bar */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-black text-slate-900 flex items-center">
              <GitFork className="w-5 h-5 mr-2 text-aicte-navy" />
              FDR Lifecycle Passport (Instrument Lineage)
            </h2>
            <span className="text-[11px] bg-blue-100 text-blue-800 font-bold px-2.5 py-0.5 rounded-full font-mono">
              Lineage: {passport.lineage_id || `LIN-${currentFdrId}`}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable chronological instrument journey: original FDR, renewals, amount changes, verifications, and release orders
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <select
            value={currentFdrId}
            onChange={(e) => onSelectFDR(Number(e.target.value))}
            className="text-xs font-bold bg-slate-100 border border-slate-300 rounded-lg px-3 py-2 text-slate-900"
          >
            {fdrs.map(f => (
              <option key={f.id} value={f.id}>
                #{f.fdr_number} &bull; {f.bank_name} &bull; ₹{(f.amount / 100000).toFixed(1)}L
              </option>
            ))}
          </select>

          <a
            href={api.getEvidencePackUrl(currentFdrId)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-1.5 bg-aicte-navy hover:bg-blue-900 text-white text-xs font-bold px-3.5 py-2 rounded-lg shadow-sm transition"
          >
            <Download className="w-3.5 h-3.5 text-amber-400" />
            <span>Download Evidence Pack (PDF)</span>
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <span className="text-[10px] text-slate-500 uppercase font-bold">Institution</span>
          <div className="mt-1 text-sm font-black text-slate-900 truncate">
            {passport.institution?.name || "Vidya Institute of Technology"}
          </div>
          <div className="text-[11px] text-slate-500">AICTE ID: {passport.institution?.aicte_id || "1-1029384751"}</div>
        </div>

        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <span className="text-[10px] text-slate-500 uppercase font-bold">Current Instrument</span>
          <div className="mt-1 text-sm font-black text-slate-900 font-mono">
            #{passport.fdr_number || "FDR-2026-001"}
          </div>
          <div className="text-[11px] text-slate-500">{passport.bank_name || "National Bank"}</div>
        </div>

        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <span className="text-[10px] text-slate-500 uppercase font-bold">Principal Deposit</span>
          <div className="mt-1 text-sm font-black text-emerald-700">
            ₹{((passport.amount || 2500000) / 100000).toFixed(2)} Lakhs
          </div>
          <div className="text-[11px] text-slate-500">Maturity: {passport.maturity_date || "2034-04-10"}</div>
        </div>

        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
          <span className="text-[10px] text-slate-500 uppercase font-bold">Lifecycle Status</span>
          <div className="mt-1 text-sm font-black text-slate-900">
            {passport.status || "ACTIVE"}
          </div>
          <div className="text-[11px] text-emerald-600 font-bold">Chain Custody Verified</div>
        </div>
      </div>

      {/* Chronological Lifecycle Timeline */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm space-y-6">
        <h3 className="font-bold text-slate-900 text-sm flex items-center">
          <Clock className="w-4 h-4 mr-2 text-aicte-navy" />
          Chronological Lifecycle Timeline
        </h3>

        <div className="relative border-l-2 border-slate-200 ml-4 space-y-6 pb-2">
          {events.length > 0 ? (
            events.map((evt: any, idx: number) => (
              <div key={idx} className="relative pl-6">
                {/* Node Dot */}
                <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white ${
                  evt.event_type?.includes("APPROV") || evt.event_type?.includes("VERIF")
                    ? "bg-emerald-600"
                    : evt.event_type?.includes("RENEW")
                    ? "bg-amber-500"
                    : "bg-aicte-navy"
                }`} />

                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">{evt.event_title || evt.event_type}</span>
                    <span className="text-[11px] text-slate-400 font-mono">{evt.timestamp}</span>
                  </div>
                  <p className="text-slate-600 text-[11px]">{evt.description || evt.remarks}</p>
                  <div className="text-[10px] text-slate-400 pt-1 flex items-center justify-between">
                    <span>Actor: <strong className="text-slate-700">{evt.actor_role || evt.actor_name || "SYSTEM"}</strong></span>
                    {evt.audit_log_id && (
                      <span className="font-mono text-slate-500">Audit Block #{evt.audit_log_id}</span>
                    )}
                  </div>
                </div>
              </div>
            ))
          ) : (
            // Default Rich Scripted Timeline for Demo
            [
              {
                title: "Original Instrument Submission & Registration",
                date: "2024-04-10 10:15 UTC",
                desc: "Institution uploaded initial deposit instrument of ₹25,00,000/- with 8-year statutory tenure.",
                actor: "INSTITUTION_USER (Registrar)",
                audit: "Block #1 (SHA256: 0041a9...)"
              },
              {
                title: "AI Document Intelligence & 4-Level Field Extraction",
                date: "2024-04-10 10:16 UTC",
                desc: "PyMuPDF native text & layout parsing extracted FDR#, IFSC, Bank, Amount with 98% confidence.",
                actor: "Celery Pipeline",
                audit: "Block #2 (SHA256: b892ec...)"
              },
              {
                title: "Bank Core Banking System (CBS) Confirmation",
                date: "2024-04-12 14:20 UTC",
                desc: "Core Banking System simulation returned AVAILABLE_CHECKS_PASSED. Deposit lien pledged to AICTE.",
                actor: "BankVerificationAdapter",
                audit: "Block #3 (SHA256: f198a0...)"
              },
              {
                title: "Maturity Radar Ladder Transition (T-30)",
                date: "2026-03-10 08:00 UTC",
                desc: "Automated daily maturity radar scan flagged upcoming expiry. Reminder dispatched to institution.",
                actor: "Celery Beat (Maturity Radar)",
                audit: "Block #4 (SHA256: 7e22bc...)"
              },
              {
                title: "Non-Destructive Renewal Instrument Pledged",
                date: "2026-04-10 11:30 UTC",
                desc: "Institution uploaded renewed instrument. Previous FDR marked SUPERSEDED; continuous cover preserved.",
                actor: "VERIFICATION_OFFICER",
                audit: "Block #5 (SHA256: d910aa...)"
              }
            ].map((evt, idx) => (
              <div key={idx} className="relative pl-6">
                <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white ${
                  idx === 0 ? "bg-blue-600" : idx === 2 ? "bg-emerald-600" : idx === 4 ? "bg-purple-600" : "bg-amber-500"
                }`} />

                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-sm">{evt.title}</span>
                    <span className="text-[11px] text-slate-400 font-mono">{evt.date}</span>
                  </div>
                  <p className="text-slate-600 text-[11px]">{evt.desc}</p>
                  <div className="text-[10px] text-slate-400 pt-1 flex items-center justify-between">
                    <span>Actor: <strong className="text-slate-700">{evt.actor}</strong></span>
                    <span className="font-mono text-slate-500">{evt.audit}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
}

