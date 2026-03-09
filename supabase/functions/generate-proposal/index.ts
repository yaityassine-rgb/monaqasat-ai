// Supabase Edge Function: AI Proposal Generator
// Generates multi-section bid proposals using RAG + Gemini
// Supports Arabic, English, and French

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

interface ProposalSection {
  key: string;
  title: string;
  content: string;
  status: "pending" | "generating" | "ready" | "error";
}

const SECTION_DEFINITIONS: Record<string, { title_en: string; title_ar: string; title_fr: string; prompt: string }> = {
  executive_summary: {
    title_en: "Executive Summary",
    title_ar: "الملخص التنفيذي",
    title_fr: "Résumé exécutif",
    prompt: "Write a compelling executive summary (300-500 words) for a bid proposal. Highlight the company's key value proposition, relevant experience, and why they are the ideal partner for this project. Be specific and persuasive.",
  },
  company_overview: {
    title_en: "Company Overview & Qualifications",
    title_ar: "نبذة عن الشركة والمؤهلات",
    title_fr: "Présentation de l'entreprise et qualifications",
    prompt: "Write a detailed company overview section (400-600 words) covering: company history, core competencies, relevant sector experience, key certifications, organizational structure, and quality management systems.",
  },
  technical_approach: {
    title_en: "Technical Approach & Methodology",
    title_ar: "النهج الفني والمنهجية",
    title_fr: "Approche technique et méthodologie",
    prompt: "Write a detailed technical approach section (500-800 words) covering: understanding of the project scope, proposed methodology, technical solutions, innovation elements, quality assurance measures, and how the approach addresses specific tender requirements.",
  },
  work_plan: {
    title_en: "Work Plan & Timeline",
    title_ar: "خطة العمل والجدول الزمني",
    title_fr: "Plan de travail et calendrier",
    prompt: "Write a work plan section (400-600 words) covering: project phases, key milestones, deliverables schedule, resource allocation plan, and a high-level timeline. Structure it as clear phases with estimated durations.",
  },
  team_qualifications: {
    title_en: "Team Qualifications",
    title_ar: "مؤهلات الفريق",
    title_fr: "Qualifications de l'équipe",
    prompt: "Write a team qualifications section (300-500 words) describing: proposed team structure, key personnel roles and experience, relevant project experience of team members, and training/certification highlights.",
  },
  compliance_matrix: {
    title_en: "Compliance Matrix",
    title_ar: "مصفوفة الامتثال",
    title_fr: "Matrice de conformité",
    prompt: "Write a compliance matrix section (300-500 words) addressing: how each tender requirement is met, relevant standards compliance (ISO, local regulations), health and safety measures, environmental compliance, and any applicable local content requirements.",
  },
  risk_management: {
    title_en: "Risk Management",
    title_ar: "إدارة المخاطر",
    title_fr: "Gestion des risques",
    prompt: "Write a risk management section (300-500 words) covering: identified project risks, risk assessment (likelihood and impact), mitigation strategies, contingency plans, and monitoring approach.",
  },
  pricing_schedule: {
    title_en: "Pricing Schedule",
    title_ar: "جدول التسعير",
    title_fr: "Grille tarifaire",
    prompt: "Write a pricing schedule introduction section (200-400 words) covering: pricing methodology, cost breakdown categories, value-for-money justification, and payment terms proposal. Note: Include placeholder tables for actual pricing figures to be filled in by the bidder.",
  },
};

const LANGUAGE_INSTRUCTIONS: Record<string, string> = {
  en: "Write in formal professional English suitable for government procurement documents.",
  ar: "اكتب بالعربية الفصحى الرسمية المناسبة لوثائق المشتريات الحكومية. استخدم المصطلحات التقنية والقانونية المناسبة.",
  fr: "Rédigez en français formel et professionnel, adapté aux documents de marchés publics.",
};

async function embedText(text: string): Promise<number[]> {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "models/text-embedding-004",
        content: { parts: [{ text }] },
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Embedding failed");
  }

  const data = await response.json();
  return data.embedding.values;
}

