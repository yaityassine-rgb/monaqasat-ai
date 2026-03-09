import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Send, Mail, MapPin, Clock, CheckCircle } from "lucide-react";
import SEOHead from "../components/SEOHead";
import { COMPANY } from "../lib/constants";

const SUBJECT_KEYS = ["general", "sales", "support", "partnership", "data"] as const;

export default function ContactPage() {
  const { t } = useTranslation();
  const [sent, setSent] = useState(false);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSent(true);
  }

  return (
    <>
      <SEOHead title={t("contact.title")} description={t("contact.subtitle")} />

      <section className="relative overflow-hidden py-24">
        <div className="pointer-events-none absolute -top-40 start-1/3 h-[500px] w-[500px] rounded-full bg-primary/8 blur-[120px]" />

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mx-auto mb-16 max-w-2xl text-center"
          >
            <h1 className="text-4xl font-extrabold text-white sm:text-5xl">
              {t("contact.title")}
            </h1>
            <p className="mt-4 text-lg text-slate-400">
              {t("contact.subtitle")}
            </p>
          </motion.div>

          <div className="grid gap-10 lg:grid-cols-5">
            {/* Form */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="lg:col-span-3"
            >
              <div className="glass-card rounded-2xl p-8">
                {sent ? (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <CheckCircle className="mb-4 h-12 w-12 text-success" />
                    <p className="text-lg font-semibold text-white">
                      {t("contact.form.success")}
                    </p>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-5">
                    {/* Name */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-300">
                        {t("contact.form.name")}
                      </label>
                      <input
                        type="text"
                        name="name"
                        required
                        className="w-full rounded-xl border border-dark-border bg-dark px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-primary"
                        placeholder={t("contact.form.name")}
                      />
                    </div>

                    {/* Email */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-300">
                        {t("contact.form.email")}
                      </label>
                      <input
                        type="email"
                        name="email"
                        required
                        className="w-full rounded-xl border border-dark-border bg-dark px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-primary"
                        placeholder={t("contact.form.email")}
                      />
                    </div>

                    {/* Subject */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-300">
                        {t("contact.form.subject")}
                      </label>
                      <select
                        name="subject"
                        required
                        className="w-full rounded-xl border border-dark-border bg-dark px-4 py-3 text-sm text-white outline-none transition-colors focus:border-primary"
                      >
                        <option value="" disabled>
                          {t("contact.form.subject")}
                        </option>
                        {SUBJECT_KEYS.map((key) => (
                          <option key={key} value={key}>
                            {t(`contact.form.subjects.${key}`)}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Message */}
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-slate-300">
                        {t("contact.form.message")}
                      </label>
                      <textarea
                        name="message"
                        required
                        rows={5}
                        className="w-full resize-none rounded-xl border border-dark-border bg-dark px-4 py-3 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-primary"
                        placeholder={t("contact.form.message")}
                      />
                    </div>

                    <button
                      type="submit"
                      className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:bg-primary-dark hover:shadow-xl hover:shadow-primary/30"
                    >
                      <Send className="h-4 w-4" />
                      {t("contact.form.send")}
                    </button>
                  </form>
                )}
              </div>
            </motion.div>

            {/* Sidebar */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="lg:col-span-2"
            >
              <div className="glass-card rounded-2xl p-8">
                <h3 className="mb-6 text-lg font-bold text-white">
                  {t("contact.info.title")}
                </h3>

                <div className="space-y-6">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                      <Mail className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-300">
                        {t("contact.info.email")}
                      </p>
                      <a
                        href={`mailto:${COMPANY.email}`}
                        className="text-sm text-primary-light transition-colors hover:text-primary"
                      >
                        {COMPANY.email}
                      </a>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                      <MapPin className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-300">
                        {t("contact.info.address")}
                      </p>
                      <p className="text-sm text-slate-400">
                        {t("contact.info.addressValue")}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary-light">
                      <Clock className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-300">
                        {t("contact.info.hours")}
                      </p>
                      <p className="text-sm text-slate-400">
                        {t("contact.info.hoursValue")}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-8 rounded-xl border border-dark-border bg-dark/50 p-4 text-center">
                  <p className="text-xs text-slate-500">{COMPANY.parent}</p>
                  <p className="mt-1 text-xs text-slate-600">{COMPANY.address}</p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>
    </>
  );
}
