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
