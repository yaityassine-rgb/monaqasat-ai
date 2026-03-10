-- ============================================================
-- Monaqasat AI — Admin Roles & Audit System
-- ============================================================

-- User roles table
CREATE TABLE IF NOT EXISTS user_roles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'superadmin')),
  granted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Admin audit log
CREATE TABLE IF NOT EXISTS admin_audit_log (
  id BIGSERIAL PRIMARY KEY,
  admin_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- AI credits tracking
CREATE TABLE IF NOT EXISTS ai_credits (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 10,
  lifetime_purchased INTEGER NOT NULL DEFAULT 0,
  lifetime_consumed INTEGER NOT NULL DEFAULT 0,
  last_reset_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Credit transactions
CREATE TABLE IF NOT EXISTS credit_transactions (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type TEXT NOT NULL CHECK (type IN ('grant', 'consume', 'purchase', 'refund', 'adjustment', 'monthly_reset')),
  amount INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  feature TEXT,
  reason TEXT,
  admin_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Scraper runs tracking (for admin visibility)
CREATE TABLE IF NOT EXISTS scraper_runs (
  id TEXT PRIMARY KEY,
  scraper_key TEXT NOT NULL,
  scraper_type TEXT NOT NULL DEFAULT 'tenders',
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  records_found INTEGER DEFAULT 0,
  duration_seconds NUMERIC DEFAULT 0,
  error_message TEXT,
  triggered_by TEXT DEFAULT 'system',
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_audit_log_admin ON admin_audit_log(admin_user_id);
CREATE INDEX idx_audit_log_date ON admin_audit_log(created_at);
CREATE INDEX idx_audit_log_action ON admin_audit_log(action);
CREATE INDEX idx_credit_tx_user ON credit_transactions(user_id);
CREATE INDEX idx_credit_tx_date ON credit_transactions(created_at);
CREATE INDEX idx_scraper_runs_key ON scraper_runs(scraper_key);
CREATE INDEX idx_scraper_runs_status ON scraper_runs(status);
CREATE INDEX idx_scraper_runs_date ON scraper_runs(started_at);

-- Updated_at triggers
CREATE TRIGGER trg_ai_credits_updated
  BEFORE UPDATE ON ai_credits
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- Helper function: is_admin()
-- ============================================================
CREATE OR REPLACE FUNCTION is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_roles
    WHERE user_id = auth.uid()
      AND role IN ('admin', 'superadmin')
  );
$$;

-- ============================================================
-- RPC: admin_get_user_stats()
-- ============================================================
CREATE OR REPLACE FUNCTION admin_get_user_stats()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result JSONB;
BEGIN
  IF NOT is_admin() THEN
    RAISE EXCEPTION 'Unauthorized';
  END IF;

  SELECT jsonb_build_object(
    'total_users', (SELECT count(*) FROM auth.users),
    'new_this_week', (SELECT count(*) FROM auth.users WHERE created_at >= now() - interval '7 days'),
    'new_this_month', (SELECT count(*) FROM auth.users WHERE created_at >= now() - interval '30 days'),
    'tier_distribution', (
      SELECT jsonb_object_agg(tier, cnt)
      FROM (
        SELECT COALESCE(s.tier, 'free') AS tier, count(*) AS cnt
        FROM auth.users u
        LEFT JOIN subscriptions s ON s.user_id = u.id AND s.status = 'active'
        GROUP BY COALESCE(s.tier, 'free')
      ) t
    )
  ) INTO result;

  RETURN result;
END;
$$;

-- ============================================================
-- RPC: admin_get_data_counts()
-- ============================================================
CREATE OR REPLACE FUNCTION admin_get_data_counts()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result JSONB;
BEGIN
  IF NOT is_admin() THEN
    RAISE EXCEPTION 'Unauthorized';
  END IF;

  SELECT jsonb_build_object(
    'tenders', (SELECT count(*) FROM tenders),
    'grants', (SELECT count(*) FROM grants),
    'ppp_projects', (SELECT count(*) FROM ppp_projects),
    'companies', (SELECT count(*) FROM companies),
    'market_intelligence', (SELECT count(*) FROM market_intelligence),
    'prequalification', (SELECT count(*) FROM prequalification_requirements),
    'saved_tenders', (SELECT count(*) FROM saved_tenders),
    'usage_events', (SELECT count(*) FROM usage_events),
    'subscriptions', (SELECT count(*) FROM subscriptions),
    'company_profiles', (SELECT count(*) FROM company_profiles),
    'tender_analyses', (SELECT count(*) FROM tender_analyses)
  ) INTO result;

  RETURN result;
END;
$$;

-- ============================================================
-- RLS for new tables
-- ============================================================

ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_runs ENABLE ROW LEVEL SECURITY;

-- user_roles: users can see their own, admins can see all
CREATE POLICY "Users can view own role"
  ON user_roles FOR SELECT
  TO authenticated
  USING (user_id = auth.uid() OR is_admin());

CREATE POLICY "Admins can manage roles"
  ON user_roles FOR ALL
  TO authenticated
  USING (is_admin());

-- admin_audit_log: admins only
CREATE POLICY "Admins can view audit log"
  ON admin_audit_log FOR SELECT
  TO authenticated
  USING (is_admin());

CREATE POLICY "Admins can insert audit log"
  ON admin_audit_log FOR INSERT
  TO authenticated
  WITH CHECK (is_admin());

-- ai_credits: users see own, admins see all
CREATE POLICY "Users can view own credits"
  ON ai_credits FOR SELECT
  TO authenticated
  USING (user_id = auth.uid() OR is_admin());

CREATE POLICY "Admins can manage credits"
  ON ai_credits FOR ALL
  TO authenticated
  USING (is_admin());

-- credit_transactions: users see own, admins see all
CREATE POLICY "Users can view own transactions"
  ON credit_transactions FOR SELECT
  TO authenticated
  USING (user_id = auth.uid() OR is_admin());

CREATE POLICY "Admins can manage transactions"
  ON credit_transactions FOR ALL
  TO authenticated
  USING (is_admin());

-- scraper_runs: admins only
CREATE POLICY "Admins can view scraper runs"
  ON scraper_runs FOR SELECT
  TO authenticated
  USING (is_admin());

CREATE POLICY "Admins can manage scraper runs"
  ON scraper_runs FOR ALL
  TO authenticated
  USING (is_admin());

-- ============================================================
-- Admin override policies on existing tables
-- ============================================================

-- company_profiles: admin can view all
CREATE POLICY "Admins can view all profiles"
  ON company_profiles FOR SELECT
  TO authenticated
  USING (is_admin());

CREATE POLICY "Admins can update all profiles"
  ON company_profiles FOR UPDATE
  TO authenticated
  USING (is_admin());

-- saved_tenders: admin can view all
CREATE POLICY "Admins can view all saved tenders"
  ON saved_tenders FOR SELECT
  TO authenticated
  USING (is_admin());

-- usage_events: admin can view all
CREATE POLICY "Admins can view all usage events"
  ON usage_events FOR SELECT
  TO authenticated
  USING (is_admin());

CREATE POLICY "Admins can manage usage events"
  ON usage_events FOR ALL
  TO authenticated
  USING (is_admin());

-- subscriptions: admin can view/manage all
CREATE POLICY "Admins can view all subscriptions"
  ON subscriptions FOR SELECT
  TO authenticated
  USING (is_admin());

CREATE POLICY "Admins can manage subscriptions"
  ON subscriptions FOR ALL
  TO authenticated
  USING (is_admin());

-- tender_analyses: admin can view all
CREATE POLICY "Admins can view all analyses"
  ON tender_analyses FOR SELECT
  TO authenticated
  USING (is_admin());

-- tenders: admin can manage (insert/update/delete)
CREATE POLICY "Admins can manage tenders"
  ON tenders FOR ALL
  TO authenticated
  USING (is_admin());

-- grants: admin can manage
CREATE POLICY "Admins can manage grants"
  ON grants FOR ALL
  TO authenticated
  USING (is_admin());

-- ppp_projects: admin can manage
CREATE POLICY "Admins can manage ppp_projects"
  ON ppp_projects FOR ALL
  TO authenticated
  USING (is_admin());

-- companies: admin can manage
CREATE POLICY "Admins can manage companies"
  ON companies FOR ALL
  TO authenticated
  USING (is_admin());

-- market_intelligence: admin can manage
CREATE POLICY "Admins can manage market_intelligence"
  ON market_intelligence FOR ALL
  TO authenticated
  USING (is_admin());

-- prequalification_requirements: admin can manage
CREATE POLICY "Admins can manage prequalification"
  ON prequalification_requirements FOR ALL
  TO authenticated
  USING (is_admin());
