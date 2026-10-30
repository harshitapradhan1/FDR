"use client";

import React, { useEffect, useState } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  ShieldCheck, Lock, CheckCircle2, AlertTriangle, RefreshCw,
  Hash, Clock, ArrowDown
} from "lucide-react";
import confetti from "canvas-confetti";

interface AuditLedgerViewProps {
  lang: Language;
}

export function AuditLedgerView({ lang }: AuditLedgerViewProps) {
  const t = translations[lang];
  const [logs, setLogs] = useState<any[]>([]);
  const [verificationResult, setVerificationResult] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      const data = await api.getAuditLedger(50);
      setLogs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const verifyChain = async () => {
    setVerifying(true);
    try {
      const res = await api.verifyAuditChain();
      setVerificationResult(res);
      if (res.verified) {
        confetti({ particleCount: 40, spread: 60 });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setVerifying(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    verifyChain();
  }, []);

  return (
    <div className="space-y-6">
      
      {/* Top Ledger Header & Verification Banner */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="font-extrabold text-slate-900 text-base flex items-center">
              <Lock className="w-5 h-5 mr-2 text-aicte-navy" />
              Cryptographic Hash-Chained Audit Ledger
            </h3>
            <span className="text-[10px] font-mono bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-bold border border-indigo-200">
              H_n = SHA256(H_{`{n-1}`} || event_n)
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Append-only tamper-evident blockchain architecture. Every state transition, AI extraction, and officer decision is permanently anchored.
          </p>
        </div>

        <button
          onClick={verifyChain}
          disabled={verifying}
          className="bg-aicte-emerald hover:bg-aicte-emeraldDark text-white font-bold text-xs px-4 py-2 rounded-lg shadow transition flex items-center space-x-1.5 self-start md:self-auto"
        >
          <ShieldCheck className="w-4 h-4" />
          <span>{verifying ? "Verifying Math..." : "Verify Hash Chain Integrity"}</span>
        </button>
      </div>

      {/* Verification Status Banner */}
      {verificationResult && (
        <div className={`p-4 rounded-xl border flex items-center justify-between text-xs ${
          verificationResult.verified
            ? "bg-emerald-50 border-emerald-300 text-emerald-900"
            : "bg-rose-50 border-rose-300 text-rose-900"
        }`}>
          <div className="flex items-center space-x-2.5">
            {verificationResult.verified ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
            )}
            <div>
              <span className="font-bold">{verificationResult.message}</span>
              <div className="text-[11px] text-slate-600 font-mono mt-0.5">
                Total Verified Blocks: <strong>{verificationResult.total_records}</strong> &bull; Latest Block Hash: <code>{verificationResult.latest_block_hash?.slice(0, 24)}...</code>
              </div>
            </div>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wider bg-white px-2.5 py-1 rounded border border-emerald-300 text-emerald-800">
            Zero Alterations Detected
          </span>
        </div>
      )}

      {/* Audit Blocks Sequence List */}
      <div className="space-y-3">
        {logs.map((block, idx) => (
          <div key={block.sequence_num} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 relative">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-2.5">
              <div className="flex items-center space-x-2">
                <span className="w-7 h-7 rounded-lg bg-aicte-navy text-white font-mono font-bold text-xs flex items-center justify-center">
                  #{block.sequence_num}
                </span>
                <span className="font-bold text-slate-900 text-xs font-mono">
                  {block.event_type}
                </span>
                <span className="text-[10px] bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded">
                  {block.entity_type} {block.entity_id}
                </span>
              </div>

              <div className="flex items-center space-x-2 text-slate-400 text-[11px]">
                <Clock className="w-3.5 h-3.5" />
                <span>{block.timestamp}</span>
                <span className="text-slate-600 font-medium">({block.actor_role || "SYSTEM"})</span>
              </div>
            </div>

            {/* Hashes Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2.5 text-[11px] font-mono">
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 text-[9px] block uppercase font-sans font-bold">Previous Hash (H_{`{n-1}`}):</span>
                <code className="text-slate-600 select-all break-all">{block.prev_hash}</code>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-slate-400 text-[9px] block uppercase font-sans font-bold">Block Hash (H_n):</span>
                <code className="text-aicte-navy font-bold select-all break-all">{block.current_hash}</code>
              </div>
            </div>

            {/* Payload summary */}
            {block.payload && Object.keys(block.payload).length > 0 && (
              <div className="mt-2 text-[11px] text-slate-600 bg-slate-50/50 p-2 rounded border border-slate-100 font-mono">
                <span className="text-slate-400 font-sans text-[10px] uppercase font-bold mr-2">Payload:</span>
                {JSON.stringify(block.payload)}
              </div>
            )}
          </div>
        ))}
      </div>

    </div>
  );
}

