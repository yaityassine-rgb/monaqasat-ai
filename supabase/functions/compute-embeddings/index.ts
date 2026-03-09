// Supabase Edge Function: Compute embeddings via Gemini
// Triggered after tender upload or profile update

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function getEmbedding(text: string): Promise<number[]> {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "models/text-embedding-004",
        content: { parts: [{ text }] },
        taskType: "SEMANTIC_SIMILARITY",
      }),
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Gemini embedding error: ${err}`);
  }

  const data = await response.json();
  return data.embedding.values;
}

Deno.serve(async (req: Request) => {
  try {
    const { type, id, batchSize = 50 } = await req.json();

    if (type === "tender") {
      // Embed a single tender
      const { data: tender } = await supabase
        .from("tenders")
        .select("id, title_en, title_ar, description_en, description_ar, sector, country")
        .eq("id", id)
        .single();

      if (!tender) return new Response(JSON.stringify({ error: "Tender not found" }), { status: 404 });

      const text = [
        tender.title_en, tender.title_ar,
        tender.description_en, tender.description_ar,
        tender.sector, tender.country,
      ].filter(Boolean).join(" ").slice(0, 2000);

      const embedding = await getEmbedding(text);

      await supabase
        .from("tenders")
        .update({ embedding: `[${embedding.join(",")}]` })
        .eq("id", id);

      return new Response(JSON.stringify({ success: true, id }));
    }

    if (type === "profile") {
      // Embed a user's company profile
      const { data: profile } = await supabase
        .from("company_profiles")
        .select("*")
        .eq("id", id)
        .single();

      if (!profile) return new Response(JSON.stringify({ error: "Profile not found" }), { status: 404 });

      const text = [
        profile.company_name,
        profile.primary_sector,
        profile.description,
        profile.certifications,
        (profile.target_countries || []).join(", "),
      ].filter(Boolean).join(" ").slice(0, 2000);

      const embedding = await getEmbedding(text);

      await supabase
        .from("company_profiles")
        .update({ embedding: `[${embedding.join(",")}]` })
        .eq("id", id);

      return new Response(JSON.stringify({ success: true, id }));
    }

    if (type === "batch_tenders") {
      // Embed tenders that don't have embeddings yet
      const { data: tenders } = await supabase
        .from("tenders")
        .select("id, title_en, title_ar, description_en, description_ar, sector, country")
        .is("embedding", null)
        .limit(batchSize);

      if (!tenders || tenders.length === 0) {
        return new Response(JSON.stringify({ success: true, processed: 0 }));
      }

      let processed = 0;
      for (const tender of tenders) {
        const text = [
          tender.title_en, tender.title_ar,
          tender.description_en, tender.description_ar,
          tender.sector, tender.country,
        ].filter(Boolean).join(" ").slice(0, 2000);

        try {
          const embedding = await getEmbedding(text);
          await supabase
            .from("tenders")
            .update({ embedding: `[${embedding.join(",")}]` })
            .eq("id", tender.id);
          processed++;
        } catch (e) {
          console.error(`Failed to embed tender ${tender.id}:`, e);
        }

        // Rate limit: ~300 RPM for Gemini free tier
        if (processed % 10 === 0) {
          await new Promise((r) => setTimeout(r, 2000));
        }
      }

      return new Response(JSON.stringify({ success: true, processed }));
    }

    return new Response(JSON.stringify({ error: "Invalid type" }), { status: 400 });
  } catch (err) {
    return new Response(JSON.stringify({ error: (err as Error).message }), { status: 500 });
  }
});
