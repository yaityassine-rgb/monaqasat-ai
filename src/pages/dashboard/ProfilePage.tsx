import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  Building2,
  Save,
  CheckCircle2,
  Briefcase,
  Globe,
  Award,
  Clock,
  FileText,
} from "lucide-react";
import { COUNTRIES, SECTORS } from "../../lib/constants";

type LangKey = "en" | "ar" | "fr";

const STORAGE_KEY = "monaqasat-company-profile";

interface CompanyProfile {
  companyName: string;
  primarySector: string;
  targetCountries: string[];
  certifications: string;
  experience: number;
  description: string;
}

const DEFAULT_PROFILE: CompanyProfile = {
  companyName: "",
  primarySector: "",
  targetCountries: [],
  certifications: "",
  experience: 0,
  description: "",
};

function loadProfile(): CompanyProfile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return { ...DEFAULT_PROFILE, ...JSON.parse(raw) };
    }
  } catch {
    // ignore
  }
  return DEFAULT_PROFILE;
}

function saveProfile(profile: CompanyProfile) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

export default function ProfilePage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as LangKey;

  const [profile, setProfile] = useState<CompanyProfile>(loadProfile);
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => setShowSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [showSuccess]);

  const updateField = <K extends keyof CompanyProfile>(
    key: K,
    value: CompanyProfile[K],
  ) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
  };

  const toggleCountry = (code: string) => {
    setProfile((prev) => {
      const exists = prev.targetCountries.includes(code);
      return {
        ...prev,
        targetCountries: exists
          ? prev.targetCountries.filter((c) => c !== code)
          : [...prev.targetCountries, code],
      };
    });
  };

  const handleSave = () => {
    saveProfile(profile);
    setShowSuccess(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-3xl mx-auto"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="flex items-center gap-3 mb-1">
          <Building2 className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("profile.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("profile.subtitle")}</p>
      </motion.div>

      {/* Success Banner */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            className="mb-6 overflow-hidden"
          >
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-400/10 border border-emerald-400/30 text-emerald-400">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span className="text-sm font-medium">
                {t("profile.saved")}
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Form */}
      <div className="space-y-6">
        {/* Company Name */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.12 }}
          className="glass-card rounded-xl p-5"
        >
          <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
            <Building2 className="w-4 h-4 text-primary-light" />
            {t("profile.companyName")}
          </label>
          <input
            type="text"
            value={profile.companyName}
            onChange={(e) => updateField("companyName", e.target.value)}
            placeholder={t("profile.companyNamePh")}
            className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
          />
        </motion.div>

        {/* Primary Sector */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.16 }}
          className="glass-card rounded-xl p-5"
        >
          <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
            <Briefcase className="w-4 h-4 text-primary-light" />
            {t("profile.sector")}
          </label>
          <select
            value={profile.primarySector}
            onChange={(e) => updateField("primarySector", e.target.value)}
            className="w-full appearance-none bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors cursor-pointer"
          >
            <option value="">--</option>
            {SECTORS.map((s) => (
              <option key={s.key} value={s.key}>
                {t(`sectors.${s.key}`)}
              </option>
            ))}
          </select>
        </motion.div>

        {/* Target Countries */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.2 }}
          className="glass-card rounded-xl p-5"
        >
          <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
            <Globe className="w-4 h-4 text-primary-light" />
            {t("profile.countries")}
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {COUNTRIES.map((c) => {
              const checked = profile.targetCountries.includes(c.code);
              return (
                <label
                  key={c.code}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer text-sm transition-colors ${
                    checked
                      ? "bg-primary/15 border-primary/40 text-primary-light"
                      : "bg-dark/40 border-dark-border text-slate-400 hover:border-dark-border hover:text-slate-300"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleCountry(c.code)}
                    className="sr-only"
                  />
                  <span
                    className={`w-4 h-4 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                      checked
                        ? "bg-primary border-primary"
                        : "border-slate-600"
                    }`}
                  >
                    {checked && (
                      <svg
                        className="w-2.5 h-2.5 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={3}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                  </span>
                  <span>
                    {c.flag} {c.name[lang]}
                  </span>
                </label>
              );
            })}
          </div>
        </motion.div>

        {/* Certifications */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.24 }}
          className="glass-card rounded-xl p-5"
        >
          <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
            <Award className="w-4 h-4 text-primary-light" />
            {t("profile.certifications")}
          </label>
          <input
            type="text"
            value={profile.certifications}
            onChange={(e) => updateField("certifications", e.target.value)}
            placeholder={t("profile.certificationsPh")}
            className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
          />
        </motion.div>

        {/* Years of Experience */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.28 }}
          className="glass-card rounded-xl p-5"
        >
          <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
            <Clock className="w-4 h-4 text-primary-light" />
            {t("profile.experience")}
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={profile.experience || ""}
            onChange={(e) =>
              updateField("experience", parseInt(e.target.value) || 0)
            }
            className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
          />
        </motion.div>

        {/* Company Description */}
        <motion.div
          {...fadeUp}
          transition={{ delay: 0.32 }}
          className="glass-card rounded-xl p-5"
        >
          <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
            <FileText className="w-4 h-4 text-primary-light" />
            {t("profile.description")}
          </label>
          <textarea
            value={profile.description}
            onChange={(e) => updateField("description", e.target.value)}
            placeholder={t("profile.descriptionPh")}
            rows={4}
            className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors resize-none"
          />
        </motion.div>

        {/* Save Button */}
        <motion.div {...fadeUp} transition={{ delay: 0.36 }}>
          <button
            onClick={handleSave}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-primary/20"
          >
            <Save className="w-4 h-4" />
            {t("profile.save")}
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
}
