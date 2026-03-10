import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { type ColumnDef } from "@tanstack/react-table";
import { toast } from "sonner";
import { adminApi } from "../../lib/admin-api";
import DataTable from "../../components/admin/DataTable";
import ExportButton from "../../components/admin/ExportButton";
import ConfirmDialog from "../../components/admin/ConfirmDialog";
import { useLang, localizedPath } from "../../lib/use-lang";

const TABLE_MAP: Record<string, string> = {
  tenders: "tenders",
  grants: "grants",
  ppp: "ppp_projects",
  companies: "companies",
  market: "market_intelligence",
  prequalification: "prequalification_requirements",
};

const TAB_LABELS: Record<string, string> = {
  tenders: "Tenders",
  grants: "Grants",
  ppp: "PPP",
  companies: "Companies",
  market: "Market",
  prequalification: "Pre-Qualification",
};

function buildColumns(type: string): ColumnDef<Record<string, unknown>, unknown>[] {
  const base: ColumnDef<Record<string, unknown>, unknown>[] = [
    { accessorKey: "id", header: "ID", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 12)}</span> },
  ];

  if (type === "tenders") {
    base.push(
      { accessorKey: "title_en", header: "Title", cell: ({ getValue }) => <span className="max-w-xs truncate block">{String(getValue())}</span> },
      { accessorKey: "organization_en", header: "Organization" },
      { accessorKey: "country", header: "Country" },
      { accessorKey: "sector", header: "Sector" },
      { accessorKey: "budget", header: "Budget", cell: ({ getValue }) => Number(getValue()).toLocaleString() },
      { accessorKey: "status", header: "Status", cell: ({ getValue }) => <StatusBadge status={String(getValue())} /> },
      { accessorKey: "deadline", header: "Deadline" },
      { accessorKey: "source", header: "Source" },
    );
  } else if (type === "grants") {
    base.push(
      { accessorKey: "title", header: "Title", cell: ({ getValue }) => <span className="max-w-xs truncate block">{String(getValue())}</span> },
      { accessorKey: "source", header: "Source" },
      { accessorKey: "country", header: "Country" },
      { accessorKey: "sector", header: "Sector" },
      { accessorKey: "funding_amount", header: "Amount", cell: ({ getValue }) => Number(getValue()).toLocaleString() },
      { accessorKey: "status", header: "Status", cell: ({ getValue }) => <StatusBadge status={String(getValue())} /> },
    );
  } else if (type === "ppp") {
    base.push(
      { accessorKey: "name", header: "Name", cell: ({ getValue }) => <span className="max-w-xs truncate block">{String(getValue())}</span> },
      { accessorKey: "country", header: "Country" },
      { accessorKey: "sector", header: "Sector" },
      { accessorKey: "stage", header: "Stage", cell: ({ getValue }) => <StatusBadge status={String(getValue())} /> },
      { accessorKey: "investment_value", header: "Value", cell: ({ getValue }) => Number(getValue()).toLocaleString() },
    );
  } else if (type === "companies") {
    base.push(
      { accessorKey: "name", header: "Name" },
      { accessorKey: "country", header: "Country" },
      { accessorKey: "sector", header: "Sector" },
      { accessorKey: "company_size", header: "Size" },
    );
  } else {
    base.push(
      { accessorKey: "created_at", header: "Created", cell: ({ getValue }) => new Date(String(getValue())).toLocaleDateString() },
    );
  }

  return base;
}

function StatusBadge({ status }: { status: string }) {
  const color = status === "open" || status === "awarded" || status === "operational"
    ? "bg-success/20 text-success"
    : status === "closing-soon" || status === "closing_soon" || status === "tender"
    ? "bg-warning/20 text-warning"
    : status === "closed" || status === "cancelled" || status === "failed"
    ? "bg-danger/20 text-danger"
    : "bg-white/10 text-slate-300";
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>{status}</span>;
}

export default function DataExplorerPage() {
  const { type: urlType } = useParams<{ type?: string }>();
  const lang = useLang();
  const [activeType, setActiveType] = useState<string>(urlType || "tenders");
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [, setLoading] = useState(true);
  const [deleteIds, setDeleteIds] = useState<string[]>([]);

  const table = TABLE_MAP[activeType] || "tenders";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getData(table, page, 25);
      setData(res.data);
      setTotal(res.count);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [table, page]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (urlType) setActiveType(urlType); }, [urlType]);

  async function handleDelete() {
    try {
      await adminApi.deleteRecords(table, deleteIds);
      toast.success(`Deleted ${deleteIds.length} records`);
      setDeleteIds([]);
      load();
    } catch {
      toast.error("Delete failed");
    }
  }

  const columns = buildColumns(activeType);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-white">Data Explorer</h1>
        <ExportButton data={data} filename={activeType} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-dark-card p-1 overflow-x-auto">
        {Object.entries(TAB_LABELS).map(([key, label]) => (
          <Link
            key={key}
            to={localizedPath(lang, `/admin/data/${key}`)}
            onClick={() => { setActiveType(key); setPage(1); }}
            className={`rounded-md px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
              activeType === key ? "bg-primary/10 text-primary-light" : "text-slate-500 hover:text-white"
            }`}
          >
            {label}
          </Link>
        ))}
      </div>

      <DataTable
        data={data}
        columns={columns}
        selectable
        serverPagination={{
          pageIndex: page - 1,
          pageCount: Math.ceil(total / 25),
          onPageChange: (p) => setPage(p + 1),
        }}
      />

      <ConfirmDialog
        open={deleteIds.length > 0}
        title="Delete Records?"
        message={`This will permanently delete ${deleteIds.length} record(s). This cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteIds([])}
      />
    </div>
  );
}
