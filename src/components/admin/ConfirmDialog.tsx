import { AlertTriangle, X } from "lucide-react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "default";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({ open, title, message, confirmLabel = "Confirm", cancelLabel = "Cancel", variant = "default", onConfirm, onCancel }: ConfirmDialogProps) {
  if (!open) return null;

  const btnClass = variant === "danger"
    ? "bg-danger hover:bg-red-600"
    : variant === "warning"
    ? "bg-warning hover:bg-amber-600 text-black"
    : "bg-primary hover:bg-primary-dark";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-card mx-4 w-full max-w-md rounded-xl p-6">
        <div className="flex items-start gap-3">
          {variant !== "default" && (
            <div className={`rounded-lg p-2 ${variant === "danger" ? "bg-danger/10 text-danger" : "bg-warning/10 text-warning"}`}>
              <AlertTriangle className="h-5 w-5" />
            </div>
          )}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="mt-2 text-sm text-slate-400">{message}</p>
          </div>
          <button onClick={onCancel} className="text-slate-500 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={onCancel} className="rounded-lg px-4 py-2 text-sm text-slate-300 hover:bg-white/5">
            {cancelLabel}
          </button>
          <button onClick={onConfirm} className={`rounded-lg px-4 py-2 text-sm font-medium text-white ${btnClass}`}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
