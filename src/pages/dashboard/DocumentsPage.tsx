import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FolderOpen,
  HardDrive,
} from "lucide-react";
import { useAuth } from "../../lib/auth-context";
import { supabase, isSupabaseConfigured } from "../../lib/supabase";
import { useSubscription } from "../../lib/use-subscription";
import { Link } from "react-router-dom";

interface UserDocument {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: "processing" | "ready" | "failed";
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

function formatFileSize(bytes: number): string {
  if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
  if (bytes >= 1_000) return `${(bytes / 1_000).toFixed(0)} KB`;
  return `${bytes} B`;
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { tier } = useSubscription();
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const canUpload = tier !== "free";

  const fetchDocuments = useCallback(async () => {
    if (!user || !isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    const { data } = await supabase
      .from("user_documents")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });

    setDocuments(data || []);
    setLoading(false);
  }, [user]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUpload = async (files: FileList | File[]) => {
    if (!user || !isSupabaseConfigured || uploading) return;

    const fileArray = Array.from(files);
    const allowed = ["pdf", "docx", "doc", "txt"];

    for (const file of fileArray) {
      const ext = file.name.split(".").pop()?.toLowerCase() || "";
      if (!allowed.includes(ext)) continue;
      if (file.size > 20 * 1024 * 1024) continue; // 20MB limit

      setUploading(true);

      try {
        const storagePath = `${user.id}/${Date.now()}_${file.name}`;

        // Upload to Supabase Storage
        const { error: uploadError } = await supabase.storage
          .from("documents")
          .upload(storagePath, file);

        if (uploadError) throw uploadError;

        // Create document record
        const { data: doc, error: docError } = await supabase
          .from("user_documents")
          .insert({
            user_id: user.id,
            file_name: file.name,
            file_type: ext,
            file_size: file.size,
            storage_path: storagePath,
            status: "processing",
          })
          .select("id")
          .single();

        if (docError) throw docError;

        // Trigger processing Edge Function
        supabase.functions
          .invoke("process-document", {
            body: {
              documentId: doc!.id,
              userId: user.id,
              storagePath,
              fileType: ext,
            },
          })
          .catch(console.error);

        await fetchDocuments();
      } catch (err) {
        console.error("Upload error:", err);
      }

      setUploading(false);
    }
  };

  const handleDelete = async (doc: UserDocument) => {
    if (!user || !isSupabaseConfigured) return;

    await supabase.from("user_documents").delete().eq("id", doc.id);
    setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  };

  if (!canUpload) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md"
        >
          <FolderOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">
            {t("documents.upgradeRequired")}
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            {t("documents.upgradeDesc")}
          </p>
          <Link
            to="/pricing"
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors"
          >
            {t("documents.upgradeCta")}
          </Link>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-2xl font-bold text-white">{t("documents.title")}</h1>
        <p className="text-slate-400 text-sm mt-1">{t("documents.subtitle")}</p>

        {/* Upload area */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`mt-6 rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
            dragOver
              ? "border-primary bg-primary/5"
              : "border-dark-border hover:border-slate-600"
          }`}
        >
          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-10 h-10 text-primary animate-spin" />
              <p className="text-sm text-slate-400">{t("documents.uploading")}</p>
            </div>
          ) : (
            <>
              <Upload className="w-10 h-10 text-slate-500 mx-auto mb-3" />
              <p className="text-sm text-slate-300 font-medium">
                {t("documents.dropzone")}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {t("documents.formats")}
              </p>
              <label className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-primary/10 hover:bg-primary/20 text-primary-light text-sm font-medium rounded-lg cursor-pointer transition-colors">
                <Upload className="w-4 h-4" />
                {t("documents.browse")}
                <input
                  type="file"
                  accept=".pdf,.docx,.doc,.txt"
                  multiple
                  className="hidden"
                  onChange={(e) => e.target.files && handleUpload(e.target.files)}
                />
              </label>
            </>
          )}
        </div>

        {/* Document list */}
        <div className="mt-8 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12">
              <HardDrive className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">{t("documents.empty")}</p>
            </div>
          ) : (
            documents.map((doc) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card rounded-xl p-4 flex items-center gap-4"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <FileText className="w-5 h-5 text-primary-light" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {doc.file_name}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-500">
                      {formatFileSize(doc.file_size)}
                    </span>
                    <span className="text-xs text-slate-500">
                      {doc.file_type.toUpperCase()}
                    </span>
                    {doc.chunk_count > 0 && (
                      <span className="text-xs text-slate-500">
                        {doc.chunk_count} {t("documents.chunks")}
                      </span>
                    )}
                  </div>
                </div>

                {/* Status badge */}
                <div className="flex items-center gap-2">
                  {doc.status === "ready" && (
                    <span className="flex items-center gap-1 text-xs text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {t("documents.ready")}
                    </span>
                  )}
                  {doc.status === "processing" && (
                    <span className="flex items-center gap-1 text-xs text-amber-400">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      {t("documents.processing")}
                    </span>
                  )}
                  {doc.status === "failed" && (
                    <span
                      className="flex items-center gap-1 text-xs text-red-400"
                      title={doc.error_message || ""}
                    >
                      <AlertCircle className="w-3.5 h-3.5" />
                      {t("documents.failed")}
                    </span>
                  )}

                  <button
                    onClick={() => handleDelete(doc)}
                    className="p-2 text-slate-500 hover:text-red-400 transition-colors"
                    title={t("documents.delete")}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))
          )}
        </div>

        {/* Info note */}
        <p className="mt-6 text-xs text-slate-500 text-center">
          {t("documents.ragNote")}
        </p>
      </motion.div>
    </div>
  );
}
