import type { Tender } from "./types";
import { MOCK_TENDERS } from "./mock-data";

let cachedTenders: Tender[] | null = null;
let loading = false;
let loadPromise: Promise<Tender[]> | null = null;

/**
 * Load tenders from the scraped data file.
 * Falls back to mock data if the file doesn't exist or fails.
 */
export async function loadTenders(): Promise<Tender[]> {
  if (cachedTenders) return cachedTenders;
  if (loadPromise) return loadPromise;

  loading = true;
  loadPromise = (async () => {
    try {
      const resp = await fetch("/data/tenders.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const raw: Tender[] = data.tenders || data;

      // Validate and normalize
      cachedTenders = raw
        .filter((t) => t.id && t.title)
        .map((t) => ({
          ...t,
          status: (["open", "closing-soon", "closed"].includes(t.status)
            ? t.status
            : "open") as Tender["status"],
          budget: typeof t.budget === "number" ? t.budget : 0,
          matchScore:
            typeof t.matchScore === "number" ? t.matchScore : 50,
          requirements: Array.isArray(t.requirements)
            ? t.requirements
            : [],
        }));

      return cachedTenders;
    } catch {
      // Fallback to mock data
      cachedTenders = MOCK_TENDERS;
      return cachedTenders;
    } finally {
      loading = false;
    }
  })();

  return loadPromise;
}

/** Synchronous getter — returns cached tenders or mock data. */
export function getTenders(): Tender[] {
  return cachedTenders || MOCK_TENDERS;
}

export function isLoading(): boolean {
  return loading;
}
