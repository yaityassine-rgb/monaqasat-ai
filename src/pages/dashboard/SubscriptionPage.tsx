import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { CreditCard, Check, Crown, Zap, Shield, Building2 } from "lucide-react";
import { useSubscription, TIER_PRICES, type Tier } from "../../lib/use-subscription";
import { useLang, localizedPath } from "../../lib/use-lang";
import CreditBalanceWidget from "../../components/CreditBalance";

const TIER_CONFIG: { key: Tier; icon: typeof Crown; color: string }[] = [
  { key: "free", icon: Zap, color: "text-slate-400" },
  { key: "starter", icon: Zap, color: "text-blue-400" },
  { key: "professional", icon: Crown, color: "text-amber-400" },
  { key: "business", icon: Shield, color: "text-emerald-400" },
  { key: "enterprise", icon: Building2, color: "text-purple-400" },
];

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

export default function SubscriptionPage() {
  const { t } = useTranslation();
  const { tier: currentTier, loading, currentPeriodEnd } = useSubscription();
  const urlLang = useLang();

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-4xl mx-auto"
    >
      <motion.div {...fadeUp} transition={{ delay: 0.1 }} className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <CreditCard className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("subscription.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("subscription.subtitle")}</p>
      </motion.div>

      {/* AI Credits */}
      <motion.div {...fadeUp} transition={{ delay: 0.13 }} className="mb-6">
        <CreditBalanceWidget />
      </motion.div>

      {/* Current Plan */}
      <motion.div {...fadeUp} transition={{ delay: 0.15 }} className="glass-card rounded-xl p-6 mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="text-sm text-slate-400 mb-1">{t("subscription.currentPlan")}</p>
            <p className="text-xl font-bold text-white capitalize">{currentTier}</p>
            {currentPeriodEnd && (
              <p className="text-xs text-slate-500 mt-1">
                {t("subscription.renewsOn")} {new Date(currentPeriodEnd).toLocaleDateString()}
              </p>
            )}
          </div>
          <div className="text-end">
            <p className="text-3xl font-bold text-white">
              ${TIER_PRICES[currentTier].monthly}
              <span className="text-sm font-normal text-slate-500">/mo</span>
            </p>
          </div>
        </div>
      </motion.div>

      {/* Plans */}
      {!loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {TIER_CONFIG.map(({ key, icon: Icon, color }, i) => {
            const isCurrent = key === currentTier;
            const price = TIER_PRICES[key];

            return (
              <motion.div
                key={key}
                {...fadeUp}
                transition={{ delay: 0.2 + i * 0.05 }}
                className={`glass-card rounded-xl p-6 ${isCurrent ? "border-primary/40 border-2" : ""}`}
              >
                <div className="flex items-center gap-2 mb-3">
                  <Icon className={`w-5 h-5 ${color}`} />
                  <h3 className="text-lg font-bold text-white capitalize">{key}</h3>
                  {isCurrent && (
                    <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary-light text-xs font-medium">
                      {t("subscription.current")}
                    </span>
                  )}
                </div>

                <p className="text-2xl font-bold text-white mb-4">
                  ${price.monthly}
                  <span className="text-sm font-normal text-slate-500">/mo</span>
                </p>

                <ul className="space-y-2 mb-6">
                  {(t(`subscription.${key}Features`, { returnObjects: true }) as string[]).map(
                    (feature: string, fi: number) => (
                      <li key={fi} className="flex items-start gap-2">
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                        <span className="text-sm text-slate-300">{feature}</span>
                      </li>
                    ),
                  )}
                </ul>

                {isCurrent ? (
                  <button
                    disabled
                    className="w-full py-2.5 rounded-lg border border-dark-border text-sm font-medium text-slate-500 cursor-not-allowed"
                  >
                    {t("subscription.currentPlan")}
                  </button>
                ) : key === "free" ? null : (
                  <Link
                    to={localizedPath(urlLang, "/pricing")}
                    className="block w-full py-2.5 rounded-lg bg-primary hover:bg-primary-dark text-center text-sm font-semibold text-white transition-colors"
                  >
                    {t("subscription.upgrade")}
                  </Link>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
