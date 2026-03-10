import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  FileText,
  Award,
  Building2,
  DollarSign,
  ClipboardCheck,
  Send,
  CheckCircle2,
  Clock,
  Globe,
  ArrowRight,
  ChevronRight,
  AlertCircle,
} from "lucide-react";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

interface QualificationStep {
  key: string;
  icon: typeof Building2;
  color: string;
}

const STEPS: QualificationStep[] = [
  { key: "companyInfo", icon: Building2, color: "text-blue-400" },
  { key: "documents", icon: FileText, color: "text-amber-400" },
  { key: "certifications", icon: Award, color: "text-purple-400" },
  { key: "financial", icon: DollarSign, color: "text-emerald-400" },
  { key: "review", icon: ClipboardCheck, color: "text-sky-400" },
  { key: "submit", icon: Send, color: "text-primary-light" },
];

type Difficulty = "easy" | "medium" | "hard";

interface CountryPortal {
  country: string;
  flag: string;
  portal: string;
  documents: string[];
  difficulty: Difficulty;
  estimatedDays: number;
}

const COUNTRY_PORTALS: CountryPortal[] = [
  {
    country: "Saudi Arabia",
    flag: "\u{1F1F8}\u{1F1E6}",
    portal: "Etimad",
    documents: [
      "Commercial Registration (CR)",
      "Chamber of Commerce Certificate",
      "GOSI Certificate",
      "Zakat & Tax Certificate",
      "Financial Statements (2 years)",
    ],
    difficulty: "medium",
    estimatedDays: 7,
  },
  {
    country: "UAE",
    flag: "\u{1F1E6}\u{1F1EA}",
    portal: "Tejari",
    documents: [
      "Trade License",
      "TRN Certificate",
      "Bank Reference Letter",
      "Company Profile",
      "ISO Certificates (if applicable)",
    ],
    difficulty: "easy",
    estimatedDays: 4,
  },
  {
    country: "Kuwait",
    flag: "\u{1F1F0}\u{1F1FC}",
    portal: "CAB (Central Agency for Public Tenders)",
    documents: [
      "Commercial License",
      "KCCI Membership",
      "Tax Clearance Certificate",
      "Social Insurance Certificate",
      "Company Financials",
    ],
    difficulty: "hard",
    estimatedDays: 10,
  },
  {
    country: "Qatar",
    flag: "\u{1F1F6}\u{1F1E6}",
    portal: "Gov Tenders Portal",
    documents: [
      "Commercial Registration",
      "Qatar Chamber Certificate",
      "Tax Card",
      "Audited Financial Statements",
      "Manpower List",
    ],
    difficulty: "medium",
    estimatedDays: 6,
  },
  {
    country: "Morocco",
    flag: "\u{1F1F2}\u{1F1E6}",
    portal: "March\u{00E9}s Publics",
    documents: [
      "Registre de Commerce",
      "Attestation Fiscale",
      "CNSS Certificate",
      "Caution Provisoire",
      "Cahier des Charges Sign\u{00E9}",
    ],
    difficulty: "medium",
    estimatedDays: 5,
  },
  {
    country: "Egypt",
    flag: "\u{1F1EA}\u{1F1EC}",
    portal: "E-Tender Portal",
    documents: [
      "Commercial Register Extract",
      "Tax Card",
      "Insurance Certificate",
      "Industrial Register (if applicable)",
      "Bank Statement",
    ],
    difficulty: "easy",
    estimatedDays: 4,
  },
];

const COMMON_DOCUMENTS = [
  { key: "cr", label: "Commercial Registration / Trade License" },
  { key: "tax", label: "Tax Clearance Certificate" },
  { key: "financials", label: "Audited Financial Statements (2 years)" },
  { key: "bank", label: "Bank Reference Letter" },
  { key: "insurance", label: "Insurance Certificate / Guarantee" },
  { key: "iso", label: "ISO / Quality Certifications" },
  { key: "profile", label: "Company Profile & Portfolio" },
  { key: "power", label: "Power of Attorney / Authorization Letter" },
];

