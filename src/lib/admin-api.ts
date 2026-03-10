import { supabase } from "./supabase";
import type {
  AdminUser,
  UserStats,
  DataCounts,
  AuditLogEntry,
  CreditTransaction,
  SubscriptionRecord,
  ActivityEvent,
  AdminRole,
} from "./admin-types";

export const adminApi = {
  // ── User Stats (RPC) ──────────────────────────────────────
  async getUserStats(): Promise<UserStats> {
    const { data, error } = await supabase.rpc("admin_get_user_stats");
    if (error) throw error;
    return data as UserStats;
  },

  async getDataCounts(): Promise<DataCounts> {
    const { data, error } = await supabase.rpc("admin_get_data_counts");
    if (error) throw error;
    return data as DataCounts;
  },

  // ── Users (via edge function) ─────────────────────────────
  async getUsers(page = 1, search = "", filters: Record<string, string> = {}): Promise<{ users: AdminUser[]; total: number }> {
    const params = new URLSearchParams({ page: String(page), search, ...filters });
    const { data, error } = await supabase.functions.invoke("admin-users", {
      body: { action: "list", params: Object.fromEntries(params) },
    });
    if (error) throw error;
    return data;
  },

  async getUserDetail(id: string): Promise<AdminUser & { subscription?: SubscriptionRecord; credits?: { balance: number; lifetime_consumed: number }; company?: Record<string, unknown>; saved_count?: number }> {
    const { data, error } = await supabase.functions.invoke("admin-users", {
      body: { action: "detail", userId: id },
    });
    if (error) throw error;
    return data;
  },

  async updateUserRole(userId: string, role: AdminRole): Promise<void> {
    const { error } = await supabase.functions.invoke("admin-users", {
      body: { action: "updateRole", userId, role },
    });
    if (error) throw error;
  },

  async suspendUser(userId: string, suspend: boolean): Promise<void> {
    const { error } = await supabase.functions.invoke("admin-users", {
      body: { action: suspend ? "suspend" : "activate", userId },
    });
    if (error) throw error;
  },

  async deleteUser(userId: string): Promise<void> {
    const { error } = await supabase.functions.invoke("admin-users", {
      body: { action: "delete", userId },
    });
    if (error) throw error;
  },

  // ── Credits ───────────────────────────────────────────────
  async adjustCredits(userId: string, amount: number, reason: string): Promise<void> {
    const { data: current } = await supabase
      .from("ai_credits")
      .select("balance")
      .eq("user_id", userId)
      .maybeSingle();

    const newBalance = (current?.balance || 0) + amount;

    // Upsert credit balance
    await supabase.from("ai_credits").upsert({
      user_id: userId,
      balance: newBalance,
      lifetime_purchased: amount > 0 ? (current ? undefined : amount) : undefined,
      updated_at: new Date().toISOString(),
    }, { onConflict: "user_id" });

    // Log transaction
    const { data: { user } } = await supabase.auth.getUser();
    await supabase.from("credit_transactions").insert({
      user_id: userId,
      type: "adjustment",
      amount,
      balance_after: newBalance,
      reason,
      admin_id: user?.id,
    });
  },

  // ── Subscriptions ─────────────────────────────────────────
  async getSubscriptions(page = 1, limit = 25): Promise<{ data: SubscriptionRecord[]; count: number }> {
    const from = (page - 1) * limit;
    const { data, error, count } = await supabase
      .from("subscriptions")
      .select("*", { count: "exact" })
      .order("created_at", { ascending: false })
      .range(from, from + limit - 1);
    if (error) throw error;
    return { data: data || [], count: count || 0 };
  },

  // ── Credit Transactions ───────────────────────────────────
  async getCreditTransactions(page = 1, limit = 25): Promise<{ data: CreditTransaction[]; count: number }> {
    const from = (page - 1) * limit;
    const { data, error, count } = await supabase
      .from("credit_transactions")
      .select("*", { count: "exact" })
      .order("created_at", { ascending: false })
      .range(from, from + limit - 1);
    if (error) throw error;
    return { data: data || [], count: count || 0 };
  },

  // ── Audit Log ─────────────────────────────────────────────
  async getAuditLog(page = 1, limit = 25): Promise<{ data: AuditLogEntry[]; count: number }> {
    const from = (page - 1) * limit;
    const { data, error, count } = await supabase
      .from("admin_audit_log")
      .select("*", { count: "exact" })
      .order("created_at", { ascending: false })
      .range(from, from + limit - 1);
    if (error) throw error;
    return { data: data || [], count: count || 0 };
  },

  async logAuditAction(action: string, targetType?: string, targetId?: string, details?: Record<string, unknown>): Promise<void> {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;
    await supabase.from("admin_audit_log").insert({
      admin_user_id: user.id,
      action,
      target_type: targetType,
      target_id: targetId,
      details: details || {},
    });
  },

  // ── Usage Events ──────────────────────────────────────────
  async getUsageEvents(page = 1, limit = 25, eventType?: string): Promise<{ data: Array<Record<string, unknown>>; count: number }> {
    const from = (page - 1) * limit;
    let query = supabase
      .from("usage_events")
      .select("*", { count: "exact" })
      .order("created_at", { ascending: false })
      .range(from, from + limit - 1);
    if (eventType) query = query.eq("event_type", eventType);
    const { data, error, count } = await query;
    if (error) throw error;
    return { data: data || [], count: count || 0 };
  },

  // ── Recent Activity ───────────────────────────────────────
  async getRecentActivity(limit = 20): Promise<ActivityEvent[]> {
    const [usageRes, scraperRes] = await Promise.all([
      supabase.from("usage_events").select("*").order("created_at", { ascending: false }).limit(limit),
      supabase.from("scraper_runs").select("*").order("started_at", { ascending: false }).limit(limit),
    ]);

    const events: ActivityEvent[] = [];

    (usageRes.data || []).forEach((e) => {
      events.push({
        id: `usage-${e.id}`,
        type: "usage",
        title: e.event_type,
        description: `User event: ${e.event_type}`,
        timestamp: e.created_at,
      });
    });

    (scraperRes.data || []).forEach((r) => {
      events.push({
        id: `scraper-${r.id}`,
        type: "scraper_run",
        title: `Scraper: ${r.scraper_key}`,
        description: `${r.status} — ${r.records_found || 0} records`,
        timestamp: r.started_at || r.created_at,
      });
    });

    events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    return events.slice(0, limit);
  },

  // ── Data CRUD ─────────────────────────────────────────────
  async getData(table: string, page = 1, limit = 25, search = "", filters: Record<string, string> = {}): Promise<{ data: Record<string, unknown>[]; count: number }> {
    const from = (page - 1) * limit;
    let query = supabase.from(table).select("*", { count: "exact" }).range(from, from + limit - 1);

    if (search) {
      if (table === "tenders") query = query.or(`title_en.ilike.%${search}%,title_ar.ilike.%${search}%,organization_en.ilike.%${search}%`);
      else if (table === "grants") query = query.or(`title.ilike.%${search}%,funding_organization.ilike.%${search}%`);
      else if (table === "companies") query = query.or(`name.ilike.%${search}%,name_ar.ilike.%${search}%`);
      else if (table === "ppp_projects") query = query.or(`name.ilike.%${search}%,name_ar.ilike.%${search}%`);
    }

    for (const [key, value] of Object.entries(filters)) {
      if (value) query = query.eq(key, value);
    }

    query = query.order("created_at", { ascending: false });
    const { data, error, count } = await query;
    if (error) throw error;
    return { data: data || [], count: count || 0 };
  },

  async updateRecord(table: string, id: string, updates: Record<string, unknown>): Promise<void> {
    const { error } = await supabase.from(table).update(updates).eq("id", id);
    if (error) throw error;
  },

  async deleteRecords(table: string, ids: string[]): Promise<void> {
    const { error } = await supabase.from(table).delete().in("id", ids);
    if (error) throw error;
  },

  async insertRecord(table: string, record: Record<string, unknown>): Promise<void> {
    const { error } = await supabase.from(table).insert(record);
    if (error) throw error;
  },
};
