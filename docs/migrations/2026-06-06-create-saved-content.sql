CREATE TABLE IF NOT EXISTS saved_content (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  content_type TEXT NOT NULL,
  match_json JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_saved_content_user_id
  ON saved_content(user_id);

ALTER TABLE saved_content ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read their own saved content" ON saved_content;
CREATE POLICY "Users can read their own saved content"
  ON saved_content
  FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own saved content" ON saved_content;
CREATE POLICY "Users can insert their own saved content"
  ON saved_content
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own saved content" ON saved_content;
CREATE POLICY "Users can update their own saved content"
  ON saved_content
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own saved content" ON saved_content;
CREATE POLICY "Users can delete their own saved content"
  ON saved_content
  FOR DELETE
  USING (auth.uid() = user_id);
