import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Target,
  Shield,
  TrendingUp,
  ChevronDown,
} from "lucide-react";
import { supabase, isSupabaseConfigured } from "../lib/supabase";
import { useAuth } from "../lib/auth-context";
import { useSubscription } from "../lib/use-subscription";
import { useLang, localizedPath } from "../lib/use-lang";
import type { Tender } from "../lib/types";

interface AnalysisResult {
  summary: string;
  keyRequirements: string[];
  eligibilityAssessment: {
    score: number;
    strengths: string[];
    gaps: string[];
    verdict: "ELIGIBLE" | "PARTIALLY_ELIGIBLE" | "NOT_ELIGIBLE";
  };
  riskFactors: { risk: string; severity: "HIGH" | "MEDIUM" | "LOW"; mitigation: string }[];
  estimatedCompetition: "HIGH" | "MEDIUM" | "LOW";
  recommendedAction: "BID" | "CONSIDER" | "SKIP";
  bidStrategy: string;
}

export default function TenderAnalysis({ tender }: { tender: Tender }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { tier, canUseFeature } = useSubscription();
  const urlLang = useLang();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(true);

  const canAnalyze = canUseFeature("analysesPerMonth") || tier !== "free";

  const runAnalysis = async () => {
    if (!isSupabaseConfigured || !user) {
      setError(t("analysis.notConfigured"));
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Check for cached analysis first
      const { data: cached } = await supabase
        .from("tender_analyses")
        .select("result")
        .eq("tender_id", tender.id)
        .eq("user_id", user.id)
        .eq("analysis_type", "full")
        .single();

      if (cached) {
        setAnalysis(cached.result as AnalysisResult);
        setLoading(false);
        return;
      }

      // Call Gemini analysis edge function
      const { data, error: fnError } = await supabase.functions.invoke("analyze-tender", {
        body: { tenderId: tender.id, userId: user.id },
      });

      if (fnError) throw fnError;
      setAnalysis(data as AnalysisResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("analysis.error"));
    } finally {
      setLoading(false);
    }
  };

  const verdictConfig = {
    ELIGIBLE: { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-400/10" },
    PARTIALLY_ELIGIBLE: { icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-400/10" },
    NOT_ELIGIBLE: { icon: XCircle, color: "text-red-400", bg: "bg-red-400/10" },
  };

  const severityColor = {
    HIGH: "text-red-400 bg-red-400/10 border-red-400/30",
    MEDIUM: "text-amber-400 bg-amber-400/10 border-amber-400/30",
    LOW: "text-emerald-400 bg-emerald-400/10 border-emerald-400/30",
  };

  const actionConfig = {
    BID: { color: "text-emerald-400", label: t("analysis.actionBid") },
    CONSIDER: { color: "text-amber-400", label: t("analysis.actionConsider") },
    SKIP: { color: "text-red-400", label: t("analysis.actionSkip") },
  };

  return (
    <div className="glass-card rounded-xl p-6 border-primary/20">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full"
      >
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-primary-light" />
          <h2 className="text-lg font-semibold gradient-text">
            {t("analysis.title")}
          </h2>
        </div>
        <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`} />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {!analysis && !loading && (
              <div className="mt-4">
                {!canAnalyze ? (
                  <div className="text-center py-6">
                    <Shield className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                    <p className="text-sm text-slate-400 mb-3">{t("analysis.upgradeRequired")}</p>
                    <a
                      href={localizedPath(urlLang, "/pricing")}
                      className="inline-flex px-4 py-2 bg-primary hover:bg-primary-dark text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      {t("analysis.upgradeCta")}
                    </a>
                  </div>
                ) : (
                  <button
                    onClick={runAnalysis}
                    className="w-full mt-2 flex items-center justify-center gap-2 px-4 py-3 bg-primary/10 hover:bg-primary/20 border border-primary/30 text-primary-light text-sm font-medium rounded-lg transition-colors"
                  >
                    <Sparkles className="w-4 h-4" />
                    {t("analysis.runAnalysis")}
                  </button>
                )}
              </div>
            )}

            {loading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-primary animate-spin" />
                <span className="ms-3 text-sm text-slate-400">{t("analysis.analyzing")}</span>
              </div>
            )}

            {error && (
              <div className="mt-4 flex items-center gap-2 px-4 py-3 rounded-lg bg-red-400/10 border border-red-400/30 text-red-400 text-sm">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            {analysis && (
              <div className="mt-4 space-y-4">
                {/* Summary */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-2">{t("analysis.summary")}</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">{analysis.summary}</p>
                </div>

                {/* Eligibility */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-2">{t("analysis.eligibility")}</h3>
                  {(() => {
                    const v = verdictConfig[analysis.eligibilityAssessment.verdict];
                    return (
                      <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${v.bg} mb-3`}>
                        <v.icon className={`w-4 h-4 ${v.color}`} />
                        <span className={`text-sm font-medium ${v.color}`}>
                          {t(`analysis.verdict.${analysis.eligibilityAssessment.verdict}`)}
                        </span>
                        <span className={`ms-auto text-lg font-bold ${v.color}`}>
                          {analysis.eligibilityAssessment.score}%
                        </span>
                      </div>
                    );
                  })()}

                  {analysis.eligibilityAssessment.strengths.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs text-slate-500 mb-1">{t("analysis.strengths")}</p>
                      <ul className="space-y-1">
                        {analysis.eligibilityAssessment.strengths.map((s, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-emerald-400">
                            <CheckCircle2 className="w-3 h-3 shrink-0 mt-0.5" /> {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {analysis.eligibilityAssessment.gaps.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-500 mb-1">{t("analysis.gaps")}</p>
                      <ul className="space-y-1">
                        {analysis.eligibilityAssessment.gaps.map((g, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-amber-400">
                            <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" /> {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Risks */}
                {analysis.riskFactors.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200 mb-2">{t("analysis.risks")}</h3>
                    <div className="space-y-2">
                      {analysis.riskFactors.map((risk, i) => (
                        <div key={i} className="p-3 rounded-lg bg-dark/40 border border-dark-border">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${severityColor[risk.severity]}`}>
                              {risk.severity}
                            </span>
                            <span className="text-xs text-slate-200">{risk.risk}</span>
                          </div>
                          <p className="text-xs text-slate-500">{risk.mitigation}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                <div className="flex items-center gap-4 p-3 rounded-lg bg-dark/40 border border-dark-border">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-slate-400" />
                    <span className="text-xs text-slate-400">{t("analysis.recommendation")}:</span>
                    <span className={`text-sm font-bold ${actionConfig[analysis.recommendedAction].color}`}>
                      {actionConfig[analysis.recommendedAction].label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 ms-auto">
                    <TrendingUp className="w-4 h-4 text-slate-400" />
                    <span className="text-xs text-slate-400">{t("analysis.competition")}:</span>
                    <span className="text-sm font-medium text-slate-200">{analysis.estimatedCompetition}</span>
                  </div>
                </div>

                {/* Strategy */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-2">{t("analysis.strategy")}</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">{analysis.bidStrategy}</p>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
