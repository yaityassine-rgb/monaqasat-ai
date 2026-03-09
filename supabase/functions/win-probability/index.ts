// Supabase Edge Function: Win Probability Calculator
// Rule-based scoring: eligibility + sector match + experience + certifications + history

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

interface ProbabilityBreakdown {
  factor: string;
  score: number; // 0-100
  weight: number;
  details: string;
}

Deno.serve(async (req: Request) => {
  try {
    const { tenderId, userId } = await req.json();

    if (!tenderId || !userId) {
      return new Response(JSON.stringify({ error: "Missing tenderId or userId" }), { status: 400 });
    }

    // Fetch tender, profile, analysis, and historical outcomes in parallel
    const [
      { data: tender },
      { data: profile },
      { data: analysis },
      { data: outcomes },
      { data: sectorAwards },
    ] = await Promise.all([
      supabase.from("tenders").select("*").eq("id", tenderId).single(),
      supabase.from("company_profiles").select("*").eq("id", userId).single(),
      supabase
        .from("tender_analyses")
        .select("result")
        .eq("tender_id", tenderId)
        .eq("user_id", userId)
        .in("analysis_type", ["full", "eligibility"])
        .limit(1)
        .single(),
      supabase
        .from("bid_outcomes")
        .select("outcome")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(50),
      supabase
        .from("award_notices")
        .select("award_amount, winner_country")
        .eq("sector", "")  // Will be filled below
        .limit(1), // Placeholder, actual query below
    ]);

    if (!tender) {
      return new Response(JSON.stringify({ error: "Tender not found" }), { status: 404 });
    }

    // Get actual sector awards
    const { data: awards } = await supabase
      .from("award_notices")
      .select("award_amount, winner_country, winner_name")
      .eq("sector", tender.sector)
      .eq("country_code", tender.country_code)
      .order("award_date", { ascending: false })
      .limit(20);

    const breakdown: ProbabilityBreakdown[] = [];

    // 1. Sector Match (weight: 25%)
    let sectorScore = 30; // base
    if (profile) {
      if (profile.primary_sector === tender.sector) {
        sectorScore = 95;
      } else if (
        (profile.additional_sectors || []).includes(tender.sector)
      ) {
        sectorScore = 75;
      }
    }
    breakdown.push({
      factor: "sector_match",
      score: sectorScore,
      weight: 0.25,
      details:
        sectorScore >= 90
          ? "Primary sector match"
          : sectorScore >= 70
            ? "Secondary sector match"
            : "No sector alignment",
    });

    // 2. Experience (weight: 20%)
    let experienceScore = 40;
    if (profile?.experience) {
      const years = Number(profile.experience);
      if (years >= 15) experienceScore = 95;
      else if (years >= 10) experienceScore = 85;
      else if (years >= 5) experienceScore = 70;
      else if (years >= 3) experienceScore = 55;
    }
    breakdown.push({
      factor: "experience",
      score: experienceScore,
      weight: 0.2,
      details: profile?.experience
        ? `${profile.experience} years of experience`
        : "No experience data",
    });

    // 3. Country Coverage (weight: 15%)
    let countryScore = 50;
    if (profile?.target_countries) {
      const countries = profile.target_countries as string[];
      if (countries.includes(tender.country_code)) {
        countryScore = 90;
      } else if (countries.length > 0) {
        countryScore = 40;
      }
    }
    breakdown.push({
      factor: "country_coverage",
      score: countryScore,
      weight: 0.15,
      details:
        countryScore >= 80
          ? "Target country match"
          : "Country not in target list",
    });

    // 4. Eligibility Score from AI Analysis (weight: 20%)
    let eligibilityScore = 50;
    if (analysis?.result) {
      const result = analysis.result as Record<string, unknown>;
      const eligibility = result.eligibilityAssessment as Record<string, unknown> | undefined;
      if (eligibility?.score) {
        eligibilityScore = Number(eligibility.score);
      }
    }
    breakdown.push({
      factor: "eligibility",
      score: eligibilityScore,
      weight: 0.2,
      details:
        eligibilityScore >= 80
          ? "Strong eligibility from AI analysis"
          : eligibilityScore >= 60
            ? "Moderate eligibility"
            : "Eligibility concerns identified",
    });

    // 5. Historical Win Rate (weight: 10%)
    let historyScore = 50; // neutral if no data
    if (outcomes && outcomes.length > 0) {
      const total = outcomes.length;
      const wins = outcomes.filter((o) => o.outcome === "won").length;
      historyScore = total > 0 ? Math.round((wins / total) * 100) : 50;
    }
    breakdown.push({
      factor: "historical_rate",
      score: historyScore,
      weight: 0.1,
      details:
        outcomes && outcomes.length > 0
          ? `Win rate: ${historyScore}% from ${outcomes.length} bids`
          : "No bid history yet",
    });

    // 6. Competition Level (weight: 10%)
    let competitionScore = 60;
    if (awards && awards.length > 0) {
      // More awards in the sector means more competition
      if (awards.length >= 15) competitionScore = 35;
      else if (awards.length >= 10) competitionScore = 45;
      else if (awards.length >= 5) competitionScore = 55;
      else competitionScore = 70;
    }
    // Budget alignment affects competition score
    if (tender.budget > 10_000_000) {
      competitionScore -= 10; // High-value tenders attract more competition
    }
    competitionScore = Math.max(10, Math.min(100, competitionScore));
    breakdown.push({
      factor: "competition",
      score: competitionScore,
      weight: 0.1,
      details:
        competitionScore >= 60
          ? "Lower competition expected"
          : "Competitive tender — expect multiple bidders",
    });

    // Calculate weighted probability
    const probability = Math.round(
      breakdown.reduce((sum, b) => sum + b.score * b.weight, 0)
    );

    // Determine verdict
    let verdict: string;
    if (probability >= 75) verdict = "HIGH";
    else if (probability >= 55) verdict = "MODERATE";
    else if (probability >= 35) verdict = "LOW";
    else verdict = "VERY_LOW";

    const result = {
      probability,
      verdict,
      breakdown,
      recommendation:
        probability >= 70
          ? "Strong candidate — prepare a thorough bid"
          : probability >= 50
            ? "Competitive opportunity — focus on differentiators"
            : probability >= 30
              ? "Consider carefully — address identified gaps before bidding"
              : "High risk — significant gaps to overcome",
    };

    return new Response(JSON.stringify(result), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
