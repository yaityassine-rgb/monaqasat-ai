import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Create client with user's JWT to check admin role
    const authHeader = req.headers.get("Authorization")!;
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseAnonKey = Deno.env.get("SUPABASE_ANON_KEY")!;
    const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

    // Verify caller is admin
    const userClient = createClient(supabaseUrl, supabaseAnonKey, {
      global: { headers: { Authorization: authHeader } },
    });

    const { data: { user } } = await userClient.auth.getUser();
    if (!user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), {
        status: 401,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const { data: roleData } = await userClient
      .from("user_roles")
      .select("role")
      .eq("user_id", user.id)
      .maybeSingle();

    const role = roleData?.role;
    if (role !== "admin" && role !== "superadmin") {
      return new Response(JSON.stringify({ error: "Forbidden — admin role required" }), {
        status: 403,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // Service role client for admin operations
    const adminClient = createClient(supabaseUrl, serviceRoleKey);

    const { action, userId, params, role: newRole } = await req.json();

    // ── LIST USERS ────────────────────────────────────
    if (action === "list") {
      const page = parseInt(params?.page || "1");
      const perPage = 25;
      const search = params?.search || "";

      const { data: { users }, error } = await adminClient.auth.admin.listUsers({
        page,
        perPage,
      });

      if (error) throw error;

      // Get roles, subscriptions, credits, and company profiles
      const userIds = users.map((u) => u.id);

      const [rolesRes, subsRes, creditsRes, profilesRes] = await Promise.all([
        adminClient.from("user_roles").select("*").in("user_id", userIds),
        adminClient.from("subscriptions").select("*").in("user_id", userIds).eq("status", "active"),
        adminClient.from("ai_credits").select("*").in("user_id", userIds),
        adminClient.from("company_profiles").select("user_id:id, company_name").in("id", userIds),
      ]);

      const roleMap = new Map((rolesRes.data || []).map((r) => [r.user_id, r.role]));
      const subMap = new Map((subsRes.data || []).map((s) => [s.user_id, s.tier]));
      const creditMap = new Map((creditsRes.data || []).map((c) => [c.user_id, c.balance]));
      const profileMap = new Map((profilesRes.data || []).map((p) => [p.user_id, p.company_name]));

      let enriched = users.map((u) => ({
        id: u.id,
        email: u.email,
        created_at: u.created_at,
        last_sign_in_at: u.last_sign_in_at,
        role: roleMap.get(u.id) || "user",
        tier: subMap.get(u.id) || "free",
        credits_balance: creditMap.get(u.id) ?? 0,
        company_name: profileMap.get(u.id) || "",
        status: u.banned_until ? "suspended" : "active",
      }));

      // Filter by search
      if (search) {
        const q = search.toLowerCase();
        enriched = enriched.filter((u) =>
          u.email?.toLowerCase().includes(q) || u.company_name?.toLowerCase().includes(q)
        );
      }

      return new Response(JSON.stringify({ users: enriched, total: enriched.length }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ── GET USER DETAIL ───────────────────────────────
    if (action === "detail") {
      const { data: { user: targetUser }, error } = await adminClient.auth.admin.getUserById(userId);
      if (error) throw error;

      const [roleRes, subRes, creditRes, profileRes, savedRes] = await Promise.all([
        adminClient.from("user_roles").select("*").eq("user_id", userId).maybeSingle(),
        adminClient.from("subscriptions").select("*").eq("user_id", userId).eq("status", "active").maybeSingle(),
        adminClient.from("ai_credits").select("*").eq("user_id", userId).maybeSingle(),
        adminClient.from("company_profiles").select("*").eq("id", userId).maybeSingle(),
        adminClient.from("saved_tenders").select("tender_id", { count: "exact" }).eq("user_id", userId),
      ]);

      return new Response(JSON.stringify({
        id: targetUser!.id,
        email: targetUser!.email,
        created_at: targetUser!.created_at,
        last_sign_in_at: targetUser!.last_sign_in_at,
        role: roleRes.data?.role || "user",
        tier: subRes.data?.tier || "free",
        credits_balance: creditRes.data?.balance ?? 0,
        company_name: profileRes.data?.company_name || "",
        status: targetUser!.banned_until ? "suspended" : "active",
        subscription: subRes.data,
        credits: creditRes.data,
        company: profileRes.data,
        saved_count: savedRes.count || 0,
      }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ── UPDATE ROLE ───────────────────────────────────
    if (action === "updateRole") {
      if (!["user", "admin", "superadmin"].includes(newRole)) {
        throw new Error("Invalid role");
      }
      // Only superadmin can grant superadmin
      if (newRole === "superadmin" && role !== "superadmin") {
        return new Response(JSON.stringify({ error: "Only superadmin can grant superadmin role" }), {
          status: 403,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      await adminClient.from("user_roles").upsert({
        user_id: userId,
        role: newRole,
        granted_by: user.id,
        granted_at: new Date().toISOString(),
      }, { onConflict: "user_id" });

      // Audit log
      await adminClient.from("admin_audit_log").insert({
        admin_user_id: user.id,
        action: "update_role",
        target_type: "user",
        target_id: userId,
        details: { new_role: newRole },
      });

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ── SUSPEND / ACTIVATE ────────────────────────────
    if (action === "suspend" || action === "activate") {
      if (action === "suspend") {
        await adminClient.auth.admin.updateUserById(userId, {
          ban_duration: "876000h", // ~100 years
        });
      } else {
        await adminClient.auth.admin.updateUserById(userId, {
          ban_duration: "none",
        });
      }

      await adminClient.from("admin_audit_log").insert({
        admin_user_id: user.id,
        action,
        target_type: "user",
        target_id: userId,
      });

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ── DELETE USER ───────────────────────────────────
    if (action === "delete") {
      if (role !== "superadmin") {
        return new Response(JSON.stringify({ error: "Only superadmin can delete users" }), {
          status: 403,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      await adminClient.auth.admin.deleteUser(userId);

      await adminClient.from("admin_audit_log").insert({
        admin_user_id: user.id,
        action: "delete_user",
        target_type: "user",
        target_id: userId,
      });

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ error: "Unknown action" }), {
      status: 400,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: (error as Error).message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
