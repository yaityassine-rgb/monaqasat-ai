import { useState, useMemo, useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLang, localizedPath } from "../../lib/use-lang";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  SlidersHorizontal,
  Bookmark,
  BookmarkCheck,
  Calendar,
  Building2,
  ArrowUpDown,
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Crown,
} from "lucide-react";
import { loadTenders, loadMatchedTenders, getTenders } from "../../lib/tender-store";
import { COUNTRIES, SECTORS } from "../../lib/constants";
import type { Tender } from "../../lib/types";
import { formatBudget, getSavedIds, setSavedIds, getMatchColor, getStatusStyle, getLocalizedText } from "../../lib/utils";
import { useAuth } from "../../lib/auth-context";
import { useSubscription } from "../../lib/use-subscription";

type LangKey = "en" | "ar" | "fr";
type SortOption = "match" | "deadline" | "budget" | "newest";

const PAGE_SIZE = 24;

export default function DashboardPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as LangKey;
  const urlLang = useLang();
  const { user } = useAuth();
  const { tier, canUseFeature } = useSubscription();

  const [allTenders, setAllTenders] = useState<Tender[]>(getTenders);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("");
  const [sector, setSector] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState<SortOption>("match");
  const [savedIds, setSavedIdsState] = useState<string[]>(getSavedIds);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const load = async () => {
      try {
        // Use personalized matching if user is logged in and has AI matching
        const data = user && canUseFeature("aiMatching")
          ? await loadMatchedTenders(user.id)
          : await loadTenders();
        setAllTenders(data);
      } catch {
        setLoadError(true);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [user, tier]);

  const toggleSave = useCallback(
    (id: string) => {
      setSavedIdsState((prev) => {
        const next = prev.includes(id)
          ? prev.filter((sid) => sid !== id)
          : [...prev, id];
        setSavedIds(next);
        return next;
      });
    },
    [],
  );

  const filtered = useMemo(() => {
    let list = [...allTenders];

    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (t) =>
          t.title.en.toLowerCase().includes(q) ||
          t.title.ar.includes(q) ||
          t.title.fr.toLowerCase().includes(q) ||
          t.organization.en.toLowerCase().includes(q) ||
          t.organization.ar.includes(q) ||
          t.organization.fr.toLowerCase().includes(q) ||
          t.id.toLowerCase().includes(q),
      );
    }

    if (country) list = list.filter((t) => t.countryCode === country);
    if (sector) list = list.filter((t) => t.sector === sector);
    if (status) list = list.filter((t) => t.status === status);

    switch (sort) {
      case "match":
        list.sort((a, b) => b.matchScore - a.matchScore);
        break;
      case "deadline":
        list.sort((a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime());
        break;
      case "budget":
        list.sort((a, b) => b.budget - a.budget);
        break;
      case "newest":
        list.sort((a, b) => new Date(b.publishDate).getTime() - new Date(a.publishDate).getTime());
        break;
    }

    return list;
  }, [allTenders, search, country, sector, status, sort]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  useEffect(() => { setPage(1); }, [search, country, sector, status, sort]);

  const hasActiveFilters = country || sector || status;

  const clearFilters = () => {
    setCountry("");
    setSector("");
    setStatus("");
    setSearch("");
  };

  const countryObj = (code: string) => COUNTRIES.find((c) => c.code === code);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-7xl mx-auto"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold gradient-text mb-1">
              {t("dashboard.title")}
            </h1>
            <p className="text-slate-400 text-sm">
              {filtered.length} {t("dashboard.results")}
              {user && canUseFeature("aiMatching") && (
                <span className="ms-2 text-primary-light text-xs">
                  {t("dashboard.personalizedScores")}
                </span>
              )}
            </p>
          </div>
          {tier === "free" && (
            <Link
              to={localizedPath(urlLang, "/pricing")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/30 text-xs font-medium text-primary-light hover:bg-primary/20 transition-colors"
            >
              <Crown className="w-3.5 h-3.5" />
              {t("dashboard.upgradeForAI")}
            </Link>
          )}
        </div>
      </motion.div>

      {/* Search & Filter Bar */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="glass-card rounded-xl p-4 mb-6"
      >
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("dashboard.search")}
              className="w-full bg-dark/60 border border-dark-border rounded-lg ps-10 pe-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
            />
          </div>
          <button
            onClick={() => setFiltersOpen(!filtersOpen)}
            className={`md:hidden flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors ${
              filtersOpen
                ? "bg-primary/20 border-primary/40 text-primary-light"
                : "bg-dark/60 border-dark-border text-slate-300 hover:border-primary/30"
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            {t("dashboard.filters")}
          </button>
        </div>

        {/* Desktop Filters */}
        <div className="hidden md:flex items-center gap-3 mt-3 flex-wrap">
          <FilterSelect value={country} onChange={setCountry} placeholder={t("dashboard.allCountries")} icon={<ChevronDown className="w-3.5 h-3.5" />}>
            <option value="">{t("dashboard.allCountries")}</option>
            {COUNTRIES.map((c) => (<option key={c.code} value={c.code}>{c.flag} {c.name[lang]}</option>))}
          </FilterSelect>

          <FilterSelect value={sector} onChange={setSector} placeholder={t("dashboard.allSectors")} icon={<ChevronDown className="w-3.5 h-3.5" />}>
            <option value="">{t("dashboard.allSectors")}</option>
            {SECTORS.map((s) => (<option key={s.key} value={s.key}>{t(`sectors.${s.key}`)}</option>))}
          </FilterSelect>

          <FilterSelect value={status} onChange={setStatus} placeholder={t("dashboard.allStatuses")} icon={<ChevronDown className="w-3.5 h-3.5" />}>
            <option value="">{t("dashboard.allStatuses")}</option>
            <option value="open">{t("dashboard.open")}</option>
            <option value="closing-soon">{t("dashboard.closingSoon")}</option>
            <option value="closed">{t("dashboard.closed")}</option>
          </FilterSelect>

          <FilterSelect value={sort} onChange={(v) => setSort(v as SortOption)} placeholder={t("dashboard.sortBy")} icon={<ArrowUpDown className="w-3.5 h-3.5" />}>
            <option value="match">{t("dashboard.sortMatch")}</option>
            <option value="deadline">{t("dashboard.sortDeadline")}</option>
            <option value="budget">{t("dashboard.sortBudget")}</option>
            <option value="newest">{t("dashboard.sortNewest")}</option>
          </FilterSelect>

          {hasActiveFilters && (
            <button onClick={clearFilters} className="flex items-center gap-1.5 px-3 py-2 text-xs text-red-400 hover:text-red-300 transition-colors">
              <X className="w-3.5 h-3.5" />
              {t("dashboard.clearFilters")}
            </button>
          )}
        </div>

        {/* Mobile Filters */}
        <AnimatePresence>
          {filtersOpen && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="md:hidden overflow-hidden">
              <div className="flex flex-col gap-3 mt-3 pt-3 border-t border-dark-border">
                <FilterSelect value={country} onChange={setCountry} placeholder={t("dashboard.allCountries")} icon={<ChevronDown className="w-3.5 h-3.5" />} fullWidth>
                  <option value="">{t("dashboard.allCountries")}</option>
                  {COUNTRIES.map((c) => (<option key={c.code} value={c.code}>{c.flag} {c.name[lang]}</option>))}
                </FilterSelect>
                <FilterSelect value={sector} onChange={setSector} placeholder={t("dashboard.allSectors")} icon={<ChevronDown className="w-3.5 h-3.5" />} fullWidth>
                  <option value="">{t("dashboard.allSectors")}</option>
                  {SECTORS.map((s) => (<option key={s.key} value={s.key}>{t(`sectors.${s.key}`)}</option>))}
                </FilterSelect>
                <FilterSelect value={status} onChange={setStatus} placeholder={t("dashboard.allStatuses")} icon={<ChevronDown className="w-3.5 h-3.5" />} fullWidth>
                  <option value="">{t("dashboard.allStatuses")}</option>
                  <option value="open">{t("dashboard.open")}</option>
                  <option value="closing-soon">{t("dashboard.closingSoon")}</option>
                  <option value="closed">{t("dashboard.closed")}</option>
                </FilterSelect>
                <FilterSelect value={sort} onChange={(v) => setSort(v as SortOption)} placeholder={t("dashboard.sortBy")} icon={<ArrowUpDown className="w-3.5 h-3.5" />} fullWidth>
                  <option value="match">{t("dashboard.sortMatch")}</option>
                  <option value="deadline">{t("dashboard.sortDeadline")}</option>
                  <option value="budget">{t("dashboard.sortBudget")}</option>
                  <option value="newest">{t("dashboard.sortNewest")}</option>
                </FilterSelect>
                {hasActiveFilters && (
                  <button onClick={clearFilters} className="flex items-center justify-center gap-1.5 px-3 py-2 text-xs text-red-400 hover:text-red-300 transition-colors">
                    <X className="w-3.5 h-3.5" />
                    {t("dashboard.clearFilters")}
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Loading State */}
      {loading && (
        <div className="glass-card rounded-xl p-12 text-center">
          <Loader2 className="w-8 h-8 text-primary animate-spin mx-auto mb-3" />
          <p className="text-slate-400 text-sm">{t("dashboard.loading")}</p>
        </div>
      )}

      {/* Error State */}
      {!loading && loadError && allTenders.length === 0 && (
        <div className="glass-card rounded-xl p-12 text-center">
          <Search className="w-12 h-12 text-red-400/60 mx-auto mb-4" />
          <p className="text-red-400 text-sm">{t("common.loadError")}</p>
        </div>
      )}

      {/* Tender Cards Grid */}
      {!loading && filtered.length === 0 ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card rounded-xl p-12 text-center">
          <Search className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 text-lg mb-4">{t("dashboard.noResults")}</p>
          <button onClick={clearFilters} className="text-primary-light hover:text-primary text-sm font-medium transition-colors">
            {t("dashboard.clearFilters")}
          </button>
        </motion.div>
      ) : !loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {paginated.map((tender, idx) => {
              const co = countryObj(tender.countryCode);
              const isSaved = savedIds.includes(tender.id);

              return (
                <motion.div
                  key={tender.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: idx * 0.03, duration: 0.3 }}
                  className="glass-card rounded-xl overflow-hidden hover:border-primary/30 transition-colors group"
                >
                  <div className="p-4 pb-3">
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="flex-1 min-w-0">
                        <Link to={localizedPath(urlLang, `/dashboard/tender/${tender.id}`)} className="block">
                          {(() => {
                            const titleInfo = getLocalizedText(tender.title, lang);
                            return (
                              <>
                                <h3 className="text-sm font-semibold text-slate-100 leading-snug line-clamp-2 group-hover:text-primary-light transition-colors">
                                  {titleInfo.text}
                                </h3>
                                {titleInfo.mismatch && (
                                  <span className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5 rounded bg-amber-400/10 border border-amber-400/30 text-[10px] font-medium text-amber-400">
                                    {t("tenderDetail.contentInEnglish")}
                                  </span>
                                )}
                              </>
                            );
                          })()}
                        </Link>
                      </div>
                      <button
                        onClick={() => toggleSave(tender.id)}
                        className={`shrink-0 p-1.5 rounded-lg transition-colors ${
                          isSaved
                            ? "text-accent bg-accent/10"
                            : "text-slate-500 hover:text-accent hover:bg-accent/10"
                        }`}
                        aria-label={isSaved ? t("dashboard.unsave") : t("dashboard.save")}
                      >
                        {isSaved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                      </button>
                    </div>

                    <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-3">
                      <Building2 className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{tender.organization[lang]}</span>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap mb-3">
                      {co && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-dark/60 border border-dark-border text-xs text-slate-300">
                          <span>{co.flag}</span>
                          {co.name[lang]}
                        </span>
                      )}
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 border border-primary/20 text-xs text-primary-light">
                        {t(`sectors.${tender.sector}`)}
                      </span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${getStatusStyle(tender.status)}`}>
                        {t(`dashboard.${tender.status === "closing-soon" ? "closingSoon" : tender.status}`)}
                      </span>
                    </div>
                  </div>

                  <div className="px-4 py-3 border-t border-dark-border bg-dark/40 flex items-center justify-between gap-2">
                    <div className="flex flex-col gap-1">
                      <span className="text-xs text-slate-500">{t("dashboard.budget")}</span>
                      <span className="text-sm font-semibold text-slate-200">
                        {formatBudget(tender.budget, tender.currency, t("dashboard.notDisclosed"))}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1 items-center">
                      <span className="text-xs text-slate-500">{t("dashboard.deadline")}</span>
                      <span className="text-xs text-slate-300 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {tender.deadline || t("dashboard.seePortal")}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1 items-end">
                      <span className="text-xs text-slate-500">{t("dashboard.matchScore")}</span>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-bold ${getMatchColor(tender.matchScore)}`}>
                        {tender.matchScore}%
                      </span>
                    </div>
                  </div>

                  <Link
                    to={localizedPath(urlLang, `/dashboard/tender/${tender.id}`)}
                    className="block px-4 py-2.5 text-center text-xs font-medium text-primary-light hover:bg-primary/10 transition-colors border-t border-dark-border"
                  >
                    {t("dashboard.viewDetails")}
                  </Link>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      ) : null}

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-8 mb-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="flex items-center gap-1 px-3 py-2 rounded-lg bg-dark/60 border border-dark-border text-xs text-slate-300 hover:border-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            {t("dashboard.prev")}
          </button>
          <span className="text-xs text-slate-400">
            {page} / {totalPages} ({filtered.length} {t("dashboard.results")})
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="flex items-center gap-1 px-3 py-2 rounded-lg bg-dark/60 border border-dark-border text-xs text-slate-300 hover:border-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {t("dashboard.next")}
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </motion.div>
  );
}

/* ---- Filter Select sub-component ---- */

function FilterSelect({
  value,
  onChange,
  children,
  placeholder: _placeholder,
  icon,
  fullWidth,
}: {
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
  placeholder: string;
  icon: React.ReactNode;
  fullWidth?: boolean;
}) {
  return (
    <div className={`relative ${fullWidth ? "w-full" : ""}`}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={`appearance-none bg-dark/60 border border-dark-border rounded-lg ps-3 pe-8 py-2 text-xs text-slate-300 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors cursor-pointer ${fullWidth ? "w-full" : ""}`}
      >
        {children}
      </select>
      <span className="absolute end-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
        {icon}
      </span>
    </div>
  );
}
