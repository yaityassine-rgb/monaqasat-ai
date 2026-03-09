// Supabase Edge Function: Create Paddle/LemonSqueezy Checkout Session
// Handles subscription checkout creation for both payment providers

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const PADDLE_API_KEY = Deno.env.get("PADDLE_API_KEY") || "";
const LEMONSQUEEZY_API_KEY = Deno.env.get("LEMONSQUEEZY_API_KEY") || "";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Paddle price IDs (configure in Paddle dashboard)
const PADDLE_PRICES: Record<string, { monthly: string; yearly: string }> = {
  starter: {
    monthly: Deno.env.get("PADDLE_STARTER_MONTHLY") || "",
    yearly: Deno.env.get("PADDLE_STARTER_YEARLY") || "",
  },
  professional: {
    monthly: Deno.env.get("PADDLE_PROFESSIONAL_MONTHLY") || "",
    yearly: Deno.env.get("PADDLE_PROFESSIONAL_YEARLY") || "",
  },
  business: {
    monthly: Deno.env.get("PADDLE_BUSINESS_MONTHLY") || "",
    yearly: Deno.env.get("PADDLE_BUSINESS_YEARLY") || "",
  },
};

// LemonSqueezy variant IDs
const LS_VARIANTS: Record<string, { monthly: string; yearly: string }> = {
  starter: {
    monthly: Deno.env.get("LS_STARTER_MONTHLY") || "",
    yearly: Deno.env.get("LS_STARTER_YEARLY") || "",
  },
  professional: {
    monthly: Deno.env.get("LS_PROFESSIONAL_MONTHLY") || "",
    yearly: Deno.env.get("LS_PROFESSIONAL_YEARLY") || "",
  },
  business: {
    monthly: Deno.env.get("LS_BUSINESS_MONTHLY") || "",
    yearly: Deno.env.get("LS_BUSINESS_YEARLY") || "",
  },
};

async function createPaddleCheckout(
  email: string,
  priceId: string,
  userId: string,
  successUrl: string
): Promise<string> {
  const response = await fetch("https://api.paddle.com/transactions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${PADDLE_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      items: [{ price_id: priceId, quantity: 1 }],
      customer: { email },
      custom_data: { user_id: userId },
      checkout: {
        url: successUrl,
      },
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Paddle error: ${err}`);
  }

  const data = await response.json();
  return data.data.checkout.url;
}

async function createLemonSqueezyCheckout(
  email: string,
  variantId: string,
  userId: string,
  successUrl: string
): Promise<string> {
  const storeId = Deno.env.get("LS_STORE_ID") || "";

  const response = await fetch("https://api.lemonsqueezy.com/v1/checkouts", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${LEMONSQUEEZY_API_KEY}`,
      "Content-Type": "application/vnd.api+json",
      "Accept": "application/vnd.api+json",
    },
    body: JSON.stringify({
      data: {
        type: "checkouts",
        attributes: {
          checkout_data: {
            email,
            custom: { user_id: userId },
          },
          product_options: {
            redirect_url: successUrl,
          },
        },
        relationships: {
          store: { data: { type: "stores", id: storeId } },
          variant: { data: { type: "variants", id: variantId } },
        },
      },
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`LemonSqueezy error: ${err}`);
  }

  const data = await response.json();
  return data.data.attributes.url;
}

Deno.serve(async (req: Request) => {
  try {
    const { userId, tier, interval, provider = "paddle", successUrl } = await req.json();

    if (!userId || !tier || !interval) {
      return new Response(JSON.stringify({ error: "Missing required fields" }), { status: 400 });
    }

    // Get user email
    const { data: { user } } = await supabase.auth.admin.getUserById(userId);
    if (!user?.email) {
      return new Response(JSON.stringify({ error: "User not found" }), { status: 404 });
    }

    let checkoutUrl: string;

    if (provider === "paddle") {
      const priceId = PADDLE_PRICES[tier]?.[interval as "monthly" | "yearly"];
      if (!priceId) throw new Error(`No Paddle price for ${tier}/${interval}`);
      checkoutUrl = await createPaddleCheckout(user.email, priceId, userId, successUrl);
    } else {
      const variantId = LS_VARIANTS[tier]?.[interval as "monthly" | "yearly"];
      if (!variantId) throw new Error(`No LS variant for ${tier}/${interval}`);
      checkoutUrl = await createLemonSqueezyCheckout(user.email, variantId, userId, successUrl);
    }

    return new Response(JSON.stringify({ url: checkoutUrl }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
