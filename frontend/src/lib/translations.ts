export type Language = "en" | "hi";

export const translations = {
  en: {
    portalTitle: "DepoSafe",
    portalSubtitle: "Security Deposit / FDR Intelligence & Management Portal",
    aicteDept: "All India Council for Technical Education (AICTE) - Regulation Bureau",
    govIndia: "Government of India",
    
    // Navigation
    navDashboard: "AICTE Master Dashboard",
    navInstitution: "Institution Portal",
    navWorkspace: "Verification Workspace",
    navMaturity: "Maturity & Renewal Radar",
    navRelease: "Release & Refund Lifecycle",
    navPassport: "Lifecycle Passport",
    navAdmin: "Admin & Governance",
    navRegistry: "FDR Registry & Review",
    navGraph: "Ecosystem Graph",
    navAudit: "Cryptographic Audit",
    navEvaluation: "Evaluation Harness",
    navRules: "Regulation Rules",
    
    // Roles
    roleAdmin: "System Administrator",
    roleOfficer: "Verification Officer",
    roleRegional: "Regional Officer",
    roleCA: "Competent Authority",
    roleInstitution: "Institution User",
    
    // KPI Cards
    totalPledged: "Total Deposit Pledged",
    activeInstruments: "Active FDR Instruments",
    reviewPriorityAlerts: "High Priority Review Alerts",
    imminentMaturities: "Maturities Within 30 Days",
    auditStatus: "Audit Chain Integrity",
    auditUntampered: "Cryptographically Verified",
    
    // Provenance
    levelSubmitted: "1. SUBMITTED (Institution)",
    levelAI: "2. AI EXTRACTED (Scan)",
    levelBank: "3. BANK CONFIRMED (CBS Mock)",
    levelOfficer: "4. OFFICER VERIFIED (Human-in-Loop)",
    statusMismatch: "DISCREPANCY / MISMATCH",
    
    // Statuses
    checksPassed: "Available checks passed",
    notConfirmed: "Not confirmed",
    simulatedNotice: "SIMULATED, not a real bank verification",
    advisoryNotice: "AI is advisory. Versioned APH regulations determine compliance.",
    placeholderNotice: "ILLUSTRATIVE PLACEHOLDERS - configurable by AICTE Admin",
    
    // Actions
    verifyBank: "Run Bank Verification",
    recordManual: "Record Officer Evidence",
    officerOverride: "Officer Override",
    renewFDR: "Renew Instrument",
    requestRelease: "Request Deposit Release",
    authorizeRelease: "Authorize Release Order",
    advanceClock: "Advance Clock",
    demoTour: "90-Second Demo Tour",
    verifyChain: "Verify Cryptographic Audit Chain",
    runBenchmark: "Run Empirical Benchmark",
    
    // Graph
    graphLegend: "Ecosystem Entity Mapping",
    trust: "Society / Trust",
    institution: "Institution",
    bank: "Bank / Branch",
    signatory: "Authorized Signatory"
  },
  hi: {
    portalTitle: "डिपो-सेफ (DepoSafe)",
    portalSubtitle: "सुरक्षा जमा / एफडीआर बुद्धिमत्ता एवं प्रबंधन पोर्टल",
    aicteDept: "अखिल भारतीय तकनीकी शिक्षा परिषद (एआईसीटीई) - विनियमन ब्यूरो",
    govIndia: "भारत सरकार",
    
    // Navigation
    navDashboard: "एआईसीटीई मुख्य डैशबोर्ड",
    navInstitution: "संस्थान पोर्टल",
    navWorkspace: "सत्यापन कार्यक्षेत्र (हीरो)",
    navMaturity: "परिपक्वता एवं नवीनीकरण रडार",
    navRelease: "विमुक्ति एवं प्रतिदाय प्रबंधन",
    navPassport: "जीवनचक्र पासपोर्ट",
    navAdmin: "प्रशासन एवं शासन",
    navRegistry: "एफडीआर पंजी एवं समीक्षा",
    navGraph: "पारिस्थितिकी तंत्र ग्राफ",
    navAudit: "क्रिप्टोग्राफिक ऑडिट लेजर",
    navEvaluation: "मूल्यांकन हार्नेस",
    navRules: "विनियमन नियम",
    
    // Roles
    roleAdmin: "सिस्टम प्रशासक",
    roleOfficer: "सत्यापन अधिकारी",
    roleRegional: "क्षेत्रीय अधिकारी",
    roleCA: "सक्षम प्राधिकारी (Competent Authority)",
    roleInstitution: "संस्थान उपयोगकर्ता",
    
    // KPI Cards
    totalPledged: "कुल गिरवी जमा राशि",
    activeInstruments: "सक्रिय एफडीआर प्रपत्र",
    reviewPriorityAlerts: "उच्च समीक्षा प्राथमिकता अलर्ट",
    imminentMaturities: "30 दिनों में परिपक्व होने वाले",
    auditStatus: "ऑडिट श्रृंखला अखंडता",
    auditUntampered: "क्रिप्टोग्राफ़िक रूप से सत्यापित",
    
    // Provenance
    levelSubmitted: "1. प्रस्तुत (संस्थान द्वारा)",
    levelAI: "2. एआई द्वारा निष्कर्षित (स्कैन)",
    levelBank: "3. बैंक द्वारा पुष्ट (सीबीएस मॉक)",
    levelOfficer: "4. अधिकारी द्वारा सत्यापित",
    statusMismatch: "विसंगति / बेमेल",
    
    // Statuses
    checksPassed: "उपलब्ध जांच उत्तीर्ण (Available checks passed)",
    notConfirmed: "पुष्ट नहीं हुआ (Not confirmed)",
    simulatedNotice: "सिम्युलेटेड, यह वास्तविक बैंक सत्यापन नहीं है",
    advisoryNotice: "एआई सलाहकार है। संस्करण विनियम अनुपालन निर्धारित करते हैं।",
    placeholderNotice: "उदाहरणात्मक प्लेसहोल्डर - एआईसीटीई व्यवस्थापक द्वारा संपादन योग्य",
    
    // Actions
    verifyBank: "बैंक सत्यापन चलाएं",
    recordManual: "अधिकारी साक्ष्य दर्ज करें",
    officerOverride: "अधिकारी ओवरराइड",
    renewFDR: "प्रपत्र का नवीनीकरण करें",
    requestRelease: "जमा राशि विमुक्ति का अनुरोध",
    authorizeRelease: "विमुक्ति आदेश अधिकृत करें",
    advanceClock: "डेमो घड़ी आगे बढ़ाएं",
    demoTour: "90-सेकंड डेमो टूर",
    verifyChain: "क्रिप्टोग्राफिक ऑडिट श्रृंखला सत्यापित करें",
    runBenchmark: "अनुभवजन्य बेंचमार्क चलाएं",
    
    // Graph
    graphLegend: "पारिस्थितिकी तंत्र मैपिंग",
    trust: "सोसायटी / ट्रस्ट",
    institution: "संस्थान",
    bank: "बैंक / शाखा",
    signatory: "अधिकृत हस्ताक्षरकर्ता"
  }
};

