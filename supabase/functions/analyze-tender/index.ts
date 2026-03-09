// Supabase Edge Function: AI Tender Analysis via Gemini
// Analyzes a tender against a user's company profile

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

Deno.serve(async (req: Request) => {
  try {
    const { tenderId, userId } = await req.json();

    if (!tenderId || !userId) {
      return new Response(JSON.stringify({ error: "Missing tenderId or userId" }), { status: 400 });
    }

    // Check for cached analysis
    const { data: cached } = await supabase
      .from("tender_analyses")
      .select("result")
      .eq("tender_id", tenderId)
      .eq("user_id", userId)
      .eq("analysis_type", "full")
      .single();

    if (cached) {
      return new Response(JSON.stringify(cached.result));
    }

    // Fetch tender and profile
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

    const prompt = `You are an expert procurement analyst specializing in MENA government tenders.

Analyze the following tender against the company profile and return a JSON object with this exact structure:
{
  "summary": "2-3 sentence executive summary of the tender",
  "keyRequirements": ["requirement 1", "requirement 2", ...],
  "eligibilityAssessment": {
    "score": <0-100 integer>,
    "strengths": ["strength 1", ...],
    "gaps": ["gap 1", ...],
    "verdict": "ELIGIBLE" | "PARTIALLY_ELIGIBLE" | "NOT_ELIGIBLE"
  },
  "riskFactors": [{"risk": "description", "severity": "HIGH"|"MEDIUM"|"LOW", "mitigation": "suggestion"}],
  "estimatedCompetition": "HIGH" | "MEDIUM" | "LOW",
  "recommendedAction": "BID" | "CONSIDER" | "SKIP",
  "bidStrategy": "1-2 sentences on recommended approach"
}

TENDER:
Title (EN): ${tender.title_en}
Title (AR): ${tender.title_ar}
Organization: ${tender.organization_en}
Country: ${tender.country}
Sector: ${tender.sector}
Budget: ${tender.budget} ${tender.currency}
Deadline: ${tender.deadline}
Description: ${tender.description_en || tender.description_ar}
Requirements: ${(tender.requirements || []).join("; ")}
Source: ${tender.source}

COMPANY PROFILE:
${profileText}

Respond ONLY with the JSON object, no markdown or explanation.`;

    const resultText = await callGemini(prompt);
    const result = JSON.parse(resultText);

    // Cache the analysis
    await supabase.from("tender_analyses").upsert({
      tender_id: tenderId,
      user_id: userId,
      analysis_type: "full",
      result,
      model: "gemini-2.0-flash",
    });

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
