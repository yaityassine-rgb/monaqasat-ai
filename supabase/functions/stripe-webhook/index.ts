// Supabase Edge Function: Payment Webhook Handler
// Handles webhooks from both Paddle and LemonSqueezy

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { hmac } from "https://deno.land/x/hmac@v2.0.1/mod.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const PADDLE_WEBHOOK_SECRET = Deno.env.get("PADDLE_WEBHOOK_SECRET") || "";
const LS_WEBHOOK_SECRET = Deno.env.get("LS_WEBHOOK_SECRET") || "";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

function getTierFromPrice(priceOrVariantId: string): string {
  // Map price/variant IDs to tiers (configured via env vars)
  const mappings: Record<string, string> = {};
  for (const tier of ["starter", "professional", "business"]) {
    for (const interval of ["monthly", "yearly"]) {
      const paddleKey = `PADDLE_${tier.toUpperCase()}_${interval.toUpperCase()}`;
      const lsKey = `LS_${tier.toUpperCase()}_${interval.toUpperCase()}`;
      const paddleVal = Deno.env.get(paddleKey);
      const lsVal = Deno.env.get(lsKey);
      if (paddleVal) mappings[paddleVal] = tier;
      if (lsVal) mappings[lsVal] = tier;
    }
  }
  return mappings[priceOrVariantId] || "starter";
}

Deno.serve(async (req: Request) => {
  try {
    const body = await req.text();
    const url = new URL(req.url);
    const provider = url.searchParams.get("provider") || "paddle";

    if (provider === "paddle") {
      // Verify Paddle webhook signature
      const signature = req.headers.get("paddle-signature") || "";
      if (PADDLE_WEBHOOK_SECRET && !verifyPaddleSignature(body, signature, PADDLE_WEBHOOK_SECRET)) {
        return new Response("Invalid signature", { status: 401 });
      }

      const event = JSON.parse(body);
      const eventType = event.event_type;

      if (eventType === "subscription.created" || eventType === "subscription.updated") {
        const sub = event.data;
        const userId = sub.custom_data?.user_id;
        if (!userId) return new Response("No user_id", { status: 400 });

        const tier = getTierFromPrice(sub.items?.[0]?.price?.id || "");

        await supabase.from("subscriptions").upsert({
          id: sub.id,
          user_id: userId,
          tier,
          status: sub.status === "active" ? "active" : sub.status === "past_due" ? "past_due" : "cancelled",
          provider: "paddle",
          provider_customer_id: sub.customer_id,
          current_period_start: sub.current_billing_period?.starts_at,
          current_period_end: sub.current_billing_period?.ends_at,
          metadata: { paddle_data: sub },
        });
      }

      if (eventType === "subscription.canceled") {
        const sub = event.data;
        await supabase
          .from("subscriptions")
          .update({ status: "cancelled" })
          .eq("id", sub.id);
      }
    } else if (provider === "lemonsqueezy") {
      // Verify LemonSqueezy webhook signature
      const signature = req.headers.get("x-signature") || "";
      if (LS_WEBHOOK_SECRET) {
        const computed = hmac("sha256", LS_WEBHOOK_SECRET, body, "utf8", "hex");
        if (computed !== signature) {
          return new Response("Invalid signature", { status: 401 });
        }
      }

      const event = JSON.parse(body);
      const eventName = event.meta?.event_name;

      if (eventName === "subscription_created" || eventName === "subscription_updated") {
        const sub = event.data.attributes;
        const userId = event.meta?.custom_data?.user_id;
        if (!userId) return new Response("No user_id", { status: 400 });

        const tier = getTierFromPrice(sub.variant_id?.toString() || "");

        await supabase.from("subscriptions").upsert({
          id: event.data.id,
          user_id: userId,
          tier,
          status: sub.status === "active" ? "active" : sub.status === "past_due" ? "past_due" : "cancelled",
          provider: "lemonsqueezy",
          provider_customer_id: sub.customer_id?.toString(),
          current_period_start: sub.renews_at,
          current_period_end: sub.ends_at,
          metadata: { ls_data: sub },
        });
      }

      if (eventName === "subscription_cancelled" || eventName === "subscription_expired") {
        await supabase
          .from("subscriptions")
          .update({ status: "cancelled" })
          .eq("id", event.data.id);
      }
    }

    return new Response(JSON.stringify({ received: true }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("Webhook error:", err);
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500 }
    );
  }
});

function verifyPaddleSignature(body: string, signature: string, secret: string): boolean {
  try {
    const parts = signature.split(";");
    const tsStr = parts.find((p: string) => p.startsWith("ts="))?.split("=")[1];
    const h1 = parts.find((p: string) => p.startsWith("h1="))?.split("=")[1];
    if (!tsStr || !h1) return false;

    const payload = `${tsStr}:${body}`;
    const computed = hmac("sha256", secret, payload, "utf8", "hex");
    return computed === h1;
  } catch {
    return false;
  }
}
