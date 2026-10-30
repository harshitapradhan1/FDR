"use client";

import React from "react";
import { Language, translations } from "@/lib/translations";
import {
  ShieldCheck, AlertTriangle, Clock, Landmark, FileText, CheckCircle,
  TrendingUp, Users, ArrowRight, ShieldAlert, Award
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";

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

  const totalAmount = fdrs.reduce((acc, curr) => acc + (curr.amount || 0), 0);
  const highPriorityCount = fdrs.filter(f => f.review_priority_level === "HIGH" || f.review_priority_level === "CRITICAL").length;
  const imminentCount = workload?.summary?.critical_escalation_t15 + workload?.summary?.warning_due_soon_t30 || 0;

  const chartData = workload?.monthly_forecast?.length > 0 ? workload.monthly_forecast : [
    { month: "Apr 2024", amount: 3500000 },
    { month: "May 2024", amount: 1500000 },
    { month: "Jun 2024", amount: 2500000 },
    { month: "Jul 2024", amount: 1500000 },
  ];

  return (
    <div className="space-y-6">
      
      {/* Official Safeguard & Advisory Disclaimer Banner */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-l-4 border-aicte-navy p-3.5 rounded-r-lg shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center space-x-2.5">
          <ShieldCheck className="w-5 h-5 text-aicte-navy flex-shrink-0" />
          <p className="text-xs text-slate-800 leading-snug font-medium">
            <strong className="text-aicte-navy">Statutory Advisory Safeguard:</strong> {t.advisoryNotice} Passing validation wording is strictly{" "}
            <span className="font-semibold text-emerald-800">&ldquo;available checks passed&rdquo;</span> vs{" "}
            <span className="font-semibold text-amber-800">&ldquo;not confirmed&rdquo;</span>. Release authorized solely by Competent Authority.
          </p>
        </div>
        <span className="text-[11px] bg-white border border-slate-200 text-slate-600 px-2 py-0.5 rounded whitespace-nowrap font-mono self-start sm:self-auto">
          Rule: APH-2024-27.v1
        </span>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Security Deposits */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t.totalPledged}</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-aicte-emerald flex items-center justify-center">
              <Landmark className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-black text-slate-900">₹ {(totalAmount / 100000).toFixed(1)} Lakhs</span>
          </div>
          <div className="mt-1 text-xs text-slate-500 flex items-center">
            <span className="text-emerald-700 font-semibold">{fdrs.length}</span> &nbsp;pledged instruments recorded
          </div>
        </div>

        {/* High Priority Review Alerts */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t.reviewPriorityAlerts}</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-black text-rose-600">{highPriorityCount}</span>
            <span className="text-xs text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full font-bold">Priority Review</span>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            Advisory risk scores requiring human justification
          </div>
        </div>

        {/* Imminent Maturities (< 30 days) */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t.imminentMaturities}</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-black text-amber-600">{imminentCount}</span>
            <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full font-bold">T-15 / T-30 Queue</span>
          </div>
          <div className="mt-1 text-xs text-slate-500">
            Automated escalation reminders active
          </div>
        </div>

        {/* Cryptographic Audit Ledger */}
        <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{t.auditStatus}</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <CheckCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-sm font-bold text-emerald-700 flex items-center">
              <CheckCircle className="w-4 h-4 mr-1 text-emerald-600" />
              {auditStatus?.verified ? "SHA256 Intact" : "Verifying..."}
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-500 font-mono">
            Block #{auditStatus?.latest_sequence || 2} &bull; Immutable Ledger
          </div>
        </div>

      </div>

      {/* Main Charts & Workload Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left: Predictive Workload Maturity Forecast */}
        <div className="lg:col-span-2 bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <TrendingUp className="w-4 h-4 mr-1.5 text-aicte-navy" />
                Predictive Workload: Maturity & Renewal Schedule
              </h3>
              <p className="text-xs text-slate-500">
                Forecasted deposit maturities requiring officer re-verification by month
              </p>
            </div>
            <button
              onClick={() => onNavigateTab("workload")}
              className="text-xs font-semibold text-aicte-navy hover:text-blue-700 flex items-center"
            >
              Full Forecast <ArrowRight className="w-3.5 h-3.5 ml-1" />
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
                  formatter={(val: any) => [`₹ ${(Number(val) / 100000).toFixed(2)} Lakhs`, "Maturing Deposits"]}
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
            <span>Orange highlight indicates next maturity cycle under demo clock</span>
            <span className="font-medium text-slate-700">Source: AICTE Regulatory Ledger</span>
          </div>
        </div>

        {/* Right: Urgent Priority Review Queue */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-500" />
                Urgent Review Queue
              </h3>
              <span className="text-[10px] bg-slate-100 text-slate-700 font-bold px-2 py-0.5 rounded">
                {fdrs.length} Items
              </span>
            </div>

            <div className="space-y-3">
              {fdrs.slice(0, 3).map((fdr) => (
                <div
                  key={fdr.id}
                  onClick={() => onSelectFDR(fdr.id)}
                  className="p-3 rounded-lg border border-slate-200 hover:border-aicte-navy/40 hover:bg-slate-50 cursor-pointer transition"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900">{fdr.bank_name}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                        fdr.review_priority_level === "HIGH" || fdr.review_priority_level === "CRITICAL"
                          ? "bg-rose-100 text-rose-800"
                          : fdr.review_priority_level === "MEDIUM"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-emerald-100 text-emerald-800"
                      }`}
                    >
                      {fdr.review_priority_level} PRIORITY ({fdr.review_priority_score})
                    </span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
                    <span className="font-mono">#{fdr.fdr_number}</span>
                    <span className="font-semibold text-slate-800">₹ {(fdr.amount / 100000).toFixed(2)} Lakhs</span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[11px] text-slate-400">
                    <span>Status: <strong className="text-slate-600">{fdr.status}</strong></span>
                    <span className="text-aicte-navy font-semibold hover:underline">Inspect 4-Level &rarr;</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => onNavigateTab("registry")}
            className="mt-4 w-full bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold py-2 rounded-lg transition text-center"
          >
            View Complete FDR Intelligence Registry
          </button>
        </div>

      </div>

    </div>
  );
}
