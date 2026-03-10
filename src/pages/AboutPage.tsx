import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Globe, BrainCircuit, MessageSquareText, Scale, Building, MapPin, Mail } from "lucide-react";
import SEOHead from "../components/SEOHead";
import { COMPANY } from "../lib/constants";
import { useLang } from "../lib/use-lang";
import { buildOrganizationJsonLd, buildBreadcrumbJsonLd } from "../lib/structured-data";

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

const VALUE_ICONS = [
  <Globe className="h-6 w-6" />,
  <BrainCircuit className="h-6 w-6" />,
  <MessageSquareText className="h-6 w-6" />,
  <Scale className="h-6 w-6" />,
];

export default function AboutPage() {
  const { t } = useTranslation();
  const lang = useLang();

  return (
    <>
      <SEOHead
        title={t("seo.aboutTitle")}
        description={t("seo.aboutDesc")}
        path="/about"
        jsonLd={[
          buildOrganizationJsonLd(lang),
          buildBreadcrumbJsonLd(lang, [{ name: t("nav.about"), path: "/about" }]),
        ]}
      />

      {/* Hero */}
      <section className="relative overflow-hidden py-24">
        <div className="pointer-events-none absolute -top-40 start-1/4 h-[500px] w-[500px] rounded-full bg-primary/8 blur-[120px]" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-3xl text-center"
          >
            <h1 className="text-4xl font-extrabold text-white sm:text-5xl">
              {t("about.title")}
            </h1>
            <p className="mt-4 text-lg text-slate-400">
              {t("about.subtitle")}
            </p>
          </motion.div>
        </div>
      </section>

      {/* Story */}
      <section className="border-y border-dark-border bg-dark-card/40 py-20">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="mb-8 text-2xl font-extrabold text-white sm:text-3xl">
              {t("about.story.title")}
            </h2>
            <div className="space-y-5 text-base leading-relaxed text-slate-400">
              <p>{t("about.story.p1")}</p>
              <p>{t("about.story.p2")}</p>
              <p>{t("about.story.p3")}</p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Values */}
      <section className="py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-16 max-w-2xl text-center"
          >
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              {t("about.values.title")}
            </h2>
          </motion.div>

          <motion.div
            variants={stagger}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            className="grid gap-6 sm:grid-cols-2"
          >
            {[1, 2, 3, 4].map((n, i) => (
              <motion.div
                key={n}
                variants={fadeUp}
                custom={i}
                className="glass-card rounded-2xl p-6 transition-all hover:border-primary/30"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary-light">
                  {VALUE_ICONS[i]}
                </div>
                <h3 className="mb-2 text-lg font-bold text-white">
                  {t(`about.values.v${n}.title`)}
                </h3>
                <p className="text-sm leading-relaxed text-slate-400">
                  {t(`about.values.v${n}.desc`)}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Company info */}
      <section className="border-t border-dark-border bg-dark-card/40 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="mx-auto max-w-lg text-center"
          >
            <h2 className="mb-8 text-2xl font-extrabold text-white">
              {t("about.company.title")}
            </h2>
            <div className="glass-card mx-auto rounded-2xl p-8">
              <div className="mb-4 flex items-center justify-center gap-2">
                <Building className="h-5 w-5 text-primary-light" />
                <span className="text-base font-semibold text-white">
                  {COMPANY.parent}
                </span>
              </div>
              <div className="mb-3 flex items-center justify-center gap-2 text-sm text-slate-400">
                <MapPin className="h-4 w-4 text-primary" />
                <span>{COMPANY.address}</span>
              </div>
              <div className="flex items-center justify-center gap-2 text-sm text-slate-400">
                <Mail className="h-4 w-4 text-primary" />
                <a
                  href={`mailto:${COMPANY.email}`}
                  className="transition-colors hover:text-primary-light"
                >
                  {COMPANY.email}
                </a>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </>
  );
}
