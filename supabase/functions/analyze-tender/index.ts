// Supabase Edge Function: AI Tender Analysis via Gemini
// Two-layer caching:
//   1. Global tender analysis (summary, requirements, risks) — cached once per tender
//   2. Per-user eligibility assessment (strengths, gaps, score) — cached per user+tender

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
    throw new Error(`Gemini API error: ${err}`);
  }

  const data = await response.json();
  return data.candidates[0].content.parts[0].text;
}

interface GlobalAnalysis {
  summary: string;
  keyRequirements: string[];
  riskFactors: { risk: string; severity: string; mitigation: string }[];
  estimatedCompetition: string;
}

interface UserAnalysis {
  eligibilityAssessment: {
    score: number;
    strengths: string[];
    gaps: string[];
    verdict: string;
  };
  recommendedAction: string;
  bidStrategy: string;
}

async function getOrCreateGlobalAnalysis(tender: Record<string, unknown>): Promise<GlobalAnalysis> {
  // Check cache — global analysis has no user_id
  const { data: cached } = await supabase
    .from("tender_analyses")
    .select("result")
    .eq("tender_id", tender.id as string)
    .is("user_id", null)
    .eq("analysis_type", "global")
    .single();

  if (cached?.result) {
    return cached.result as GlobalAnalysis;
  }

  const prompt = `You are an expert procurement analyst specializing in MENA government tenders.

Analyze the following tender and return a JSON object with this exact structure:
{
  "summary": "2-3 sentence executive summary of the tender",
  "keyRequirements": ["requirement 1", "requirement 2", ...],
  "riskFactors": [{"risk": "description", "severity": "HIGH"|"MEDIUM"|"LOW", "mitigation": "suggestion"}],
  "estimatedCompetition": "HIGH" | "MEDIUM" | "LOW"
}

TENDER:
Title (EN): ${tender.title_en}
Title (AR): ${tender.title_ar}
Organization: ${tender.organization_en}
Country: ${tender.country_code}
Sector: ${tender.sector}
Budget: ${tender.budget} ${tender.currency}
Deadline: ${tender.deadline}
Description: ${(tender.description_en || tender.description_ar) as string}
Requirements: ${((tender.requirements as string[]) || []).join("; ")}
Source: ${tender.source}

Respond ONLY with the JSON object, no markdown or explanation.`;

  const resultText = await callGemini(prompt);
  const result = JSON.parse(resultText) as GlobalAnalysis;

  // Cache globally (no user_id)
  await supabase.from("tender_analyses").upsert({
    tender_id: tender.id,
    user_id: null,
    analysis_type: "global",
    result,
    model: "gemini-2.0-flash",
  });

  return result;
}

async function getOrCreateUserAnalysis(
  tender: Record<string, unknown>,
  userId: string,
  profileText: string,
  globalAnalysis: GlobalAnalysis
): Promise<UserAnalysis> {
  // Check cache — per-user analysis
  const { data: cached } = await supabase
    .from("tender_analyses")
    .select("result")
    .eq("tender_id", tender.id as string)
    .eq("user_id", userId)
    .eq("analysis_type", "eligibility")
    .single();

  if (cached?.result) {
    return cached.result as UserAnalysis;
  }

  const prompt = `You are an expert procurement analyst specializing in MENA government tenders.

Given the tender summary and the company profile below, assess eligibility and return a JSON object with this exact structure:
{
  "eligibilityAssessment": {
    "score": <0-100 integer>,
    "strengths": ["strength 1", ...],
    "gaps": ["gap 1", ...],
    "verdict": "ELIGIBLE" | "PARTIALLY_ELIGIBLE" | "NOT_ELIGIBLE"
  },
  "recommendedAction": "BID" | "CONSIDER" | "SKIP",
  "bidStrategy": "1-2 sentences on recommended approach"
}

TENDER SUMMARY:
${globalAnalysis.summary}

KEY REQUIREMENTS:
${globalAnalysis.keyRequirements.join("\n- ")}

TENDER DETAILS:
Title: ${tender.title_en || tender.title_ar}
Sector: ${tender.sector}
Budget: ${tender.budget} ${tender.currency}
Country: ${tender.country_code}

COMPANY PROFILE:
${profileText}

Respond ONLY with the JSON object, no markdown or explanation.`;

  const resultText = await callGemini(prompt);
  const result = JSON.parse(resultText) as UserAnalysis;

  // Cache per user
  await supabase.from("tender_analyses").upsert({
    tender_id: tender.id,
    user_id: userId,
    analysis_type: "eligibility",
    result,
    model: "gemini-2.0-flash",
  });

  return result;
}

Deno.serve(async (req: Request) => {
  try {
    const { tenderId, userId } = await req.json();

    if (!tenderId || !userId) {
      return new Response(JSON.stringify({ error: "Missing tenderId or userId" }), { status: 400 });
    }

    // Check for a full cached analysis first (legacy or pre-combined)
    const { data: fullCached } = await supabase
      .from("tender_analyses")
      .select("result")
      .eq("tender_id", tenderId)
      .eq("user_id", userId)
      .eq("analysis_type", "full")
      .single();

    if (fullCached?.result) {
      return new Response(JSON.stringify(fullCached.result), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Fetch tender and profile in parallel
    const [{ data: tender }, { data: profile }] = await Promise.all([
      supabase.from("tenders").select("*").eq("id", tenderId).single(),
      supabase.from("company_profiles").select("*").eq("id", userId).single(),
    ]);

    if (!tender) {
      return new Response(JSON.stringify({ error: "Tender not found" }), { status: 404 });
    }

    const profileText = profile
      ? `Company: ${profile.company_name}
Sector: ${profile.primary_sector}
Experience: ${profile.experience} years
Certifications: ${profile.certifications}
Target Countries: ${(profile.target_countries || []).join(", ")}
Description: ${profile.description}`
      : "No company profile provided.";

    // Step 1: Get or create global analysis (shared across all users)
    const globalAnalysis = await getOrCreateGlobalAnalysis(tender);

    // Step 2: Get or create per-user eligibility assessment
    const userAnalysis = await getOrCreateUserAnalysis(tender, userId, profileText, globalAnalysis);

    // Combine into full response
    const result = {
      ...globalAnalysis,
      ...userAnalysis,
    };

    // Log usage event
    await supabase.from("usage_events").insert({
      user_id: userId,
      event_type: "analysis",
      metadata: { tender_id: tenderId },
    });

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
