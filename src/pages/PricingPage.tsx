import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { Check, ChevronDown, Sparkles, Zap, Crown, Shield, Building2, Loader2, Coins } from "lucide-react";
import { useAuth } from "../lib/auth-context";
import { supabase, isSupabaseConfigured } from "../lib/supabase";
import SEOHead from "../components/SEOHead";
import { useLang, localizedPath } from "../lib/use-lang";
import { buildOrganizationJsonLd, buildBreadcrumbJsonLd, buildFaqJsonLd } from "../lib/structured-data";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: "easeOut" as const },
  }),
};

const stagger = {
  visible: { transition: { staggerChildren: 0.08 } },
};

interface Tier {
  key: string;
  monthly: number;
  yearly: number;
  popular?: boolean;
  enterprise?: boolean;
  icon: typeof Zap;
  credits: number | string;
  features: string[];
}

const TIERS: Tier[] = [
  {
    key: "explorer",
    monthly: 0,
    yearly: 0,
    icon: Zap,
    credits: 10,
    features: [
      "50 tender views/month",
      "3 countries",
      "Basic search & filters",
      "Weekly email digest",
      "10 AI credits/month",
    ],
  },
  {
    key: "starter",
    monthly: 49,
    yearly: 470,
    icon: Sparkles,
    credits: 100,
    features: [
      "Unlimited tender views",
      "All 12+ countries",
      "AI smart matching",
      "Real-time alerts",
      "Save & track tenders",
      "100 AI credits/month",
    ],
  },
  {
    key: "professional",
    monthly: 149,
    yearly: 1430,
    popular: true,
    icon: Crown,
    credits: 500,
    features: [
      "Everything in Starter",
      "AI proposal generation",
      "Competitor insights",
      "BOQ analysis",
      "Grants intelligence",
      "500 AI credits/month",
      "Priority 24/7 support",
    ],
  },
  {
    key: "business",
    monthly: 399,
    yearly: 3830,
    icon: Shield,
    credits: 2000,
    features: [
      "Everything in Professional",
      "PPP intelligence",
      "JV partner matchmaking",
      "Pre-qualification service",
      "Team workspace (5 seats)",
      "API access",
      "2,000 AI credits/month",
      "Dedicated account manager",
    ],
  },
  {
    key: "enterprise",
    monthly: 0,
    yearly: 0,
    enterprise: true,
    icon: Building2,
    credits: "Unlimited",
    features: [
      "Everything in Business",
      "Unlimited AI credits",
      "Custom integrations",
      "Unlimited team seats",
      "Market entry consulting",
      "On-premise deployment option",
      "SLA guarantee",
      "Custom training",
    ],
  },
];

