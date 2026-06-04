-- ============================================================
-- World Cup AI Content Engine — Supabase Migration
-- New Supabase project: run this in the SQL editor
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE: matches
-- Stores World Cup fixture data (synced from football-data.org)
-- ============================================================
CREATE TABLE IF NOT EXISTS matches (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id     TEXT UNIQUE NOT NULL,
  home_team       TEXT NOT NULL,
  away_team       TEXT NOT NULL,
  home_team_flag  TEXT DEFAULT '',
  away_team_flag  TEXT DEFAULT '',
  stage           TEXT DEFAULT 'Group Stage',
  status          TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'live', 'finished', 'postponed')),
  kickoff_time    TIMESTAMPTZ,
  venue           TEXT,
  score           TEXT DEFAULT 'TBD',
  competition     TEXT DEFAULT 'FIFA World Cup 2026',
  home_team_logo  TEXT,
  away_team_logo  TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_kickoff ON matches(kickoff_time);
CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);

-- ============================================================
-- TABLE: users
-- App users (created on first generate request)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email               TEXT UNIQUE,
  display_name        TEXT,
  tier                TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
  daily_limit         INTEGER DEFAULT 10,
  monthly_limit       INTEGER DEFAULT 100,
  daily_usage         INTEGER DEFAULT 0,
  monthly_usage       INTEGER DEFAULT 0,
  total_tokens_used   INTEGER DEFAULT 0,
  total_cost_cents    INTEGER DEFAULT 0,
  stripe_customer_id  TEXT,
  last_reset_date     DATE DEFAULT CURRENT_DATE,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);

