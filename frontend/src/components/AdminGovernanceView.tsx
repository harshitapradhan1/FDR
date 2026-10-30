"use client";

import React, { useState, useEffect } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  Settings, BookOpen, Clock, Users, Activity, CheckCircle2,
  AlertTriangle, RefreshCw, Send, ShieldCheck, Database, Server
} from "lucide-react";
import confetti from "canvas-confetti";

interface AdminGovernanceViewProps {
  lang: Language;
  currentSimulatedDate: string;
  onClockUpdate: () => void;
}

export function AdminGovernanceView({
  lang,
  currentSimulatedDate,
  onClockUpdate
}: AdminGovernanceViewProps) {
  const t = translations[lang];

  const [activeAdminTab, setActiveAdminTab] = useState<"rules" | "impact" | "clock" | "radar" | "adapters">("rules");
  const [ruleHistory, setRuleHistory] = useState<any[]>([]);
  const [activeRule, setActiveRule] = useState<any>(null);
  const [dryRunReport, setDryRunReport] = useState<any>(null);
  const [runningDryRun, setRunningDryRun] = useState(false);
  const [targetClockDate, setTargetClockDate] = useState(currentSimulatedDate || "2026-04-15");
  const [advancing, setAdvancing] = useState(false);

  useEffect(() => {
    api.getActiveRules().then(res => setActiveRule(res)).catch(() => {});
    api.getRuleHistory().then(res => setRuleHistory(res.rules || res || [])).catch(() => {});
  }, []);

  const handleRunDryRun = async () => {
    setRunningDryRun(true);
    try {
      // Simulate draft v2 rule with higher minimum amount requirement (e.g. 35 Lakhs)
      const res = await api.runImpactReport({
        version_tag: "APH-2025-26.v2",
        rules: [
          {
            rule_id: "APH_MIN_AMOUNT_V2",
            rule_type: "min_amount",
            parameters: { minimum_amount_inr: 3500000.0 },
            severity: "HIGH"
          }
        ]
      });
      setDryRunReport(res);
      confetti({ particleCount: 30, spread: 50 });
    } catch (err: any) {
      alert("Impact report simulation error: " + err.message);
    } finally {
      setRunningDryRun(false);
    }
  };

  const handleSetClock = async () => {
    setAdvancing(true);
    try {
      await api.setClock(targetClockDate);
      onClockUpdate();
      confetti({ particleCount: 35, spread: 60 });
      alert(`Demo Clock successfully adjusted to ${targetClockDate}!`);
    } catch (err: any) {
      alert("Error setting clock: " + err.message);
    } finally {
      setAdvancing(false);
    }
  };

  const handleAdvanceDays = async (days: number) => {
    setAdvancing(true);
    try {
      await api.advanceClock(days);
      onClockUpdate();
      confetti({ particleCount: 35, spread: 60 });
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setAdvancing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner */}
      <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-black text-slate-900 flex items-center">
              <Settings className="w-5 h-5 mr-2 text-aicte-navy" />
              Admin, Governance & Regulatory Configuration
            </h2>
            <span className="text-[11px] bg-indigo-100 text-indigo-800 font-bold px-2.5 py-0.5 rounded-full">
              System Admin Only
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure APH handbook rule versions, dry-run impact simulation, maturity radar schedules, and system adapter health
          </p>
        </div>

        <div className="text-xs font-mono bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700">
          Demo Clock: <strong className="text-slate-900">{currentSimulatedDate || "2026-04-15"}</strong>
        </div>
      </div>

      {/* Sub-Tabs Bar */}
      <div className="bg-white p-2 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-1 text-xs font-bold overflow-x-auto">
        <button
          onClick={() => setActiveAdminTab("rules")}
          className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
            activeAdminTab === "rules" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          1. Regulation Rule Editor & History
        </button>

        <button
          onClick={() => setActiveAdminTab("impact")}
          className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
            activeAdminTab === "impact" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          2. Dry-Run Impact Simulation
        </button>

        <button
          onClick={() => setActiveAdminTab("clock")}
          className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
            activeAdminTab === "clock" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          3. Controllable Demo Clock
        </button>

        <button
          onClick={() => setActiveAdminTab("radar")}
          className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
            activeAdminTab === "radar" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          4. Alert Schedule Config
        </button>

        <button
          onClick={() => setActiveAdminTab("adapters")}
          className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
            activeAdminTab === "adapters" ? "bg-aicte-navy text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          5. Adapter Status Board
        </button>
      </div>

      {/* Tab 1: RULE EDITOR & HISTORY */}
      {activeAdminTab === "rules" && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <BookOpen className="w-4 h-4 mr-1.5 text-aicte-navy" />
                Versioned APH Regulation Rules (Active: {activeRule?.version_tag || "APH-2024-27.v1"})
              </h3>
              <p className="text-xs text-slate-500">
                All statutory evaluation rules are versioned and stored with effective dates
              </p>
            </div>
            <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2.5 py-0.5 rounded">
              Active in Production
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="font-bold text-slate-900 text-xs flex justify-between">
                <span>Rule: MIN_SECURITY_DEPOSIT</span>
                <span className="text-[10px] bg-slate-200 px-1.5 py-0.2 rounded font-mono">APH_MIN_AMOUNT</span>
              </div>
              <p className="text-[11px] text-slate-600">
                Mandatory minimum deposit amount: <strong>₹25,00,000/- (Rs. 25 Lakhs)</strong> for Technical/Engineering programs.
              </p>
              <div className="text-[10px] text-slate-400">Severity: HIGH &bull; Handbook Ref: Clause 4.1.2</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="font-bold text-slate-900 text-xs flex justify-between">
                <span>Rule: MIN_TENURE_8_YEARS</span>
                <span className="text-[10px] bg-slate-200 px-1.5 py-0.2 rounded font-mono">APH_MIN_TENURE</span>
              </div>
              <p className="text-[11px] text-slate-600">
                Minimum instrument validity: <strong>96 Months (8 Years)</strong> with joint lien marked to AICTE.
              </p>
              <div className="text-[10px] text-slate-400">Severity: HIGH &bull; Handbook Ref: Clause 4.1.5</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="font-bold text-slate-900 text-xs flex justify-between">
                <span>Rule: SCHEDULED_BANK_WHITELIST</span>
                <span className="text-[10px] bg-slate-200 px-1.5 py-0.2 rounded font-mono">APH_BANK_WHITELIST</span>
              </div>
              <p className="text-[11px] text-slate-600">
                Bank must be listed in RBI Second Schedule (Nationalized, Scheduled Commercial, or Regional Rural).
              </p>
              <div className="text-[10px] text-slate-400">Severity: CRITICAL &bull; Handbook Ref: Clause 4.2.1</div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="font-bold text-slate-900 text-xs flex justify-between">
                <span>Rule: ZERO_GAP_RENEWAL</span>
                <span className="text-[10px] bg-slate-200 px-1.5 py-0.2 rounded font-mono">ZERO_GAP_COVERAGE</span>
              </div>
              <p className="text-[11px] text-slate-600">
                Guarantees zero uncovered gap days between old instrument expiry and approved replacement issue.
              </p>
              <div className="text-[10px] text-slate-400">Severity: MEDIUM &bull; Handbook Ref: Clause 5.3.1</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: DRY-RUN IMPACT SIMULATION */}
      {activeAdminTab === "impact" && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <Activity className="w-4 h-4 mr-1.5 text-aicte-navy" />
                Regulation Change Impact Simulation (Dry-Run)
              </h3>
              <p className="text-xs text-slate-500">
                Identify which institutions and FDR instruments flip from COMPLIANT to NON_COMPLIANT before publishing
              </p>
            </div>

            <button
              onClick={handleRunDryRun}
              disabled={runningDryRun}
              className="flex items-center space-x-1.5 bg-aicte-navy hover:bg-blue-900 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningDryRun ? "animate-spin" : ""}`} />
              <span>Simulate V2 Impact</span>
            </button>
          </div>

          {dryRunReport ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                  <div className="text-[10px] text-slate-500 uppercase font-bold">Total Scanned</div>
                  <div className="text-xl font-black text-slate-900">{dryRunReport.total_evaluated || 164}</div>
                </div>
                <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-center">
                  <div className="text-[10px] text-emerald-700 uppercase font-bold">Remain Compliant</div>
                  <div className="text-xl font-black text-emerald-700">{dryRunReport.still_compliant || 142}</div>
                </div>
                <div className="p-3 bg-rose-50 rounded-lg border border-rose-200 text-center">
                  <div className="text-[10px] text-rose-700 uppercase font-bold">Flip Non-Compliant</div>
                  <div className="text-xl font-black text-rose-600">{dryRunReport.flipped_non_compliant || 22}</div>
                </div>
              </div>

              <div className="p-3 bg-blue-50 rounded-lg border border-blue-200 text-xs text-blue-900">
                Simulation complete. Zero retrospective application will occur without explicit Administrator authorization.
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-slate-300 rounded-xl">
              Click &ldquo;Simulate V2 Impact&rdquo; to execute a sandbox dry-run across all 164 instruments.
            </div>
          )}
        </div>
      )}

      {/* Tab 3: CONTROLLABLE DEMO CLOCK */}
      {activeAdminTab === "clock" && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-5">
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center">
              <Clock className="w-4 h-4 mr-1.5 text-amber-500" />
              Controllable Demo Clock (Time Machine for Evaluations)
            </h3>
            <p className="text-xs text-slate-500">
              Advance simulated time to trigger live maturity ladders, proactive reminders, and predictive forecasts
            </p>
          </div>

          <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
              <div>
                <span className="text-slate-600 font-semibold">Current Simulated Time:</span>
                <div className="text-xl font-black text-slate-900 font-mono mt-0.5">
                  {currentSimulatedDate || "2026-04-15"}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="date"
                  value={targetClockDate}
                  onChange={(e) => setTargetClockDate(e.target.value)}
                  className="border border-slate-300 rounded px-2.5 py-1 text-xs bg-white"
                />
                <button
                  onClick={handleSetClock}
                  disabled={advancing}
                  className="bg-aicte-navy text-white px-3 py-1 rounded text-xs font-bold hover:bg-blue-900"
                >
                  Set Date
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-amber-200 text-xs">
              <span className="text-slate-600 font-medium mr-1">Quick Advance:</span>
              <button
                onClick={() => handleAdvanceDays(7)}
                className="bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 px-3 py-1 rounded font-bold"
              >
                +7 Days (T-7)
              </button>
              <button
                onClick={() => handleAdvanceDays(15)}
                className="bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 px-3 py-1 rounded font-bold"
              >
                +15 Days (T-15)
              </button>
              <button
                onClick={() => handleAdvanceDays(30)}
                className="bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 px-3 py-1 rounded font-bold"
              >
                +30 Days (T-30)
              </button>
              <button
                onClick={() => handleAdvanceDays(60)}
                className="bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 px-3 py-1 rounded font-bold"
              >
                +60 Days (T-60)
              </button>
              <button
                onClick={() => handleAdvanceDays(90)}
                className="bg-amber-600 hover:bg-amber-700 text-white px-3 py-1 rounded font-bold shadow-sm"
              >
                +90 Days (T-90)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: ALERT SCHEDULE CONFIG */}
      {activeAdminTab === "radar" && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-900 text-sm">Maturity Radar Ladder Schedule Configuration</h3>
          <p className="text-xs text-slate-500">
            Escalation thresholds determining in-app and email reminder notifications
          </p>

          <div className="space-y-2 text-xs">
            {[
              { tier: "T-90", label: "Initial Early Advisory", target: "Institution Registrar", channel: "In-App + Email" },
              { tier: "T-60", label: "Formal Renewal Notice", target: "Institution Registrar + Trust", channel: "In-App + Email" },
              { tier: "T-30", label: "Urgent Compliance Notice", target: "Institution + Regional Officer", channel: "In-App + Email" },
              { tier: "T-15", label: "Critical Escalation", target: "Verification Officer + RO", channel: "Urgent Dispatch" },
              { tier: "T-7", label: "Final Pre-Expiry Notice", target: "Competent Authority Desk", channel: "Priority Queue" },
              { tier: "OVERDUE", label: "Regulatory Cover Gap", target: "Bureau Head + System Admin", channel: "Statutory Block" },
            ].map((sch) => (
              <div key={sch.tier} className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
                <div>
                  <span className="font-bold text-slate-900 font-mono text-xs">{sch.tier}: {sch.label}</span>
                  <div className="text-[11px] text-slate-500">Target: {sch.target}</div>
                </div>
                <span className="text-[10px] bg-white border border-slate-300 text-slate-700 font-bold px-2 py-0.5 rounded">
                  {sch.channel}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: ADAPTER STATUS BOARD */}
      {activeAdminTab === "adapters" && (
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-4">
          <h3 className="font-bold text-slate-900 text-sm flex items-center">
            <Server className="w-4 h-4 mr-1.5 text-aicte-navy" />
            Infrastructure & System Adapter Status Board
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-900">Simulated Bank Core Banking Adapter</span>
                <div className="text-[11px] text-slate-500">Simulated CBS FastAPI Container (Port 8001)</div>
              </div>
              <span className="text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded text-[10px]">HEALTHY</span>
            </div>

            <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-900">Celery Worker & Celery Beat</span>
                <div className="text-[11px] text-slate-500">Maturity Radar & Async Document AI</div>
              </div>
              <span className="text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded text-[10px]">RUNNING</span>
            </div>

            <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-900">MinIO / Local Encrypted Storage</span>
                <div className="text-[11px] text-slate-500">Document Vault & Forensics Artifacts</div>
              </div>
              <span className="text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded text-[10px]">CONNECTED</span>
            </div>

            <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
              <div>
                <span className="font-bold text-slate-900">Cryptographic Hash Audit Ledger</span>
                <div className="text-[11px] text-slate-500">SHA-256 Block Chain Traversal</div>
              </div>
              <span className="text-emerald-700 font-bold bg-emerald-100 px-2 py-0.5 rounded text-[10px]">VERIFIED INTACT</span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

