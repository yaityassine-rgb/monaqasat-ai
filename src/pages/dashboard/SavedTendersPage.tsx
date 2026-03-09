import { useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookmarkX,
  BookmarkCheck,
  Building2,
  Calendar,
  Search,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";
import { getTenders } from "../../lib/tender-store";
import { COUNTRIES } from "../../lib/constants";
import { formatBudget, getSavedIds, setSavedIds, getMatchTextColor, getStatusStyle } from "../../lib/utils";

type LangKey = "en" | "ar" | "fr";

export default function SavedTendersPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as LangKey;
  const isRtl = lang === "ar";

  const [savedIds, setSavedIdsState] = useState<string[]>(getSavedIds);

  const unsave = useCallback((id: string) => {
    setSavedIdsState((prev) => {
      const next = prev.filter((sid) => sid !== id);
      setSavedIds(next);
      return next;
    });
  }, []);

  const savedTenders = useMemo(() => {
    return getTenders().filter((t) => savedIds.includes(t.id));
  }, [savedIds]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-5xl mx-auto"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <BookmarkCheck className="w-6 h-6 text-accent" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text-gold">
            {t("savedTenders.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("savedTenders.subtitle")}</p>
      </motion.div>

      {/* Empty State */}
      {savedTenders.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="glass-card rounded-xl p-12 text-center"
        >
          <Search className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-300 text-lg mb-2 font-medium">
            {t("savedTenders.title")}
          </p>
          <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
            {t("savedTenders.empty")}
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-medium rounded-lg transition-colors"
          >
            {t("savedTenders.browseTenders")}
            {isRtl ? (
              <ArrowLeft className="w-4 h-4" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
          </Link>
        </motion.div>
      ) : (
        <>
          {/* Count */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.12 }}
            className="text-sm text-slate-500 mb-4"
          >
            {savedTenders.length} {t("dashboard.results")}
          </motion.p>

          {/* Saved Tenders List */}
          <div className="space-y-4">
            <AnimatePresence mode="popLayout">
              {savedTenders.map((tender, idx) => {
                const co = COUNTRIES.find(
                  (c) => c.code === tender.countryCode,
                );

                return (
                  <motion.div
                    key={tender.id}
                    layout
                    initial={{ opacity: 0, x: isRtl ? 20 : -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: isRtl ? -40 : 40, scale: 0.95 }}
                    transition={{ delay: idx * 0.05, duration: 0.3 }}
                    className="glass-card rounded-xl overflow-hidden hover:border-primary/30 transition-colors"
                  >
                    <div className="p-4 md:p-5 flex flex-col md:flex-row md:items-center gap-4">
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-2">
                          <span className="text-xs text-slate-500 font-mono">
                            {tender.id}
                          </span>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md border text-xs font-medium ${getStatusStyle(tender.status)}`}
                          >
                            {t(
                              `dashboard.${tender.status === "closing-soon" ? "closingSoon" : tender.status}`,
                            )}
                          </span>
                        </div>

                        <Link to={`/dashboard/tender/${tender.id}`}>
                          <h3 className="text-sm md:text-base font-semibold text-slate-100 leading-snug line-clamp-2 hover:text-primary-light transition-colors mb-2">
                            {tender.title[lang]}
                          </h3>
                        </Link>

                        <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-3">
                          <Building2 className="w-3.5 h-3.5 shrink-0" />
                          <span className="truncate">
                            {tender.organization[lang]}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 flex-wrap text-xs text-slate-400">
                          {co && (
                            <span className="flex items-center gap-1">
                              <span>{co.flag}</span>
                              {co.name[lang]}
                            </span>
                          )}
                          <span className="text-primary-light">
                            {t(`sectors.${tender.sector}`)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {tender.deadline}
                          </span>
                          <span className="font-semibold text-slate-200">
                            {formatBudget(tender.budget, tender.currency, t("dashboard.notDisclosed"))}
                          </span>
                        </div>
                      </div>

                      {/* Right Side: Match Score + Unsave */}
                      <div className="flex md:flex-col items-center gap-3 md:gap-2 shrink-0">
                        <span
                          className={`text-xl font-bold ${getMatchTextColor(tender.matchScore)}`}
                        >
                          {tender.matchScore}%
                        </span>
                        <span className="text-xs text-slate-500">
                          {t("dashboard.matchScore")}
                        </span>
                        <button
                          onClick={() => unsave(tender.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-400/10 border border-transparent hover:border-red-400/20 rounded-lg transition-colors"
                        >
                          <BookmarkX className="w-3.5 h-3.5" />
                          {t("dashboard.unsave")}
                        </button>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        </>
      )}
    </motion.div>
  );
}
