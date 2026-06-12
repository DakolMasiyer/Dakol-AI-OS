#!/usr/bin/env bash
# Apply the Phase 8B listening-farm tables to the live Supabase project.
# Run once after obtaining a Personal Access Token from:
#   https://supabase.com/dashboard/account/tokens
#
# Usage:
#   ./scripts/apply_phase8b_migration.sh

set -euo pipefail

MIGRATION="supabase/migrations/20260609000000_phase8b_listening_farm_tables.sql"
PROJECT_REF="vlxludzuyyzefmhzruof"

if [[ ! -f "$MIGRATION" ]]; then
  echo "ERROR: migration file not found: $MIGRATION" >&2
  exit 1
fi

# ---- Option A: Supabase CLI (preferred) ------------------------------------
if command -v supabase &>/dev/null; then
  if supabase projects list &>/dev/null 2>&1; then
    echo "Supabase CLI is authenticated — linking and pushing migration..."
    supabase link --project-ref "$PROJECT_REF"
    supabase db push
    echo "Done. Verifying tables..."
    supabase db query "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('evaluation_log','tracks','workflow_executions','workflow_checkpoints') ORDER BY table_name;" --project-ref "$PROJECT_REF"
    exit 0
  else
    echo "Supabase CLI found but not logged in."
    echo "Run: supabase login"
    echo "Then re-run this script."
  fi
fi

# ---- Option B: Management API with PAT -------------------------------------
if [[ -n "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
  echo "Using Management API with SUPABASE_ACCESS_TOKEN..."
  SQL=$(cat "$MIGRATION")
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "https://api.supabase.com/v1/projects/${PROJECT_REF}/database/query" \
    -H "Authorization: Bearer ${SUPABASE_ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"query\": $(echo "$SQL" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}")
  if [[ "$RESPONSE" == "200" ]]; then
    echo "Migration applied successfully."
  else
    echo "Management API returned HTTP $RESPONSE. Check your token or try the dashboard."
    exit 1
  fi
  exit 0
fi

# ---- Option C: Paste into Dashboard SQL editor -----------------------------
echo ""
echo "====================================================================="
echo "Could not apply automatically. Paste the following SQL into:"
echo "  https://supabase.com/dashboard/project/${PROJECT_REF}/sql/new"
echo "====================================================================="
echo ""
cat "$MIGRATION"
