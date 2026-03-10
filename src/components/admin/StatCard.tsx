import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  trend?: { value: number; label: string };
  color?: "primary" | "success" | "warning" | "danger" | "accent";
}

const colorMap = {
  primary: "bg-primary/10 text-primary-light",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
  accent: "bg-accent/10 text-accent",
};

export default function StatCard({ label, value, icon: Icon, trend, color = "primary" }: StatCardProps) {
  return (
    <div className="glass-card rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mt-1 text-2xl font-bold text-white">{value}</p>
          {trend && (
            <p className={`mt-1 text-xs ${trend.value >= 0 ? "text-success" : "text-danger"}`}>
              {trend.value >= 0 ? "+" : ""}{trend.value} {trend.label}
            </p>
          )}
        </div>
        <div className={`rounded-lg p-2.5 ${colorMap[color]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
