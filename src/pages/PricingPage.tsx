import { useState } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import { Check, ChevronDown, Sparkles, Zap, Crown, Shield, Loader2 } from "lucide-react";
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
  icon: typeof Zap;
  features: string[];
}

const TIERS: Tier[] = [
  {
    key: "free",
    monthly: 0,
    yearly: 0,
    icon: Zap,
    features: [
      "10 tender views/day",
      "Basic search & filters",
      "Save up to 10 tenders",
      "Community support",
    ],
  },
  {
    key: "starter",
    monthly: 79,
    yearly: 790,
    icon: Sparkles,
    features: [
      "Everything in Free",
      "Real AI match scores",
      "20 AI analyses/month",
      "Email alerts for new matches",
      "Priority support",
    ],
  },
  {
    key: "professional",
    monthly: 199,
    yearly: 1990,
    popular: true,
    icon: Crown,
    features: [
      "Everything in Starter",
      "Unlimited AI analyses",
      "10 AI proposals/month (AR/EN/FR)",
      "Competitor insights",
      "BOQ analysis",
      "Priority 24/7 support",
    ],
  },
  {
    key: "business",
    monthly: 499,
    yearly: 4990,
    icon: Shield,
    features: [
      "Everything in Professional",
      "Unlimited proposals",
      "API access",
      "Team workspace (5 seats)",
      "Market intelligence dashboard",
      "Dedicated account manager",
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
      <section className="pb-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid gap-6 md:grid-cols-2 xl:grid-cols-4"
          >
            {TIERS.map((tier, i) => (
              <motion.div
                key={tier.key}
                variants={fadeUp}
                custom={i}
                className={`relative flex flex-col rounded-2xl p-8 transition-all ${
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
                  <h3 className="text-lg font-bold text-white capitalize">{tier.key}</h3>
                </div>

                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-extrabold text-white">
                    ${yearly ? Math.round(tier.yearly / 12) : tier.monthly}
                  </span>
                  {tier.monthly > 0 && (
                    <span className="text-sm text-slate-500">
                      /{yearly ? t("pricing.perMonth") : t("pricing.perMonth")}
                    </span>
                  )}
                </div>
                {yearly && tier.yearly > 0 && (
                  <p className="text-xs text-slate-500 mt-1">
                    ${tier.yearly}/year (save ${tier.monthly * 12 - tier.yearly})
                  </p>
                )}

                <ul className="mt-8 flex-1 space-y-3">
                  {tier.features.map((feature, fi) => (
                    <li key={fi} className="flex items-start gap-2.5">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                      <span className="text-sm text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleCheckout(tier.key)}
                  disabled={checkoutLoading === tier.key}
                  className={`mt-8 flex items-center justify-center gap-2 rounded-xl py-3 text-center text-sm font-semibold transition-all ${
                    tier.popular
                      ? "bg-primary text-white shadow-lg shadow-primary/25 hover:bg-primary-dark"
                      : "border border-dark-border text-slate-300 hover:border-slate-600 hover:text-white"
                  } disabled:opacity-50`}
                >
                  {checkoutLoading === tier.key ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : null}
                  {tier.key === "free"
                    ? t("pricing.getStarted")
                    : tier.key === "business"
                      ? t("pricing.contactSales")
                      : t("pricing.subscribe")}
                </button>
              </motion.div>
            ))}
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
