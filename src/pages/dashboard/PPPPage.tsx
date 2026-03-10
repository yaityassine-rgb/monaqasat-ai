import { useState, useMemo, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { supabase } from "../../lib/supabase";
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
  Loader2,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Stage = "identification" | "planning" | "feasibility" | "tender" | "shortlisted" | "awarded" | "construction" | "operational" | "cancelled";

interface PPPProject {
  id: string;
  name: string;
  country: string;
  countryFlag: string;
  sector: string;
  estimatedValue: string;
  estimatedValueNum: number;
  stage: Stage;
  authority: string;
  expectedTenderDate: string;
  aiRelevanceScore: number;
}

/* ------------------------------------------------------------------ */
/*  Country code → flag emoji                                          */
/* ------------------------------------------------------------------ */

function countryCodeToFlag(code: string): string {
  if (!code || code.length !== 2) return "";
  const offset = 127397;
  return String.fromCodePoint(
    code.toUpperCase().charCodeAt(0) + offset,
    code.toUpperCase().charCodeAt(1) + offset,
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatValue(amount: number): string {
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(0)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount}`;
}

function formatTenderDate(deadline: string | null, stage: string): string {
  if (stage === "awarded" || stage === "operational") return stage.charAt(0).toUpperCase() + stage.slice(1);
  if (!deadline) return "TBD";
  const d = new Date(deadline);
  const q = Math.ceil((d.getMonth() + 1) / 3);
  return `Q${q} ${d.getFullYear()}`;
}

const STAGE_ORDER: Stage[] = ["identification", "planning", "feasibility", "tender", "shortlisted", "awarded", "construction", "operational"];

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

function getStageStyle(stage: string): { bg: string; text: string; border: string } {
  switch (stage) {
    case "identification":
    case "planning":
      return { bg: "bg-slate-400/10", text: "text-slate-300", border: "border-slate-400/30" };
    case "feasibility":
      return { bg: "bg-purple-400/10", text: "text-purple-400", border: "border-purple-400/30" };
    case "tender":
      return { bg: "bg-sky-400/10", text: "text-sky-400", border: "border-sky-400/30" };
    case "shortlisted":
      return { bg: "bg-amber-400/10", text: "text-amber-400", border: "border-amber-400/30" };
    case "awarded":
    case "construction":
    case "operational":
      return { bg: "bg-emerald-400/10", text: "text-emerald-400", border: "border-emerald-400/30" };
    case "cancelled":
      return { bg: "bg-red-400/10", text: "text-red-400", border: "border-red-400/30" };
    default:
      return { bg: "bg-slate-400/10", text: "text-slate-300", border: "border-slate-400/30" };
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

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function PPPPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language;

  /* Data state */
  const [projects, setProjects] = useState<PPPProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPipelineValue, setTotalPipelineValue] = useState(0);
  const [uniqueCountriesCount, setUniqueCountriesCount] = useState(0);

  /* Filters */
  const [selectedCountry, setSelectedCountry] = useState<string>("all");
  const [selectedSector, setSelectedSector] = useState<string>("all");
  const [selectedStage, setSelectedStage] = useState<string>("all");

  /* Fetch from Supabase */
  useEffect(() => {
    async function fetchProjects() {
      setLoading(true);
      try {
        const { count } = await supabase
          .from("ppp_projects")
          .select("*", { count: "exact", head: true });
        setTotalCount(count || 0);

        const { data, error } = await supabase
          .from("ppp_projects")
          .select("id, name, name_ar, name_fr, country, country_code, sector, stage, investment_value, government_entity, government_entity_ar, government_entity_fr, tender_deadline")
          .order("investment_value", { ascending: false })
          .limit(100);

        if (error) throw error;

        if (data) {
          // Total pipeline value
          const { data: valData } = await supabase
            .from("ppp_projects")
            .select("investment_value");
          const total = (valData || []).reduce((s, r) => s + (Number(r.investment_value) || 0), 0);
          setTotalPipelineValue(total);

          // Unique countries
          const countries = new Set((valData || []).map(() => ""));
          const { data: countryData } = await supabase
            .from("ppp_projects")
            .select("country")
            .neq("country", "");
          const uc = new Set((countryData || []).map(r => r.country));
          setUniqueCountriesCount(uc.size);
          // Keep countries set reference clean
          void countries;

          const mapped: PPPProject[] = data.map((row) => {
            const name = lang === "ar" ? (row.name_ar || row.name) : lang === "fr" ? (row.name_fr || row.name) : row.name;
            const authority = lang === "ar" ? (row.government_entity_ar || row.government_entity) : lang === "fr" ? (row.government_entity_fr || row.government_entity) : row.government_entity;
            const val = Number(row.investment_value) || 0;

            // Simple relevance score
            let score = 50;
            if (val > 10_000_000_000) score += 35;
            else if (val > 1_000_000_000) score += 25;
            else if (val > 100_000_000) score += 15;
            if (row.stage === "tender") score += 15;
            else if (row.stage === "shortlisted") score += 10;
            score = Math.min(score, 99);

            return {
              id: row.id,
              name: name || "Untitled Project",
              country: row.country || "",
              countryFlag: countryCodeToFlag(row.country_code || ""),
              sector: row.sector || "general",
              estimatedValue: formatValue(val),
              estimatedValueNum: val / 1_000_000_000, // in billions for pipeline chart
              stage: (row.stage || "planning") as Stage,
              authority: authority || "",
              expectedTenderDate: formatTenderDate(row.tender_deadline, row.stage || ""),
              aiRelevanceScore: score,
            };
          });

          setProjects(mapped);
        }
      } catch (err) {
        console.error("Failed to fetch PPP projects:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchProjects();
  }, [lang]);

  /* Derived filter options */
  const countryOptions = useMemo(() => [...new Set(projects.map(p => p.country).filter(Boolean))].sort(), [projects]);
  const sectorOptions = useMemo(() => [...new Set(projects.map(p => p.sector).filter(Boolean))].sort(), [projects]);
  const stageOptions = useMemo(() => [...new Set(projects.map(p => p.stage))].sort(), [projects]);

  const filteredProjects = useMemo(() => {
    return projects.filter((p) => {
      if (selectedCountry !== "all" && p.country !== selectedCountry) return false;
      if (selectedSector !== "all" && p.sector !== selectedSector) return false;
      if (selectedStage !== "all" && p.stage !== selectedStage) return false;
      return true;
    });
  }, [projects, selectedCountry, selectedSector, selectedStage]);

  const pipelineByStage = useMemo(() => {
    return STAGE_ORDER.map((stage) => {
      const stageProjects = projects.filter((p) => p.stage === stage);
      const totalValue = stageProjects.reduce((sum, p) => sum + p.estimatedValueNum, 0);
      return { stage, count: stageProjects.length, totalValue };
    }).filter((s) => s.count > 0);
  }, [projects]);

  const maxStageCount = Math.max(...pipelineByStage.map((s) => s.count), 1);
  const avgProjectValue = totalCount > 0 ? totalPipelineValue / totalCount : 0;

  const statCards = [
    {
      icon: DollarSign,
      label: t("ppp.totalPipeline"),
      value: formatValue(totalPipelineValue),
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      borderColor: "border-emerald-400/20",
    },
    {
      icon: FolderKanban,
      label: t("ppp.activeProjects"),
      value: String(totalCount),
      color: "text-sky-400",
      bgColor: "bg-sky-400/10",
      borderColor: "border-sky-400/20",
    },
    {
      icon: Globe,
      label: t("ppp.countries"),
      value: String(uniqueCountriesCount),
      color: "text-primary-light",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
    },
    {
      icon: TrendingUp,
      label: t("ppp.avgProjectValue"),
      value: formatValue(avgProjectValue),
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
              {countryOptions.map((c) => (
                <option key={c} value={c}>{c}</option>
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
              {sectorOptions.map((s) => (
                <option key={s} value={s}>{s}</option>
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
              {stageOptions.map((s) => (
                <option key={s} value={s}>{s}</option>
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

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-primary-light animate-spin" />
        </div>
      )}

      {/* Project Cards */}
      {!loading && (
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
                          {project.stage}
                        </span>
                      </div>

                      {/* Country + Sector */}
                      <div className="flex items-center gap-3 flex-wrap text-xs text-slate-400 mb-3">
                        <span className="flex items-center gap-1.5">
                          <span>{project.countryFlag}</span>
                          {project.country}
                        </span>
                        <span className="text-primary-light font-medium">
                          {project.sector}
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
                            {project.authority || "—"}
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
      )}

      {/* Pipeline Summary */}
      {!loading && pipelineByStage.length > 0 && (
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
                        {item.stage}
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
                        item.stage === "identification" || item.stage === "planning"
                          ? "bg-gradient-to-r from-slate-500 to-slate-400"
                          : item.stage === "feasibility"
                            ? "bg-gradient-to-r from-purple-500 to-purple-400"
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
              {formatValue(totalPipelineValue)}
            </span>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
