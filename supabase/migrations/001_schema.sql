-- ============================================================
-- Monaqasat AI — Core Schema
-- ============================================================

-- Enable pgvector for embedding columns
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;

-- Company Profiles (one per user)
CREATE TABLE company_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  company_name TEXT NOT NULL DEFAULT '',
  primary_sector TEXT NOT NULL DEFAULT '',
  target_countries TEXT[] NOT NULL DEFAULT '{}',
  certifications TEXT NOT NULL DEFAULT '',
  experience INTEGER NOT NULL DEFAULT 0,
  description TEXT NOT NULL DEFAULT '',
  embedding VECTOR(768),  -- Gemini text-embedding-004 dimension
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tenders (scraped data)
CREATE TABLE tenders (
  id TEXT PRIMARY KEY,
  title_en TEXT NOT NULL DEFAULT '',
  title_ar TEXT NOT NULL DEFAULT '',
  title_fr TEXT NOT NULL DEFAULT '',
  organization_en TEXT NOT NULL DEFAULT '',
  organization_ar TEXT NOT NULL DEFAULT '',
  organization_fr TEXT NOT NULL DEFAULT '',
  country TEXT NOT NULL DEFAULT '',
  country_code TEXT NOT NULL DEFAULT '',
  sector TEXT NOT NULL DEFAULT '',
  budget NUMERIC NOT NULL DEFAULT 0,
  currency TEXT NOT NULL DEFAULT 'USD',
  deadline TEXT NOT NULL DEFAULT '',
  publish_date TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closing-soon', 'closed')),
  description_en TEXT NOT NULL DEFAULT '',
  description_ar TEXT NOT NULL DEFAULT '',
  description_fr TEXT NOT NULL DEFAULT '',
  requirements TEXT[] NOT NULL DEFAULT '{}',
  match_score INTEGER NOT NULL DEFAULT 50,
  source_language TEXT DEFAULT 'en',
  source_url TEXT DEFAULT '',
  source TEXT DEFAULT '',
  embedding VECTOR(768),  -- Gemini text-embedding-004 dimension
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Saved tenders (bookmarks per user)
CREATE TABLE saved_tenders (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tender_id TEXT NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, tender_id)
);

-- Usage events for analytics and tier enforcement
CREATE TABLE usage_events (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,  -- 'tender_view', 'analysis', 'proposal', etc.
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Subscriptions (synced from Paddle/LemonSqueezy)
CREATE TABLE subscriptions (
  id TEXT PRIMARY KEY,  -- Paddle/LS subscription ID
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'starter', 'professional', 'business')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'past_due', 'cancelled', 'expired')),
  provider TEXT NOT NULL DEFAULT 'paddle' CHECK (provider IN ('paddle', 'lemonsqueezy')),
  provider_customer_id TEXT,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tender analyses (cached AI analysis results)
CREATE TABLE tender_analyses (
  id BIGSERIAL PRIMARY KEY,
  tender_id TEXT NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  analysis_type TEXT NOT NULL DEFAULT 'full',  -- 'full', 'eligibility'
  result JSONB NOT NULL DEFAULT '{}',
  model TEXT NOT NULL DEFAULT 'gemini-2.0-flash',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tender_id, user_id, analysis_type)
);

-- Indexes
CREATE INDEX idx_tenders_sector ON tenders(sector);
CREATE INDEX idx_tenders_country ON tenders(country_code);
CREATE INDEX idx_tenders_status ON tenders(status);
CREATE INDEX idx_tenders_deadline ON tenders(deadline);
CREATE INDEX idx_saved_tenders_user ON saved_tenders(user_id);
CREATE INDEX idx_usage_events_user ON usage_events(user_id, event_type);
CREATE INDEX idx_usage_events_date ON usage_events(created_at);
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_analyses_tender ON tender_analyses(tender_id);

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_company_profiles_updated
  BEFORE UPDATE ON company_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_tenders_updated
  BEFORE UPDATE ON tenders
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_subscriptions_updated
  BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- Row Level Security
-- ============================================================

ALTER TABLE company_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_tenders ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tender_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenders ENABLE ROW LEVEL SECURITY;

-- Tenders: readable by all authenticated users
CREATE POLICY "Tenders are viewable by authenticated users"
  ON tenders FOR SELECT
  TO authenticated
  USING (true);

-- Company profiles: users can CRUD their own
CREATE POLICY "Users can view own profile"
  ON company_profiles FOR SELECT
  TO authenticated
  USING (id = auth.uid());

CREATE POLICY "Users can insert own profile"
  ON company_profiles FOR INSERT
  TO authenticated
  WITH CHECK (id = auth.uid());

CREATE POLICY "Users can update own profile"
  ON company_profiles FOR UPDATE
  TO authenticated
  USING (id = auth.uid());

-- Saved tenders: users manage their own
CREATE POLICY "Users can view own saved tenders"
  ON saved_tenders FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can save tenders"
  ON saved_tenders FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can unsave tenders"
  ON saved_tenders FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

-- Usage events: users see own events
CREATE POLICY "Users can view own usage"
  ON usage_events FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can log events"
  ON usage_events FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Subscriptions: users see own subscription
CREATE POLICY "Users can view own subscription"
  ON subscriptions FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

-- Analyses: users see own analyses
CREATE POLICY "Users can view own analyses"
  ON tender_analyses FOR SELECT
  TO authenticated
  USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can create analyses"
  ON tender_analyses FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());
