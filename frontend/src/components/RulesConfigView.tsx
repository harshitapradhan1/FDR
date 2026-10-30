"use client";

import React, { useEffect, useState } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import { BookOpen, Shield, CheckCircle, AlertTriangle, Landmark, Tag } from "lucide-react";

interface RulesConfigViewProps {
  lang: Language;
}

export function RulesConfigView({ lang }: RulesConfigViewProps) {
  const t = translations[lang];
  const [rulesData, setRulesData] = useState<any>(null);

  useEffect(() => {
    api.getActiveRules().then(setRulesData).catch(console.error);
  }, []);

  const norms = rulesData?.rules?.deposit_norms_inr || {};
  const concessions = rulesData?.rules?.category_concessions || {};
  const banks = rulesData?.rules?.rbi_scheduled_commercial_banks || [];

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-xl shadow-sm space-y-1">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <h3 className="font-extrabold text-amber-900 text-sm">
            Statutory Versioned Regulations: {rulesData?.version_tag || "APH-2024-27.v1"}
          </h3>
        </div>
        <p className="text-xs text-amber-800">
          <strong>Non-negotiable Safeguard:</strong> {rulesData?.disclaimer || "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin"}. Amounts, validity, and release conditions are version-controlled configurations with effective dates. Never hardcoded.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Deposit Norms by Program & Level */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
          <h4 className="font-bold text-slate-900 text-sm flex items-center">
            <BookOpen className="w-4 h-4 mr-2 text-aicte-navy" />
            Prescribed Minimum Security Deposit Norms (INR)
          </h4>

          <div className="space-y-3 text-xs">
            {Object.keys(norms).map((cat) => (
              <div key={cat} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                <span className="font-bold text-slate-900 block mb-1">{cat}</span>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(norms[cat]).map(([lvl, amt]: any) => (
                    <span key={lvl} className="bg-white px-2.5 py-1 rounded border border-slate-200 text-slate-700 font-mono">
                      {lvl}: <strong>₹ {Number(amt).toLocaleString("en-IN")}</strong>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Concessions & Scheduled Banks */}
        <div className="space-y-6">
          
          {/* Concessions Card */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3 text-xs">
            <h4 className="font-bold text-slate-900 text-sm flex items-center">
              <Tag className="w-4 h-4 mr-2 text-aicte-saffron" />
              Special Category Regulatory Concessions
            </h4>

            <div className="grid grid-cols-2 gap-2">
              {Object.entries(concessions).map(([cat, rate]: any) => (
                <div key={cat} className="p-2.5 rounded bg-slate-50 border border-slate-200 flex items-center justify-between">
                  <span className="text-slate-700 font-semibold">{cat}:</span>
                  <span className="font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                    {(rate * 100).toFixed(0)}% Concession
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Whitelisted Scheduled Banks */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3 text-xs">
            <h4 className="font-bold text-slate-900 text-sm flex items-center">
              <Landmark className="w-4 h-4 mr-2 text-aicte-emerald" />
              RBI Scheduled Commercial Banks Whitelist
            </h4>

            <div className="flex flex-wrap gap-1.5">
              {banks.map((b: string) => (
                <span key={b} className="bg-slate-100 text-slate-800 px-2 py-1 rounded text-[11px] font-medium border border-slate-200">
                  {b}
                </span>
              ))}
            </div>
            <p className="text-[10px] text-slate-400 mt-1">
              Instruments issued by non-scheduled urban co-ops trigger high-priority inspection flags.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
}

