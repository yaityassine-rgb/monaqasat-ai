import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Home } from "lucide-react";
import SEOHead from "../components/SEOHead";

export default function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <>
      <SEOHead title={t("notFound.subtitle")} />

      <section className="relative flex min-h-[70vh] items-center justify-center overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute start-1/3 top-1/3 h-[400px] w-[400px] rounded-full bg-primary/8 blur-[120px]" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative px-4 text-center"
        >
          <h1 className="gradient-text text-8xl font-black sm:text-9xl">
            {t("notFound.title")}
          </h1>
          <h2 className="mt-4 text-2xl font-bold text-white sm:text-3xl">
            {t("notFound.subtitle")}
          </h2>
          <p className="mt-3 text-base text-slate-400">
            {t("notFound.text")}
          </p>
          <Link
            to="/"
            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:bg-primary-dark hover:shadow-xl hover:shadow-primary/30"
          >
            <Home className="h-4 w-4" />
            {t("notFound.cta")}
          </Link>
        </motion.div>
      </section>
    </>
  );
}
