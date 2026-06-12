# Phase 8B: No-Bluff Verification Checklist Implementation Plan

## Goal Description

Systematically verify all Phase 8B requirements using the "No-Bluff Verification Checklist". The objective is to prove through observable, testable, replayable, and operationally verified tests that the live operational traffic capabilities, orchestration resilience, storage integrity, and control plane integrations work securely and correctly.

## User Review Required

Please review the proposed test structure. For items requiring cloud deployment verification (Step 9: Cloud Run, CI/CD), I will verify using simulated scripts and mocked checks since I operate in a local IDE environment. Are you okay with simulated environment variables and mock CI/CD execution for Step 9?

## Proposed Changes

We will build an automated verification suite that enforces the "No Bluff" rule. I will create the following test files in the `tests/` directory to explicitly run these checks:

### 1. `tests/test_live_worldcup.py`
- Tests a real `/worldcup/generate` request.
- Simulates a generation stage failure to test retry safety.
- Tests the publishing pipeline and verifies artifacts and traces are stored.
- Replays a completed generation and checks fingerprint immutability.

### 2. `tests/test_live_ingestion.py`
- Triggers `/syncmaster/evaluate` to confirm ingestion workflows create evaluation entries in Supabase.
- Runs concurrent ingestion jobs using ThreadPoolExecutor to verify no duplicate evaluations.
- Simulates quota exhaustion (using our quota manager mock) and verifies safe halts.
- Confirms that scoring lineage and intelligence accumulation persists correctly.

### 3. `tests/test_live_syncmaster.py`
- Hits `/syncmaster/submit` to test catalog submission queueing.
- Asserts that the human approval checkpoint pauses execution (`status: "PAUSED"`).
- Tests recommendation exports and ensures lineage is preserved.

### 4. `tests/test_live_control_plane.py`
- Hits `/control-plane/metrics` and `/control-plane/workflows` endpoints.
- Triggers worker failures and verifies incidents appear in the dashboard.
- Retrieves replay traces from the logs.

### 5. `tests/test_live_storage_recovery.py`
- Verifies traces persist and can be queried.
- Validates that `evaluation_log`, `workflow_executions`, and `workflow_checkpoints` are appended properly in `db/supabase_schema.sql` mappings.
- Tests worker crash recovery by simulating a process crash and validating that another worker recovers the lease deterministically.

### 6. `tests/test_live_auth_governance.py`
- Tests unauthorized requests via missing/invalid JWTs (mocked via middleware).
- Verifies cross-app access rules (WorldCup tokens vs SyncMaster).
- Verifies frontend mutation attempts to the internal workflow engine are rejected.

### 7. `tests/test_live_load_extended.py`
- Launches simultaneous jobs to test concurrency stability.
- Replays workflows during active load.
- Validates queue depth scaling behavior.

## Verification Plan

### Automated Tests
- Run `venv/bin/pytest tests/test_live_*.py`
- Generate a final `certification_report.md` proving the checklist passes successfully.

### Manual Verification
- Output logs demonstrating trace lineage, queue states, recovery behavior, and dashboard visibility directly into the final report.
