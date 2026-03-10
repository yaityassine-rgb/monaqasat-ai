import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useLang, localizedPath } from "../../lib/use-lang";
import { supabase } from "../../lib/supabase";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Calendar,
  DollarSign,
  Globe,
  Layers,
  ExternalLink,
  Bookmark,
  Clock,
  Target,
  MapPin,
  Sparkles,
  FileText,
  Loader2,
  AlertCircle,
  Users,
  Tag,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface GrantDetail {
  id: string;
  title: string;
  source: string;
  sourceLabel: string;
  sourceUrl: string;
  fundingOrganization: string;
  fundingAmount: number;
  fundingAmountMax: number;
  currency: string;
  grantType: string;
  country: string;
  countryCode: string;
  region: string;
  sector: string;
  sectors: string[];
  eligibilityCriteria: string;
  eligibilityCountries: string[];
  description: string;
  applicationDeadline: string;
  publishDate: string;
  status: string;
  contactInfo: string;
  documentsUrl: string;
  tags: string[];
}

/* ------------------------------------------------------------------ */
/*  Source styling                                                      */
/* ------------------------------------------------------------------ */

const SOURCE_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  world_bank: { color: "text-blue-400", bg: "bg-blue-400/10 border-blue-400/30", label: "World Bank" },
  isdb:       { color: "text-emerald-400", bg: "bg-emerald-400/10 border-emerald-400/30", label: "IsDB" },
  afdb:       { color: "text-amber-400", bg: "bg-amber-400/10 border-amber-400/30", label: "AfDB" },
  ungm:       { color: "text-sky-400", bg: "bg-sky-400/10 border-sky-400/30", label: "UN (UNGM)" },
  eu_ted:     { color: "text-indigo-400", bg: "bg-indigo-400/10 border-indigo-400/30", label: "EU (TED)" },
  ebrd:       { color: "text-violet-400", bg: "bg-violet-400/10 border-violet-400/30", label: "EBRD" },
  afesd:      { color: "text-teal-400", bg: "bg-teal-400/10 border-teal-400/30", label: "AFESD" },
  opec_fund:  { color: "text-orange-400", bg: "bg-orange-400/10 border-orange-400/30", label: "OPEC Fund" },
};

