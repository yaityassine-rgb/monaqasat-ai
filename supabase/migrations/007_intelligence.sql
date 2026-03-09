-- ============================================================
-- Intelligence Platform — bid_outcomes, award_notices, tender_snapshots
-- ============================================================

-- Track user bid outcomes for win probability model
CREATE TABLE bid_outcomes (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tender_id TEXT NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
  outcome TEXT NOT NULL CHECK (outcome IN ('won', 'lost', 'pending', 'no_bid')),
  bid_amount NUMERIC,
  currency TEXT DEFAULT 'USD',
  winning_amount NUMERIC,
  competitor_count INTEGER,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, tender_id)
);

-- Award notices scraped from procurement portals
CREATE TABLE award_notices (
  id BIGSERIAL PRIMARY KEY,
  tender_id TEXT REFERENCES tenders(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  organization TEXT,
  country_code TEXT,
  sector TEXT,
  winner_name TEXT,
  winner_country TEXT,
  award_amount NUMERIC,
  currency TEXT DEFAULT 'USD',
  award_date DATE,
  source TEXT,
  source_url TEXT,
  raw_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Monthly tender snapshots for trend analysis
CREATE TABLE tender_snapshots (
  id BIGSERIAL PRIMARY KEY,
  snapshot_month DATE NOT NULL, -- first of month
  country_code TEXT NOT NULL,
  sector TEXT NOT NULL,
  tender_count INTEGER NOT NULL DEFAULT 0,
  total_value NUMERIC NOT NULL DEFAULT 0,
  avg_budget NUMERIC NOT NULL DEFAULT 0,
  open_count INTEGER NOT NULL DEFAULT 0,
  avg_lead_days INTEGER, -- avg days from publish to deadline
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(snapshot_month, country_code, sector)
);

-- Indexes
CREATE INDEX idx_bid_outcomes_user ON bid_outcomes(user_id);
CREATE INDEX idx_bid_outcomes_tender ON bid_outcomes(tender_id);
CREATE INDEX idx_award_notices_sector ON award_notices(sector);
CREATE INDEX idx_award_notices_country ON award_notices(country_code);
CREATE INDEX idx_award_notices_winner ON award_notices(winner_name);
CREATE INDEX idx_award_notices_date ON award_notices(award_date);
CREATE INDEX idx_tender_snapshots_month ON tender_snapshots(snapshot_month);
CREATE INDEX idx_tender_snapshots_country ON tender_snapshots(country_code);

-- Updated_at trigger for bid_outcomes
CREATE TRIGGER trg_bid_outcomes_updated
  BEFORE UPDATE ON bid_outcomes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS
ALTER TABLE bid_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE award_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE tender_snapshots ENABLE ROW LEVEL SECURITY;

-- Bid outcomes: users see only their own
CREATE POLICY "Users can view own bid outcomes"
  ON bid_outcomes FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can insert own bid outcomes"
  ON bid_outcomes FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own bid outcomes"
  ON bid_outcomes FOR UPDATE TO authenticated
  USING (user_id = auth.uid());

-- Award notices: all authenticated users can view (public data)
CREATE POLICY "Authenticated users can view award notices"
  ON award_notices FOR SELECT TO authenticated
  USING (true);

-- Tender snapshots: all authenticated users can view
CREATE POLICY "Authenticated users can view snapshots"
  ON tender_snapshots FOR SELECT TO authenticated
  USING (true);

-- ============================================================
-- Function: compute monthly snapshot from current tender data
-- ============================================================
CREATE OR REPLACE FUNCTION compute_tender_snapshot(p_month DATE DEFAULT date_trunc('month', now())::date)
RETURNS INTEGER AS $$
DECLARE
  inserted_count INTEGER;
BEGIN
  INSERT INTO tender_snapshots (snapshot_month, country_code, sector, tender_count, total_value, avg_budget, open_count, avg_lead_days)
  SELECT
    p_month,
    t.country_code,
    t.sector,
    COUNT(*) AS tender_count,
    COALESCE(SUM(t.budget), 0) AS total_value,
    COALESCE(AVG(NULLIF(t.budget, 0)), 0) AS avg_budget,
    COUNT(*) FILTER (WHERE t.status IN ('open', 'closing-soon')) AS open_count,
    AVG(
      CASE WHEN t.deadline IS NOT NULL AND t.created_at IS NOT NULL
        THEN EXTRACT(DAY FROM (t.deadline::timestamp - t.created_at))
        ELSE NULL
      END
    )::integer AS avg_lead_days
  FROM tenders t
  WHERE t.created_at >= p_month
    AND t.created_at < (p_month + interval '1 month')
  GROUP BY t.country_code, t.sector
  ON CONFLICT (snapshot_month, country_code, sector)
  DO UPDATE SET
    tender_count = EXCLUDED.tender_count,
    total_value = EXCLUDED.total_value,
    avg_budget = EXCLUDED.avg_budget,
    open_count = EXCLUDED.open_count,
    avg_lead_days = EXCLUDED.avg_lead_days;

  GET DIAGNOSTICS inserted_count = ROW_COUNT;
  RETURN inserted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- Function: get market trends (compare current vs previous month)
-- ============================================================
CREATE OR REPLACE FUNCTION get_market_trends(
  p_months INTEGER DEFAULT 6
)
RETURNS TABLE (
  snapshot_month DATE,
  country_code TEXT,
  sector TEXT,
  tender_count INTEGER,
  total_value NUMERIC,
  avg_budget NUMERIC,
  open_count INTEGER,
  avg_lead_days INTEGER
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    ts.snapshot_month,
    ts.country_code,
    ts.sector,
    ts.tender_count,
    ts.total_value,
    ts.avg_budget,
    ts.open_count,
    ts.avg_lead_days
  FROM tender_snapshots ts
  WHERE ts.snapshot_month >= (date_trunc('month', now()) - (p_months || ' months')::interval)::date
  ORDER BY ts.snapshot_month DESC, ts.total_value DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION compute_tender_snapshot TO authenticated;
GRANT EXECUTE ON FUNCTION get_market_trends TO authenticated;
