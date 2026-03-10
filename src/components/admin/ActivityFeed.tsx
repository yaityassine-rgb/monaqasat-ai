import { formatDistanceToNow } from "date-fns";
import { Activity, Database, User, CreditCard, Shield } from "lucide-react";
import type { ActivityEvent } from "../../lib/admin-types";

const iconMap: Record<string, typeof Activity> = {
  scraper_run: Database,
  user_signup: User,
  subscription: CreditCard,
  usage: Activity,
  admin_action: Shield,
};

const colorMap: Record<string, string> = {
  scraper_run: "text-primary-light bg-primary/10",
  user_signup: "text-success bg-success/10",
  subscription: "text-accent bg-accent/10",
  usage: "text-slate-400 bg-white/5",
  admin_action: "text-warning bg-warning/10",
};

interface ActivityFeedProps {
  events: ActivityEvent[];
  loading?: boolean;
}

export default function ActivityFeed({ events, loading }: ActivityFeedProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-3 animate-pulse">
            <div className="h-8 w-8 rounded-lg bg-white/5" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3 w-2/3 rounded bg-white/5" />
              <div className="h-2.5 w-1/3 rounded bg-white/5" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!events.length) {
    return <p className="text-sm text-slate-500">No recent activity</p>;
  }

  return (
    <div className="space-y-1">
      {events.map((event) => {
        const Icon = iconMap[event.type] || Activity;
        const color = colorMap[event.type] || "text-slate-400 bg-white/5";
        return (
          <div key={event.id} className="flex items-start gap-3 rounded-lg p-2 hover:bg-white/[0.02]">
            <div className={`mt-0.5 rounded-lg p-1.5 ${color}`}>
              <Icon className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm text-slate-200">{event.title}</p>
              <p className="truncate text-xs text-slate-500">{event.description}</p>
            </div>
            <span className="shrink-0 text-xs text-slate-600">
              {formatDistanceToNow(new Date(event.timestamp), { addSuffix: true })}
            </span>
          </div>
        );
      })}
    </div>
  );
}