function getSourceStyle(source: string) {
  return SOURCE_STYLES[source] || { color: "text-slate-400", bg: "bg-slate-400/10 border-slate-400/30", label: source };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function countryCodeToFlag(code: string): string {
  if (!code || code.length !== 2) return "";
  const offset = 127397;
  return String.fromCodePoint(
    code.toUpperCase().charCodeAt(0) + offset,
    code.toUpperCase().charCodeAt(1) + offset,
  );
}

function formatAmount(amount: number, currency = "USD"): string {
  if (!amount || amount <= 0) return "Not disclosed";
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B ${currency}`;
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M ${currency}`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K ${currency}`;
  return `$${amount.toLocaleString()} ${currency}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function getStatusStyle(status: string): string {
  switch (status) {
    case "open":
    case "upcoming":
      return "text-emerald-400 bg-emerald-400/10 border-emerald-400/30";
    case "closing_soon":
      return "text-amber-400 bg-amber-400/10 border-amber-400/30";
    case "closed":
    case "awarded":
      return "text-red-400 bg-red-400/10 border-red-400/30";
    default:
      return "text-slate-400 bg-slate-400/10 border-slate-400/30";
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "open": return "Open";
    case "closing_soon": return "Closing Soon";
    case "closed": return "Closed";
    case "upcoming": return "Upcoming";
    case "awarded": return "Awarded";
    default: return status;
  }
}

function getGrantTypeLabel(type: string): string {
  switch (type) {
    case "project_grant": return "Project Grant";
    case "technical_assistance": return "Technical Assistance";
    case "capacity_building": return "Capacity Building";
    case "research": return "Research";
    case "emergency": return "Emergency";
    default: return type || "Grant";
  }
}

const fadeUp = { initial: { opacity: 0, y: 20 }, animate: { opacity: 1, y: 0 } };

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function GrantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const lang = i18n.language as "en" | "ar" | "fr";
  const urlLang = useLang();
  const isRtl = lang === "ar";

  const [grant, setGrant] = useState<GrantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [saved, setSaved] = useState(false);
  const [similarGrants, setSimilarGrants] = useState<{ id: string; title: string; source: string; fundingAmount: number; country: string; countryCode: string }[]>([]);

  useEffect(() => {
    async function fetchGrant() {
      if (!id) { setError(true); setLoading(false); return; }
      setLoading(true);
      setError(false);

      try {
        const { data, error: fetchError } = await supabase
          .from("grants")
          .select("*")
          .eq("id", id)
          .single();

        if (fetchError || !data) {
          setError(true);
          setLoading(false);
          return;
        }

        const title = lang === "ar" ? (data.title_ar || data.title) : lang === "fr" ? (data.title_fr || data.title) : data.title;
        const desc = lang === "ar" ? (data.description_ar || data.description) : lang === "fr" ? (data.description_fr || data.description) : data.description;
        const fundingOrg = lang === "ar" ? (data.funding_organization_ar || data.funding_organization) : lang === "fr" ? (data.funding_organization_fr || data.funding_organization) : data.funding_organization;
        const style = getSourceStyle(data.source);

        setGrant({
          id: data.id,
          title: title || "Untitled Grant",
          source: data.source || "",
          sourceLabel: style.label,
          sourceUrl: data.source_url || "",
          fundingOrganization: fundingOrg || "",
          fundingAmount: Number(data.funding_amount) || 0,
          fundingAmountMax: Number(data.funding_amount_max) || 0,
          currency: data.currency || "USD",
          grantType: data.grant_type || "",
          country: data.country || "",
          countryCode: data.country_code || "",
          region: data.region || "",
          sector: data.sector || "",
          sectors: data.sectors || [],
          eligibilityCriteria: data.eligibility_criteria || "",
          eligibilityCountries: data.eligibility_countries || [],
          description: desc || "",
          applicationDeadline: data.application_deadline || "",
          publishDate: data.publish_date || "",
          status: data.status || "open",
          contactInfo: data.contact_info || "",
          documentsUrl: data.documents_url || "",
          tags: data.tags || [],
        });

        // Fetch similar grants (same sector, different ID)
        if (data.sector) {
          const { data: similar } = await supabase
            .from("grants")
            .select("id, title, title_ar, title_fr, source, funding_amount, country, country_code")
            .eq("sector", data.sector)
            .neq("id", data.id)
            .eq("status", "open")
            .order("funding_amount", { ascending: false })
            .limit(4);

          if (similar) {
            setSimilarGrants(similar.map((s) => ({
              id: s.id,
              title: lang === "ar" ? (s.title_ar || s.title) : lang === "fr" ? (s.title_fr || s.title) : s.title,
              source: s.source,
              fundingAmount: Number(s.funding_amount) || 0,
              country: s.country || "",
              countryCode: s.country_code || "",
            })));
          }
        }
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    }

    fetchGrant();
  }, [id, lang]);

  // Check saved state from localStorage
  useEffect(() => {
    if (!id) return;
    try {
      const savedGrants = JSON.parse(localStorage.getItem("monaqasat-saved-grants") || "[]");
      setSaved(savedGrants.includes(id));
    } catch { /* ignore */ }
  }, [id]);

  const toggleSave = () => {
    if (!id) return;
    const savedGrants: string[] = JSON.parse(localStorage.getItem("monaqasat-saved-grants") || "[]");
    const next = saved ? savedGrants.filter((gid) => gid !== id) : [...savedGrants, id];
    localStorage.setItem("monaqasat-saved-grants", JSON.stringify(next));
    setSaved(!saved);
  };

  /* Loading */
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <Loader2 className="w-10 h-10 text-primary-light animate-spin" />
      </div>
    );
  }

  /* Not found */
  if (error || !grant) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="glass-card rounded-xl p-12 text-center max-w-md">
          <Target className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-slate-200 mb-2">
            {t("grantDetail.notFound")}
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            {t("grantDetail.notFoundDesc")}
          </p>
          <Link
            to={localizedPath(urlLang, "/dashboard/grants")}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary hover:bg-primary-dark text-white text-sm font-medium rounded-lg transition-colors"
          >
            {isRtl ? <ArrowRight className="w-4 h-4" /> : <ArrowLeft className="w-4 h-4" />}
            {t("grantDetail.backToGrants")}
          </Link>
        </div>
      </div>
    );
  }

  const sourceStyle = getSourceStyle(grant.source);
  const deadlineDate = grant.applicationDeadline ? new Date(grant.applicationDeadline) : null;
  const isExpired = deadlineDate ? deadlineDate < new Date() : false;
  const daysLeft = deadlineDate ? Math.ceil((deadlineDate.getTime() - Date.now()) / 86400000) : null;

  const infoItems = [
    {
      icon: DollarSign,
      label: t("grantDetail.fundingAmount"),
      value: formatAmount(grant.fundingAmount, grant.currency),
    },
    {
      icon: Calendar,
      label: t("grantDetail.deadline"),
      value: formatDate(grant.applicationDeadline),
      extra: daysLeft !== null && !isExpired ? `${daysLeft} days left` : isExpired ? "Expired" : undefined,
      extraColor: daysLeft !== null && daysLeft <= 14 ? "text-amber-400" : isExpired ? "text-red-400" : "text-emerald-400",
    },
    {
      icon: Clock,
      label: t("grantDetail.published"),
      value: formatDate(grant.publishDate),
    },
    {
      icon: Layers,
      label: t("grantDetail.sector"),
      value: grant.sector || "General",
    },
    {
      icon: Globe,
      label: t("grantDetail.country"),
      value: grant.country ? `${countryCodeToFlag(grant.countryCode)} ${grant.country}` : grant.region || "Global",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen p-4 md:p-6 lg:p-8 max-w-5xl mx-auto"
    >
      {/* Back Button */}
      <motion.div {...fadeUp} transition={{ delay: 0.05 }}>
        <Link
          to={localizedPath(urlLang, "/dashboard/grants")}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-primary-light transition-colors mb-6"
        >
          {isRtl ? <ArrowRight className="w-4 h-4" /> : <ArrowLeft className="w-4 h-4" />}
          {t("grantDetail.backToGrants")}
        </Link>
      </motion.div>

      {/* Header */}
      <motion.div {...fadeUp} transition={{ delay: 0.1 }} className="glass-card rounded-xl p-6 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-start gap-6">
          <div className="flex-1 min-w-0">
            {/* Badges row */}
            <div className="flex items-center gap-2 flex-wrap mb-3">
              <span className="text-xs text-slate-500 font-mono">{grant.id.slice(0, 20)}</span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md border text-xs font-medium ${getStatusStyle(grant.status)}`}>
                {getStatusLabel(grant.status)}
              </span>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md border text-xs font-medium ${sourceStyle.bg} ${sourceStyle.color}`}>
                {grant.sourceLabel}
              </span>
              {grant.grantType && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-md border border-dark-border text-xs font-medium text-slate-400">
                  {getGrantTypeLabel(grant.grantType)}
                </span>
              )}
            </div>

            {/* Title */}
            <h1 className="text-xl md:text-2xl font-bold text-slate-100 leading-snug mb-2">
              {grant.title}
            </h1>

            {/* Organization */}
            {grant.fundingOrganization && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Building2 className="w-4 h-4 shrink-0" />
                <span>{grant.fundingOrganization}</span>
              </div>
            )}
          </div>

          {/* Funding badge */}
          <div className="shrink-0 flex flex-col items-center">
            <span className="text-xs text-slate-500 mb-2">{t("grantDetail.fundingAmount")}</span>
            <div className="px-5 py-4 rounded-xl bg-emerald-400/10 border border-emerald-400/30">
              <span className="text-2xl font-bold text-emerald-400">
                {formatAmount(grant.fundingAmount, grant.currency)}
              </span>
              {grant.fundingAmountMax > 0 && grant.fundingAmountMax !== grant.fundingAmount && (
                <div className="text-xs text-slate-400 text-center mt-1">
                  up to {formatAmount(grant.fundingAmountMax, grant.currency)}
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Info Grid */}
      <motion.div
        {...fadeUp}
        transition={{ delay: 0.15 }}
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6"
      >
        {infoItems.map((item, idx) => (
          <div key={idx} className="glass-card rounded-xl p-4 flex flex-col gap-2">
            <div className="flex items-center gap-2 text-slate-500">
              <item.icon className="w-4 h-4" />
              <span className="text-xs">{item.label}</span>
            </div>
            <span className="text-sm font-semibold text-slate-200">{item.value}</span>
            {"extra" in item && item.extra && (
              <span className={`text-xs font-medium ${item.extraColor}`}>{item.extra}</span>
            )}
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <motion.div {...fadeUp} transition={{ delay: 0.2 }} className="glass-card rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">{t("grantDetail.description")}</h2>
            {grant.description ? (
              <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{grant.description}</p>
            ) : (
              <p className="text-sm text-slate-500 italic">{t("grantDetail.noDescription")}</p>
            )}
          </motion.div>

          {/* Eligibility */}
          {(grant.eligibilityCriteria || grant.eligibilityCountries.length > 0) && (
            <motion.div {...fadeUp} transition={{ delay: 0.25 }} className="glass-card rounded-xl p-6">
              <h2 className="text-lg font-semibold text-slate-100 mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-primary-light" />
                {t("grantDetail.eligibility")}
              </h2>
              {grant.eligibilityCriteria && (
                <p className="text-sm text-slate-300 leading-relaxed mb-4 whitespace-pre-line">{grant.eligibilityCriteria}</p>
              )}
              {grant.eligibilityCountries.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase tracking-wider text-slate-500 mb-2">{t("grantDetail.eligibleCountries")}</h3>
                  <div className="flex flex-wrap gap-2">
                    {grant.eligibilityCountries.map((c) => (
                      <span key={c} className="inline-flex items-center px-2.5 py-1 rounded-md bg-dark/60 border border-dark-border text-xs text-slate-300">
                        <MapPin className="w-3 h-3 mr-1 text-slate-500" />
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Sectors & Tags */}
          {(grant.sectors.length > 0 || grant.tags.length > 0) && (
            <motion.div {...fadeUp} transition={{ delay: 0.3 }} className="glass-card rounded-xl p-6">
              {grant.sectors.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
                    <Layers className="w-4 h-4 text-primary-light" />
                    {t("grantDetail.sectors")}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {grant.sectors.map((s) => (
                      <span key={s} className="inline-flex items-center px-2.5 py-1 rounded-md bg-primary/10 border border-primary/20 text-xs text-primary-light font-medium">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {grant.tags.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-2 flex items-center gap-2">
                    <Tag className="w-4 h-4 text-slate-400" />
                    {t("grantDetail.tags")}
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {grant.tags.map((tag) => (
                      <span key={tag} className="inline-flex items-center px-2.5 py-1 rounded-md bg-dark/60 border border-dark-border text-xs text-slate-400">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Action Buttons */}
          <motion.div {...fadeUp} transition={{ delay: 0.2 }} className="glass-card rounded-xl p-5 space-y-3">
            {/* Apply / View on Source */}
            <a
              href={grant.sourceUrl || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className={`w-full flex items-center justify-center gap-2 px-4 py-3 text-white text-sm font-medium rounded-lg transition-colors ${
                grant.sourceUrl
                  ? "bg-primary hover:bg-primary-dark cursor-pointer"
                  : "bg-gray-600 cursor-not-allowed opacity-50"
              }`}
              onClick={(e) => { if (!grant.sourceUrl) e.preventDefault(); }}
            >
              <ExternalLink className="w-4 h-4" />
              {t("grantDetail.applyNow")}
            </a>
            {grant.sourceUrl ? (
              <p className="text-[10px] text-slate-500 text-center -mt-1">
                {t("grantDetail.externalLink")}
              </p>
            ) : (
              <p className="text-[10px] text-amber-400 text-center -mt-1 flex items-center justify-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {t("grantDetail.noSourceUrl")}
              </p>
            )}

            {/* Documents link */}
            {grant.documentsUrl && (
              <a
                href={grant.documentsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full flex items-center justify-center gap-2 px-4 py-3 border border-dark-border bg-dark/40 text-slate-300 hover:border-primary/30 hover:text-primary-light text-sm font-medium rounded-lg transition-colors"
              >
                <FileText className="w-4 h-4" />
                {t("grantDetail.viewDocuments")}
              </a>
            )}

            {/* Save */}
            <button
              onClick={toggleSave}
              className={`w-full flex items-center justify-center gap-2 px-4 py-3 border text-sm font-medium rounded-lg transition-colors ${
                saved
                  ? "border-accent/40 bg-accent/10 text-accent hover:bg-accent/20"
                  : "border-dark-border bg-dark/40 text-slate-300 hover:border-primary/30 hover:text-primary-light"
              }`}
            >
              <Bookmark className="w-4 h-4" />
              {saved ? t("grantDetail.saved") : t("grantDetail.saveForLater")}
            </button>
          </motion.div>

          {/* Contact Info */}
          {grant.contactInfo && (
            <motion.div {...fadeUp} transition={{ delay: 0.25 }} className="glass-card rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-3">{t("grantDetail.contactInfo")}</h3>
              <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-line">{grant.contactInfo}</p>
            </motion.div>
          )}

          {/* Deadline countdown */}
          {deadlineDate && !isExpired && daysLeft !== null && (
            <motion.div {...fadeUp} transition={{ delay: 0.3 }} className="glass-card rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" />
                {t("grantDetail.timeRemaining")}
              </h3>
              <div className="text-center">
                <span className={`text-3xl font-bold ${daysLeft <= 7 ? "text-red-400" : daysLeft <= 30 ? "text-amber-400" : "text-emerald-400"}`}>
                  {daysLeft}
                </span>
                <span className="text-sm text-slate-400 ml-2">{t("grantDetail.daysLeft")}</span>
              </div>
            </motion.div>
          )}

          {/* Similar Grants */}
          {similarGrants.length > 0 && (
            <motion.div {...fadeUp} transition={{ delay: 0.35 }} className="glass-card rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-primary-light" />
                {t("grantDetail.similarGrants")}
              </h3>
              <div className="space-y-3">
                {similarGrants.map((sg) => {
                  const sgStyle = getSourceStyle(sg.source);
                  return (
                    <Link
                      key={sg.id}
                      to={localizedPath(urlLang, `/dashboard/grants/${sg.id}`)}
                      className="block p-3 rounded-lg bg-dark/40 border border-dark-border hover:border-primary/30 transition-colors"
                    >
                      <h4 className="text-xs font-medium text-slate-200 line-clamp-2 mb-2">{sg.title}</h4>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-slate-500">
                          {countryCodeToFlag(sg.countryCode)} {sg.country}
                        </span>
                        <span className={`text-xs font-bold ${sgStyle.color}`}>
                          {formatAmount(sg.fundingAmount, "USD")}
                        </span>
                      </div>
                    </Link>
                  );
                })}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
