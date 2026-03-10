import { useState, useEffect, useCallback } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { DollarSign, Users, TrendingUp, BarChart3 } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { toast } from "sonner";
import { adminApi } from "../../lib/admin-api";
import StatCard from "../../components/admin/StatCard";
import DataTable from "../../components/admin/DataTable";
import ExportButton from "../../components/admin/ExportButton";
import type { SubscriptionRecord, UserStats } from "../../lib/admin-types";

const TIER_BADGE: Record<string, string> = {
  free: "bg-slate-500/20 text-slate-400",
  starter: "bg-blue-500/20 text-blue-400",
  professional: "bg-primary/20 text-primary-light",
  business: "bg-accent/20 text-accent",
  enterprise: "bg-success/20 text-success",
};

const STATUS_BADGE: Record<string, string> = {
  active: "bg-success/20 text-success",
  past_due: "bg-warning/20 text-warning",
  cancelled: "bg-danger/20 text-danger",
  expired: "bg-slate-500/20 text-slate-400",
};

const PIE_COLORS = ["#64748b", "#3b82f6", "#6366f1", "#f59e0b", "#10b981"];

const TIER_PRICES: Record<string, number> = { free: 0, starter: 49, professional: 149, business: 399, enterprise: 999 };

const columns: ColumnDef<SubscriptionRecord, unknown>[] = [
  { accessorKey: "id", header: "ID", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 10)}</span> },
  { accessorKey: "user_id", header: "User", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> },
  { accessorKey: "tier", header: "Tier", cell: ({ getValue }) => { const t = String(getValue()); return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TIER_BADGE[t] || ""}`}>{t}</span>; } },
  { accessorKey: "status", header: "Status", cell: ({ getValue }) => { const s = String(getValue()); return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[s] || ""}`}>{s}</span>; } },
  { accessorKey: "provider", header: "Provider" },
  { accessorKey: "current_period_end", header: "Renews", cell: ({ getValue }) => getValue() ? new Date(String(getValue())).toLocaleDateString() : "-" },
  { accessorKey: "created_at", header: "Created", cell: ({ getValue }) => new Date(String(getValue())).toLocaleDateString() },
];

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<SubscriptionRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [subRes, stats] = await Promise.all([
        adminApi.getSubscriptions(page),
        adminApi.getUserStats().catch(() => null),
      ]);
      setSubs(subRes.data);
      setTotal(subRes.count);
      if (stats) setUserStats(stats);
    } catch {
      toast.error("Failed to load subscriptions");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const tierDist = userStats?.tier_distribution
    ? Object.entries(userStats.tier_distribution).map(([name, value]) => ({ name, value: value as number }))
    : [];

  const activeSubs = subs.filter((s) => s.status === "active" && s.tier !== "free");
  const mrr = activeSubs.reduce((sum, s) => sum + (TIER_PRICES[s.tier] || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold text-white">Subscriptions</h1>
        <ExportButton data={subs} filename="subscriptions" />
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="MRR" value={`$${mrr.toLocaleString()}`} icon={DollarSign} color="success" />
        <StatCard label="ARR" value={`$${(mrr * 12).toLocaleString()}`} icon={TrendingUp} color="accent" />
        <StatCard label="Active Subscribers" value={activeSubs.length} icon={Users} color="primary" />
        <StatCard label="Total Users" value={userStats?.total_users ?? 0} icon={BarChart3} color="primary" />
      </div>

      {/* Tier chart */}
      {tierDist.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">Tier Distribution</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={tierDist} cx="50%" cy="50%" innerRadius={50} outerRadius={85} paddingAngle={3} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                {tierDist.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: "#0a0a0f", border: "1px solid #1a1a2e", borderRadius: 8, color: "#e2e8f0" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      <DataTable
        data={subs}
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