async function callGemini(prompt: string, maxTokens = 2048): Promise<string> {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.4,
          maxOutputTokens: maxTokens,
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

async function getRAGContext(userId: string, sectionPrompt: string): Promise<string> {
  try {
    const queryEmbedding = await embedText(sectionPrompt);

    const { data: chunks } = await supabase.rpc("search_document_chunks", {
      p_user_id: userId,
      p_query_embedding: JSON.stringify(queryEmbedding),
      p_limit: 5,
      p_min_similarity: 0.3,
    });

    if (!chunks || chunks.length === 0) return "";

    return chunks
      .map(
        (c: { content: string; file_name: string; similarity: number }) =>
          `[From: ${c.file_name} | Relevance: ${Math.round(c.similarity * 100)}%]\n${c.content}`
      )
      .join("\n\n---\n\n");
  } catch {
    return "";
  }
}

async function generateSection(
  sectionKey: string,
  language: string,
  tender: Record<string, unknown>,
  profile: Record<string, unknown> | null,
  ragContext: string
): Promise<string> {
  const sectionDef = SECTION_DEFINITIONS[sectionKey];
  if (!sectionDef) throw new Error(`Unknown section: ${sectionKey}`);

  const langInstruction = LANGUAGE_INSTRUCTIONS[language] || LANGUAGE_INSTRUCTIONS.en;

  const profileText = profile
    ? `Company: ${profile.company_name}
Sector: ${profile.primary_sector}
Experience: ${profile.experience} years
Certifications: ${profile.certifications}
Target Countries: ${((profile.target_countries as string[]) || []).join(", ")}
Description: ${profile.description}`
    : "No company profile available — use generic professional language.";

  const ragSection = ragContext
    ? `\n\nRELEVANT CONTENT FROM COMPANY'S PAST DOCUMENTS:\n${ragContext}\n\nUse the above reference material to inform the writing style, specific details, and evidence. Draw from the company's actual experience and past proposal language where relevant.`
    : "";

  const prompt = `You are an expert bid proposal writer specializing in MENA government procurement.

${langInstruction}

${sectionDef.prompt}

TENDER INFORMATION:
Title: ${tender.title_en || tender.title_ar}
Organization: ${tender.organization_en}
Country: ${tender.country_code}
Sector: ${tender.sector}
Budget: ${tender.budget} ${tender.currency}
Deadline: ${tender.deadline}
Description: ${(tender.description_en || tender.description_ar || "") as string}
Requirements: ${((tender.requirements as string[]) || []).join("; ")}

COMPANY PROFILE:
${profileText}
${ragSection}

Write the section content directly. Do not include the section title as a heading. Do not include any preamble or meta-commentary. Output only the section content.`;

  return await callGemini(prompt, 3000);
}

Deno.serve(async (req: Request) => {
  try {
    const body = await req.json();
    const {
      proposalId,
      tenderId,
      userId,
      language = "en",
      sections: requestedSections,
      mode = "full", // "full" | "single"
      sectionKey, // for single mode
    } = body;

    if (!userId) {
      return new Response(JSON.stringify({ error: "Missing userId" }), {
        status: 400,
      });
    }

    // Fetch tender and profile in parallel
    const [{ data: tender }, { data: profile }] = await Promise.all([
      tenderId
        ? supabase.from("tenders").select("*").eq("id", tenderId).single()
        : Promise.resolve({ data: null }),
      supabase.from("company_profiles").select("*").eq("id", userId).single(),
    ]);

    if (!tender && tenderId) {
      return new Response(JSON.stringify({ error: "Tender not found" }), {
        status: 404,
      });
    }

    // Use a generic tender object if no tender is linked
    const tenderData = tender || {
      title_en: "General Proposal",
      title_ar: "",
      organization_en: "N/A",
      country_code: "",
      sector: "",
      budget: 0,
      currency: "",
      deadline: "",
      description_en: "",
      requirements: [],
    };

    // Determine which sections to generate
    const sectionKeys =
      mode === "single" && sectionKey
        ? [sectionKey]
        : requestedSections ||
          Object.keys(SECTION_DEFINITIONS);

    // Create or update proposal record
    let currentProposalId = proposalId;

    if (!currentProposalId) {
      const titleKey = language === "ar" ? "title_ar" : "title_en";
      const { data: newProposal, error: createError } = await supabase
        .from("proposals")
        .insert({
          user_id: userId,
          tender_id: tenderId || null,
          title: `Proposal — ${(tenderData[titleKey] || tenderData.title_en || "Untitled") as string}`,
          language,
          status: "generating",
          sections: sectionKeys.map((key: string) => ({
            key,
            title:
              SECTION_DEFINITIONS[key]?.[
                `title_${language}` as keyof typeof SECTION_DEFINITIONS[string]
              ] || SECTION_DEFINITIONS[key]?.title_en || key,
            content: "",
            status: "pending",
          })),
        })
        .select("id")
        .single();

      if (createError) throw createError;
      currentProposalId = newProposal!.id;
    } else {
      await supabase
        .from("proposals")
        .update({ status: "generating" })
        .eq("id", currentProposalId);
    }

    // Generate each section
    const generatedSections: ProposalSection[] = [];

    for (const key of sectionKeys) {
      const sectionDef = SECTION_DEFINITIONS[key];
      if (!sectionDef) continue;

      const title =
        sectionDef[`title_${language}` as keyof typeof sectionDef] ||
        sectionDef.title_en;

      try {
        // Get RAG context for this section
        const ragContext = await getRAGContext(
          userId,
          `${sectionDef.prompt} ${(tenderData.title_en || tenderData.title_ar || "") as string} ${(tenderData.sector || "") as string}`
        );

        const content = await generateSection(
          key,
          language,
          tenderData,
          profile,
          ragContext
        );

        generatedSections.push({
          key,
          title: title as string,
          content,
          status: "ready",
        });
      } catch (err) {
        console.error(`Section ${key} failed:`, err);
        generatedSections.push({
          key,
          title: title as string,
          content: `Generation failed: ${(err as Error).message}`,
          status: "error",
        });
      }

      // Rate limit between sections
      await new Promise((r) => setTimeout(r, 300));
    }

    // Update proposal with generated sections
    if (mode === "single" && proposalId) {
      // Merge single section into existing sections
      const { data: existing } = await supabase
        .from("proposals")
        .select("sections")
        .eq("id", currentProposalId)
        .single();

      const existingSections = (existing?.sections as ProposalSection[]) || [];
      const updatedSections = existingSections.map((s) => {
        const generated = generatedSections.find((g) => g.key === s.key);
        return generated || s;
      });

      await supabase
        .from("proposals")
        .update({
          sections: updatedSections,
          status: "ready",
        })
        .eq("id", currentProposalId);
    } else {
      await supabase
        .from("proposals")
        .update({
          sections: generatedSections,
          status: "ready",
        })
        .eq("id", currentProposalId);
    }

    // Log usage
    await supabase.from("usage_events").insert({
      user_id: userId,
      event_type: "proposal",
      metadata: {
        proposal_id: currentProposalId,
        tender_id: tenderId,
        sections: sectionKeys.length,
        language,
      },
    });

    return new Response(
      JSON.stringify({
        proposalId: currentProposalId,
        sections: generatedSections,
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
