import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FileText,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Globe,
  Download,
  Trash2,
  Sparkles,
  Lock,
} from "lucide-react";
import { useAuth } from "../../lib/auth-context";
import { supabase, isSupabaseConfigured } from "../../lib/supabase";
import { useSubscription } from "../../lib/use-subscription";
import ProposalExport from "../../components/ProposalExport";

interface ProposalSection {
  key: string;
  title: string;
  content: string;
  status: "pending" | "generating" | "ready" | "error";
}

interface Proposal {
  id: string;
  title: string;
  language: string;
  status: string;
  sections: ProposalSection[];
  tender_id: string | null;
  created_at: string;
  updated_at: string;
}

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ar", label: "العربية" },
  { code: "fr", label: "Français" },
];

export default function ProposalPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { id: proposalId } = useParams();
  const [searchParams] = useSearchParams();
  const tenderId = searchParams.get("tender");
  const { limits } = useSubscription();

  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [activeProposal, setActiveProposal] = useState<Proposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [regeneratingSection, setRegeneratingSection] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [language, setLanguage] = useState("en");
  const [showExport, setShowExport] = useState(false);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  const canGenerate = limits.proposalsPerMonth > 0;

  const fetchProposals = useCallback(async () => {
    if (!user || !isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    const { data } = await supabase
      .from("proposals")
      .select("*")
      .eq("user_id", user.id)
      .order("updated_at", { ascending: false });

    setProposals(data || []);

    // If we have a proposal ID from URL, load it
    if (proposalId && data) {
      const found = data.find((p: Proposal) => p.id === proposalId);
      if (found) {
        setActiveProposal(found);
        setLanguage(found.language);
      }
    }

    setLoading(false);
  }, [user, proposalId]);

  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  const generateProposal = async () => {
    if (!user || !isSupabaseConfigured || generating) return;

    setGenerating(true);

    try {
      const { data, error } = await supabase.functions.invoke(
        "generate-proposal",
        {
          body: {
            userId: user.id,
            tenderId: tenderId || activeProposal?.tender_id || null,
            language,
            proposalId: activeProposal?.id || null,
            mode: "full",
          },
        }
      );

      if (error) throw error;

      if (data?.proposalId) {
        // Fetch the updated proposal
        const { data: updated } = await supabase
          .from("proposals")
          .select("*")
          .eq("id", data.proposalId)
          .single();

        if (updated) {
          setActiveProposal(updated);
          setExpandedSection(
            (updated.sections as ProposalSection[])?.[0]?.key || null
          );
        }
        await fetchProposals();
      }
    } catch (err) {
      console.error("Generate proposal error:", err);
    }

    setGenerating(false);
  };

  const regenerateSection = async (sectionKey: string) => {
    if (!user || !activeProposal || regeneratingSection) return;

    setRegeneratingSection(sectionKey);

    try {
      const { data, error } = await supabase.functions.invoke(
        "generate-proposal",
        {
          body: {
            userId: user.id,
            tenderId: activeProposal.tender_id,
            language: activeProposal.language,
            proposalId: activeProposal.id,
            mode: "single",
            sectionKey,
          },
        }
      );

      if (error) throw error;

      if (data?.proposalId) {
        const { data: updated } = await supabase
          .from("proposals")
          .select("*")
          .eq("id", data.proposalId)
          .single();

        if (updated) setActiveProposal(updated);
      }
    } catch (err) {
      console.error("Regenerate section error:", err);
    }

    setRegeneratingSection(null);
  };

  const saveSection = async (sectionKey: string) => {
    if (!activeProposal) return;

    const updatedSections = (activeProposal.sections as ProposalSection[]).map(
      (s) => (s.key === sectionKey ? { ...s, content: editContent } : s)
    );

    await supabase
      .from("proposals")
      .update({ sections: updatedSections })
      .eq("id", activeProposal.id);

    setActiveProposal({ ...activeProposal, sections: updatedSections });
    setEditingSection(null);
  };

  const deleteProposal = async (id: string) => {
    await supabase.from("proposals").delete().eq("id", id);
    if (activeProposal?.id === id) setActiveProposal(null);
    setProposals((prev) => prev.filter((p) => p.id !== id));
  };

  // Upgrade required
  if (!canGenerate) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md"
        >
          <Lock className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">
            {t("proposals.upgradeRequired")}
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            {t("proposals.upgradeDesc")}
          </p>
          <Link
            to="/pricing"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors"
          >
            {t("proposals.upgradeCta")}
          </Link>
        </motion.div>
      </div>
    );
  }

  // Active proposal editor
  if (activeProposal) {
    const sections = activeProposal.sections as ProposalSection[];

    return (
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <button
                onClick={() => setActiveProposal(null)}
                className="text-sm text-primary-light hover:text-primary mb-2 inline-block"
              >
                ← {t("proposals.backToList")}
              </button>
              <h1 className="text-xl font-bold text-white">
                {activeProposal.title}
              </h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-slate-500">
                  {LANGUAGES.find((l) => l.code === activeProposal.language)
                    ?.label || activeProposal.language}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    activeProposal.status === "ready"
                      ? "bg-emerald-400/10 text-emerald-400"
                      : activeProposal.status === "generating"
                        ? "bg-amber-400/10 text-amber-400"
                        : "bg-slate-400/10 text-slate-400"
                  }`}
                >
                  {activeProposal.status}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowExport(!showExport)}
                className="flex items-center gap-2 px-3 py-2 bg-primary/10 text-primary-light text-sm rounded-lg hover:bg-primary/20 transition-colors"
              >
                <Download className="w-4 h-4" />
                {t("proposals.export")}
              </button>
            </div>
          </div>

          {/* Export panel */}
          {showExport && (
            <div className="mb-6">
              <ProposalExport proposal={activeProposal} />
            </div>
          )}

          {/* Sections */}
          <div className="space-y-3">
            {sections.map((section) => (
              <div key={section.key} className="glass-card rounded-xl overflow-hidden">
                <button
                  onClick={() =>
                    setExpandedSection(
                      expandedSection === section.key ? null : section.key
                    )
                  }
                  className="flex w-full items-center justify-between px-5 py-4 text-start"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        section.status === "ready"
                          ? "bg-emerald-400"
                          : section.status === "error"
                            ? "bg-red-400"
                            : section.status === "generating"
                              ? "bg-amber-400 animate-pulse"
                              : "bg-slate-600"
                      }`}
                    />
                    <span className="text-sm font-semibold text-white">
                      {section.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {section.status === "ready" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          regenerateSection(section.key);
                        }}
                        disabled={regeneratingSection === section.key}
                        className="p-1.5 text-slate-500 hover:text-primary-light transition-colors"
                        title={t("proposals.regenerate")}
                      >
                        {regeneratingSection === section.key ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                      </button>
                    )}
                    {expandedSection === section.key ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                </button>

                {expandedSection === section.key && (
                  <div className="px-5 pb-4 border-t border-dark-border pt-4">
                    {editingSection === section.key ? (
                      <div>
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-primary/50 min-h-[200px] resize-y"
                          dir={activeProposal.language === "ar" ? "rtl" : "ltr"}
                        />
                        <div className="flex gap-2 mt-3">
                          <button
                            onClick={() => saveSection(section.key)}
                            className="px-4 py-2 bg-primary text-white text-sm rounded-lg hover:bg-primary-dark transition-colors"
                          >
                            {t("proposals.save")}
                          </button>
                          <button
                            onClick={() => setEditingSection(null)}
                            className="px-4 py-2 text-slate-400 text-sm hover:text-white transition-colors"
                          >
                            {t("proposals.cancel")}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div
                          className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap"
                          dir={activeProposal.language === "ar" ? "rtl" : "ltr"}
                        >
                          {section.content || (
                            <span className="text-slate-500 italic">
                              {t("proposals.notGenerated")}
                            </span>
                          )}
                        </div>
                        {section.content && (
                          <button
                            onClick={() => {
                              setEditingSection(section.key);
                              setEditContent(section.content);
                            }}
                            className="mt-3 text-xs text-primary-light hover:text-primary transition-colors"
                          >
                            {t("proposals.edit")}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    );
  }

  // Proposal list view
  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">
              {t("proposals.title")}
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              {t("proposals.subtitle")}
            </p>
          </div>
        </div>

        {/* New proposal card */}
        <div className="glass-card rounded-2xl p-6 mb-8">
          <h3 className="text-lg font-semibold text-white mb-4">
            {t("proposals.createNew")}
          </h3>

          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-slate-400" />
              <span className="text-sm text-slate-400">{t("proposals.language")}:</span>
            </div>
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                onClick={() => setLanguage(lang.code)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  language === lang.code
                    ? "bg-primary text-white"
                    : "text-slate-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>

          {tenderId && (
            <p className="text-xs text-slate-500 mb-4">
              {t("proposals.linkedToTender")}: {tenderId}
            </p>
          )}

          <button
            onClick={generateProposal}
            disabled={generating}
            className="flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-primary/20 disabled:opacity-50"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {t("proposals.generating")}
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                {t("proposals.generate")}
              </>
            )}
          </button>

          <p className="text-xs text-slate-500 mt-3">
            {t("proposals.tierInfo", {
              count: limits.proposalsPerMonth === Infinity ? "∞" : String(limits.proposalsPerMonth),
            } as Record<string, string>)}
          </p>
        </div>

        {/* Proposals list */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
          </div>
        ) : proposals.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-sm text-slate-400">{t("proposals.empty")}</p>
          </div>
        ) : (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
              {t("proposals.yourProposals")}
            </h3>
            {proposals.map((proposal) => (
              <motion.div
                key={proposal.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card rounded-xl p-4 flex items-center gap-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
                onClick={() => {
                  setActiveProposal(proposal);
                  setLanguage(proposal.language);
                  setExpandedSection(
                    (proposal.sections as ProposalSection[])?.[0]?.key || null
                  );
                }}
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <FileText className="w-5 h-5 text-primary-light" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {proposal.title}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-500">
                      {LANGUAGES.find((l) => l.code === proposal.language)?.label}
                    </span>
                    <span className="text-xs text-slate-500">
                      {(proposal.sections as ProposalSection[]).filter(
                        (s) => s.status === "ready"
                      ).length}
                      /{(proposal.sections as ProposalSection[]).length}{" "}
                      {t("proposals.sections")}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(proposal.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    proposal.status === "ready"
                      ? "bg-emerald-400/10 text-emerald-400"
                      : proposal.status === "generating"
                        ? "bg-amber-400/10 text-amber-400"
                        : "bg-slate-400/10 text-slate-400"
                  }`}
                >
                  {proposal.status}
                </span>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteProposal(proposal.id);
                  }}
                  className="p-2 text-slate-500 hover:text-red-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
