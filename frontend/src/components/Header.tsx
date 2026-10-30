"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import { Shield, Clock, Globe, UserCheck, Calendar, Sparkles, CheckCircle2 } from "lucide-react";
import confetti from "canvas-confetti";

interface HeaderProps {
  lang: Language;
  setLang: (l: Language) => void;
  activeRole: string;
  setActiveRole: (role: string) => void;
  currentSimulatedDate: string;
  onClockUpdate: () => void;
  onStartDemoTour: () => void;
}

export const ROLE_ACCOUNTS = [
  { role: "SYSTEM_ADMIN", label: "System Admin", email: "admin@deposafe.aicte.gov.in" },
  { role: "VERIFICATION_OFFICER", label: "Verification Officer", email: "officer@deposafe.aicte.gov.in" },
  { role: "REGIONAL_OFFICER", label: "Regional Officer", email: "ro.north@deposafe.aicte.gov.in" },
  { role: "COMPETENT_AUTHORITY", label: "Competent Authority", email: "director.approval@aicte-india.org" },
  { role: "INSTITUTION_USER", label: "Institution (Vidya Tech)", email: "institution1@vidya.edu.in" }
];

export function Header({
  lang,
  setLang,
  activeRole,
  setActiveRole,
  currentSimulatedDate,
  onClockUpdate,
  onStartDemoTour
}: HeaderProps) {
  const t = translations[lang];
  const [advancing, setAdvancing] = useState(false);

  const handleRoleChange = async (newRole: string) => {
    setActiveRole(newRole);
    const acc = ROLE_ACCOUNTS.find(a => a.role === newRole);
    if (acc) {
      try {
        const res = await api.login(acc.email, "Password@123");
        localStorage.setItem("deposafe_token", res.access_token);
        localStorage.setItem("deposafe_role", newRole);
      } catch (err) {
        console.error("Role switch error:", err);
      }
    }
  };

  const advanceDays = async (days: number) => {
    setAdvancing(true);
    try {
      await api.advanceClock(days);
      onClockUpdate();
      confetti({ particleCount: 40, spread: 60, origin: { y: 0.1 } });
    } catch (err) {
      console.error(err);
    } finally {
      setAdvancing(false);
    }
  };

  return (
    <header className="bg-aicte-navy text-white shadow-md border-b-4 border-aicte-saffron">
      {/* Top Gov Tricolor Strip */}
      <div className="h-1 bg-gradient-to-r from-aicte-saffron via-white to-aicte-emerald w-full" />
      
      <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          
          {/* Logo & Bureau Title */}
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-lg bg-white/10 p-2 flex items-center justify-center border border-white/20 shadow-inner">
              <Shield className="w-7 h-7 text-aicte-saffron" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-xl tracking-tight text-white">{t.portalTitle}</span>
                <span className="text-[10px] bg-aicte-emerald/80 text-white px-2 py-0.5 rounded font-semibold tracking-wider uppercase">
                  AICTE Gov-Tech
                </span>
                <span className="text-[10px] bg-aicte-saffron/90 text-aicte-darkNavy px-2 py-0.5 rounded font-bold tracking-wider uppercase">
                  APH 2024-27
                </span>
              </div>
              <p className="text-xs text-slate-300 font-medium">
                {t.portalSubtitle} &bull; <span className="text-slate-400">{t.aicteDept}</span>
              </p>
            </div>
          </div>

          {/* Right Controls: Role Switcher, Language Toggle, Demo Tour */}
          <div className="flex flex-wrap items-center gap-2">
            
            {/* 90-Sec Demo Tour Button */}
            <button
              onClick={onStartDemoTour}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-aicte-saffron to-amber-500 hover:from-aicte-saffronDark hover:to-amber-600 text-slate-900 font-bold text-xs px-3 py-1.5 rounded-md shadow transition"
              title="Guided 90-second Grand Finale walkthrough"
            >
              <Sparkles className="w-3.5 h-3.5 text-slate-950" />
              <span>{t.demoTour}</span>
            </button>

            {/* Role Switcher */}
            <div className="flex items-center bg-white/10 rounded-md px-2 py-1 border border-white/15 text-xs">
              <UserCheck className="w-3.5 h-3.5 text-aicte-saffron mr-1.5" />
              <select
                value={activeRole}
                onChange={(e) => handleRoleChange(e.target.value)}
                className="bg-transparent text-white font-medium text-xs focus:outline-none cursor-pointer pr-1"
              >
                {ROLE_ACCOUNTS.map((acc) => (
                  <option key={acc.role} value={acc.role} className="bg-slate-900 text-white">
                    {acc.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Language Switcher */}
            <button
              onClick={() => setLang(lang === "en" ? "hi" : "en")}
              className="flex items-center space-x-1 bg-white/10 hover:bg-white/20 text-white text-xs px-2.5 py-1 rounded-md border border-white/15 transition"
            >
              <Globe className="w-3.5 h-3.5 text-cyan-300" />
              <span className="font-semibold">{lang === "en" ? "हिन्दी" : "English"}</span>
            </button>
          </div>
        </div>

        {/* Controllable DEMO CLOCK Bar */}
        <div className="mt-3 pt-2.5 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-2">
            <span className="flex items-center space-x-1 bg-amber-400/20 text-amber-200 border border-amber-400/30 px-2 py-0.5 rounded font-mono font-medium">
              <Clock className="w-3 h-3 text-amber-300" />
              <span>DEMO CLOCK:</span>
              <strong className="text-white">{currentSimulatedDate || "Loading..."}</strong>
            </span>
            <span className="text-[11px] text-slate-300 hidden sm:inline">
              (Live simulated date for maturity & reminder escalation testing)
            </span>
          </div>

          <div className="flex items-center space-x-1.5">
            <span className="text-slate-300 font-medium">Advance simulated date:</span>
            <button
              onClick={() => advanceDays(15)}
              disabled={advancing}
              className="bg-white/10 hover:bg-white/20 text-white px-2 py-0.5 rounded border border-white/20 font-mono text-xs transition"
            >
              +15 Days
            </button>
            <button
              onClick={() => advanceDays(30)}
              disabled={advancing}
              className="bg-white/10 hover:bg-white/20 text-white px-2 py-0.5 rounded border border-white/20 font-mono text-xs transition"
            >
              +30 Days
            </button>
            <button
              onClick={() => advanceDays(90)}
              disabled={advancing}
              className="bg-aicte-emerald/80 hover:bg-aicte-emerald text-white font-bold px-2.5 py-0.5 rounded border border-emerald-400/40 font-mono text-xs transition"
            >
              +90 Days
            </button>
          </div>
        </div>

      </div>
    </header>
  );
}

