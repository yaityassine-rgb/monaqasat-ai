// Supabase Edge Function: Send Smart Email Alerts
// Triggered daily after scraper run — finds new matching tenders for each user
// and sends personalized email digests via Resend

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") || "";
const FROM_EMAIL = Deno.env.get("ALERT_FROM_EMAIL") || "alerts@monaqasat.ai";
const APP_URL = Deno.env.get("APP_URL") || "https://monaqasat.ai";

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

interface MatchedTender {
  tender_id: string;
  similarity: number;
  title_en: string;
  title_ar: string;
  organization_en: string;
  country_code: string;
  sector: string;
  budget: number;
  currency: string;
  deadline: string;
}

async function sendEmail(to: string, subject: string, html: string): Promise<boolean> {
  if (!RESEND_API_KEY) {
    console.log(`[DRY RUN] Would send email to ${to}: ${subject}`);
    return true;
  }

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: FROM_EMAIL,
      to: [to],
      subject,
      html,
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    console.error(`Failed to send email to ${to}: ${err}`);
    return false;
  }

  return true;
}

function formatBudget(amount: number, currency: string): string {
  if (!amount || amount <= 0) return "Not disclosed";
  if (amount >= 1_000_000_000) return `${(amount / 1_000_000_000).toFixed(1)}B ${currency}`;
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M ${currency}`;
  if (amount >= 1_000) return `${(amount / 1_000).toFixed(0)}K ${currency}`;
  return `${amount.toLocaleString()} ${currency}`;
}

function buildEmailHtml(tenders: MatchedTender[], userName: string): string {
  const tenderRows = tenders.map((t) => `
    <tr style="border-bottom: 1px solid #2d3748;">
      <td style="padding: 16px 12px;">
        <a href="${APP_URL}/dashboard/tender/${t.tender_id}"
           style="color: #60a5fa; text-decoration: none; font-weight: 600; font-size: 14px;">
          ${t.title_en || t.title_ar}
        </a>
        <div style="color: #94a3b8; font-size: 12px; margin-top: 4px;">
          ${t.organization_en} — ${t.country_code}
        </div>
      </td>
      <td style="padding: 16px 12px; text-align: center;">
        <span style="display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 700;
          ${t.similarity >= 0.8 ? 'background: #065f4620; color: #34d399;' :
            t.similarity >= 0.6 ? 'background: #92400e20; color: #fbbf24;' :
              'background: #7f1d1d20; color: #f87171;'}">
          ${Math.round(t.similarity * 100)}%
        </span>
      </td>
      <td style="padding: 16px 12px; color: #e2e8f0; font-size: 13px;">
        ${formatBudget(t.budget, t.currency)}
      </td>
      <td style="padding: 16px 12px; color: #94a3b8; font-size: 13px;">
        ${t.deadline || "See portal"}
      </td>
    </tr>`).join("");

  return `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; background: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <div style="max-width: 640px; margin: 0 auto; padding: 32px 16px;">
    <!-- Header -->
    <div style="text-align: center; margin-bottom: 32px;">
      <div style="display: inline-block; background: #3b82f6; color: white; font-weight: 700; font-size: 20px; width: 40px; height: 40px; line-height: 40px; border-radius: 10px; margin-bottom: 12px;">M</div>
      <h1 style="color: white; font-size: 22px; margin: 8px 0 4px;">New Matching Tenders</h1>
      <p style="color: #94a3b8; font-size: 14px; margin: 0;">
        ${tenders.length} new tender${tenders.length > 1 ? 's' : ''} match your profile
      </p>
    </div>

    <!-- Greeting -->
    <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
      Hi${userName ? ` ${userName}` : ''},<br>
      We found <strong style="color: white;">${tenders.length} new tender${tenders.length > 1 ? 's' : ''}</strong>
      matching your company profile. Here are your top matches:
    </p>

    <!-- Tender Table -->
    <table style="width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; margin: 24px 0;">
      <thead>
        <tr style="background: #334155;">
          <th style="padding: 12px; text-align: start; color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Tender</th>
          <th style="padding: 12px; text-align: center; color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Match</th>
          <th style="padding: 12px; text-align: start; color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Budget</th>
          <th style="padding: 12px; text-align: start; color: #94a3b8; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Deadline</th>
        </tr>
      </thead>
      <tbody>
        ${tenderRows}
      </tbody>
    </table>

    <!-- CTA -->
    <div style="text-align: center; margin: 32px 0;">
      <a href="${APP_URL}/dashboard"
         style="display: inline-block; background: #3b82f6; color: white; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-weight: 600; font-size: 14px;">
        View All Matches in Dashboard
      </a>
    </div>

    <!-- Footer -->
    <div style="text-align: center; padding-top: 24px; border-top: 1px solid #1e293b;">
      <p style="color: #64748b; font-size: 12px; margin: 0;">
        Monaqasat AI — AI-Powered Procurement Intelligence for MENA
      </p>
      <p style="color: #475569; font-size: 11px; margin: 8px 0 0;">
        <a href="${APP_URL}/dashboard/alerts" style="color: #475569;">Manage alert preferences</a> ·
        <a href="${APP_URL}/dashboard/subscription" style="color: #475569;">Manage subscription</a>
      </p>
    </div>
  </div>
</body>
</html>`;
}

Deno.serve(async (req: Request) => {
  try {
    const body = await req.json().catch(() => ({}));
    const sinceHours = body.sinceHours || 24;
    const dryRun = body.dryRun || false;

    const since = new Date(Date.now() - sinceHours * 60 * 60 * 1000).toISOString();

    // Get all users with alerts enabled
    const { data: alertPrefs, error: prefsError } = await supabase
      .from("alert_preferences")
      .select("*")
      .eq("enabled", true);

    if (prefsError) throw prefsError;
    if (!alertPrefs || alertPrefs.length === 0) {
      return new Response(JSON.stringify({ message: "No users with alerts enabled", sent: 0 }));
    }

    let sent = 0;
    let failed = 0;
    let skipped = 0;

    for (const prefs of alertPrefs) {
      try {
        // Get user email
        const { data: { user } } = await supabase.auth.admin.getUserById(prefs.id);
        if (!user?.email) {
          skipped++;
          continue;
        }

        const email = prefs.email_override || user.email;
        const minScore = (prefs.min_match_score || 60) / 100;

        // Find new matching tenders
        const { data: matches, error: matchError } = await supabase.rpc(
          "get_new_matching_tenders",
          {
            p_user_id: prefs.id,
            p_since: since,
            p_min_score: minScore,
            p_sectors: prefs.sectors?.length ? prefs.sectors : [],
            p_countries: prefs.countries?.length ? prefs.countries : [],
            p_statuses: prefs.statuses?.length ? prefs.statuses : ["open", "closing-soon"],
            p_min_budget: prefs.min_budget || 0,
            p_limit: 20,
          }
        );

        if (matchError) {
          console.error(`Match error for user ${prefs.id}:`, matchError);
          failed++;
          continue;
        }

        if (!matches || matches.length === 0) {
          skipped++;
          continue;
        }

        const tenders = matches as MatchedTender[];

        // Get company name for greeting
        const { data: profile } = await supabase
          .from("company_profiles")
          .select("company_name")
          .eq("id", prefs.id)
          .single();

        const userName = profile?.company_name || "";

        // Build and send email
        const subject = `${tenders.length} new matching tender${tenders.length > 1 ? 's' : ''} — Monaqasat AI`;
        const html = buildEmailHtml(tenders, userName);

        let emailSent = false;
        if (!dryRun) {
          emailSent = await sendEmail(email, subject, html);
        } else {
          emailSent = true;
        }

        // Build score map for history
        const scoreMap: Record<string, number> = {};
        tenders.forEach((t) => { scoreMap[t.tender_id] = Math.round(t.similarity * 100); });

        // Log to alert_history
        await supabase.from("alert_history").insert({
          user_id: prefs.id,
          tender_ids: tenders.map((t) => t.tender_id),
          tender_count: tenders.length,
          match_scores: scoreMap,
          email_sent_to: email,
          status: emailSent ? "sent" : "failed",
          error_message: emailSent ? null : "Email send failed",
        });

        if (emailSent) {
          sent++;
        } else {
          failed++;
        }

        // Rate limit: don't spam Resend
        await new Promise((r) => setTimeout(r, 200));
      } catch (userErr) {
        console.error(`Alert error for user ${prefs.id}:`, userErr);
        failed++;
      }
    }

    return new Response(JSON.stringify({
      message: `Alerts processed: ${sent} sent, ${failed} failed, ${skipped} skipped`,
      sent,
      failed,
      skipped,
      totalUsers: alertPrefs.length,
    }), {
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: (err as Error).message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
