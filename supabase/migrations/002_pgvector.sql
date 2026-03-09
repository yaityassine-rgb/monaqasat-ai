-- ============================================================
-- pgvector extension + indexes for semantic search
-- ============================================================

-- Enable pgvector (must be done by superuser / dashboard)
CREATE EXTENSION IF NOT EXISTS vector;

-- IVFFlat indexes for fast cosine similarity search
-- These are created after initial data load for best performance
CREATE INDEX IF NOT EXISTS idx_tenders_embedding
  ON tenders USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_company_profiles_embedding
  ON company_profiles USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 20);
