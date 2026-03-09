import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Layers,
  BrainCircuit,
  Bell,
  BarChart3,
  FileText,
  Languages,
  HardHat,
  Monitor,
  Heart,
  Zap,
  GraduationCap,
  Truck,
  Shield,
  Droplets,
  Radio,
  Wheat,
  ArrowRight,
  Sparkles,
  Star,
  ChevronRight,
} from "lucide-react";
import SEOHead from "../components/SEOHead";
import { COUNTRIES, SECTORS } from "../lib/constants";

/* ------------------------------------------------------------------ */
/*  Animation helpers                                                  */
/* ------------------------------------------------------------------ */
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

/* ------------------------------------------------------------------ */
/*  Icon map for sectors                                               */
/* ------------------------------------------------------------------ */
const sectorIcons: Record<string, React.ReactNode> = {
  HardHat: <HardHat className="h-5 w-5" />,
  Monitor: <Monitor className="h-5 w-5" />,
  Heart: <Heart className="h-5 w-5" />,
  Zap: <Zap className="h-5 w-5" />,
  GraduationCap: <GraduationCap className="h-5 w-5" />,
  Truck: <Truck className="h-5 w-5" />,
  Shield: <Shield className="h-5 w-5" />,
  Droplets: <Droplets className="h-5 w-5" />,
  Radio: <Radio className="h-5 w-5" />,
  Wheat: <Wheat className="h-5 w-5" />,
};

/* ------------------------------------------------------------------ */
/*  Feature definitions                                                */
/* ------------------------------------------------------------------ */
const FEATURES = [
  { key: "f1", icon: <Layers className="h-6 w-6" /> },
  { key: "f2", icon: <BrainCircuit className="h-6 w-6" /> },
  { key: "f3", icon: <Bell className="h-6 w-6" /> },
  { key: "f4", icon: <BarChart3 className="h-6 w-6" /> },
  { key: "f5", icon: <FileText className="h-6 w-6" /> },
  { key: "f6", icon: <Languages className="h-6 w-6" /> },
];

/* ------------------------------------------------------------------ */
/*  Stats data                                                         */
/* ------------------------------------------------------------------ */
const STATS = [
  { value: "10,000+", key: "tenders" },
  { value: "12+", key: "countries" },
  { value: "10", key: "sectors" },
  { value: "$2B+", key: "saved" },
];

