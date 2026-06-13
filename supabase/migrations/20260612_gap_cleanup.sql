-- Gap 5: monthly_limit removed (app uses PLAN_MONTHLY_LIMITS hardcode)
-- Gap 7: usage_logs removed (no consumer; content_outputs covers generation tracking)

ALTER TABLE users DROP COLUMN IF EXISTS monthly_limit;
DROP TABLE IF EXISTS usage_logs;
