"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import { X, Plus, Upload, Landmark, Calendar, FileText } from "lucide-react";
import confetti from "canvas-confetti";

interface CreateFDRModalProps {
  lang: Language;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateFDRModal({ lang, onClose, onCreated }: CreateFDRModalProps) {
  const [formData, setFormData] = useState({
    institution_id: 1,
    bank_name: "State Bank of India",
    branch_name: "Connaught Place, New Delhi",
    ifsc_code: "SBIN0000691",
    fdr_number: `SBI-NEW-${Math.floor(10000000 + Math.random() * 90000000)}`,
    amount: 3500000,
    issue_date: new Date().toISOString().split("T")[0],
    maturity_date: new Date(Date.now() + 96 * 30 * 86400000).toISOString().split("T")[0],
    tenure_months: 96,
    interest_rate: 7.25,
    auto_renewal: true,
    lien_marked_to_aicte: true,
    lien_clause_text: "Pledged under Lien jointly in the name of Regional Officer, AICTE (North Western Regional Office) and President/Secretary, Shree Vidya Educational Trust."
  });

  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createFDR(formData);
      confetti({ particleCount: 30, spread: 60 });
      onCreated();
      onClose();
    } catch (err: any) {
      alert("Error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white max-w-2xl w-full rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="bg-aicte-navy text-white px-6 py-4 flex items-center justify-between border-b border-aicte-saffron">
          <div className="flex items-center space-x-2">
            <Plus className="w-5 h-5 text-aicte-saffron" />
            <h3 className="font-extrabold text-base">Register Security Deposit (FDR)</h3>
          </div>
          <button onClick={onClose} className="text-slate-300 hover:text-white p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4 text-xs">
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="font-bold text-slate-700 block mb-1">Issuing Bank Name</label>
              <select
                value={formData.bank_name}
                onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                className="w-full border border-slate-300 rounded p-2 text-xs"
              >
                <option value="State Bank of India">State Bank of India (Scheduled)</option>
                <option value="Punjab National Bank">Punjab National Bank (Scheduled)</option>
                <option value="Bank of Baroda">Bank of Baroda (Scheduled)</option>
                <option value="Canara Bank">Canara Bank (Scheduled)</option>
                <option value="HDFC Bank">HDFC Bank (Scheduled)</option>
                <option value="City Cooperative Urban Bank">City Cooperative Urban Bank (Non-Scheduled Anomaly)</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Branch Name</label>
              <input
                type="text"
                value={formData.branch_name}
                onChange={(e) => setFormData({ ...formData, branch_name: e.target.value })}
                className="w-full border border-slate-300 rounded p-2 text-xs"
                required
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">IFSC Code</label>
              <input
                type="text"
                value={formData.ifsc_code}
                onChange={(e) => setFormData({ ...formData, ifsc_code: e.target.value.toUpperCase() })}
                className="w-full border border-slate-300 rounded p-2 font-mono text-xs uppercase"
                required
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">FDR Instrument Number</label>
              <input
                type="text"
                value={formData.fdr_number}
                onChange={(e) => setFormData({ ...formData, fdr_number: e.target.value })}
                className="w-full border border-slate-300 rounded p-2 font-mono text-xs"
                required
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Pledged Amount (₹ INR)</label>
              <input
                type="number"
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
                className="w-full border border-slate-300 rounded p-2 font-mono text-xs"
                required
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Tenure (Months)</label>
              <input
                type="number"
                value={formData.tenure_months}
                onChange={(e) => setFormData({ ...formData, tenure_months: parseInt(e.target.value) })}
                className="w-full border border-slate-300 rounded p-2 font-mono text-xs"
                required
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Date of Issue</label>
              <input
                type="date"
                value={formData.issue_date}
                onChange={(e) => setFormData({ ...formData, issue_date: e.target.value })}
                className="w-full border border-slate-300 rounded p-2 font-mono text-xs"
                required
              />
            </div>

            <div>
              <label className="font-bold text-slate-700 block mb-1">Date of Maturity</label>
              <input
                type="date"
                value={formData.maturity_date}
                onChange={(e) => setFormData({ ...formData, maturity_date: e.target.value })}
                className="w-full border border-slate-300 rounded p-2 font-mono text-xs"
                required
              />
            </div>
          </div>

          <div>
            <label className="font-bold text-slate-700 block mb-1">AICTE Mandatory Lien Marking Clause</label>
            <textarea
              rows={2}
              value={formData.lien_clause_text}
              onChange={(e) => setFormData({ ...formData, lien_clause_text: e.target.value })}
              className="w-full border border-slate-300 rounded p-2 text-xs"
            />
          </div>

          <div className="flex items-center space-x-4 pt-1">
            <label className="flex items-center space-x-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.auto_renewal}
                onChange={(e) => setFormData({ ...formData, auto_renewal: e.target.checked })}
                className="rounded text-aicte-navy"
              />
              <span className="text-slate-700">Auto-Renewal Clause Active</span>
            </label>

            <label className="flex items-center space-x-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.lien_marked_to_aicte}
                onChange={(e) => setFormData({ ...formData, lien_marked_to_aicte: e.target.checked })}
                className="rounded text-aicte-navy"
              />
              <span className="text-slate-700">Lien Pledged to Regional Officer, AICTE</span>
            </label>
          </div>

          <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-slate-600 text-[11px]">
            * Upon submission, 4-level field provenance records are automatically initialized at stage 1 (SUBMITTED).
          </div>

          <div className="flex justify-end space-x-2 pt-2 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 bg-slate-100 rounded-lg text-slate-700 font-bold">
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-aicte-navy hover:bg-aicte-darkNavy text-white rounded-lg font-bold shadow"
            >
              {loading ? "Recording..." : "Save Deposit Record"}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}

