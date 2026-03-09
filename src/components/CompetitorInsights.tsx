import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Users, Loader2, Trophy, TrendingUp, AlertTriangle } from "lucide-react";
import { supabase, isSupabaseConfigured } from "../lib/supabase";
import { useAuth } from "../lib/auth-context";
import { useSubscription } from "../lib/use-subscription";

interface Competitor {
  name: string;
  wins: number;
  totalValue: number;
  avgAmount: number;
  countries: string[];
  sectors: string[];
}

interface MarketStats {
  totalAwards: number;
  totalValue: number;
  avgAwardValue: number;
  uniqueWinners: number;
}

interface AIInsights {
  marketConcentration: string;
  dominantPlayers: string[];
  entryBarriers: string;
  pricingTrend: string;
  opportunities: string[];
  strategy: string;
}

interface CompetitorResult {
  competitors: Competitor[];
  market: MarketStats;
  aiInsights: AIInsights | null;
}

function formatValue(n: number): string {
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toLocaleString();
}

export default function CompetitorInsights({
  sector,
  countryCode,
  tenderId,
}: {
  sector: string;
  countryCode: string;
  tenderId?: string;
}) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { canUseFeature } = useSubscription();
  const [result, setResult] = useState<CompetitorResult | null>(null);
  const [loading, setLoading] = useState(false);

  const canUse = canUseFeature("competitorInsights");

  const analyze = async () => {
    if (!user || !isSupabaseConfigured) return;
    setLoading(true);

    try {
      const { data, error } = await supabase.functions.invoke("competitor-analysis", {
        body: { sector, countryCode, userId: user.id, tenderId },
      });
      if (error) throw error;
      setResult(data);
    } catch (err) {
      console.error("Competitor analysis error:", err);
    }
    setLoading(false);
  };

  if (!canUse) return null;

  return (
    <div className="glass-card rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-accent" />
        {t("competitors.title")}
      </h3>

      {!result && !loading && (
        <button
          onClick={analyze}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-accent/10 text-accent text-sm font-medium rounded-lg hover:bg-accent/20 transition-colors"
        >
          <Users className="w-4 h-4" />
          {t("competitors.analyze")}
        </button>
      )}

      {loading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 text-accent animate-spin" />
        </div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          {/* Market stats */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-dark/40 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-white">{result.market.totalAwards}</p>
              <p className="text-[10px] text-slate-500">{t("competitors.totalAwards")}</p>
            </div>
            <div className="bg-dark/40 rounded-lg p-3 text-center">
              <p className="text-lg font-bold text-white">{result.market.uniqueWinners}</p>
              <p className="text-[10px] text-slate-500">{t("competitors.uniqueWinners")}</p>
            </div>
          </div>

          {/* Top competitors */}
          {result.competitors.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                {t("competitors.topCompetitors")}
              </p>
              <div className="space-y-2">
                {result.competitors.slice(0, 5).map((c, i) => (
                  <div
                    key={c.name}
                    className="flex items-center gap-3 bg-dark/40 rounded-lg px-3 py-2"
                  >
                    <span className="w-5 h-5 rounded bg-accent/10 text-accent text-[10px] font-bold flex items-center justify-center shrink-0">
                      {i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-slate-200 truncate">
                        {c.name}
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {c.wins} {t("competitors.wins")} · ${formatValue(c.avgAmount)} {t("competitors.avg")}
                      </p>
                    </div>
                    <Trophy className="w-3 h-3 text-amber-400 shrink-0" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.competitors.length === 0 && (
            <p className="text-xs text-slate-500 text-center py-3">
              {t("competitors.noData")}
            </p>
          )}

          {/* AI Insights */}
          {result.aiInsights && (
            <div className="border-t border-dark-border pt-3">
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                {t("competitors.aiInsights")}
              </p>

              <div className="space-y-2 text-xs">
                <div className="flex items-start gap-2">
                  <TrendingUp className="w-3 h-3 text-primary-light mt-0.5 shrink-0" />
                  <span className="text-slate-300">
                    {t("competitors.pricing")}: {result.aiInsights.pricingTrend}
                  </span>
                </div>
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 shrink-0" />
                  <span className="text-slate-300">
                    {result.aiInsights.entryBarriers}
                  </span>
                </div>
                {result.aiInsights.strategy && (
                  <p className="text-slate-400 italic leading-relaxed mt-2">
                    {result.aiInsights.strategy}
                  </p>
                )}
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
