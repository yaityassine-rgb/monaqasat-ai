import { useState, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLang, localizedPath } from "../../lib/use-lang";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Calendar,
  DollarSign,
  Globe,
  Layers,
  CheckCircle2,
  ExternalLink,
  Bookmark,
  FileText,
  Clock,
  Target,
} from "lucide-react";
import { getTenders } from "../../lib/tender-store";
import { COUNTRIES } from "../../lib/constants";
import { formatBudget, getSavedIds, setSavedIds, getStatusStyle, getLocalizedText } from "../../lib/utils";
import TenderAnalysis from "../../components/TenderAnalysis";
import WinProbability from "../../components/WinProbability";
import CompetitorInsights from "../../components/CompetitorInsights";

type LangKey = "en" | "ar" | "fr";

function getMatchScoreColor(score: number) {
  if (score >= 80)
    return {
      ring: "border-emerald-400",
      bg: "bg-emerald-400/10",
      text: "text-emerald-400",
      glow: "shadow-emerald-400/20",
    };
  if (score >= 60)
    return {
      ring: "border-amber-400",
      bg: "bg-amber-400/10",
      text: "text-amber-400",
      glow: "shadow-amber-400/20",
    };
  return {
    ring: "border-red-400",
    bg: "bg-red-400/10",
    text: "text-red-400",
    glow: "shadow-red-400/20",
  };
}

function getStatusLabel(status: string, t: (k: string) => string) {
  switch (status) {
    case "open":
      return t("dashboard.open");
    case "closing-soon":
      return t("dashboard.closingSoon");
    case "closed":
      return t("dashboard.closed");
    default:
      return status;
  }
}

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

