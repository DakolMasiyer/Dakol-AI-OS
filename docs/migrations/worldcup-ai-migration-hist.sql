-- ============================================================
-- World Cup AI Content Engine — Historical Matches Migration
-- Run this in your Supabase SQL editor
-- ============================================================

CREATE TABLE IF NOT EXISTS historical_matches (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  year            INTEGER NOT NULL,
  date            DATE,
  home_team       TEXT NOT NULL,
  away_team       TEXT NOT NULL,
  home_score      INTEGER,
  away_score      INTEGER,
  tournament      TEXT DEFAULT 'FIFA World Cup',
  city            TEXT,
  country         TEXT,
  neutral         BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast query lookup
CREATE INDEX IF NOT EXISTS idx_hist_year ON historical_matches(year);
CREATE INDEX IF NOT EXISTS idx_hist_home_team ON historical_matches(home_team);
CREATE INDEX IF NOT EXISTS idx_hist_away_team ON historical_matches(away_team);

-- Enable Row Level Security (RLS)
ALTER TABLE historical_matches ENABLE ROW LEVEL SECURITY;

-- Policies
DROP POLICY IF EXISTS "historical_matches_public_read" ON historical_matches;
CREATE POLICY "historical_matches_public_read" ON historical_matches 
  FOR SELECT USING (true);

DROP POLICY IF EXISTS "historical_matches_anon_insert" ON historical_matches;
CREATE POLICY "historical_matches_anon_insert" ON historical_matches 
  FOR INSERT TO anon WITH CHECK (true);

DROP POLICY IF EXISTS "historical_matches_service_all" ON historical_matches;
CREATE POLICY "historical_matches_service_all" ON historical_matches 
  FOR ALL TO service_role USING (true);
