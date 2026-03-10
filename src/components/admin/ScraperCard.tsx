import { formatDistanceToNow } from "date-fns";
import { Play, Clock, CheckCircle2, XCircle, Loader2, History } from "lucide-react";
import type { ScraperInfo } from "../../lib/admin-types";

interface ScraperCardProps {
  scraper: ScraperInfo;
  onRun: (key: string) => void;
  onHistory: (key: string) => void;
}

const statusConfig: Record<string, { icon: typeof Play; color: string; label: string }> = {
  idle: { icon: Clock, color: "text-slate-400 bg-white/5", label: "Idle" },
  running: { icon: Loader2, color: "text-primary-light bg-primary/10", label: "Running" },
  completed: { icon: CheckCircle2, color: "text-success bg-success/10", label: "Completed" },
  failed: { icon: XCircle, color: "text-danger bg-danger/10", label: "Failed" },
};

const typeBadgeColor: Record<string, string> = {
  tenders: "bg-primary/20 text-primary-light",
  grants: "bg-success/20 text-success",
  ppp: "bg-accent/20 text-accent",
  companies: "bg-blue-500/20 text-blue-400",
  market: "bg-purple-500/20 text-purple-400",
  prequalification: "bg-teal-500/20 text-teal-400",
};

export default function ScraperCard({ scraper, onRun, onHistory }: ScraperCardProps) {
  const { icon: StatusIcon, color, label } = statusConfig[scraper.status] || statusConfig.idle;
  const isRunning = scraper.status === "running";

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-white">{scraper.name}</h3>
          <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${typeBadgeColor[scraper.type] || "bg-white/10 text-slate-300"}`}>
            {scraper.type}
          </span>
        </div>
        <div className={`rounded-lg p-1.5 ${color}`}>
          <StatusIcon className={`h-4 w-4 ${isRunning ? "animate-spin" : ""}`} />
        </div>
      </div>

      <div className="mt-3 space-y-1 text-xs text-slate-500">
        <p>Status: <span className="text-slate-300">{label}</span></p>
        {scraper.last_run && (
          <p>Last run: <span className="text-slate-300">{formatDistanceToNow(new Date(scraper.last_run), { addSuffix: true })}</span></p>
        )}
        {scraper.records_found !== undefined && (
          <p>Records: <span className="text-slate-300">{scraper.records_found.toLocaleString()}</span></p>
        )}
        {scraper.duration !== undefined && (
          <p>Duration: <span className="text-slate-300">{scraper.duration}s</span></p>
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => onRun(scraper.key)}
          disabled={isRunning}
          className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary-light transition-colors hover:bg-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isRunning ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
          {isRunning ? "Running..." : "Run"}
        </button>
        <button
          onClick={() => onHistory(scraper.key)}
          className="flex items-center gap-1 rounded-lg border border-dark-border px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5 hover:text-white"
        >
          <History className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
