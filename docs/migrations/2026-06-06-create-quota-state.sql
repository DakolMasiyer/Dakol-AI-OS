CREATE TABLE IF NOT EXISTS quota_state (
  key        TEXT PRIMARY KEY,
  value      JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE quota_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "quota_state_service_all" ON quota_state;
CREATE POLICY "quota_state_service_all" ON quota_state
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);