-- ============================================================
-- TABLE: content_outputs
-- Every piece of AI-generated content
-- ============================================================
CREATE TABLE IF NOT EXISTS content_outputs (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
  match_id            UUID REFERENCES matches(id) ON DELETE SET NULL,
  content_type        TEXT NOT NULL,
  input_prompt        TEXT,
  output_text         TEXT NOT NULL,
  model               TEXT DEFAULT 'gemini-2.5-flash',
  input_tokens        INTEGER DEFAULT 0,
  output_tokens       INTEGER DEFAULT 0,
  total_tokens        INTEGER DEFAULT 0,
  generation_time_ms  INTEGER DEFAULT 0,
  cost_cents          INTEGER DEFAULT 0,
  is_saved            BOOLEAN DEFAULT FALSE,
  is_shared           BOOLEAN DEFAULT FALSE,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_user_id ON content_outputs(user_id);
CREATE INDEX IF NOT EXISTS idx_content_match_id ON content_outputs(match_id);
CREATE INDEX IF NOT EXISTS idx_content_type ON content_outputs(content_type);
CREATE INDEX IF NOT EXISTS idx_content_created_at ON content_outputs(created_at DESC);

-- ============================================================
-- TABLE: usage_logs
-- Per-request metering for billing & monitoring
-- ============================================================
CREATE TABLE IF NOT EXISTS usage_logs (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
  event_type  TEXT NOT NULL CHECK (event_type IN ('generation', 'api_call', 'cache_hit', 'error')),
  resource    TEXT,
  tokens      INTEGER DEFAULT 0,
  cost_cents  INTEGER DEFAULT 0,
  metadata    JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_event_type ON usage_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage_logs(created_at DESC);

-- ============================================================
-- TABLE: prompts
-- Versioned prompt templates (override defaults from DB)
-- ============================================================
CREATE TABLE IF NOT EXISTS prompts (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  type           TEXT NOT NULL,
  version        INTEGER DEFAULT 1,
  system_message TEXT NOT NULL,
  user_template  TEXT NOT NULL,
  max_tokens     INTEGER DEFAULT 800,
  temperature    FLOAT DEFAULT 0.8,
  model          TEXT DEFAULT 'gemini-2.5-flash',
  is_active      BOOLEAN DEFAULT TRUE,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompts_type ON prompts(type);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(is_active);

-- ============================================================
-- ROW-LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;

-- Matches & prompts are public (read-only for all)
CREATE POLICY "matches_public_read" ON matches FOR SELECT USING (true);
CREATE POLICY "prompts_public_read" ON prompts FOR SELECT USING (true);

-- Users can only see their own data
CREATE POLICY "users_own_data" ON users
  FOR ALL USING (auth.uid() = id);

CREATE POLICY "content_own_data" ON content_outputs
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "usage_own_data" ON usage_logs
  FOR ALL USING (auth.uid() = user_id);

-- Service role can do everything (for Python backend)
CREATE POLICY "service_full_access_users" ON users
  FOR ALL TO service_role USING (true);

CREATE POLICY "service_full_access_content" ON content_outputs
  FOR ALL TO service_role USING (true);

CREATE POLICY "service_full_access_usage" ON usage_logs
  FOR ALL TO service_role USING (true);

CREATE POLICY "service_full_access_matches" ON matches
  FOR ALL TO service_role USING (true);

-- ============================================================
-- FUNCTION: increment_user_usage
-- ============================================================
CREATE OR REPLACE FUNCTION increment_user_usage(
  p_user_id   UUID,
  p_tokens    INTEGER,
  p_cost_cents INTEGER
)
RETURNS TABLE(daily_usage INTEGER, monthly_usage INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE users
  SET
    daily_usage       = daily_usage + 1,
    monthly_usage     = monthly_usage + 1,
    total_tokens_used = total_tokens_used + p_tokens,
    total_cost_cents  = total_cost_cents + p_cost_cents,
    updated_at        = NOW()
  WHERE id = p_user_id;

  RETURN QUERY SELECT u.daily_usage, u.monthly_usage FROM users u WHERE u.id = p_user_id;
END;
$$;

-- ============================================================
-- SEED: Insert World Cup 2026 mock fixtures
-- ============================================================
INSERT INTO matches (external_id, home_team, away_team, home_team_flag, away_team_flag, stage, status, kickoff_time, venue, score, competition)
VALUES
  ('mock-001', 'Argentina', 'Canada',      '🇦🇷', '🇨🇦', 'Group A', 'scheduled', '2026-06-11 20:00:00+00', 'SoFi Stadium, Los Angeles',         'TBD', 'FIFA World Cup 2026'),
  ('mock-002', 'Brazil',    'Mexico',      '🇧🇷', '🇲🇽', 'Group D', 'scheduled', '2026-06-12 18:00:00+00', 'Estadio Azteca, Mexico City',        'TBD', 'FIFA World Cup 2026'),
  ('mock-003', 'England',   'France',      '🏴', '🇫🇷', 'Group B', 'scheduled', '2026-06-13 21:00:00+00', 'MetLife Stadium, New York',          'TBD', 'FIFA World Cup 2026'),
  ('mock-004', 'Spain',     'Germany',     '🇪🇸', '🇩🇪', 'Group E', 'scheduled', '2026-06-14 18:00:00+00', 'AT&T Stadium, Dallas',              'TBD', 'FIFA World Cup 2026'),
  ('mock-005', 'Portugal',  'Morocco',     '🇵🇹', '🇲🇦', 'Group F', 'scheduled', '2026-06-15 21:00:00+00', 'Levi''s Stadium, San Francisco',     'TBD', 'FIFA World Cup 2026'),
  ('mock-006', 'USA',       'Netherlands', '🇺🇸', '🇳🇱', 'Group C', 'scheduled', '2026-06-16 20:00:00+00', 'Arrowhead Stadium, Kansas City',     'TBD', 'FIFA World Cup 2026'),
  ('mock-007', 'Italy',     'Japan',       '🇮🇹', '🇯🇵', 'Group G', 'scheduled', '2026-06-17 18:00:00+00', 'Lincoln Financial Field, Philly',   'TBD', 'FIFA World Cup 2026'),
  ('mock-008', 'Colombia',  'Senegal',     '🇨🇴', '🇸🇳', 'Group H', 'scheduled', '2026-06-18 21:00:00+00', 'NRG Stadium, Houston',               'TBD', 'FIFA World Cup 2026')
ON CONFLICT (external_id) DO NOTHING;
