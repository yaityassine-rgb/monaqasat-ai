import { X } from "lucide-react";

interface BulkAction {
  label: string;
  icon?: React.ReactNode;
  variant?: "default" | "danger";
  onClick: () => void;
}

interface BulkActionBarProps {
  count: number;
  actions: BulkAction[];
  onClear: () => void;
}

export default function BulkActionBar({ count, actions, onClear }: BulkActionBarProps) {
  if (count === 0) return null;

  return (
    <div className="fixed inset-x-0 bottom-6 z-50 mx-auto flex w-fit items-center gap-3 rounded-xl glass border border-dark-border px-4 py-3 shadow-2xl shadow-black/40">
      <span className="text-sm font-medium text-white">
        {count} selected
      </span>
      <div className="h-4 w-px bg-dark-border" />
      {actions.map((action, i) => (
        <button
          key={i}
          onClick={action.onClick}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            action.variant === "danger"
              ? "text-danger hover:bg-danger/10"
              : "text-slate-300 hover:bg-white/5"
          }`}
        >
          {action.icon}
          {action.label}
        </button>
      ))}
      <button onClick={onClear} className="ms-1 rounded p-1 text-slate-500 hover:bg-white/5 hover:text-white">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