export default function HomePage() {
  const { t, i18n } = useTranslation();
  const lang = (i18n.language || "en") as "en" | "ar" | "fr";

  return (
    <>
      <SEOHead
        title="Monaqasat AI"
        description="AI-powered procurement intelligence for MENA. Find and win government contracts faster."
      />

      {/* ============================================================ */}
      {/*  HERO                                                         */}
      {/* ============================================================ */}
      <section className="relative overflow-hidden">
        {/* Background gradients */}
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-40 start-1/4 h-[600px] w-[600px] rounded-full bg-primary/10 blur-[120px]" />
          <div className="absolute -bottom-20 end-1/4 h-[400px] w-[400px] rounded-full bg-accent/8 blur-[100px]" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 pb-20 pt-24 sm:px-6 sm:pt-32 lg:px-8 lg:pt-40">
          <div className="mx-auto max-w-4xl text-center">
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary-light"
            >
              <Sparkles className="h-4 w-4" />
              {t("hero.badge")}
            </motion.div>

            {/* Title */}
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-4xl font-extrabold leading-tight tracking-tight text-white sm:text-5xl lg:text-6xl"
            >
              {t("hero.title")}{" "}
              <span className="gradient-text">{t("hero.titleHighlight")}</span>
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-400"
            >
              {t("hero.subtitle")}
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row"
            >
              <Link
                to="/dashboard"
                className="group flex items-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:bg-primary-dark hover:shadow-xl hover:shadow-primary/30"
              >
                {t("hero.cta")}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1 rtl:rotate-180 rtl:group-hover:-translate-x-1" />
              </Link>
              <Link
                to="/about"
                className="flex items-center gap-2 rounded-xl border border-dark-border px-8 py-3.5 text-base font-semibold text-slate-300 transition-all hover:border-slate-600 hover:text-white"
              >
                {t("hero.ctaSecondary")}
              </Link>
            </motion.div>
          </div>

          {/* Country flags row */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="mx-auto mt-16 max-w-3xl"
          >
            <p className="mb-4 text-center text-sm font-medium text-slate-500">
              {t("hero.trustedBy")}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {COUNTRIES.map((country, i) => (
                <motion.div
                  key={country.code}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.5 + i * 0.04, duration: 0.3 }}
                  className="glass-card flex items-center gap-2 rounded-full px-3 py-1.5"
                >
                  <span className="text-lg">{country.flag}</span>
                  <span className="text-xs font-medium text-slate-400">
                    {country.name[lang] ?? country.name.en}
                  </span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============================================================ */}
      {/*  STATS                                                        */}
      {/* ============================================================ */}
      <section className="relative border-y border-dark-border bg-dark-card/40">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid grid-cols-2 gap-8 lg:grid-cols-4"
          >
            {STATS.map((stat, i) => (
              <motion.div
                key={stat.key}
                variants={fadeUp}
                custom={i}
                className="text-center"
              >
                <p className="text-3xl font-extrabold text-white sm:text-4xl">
                  {stat.value}
                </p>
                <p className="mt-1 text-sm font-medium text-slate-400">
                  {t(`stats.${stat.key}`)}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ============================================================ */}
      {/*  FEATURES                                                     */}
      {/* ============================================================ */}
      <section className="relative py-24">
        <div className="pointer-events-none absolute end-0 top-0 h-[500px] w-[500px] rounded-full bg-primary/5 blur-[140px]" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-16 max-w-2xl text-center"
          >
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              {t("features.title")}
            </h2>
            <p className="mt-4 text-lg text-slate-400">
              {t("features.subtitle")}
            </p>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
          >
            {FEATURES.map((feat, i) => (
              <motion.div
                key={feat.key}
                variants={fadeUp}
                custom={i}
                className="glass-card group rounded-2xl p-6 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary-light transition-colors group-hover:bg-primary/20">
                  {feat.icon}
                </div>
                <h3 className="mb-2 text-lg font-bold text-white">
                  {t(`features.${feat.key}.title`)}
                </h3>
                <p className="text-sm leading-relaxed text-slate-400">
                  {t(`features.${feat.key}.desc`)}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ============================================================ */}
      {/*  HOW IT WORKS                                                 */}
      {/* ============================================================ */}
      <section className="relative border-y border-dark-border bg-dark-card/40 py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-16 max-w-2xl text-center"
          >
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              {t("howItWorks.title")}
            </h2>
            <p className="mt-4 text-lg text-slate-400">
              {t("howItWorks.subtitle")}
            </p>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid gap-10 md:grid-cols-3"
          >
            {[1, 2, 3].map((step, i) => (
              <motion.div
                key={step}
                variants={fadeUp}
                custom={i}
                className="relative text-center"
              >
                {/* Connector line */}
                {i < 2 && (
                  <div className="absolute end-0 top-8 hidden h-0.5 w-full translate-x-1/2 bg-gradient-to-r from-primary/40 to-transparent md:block rtl:rotate-180" />
                )}

                <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-2xl font-extrabold text-primary-light ring-4 ring-primary/20">
                  {step}
                </div>
                <h3 className="mb-2 text-xl font-bold text-white">
                  {t(`howItWorks.s${step}.title`)}
                </h3>
                <p className="mx-auto max-w-xs text-sm leading-relaxed text-slate-400">
                  {t(`howItWorks.s${step}.desc`)}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ============================================================ */}
      {/*  SECTORS                                                      */}
      {/* ============================================================ */}
      <section className="relative py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-12 max-w-2xl text-center"
          >
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              {t("sectors.title")}
            </h2>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-60px" }}
            className="flex flex-wrap justify-center gap-3"
          >
            {SECTORS.map((sector, i) => (
              <motion.div
                key={sector.key}
                variants={fadeUp}
                custom={i}
                className="glass-card flex items-center gap-2.5 rounded-xl px-5 py-3 transition-all hover:border-primary/30 hover:shadow-md hover:shadow-primary/5"
              >
                <span className="text-primary-light">
                  {sectorIcons[sector.icon]}
                </span>
                <span className="text-sm font-medium text-slate-300">
                  {t(`sectors.${sector.key}`)}
                </span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ============================================================ */}
      {/*  TESTIMONIALS                                                 */}
      {/* ============================================================ */}
      <section className="relative border-y border-dark-border bg-dark-card/40 py-24">
        <div className="pointer-events-none absolute start-0 top-0 h-[400px] w-[400px] rounded-full bg-accent/5 blur-[120px]" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-16 max-w-2xl text-center"
          >
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              {t("testimonials.title")}
            </h2>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid gap-6 md:grid-cols-3"
          >
            {[1, 2, 3].map((n, i) => (
              <motion.div
                key={n}
                variants={fadeUp}
                custom={i}
                className="glass-card flex flex-col rounded-2xl p-6"
              >
                <div className="mb-4 flex gap-1">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Star
                      key={j}
                      className="h-4 w-4 fill-accent text-accent"
                    />
                  ))}
                </div>
                <p className="mb-6 flex-1 text-sm leading-relaxed text-slate-300">
                  &ldquo;{t(`testimonials.t${n}.text`)}&rdquo;
                </p>
                <div>
                  <p className="text-sm font-semibold text-white">
                    {t(`testimonials.t${n}.name`)}
                  </p>
                  <p className="text-xs text-slate-500">
                    {t(`testimonials.t${n}.role`)}
                  </p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ============================================================ */}
      {/*  FINAL CTA                                                    */}
      {/* ============================================================ */}
      <section className="relative py-24">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute start-1/3 top-1/2 h-[400px] w-[500px] -translate-y-1/2 rounded-full bg-primary/8 blur-[120px]" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="relative mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8"
        >
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl lg:text-5xl">
            {t("hero.title")}{" "}
            <span className="gradient-text">{t("hero.titleHighlight")}</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-lg text-slate-400">
            {t("hero.subtitle")}
          </p>
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/dashboard"
              className="group flex items-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:bg-primary-dark hover:shadow-xl hover:shadow-primary/30"
            >
              {t("hero.cta")}
              <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1 rtl:rotate-180 rtl:group-hover:-translate-x-1" />
            </Link>
            <Link
              to="/pricing"
              className="flex items-center gap-2 rounded-xl border border-dark-border px-8 py-3.5 text-base font-semibold text-slate-300 transition-all hover:border-slate-600 hover:text-white"
            >
              {t("nav.pricing")}
            </Link>
          </div>
        </motion.div>
      </section>
    </>
  );
}
