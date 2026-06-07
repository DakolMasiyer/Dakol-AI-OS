CREATE TABLE IF NOT EXISTS brand_profiles (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  default_tone TEXT NOT NULL DEFAULT 'analytical',
  default_platforms TEXT[] NOT NULL DEFAULT ARRAY['twitter']::TEXT[],
  favourite_team TEXT NOT NULL DEFAULT '',
  style_notes TEXT NOT NULL DEFAULT '',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_profiles_user_id
  ON brand_profiles(user_id);

ALTER TABLE brand_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read their own brand profile" ON brand_profiles;
CREATE POLICY "Users can read their own brand profile"
  ON brand_profiles
  FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own brand profile" ON brand_profiles;
CREATE POLICY "Users can insert their own brand profile"
  ON brand_profiles
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own brand profile" ON brand_profiles;
CREATE POLICY "Users can update their own brand profile"
  ON brand_profiles
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
