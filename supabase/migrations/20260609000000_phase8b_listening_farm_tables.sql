-- Phase 8B: Listening Farm moat tables and orchestration tables.
-- Apply via: supabase db push
-- Or paste directly in the Supabase Dashboard SQL editor.

-- Evaluation moat: every brief × track evaluation written here.
CREATE TABLE IF NOT EXISTS public.evaluation_log (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  track_id        UUID,
  track_source    TEXT,
  brief_id        TEXT,
  placement_type  TEXT,
  brief           JSONB,
  fit_score       FLOAT,
  strengths       TEXT[],
  weaknesses      TEXT[],
  recommendation  TEXT,
  reasoning       TEXT,
  bpm_estimate    FLOAT,
  key_estimate    TEXT,
  energy_level    FLOAT,
  mood_tags       TEXT[],
  listener_model  TEXT,
  synthetic       BOOLEAN     NOT NULL DEFAULT FALSE,
  evaluated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Track catalogue: audio assets uploaded or imported into the farm.
CREATE TABLE IF NOT EXISTS public.tracks (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id    UUID,
  audio_url    TEXT,
  filename     TEXT,
  duration_secs FLOAT,
  title        TEXT,
  uploaded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orchestration: top-level record per workflow execution.
CREATE TABLE IF NOT EXISTS public.workflow_executions (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id TEXT        UNIQUE NOT NULL,
  app_id      TEXT        NOT NULL,
  status      TEXT        NOT NULL,
  state       JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orchestration: checkpoint per stage within a workflow execution.
CREATE TABLE IF NOT EXISTS public.workflow_checkpoints (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id      TEXT        NOT NULL REFERENCES public.workflow_executions(workflow_id),
  stage            TEXT        NOT NULL,
  payload          JSONB,
  result           JSONB,
  checkpoint_time  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast track-level evaluation queries.
CREATE INDEX IF NOT EXISTS idx_evaluation_log_track_id
  ON public.evaluation_log (track_id);

CREATE INDEX IF NOT EXISTS idx_evaluation_log_brief_id
  ON public.evaluation_log (brief_id);

CREATE INDEX IF NOT EXISTS idx_workflow_checkpoints_workflow_id
  ON public.workflow_checkpoints (workflow_id);
