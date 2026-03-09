-- ============================================================
-- Smart Email Alerts — alert_preferences + alert_history
-- ============================================================

-- Alert preferences (one per user)
CREATE TABLE alert_preferences (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL DEFAULT false,
  frequency TEXT NOT NULL DEFAULT 'daily' CHECK (frequency IN ('instant', 'daily', 'weekly')),
  min_match_score INTEGER NOT NULL DEFAULT 60 CHECK (min_match_score BETWEEN 0 AND 100),
  sectors TEXT[] NOT NULL DEFAULT '{}',         -- empty = all sectors
  countries TEXT[] NOT NULL DEFAULT '{}',       -- empty = all countries
  statuses TEXT[] NOT NULL DEFAULT '{open,closing-soon}',
  min_budget NUMERIC NOT NULL DEFAULT 0,
  email_override TEXT,                          -- override user email if needed
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Alert history (log of sent alerts)
CREATE TABLE alert_history (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tender_ids TEXT[] NOT NULL DEFAULT '{}',
  tender_count INTEGER NOT NULL DEFAULT 0,
  match_scores JSONB NOT NULL DEFAULT '{}',     -- {tender_id: score}
  email_sent_to TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'skipped')),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_alert_prefs_enabled ON alert_preferences(enabled) WHERE enabled = true;
CREATE INDEX idx_alert_history_user ON alert_history(user_id);
CREATE INDEX idx_alert_history_date ON alert_history(created_at);

-- Updated_at trigger
CREATE TRIGGER trg_alert_preferences_updated
  BEFORE UPDATE ON alert_preferences
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS
ALTER TABLE alert_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own alert preferences"
  ON alert_preferences FOR SELECT
  TO authenticated
  USING (id = auth.uid());

CREATE POLICY "Users can insert own alert preferences"
  ON alert_preferences FOR INSERT
  TO authenticated
  WITH CHECK (id = auth.uid());

CREATE POLICY "Users can update own alert preferences"
  ON alert_preferences FOR UPDATE
  TO authenticated
  USING (id = auth.uid());

CREATE POLICY "Users can view own alert history"
  ON alert_history FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

-- ============================================================
-- Helper: get new tenders since a given timestamp
-- ============================================================

CREATE OR REPLACE FUNCTION get_new_matching_tenders(
  p_user_id UUID,
  p_since TIMESTAMPTZ,
  p_min_score FLOAT DEFAULT 0.6,
  p_sectors TEXT[] DEFAULT '{}',
  p_countries TEXT[] DEFAULT '{}',
  p_statuses TEXT[] DEFAULT '{open,closing-soon}',
  p_min_budget NUMERIC DEFAULT 0,
  p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
  tender_id TEXT,
  similarity FLOAT,
  title_en TEXT,
  title_ar TEXT,
  organization_en TEXT,
  country_code TEXT,
  sector TEXT,
  budget NUMERIC,
  currency TEXT,
  deadline TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.id AS tender_id,
    CASE
      WHEN cp.embedding IS NOT NULL AND t.embedding IS NOT NULL
      THEN 1 - (t.embedding <=> cp.embedding)
      ELSE 0.5
    END AS similarity,
    t.title_en,
    t.title_ar,
    t.organization_en,
    t.country_code,
    t.sector,
    t.budget,
    t.currency,
    t.deadline
  FROM tenders t
  LEFT JOIN company_profiles cp ON cp.id = p_user_id
  WHERE
    t.created_at >= p_since
    AND (array_length(p_statuses, 1) IS NULL OR t.status = ANY(p_statuses))
    AND (array_length(p_sectors, 1) IS NULL OR t.sector = ANY(p_sectors))
    AND (array_length(p_countries, 1) IS NULL OR t.country_code = ANY(p_countries))
    AND t.budget >= p_min_budget
    AND (
      cp.embedding IS NULL
      OR t.embedding IS NULL
      OR (1 - (t.embedding <=> cp.embedding)) >= p_min_score
    )
  ORDER BY
    CASE
      WHEN cp.embedding IS NOT NULL AND t.embedding IS NOT NULL
      THEN 1 - (t.embedding <=> cp.embedding)
      ELSE 0.5
    END DESC
  LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION get_new_matching_tenders TO authenticated;
