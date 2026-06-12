CREATE TABLE IF NOT EXISTS evaluation_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  track_id UUID,
  track_source TEXT,
  brief_id TEXT,
  placement_type TEXT,
  brief JSONB,
  fit_score FLOAT,
  strengths TEXT[],
  weaknesses TEXT[],
  recommendation TEXT,
  reasoning TEXT,
  bpm_estimate FLOAT,
  key_estimate TEXT,
  energy_level FLOAT,
  mood_tags TEXT[],
  listener_model TEXT,
  synthetic BOOLEAN DEFAULT FALSE,
  evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id UUID,
  audio_url TEXT,
  filename TEXT,
  duration_secs FLOAT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id TEXT UNIQUE NOT NULL,
  app_id TEXT NOT NULL,
  status TEXT NOT NULL,
  state JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id TEXT NOT NULL REFERENCES workflow_executions(workflow_id),
  stage TEXT NOT NULL,
  payload JSONB,
  result JSONB,
  checkpoint_time TIMESTAMPTZ DEFAULT NOW()
);
