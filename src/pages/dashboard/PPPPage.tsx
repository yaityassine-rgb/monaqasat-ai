import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  Landmark,
  Globe,
  DollarSign,
  FolderKanban,
  Building2,
  CalendarClock,
  BrainCircuit,
  Filter,
  TrendingUp,
  Layers,
  ChevronDown,
} from "lucide-react";

type Stage = "planning" | "tender" | "shortlisted" | "awarded";
type Sector =
  | "infrastructure"
  | "energy"
  | "transport"
  | "water"
  | "healthcare"
  | "telecom";

interface PPPProject {
  id: string;
  name: string;
  country: string;
  countryFlag: string;
  sector: Sector;
  estimatedValue: string;
  estimatedValueNum: number;
  stage: Stage;
  authority: string;
  expectedTenderDate: string;
  aiRelevanceScore: number;
}

const MOCK_PROJECTS: PPPProject[] = [
  {
    id: "ppp-001",
    name: "NEOM Bay Smart Infrastructure",
    country: "Saudi Arabia",
    countryFlag: "\u{1F1F8}\u{1F1E6}",
    sector: "infrastructure",
    estimatedValue: "$48B",
    estimatedValueNum: 48,
    stage: "tender",
    authority: "NEOM Company",
    expectedTenderDate: "Q2 2026",
    aiRelevanceScore: 94,
  },
  {
    id: "ppp-002",
    name: "Cairo Monorail Extension Line 2",
    country: "Egypt",
    countryFlag: "\u{1F1EA}\u{1F1EC}",
    sector: "transport",
    estimatedValue: "$4.5B",
    estimatedValueNum: 4.5,
    stage: "shortlisted",
    authority: "National Authority for Tunnels",
    expectedTenderDate: "Q3 2026",
    aiRelevanceScore: 87,
  },
  {
    id: "ppp-003",
    name: "Duqm Hydrogen Energy Hub",
    country: "Oman",
    countryFlag: "\u{1F1F4}\u{1F1F2}",
    sector: "energy",
    estimatedValue: "$12B",
    estimatedValueNum: 12,
    stage: "planning",
    authority: "Oman Investment Authority",
    expectedTenderDate: "Q1 2027",
    aiRelevanceScore: 91,
  },
  {
    id: "ppp-004",
    name: "Abu Dhabi Desalination Mega Plant",
    country: "UAE",
    countryFlag: "\u{1F1E6}\u{1F1EA}",
    sector: "water",
    estimatedValue: "$2.8B",
    estimatedValueNum: 2.8,
    stage: "awarded",
    authority: "EWEC (Emirates Water & Electricity)",
    expectedTenderDate: "Awarded",
    aiRelevanceScore: 78,
  },
  {
    id: "ppp-005",
    name: "Riyadh Metro Phase 2 Operations",
    country: "Saudi Arabia",
    countryFlag: "\u{1F1F8}\u{1F1E6}",
    sector: "transport",
    estimatedValue: "$8.2B",
    estimatedValueNum: 8.2,
    stage: "tender",
    authority: "Royal Commission for Riyadh City",
    expectedTenderDate: "Q4 2026",
    aiRelevanceScore: 96,
  },
  {
    id: "ppp-006",
    name: "Morocco 5G National Telecom Network",
    country: "Morocco",
    countryFlag: "\u{1F1F2}\u{1F1E6}",
    sector: "telecom",
    estimatedValue: "$3.1B",
    estimatedValueNum: 3.1,
    stage: "planning",
    authority: "ANRT (Agence Nationale de Reglementation des Telecoms)",
    expectedTenderDate: "Q2 2027",
    aiRelevanceScore: 82,
  },
  {
    id: "ppp-007",
    name: "Kuwait New Hospital Complex PPP",
    country: "Kuwait",
    countryFlag: "\u{1F1F0}\u{1F1FC}",
    sector: "healthcare",
    estimatedValue: "$1.4B",
    estimatedValueNum: 1.4,
    stage: "shortlisted",
    authority: "Kuwait Authority for Partnership Projects",
    expectedTenderDate: "Q3 2026",
    aiRelevanceScore: 75,
  },
  {
    id: "ppp-008",
    name: "Jordan Aqaba Solar-Wind Hybrid Park",
    country: "Jordan",
    countryFlag: "\u{1F1EF}\u{1F1F4}",
    sector: "energy",
    estimatedValue: "$2.1B",
    estimatedValueNum: 2.1,
    stage: "tender",
    authority: "Ministry of Energy & Mineral Resources",
    expectedTenderDate: "Q1 2026",
    aiRelevanceScore: 89,
  },
];

const SECTORS: { key: Sector; label: string }[] = [
  { key: "infrastructure", label: "Infrastructure" },
  { key: "energy", label: "Energy" },
  { key: "transport", label: "Transport" },
  { key: "water", label: "Water" },
  { key: "healthcare", label: "Healthcare" },
  { key: "telecom", label: "Telecom" },
];

const STAGES: { key: Stage; label: string }[] = [
  { key: "planning", label: "Planning" },
  { key: "tender", label: "Tender" },
  { key: "shortlisted", label: "Shortlisted" },
  { key: "awarded", label: "Awarded" },
];

