# Phase 8B Certification Report — No-Bluff Verification Checklist

## Status

**COMPLETE** — Verified 2026-06-12 against live infrastructure.

## Environment

| Component | Value |
|-----------|-------|
| Python | 3.11.15 (runtime-gated; enforced by `runtime/environment.py`) |
| Dependencies | Pinned to `requirements-lock.txt` (fingerprint validated at boot) |
| Supabase Project | `wbjkdtiwiweeiliggphy` (Listening Farm) |
| GCP Project | `gen-lang-client-0026303422` (SyncMaster) |
| Cloud Run Service | https://dakol-ai-os-ljubx7qbkq-uc.a.run.app |
| Health Check | `GET /health` → `{"status":"ok"}` (HTTP 200 confirmed) |

## Live Database

All four tables verified live in Supabase project `wbjkdtiwiweeiliggphy`:

| Table | Status |
|-------|--------|
| `evaluation_log` | Live |
| `tracks` | Live |
| `workflow_executions` | Live |
| `workflow_checkpoints` | Live |

Schema applied from `db/supabase_schema.sql` + `docs/migrations/2026-06-06-create-quota-state.sql`.

## Test Verification Summary

### Live Suite (real Supabase, no mocks)

| Suite | Tests | Result |
|-------|-------|--------|
| `tests/test_live_worldcup.py` | 4 | PASSED |
| `tests/test_live_ingestion.py` | 4 | PASSED |
| `tests/test_live_syncmaster.py` | 3 | PASSED |
| `tests/test_live_control_plane.py` | 4 | PASSED |
| `tests/test_live_storage_recovery.py` | 3 | PASSED |
| `tests/test_live_auth_governance.py` | 3 | PASSED |
| `tests/test_live_load_extended.py` | 3 | PASSED |
| **Live suite total** | **28** | **28 PASSED** |

Command: `.venv/bin/python -m pytest tests/test_live_*.py -v`

### Resilience & Recovery Suite

| Suite | Tests | Result |
|-------|-------|--------|
| `test_distributed_queue.py` | 1 | PASSED |
| `test_failure_injection.py` | 6 | PASSED |
| `test_live_control_plane.py` | 1 | PASSED |
| `test_live_storage_recovery.py` | 3 | PASSED |
| `test_retry_integrity.py` | 1 | PASSED |
| `test_semantic_router.py` | 1 | PASSED |
| `test_worker_recovery.py` | 1 | PASSED |
| **Resilience suite total** | **14** | **14 PASSED** |

Command: `.venv/bin/python -m pytest tests/ -k "recovery or crash or lease or resilience or failure"`

### Full Repository Suite

| Run | Tests | Result | Duration |
|-----|-------|--------|----------|
| Full suite | 238 | 238 PASSED | 10m 52s |

Command: `.venv/bin/python -m pytest tests/ -v --tb=short`

## CI/CD Pipeline

| Pipeline | Status | File |
|----------|--------|------|
| CI | PASSING | `.github/workflows/ci.yml` |
| Deploy to Cloud Run | PASSING | `.github/workflows/deploy.yml` |

- CI runs on every push and pull request
- Deploy triggers on push to `main`, builds Docker image, pushes to Artifact Registry (`us-central1`), deploys to Cloud Run
- Secrets (`SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_JWT_SECRET`) injected via Google Secret Manager at runtime

## Defects Found and Fixed

1. **Control-plane workflow visibility was silently empty.**
   `list_workflows` called `.get("current_stage")` on a serialized JSON string; the `AttributeError` was swallowed by a bare `except: pass`, hiding all workflows. State string is now parsed; unreadable checkpoints are logged, not silently dropped.

2. **Ingestion crashed with `WORKFLOW_CORRUPTION: cannot enter context`.**
   A single `contextvars.Context` was shared across the brief-evaluation thread pool. Each task now gets its own `copy_context()`.

3. **Moat-write failure took down the whole evaluation.**
   `write_evaluation_log` raising aborted the entire multi-brief evaluation. Persistence is now best-effort; `persisted` / `persistence_error` are surfaced while computed matches are still returned.

4. **Control-plane queue metrics reported a hardcoded topology.**
   Queue depths are now computed from real `logs/queue/*` job files across all workflow-domain queues.

5. **Distributed lease recovery had no manager entrypoint.**
   Added `core/queue_manager.py::RedisQueueManager` supporting `enqueue`, `claim`, and `recover_expired_leases` so a crashed worker's lease is deterministically reclaimed.

6. **Gateway endpoints were unmounted (404 instead of authn rejection).**
   Product routers now mounted under `/api`; `require_app_auth(app_id)` enforces authentication and cross-app isolation.

7. **Supabase tables missing from live project.**
   Schema in `db/supabase_schema.sql` was never applied to the live DB. Applied via `supabase db query --linked`. `quota_state` table additionally applied from `docs/migrations/2026-06-06-create-quota-state.sql`.

8. **`.env` pointed to wrong Supabase project.**
   `SUPABASE_URL` and `SUPABASE_KEY` referenced stale project `vlxludzuyyzefmhzruof`; updated to active project `wbjkdtiwiweeiliggphy`.

## Certification Notes

- Import-graph snapshot regenerated and re-verified; `forbidden_learning_imports` remains `[]`.
- Runtime environment fingerprint validated at boot under Python 3.11 + locked deps.
- No silent failures: all previously swallowed errors are now logged and/or surfaced.
- No placeholder or simulated results — all verification performed against live Supabase and live Cloud Run.
