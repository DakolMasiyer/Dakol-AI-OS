-- ============================================================
-- WORLD CUP AI — COMBINED SUPABASE MIGRATION SCRIPT
-- Copy and paste the entire content of this script into your 
-- Supabase Dashboard SQL Editor and click "Run".
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE: matches
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
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email               TEXT UNIQUE,
  display_name        TEXT,
  tier                TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
  daily_limit         INTEGER DEFAULT 3,
  monthly_limit       INTEGER DEFAULT 100,
  daily_usage         INTEGER DEFAULT 0,
  monthly_usage       INTEGER DEFAULT 0,
  total_tokens_used   INTEGER DEFAULT 0,
  total_cost_cents    INTEGER DEFAULT 0,
  stripe_customer_id  TEXT,
  expires_at          TIMESTAMPTZ,
  last_reset_date     DATE DEFAULT CURRENT_DATE,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);

-- ============================================================
-- TABLE: content_outputs
-- ============================================================
CREATE TABLE IF NOT EXISTS content_outputs (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
  match_id            UUID REFERENCES matches(id) ON DELETE SET NULL,
  content_type        TEXT NOT NULL,
  input_prompt        TEXT,
  output_text         TEXT NOT NULL,
  model               TEXT DEFAULT 'gemini-1.5-flash',
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
-- ============================================================
CREATE TABLE IF NOT EXISTS prompts (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  type           TEXT NOT NULL,
  version        INTEGER DEFAULT 1,
  system_message TEXT NOT NULL,
  user_template  TEXT NOT NULL,
  max_tokens     INTEGER DEFAULT 800,
  temperature    FLOAT DEFAULT 0.8,
  model          TEXT DEFAULT 'gemini-1.5-flash',
  is_active      BOOLEAN DEFAULT TRUE,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompts_type ON prompts(type);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(is_active);

-- ============================================================
-- TABLE: historical_matches
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

CREATE INDEX IF NOT EXISTS idx_hist_year ON historical_matches(year);
CREATE INDEX IF NOT EXISTS idx_hist_home_team ON historical_matches(home_team);
CREATE INDEX IF NOT EXISTS idx_hist_away_team ON historical_matches(away_team);

-- ============================================================
-- TABLE: brand_profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS brand_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  default_tone TEXT NOT NULL DEFAULT 'analytical',
  default_platforms TEXT[] NOT NULL DEFAULT ARRAY['twitter']::TEXT[],
  favourite_team TEXT NOT NULL DEFAULT '',
  style_notes TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  tone_key TEXT DEFAULT 'analytical',
  region_key TEXT DEFAULT 'global',
  custom_tone_instruction TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_profiles_user_id ON brand_profiles(user_id);

-- ============================================================
-- TABLE: saved_content
-- ============================================================
CREATE TABLE IF NOT EXISTS saved_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  content_type TEXT NOT NULL,
  match_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saved_content_user_id ON saved_content(user_id);

-- ============================================================
-- TABLE: social_connections
-- ============================================================
CREATE TABLE IF NOT EXISTS social_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('twitter', 'instagram', 'linkedin')),
  access_token TEXT NOT NULL,
  refresh_token TEXT,
  token_expires_at TIMESTAMPTZ,
  platform_user_id TEXT,
  platform_username TEXT,
  connected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_social_connections_user_id ON social_connections(user_id);

-- ============================================================
-- TABLE: quota_state
-- ============================================================
CREATE TABLE IF NOT EXISTS quota_state (
  key        TEXT PRIMARY KEY,
  value      JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: flutterwave_processed_tx_refs
-- ============================================================
CREATE TABLE IF NOT EXISTS flutterwave_processed_tx_refs (
  tx_ref TEXT PRIMARY KEY,
  flutterwave_transaction_id TEXT,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_type TEXT NOT NULL CHECK (plan_type IN ('monthly', 'yearly')),
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'NGN')),
  amount NUMERIC NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_flutterwave_processed_tx_refs_user_id ON flutterwave_processed_tx_refs(user_id);

-- ============================================================
-- ROW-LEVEL SECURITY (RLS) & POLICIES
-- ============================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_outputs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE historical_matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE quota_state ENABLE ROW LEVEL SECURITY;

-- Matches & prompts public read
DROP POLICY IF EXISTS "matches_public_read" ON matches;
CREATE POLICY "matches_public_read" ON matches FOR SELECT USING (true);

DROP POLICY IF EXISTS "prompts_public_read" ON prompts;
CREATE POLICY "prompts_public_read" ON prompts FOR SELECT USING (true);

-- User self-access policies
DROP POLICY IF EXISTS "users_own_data" ON users;
CREATE POLICY "users_own_data" ON users FOR ALL USING (auth.uid() = id);

DROP POLICY IF EXISTS "content_own_data" ON content_outputs;
CREATE POLICY "content_own_data" ON content_outputs FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "usage_own_data" ON usage_logs;
CREATE POLICY "usage_own_data" ON usage_logs FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can read their own brand profile" ON brand_profiles;
CREATE POLICY "Users can read their own brand profile" ON brand_profiles FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own brand profile" ON brand_profiles;
CREATE POLICY "Users can insert their own brand profile" ON brand_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own brand profile" ON brand_profiles;
CREATE POLICY "Users can update their own brand profile" ON brand_profiles FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "brand_profiles_delete" ON brand_profiles
  FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can read their own saved content" ON saved_content;
CREATE POLICY "Users can read their own saved content" ON saved_content FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own saved content" ON saved_content;
CREATE POLICY "Users can insert their own saved content" ON saved_content FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own saved content" ON saved_content;
CREATE POLICY "Users can update their own saved content" ON saved_content FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own saved content" ON saved_content;
CREATE POLICY "Users can delete their own saved content" ON saved_content FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can read their own social connections" ON social_connections;
CREATE POLICY "Users can read their own social connections" ON social_connections FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own social connections" ON social_connections;
CREATE POLICY "Users can insert their own social connections" ON social_connections FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own social connections" ON social_connections;
CREATE POLICY "Users can update their own social connections" ON social_connections FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own social connections" ON social_connections;
CREATE POLICY "Users can delete their own social connections" ON social_connections FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "historical_matches_public_read" ON historical_matches;
CREATE POLICY "historical_matches_public_read" ON historical_matches FOR SELECT USING (true);

-- Service-role full access policies
DROP POLICY IF EXISTS "service_full_access_users" ON users;
CREATE POLICY "service_full_access_users" ON users FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "service_full_access_content" ON content_outputs;
CREATE POLICY "service_full_access_content" ON content_outputs FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "service_full_access_usage" ON usage_logs;
CREATE POLICY "service_full_access_usage" ON usage_logs FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "service_full_access_matches" ON matches;
CREATE POLICY "service_full_access_matches" ON matches FOR ALL TO service_role USING (true);

DROP POLICY IF EXISTS "quota_state_service_all" ON quota_state;
CREATE POLICY "quota_state_service_all" ON quota_state FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "historical_matches_service_all" ON historical_matches;
CREATE POLICY "historical_matches_service_all" ON historical_matches FOR ALL TO service_role USING (true);

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
-- FUNCTION: increment_usage
-- ============================================================
CREATE OR REPLACE FUNCTION increment_usage(
  p_user_id UUID,
  p_tokens int DEFAULT 0,
  p_increment_generation boolean DEFAULT true
)
RETURNS TABLE(allowed boolean, daily_usage integer, daily_limit integer)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  UPDATE users
    SET
      daily_usage        = users.daily_usage + CASE WHEN p_increment_generation THEN 1 ELSE 0 END,
      total_tokens_used  = COALESCE(total_tokens_used, 0) + p_tokens,
      updated_at         = now()
    WHERE
      id = p_user_id
      AND (
        NOT p_increment_generation
        OR tier <> 'free'
        OR users.daily_usage < users.daily_limit
      )
    RETURNING true, users.daily_usage, users.daily_limit
    INTO allowed, daily_usage, daily_limit;

  IF FOUND THEN
    RETURN NEXT;
    RETURN;
  END IF;

  RETURN QUERY
    SELECT false, users.daily_usage, users.daily_limit
    FROM users
    WHERE id = p_user_id;
END;
$$;

-- ============================================================
-- SEED DATA: Insert World Cup 2026 fixtures
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
