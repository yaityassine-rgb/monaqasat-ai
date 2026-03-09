import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bell,
  BellRing,
  Save,
  CheckCircle2,
  Loader2,
  Globe,
  Briefcase,
  Gauge,
  Clock,
  DollarSign,
  Mail,
  History,
  ExternalLink,
} from "lucide-react";
import { COUNTRIES, SECTORS } from "../../lib/constants";
import { useAuth } from "../../lib/auth-context";
import { supabase, isSupabaseConfigured } from "../../lib/supabase";
import { useSubscription } from "../../lib/use-subscription";

type LangKey = "en" | "ar" | "fr";

interface AlertPrefs {
  enabled: boolean;
  frequency: "instant" | "daily" | "weekly";
  min_match_score: number;
  sectors: string[];
  countries: string[];
  statuses: string[];
  min_budget: number;
  email_override: string;
}

interface AlertHistoryEntry {
  id: number;
  tender_count: number;
  email_sent_to: string;
  status: string;
  created_at: string;
  match_scores: Record<string, number>;
}

const DEFAULT_PREFS: AlertPrefs = {
  enabled: false,
  frequency: "daily",
  min_match_score: 60,
  sectors: [],
  countries: [],
  statuses: ["open", "closing-soon"],
  min_budget: 0,
  email_override: "",
};

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

