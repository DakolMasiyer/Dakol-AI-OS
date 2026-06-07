CREATE TABLE IF NOT EXISTS flutterwave_processed_tx_refs (
  tx_ref TEXT PRIMARY KEY,
  flutterwave_transaction_id TEXT,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_type TEXT NOT NULL CHECK (plan_type IN ('monthly', 'yearly')),
  currency TEXT NOT NULL CHECK (currency IN ('USD', 'NGN')),
  amount NUMERIC NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_flutterwave_processed_tx_refs_user_id
  ON flutterwave_processed_tx_refs(user_id);
