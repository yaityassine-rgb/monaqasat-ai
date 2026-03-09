import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Target, Loader2, TrendingUp, Shield, Globe, Award, Users, Clock } from "lucide-react";
import { supabase, isSupabaseConfigured } from "../lib/supabase";
import { useAuth } from "../lib/auth-context";
import { useSubscription } from "../lib/use-subscription";

interface ProbabilityBreakdown {
  factor: string;
  score: number;
  weight: number;
  details: string;
}

interface WinProbabilityResult {
  probability: number;
  verdict: string;
  breakdown: ProbabilityBreakdown[];
  recommendation: string;
}

const FACTOR_ICONS: Record<string, typeof Target> = {
  sector_match: Target,
  experience: Clock,
  country_coverage: Globe,
  eligibility: Shield,
  historical_rate: Award,
  competition: Users,
};

const FACTOR_LABELS: Record<string, string> = {
  sector_match: "winProb.sectorMatch",
  experience: "winProb.experience",
  country_coverage: "winProb.countryCoverage",
  eligibility: "winProb.eligibility",
  historical_rate: "winProb.historicalRate",
  competition: "winProb.competition",
};

function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case "HIGH": return "text-emerald-400";
    case "MODERATE": return "text-amber-400";
    case "LOW": return "text-orange-400";
    default: return "text-red-400";
  }
}

function getGaugeColor(prob: number): string {
  if (prob >= 70) return "#34d399";
  if (prob >= 50) return "#fbbf24";
  if (prob >= 30) return "#fb923c";
  return "#f87171";
}

export default function WinProbability({ tenderId }: { tenderId: string }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { canUseFeature } = useSubscription();
  const [result, setResult] = useState<WinProbabilityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canUse = canUseFeature("competitorInsights");

  const calculate = async () => {
    if (!user || !isSupabaseConfigured) return;
    setLoading(true);
    setError("");

    try {
      const { data, error: fnError } = await supabase.functions.invoke("win-probability", {
        body: { tenderId, userId: user.id },
      });
      if (fnError) throw fnError;
      setResult(data);
    } catch (err) {
      setError((err as Error).message);
    }
    setLoading(false);
  };

  if (!canUse) return null;

  return (
    <div className="glass-card rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4 text-primary-light" />
        {t("winProb.title")}
      </h3>

      {!result && !loading && (
        <button
          onClick={calculate}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary/10 text-primary-light text-sm font-medium rounded-lg hover:bg-primary/20 transition-colors"
        >
          <Target className="w-4 h-4" />
          {t("winProb.calculate")}
        </button>
      )}

      {loading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 text-primary animate-spin" />
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 text-center py-3">{error}</p>
      )}

      {result && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          {/* Probability gauge */}
          <div className="flex items-center gap-4 mb-4">
            <div className="relative w-20 h-20">
              <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#1e293b" strokeWidth="8" />
                <circle
                  cx="50" cy="50" r="40" fill="none"
                  stroke={getGaugeColor(result.probability)}
                  strokeWidth="8"
                  strokeDasharray={`${result.probability * 2.51} 251`}
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-white">
                {result.probability}%
              </span>
            </div>
            <div>
              <p className={`text-sm font-bold ${getVerdictColor(result.verdict)}`}>
                {t(`winProb.verdict.${result.verdict}`)}
              </p>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                {result.recommendation}
              </p>
            </div>
          </div>

          {/* Breakdown */}
          <div className="space-y-2.5">
            {result.breakdown.map((b) => {
              const Icon = FACTOR_ICONS[b.factor] || Target;
              return (
                <div key={b.factor}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="flex items-center gap-1.5 text-xs text-slate-400">
                      <Icon className="w-3 h-3" />
                      {t(FACTOR_LABELS[b.factor] || b.factor)}
                    </span>
                    <span className="text-xs font-semibold text-slate-300">
                      {b.score}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-dark/60 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${b.score}%` }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: getGaugeColor(b.score) }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}
    </div>
  );
}
