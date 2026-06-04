-- Disable RLS on farm tables so the API can write freely
ALTER TABLE evaluation_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE tracks DISABLE ROW LEVEL SECURITY;
