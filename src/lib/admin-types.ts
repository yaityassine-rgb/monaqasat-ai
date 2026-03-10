export type AdminRole = "user" | "admin" | "superadmin";

export interface UserRole {
  user_id: string;
  role: AdminRole;
  granted_by: string | null;
  granted_at: string;
}

export interface AuditLogEntry {
  id: number;
  admin_user_id: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  last_sign_in_at: string | null;
  role: AdminRole;
  company_name?: string;
  tier?: string;
  credits_balance?: number;
  status?: "active" | "suspended";
}

export interface UserStats {
  total_users: number;
  new_this_week: number;
  new_this_month: number;
  tier_distribution: Record<string, number>;
}

export interface DataCounts {
  tenders: number;
  grants: number;
  ppp_projects: number;
  companies: number;
  market_intelligence: number;
  prequalification: number;
  saved_tenders: number;
  usage_events: number;
  subscriptions: number;
  company_profiles: number;
  tender_analyses: number;
}

export interface ScraperInfo {
  key: string;
  name: string;
  type: string;
  status: "idle" | "running" | "completed" | "failed";
  last_run?: string;
  records_found?: number;
  duration?: number;
}

export interface ScraperJob {
  id: string;
  scraper_key: string;
  scraper_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  records_found: number;
  duration_seconds: number;
  error_message?: string;
  triggered_by: string;
  started_at: string;
  completed_at?: string;
}

export interface CreditTransaction {
  id: number;
  user_id: string;
  type: "grant" | "consume" | "purchase" | "refund" | "adjustment" | "monthly_reset";
  amount: number;
  balance_after: number;
  feature?: string;
  reason?: string;
  admin_id?: string;
  created_at: string;
  user_email?: string;
}

export interface SubscriptionRecord {
  id: string;
  user_id: string;
  tier: string;
  status: string;
  provider: string;
  provider_customer_id?: string;
  current_period_start?: string;
  current_period_end?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  user_email?: string;
}

export type DataType = "tenders" | "grants" | "ppp" | "companies" | "market" | "prequalification";

export interface ActivityEvent {
  id: string;
  type: "scraper_run" | "user_signup" | "subscription" | "usage" | "admin_action";
  title: string;
  description: string;
  timestamp: string;
  icon?: string;
}
