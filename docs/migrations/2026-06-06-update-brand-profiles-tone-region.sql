ALTER TABLE brand_profiles
  ADD COLUMN IF NOT EXISTS tone_key TEXT DEFAULT 'analytical',
  ADD COLUMN IF NOT EXISTS region_key TEXT DEFAULT 'global',
  ADD COLUMN IF NOT EXISTS custom_tone_instruction TEXT DEFAULT NULL;

UPDATE brand_profiles
SET
  tone_key = COALESCE(
    tone_key,
    CASE
      WHEN default_tone = 'editorial' THEN 'professional'
      ELSE default_tone
    END,
    'analytical'
  ),
  default_tone = COALESCE(
    tone_key,
    CASE
      WHEN default_tone = 'editorial' THEN 'professional'
      ELSE default_tone
    END,
    'analytical'
  ),
  region_key = COALESCE(NULLIF(region_key, ''), 'global')
WHERE TRUE;

ALTER TABLE brand_profiles
  ALTER COLUMN tone_key SET DEFAULT 'analytical',
  ALTER COLUMN region_key SET DEFAULT 'global';

