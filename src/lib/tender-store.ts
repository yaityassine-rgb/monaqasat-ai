import type { Tender } from "./types";
import { MOCK_TENDERS } from "./mock-data";
import { supabase, isSupabaseConfigured } from "./supabase";

let cachedTenders: Tender[] | null = null;
let loading = false;
let loadPromise: Promise<Tender[]> | null = null;

/** Convert Supabase row to Tender object */
function rowToTender(row: Record<string, unknown>): Tender {
  return {
    id: row.id as string,
    title: {
      en: (row.title_en as string) || "",
      ar: (row.title_ar as string) || "",
      fr: (row.title_fr as string) || "",
    },
    organization: {
      en: (row.organization_en as string) || "",
      ar: (row.organization_ar as string) || "",
      fr: (row.organization_fr as string) || "",
    },
    country: (row.country as string) || "",
    countryCode: (row.country_code as string) || "",
    sector: (row.sector as string) || "",
    budget: Number(row.budget) || 0,
    currency: (row.currency as string) || "USD",
    deadline: (row.deadline as string) || "",
    publishDate: (row.publish_date as string) || "",
    status: (["open", "closing-soon", "closed"].includes(row.status as string)
      ? row.status
      : "open") as Tender["status"],
    description: {
      en: (row.description_en as string) || "",
      ar: (row.description_ar as string) || "",
      fr: (row.description_fr as string) || "",
    },
    requirements: Array.isArray(row.requirements) ? row.requirements as string[] : [],
    matchScore: Number(row.match_score) || 50,
    sourceLanguage: (row.source_language as "en" | "ar" | "fr") || "en",
    sourceUrl: (row.source_url as string) || "",
    source: (row.source as string) || "",
  };
}

/** Load tenders from Supabase, fallback to static JSON, then mock data */
export async function loadTenders(): Promise<Tender[]> {
  if (cachedTenders) return cachedTenders;
  if (loadPromise) return loadPromise;

  loading = true;
  loadPromise = (async () => {
    try {
      // Try Supabase first
      if (isSupabaseConfigured) {
        const { data, error } = await supabase
          .from("tenders")
          .select("*")
          .order("publish_date", { ascending: false });

        if (!error && data && data.length > 0) {
          cachedTenders = data.map(rowToTender);
          return cachedTenders;
        }
      }

      // Fallback to static JSON file
      const resp = await fetch("/data/tenders.json");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      const raw: Tender[] = json.tenders || json;

      cachedTenders = raw
        .filter((t) => t.id && t.title)
        .map((t) => ({
          ...t,
          status: (["open", "closing-soon", "closed"].includes(t.status)
            ? t.status
            : "open") as Tender["status"],
          budget: typeof t.budget === "number" ? t.budget : 0,
          matchScore: typeof t.matchScore === "number" ? t.matchScore : 50,
          requirements: Array.isArray(t.requirements) ? t.requirements : [],
        }));

      return cachedTenders;
    } catch {
      cachedTenders = MOCK_TENDERS;
      return cachedTenders;
    } finally {
      loading = false;
    }
  })();

  return loadPromise;
}

/** Load tenders with personalized match scores from pgvector */
export async function loadMatchedTenders(userId: string): Promise<Tender[]> {
  if (!isSupabaseConfigured) return loadTenders();

  try {
    // Get match scores via RPC
    const { data: matchData } = await supabase.rpc("match_tenders", {
      p_user_id: userId,
      p_match_count: 500,
    });

    // Build score map
    const scoreMap = new Map<string, number>();
    if (matchData) {
      for (const row of matchData) {
        scoreMap.set(row.id, Math.round(row.similarity * 100));
      }
    }

    // Load all tenders
    const tenders = await loadTenders();

    // Apply personalized scores
    return tenders.map((t) => ({
      ...t,
      matchScore: scoreMap.get(t.id) ?? t.matchScore,
    }));
  } catch {
    return loadTenders();
  }
}

/** Synchronous getter — returns cached tenders or mock data. */
export function getTenders(): Tender[] {
  return cachedTenders || MOCK_TENDERS;
}

export function isLoading(): boolean {
  return loading;
}

/** Clear cache to force reload */
export function clearCache() {
  cachedTenders = null;
  loadPromise = null;
}
