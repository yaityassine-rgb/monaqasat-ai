import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  TrendingUp,
  DollarSign,
  FileCheck,
  AlertTriangle,
  BarChart3,
  Trophy,
  Globe,
  Layers,
} from "lucide-react";
import { MOCK_TENDERS } from "../../lib/mock-data";
import { COUNTRIES } from "../../lib/constants";

type LangKey = "en" | "ar" | "fr";

function formatValue(amount: number): string {
  if (amount >= 1_000_000_000_000) {
    return `${(amount / 1_000_000_000_000).toFixed(1)}T`;
  }
  if (amount >= 1_000_000_000) {
    return `${(amount / 1_000_000_000).toFixed(1)}B`;
  }
  if (amount >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(1)}M`;
  }
  if (amount >= 1_000) {
    return `${(amount / 1_000).toFixed(0)}K`;
  }
  return amount.toLocaleString();
}

function formatBudgetWithCurrency(amount: number, currency: string): string {
  return `${formatValue(amount)} ${currency}`;
}

function getMatchColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  return "text-red-400";
}

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

export default function AnalyticsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as LangKey;

  const stats = useMemo(() => {
    const tenders = MOCK_TENDERS;
    const totalValue = tenders.reduce((sum, t) => sum + t.budget, 0);
    const avgBudget = tenders.length > 0 ? totalValue / tenders.length : 0;
    const openCount = tenders.filter((t) => t.status === "open").length;
    const closingSoonCount = tenders.filter(
      (t) => t.status === "closing-soon",
    ).length;

    return { totalValue, avgBudget, openCount, closingSoonCount };
  }, []);

  const tendersByCountry = useMemo(() => {
    const map = new Map<string, number>();
    MOCK_TENDERS.forEach((t) => {
      map.set(t.countryCode, (map.get(t.countryCode) || 0) + 1);
    });
    const entries = Array.from(map.entries())
      .map(([code, count]) => {
        const co = COUNTRIES.find((c) => c.code === code);
        return {
          code,
          name: co ? co.name[lang] : code,
          flag: co ? co.flag : "",
          count,
        };
      })
      .sort((a, b) => b.count - a.count);
    const max = Math.max(...entries.map((e) => e.count), 1);
    return { entries, max };
  }, [lang]);

  const tendersBySector = useMemo(() => {
    const map = new Map<string, number>();
    MOCK_TENDERS.forEach((t) => {
      map.set(t.sector, (map.get(t.sector) || 0) + 1);
    });
    const entries = Array.from(map.entries())
      .map(([key, count]) => ({
        key,
        name: t(`sectors.${key}`),
        count,
      }))
      .sort((a, b) => b.count - a.count);
    const max = Math.max(...entries.map((e) => e.count), 1);
    return { entries, max };
  }, [t]);

  const topOpportunities = useMemo(() => {
    return [...MOCK_TENDERS]
      .sort((a, b) => b.matchScore - a.matchScore)
      .slice(0, 5);
  }, []);

  const statCards = [
    {
      icon: DollarSign,
      label: t("analytics.totalValue"),
      value: formatValue(stats.totalValue),
      color: "text-emerald-400",
      bgColor: "bg-emerald-400/10",
      borderColor: "border-emerald-400/20",
    },
    {
      icon: TrendingUp,
      label: t("analytics.avgBudget"),
      value: formatValue(stats.avgBudget),
      color: "text-primary-light",
      bgColor: "bg-primary/10",
      borderColor: "border-primary/20",
    },
    {
      icon: FileCheck,
      label: t("analytics.openTenders"),
      value: stats.openCount.toString(),
      color: "text-sky-400",
      bgColor: "bg-sky-400/10",
      borderColor: "border-sky-400/20",
    },
    {
      icon: AlertTriangle,
      label: t("analytics.closingSoon"),
      value: stats.closingSoonCount.toString(),
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
          <BarChart3 className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("analytics.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("analytics.subtitle")}</p>
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Tenders by Country */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.3 }}
          className="glass-card rounded-xl p-5 md:p-6"
        >
          <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
            <Globe className="w-4 h-4 text-primary-light" />
            {t("analytics.byCountry")}
          </h2>
          <div className="space-y-3">
            {tendersByCountry.entries.map((entry, idx) => (
              <motion.div
                key={entry.code}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.35 + idx * 0.04 }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-slate-300 flex items-center gap-1.5">
                    <span>{entry.flag}</span>
                    {entry.name}
                  </span>
                  <span className="text-sm font-semibold text-slate-200">
                    {entry.count}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-dark/60 border border-dark-border overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${(entry.count / tendersByCountry.max) * 100}%`,
                    }}
                    transition={{
                      delay: 0.5 + idx * 0.05,
                      duration: 0.6,
                      ease: "easeOut" as const,
                    }}
                    className="h-full rounded-full bg-gradient-to-r from-primary to-primary-light"
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Tenders by Sector */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.35 }}
          className="glass-card rounded-xl p-5 md:p-6"
        >
          <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent" />
            {t("analytics.bySector")}
          </h2>
          <div className="space-y-3">
            {tendersBySector.entries.map((entry, idx) => (
              <motion.div
                key={entry.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + idx * 0.04 }}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-slate-300">{entry.name}</span>
                  <span className="text-sm font-semibold text-slate-200">
                    {entry.count}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-dark/60 border border-dark-border overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${(entry.count / tendersBySector.max) * 100}%`,
                    }}
                    transition={{
                      delay: 0.55 + idx * 0.05,
                      duration: 0.6,
                      ease: "easeOut" as const,
                    }}
                    className="h-full rounded-full bg-gradient-to-r from-accent to-accent-light"
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Top Matched Opportunities */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.45 }}
        className="glass-card rounded-xl p-5 md:p-6"
      >
        <h2 className="text-base font-semibold text-slate-100 mb-5 flex items-center gap-2">
          <Trophy className="w-4 h-4 text-accent" />
          {t("analytics.topOpportunities")}
        </h2>
        <div className="space-y-3">
          {topOpportunities.map((tender, idx) => {
            const co = COUNTRIES.find((c) => c.code === tender.countryCode);

            return (
              <motion.div
                key={tender.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + idx * 0.06 }}
              >
                <Link
                  to={`/dashboard/tender/${tender.id}`}
                  className="flex items-center gap-4 p-3 md:p-4 rounded-lg bg-dark/40 border border-dark-border hover:border-primary/30 transition-colors group"
                >
                  {/* Rank */}
                  <span className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-xs font-bold text-primary-light shrink-0">
                    #{idx + 1}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-slate-200 line-clamp-1 group-hover:text-primary-light transition-colors">
                      {tender.title[lang]}
                    </h3>
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                      {co && (
                        <span className="flex items-center gap-1">
                          <span>{co.flag}</span>
                          {co.name[lang]}
                        </span>
                      )}
                      <span>{t(`sectors.${tender.sector}`)}</span>
                      <span className="text-slate-300 font-medium">
                        {formatBudgetWithCurrency(
                          tender.budget,
                          tender.currency,
                        )}
                      </span>
                    </div>
                  </div>

                  {/* Match Score */}
                  <span
                    className={`text-lg font-bold shrink-0 ${getMatchColor(tender.matchScore)}`}
                  >
                    {tender.matchScore}%
                  </span>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}