export default function PricingPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const lang = useLang();
  const [yearly, setYearly] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);

  const handleCheckout = async (tierKey: string) => {
    if (!user) {
      window.location.href = localizedPath(lang, "/auth/signup");
      return;
    }

    if (tierKey === "free") {
      window.location.href = localizedPath(lang, "/dashboard");
      return;
    }

    if (!isSupabaseConfigured) {
      window.location.href = localizedPath(lang, "/dashboard");
      return;
    }

    setCheckoutLoading(tierKey);

    try {
      const { data, error } = await supabase.functions.invoke("create-checkout", {
        body: {
          userId: user.id,
          tier: tierKey,
          interval: yearly ? "yearly" : "monthly",
          provider: "paddle",
          successUrl: `${window.location.origin}/dashboard/subscription?success=true`,
        },
      });

      if (error) throw error;
      if (data?.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      console.error("Checkout error:", err);
      // Fallback: redirect to dashboard
      window.location.href = localizedPath(lang, "/dashboard/subscription");
    } finally {
      setCheckoutLoading(null);
    }
  };

  return (
    <>
      <SEOHead
        title={t("seo.pricingTitle")}
        description={t("seo.pricingDesc")}
        path="/pricing"
        jsonLd={[
          buildOrganizationJsonLd(lang),
          buildBreadcrumbJsonLd(lang, [{ name: t("nav.pricing"), path: "/pricing" }]),
          buildFaqJsonLd(
            [1, 2, 3, 4, 5].map((n) => ({
              question: t(`pricing.faq.q${n}.q`),
              answer: t(`pricing.faq.q${n}.a`),
            }))
          ),
        ]}
      />

      {/* Hero */}
      <section className="relative overflow-hidden py-24">
        <div className="pointer-events-none absolute -top-40 end-1/4 h-[500px] w-[500px] rounded-full bg-primary/8 blur-[120px]" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-2xl text-center"
          >
            <h1 className="text-4xl font-extrabold text-white sm:text-5xl">
              {t("pricing.title")}
            </h1>
            <p className="mt-4 text-lg text-slate-400">
              {t("pricing.subtitle")}
            </p>

            {/* Toggle */}
            <div className="mt-8 inline-flex items-center gap-3 rounded-full border border-dark-border p-1">
              <button
                onClick={() => setYearly(false)}
                className={`rounded-full px-5 py-2 text-sm font-medium transition-all ${
                  !yearly
                    ? "bg-primary text-white shadow-md shadow-primary/25"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {t("pricing.monthly")}
              </button>
              <button
                onClick={() => setYearly(true)}
                className={`flex items-center gap-2 rounded-full px-5 py-2 text-sm font-medium transition-all ${
                  yearly
                    ? "bg-primary text-white shadow-md shadow-primary/25"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {t("pricing.yearly")}
                <span className="rounded-full bg-accent/20 px-2 py-0.5 text-xs font-semibold text-accent">
                  {t("pricing.save")}
                </span>
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Pricing cards */}
      <section className="pb-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid gap-5 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
          >
            {TIERS.map((tier, i) => (
              <motion.div
                key={tier.key}
                variants={fadeUp}
                custom={i}
                className={`relative flex flex-col rounded-2xl p-6 transition-all ${
                  tier.popular
                    ? "border-2 border-primary bg-dark-card shadow-xl shadow-primary/10"
                    : "glass-card"
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-3 start-1/2 -translate-x-1/2 rtl:translate-x-1/2">
                    <span className="inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-white">
                      <Sparkles className="h-3 w-3" />
                      {t("pricing.popular")}
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-2 mb-1">
                  <tier.icon className={`w-5 h-5 ${tier.popular ? "text-primary-light" : "text-slate-400"}`} />
                  <h3 className="text-lg font-bold text-white capitalize">
                    {t(`pricing.tiers.${tier.key}.name`)}
                  </h3>
                </div>

                <div className="mt-3 flex items-baseline gap-1">
                  {tier.enterprise ? (
                    <span className="text-2xl font-extrabold text-white">{t("pricing.custom")}</span>
                  ) : (
                    <>
                      <span className="text-3xl font-extrabold text-white">
                        ${yearly && tier.yearly > 0 ? Math.round(tier.yearly / 12) : tier.monthly}
                      </span>
                      {tier.monthly > 0 && (
                        <span className="text-sm text-slate-500">/{t("pricing.perMonth")}</span>
                      )}
                    </>
                  )}
                </div>
                {yearly && tier.yearly > 0 && (
                  <p className="text-xs text-slate-500 mt-1">
                    ${tier.yearly}/{t("pricing.perYear")} ({t("pricing.save")} ${tier.monthly * 12 - tier.yearly})
                  </p>
                )}

                <div className="mt-3 flex items-center gap-1.5 text-xs">
                  <Coins className="w-3.5 h-3.5 text-accent" />
                  <span className="text-accent font-medium">
                    {typeof tier.credits === "number" ? `${tier.credits} ${t("pricing.aiCredits")}` : t("pricing.unlimitedCredits")}
                  </span>
                </div>

                <ul className="mt-5 flex-1 space-y-2.5">
                  {tier.features.map((feature, fi) => (
                    <li key={fi} className="flex items-start gap-2">
                      <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" />
                      <span className="text-xs text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleCheckout(tier.key)}
                  disabled={checkoutLoading === tier.key}
                  className={`mt-6 flex items-center justify-center gap-2 rounded-xl py-2.5 text-center text-sm font-semibold transition-all ${
                    tier.popular
                      ? "bg-primary text-white shadow-lg shadow-primary/25 hover:bg-primary-dark"
                      : tier.enterprise
                        ? "bg-accent/10 border border-accent/30 text-accent hover:bg-accent/20"
                        : "border border-dark-border text-slate-300 hover:border-slate-600 hover:text-white"
                  } disabled:opacity-50`}
                >
                  {checkoutLoading === tier.key ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : null}
                  {tier.enterprise
                    ? t("pricing.contactSales")
                    : tier.monthly === 0
                      ? t("pricing.getStarted")
                      : t("pricing.subscribe")}
                </button>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* AI Credit Packs */}
      <section className="pb-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="glass-card rounded-2xl p-8 text-center"
          >
            <div className="flex items-center justify-center gap-2 mb-3">
              <Coins className="w-6 h-6 text-accent" />
              <h2 className="text-xl font-bold text-white">{t("pricing.creditPacks.title")}</h2>
            </div>
            <p className="text-slate-400 text-sm mb-6 max-w-lg mx-auto">
              {t("pricing.creditPacks.desc")}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { credits: 100, price: 49 },
                { credits: 300, price: 129 },
                { credits: 1000, price: 399 },
              ].map((pack) => (
                <div key={pack.credits} className="rounded-xl border border-dark-border p-4 hover:border-accent/30 transition-colors">
                  <p className="text-2xl font-bold text-accent">{pack.credits}</p>
                  <p className="text-xs text-slate-400 mb-2">{t("pricing.aiCredits")}</p>
                  <p className="text-lg font-bold text-white">${pack.price}</p>
                  <p className="text-[10px] text-slate-500">${(pack.price / pack.credits).toFixed(2)}/{t("pricing.perCredit")}</p>
                  <button
                    onClick={() => handleCheckout(`credits-${pack.credits}`)}
                    className="mt-3 w-full rounded-lg border border-accent/30 py-2 text-xs font-medium text-accent hover:bg-accent/10 transition-colors"
                  >
                    {t("pricing.creditPacks.buy")}
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* FAQ */}
      <section className="border-t border-dark-border bg-dark-card/40 py-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mb-12 text-center"
          >
            <h2 className="text-3xl font-extrabold text-white">
              {t("pricing.faq.title")}
            </h2>
          </motion.div>

          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((n) => (
              <motion.div
                key={n}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: n * 0.05, duration: 0.3 }}
                className="glass-card overflow-hidden rounded-xl"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === n ? null : n)}
                  className="flex w-full items-center justify-between px-6 py-4 text-start"
                >
                  <span className="text-sm font-semibold text-white">
                    {t(`pricing.faq.q${n}.q`)}
                  </span>
                  <ChevronDown
                    className={`h-4 w-4 shrink-0 text-slate-400 transition-transform duration-200 ${
                      openFaq === n ? "rotate-180" : ""
                    }`}
                  />
                </button>
                <AnimatePresence>
                  {openFaq === n && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <p className="px-6 pb-4 text-sm leading-relaxed text-slate-400">
                        {t(`pricing.faq.q${n}.a`)}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
