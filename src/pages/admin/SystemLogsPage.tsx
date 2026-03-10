import { useState, useEffect, useCallback } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { formatDistanceToNow } from "date-fns";
import { Activity, Shield, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { adminApi } from "../../lib/admin-api";
import DataTable from "../../components/admin/DataTable";
import ExportButton from "../../components/admin/ExportButton";
import type { AuditLogEntry } from "../../lib/admin-types";

type Tab = "usage" | "audit" | "errors";

const usageColumns: ColumnDef<Record<string, unknown>, unknown>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "user_id", header: "User", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> },
  { accessorKey: "event_type", header: "Event", cell: ({ getValue }) => <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs">{String(getValue())}</span> },
  { accessorKey: "metadata", header: "Details", cell: ({ getValue }) => { const v = getValue(); return v ? <span className="max-w-xs truncate block text-xs text-slate-500">{JSON.stringify(v)}</span> : "-"; } },
  { accessorKey: "created_at", header: "Time", cell: ({ getValue }) => formatDistanceToNow(new Date(String(getValue())), { addSuffix: true }) },
];

const auditColumns: ColumnDef<AuditLogEntry, unknown>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "admin_user_id", header: "Admin", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> },
  { accessorKey: "action", header: "Action", cell: ({ getValue }) => <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs text-warning">{String(getValue())}</span> },
  { accessorKey: "target_type", header: "Target Type", cell: ({ getValue }) => getValue() || "-" },
  { accessorKey: "target_id", header: "Target ID", cell: ({ getValue }) => getValue() ? <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> : "-" },
  { accessorKey: "details", header: "Details", cell: ({ getValue }) => { const v = getValue(); return v && Object.keys(v as Record<string, unknown>).length ? <span className="max-w-xs truncate block text-xs text-slate-500">{JSON.stringify(v)}</span> : "-"; } },
  { accessorKey: "created_at", header: "Time", cell: ({ getValue }) => formatDistanceToNow(new Date(String(getValue())), { addSuffix: true }) },
];

export default function SystemLogsPage() {
  const [tab, setTab] = useState<Tab>("usage");
  const [usageData, setUsageData] = useState<Record<string, unknown>[]>([]);
  const [auditData, setAuditData] = useState<AuditLogEntry[]>([]);
  const [errorData, setErrorData] = useState<Record<string, unknown>[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === "usage") {
        const res = await adminApi.getUsageEvents(page);
        setUsageData(res.data);
        setTotal(res.count);
      } else if (tab === "audit") {
        const res = await adminApi.getAuditLog(page);
        setAuditData(res.data);
        setTotal(res.count);
      } else {
        // Errors from scraper_runs
        const res = await adminApi.getData("scraper_runs", page, 25, "", { status: "failed" });
        setErrorData(res.data);
        setTotal(res.count);
      }
    } catch {
      toast.error("Failed to load logs");
    } finally {
      setLoading(false);
    }
  }, [tab, page]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(1); }, [tab]);

  const tabs: { key: Tab; label: string; icon: typeof Activity }[] = [
    { key: "usage", label: "Usage Events", icon: Activity },
    { key: "audit", label: "Audit Trail", icon: Shield },
    { key: "errors", label: "Error Log", icon: AlertCircle },
  ];

  const errorColumns: ColumnDef<Record<string, unknown>, unknown>[] = [
    { accessorKey: "id", header: "ID", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> },
    { accessorKey: "scraper_key", header: "Scraper" },
    { accessorKey: "scraper_type", header: "Type" },
    { accessorKey: "error_message", header: "Error", cell: ({ getValue }) => <span className="max-w-sm truncate block text-xs text-danger">{String(getValue() || "Unknown error")}</span> },
    { accessorKey: "started_at", header: "Time", cell: ({ getValue }) => getValue() ? formatDistanceToNow(new Date(String(getValue())), { addSuffix: true }) : "-" },
  ];

  const currentData = tab === "usage" ? usageData : tab === "audit" ? auditData : errorData;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-white">System Logs</h1>
        <ExportButton data={currentData as Record<string, unknown>[]} filename={`logs-${tab}`} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-dark-card p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-primary/10 text-primary-light" : "text-slate-500 hover:text-white"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {tab === "usage" && (
        <DataTable
          data={usageData}
          columns={usageColumns}
          serverPagination={{ pageIndex: page - 1, pageCount: Math.ceil(total / 25), onPageChange: (p) => setPage(p + 1) }}
        />
      )}
      {tab === "audit" && (
        <DataTable
          data={auditData}
          columns={auditColumns}
          serverPagination={{ pageIndex: page - 1, pageCount: Math.ceil(total / 25), onPageChange: (p) => setPage(p + 1) }}
        />
      )}
      {tab === "errors" && (
        <DataTable
          data={errorData}
          columns={errorColumns}
          serverPagination={{ pageIndex: page - 1, pageCount: Math.ceil(total / 25), onPageChange: (p) => setPage(p + 1) }}
        />
      )}
    </div>
  );
}