export default function TenderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const lang = i18n.language as LangKey;
  const urlLang = useLang();
  const isRtl = lang === "ar";

  const tender = getTenders().find((t) => t.id === id);

  const [savedIdsState, setSavedIdsState] = useState<string[]>(getSavedIds);
  const isSaved = tender ? savedIdsState.includes(tender.id) : false;

  const toggleSave = () => {
    if (!tender) return;
    setSavedIdsState((prev) => {
      const next = prev.includes(tender.id)
        ? prev.filter((sid) => sid !== tender.id)
        : [...prev, tender.id];
      setSavedIds(next);
      return next;
    });
  };

  const similarTenders = useMemo(() => {
    if (!tender) return [];
    return getTenders().filter(
      (t) => t.sector === tender.sector && t.id !== tender.id,
    )
      .sort((a, b) => b.matchScore - a.matchScore)
      .slice(0, 3);
  }, [tender]);

  const countryObj = tender
    ? COUNTRIES.find((c) => c.code === tender.countryCode)
    : null;

  if (!tender) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="glass-card rounded-xl p-12 text-center max-w-md">
          <Target className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-200 mb-2">
            {t("tenderDetail.notFound")}
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            {t("tenderDetail.notFoundDesc")}
          </p>
          <Link
            to={localizedPath(urlLang, "/dashboard")}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-dark text-white text-sm font-medium rounded-lg transition-colors"
          >
            {isRtl ? (
              <ArrowRight className="w-4 h-4" />
            ) : (
              <ArrowLeft className="w-4 h-4" />
            )}
            {t("tenderDetail.back")}
          </Link>
        </div>
      </div>
    );
  }

  const matchColors = getMatchScoreColor(tender.matchScore);

  const infoItems = [
    {
      icon: DollarSign,
      label: t("tenderDetail.budget"),
      value: formatBudget(tender.budget, tender.currency, t("dashboard.notDisclosed")),
    },
    {
      icon: Calendar,
      label: t("tenderDetail.deadline"),
      value: tender.deadline,
    },
    {
      icon: Clock,
      label: t("tenderDetail.published"),
      value: tender.publishDate,
    },
    {
      icon: Layers,
      label: t("tenderDetail.sector"),
      value: t(`sectors.${tender.sector}`),
    },
    {
      icon: Globe,
      label: t("tenderDetail.country"),
      value: countryObj
        ? `${countryObj.flag} ${countryObj.name[lang]}`
        : tender.country,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-5xl mx-auto"
    >
      {/* Back Button */}
      <motion.div {...fadeUp} transition={{ delay: 0.05 }}>
        <Link
          to={localizedPath(urlLang, "/dashboard")}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-primary-light transition-colors mb-6"
        >
          {isRtl ? (
            <ArrowRight className="w-4 h-4" />
          ) : (
            <ArrowLeft className="w-4 h-4" />
          )}
          {t("tenderDetail.back")}
        </Link>
      </motion.div>

      {/* Header */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.1 }}
        className="glass-card rounded-xl p-6 mb-6"
      >
        <div className="flex flex-col lg:flex-row lg:items-start gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-3">
              <span className="text-xs text-slate-500 font-mono">{tender.id}</span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md border text-xs font-medium ${getStatusStyle(tender.status)}`}>
                {getStatusLabel(tender.status, t)}
              </span>
            </div>
            {(() => {
              const titleInfo = getLocalizedText(tender.title, lang);
              return (
                <>
                  <h1 className="text-xl md:text-2xl font-bold text-slate-100 leading-snug mb-2">
                    {titleInfo.text}
                  </h1>
                  {titleInfo.mismatch && (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-400/10 border border-amber-400/30 text-xs font-medium text-amber-400 mb-2">
                      <Globe className="w-3 h-3" />
                      {t("tenderDetail.contentInEnglish")}
                    </span>
                  )}
                </>
              );
            })()}
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Building2 className="w-4 h-4 shrink-0" />
              <span>{tender.organization[lang]}</span>
            </div>
          </div>

          {/* Match Score Badge */}
          <div className="shrink-0 flex flex-col items-center">
            <span className="text-xs text-slate-500 mb-2">{t("tenderDetail.matchScore")}</span>
            <div className={`w-20 h-20 rounded-full border-3 flex items-center justify-center ${matchColors.ring} ${matchColors.bg} shadow-lg ${matchColors.glow}`}>
              <span className={`text-2xl font-bold ${matchColors.text}`}>
                {tender.matchScore}%
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Info Grid */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6"
      >
        {infoItems.map((item, idx) => (
          <div key={idx} className="glass-card rounded-xl p-4 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-slate-500">
              <item.icon className="w-4 h-4" />
              <span className="text-xs">{item.label}</span>
            </div>
            <span className="text-sm font-semibold text-slate-200">{item.value}</span>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <motion.div {...fadeUp} transition={{ delay: 0.2 }} className="glass-card rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">{t("tenderDetail.description")}</h2>
            <p className="text-sm text-slate-300 leading-relaxed">{tender.description[lang]}</p>
          </motion.div>

          {/* Requirements */}
          {tender.requirements && tender.requirements.length > 0 ? (
            <motion.div {...fadeUp} transition={{ delay: 0.25 }} className="glass-card rounded-xl p-6">
              <h2 className="text-lg font-semibold text-slate-100 mb-4">{t("tenderDetail.requirements")}</h2>
              <ul className="space-y-3">
                {tender.requirements.map((req, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span className="text-sm text-slate-300">{req}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ) : (
            <motion.div {...fadeUp} transition={{ delay: 0.25 }} className="glass-card rounded-xl p-6">
              <h2 className="text-lg font-semibold text-slate-100 mb-4">{t("tenderDetail.requirements")}</h2>
              <p className="text-sm text-slate-400 italic">{t("tenderDetail.noRequirements")}</p>
            </motion.div>
          )}

          {/* AI Analysis — Real Gemini-powered analysis */}
          <motion.div {...fadeUp} transition={{ delay: 0.3 }}>
            <TenderAnalysis tender={tender} />
          </motion.div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Action Buttons */}
          <motion.div {...fadeUp} transition={{ delay: 0.2 }} className="glass-card rounded-xl p-5 space-y-3">
            <a
              href={tender.sourceUrl || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className={`w-full flex items-center justify-center gap-2 px-4 py-3 text-white text-sm font-medium rounded-lg transition-colors ${
                tender.sourceUrl
                  ? "bg-primary hover:bg-primary-dark cursor-pointer"
                  : "bg-gray-600 cursor-not-allowed opacity-50"
              }`}
              onClick={(e) => { if (!tender.sourceUrl) e.preventDefault(); }}
            >
              <ExternalLink className="w-4 h-4" />
              {t("tenderDetail.applyNow")}
            </a>
            {tender.sourceUrl && (
              <p className="text-[10px] text-slate-500 text-center -mt-1">
                {t("tenderDetail.externalLink")}
              </p>
            )}
            <button
              onClick={toggleSave}
              className={`w-full flex items-center justify-center gap-2 px-4 py-3 border text-sm font-medium rounded-lg transition-colors ${
                isSaved
                  ? "border-accent/40 bg-accent/10 text-accent hover:bg-accent/20"
                  : "border-dark-border bg-dark/40 text-slate-300 hover:border-primary/30 hover:text-primary-light"
              }`}
            >
              <Bookmark className="w-4 h-4" />
              {isSaved ? t("dashboard.saved") : t("tenderDetail.saveForLater")}
            </button>
            <Link
              to={localizedPath(urlLang, `/dashboard/proposals?tender=${tender.id}`)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 border border-dark-border bg-dark/40 text-slate-300 hover:border-primary/30 hover:text-primary-light text-sm font-medium rounded-lg transition-colors"
            >
              <FileText className="w-4 h-4" />
              {t("tenderDetail.generateProposal")}
            </Link>
          </motion.div>

          {/* Win Probability */}
          <WinProbability tenderId={tender.id} />

          {/* Competitor Insights */}
          <CompetitorInsights
            sector={tender.sector}
            countryCode={tender.countryCode}
            tenderId={tender.id}
          />

          {/* Similar Tenders */}
          {similarTenders.length > 0 && (
            <motion.div {...fadeUp} transition={{ delay: 0.35 }} className="glass-card rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-4">{t("tenderDetail.similarTenders")}</h3>
              <div className="space-y-3">
                {similarTenders.map((st) => {
                  const stCountry = COUNTRIES.find((c) => c.code === st.countryCode);
                  const stMatchColors = getMatchScoreColor(st.matchScore);
                  return (
                    <Link
                      key={st.id}
                      to={localizedPath(urlLang, `/dashboard/tender/${st.id}`)}
                      className="block p-3 rounded-lg bg-dark/40 border border-dark-border hover:border-primary/30 transition-colors"
                    >
                      <h4 className="text-xs font-medium text-slate-200 line-clamp-2 mb-2">{st.title[lang]}</h4>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">
                          {stCountry ? `${stCountry.flag} ${stCountry.name[lang]}` : st.country}
                        </span>
                        <span className={`text-xs font-bold ${stMatchColors.text}`}>{st.matchScore}%</span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
