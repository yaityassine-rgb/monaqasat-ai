import { useState, useEffect, useCallback } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { Coins, TrendingDown, Users, AlertTriangle } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { toast } from "sonner";
import { adminApi } from "../../lib/admin-api";
import StatCard from "../../components/admin/StatCard";
import DataTable from "../../components/admin/DataTable";
import ExportButton from "../../components/admin/ExportButton";
import type { CreditTransaction } from "../../lib/admin-types";

const TYPE_BADGE: Record<string, string> = {
  grant: "bg-success/20 text-success",
  consume: "bg-danger/20 text-danger",
  purchase: "bg-primary/20 text-primary-light",
  refund: "bg-warning/20 text-warning",
  adjustment: "bg-accent/20 text-accent",
  monthly_reset: "bg-blue-500/20 text-blue-400",
};

const columns: ColumnDef<CreditTransaction, unknown>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "user_id", header: "User", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> },
  { accessorKey: "type", header: "Type", cell: ({ getValue }) => { const t = String(getValue()); return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_BADGE[t] || ""}`}>{t}</span>; } },
  { accessorKey: "amount", header: "Amount", cell: ({ getValue }) => { const v = Number(getValue()); return <span className={v >= 0 ? "text-success" : "text-danger"}>{v >= 0 ? "+" : ""}{v}</span>; } },
  { accessorKey: "balance_after", header: "Balance" },
  { accessorKey: "feature", header: "Feature", cell: ({ getValue }) => getValue() || "-" },
  { accessorKey: "reason", header: "Reason", cell: ({ getValue }) => getValue() || "-" },
  { accessorKey: "created_at", header: "Date", cell: ({ getValue }) => new Date(String(getValue())).toLocaleDateString() },
];

export default function CreditsPage() {
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [, setLoading] = useState(true);

  // Manual adjustment state
  const [adjustUserId, setAdjustUserId] = useState("");
  const [adjustAmount, setAdjustAmount] = useState("");
  const [adjustReason, setAdjustReason] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await adminApi.getCreditTransactions(page);
      setTransactions(res.data);
      setTotal(res.count);
    } catch {
      toast.error("Failed to load transactions");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  async function handleAdjust() {
    if (!adjustUserId || !adjustAmount) {
      toast.error("User ID and amount are required");
      return;
    }
    try {
      await adminApi.adjustCredits(adjustUserId, Number(adjustAmount), adjustReason);
      toast.success("Credits adjusted");
      setAdjustUserId("");
      setAdjustAmount("");
      setAdjustReason("");
      load();
    } catch {
      toast.error("Failed to adjust credits");
    }
  }

  const consumed = transactions.filter((t) => t.type === "consume").reduce((s, t) => s + Math.abs(t.amount), 0);
  const issued = transactions.filter((t) => t.type === "grant" || t.type === "purchase").reduce((s, t) => s + t.amount, 0);

  // Group consumption by feature
  const byFeature: Record<string, number> = {};
  transactions.filter((t) => t.type === "consume" && t.feature).forEach((t) => {
    byFeature[t.feature!] = (byFeature[t.feature!] || 0) + Math.abs(t.amount);
  });
  const featureData = Object.entries(byFeature).map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-white">AI Credits</h1>
        <ExportButton data={transactions} filename="credit-transactions" />
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Credits Issued" value={issued} icon={Coins} color="success" />
        <StatCard label="Credits Consumed" value={consumed} icon={TrendingDown} color="danger" />
        <StatCard label="Transactions" value={total} icon={Users} color="primary" />
        <StatCard label="Avg Per Txn" value={total ? Math.round(consumed / total) : 0} icon={AlertTriangle} color="warning" />
      </div>

      {/* Chart */}
      {featureData.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">Consumption by Feature</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={featureData}>
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#0a0a0f", border: "1px solid #1a1a2e", borderRadius: 8, color: "#e2e8f0" }} />
              <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Manual adjustment */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Manual Credit Adjustment</h2>
        <div className="flex flex-wrap gap-3">
          <input
            value={adjustUserId}
            onChange={(e) => setAdjustUserId(e.target.value)}
            placeholder="User ID"
            className="rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-primary/50 focus:outline-none"
          />
          <input
            value={adjustAmount}
            onChange={(e) => setAdjustAmount(e.target.value)}
            placeholder="Amount (+/-)"
            type="number"
            className="w-28 rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-primary/50 focus:outline-none"
          />
          <input
            value={adjustReason}
            onChange={(e) => setAdjustReason(e.target.value)}
            placeholder="Reason"
            className="flex-1 rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-primary/50 focus:outline-none"
          />
          <button onClick={handleAdjust} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark">
            Apply
          </button>
        </div>
      </div>

      <DataTable
        data={transactions}
        columns={columns}
        serverPagination={{
          pageIndex: page - 1,
          pageCount: Math.ceil(total / 25),
          onPageChange: (p) => setPage(p + 1),
        }}
      />
    </div>
  );
}
