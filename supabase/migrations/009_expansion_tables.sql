-- ============================================================
-- Monaqasat AI — Expansion Tables
-- Grants, PPP Projects, Companies, Pre-Qualification, Market Intel
-- ============================================================

-- Update subscriptions tier constraint to include enterprise
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_tier_check;
ALTER TABLE subscriptions ADD CONSTRAINT subscriptions_tier_check
  CHECK (tier IN ('free', 'starter', 'professional', 'business', 'enterprise'));

-- ============================================================
-- 1. Grants
-- ============================================================
CREATE TABLE IF NOT EXISTS grants (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  title_ar TEXT NOT NULL DEFAULT '',
  title_fr TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',           -- 'world_bank', 'afdb', 'isdb', 'eu_ted', 'ungm', 'ebrd', 'afesd', 'opec_fund'
  source_ref TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  funding_organization TEXT DEFAULT '',
  funding_organization_ar TEXT DEFAULT '',
  funding_organization_fr TEXT DEFAULT '',
  funding_amount NUMERIC DEFAULT 0,
  funding_amount_max NUMERIC DEFAULT 0,      -- range support
  currency TEXT DEFAULT 'USD',
  grant_type TEXT DEFAULT '',                -- 'project_grant', 'technical_assistance', 'capacity_building', 'research', 'emergency'
  country TEXT DEFAULT '',
  country_code TEXT DEFAULT '',
  region TEXT DEFAULT '',                    -- 'MENA', 'North Africa', 'Gulf', 'Levant'
  sector TEXT DEFAULT '',
  sectors TEXT[] DEFAULT '{}',               -- multiple sectors
  eligibility_criteria TEXT DEFAULT '',
  eligibility_countries TEXT[] DEFAULT '{}', -- which countries can apply
  description TEXT DEFAULT '',
  description_ar TEXT DEFAULT '',
  description_fr TEXT DEFAULT '',
  application_deadline TIMESTAMPTZ,
  publish_date TIMESTAMPTZ,
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closing_soon', 'closed', 'upcoming', 'awarded')),
  contact_info TEXT DEFAULT '',
  documents_url TEXT DEFAULT '',
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  embedding VECTOR(768),
  scraped_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_grants_source ON grants(source);
CREATE INDEX idx_grants_country ON grants(country_code);
CREATE INDEX idx_grants_sector ON grants(sector);
CREATE INDEX idx_grants_status ON grants(status);
CREATE INDEX idx_grants_deadline ON grants(application_deadline);
CREATE INDEX idx_grants_amount ON grants(funding_amount);
CREATE INDEX idx_grants_type ON grants(grant_type);

-- ============================================================
-- 2. PPP Projects
-- ============================================================
CREATE TABLE IF NOT EXISTS ppp_projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '',
  name_ar TEXT NOT NULL DEFAULT '',
  name_fr TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',           -- 'ppi_database', 'meed', 'national_ppp', 'infrappp'
  source_ref TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  country TEXT DEFAULT '',
  country_code TEXT DEFAULT '',
  region TEXT DEFAULT '',
  sector TEXT DEFAULT '',
  subsector TEXT DEFAULT '',
  stage TEXT DEFAULT 'planning' CHECK (stage IN ('identification', 'planning', 'feasibility', 'tender', 'shortlisted', 'awarded', 'construction', 'operational', 'cancelled')),
  contract_type TEXT DEFAULT '',             -- 'BOT', 'BOO', 'BOOT', 'BTO', 'concession', 'management', 'lease', 'divestiture'
  investment_value NUMERIC DEFAULT 0,
  debt_value NUMERIC DEFAULT 0,
  equity_value NUMERIC DEFAULT 0,
  currency TEXT DEFAULT 'USD',
  government_entity TEXT DEFAULT '',
  government_entity_ar TEXT DEFAULT '',
  government_entity_fr TEXT DEFAULT '',
  sponsors TEXT[] DEFAULT '{}',              -- private sector sponsors
  lenders TEXT[] DEFAULT '{}',               -- financial institutions
  advisors TEXT[] DEFAULT '{}',              -- legal/financial advisors
  description TEXT DEFAULT '',
  description_ar TEXT DEFAULT '',
  description_fr TEXT DEFAULT '',
  financial_close_date TIMESTAMPTZ,
  contract_duration_years INTEGER,
  tender_deadline TIMESTAMPTZ,
  award_date TIMESTAMPTZ,
  start_date TIMESTAMPTZ,
  completion_date TIMESTAMPTZ,
  risk_allocation JSONB DEFAULT '{}',       -- {'construction': 'private', 'demand': 'shared', ...}
  key_terms JSONB DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  embedding VECTOR(768),
  scraped_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ppp_country ON ppp_projects(country_code);
CREATE INDEX idx_ppp_sector ON ppp_projects(sector);
CREATE INDEX idx_ppp_stage ON ppp_projects(stage);
CREATE INDEX idx_ppp_source ON ppp_projects(source);
CREATE INDEX idx_ppp_value ON ppp_projects(investment_value);
CREATE INDEX idx_ppp_contract_type ON ppp_projects(contract_type);

-- ============================================================
-- 3. Companies (for JV Partner Matching)
-- ============================================================
CREATE TABLE IF NOT EXISTS companies (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '',
  name_ar TEXT NOT NULL DEFAULT '',
  name_fr TEXT NOT NULL DEFAULT '',
  legal_name TEXT DEFAULT '',
  source TEXT NOT NULL DEFAULT '',           -- 'opencorporates', 'etimad_vendors', 'dewa_vendors', 'chamber_commerce', 'manual'
  source_ref TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  country TEXT DEFAULT '',
  country_code TEXT DEFAULT '',
  city TEXT DEFAULT '',
  address TEXT DEFAULT '',
  website TEXT DEFAULT '',
  email TEXT DEFAULT '',
  phone TEXT DEFAULT '',
  sector TEXT DEFAULT '',
  sectors TEXT[] DEFAULT '{}',
  subsectors TEXT[] DEFAULT '{}',
  company_type TEXT DEFAULT '',              -- 'contractor', 'consultant', 'supplier', 'manufacturer', 'developer'
  company_size TEXT DEFAULT '',              -- 'micro', 'small', 'medium', 'large', 'enterprise'
  employee_count INTEGER,
  annual_revenue NUMERIC,
  revenue_currency TEXT DEFAULT 'USD',
  founded_year INTEGER,
  registration_number TEXT DEFAULT '',
  tax_id TEXT DEFAULT '',
  certifications TEXT[] DEFAULT '{}',        -- ['ISO 9001', 'ISO 14001', 'OHSAS 18001', ...]
  classifications TEXT[] DEFAULT '{}',       -- ISIC/UNSPSC codes
  prequalified_with TEXT[] DEFAULT '{}',     -- ['etimad', 'tejari', 'ashghal', ...]
  notable_projects TEXT[] DEFAULT '{}',
  jv_experience BOOLEAN DEFAULT false,
  international_presence TEXT[] DEFAULT '{}', -- country codes where active
  description TEXT DEFAULT '',
  description_ar TEXT DEFAULT '',
  description_fr TEXT DEFAULT '',
  financial_data JSONB DEFAULT '{}',         -- yearly revenue, assets, etc.
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  embedding VECTOR(768),
  verified BOOLEAN DEFAULT false,
  active BOOLEAN DEFAULT true,
  scraped_at TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_companies_country ON companies(country_code);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_sectors ON companies USING gin(sectors);
CREATE INDEX idx_companies_type ON companies(company_type);
CREATE INDEX idx_companies_size ON companies(company_size);
CREATE INDEX idx_companies_certs ON companies USING gin(certifications);
CREATE INDEX idx_companies_prequalified ON companies USING gin(prequalified_with);
CREATE INDEX idx_companies_source ON companies(source);
CREATE INDEX idx_companies_active ON companies(active);

-- ============================================================
-- 4. Pre-Qualification Requirements
-- ============================================================
CREATE TABLE IF NOT EXISTS prequalification_requirements (
  id TEXT PRIMARY KEY,
  country TEXT NOT NULL,
  country_code TEXT NOT NULL,
  portal_name TEXT NOT NULL DEFAULT '',
  portal_name_ar TEXT DEFAULT '',
  portal_name_fr TEXT DEFAULT '',
  portal_url TEXT DEFAULT '',
  registration_url TEXT DEFAULT '',
  authority_name TEXT DEFAULT '',
  authority_name_ar TEXT DEFAULT '',
  authority_name_fr TEXT DEFAULT '',
  -- Structured requirements
  required_documents JSONB DEFAULT '[]',     -- [{name, name_ar, name_fr, required, description, category}]
  certifications JSONB DEFAULT '[]',         -- [{name, issuing_authority, required, validity_period}]
  financial_requirements JSONB DEFAULT '{}', -- {min_capital, bank_guarantee, insurance, ...}
  technical_requirements JSONB DEFAULT '{}', -- {min_experience_years, min_projects, ...}
  legal_requirements JSONB DEFAULT '[]',     -- [{requirement, description}]
  -- Registration process
  registration_steps JSONB DEFAULT '[]',     -- [{step_number, title, title_ar, description, duration}]
  registration_fee NUMERIC DEFAULT 0,
  registration_fee_currency TEXT DEFAULT '',
  registration_validity TEXT DEFAULT '',     -- '1 year', '2 years', etc.
  renewal_process TEXT DEFAULT '',
  -- Timeline
  estimated_processing_days INTEGER,
  -- Categories/Classifications
  contractor_categories JSONB DEFAULT '[]',  -- [{category, description, requirements}]
  classification_system TEXT DEFAULT '',      -- 'ISIC', 'UNSPSC', 'custom'
  -- Additional info
  tips TEXT DEFAULT '',
  tips_ar TEXT DEFAULT '',
  tips_fr TEXT DEFAULT '',
  common_pitfalls TEXT DEFAULT '',
  helpful_links JSONB DEFAULT '[]',          -- [{title, url}]
  last_verified TIMESTAMPTZ,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_preq_country ON prequalification_requirements(country_code);

-- ============================================================
-- 5. Market Intelligence
-- ============================================================
CREATE TABLE IF NOT EXISTS market_intelligence (
  id TEXT PRIMARY KEY,
  country TEXT NOT NULL,
  country_code TEXT NOT NULL,
  year INTEGER NOT NULL,
  -- Economic indicators
  gdp_usd NUMERIC,                          -- in billions
  gdp_growth_pct NUMERIC,
  inflation_pct NUMERIC,
  population NUMERIC,                        -- in millions
  unemployment_pct NUMERIC,
  fdi_inflow_usd NUMERIC,                   -- in billions
  -- Construction & infrastructure
  construction_output_usd NUMERIC,           -- in billions
  construction_growth_pct NUMERIC,
  infrastructure_spend_usd NUMERIC,          -- in billions
  active_projects_count INTEGER,
  active_projects_value_usd NUMERIC,         -- in billions
  -- Business environment
  ease_of_business_rank INTEGER,
  ease_of_business_score NUMERIC,
  corruption_perception_index NUMERIC,
  government_effectiveness_score NUMERIC,
  -- Sector breakdown
  sector_breakdown JSONB DEFAULT '{}',       -- {construction: 30, energy: 25, ...} percentages
  top_sectors TEXT[] DEFAULT '{}',
  -- Trade & investment
  major_trading_partners TEXT[] DEFAULT '{}',
  bilateral_agreements TEXT[] DEFAULT '{}',
  free_trade_zones TEXT[] DEFAULT '{}',
  -- Key data
  currency_code TEXT DEFAULT '',
  currency_name TEXT DEFAULT '',
  exchange_rate_usd NUMERIC,
  -- Qualitative
  market_summary TEXT DEFAULT '',
  market_summary_ar TEXT DEFAULT '',
  market_summary_fr TEXT DEFAULT '',
  opportunities TEXT DEFAULT '',
  opportunities_ar TEXT DEFAULT '',
  opportunities_fr TEXT DEFAULT '',
  challenges TEXT DEFAULT '',
  challenges_ar TEXT DEFAULT '',
  challenges_fr TEXT DEFAULT '',
  regulatory_environment TEXT DEFAULT '',
  key_regulations JSONB DEFAULT '[]',
  -- Sources
  source TEXT DEFAULT '',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(country_code, year)
);

CREATE INDEX idx_market_country ON market_intelligence(country_code);
CREATE INDEX idx_market_year ON market_intelligence(year);

-- ============================================================
-- 6. Scraper Runs (for admin dashboard orchestration)
-- ============================================================
CREATE TABLE IF NOT EXISTS scraper_runs (
  id BIGSERIAL PRIMARY KEY,
  scraper_name TEXT NOT NULL,                -- 'grants_worldbank', 'ppp_ppi', 'companies_opencorp', etc.
  scraper_type TEXT NOT NULL DEFAULT 'tenders', -- 'tenders', 'grants', 'ppp', 'companies', 'market_intel'
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  records_found INTEGER DEFAULT 0,
  records_inserted INTEGER DEFAULT 0,
  records_updated INTEGER DEFAULT 0,
  records_skipped INTEGER DEFAULT 0,
  error_message TEXT DEFAULT '',
  error_stack TEXT DEFAULT '',
  triggered_by TEXT DEFAULT 'system',        -- 'system', 'admin', 'cron'
  triggered_by_user UUID REFERENCES auth.users(id),
  duration_seconds INTEGER,
  metadata JSONB DEFAULT '{}',               -- scraper-specific config/params
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_scraper_runs_name ON scraper_runs(scraper_name);
CREATE INDEX idx_scraper_runs_status ON scraper_runs(status);
CREATE INDEX idx_scraper_runs_type ON scraper_runs(scraper_type);
CREATE INDEX idx_scraper_runs_created ON scraper_runs(created_at);

-- ============================================================
-- 7. AI Credits
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_credits (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 0,
  plan_credits INTEGER NOT NULL DEFAULT 10,  -- monthly allowance from plan
  purchased_credits INTEGER NOT NULL DEFAULT 0,
  reset_date TIMESTAMPTZ,                    -- next monthly reset
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS credit_transactions (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,                   -- positive = add, negative = consume
  balance_after INTEGER NOT NULL,
  transaction_type TEXT NOT NULL,             -- 'plan_reset', 'purchase', 'consumption', 'bonus', 'refund'
  feature_key TEXT DEFAULT '',               -- which feature consumed credits
  description TEXT DEFAULT '',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_credits_user ON ai_credits(user_id);
CREATE INDEX idx_credit_tx_user ON credit_transactions(user_id);
CREATE INDEX idx_credit_tx_type ON credit_transactions(transaction_type);
CREATE INDEX idx_credit_tx_date ON credit_transactions(created_at);

-- ============================================================
-- Row Level Security for new tables
-- ============================================================

ALTER TABLE grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE ppp_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE prequalification_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_intelligence ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

-- Public data tables: readable by all authenticated users
CREATE POLICY "Grants viewable by authenticated" ON grants
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "PPP projects viewable by authenticated" ON ppp_projects
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Companies viewable by authenticated" ON companies
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "PreQual requirements viewable by authenticated" ON prequalification_requirements
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Market intel viewable by authenticated" ON market_intelligence
  FOR SELECT TO authenticated USING (true);

-- Scraper runs: admin only (service role bypasses RLS)
CREATE POLICY "Scraper runs admin only" ON scraper_runs
  FOR ALL TO authenticated
  USING (false);

-- AI Credits: users see own
CREATE POLICY "Users view own credits" ON ai_credits
  FOR SELECT TO authenticated USING (user_id = auth.uid());

CREATE POLICY "Users view own credit transactions" ON credit_transactions
  FOR SELECT TO authenticated USING (user_id = auth.uid());

-- Updated_at triggers for new tables
CREATE TRIGGER trg_grants_updated
  BEFORE UPDATE ON grants FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_ppp_updated
  BEFORE UPDATE ON ppp_projects FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_companies_updated
  BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_preq_updated
  BEFORE UPDATE ON prequalification_requirements FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_market_updated
  BEFORE UPDATE ON market_intelligence FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_credits_updated
  BEFORE UPDATE ON ai_credits FOR EACH ROW EXECUTE FUNCTION update_updated_at();
