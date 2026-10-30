"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import {
  Sparkles, CheckCircle2, Clock, AlertTriangle, ArrowRight,
  ShieldAlert, RefreshCw, X, Play, Landmark, FileText, UserCheck
} from "lucide-react";
import confetti from "canvas-confetti";

interface DemoModeModalProps {
  lang: Language;
  onClose: () => void;
  onSelectTab: (tab: string) => void;
  onSelectFDR: (id: number) => void;
  onClockUpdate: () => void;
}

export const DEMO_SCENARIO_STEPS = [
  {
    step: 1,
    title: "1. Institution Uploads Instrument",
    desc: "Institution submits suspicious FDR with manipulated pixel-level amount and altered maturity date.",
    tab: "institution",
  },
  {
    step: 2,
    title: "2. Async AI Document OCR Pipeline",
    desc: "PyMuPDF native text extraction, OpenCV deskew, and per-bank YAML layout schema matching run in parallel.",
    tab: "workspace",
  },
  {
    step: 3,
    title: "3. Cross-Document Maturity Mismatch",
    desc: "Cross-document reconciliation flags mismatch: FDR Certificate states 2034, but Bank Confirmation schedule states 2029.",
    tab: "workspace",
  },
  {
    step: 4,
    title: "4. Multi-Modal Duplicate Detection",
    desc: "Perceptual hash (pHash) visual collision detected with existing instrument in AICTE Registry across another college.",
    tab: "workspace",
  },
  {
    step: 5,
    title: "5. Versioned Statutory Compliance Check",
    desc: "APH-2024-27.v1 evaluation marks instrument NON_COMPLIANT with bilingual regulatory citations (EN/HI).",
    tab: "workspace",
  },
  {
    step: 6,
    title: "6. Explainable Risk Score Reaches 78.5",
    desc: "Explainable Risk Engine flags case as HIGH PRIORITY with concrete evidentiary breakdown and recommended officer action.",
    tab: "workspace",
  },
  {
    step: 7,
    title: "7. Officer Requests Institutional Clarification",
    desc: "Verification Officer puts instrument into CLARIFICATION_REQUIRED with statutory scrutiny observation.",
    tab: "workspace",
  },
  {
    step: 8,
    title: "8. Institution Submits Corrected Evidence",
    desc: "Institution uploads certified Bank Manager endorsement letter clarifying validity and authenticating original deposit.",
    tab: "institution",
  },
  {
    step: 9,
    title: "9. Officer Completes Verification (Dual-Truth)",
    desc: "Officer executes Bank CBS Simulation Adapter -> Ledger updated to BANK_CONFIRMED & OFFICER_VERIFIED. FDR marked ACTIVE.",
    tab: "workspace",
  },
  {
    step: 10,
    title: "10. Demo Clock Advanced & Radar Escalates",
    desc: "Demo Clock advanced by +60 days into T-15 radar ladder. Automated Celery Beat escalation reminder fires to officer desk!",
    tab: "maturity",
  }
];

export function DemoModeModal({
  lang,
  onClose,
  onSelectTab,
  onSelectFDR,
  onClockUpdate
}: DemoModeModalProps) {
  const t = translations[lang];

  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const executeStep = async (stepIdx: number) => {
    setCurrentStepIdx(stepIdx);
    const stepData = DEMO_SCENARIO_STEPS[stepIdx];

    onSelectTab(stepData.tab);
    onSelectFDR(1);

    if (stepIdx === 9) {
      // Step 10: Advance demo clock by 15 days
      try {
        await api.advanceClock(15);
        onClockUpdate();
      } catch (err) {
        console.error("Clock advance error in demo mode:", err);
      }
    }

    setCompletedSteps((prev) => Array.from(new Set([...prev, stepIdx])));
    confetti({ particleCount: 20, spread: 45, origin: { y: 0.3 } });
  };

  const handleRunFullDemo = async () => {
    setIsRunning(true);
    for (let i = 0; i < DEMO_SCENARIO_STEPS.length; i++) {
      await executeStep(i);
      await new Promise((r) => setTimeout(r, 1600));
    }
    setIsRunning(false);
    confetti({ particleCount: 70, spread: 80 });
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 border border-slate-200 shadow-2xl space-y-5">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-amber-600" />
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900 text-base">
                Grand Finale Scripted Scenario (Demo Mode)
              </h3>
              <p className="text-xs text-slate-500">
                End-to-end statutory walkthrough: Suspicious FDR &rarr; Discrepancy &rarr; Clarification &rarr; CBS Verification &rarr; Maturity Radar
              </p>
            </div>
          </div>

          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stepper Steps List */}
        <div className="space-y-2 max-h-[380px] overflow-y-auto pr-2 text-xs">
          {DEMO_SCENARIO_STEPS.map((s, idx) => {
            const isCurrent = currentStepIdx === idx;
            const isDone = completedSteps.includes(idx);
            return (
              <div
                key={s.step}
                onClick={() => executeStep(idx)}
                className={`p-3 rounded-xl border cursor-pointer transition flex items-start space-x-3 ${
                  isCurrent
                    ? "bg-amber-50/80 border-amber-300 shadow-sm"
                    : isDone
                    ? "bg-slate-50 border-slate-200 text-slate-700"
                    : "bg-white border-slate-200 hover:bg-slate-50 opacity-80"
                }`}
              >
                <div className="mt-0.5">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] font-bold ${
                      isCurrent ? "border-amber-600 bg-amber-600 text-white" : "border-slate-300 text-slate-500"
                    }`}>
                      {s.step}
                    </div>
                  )}
                </div>

                <div className="space-y-0.5 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 text-xs">{s.title}</span>
                    <span className="text-[10px] uppercase font-mono font-bold text-slate-400">
                      Tab: {s.tab}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-snug">{s.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Actions */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Step {currentStepIdx + 1} of {DEMO_SCENARIO_STEPS.length}
          </span>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleRunFullDemo}
              disabled={isRunning}
              className="flex items-center space-x-1.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 font-black text-xs px-4 py-2 rounded-lg shadow-sm transition"
            >
              <Play className="w-3.5 h-3.5 fill-slate-950" />
              <span>{isRunning ? "Running Scenario..." : "Auto-Play Full Scenario"}</span>
            </button>
            <button
              onClick={onClose}
              className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg transition"
            >
              Close
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

