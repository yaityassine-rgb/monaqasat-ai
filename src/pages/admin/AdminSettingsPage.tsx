import { useState, useEffect } from "react";
import { Eye, EyeOff, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { scraperApi } from "../../lib/scraper-api";

export default function AdminSettingsPage() {
  const [orchestratorUrl, setOrchestratorUrl] = useState(import.meta.env.VITE_ORCHESTRATOR_URL || "http://localhost:8787");
  const [supabaseUrl] = useState(import.meta.env.VITE_SUPABASE_URL || "");
  const [anonKey] = useState(import.meta.env.VITE_SUPABASE_ANON_KEY || "");
  const [showKeys, setShowKeys] = useState(false);
  const [health, setHealth] = useState<"up" | "down" | "checking">("checking");
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [maintenanceMsg, setMaintenanceMsg] = useState("");

  useEffect(() => {
    checkHealth();
  }, []);

  async function checkHealth() {
    setHealth("checking");
    try {
      await scraperApi.healthCheck();
      setHealth("up");
    } catch {
      setHealth("down");
    }
  }

  function maskKey(key: string) {
    if (!key) return "";
    if (showKeys) return key;
    return key.slice(0, 12) + "..." + key.slice(-4);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      {/* Orchestrator */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Orchestrator</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">URL</label>
            <div className="flex gap-2">
              <input
                value={orchestratorUrl}
                onChange={(e) => setOrchestratorUrl(e.target.value)}
                className="flex-1 rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm text-white focus:border-primary/50 focus:outline-none"
              />
              <button onClick={checkHealth} className="flex items-center gap-1.5 rounded-lg border border-dark-border px-3 py-2 text-sm text-slate-400 hover:bg-white/5">
                <RefreshCw className="h-3.5 w-3.5" />
                Test
              </button>
            </div>
            <div className="mt-1.5 flex items-center gap-1.5 text-xs">
              <span className={`h-1.5 w-1.5 rounded-full ${health === "up" ? "bg-success" : health === "down" ? "bg-danger" : "bg-slate-500 animate-pulse"}`} />
              <span className={health === "up" ? "text-success" : health === "down" ? "text-danger" : "text-slate-500"}>
                {health === "up" ? "Connected" : health === "down" ? "Unreachable" : "Checking..."}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="glass-card rounded-xl p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">API Keys</h2>
          <button onClick={() => setShowKeys(!showKeys)} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-white">
            {showKeys ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            {showKeys ? "Hide" : "Show"}
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">Supabase URL</label>
            <div
              onClick={() => copyToClipboard(supabaseUrl)}
              className="cursor-pointer rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm font-mono text-slate-400 hover:border-primary/30"
            >
              {maskKey(supabaseUrl) || "Not configured"}
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Supabase Anon Key</label>
            <div
              onClick={() => copyToClipboard(anonKey)}
              className="cursor-pointer rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm font-mono text-slate-400 hover:border-primary/30"
            >
              {maskKey(anonKey) || "Not configured"}
            </div>
          </div>
        </div>
      </div>

      {/* Maintenance Mode */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Maintenance Mode</h2>
        <div className="space-y-3">
          <label className="flex cursor-pointer items-center gap-3">
            <div className={`relative h-6 w-11 rounded-full transition-colors ${maintenanceMode ? "bg-warning" : "bg-white/10"}`}>
              <input type="checkbox" className="sr-only" checked={maintenanceMode} onChange={(e) => setMaintenanceMode(e.target.checked)} />
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${maintenanceMode ? "translate-x-5" : "translate-x-0.5"}`} />
            </div>
            <span className="text-sm text-slate-300">Enable maintenance mode</span>
          </label>
          {maintenanceMode && (
            <input
              value={maintenanceMsg}
              onChange={(e) => setMaintenanceMsg(e.target.value)}
              placeholder="Custom maintenance message..."
              className="w-full rounded-lg border border-dark-border bg-dark-card px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-primary/50 focus:outline-none"
            />
          )}
        </div>
      </div>

      {/* Notifications */}
      <div className="glass-card rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Notifications</h2>
        <div className="space-y-2">
          {[
            "Scraper failure alerts",
            "New user signup",
            "Subscription changes",
            "Low credit warnings",
          ].map((label) => (
            <label key={label} className="flex cursor-pointer items-center gap-3 rounded-lg p-2 hover:bg-white/[0.02]">
              <input type="checkbox" className="accent-primary" defaultChecked />
              <span className="text-sm text-slate-300">{label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
