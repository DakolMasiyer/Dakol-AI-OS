# SyncMaster — Pending Fixes

## From graph analysis (2026-06-13)

### 1. route_task_semantically() — cross-community god node (42 edges)
Sits at the intersection of WorldCup, SyncMaster, and core routing. Any change to 
intent detection or agent weights will ripple here. Needs isolated unit tests before 
touching orchestrator logic.

### 2. create_syncmaster_submission_workflow — hardcoded mock
generate_rec_stage returns {"sync_fit": "high", "score": 95} — not wired to 
syncmaster/matching.py or syncmaster/licensing.py. PRD gap 5.
Fix: connect to syncmaster.matching.match_to_brief() and 
syncmaster.licensing.recommend_licensing()

### 3. syncmaster/audio.py — audioop deprecated
Uses audioop (removed in Python 3.13). Replace with numpy RMS/peak computation.
PRD gap from Section 13.

### 4. LocalStorageBackend — 32 edges, god node
Memory and learning state backed by local filesystem. Resets on Cloud Run restart.
Fix: migrate to Supabase-backed storage (PRD gap 1 — highest unblocking value).

### 5. SyncMaster Intelligence Layer ↔ imayer Intelligence Stack
Graph shows these two subsystems described from different angles in separate docs.
Consolidate into a single architecture doc to avoid drift.
