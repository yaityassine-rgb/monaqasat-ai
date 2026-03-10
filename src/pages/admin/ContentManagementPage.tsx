import { useState, useEffect, useCallback } from "react";
import { FileUp, Trash2, RefreshCw, CheckCircle2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { adminApi } from "../../lib/admin-api";
import type { DataCounts } from "../../lib/admin-types";

interface QualityInfo {
  type: string;
  label: string;
  total: number;
  table: string;
}

export default function ContentManagementPage() {
  const [counts, setCounts] = useState<DataCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [, setImporting] = useState(false);

  const load = useCallback(async () => {
    try {
      const c = await adminApi.getDataCounts();
      setCounts(c);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const types: QualityInfo[] = counts ? [
    { type: "tenders", label: "Tenders", total: counts.tenders, table: "tenders" },
    { type: "grants", label: "Grants", total: counts.grants, table: "grants" },
    { type: "ppp", label: "PPP Projects", total: counts.ppp_projects, table: "ppp_projects" },
    { type: "companies", label: "Companies", total: counts.companies, table: "companies" },
    { type: "market", label: "Market Intel", total: counts.market_intelligence, table: "market_intelligence" },
    { type: "prequalification", label: "Pre-Qualification", total: counts.prequalification, table: "prequalification_requirements" },
  ] : [];

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>, table: string) {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    try {
      const text = await file.text();
      const records = JSON.parse(text);
      if (!Array.isArray(records)) throw new Error("Expected JSON array");

      let imported = 0;
      for (const record of records) {
        try {
          await adminApi.insertRecord(table, record);
          imported++;
        } catch {
          // Skip duplicates
        }
      }
      toast.success(`Imported ${imported} / ${records.length} records`);
      load();
    } catch (err) {
      toast.error("Import failed — ensure file is a JSON array");
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(6)].map((_, i) => <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-white">Content Management</h1>

      {/* Data Quality Dashboard */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {types.map((t) => (
          <div key={t.type} className="glass-card rounded-xl p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white">{t.label}</h3>
              <span className="text-lg font-bold text-primary-light">{t.total.toLocaleString()}</span>
            </div>

            {/* Quality bar */}
            <div className="mt-3">
              <div className="flex justify-between text-xs text-slate-500">
                <span>Records</span>
                <span>{t.total > 0 ? "Active" : "Empty"}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/5">
                <div
                  className={`h-full rounded-full ${t.total > 100 ? "bg-success" : t.total > 0 ? "bg-warning" : "bg-danger"}`}
                  style={{ width: `${Math.min(100, (t.total / 1000) * 100)}%` }}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="mt-3 flex gap-2">
              <label className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-dark-border px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5 hover:text-white">
                <FileUp className="h-3 w-3" />
                Import JSON
                <input type="file" accept=".json" className="hidden" onChange={(e) => handleImport(e, t.table)} />
              </label>
            </div>
          </div>
        ))}
      </div>

      {/* Bulk Operations */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Bulk Operations</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <button
            onClick={() => toast.info("Update expired statuses — coming soon")}
            className="flex items-center gap-2 rounded-lg border border-dark-border p-4 text-start text-sm text-slate-400 hover:border-warning/30 hover:bg-warning/5 hover:text-white"
          >
            <RefreshCw className="h-5 w-5 text-warning" />
            <div>
              <p className="font-medium">Update Expired</p>
              <p className="text-xs text-slate-600">Close past-deadline tenders</p>
            </div>
          </button>
          <button
            onClick={() => toast.info("Remove duplicates — coming soon")}
            className="flex items-center gap-2 rounded-lg border border-dark-border p-4 text-start text-sm text-slate-400 hover:border-danger/30 hover:bg-danger/5 hover:text-white"
          >
            <Trash2 className="h-5 w-5 text-danger" />
            <div>
              <p className="font-medium">Remove Duplicates</p>
              <p className="text-xs text-slate-600">Find and remove duplicates</p>
            </div>
          </button>
          <button
            onClick={() => toast.info("Re-embed records — coming soon")}
            className="flex items-center gap-2 rounded-lg border border-dark-border p-4 text-start text-sm text-slate-400 hover:border-primary/30 hover:bg-primary/5 hover:text-white"
          >
            <CheckCircle2 className="h-5 w-5 text-primary-light" />
            <div>
              <p className="font-medium">Re-run Embeddings</p>
              <p className="text-xs text-slate-600">Embed null records</p>
            </div>
          </button>
          <button
            onClick={() => toast.info("Data validation — coming soon")}
            className="flex items-center gap-2 rounded-lg border border-dark-border p-4 text-start text-sm text-slate-400 hover:border-accent/30 hover:bg-accent/5 hover:text-white"
          >
            <AlertTriangle className="h-5 w-5 text-accent" />
            <div>
              <p className="font-medium">Validate Data</p>
              <p className="text-xs text-slate-600">Check data quality</p>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