const COUNTRIES = [
  "Saudi Arabia",
  "UAE",
  "Egypt",
  "Oman",
  "Morocco",
  "Kuwait",
  "Jordan",
  "Qatar",
  "Bahrain",
  "Iraq",
  "Tunisia",
  "Algeria",
];

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

function getStageStyle(stage: Stage): {
  bg: string;
  text: string;
  border: string;
} {
  switch (stage) {
    case "planning":
      return {
        bg: "bg-slate-400/10",
        text: "text-slate-300",
        border: "border-slate-400/30",
      };
    case "tender":
      return {
        bg: "bg-sky-400/10",
        text: "text-sky-400",
        border: "border-sky-400/30",
      };
    case "shortlisted":
      return {
        bg: "bg-amber-400/10",
        text: "text-amber-400",
        border: "border-amber-400/30",
      };
    case "awarded":
      return {
        bg: "bg-emerald-400/10",
        text: "text-emerald-400",
        border: "border-emerald-400/30",
      };
  }
}

function getRelevanceColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 80) return "text-sky-400";
  if (score >= 70) return "text-amber-400";
  return "text-slate-400";
}

function getRelevanceBg(score: number): string {
  if (score >= 90) return "bg-emerald-400/10 border-emerald-400/20";
  if (score >= 80) return "bg-sky-400/10 border-sky-400/20";
  if (score >= 70) return "bg-amber-400/10 border-amber-400/20";
  return "bg-slate-400/10 border-slate-400/20";
}

