import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Users, CreditCard, Database, Activity, Coins, HeartPulse,
  Play, Upload, UserPlus, Download, AlertCircle, Stethoscope,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from "recharts";
import { useLang, localizedPath } from "../../lib/use-lang";
import { adminApi } from "../../lib/admin-api";
import { scraperApi } from "../../lib/scraper-api";
import StatCard from "../../components/admin/StatCard";
import ActivityFeed from "../../components/admin/ActivityFeed";
import type { UserStats, DataCounts, ActivityEvent } from "../../lib/admin-types";

const PIE_COLORS = ["#6366f1", "#818cf8", "#f59e0b", "#10b981", "#ef4444"];

export default function AdminOverviewPage() {
  const navigate = useNavigate();
  const lang = useLang();
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [dataCounts, setDataCounts] = useState<DataCounts | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [health, setHealth] = useState<"up" | "down" | "loading">("loading");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [stats, counts, events] = await Promise.all([
        adminApi.getUserStats().catch(() => null),
        adminApi.getDataCounts().catch(() => null),
        adminApi.getRecentActivity(20).catch(() => []),
      ]);
      if (stats) setUserStats(stats);
      if (counts) setDataCounts(counts);
      setActivity(events);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    scraperApi.healthCheck().then(() => setHealth("up")).catch(() => setHealth("down"));
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load]);

  const totalRecords = dataCounts
    ? dataCounts.tenders + dataCounts.grants + dataCounts.ppp_projects + dataCounts.companies + dataCounts.market_intelligence + dataCounts.prequalification
    : 0;

  const tierData = userStats?.tier_distribution
    ? Object.entries(userStats.tier_distribution).map(([name, value]) => ({ name, value: value as number }))
    : [];

  const dataInventory = dataCounts
    ? [
        { name: "Tenders", count: dataCounts.tenders },
        { name: "Grants", count: dataCounts.grants },
        { name: "PPP", count: dataCounts.ppp_projects },
        { name: "Companies", count: dataCounts.companies },
        { name: "Market", count: dataCounts.market_intelligence },
        { name: "Pre-Qual", count: dataCounts.prequalification },
      ]
    : [];

  const quickActions = [
    { label: "Run All Scrapers", icon: Play, path: "/admin/scrapers" },
    { label: "Upload Data", icon: Upload, path: "/admin/scrapers" },
    { label: "Add Admin", icon: UserPlus, path: "/admin/users" },
    { label: "Export Users", icon: Download, path: "/admin/users" },
    { label: "View Errors", icon: AlertCircle, path: "/admin/logs" },
    { label: "Health Check", icon: Stethoscope, path: "/admin/settings" },
  ];

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
          {[...Array(6)].map((_, i) => <div key={i} className="h-28 rounded-xl bg-white/5" />)}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-80 rounded-xl bg-white/5" />
          <div className="h-80 rounded-xl bg-white/5" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-white">Command Center</h1>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          label="Total Users"
          value={userStats?.total_users ?? 0}
          icon={Users}
          trend={userStats ? { value: userStats.new_this_week, label: "this week" } : undefined}
          color="primary"
        />
        <StatCard
          label="Subscriptions"
          value={tierData.filter((t) => t.name !== "free").reduce((s, t) => s + t.value, 0)}
          icon={CreditCard}
          color="success"
        />
        <StatCard
          label="Total Records"
          value={totalRecords.toLocaleString()}
          icon={Database}
          color="accent"
        />
        <StatCard
          label="Scrapers"
          value="18"
          icon={Activity}
          color="primary"
        />
        <StatCard
          label="AI Credits"
          value={dataCounts?.usage_events ?? 0}
          icon={Coins}
          color="warning"
        />
        <StatCard
          label="System Health"
          value={health === "loading" ? "..." : health === "up" ? "Online" : "Offline"}
          icon={HeartPulse}
          color={health === "up" ? "success" : health === "down" ? "danger" : "primary"}
        />
      </div>

      {/* Activity + Quick Actions */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass-card rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">Recent Activity</h2>
          <div className="max-h-72 overflow-y-auto">
            <ActivityFeed events={activity} />
          </div>
        </div>
        <div className="glass-card rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {quickActions.map((action) => (
              <button
                key={action.label}
                onClick={() => navigate(localizedPath(lang, action.path))}
                className="flex flex-col items-center gap-2 rounded-lg border border-dark-border p-4 text-slate-400 transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-white"
              >
                <action.icon className="h-5 w-5" />
                <span className="text-xs">{action.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass-card rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">Data Inventory</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={dataInventory} layout="vertical" margin={{ left: 60 }}>
              <XAxis type="number" tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} width={60} />
              <Tooltip
                contentStyle={{ background: "#0a0a0f", border: "1px solid #1a1a2e", borderRadius: 8, color: "#e2e8f0" }}
              />
              <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="glass-card rounded-xl p-5">
          <h2 className="mb-4 text-sm font-semibold text-white">Subscription Distribution</h2>
          {tierData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={tierData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {tierData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#0a0a0f", border: "1px solid #1a1a2e", borderRadius: 8, color: "#e2e8f0" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[250px] items-center justify-center text-sm text-slate-600">No subscription data</div>
          )}
        </div>
      </div>

      {/* User Growth */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">User Growth (Last 30 Days)</h2>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={[
            { day: "Week 1", users: Math.max(1, (userStats?.total_users ?? 0) - (userStats?.new_this_month ?? 0)) },
            { day: "Week 2", users: Math.max(1, (userStats?.total_users ?? 0) - Math.floor((userStats?.new_this_month ?? 0) * 0.66)) },
            { day: "Week 3", users: Math.max(1, (userStats?.total_users ?? 0) - Math.floor((userStats?.new_this_month ?? 0) * 0.33)) },
            { day: "Week 4", users: userStats?.total_users ?? 0 },
          ]}>
            <defs>
              <linearGradient id="userGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="day" tick={{ fill: "#64748b", fontSize: 12 }} />
            <YAxis tick={{ fill: "#64748b", fontSize: 12 }} />
            <Tooltip contentStyle={{ background: "#0a0a0f", border: "1px solid #1a1a2e", borderRadius: 8, color: "#e2e8f0" }} />
            <Area type="monotone" dataKey="users" stroke="#6366f1" fill="url(#userGradient)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