export default function AlertsPage() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as LangKey;
  const { user } = useAuth();
  const { canUseFeature } = useSubscription();

  const [prefs, setPrefs] = useState<AlertPrefs>(DEFAULT_PREFS);
  const [history, setHistory] = useState<AlertHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [tab, setTab] = useState<"settings" | "history">("settings");

  const hasAlertAccess = canUseFeature("emailAlerts");

  useEffect(() => {
    if (!user || !isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    async function load() {
      const [{ data: prefsData }, { data: historyData }] = await Promise.all([
        supabase.from("alert_preferences").select("*").eq("id", user!.id).single(),
        supabase.from("alert_history").select("*").eq("user_id", user!.id).order("created_at", { ascending: false }).limit(20),
      ]);

      if (prefsData) {
        setPrefs({
          enabled: prefsData.enabled,
          frequency: prefsData.frequency,
          min_match_score: prefsData.min_match_score,
          sectors: prefsData.sectors || [],
          countries: prefsData.countries || [],
          statuses: prefsData.statuses || ["open", "closing-soon"],
          min_budget: prefsData.min_budget || 0,
          email_override: prefsData.email_override || "",
        });
      }

      if (historyData) {
        setHistory(historyData);
      }

      setLoading(false);
    }

    load();
  }, [user]);

  useEffect(() => {
    if (showSuccess) {
      const timer = setTimeout(() => setShowSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [showSuccess]);

  const handleSave = async () => {
    if (!user || !isSupabaseConfigured) return;
    setSaving(true);

    await supabase.from("alert_preferences").upsert({
      id: user.id,
      ...prefs,
    });

    setSaving(false);
    setShowSuccess(true);
  };

  const toggleSector = (key: string) => {
    setPrefs((prev) => ({
      ...prev,
      sectors: prev.sectors.includes(key)
        ? prev.sectors.filter((s) => s !== key)
        : [...prev.sectors, key],
    }));
  };

  const toggleCountry = (code: string) => {
    setPrefs((prev) => ({
      ...prev,
      countries: prev.countries.includes(code)
        ? prev.countries.filter((c) => c !== code)
        : [...prev.countries, code],
    }));
  };

  const toggleStatus = (s: string) => {
    setPrefs((prev) => ({
      ...prev,
      statuses: prev.statuses.includes(s)
        ? prev.statuses.filter((x) => x !== s)
        : [...prev.statuses, s],
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-3xl mx-auto"
    >
      {/* Header */}
      <motion.div {...fadeUp} transition={{ delay: 0.1 }} className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <BellRing className="w-6 h-6 text-primary-light" />
          <h1 className="text-2xl md:text-3xl font-bold gradient-text">
            {t("alerts.title")}
          </h1>
        </div>
        <p className="text-slate-400 text-sm">{t("alerts.subtitle")}</p>
      </motion.div>

      {/* Upgrade prompt for free users */}
      {!hasAlertAccess && (
        <motion.div {...fadeUp} transition={{ delay: 0.15 }} className="glass-card rounded-xl p-6 mb-6 border-primary/20 text-center">
          <Bell className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400 mb-3">{t("alerts.upgradeRequired")}</p>
          <a href="/pricing" className="inline-flex px-4 py-2 bg-primary hover:bg-primary-dark text-white text-sm font-medium rounded-lg transition-colors">
            {t("alerts.upgradeCta")}
          </a>
        </motion.div>
      )}

      {/* Success Banner */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div initial={{ opacity: 0, y: -10, height: 0 }} animate={{ opacity: 1, y: 0, height: "auto" }} exit={{ opacity: 0, y: -10, height: 0 }} className="mb-6 overflow-hidden">
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-emerald-400/10 border border-emerald-400/30 text-emerald-400">
              <CheckCircle2 className="w-5 h-5 shrink-0" />
              <span className="text-sm font-medium">{t("alerts.saved")}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tabs */}
      <motion.div {...fadeUp} transition={{ delay: 0.15 }} className="flex gap-2 mb-6">
        <button
          onClick={() => setTab("settings")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "settings" ? "bg-primary/20 text-primary-light border border-primary/40" : "text-slate-400 hover:text-white bg-dark/40 border border-dark-border"
          }`}
        >
          <Bell className="w-4 h-4" />
          {t("alerts.settings")}
        </button>
        <button
          onClick={() => setTab("history")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            tab === "history" ? "bg-primary/20 text-primary-light border border-primary/40" : "text-slate-400 hover:text-white bg-dark/40 border border-dark-border"
          }`}
        >
          <History className="w-4 h-4" />
          {t("alerts.history")}
        </button>
      </motion.div>

      {tab === "settings" && (
        <div className={`space-y-6 ${!hasAlertAccess ? "opacity-50 pointer-events-none" : ""}`}>
          {/* Enable Toggle */}
          <motion.div {...fadeUp} transition={{ delay: 0.18 }} className="glass-card rounded-xl p-5">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-200">
                <BellRing className="w-4 h-4 text-primary-light" />
                {t("alerts.enableAlerts")}
              </label>
              <button
                onClick={() => setPrefs((p) => ({ ...p, enabled: !p.enabled }))}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  prefs.enabled ? "bg-primary" : "bg-slate-600"
                }`}
              >
                <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                  prefs.enabled ? "translate-x-6" : "translate-x-0.5"
                }`} />
              </button>
            </div>
          </motion.div>

          {/* Frequency */}
          <motion.div {...fadeUp} transition={{ delay: 0.2 }} className="glass-card rounded-xl p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
              <Clock className="w-4 h-4 text-primary-light" />
              {t("alerts.frequency")}
            </label>
            <div className="flex gap-2 flex-wrap">
              {(["daily", "weekly"] as const).map((freq) => (
                <button
                  key={freq}
                  onClick={() => setPrefs((p) => ({ ...p, frequency: freq }))}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${
                    prefs.frequency === freq
                      ? "bg-primary/20 border-primary/40 text-primary-light"
                      : "bg-dark/40 border-dark-border text-slate-400 hover:text-white"
                  }`}
                >
                  {t(`alerts.freq.${freq}`)}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Min Match Score */}
          <motion.div {...fadeUp} transition={{ delay: 0.22 }} className="glass-card rounded-xl p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
              <Gauge className="w-4 h-4 text-primary-light" />
              {t("alerts.minScore")}
            </label>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min={20}
                max={95}
                step={5}
                value={prefs.min_match_score}
                onChange={(e) => setPrefs((p) => ({ ...p, min_match_score: parseInt(e.target.value) }))}
                className="flex-1 accent-primary"
              />
              <span className="text-lg font-bold text-primary-light w-12 text-center">
                {prefs.min_match_score}%
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-2">{t("alerts.minScoreHint")}</p>
          </motion.div>

          {/* Min Budget */}
          <motion.div {...fadeUp} transition={{ delay: 0.24 }} className="glass-card rounded-xl p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
              <DollarSign className="w-4 h-4 text-primary-light" />
              {t("alerts.minBudget")}
            </label>
            <input
              type="number"
              min={0}
              step={10000}
              value={prefs.min_budget || ""}
              onChange={(e) => setPrefs((p) => ({ ...p, min_budget: parseInt(e.target.value) || 0 }))}
              placeholder="0"
              className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
            />
          </motion.div>

          {/* Sectors */}
          <motion.div {...fadeUp} transition={{ delay: 0.26 }} className="glass-card rounded-xl p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
              <Briefcase className="w-4 h-4 text-primary-light" />
              {t("alerts.sectors")}
            </label>
            <p className="text-xs text-slate-500 mb-3">{t("alerts.sectorsHint")}</p>
            <div className="flex flex-wrap gap-2">
              {SECTORS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => toggleSector(s.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                    prefs.sectors.includes(s.key)
                      ? "bg-primary/20 border-primary/40 text-primary-light"
                      : "bg-dark/40 border-dark-border text-slate-400 hover:text-white"
                  }`}
                >
                  {t(`sectors.${s.key}`)}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Countries */}
          <motion.div {...fadeUp} transition={{ delay: 0.28 }} className="glass-card rounded-xl p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
              <Globe className="w-4 h-4 text-primary-light" />
              {t("alerts.countries")}
            </label>
            <p className="text-xs text-slate-500 mb-3">{t("alerts.countriesHint")}</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {COUNTRIES.map((c) => {
                const checked = prefs.countries.includes(c.code);
                return (
                  <button
                    key={c.code}
                    onClick={() => toggleCountry(c.code)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
                      checked
                        ? "bg-primary/15 border-primary/40 text-primary-light"
                        : "bg-dark/40 border-dark-border text-slate-400 hover:text-slate-300"
                    }`}
                  >
                    {c.flag} {c.name[lang]}
                  </button>
                );
              })}
            </div>
          </motion.div>

          {/* Statuses */}
          <motion.div {...fadeUp} transition={{ delay: 0.3 }} className="glass-card rounded-xl p-5">
            <label className="text-sm font-medium text-slate-200 mb-3 block">
              {t("alerts.statuses")}
            </label>
            <div className="flex gap-2 flex-wrap">
              {["open", "closing-soon"].map((s) => (
                <button
                  key={s}
                  onClick={() => toggleStatus(s)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${
                    prefs.statuses.includes(s)
                      ? "bg-primary/20 border-primary/40 text-primary-light"
                      : "bg-dark/40 border-dark-border text-slate-400 hover:text-white"
                  }`}
                >
                  {t(`dashboard.${s === "closing-soon" ? "closingSoon" : s}`)}
                </button>
              ))}
            </div>
          </motion.div>

          {/* Email Override */}
          <motion.div {...fadeUp} transition={{ delay: 0.32 }} className="glass-card rounded-xl p-5">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-200 mb-3">
              <Mail className="w-4 h-4 text-primary-light" />
              {t("alerts.emailOverride")}
            </label>
            <input
              type="email"
              value={prefs.email_override}
              onChange={(e) => setPrefs((p) => ({ ...p, email_override: e.target.value }))}
              placeholder={user?.email || t("alerts.emailPlaceholder")}
              className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/25 transition-colors"
            />
            <p className="text-xs text-slate-500 mt-2">{t("alerts.emailHint")}</p>
          </motion.div>

          {/* Save Button */}
          <motion.div {...fadeUp} transition={{ delay: 0.34 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {saving ? t("alerts.saving") : t("alerts.savePrefs")}
            </button>
          </motion.div>
        </div>
      )}

      {tab === "history" && (
        <motion.div {...fadeUp} transition={{ delay: 0.15 }}>
          {history.length === 0 ? (
            <div className="glass-card rounded-xl p-12 text-center">
              <History className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-sm">{t("alerts.noHistory")}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((entry) => (
                <div key={entry.id} className="glass-card rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${entry.status === "sent" ? "bg-emerald-400" : entry.status === "failed" ? "bg-red-400" : "bg-slate-400"}`} />
                      <span className="text-sm font-medium text-slate-200">
                        {entry.tender_count} {t("alerts.tendersMatched")}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {new Date(entry.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <span>{t("alerts.sentTo")}: {entry.email_sent_to}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      entry.status === "sent" ? "bg-emerald-400/10 text-emerald-400" :
                      entry.status === "failed" ? "bg-red-400/10 text-red-400" :
                      "bg-slate-400/10 text-slate-400"
                    }`}>
                      {entry.status}
                    </span>
                  </div>
                  {Object.keys(entry.match_scores).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {Object.entries(entry.match_scores).slice(0, 5).map(([tid, score]) => (
                        <a
                          key={tid}
                          href={`/dashboard/tender/${tid}`}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-dark/60 border border-dark-border text-[10px] text-slate-400 hover:text-primary-light hover:border-primary/30 transition-colors"
                        >
                          <ExternalLink className="w-2.5 h-2.5" />
                          {score}%
                        </a>
                      ))}
                      {Object.keys(entry.match_scores).length > 5 && (
                        <span className="text-[10px] text-slate-500">
                          +{Object.keys(entry.match_scores).length - 5} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
