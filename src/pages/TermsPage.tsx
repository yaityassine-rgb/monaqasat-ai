import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import SEOHead from "../components/SEOHead";
import { useLang } from "../lib/use-lang";
import { buildBreadcrumbJsonLd } from "../lib/structured-data";

const SECTION_KEYS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"] as const;

export default function TermsPage() {
  const { t } = useTranslation();
  const lang = useLang();

  return (
    <>
      <SEOHead
        title={t("seo.termsTitle")}
        description={t("seo.termsDesc")}
        path="/terms"
        jsonLd={buildBreadcrumbJsonLd(lang, [{ name: t("terms.title"), path: "/terms" }])}
      />

      <section className="relative py-24">
        <div className="pointer-events-none absolute -top-40 start-1/4 h-[400px] w-[400px] rounded-full bg-primary/5 blur-[120px]" />

        <div className="relative mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-12"
          >
            <h1 className="text-3xl font-extrabold text-white sm:text-4xl">
              {t("terms.title")}
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              {t("terms.lastUpdated")}
            </p>
          </motion.div>

          <div className="space-y-8">
            {SECTION_KEYS.map((key, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 15 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.03, duration: 0.4 }}
                className="glass-card rounded-xl p-6"
              >
                <h2 className="mb-3 text-base font-bold text-white">
                  {t(`terms.sections.${key}.title`)}
                </h2>
                <p className="whitespace-pre-line text-sm leading-relaxed text-slate-400">
                  {t(`terms.sections.${key}.content`)}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
