// Supabase Edge Function: Process Document for RAG
// Downloads file from Supabase Storage, extracts text, chunks, embeds via Gemini

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!;
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

const CHUNK_SIZE = 2000; // ~500 tokens
const CHUNK_OVERLAP = 200;
const EMBEDDING_BATCH_SIZE = 20;

function chunkText(text: string): { content: string; index: number }[] {
  const chunks: { content: string; index: number }[] = [];
  let start = 0;
  let index = 0;

  while (start < text.length) {
    let end = Math.min(start + CHUNK_SIZE, text.length);

    // Try to break at paragraph or sentence boundary
    if (end < text.length) {
      const lastParagraph = text.lastIndexOf("\n\n", end);
      if (lastParagraph > start + CHUNK_SIZE / 2) {
        end = lastParagraph;
      } else {
        const lastSentence = text.lastIndexOf(". ", end);
        if (lastSentence > start + CHUNK_SIZE / 2) {
          end = lastSentence + 1;
        }
      }
    }

    const content = text.slice(start, end).trim();
    if (content.length > 50) {
      chunks.push({ content, index });
      index++;
    }

    start = end - CHUNK_OVERLAP;
    if (start >= text.length) break;
  }

  return chunks;
}

async function embedTexts(texts: string[]): Promise<number[][]> {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key=${GEMINI_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requests: texts.map((text) => ({
          model: "models/text-embedding-004",
          content: { parts: [{ text }] },
        })),
      }),
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Gemini embedding error: ${err}`);
  }

  const data = await response.json();
  return data.embeddings.map((e: { values: number[] }) => e.values);
}

async function extractTextFromFile(
  fileBytes: Uint8Array,
  fileType: string
): Promise<string> {
  if (fileType === "txt") {
    return new TextDecoder().decode(fileBytes);
  }

  if (fileType === "pdf") {
    // Use Gemini to extract text from PDF (multimodal)
    const base64 = btoa(String.fromCharCode(...fileBytes));

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  inlineData: {
                    mimeType: "application/pdf",
                    data: base64,
                  },
                },
                {
                  text: "Extract ALL text content from this PDF document. Return the complete text exactly as it appears, preserving structure with paragraphs and line breaks. Include headers, body text, tables (as text), and any other textual content. Do not summarize or add commentary — just return the raw extracted text.",
                },
              ],
            },
          ],
          generationConfig: {
            temperature: 0,
            maxOutputTokens: 8192,
          },
        }),
      }
    );

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`PDF extraction error: ${err}`);
    }

    const data = await response.json();
    return data.candidates[0].content.parts[0].text;
  }

  // For DOCX, extract as best we can by looking for text patterns
  // (Deno Edge Functions don't support full DOCX parsing libraries well)
  if (fileType === "docx" || fileType === "doc") {
    // DOCX is a zip file, try to extract text content from XML
    // For simplicity, use Gemini multimodal if the file is small enough
    if (fileBytes.length < 10 * 1024 * 1024) {
      const base64 = btoa(String.fromCharCode(...fileBytes));

      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [
              {
                parts: [
                  {
                    inlineData: {
                      mimeType:
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                      data: base64,
                    },
                  },
                  {
                    text: "Extract ALL text content from this document. Return the complete text exactly as it appears, preserving structure. Do not summarize.",
                  },
                ],
              },
            ],
            generationConfig: {
              temperature: 0,
              maxOutputTokens: 8192,
            },
          }),
        }
      );

      if (!response.ok) {
        throw new Error("DOCX extraction failed via Gemini");
      }

      const data = await response.json();
      return data.candidates[0].content.parts[0].text;
    }

    throw new Error("DOCX file too large for processing");
  }

  throw new Error(`Unsupported file type: ${fileType}`);
}

Deno.serve(async (req: Request) => {
  try {
    const { documentId, userId, storagePath, fileType } = await req.json();

    if (!documentId || !userId || !storagePath) {
      return new Response(
        JSON.stringify({ error: "Missing required parameters" }),
        { status: 400 }
      );
    }

    // Update status to processing
    await supabase
      .from("user_documents")
      .update({ status: "processing" })
      .eq("id", documentId);

    // Download file from Supabase Storage
    const { data: fileData, error: downloadError } = await supabase.storage
      .from("documents")
      .download(storagePath);

    if (downloadError || !fileData) {
      await supabase
        .from("user_documents")
        .update({ status: "failed", error_message: "Failed to download file" })
        .eq("id", documentId);
      return new Response(
        JSON.stringify({ error: "Failed to download file" }),
        { status: 500 }
      );
    }

    // Extract text
    const fileBytes = new Uint8Array(await fileData.arrayBuffer());
    let extractedText: string;

    try {
      extractedText = await extractTextFromFile(fileBytes, fileType || "pdf");
    } catch (err) {
      await supabase
        .from("user_documents")
        .update({
          status: "failed",
          error_message: `Text extraction failed: ${(err as Error).message}`,
        })
        .eq("id", documentId);
      return new Response(
        JSON.stringify({ error: `Text extraction failed: ${(err as Error).message}` }),
        { status: 500 }
      );
    }

    if (!extractedText || extractedText.length < 50) {
      await supabase
        .from("user_documents")
        .update({
          status: "failed",
          error_message: "No text content found in document",
        })
        .eq("id", documentId);
      return new Response(
        JSON.stringify({ error: "No text content found" }),
        { status: 400 }
      );
    }

    // Chunk text
    const chunks = chunkText(extractedText);

    // Delete any existing chunks for this document
    await supabase
      .from("document_chunks")
      .delete()
      .eq("document_id", documentId);

    // Embed and store chunks in batches
    for (let i = 0; i < chunks.length; i += EMBEDDING_BATCH_SIZE) {
      const batch = chunks.slice(i, i + EMBEDDING_BATCH_SIZE);
      const texts = batch.map((c) => c.content);

      let embeddings: number[][];
      try {
        embeddings = await embedTexts(texts);
      } catch (err) {
        console.error(`Embedding batch ${i} failed:`, err);
        // Store chunks without embeddings
        embeddings = texts.map(() => []);
      }

      const rows = batch.map((chunk, j) => ({
        document_id: documentId,
        user_id: userId,
        chunk_index: chunk.index,
        content: chunk.content,
        token_count: Math.ceil(chunk.content.length / 4),
        embedding:
          embeddings[j] && embeddings[j].length > 0
            ? JSON.stringify(embeddings[j])
            : null,
      }));

      await supabase.from("document_chunks").insert(rows);

      // Rate limit
      if (i + EMBEDDING_BATCH_SIZE < chunks.length) {
        await new Promise((r) => setTimeout(r, 200));
      }
    }

    // Update document status
    await supabase
      .from("user_documents")
      .update({
        status: "ready",
        chunk_count: chunks.length,
        error_message: null,
      })
      .eq("id", documentId);

    return new Response(
      JSON.stringify({
        success: true,
        chunks: chunks.length,
        textLength: extractedText.length,
      }),
      { headers: { "Content-Type": "application/json" } }
    );
  } catch (err) {
    console.error("Process document error:", err);
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
