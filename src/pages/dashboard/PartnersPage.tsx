import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  Handshake,
  Search,
  Building2,
  Globe,
  ShieldCheck,
  Users,
  Briefcase,
  FolderCheck,
  ChevronDown,
  Sparkles,
  UserPlus,
  ArrowRight,
  BadgeCheck,
  Target,
  FileSignature,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

interface PartnerCompany {
  id: string;
  name: string;
  country: string;
  countryFlag: string;
  primarySector: string;
  additionalSectors: string[];
  certifications: string[];
  yearsOfExperience: number;
  completedProjects: number;
  aiCompatibilityScore: number;
}

/* ------------------------------------------------------------------ */
/*  Mock Data                                                         */
/* ------------------------------------------------------------------ */

const MOCK_PARTNERS: PartnerCompany[] = [
  {
    id: "p1",
    name: "Al Rajhi Construction Group",
    country: "Saudi Arabia",
    countryFlag: "\u{1F1F8}\u{1F1E6}",
    primarySector: "construction",
    additionalSectors: ["infrastructure", "energy"],
    certifications: ["ISO 9001", "ISO 14001", "OHSAS 18001"],
    yearsOfExperience: 25,
    completedProjects: 340,
    aiCompatibilityScore: 94,
  },
  {
    id: "p2",
    name: "Gulf Engineering Solutions",
    country: "UAE",
    countryFlag: "\u{1F1E6}\u{1F1EA}",
    primarySector: "it",
    additionalSectors: ["telecom", "defense"],
    certifications: ["ISO 27001", "CMMI Level 5"],
    yearsOfExperience: 15,
    completedProjects: 185,
    aiCompatibilityScore: 87,
  },
  {
    id: "p3",
    name: "Nile Valley Contractors",
    country: "Egypt",
    countryFlag: "\u{1F1EA}\u{1F1EC}",
    primarySector: "infrastructure",
    additionalSectors: ["water", "construction"],
    certifications: ["ISO 9001", "ISO 45001"],
    yearsOfExperience: 30,
    completedProjects: 520,
    aiCompatibilityScore: 78,
  },
  {
    id: "p4",
    name: "Doha Advanced Systems",
    country: "Qatar",
    countryFlag: "\u{1F1F6}\u{1F1E6}",
    primarySector: "defense",
    additionalSectors: ["it", "energy"],
    certifications: ["ISO 27001", "NATO AQAP"],
    yearsOfExperience: 12,
    completedProjects: 95,
    aiCompatibilityScore: 91,
  },
  {
    id: "p5",
    name: "Atlas Medical Supplies",
    country: "Morocco",
    countryFlag: "\u{1F1F2}\u{1F1E6}",
    primarySector: "healthcare",
    additionalSectors: ["pharma"],
    certifications: ["ISO 13485", "CE Mark", "ISO 9001"],
    yearsOfExperience: 18,
    completedProjects: 210,
    aiCompatibilityScore: 72,
  },
  {
    id: "p6",
    name: "Kuwait Energy Partners",
    country: "Kuwait",
    countryFlag: "\u{1F1F0}\u{1F1FC}",
    primarySector: "energy",
    additionalSectors: ["construction", "environment"],
    certifications: ["ISO 14001", "API Q1", "ISO 9001"],
    yearsOfExperience: 22,
    completedProjects: 275,
    aiCompatibilityScore: 85,
  },
];

const SECTOR_OPTIONS = [
  "all",
  "construction",
  "infrastructure",
  "it",
  "energy",
  "defense",
  "healthcare",
  "telecom",
  "water",
  "environment",
  "pharma",
];

const COUNTRY_OPTIONS = [
  "all",
  "Saudi Arabia",
  "UAE",
  "Qatar",
  "Kuwait",
  "Egypt",
  "Morocco",
  "Bahrain",
  "Oman",
  "Jordan",
  "Iraq",
  "Tunisia",
  "Algeria",
];

const CERTIFICATION_OPTIONS = [
  "all",
  "ISO 9001",
  "ISO 14001",
  "ISO 27001",
  "ISO 45001",
  "ISO 13485",
  "OHSAS 18001",
  "CMMI Level 5",
  "CE Mark",
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

function getScoreColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 80) return "text-primary-light";
  if (score >= 70) return "text-amber-400";
  return "text-red-400";
}

