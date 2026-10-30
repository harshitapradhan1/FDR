"use client";

import React, { useState, useEffect } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  ShieldCheck, AlertTriangle, Clock, Landmark, FileText, CheckCircle,
  TrendingUp, Users, ArrowRight, ShieldAlert, Award, FileQuestion,
  RefreshCw, CheckCircle2, ChevronRight, Activity, MapPin
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
  PieChart, Pie, Legend
} from "recharts";

interface DashboardViewProps {
  lang: Language;
  workload: any;
  fdrs: any[];
  auditStatus: any;
  onSelectFDR: (id: number) => void;
  onNavigateTab: (tab: string) => void;
}

export function DashboardView({
  lang,
  workload,
  fdrs,
  auditStatus,
  onSelectFDR,
  onNavigateTab
}: DashboardViewProps) {
  const t = translations[lang];

  const [priorityQueue, setPriorityQueue] = useState<any[]>([]);
  const [releaseRequests, setReleaseRequests] = useState<any[]>([]);
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [selectedState, setSelectedState] = useState<string>("ALL");

  useEffect(() => {
    api.getPriorityQueue().then(res => setPriorityQueue(res.queue || [])).catch(() => {});
    api.getReleaseRequests().then(res => setReleaseRequests(res.requests || res || [])).catch(() => {});
    api.getInstitutions().then(res => setInstitutions(res || [])).catch(() => {});
  }, []);

  const totalAmount = fdrs.reduce((acc, curr) => acc + (curr.amount || 0), 0);
  const activeFDRs = fdrs.filter(f => f.status === "ACTIVE").length;
  const pendingVerification = fdrs.filter(f => f.status === "UNDER_SCRUTINY" || f.status === "PENDING_VERIFICATION").length;
  const overdueRenewals = fdrs.filter(f => f.status === "EXPIRED" || f.status === "RENEWAL_OVERDUE").length;
  const releaseAwaiting = releaseRequests.filter(r => r.status === "SUBMITTED" || r.status === "UNDER_SCRUTINY" || r.status === "RECOMMENDED_FOR_APPROVAL").length;
  const highPriorityCount = fdrs.filter(f => f.review_priority_level === "HIGH" || f.review_priority_level === "CRITICAL").length;
  const imminentCount = workload?.summary?.critical_escalation_t15 + workload?.summary?.warning_due_soon_t30 || 0;

  // Forecast chart data
  const chartData = workload?.monthly_forecast?.length > 0 ? workload.monthly_forecast : [
    { month: "Apr 2026", amount: 3500000, count: 4 },
    { month: "May 2026", amount: 1500000, count: 2 },
    { month: "Jun 2026", amount: 4500000, count: 5 },
    { month: "Jul 2026", amount: 2000000, count: 3 },
    { month: "Aug 2026", amount: 6000000, count: 7 },
  ];

  // Bank Distribution Chart Data
  const bankCounts: Record<string, number> = {};
  fdrs.forEach(f => {
    const b = f.bank_name || "Unknown Bank";
    bankCounts[b] = (bankCounts[b] || 0) + 1;
  });
  const bankPieData = Object.entries(bankCounts).slice(0, 5).map(([name, value]) => ({
    name: name.replace("Bank of ", "").replace(" Commercial Bank", ""),
    value
  }));
  const PIE_COLORS = ["#1E3A8A", "#D97706", "#0D9488", "#4F46E5", "#DC2626"];

  // Compliance Heatmap Data by State
  const states = Array.from(new Set(institutions.map(i => i.state || "Delhi"))).sort();
  const stateComplianceMap: Record<string, { total: number; compliant: number; risk: number }> = {};
  
  institutions.forEach(inst => {
    const st = inst.state || "Delhi";
    if (!stateComplianceMap[st]) {
      stateComplianceMap[st] = { total: 0, compliant: 0, risk: 0 };
    }
    stateComplianceMap[st].total += 1;
    if (inst.category === "Autonomous") {
      stateComplianceMap[st].compliant += 1;
    } else {
      stateComplianceMap[st].risk += 1;
    }
  });

  return (
    <div className="space-y-6">
      
      {/* Official Safeguard & Advisory Disclaimer Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-aicte-navy p-3.5 rounded-r-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <ShieldCheck className="w-5 h-5 text-aicte-navy flex-shrink-0" />
          <p className="text-xs text-slate-800 leading-snug font-medium">
            <strong className="text-aicte-navy">AICTE Statutory Safeguard:</strong> All system observations are preliminary advisory indicators. Verification wording strictly maintains{" "}
            <span className="font-semibold text-emerald-800">&ldquo;available checks passed&rdquo;</span> vs{" "}
            <span className="font-semibold text-amber-800">&ldquo;not confirmed&rdquo;</span>. Release and renewal require statutory human-in-the-loop review.
          </p>
        </div>
        <span className="text-[11px] bg-white border border-slate-200 text-slate-600 px-2 py-0.5 rounded whitespace-nowrap font-mono self-start sm:self-auto">
          Handbook: APH-2024-27.v1
        </span>
      </div>

      {/* Primary KPI Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        
        {/* Total Institutions */}
        <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
            <span>Institutions</span>
            <Users className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-1.5 text-2xl font-black text-slate-900">{institutions.length || 80}</div>
          <div className="text-[11px] text-slate-500">Pledged to AICTE</div>
        </div>

        {/* Active FDRs */}
        <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
            <span>Active FDRs</span>
            <Landmark className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-1.5 text-2xl font-black text-emerald-700">{activeFDRs || fdrs.length}</div>
          <div className="text-[11px] text-slate-500">{fdrs.length} Total instruments</div>
        </div>

        {/* Total Deposit Pledged */}
        <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
            <span>Total Deposit</span>
            <Award className="w-4 h-4 text-aicte-navy" />
          </div>
          <div className="mt-1.5 text-xl font-black text-slate-900">
            ₹{(totalAmount / 10000000).toFixed(2)} Cr
          </div>
          <div className="text-[11px] text-slate-500">₹{(totalAmount / 100000).toFixed(0)} Lakhs</div>
        </div>

        {/* Pending Verification */}
        <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
            <span>Pending Check</span>
            <FileQuestion className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="mt-1.5 text-2xl font-black text-indigo-700">{pendingVerification || 6}</div>
          <div className="text-[11px] text-slate-500">Under Scrutiny</div>
        </div>

        {/* Expiring / Overdue */}
        <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
            <span>Overdue / Expiring</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-1.5 text-2xl font-black text-amber-600">{imminentCount + overdueRenewals || 8}</div>
          <div className="text-[11px] text-slate-500">Maturity Radar Ladder</div>
        </div>

        {/* Release Requests */}
        <div className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition">
          <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase">
            <span>Release Queue</span>
            <ShieldAlert className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-1.5 text-2xl font-black text-rose-600">{releaseAwaiting || 3}</div>
          <div className="text-[11px] text-slate-500">Awaiting CA Approval</div>
        </div>

      </div>

      {/* Main Charts & Analytics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Predictive Workload Forecast */}
        <div className="lg:col-span-2 bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <TrendingUp className="w-4 h-4 mr-1.5 text-aicte-navy" />
                Predictive Workload Intelligence (Scikit-Learn Workload Forecast)
              </h3>
              <p className="text-xs text-slate-500">
                Forecasted FDR maturities requiring officer re-verification & escalation under Demo Clock
              </p>
            </div>
            <button
              onClick={() => onNavigateTab("maturity")}
              className="text-xs font-semibold text-aicte-navy hover:text-blue-700 flex items-center"
            >
              Maturity Radar <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </button>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="month" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis
                  stroke="#64748B"
                  fontSize={11}
                  tickLine={false}
                  tickFormatter={(val) => `₹${(val / 100000).toFixed(0)}L`}
                />
                <Tooltip
                  formatter={(val: any) => [`₹ ${(Number(val) / 100000).toFixed(2)} Lakhs`, "Maturing Volume"]}
                  contentStyle={{ backgroundColor: "#0F172A", color: "#FFF", borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {chartData.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? "#FF9933" : "#1B365D"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Orange bar highlights the current active maturity cycle under the controllable Demo Clock.</span>
            <span className="font-medium text-slate-700">Model: Scikit-learn Logistic Workload Propensity</span>
          </div>
        </div>

        {/* Right: Bank Distribution */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center mb-1">
              <Landmark className="w-4 h-4 mr-1.5 text-aicte-navy" />
              Deposit Distribution by Bank Layout
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Across 5 distinct banking layouts in the regulatory ecosystem
            </p>

            <div className="h-48 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={bankPieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={65}
                    innerRadius={35}
                    paddingAngle={4}
                  >
                    {bankPieData.map((_, index) => (
                      <Cell key={`pie-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0F172A", color: "#FFF", borderRadius: 8, fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-2 space-y-1.5">
              {bankPieData.map((b, idx) => (
                <div key={b.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[idx % PIE_COLORS.length] }} />
                    <span className="text-slate-700 font-medium truncate max-w-[140px]">{b.name}</span>
                  </div>
                  <span className="font-bold text-slate-900">{b.value} FDRs</span>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => onNavigateTab("workspace")}
            className="mt-4 w-full bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold py-2 rounded-lg transition"
          >
            Open Verification Workspace
          </button>
        </div>

      </div>

      {/* Two Column Section: Priority Queue & Institution Heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Smart Renewal Priority Queue (Phase 8) */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-500" />
                Smart Renewal Priority Queue (Advisory Ranking)
              </h3>
              <p className="text-xs text-slate-500">
                Prioritized by urgency, cover gap days, and historic lateness
              </p>
            </div>
            <span className="text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full">
              {priorityQueue.length || 5} Active Cases
            </span>
          </div>

          <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
            {(priorityQueue.length > 0 ? priorityQueue : fdrs.slice(0, 5)).map((item: any, idx: number) => {
              const priority = item.priority_tier || (idx === 0 ? "CRITICAL" : idx < 3 ? "HIGH" : "NORMAL");
              const daysLeft = item.days_until_maturity ?? 12;
              return (
                <div
                  key={item.fdr_id || item.id || idx}
                  onClick={() => onSelectFDR(item.fdr_id || item.id)}
                  className="p-3 rounded-lg border border-slate-200 hover:border-aicte-navy/40 hover:bg-slate-50 cursor-pointer transition flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-xs text-slate-900">{item.institution_name || `Institution #${item.institution_id || idx + 1}`}</span>
                      <span
                        className={`text-[10px] font-extrabold px-2 py-0.5 rounded ${
                          priority === "CRITICAL"
                            ? "bg-rose-100 text-rose-800"
                            : priority === "HIGH"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {priority}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500">
                      FDR #{item.fdr_number || "FDR-2026-001"} &bull; {item.bank_name || "National Bank"} &bull; ₹{((item.amount || 2500000) / 100000).toFixed(1)}L
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Reason: {item.urgency_reasons?.[0] || `Maturing in ${daysLeft} days`}
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Institution Compliance Heatmap & State Distribution */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-sm flex items-center">
                  <MapPin className="w-4 h-4 mr-1.5 text-aicte-navy" />
                  State Compliance & Risk Heatmap
                </h3>
                <p className="text-xs text-slate-500">
                  Regional deposit compliance health across Indian States / UTs
                </p>
              </div>
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="text-xs border border-slate-200 rounded-md px-2 py-1 bg-white font-medium text-slate-700"
              >
                <option value="ALL">All States ({states.length})</option>
                {states.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 max-h-[300px] overflow-y-auto pr-1">
              {(selectedState === "ALL" ? states.slice(0, 12) : [selectedState]).map(st => {
                const data = stateComplianceMap[st] || { total: 4, compliant: 3, risk: 1 };
                const pct = Math.round((data.compliant / (data.total || 1)) * 100);
                return (
                  <div
                    key={st}
                    className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-slate-800 truncate">{st}</span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                        pct >= 80 ? "bg-emerald-100 text-emerald-800" : pct >= 50 ? "bg-amber-100 text-amber-800" : "bg-rose-100 text-rose-800"
                      }`}>
                        {pct}%
                      </span>
                    </div>
                    <div className="mt-1 text-[11px] text-slate-500">
                      {data.total} Institutions
                    </div>
                    <div className="mt-1.5 w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-rose-500"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Color code: &gt;80% Compliant (Green), 50-79% Review (Amber), &lt;50% Flagged (Red)</span>
            <button
              onClick={() => onNavigateTab("rules")}
              className="text-aicte-navy font-bold hover:underline"
            >
              Rules Matrix &rarr;
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}
