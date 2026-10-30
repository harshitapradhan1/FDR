"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Language, translations } from "@/lib/translations";
import { api } from "@/lib/api";
import { Header, ROLE_ACCOUNTS } from "@/components/Header";
import { DashboardView } from "@/components/DashboardView";
import { FDRRegistryView } from "@/components/FDRRegistryView";
import { FDRDetailModal } from "@/components/FDRDetailModal";
import { RelationshipGraphView } from "@/components/RelationshipGraphView";
import { AuditLedgerView } from "@/components/AuditLedgerView";
import { EvaluationHarnessView } from "@/components/EvaluationHarnessView";
import { RulesConfigView } from "@/components/RulesConfigView";
import { CreateFDRModal } from "@/components/CreateFDRModal";
import { DemoTourModal } from "@/components/DemoTourModal";
import {
  LayoutDashboard, FileText, GitFork, Lock, Award, BookOpen,
  Calendar, Shield
} from "lucide-react";

export default function DepoSafeApp() {
  const [lang, setLang] = useState<Language>("en");
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [activeRole, setActiveRole] = useState<string>("SYSTEM_ADMIN");

  const [currentSimulatedDate, setCurrentSimulatedDate] = useState<string>("");
  const [fdrs, setFdrs] = useState<any[]>([]);
  const [workload, setWorkload] = useState<any>(null);
  const [auditStatus, setAuditStatus] = useState<any>(null);

  const [selectedFDRDetail, setSelectedFDRDetail] = useState<any>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDemoTourOpen, setIsDemoTourOpen] = useState(false);

  const t = translations[lang];

  // Initialize login for default role
  const initializeAuth = useCallback(async () => {
    try {
      const defaultAcc = ROLE_ACCOUNTS[0];
      const res = await api.login(defaultAcc.email, "Password@123");
      localStorage.setItem("deposafe_token", res.access_token);
      localStorage.setItem("deposafe_role", defaultAcc.role);
    } catch (err) {
      console.error("Initial auth failed:", err);
    }
  }, []);

  // Fetch Core System State
  const refreshSystemData = useCallback(async () => {
    try {
      const [clockRes, fdrList, wlRes, auditRes] = await Promise.all([
        api.getClock().catch(() => ({ current_simulated_date: "2024-04-15" })),
        api.getFDRs().catch(() => []),
        api.getWorkload().catch(() => null),
        api.verifyAuditChain().catch(() => null)
      ]);

      setCurrentSimulatedDate(clockRes.current_simulated_date);
      setFdrs(fdrList);
      setWorkload(wlRes);
      setAuditStatus(auditRes);
    } catch (err) {
      console.error("Data refresh error:", err);
    }
  }, []);

  useEffect(() => {
    initializeAuth().then(() => {
      refreshSystemData();
    });
  }, [initializeAuth, refreshSystemData]);

  const handleSelectFDR = async (id: number) => {
    try {
      const detail = await api.getFDRDetail(id);
      setSelectedFDRDetail(detail);
    } catch (err) {
      console.error("Failed to load FDR detail:", err);
    }
  };

  const handleRefreshDetail = async () => {
    if (selectedFDRDetail) {
      handleSelectFDR(selectedFDRDetail.id);
    }
    refreshSystemData();
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      
      {/* Gov-Tech Header with Controllable Demo Clock & Role Switcher */}
      <Header
        lang={lang}
        setLang={setLang}
        activeRole={activeRole}
        setActiveRole={setActiveRole}
        currentSimulatedDate={currentSimulatedDate}
        onClockUpdate={refreshSystemData}
        onStartDemoTour={() => setIsDemoTourOpen(true)}
      />

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full flex-1 flex flex-col space-y-6">
        
        {/* Navigation Tabs Bar */}
        <div className="bg-white p-1.5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-1 text-xs font-bold overflow-x-auto">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg transition whitespace-nowrap ${
              activeTab === "dashboard"
                ? "bg-aicte-navy text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>{t.navDashboard}</span>
          </button>

          <button
            onClick={() => setActiveTab("registry")}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg transition whitespace-nowrap ${
              activeTab === "registry"
                ? "bg-aicte-navy text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>{t.navRegistry}</span>
            <span className="ml-1 text-[10px] bg-white/20 px-1.5 py-0.2 rounded font-mono">
              {fdrs.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("graph")}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg transition whitespace-nowrap ${
              activeTab === "graph"
                ? "bg-aicte-navy text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <GitFork className="w-4 h-4" />
            <span>{t.navGraph}</span>
          </button>

          <button
            onClick={() => setActiveTab("audit")}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg transition whitespace-nowrap ${
              activeTab === "audit"
                ? "bg-aicte-navy text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <Lock className="w-4 h-4" />
            <span>{t.navAudit}</span>
          </button>

          <button
            onClick={() => setActiveTab("evaluation")}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg transition whitespace-nowrap ${
              activeTab === "evaluation"
                ? "bg-aicte-navy text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <Award className="w-4 h-4 text-amber-400" />
            <span>{t.navEvaluation}</span>
          </button>

          <button
            onClick={() => setActiveTab("rules")}
            className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg transition whitespace-nowrap ${
              activeTab === "rules"
                ? "bg-aicte-navy text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            <BookOpen className="w-4 h-4" />
            <span>{t.navRules}</span>
          </button>
        </div>

        {/* Tab Content Panes */}
        <main className="flex-1">
          {activeTab === "dashboard" && (
            <DashboardView
              lang={lang}
              workload={workload}
              fdrs={fdrs}
              auditStatus={auditStatus}
              onSelectFDR={handleSelectFDR}
              onNavigateTab={(tab) => setActiveTab(tab)}
            />
          )}

          {activeTab === "registry" && (
            <FDRRegistryView
              lang={lang}
              fdrs={fdrs}
              onSelectFDR={handleSelectFDR}
              onOpenCreateModal={() => setIsCreateModalOpen(true)}
              activeRole={activeRole}
            />
          )}

          {activeTab === "graph" && (
            <RelationshipGraphView
              lang={lang}
              onSelectFDR={handleSelectFDR}
            />
          )}

          {activeTab === "audit" && (
            <AuditLedgerView lang={lang} />
          )}

          {activeTab === "evaluation" && (
            <EvaluationHarnessView lang={lang} />
          )}

          {activeTab === "rules" && (
            <RulesConfigView lang={lang} />
          )}
        </main>

      </div>

      {/* Deep FDR Intelligence & Provenance Inspector Modal */}
      {selectedFDRDetail && (
        <FDRDetailModal
          lang={lang}
          fdrDetail={selectedFDRDetail}
          onClose={() => setSelectedFDRDetail(null)}
          onRefresh={handleRefreshDetail}
          activeRole={activeRole}
        />
      )}

      {/* Create Deposit Modal */}
      {isCreateModalOpen && (
        <CreateFDRModal
          lang={lang}
          onClose={() => setIsCreateModalOpen(false)}
          onCreated={refreshSystemData}
        />
      )}

      {/* 90-Second Guided Demo Tour Modal */}
      {isDemoTourOpen && (
        <DemoTourModal
          lang={lang}
          onClose={() => setIsDemoTourOpen(false)}
          onSelectTab={(tab) => setActiveTab(tab)}
          onSelectFDR={handleSelectFDR}
        />
      )}

      {/* Gov Footer */}
      <footer className="bg-slate-900 text-slate-400 text-xs py-4 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-white">DepoSafe AICTE</span>
            <span>&bull; Smart India Hackathon Grand Finale Edition</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Certified Synthetic Data Only &bull; Cryptographic SHA256 Ledger &bull; Human-in-the-Loop Governance
          </div>
        </div>
      </footer>

    </div>
  );
}
