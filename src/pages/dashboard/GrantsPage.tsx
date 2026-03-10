import { useState, useMemo, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLang, localizedPath } from "../../lib/use-lang";
import { motion } from "framer-motion";
import { supabase } from "../../lib/supabase";
import {
  Globe,
  DollarSign,
  MapPin,
  TrendingUp,
  Calendar,
  ExternalLink,
  Search,
  SlidersHorizontal,
  Sparkles,
  Building2,
  Clock,
  Filter,
  ChevronDown,
  Loader2,
} from "lucide-react";


/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type GrantStatus = "open" | "closing-soon" | "closed";

interface Grant {
  id: string;
  title: string;
  source: string;
  sourceColor: string;
  sourceBg: string;
  sector: string;
  countries: string[];
  fundingAmount: string;
  deadline: string;
  status: GrantStatus;
  matchScore: number;
  description: string;
  sourceUrl?: string;
}

/* ------------------------------------------------------------------ */
/*  Source styling map                                                  */
/* ------------------------------------------------------------------ */

const SOURCE_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  world_bank:  { color: "text-blue-400",    bg: "bg-blue-400/10 border-blue-400/30",    label: "World Bank" },
  isdb:        { color: "text-emerald-400",  bg: "bg-emerald-400/10 border-emerald-400/30", label: "IsDB" },
  afdb:        { color: "text-amber-400",    bg: "bg-amber-400/10 border-amber-400/30",  label: "AfDB" },
  ungm:        { color: "text-sky-400",      bg: "bg-sky-400/10 border-sky-400/30",      label: "UN" },
  eu_ted:      { color: "text-indigo-400",   bg: "bg-indigo-400/10 border-indigo-400/30", label: "EU" },
  ebrd:        { color: "text-violet-400",   bg: "bg-violet-400/10 border-violet-400/30", label: "EBRD" },
  afesd:       { color: "text-teal-400",     bg: "bg-teal-400/10 border-teal-400/30",    label: "AFESD" },
  opec_fund:   { color: "text-orange-400",   bg: "bg-orange-400/10 border-orange-400/30", label: "OPEC Fund" },
};

