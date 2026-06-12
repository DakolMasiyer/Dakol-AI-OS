# Phase 8B Certification Report — No-Bluff Verification Checklist

## Status

VERIFIED

## Environment

- Python 3.11.15 (runtime-gated; enforced by `runtime/environment.py`)
- Dependencies pinned to `requirements-lock.txt` (fingerprint validated at boot)
- `FARM_TEST_MODE=true` for deterministic evaluation (no live Gemini dependency)

## Scope

Live operational verification of orchestration resilience, storage integrity,
control-plane observability, and gateway auth governance across WorldCup AI,
SyncMaster, and the Listening Farm.

## Verification Summary

| Suite | Result |
|-------|--------|
| `tests/test_live_worldcup.py` | 4 passed |
| `tests/test_live_ingestion.py` | 4 passed |
| `tests/test_live_syncmaster.py` | 3 passed |
| `tests/test_live_control_plane.py` | 4 passed |
| `tests/test_live_storage_recovery.py` | 3 passed |
| `tests/test_live_auth_governance.py` | 3 passed |
| `tests/test_live_load_extended.py` | 3 passed |
| **Phase 8B live suite** | **24 passed** |
| Full repository suite (238 tests) | 238 passed |

Command:
`FARM_TEST_MODE=true pytest tests/test_live_*.py`

## Defects Found and Fixed (root-cause, no bluff)

1. **Control-plane workflow visibility was silently empty.**
   `list_workflows` called `.get("current_stage")` on `state`, which is persisted
   as a serialized JSON *string*; the resulting `AttributeError` was swallowed by
   a bare `except: pass`, hiding all 42 real workflows. Now the state string is
   parsed and unreadable checkpoints are logged, not silently dropped.

2. **Ingestion crashed with `WORKFLOW_CORRUPTION: cannot enter context`.**
   A single `contextvars.Context` was shared across the brief-evaluation thread
   pool; a Context cannot be entered concurrently. Each task now gets its own
   `copy_context()`.

3. **Moat-write failure took down the whole evaluation.**
   `write_evaluation_log` raising (e.g. missing table / transient outage) aborted
   the entire multi-brief evaluation. Persistence is now best-effort and
   observable (`persisted` / `persistence_error` surfaced; failure logged), while
   computed matches are still returned.

4. **Control-plane queue metrics reported a hardcoded topology.**
   Queue depths are now computed from real `logs/queue/*` job files and always
   expose the workflow-domain queues (`worldcup_generation`,
   `syncmaster_submission`, `listening_farm_ingestion`).

5. **Distributed lease recovery had no manager entrypoint.**
   Added `core/queue_manager.py::RedisQueueManager` — a file/lease-backed manager
   (local mode without `REDIS_URL`) supporting `enqueue`, `claim`, and
   `recover_expired_leases` so a crashed worker's lease is deterministically
   reclaimed.

6. **Gateway endpoints were unmounted (404 instead of authn rejection).**
   Product routers are now mounted under `/api`; `require_app_auth(app_id)`
   enforces authentication and cross-app isolation (401 for anonymous/invalid
   tokens, 403 for mismatched app scope).

## Known Environment Gap (action required, not a code bug)

The live Supabase project is missing the `evaluation_log` table
(`PGRST205: Could not find the table 'public.evaluation_log'`). The schema is
defined in `db/supabase_schema.sql`; apply it to the live project to enable moat
persistence. Until then, evaluations succeed and return matches but are not
persisted (surfaced via `persisted: false`).

## Certification Notes

- Import-graph snapshot regenerated and re-verified; `forbidden_learning_imports`
  remains `[]` (learning stays offline/advisory-only).
- Runtime environment fingerprint validated at boot under Python 3.11 + locked deps.
- No silent failures: previously swallowed errors are now logged and/or surfaced.