function getScoreBg(score: number): string {
  if (score >= 90) return "bg-emerald-400/10 border-emerald-400/30";
  if (score >= 80) return "bg-primary/10 border-primary/30";
  if (score >= 70) return "bg-amber-400/10 border-amber-400/30";
  return "bg-red-400/10 border-red-400/30";
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export default function PartnersPage() {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [countryFilter, setCountryFilter] = useState("all");
  const [certFilter, setCertFilter] = useState("all");

  /* ---- filtered partners ---- */
  const filteredPartners = useMemo(() => {
    return MOCK_PARTNERS.filter((p) => {
      const matchesSearch =
        !searchQuery ||
        p.name.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesSector =
        sectorFilter === "all" ||
        p.primarySector === sectorFilter ||
        p.additionalSectors.includes(sectorFilter);

      const matchesCountry =
        countryFilter === "all" || p.country === countryFilter;

      const matchesCert =
        certFilter === "all" || p.certifications.includes(certFilter);

      return matchesSearch && matchesSector && matchesCountry && matchesCert;
    });
  }, [searchQuery, sectorFilter, countryFilter, certFilter]);

  /* ---- stats ---- */
  const stats = [
    {
      icon: Building2,
      label: t("partners.statCompanies"),
      value: "1,240+",
      color: "text-primary-light",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
    },
    {
      icon: Handshake,
      label: t("partners.statJVs"),
      value: "89",
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      borderColor: "border-emerald-400/20",
    },
    {
      icon: Briefcase,
      label: t("partners.statSectors"),
      value: "10",
      color: "text-accent",
      bgColor: "bg-accent/10",
      borderColor: "border-accent/20",
    },
    {
      icon: Globe,
      label: t("partners.statCountries"),
      value: "12",
      color: "text-sky-400",
      bgColor: "bg-sky-400/10",
      borderColor: "border-sky-400/20",
    },
  ];

  /* ---- how it works steps ---- */
  const steps = [
    {
      icon: UserPlus,
      title: t("partners.step1Title"),
      desc: t("partners.step1Desc"),
    },
    {
      icon: Target,
      title: t("partners.step2Title"),
      desc: t("partners.step2Desc"),
    },
    {
      icon: FileSignature,
      title: t("partners.step3Title"),
      desc: t("partners.step3Desc"),
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-6xl mx-auto"
    >
      {/* ======== Header ======== */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <Handshake className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("partners.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("partners.subtitle")}</p>
      </motion.div>

      {/* ======== Stat Cards ======== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-8">
        {stats.map((card, idx) => (
          <motion.div
            key={idx}
            {...fadeUp}
            transition={{ delay: 0.12 + idx * 0.05 }}
            className={`glass-card rounded-xl p-4 md:p-5 border ${card.borderColor}`}
          >
            <div
              className={`w-10 h-10 rounded-lg ${card.bgColor} flex items-center justify-center mb-3`}
            >
              <card.icon className={`w-5 h-5 ${card.color}`} />
            </div>
            <p className="text-xs text-slate-500 mb-1">{card.label}</p>
            <p className={`text-xl md:text-2xl font-bold ${card.color}`}>
              {card.value}
            </p>
          </motion.div>
        ))}
      </div>

      {/* ======== Search & Filters ======== */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.3 }}
        className="glass-card rounded-xl p-4 md:p-5 mb-8"
      >
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search input */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("partners.searchPlaceholder")}
              className="w-full bg-dark/60 border border-dark-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>

          {/* Sector filter */}
          <div className="relative">
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 pr-9 text-sm text-slate-200 focus:outline-none focus:border-primary/50 transition-colors cursor-pointer"
            >
              {SECTOR_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s === "all" ? t("partners.allSectors") : t(`sectors.${s}`)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>

          {/* Country filter */}
          <div className="relative">
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 pr-9 text-sm text-slate-200 focus:outline-none focus:border-primary/50 transition-colors cursor-pointer"
            >
              {COUNTRY_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c === "all" ? t("partners.allCountries") : c}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>

          {/* Certification filter */}
          <div className="relative">
            <select
              value={certFilter}
              onChange={(e) => setCertFilter(e.target.value)}
              className="appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 pr-9 text-sm text-slate-200 focus:outline-none focus:border-primary/50 transition-colors cursor-pointer"
            >
              {CERTIFICATION_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  {c === "all" ? t("partners.allCertifications") : c}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>
        </div>
      </motion.div>

      {/* ======== Results Count ======== */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.35 }}
        className="text-sm text-slate-500 mb-4"
      >
        {filteredPartners.length} {t("partners.companiesFound")}
      </motion.p>

      {/* ======== Partner Cards Grid ======== */}
      {filteredPartners.length === 0 ? (
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.35 }}
          className="glass-card rounded-xl p-12 text-center"
        >
          <Search className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-300 text-lg mb-2 font-medium">
            {t("partners.noResults")}
          </p>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            {t("partners.noResultsDesc")}
          </p>
        </motion.div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 mb-12">
          {filteredPartners.map((partner, idx) => (
            <motion.div
              key={partner.id}
              {...fadeUp}
              transition={{ delay: 0.35 + idx * 0.06 }}
              className="glass-card rounded-xl overflow-hidden hover:border-primary/30 transition-colors group"
            >
              <div className="p-5">
                {/* Company Name & Country */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-slate-100 leading-snug group-hover:text-primary-light transition-colors">
                      {partner.name}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
                      <span>{partner.countryFlag}</span>
                      {partner.country}
                    </p>
                  </div>

                  {/* AI Compatibility Score */}
                  <div
                    className={`shrink-0 ml-3 flex flex-col items-center px-2.5 py-1.5 rounded-lg border ${getScoreBg(partner.aiCompatibilityScore)}`}
                  >
                    <Sparkles className={`w-3.5 h-3.5 mb-0.5 ${getScoreColor(partner.aiCompatibilityScore)}`} />
                    <span
                      className={`text-lg font-bold leading-none ${getScoreColor(partner.aiCompatibilityScore)}`}
                    >
                      {partner.aiCompatibilityScore}%
                    </span>
                    <span className="text-[10px] text-slate-500 mt-0.5">
                      {t("partners.aiMatch")}
                    </span>
                  </div>
                </div>

                {/* Sectors */}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 border border-primary/20 text-[11px] font-medium text-primary-light">
                    {t(`sectors.${partner.primarySector}`)}
                  </span>
                  {partner.additionalSectors.map((sector) => (
                    <span
                      key={sector}
                      className="inline-flex items-center px-2 py-0.5 rounded-md bg-dark/60 border border-dark-border text-[11px] text-slate-400"
                    >
                      {t(`sectors.${sector}`)}
                    </span>
                  ))}
                </div>

                {/* Certifications */}
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {partner.certifications.map((cert) => (
                    <span
                      key={cert}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-400/5 border border-emerald-400/15 text-[11px] text-emerald-400"
                    >
                      <ShieldCheck className="w-3 h-3" />
                      {cert}
                    </span>
                  ))}
                </div>

                {/* Experience & Projects */}
                <div className="flex items-center gap-4 mb-4 text-xs text-slate-400">
                  <span className="flex items-center gap-1.5">
                    <BadgeCheck className="w-3.5 h-3.5 text-slate-500" />
                    {partner.yearsOfExperience} {t("partners.years")}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <FolderCheck className="w-3.5 h-3.5 text-slate-500" />
                    {partner.completedProjects} {t("partners.projects")}
                  </span>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2">
                  <button className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-dark/60 border border-dark-border text-xs font-medium text-slate-300 rounded-lg hover:border-primary/30 hover:text-white transition-colors">
                    <Users className="w-3.5 h-3.5" />
                    {t("partners.viewProfile")}
                  </button>
                  <button className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-primary hover:bg-primary-dark text-xs font-medium text-white rounded-lg transition-colors">
                    <Handshake className="w-3.5 h-3.5" />
                    {t("partners.requestPartnership")}
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* ======== How It Works ======== */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.6 }}
        className="glass-card rounded-xl p-6 md:p-8 mb-8"
      >
        <h2 className="text-lg font-semibold text-slate-100 text-center mb-2">
          {t("partners.howItWorksTitle")}
        </h2>
        <p className="text-sm text-slate-400 text-center mb-8 max-w-lg mx-auto">
          {t("partners.howItWorksSubtitle")}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {steps.map((step, idx) => (
            <motion.div
              key={idx}
              {...fadeUp}
              transition={{ delay: 0.65 + idx * 0.08 }}
              className="text-center"
            >
              <div className="relative inline-flex items-center justify-center mb-4">
                <div className="w-14 h-14 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <step.icon className="w-6 h-6 text-primary-light" />
                </div>
                <span className="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-primary text-white text-xs font-bold flex items-center justify-center">
                  {idx + 1}
                </span>
              </div>

              <h3 className="text-sm font-semibold text-slate-100 mb-1">
                {step.title}
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {step.desc}
              </p>

              {/* Arrow between steps (hidden on last step and on mobile) */}
              {idx < steps.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-3">
                  <ArrowRight className="w-5 h-5 text-slate-600" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
