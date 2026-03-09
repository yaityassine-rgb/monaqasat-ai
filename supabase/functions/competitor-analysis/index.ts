// Supabase Edge Function: Competitor Analysis
// Analyzes award data to build competitor landscape for a sector/country

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function callGemini(prompt: string): Promise<string> {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          responseMimeType: "application/json",
          temperature: 0.3,
          maxOutputTokens: 2048,
        },
      }),
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Gemini error: ${err}`);
  }

  const data = await response.json();
  return data.candidates[0].content.parts[0].text;
}

Deno.serve(async (req: Request) => {
  try {
    const { sector, countryCode, userId, tenderId } = await req.json();

    if (!userId) {
      return new Response(JSON.stringify({ error: "Missing userId" }), { status: 400 });
    }

    // Fetch award notices for the sector/country
    let query = supabase
      .from("award_notices")
      .select("*")
      .order("award_date", { ascending: false })
      .limit(100);

    if (sector) query = query.eq("sector", sector);
    if (countryCode) query = query.eq("country_code", countryCode);

    const { data: awards } = await query;

    // Aggregate competitor data from awards
    const competitorMap = new Map<
      string,
      {
        name: string;
        wins: number;
        totalValue: number;
        countries: Set<string>;
        sectors: Set<string>;
        avgAmount: number;
      }
    >();

    if (awards) {
      for (const award of awards) {
        if (!award.winner_name) continue;
        const name = award.winner_name.trim();
        const existing = competitorMap.get(name) || {
          name,
          wins: 0,
          totalValue: 0,
          countries: new Set<string>(),
          sectors: new Set<string>(),
          avgAmount: 0,
        };

        existing.wins += 1;
        existing.totalValue += Number(award.award_amount) || 0;
        if (award.country_code) existing.countries.add(award.country_code);
        if (award.sector) existing.sectors.add(award.sector);
        competitorMap.set(name, existing);
      }
    }

    // Convert to sorted array
    const competitors = Array.from(competitorMap.values())
      .map((c) => ({
        name: c.name,
        wins: c.wins,
        totalValue: c.totalValue,
        avgAmount: c.wins > 0 ? Math.round(c.totalValue / c.wins) : 0,
        countries: Array.from(c.countries),
        sectors: Array.from(c.sectors),
      }))
      .sort((a, b) => b.wins - a.wins)
      .slice(0, 20);

    // Market stats
    const totalAwards = awards?.length || 0;
    const totalValue = awards?.reduce(
      (sum, a) => sum + (Number(a.award_amount) || 0),
      0
    ) || 0;
    const avgAwardValue = totalAwards > 0 ? Math.round(totalValue / totalAwards) : 0;
    const uniqueWinners = competitorMap.size;

    // Get AI insights if we have enough data
    let aiInsights = null;
    if (competitors.length >= 3 && GEMINI_API_KEY) {
      try {
        const competitorSummary = competitors
          .slice(0, 10)
          .map(
            (c) =>
              `${c.name}: ${c.wins} wins, avg ${c.avgAmount} ${awards?.[0]?.currency || "USD"}`
          )
          .join("\n");

        const prompt = `You are a procurement intelligence analyst for the MENA region.

Given the following competitor data for ${sector || "all sectors"} in ${countryCode || "MENA"}, provide a JSON analysis:

TOP COMPETITORS:
${competitorSummary}

MARKET STATS:
Total awards: ${totalAwards}
Total value: ${totalValue}
Unique winners: ${uniqueWinners}

Return JSON:
{
  "marketConcentration": "HIGH" | "MODERATE" | "LOW",
  "dominantPlayers": ["name1", "name2"],
  "entryBarriers": "description of barriers to entry",
  "pricingTrend": "INCREASING" | "STABLE" | "DECREASING",
  "opportunities": ["opportunity 1", "opportunity 2"],
  "strategy": "recommended competitive strategy in 2-3 sentences"
}`;

        const resultText = await callGemini(prompt);
        aiInsights = JSON.parse(resultText);
      } catch (err) {
        console.error("AI insights failed:", err);
      }
    }

    // Log usage
    await supabase.from("usage_events").insert({
      user_id: userId,
      event_type: "competitor_analysis",
      metadata: { sector, country_code: countryCode, tender_id: tenderId },
    });

    return new Response(
      JSON.stringify({
        competitors,
        market: {
          totalAwards,
          totalValue,
          avgAwardValue,
          uniqueWinners,
        },
        aiInsights,
        sector,
        countryCode,
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
