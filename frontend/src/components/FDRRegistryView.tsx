"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/translations";
import {
  Search, Filter, Plus, FileText, CheckCircle2, AlertTriangle,
  Clock, ShieldAlert, ArrowUpDown, ExternalLink
} from "lucide-react";

interface FDRRegistryViewProps {
  lang: Language;
  fdrs: any[];
  onSelectFDR: (id: number) => void;
  onOpenCreateModal: () => void;
  activeRole: string;
}

export function FDRRegistryView({
  lang,
  fdrs,
  onSelectFDR,
  onOpenCreateModal,
  activeRole
}: FDRRegistryViewProps) {
  const t = translations[lang];
  const [searchTerm, setSearchTerm] = useState("");
  const [filterPriority, setFilterPriority] = useState("ALL");
  const [filterStatus, setFilterStatus] = useState("ALL");

  const filtered = fdrs.filter((fdr) => {
    const matchesSearch =
      fdr.fdr_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
      fdr.bank_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesPriority = filterPriority === "ALL" || fdr.review_priority_level === filterPriority;
    const matchesStatus = filterStatus === "ALL" || fdr.status === filterStatus;
    return matchesSearch && matchesPriority && matchesStatus;
  });

  return (
    <div className="space-y-4">
      
      {/* Top Filter & Action Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex flex-1 items-center space-x-3">
          {/* Search Box */}
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by FDR Number, Bank, or Institution..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-aicte-navy"
            />
          </div>

          {/* Filter by Priority */}
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Priorities</option>
            <option value="CRITICAL">Critical Priority</option>
            <option value="HIGH">High Priority</option>
            <option value="MEDIUM">Medium Priority</option>
            <option value="LOW">Low Priority</option>
          </select>

          {/* Filter by Status */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLIANT">Compliant</option>
            <option value="UNDER_VERIFICATION">Under Verification</option>
            <option value="RENEWAL_DUE">Renewal Due</option>
            <option value="RELEASE_REQUESTED">Release Requested</option>
            <option value="RENEWED_SUPERSEDED">Renewed (Superseded)</option>
          </select>
        </div>

        {/* Action Button */}
        <button
          onClick={onOpenCreateModal}
          className="flex items-center space-x-1.5 bg-aicte-navy hover:bg-aicte-darkNavy text-white font-bold text-xs px-3.5 py-2 rounded-lg shadow transition"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Security Deposit</span>
        </button>
      </div>

      {/* FDR Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">Instrument / FDR #</th>
                <th className="py-3 px-4">Issuing Bank & Branch</th>
                <th className="py-3 px-4 text-right">Pledged Amount (₹)</th>
                <th className="py-3 px-4">Maturity Date</th>
                <th className="py-3 px-4 text-center">Review Priority Indicator</th>
                <th className="py-3 px-4">Regulatory Status</th>
                <th className="py-3 px-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {filtered.map((fdr) => (
                <tr
                  key={fdr.id}
                  className="hover:bg-slate-50/80 transition cursor-pointer"
                  onClick={() => onSelectFDR(fdr.id)}
                >
                  <td className="py-3 px-4 font-mono font-bold text-slate-900">
                    <div className="flex items-center space-x-1.5">
                      <FileText className="w-4 h-4 text-aicte-navy" />
                      <span>{fdr.fdr_number}</span>
                    </div>
                    {fdr.predecessor_fdr_id && (
                      <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded font-sans">
                        Linked Renewal Chain
                      </span>
                    )}
                  </td>
                  
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-800">{fdr.bank_name}</div>
                    <div className="text-[11px] text-slate-500">{fdr.branch_name} &bull; IFSC: {fdr.ifsc_code}</div>
                  </td>

                  <td className="py-3 px-4 text-right font-black text-slate-900 font-mono">
                    ₹ {Number(fdr.amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </td>

                  <td className="py-3 px-4 text-slate-700 font-mono">
                    {fdr.maturity_date}
                    <div className="text-[10px] text-slate-400 font-sans">
                      Tenure: {fdr.tenure_months} Months
                    </div>
                  </td>

                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-extrabold ${
                        fdr.review_priority_level === "CRITICAL"
                          ? "bg-rose-100 text-rose-800 border border-rose-200"
                          : fdr.review_priority_level === "HIGH"
                          ? "bg-rose-50 text-rose-700 border border-rose-200"
                          : fdr.review_priority_level === "MEDIUM"
                          ? "bg-amber-100 text-amber-800 border border-amber-200"
                          : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                      }`}
                    >
                      {fdr.review_priority_level} ({fdr.review_priority_score})
                    </span>
                    {fdr.officer_override && (
                      <span className="block text-[9px] text-purple-700 font-semibold mt-0.5">
                        Officer Overridden
                      </span>
                    )}
                  </td>

                  <td className="py-3 px-4">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold ${
                        fdr.status === "COMPLIANT"
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : fdr.status === "RENEWAL_DUE"
                          ? "bg-amber-50 text-amber-700 border border-amber-300"
                          : fdr.status === "RELEASE_REQUESTED"
                          ? "bg-blue-50 text-blue-700 border border-blue-200"
                          : fdr.status === "RELEASED"
                          ? "bg-slate-100 text-slate-600"
                          : fdr.status === "RENEWED_SUPERSEDED"
                          ? "bg-slate-100 text-slate-500 line-through"
                          : "bg-rose-50 text-rose-700 border border-rose-200"
                      }`}
                    >
                      {fdr.status}
                    </span>
                  </td>

                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectFDR(fdr.id);
                      }}
                      className="text-xs text-aicte-navy font-bold hover:underline inline-flex items-center"
                    >
                      Inspect <ExternalLink className="w-3 h-3 ml-1" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