function getDifficultyConfig(difficulty: Difficulty) {
  switch (difficulty) {
    case "easy":
      return { label: "Easy", color: "text-emerald-400", bg: "bg-emerald-400/10", border: "border-emerald-400/30" };
    case "medium":
      return { label: "Medium", color: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-400/30" };
    case "hard":
      return { label: "Hard", color: "text-red-400", bg: "bg-red-400/10", border: "border-red-400/30" };
  }
}

export default function PreQualificationPage() {
  const { t } = useTranslation();
  const [activeStep, setActiveStep] = useState(0);
  const [checkedDocs, setCheckedDocs] = useState<Set<string>>(new Set());

  const toggleDoc = (key: string) => {
    setCheckedDocs((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const stats = [
    {
      icon: Globe,
      value: "12",
      label: t("preQual.countriesSupported"),
      color: "text-primary-light",
      bg: "bg-primary/10",
      border: "border-primary/20",
    },
    {
      icon: CheckCircle2,
      value: "94%",
      label: t("preQual.successRate"),
      color: "text-emerald-400",
      bg: "bg-emerald-400/10",
      border: "border-emerald-400/20",
    },
    {
      icon: Clock,
      value: "5",
      label: t("preQual.avgProcessingDays"),
      color: "text-amber-400",
      bg: "bg-amber-400/10",
      border: "border-amber-400/20",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-6xl mx-auto"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <div className="flex items-center gap-3 mb-1">
          <ShieldCheck className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("preQual.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("preQual.subtitle")}</p>
      </motion.div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3 md:gap-4 mb-8">
        {stats.map((stat, idx) => (
          <motion.div
            key={idx}
            {...fadeUp}
            transition={{ delay: 0.12 + idx * 0.05 }}
            className={`glass-card rounded-xl p-4 md:p-5 border ${stat.border}`}
          >
            <div
              className={`w-10 h-10 rounded-lg ${stat.bg} flex items-center justify-center mb-3`}
            >
              <stat.icon className={`w-5 h-5 ${stat.color}`} />
            </div>
            <p className={`text-xl md:text-2xl font-bold ${stat.color}`}>
              {stat.value}
            </p>
            <p className="text-xs text-slate-500 mt-1">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Progress Tracker */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.2 }}
        className="glass-card rounded-xl p-5 md:p-6 mb-8"
      >
        <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
          <ClipboardCheck className="w-4 h-4 text-primary-light" />
          {t("preQual.qualificationSteps")}
        </h2>

        {/* Steps */}
        <div className="flex items-center justify-between gap-1 md:gap-2 overflow-x-auto pb-2">
          {STEPS.map((step, idx) => {
            const isActive = idx === activeStep;
            const isCompleted = idx < activeStep;
            const StepIcon = step.icon;

            return (
              <button
                key={step.key}
                onClick={() => setActiveStep(idx)}
                className="flex flex-col items-center gap-2 flex-1 min-w-0 group"
              >
                <div className="flex items-center w-full">
                  {/* Step circle */}
                  <div
                    className={`w-10 h-10 md:w-12 md:h-12 rounded-full flex items-center justify-center shrink-0 transition-all mx-auto ${
                      isCompleted
                        ? "bg-emerald-400/20 border-2 border-emerald-400/50"
                        : isActive
                        ? "bg-primary/20 border-2 border-primary/60 shadow-lg shadow-primary/20"
                        : "bg-dark/60 border-2 border-dark-border"
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <StepIcon
                        className={`w-5 h-5 ${
                          isActive ? step.color : "text-slate-500"
                        }`}
                      />
                    )}
                  </div>
                </div>
                <span
                  className={`text-[10px] md:text-xs text-center leading-tight transition-colors ${
                    isActive
                      ? "text-slate-200 font-medium"
                      : isCompleted
                      ? "text-emerald-400/80"
                      : "text-slate-500"
                  }`}
                >
                  {t(`preQual.step.${step.key}`)}
                </span>
              </button>
            );
          })}
        </div>

        {/* Step connector lines */}
        <div className="flex items-center justify-between px-6 md:px-8 -mt-[52px] md:-mt-[60px] mb-8 pointer-events-none">
          {STEPS.slice(0, -1).map((_, idx) => (
            <div
              key={idx}
              className={`flex-1 h-0.5 mx-1 rounded-full transition-colors ${
                idx < activeStep
                  ? "bg-emerald-400/50"
                  : "bg-dark-border"
              }`}
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-dark-border">
          <button
            onClick={() => setActiveStep(Math.max(0, activeStep - 1))}
            disabled={activeStep === 0}
            className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {t("preQual.previous")}
          </button>
          <span className="text-xs text-slate-500">
            {t("preQual.stepOf", { current: activeStep + 1, total: STEPS.length })}
          </span>
          <button
            onClick={() => setActiveStep(Math.min(STEPS.length - 1, activeStep + 1))}
            disabled={activeStep === STEPS.length - 1}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-primary-light hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {t("preQual.next")}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </motion.div>

      {/* Country-Specific Pre-Qualification Cards */}
      <motion.div {...fadeUp} transition={{ delay: 0.25 }} className="mb-8">
        <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
          <Globe className="w-4 h-4 text-primary-light" />
          {t("preQual.countryPortals")}
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {COUNTRY_PORTALS.map((portal, idx) => {
            const diff = getDifficultyConfig(portal.difficulty);

            return (
              <motion.div
                key={portal.country}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + idx * 0.06 }}
                className="glass-card rounded-xl p-5 border border-dark-border hover:border-primary/30 transition-all group"
              >
                {/* Country Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2.5">
                    <span className="text-2xl">{portal.flag}</span>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-100">
                        {portal.country}
                      </h3>
                      <p className="text-xs text-slate-500">{portal.portal}</p>
                    </div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${diff.bg} ${diff.color} ${diff.border} border`}
                  >
                    {diff.label}
                  </span>
                </div>

                {/* Required Documents */}
                <div className="mb-4">
                  <p className="text-xs font-medium text-slate-400 mb-2">
                    {t("preQual.requiredDocuments")}
                  </p>
                  <ul className="space-y-1.5">
                    {portal.documents.map((doc, docIdx) => (
                      <li
                        key={docIdx}
                        className="flex items-start gap-2 text-xs text-slate-300"
                      >
                        <FileText className="w-3 h-3 text-slate-500 mt-0.5 shrink-0" />
                        <span>{doc}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Estimated Time */}
                <div className="flex items-center gap-1.5 mb-4 text-xs text-slate-400">
                  <Clock className="w-3.5 h-3.5" />
                  <span>
                    {t("preQual.estimatedTime", { days: portal.estimatedDays })}
                  </span>
                </div>

                {/* CTA */}
                <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary/10 hover:bg-primary/20 border border-primary/30 hover:border-primary/50 text-primary-light text-sm font-medium rounded-lg transition-all group-hover:shadow-lg group-hover:shadow-primary/10">
                  {t("preQual.startApplication")}
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                </button>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Document Checklist */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.5 }}
        className="glass-card rounded-xl p-5 md:p-6 mb-8"
      >
        <h2 className="text-base font-semibold text-slate-100 mb-1 flex items-center gap-2">
          <ClipboardCheck className="w-4 h-4 text-primary-light" />
          {t("preQual.documentChecklist")}
        </h2>
        <p className="text-xs text-slate-500 mb-5">
          {t("preQual.documentChecklistDesc")}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {COMMON_DOCUMENTS.map((doc, idx) => {
            const checked = checkedDocs.has(doc.key);

            return (
              <motion.button
                key={doc.key}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.55 + idx * 0.03 }}
                onClick={() => toggleDoc(doc.key)}
                className={`flex items-center gap-3 p-3 rounded-lg border text-start transition-all ${
                  checked
                    ? "bg-emerald-400/5 border-emerald-400/30"
                    : "bg-dark/40 border-dark-border hover:border-slate-600"
                }`}
              >
                <div
                  className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-colors ${
                    checked
                      ? "bg-emerald-400 border-emerald-400"
                      : "border-slate-600"
                  }`}
                >
                  {checked && (
                    <svg
                      className="w-3 h-3 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={3}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </div>
                <span
                  className={`text-sm transition-colors ${
                    checked ? "text-emerald-300" : "text-slate-300"
                  }`}
                >
                  {doc.label}
                </span>
              </motion.button>
            );
          })}
        </div>

        {/* Progress indicator */}
        <div className="mt-5 pt-4 border-t border-dark-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400">
              {t("preQual.documentsReady")}
            </span>
            <span className="text-xs font-semibold text-slate-200">
              {checkedDocs.size}/{COMMON_DOCUMENTS.length}
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-dark/60 border border-dark-border overflow-hidden">
            <motion.div
              animate={{
                width: `${(checkedDocs.size / COMMON_DOCUMENTS.length) * 100}%`,
              }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400"
            />
          </div>
        </div>
      </motion.div>

      {/* Help Notice */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.6 }}
        className="glass-card rounded-xl p-5 border border-primary/20"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-primary-light shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-slate-100 mb-1">
              {t("preQual.needHelp")}
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              {t("preQual.needHelpDesc")}
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