function getSourceStyle(source: string) {
  return SOURCE_STYLES[source] || { color: "text-slate-400", bg: "bg-slate-400/10 border-slate-400/30", label: source };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatAmount(amount: number): string {
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(0)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount}`;
}

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

function getStatusStyle(status: GrantStatus): string {
  switch (status) {
    case "open":
      return "bg-emerald-400/10 border-emerald-400/30 text-emerald-400";
    case "closing-soon":
      return "bg-amber-400/10 border-amber-400/30 text-amber-400";
    case "closed":
      return "bg-slate-400/10 border-slate-400/30 text-slate-500";
  }
}

function getMatchTextColor(score: number): string {
  if (score >= 85) return "text-emerald-400";
  if (score >= 70) return "text-primary-light";
  if (score >= 50) return "text-amber-400";
  return "text-slate-400";
}

function getMatchBgColor(score: number): string {
  if (score >= 85) return "bg-emerald-400/10 border-emerald-400/20";
  if (score >= 70) return "bg-primary/10 border-primary/20";
  if (score >= 50) return "bg-amber-400/10 border-amber-400/20";
  return "bg-slate-400/10 border-slate-400/20";
}

// DB status uses underscore, UI uses hyphen
function normalizeStatus(dbStatus: string): GrantStatus {
  if (dbStatus === "closing_soon") return "closing-soon";
  if (dbStatus === "open" || dbStatus === "upcoming") return "open";
  return "closed";
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function GrantsPage() {
  const { t, i18n } = useTranslation();
  const urlLang = useLang();
  const lang = i18n.language;

  /* Data state */
  const [grants, setGrants] = useState<Grant[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [totalValue, setTotalValue] = useState(0);
  const [uniqueCountries, setUniqueCountries] = useState<string[]>([]);

  /* Filters */
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);

  /* Fetch grants from Supabase */
  useEffect(() => {
    async function fetchGrants() {
      setLoading(true);
      try {
        // Get total count
        const { count } = await supabase
          .from("grants")
          .select("*", { count: "exact", head: true });

        setTotalCount(count || 0);

        // Get grants data (limit 100 for display)
        const { data, error } = await supabase
          .from("grants")
          .select("id, title, title_ar, title_fr, source, sector, country, country_code, funding_amount, application_deadline, status, description, description_ar, description_fr, source_url, eligibility_countries")
          .order("application_deadline", { ascending: true })
          .limit(100);

        if (error) throw error;

        if (data) {
          // Compute total value
          const { data: sumData } = await supabase
            .from("grants")
            .select("funding_amount");
          const total = (sumData || []).reduce((sum, r) => sum + (Number(r.funding_amount) || 0), 0);
          setTotalValue(total);

          // Extract unique countries
          const countries = [...new Set(data.map(g => g.country).filter(Boolean))].sort();
          setUniqueCountries(countries);

          // Map to Grant interface
          const mapped: Grant[] = data.map((row) => {
            const style = getSourceStyle(row.source);
            const title = lang === "ar" ? (row.title_ar || row.title) : lang === "fr" ? (row.title_fr || row.title) : row.title;
            const desc = lang === "ar" ? (row.description_ar || row.description) : lang === "fr" ? (row.description_fr || row.description) : row.description;
            const deadline = row.application_deadline ? new Date(row.application_deadline).toLocaleDateString() : "";

            // Simple relevance score based on funding amount and status
            const amount = Number(row.funding_amount) || 0;
            let score = 50;
            if (amount > 100_000_000) score += 30;
            else if (amount > 10_000_000) score += 20;
            else if (amount > 1_000_000) score += 10;
            if (row.status === "open") score += 15;
            else if (row.status === "closing_soon") score += 10;
            score = Math.min(score, 99);

            return {
              id: row.id,
              title: title || "Untitled Grant",
              source: style.label,
              sourceColor: style.color,
              sourceBg: style.bg,
              sector: row.sector || "General",
              countries: row.eligibility_countries?.length
                ? row.eligibility_countries
                : row.country ? [row.country] : [],
              fundingAmount: formatAmount(amount),
              deadline,
              status: normalizeStatus(row.status || "open"),
              matchScore: score,
              description: desc || "",
              sourceUrl: row.source_url || undefined,
            };
          });

          setGrants(mapped);
        }
      } catch (err) {
        console.error("Failed to fetch grants:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchGrants();
  }, [lang]);

  /* Derived filter options from data */
  const sourceOptions = useMemo(() => [...new Set(grants.map(g => g.source))].sort(), [grants]);
  const sectorOptions = useMemo(() => [...new Set(grants.map(g => g.sector))].sort(), [grants]);

  /* Filtered grants */
  const filtered = useMemo(() => {
    let list = [...grants];

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (g) =>
          g.title.toLowerCase().includes(q) ||
          g.source.toLowerCase().includes(q) ||
          g.sector.toLowerCase().includes(q) ||
          g.description.toLowerCase().includes(q) ||
          g.id.toLowerCase().includes(q),
      );
    }

    if (sourceFilter) list = list.filter((g) => g.source === sourceFilter);
    if (countryFilter) list = list.filter((g) => g.countries.includes(countryFilter));
    if (sectorFilter) list = list.filter((g) => g.sector === sectorFilter);

    return list;
  }, [grants, search, sourceFilter, countryFilter, sectorFilter]);

  const activeFilterCount = [sourceFilter, countryFilter, sectorFilter].filter(Boolean).length;

  /* Stat cards — computed from real data */
  const avgSize = totalCount > 0 ? totalValue / totalCount : 0;
  const statCards = [
    {
      icon: Globe,
      label: t("grants.statsTotal"),
      value: totalCount.toLocaleString(),
      color: "text-primary-light",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
    },
    {
      icon: DollarSign,
      label: t("grants.statsTotalValue"),
      value: formatAmount(totalValue),
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      borderColor: "border-emerald-400/20",
    },
    {
      icon: MapPin,
      label: t("grants.statsCountries"),
      value: String(uniqueCountries.length),
      color: "text-sky-400",
      bgColor: "bg-sky-400/10",
      borderColor: "border-sky-400/20",
    },
    {
      icon: TrendingUp,
      label: t("grants.statsAvgSize"),
      value: formatAmount(avgSize),
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
      {/* ── Header ─────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <Sparkles className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("grants.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("grants.subtitle")}</p>
      </motion.div>

      {/* ── Stat Cards ─────────────────────────────────────────── */}
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

      {/* ── Search & Filter Bar ────────────────────────────────── */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.3 }}
        className="glass-card rounded-xl p-4 mb-6"
      >
        {/* Search input */}
        <div className="flex items-center gap-3 mb-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("grants.searchPlaceholder")}
              className="w-full bg-dark/60 border border-dark-border rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
            />
          </div>
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors border ${
              filtersOpen || activeFilterCount > 0
                ? "bg-primary/20 border-primary/40 text-primary-light"
                : "bg-dark/40 border-dark-border text-slate-400 hover:text-white"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            {t("grants.filters")}
            {activeFilterCount > 0 && (
              <span className="ml-1 w-5 h-5 rounded-full bg-primary text-white text-xs flex items-center justify-center font-bold">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Expandable filter row */}
        {filtersOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-3 pt-3 border-t border-dark-border"
          >
            {/* Source filter */}
            <div className="relative">
              <label className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 block">
                {t("grants.filterSource")}
              </label>
              <div className="relative">
                <Building2 className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="appearance-none bg-dark/60 border border-dark-border rounded-lg pl-8 pr-8 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary/50 transition-colors cursor-pointer"
                >
                  <option value="">{t("grants.allSources")}</option>
                  {sourceOptions.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              </div>
            </div>

            {/* Country filter */}
            <div className="relative">
              <label className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 block">
                {t("grants.filterCountry")}
              </label>
              <div className="relative">
                <MapPin className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                <select
                  value={countryFilter}
                  onChange={(e) => setCountryFilter(e.target.value)}
                  className="appearance-none bg-dark/60 border border-dark-border rounded-lg pl-8 pr-8 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary/50 transition-colors cursor-pointer"
                >
                  <option value="">{t("grants.allCountries")}</option>
                  {uniqueCountries.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              </div>
            </div>

            {/* Sector filter */}
            <div className="relative">
              <label className="text-[10px] uppercase tracking-wider text-slate-500 mb-1 block">
                {t("grants.filterSector")}
              </label>
              <div className="relative">
                <Filter className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
                <select
                  value={sectorFilter}
                  onChange={(e) => setSectorFilter(e.target.value)}
                  className="appearance-none bg-dark/60 border border-dark-border rounded-lg pl-8 pr-8 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary/50 transition-colors cursor-pointer"
                >
                  <option value="">{t("grants.allSectors")}</option>
                  {sectorOptions.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
              </div>
            </div>

            {/* Clear all filters */}
            {activeFilterCount > 0 && (
              <div className="flex items-end">
                <button
                  onClick={() => {
                    setSourceFilter("");
                    setCountryFilter("");
                    setSectorFilter("");
                  }}
                  className="text-xs text-red-400 hover:text-red-300 px-3 py-2 rounded-lg border border-red-400/20 hover:bg-red-400/10 transition-colors"
                >
                  {t("grants.clearFilters")}
                </button>
              </div>
            )}
          </motion.div>
        )}
      </motion.div>

      {/* ── Results count ──────────────────────────────────────── */}
      <motion.p
        {...fadeUp}
        transition={{ delay: 0.35 }}
        className="text-sm text-slate-500 mb-4"
      >
        {filtered.length} {t("grants.resultsFound")}
      </motion.p>

      {/* ── Loading state ────────────────────────────────────── */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-primary-light animate-spin" />
        </div>
      )}

      {/* ── Grant Cards ────────────────────────────────────────── */}
      {!loading && (
        <div className="space-y-4">
          {filtered.map((grant, idx) => (
            <motion.div
              key={grant.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.38 + idx * 0.05 }}
              className="glass-card rounded-xl overflow-hidden hover:border-primary/30 transition-colors"
            >
              <div className="p-4 md:p-5">
                {/* Top row: ID + Status + Source Badge */}
                <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-slate-500 font-mono">
                      {grant.id.slice(0, 16)}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${getStatusStyle(grant.status)}`}
                    >
                      {t(`grants.status.${grant.status}`)}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${grant.sourceBg} ${grant.sourceColor}`}
                    >
                      {grant.source}
                    </span>
                  </div>

                  {/* AI Match Score */}
                  <div
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${getMatchBgColor(grant.matchScore)}`}
                  >
                    <Sparkles className={`w-3.5 h-3.5 ${getMatchTextColor(grant.matchScore)}`} />
                    <span
                      className={`text-sm font-bold ${getMatchTextColor(grant.matchScore)}`}
                    >
                      {grant.matchScore}%
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {t("grants.aiMatch")}
                    </span>
                  </div>
                </div>

                {/* Title */}
                <h3 className="text-sm md:text-base font-semibold text-slate-100 leading-snug mb-2">
                  {grant.title}
                </h3>

                {/* Description */}
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-2 mb-3">
                  {grant.description}
                </p>

                {/* Meta row */}
                <div className="flex items-center gap-3 flex-wrap text-xs text-slate-400 mb-3">
                  <span className="flex items-center gap-1">
                    <Filter className="w-3 h-3" />
                    {grant.sector}
                  </span>
                  <span className="flex items-center gap-1 font-semibold text-emerald-400">
                    <DollarSign className="w-3 h-3" />
                    {grant.fundingAmount}
                  </span>
                  {grant.deadline && (
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {grant.deadline}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {t("grants.deadline")}
                  </span>
                </div>

                {/* Countries + View Details */}
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <MapPin className="w-3 h-3 text-slate-500 shrink-0" />
                    {grant.countries.slice(0, 5).map((country) => (
                      <span
                        key={country}
                        className="inline-flex px-2 py-0.5 rounded bg-dark/60 border border-dark-border text-[11px] text-slate-400"
                      >
                        {country}
                      </span>
                    ))}
                    {grant.countries.length > 5 && (
                      <span className="text-[11px] text-slate-500">
                        +{grant.countries.length - 5}
                      </span>
                    )}
                  </div>

                  <Link
                    to={localizedPath(urlLang, `/dashboard/grants/${grant.id}`)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-primary-light hover:text-white bg-primary/10 hover:bg-primary/20 border border-primary/30 hover:border-primary/50 rounded-lg transition-colors"
                  >
                    {t("grants.viewDetails")}
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </motion.div>
          ))}

          {/* Empty state */}
          {filtered.length === 0 && (
            <motion.div
              {...fadeUp}
              transition={{ delay: 0.4 }}
              className="glass-card rounded-xl p-12 text-center"
            >
              <Search className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-300 text-lg mb-2 font-medium">
                {t("grants.noResults")}
              </p>
              <p className="text-slate-400 text-sm max-w-md mx-auto">
                {t("grants.noResultsHint")}
              </p>
            </motion.div>
          )}
        </div>
      )}
    </motion.div>
  );
}
