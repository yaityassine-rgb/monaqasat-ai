import { useState, useEffect, useCallback } from "react";
import { Play, Upload, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { type ColumnDef } from "@tanstack/react-table";
import { formatDistanceToNow } from "date-fns";
import { scraperApi } from "../../lib/scraper-api";
import ScraperCard from "../../components/admin/ScraperCard";
import DataTable from "../../components/admin/DataTable";
import type { ScraperInfo, ScraperJob } from "../../lib/admin-types";

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-slate-500/20 text-slate-300",
  running: "bg-primary/20 text-primary-light",
  completed: "bg-success/20 text-success",
  failed: "bg-danger/20 text-danger",
  cancelled: "bg-warning/20 text-warning",
};

const jobColumns: ColumnDef<ScraperJob, unknown>[] = [
  { accessorKey: "id", header: "ID", cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue()).slice(0, 8)}</span> },
  { accessorKey: "scraper_key", header: "Scraper" },
  { accessorKey: "scraper_type", header: "Type", cell: ({ getValue }) => <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs">{String(getValue())}</span> },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ getValue }) => {
      const s = String(getValue());
      return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGE[s] || ""}`}>{s}</span>;
    },
  },
  {
    accessorKey: "started_at",
    header: "Started",
    cell: ({ getValue }) => getValue() ? formatDistanceToNow(new Date(String(getValue())), { addSuffix: true }) : "-",
  },
  { accessorKey: "duration_seconds", header: "Duration", cell: ({ getValue }) => `${getValue()}s` },
  { accessorKey: "records_found", header: "Records" },
  { accessorKey: "triggered_by", header: "Triggered By" },
];

export default function ScraperManagementPage() {
  const [scrapers, setScrapers] = useState<ScraperInfo[]>([]);
  const [jobs, setJobs] = useState<ScraperJob[]>([]);
  const [health, setHealth] = useState<"up" | "down" | "checking">("checking");
  const [loading, setLoading] = useState(true);

  const hasRunning = jobs.some((j) => j.status === "running" || j.status === "pending");

  const load = useCallback(async () => {
    try {
      const [scraperList, jobList] = await Promise.all([
        scraperApi.listScrapers().catch(() => []),
        scraperApi.listRuns(100).catch(() => []),
      ]);
      setScrapers(scraperList);
      setJobs(jobList);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    scraperApi.healthCheck().then(() => setHealth("up")).catch(() => setHealth("down"));
  }, [load]);

  // Polling
  useEffect(() => {
    const interval = setInterval(load, hasRunning ? 5000 : 30000);
    return () => clearInterval(interval);
  }, [load, hasRunning]);

  async function runAll() {
    try {
      await scraperApi.runAllScrapers();
      toast.success("All scrapers started");
      load();
    } catch (e) {
      toast.error("Failed to start scrapers");
    }
  }

  async function uploadAll() {
    try {
      await scraperApi.triggerUpload();
      toast.success("Upload triggered");
    } catch (e) {
      toast.error("Upload failed");
    }
  }

  async function runOne(key: string) {
    try {
      await scraperApi.runScraper(key);
      toast.success(`Started: ${key}`);
      load();
    } catch (e) {
      toast.error(`Failed to start: ${key}`);
    }
  }

  // Group scrapers by type
  const grouped = scrapers.reduce<Record<string, ScraperInfo[]>>((acc, s) => {
    (acc[s.type] ||= []).push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Top bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white">Scraper Management</h1>
          <div className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${health === "up" ? "bg-success/10 text-success" : health === "down" ? "bg-danger/10 text-danger" : "bg-white/5 text-slate-500"}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${health === "up" ? "bg-success" : health === "down" ? "bg-danger" : "bg-slate-500"}`} />
            {health === "up" ? "Online" : health === "down" ? "Offline" : "Checking..."}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={runAll} className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark">
            <Play className="h-4 w-4" /> Run All
          </button>
          <button onClick={uploadAll} className="flex items-center gap-1.5 rounded-lg border border-dark-border px-4 py-2 text-sm text-slate-300 hover:bg-white/5">
            <Upload className="h-4 w-4" /> Upload All
          </button>
          <button onClick={load} className="rounded-lg border border-dark-border p-2 text-slate-400 hover:bg-white/5">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Scraper Grid */}
      {loading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          {[...Array(12)].map((_, i) => <div key={i} className="h-44 animate-pulse rounded-xl bg-white/5" />)}
        </div>
      ) : (
        Object.entries(grouped).map(([type, list]) => (
          <div key={type}>
            <h2 className="mb-3 text-sm font-semibold capitalize text-slate-400">{type}</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
              {list.map((s) => (
                <ScraperCard key={s.key} scraper={s} onRun={runOne} onHistory={() => {}} />
              ))}
            </div>
          </div>
        ))
      )}

      {/* Job History */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Job History</h2>
        <DataTable data={jobs} columns={jobColumns} pageSize={25} />
      </div>
    </div>
  );
}
