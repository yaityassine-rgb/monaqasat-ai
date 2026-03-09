-- ============================================================
-- match_tenders() RPC — personalized semantic matching
-- ============================================================

CREATE OR REPLACE FUNCTION match_tenders(
  p_user_id UUID,
  p_match_threshold FLOAT DEFAULT 0.0,
  p_match_count INTEGER DEFAULT 100,
  p_sector TEXT DEFAULT NULL,
  p_country_code TEXT DEFAULT NULL,
  p_status TEXT DEFAULT NULL
)
RETURNS TABLE (
  id TEXT,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    t.id,
    CASE
      WHEN cp.embedding IS NOT NULL AND t.embedding IS NOT NULL
      THEN 1 - (t.embedding <=> cp.embedding)
      ELSE 0.5  -- default score when no embeddings
    END AS similarity
  FROM tenders t
  LEFT JOIN company_profiles cp ON cp.id = p_user_id
  WHERE
    (p_sector IS NULL OR t.sector = p_sector)
    AND (p_country_code IS NULL OR t.country_code = p_country_code)
    AND (p_status IS NULL OR t.status = p_status)
    AND (
      cp.embedding IS NULL
      OR t.embedding IS NULL
      OR (1 - (t.embedding <=> cp.embedding)) >= p_match_threshold
    )
  ORDER BY
    CASE
      WHEN cp.embedding IS NOT NULL AND t.embedding IS NOT NULL
      THEN 1 - (t.embedding <=> cp.embedding)
      ELSE 0.5
    END DESC
  LIMIT p_match_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant access
GRANT EXECUTE ON FUNCTION match_tenders TO authenticated;
