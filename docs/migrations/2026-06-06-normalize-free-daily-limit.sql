UPDATE users
SET
  daily_limit = 3,
  updated_at = now()
WHERE
  tier = 'free'
  AND daily_limit = 10;