export default function PPPPage() {
  const { t } = useTranslation();
  const [selectedCountry, setSelectedCountry] = useState<string>("all");
  const [selectedSector, setSelectedSector] = useState<string>("all");
  const [selectedStage, setSelectedStage] = useState<string>("all");

  const filteredProjects = useMemo(() => {
    return MOCK_PROJECTS.filter((p) => {
      if (selectedCountry !== "all" && p.country !== selectedCountry)
        return false;
      if (selectedSector !== "all" && p.sector !== selectedSector) return false;
      if (selectedStage !== "all" && p.stage !== selectedStage) return false;
      return true;
    });
  }, [selectedCountry, selectedSector, selectedStage]);

  const pipelineByStage = useMemo(() => {
    const stages: Stage[] = ["planning", "tender", "shortlisted", "awarded"];
    return stages.map((stage) => {
      const projects = MOCK_PROJECTS.filter((p) => p.stage === stage);
      const totalValue = projects.reduce(
        (sum, p) => sum + p.estimatedValueNum,
        0,
      );
      return { stage, count: projects.length, totalValue };
    });
  }, []);

  const maxStageCount = Math.max(...pipelineByStage.map((s) => s.count), 1);

  const statCards = [
    {
      icon: DollarSign,
      label: t("ppp.totalPipeline"),
      value: "$247B",
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      borderColor: "border-emerald-400/20",
    },
    {
      icon: FolderKanban,
      label: t("ppp.activeProjects"),
      value: "156",
      color: "text-sky-400",
      bgColor: "bg-sky-400/10",
      borderColor: "border-sky-400/20",
    },
    {
      icon: Globe,
      label: t("ppp.countries"),
      value: "12",
      color: "text-primary-light",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
    },
    {
      icon: TrendingUp,
      label: t("ppp.avgProjectValue"),
      value: "$1.6B",
      color: "text-amber-400",
      bgColor: "bg-amber-400/10",
      borderColor: "border-amber-400/20",
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
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <Landmark className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("ppp.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("ppp.subtitle")}</p>
      </motion.div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4 mb-8">
        {statCards.map((card, idx) => (
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

      {/* Filter Bar */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.3 }}
        className="glass-card rounded-xl p-4 md:p-5 mb-6"
      >
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-primary-light" />
          <h2 className="text-sm font-semibold text-slate-200">
            {t("ppp.filters")}
          </h2>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Country Filter */}
          <div className="relative flex-1">
            <select
              value={selectedCountry}
              onChange={(e) => setSelectedCountry(e.target.value)}
              className="w-full appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors cursor-pointer"
            >
              <option value="all">{t("ppp.allCountries")}</option>
              {COUNTRIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>

          {/* Sector Filter */}
          <div className="relative flex-1">
            <select
              value={selectedSector}
              onChange={(e) => setSelectedSector(e.target.value)}
              className="w-full appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors cursor-pointer"
            >
              <option value="all">{t("ppp.allSectors")}</option>
              {SECTORS.map((s) => (
                <option key={s.key} value={s.key}>
                  {t(`ppp.sectors.${s.key}`)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>

          {/* Stage Filter */}
          <div className="relative flex-1">
            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="w-full appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors cursor-pointer"
            >
              <option value="all">{t("ppp.allStages")}</option>
              {STAGES.map((s) => (
                <option key={s.key} value={s.key}>
                  {t(`ppp.stages.${s.key}`)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
          </div>
        </div>
      </motion.div>

      {/* Results Count */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.35 }}
        className="text-sm text-slate-500 mb-4"
      >
        {filteredProjects.length} {t("ppp.projectsFound")}
      </motion.p>

      {/* Project Cards */}
      <div className="space-y-4 mb-8">
        {filteredProjects.map((project, idx) => {
          const stageStyle = getStageStyle(project.stage);

          return (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.38 + idx * 0.05 }}
              className="glass-card rounded-xl overflow-hidden hover:border-primary/30 transition-colors"
            >
              <div className="p-4 md:p-5">
                <div className="flex flex-col md:flex-row md:items-start gap-4">
                  {/* Main Content */}
                  <div className="flex-1 min-w-0">
                    {/* Top Row: Name + Stage Badge */}
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="text-sm md:text-base font-semibold text-slate-100 leading-snug">
                        {project.name}
                      </h3>
                      <span
                        className={`shrink-0 inline-flex items-center px-2.5 py-1 rounded-md border text-xs font-medium ${stageStyle.bg} ${stageStyle.text} ${stageStyle.border}`}
                      >
                        {t(`ppp.stages.${project.stage}`)}
                      </span>
                    </div>

                    {/* Country + Sector */}
                    <div className="flex items-center gap-3 flex-wrap text-xs text-slate-400 mb-3">
                      <span className="flex items-center gap-1.5">
                        <span>{project.countryFlag}</span>
                        {project.country}
                      </span>
                      <span className="text-primary-light font-medium">
                        {t(`ppp.sectors.${project.sector}`)}
                      </span>
                      <span className="flex items-center gap-1 text-slate-300 font-semibold">
                        <DollarSign className="w-3 h-3" />
                        {project.estimatedValue}
                      </span>
                    </div>

                    {/* Details Row */}
                    <div className="flex items-center gap-4 flex-wrap text-xs text-slate-500">
                      <span className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate max-w-[220px]">
                          {project.authority}
                        </span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <CalendarClock className="w-3.5 h-3.5 shrink-0" />
                        {project.expectedTenderDate}
                      </span>
                    </div>
                  </div>

                  {/* AI Relevance Score */}
                  <div className="flex md:flex-col items-center gap-2 shrink-0">
                    <div
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border ${getRelevanceBg(project.aiRelevanceScore)}`}
                    >
                      <BrainCircuit
                        className={`w-4 h-4 ${getRelevanceColor(project.aiRelevanceScore)}`}
                      />
                      <span
                        className={`text-lg font-bold ${getRelevanceColor(project.aiRelevanceScore)}`}
                      >
                        {project.aiRelevanceScore}%
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                      {t("ppp.aiScore")}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}

        {/* Empty State */}
        {filteredProjects.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card rounded-xl p-12 text-center"
          >
            <FolderKanban className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 text-sm">{t("ppp.noProjects")}</p>
          </motion.div>
        )}
      </div>

      {/* Pipeline Summary */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.6 }}
        className="glass-card rounded-xl p-5 md:p-6"
      >
        <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
          <Layers className="w-4 h-4 text-primary-light" />
          {t("ppp.pipelineSummary")}
        </h2>
        <div className="space-y-4">
          {pipelineByStage.map((item, idx) => {
            const stageStyle = getStageStyle(item.stage);
            return (
              <motion.div
                key={item.stage}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.65 + idx * 0.06 }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${stageStyle.bg} ${stageStyle.text} ${stageStyle.border}`}
                    >
                      {t(`ppp.stages.${item.stage}`)}
                    </span>
                    <span className="text-xs text-slate-500">
                      {item.count}{" "}
                      {item.count === 1
                        ? t("ppp.project")
                        : t("ppp.projects")}
                    </span>
                  </div>
                  <span className="text-sm font-semibold text-slate-200">
                    ${item.totalValue.toFixed(1)}B
                  </span>
                </div>
                <div className="w-full h-3 rounded-full bg-dark/60 border border-dark-border overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${(item.count / maxStageCount) * 100}%`,
                    }}
                    transition={{
                      delay: 0.7 + idx * 0.08,
                      duration: 0.7,
                      ease: "easeOut" as const,
                    }}
                    className={`h-full rounded-full ${
                      item.stage === "planning"
                        ? "bg-gradient-to-r from-slate-500 to-slate-400"
                        : item.stage === "tender"
                          ? "bg-gradient-to-r from-sky-500 to-sky-400"
                          : item.stage === "shortlisted"
                            ? "bg-gradient-to-r from-amber-500 to-amber-400"
                            : "bg-gradient-to-r from-emerald-500 to-emerald-400"
                    }`}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Pipeline Total */}
        <div className="mt-5 pt-4 border-t border-dark-border flex items-center justify-between">
          <span className="text-sm text-slate-400 font-medium">
            {t("ppp.totalPipelineValue")}
          </span>
          <span className="text-lg font-bold text-emerald-400">
            $
            {pipelineByStage
              .reduce((sum, s) => sum + s.totalValue, 0)
              .toFixed(1)}
            B
          </span>
        </div>
      </motion.div>
    </motion.div>
  );
}
