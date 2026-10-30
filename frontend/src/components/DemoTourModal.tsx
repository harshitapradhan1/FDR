"use client";

import React, { useState } from "react";
import { Language, translations } from "@/lib/translations";
import {
  Sparkles, CheckCircle2, ArrowRight, ArrowLeft, X, Shield,
  FileText, Landmark, Clock, Lock, Award
} from "lucide-react";
import confetti from "canvas-confetti";

interface DemoTourModalProps {
  lang: Language;
  onClose: () => void;
  onSelectTab: (tab: string) => void;
  onSelectFDR: (id: number) => void;
}

export function DemoTourModal({
  lang,
  onClose,
  onSelectTab,
  onSelectFDR
}: DemoTourModalProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      title: "1. Four-Level Field Provenance Tracking",
      subtitle: "Zero Black-Box Transparency",
      icon: Shield,
      description: "Unlike black-box AI tools, DepoSafe records a 4-level audit trail for every single field: Submitted (Institution) → AI Extracted (PyMuPDF) → Bank Confirmed (CBS Mock) → Officer Verified (Human-in-the-Loop), explicitly flagging discrepancies and mismatches.",
      actionLabel: "Inspect Deposit Provenance Matrix",
      action: () => {
        onSelectTab("registry");
        onSelectFDR(2); // Opens FDR 2 which has mismatches
      }
    },
    {
      title: "2. Document Forensics & Tampering Scans",
      subtitle: "Perceptual Image Hash (pHash) & Metadata Inspection",
      icon: FileText,
      description: "Detects graphic editing software (Canva, Photoshop, GIMP) embedded in PDF metadata, computes pHash visual collision for reused deposit templates across institutions, and checks Laplacian scan blur.",
      actionLabel: "View Document Forensics & Hashes",
      action: () => {
        onSelectTab("registry");
        onSelectFDR(2);
      }
    },
    {
      title: "3. Bank Verification Adapter Pattern",
      subtitle: "Simulated SFMS Mock with Official Disclaimers",
      icon: Landmark,
      description: "Clean BankVerificationAdapter interface. Clearly watermarked 'SIMULATED, not a real bank verification' with statutory wording 'available checks passed' vs 'not confirmed'. Allows manual officer verification recording if bank feed is unavailable.",
      actionLabel: "Test Bank Verification Simulator",
      action: () => {
        onSelectTab("registry");
        onSelectFDR(1);
      }
    },
    {
      title: "4. Controllable Demo Clock & Predictive Workload",
      subtitle: "Live Maturity & Reminder Escalation Testing",
      icon: Clock,
      description: "Admins can advance simulated 'today' (+15, +30, +90 days) during a live demo to instantly trigger T-15 escalations, maturity reminders, and predictive verification workload charts without waiting months.",
      actionLabel: "Explore Workload & Demo Clock",
      action: () => {
        onSelectTab("dashboard");
      }
    },
    {
      title: "5. Append-Only Cryptographic Audit Ledger",
      subtitle: "Blockchain-Grade Hash Chain: H_n = SHA256(H_{n-1} || event_n)",
      icon: Lock,
      description: "Every state transition, extraction, and officer decision writes to a cryptographic hash chain. Provides one-click mathematical integrity verification that zero records have been altered, deleted, or inserted.",
      actionLabel: "Inspect Cryptographic Hash Chain",
      action: () => {
        onSelectTab("audit");
      }
    },
    {
      title: "6. Empirical Evaluation Harness",
      subtitle: "Empirically Measured Benchmarks on Labelled Data",
      icon: Award,
      description: "DepoSafe ships an evaluation harness with real numbers: 100% extraction F1-score, 100% forensic anomaly accuracy, and ~49ms document latency measured live on certified synthetic data. Zero unmeasured claims.",
      actionLabel: "View Evaluation Harness Dashboard",
      action: () => {
        onSelectTab("evaluation");
        confetti({ particleCount: 50, spread: 80 });
      }
    }
  ];

  const step = steps[currentStep];
  const StepIcon = step.icon;

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onClose();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white max-w-xl w-full rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-aicte-navy via-slate-900 to-aicte-darkNavy text-white p-5 flex items-center justify-between border-b-2 border-aicte-saffron">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-aicte-saffron text-slate-950 flex items-center justify-center font-bold">
              <Sparkles className="w-4 h-4 fill-current" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm text-white">90-Second Grand Finale Demo Tour</h3>
              <p className="text-[11px] text-slate-300">Step {currentStep + 1} of {steps.length}: {step.subtitle}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-300 hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step Body */}
        <div className="p-6 space-y-4 text-xs">
          <div className="flex items-start space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-aicte-navy flex items-center justify-center flex-shrink-0">
              <StepIcon className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <h4 className="font-black text-slate-900 text-sm">{step.title}</h4>
              <p className="text-slate-600 leading-relaxed text-xs">{step.description}</p>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={() => {
                step.action();
                onClose();
              }}
              className="w-full bg-slate-100 hover:bg-slate-200 text-aicte-navy font-bold py-2.5 px-4 rounded-xl transition flex items-center justify-center space-x-1.5 border border-slate-200 shadow-sm"
            >
              <span>{step.actionLabel}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Footer Navigation */}
        <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={currentStep === 0}
            className="text-xs text-slate-600 font-bold hover:text-slate-900 disabled:opacity-30 flex items-center space-x-1"
          >
            <ArrowLeft className="w-3 h-3" />
            <span>Previous</span>
          </button>

          <div className="flex space-x-1.5">
            {steps.map((_, idx) => (
              <span
                key={idx}
                className={`w-2 h-2 rounded-full transition ${
                  idx === currentStep ? "bg-aicte-navy w-4" : "bg-slate-300"
                }`}
              />
            ))}
          </div>

          <button
            onClick={handleNext}
            className="text-xs bg-aicte-navy hover:bg-aicte-darkNavy text-white font-bold px-3 py-1.5 rounded-lg flex items-center space-x-1"
          >
            <span>{currentStep === steps.length - 1 ? "Finish Tour" : "Next Step"}</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

      </div>
    </div>
  );
}

