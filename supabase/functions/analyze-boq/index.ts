// Supabase Edge Function: BOQ (Bill of Quantities) Analysis
// Analyzes uploaded BOQ data via Gemini — flags pricing anomalies, missing items

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
          temperature: 0.2,
          maxOutputTokens: 4096,
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
    const { boqData, tenderId, userId, currency = "SAR" } = await req.json();

    if (!boqData || !userId) {
      return new Response(
        JSON.stringify({ error: "Missing boqData or userId" }),
        { status: 400 }
      );
    }

    // Check cache
    if (tenderId) {
      const { data: cached } = await supabase
        .from("tender_analyses")
        .select("result")
        .eq("tender_id", tenderId)
        .eq("user_id", userId)
        .eq("analysis_type", "boq")
        .single();

      if (cached?.result) {
        return new Response(JSON.stringify(cached.result), {
          headers: { "Content-Type": "application/json" },
        });
      }
    }

    const prompt = `You are an expert quantity surveyor and cost estimator specializing in MENA construction and government procurement projects.

Analyze the following Bill of Quantities (BOQ) data and return a JSON object with this structure:

{
  "summary": {
    "totalItems": <number>,
    "totalEstimatedValue": <number>,
    "currency": "${currency}",
    "overallAssessment": "COMPETITIVE" | "ABOVE_MARKET" | "BELOW_MARKET" | "MIXED"
  },
  "lineItemAnalysis": [
    {
      "item": "item description",
      "quantity": <number>,
      "unit": "unit",
      "unitPrice": <number>,
      "assessment": "FAIR" | "HIGH" | "LOW" | "MISSING_PRICE",
      "marketRange": {"low": <number>, "high": <number>},
      "notes": "explanation"
    }
  ],
  "anomalies": [
    {
      "type": "OVERPRICED" | "UNDERPRICED" | "MISSING_ITEM" | "UNUSUAL_QUANTITY" | "DUPLICATE",
      "description": "what's wrong",
      "severity": "HIGH" | "MEDIUM" | "LOW",
      "recommendation": "what to do"
    }
  ],
  "missingItems": [
    {
      "item": "suggested missing item",
      "reason": "why it should be included",
      "estimatedCost": <number or null>
    }
  ],
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ],
  "competitiveAdvantage": "brief strategy suggestion for pricing this BOQ competitively"
}

BOQ DATA:
${typeof boqData === "string" ? boqData : JSON.stringify(boqData, null, 2)}

Analyze each line item against typical market rates in the MENA region (Saudi Arabia / GCC focus). Flag any pricing anomalies, missing items that are commonly required, and provide actionable recommendations.

Respond ONLY with the JSON object.`;

    const resultText = await callGemini(prompt);
    const result = JSON.parse(resultText);

    // Cache if tender-linked
    if (tenderId) {
      await supabase.from("tender_analyses").upsert({
        tender_id: tenderId,
        user_id: userId,
        analysis_type: "boq",
        result,
        model: "gemini-2.0-flash",
      });
    }

    // Log usage
    await supabase.from("usage_events").insert({
      user_id: userId,
      event_type: "boq_analysis",
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
