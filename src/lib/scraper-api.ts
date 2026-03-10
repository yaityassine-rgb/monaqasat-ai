import type { ScraperInfo, ScraperJob } from "./admin-types";

const BASE_URL = import.meta.env.VITE_ORCHESTRATOR_URL || "http://localhost:8787";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Orchestrator error ${res.status}: ${body}`);
  }
  return res.json();
}

export const scraperApi = {
  listScrapers(): Promise<ScraperInfo[]> {
    return api("/api/scrapers");
  },

  scrapersStatus(): Promise<Record<string, ScraperInfo>> {
    return api("/api/scrapers/status");
  },

  runScraper(key: string): Promise<ScraperJob> {
    return api("/api/scrapers/run", {
      method: "POST",
      body: JSON.stringify({ scraper: key }),
    });
  },

  runAllScrapers(type?: string): Promise<{ jobs: ScraperJob[] }> {
    return api("/api/scrapers/run-all", {
      method: "POST",
      body: JSON.stringify({ type }),
    });
  },

  listRuns(limit = 50, type?: string): Promise<ScraperJob[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (type) params.set("type", type);
    return api(`/api/scrapers/runs?${params}`);
  },

  cancelRun(id: string): Promise<{ success: boolean }> {
    return api(`/api/scrapers/runs/${id}/cancel`, { method: "POST" });
  },

  scraperStats(): Promise<Record<string, { total_runs: number; total_records: number; avg_duration: number }>> {
    return api("/api/scrapers/stats");
  },

  triggerUpload(type?: string): Promise<{ success: boolean; message: string }> {
    return api("/api/scrapers/upload", {
      method: "POST",
      body: JSON.stringify({ type }),
    });
  },

  healthCheck(): Promise<{ status: string; uptime: number }> {
    return api("/api/health");
  },
};
